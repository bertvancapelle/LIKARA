"""LI040 — "Midden" is geen oordeel als niemand het heeft gegeven.

Offline: `complexiteit`/`prioriteit` zijn nullable ZONDER default (0067-patroon); de
enum-waarden zelf blijven (midden is een geldig oordeel — het wordt alleen niet meer
gratis uitgedeeld); Create zonder oordeel = None; de route kent de oordeel- én
ontbreekt-filters; de filterwaarheid filtert op afwezigheid; de engine kent de velden
niet.

Live (skip-if-no-DB): de ontbreekt-filters exact + complementair (gat-set ∪
waarde-sets = totaal); een gezette waarde verlaat het gat-filter.
"""
import asyncio
import inspect

import pytest

import app.core.database  # noqa: F401 — registreert de RLS after_begin-hook (app.tenant_id)
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline ──────────────────────────────────────────────────────────────────────

def test_oordeel_kolommen_nullable_zonder_default_enum_intact():
    from models.models import Component, NiveauEnum

    for naam in ("complexiteit", "prioriteit"):
        kolom = Component.__table__.columns[naam]
        assert kolom.nullable is True
        assert kolom.server_default is None and kolom.default is None
    # De enum blijft ongewijzigd — midden is een geldig oordeel (§1.2).
    assert [e.value for e in NiveauEnum] == ["laag", "midden", "hoog"]


def test_create_zonder_oordeel_verzint_niets():
    from schemas.component import ComponentCreate, ComponentUpdate

    c = ComponentCreate(naam="X", componenttype="database")
    assert c.complexiteit is None and c.prioriteit is None
    # Expliciet null wist (corrigeerbaar); weggelaten laat staan.
    dump = ComponentUpdate(prioriteit=None).model_dump(exclude_unset=True)
    assert "prioriteit" in dump and dump["prioriteit"] is None
    assert "prioriteit" not in ComponentUpdate(naam="Y").model_dump(exclude_unset=True)


def test_route_kent_oordeel_en_ontbreekt_filters():
    from models.models import NiveauEnum
    from routes.component import lijst_componenten

    params = inspect.signature(lijst_componenten).parameters
    for naam in ("complexiteit", "prioriteit"):
        assert params[naam].annotation == (NiveauEnum | None)
        assert f"{naam}_ontbreekt" in params


def test_ontbreekt_filtert_op_afwezigheid():
    from services import component_service as svc

    bron = inspect.getsource(svc._pas_filters_toe)
    assert "complexiteit.is_(None)" in bron and "prioriteit.is_(None)" in bron


def test_engine_kent_de_oordeel_velden_niet():
    """De engine-invariant: de component-oordelen `complexiteit`/`prioriteit` komen in
    geen enkel engine-pad voor (de checklistvraag-prioriteit is een ánder veld en leeft
    óók niet in deze modules — bronnen zijn gemeten schoon)."""
    from services import blokkade_service, checklistscore_service, lifecycle_service

    for module in (lifecycle_service, checklistscore_service, blokkade_service):
        src = inspect.getsource(module)
        for verboden in ("complexiteit", "prioriteit"):
            assert verboden not in src, f"{module.__name__} refereert aan {verboden!r}"


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
def test_oordeel_filters_exact_complementair_en_gat_verlaten_live():
    """"Nog niet vastgelegd" levert exact de oordeel-loze componenten; gat ∪ waarden =
    totaal; Prioriteit=hoog zetten verlaat het gat en verschijnt onder 'hoog'
    (browsercheck stap 3)."""
    from sqlalchemy import text as _text

    from schemas.component import ComponentCreate, ComponentUpdate
    from services import component_service as svc

    async def _flow(s):
        ids = []
        try:
            plan = [
                ("WT-GO-a", "hoog", "laag"),   # (naam, complexiteit, prioriteit)
                ("WT-GO-b", "midden", None),   # midden is een GELDIG (bewust gezet) oordeel
                ("WT-GO-c", None, None),
            ]
            for naam, comp, prio in plan:
                c = await svc.maak_aan(s, _TID, ComponentCreate(
                    naam=naam, componenttype="database", complexiteit=comp, prioriteit=prio))
                ids.append((naam, c["id"]))

            async def _namen(**kw):
                items, _ = await svc.lijst(s, _TID, zoek="WT-GO-", limit=50, **kw)
                return {i["naam"] for i in items}

            totaal = await _namen()
            comp_gat = await _namen(complexiteit_ontbreekt=True)
            comp_hoog = await _namen(complexiteit="hoog")
            comp_midden = await _namen(complexiteit="midden")
            prio_gat = await _namen(prioriteit_ontbreekt=True)
            prio_laag = await _namen(prioriteit="laag")

            # Prioriteit=hoog zetten bij c → verlaat het gat, verschijnt onder hoog.
            cid = dict(ids)["WT-GO-c"]
            await svc.werk_bij(s, _TID, cid, ComponentUpdate(prioriteit="hoog"))
            prio_gat_na = await _namen(prioriteit_ontbreekt=True)
            prio_hoog_na = await _namen(prioriteit="hoog")
            return totaal, comp_gat, comp_hoog, comp_midden, prio_gat, prio_laag, prio_gat_na, prio_hoog_na
        finally:
            for _, eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    (totaal, comp_gat, comp_hoog, comp_midden, prio_gat, prio_laag,
     prio_gat_na, prio_hoog_na) = asyncio.run(_sessie_run(_flow))
    assert totaal == {"WT-GO-a", "WT-GO-b", "WT-GO-c"}
    # Exact + complementair: gat ∪ waarde-sets = totaal (geen component buiten beide).
    assert comp_gat == {"WT-GO-c"} and comp_hoog == {"WT-GO-a"} and comp_midden == {"WT-GO-b"}
    assert comp_gat | comp_hoog | comp_midden == totaal
    assert prio_gat == {"WT-GO-b", "WT-GO-c"} and prio_laag == {"WT-GO-a"}
    assert prio_gat | prio_laag == totaal
    # Een gezet oordeel verlaat het gat.
    assert prio_gat_na == {"WT-GO-b"} and prio_hoog_na == {"WT-GO-c"}
