"""Unit-tests — Applicatie-schemas (P5).

Schema-validatie: happy path, `extra='forbid'`, enum-grenzen, lengte-/leeg-
validatie, PATCH-semantiek en uitsluiting van server-beheerde velden.
Geen DB nodig.
"""
import pytest
from pydantic import ValidationError


def _basis() -> dict:
    return dict(
        naam="Zaaksysteem",
        hostingmodel="saas",
        eigenaar_organisatie="Gemeente Veldendam",
        migratiepad="herbouw",
        complexiteit="midden",
        prioriteit="hoog",
    )


# ── Create ──────────────────────────────────────────────────────────────────

def test_create_happy_path():
    from schemas.applicatie import ApplicatieCreate

    m = ApplicatieCreate(**_basis())
    assert m.naam == "Zaaksysteem"
    assert m.beschrijving is None
    assert m.hostingmodel.value == "saas"


def test_create_extra_forbid():
    from schemas.applicatie import ApplicatieCreate

    with pytest.raises(ValidationError):
        ApplicatieCreate(**_basis(), onbekend_veld="x")


def test_create_ongeldige_enum_geweigerd():
    from schemas.applicatie import ApplicatieCreate

    d = _basis()
    d["hostingmodel"] = "mainframe"  # geen geldige HostingModel-waarde
    with pytest.raises(ValidationError):
        ApplicatieCreate(**d)


def test_create_alle_geldige_hostingmodellen():
    from schemas.applicatie import ApplicatieCreate
    from models.models import HostingModel

    for hm in HostingModel:
        d = _basis()
        d["hostingmodel"] = hm.value
        assert ApplicatieCreate(**d).hostingmodel == hm


def test_create_lege_naam_geweigerd():
    from schemas.applicatie import ApplicatieCreate

    d = _basis()
    d["naam"] = "   "
    with pytest.raises(ValidationError):
        ApplicatieCreate(**d)


def test_create_naam_wordt_gestript():
    from schemas.applicatie import ApplicatieCreate

    d = _basis()
    d["naam"] = "  Zaaksysteem  "
    assert ApplicatieCreate(**d).naam == "Zaaksysteem"


def test_create_eigenaar_organisatie_te_lang_geweigerd():
    from schemas.applicatie import ApplicatieCreate

    d = _basis()
    d["eigenaar_organisatie"] = "x" * 121  # max 120
    with pytest.raises(ValidationError):
        ApplicatieCreate(**d)


def test_create_eigenaar_organisatie_is_vrije_tekst():
    from schemas.applicatie import ApplicatieCreate

    d = _basis()
    d["eigenaar_organisatie"] = "Willekeurige Dienst BV"
    assert ApplicatieCreate(**d).eigenaar_organisatie == "Willekeurige Dienst BV"


def test_create_optionele_lege_tekst_wordt_none():
    from schemas.applicatie import ApplicatieCreate

    d = _basis()
    d["leverancier"] = "   "
    assert ApplicatieCreate(**d).leverancier is None


def test_create_geen_serverbeheerde_velden():
    from schemas.applicatie import ApplicatieCreate

    for veld in ("id", "tenant_id", "created_at", "updated_at", "lifecycle_status"):
        assert veld not in ApplicatieCreate.model_fields


# ── Update (PATCH) ──────────────────────────────────────────────────────────

def test_update_partieel():
    from schemas.applicatie import ApplicatieUpdate

    m = ApplicatieUpdate(naam="Nieuwe naam")
    assert m.model_dump(exclude_unset=True) == {"naam": "Nieuwe naam"}


def test_update_leeg_is_toegestaan():
    from schemas.applicatie import ApplicatieUpdate

    assert ApplicatieUpdate().model_dump(exclude_unset=True) == {}


def test_update_extra_forbid():
    from schemas.applicatie import ApplicatieUpdate

    with pytest.raises(ValidationError):
        ApplicatieUpdate(zzz=1)


def test_update_null_op_verplicht_veld_geweigerd():
    from schemas.applicatie import ApplicatieUpdate

    with pytest.raises(ValidationError):
        ApplicatieUpdate(naam=None)


def test_update_nullable_veld_wissen_toegestaan():
    from schemas.applicatie import ApplicatieUpdate

    m = ApplicatieUpdate(leverancier=None)
    assert "leverancier" in m.model_fields_set
    assert m.leverancier is None


def test_update_geen_lifecycle_veld():
    from schemas.applicatie import ApplicatieUpdate

    assert "lifecycle_status" not in ApplicatieUpdate.model_fields


def test_update_ongeldige_enum_geweigerd():
    from schemas.applicatie import ApplicatieUpdate

    with pytest.raises(ValidationError):
        ApplicatieUpdate(complexiteit="extreem")


# ── Read ────────────────────────────────────────────────────────────────────

def test_read_exposeert_geen_tenant_id():
    from schemas.applicatie import ApplicatieRead

    assert "tenant_id" not in ApplicatieRead.model_fields


def test_read_bevat_lifecycle_en_timestamps():
    from schemas.applicatie import ApplicatieRead

    for veld in ("id", "lifecycle_status", "created_at", "updated_at"):
        assert veld in ApplicatieRead.model_fields
