"""Pydantic v2-schemas — functievervulling (ADR-049, gate 2a).

`FunctievervullingAanmaken` = invoer (component_id, functie_id, optioneel ouder_functie_id +
toelichting), `extra='forbid'`. Leeg `ouder_functie_id` = GROF ("geldt overal"); gevuld = FIJN
(déze plek). De as is KAAL — géén applicatiefunctie/werkwoord (ADR-049 besluit 3).

`FunctievervullingUit` = één koppelregel na aanmaak (verrijkt). `PlekDekkingUit` = de LEESREGEL-
uitkomst per plek: "welke componenten dragen déze plek" mét `herkomst` (fijn verdringt grof —
ADR-049 besluit 1/5); consumenten lezen dit, ze rekenen niet zelf.
"""
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _optionele_tekst


class FunctievervullingAanmaken(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: uuid.UUID
    functie_id: uuid.UUID
    # Leeg = grove koppeling (geldt overal); gevuld = fijne koppeling op díé plek (onder deze ouder).
    ouder_functie_id: uuid.UUID | None = None
    toelichting: str | None = None

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)


class DekkingComponent(BaseModel):
    """Eén dragend component binnen de dekking van een plek."""

    model_config = ConfigDict(from_attributes=True)

    vervulling_id: uuid.UUID
    component_id: uuid.UUID
    component_naam: str
    componenttype: str
    componenttype_label: str
    toelichting: str | None = None


class FunctievervullingUit(DekkingComponent):
    """Eén koppelregel ná aanmaak, mét plek-context + herkomst (grof/fijn)."""

    functie_id: uuid.UUID
    ouder_functie_id: uuid.UUID | None = None
    herkomst: str  # 'grof' (geldt overal) | 'fijn' (deze plek)
    verklaard_door_naam: str | None = None


class PlekDekkingUit(BaseModel):
    """De leesregel-uitkomst voor één plek: fijn verdringt grof (ADR-049). `herkomst` = 'fijn'
    als deze plek een eigen antwoord draagt, anders 'grof' (het geldt-overal-antwoord van de
    functie). `componenten` is nooit leeg (plekken zonder dekking staan niet in de lijst).

    De verdringing benoemt zichzelf (LI041): op een fijne plek draagt `verdrongen` het grove
    antwoord dat hier verborgen is (read-only — het bestaat nog, ADR-049 besluit 1; géén actie
    op deze plek). Op een grove plek tellen `grof_totaal_plekken` (N) en `grof_geldt_op` (M) de
    reikwijdte voor het getelde label — beide uit dezelfde afleiding, nooit opgeslagen."""

    model_config = ConfigDict(from_attributes=True)

    functie_id: uuid.UUID
    ouder_functie_id: uuid.UUID | None = None
    herkomst: str
    componenten: list[DekkingComponent]
    # LI041 — de verdringing benoemt zichzelf.
    verdrongen: list[DekkingComponent] = []
    grof_totaal_plekken: int | None = None
    grof_geldt_op: int | None = None
