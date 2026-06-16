"""Pydantic v2-schemas — cross-element laagprojectie (ADR-023 Fase F / F-2).

Read-only projectie: per element de afgeleide ArchiMate-typing (laag/aspect/element) +
een per-subtype afgeleide weergavenaam. Geen schema-/modelwijziging.
"""
import uuid

from pydantic import BaseModel


class ArchitectuurElementRead(BaseModel):
    id: uuid.UUID
    element_type: str
    naam: str
    naam_secundair: str | None = None  # bv. datatype-omschrijving (categorie = primaire naam)
    archimate_element: str | None = None
    laag: str | None = None
    aspect: str | None = None


class ArchitectuurPagina(BaseModel):
    items: list[ArchitectuurElementRead]
    volgende_cursor: str | None = None
