"""Pydantic v2-schemas — procesvervulling (ADR-042 slice 3).

`ProcesvervullingAanmaken` = invoer (component_id, proces_id, applicatiefunctie +
optionele toelichting), `extra='forbid'`. `ProcesvervullingUit` = verrijkte uitvoer
(vervulling_id + functie-label + de geresolveerde namen). Welke verrijkings-velden gevuld
zijn hangt af van de leesrichting (proces-zijde vult de component-velden; component-zijde
vult de proces-velden) — daarom zijn ze optioneel. Spiegel van `schemas/roltoewijzing`.
"""
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _optionele_tekst


class ProcesvervullingAanmaken(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: uuid.UUID
    proces_id: uuid.UUID
    applicatiefunctie: str
    toelichting: str | None = None

    @field_validator("applicatiefunctie")
    @classmethod
    def _v_functie(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("applicatiefunctie is verplicht")
        if len(v) > 60:
            raise ValueError("applicatiefunctie is te lang")
        return v

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)


class ProcesvervullingUit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vervulling_id: uuid.UUID
    applicatiefunctie: str
    applicatiefunctie_label: str
    toelichting: str | None = None
    # Proces-zijde (lijst voor één proces): component-velden gevuld.
    component_id: uuid.UUID | None = None
    component_naam: str | None = None
    componenttype: str | None = None
    componenttype_label: str | None = None
    # Component-zijde (lijst voor één component): proces-velden gevuld.
    proces_id: uuid.UUID | None = None
    proces_naam: str | None = None
    # Procescontext (ADR-042 besluit 2): de ouder-naam voor de identiteit
    # "Aanvraag behandelen — Vergunningverlening"; None bij een top-level proces.
    proces_ouder_naam: str | None = None
