"""Pydantic v2-schemas — procesvervulling (ADR-042 slice 3).

`ProcesvervullingAanmaken` = invoer (component_id, proces_id, applicatiefunctie +
optionele toelichting), `extra='forbid'`. `ProcesvervullingUit` = verrijkte uitvoer
(vervulling_id + functie-label + de geresolveerde namen). Welke verrijkings-velden gevuld
zijn hangt af van de leesrichting (proces-zijde vult de component-velden; component-zijde
vult de proces-velden) — daarom zijn ze optioneel. Spiegel van `schemas/roltoewijzing`.
"""
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _optionele_tekst, _verplichte_tekst


class ProcesvervullingAanmaken(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: uuid.UUID
    proces_id: uuid.UUID
    applicatiefunctie: str
    toelichting: str | None = None

    @field_validator("applicatiefunctie")
    @classmethod
    def _v_functie(cls, v: str) -> str:
        # LI051 — via de gedeelde tekst-validator (blok A/B); applicatiefunctie is een
        # enkelregelige catalogus-sleutel.
        return _verplichte_tekst(v, "applicatiefunctie", 60)

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000, meerregelig=True)


class ProcesvervullingWijzigen(BaseModel):
    """Partieel — alleen de KENMERK-velden zijn wijzigbaar (applicatiefunctie +
    toelichting); component en proces zijn de ankers van het feit en staan bewust
    niet in dit schema (extra='forbid' weert ze — regel-acties-patroon)."""

    model_config = ConfigDict(extra="forbid")

    applicatiefunctie: str | None = None
    toelichting: str | None = None

    @field_validator("applicatiefunctie")
    @classmethod
    def _v_functie(cls, v: str | None) -> str | None:
        # LI051 — via de gedeelde tekst-validator (blok A/B); enkelregelige catalogus-sleutel.
        # In Update mag het veld ontbreken (partieel), maar niet leeg zijn als het meekomt.
        return None if v is None else _verplichte_tekst(v, "applicatiefunctie", 60)

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000, meerregelig=True)


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
    # Slice 5 — alleen gevuld in de roll-up-lezing: het herkomst-pad (proces-namen vanaf
    # het directe deelproces t/m het herkomst-proces; de opgevraagde wortel zelf niet) +
    # de tak (het id van dat directe deelproces — de stabiele groepeersleutel; namen
    # kunnen botsen, ids niet).
    proces_pad: list[str] | None = None
    tak_id: uuid.UUID | None = None


class OrganisatieProcesComponent(BaseModel):
    """Slice 5 — brug-component in het afgeleide organisatie-procesbeeld."""

    model_config = ConfigDict(from_attributes=True)

    component_id: uuid.UUID
    component_naam: str
    componenttype: str
    componenttype_label: str


class OrganisatieProcesUit(BaseModel):
    """Slice 5 — afgeleid beeld per proces: "dit proces steunt op N componenten van deze
    organisatie" (eigendom + geregistreerd gebruik samengenomen; dedupe per proces).
    Puur lezen — er hoort geen invoer-schema bij."""

    model_config = ConfigDict(from_attributes=True)

    proces_id: uuid.UUID
    proces_naam: str
    proces_ouder_naam: str | None = None
    component_aantal: int
    componenten: list[OrganisatieProcesComponent]
