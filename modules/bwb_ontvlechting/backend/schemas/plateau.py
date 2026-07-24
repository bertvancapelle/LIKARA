"""Pydantic v2-schemas — Plateau + plateau-lidmaatschap (ADR-023 Fase E, E1).

Een plateau is een momentopname van het landschap (naam + toelichting). Lidmaatschap
loopt via het unified relatiemodel als aggregation-relatie (bron=plateau, doel=lid) met
de contractuele bevestiging als kenmerken. ADR-046 besluit 2: de dispositie is als
bestemmingsveld AFGEBOUWD — het plateau draagt geen eigen bedoeling meer (die leeft op
het component: `migratiepad`); historische dispositie-waarden blijven read-only
resolvebaar. De bevestigingsgegevens zijn registratie (geen validatie/vergelijking);
`bevestigd_door`/`bevestigd_op` worden server-side gevuld (niet via invoer).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _optionele_tekst, _verplichte_tekst


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
        return _optionele_tekst(v, 10_000, meerregelig=True)


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
        return _optionele_tekst(v, 10_000, meerregelig=True)


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
    """Een lid (component of contract) in een plateau hangen, met optionele contractuele
    bevestiging. ADR-046: géén dispositie meer (`extra='forbid'` weert het veld) — de
    bedoeling leeft op het component. `bevestigd_door`/`bevestigd_op` server-side."""

    model_config = ConfigDict(extra="forbid")

    lid_id: uuid.UUID
    contractueel_bevestigd: bool = False
    bevestigd_aantal_gebruikers: int | None = None

    @field_validator("bevestigd_aantal_gebruikers")
    @classmethod
    def _v_aantal(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("bevestigd_aantal_gebruikers mag niet negatief zijn")
        return v


class PlateauLidUpdate(BaseModel):
    """Partieel: de contractuele bevestiging bijwerken (dispositie vervallen, ADR-046)."""

    model_config = ConfigDict(extra="forbid")

    contractueel_bevestigd: bool | None = None
    bevestigd_aantal_gebruikers: int | None = None

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
    lid_naam: str | None          # naam van het lid (component.naam / contract.contractnaam)
    # ADR-046 — read-only HISTORIE: rijen van vóór de afbouw dragen nog een dispositie
    # (soft-gedeactiveerde catalogus blijft label-resolvebaar); nieuwe rijen niet (null).
    dispositie: str | None = None
    dispositie_label: str | None = None
    contractueel_bevestigd: bool
    bevestigd_aantal_gebruikers: int | None
    bevestigd_door: str | None    # ADR-029: e-mail-fallback van de actor (historisch: kale string)
    bevestigd_door_naam: str | None = None  # ADR-029 Fase 3b — geresolveerde naam (sub → persoon)
    bevestigd_op: str | None      # server-side ISO-timestamp op moment van bevestigen
    created_at: datetime
    updated_at: datetime
