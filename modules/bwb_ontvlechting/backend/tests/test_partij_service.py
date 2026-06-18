"""Tests — partij-beheer (ADR-024 slice 2a). Vervangt test_externe_partij_service.

Offline (mocked) service-/schema-asserts + engine-onaangeroerd-borging (import-afwezigheid).
Live: geen trigger op `partij`, geen wees-element. Generalisatie: maak_aan zet de meegegeven
aard (niet langer hardgecodeerd externe_partij).
"""
import asyncio
import pathlib
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text


def _result(val):
    r = MagicMock()
    r.scalar_one_or_none.return_value = val
    return r


def _scalar_one(val):
    r = MagicMock()
    r.scalar_one.return_value = val
    return r


# ── Offline: schema-/service-asserts ─────────────────────────────────────────────

def test_sorteer_allowlist_synchroon_met_schema():
    from schemas.partij import PartijSorteerveld
    from services import partij_service as svc

    assert set(svc._SORTEERBARE_KOLOMMEN) == {e.value for e in PartijSorteerveld}


def test_maak_aan_is_element_backed_en_zet_meegegeven_aard():
    from models.models import Element, ElementType, Partij, PartijAard
    from schemas.partij import PartijCreate
    from services import partij_service as svc

    # Generalisatie: een organisatie (niet externe_partij) wordt element-backed aangemaakt.
    # Aard organisatie heeft géén organisatie-ouder → geen cross-row lookup nodig (mock-vrij).
    session = AsyncMock()
    toegevoegd = []
    session.add = lambda o: toegevoegd.append(o)
    asyncio.run(svc.maak_aan(session, uuid.uuid4(), PartijCreate(aard="organisatie", naam="Gemeente X")))
    assert isinstance(toegevoegd[0], Element) and toegevoegd[0].element_type == ElementType.partij
    assert isinstance(toegevoegd[1], Partij) and toegevoegd[1].aard == PartijAard.organisatie
    assert toegevoegd[1].naam == "Gemeente X"
    session.flush.assert_awaited()  # flush vóór de partij (shared-PK)
    session.commit.assert_awaited_once()


def test_haal_op_niet_gevonden():
    from services import partij_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    session.execute.return_value = _result(None)
    with pytest.raises(NietGevonden):
        asyncio.run(svc.haal_op(session, uuid.uuid4(), uuid.uuid4()))


def test_update_kent_geen_aard():
    """De aard is vast na aanmaken — PartijUpdate heeft geen aard-veld (extra='forbid')."""
    from pydantic import ValidationError
    from schemas.partij import PartijUpdate

    assert "aard" not in PartijUpdate.model_fields
    with pytest.raises(ValidationError):
        PartijUpdate(aard="organisatie")  # extra veld geweigerd


def test_verwijder_met_contracten_geeft_in_gebruik():
    from models.models import PartijAard
    from services import partij_service as svc
    from services.errors import RegistratieConflict

    partij = SimpleNamespace(id=uuid.uuid4(), aard=PartijAard.externe_partij, naam="Acme")
    session = AsyncMock()
    # haal_op ⇒ partij; daarna count(contracten) ⇒ 1 ⇒ IN_GEBRUIK (vóór de FK RESTRICT).
    session.execute.side_effect = [_result(partij), _scalar_one(1)]
    with pytest.raises(RegistratieConflict) as ei:
        asyncio.run(svc.verwijder(session, uuid.uuid4(), partij.id))
    assert ei.value.code == "IN_GEBRUIK"
    session.commit.assert_not_awaited()


def test_soort_validatie_weigert_onbekende_soort():
    from services import partijsoort_catalog
    from services.errors import OngeldigeRegistratie

    session = AsyncMock()
    r = MagicMock()
    r.scalars.return_value.all.return_value = ["leverancier"]
    session.execute.return_value = r
    asyncio.run(partijsoort_catalog.valideer_soort(session, None))  # None ⇒ ok
    with pytest.raises(OngeldigeRegistratie) as ei:
        asyncio.run(partijsoort_catalog.valideer_soort(session, "onzin"))
    assert ei.value.code == "ONGELDIGE_SOORT"


# ── Lidmaatschap (slice 2a-bis): structuur + cross-row laag-consistentie ─────────

def test_schema_persoon_zonder_organisatie_geweigerd():
    from pydantic import ValidationError
    from schemas.partij import PartijCreate

    with pytest.raises(ValidationError):
        PartijCreate(aard="persoon", naam="J")  # organisatie verplicht
    with pytest.raises(ValidationError):
        PartijCreate(aard="organisatie_eenheid", naam="A")  # afdeling vereist organisatie
    with pytest.raises(ValidationError):
        PartijCreate(aard="organisatie", naam="O", organisatie_id=uuid.uuid4())  # top staat op zichzelf


def test_lidmaatschap_organisatie_moet_organisatie_achtig_zijn():
    from models.models import PartijAard
    from services import partij_service as svc
    from services.errors import OngeldigeRegistratie

    org_id = uuid.uuid4()
    persoon = SimpleNamespace(id=org_id, aard=PartijAard.persoon, organisatie_id=uuid.uuid4())
    session = AsyncMock()
    session.execute.return_value = _result(persoon)  # de "organisatie" is in werkelijkheid een persoon
    with pytest.raises(OngeldigeRegistratie) as ei:
        asyncio.run(svc._valideer_lidmaatschap(session, uuid.uuid4(), PartijAard.persoon, org_id, None))
    assert ei.value.code == "ONGELDIGE_ORGANISATIE"


def test_lidmaatschap_afdeling_moet_bij_gekozen_organisatie_horen():
    from models.models import PartijAard
    from services import partij_service as svc
    from services.errors import OngeldigeRegistratie

    org_id, afd_id = uuid.uuid4(), uuid.uuid4()
    org = SimpleNamespace(id=org_id, aard=PartijAard.organisatie, organisatie_id=None)
    afd_andere_org = SimpleNamespace(id=afd_id, aard=PartijAard.organisatie_eenheid, organisatie_id=uuid.uuid4())
    session = AsyncMock()
    session.execute.side_effect = [_result(org), _result(afd_andere_org)]
    with pytest.raises(OngeldigeRegistratie) as ei:
        asyncio.run(svc._valideer_lidmaatschap(session, uuid.uuid4(), PartijAard.persoon, org_id, afd_id))
    assert ei.value.code == "ONGELDIGE_AFDELING"


def test_lidmaatschap_geldig_persoon_org_en_afdeling():
    from models.models import PartijAard
    from services import partij_service as svc

    org_id, afd_id = uuid.uuid4(), uuid.uuid4()
    org = SimpleNamespace(id=org_id, aard=PartijAard.organisatie, organisatie_id=None)
    afd = SimpleNamespace(id=afd_id, aard=PartijAard.organisatie_eenheid, organisatie_id=org_id)
    session = AsyncMock()
    session.execute.side_effect = [_result(org), _result(afd)]
    # Geldig: afdeling hoort bij de gekozen organisatie ⇒ geen exception.
    asyncio.run(svc._valideer_lidmaatschap(session, uuid.uuid4(), PartijAard.persoon, org_id, afd_id))


# ── Engine-onaangeroerd (1): offline import-afwezigheid ──────────────────────────

def test_engine_niet_geimporteerd_in_partij_paden():
    base = pathlib.Path(__file__).resolve().parents[1] / "services"
    verboden = ("lifecycle_service", "herbereken_lifecycle", "ComponentProfiel", "Blokkade", "Checklistscore")
    for naam in ("partij_service.py", "partijsoort_catalog.py"):
        importregels = [
            r for r in (base / naam).read_text(encoding="utf-8").splitlines()
            if r.lstrip().startswith(("import ", "from "))
        ]
        blob = "\n".join(importregels)
        for term in verboden:
            assert term not in blob, f"{naam} importeert onverwacht {term}"


# ── Live (na DB-reset) ───────────────────────────────────────────────────────────

_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"
_DEV_TENANT = "11111111-1111-1111-1111-111111111111"


def _partij_tabel_bestaat() -> bool:
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_CD_APP_URL)
        try:
            async with eng.connect() as c:
                return (await c.execute(text("SELECT to_regclass('partij')"))).scalar() is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


live = pytest.mark.skipif(
    not _partij_tabel_bestaat(), reason="partij-tabel niet bereikbaar (migratie 0027 niet toegepast)"
)


@live
def test_live_geen_trigger_op_partij():
    """Engine-onaangeroerd (2, live): geen trigger op `partij` → een partij-write kan geen
    component_profiel/lifecycle-state laten ontstaan (geen cascade-pad)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _run():
        eng = create_async_engine(_CD_APP_URL)
        try:
            async with eng.connect() as c:
                return (await c.execute(text(
                    "SELECT count(*) FROM pg_trigger t JOIN pg_class cl ON cl.oid = t.tgrelid "
                    "WHERE cl.relname = 'partij' AND NOT t.tgisinternal"
                ))).scalar()
        finally:
            await eng.dispose()
    assert asyncio.run(_run()) == 0


@live
def test_live_geen_wees_element_partij():
    """Geen wees-element: er is geen element van type 'partij' zonder bijbehorende partij-rij."""
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _run():
        eng = create_async_engine(_CD_APP_URL)
        try:
            async with eng.connect() as c:
                # `element`/`partij` zijn FORCE RLS → tenant-context zetten vóór de telling.
                await c.execute(
                    text("SELECT set_config('app.tenant_id', :t, false)"), {"t": _DEV_TENANT}
                )
                return (await c.execute(text(
                    "SELECT count(*) FROM element e WHERE e.element_type = 'partij' "
                    "AND NOT EXISTS (SELECT 1 FROM partij p WHERE p.id = e.id)"
                ))).scalar()
        finally:
            await eng.dispose()
    assert asyncio.run(_run()) == 0
