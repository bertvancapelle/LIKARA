"""Pydantic v2 schemas — relatiemodel (ADR-023 Fase B)."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from schemas._validators import _verplichte_tekst


class RelatieCreate(BaseModel):
    model_config = {"extra": "forbid"}

    bron_id: uuid.UUID
    doel_id: uuid.UUID
    relatietype: str = Field(min_length=1, max_length=40)
    # ADR-023a — identificerende koppeling-naam: VERPLICHT voor flow, optioneel voor andere typen.
    naam: str | None = Field(default=None, max_length=150)
    kenmerken: dict = Field(default_factory=dict)
    omschrijving: str | None = Field(default=None, max_length=2000)
    # Overrule-vlag voor de dubbel-signalering (KOPPELING_DUBBEL). Geen persistent veld:
    # de service leest dit alleen om de waarschuwing al-dan-niet over te slaan.
    negeer_waarschuwing: bool = False

    @field_validator("relatietype")
    @classmethod
    def _strip_type(cls, v: str) -> str:
        # LI051 — via de gedeelde tekst-validator (blok A/B); relatietype is een enkelregelige
        # catalogus-sleutel (de service valideert 'm bovendien tegen de gesloten set).
        return _verplichte_tekst(v, "relatietype", 40)

    @model_validator(mode="after")
    def _naam_verplicht_voor_flow(self):
        if self.relatietype == "flow" and not (self.naam and self.naam.strip()):
            raise ValueError("naam is verplicht voor een flow-koppeling")
        return self


class RelatieUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    # ADR-023a — `naam` muteerbaar (endpoints/relatietype blijven immutabel). De
    # naam-verplicht-voor-flow-regel bij bewerken zit in de servicelaag (kent `relatietype`).
    naam: str | None = Field(default=None, max_length=150)
    kenmerken: dict | None = None
    omschrijving: str | None = Field(default=None, max_length=2000)


class RelatieRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    bron_id: uuid.UUID
    doel_id: uuid.UUID
    relatietype: str
    naam: str | None = None
    kenmerken: dict
    omschrijving: str | None = None
    dubbel_waarschuwing_genegeerd: bool = False
    created_at: datetime
    updated_at: datetime


class RelatiePagina(BaseModel):
    items: list[RelatieRead]
    volgende_cursor: str | None = None
