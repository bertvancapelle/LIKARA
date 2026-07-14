"""LI040 — "nog niet vastgelegd" is een uitkomst, en dus vindbaar.

Offline: `onbekend` bestaat niet meer in de bedoeling-enum; de kolom is nullable zonder
default (vormkeuze B — identiek aan levensfase); de route kent de `*_ontbreekt`-filters
(afwezigheid = NULL, geen sentinel); Create zonder bedoeling = None (geen verzonnen
waarde); de engine kent de velden niet (herbevestigd).

Live (skip-if-no-DB): de ontbreekt-filters leveren exact de componenten zonder waarde;
echte-waarde-sets + ontbreekt-set dekken samen het totaal (geen component valt buiten
beide); een gezette bedoeling verlaat het ontbreekt-filter.
"""
import asyncio
import inspect

import pytest

import app.core.database  # noqa: F401 — registreert de RLS after_begin-hook (app.tenant_id)
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline: vorm ────────────────────────────────────────────────────────────────

def test_bedoeling_enum_zonder_onbekend_en_alleen_bestemmingen():
    from models.models import Migratiepad

    waarden = [e.value for e in Migratiepad]
    assert waarden == ["lift_and_shift", "herbouw", "vervangen", "gedeeld"]
    # Geen fase- of leegte-taal meer tussen de bestemmingen.
    for verboden in ("onbekend", "uitfaseren"):
        assert verboden not in waarden


def test_bedoeling_kolom_nullable_zonder_default():
    from models.models import Component

    kolom = Component.__table__.columns["migratiepad"]
    assert kolom.nullable is True
    assert kolom.server_default is None and kolom.default is None


def test_create_zonder_bedoeling_verzint_geen_waarde():
    from schemas.component import ComponentCreate, ComponentUpdate

    c = ComponentCreate(naam="X", componenttype="database")
    assert c.migratiepad is None  # weggelaten = "nog niet vastgelegd" — geen default
    # Expliciet null wist (registratie is corrigeerbaar); weggelaten laat staan.
    dump = ComponentUpdate(migratiepad=None).model_dump(exclude_unset=True)
    assert "migratiepad" in dump and dump["migratiepad"] is None
    assert "migratiepad" not in ComponentUpdate(naam="Y").model_dump(exclude_unset=True)


def test_route_kent_de_ontbreekt_filters():
    from routes.component import lijst_componenten

    params = inspect.signature(lijst_componenten).parameters
    assert "levensfase_ontbreekt" in params and "migratiepad_ontbreekt" in params


def test_ontbreekt_filtert_op_afwezigheid_geen_sentinel():
    """De filterwaarheid filtert op NULL (`is_(None)`) — nooit op een sentinel-waarde."""
    from services import component_service as svc

    bron = inspect.getsource(svc._pas_filters_toe)
    assert "levensfase.is_(None)" in bron
    assert "migratiepad.is_(None)" in bron
    assert "'onbekend'" not in bron and '"onbekend"' not in bron


def test_engine_kent_bedoeling_noch_levensfase():
    """Herbevestiging engine-grens: de engine leest/schrijft geen van beide velden."""
    from services import blokkade_service, checklistscore_service, lifecycle_service

    for module in (lifecycle_service, checklistscore_service, blokkade_service):
        src = inspect.getsource(module)
        for verboden in ("levensfase", "Levensfase", "migratiepad", "Migratiepad"):
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
def test_ontbreekt_filters_exact_en_complementair_live():
    """"Nog niet vastgelegd" levert exact de componenten zonder waarde; samen met de
    echte waarden dekt het het totaal (geen component valt buiten beide). Een gezette
    bedoeling verlaat het ontbreekt-filter."""
    from sqlalchemy import text as _text

    from schemas.component import ComponentCreate, ComponentUpdate
    from services import component_service as svc

    async def _flow(s):
        ids = []
        try:
            plan = [
                ("WT-LV-a", "vervangen", "uitfaseren"),   # (naam, bedoeling, levensfase)
                ("WT-LV-b", None, "in_productie"),
                ("WT-LV-c", None, None),
            ]
            for naam, pad, fase in plan:
                c = await svc.maak_aan(s, _TID, ComponentCreate(
                    naam=naam, componenttype="database", migratiepad=pad, levensfase=fase))
                ids.append((naam, c["id"]))

            async def _namen(**kw):
                items, _ = await svc.lijst(s, _TID, zoek="WT-LV-", limit=50, **kw)
                return {i["naam"] for i in items}

            totaal = await _namen()
            pad_leeg = await _namen(migratiepad_ontbreekt=True)
            pad_echt = await _namen(migratiepad="vervangen")
            fase_leeg = await _namen(levensfase_ontbreekt=True)
            fase_uit = await _namen(levensfase="uitfaseren")
            fase_prod = await _namen(levensfase="in_productie")

            # Een gezette bedoeling verlaat het ontbreekt-filter (browsercheck stap 4).
            cid = dict(ids)["WT-LV-c"]
            await svc.werk_bij(s, _TID, cid, ComponentUpdate(migratiepad="gedeeld"))
            pad_leeg_na = await _namen(migratiepad_ontbreekt=True)
            pad_gedeeld = await _namen(migratiepad="gedeeld")
            return totaal, pad_leeg, pad_echt, fase_leeg, fase_uit, fase_prod, pad_leeg_na, pad_gedeeld
        finally:
            for _, eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    totaal, pad_leeg, pad_echt, fase_leeg, fase_uit, fase_prod, pad_leeg_na, pad_gedeeld = (
        asyncio.run(_sessie_run(_flow))
    )
    assert totaal == {"WT-LV-a", "WT-LV-b", "WT-LV-c"}
    # Exact: het gat = b + c; de echte waarde = a. Complementair: samen = het totaal.
    assert pad_leeg == {"WT-LV-b", "WT-LV-c"} and pad_echt == {"WT-LV-a"}
    assert pad_leeg | pad_echt == totaal
    assert fase_leeg == {"WT-LV-c"} and fase_uit == {"WT-LV-a"} and fase_prod == {"WT-LV-b"}
    assert fase_leeg | fase_uit | fase_prod == totaal
    # Ná het zetten van de bedoeling: c weg uit het gat, zichtbaar onder zijn waarde.
    assert pad_leeg_na == {"WT-LV-b"} and pad_gedeeld == {"WT-LV-c"}
