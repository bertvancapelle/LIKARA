"""Unit-tests — Checklistscore-schemas (ADR-013)."""
import uuid

import pytest
from pydantic import ValidationError


def _basis() -> dict:
    return {
        "applicatie_id": str(uuid.uuid4()),
        "vraag_code": "1.1",
        "score": "nee",
    }


def test_create_happy_path():
    from schemas.checklistscore import ChecklistscoreCreate

    m = ChecklistscoreCreate(**_basis(), bevinding="ontbreekt")
    assert m.score.value == "nee"
    assert m.vraag_code == "1.1"


def test_create_score_verplicht():
    from schemas.checklistscore import ChecklistscoreCreate

    d = _basis()
    del d["score"]
    with pytest.raises(ValidationError):
        ChecklistscoreCreate(**d)


def test_create_extra_forbid():
    from schemas.checklistscore import ChecklistscoreCreate

    with pytest.raises(ValidationError):
        ChecklistscoreCreate(**_basis(), onbekend="x")


def test_create_ongeldige_score():
    from schemas.checklistscore import ChecklistscoreCreate

    d = _basis()
    d["score"] = "misschien"
    with pytest.raises(ValidationError):
        ChecklistscoreCreate(**d)


def test_create_alle_scores():
    from models.models import ChecklistScore
    from schemas.checklistscore import ChecklistscoreCreate

    for s in ChecklistScore:
        d = _basis()
        d["score"] = s.value
        assert ChecklistscoreCreate(**d).score == s


def test_create_lege_vraag_code():
    from schemas.checklistscore import ChecklistscoreCreate

    d = _basis()
    d["vraag_code"] = "   "
    with pytest.raises(ValidationError):
        ChecklistscoreCreate(**d)


def test_create_geen_serverbeheerde_velden():
    from schemas.checklistscore import ChecklistscoreCreate

    for veld in ("id", "tenant_id", "created_at", "updated_at"):
        assert veld not in ChecklistscoreCreate.model_fields


def test_update_geen_applicatie_id_of_vraag_code():
    from schemas.checklistscore import ChecklistscoreUpdate

    assert "applicatie_id" not in ChecklistscoreUpdate.model_fields
    assert "vraag_code" not in ChecklistscoreUpdate.model_fields


def test_update_score_wijzigen_mag():
    from schemas.checklistscore import ChecklistscoreUpdate

    m = ChecklistscoreUpdate(score="ja")
    assert m.model_dump(exclude_unset=True) == {"score": "ja"}


def test_update_score_null_geweigerd():
    from schemas.checklistscore import ChecklistscoreUpdate

    with pytest.raises(ValidationError):
        ChecklistscoreUpdate(score=None)


def test_read_geen_tenant_id():
    from schemas.checklistscore import ChecklistscoreRead

    assert "tenant_id" not in ChecklistscoreRead.model_fields
    assert "vraag_code" in ChecklistscoreRead.model_fields
    assert "antwoord_waarde" in ChecklistscoreRead.model_fields


# ── ADR-019: antwoord_waarde envelope-validatie (structureel, Pydantic → 422) ──

@pytest.mark.parametrize("waarde", [
    None,
    {"optie": "saas"},
    {"opties": ["api", "middleware"]},
    {"opties": []},
    {"getal": 1},
    {"getal": 7},
])
def test_create_antwoord_waarde_geldig(waarde):
    from schemas.checklistscore import ChecklistscoreCreate

    m = ChecklistscoreCreate(**_basis(), antwoord_waarde=waarde)
    assert m.antwoord_waarde == waarde


@pytest.mark.parametrize("waarde", [
    {},                              # geen sleutel
    {"optie": "a", "getal": 1},      # meer dan één sleutel
    {"onbekend": "x"},               # onbekende sleutel
    {"optie": ""},                   # lege optie
    {"optie": 3},                    # optie geen str
    {"opties": "api"},               # opties geen lijst
    {"opties": ["api", "api"]},      # dubbele sleutels
    {"opties": ["api", 2]},          # niet-str element
    {"getal": 0},                    # < 1
    {"getal": -1},                   # < 1
    {"getal": 1.5},                  # geen int
    {"getal": True},                 # bool uitgesloten
])
def test_create_antwoord_waarde_ongeldig(waarde):
    from schemas.checklistscore import ChecklistscoreCreate

    with pytest.raises(ValidationError):
        ChecklistscoreCreate(**_basis(), antwoord_waarde=waarde)


def test_update_antwoord_waarde_mag_null():
    from schemas.checklistscore import ChecklistscoreUpdate

    m = ChecklistscoreUpdate(antwoord_waarde=None)
    assert "antwoord_waarde" in m.model_fields_set
    assert m.model_dump(exclude_unset=True) == {"antwoord_waarde": None}
