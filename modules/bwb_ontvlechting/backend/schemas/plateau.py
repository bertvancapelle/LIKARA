"""Pydantic v2-schemas — Plateau + plateau-lidmaatschap (ADR-023 Fase E, E1).

Een plateau is een momentopname van het landschap (naam + toelichting). Lidmaatschap
loopt via het unified relatiemodel als aggregation-relatie (bron=plateau, doel=lid) met
de dispositie + contractuele bevestiging als kenmerken. De bevestigingsgegevens zijn
registratie (geen validatie/vergelijking); `bevestigd_door`/`bevestigd_op` worden
server-side gevuld (niet via invoer).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from schemas.applicatie import _optionele_tekst, _verplichte_tekst


class PlateauCreate(BaseModel):
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
        return _optionele_tekst(v, 10_000)


class PlateauUpdate(BaseModel):
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
        return _optionele_tekst(v, 10_000)


class PlateauRead(BaseModel):
    id: uuid.UUID
    naam: str
    toelichting: str | None
    created_at: datetime
    updated_at: datetime


class PlateauPagina(BaseModel):
    items: list[PlateauRead]
    volgende_cursor: str | None = None


class PlateauLidCreate(BaseModel):
    """Een lid (component of contract) in een plateau hangen, met dispositie + optionele
    contractuele bevestiging. `bevestigd_door`/`bevestigd_op` worden server-side gevuld."""

    model_config = ConfigDict(extra="forbid")

    lid_id: uuid.UUID
    dispositie: str
    contractueel_bevestigd: bool = False
    bevestigd_aantal_gebruikers: int | None = None

    @field_validator("dispositie")
    @classmethod
    def _v_dispositie(cls, v: str) -> str:
        return _verplichte_tekst(v, "dispositie", 60)

    @field_validator("bevestigd_aantal_gebruikers")
    @classmethod
    def _v_aantal(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("bevestigd_aantal_gebruikers mag niet negatief zijn")
        return v


class PlateauLidUpdate(BaseModel):
    """Partieel: dispositie en/of de contractuele bevestiging bijwerken."""

    model_config = ConfigDict(extra="forbid")

    dispositie: str | None = None
    contractueel_bevestigd: bool | None = None
    bevestigd_aantal_gebruikers: int | None = None

    @field_validator("dispositie")
    @classmethod
    def _v_dispositie(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "dispositie", 60)

    @field_validator("bevestigd_aantal_gebruikers")
    @classmethod
    def _v_aantal(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("bevestigd_aantal_gebruikers mag niet negatief zijn")
        return v


class PlateauLidRead(BaseModel):
    id: uuid.UUID                 # de aggregation-relatie-id
    plateau_id: uuid.UUID
    lid_id: uuid.UUID
    lid_element_type: str         # 'component' | 'contract'
    dispositie: str
    dispositie_label: str
    contractueel_bevestigd: bool
    bevestigd_aantal_gebruikers: int | None
    bevestigd_door: str | None    # server-side (actor) op moment van bevestigen
    bevestigd_op: str | None      # server-side ISO-timestamp op moment van bevestigen
    created_at: datetime
    updated_at: datetime
