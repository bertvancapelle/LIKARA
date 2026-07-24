"""Pydantic v2-schemas — Bedrijfsfunctie (ADR-043 gate 1a; ADR-044 gate 1a-bis).

Een bedrijfsfunctie is de logische ruggengraat van de kaart. **ADR-044: de boom leeft in
PLAATSINGEN** (aggregation-relaties, ouder → kind), niet in een ouder-kolom — één functie
kan op meerdere plekken staan (meerdere ouders), zonder rangorde of thuisplek.

- Create/Update dragen GEEN bron-/vervallen-velden (`extra='forbid'` weert ze): het
  gebruikers-pad maakt uitsluitend EIGEN functies; herkomst en vervallen worden door de
  seed/import gezet (gate 1b). Modelinhoud-bescherming (bronsleutel → naam/definitie/
  plaatsing read-only, 422 `MODELINHOUD_BESCHERMD`) zit in de servicelaag.
- Create kent een optionele `ouder_id` als GEMAK (de "+ Deelfunctie"-flow: aanmaken mét
  eerste plaatsing in één handeling); Update kent GEEN plaatsing-velden — plaatsingen
  muteer je via de plaatsings-endpoints (`PlaatsingCreate`).
- Read levert `ouder_ids` (alle plaatsingen — gelijkwaardig, geen rangorde) + herkomst +
  vervallen mét resolutie (`bron_model_naam`/`bron_model_versie`).
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
        return _optionele_tekst(v, 10_000, meerregelig=True)


class BedrijfsfunctieUpdate(BaseModel):
    """Partieel — alléén zinvol op een EIGEN functie (modelinhoud is read-only; de
    service weigert met 422 `MODELINHOUD_BESCHERMD`). Plaatsingen (waar de functie
    hangt) muteer je NIET hier maar via de plaatsings-endpoints (ADR-044)."""

    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    definitie: str | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 255)

    @field_validator("definitie")
    @classmethod
    def _v_definitie(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000, meerregelig=True)


class PlaatsingCreate(BaseModel):
    """ADR-044 — één plaatsing toevoegen: hang déze functie (route-pad) onder `ouder_id`.
    Meerdere ouders = meerdere plaatsingen; alle plekken zijn gelijkwaardig."""

    model_config = ConfigDict(extra="forbid")

    ouder_id: uuid.UUID


class BedrijfsfunctieRead(BaseModel):
    id: uuid.UUID
    naam: str
    definitie: str | None
    # ADR-044 — álle plaatsingen (ouders), gelijkwaardig en ongeordend van betekenis
    # (gesorteerd geleverd voor een deterministische respons); leeg = wortel.
    ouder_ids: list[uuid.UUID] = []
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
    """Eén afstammeling in de subboom-lees-traversal (deelfuncties, alle niveaus).
    ADR-044: `ouder_id` is hier de TRAVERSAL-ouder (via welke plaatsing dit item in de
    subboom is bereikt — kortste pad); een functie kan daarnaast nog andere plaatsingen
    hebben (zie `BedrijfsfunctieRead.ouder_ids`)."""

    id: uuid.UUID
    naam: str
    ouder_id: uuid.UUID | None
    vervallen: bool
    niveau: int            # 1 = directe deelfunctie van de wortel
    pad: list[str]         # functie-namen van de wortel → deze functie
