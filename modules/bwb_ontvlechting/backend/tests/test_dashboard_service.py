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


def _label_rij(sleutel, label):
    return SimpleNamespace(optie_sleutel=sleutel, label=label, actief=True)


def test_dashboard_vorm_en_telling():
    # ADR-022 Fase F: readiness PER TYPE. Execute-volgorde: (1) group-by
    # (componenttype, status, count), (2) catalogus-labels, (3) open-blokkades, (4) recent.
    nu = datetime(2026, 6, 7, 10, 0, tzinfo=timezone.utc)
    group_rows = [
        ("applicatie", LifecycleStatus.concept, 3),
        ("applicatie", LifecycleStatus.geblokkeerd, 2),
        ("applicatie", LifecycleStatus.migratieklaar, 1),
        # Transient — moet genegeerd worden, niet als sleutel verschijnen:
        ("applicatie", LifecycleStatus.checklist_compleet, 9),
        ("database", LifecycleStatus.in_inventarisatie, 2),
    ]
    label_rows = [_label_rij("applicatie", "Applicatie"), _label_rij("database", "Database")]
    recent_rows = [
        _recent_rij("Zaaksysteem", LifecycleStatus.geblokkeerd, nu),
        _recent_rij("Oracle FIN-DB", LifecycleStatus.in_inventarisatie, nu),
    ]
    sessie = _SeqSession(
        [
            _FakeResult(rows=group_rows),
            _FakeResult(rows=label_rows),
            _FakeResult(scalar=4),
            _FakeResult(rows=recent_rows),
            # ADR-027 slice 3 — (5) klaar_verklaard, (6) klaar_met_afwijking.
            _FakeResult(scalar=3),
            _FakeResult(scalar=1),
        ]
    )

    resultaat = asyncio.run(svc.haal_dashboard(sessie, TENANT_A))

    # Per-type, gesorteerd op componenttype; geen gefuseerd cijfer (Besluit 3).
    per_type = {r["componenttype"]: r for r in resultaat["readiness_per_type"]}
    assert list(per_type) == ["applicatie", "database"]
    app = per_type["applicatie"]
    assert app["componenttype_label"] == "Applicatie"
    # Exact de 4 reële statussen, 0-default, transient genegeerd.
    assert set(app["telling"]) == {"concept", "in_inventarisatie", "geblokkeerd", "migratieklaar"}
    assert "checklist_compleet" not in app["telling"]
    assert app["telling"]["concept"] == 3
    assert app["telling"]["geblokkeerd"] == 2
    assert app["telling"]["migratieklaar"] == 1
    assert app["telling"]["in_inventarisatie"] == 0
    assert app["totaal"] == 6 and app["migratieklaar"] == 1  # "n van m gereed"
    db = per_type["database"]
    assert db["componenttype_label"] == "Database"
    assert db["telling"]["in_inventarisatie"] == 2 and db["totaal"] == 2 and db["migratieklaar"] == 0

    # Open blokkades = de scalar.
    assert resultaat["open_blokkades"] == 4

    # ADR-027 slice 3 — klaarverklaring-voortgang (read-only afgeleid).
    assert resultaat["klaar_verklaard"] == 3
    assert resultaat["klaar_met_afwijking"] == 1

    # Recent (type-generiek): mapping updated_at → gewijzigd_op, volgorde behouden.
    assert [r["naam"] for r in resultaat["recent_gewijzigd"]] == ["Zaaksysteem", "Oracle FIN-DB"]
    assert resultaat["recent_gewijzigd"][0]["gewijzigd_op"] == nu
    assert "id" in resultaat["recent_gewijzigd"][0]


def test_dashboard_leeg_geeft_lege_rollup_en_recent():
    sessie = _SeqSession(
        [
            _FakeResult(rows=[]),  # geen profiel-dragende componenten
            _FakeResult(rows=[]),  # catalogus-labels
            _FakeResult(scalar=0),
            _FakeResult(rows=[]),
            _FakeResult(scalar=0),  # klaar_verklaard
            _FakeResult(scalar=0),  # klaar_met_afwijking
        ]
    )

    resultaat = asyncio.run(svc.haal_dashboard(sessie, TENANT_A))

    assert resultaat["readiness_per_type"] == []  # geen type met profielen
    assert resultaat["open_blokkades"] == 0
    assert resultaat["recent_gewijzigd"] == []
    assert resultaat["klaar_verklaard"] == 0 and resultaat["klaar_met_afwijking"] == 0


def test_recent_limiet_is_vast_server_side():
    """Het limiet zit server-side vast (geen client-input)."""
    assert svc._RECENT_LIMIT == 5
