"""Pydantic v2-schemas voor het grove gebruiksfeit `organisatiegebruik` (ADR-036, stap A).

"Organisatie gebruikt applicatie" als op-zichzelf-vastlegbaar registratie-feit. Onvolledig
(alleen organisatie + applicatie) is een geldige toestand. `heeft_verfijning` = of er een
gebruikersgroep (afdeling) ónder dit feit hangt — read-only afgeleid.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrganisatiegebruikCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organisatie_id: uuid.UUID
    applicatie_id: uuid.UUID


class OrganisatiegebruikRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organisatie_id: uuid.UUID
    organisatie_naam: str | None = None
    applicatie_id: uuid.UUID
    # Read-only afgeleid: hangt er minstens één gebruikersgroep (verfijning) onder dit feit?
    heeft_verfijning: bool = False
    # ADR-046 stuk 2 — de bekende afdelingsnamen uit de verfijnende groepen (leeg =
    # "afdeling onbekend": de normale stand na een eerste workshop, geen fout).
    afdelingen: list[str] = []
    created_at: datetime
    updated_at: datetime


class OrganisatieComponentRead(BaseModel):
    """De applicaties die één organisatie gebruikt (grove feit → applicatie-component). Gedeelde
    rij-vorm met de gebruiker-context-componenten (`ContextComponentRead`) + de Landschapskaart-
    subgraaf, aangevuld met `verfijnd`: hangt er een afdeling/gebruikersgroep onder dit grove feit
    (False = grof-only, "nog niet verfijnd"). Read-only afgeleid."""

    model_config = ConfigDict(from_attributes=True)

    component_id: uuid.UUID
    component_naam: str
    componenttype: str
    verfijnd: bool = False
