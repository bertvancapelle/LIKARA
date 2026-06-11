"""Tests — CD044 §0 responsuitbreidingen (deelcontracten-dekking, lifecycle, datums)."""
import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


def _all(rows):
    r = MagicMock()
    r.all.return_value = rows
    return r


# ── §0c — deelcontracten met gelabelde dekking ──────────────────────────────────

def test_deelcontracten_bevat_gelabelde_dekking_incl_inactief(monkeypatch):
    from models.models import ContractType
    from services import contract_service as svc
    from services import contractconfig_catalog as catalog

    async def _haal(s, t, c):
        return MagicMock()

    async def _labels(s, dim):
        return {"hosting": ("Hosting", True), "oud_model": ("Oud model", False)}

    monkeypatch.setattr(svc, "haal_op", _haal)
    monkeypatch.setattr(catalog, "labels", _labels)

    deel_id = uuid4()
    deel = SimpleNamespace(
        id=deel_id, contractnaam="Deel A", contracttype=ContractType.deelcontract,
        begindatum=None, einddatum=None, vernieuwingsdatum=None,
    )
    session = AsyncMock()
    session.execute.side_effect = [
        _all([deel]),  # deelcontracten
        _all([SimpleNamespace(contract_id=deel_id, optie_sleutel="hosting"),
              SimpleNamespace(contract_id=deel_id, optie_sleutel="oud_model")]),  # dekking-tags
    ]
    out = asyncio.run(svc.deelcontracten(session, "11111111-1111-1111-1111-111111111111", "m1"))
    assert len(out) == 1
    dek = {o["optie_sleutel"]: o for o in out[0]["dekking"]}
    assert dek["hosting"]["label"] == "Hosting" and dek["hosting"]["actief"] is True
    assert dek["oud_model"]["label"] == "Oud model" and dek["oud_model"]["actief"] is False  # gedeactiveerd, resolvet


def test_deelcontractitem_heeft_dekking_maar_contractlijstitem_niet():
    from schemas.contract import ContractLijstItem, DeelcontractItem

    assert "dekking" in DeelcontractItem.model_fields
    assert "dekking" not in ContractLijstItem.model_fields  # gedeelde lijst onaangeroerd


# ── §0a — contract→applicaties met lifecycle_status ─────────────────────────────

def test_contract_applicaties_bevat_lifecycle(monkeypatch):
    from models.models import LifecycleStatus
    from services import contract_service as svc
    from services import contractconfig_catalog as catalog

    async def _haal(s, t, c):
        return MagicMock()

    async def _labels(s, dim):
        return {"valt_onder": ("Valt onder", True)}

    monkeypatch.setattr(svc, "haal_op", _haal)
    monkeypatch.setattr(catalog, "labels", _labels)

    row = SimpleNamespace(
        koppeling_id=uuid4(), applicatie_id=uuid4(), applicatie_naam="App",
        lifecycle_status=LifecycleStatus.geblokkeerd, relatie_rol="valt_onder",
    )
    session = AsyncMock()
    session.execute.return_value = _all([row])
    out = asyncio.run(svc.applicaties(session, "11111111-1111-1111-1111-111111111111", "c1"))
    assert out[0]["lifecycle_status"] == LifecycleStatus.geblokkeerd
    assert out[0]["relatie_rol_label"] == "Valt onder"

    from schemas.applicatie_contract import ApplicatieVoorContract
    assert "lifecycle_status" in ApplicatieVoorContract.model_fields


# ── §0b — app→contracten met begin-/einddatum ──────────────────────────────────

def test_app_contracten_bevat_datums(monkeypatch):
    from models.models import ContractType
    from services import applicatie_contract_service as svc
    from services import applicatie_service
    from services import contractconfig_catalog as catalog

    async def _ok(*a, **k):
        return MagicMock()

    async def _labels(s, dim):
        return {"valt_onder": ("Valt onder", True)}

    monkeypatch.setattr(applicatie_service, "haal_op", _ok)
    monkeypatch.setattr(catalog, "labels", _labels)

    row = SimpleNamespace(
        koppeling_id=uuid4(), contract_id=uuid4(), contractnaam="C",
        contracttype=ContractType.los_contract, leverancier_id=uuid4(),
        leverancier_naam="Lev", begindatum=date(2026, 1, 1), einddatum=None,
        relatie_rol="valt_onder",
    )
    session = AsyncMock()
    session.execute.return_value = _all([row])
    out = asyncio.run(svc.contracten_van_applicatie(session, "11111111-1111-1111-1111-111111111111", "a1"))
    assert out[0]["begindatum"] == date(2026, 1, 1)
    assert out[0]["einddatum"] is None

    from schemas.applicatie_contract import ContractVoorApplicatie
    assert {"begindatum", "einddatum"} <= set(ContractVoorApplicatie.model_fields)
