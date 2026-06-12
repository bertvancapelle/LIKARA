"""Unit-tests — Applicatie service-laag (P5).

Geen echte DB: de async-sessie wordt gemockt (AsyncMock). Getest worden de
default-lifecycle bij aanmaken, de pure lifecycle-overgangsregel (geldig +
ongeldig), tenant-scoped niet-gevonden (OP-6) en de cursor-paginering-helper.
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _create_data():
    from schemas.applicatie import ApplicatieCreate

    return ApplicatieCreate(
        naam="Zaaksysteem",
        hostingmodel="saas",
        eigenaar_organisatie="Gemeente Veldendam",
        migratiepad="herbouw",
        complexiteit="midden",
        prioriteit="hoog",
    )


# ── maak_aan: default lifecycle = concept ───────────────────────────────────

def test_maak_aan_zet_lifecycle_concept():
    # ADR-021: maak_aan creëert component (naam/identiteit) + applicatie-subtype
    # (lifecycle) atomair — shared-PK class-table.
    from models.models import Applicatie, Component, ComponentProfiel, LifecycleStatus
    from services import applicatie_service as svc

    session = AsyncMock()
    toegevoegd = []
    session.add = lambda obj: toegevoegd.append(obj)  # add is synchroon

    tid = "11111111-1111-1111-1111-111111111111"
    asyncio.run(svc.maak_aan(session, tid, _create_data()))

    comp = next(o for o in toegevoegd if isinstance(o, Component))
    sub = next(o for o in toegevoegd if isinstance(o, Applicatie))
    # ADR-022 Fase A: lifecycle_status leeft op het generieke ComponentProfiel (shared-PK).
    profiel = next(o for o in toegevoegd if isinstance(o, ComponentProfiel))
    assert comp.naam == "Zaaksysteem"
    assert comp.componenttype == "applicatie"
    assert str(comp.tenant_id) == tid
    assert profiel.lifecycle_status == LifecycleStatus.concept
    assert str(sub.tenant_id) == tid
    session.flush.assert_awaited_once()  # component-id vóór het subtype
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once()


# ── lifecycle-overgang (pure regel) ─────────────────────────────────────────

def test_start_inventarisatie_geldige_overgang():
    from models.models import LifecycleStatus
    from services.applicatie_service import volgende_status_na_start

    assert volgende_status_na_start(LifecycleStatus.concept) == LifecycleStatus.in_inventarisatie


def test_start_inventarisatie_ongeldige_overgangen():
    from models.models import LifecycleStatus
    from services.applicatie_service import volgende_status_na_start
    from services.errors import OngeldigeStatusovergang

    for status in (
        LifecycleStatus.in_inventarisatie,
        LifecycleStatus.checklist_compleet,
        LifecycleStatus.geblokkeerd,
        LifecycleStatus.migratieklaar,
    ):
        with pytest.raises(OngeldigeStatusovergang):
            volgende_status_na_start(status)


# ── tenant-scoped niet gevonden (OP-6) ──────────────────────────────────────

def test_haal_op_niet_gevonden_geeft_nietgevonden():
    from services import applicatie_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    resultaat = MagicMock()
    resultaat.scalar_one_or_none.return_value = None
    session.execute.return_value = resultaat

    with pytest.raises(NietGevonden):
        asyncio.run(svc.haal_op(session, uuid.uuid4(), uuid.uuid4()))
