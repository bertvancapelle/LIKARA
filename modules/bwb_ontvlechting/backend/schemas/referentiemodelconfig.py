"""Pydantic v2-schemas — platform-beheer van het referentiemodel-aanbod (gate 1b §2.1).

Spiegel van `schemas/applicatiefunctieconfig`, met één bewust verschil: er is GEEN
Create-schema. Het aanbod is gesloten (ADR-043: repo-route — een aanbod-rij zonder
meegeleverd modelbestand kan niet ingelezen worden); nieuw aanbod = release-curatie
(bestand + `HERKOMST.md` + seed), geen beheerscherm-handeling. Beheerbaar zijn label,
volgorde en actief (soft-deactivate); sleutel/herkomst/versie zijn de gecureerde
identiteit en read-only.
"""
from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _verplichte_tekst


class ReferentiemodelOptieUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    volgorde: int | None = None
    actief: bool | None = None

    @field_validator("label")
    @classmethod
    def _label(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "label", 150)


class ReferentiemodelOptieRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    optie_sleutel: str
    label: str
    herkomst: str
    versie: str
    volgorde: int
    actief: bool
