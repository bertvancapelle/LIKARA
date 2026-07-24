"""Pydantic v2-schemas — Deliverable + realisatieketen (ADR-023 Fase E, E3).

Een deliverable is een op te leveren resultaat (naam + toelichting). De keten
work_package → deliverable → plateau loopt via `realization`-relaties; koppelingen zijn
expliciet en optioneel (Besluit 8). De lees-schema's ontsluiten de keten read-only.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _optionele_tekst, _verplichte_tekst


class DeliverableCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str
    toelichting: str | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000, meerregelig=True)


class DeliverableUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    toelichting: str | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 255)

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000, meerregelig=True)


class DeliverableRead(BaseModel):
    id: uuid.UUID
    naam: str
    toelichting: str | None
    created_at: datetime
    updated_at: datetime


class DeliverablePagina(BaseModel):
    items: list[DeliverableRead]
    volgende_cursor: str | None = None


# ── Ketenkoppelingen (realization) ───────────────────────────────────────────────

class KoppelWerkpakket(BaseModel):
    """Koppel het werkpakket dat deze deliverable oplevert (work_package → deliverable)."""

    model_config = ConfigDict(extra="forbid")
    work_package_id: uuid.UUID


class KoppelPlateau(BaseModel):
    """Koppel het plateau dat deze deliverable mee helpt realiseren (deliverable → plateau)."""

    model_config = ConfigDict(extra="forbid")
    plateau_id: uuid.UUID


class RealisatieKoppeling(BaseModel):
    """Eén realization-koppeling (de relatie-id + het gekoppelde element)."""

    relatie_id: uuid.UUID
    element_id: uuid.UUID
    naam: str


class DeliverableKeten(BaseModel):
    """De keten rond één deliverable: de realiserende werkpakketten + de gerealiseerde plateaus."""

    werkpakketten: list[RealisatieKoppeling] = []
    plateaus: list[RealisatieKoppeling] = []


# ── Werkpakket-centrische keten-traversal (work_package → deliverables → plateaus) ─

class KetenPlateau(BaseModel):
    plateau_id: uuid.UUID
    naam: str


class KetenDeliverable(BaseModel):
    deliverable_id: uuid.UUID
    naam: str
    plateaus: list[KetenPlateau] = []


class WerkpakketKeten(BaseModel):
    work_package_id: uuid.UUID
    deliverables: list[KetenDeliverable] = []
