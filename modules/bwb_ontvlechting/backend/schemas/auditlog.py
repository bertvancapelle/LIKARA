"""Pydantic v2 lees-schemas voor het audit-spoor (ADR-006 Fase E).

Read-only: het audit-spoor wordt door de capture-hook geschreven, nooit via de API.
De lijst levert **correlatie-gegroepeerde gebeurtenissen** (driver + afgeleide gevolgen),
zodat #14 het scherm hierop kan bouwen zonder herontwerp.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditRecordRead(BaseModel):
    """Eén auditrecord (één rij in `audit_log`)."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    tijdstip: datetime
    actor_sub: str
    actor_email: str | None = None
    actor_naam: str | None = None  # ADR-029 Fase 3a — sub → persoon.naam, anders e-mail-fallback (transient)
    entiteit_type: str
    entiteit_id: uuid.UUID
    actie: str
    wijziging: dict | None = None
    correlatie_id: uuid.UUID
    record_hash: str
    vorige_hash: str | None = None


class AuditGebeurtenis(BaseModel):
    """Eén handeling = alle records met hetzelfde `correlatie_id` (driver + afgeleide
    gevolgen). `tijdstip` is het ankermoment (de driver); `records` staat chronologisch
    (driver eerst)."""

    correlatie_id: uuid.UUID
    tijdstip: datetime
    actor_sub: str | None = None
    actor_email: str | None = None
    actor_naam: str | None = None  # ADR-029 Fase 3a — geresolveerde naam (driver), e-mail-fallback
    records: list[AuditRecordRead]


class AuditLogPagina(BaseModel):
    items: list[AuditGebeurtenis]
    volgende_cursor: str | None = None
