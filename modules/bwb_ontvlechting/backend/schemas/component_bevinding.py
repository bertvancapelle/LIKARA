"""Pydantic v2-schemas — component-bevinding "bewust geen" (ADR-052 slice 2).

`soort` ∈ {koppelingen, contract} (service valideert tegen de enum); `toelichting` optioneel.
Server-velden (`id`, `tenant_id`, `verklaard_door`/`verklaard_op`, timestamps) stempelt de service —
nooit in de invoer. `component_id` reist via het pad, niet in de body.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


def _optionele_toelichting(v):
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    if len(v) > 2000:
        raise ValueError("toelichting mag maximaal 2000 tekens zijn")
    return v


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
