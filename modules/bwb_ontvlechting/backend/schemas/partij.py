"""Pydantic v2-schemas voor het partij-beheer (ADR-024 slice 2a; vervangt externe_partij).

Eén beheerpad voor alle partij-aarden (externe_partij / organisatie / organisatie_eenheid /
persoon). Gescheiden Create/Update/Read, `extra='forbid'`. `email`/`telefoon` zijn gewone `str`
(geen formaatvalidatie). `soort` is **optioneel** (platform-catalogus `partijsoort_optie`,
app-side gevalideerd in de service). `aard` is **verplicht bij aanmaken** en daarna **niet
wijzigbaar** (ontbreekt in Update). `naam` is het enige verplichte inhoudsveld; de overige
contactvelden zijn optioneel en gedeeld over alle aarden (geen aard-eigen velden).
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from models.models import PartijAard
from schemas.applicatie import _optionele_tekst, _verplichte_tekst


class PartijSorteerveld(str, Enum):
    """Allowlist van sorteerbare velden (ADR-017). `plaats` is nullable (v2n-NULLS-LAST)."""

    created_at = "created_at"
    naam = "naam"
    plaats = "plaats"


_VERPLICHTE_VELDEN = frozenset({"naam"})


class PartijCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aard: PartijAard  # verplicht; daarna niet wijzigbaar (ontbreekt in Update)
    naam: str
    straat_huisnummer: str | None = None
    postcode: str | None = None
    plaats: str | None = None
    contactpersoon: str | None = None
    telefoon: str | None = None
    mobiel: str | None = None
    email: str | None = None
    omschrijving: str | None = None
    soort: str | None = None  # platform-catalogus partijsoort_optie; service valideert

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

    @field_validator("soort")
    @classmethod
    def _v_soort(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 60)

    @field_validator("omschrijving")
    @classmethod
    def _v_omschrijving(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)


class PartijUpdate(BaseModel):
    """Partiële update (PATCH). `naam` mag weggelaten, maar niet op null gezet. `aard` ontbreekt
    bewust — de aard ligt vast na aanmaken (een persoon blijft een persoon)."""

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
    soort: str | None = None

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

    @field_validator("soort")
    @classmethod
    def _v_soort(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 60)

    @field_validator("omschrijving")
    @classmethod
    def _v_omschrijving(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)

    @model_validator(mode="after")
    def _verbied_null_op_verplicht(self) -> "PartijUpdate":
        for veld in _VERPLICHTE_VELDEN:
            if veld in self.model_fields_set and getattr(self, veld) is None:
                raise ValueError(f"{veld} mag niet op null worden gezet")
        return self


class PartijRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    aard: str
    naam: str
    straat_huisnummer: str | None
    postcode: str | None
    plaats: str | None
    contactpersoon: str | None
    telefoon: str | None
    mobiel: str | None
    email: str | None
    omschrijving: str | None
    soort: str | None
    created_at: datetime
    updated_at: datetime


class PartijPagina(BaseModel):
    items: list[PartijRead]
    volgende_cursor: str | None = None
