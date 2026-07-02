"""Pydantic v2-schemas voor de entiteit Datatype (P5-vervolg, ADR-009).

Zelfde patroon als `schemas/applicatie.py`, zónder lifecycle. `applicatie_id`
zit wél in Create (ouder bij aanmaken) maar NIET in Update (immutabel — geen
reparenting). Validatie-helpers worden hergebruikt uit `schemas.applicatie`.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from enum import Enum

from models.models import DatatypeCategorie
from schemas._validators import _optionele_tekst

_VERPLICHTE_VELDEN = frozenset({"categorie"})


class DatatypeSorteerveld(str, Enum):
    """Allowlist van sorteerbare lijst-velden (ADR-017 B2, retrofit CD020).

    Dekt de getoonde kolommen. NOT NULL: `categorie`, `created_at`. Nullable
    (NULLS LAST, ADR-017 B5): `omschrijving`, `omvang_indicatie`. De service mapt
    deze namen 1-op-1 op een kolom; een test borgt de synchroniteit.
    """

    created_at = "created_at"
    categorie = "categorie"
    omschrijving = "omschrijving"
    omvang_indicatie = "omvang_indicatie"


class DatatypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applicatie_id: uuid.UUID
    categorie: DatatypeCategorie
    omschrijving: str | None = None
    omvang_indicatie: str | None = None

    @field_validator("omschrijving")
    @classmethod
    def _v_omschrijving(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)

    @field_validator("omvang_indicatie")
    @classmethod
    def _v_omvang(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)


class DatatypeUpdate(BaseModel):
    """Partiële update; `applicatie_id` immutabel ⇒ niet aanwezig."""

    model_config = ConfigDict(extra="forbid")

    categorie: DatatypeCategorie | None = None
    omschrijving: str | None = None
    omvang_indicatie: str | None = None

    @field_validator("omschrijving")
    @classmethod
    def _v_omschrijving(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)

    @field_validator("omvang_indicatie")
    @classmethod
    def _v_omvang(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @model_validator(mode="after")
    def _verbied_null_op_verplicht(self) -> "DatatypeUpdate":
        for veld in _VERPLICHTE_VELDEN:
            if veld in self.model_fields_set and getattr(self, veld) is None:
                raise ValueError(f"{veld} mag niet op null worden gezet")
        return self


class DatatypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # ADR-023: afgeleid uit de access-relatie; None = wees (applicatie verwijderd, Besluit 13).
    applicatie_id: uuid.UUID | None
    categorie: DatatypeCategorie
    omschrijving: str | None
    omvang_indicatie: str | None
    created_at: datetime
    updated_at: datetime


class DatatypePagina(BaseModel):
    items: list[DatatypeRead]
    volgende_cursor: str | None = None


class DatatypeOpties(BaseModel):
    """Read-only keuzewaarden per enumveld (voor de frontend-dropdowns)."""

    categorie: list[str]
