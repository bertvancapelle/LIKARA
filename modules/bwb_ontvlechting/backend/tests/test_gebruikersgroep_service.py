"""Unit-tests — Gebruikersgroep service-laag (P5-vervolg).

Focus: ouder-validatie tenant-scoped, happy-path aanmaken, tenant-scoped
niet-gevonden. DB gemockt.
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _create_data(applicatie_id):
    from schemas.gebruikersgroep import GebruikersgroepCreate

    return GebruikersgroepCreate(
        applicatie_id=applicatie_id, organisatie="Gemeente Veldendam", aantal_gebruikers=5
    )


def test_maak_aan_ouder_ontbreekt_geeft_nietgevonden(monkeypatch):
    from services import applicatie_service, gebruikersgroep_service as svc
    from services.errors import NietGevonden

    async def _raise(*a, **k):
        raise NietGevonden("applicatie", "x")

    monkeypatch.setattr(applicatie_service, "haal_op", _raise)
    session = AsyncMock()

    with pytest.raises(NietGevonden):
        asyncio.run(svc.maak_aan(session, uuid.uuid4(), _create_data(uuid.uuid4())))
    session.commit.assert_not_awaited()


def test_maak_aan_ouder_bestaat(monkeypatch):
    # ADR-023 slice 4: element + gebruikersgroep + serving-relatie (applicatie → groep).
    from models.models import Element, Relatie
    from services import applicatie_service, gebruikersgroep_service as svc

    async def _ok(*a, **k):
        return object()

    monkeypatch.setattr(applicatie_service, "haal_op", _ok)
    session = AsyncMock()
    toegevoegd = []
    session.add = lambda obj: toegevoegd.append(obj)

    app_id = uuid.uuid4()
    tid = "11111111-1111-1111-1111-111111111111"
    out = asyncio.run(svc.maak_aan(session, tid, _create_data(app_id)))

    assert str(out["applicatie_id"]) == str(app_id)
    assert out["organisatie"] == "Gemeente Veldendam"
    assert out["aantal_gebruikers"] == 5
    assert any(isinstance(o, Element) for o in toegevoegd)
    rel = next(o for o in toegevoegd if isinstance(o, Relatie))
    assert rel.relatietype == "serving" and str(rel.bron_id) == str(app_id)
    session.commit.assert_awaited_once()


def test_haal_op_niet_gevonden():
    from services import gebruikersgroep_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    resultaat = MagicMock()
    resultaat.scalar_one_or_none.return_value = None
    session.execute.return_value = resultaat

    with pytest.raises(NietGevonden):
        asyncio.run(svc.haal_op(session, uuid.uuid4(), uuid.uuid4()))
