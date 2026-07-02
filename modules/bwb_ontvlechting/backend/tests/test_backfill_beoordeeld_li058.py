"""LI058 (Slice 2) — profiel-backfill bij het activeren van een componenttype (`checklist_dragend`
False→True).

- **Offline** (geen nieuwe lifecycle-driver): de backfill zet enkel de geboortestatus `concept` en
  delegeert het afleiden aan de engine (`herbereken_type` → `herbereken_lifecycle`).
- **Live** (geseede lk_app-DB, skip indien offline): een bestaand component van een niet-beoordeeld
  type krijgt na de backfill een profiel + afgeleide status; idempotent; alléén het geactiveerde
  type wordt geraakt.
"""
import asyncio
import inspect
import uuid

import pytest

import app.core.database  # noqa: F401 — registreert de RLS/audit after_begin-hooks (app.tenant_id)
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline: geen eigen status-logica; de engine blijft de driver ────────────
def test_backfill_delegeert_afleiding_aan_de_engine():
    from services import checklistconfig_service as ccs

    src = inspect.getsource(ccs.backfill_profielen)
    assert "herbereken_type" in src            # afleiden loopt via de engine
    assert "bepaal_lifecycle" not in src        # geen eigen driver hier


# ── Live-integratie ──────────────────────────────────────────────────────────
def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                await c.execute(text("SELECT 1"))
            return True
        finally:
            await eng.dispose()

    try:
        return asyncio.run(_check())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar (offline)")


async def _sessie_run(fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tok = zet_tenant_context(_TID)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_tenant_context(tok)
        await eng.dispose()


@integratie
def test_backfill_geeft_bestaand_niet_beoordeeld_component_profiel_en_score():
    from schemas.component import ComponentCreate
    from services import checklistconfig_service as ccs
    from services import component_service as cs

    naam = f"LI058-cs-{uuid.uuid4().hex[:8]}"

    async def _flow(s):
        # 'client_software' is niet-beoordeeld én heeft géén dev-seed-componenten → de tenant-brede
        # backfill raakt alléén het hier aangemaakte component (geen vervuiling van gedeelde infra
        # zoals de saas_dienst/fileshare-demo's, die wél in de dev-seed voorkomen). Create geeft
        # nog GÉÉN profiel.
        comp = await cs.maak_aan(s, _TID, ComponentCreate(naam=naam, componenttype="client_software"))
        cid = comp["id"]
        assert comp["lifecycle_status"] is None
        # Backfill (activatie): bestaande componenten van dit type krijgen een profiel + herberekening.
        n = await ccs.backfill_profielen(s, _TID, "client_software")
        await s.commit()
        assert n >= 1
        detail = await cs.lees_detail(s, _TID, cid)
        assert detail["lifecycle_status"] is not None  # profiel nu aanwezig, status afgeleid
        # Idempotent: opnieuw → 0 nieuwe profielen.
        assert await ccs.backfill_profielen(s, _TID, "client_software") == 0
        await s.commit()
        await cs.verwijder(s, _TID, cid)
        await s.commit()

    asyncio.run(_sessie_run(_flow))


@integratie
def test_backfill_raakt_alleen_het_geactiveerde_type():
    from schemas.component import ComponentCreate
    from services import checklistconfig_service as ccs
    from services import component_service as cs

    naam = f"LI058-cs2-{uuid.uuid4().hex[:8]}"

    async def _flow(s):
        fs = await cs.maak_aan(s, _TID, ComponentCreate(naam=naam, componenttype="client_software"))
        # Backfill van een ANDER type (server_compute — beoordeeld maar zonder dev-seed-componenten,
        # dus een schone no-op) mag dit component niet raken (geen ongewenste mutatie).
        await ccs.backfill_profielen(s, _TID, "server_compute")
        await s.commit()
        detail = await cs.lees_detail(s, _TID, fs["id"])
        assert detail["lifecycle_status"] is None
        await cs.verwijder(s, _TID, fs["id"])
        await s.commit()

    asyncio.run(_sessie_run(_flow))
