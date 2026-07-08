"""Pydantic v2-schemas — platform-beheer van de applicatiefunctie-catalogus (ADR-042 slice 2).

Enkel-doel catalogus (geen `dimensie`), spiegel van `schemas/componentrolconfig`.
`optie_sleutel` is immutable — ontbreekt in Update. Soft-deactivate (geen V); er is
GEEN systeem-sleutel (elke optie is deactiveerbaar, ADR-042 besluit 3).
"""
import re

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _verplichte_tekst

_SLEUTEL_PATROON = re.compile(r"^[a-z][a-z0-9_]*$")


def _v_sleutel(v: str) -> str:
    v = _verplichte_tekst(v, "optie_sleutel", 60)
    if not _SLEUTEL_PATROON.match(v):
        raise ValueError("optie_sleutel moet lowercase snake_case zijn (a-z, 0-9, _)")
    return v


class ApplicatiefunctieOptieCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    optie_sleutel: str
    label: str
    volgorde: int | None = None

    @field_validator("optie_sleutel")
    @classmethod
    def _sleutel(cls, v: str) -> str:
        return _v_sleutel(v)

    @field_validator("label")
    @classmethod
    def _label(cls, v: str) -> str:
        return _verplichte_tekst(v, "label", 120)


class ApplicatiefunctieOptieUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    volgorde: int | None = None
    actief: bool | None = None

    @field_validator("label")
    @classmethod
    def _label(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "label", 120)


class ApplicatiefunctieOptieRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    optie_sleutel: str
    label: str
    volgorde: int
    actief: bool
