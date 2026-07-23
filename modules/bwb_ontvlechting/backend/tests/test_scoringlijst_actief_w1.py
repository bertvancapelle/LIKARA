"""Tests — ADR-022 W1: de scoringslijst-read toont alleen ACTIEVE vragen, byte-
identiek aan de set die de engine voor `aantal_vragen` telt (live lk_app-DB, skip
indien onbereikbaar).

Gedekt:
- een actieve vraag staat in `checklistvraag_service.lijst_alle` (scoring-read);
- na soft-deactivatie valt de vraag uit de scoring-read;
- de scoring-read-set == de engine-set (`componenttype + actief`, RLS) — geen divergentie;
- een bestaande score op een gedeactiveerde vraag blijft als historie in de DB bestaan.
"""
import asyncio
import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_LK_ADMIN_URL = "postgresql+asyncpg://lk_admin:changeme_dev@localhost:5432/likara"


def _db_bereikbaar() -> bool:
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


async def _admin_exec(sql: str, params: dict | None = None):
    eng = create_async_engine(_LK_ADMIN_URL)
    try:
        async with eng.begin() as c:
            await c.execute(text(sql), params or {})
    finally:
        await eng.dispose()


async def _actieve_applicatievragen(s):
    from services import checklistvraag_service as cvs

    return [v for v in await cvs.lijst_alle(s) if v["componenttype"] == "applicatie"]


async def _engine_aantal_applicatievragen(s):
    from models.models import ChecklistVraag

    return (
        await s.execute(
            select(func.count()).select_from(ChecklistVraag).where(
                ChecklistVraag.componenttype == "applicatie",
                ChecklistVraag.actief.is_(True),
            )
        )
    ).scalar_one()


@integratie
def test_scoringlijst_volgt_actieve_set():
    from models.models import ChecklistScore
    from schemas.checklistconfig import CategorieCreate, VraagCreate
    from schemas.checklistscore import ChecklistscoreCreate
    from schemas.component import ComponentCreate
    from services import checklistconfig_service as cc
    from services import checklistscore_service as score_svc
    from services import component_service as comp

    sfx = uuid.uuid4().hex[:6]
    code = f"SL{sfx}"  # <= varchar(10)

    async def _flow(s):
        app_id = None
        vraag_id = None
        cat_id = None
        try:
            n0 = len(await _actieve_applicatievragen(s))
            assert n0 == await _engine_aantal_applicatievragen(s)  # lijst == engine-set

            # LI050: de vraag KIEST een bestaande categorie — wegwerp-categorie eerst.
            cat = await cc.maak_categorie(
                s, _TID, CategorieCreate(componenttype="applicatie", naam=f"SL-cat-{sfx}", volgorde=99)
            )
            cat_id = cat["id"]
            # Actieve vraag → staat in de scoring-read.
            # LI050 (W4): de code wordt door het systeem toegekend — geen invoer.
            vraag = await cc.maak_vraag(
                s, _TID,
                VraagCreate(componenttype="applicatie", vraag="scoring-actief test",
                            categorie_id=cat_id),
            )
            vraag_id = vraag["id"]
            actief1 = await _actieve_applicatievragen(s)
            assert len(actief1) == n0 + 1
            assert any(v["id"] == vraag_id for v in actief1)
            assert len(actief1) == await _engine_aantal_applicatievragen(s)

            # Score op de vraag (historie): verse applicatie scoren op de nieuwe vraag.
            app = await comp.maak_aan(s, _TID, ComponentCreate(naam=f"SL-app-{sfx}", componenttype="applicatie"))
            app_id = app["id"]
            await score_svc.maak_aan(
                s, _TID, ChecklistscoreCreate(component_id=app_id, checklistvraag_id=vraag_id, score=ChecklistScore.ja),
            )

            # Soft-deactiveren → vraag valt uit de scoring-read én de engine-set.
            await cc.zet_actief(s, _TID, vraag_id, False)
            actief2 = await _actieve_applicatievragen(s)
            assert not any(v["id"] == vraag_id for v in actief2)
            assert len(actief2) == n0
            assert len(actief2) == await _engine_aantal_applicatievragen(s)  # geen divergentie

            # Historie: de score op de gedeactiveerde vraag bestaat nog in de DB.
            cnt = (
                await s.execute(text("select count(*) from checklistscore where checklistvraag_id=:v"), {"v": vraag_id})
            ).scalar_one()
            assert cnt == 1
        finally:
            # Opruimen: verse applicatie via het element-supertype (cascade wist subtype +
            # score; component-delete zou het element als wees achterlaten), dan de vraag.
            if app_id is not None:
                await s.execute(text("delete from element where id = :i"), {"i": app_id})
                await s.commit()
            if vraag_id is not None:
                await _admin_exec("DELETE FROM checklistvraag WHERE id = :i", {"i": vraag_id})
            # LI050: de wegwerp-categorie ná de vraag (RESTRICT-FK).
            if cat_id is not None:
                await _admin_exec("DELETE FROM checklist_categorie WHERE id = :i", {"i": cat_id})

    asyncio.run(_sessie_run(_flow))
