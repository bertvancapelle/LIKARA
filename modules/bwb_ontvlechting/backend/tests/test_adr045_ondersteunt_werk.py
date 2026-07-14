"""ADR-045 — "ondersteunt werk" als eigenschap van het componenttype.

Dekt: het model (kolom), de Create-/Update-schema's (vlaggen verplicht bij
componenttype, geweerd elders — incl. de 422-regressie: aanmaken mét beide vlaggen
slaagt, exact de payload die het beheerscherm bouwt), de service (voeg_toe zet de
vlaggen; wijzig weigert ze op een andere dimensie), de seed (5 typen true / 3 false,
uniforme sleutelset, idempotent), het tenant-read-pad (ComponentKeuze + catalog) en
het lijstfilter (guard: default-pad byte-identiek; clause alleen bij een waarde).

Live (skipif): de DB-CHECK-backstop van migratie 0065 + de catalogusstand.

GEEN engine-borging: de componentcatalogus is platform-referentiedata en raakt
lifecycle/score/blokkade niet — expliciet bevestigd doordat dit spoor uitsluitend
`componentconfig_optie` en een read-only IN-subquery op de componentlijst wijzigt.
"""
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

_TYP = {"archimate_element": "system_software", "archimate_laag": "technology", "archimate_aspect": "active"}
_VLAGGEN = {"checklist_dragend": True, "ondersteunt_werk": True}

_WERK_TRUE = {"applicatie", "saas_dienst", "landelijke_voorziening", "fileshare", "client_software"}
_WERK_FALSE = {"database", "server_compute", "integratievoorziening"}


def _result(scalar):
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar
    return r


def _scalar_one(waarde):
    r = MagicMock()
    r.scalar_one.return_value = waarde
    return r


# ── Model ─────────────────────────────────────────────────────────────────────────

def test_model_draagt_ondersteunt_werk_not_null_default_false():
    from models.models import ComponentConfigOptie

    kol = ComponentConfigOptie.__table__.c.ondersteunt_werk
    assert kol.nullable is False
    assert kol.server_default is not None and "false" in str(kol.server_default.arg)


# ── Schema: Create (incl. de 422-regressie die deze slice repareert) ──────────────

def test_create_componenttype_met_beide_vlaggen_slaagt():
    """DE 422-REGRESSIE: exact de payload die het beheerscherm bouwt (typering + beide
    vlaggen) wordt door het Create-schema geaccepteerd — vóór deze slice gaf
    `checklist_dragend` hier `extra_forbidden` en was 'componenttype toevoegen' kapot."""
    from schemas.componentconfig import ComponentConfigOptieCreate

    ok = ComponentConfigOptieCreate(
        dimensie="componenttype", optie_sleutel="proef_type", label="Proef",
        **_TYP, **_VLAGGEN,
    )
    assert ok.checklist_dragend is True and ok.ondersteunt_werk is True


def test_create_componenttype_zonder_vlaggen_geweigerd():
    from schemas.componentconfig import ComponentConfigOptieCreate

    # beide afwezig
    with pytest.raises(ValidationError):
        ComponentConfigOptieCreate(dimensie="componenttype", optie_sleutel="x", label="X", **_TYP)
    # één afwezig
    with pytest.raises(ValidationError):
        ComponentConfigOptieCreate(
            dimensie="componenttype", optie_sleutel="x", label="X", **_TYP, checklist_dragend=False,
        )


def test_create_vlaggen_geweerd_op_andere_dimensies():
    from schemas.componentconfig import ComponentConfigOptieCreate

    for dim in ("structuurrelatie_type", "archimate_relatie"):
        # zonder vlaggen blijft toegestaan
        ok = ComponentConfigOptieCreate(dimensie=dim, optie_sleutel="iets", label="Iets")
        assert ok.checklist_dragend is None and ok.ondersteunt_werk is None
        # mét een vlag geweigerd
        with pytest.raises(ValidationError):
            ComponentConfigOptieCreate(dimensie=dim, optie_sleutel="iets", label="Iets", ondersteunt_werk=True)
        with pytest.raises(ValidationError):
            ComponentConfigOptieCreate(dimensie=dim, optie_sleutel="iets", label="Iets", checklist_dragend=True)


def test_create_extra_forbid_intact():
    from schemas.componentconfig import ComponentConfigOptieCreate

    with pytest.raises(ValidationError):
        ComponentConfigOptieCreate(
            dimensie="componenttype", optie_sleutel="x", label="X", onbekend="z", **_TYP, **_VLAGGEN,
        )


def test_update_en_read_dragen_ondersteunt_werk():
    from schemas.componentconfig import ComponentConfigOptieRead, ComponentConfigOptieUpdate

    upd = ComponentConfigOptieUpdate(ondersteunt_werk=True)
    assert upd.model_dump(exclude_unset=True) == {"ondersteunt_werk": True}
    assert ComponentConfigOptieRead.model_fields["ondersteunt_werk"].default is False


# ── Service ───────────────────────────────────────────────────────────────────────

def test_voeg_toe_zet_beide_vlaggen():
    from schemas.componentconfig import ComponentConfigOptieCreate
    from services import componentconfig_service as svc

    session = AsyncMock()
    session.execute.side_effect = [_result(None), _scalar_one(7)]
    toegevoegd = []
    session.add = lambda o: toegevoegd.append(o)
    asyncio.run(svc.voeg_toe(session, ComponentConfigOptieCreate(
        dimensie="componenttype", optie_sleutel="proef_type", label="Proef", **_TYP, **_VLAGGEN,
    )))
    assert toegevoegd[0].checklist_dragend is True
    assert toegevoegd[0].ondersteunt_werk is True


def test_voeg_toe_andere_dimensie_vlaggen_false():
    """Niet-componenttype: schema levert None → de service schrijft False (CHECK-veilig)."""
    from schemas.componentconfig import ComponentConfigOptieCreate
    from services import componentconfig_service as svc

    session = AsyncMock()
    session.execute.side_effect = [_result(None), _scalar_one(1)]
    toegevoegd = []
    session.add = lambda o: toegevoegd.append(o)
    asyncio.run(svc.voeg_toe(session, ComponentConfigOptieCreate(
        dimensie="structuurrelatie_type", optie_sleutel="iets", label="Iets",
    )))
    assert toegevoegd[0].checklist_dragend is False
    assert toegevoegd[0].ondersteunt_werk is False


def test_wijzig_vlag_op_andere_dimensie_geweigerd():
    from models.models import ComponentConfigDimensie
    from schemas.componentconfig import ComponentConfigOptieUpdate
    from services import componentconfig_service as svc
    from services.errors import OngeldigeRegistratie

    optie = SimpleNamespace(
        id=9, dimensie=ComponentConfigDimensie.archimate_relatie, optie_sleutel="flow",
        label="Flow", volgorde=4, actief=True,
    )
    session = AsyncMock()
    session.execute.return_value = _result(optie)
    for payload in (
        ComponentConfigOptieUpdate(ondersteunt_werk=True),
        ComponentConfigOptieUpdate(checklist_dragend=True),
    ):
        with pytest.raises(OngeldigeRegistratie) as e:
            asyncio.run(svc.wijzig(session, optie.id, payload))
        assert e.value.code == "VLAG_ALLEEN_COMPONENTTYPE"


def test_wijzig_zet_ondersteunt_werk_op_componenttype():
    from models.models import ComponentConfigDimensie
    from schemas.componentconfig import ComponentConfigOptieUpdate
    from services import componentconfig_service as svc

    optie = SimpleNamespace(
        id=3, dimensie=ComponentConfigDimensie.componenttype, optie_sleutel="fileshare",
        label="Fileshare", volgorde=6, actief=True, checklist_dragend=False, ondersteunt_werk=True,
    )
    session = AsyncMock()
    session.execute.return_value = _result(optie)
    asyncio.run(svc.wijzig(session, optie.id, ComponentConfigOptieUpdate(ondersteunt_werk=False)))
    assert optie.ondersteunt_werk is False  # flip; geen backfill-machinerie (ADR-045 besluit 6)


# ── Seed ──────────────────────────────────────────────────────────────────────────

def test_seed_stand_vijf_true_drie_false():
    from services.seed_componentconfig import bouw_componentconfig

    rijen = bouw_componentconfig()
    typen = {r["optie_sleutel"]: r["ondersteunt_werk"] for r in rijen if r["dimensie"].value == "componenttype"}
    assert {t for t, w in typen.items() if w} == _WERK_TRUE
    assert {t for t, w in typen.items() if not w} == _WERK_FALSE
    # Uniforme sleutelset (multi-row pg_insert-eis): élke rij draagt de sleutel; buiten
    # de dimensie componenttype altijd False (CHECK 0065).
    assert all("ondersteunt_werk" in r for r in rijen)
    assert all(r["ondersteunt_werk"] is False for r in rijen if r["dimensie"].value != "componenttype")


def test_seed_migratie_byte_gelijk():
    """De reconcile-migratie (0065) en de seed zetten dezelfde vijf typen op true."""
    import importlib.util
    import pathlib

    pad = pathlib.Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0065_adr045_ondersteunt_werk.py"
    spec = importlib.util.spec_from_file_location("m0065", pad)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert set(m._WERK_TRUE) == _WERK_TRUE


def test_seed_idempotent():
    from services.seed_componentconfig import seed_componentconfig

    session = AsyncMock()
    assert asyncio.run(seed_componentconfig(session)) == 18
    assert asyncio.run(seed_componentconfig(session)) == 18


def test_dode_seed_functie_opgeruimd():
    """LI040 — `_seed_tweede_type` (dood, stale docstring) is verwijderd uit de dev-seed."""
    import pathlib

    bron = (pathlib.Path(__file__).resolve().parents[4] / "backend" / "dev_seed_testdata.py").read_text()
    assert "_seed_tweede_type" not in bron


# ── Tenant-read-pad (feitenrapport B2 — de drie plekken) ──────────────────────────

def test_componentkeuze_draagt_ondersteunt_werk():
    from schemas.component import ComponentKeuze

    keuze = ComponentKeuze(optie_sleutel="applicatie", label="Applicatie", ondersteunt_werk=True)
    assert keuze.ondersteunt_werk is True
    assert ComponentKeuze.model_fields["ondersteunt_werk"].default is False


def test_catalog_levert_ondersteunt_werk_mee():
    """`actieve_opties_per_dimensie` selecteert én projecteert de vlag (bronscan — de
    twee catalog-plekken van het read-pad)."""
    import inspect

    from services import componentconfig_catalog as catalog

    bron = inspect.getsource(catalog.actieve_opties_per_dimensie)
    assert bron.count("ondersteunt_werk") >= 2  # select-kolom + dict-projectie


# ── Lijstfilter (besluit 5) ───────────────────────────────────────────────────────

def test_lijst_filter_alleen_achter_guard():
    """Default-pad byte-identiek (ADR-028-guard-les): de clause bestaat uitsluitend
    achter `if ondersteunt_werk is not None` en filtert via een IN-subquery op de
    CATALOGUS (nooit een typen-lijst in code)."""
    import inspect
    import re

    from services import component_service as svc

    bron = inspect.getsource(svc.lijst)
    m = re.search(r"if ondersteunt_werk is not None:\n(.+?)\n    (?:if|#|[a-z])", bron, re.S)
    assert m, "guard ontbreekt"
    blok = m.group(1)
    assert "ComponentConfigOptie.ondersteunt_werk" in blok
    assert "componenttype.in_" in blok.replace(" ", "").replace("Component.", "componenttype_") or "in_(" in blok


def test_route_kent_ondersteunt_werk_param():
    import inspect

    from routes import component as route

    sig = inspect.signature(route.lijst_componenten)
    assert "ondersteunt_werk" in sig.parameters
    bron = inspect.getsource(route.lijst_componenten)
    assert "ondersteunt_werk=ondersteunt_werk" in bron  # doorgegeven aan de service


# ── Live (skipif — DB-CHECK-backstop + catalogusstand) ────────────────────────────

_LK_PLATFORM_URL = os.environ.get(
    "LK_PLATFORM_TEST_URL",
    "postgresql+asyncpg://lk_platform:changeme_dev@localhost:5432/likara",
)
_LK_APP_URL = os.environ.get(
    "LK_APP_TEST_URL",
    "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara",
)


def _db_bereikbaar(url: str, probe: str) -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(url)
        try:
            async with eng.connect() as c:
                return (await c.execute(text(probe))).scalar() is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


_PROBE = "SELECT to_regclass('componentconfig_optie')"
live_platform = pytest.mark.skipif(
    not _db_bereikbaar(_LK_PLATFORM_URL, _PROBE),
    reason="componentconfig_optie niet bereikbaar als lk_platform (stack/migratie 0065 niet toegepast)",
)
live_app = pytest.mark.skipif(
    not _db_bereikbaar(_LK_APP_URL, _PROBE),
    reason="componentconfig_optie niet bereikbaar als lk_app",
)


@live_platform
def test_live_check_weigert_vlag_buiten_componenttype():
    """DB-CHECK-backstop (0065): `ondersteunt_werk = true` op een andere dimensie wordt
    door de database geweigerd — óók buiten de app-laag om."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _run():
        eng = create_async_engine(_LK_PLATFORM_URL)
        try:
            async with eng.begin() as c:
                await c.execute(text(
                    "UPDATE componentconfig_optie SET ondersteunt_werk = true "
                    "WHERE dimensie = 'archimate_relatie' AND optie_sleutel = 'flow'"
                ))
        finally:
            await eng.dispose()

    with pytest.raises(IntegrityError):
        asyncio.run(_run())


@live_app
def test_live_catalogusstand_vijf_true_drie_false():
    """Toetst de reconcile-stand van de ACHT seed-typen — bewust als subset, niet als
    set-gelijkheid over alle rijen: de catalogus is beheerbaar (ADR-045), dus een door
    de platformbeheerder toegevoegd type mag deze test nooit laten falen (LI021-les:
    asserteer alléén op je eigen data; de browsercheck-proefrij bewees het punt)."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _run():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                rijen = (await c.execute(text(
                    "SELECT optie_sleutel, ondersteunt_werk FROM componentconfig_optie "
                    "WHERE dimensie = 'componenttype'"
                ))).all()
            return {s: w for s, w in rijen}
        finally:
            await eng.dispose()

    stand = asyncio.run(_run())
    for sleutel in _WERK_TRUE:
        assert stand.get(sleutel) is True, f"{sleutel} hoort ondersteunt_werk=true te dragen"
    for sleutel in _WERK_FALSE:
        assert stand.get(sleutel) is False, f"{sleutel} hoort ondersteunt_werk=false te dragen"
