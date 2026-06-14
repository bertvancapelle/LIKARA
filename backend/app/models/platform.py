"""Platform-modellen (ADR-012) — NIET tenant-scoped, GEEN RLS.

De `tenant`-tabel is het platform-register van tenants. Hij wordt uitsluitend
via het platform-domein (cd_platform) benaderd; tenant-accounts (cd_app) hebben
er geen toegang toe. Het aanmaken van een tenant-record raakt geen
tenant-gescopete data — een nieuwe tenant start leeg.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.audit import AuditActie, auditactie_enum
from app.models.base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    naam: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'actief'")
    )


class PlatformAuditLog(Base):
    """ADR-006 — platform-breed audit-record (GEEN RLS, eigen hash-keten, append-only).

    Onwijzigbaar via grants (SELECT/INSERT) + BEFORE UPDATE/DELETE-trigger (migratie
    0010). `entiteit_id` is **text** (polymorf/koppelingsloos): draagt zowel UUID's
    (Tenant) als integer-catalogus-PK's (`componentconfig_optie`/`contractconfig_optie`)
    als string (ADR-006 v2-verfijning). Records worden door de centrale capture-hook
    geschreven; dit model dient de lees-zijde."""

    __tablename__ = "platform_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tijdstip: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actor_sub: Mapped[str] = mapped_column(Text, nullable=False)
    actor_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    entiteit_type: Mapped[str] = mapped_column(Text, nullable=False)
    entiteit_id: Mapped[str] = mapped_column(Text, nullable=False)
    actie: Mapped[AuditActie] = mapped_column(auditactie_enum, nullable=False)
    wijziging: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correlatie_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    record_hash: Mapped[str] = mapped_column(Text, nullable=False)
    vorige_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
