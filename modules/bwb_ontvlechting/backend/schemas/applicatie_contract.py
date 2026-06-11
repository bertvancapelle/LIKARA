"""Pydantic v2-schemas voor de koppeltabel ApplicatieContract (ADR-020 Besluit 5).

Precies één `relatie_rol` per koppeling (catalogus-dimensie `relatie_rol`, app-side
gevalideerd). Plus de twee read-only overzicht-items: app → gekoppelde contracten en
contract → gekoppelde applicaties (elk met de rol, geresolveerd naar label).
"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from models.models import ContractType, LifecycleStatus
from schemas.applicatie import _verplichte_tekst


class ApplicatieContractCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applicatie_id: uuid.UUID
    contract_id: uuid.UUID
    relatie_rol: str

    @field_validator("relatie_rol")
    @classmethod
    def _v_rol(cls, v: str) -> str:
        return _verplichte_tekst(v, "relatie_rol", 60)


class ApplicatieContractUpdate(BaseModel):
    """Alleen de rol is wijzigbaar; de FK's (applicatie/contract) zijn immutabel."""

    model_config = ConfigDict(extra="forbid")

    relatie_rol: str

    @field_validator("relatie_rol")
    @classmethod
    def _v_rol(cls, v: str) -> str:
        return _verplichte_tekst(v, "relatie_rol", 60)


class ApplicatieContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    applicatie_id: uuid.UUID
    contract_id: uuid.UUID
    relatie_rol: str
    relatie_rol_label: str
    created_at: datetime
    updated_at: datetime


class ContractVoorApplicatie(BaseModel):
    """Item van 'app → waar valt hij onder': het gekoppelde contract + rol.
    `begindatum`/`einddatum` (CD044 §0b) voeden o.a. het context-paneel bij categorie 8."""

    koppeling_id: uuid.UUID
    contract_id: uuid.UUID
    contractnaam: str
    contracttype: ContractType
    leverancier_id: uuid.UUID
    leverancier_naam: str
    begindatum: date | None
    einddatum: date | None
    relatie_rol: str
    relatie_rol_label: str


class ApplicatieVoorContract(BaseModel):
    """Item van 'contract → welke applicaties': de gekoppelde applicatie + rol.
    `lifecycle_status` (CD044 §0a) toont de gereedheid van de app naast het contract."""

    koppeling_id: uuid.UUID
    applicatie_id: uuid.UUID
    applicatie_naam: str
    lifecycle_status: LifecycleStatus
    relatie_rol: str
    relatie_rol_label: str
