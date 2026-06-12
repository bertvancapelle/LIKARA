"""Pydantic v2-schemas voor de entiteit Checklistscore (ADR-009/013).

`score` is in Create **verplicht** (besluit Bert / ADR-013): een rij betekent
"gescoord". `applicatie_id` + `vraag_code` zitten in Create maar zijn immutabel
(niet in Update). `score` is bewerkbaar maar mag niet op null. Validatie-helpers
worden hergebruikt uit `schemas.applicatie`.
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from models.models import ChecklistScore
from schemas.applicatie import _optionele_tekst

_VERPLICHTE_VELDEN = frozenset({"score"})

# Toegestane envelope-sleutels van `antwoord_waarde` (ADR-019). De *structurele*
# validatie (vorm/typen) gebeurt hier (Pydantic → 422 native); de *semantische*
# validatie (past het type bij de vraag, is de optie actief) zit in de service
# (vereist de catalogus → `OngeldigAntwoord`, 422-envelope).
_ANTWOORD_SLEUTELS = frozenset({"optie", "opties", "getal"})


def _valideer_antwoord_envelope(v: dict | None) -> dict | None:
    """Structurele validatie van `antwoord_waarde`: exact één van
    `optie` (str) / `opties` (list[str], uniek) / `getal` (int ≥ 1)."""
    if v is None:
        return None
    if not isinstance(v, dict):
        raise ValueError("antwoord_waarde moet een object zijn")
    sleutels = set(v.keys())
    if len(sleutels) != 1 or not sleutels <= _ANTWOORD_SLEUTELS:
        raise ValueError("antwoord_waarde moet exact één van 'optie'/'opties'/'getal' bevatten")
    if "optie" in v:
        if not isinstance(v["optie"], str) or not v["optie"].strip():
            raise ValueError("'optie' moet een niet-lege optiesleutel zijn")
    elif "opties" in v:
        waarde = v["opties"]
        if not isinstance(waarde, list) or not all(
            isinstance(x, str) and x.strip() for x in waarde
        ):
            raise ValueError("'opties' moet een lijst optiesleutels zijn")
        if len(waarde) != len(set(waarde)):
            raise ValueError("'opties' mag geen dubbele sleutels bevatten")
    else:  # getal
        waarde = v["getal"]
        # bool is een subklasse van int — expliciet uitsluiten.
        if isinstance(waarde, bool) or not isinstance(waarde, int) or waarde < 1:
            raise ValueError("'getal' moet een geheel getal >= 1 zijn")
    return v


class ChecklistscoreSorteerveld(str, Enum):
    """Allowlist van sorteerbare lijst-velden (ADR-017 B2, retrofit CD020).

    API-only retrofit (zie route-docstring): de frontend-sectie is bewust een
    vraag-gedreven invulformulier, geen sorteerbare tabel. NOT NULL:
    `checklistvraag_id`, `created_at`. Nullable (NULLS LAST, ADR-017 B5): `score`,
    `eigenaar`. De service mapt deze namen 1-op-1 op een kolom; een test borgt de
    synchroniteit.
    """

    created_at = "created_at"
    checklistvraag_id = "checklistvraag_id"
    score = "score"
    eigenaar = "eigenaar"


class ChecklistscoreCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: uuid.UUID
    checklistvraag_id: uuid.UUID
    score: ChecklistScore  # verplicht (geen default)
    bevinding: str | None = None
    eigenaar: str | None = None
    actie: str | None = None
    antwoord_waarde: dict | None = None

    @field_validator("bevinding", "actie")
    @classmethod
    def _v_lange_tekst(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)

    @field_validator("eigenaar")
    @classmethod
    def _v_eigenaar(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @field_validator("antwoord_waarde")
    @classmethod
    def _v_antwoord(cls, v: dict | None) -> dict | None:
        return _valideer_antwoord_envelope(v)


class ChecklistscoreUpdate(BaseModel):
    """Partiële update; `component_id`/`checklistvraag_id` immutabel ⇒ niet aanwezig.

    `score` mag worden gewijzigd maar niet op null gezet.
    """

    model_config = ConfigDict(extra="forbid")

    score: ChecklistScore | None = None
    bevinding: str | None = None
    eigenaar: str | None = None
    actie: str | None = None
    # Mag wél op null (antwoord wissen) — niet in _VERPLICHTE_VELDEN.
    antwoord_waarde: dict | None = None

    @field_validator("bevinding", "actie")
    @classmethod
    def _v_lange_tekst(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)

    @field_validator("eigenaar")
    @classmethod
    def _v_eigenaar(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @field_validator("antwoord_waarde")
    @classmethod
    def _v_antwoord(cls, v: dict | None) -> dict | None:
        return _valideer_antwoord_envelope(v)

    @model_validator(mode="after")
    def _verbied_null_op_verplicht(self) -> "ChecklistscoreUpdate":
        for veld in _VERPLICHTE_VELDEN:
            if veld in self.model_fields_set and getattr(self, veld) is None:
                raise ValueError(f"{veld} mag niet op null worden gezet")
        return self


class ChecklistscoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    component_id: uuid.UUID
    checklistvraag_id: uuid.UUID
    # Kolom is nullable in de DB; defensief getypeerd hoewel Create score afdwingt.
    score: ChecklistScore | None
    bevinding: str | None
    eigenaar: str | None
    actie: str | None
    antwoord_waarde: dict | None
    created_at: datetime
    updated_at: datetime


class ChecklistscorePagina(BaseModel):
    items: list[ChecklistscoreRead]
    volgende_cursor: str | None = None


class ChecklistscoreOpties(BaseModel):
    """Read-only keuzewaarden per enumveld (voor de frontend-dropdowns)."""

    score: list[str]
