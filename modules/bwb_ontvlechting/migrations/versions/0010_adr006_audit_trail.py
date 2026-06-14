"""ADR-006 — audit-trail (append-only wijzigingsspoor).

Revision ID: 0010_adr006_audit_trail
Revises: 0009_adr022_e_checklist_dragend
Create Date: 2026-06-14

Twee onwijzigbare logboeken (Besluit 4):
- `audit_log` — tenant-scoped (FORCE RLS), `entiteit_id uuid`, hash-keten per tenant;
- `platform_audit_log` — platform-breed (GEEN RLS), `entiteit_id text` (polymorf,
  koppelingsloos: draagt zowel UUID's als integer-catalogus-PK's), eigen hash-keten.

Onwijzigbaarheid is structureel (Besluit 5): (a) grants beperkt tot SELECT+INSERT
(geen UPDATE/DELETE), (b) een `BEFORE UPDATE OR DELETE`-trigger die `RAISE EXCEPTION`
doet — dekt ook owner-/migratiepaden.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_adr006_audit_trail"
down_revision: Union[str, Sequence[str], None] = "0009_adr022_e_checklist_dragend"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    auditactie = postgresql.ENUM(
        "create", "update", "delete", "derive", name="auditactie_enum", create_type=False
    )
    auditactie.create(op.get_bind(), checkfirst=True)

    # --- tenant-scoped audit_log (FORCE RLS, entiteit_id uuid) ------------------
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tijdstip", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("actor_sub", sa.Text(), nullable=False),
        sa.Column("actor_email", sa.Text(), nullable=True),
        sa.Column("entiteit_type", sa.Text(), nullable=False),
        sa.Column("entiteit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actie", auditactie, nullable=False),
        sa.Column("wijziging", postgresql.JSONB(), nullable=True),
        sa.Column("correlatie_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_hash", sa.Text(), nullable=False),
        sa.Column("vorige_hash", sa.Text(), nullable=True),
    )
    op.create_index("ix_audit_log_tenant", "audit_log", ["tenant_id"])
    op.create_index("ix_audit_log_correlatie", "audit_log", ["correlatie_id"])
    op.create_index("ix_audit_log_entiteit", "audit_log", ["entiteit_type", "entiteit_id"])

    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON audit_log "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    # Append-only (Besluit 5a): cd_app mag uitsluitend lezen + invoegen. REVOKE ALL is
    # noodzakelijk omdat init-db `ALTER DEFAULT PRIVILEGES ... GRANT ALL ON TABLES TO
    # cd_app` elke nieuwe tabel ALL geeft — inclusief TRUNCATE, dat de row-trigger (5b)
    # NIET vangt. Pas na REVOKE is de beperkte grant effectief.
    op.execute("REVOKE ALL ON audit_log FROM cd_app")
    op.execute("GRANT SELECT, INSERT ON audit_log TO cd_app")

    # --- platform-breed platform_audit_log (GEEN RLS, entiteit_id text) ---------
    op.create_table(
        "platform_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tijdstip", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("actor_sub", sa.Text(), nullable=False),
        sa.Column("actor_email", sa.Text(), nullable=True),
        sa.Column("entiteit_type", sa.Text(), nullable=False),
        # Polymorf/koppelingsloos: draagt UUID's én integer-catalogus-PK's als string.
        sa.Column("entiteit_id", sa.Text(), nullable=False),
        sa.Column("actie", auditactie, nullable=False),
        sa.Column("wijziging", postgresql.JSONB(), nullable=True),
        sa.Column("correlatie_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_hash", sa.Text(), nullable=False),
        sa.Column("vorige_hash", sa.Text(), nullable=True),
    )
    op.create_index("ix_platform_audit_log_correlatie", "platform_audit_log", ["correlatie_id"])
    op.create_index("ix_platform_audit_log_entiteit", "platform_audit_log",
                    ["entiteit_type", "entiteit_id"])
    # Platform-endpoints (cd_platform) én de platform-init/seed (cd_app, geen RLS)
    # schrijven hier — append-only. REVOKE ALL FROM cd_app eerst (default-ALL, zie boven);
    # cd_app behoudt alleen INSERT (platform_init seedt als cd_app), cd_platform SELECT+INSERT.
    op.execute("REVOKE ALL ON platform_audit_log FROM cd_app")
    op.execute("GRANT SELECT, INSERT ON platform_audit_log TO cd_platform")
    op.execute("GRANT INSERT ON platform_audit_log TO cd_app")

    # --- onwijzigbaarheids-backstop: trigger weigert UPDATE/DELETE (Besluit 5b) -
    op.execute(
        """
        CREATE OR REPLACE FUNCTION cd_audit_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit-trail is append-only: % op % is niet toegestaan',
                TG_OP, TG_TABLE_NAME;
        END;
        $$;
        """
    )
    for tabel in ("audit_log", "platform_audit_log"):
        op.execute(
            f"CREATE TRIGGER trg_{tabel}_append_only "
            f"BEFORE UPDATE OR DELETE ON {tabel} "
            f"FOR EACH ROW EXECUTE FUNCTION cd_audit_append_only()"
        )


def downgrade() -> None:
    for tabel in ("audit_log", "platform_audit_log"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tabel}_append_only ON {tabel}")
    op.execute("DROP FUNCTION IF EXISTS cd_audit_append_only()")

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON audit_log")
    op.drop_index("ix_platform_audit_log_entiteit", table_name="platform_audit_log")
    op.drop_index("ix_platform_audit_log_correlatie", table_name="platform_audit_log")
    op.drop_table("platform_audit_log")
    op.drop_index("ix_audit_log_entiteit", table_name="audit_log")
    op.drop_index("ix_audit_log_correlatie", table_name="audit_log")
    op.drop_index("ix_audit_log_tenant", table_name="audit_log")
    op.drop_table("audit_log")
    postgresql.ENUM(name="auditactie_enum").drop(op.get_bind(), checkfirst=True)
