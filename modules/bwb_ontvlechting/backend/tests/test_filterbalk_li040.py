"""LI040 — de filterbalk vertelt wat hij doet (bedoeling-filter, resultaatregel-tellingen,
BIV op de hoogste as).

Offline: de route kent `migratiepad`/`biv_min`/`biv_ontbreekt` en de per-as-BIV-params
zijn ECHT weg; het sorteerveld beweegt mee; `ComponentPagina` draagt de tellingen; de
telling en de lijst delen aantoonbaar dezelfde filterfunctie (één filterwaarheid).

Live (skip-if-no-DB): `tel` levert gefilterd + ongefilterd totaal over de hele dataset
(cursor/limit raken de telling niet); het bedoeling-filter; hoogste-as-semantiek met een
DEELS ingevulde BIV (deels = vastgelegd; de hoogste ingevulde as bepaalt).
"""
import asyncio
import inspect
import uuid

import pytest

import app.core.database  # noqa: F401 — registreert de RLS after_begin-hook (app.tenant_id)
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline ──────────────────────────────────────────────────────────────────────

def test_route_kent_bedoeling_en_biv_min_en_per_as_is_weg():
    from models.models import Migratiepad
    from routes.component import lijst_componenten

    params = inspect.signature(lijst_componenten).parameters
    assert params["migratiepad"].annotation == (Migratiepad | None)
    assert "biv_min" in params and "biv_ontbreekt" in params
    # LI040 — het per-as-filteren is vervallen (drie dropdowns → één BIV-filter).
    for weg in ("biv_beschikbaarheid_min", "biv_integriteit_min", "biv_vertrouwelijkheid_min"):
        assert weg not in params


def test_sorteerveld_allowlist_bevat_migratiepad():
    from schemas.component import ComponentSorteerveld
    from services import component_service as svc

    assert "migratiepad" in {e.value for e in ComponentSorteerveld}
    assert "migratiepad" in svc._SORTEERBARE_KOLOMMEN and "migratiepad" in svc._WAARDE_PARSERS


def test_pagina_schema_draagt_de_tellingen():
    from schemas.component import ComponentPagina

    velden = ComponentPagina.model_fields
    assert "totaal" in velden and "totaal_ongefilterd" in velden


def test_tel_en_lijst_delen_een_filterwaarheid():
    """De telling mag nooit stil van de lijst afwijken: beide roepen dezelfde
    `_pas_filters_toe` aan (bronscan), en er staat geen tweede filter-opbouw in `tel`."""
    from services import component_service as svc

    for fn in (svc.lijst, svc.tel):
        assert "_pas_filters_toe(" in inspect.getsource(fn), (
            f"{fn.__name__} bouwt zijn filters niet via de gedeelde _pas_filters_toe"
        )
    # `tel` bevat zelf geen filter-clauses (alleen de count-basis + de helper-aanroep).
    tel_src = inspect.getsource(svc.tel)
    for clause in ("ilike", "biv_", "levensfase ==", "migratiepad =="):
        assert clause not in tel_src


# ── Live-integratie ──────────────────────────────────────────────────────────────

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
def test_tel_gefilterd_en_ongefilterd_live():
    """De resultaatregel-aantallen: `totaal` volgt de filters over de HELE dataset
    (limit/cursor doen niet mee); `totaal_ongefilterd` is de tenant-brede teller."""
    from sqlalchemy import text as _text

    from schemas.component import ComponentCreate
    from services import component_service as svc

    async def _flow(s):
        ids = []
        try:
            plan = [("WT-TEL-a", "vervangen"), ("WT-TEL-b", "vervangen"), ("WT-TEL-c", None)]
            for naam, pad in plan:
                c = await svc.maak_aan(s, _TID, ComponentCreate(
                    naam=naam, componenttype="database", migratiepad=pad))
                ids.append(c["id"])

            alles = await svc.tel(s, _TID, zoek="WT-TEL-")
            gefilterd = await svc.tel(s, _TID, zoek="WT-TEL-", migratiepad="vervangen")
            # Kleine limit bewijst: de telling gaat over de dataset, niet de pagina.
            items, _ = await svc.lijst(s, _TID, zoek="WT-TEL-", migratiepad="vervangen", limit=1)
            return alles, gefilterd, len(items)
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    alles, gefilterd, pagina_len = asyncio.run(_sessie_run(_flow))
    assert alles["totaal"] == 3
    assert gefilterd["totaal"] == 2          # het bedoeling-filter werkt in de telling…
    assert pagina_len == 1                    # …terwijl de pagina door limit kleiner is
    assert alles["totaal_ongefilterd"] == gefilterd["totaal_ongefilterd"] >= 3


@integratie
def test_biv_hoogste_as_en_deels_ingevuld_live():
    """LI040 — de zwaarste as bepaalt: een component met ALLEEN beschikbaarheid=hoog
    matcht op `biv_min=hoog`; deels ingevuld telt als vastgelegd (valt dus buiten
    `biv_ontbreekt`), en de hoogste ingevulde as bepaalt de drempelmatch."""
    from sqlalchemy import text as _text

    from schemas.component import ComponentCreate
    from services import component_service as svc

    async def _flow(s):
        ids = []
        try:
            # (a) deels ingevuld: alleen B=hoog → hoogste as = hoog.
            a = await svc.maak_aan(s, _TID, ComponentCreate(
                naam="WT-BIV-a", componenttype="database", biv_beschikbaarheid="hoog"))
            # (b) volledig laag → hoogste as = laag.
            b = await svc.maak_aan(s, _TID, ComponentCreate(
                naam="WT-BIV-b", componenttype="database",
                biv_beschikbaarheid="laag", biv_integriteit="laag", biv_vertrouwelijkheid="laag"))
            # (c) niets ingevuld → het registratiegat.
            c = await svc.maak_aan(s, _TID, ComponentCreate(naam="WT-BIV-c", componenttype="database"))
            ids += [a["id"], b["id"], c["id"]]

            async def _namen(**kw):
                items, _ = await svc.lijst(s, _TID, zoek="WT-BIV-", limit=50, **kw)
                return {i["naam"] for i in items}

            hoog = await _namen(biv_min="hoog")
            laag = await _namen(biv_min="laag")
            gat = await _namen(biv_ontbreekt=True)
            return hoog, laag, gat
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    hoog, laag, gat = asyncio.run(_sessie_run(_flow))
    assert hoog == {"WT-BIV-a"}                       # minstens één as ≥ hoog
    assert laag == {"WT-BIV-a", "WT-BIV-b"}           # ≥ laag: beide vastgelegde
    assert gat == {"WT-BIV-c"}                        # exact de BIV-loze (deels ≠ gat)
