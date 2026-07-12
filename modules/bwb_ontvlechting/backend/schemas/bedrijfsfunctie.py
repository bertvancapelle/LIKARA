"""Pydantic v2-schemas — Bedrijfsfunctie (ADR-043 gate 1a).

Een bedrijfsfunctie is de logische ruggengraat van de kaart, nestbaar via `ouder_id`
(composiet self-FK; de plek in de boom ís het niveau — topgroeperingen zijn gewone
wortelknopen). Het proces-schema-recept 1-op-1, met de ADR-043-lezing:

- Create/Update dragen GEEN bron-/vervallen-velden (`extra='forbid'` weert ze): het
  gebruikers-pad maakt uitsluitend EIGEN functies; herkomst en vervallen worden door de
  seed/import gezet (gate 1b). Modelinhoud-bescherming (bronsleutel → naam/definitie/
  ouder read-only, 422 `MODELINHOUD_BESCHERMD`) zit in de servicelaag.
- Read levert herkomst + vervallen mét resolutie (`bron_model_naam`/`bron_model_versie`)
  zodat de UI de rustige herkomstvermelding ("uit [model], versie X") kan tonen.
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _optionele_tekst, _verplichte_tekst


class BedrijfsfunctieSorteerveld(str, Enum):
    """Sorteer-allowlist op de API-rand (ADR-017) — onbekend veld ⇒ 422. Single source
    naast `bedrijfsfunctie_service._SORTEERBARE_KOLOMMEN` (synctest borgt de koppeling)."""

    created_at = "created_at"
    naam = "naam"


class BedrijfsfunctieCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str
    definitie: str | None = None
    ouder_id: uuid.UUID | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @field_validator("definitie")
    @classmethod
    def _v_definitie(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)


class BedrijfsfunctieUpdate(BaseModel):
    """Partieel — alléén zinvol op een EIGEN functie (modelinhoud is read-only; de
    service weigert met 422 `MODELINHOUD_BESCHERMD`). `ouder_id` meesturen =
    verplaatsen (incl. expliciet `null` = loskoppelen tot wortel); weglaten =
    ongewijzigd."""

    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    definitie: str | None = None
    ouder_id: uuid.UUID | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 255)

    @field_validator("definitie")
    @classmethod
    def _v_definitie(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)


class BedrijfsfunctieRead(BaseModel):
    id: uuid.UUID
    naam: str
    definitie: str | None
    ouder_id: uuid.UUID | None
    # Herkomst (beide gezet = modelinhoud/read-only; beide None = eigen functie).
    bron_model_id: uuid.UUID | None
    bron_sleutel: str | None
    bron_model_naam: str | None = None
    bron_model_versie: str | None = None
    # Besluit LI039-6 — "bestaat niet meer in het ingelezen model" (zichtbaar, niet koppelbaar).
    vervallen: bool
    created_at: datetime
    updated_at: datetime


class BedrijfsfunctiePagina(BaseModel):
    items: list[BedrijfsfunctieRead]
    volgende_cursor: str | None = None


class BedrijfsfunctieBoomItem(BaseModel):
    """Eén afstammeling in de subboom-lees-traversal (deelfuncties, alle niveaus)."""

    id: uuid.UUID
    naam: str
    ouder_id: uuid.UUID | None
    vervallen: bool
    niveau: int            # 1 = directe deelfunctie van de wortel
    pad: list[str]         # functie-namen van de wortel → deze functie
