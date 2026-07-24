"""Pydantic v2-schemas — component-klaarverklaring (ADR-027).

Gescheiden Create (aanmaken = status `klaar`) + StatusWijzig (klaar↔open), beide met `extra='forbid'`
en een verplichte, niet-lege `reden`. Server-velden (`id`, `tenant_id`, `status`-default,
`verklaard_door`, `verklaard_op`, timestamps) staan NOOIT in de invoer — die stempelt de service.
Klaarverklaring is op componentniveau (geen categorie-dimensie).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _verplichte_tekst


def _verplichte_reden(v: str) -> str:
    # LI051 — via de gedeelde tekst-validator (blok A/B: NFC-normalisatie + nul-/stuurteken-
    # weigering). Een reden is een toelichting → meerregelig (alinea's toegestaan).
    return _verplichte_tekst(v, "reden", 2000, meerregelig=True)


class KlaarverklaringCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: uuid.UUID
    reden: str

    @field_validator("reden")
    @classmethod
    def _v_reden(cls, v: str) -> str:
        return _verplichte_reden(v)


class KlaarverklaringStatusWijzig(BaseModel):
    """Symmetrische statushandeling (klaar↔open); nieuwe status + verplichte reden."""

    model_config = ConfigDict(extra="forbid")

    status: str  # 'klaar' | 'open' — service valideert tegen de enum
    reden: str

    @field_validator("status")
    @classmethod
    def _v_status(cls, v: str) -> str:
        if v not in ("klaar", "open"):
            raise ValueError("status moet 'klaar' of 'open' zijn")
        return v

    @field_validator("reden")
    @classmethod
    def _v_reden(cls, v: str) -> str:
        return _verplichte_reden(v)


class KlaarverklaringRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    component_id: uuid.UUID
    status: str
    reden: str
    verklaard_door: str | None  # ADR-029: voortaan de e-mail-fallback (historisch: de oude string)
    # ADR-029 Fase 3b — read-side geresolveerde naam (sub → persoon.naam) of e-mail-fallback (transient).
    verklaard_door_naam: str | None = None
    verklaard_op: datetime
    # ADR-052 slice 3 — bevroren snapshot: verplichte feiten die bij het verklaren open stonden.
    open_feiten: list[str] = []
    created_at: datetime
    updated_at: datetime
