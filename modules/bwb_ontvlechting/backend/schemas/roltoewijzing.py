"""Pydantic v2-schemas voor rol-toewijzing (ADR-024 slice 2b).

`RoltoewijzingAanmaken` = invoer (partij_id, object_id, rol), `extra='forbid'`. `RoltoewijzingUit`
= verrijkte uitvoer (toewijzing_id + de geresolveerde partij-/object-namen + rol-label). Welke
verrijkings-velden gevuld zijn hangt af van de leesrichting (object-zijde vult de partij-velden;
partij-zijde vult de object-velden) — daarom zijn ze optioneel.
"""
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _verplichte_tekst


class RoltoewijzingAanmaken(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partij_id: uuid.UUID
    object_id: uuid.UUID
    rol: str

    @field_validator("rol")
    @classmethod
    def _v_rol(cls, v: str) -> str:
        # LI051 — via de gedeelde tekst-validator (blok A/B: NFC + nul-/stuurteken-weigering).
        # Een rol is een enkelregelige sleutel-aanduiding.
        return _verplichte_tekst(v, "rol", 60)


class RoltoewijzingUit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    toewijzing_id: uuid.UUID
    rol: str
    rol_label: str
    # Object-zijde (lijst voor één object): partij-velden gevuld.
    partij_id: uuid.UUID | None = None
    partij_naam: str | None = None
    partij_aard: str | None = None
    # Partij-zijde (lijst voor één partij): object-velden gevuld.
    object_id: uuid.UUID | None = None
    object_naam: str | None = None
    object_type: str | None = None
