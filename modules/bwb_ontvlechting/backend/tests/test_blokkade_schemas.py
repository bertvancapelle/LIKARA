"""Unit-tests — Blokkade-schemas (ADR-013). Geen Create (systeem-afgeleid)."""
import pytest
from pydantic import ValidationError


def test_geen_create_schema():
    import schemas.blokkade as b

    assert not hasattr(b, "BlokkadeCreate")


def test_update_happy_path():
    from schemas.blokkade import BlokkadeUpdate

    m = BlokkadeUpdate(status="in_behandeling", eigenaar="Team Migratie")
    assert m.status.value == "in_behandeling"


def test_update_extra_forbid():
    from schemas.blokkade import BlokkadeUpdate

    with pytest.raises(ValidationError):
        BlokkadeUpdate(onbekend="x")


def test_update_ongeldige_status():
    from schemas.blokkade import BlokkadeUpdate

    with pytest.raises(ValidationError):
        BlokkadeUpdate(status="afgewezen")


def test_update_status_null_geweigerd():
    from schemas.blokkade import BlokkadeUpdate

    with pytest.raises(ValidationError):
        BlokkadeUpdate(status=None)


def test_update_geen_opgelost_op_veld():
    from schemas.blokkade import BlokkadeUpdate

    # opgelost_op is server-beheerd (afgeleid uit status) — niet door de client.
    assert "opgelost_op" not in BlokkadeUpdate.model_fields


def test_update_toelichting_only():
    from schemas.blokkade import BlokkadeUpdate

    m = BlokkadeUpdate(toelichting="in afwachting van leverancier")
    assert m.model_dump(exclude_unset=True) == {"toelichting": "in afwachting van leverancier"}


def test_read_velden_en_geen_tenant_id():
    from schemas.blokkade import BlokkadeRead

    assert "tenant_id" not in BlokkadeRead.model_fields
    for veld in ("id", "checklistscore_id", "component_id", "status", "opgelost_op"):
        assert veld in BlokkadeRead.model_fields
