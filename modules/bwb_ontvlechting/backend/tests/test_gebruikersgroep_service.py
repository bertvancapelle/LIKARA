"""Unit-tests — Gebruikersgroep service-laag (P5-vervolg).

Focus: ouder-validatie tenant-scoped, happy-path aanmaken, tenant-scoped
niet-gevonden. DB gemockt.
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _create_data(component_id, organisatie_id=None):
    from schemas.gebruikersgroep import GebruikersgroepCreate

    # ADR-038 — organisatie is verplicht.
    return GebruikersgroepCreate(
        component_id=component_id, organisatie_id=organisatie_id or uuid.uuid4(), aantal_gebruikers=5
    )


def test_maak_aan_ouder_ontbreekt_geeft_nietgevonden(monkeypatch):
    # LI059 Slice 3: de ouder-check loopt via component_service.haal_op (geen subtabel meer).
    from services import component_service, gebruikersgroep_service as svc
    from services.errors import NietGevonden

    async def _raise(*a, **k):
        raise NietGevonden("component", "x")

    monkeypatch.setattr(component_service, "haal_op", _raise)
    session = AsyncMock()

    with pytest.raises(NietGevonden):
        asyncio.run(svc.maak_aan(session, uuid.uuid4(), _create_data(uuid.uuid4())))
    session.commit.assert_not_awaited()


def test_maak_aan_ouder_bestaat(monkeypatch):
    # ADR-023 slice 4: element + gebruikersgroep + serving-relatie (applicatie → groep).
    # LI059 Slice 3: de ouder-check verifieert componenttype='applicatie' via component_service.
    from types import SimpleNamespace

    from models.models import Element, Relatie
    from services import component_service, gebruikersgroep_service as svc
    from services import organisatiegebruik_service

    async def _ok(*a, **k):
        return SimpleNamespace(componenttype="applicatie")

    monkeypatch.setattr(component_service, "haal_op", _ok)
    # ADR-038 — organisatie is verplicht: het grove feit wordt altijd ge-ensured. Mock de ensure
    # + de leesresolutie (org-/afdeling-naam) zodat deze unit-test de maak_aan-mechaniek toetst.
    gebruik_id = uuid.uuid4()
    org_id = uuid.uuid4()

    async def _ensure(*a, **k):
        return gebruik_id

    async def _org(*a, **k):
        return (org_id, "WT-Org")

    async def _afd(*a, **k):
        return None

    monkeypatch.setattr(organisatiegebruik_service, "ensure", _ensure)
    monkeypatch.setattr(svc, "_org_voor_gebruik", _org)
    monkeypatch.setattr(svc, "_afdeling_naam", _afd)
    session = AsyncMock()
    toegevoegd = []
    session.add = lambda obj: toegevoegd.append(obj)

    app_id = uuid.uuid4()
    tid = "11111111-1111-1111-1111-111111111111"
    out = asyncio.run(svc.maak_aan(session, tid, _create_data(app_id, organisatie_id=org_id)))

    assert str(out["component_id"]) == str(app_id)
    assert out["organisatie_id"] == org_id and out["organisatie_naam"] == "WT-Org"
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
