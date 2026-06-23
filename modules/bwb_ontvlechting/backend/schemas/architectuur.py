"""Pydantic v2-schemas — cross-element laagprojectie (ADR-023 Fase F / F-2).

Read-only projectie: per element de afgeleide ArchiMate-typing (laag/aspect/element) +
een per-subtype afgeleide weergavenaam. Geen schema-/modelwijziging.
"""
import uuid
from enum import Enum

from pydantic import BaseModel


class ArchitectuurSorteerveld(str, Enum):
    """Allowlist van sorteerbare kolommen (ADR-017). Naam/laag/aspect/soort zijn server-side
    afgeleid in SQL; `type` = element_type. Synchroon met `architectuur_service._SORTEERVELDEN`."""

    created_at = "created_at"
    naam = "naam"
    type = "type"
    laag = "laag"
    aspect = "aspect"
    soort = "soort"


class ArchitectuurElementRead(BaseModel):
    id: uuid.UUID
    element_type: str
    naam: str
    naam_secundair: str | None = None  # bv. datatype-omschrijving (categorie = primaire naam)
    archimate_element: str | None = None
    laag: str | None = None
    aspect: str | None = None
    partij_aard: str | None = None  # ADR-024 — alleen gevuld voor element_type='partij'


class ArchitectuurPagina(BaseModel):
    items: list[ArchitectuurElementRead]
    volgende_cursor: str | None = None
