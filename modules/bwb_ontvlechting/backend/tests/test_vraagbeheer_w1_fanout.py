"""Tests — ADR-022 W1: tenant-vraag-CRUD + in-tenant fan-out (live lk_app-DB, skip
indien onbereikbaar).

Gedekt:
- een vraag toevoegen aan een type herberekent **in-tenant, atomair** de lifecycle
  van bestaande componenten van dat type (een volledig gescoorde applicatie verlaat
  `migratieklaar` → `in_inventarisatie` zodra er een extra actieve vraag bijkomt);
- `(de)activeren` herberekent eveneens (een inactieve vraag valt uit `aantal_vragen`
  → de applicatie keert terug naar `migratieklaar`);
- duplicaat `(componenttype, code)` ⇒ `CHECKLISTVRAAG_BESTAAT` (409);
- `impact_telling` geeft het aantal componenten van het type (in-tenant).

De test herstelt de seed-staat (deactiveren brengt de applicaties terug op
`migratieklaar`) en ruimt de wegwerp-vraag hard op als `lk_admin` (fixture-rol).
"""
import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_CD_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_CD_ADMIN_URL = "postgresql+asyncpg://lk_admin:changeme_dev@localhost:5432/likara"


def _db_bereikbaar() -> bool:
    async def _check():
        eng = create_async_engine(_CD_APP_URL)
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
    eng = create_async_engine(_CD_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tok = zet_tenant_context(_TID)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_tenant_context(tok)
        await eng.dispose()


async def _admin_exec(sql: str, params: dict | None = None):
    eng = create_async_engine(_CD_ADMIN_URL)
    try:
        async with eng.begin() as c:
            await c.execute(text(sql), params or {})
    finally:
        await eng.dispose()


@integratie
def test_vraag_toevoegen_en_deactiveren_fan_out():
    from models.models import LifecycleStatus
    from schemas.checklistconfig import VraagCreate
    from services import checklistconfig_service as svc
    from services import component_service as comp_svc
    from services.errors import RegistratieConflict

    code = f"W1{uuid.uuid4().hex[:6]}"  # <= varchar(10)

    async def _flow(s):
        # BRP is volledig gescoord (89/89, geen blokkade) → migratieklaar.
        brp = (await s.execute(text("select id from component where naam='BRP'"))).first()[0]
        assert (await comp_svc.lees_detail(s, _TID, brp))  # bestaat
        lc0 = (await s.execute(text("select lifecycle_status from component_profiel where id=:i"), {"i": brp})).scalar_one()
        assert lc0 == "migratieklaar"

        n = await svc.impact_telling(s, "applicatie")
        assert n >= 1  # raakt N applicaties

        # Vraag toevoegen → fan-out: BRP heeft nu 89/90 → in_inventarisatie.
        vraag = await svc.maak_vraag(
            s, _TID,
            VraagCreate(componenttype="applicatie", code=code, vraag="W1 fan-out test",
                        categorie_nr=99, categorie_naam="Test"),
        )
        lc1 = (await s.execute(text("select lifecycle_status from component_profiel where id=:i"), {"i": brp})).scalar_one()
        assert lc1 == "in_inventarisatie"

        # Duplicaat (zelfde componenttype+code) → CHECKLISTVRAAG_BESTAAT (409).
        with pytest.raises(RegistratieConflict) as ei:
            await svc.maak_vraag(
                s, _TID,
                VraagCreate(componenttype="applicatie", code=code, vraag="dup", categorie_nr=99, categorie_naam="Test"),
            )
        await s.rollback()
        assert ei.value.code == "CHECKLISTVRAAG_BESTAAT"

        # Deactiveren → fan-out terug: inactieve vraag valt uit aantal_vragen → migratieklaar.
        await svc.zet_actief(s, _TID, vraag["id"], False)
        lc2 = (await s.execute(text("select lifecycle_status from component_profiel where id=:i"), {"i": brp})).scalar_one()
        assert lc2 == "migratieklaar"
        return vraag["id"]

    vraag_id = asyncio.run(_sessie_run(_flow))
    # Opruimen: de wegwerp-vraag hard verwijderen (fixture-rol lk_admin).
    asyncio.run(_admin_exec("DELETE FROM checklistvraag WHERE id = :i", {"i": vraag_id}))
