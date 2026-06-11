"""Pydantic v2-schemas voor de entiteit Leverancier (ADR-020 Besluit 1).

Gescheiden Create / Update / Read, `extra='forbid'`. Puur registratief: `email`
en `telefoon` zijn gewone `str` (GEEN `EmailStr`/formaatvalidatie — B-besluit).
`max_length`-grenzen op de API-rand spiegelen de DB-kolommen (structureel 422
native, ADR-014). Server-velden (`id`, `tenant_id`, timestamps) nooit in Create/Update;
`tenant_id` ook niet in Read.
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from schemas.applicatie import _optionele_tekst, _verplichte_tekst


class LeverancierSorteerveld(str, Enum):
    """Allowlist van sorteerbare Leverancier-velden (ADR-017). `plaats` is nullable
    (v2n-NULLS-LAST); `naam`/`created_at` zijn NOT NULL."""

    created_at = "created_at"
    naam = "naam"
    plaats = "plaats"


_VERPLICHTE_VELDEN = frozenset({"naam"})


class LeverancierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str
    straat_huisnummer: str | None = None
    postcode: str | None = None
    plaats: str | None = None
    contactpersoon: str | None = None
    telefoon: str | None = None
    mobiel: str | None = None
    email: str | None = None
    omschrijving: str | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @field_validator("postcode")
    @classmethod
    def _v_postcode(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 20)

    @field_validator("telefoon", "mobiel")
    @classmethod
    def _v_tel(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 40)

    @field_validator("straat_huisnummer", "plaats", "contactpersoon", "email")
    @classmethod
    def _v_opt_255(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @field_validator("omschrijving")
    @classmethod
    def _v_omschrijving(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)


class LeverancierUpdate(BaseModel):
    """Partiële update (PATCH). `naam` mag weggelaten, maar niet op null gezet."""

    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    straat_huisnummer: str | None = None
    postcode: str | None = None
    plaats: str | None = None
    contactpersoon: str | None = None
    telefoon: str | None = None
    mobiel: str | None = None
    email: str | None = None
    omschrijving: str | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 255)

    @field_validator("postcode")
    @classmethod
    def _v_postcode(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 20)

    @field_validator("telefoon", "mobiel")
    @classmethod
    def _v_tel(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 40)

    @field_validator("straat_huisnummer", "plaats", "contactpersoon", "email")
    @classmethod
    def _v_opt_255(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @field_validator("omschrijving")
    @classmethod
    def _v_omschrijving(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)

    @model_validator(mode="after")
    def _verbied_null_op_verplicht(self) -> "LeverancierUpdate":
        for veld in _VERPLICHTE_VELDEN:
            if veld in self.model_fields_set and getattr(self, veld) is None:
                raise ValueError(f"{veld} mag niet op null worden gezet")
        return self


class LeverancierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    naam: str
    straat_huisnummer: str | None
    postcode: str | None
    plaats: str | None
    contactpersoon: str | None
    telefoon: str | None
    mobiel: str | None
    email: str | None
    omschrijving: str | None
    created_at: datetime
    updated_at: datetime


class LeverancierPagina(BaseModel):
    items: list[LeverancierRead]
    volgende_cursor: str | None = None
