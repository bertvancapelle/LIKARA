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
    created_at: datetime
    updated_at: datetime
