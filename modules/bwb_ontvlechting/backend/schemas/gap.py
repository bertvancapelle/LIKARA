"""Pydantic v2-schemas — Gap + leden + readiness (ADR-023 Fase E, E4).

Een gap is een geregistreerde kloof tussen een baseline-plateau en een doel-plateau
(naam + toelichting + twee verplichte plateau-referenties). Leden (component/contract)
lopen via `association`-relaties (bron=gap → doel=lid). De twee readiness-cijfers
(technisch + contractueel) zijn **puur read-only afgeleid** en worden in de detail-respons
ingebed; ze worden nooit vermengd tot één getal en er wordt niets opgeslagen.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _optionele_tekst, _verplichte_tekst


class GapCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str
    toelichting: str | None = None
    baseline_plateau_id: uuid.UUID
    doel_plateau_id: uuid.UUID

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)


class GapUpdate(BaseModel):
    """Partieel. Naast naam/toelichting mogen ook baseline-/doel-plateau gewijzigd worden
    (UX-A4-4-aanvulling): een gebruiker corrigeert een vergissing of een verschoven planning
    ter plekke, zónder de gap weg te gooien en de leden te verliezen. Dezelfde validatie als
    bij aanmaken geldt (beide een geldig plateau, baseline ≠ doel) — in de servicelaag, omdat
    die een DB-lookup vergt. De kolommen waren al NOT NULL; alleen de mutatie-conventie wijzigt."""

    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    toelichting: str | None = None
    baseline_plateau_id: uuid.UUID | None = None
    doel_plateau_id: uuid.UUID | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 255)

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)


class GapRead(BaseModel):
    id: uuid.UUID
    naam: str
    toelichting: str | None
    baseline_plateau_id: uuid.UUID
    doel_plateau_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class GapPagina(BaseModel):
    items: list[GapRead]
    volgende_cursor: str | None = None


# ── Readiness (puur read-only afgeleid; twee gescheiden cijfers) ──────────────────

class ReadinessCijfer(BaseModel):
    """Telling + percentage van één readiness-as. Lege noemer ⇒ percentage = None
    (niet 0), aantallen 0. De twee assen worden nooit vermengd tot één getal."""

    aantal_klaar: int
    aantal_totaal: int
    percentage: float | None


class GapDetail(BaseModel):
    """Gap-detail met de twee gescheiden readiness-cijfers ingebed (read-only afgeleid)."""

    id: uuid.UUID
    naam: str
    toelichting: str | None
    baseline_plateau_id: uuid.UUID
    doel_plateau_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    readiness_technisch: ReadinessCijfer
    readiness_contractueel: ReadinessCijfer


# ── Leden (association bron=gap → doel=lid) ───────────────────────────────────────

class GapLidCreate(BaseModel):
    """Een lid (component of contract) aan een gap koppelen."""

    model_config = ConfigDict(extra="forbid")
    lid_id: uuid.UUID


class GapLidRead(BaseModel):
    id: uuid.UUID            # de association-relatie-id
    gap_id: uuid.UUID
    lid_id: uuid.UUID
    lid_element_type: str    # 'component' | 'contract'
    naam: str | None
    created_at: datetime
    updated_at: datetime
