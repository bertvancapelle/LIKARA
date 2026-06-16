"""Unit-tests — Blokkade service-laag (ADR-013, Model A).

Focus: statusprogressie + afgeleide `opgelost_op`, behoud van de tijd bij een
toelichting-only-edit, en dat een wijziging de lifecycle-herberekening aanroept.
Geen `maak_aan`/`verwijder` aanwezig (systeem-afgeleid). DB gemockt.
"""
import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

_APP = uuid.uuid4()
_TENANT = "11111111-1111-1111-1111-111111111111"


def _result(waarde):
    r = MagicMock()
    r.scalar_one_or_none.return_value = waarde
    return r


def test_geen_handmatige_aanmaak_of_verwijder():
    import services.blokkade_service as svc

    assert not hasattr(svc, "maak_aan")
    assert not hasattr(svc, "verwijder")


def test_werk_bij_handmatig_opgelost_weigeren_409(monkeypatch):
    # ADR-016: `opgelost` mag NIET handmatig — uitsluitend via de auto-logica.
    from models.models import BlokkadeStatus
    from schemas.blokkade import BlokkadeUpdate
    from services import blokkade_service as svc, lifecycle_service
    from services.errors import OngeldigeStatusovergang

    blok = SimpleNamespace(status=BlokkadeStatus.open, opgelost_op=None, component_id=_APP)
    session = AsyncMock()
    session.execute.return_value = _result(blok)

    herberekend = {}

    async def _herb(session, tenant_id, app_id):
        herberekend["app"] = app_id

    monkeypatch.setattr(lifecycle_service, "herbereken_lifecycle", _herb)

    with pytest.raises(OngeldigeStatusovergang):
        asyncio.run(
            svc.werk_bij(session, uuid.uuid4(), uuid.uuid4(), BlokkadeUpdate(status="opgelost"))
        )

    # Geweigerd vóór mutatie/herberekening: status ongewijzigd, geen herbereken-call.
    assert blok.status == BlokkadeStatus.open
    assert "app" not in herberekend


def test_werk_bij_terug_naar_open_leegt_tijd(monkeypatch):
    from models.models import BlokkadeStatus
    from schemas.blokkade import BlokkadeUpdate
    from services import blokkade_service as svc, lifecycle_service

    blok = SimpleNamespace(
        status=BlokkadeStatus.opgelost, opgelost_op="2026-01-01", component_id=_APP
    )
    session = AsyncMock()
    session.execute.return_value = _result(blok)

    async def _herb(*a, **k):
        return None

    monkeypatch.setattr(lifecycle_service, "herbereken_lifecycle", _herb)

    obj = asyncio.run(
        svc.werk_bij(session, uuid.uuid4(), uuid.uuid4(), BlokkadeUpdate(status="in_behandeling"))
    )

    assert obj.status == BlokkadeStatus.in_behandeling
    assert obj.opgelost_op is None


def test_werk_bij_toelichting_only_behoudt_opgelost_op(monkeypatch):
    from models.models import BlokkadeStatus
    from schemas.blokkade import BlokkadeUpdate
    from services import blokkade_service as svc, lifecycle_service

    blok = SimpleNamespace(
        status=BlokkadeStatus.opgelost, opgelost_op="2026-01-01", component_id=_APP
    )
    session = AsyncMock()
    session.execute.return_value = _result(blok)

    async def _herb(*a, **k):
        return None

    monkeypatch.setattr(lifecycle_service, "herbereken_lifecycle", _herb)

    obj = asyncio.run(
        svc.werk_bij(session, uuid.uuid4(), uuid.uuid4(), BlokkadeUpdate(toelichting="nieuw"))
    )

    # Status blijft opgelost → bestaande opgelost_op niet resetten.
    assert obj.status == BlokkadeStatus.opgelost
    assert obj.opgelost_op == "2026-01-01"


def test_haal_op_niet_gevonden():
    from services import blokkade_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    session.execute.return_value = _result(None)
    with pytest.raises(NietGevonden):
        asyncio.run(svc.haal_op(session, uuid.uuid4(), uuid.uuid4()))


# ── Herkomst-verrijking per-component lijst (DOORLOOP) ──────────────────────────
#
# Offline capture-sessie (zelfde patroon als test_blokkade_overzicht_service): we
# leggen het samengestelde statement vast (join-assert) en voeren rij-objecten terug
# om de verrijkte itemvorm te asserten. Bewijst dat de read de bron-vraag via de
# bestaande FK-keten (Blokkade → Checklistscore → ChecklistVraag) meelevert.

class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _CaptureSession:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.stmt = None

    async def execute(self, stmt):
        self.stmt = stmt
        return _Result(self._rows)


def _row(**kw):
    base = dict(
        id=uuid.uuid4(),
        checklistscore_id=uuid.uuid4(),
        component_id=_APP,
        status="open",
        toelichting=None,
        eigenaar=None,
        opgelost_op=None,
        created_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        checklistvraag_id=uuid.uuid4(),
        score="nee",
        vraag_code="1.1",
        vraag="Wat is de naam van de applicatie?",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_lijst_join_op_checklistscore_en_vraag():
    from services import blokkade_service as svc

    sess = _CaptureSession([_row()])
    asyncio.run(svc.lijst(sess, _TENANT, component_id=_APP))
    sql = str(sess.stmt)
    # De verplichte FK-keten wordt gejoind voor de herkomst (bron-vraag + score).
    assert "JOIN checklistscore" in sql
    assert "JOIN checklistvraag" in sql


def test_lijst_levert_bronvraag_en_score_mee():
    from services import blokkade_service as svc

    sess = _CaptureSession([_row(vraag_code="2.7", vraag="Gedeelde infra?", score="deels")])
    items, cursor = asyncio.run(svc.lijst(sess, _TENANT, component_id=_APP))
    assert len(items) == 1 and cursor is None
    it = items[0]
    # Herkomst-velden aanwezig en correct herleid.
    assert it["vraag_code"] == "2.7"
    assert it["vraag"] == "Gedeelde infra?"
    assert it["score"] == "deels"
    # Superset van BlokkadeRead: de bestaande velden blijven aanwezig (geen breuk).
    assert {"id", "checklistscore_id", "component_id", "status", "opgelost_op",
            "created_at", "updated_at"} <= set(it)
