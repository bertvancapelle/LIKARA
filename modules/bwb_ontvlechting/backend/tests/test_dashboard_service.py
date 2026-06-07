"""Unit-tests — dashboard_service (CD014, #9).

Offline (complidata-tests): een sequentiële fake-sessie levert per `execute`
een vooraf bepaald resultaat terug (group-by → `.all()`, count → `.scalar_one()`,
recent → `.all()`). Geen echte Postgres; de keyset/aggregatie is DB-zijdig en
valt buiten deze scope — getest wordt de respons-vorming.
"""
import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from models.models import LifecycleStatus
from services import dashboard_service as svc

TENANT_A = "11111111-1111-1111-1111-111111111111"


class _FakeResult:
    """Resultaat-stand-in: `.all()` voor rij-sets, `.scalar_one()` voor een scalar."""

    def __init__(self, *, rows=None, scalar=None):
        self._rows = rows
        self._scalar = scalar

    def all(self):
        return self._rows

    def scalar_one(self):
        return self._scalar


class _SeqSession:
    """Levert de gequeue'de resultaten in volgorde van de `execute`-aanroepen."""

    def __init__(self, resultaten):
        self._resultaten = list(resultaten)
        self.aantal_calls = 0

    async def execute(self, _stmt):
        result = self._resultaten[self.aantal_calls]
        self.aantal_calls += 1
        return result


def _recent_rij(naam, status, tijd):
    return SimpleNamespace(
        id=uuid.uuid4(), naam=naam, lifecycle_status=status, updated_at=tijd
    )


def test_dashboard_vorm_en_telling():
    nu = datetime(2026, 6, 7, 10, 0, tzinfo=timezone.utc)
    group_rows = [
        (LifecycleStatus.concept, 3),
        (LifecycleStatus.geblokkeerd, 2),
        (LifecycleStatus.migratieklaar, 1),
        # Transient — moet genegeerd worden, niet als sleutel verschijnen:
        (LifecycleStatus.checklist_compleet, 9),
    ]
    recent_rows = [
        _recent_rij("Zaaksysteem", LifecycleStatus.geblokkeerd, nu),
        _recent_rij("DMS", LifecycleStatus.migratieklaar, nu),
    ]
    sessie = _SeqSession(
        [
            _FakeResult(rows=group_rows),
            _FakeResult(scalar=4),
            _FakeResult(rows=recent_rows),
        ]
    )

    resultaat = asyncio.run(svc.haal_dashboard(sessie, TENANT_A))

    # Telling: exact de 4 reële statussen, 0-default, transient genegeerd.
    assert set(resultaat["lifecycle_telling"]) == {
        "concept",
        "in_inventarisatie",
        "geblokkeerd",
        "migratieklaar",
    }
    assert "checklist_compleet" not in resultaat["lifecycle_telling"]
    assert resultaat["lifecycle_telling"]["concept"] == 3
    assert resultaat["lifecycle_telling"]["geblokkeerd"] == 2
    assert resultaat["lifecycle_telling"]["migratieklaar"] == 1
    assert resultaat["lifecycle_telling"]["in_inventarisatie"] == 0  # niet in group-by

    # Open blokkades = de scalar.
    assert resultaat["open_blokkades"] == 4

    # Recent: mapping updated_at → gewijzigd_op, volgorde behouden.
    assert [r["naam"] for r in resultaat["recent_gewijzigd"]] == ["Zaaksysteem", "DMS"]
    assert resultaat["recent_gewijzigd"][0]["gewijzigd_op"] == nu
    assert "id" in resultaat["recent_gewijzigd"][0]


def test_dashboard_leeg_geeft_nul_telling_en_lege_recent():
    sessie = _SeqSession(
        [
            _FakeResult(rows=[]),  # geen applicaties
            _FakeResult(scalar=0),
            _FakeResult(rows=[]),
        ]
    )

    resultaat = asyncio.run(svc.haal_dashboard(sessie, TENANT_A))

    assert resultaat["lifecycle_telling"] == {
        "concept": 0,
        "in_inventarisatie": 0,
        "geblokkeerd": 0,
        "migratieklaar": 0,
    }
    assert resultaat["open_blokkades"] == 0
    assert resultaat["recent_gewijzigd"] == []


def test_recent_limiet_is_vast_server_side():
    """Het limiet zit server-side vast (geen client-input)."""
    assert svc._RECENT_LIMIT == 5
