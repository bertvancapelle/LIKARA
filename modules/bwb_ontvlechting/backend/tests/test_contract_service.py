"""Unit-tests — Contract service-laag (ADR-020 fase B): invarianten I1–I4,
sorteer-allowlist en cursor-mismatch. DB gemockt/monkeypatched."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

TID = "11111111-1111-1111-1111-111111111111"


def _mantel(contracttype, leverancier_id):
    m = MagicMock()
    m.contracttype = contracttype
    m.leverancier_id = leverancier_id
    return m


def test_sorteer_allowlist_synchroon_met_schema():
    from schemas.contract import ContractSorteerveld
    from services import contract_service as svc

    velden = {e.value for e in ContractSorteerveld}
    assert velden == set(svc._SORTEERBARE_KOLOMMEN)
    assert velden == set(svc._WAARDE_PARSERS)


def test_i1_mantel_moet_mantelcontract_zijn(monkeypatch):
    from models.models import ContractType
    from services import contract_service as svc
    from services.errors import OngeldigeRegistratie

    lev = uuid.uuid4()

    async def _haal(session, tenant_id, cid):
        return _mantel(ContractType.deelcontract, lev)  # geen mantelcontract

    monkeypatch.setattr(svc, "haal_op", _haal)
    with pytest.raises(OngeldigeRegistratie) as e:
        asyncio.run(svc._valideer_consistentie(
            AsyncMock(), TID, contracttype=ContractType.deelcontract,
            mantelcontract_id=uuid.uuid4(), leverancier_id=lev))
    assert e.value.code == "ONGELDIGE_MANTEL"


def test_i2_leverancier_mismatch(monkeypatch):
    from models.models import ContractType
    from services import contract_service as svc
    from services.errors import OngeldigeRegistratie

    async def _haal(session, tenant_id, cid):
        return _mantel(ContractType.mantelcontract, uuid.uuid4())  # andere leverancier

    monkeypatch.setattr(svc, "haal_op", _haal)
    with pytest.raises(OngeldigeRegistratie) as e:
        asyncio.run(svc._valideer_consistentie(
            AsyncMock(), TID, contracttype=ContractType.deelcontract,
            mantelcontract_id=uuid.uuid4(), leverancier_id=uuid.uuid4()))
    assert e.value.code == "LEVERANCIER_MISMATCH"


def test_geldig_deelcontract_passeert(monkeypatch):
    from models.models import ContractType
    from services import contract_service as svc

    lev = uuid.uuid4()

    async def _haal(session, tenant_id, cid):
        return _mantel(ContractType.mantelcontract, lev)

    monkeypatch.setattr(svc, "haal_op", _haal)
    # geen exception
    asyncio.run(svc._valideer_consistentie(
        AsyncMock(), TID, contracttype=ContractType.deelcontract,
        mantelcontract_id=uuid.uuid4(), leverancier_id=lev))


def test_niet_deelcontract_met_mantel_geweigerd():
    from models.models import ContractType
    from services import contract_service as svc
    from services.errors import OngeldigeRegistratie

    with pytest.raises(OngeldigeRegistratie) as e:
        asyncio.run(svc._valideer_consistentie(
            AsyncMock(), TID, contracttype=ContractType.los_contract,
            mantelcontract_id=uuid.uuid4(), leverancier_id=uuid.uuid4()))
    assert e.value.code == "ONGELDIGE_MANTEL"


def test_deelcontract_zonder_mantel_geweigerd():
    from models.models import ContractType
    from services import contract_service as svc
    from services.errors import OngeldigeRegistratie

    with pytest.raises(OngeldigeRegistratie) as e:
        asyncio.run(svc._valideer_consistentie(
            AsyncMock(), TID, contracttype=ContractType.deelcontract,
            mantelcontract_id=None, leverancier_id=uuid.uuid4()))
    assert e.value.code == "ONGELDIGE_MANTEL"


def _bestaande_mantel():
    from models.models import ContractType
    obj = MagicMock()
    obj.contracttype = ContractType.mantelcontract
    obj.leverancier_id = uuid.uuid4()
    obj.mantelcontract_id = None
    return obj


def test_i3_type_wissel_mantel_met_deel_geweigerd(monkeypatch):
    from services import contract_service as svc
    from schemas.contract import ContractUpdate
    from services.errors import OngeldigeRegistratie

    obj = _bestaande_mantel()

    async def _haal(session, tenant_id, cid):
        return obj

    async def _heeft_deel(session, tid, cid):
        return True

    monkeypatch.setattr(svc, "haal_op", _haal)
    monkeypatch.setattr(svc, "_heeft_deelcontracten", _heeft_deel)
    with pytest.raises(OngeldigeRegistratie) as e:
        asyncio.run(svc.werk_bij(AsyncMock(), TID, uuid.uuid4(), ContractUpdate(contracttype="los_contract")))
    assert e.value.code == "MANTEL_IN_GEBRUIK"


def test_i3_leverancier_wissel_mantel_met_deel_geweigerd(monkeypatch):
    from services import contract_service as svc
    from schemas.contract import ContractUpdate
    from services.errors import OngeldigeRegistratie

    obj = _bestaande_mantel()

    async def _haal(session, tenant_id, cid):
        return obj

    async def _heeft_deel(session, tid, cid):
        return True

    monkeypatch.setattr(svc, "haal_op", _haal)
    monkeypatch.setattr(svc, "_heeft_deelcontracten", _heeft_deel)
    with pytest.raises(OngeldigeRegistratie) as e:
        asyncio.run(svc.werk_bij(AsyncMock(), TID, uuid.uuid4(), ContractUpdate(leverancier_id=uuid.uuid4())))
    assert e.value.code == "MANTEL_IN_GEBRUIK"


def test_i4_verwijder_mantel_met_deel_geeft_in_gebruik(monkeypatch):
    from services import contract_service as svc
    from services.errors import RegistratieConflict

    async def _haal(session, tenant_id, cid):
        return MagicMock()

    async def _deel(session, tid, cid):
        return True

    monkeypatch.setattr(svc, "haal_op", _haal)
    monkeypatch.setattr(svc, "_heeft_deelcontracten", _deel)
    with pytest.raises(RegistratieConflict) as e:
        asyncio.run(svc.verwijder(AsyncMock(), TID, uuid.uuid4()))
    assert e.value.code == "IN_GEBRUIK"


def test_i4_verwijder_contract_met_koppelingen_geeft_in_gebruik(monkeypatch):
    from services import contract_service as svc
    from services.errors import RegistratieConflict

    async def _haal(session, tenant_id, cid):
        return MagicMock()

    async def _geen_deel(session, tid, cid):
        return False

    async def _kopp(session, tid, cid):
        return True

    monkeypatch.setattr(svc, "haal_op", _haal)
    monkeypatch.setattr(svc, "_heeft_deelcontracten", _geen_deel)
    monkeypatch.setattr(svc, "_heeft_koppelingen", _kopp)
    with pytest.raises(RegistratieConflict) as e:
        asyncio.run(svc.verwijder(AsyncMock(), TID, uuid.uuid4()))
    assert e.value.code == "IN_GEBRUIK"


def test_lijst_cursor_mismatch_geeft_valueerror():
    from services import contract_service as svc
    from services.pagination import encode_sort_cursor_nullable

    cursor = encode_sort_cursor_nullable(sort="created_at", order="asc", waarde=None, id=uuid.uuid4())
    with pytest.raises(ValueError):
        asyncio.run(svc.lijst(AsyncMock(), TID, after=cursor, sort="contractnaam", order="asc"))


def test_maak_aan_roept_validaties_en_commit(monkeypatch):
    from services import contract_service as svc
    from services import contractconfig_catalog as catalog
    from schemas.contract import ContractCreate

    sporen = []

    # ADR-024 slice 1: de leverancier-verwijzing wordt nu als externe partij gevalideerd.
    async def _lev(session, tid, pid):
        sporen.append("lev")

    async def _cons(*a, **k):
        sporen.append("cons")

    async def _val(session, dim, sleutels):
        sporen.append("val")

    async def _zet(session, tid, cid, veld, sleutels):
        sporen.append(("zet", veld))

    async def _detail(session, tenant_id, cid):
        return {"id": cid, "ok": True}

    monkeypatch.setattr(svc, "_valideer_externe_partij", _lev)
    monkeypatch.setattr(svc, "_valideer_consistentie", _cons)
    monkeypatch.setattr(catalog, "valideer_sleutels", _val)
    monkeypatch.setattr(svc, "_zet_tags", _zet)
    monkeypatch.setattr(svc, "lees_detail", _detail)

    session = AsyncMock()
    session.add = lambda obj: None
    data = ContractCreate(
        leverancier_id=uuid.uuid4(), contracttype="los_contract", contractnaam="X",
        dekking=["hosting"], kostenmodel=[],
    )
    res = asyncio.run(svc.maak_aan(session, TID, data))
    assert res["ok"] is True
    assert sporen.count("lev") == 1 and sporen.count("cons") == 1
    assert ("zet", "dekking") in sporen and ("zet", "kostenmodel") in sporen
    # ADR-023 B-mig-1: element-identiteit eerst (flush voor elem.id), dan contract (flush voor obj.id).
    assert session.flush.await_count == 2
    session.commit.assert_awaited_once()
