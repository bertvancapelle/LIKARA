"""Pydantic v2-schemas voor de platform-beheer-API van de relatie-kenmerk-catalogus
(ADR-023 Fase F / F-4). Spiegel van `schemas/componentconfig`, op `RelatieKenmerkOptie`.

`dimensie` en `optie_sleutel` zijn immutable (stabiele sleutel) — ze ontbreken in Update;
meesturen ⇒ 422 (`extra='forbid'`). Anders dan componentconfig is er hier GEEN beschermde
systeem-sleutel: álle waarden zijn soft-deactiveerbaar.
"""
import re

from pydantic import BaseModel, ConfigDict, field_validator

from models.models import RelatieKenmerkDimensie
from schemas._validators import _verplichte_tekst

_SLEUTEL_PATROON = re.compile(r"^[a-z][a-z0-9_]*$")


def _v_sleutel(v: str) -> str:
    v = _verplichte_tekst(v, "optie_sleutel", 60)
    if not _SLEUTEL_PATROON.match(v):
        raise ValueError("optie_sleutel moet lowercase snake_case zijn (a-z, 0-9, _)")
    return v


class RelatieKenmerkOptieCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimensie: RelatieKenmerkDimensie
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


class RelatieKenmerkOptieUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    volgorde: int | None = None
    actief: bool | None = None

    @field_validator("label")
    @classmethod
    def _label(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "label", 120)


class RelatieKenmerkOptieRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dimensie: RelatieKenmerkDimensie
    optie_sleutel: str
    label: str
    volgorde: int
    actief: bool
