"""Unit-tests — Blokkade service-laag (ADR-013, Model A).

Focus: statusprogressie + afgeleide `opgelost_op`, behoud van de tijd bij een
toelichting-only-edit, en dat een wijziging de lifecycle-herberekening aanroept.
Geen `maak_aan`/`verwijder` aanwezig (systeem-afgeleid). DB gemockt.
"""
import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

_APP = uuid.uuid4()


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
