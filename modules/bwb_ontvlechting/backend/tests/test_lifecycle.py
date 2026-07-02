"""Unit-tests — lifecycle-herberekening (Model A, ADR-013).

De pure beslisregel `bepaal_lifecycle` (alle uitkomsten + reverse) wordt DB-vrij
getest; `herbereken_lifecycle` wordt met een gemockte sessie op de bedrading
getest; en de additieve koppeling in `start_inventarisatie` op het aanroepen van
de herberekening.
"""
import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

_TID = "11111111-1111-1111-1111-111111111111"
_APP = "22222222-2222-2222-2222-222222222222"


# ── Pure beslisregel ────────────────────────────────────────────────────────

def test_concept_blijft_concept_ongeacht_feiten():
    from models.models import LifecycleStatus
    from services.lifecycle_service import bepaal_lifecycle

    # Zelfs alles gescoord + open blokkade mag concept niet verlaten.
    assert bepaal_lifecycle(LifecycleStatus.concept, 89, 89, 3) == LifecycleStatus.concept
    assert bepaal_lifecycle(LifecycleStatus.concept, 0, 89, 0) == LifecycleStatus.concept


def test_niet_alles_gescoord_geeft_in_inventarisatie():
    from models.models import LifecycleStatus
    from services.lifecycle_service import bepaal_lifecycle

    assert (
        bepaal_lifecycle(LifecycleStatus.in_inventarisatie, 40, 89, 0)
        == LifecycleStatus.in_inventarisatie
    )


def test_alles_gescoord_met_open_blokkade_geeft_geblokkeerd():
    from models.models import LifecycleStatus
    from services.lifecycle_service import bepaal_lifecycle

    assert (
        bepaal_lifecycle(LifecycleStatus.in_inventarisatie, 89, 89, 1)
        == LifecycleStatus.geblokkeerd
    )


def test_alles_gescoord_geen_open_blokkade_geeft_migratieklaar():
    from models.models import LifecycleStatus
    from services.lifecycle_service import bepaal_lifecycle

    assert (
        bepaal_lifecycle(LifecycleStatus.in_inventarisatie, 89, 89, 0)
        == LifecycleStatus.migratieklaar
    )


def test_reverse_migratieklaar_naar_in_inventarisatie_bij_nieuwe_vraag():
    from models.models import LifecycleStatus
    from services.lifecycle_service import bepaal_lifecycle

    # Vraag erbij (90) terwijl 89 gescoord → terug naar in_inventarisatie.
    assert (
        bepaal_lifecycle(LifecycleStatus.migratieklaar, 89, 90, 0)
        == LifecycleStatus.in_inventarisatie
    )


def test_reverse_geblokkeerd_naar_migratieklaar_bij_oplossen():
    from models.models import LifecycleStatus
    from services.lifecycle_service import bepaal_lifecycle

    assert (
        bepaal_lifecycle(LifecycleStatus.geblokkeerd, 89, 89, 0)
        == LifecycleStatus.migratieklaar
    )


def test_reverse_migratieklaar_naar_geblokkeerd_bij_heropenen():
    from models.models import LifecycleStatus
    from services.lifecycle_service import bepaal_lifecycle

    assert (
        bepaal_lifecycle(LifecycleStatus.migratieklaar, 89, 89, 1)
        == LifecycleStatus.geblokkeerd
    )


def test_lege_vragenset_geeft_in_inventarisatie():
    from models.models import LifecycleStatus
    from services.lifecycle_service import bepaal_lifecycle

    assert (
        bepaal_lifecycle(LifecycleStatus.in_inventarisatie, 0, 0, 0)
        == LifecycleStatus.in_inventarisatie
    )


# ── herbereken_lifecycle (bedrading met gemockte sessie) ────────────────────

def _resultaat(waarde):
    r = MagicMock()
    r.scalar_one_or_none.return_value = waarde
    r.scalar_one.return_value = waarde
    return r


def _rij(profiel, componenttype="applicatie"):
    """ADR-022 Fase B: herbereken leest (profiel, componenttype) via `.first()`
    (join profiel→component). None ⇒ niet gevonden."""
    r = MagicMock()
    r.first.return_value = None if profiel is None else (profiel, componenttype)
    return r


def test_herbereken_zet_geblokkeerd():
    from models.models import LifecycleStatus
    from services import lifecycle_service as ls

    profiel = SimpleNamespace(lifecycle_status=LifecycleStatus.in_inventarisatie)
    session = AsyncMock()
    # Volgorde: (profiel, type)-select, per-type vragen-count, gescoord-count, open-blokkade-count
    session.execute.side_effect = [
        _rij(profiel),
        _resultaat(89),
        _resultaat(89),
        _resultaat(2),
    ]

    nieuwe = asyncio.run(ls.herbereken_lifecycle(session, _TID, _APP))
    assert nieuwe == LifecycleStatus.geblokkeerd
    assert profiel.lifecycle_status == LifecycleStatus.geblokkeerd


def test_herbereken_concept_blijft_concept():
    from models.models import LifecycleStatus
    from services import lifecycle_service as ls

    profiel = SimpleNamespace(lifecycle_status=LifecycleStatus.concept)
    session = AsyncMock()
    session.execute.side_effect = [
        _rij(profiel),
        _resultaat(89),
        _resultaat(89),
        _resultaat(0),
    ]

    nieuwe = asyncio.run(ls.herbereken_lifecycle(session, _TID, _APP))
    assert nieuwe == LifecycleStatus.concept
    assert profiel.lifecycle_status == LifecycleStatus.concept


def test_herbereken_onbekende_applicatie_geeft_nietgevonden():
    from services import lifecycle_service as ls
    from services.errors import NietGevonden
    import pytest

    session = AsyncMock()
    session.execute.side_effect = [_rij(None)]
    with pytest.raises(NietGevonden):
        asyncio.run(ls.herbereken_lifecycle(session, _TID, _APP))


# ── start_inventarisatie roept herberekening aan (additief, P5-uitbreiding) ──

def test_start_inventarisatie_herberekent_na_transitie(monkeypatch):
    from models.models import LifecycleStatus
    from services import applicatie_service as svc, lifecycle_service

    # ADR-022 Fase E: start_inventarisatie delegeert naar de type-generieke
    # lifecycle_service.start_beoordeling (concept → in_inventarisatie + herberekening).
    # LI059 Slice 3: de facade levert een component-object; `lifecycle_status` is een
    # transient attribuut (via `_verrijk` uit het profiel), niet meer `.profiel.lifecycle_status`.
    from services import componentconfig_catalog

    comp = SimpleNamespace(id=_APP, eigenaar_organisatie_id=None)

    async def _haal(session, tenant_id, app_id):
        return comp

    monkeypatch.setattr(svc, "haal_op", _haal)

    aangeroepen = {}

    async def _start(session, tenant_id, component_id):
        aangeroepen["yes"] = True
        # Simuleer: vóór de start al alles gescoord, geen open blokkade → migratieklaar.
        return LifecycleStatus.migratieklaar

    monkeypatch.setattr(lifecycle_service, "start_beoordeling", _start)

    async def _dragend(session, sleutel):
        return True

    monkeypatch.setattr(componentconfig_catalog, "is_checklist_dragend", _dragend)

    # `_verrijk` her-queryt de lifecycle uit het profiel → voed het mock-resultaat
    # (expliciete MagicMock zodat `.scalar_one_or_none()` synchroon de status teruggeeft).
    _res = MagicMock()
    _res.scalar_one_or_none.return_value = LifecycleStatus.migratieklaar
    session = AsyncMock()
    session.execute.return_value = _res

    obj = asyncio.run(svc.start_inventarisatie(session, _TID, _APP))

    assert aangeroepen.get("yes") is True
    assert obj is comp
    assert obj.lifecycle_status == LifecycleStatus.migratieklaar
