"""Pydantic v2-schemas — Proces (ADR-042 slice 1).

Een proces is wat de organisatie dóét, nestbaar van grof naar fijn via `ouder_id`
(composiet self-FK; de plek in de boom ís het niveau). Cycluspreventie + verwijdergedrag
worden server-side gehandhaafd (zie proces_service). Work_package-spiegel.
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _optionele_tekst, _verplichte_tekst


class ProcesSorteerveld(str, Enum):
    """Sorteer-allowlist op de API-rand (ADR-017) — onbekend veld ⇒ 422. Single source
    naast `proces_service._SORTEERBARE_KOLOMMEN` (synctest borgt de 1-op-1-koppeling)."""

    created_at = "created_at"
    naam = "naam"


class ProcesCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str
    toelichting: str | None = None
    ouder_id: uuid.UUID | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000, meerregelig=True)


class ProcesUpdate(BaseModel):
    """Partieel. `ouder_id` meesturen = verplaatsen (incl. expliciet `null` = loskoppelen
    tot top-level proces); weglaten = ongewijzigd."""

    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    toelichting: str | None = None
    ouder_id: uuid.UUID | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 255)

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000, meerregelig=True)


class ProcesRead(BaseModel):
    id: uuid.UUID
    naam: str
    toelichting: str | None
    ouder_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ProcesPagina(BaseModel):
    items: list[ProcesRead]
    volgende_cursor: str | None = None


class ProcesBoomItem(BaseModel):
    """Eén afstammeling in de subboom-lees-traversal (deelprocessen, alle niveaus)."""

    id: uuid.UUID
    naam: str
    ouder_id: uuid.UUID | None
    niveau: int            # 1 = direct deelproces van de wortel
    pad: list[str]         # proces-namen van de wortel → dit proces
