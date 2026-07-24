"""Pydantic v2-schemas — component-bevinding "bewust geen" (ADR-052 slice 2).

`soort` ∈ {koppelingen, contract} (service valideert tegen de enum); `toelichting` optioneel.
Server-velden (`id`, `tenant_id`, `verklaard_door`/`verklaard_op`, timestamps) stempelt de service —
nooit in de invoer. `component_id` reist via het pad, niet in de body.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _optionele_tekst


def _optionele_toelichting(v):
    # LI051 — via de gedeelde tekst-validator (blok A/B: NFC + nul-/stuurteken-weigering).
    # Een toelichting is vrije tekst → meerregelig (alinea's toegestaan).
    return _optionele_tekst(v, 2000, meerregelig=True)


class BevindingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    soort: str  # 'koppelingen' | 'contract' — service valideert tegen de enum
    toelichting: str | None = None

    @field_validator("soort")
    @classmethod
    def _v_soort(cls, v: str) -> str:
        if v not in ("koppelingen", "contract"):
            raise ValueError("soort moet 'koppelingen' of 'contract' zijn")
        return v

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v):
        return _optionele_toelichting(v)


class BevindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    component_id: uuid.UUID
    soort: str
    verklaard_door: str | None  # ADR-029: e-mail-fallback
    verklaard_door_naam: str | None = None  # read-side geresolveerde naam (transient)
    verklaard_op: datetime
    toelichting: str | None = None
