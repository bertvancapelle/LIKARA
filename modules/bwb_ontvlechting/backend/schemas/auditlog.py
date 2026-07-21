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
    entiteit_naam: str | None = None  # LI019 — geresolveerde objectnaam (transient; None = verwijderd/naamloos)
    actie: str
    wijziging: dict | None = None
    correlatie_id: uuid.UUID
    record_hash: str
    vorige_hash: str | None = None


class AuditGebeurtenis(BaseModel):
    """Eén handeling = alle records met hetzelfde `correlatie_id`. `tijdstip` is het
    ankermoment; `records` staat chronologisch.

    LI048 — de SAMENVATTING (`entiteit_type`/`entiteit_naam`/`actie`) wordt door de service
    bepaald en niet door de UI afgeleid. De driver is de eerste record die iets inhoudelijks
    zegt; een supertype-rij die alleen het discriminator-veld draagt wordt overgeslagen. Zou de
    UI zelf `records[0]` nemen, dan lopen beide kanten uiteen zodra dit verandert."""

    correlatie_id: uuid.UUID
    tijdstip: datetime
    actor_sub: str | None = None
    actor_email: str | None = None
    actor_naam: str | None = None  # ADR-029 Fase 3a — geresolveerde naam (driver), e-mail-fallback
    entiteit_type: str | None = None
    entiteit_id: uuid.UUID | None = None
    # De naam van TOEN (uit de vastgelegde wijziging); bij een verwijdering nooit de huidige naam.
    entiteit_naam: str | None = None
    actie: str | None = None
    # Aantal BETEKENISDRAGENDE gevolgen naast de driver — betekenisloze supertype-rijen tellen niet.
    aantal_afgeleid: int = 0
    records: list[AuditRecordRead]


class AuditLogPagina(BaseModel):
    items: list[AuditGebeurtenis]
    volgende_cursor: str | None = None
