"""Unit-tests — Gebruikersgroep-schemas (P5-vervolg)."""
import uuid

import pytest
from pydantic import ValidationError


def _basis() -> dict:
    # ADR-038 — organisatie is verplicht; `_basis()` levert alleen `component_id` (tests vullen
    # `organisatie_id` waar een geldige Create nodig is).
    return {"component_id": str(uuid.uuid4())}


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


def test_create_organisatie_verplicht():
    # ADR-038 — zonder organisatie is ongeldig (verplicht veld).
    from schemas.gebruikersgroep import GebruikersgroepCreate

    with pytest.raises(ValidationError):
        GebruikersgroepCreate(**_basis())


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

    assert GebruikersgroepCreate(**_basis(), organisatie_id=uuid.uuid4(), aantal_gebruikers=0).aantal_gebruikers == 0


def test_create_geen_serverbeheerde_velden():
    from schemas.gebruikersgroep import GebruikersgroepCreate

    for veld in ("id", "tenant_id", "created_at", "updated_at"):
        assert veld not in GebruikersgroepCreate.model_fields


def test_update_geen_component_id():
    from schemas.gebruikersgroep import GebruikersgroepUpdate

    assert "component_id" not in GebruikersgroepUpdate.model_fields  # immutabel


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
    assert "component_id" in GebruikersgroepRead.model_fields


# ── ADR-055 open punt 1 — de contractnaam op één plek houden ───────────────────────────────────

def _contractnamen() -> dict[str, set[str]]:
    """De naam waarmee de gebruikersgroep aan zijn component hangt, op de DRIE plekken die samen
    het contract vormen: het Create-schema, het Read-schema en de lijst-filter op de route."""
    import inspect

    from routes import gebruikersgroep as route
    from schemas.gebruikersgroep import GebruikersgroepCreate, GebruikersgroepRead

    kandidaten = {"applicatie_id", "component_id"}
    return {
        "create": kandidaten & set(GebruikersgroepCreate.model_fields),
        "read": kandidaten & set(GebruikersgroepRead.model_fields),
        "route-filter": kandidaten & set(inspect.signature(route.lijst_gebruikersgroepen).parameters),
    }


def test_contractnaam_is_overal_dezelfde_en_zegt_wat_hij_draagt():
    """Een half doorgevoerde hernoeming levert een gebroken scherm op: de frontend stuurt de ene
    naam, de backend verwacht de andere. Deze toets houdt de drie plekken bij elkaar.

    En hij legt de naam zélf vast: het veld draagt sinds ADR-055 het id van ELK werk-ondersteunend
    componenttype (fileshare, saas_dienst, client_software), niet alleen van een applicatie. Een
    contractnaam die iets anders belooft dan hij draagt, kost de volgende lezer een verkeerde
    aanname — en die schrijft er code op."""
    namen = _contractnamen()
    for plek, gevonden in namen.items():
        assert len(gevonden) == 1, f"{plek}: verwacht precies één contractnaam, gevonden {gevonden or '{}'}"
    uniek = set().union(*namen.values())
    assert len(uniek) == 1, f"de drie plekken lopen uiteen — half hernoemd? {namen}"
    assert uniek == {"component_id"}, (
        f"het veld draagt een component-id van elk werk-ondersteunend type; naam is {uniek}"
    )
