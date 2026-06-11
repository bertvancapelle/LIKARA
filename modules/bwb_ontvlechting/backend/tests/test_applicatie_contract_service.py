"""Unit-tests — ApplicatieContract service-laag (ADR-020 fase B). DB gemockt."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

TID = "11111111-1111-1111-1111-111111111111"


def _create(rol="valt_onder"):
    from schemas.applicatie_contract import ApplicatieContractCreate

    return ApplicatieContractCreate(
        applicatie_id=uuid.uuid4(), contract_id=uuid.uuid4(), relatie_rol=rol
    )


def test_maak_aan_dubbele_koppeling_geeft_conflict(monkeypatch):
    from services import applicatie_contract_service as svc
    from services import applicatie_service, contract_service
    from services import contractconfig_catalog as catalog
    from services.errors import RegistratieConflict

    async def _ok(*a, **k):
        return MagicMock()

    async def _val(session, dim, sleutels):
        return None

    monkeypatch.setattr(applicatie_service, "haal_op", _ok)
    monkeypatch.setattr(contract_service, "haal_op", _ok)
    monkeypatch.setattr(catalog, "valideer_sleutels", _val)

    session = AsyncMock()
    bestaat = MagicMock()
    bestaat.scalar_one_or_none.return_value = uuid.uuid4()  # koppeling bestaat al
    session.execute.return_value = bestaat

    with pytest.raises(RegistratieConflict) as e:
        asyncio.run(svc.maak_aan(session, TID, _create()))
    assert e.value.code == "KOPPELING_BESTAAT"
    session.commit.assert_not_awaited()


def test_maak_aan_ongeldige_rol_geeft_422(monkeypatch):
    from services import applicatie_contract_service as svc
    from services import applicatie_service, contract_service
    from services import contractconfig_catalog as catalog
    from services.errors import OngeldigeRegistratie

    async def _ok(*a, **k):
        return MagicMock()

    async def _actief(session, dim):
        return set()  # geen actieve rollen → elke rol ongeldig

    monkeypatch.setattr(applicatie_service, "haal_op", _ok)
    monkeypatch.setattr(contract_service, "haal_op", _ok)
    monkeypatch.setattr(catalog, "actieve_sleutels", _actief)

    session = AsyncMock()
    with pytest.raises(OngeldigeRegistratie) as e:
        asyncio.run(svc.maak_aan(session, TID, _create(rol="onbekend")))
    assert e.value.code == "ONGELDIGE_OPTIE"


def test_maak_aan_contract_buiten_tenant_geeft_404(monkeypatch):
    from services import applicatie_contract_service as svc
    from services import applicatie_service, contract_service
    from services.errors import NietGevonden

    async def _app_ok(*a, **k):
        return MagicMock()

    async def _contract_weg(session, tenant_id, cid):
        raise NietGevonden("contract", cid)

    monkeypatch.setattr(applicatie_service, "haal_op", _app_ok)
    monkeypatch.setattr(contract_service, "haal_op", _contract_weg)

    session = AsyncMock()
    with pytest.raises(NietGevonden):
        asyncio.run(svc.maak_aan(session, TID, _create()))
    session.commit.assert_not_awaited()


def test_haal_op_niet_gevonden():
    from services import applicatie_contract_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    resultaat = MagicMock()
    resultaat.scalar_one_or_none.return_value = None
    session.execute.return_value = resultaat

    with pytest.raises(NietGevonden):
        asyncio.run(svc.haal_op(session, uuid.uuid4(), uuid.uuid4()))
