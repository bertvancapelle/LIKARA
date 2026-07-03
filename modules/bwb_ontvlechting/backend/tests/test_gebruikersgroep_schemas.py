"""Unit-tests — Gebruikersgroep-schemas (P5-vervolg)."""
import uuid

import pytest
from pydantic import ValidationError


def _basis() -> dict:
    # UX-B6-a — organisatie is een optionele verwijzing (organisatie_id); leeg laten mag.
    return {"applicatie_id": str(uuid.uuid4())}


def test_create_happy_path():
    from schemas.gebruikersgroep import GebruikersgroepCreate

    org_id = uuid.uuid4()
    afd_id = uuid.uuid4()
    m = GebruikersgroepCreate(**_basis(), organisatie_id=org_id, afdeling_id=afd_id, aantal_gebruikers=12)
    assert m.organisatie_id == org_id
    assert m.afdeling_id == afd_id
    assert m.aantal_gebruikers == 12


def test_create_extra_forbid():
    from schemas.gebruikersgroep import GebruikersgroepCreate

    with pytest.raises(ValidationError):
        GebruikersgroepCreate(**_basis(), onbekend="x")


def test_create_organisatie_optioneel():
    # UX-B6-a — zonder organisatie is geldig (optioneel veld).
    from schemas.gebruikersgroep import GebruikersgroepCreate

    assert GebruikersgroepCreate(**_basis()).organisatie_id is None


def test_create_organisatie_geen_uuid_geweigerd():
    from schemas.gebruikersgroep import GebruikersgroepCreate

    d = _basis()
    d["organisatie_id"] = "geen-uuid"
    with pytest.raises(ValidationError):
        GebruikersgroepCreate(**d)


def test_create_aantal_negatief_geweigerd():
    from schemas.gebruikersgroep import GebruikersgroepCreate

    with pytest.raises(ValidationError):
        GebruikersgroepCreate(**_basis(), aantal_gebruikers=-1)


def test_create_aantal_nul_toegestaan():
    from schemas.gebruikersgroep import GebruikersgroepCreate

    assert GebruikersgroepCreate(**_basis(), aantal_gebruikers=0).aantal_gebruikers == 0


def test_create_geen_serverbeheerde_velden():
    from schemas.gebruikersgroep import GebruikersgroepCreate

    for veld in ("id", "tenant_id", "created_at", "updated_at"):
        assert veld not in GebruikersgroepCreate.model_fields


def test_update_geen_applicatie_id():
    from schemas.gebruikersgroep import GebruikersgroepUpdate

    assert "applicatie_id" not in GebruikersgroepUpdate.model_fields  # immutabel


def test_update_organisatie_wissen_toegestaan():
    # UX-B6-a — organisatie op null zetten mag (optioneel; "onbekend").
    from schemas.gebruikersgroep import GebruikersgroepUpdate

    m = GebruikersgroepUpdate(organisatie_id=None)
    assert "organisatie_id" in m.model_fields_set and m.organisatie_id is None


def test_update_aantal_negatief_geweigerd():
    from schemas.gebruikersgroep import GebruikersgroepUpdate

    with pytest.raises(ValidationError):
        GebruikersgroepUpdate(aantal_gebruikers=-5)


def test_update_afdeling_wissen_toegestaan():
    from schemas.gebruikersgroep import GebruikersgroepUpdate

    m = GebruikersgroepUpdate(afdeling_id=None)
    assert "afdeling_id" in m.model_fields_set and m.afdeling_id is None


def test_read_geen_tenant_id():
    from schemas.gebruikersgroep import GebruikersgroepRead

    assert "tenant_id" not in GebruikersgroepRead.model_fields
    assert "applicatie_id" in GebruikersgroepRead.model_fields
