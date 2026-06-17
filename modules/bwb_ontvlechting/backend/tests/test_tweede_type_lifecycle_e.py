"""Tests — ADR-022 Fase E: een tweede checklist-dragend componenttype end-to-end
(live cd_app-DB, skip indien onbereikbaar).

Gebruikt `saas_dienst` als wegwerp-type: de catalogus-vlag wordt als `cd_admin`
(fixture-rol) op true gezet en in `finally` weer op false; componenten/vragen worden
opgeruimd. (`applicatieserver` is het persistente dev-seed-demotype; hier bewust een
ánder ongebruikt type zodat de test onafhankelijk van de seed draait.)

Gedekt:
- checklist-dragend (niet-`applicatie`) component krijgt een profiel op `concept`;
- generieke "start beoordeling" → `in_inventarisatie`; lege vragenset blijft `in_inventarisatie`;
- volledig beantwoord zonder blokkade → `migratieklaar`; met `nee`-score → `geblokkeerd`;
- scoring-read type-scoping symmetrisch met de engine (saas ziet alleen eigen vragen; applicatie niet);
- `checklist_dragend=false`-type: geen profiel, geen lifecycle, start → 404.
"""
import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"
_CD_ADMIN_URL = "postgresql+asyncpg://cd_admin:changeme_dev@localhost:5432/complidata"
_TYPE = "saas_dienst"


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


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="cd_app-DB niet bereikbaar (offline)")


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


async def _lc(s, component_id):
    return (
        await s.execute(text("select lifecycle_status from component_profiel where id=:i"), {"i": component_id})
    ).scalar_one_or_none()


@integratie
def test_tweede_type_lifecycle_end_to_end():
    from models.models import LifecycleStatus
    from schemas.checklistconfig import VraagCreate
    from schemas.checklistscore import ChecklistscoreCreate
    from schemas.component import ComponentCreate
    from services import checklistconfig_service as cc
    from services import checklistscore_service as score
    from services import checklistvraag_service as cvs
    from services import component_service as comp
    from services.errors import NietGevonden

    sfx = uuid.uuid4().hex[:6]

    async def _flow(s):
        comp_ids = []
        try:
            # checklist-dragend component → profiel op concept.
            c = await comp.maak_aan(
                s, _TID, ComponentCreate(naam=f"E-saas-{sfx}", componenttype=_TYPE, eigenaar_organisatie="ICT")
            )
            comp_ids.append(c["id"])
            assert c["checklist_dragend"] is True
            assert c["lifecycle_status"] == LifecycleStatus.concept

            # Generieke start → lege vragenset (0 vragen van dit type) → in_inventarisatie.
            d = await comp.start_beoordeling(s, _TID, c["id"])
            assert d["lifecycle_status"] == LifecycleStatus.in_inventarisatie

            # Vraag toevoegen (fan-out) → 0/1 gescoord → in_inventarisatie.
            v1 = await cc.maak_vraag(
                s, _TID, VraagCreate(componenttype=_TYPE, code="SD.1", vraag="vraag 1", categorie_nr=1, categorie_naam="SaaS")
            )
            assert await _lc(s, c["id"]) == "in_inventarisatie"

            # Score ja → 1/1, geen blokkade → migratieklaar.
            await score.maak_aan(
                s, _TID, ChecklistscoreCreate(component_id=c["id"], checklistvraag_id=v1["id"], score="ja")
            )
            assert await _lc(s, c["id"]) == "migratieklaar"

            # Tweede vraag + score nee → blokkade → geblokkeerd.
            v2 = await cc.maak_vraag(
                s, _TID, VraagCreate(componenttype=_TYPE, code="SD.2", vraag="vraag 2", categorie_nr=1, categorie_naam="SaaS")
            )
            await score.maak_aan(
                s, _TID, ChecklistscoreCreate(component_id=c["id"], checklistvraag_id=v2["id"], score="nee")
            )
            assert await _lc(s, c["id"]) == "geblokkeerd"

            # Scoring-read type-scoping (symmetrisch met de engine).
            saas = await cvs.lijst_alle(s, _TYPE)
            assert {v["code"] for v in saas} == {"SD.1", "SD.2"}
            assert all(v["componenttype"] == _TYPE for v in saas)
            app = await cvs.lijst_alle(s, "applicatie")
            assert not any(v["componenttype"] == _TYPE for v in app)

            # checklist_dragend=false type: geen profiel, geen lifecycle, start → 404.
            m = await comp.maak_aan(
                s, _TID, ComponentCreate(naam=f"E-mw-{sfx}", componenttype="middleware", eigenaar_organisatie="ICT")
            )
            comp_ids.append(m["id"])
            assert m["checklist_dragend"] is False
            assert m["lifecycle_status"] is None
            with pytest.raises(NietGevonden):
                await comp.start_beoordeling(s, _TID, m["id"])
            await s.rollback()
        finally:
            for cid in comp_ids:
                # Via het element-supertype (cascade omlaag); component-delete zou het
                # element als wees achterlaten.
                await s.execute(text("delete from element where id = :i"), {"i": cid})
            await s.commit()

    async def _run():
        # Setup: markeer het wegwerp-type checklist-dragend (cd_admin-fixture).
        await _admin_exec(
            "UPDATE componentconfig_optie SET checklist_dragend = true "
            "WHERE dimensie = 'componenttype' AND optie_sleutel = :t",
            {"t": _TYPE},
        )
        try:
            await _sessie_run(_flow)
        finally:
            # Teardown: wegwerp-vragen weg + de vlag terug op false.
            await _admin_exec("DELETE FROM checklistvraag WHERE componenttype = :t", {"t": _TYPE})
            await _admin_exec(
                "UPDATE componentconfig_optie SET checklist_dragend = false "
                "WHERE dimensie = 'componenttype' AND optie_sleutel = :t",
                {"t": _TYPE},
            )

    asyncio.run(_run())
