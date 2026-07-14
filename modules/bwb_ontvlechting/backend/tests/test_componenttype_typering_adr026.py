"""Tests — ADR-026: beheerbare componenttype-typering (element/laag/aspect).

Dekt: gesloten whitelist + validators (geldigheid), volledigheid bij aanmaken, service
(lek dicht / corrigeren / leegmaken geweigerd), DB-CHECK-backstop (live), live-DB-dekkingstest
(geen actief componenttype zonder typering), engine-onaangeroerd (offline import-afwezigheid +
live trigger-afwezigheid) en de F-2-laagprojectie voor een volledig getypeerd componenttype.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy import text

_TYP = {"archimate_element": "system_software", "archimate_laag": "technology", "archimate_aspect": "active",
        # ADR-045 besluit 4 — een componenttype wordt in één handeling volledig ingericht.
        "checklist_dragend": False, "ondersteunt_werk": False}


def _result(val):
    r = MagicMock()
    r.scalar_one_or_none.return_value = val
    return r


def _scalar_one(val):
    r = MagicMock()
    r.scalar_one.return_value = val
    return r


# ── Besluit 1: whitelist dekt alle reeds gebruikte element-namen ─────────────────

def test_whitelist_dekt_alle_in_gebruik_zijnde_elementen():
    from services.archimate_typing import ELEMENT_ARCHIMATE_TYPING, TOEGESTANE_ELEMENTEN
    from services.seed_componentconfig import bouw_componentconfig

    in_seed = {
        r["archimate_element"]
        for r in bouw_componentconfig()
        if r["dimensie"].value == "componenttype" and r["archimate_element"]
    }
    in_constante = {t["archimate_element"] for t in ELEMENT_ARCHIMATE_TYPING.values()}
    ontbrekend = (in_seed | in_constante) - TOEGESTANE_ELEMENTEN
    assert ontbrekend == set(), f"element-namen buiten de whitelist: {ontbrekend}"


# ── Besluit 3: geldigheid via field-validators ───────────────────────────────────

def test_validators_geldige_en_ongeldige_waarden():
    from schemas.componentconfig import ComponentConfigOptieCreate

    ok = ComponentConfigOptieCreate(dimensie="componenttype", optie_sleutel="etl_tool", label="ETL", **_TYP)
    assert ok.archimate_element == "system_software" and ok.archimate_laag == "technology"

    for veld, slechte in (
        ("archimate_element", "verzonnen_element"),
        ("archimate_laag", "verzonnen_laag"),
        ("archimate_aspect", "verzonnen_aspect"),
    ):
        kwargs = {**_TYP, veld: slechte}
        with pytest.raises(ValidationError):
            ComponentConfigOptieCreate(dimensie="componenttype", optie_sleutel="x", label="X", **kwargs)


def test_extra_forbid_blijft():
    from schemas.componentconfig import ComponentConfigOptieCreate

    with pytest.raises(ValidationError):
        ComponentConfigOptieCreate(
            dimensie="componenttype", optie_sleutel="x", label="X", onbekend_veld="z", **_TYP
        )


# ── Besluit 4: volledigheid bij aanmaken ─────────────────────────────────────────

def test_componenttype_zonder_volledige_typering_geweigerd():
    from schemas.componentconfig import ComponentConfigOptieCreate

    # helemaal geen typering
    with pytest.raises(ValidationError):
        ComponentConfigOptieCreate(dimensie="componenttype", optie_sleutel="x", label="X")
    # half gevuld
    with pytest.raises(ValidationError):
        ComponentConfigOptieCreate(
            dimensie="componenttype", optie_sleutel="x", label="X",
            archimate_element="system_software",
        )


def test_andere_dimensies_zonder_typering_toegestaan():
    from schemas.componentconfig import ComponentConfigOptieCreate

    for dim in ("structuurrelatie_type", "archimate_relatie"):
        opt = ComponentConfigOptieCreate(dimensie=dim, optie_sleutel="iets", label="Iets")
        assert opt.archimate_element is None and opt.archimate_laag is None and opt.archimate_aspect is None


# ── Besluit 5: service zet/corrigeert; leegmaken geweigerd ───────────────────────

def test_voeg_toe_zet_typering_lek_dicht():
    from schemas.componentconfig import ComponentConfigOptieCreate
    from services import componentconfig_service as svc

    session = AsyncMock()
    session.execute.side_effect = [_result(None), _scalar_one(2)]
    toegevoegd = []
    session.add = lambda o: toegevoegd.append(o)
    asyncio.run(svc.voeg_toe(session, ComponentConfigOptieCreate(
        dimensie="componenttype", optie_sleutel="etl_tool", label="ETL", **_TYP)))
    assert toegevoegd[0].archimate_element == "system_software"
    assert toegevoegd[0].laag == "technology" and toegevoegd[0].aspect == "active"


def test_wijzig_corrigeert_typering():
    from models.models import ComponentConfigDimensie
    from schemas.componentconfig import ComponentConfigOptieUpdate
    from services import componentconfig_service as svc

    optie = SimpleNamespace(
        id=5, dimensie=ComponentConfigDimensie.componenttype, optie_sleutel="database",
        label="Database", volgorde=1, actief=True,
        archimate_element="system_software", laag="technology", aspect="active",
    )
    session = AsyncMock()
    session.execute.return_value = _result(optie)
    asyncio.run(svc.wijzig(session, optie.id, ComponentConfigOptieUpdate(
        archimate_element="node", archimate_laag="technology", archimate_aspect="active")))
    assert optie.archimate_element == "node"  # gecorrigeerd
    assert optie.laag == "technology" and optie.aspect == "active"


def test_wijzig_leegmaken_componenttype_geweigerd():
    from models.models import ComponentConfigDimensie
    from schemas.componentconfig import ComponentConfigOptieUpdate
    from services import componentconfig_service as svc
    from services.errors import OngeldigeRegistratie

    optie = SimpleNamespace(
        id=5, dimensie=ComponentConfigDimensie.componenttype, optie_sleutel="database",
        label="Database", volgorde=1, actief=True,
        archimate_element="system_software", laag="technology", aspect="active",
    )
    session = AsyncMock()
    session.execute.return_value = _result(optie)
    # expliciet leegmaken (None) ⇒ geweigerd
    with pytest.raises(OngeldigeRegistratie) as ei:
        asyncio.run(svc.wijzig(session, optie.id, ComponentConfigOptieUpdate(archimate_element=None)))
    assert ei.value.code == "TYPERING_VERPLICHT"
    session.commit.assert_not_awaited()


# ── Engine onaangeroerd (1): offline import-afwezigheid ──────────────────────────

def test_engine_niet_geimporteerd_in_typering_paden():
    import pathlib

    base = pathlib.Path(__file__).resolve().parents[1] / "services"
    verboden = ("lifecycle_service", "herbereken_lifecycle", "ComponentProfiel", "Blokkade", "Checklistscore")
    for naam in ("componentconfig_service.py", "archimate_typing.py"):
        bron = (base / naam).read_text(encoding="utf-8")
        # alleen import-regels controleren (geen toevallige tekst in docstrings)
        importregels = [r for r in bron.splitlines() if r.lstrip().startswith(("import ", "from "))]
        blob = "\n".join(importregels)
        for term in verboden:
            assert term not in blob, f"{naam} importeert onverwacht {term}"


# ── F-2: volledig getypeerd componenttype komt correct door de laagprojectie ─────

def test_f2_projectie_volledig_getypeerd_componenttype():
    from models.models import ElementType
    from services import architectuur_service as arch

    catalog_typing = {
        "etl_tool": {"archimate_element": "system_software", "laag": "technology", "aspect": "active"},
        "kapot": {"archimate_element": None, "laag": None, "aspect": None},  # ongetypeerd (bestaat niet meer post-ADR-026)
    }
    rij = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001", element_type=ElementType.component,
        componenttype="etl_tool", component_naam="ETL X",
    )
    gelezen = arch._lees(rij, catalog_typing)
    assert gelezen["laag"] == "technology"
    assert gelezen["archimate_element"] == "system_software"
    assert gelezen["aspect"] == "active"

    # laag-filterset: een volledig getypeerd type valt in zijn laag; een ongetypeerd niet.
    typen_in_technology = [t for t, info in catalog_typing.items() if info.get("laag") == "technology"]
    assert "etl_tool" in typen_in_technology and "kapot" not in typen_in_technology


# ── Live tests (skipped als de dev-DB niet bereikbaar is) ────────────────────────

_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_LK_PLATFORM_URL = "postgresql+asyncpg://lk_platform:changeme_dev@localhost:5432/likara"


def _db_bereikbaar(url: str, probe: str) -> bool:
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


live_app = pytest.mark.skipif(
    not _db_bereikbaar(_LK_APP_URL, "SELECT to_regclass('componentconfig_optie')"),
    reason="componentconfig_optie niet bereikbaar als lk_app (stack/migratie 0025 niet toegepast)",
)
live_platform = pytest.mark.skipif(
    not _db_bereikbaar(_LK_PLATFORM_URL, "SELECT to_regclass('componentconfig_optie')"),
    reason="componentconfig_optie niet bereikbaar als lk_platform",
)


@live_app
def test_live_geen_actief_componenttype_zonder_typering():
    """Live-DB-dekkingstest (vervangt het gat van de seed-only test): geen ENKEL actief
    componenttype in de database draagt NULL-typering."""
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _run():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                n = (await c.execute(text(
                    "SELECT count(*) FROM componentconfig_optie "
                    "WHERE dimensie = 'componenttype' AND actief = true "
                    "AND (archimate_element IS NULL OR laag IS NULL OR aspect IS NULL)"
                ))).scalar()
            return n
        finally:
            await eng.dispose()
    assert asyncio.run(_run()) == 0


@live_platform
def test_live_db_check_weigert_ongetypeerd_componenttype():
    """DB-CHECK-backstop: een directe INSERT (buiten de app-laag, als de beheer-rol
    lk_platform) van een componenttype zonder volledige typering wordt door de DB geweigerd."""
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _run():
        eng = create_async_engine(_LK_PLATFORM_URL)
        try:
            async with eng.begin() as c:
                await c.execute(text(
                    "INSERT INTO componentconfig_optie "
                    "(dimensie, optie_sleutel, label, volgorde, actief, archimate_element, laag, aspect) "
                    "VALUES ('componenttype', 'adr026_backstop_probe', 'Probe', 999, true, NULL, NULL, NULL)"
                ))
        finally:
            await eng.dispose()

    with pytest.raises(IntegrityError):
        asyncio.run(_run())


@live_app
def test_live_geen_trigger_op_componentconfig_optie():
    """Engine onaangeroerd (2, live): er is GEEN trigger op componentconfig_optie, dus een
    INSERT/UPDATE van de typering kan onmogelijk component_profiel/lifecycle-state laten
    ontstaan of muteren (geen cascade-pad in de DB)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _run():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                return (await c.execute(text(
                    "SELECT count(*) FROM pg_trigger t "
                    "JOIN pg_class cl ON cl.oid = t.tgrelid "
                    "WHERE cl.relname = 'componentconfig_optie' AND NOT t.tgisinternal"
                ))).scalar()
        finally:
            await eng.dispose()
    assert asyncio.run(_run()) == 0
