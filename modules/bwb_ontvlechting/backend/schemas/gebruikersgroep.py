"""Pydantic v2-schemas voor de entiteit Gebruikersgroep (P5-vervolg, ADR-009).

ADR-024 UX-B6-a: `organisatie` is een **optionele verwijzing** naar een organisatie-partij
(`organisatie_id`), niet langer vrije tekst. `aantal_gebruikers` is optioneel en niet-negatief
(`ge=0`). `applicatie_id` zit in Create maar niet in Update (immutabel).
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from schemas._validators import _optionele_tekst


class GebruikersgroepSorteerveld(str, Enum):
    """Allowlist van sorteerbare lijst-velden (ADR-017 B2, retrofit CD020).

    Dekt de getoonde kolommen. `organisatie` sorteert op de naam van de gekoppelde
    organisatie-partij (nullable → NULLS LAST). `afdeling`/`aantal_gebruikers` nullable
    eveneens. De service mapt deze namen 1-op-1; een test borgt de synchroniteit.
    """

    created_at = "created_at"
    organisatie = "organisatie"
    afdeling = "afdeling"
    aantal_gebruikers = "aantal_gebruikers"


class GebruikersgroepCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applicatie_id: uuid.UUID
    # ADR-024 UX-B6-a — optionele verwijzing naar de organisatie (partij, aard=organisatie).
    organisatie_id: uuid.UUID | None = None
    afdeling: str | None = None
    aantal_gebruikers: int | None = Field(default=None, ge=0)

    @field_validator("afdeling")
    @classmethod
    def _v_afdeling(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)


class GebruikersgroepUpdate(BaseModel):
    """Partiële update; `applicatie_id` immutabel ⇒ niet aanwezig."""

    model_config = ConfigDict(extra="forbid")

    organisatie_id: uuid.UUID | None = None
    afdeling: str | None = None
    aantal_gebruikers: int | None = Field(default=None, ge=0)

    @field_validator("afdeling")
    @classmethod
    def _v_afdeling(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)


class GebruikersgroepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # ADR-023: afgeleid uit de serving-relatie; None = wees (Besluit 13).
    applicatie_id: uuid.UUID | None
    # ADR-024 UX-B6-a — organisatie als verwijzing + geresolveerde naam (read).
    organisatie_id: uuid.UUID | None = None
    organisatie_naam: str | None = None
    afdeling: str | None
    aantal_gebruikers: int | None
    created_at: datetime
    updated_at: datetime


class GebruikersgroepPagina(BaseModel):
    items: list[GebruikersgroepRead]
    volgende_cursor: str | None = None
