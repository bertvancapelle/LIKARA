"""Pydantic v2-schemas voor de platform-beheer-API van de checklist-
antwoordconfiguratie (ADR-019 fase 2D, ADR-012 Addendum A).

Beheer-read (incl. inactieve opties + optie-`id` + `afgeleid_bron`), apart van de
tenant-facing `ChecklistVraagRead` (2B): de beheerder adresseert opties op `id` en
moet de read-only-status van afgeleide sets kunnen tonen.
"""
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from models.models import AntwoordType
from schemas.applicatie import _optionele_tekst, _verplichte_tekst


class ConfigOptieRead(BaseModel):
    """Eén optie uit de catalogus, beheer-perspectief."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    optie_sleutel: str
    label: str
    volgorde: int
    actief: bool
    afgeleid_bron: str | None


class ConfigVraagRead(BaseModel):
    """Eén vraag + antwoordtype + ALLE opties (incl. inactieve)."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    vraag: str
    antwoordtype: AntwoordType
    opties: list[ConfigOptieRead] = []


class AntwoordTypeUpdate(BaseModel):
    """Antwoordtype van een vraag zetten."""

    model_config = ConfigDict(extra="forbid")

    antwoordtype: AntwoordType


class OptieCreate(BaseModel):
    """Nieuwe optie toevoegen aan een (niet-afgeleide) vraag."""

    model_config = ConfigDict(extra="forbid")

    optie_sleutel: str
    label: str
    volgorde: int = 0

    @field_validator("optie_sleutel")
    @classmethod
    def _v_sleutel(cls, v: str) -> str:
        return _verplichte_tekst(v, "optie_sleutel", 60)

    @field_validator("label")
    @classmethod
    def _v_label(cls, v: str) -> str:
        return _verplichte_tekst(v, "label", 120)


class OptieUpdate(BaseModel):
    """Label en/of volgorde van een optie wijzigen (partieel)."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    volgorde: int | None = None

    @field_validator("label")
    @classmethod
    def _v_label(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "label", 120)
