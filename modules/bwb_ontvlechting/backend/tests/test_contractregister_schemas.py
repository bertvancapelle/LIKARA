"""Unit-tests — ADR-020 fase B schema-validatie (Pydantic v2, DB-vrij)."""
import uuid

import pytest
from pydantic import ValidationError


def test_leverancier_create_naam_verplicht_en_extra_forbid():
    # ADR-024 slice 2a: leverancier-/externe-partij-schema gegeneraliseerd naar partij (aard verplicht).
    from schemas.partij import PartijCreate

    lev = PartijCreate(aard="externe_partij", naam="  Acme BV  ", postcode="1234AB")
    assert lev.naam == "Acme BV"  # gestript
    assert lev.plaats is None

    with pytest.raises(ValidationError):
        PartijCreate(aard="externe_partij", naam="   ")  # leeg na strip
    with pytest.raises(ValidationError):
        PartijCreate(naam="X")  # aard verplicht
    with pytest.raises(ValidationError):
        PartijCreate(aard="externe_partij", naam="X", onbekend="y")  # extra='forbid'
    with pytest.raises(ValidationError):
        PartijCreate(aard="externe_partij", naam="X", postcode="X" * 21)  # max_length 20


def test_leverancier_update_verbiedt_null_op_naam():
    from schemas.partij import PartijUpdate as LeverancierUpdate

    assert LeverancierUpdate(plaats="Tiel").naam is None  # weglaten mag
    with pytest.raises(ValidationError):
        LeverancierUpdate(naam=None)  # expliciet null op verplicht veld


def test_contract_create_verplichte_velden_en_dedup():
    from schemas.contract import ContractCreate

    c = ContractCreate(
        leverancier_id=uuid.uuid4(),
        contracttype="los_contract",
        contractnaam="Onderhoud 2026",
        dekking=["hosting", "hosting", "onderhoud_support"],
        kostenmodel=[],
    )
    assert c.dekking == ["hosting", "onderhoud_support"]  # gededupliceerd, volgorde-stabiel
    assert c.mantelcontract_id is None

    with pytest.raises(ValidationError):
        ContractCreate(leverancier_id=uuid.uuid4(), contracttype="onzin", contractnaam="X")
    with pytest.raises(ValidationError):
        ContractCreate(contracttype="los_contract", contractnaam="X")  # leverancier_id mist


def test_contract_update_null_op_verplicht_en_optionele_lijst():
    from schemas.contract import ContractUpdate

    u = ContractUpdate(omschrijving="x")
    assert u.dekking is None and "dekking" not in u.model_fields_set  # weggelaten = ongewijzigd
    assert ContractUpdate(dekking=[]).dekking == []  # expliciet leegmaken mag
    with pytest.raises(ValidationError):
        ContractUpdate(contractnaam=None)


def test_applicatie_contract_create_rol_verplicht():
    from schemas.applicatie_contract import (
        ApplicatieContractCreate,
        ApplicatieContractUpdate,
    )

    k = ApplicatieContractCreate(
        applicatie_id=uuid.uuid4(), contract_id=uuid.uuid4(), relatie_rol="valt_onder"
    )
    assert k.relatie_rol == "valt_onder"
    with pytest.raises(ValidationError):
        ApplicatieContractCreate(applicatie_id=uuid.uuid4(), contract_id=uuid.uuid4(), relatie_rol="  ")
    with pytest.raises(ValidationError):
        ApplicatieContractUpdate(relatie_rol="x", extra="nee")  # extra='forbid'
