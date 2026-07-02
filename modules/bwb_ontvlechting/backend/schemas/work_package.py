"""Pydantic v2-schemas — Work Package (ADR-023 Fase E, E2).

Een werkpakket is een eenheid van migratiewerk (naam + toelichting), hiërarchisch
opdeelbaar via `bovenliggend_id` (composiet self-FK). Cycluspreventie + verwijdergedrag
worden server-side gehandhaafd (zie work_package_service).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _optionele_tekst, _verplichte_tekst


class WorkPackageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str
    toelichting: str | None = None
    bovenliggend_id: uuid.UUID | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)


class WorkPackageUpdate(BaseModel):
    """Partieel. `bovenliggend_id` meesturen = wijzigen (incl. expliciet `null` =
    loskoppelen tot top-level); weglaten = ongewijzigd."""

    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    toelichting: str | None = None
    bovenliggend_id: uuid.UUID | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 255)

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)


class WorkPackageRead(BaseModel):
    id: uuid.UUID
    naam: str
    toelichting: str | None
    bovenliggend_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class WorkPackagePagina(BaseModel):
    items: list[WorkPackageRead]
    volgende_cursor: str | None = None


class WorkPackageBoomItem(BaseModel):
    """Eén afstammeling in de subboom-lees-traversal."""

    id: uuid.UUID
    naam: str
    bovenliggend_id: uuid.UUID | None
    niveau: int            # 1 = direct subpakket van de wortel
    pad: list[str]         # werkpakket-namen van de wortel → dit pakket
