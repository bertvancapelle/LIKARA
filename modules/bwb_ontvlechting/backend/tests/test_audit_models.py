"""ADR-006 Fase A — audit-modellen + enum (offline, geen DB)."""
import uuid


def test_auditactie_enum_waarden():
    from app.core.audit import AuditActie

    assert [e.value for e in AuditActie] == ["create", "update", "delete", "derive"]


def test_audit_log_model_kolommen_en_tenant_scoped():
    from models.models import AuditLog

    assert AuditLog.__tablename__ == "audit_log"
    kols = AuditLog.__table__.columns
    # Tenant-scoped: tenant_id aanwezig; entiteit_id = uuid (alle tenant-PK's zijn uuid).
    assert "tenant_id" in kols
    assert str(kols["entiteit_id"].type) == "UUID"
    for verplicht in (
        "id", "tijdstip", "actor_sub", "actor_email", "entiteit_type", "entiteit_id",
        "actie", "wijziging", "correlatie_id", "record_hash", "vorige_hash",
    ):
        assert verplicht in kols


def test_platform_audit_log_entiteit_id_is_text_en_geen_tenant():
    from app.models.platform import PlatformAuditLog

    assert PlatformAuditLog.__tablename__ == "platform_audit_log"
    kols = PlatformAuditLog.__table__.columns
    # v2-verfijning: entiteit_id = text (draagt UUID's én int-catalogus-PK's), GEEN tenant_id.
    assert "tenant_id" not in kols
    assert str(kols["entiteit_id"].type) in ("TEXT", "VARCHAR")


def test_auditactie_enum_typenaam():
    from app.core.audit import auditactie_enum

    assert auditactie_enum.name == "auditactie_enum"
