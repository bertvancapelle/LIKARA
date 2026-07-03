"""Pydantic v2-schemas voor de entiteit Gebruikersgroep (P5-vervolg, ADR-009; ADR-036; ADR-036a).

ADR-024 UX-B6-a: `organisatie` is een **optionele verwijzing** naar een organisatie-partij
(`organisatie_id`). `aantal_gebruikers` is optioneel en niet-negatief (`ge=0`). `applicatie_id` zit
in Create maar niet in Update (immutabel).

ADR-036a: `afdeling` is niet langer vrije tekst maar een **structurele referentie** `afdeling_id`
naar een `organisatie_eenheid`-partij (binnen de organisatie van het grove feit — service borgt
dat). Create/Update dragen `afdeling_id`; Read geeft `afdeling_id` + de geresolveerde `afdeling`
(partij-naam) terug.
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class GebruikersgroepSorteerveld(str, Enum):
    """Allowlist van sorteerbare lijst-velden (ADR-017 B2, retrofit CD020).

    `organisatie`/`afdeling` sorteren op de naam van de gekoppelde partij (nullable → NULLS LAST);
    `aantal_gebruikers` nullable eveneens. De service mapt deze namen 1-op-1; een test borgt de
    synchroniteit.
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
    # ADR-036a — optionele verwijzing naar een organisatie_eenheid-partij (afdeling).
    afdeling_id: uuid.UUID | None = None
    aantal_gebruikers: int | None = Field(default=None, ge=0)


class GebruikersgroepUpdate(BaseModel):
    """Partiële update; `applicatie_id` immutabel ⇒ niet aanwezig."""

    model_config = ConfigDict(extra="forbid")

    organisatie_id: uuid.UUID | None = None
    afdeling_id: uuid.UUID | None = None
    aantal_gebruikers: int | None = Field(default=None, ge=0)


class GebruikersgroepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # ADR-023: afgeleid uit de serving-relatie; None = wees (Besluit 13).
    applicatie_id: uuid.UUID | None
    # ADR-024 UX-B6-a — organisatie als verwijzing + geresolveerde naam (read).
    organisatie_id: uuid.UUID | None = None
    organisatie_naam: str | None = None
    # ADR-036a — afdeling als verwijzing + geresolveerde partij-naam.
    afdeling_id: uuid.UUID | None = None
    afdeling: str | None = None
    aantal_gebruikers: int | None
    created_at: datetime
    updated_at: datetime


class GebruikersgroepPagina(BaseModel):
    items: list[GebruikersgroepRead]
    volgende_cursor: str | None = None
