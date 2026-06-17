"""Tests — ADR-022 Fase C: toestand-gebaseerde type-lock + capability + "wat verdwijnt".

Live-integratie tegen de cd_app-DB (skip indien onbereikbaar). Elke test maakt zijn
eigen wegwerp-componenten (uniek achtervoegsel) en ruimt ze in `finally` op.

Gedekt:
- drempel: kaal/lege applicatie → `type_wijzigbaar=true`; eerste beantwoorde score
  of lifecycle voorbij `concept` → `false`;
- vrije wissel op leeg: kaal↔kaal, kaal→applicatie (promotie: profiel ontstaat),
  applicatie→kaal (profiel + subtype weg), géén overdracht van oude scores;
- gevuld → geweigerd met `SUBTYPE_HEEFT_DATA` + tellingen in het bericht;
- "wat verdwijnt" geeft correcte tellingen en muteert niets.
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


async def _maak(s, naam, type_):
    from schemas.component import ComponentCreate
    from services import component_service as svc

    return await svc.maak_aan(s, _TID, ComponentCreate(naam=naam, componenttype=type_))


async def _opruimen(s, ids):
    # Verwijder via het ELEMENT-supertype: FK ON DELETE CASCADE wist het hele subtype-pad
    # (element → component → subtype/profiel/scores/blokkades). Component-delete zou het
    # element als wees achterlaten (zichtbaar als "component <id8>" in de architectuur-view).
    await s.execute(text("delete from element where id = any(:ids)"), {"ids": ids})
    await s.commit()


async def _eerste_applicatievraag(s):
    return (
        await s.execute(text("select id from checklistvraag where componenttype='applicatie' limit 1"))
    ).first()[0]


@integratie
def test_drempel_leeg_vs_gevuld():
    from services import applicatie_service, checklistscore_service, component_service as svc
    from schemas.checklistscore import ChecklistscoreCreate

    sfx = uuid.uuid4().hex[:8]

    async def _flow(s):
        ids = []
        try:
            kaal = await _maak(s, f"TL-kaal-{sfx}", "database")
            app = await _maak(s, f"TL-app-{sfx}", "applicatie")
            ids = [kaal["id"], app["id"]]

            # Kaal (geen profiel) en verse applicatie (concept, 0 scores) → vrij wijzigbaar.
            assert (await svc.lees_detail(s, _TID, kaal["id"]))["type_wijzigbaar"] is True
            assert (await svc.lees_detail(s, _TID, app["id"]))["type_wijzigbaar"] is True

            # Eén beantwoorde score → vergrendeld.
            vraag = await _eerste_applicatievraag(s)
            await checklistscore_service.maak_aan(
                s, _TID, ChecklistscoreCreate(component_id=app["id"], checklistvraag_id=vraag, score="ja")
            )
            assert (await svc.lees_detail(s, _TID, app["id"]))["type_wijzigbaar"] is False

            # Lifecycle voorbij concept vergrendelt óók zonder scores: aparte verse app.
            app2 = await _maak(s, f"TL-app2-{sfx}", "applicatie")
            ids.append(app2["id"])
            assert (await svc.lees_detail(s, _TID, app2["id"]))["type_wijzigbaar"] is True
            await applicatie_service.start_inventarisatie(s, _TID, app2["id"])  # → in_inventarisatie
            assert (await svc.lees_detail(s, _TID, app2["id"]))["type_wijzigbaar"] is False
        finally:
            await _opruimen(s, ids)

    asyncio.run(_sessie_run(_flow))


@integratie
def test_vrije_wissel_op_leeg():
    from schemas.component import ComponentUpdate
    from services import component_service as svc

    sfx = uuid.uuid4().hex[:8]

    async def _flow(s):
        ids = []
        try:
            # kaal → kaal (geen profiel betrokken).
            kaal = await _maak(s, f"TLW-kaal-{sfx}", "database")
            ids.append(kaal["id"])
            r1 = await svc.werk_bij(s, _TID, kaal["id"], ComponentUpdate(componenttype="fileshare"))
            assert r1["componenttype"] == "fileshare"
            assert r1["heeft_applicatie_subtype"] is False

            # kaal → applicatie (promotie: subtype + profiel ontstaan).
            r2 = await svc.werk_bij(s, _TID, kaal["id"], ComponentUpdate(componenttype="applicatie"))
            assert r2["componenttype"] == "applicatie"
            assert r2["heeft_applicatie_subtype"] is True
            # profiel bestaat nu (lifecycle concept → nog vrij wijzigbaar).
            assert r2["type_wijzigbaar"] is True

            # applicatie (leeg) → database (subtype + profiel weg; geen overdracht).
            r3 = await svc.werk_bij(s, _TID, kaal["id"], ComponentUpdate(componenttype="database"))
            assert r3["componenttype"] == "database"
            assert r3["heeft_applicatie_subtype"] is False
            geen_profiel = (
                await s.execute(text("select count(*) from component_profiel where id=:i"), {"i": kaal["id"]})
            ).scalar_one()
            assert geen_profiel == 0
        finally:
            await _opruimen(s, ids)

    asyncio.run(_sessie_run(_flow))


@integratie
def test_gevuld_weigert_met_subtype_heeft_data():
    from schemas.checklistscore import ChecklistscoreCreate
    from schemas.component import ComponentUpdate
    from services import checklistscore_service, component_service as svc
    from services.errors import OngeldigeRegistratie

    sfx = uuid.uuid4().hex[:8]

    async def _flow(s):
        ids = []
        try:
            app = await _maak(s, f"TLG-app-{sfx}", "applicatie")
            ids.append(app["id"])
            vraag = await _eerste_applicatievraag(s)
            await checklistscore_service.maak_aan(
                s, _TID, ChecklistscoreCreate(component_id=app["id"], checklistvraag_id=vraag, score="ja")
            )
            with pytest.raises(OngeldigeRegistratie) as ei:
                await svc.werk_bij(s, _TID, app["id"], ComponentUpdate(componenttype="database"))
            await s.rollback()
            assert ei.value.code == "SUBTYPE_HEEFT_DATA"
            assert "score" in ei.value.bericht.lower()  # tellingen benoemd
        finally:
            await _opruimen(s, ids)

    asyncio.run(_sessie_run(_flow))


@integratie
def test_wat_verdwijnt_telt_en_muteert_niet():
    from schemas.checklistscore import ChecklistscoreCreate
    from services import checklistscore_service, component_service as svc

    sfx = uuid.uuid4().hex[:8]

    async def _flow(s):
        ids = []
        try:
            app = await _maak(s, f"TLD-app-{sfx}", "applicatie")
            ids.append(app["id"])
            vraag = await _eerste_applicatievraag(s)
            await checklistscore_service.maak_aan(
                s, _TID, ChecklistscoreCreate(component_id=app["id"], checklistvraag_id=vraag, score="nee")
            )  # 'nee' → score beantwoord + auto-blokkade
            wd = await svc.wat_verdwijnt(s, _TID, app["id"])
            assert wd == {
                "beantwoorde_scores": 1,
                "blokkades": 1,
                "datatypes": 0,
                "gebruikersgroepen": 0,
            }
            # Geen mutatie: de score bestaat nog, type nog applicatie.
            n = (
                await s.execute(text("select count(*) from checklistscore where component_id=:i"), {"i": app["id"]})
            ).scalar_one()
            assert n == 1
            assert (await svc.lees_detail(s, _TID, app["id"]))["componenttype"] == "applicatie"
        finally:
            await _opruimen(s, ids)

    asyncio.run(_sessie_run(_flow))
