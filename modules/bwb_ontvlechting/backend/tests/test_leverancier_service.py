"""Unit-tests — Leverancier service-laag (ADR-020 fase B). DB gemockt."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

TID = "11111111-1111-1111-1111-111111111111"


def test_sorteer_allowlist_synchroon_met_schema():
    """De schema-enum en de service-allowlist + parsers blijven synchroon (ADR-017)."""
    from schemas.leverancier import LeverancierSorteerveld
    from services import leverancier_service as svc

    enum_velden = {e.value for e in LeverancierSorteerveld}
    assert enum_velden == set(svc._SORTEERBARE_KOLOMMEN)
    assert enum_velden == set(svc._WAARDE_PARSERS)


def test_maak_aan_zet_tenant_en_velden():
    from services import leverancier_service as svc
    from schemas.leverancier import LeverancierCreate

    session = AsyncMock()
    vast = {}
    session.add = lambda obj: vast.setdefault("obj", obj)

    obj = asyncio.run(svc.maak_aan(session, TID, LeverancierCreate(naam="Acme BV", plaats="Tiel")))
    assert obj.naam == "Acme BV"
    assert str(obj.tenant_id) == TID
    session.commit.assert_awaited_once()


def test_haal_op_niet_gevonden():
    from services import leverancier_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    resultaat = MagicMock()
    resultaat.scalar_one_or_none.return_value = None
    session.execute.return_value = resultaat

    with pytest.raises(NietGevonden):
        asyncio.run(svc.haal_op(session, uuid.uuid4(), uuid.uuid4()))


def test_verwijder_met_contracten_geeft_in_gebruik(monkeypatch):
    from services import leverancier_service as svc
    from services.errors import RegistratieConflict

    async def _haal(session, tenant_id, lev_id):
        return MagicMock()

    monkeypatch.setattr(svc, "haal_op", _haal)
    session = AsyncMock()
    telling = MagicMock()
    telling.scalar_one.return_value = 2  # heeft contracten
    session.execute.return_value = telling

    with pytest.raises(RegistratieConflict) as exc:
        asyncio.run(svc.verwijder(session, TID, uuid.uuid4()))
    assert exc.value.code == "IN_GEBRUIK"
    session.delete.assert_not_called()
