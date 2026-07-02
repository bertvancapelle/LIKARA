"""Pydantic v2-schemas voor de platform-beheer-API van de contract-classificatie-
catalogus (ADR-020 Besluit 6, ADR-012 Addendum B).

Beheer-perspectief: opties worden geadresseerd op `id` (int-PK) en de beheerder ziet
ook inactieve opties. `dimensie` en `optie_sleutel` zijn **immutable** (stabiele sleutel,
Besluit 6) — ze ontbreken in Update; meesturen ⇒ 422 (`extra='forbid'`).
"""
import re

from pydantic import BaseModel, ConfigDict, field_validator

from models.models import ContractConfigDimensie
from schemas._validators import _verplichte_tekst

# Stabiele sleutel: lowercase snake_case (start met letter; a-z, 0-9, _). Geen
# hoofdletters/spaties — anders is de sleutel niet stabiel/herleidbaar.
_SLEUTEL_PATROON = re.compile(r"^[a-z][a-z0-9_]*$")


def _v_sleutel(v: str) -> str:
    v = _verplichte_tekst(v, "optie_sleutel", 60)
    if not _SLEUTEL_PATROON.match(v):
        raise ValueError("optie_sleutel moet lowercase snake_case zijn (a-z, 0-9, _)")
    return v


class ContractConfigOptieCreate(BaseModel):
    """Nieuwe catalogus-optie binnen een dimensie."""

    model_config = ConfigDict(extra="forbid")

    dimensie: ContractConfigDimensie
    optie_sleutel: str
    label: str
    volgorde: int | None = None  # None ⇒ service plaatst achteraan binnen de dimensie

    @field_validator("optie_sleutel")
    @classmethod
    def _sleutel(cls, v: str) -> str:
        return _v_sleutel(v)

    @field_validator("label")
    @classmethod
    def _label(cls, v: str) -> str:
        return _verplichte_tekst(v, "label", 120)


class ContractConfigOptieUpdate(BaseModel):
    """Partieel: label / volgorde / actief. `dimensie` en `optie_sleutel` zijn immutable."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    volgorde: int | None = None
    actief: bool | None = None

    @field_validator("label")
    @classmethod
    def _label(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "label", 120)


class ContractConfigOptieRead(BaseModel):
    """Eén catalogus-optie, beheer-perspectief (incl. inactieve)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    dimensie: ContractConfigDimensie
    optie_sleutel: str
    label: str
    volgorde: int
    actief: bool
