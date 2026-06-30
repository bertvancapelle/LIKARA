"""Hernoem audit-trigger-functie cd_audit_append_only -> lk_audit_append_only (LI050 / S7).

Laatste cd_-identifier in het schema. ADR-006: de audit-trail blijft append-only en
hash-geketend — alleen de FUNCTIE-NAAM wijzigt, de body is byte-identiek. PostgreSQL
voert DDL transactioneel uit, dus er is geen moment zonder append-only-bescherming:
binnen één transactie wordt de nieuwe functie aangemaakt, elke trigger omgehangen, en
pas daarna de oude functie verwijderd.

De oorspronkelijke definitie in 0010_adr006_audit_trail blijft als historisch record
staan (toegepaste migratie = historie, niet bewerken).

Revision ID: 0044_lk_audit_append_only
Revises: 0043_adr030_contract_band
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0044_lk_audit_append_only"
down_revision: Union[str, Sequence[str], None] = "0043_adr030_contract_band"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABELLEN = ("audit_log", "platform_audit_log")


def upgrade() -> None:
    # 1. nieuwe functie — body byte-identiek aan 0010, alleen de naam wijzigt
    op.execute(
        """
        CREATE OR REPLACE FUNCTION lk_audit_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit-trail is append-only: % op % is niet toegestaan',
                TG_OP, TG_TABLE_NAME;
        END;
        $$;
        """
    )
    # 2. elke trigger omhangen naar de nieuwe functie
    for tabel in _TABELLEN:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tabel}_append_only ON {tabel}")
        op.execute(
            f"CREATE TRIGGER trg_{tabel}_append_only "
            f"BEFORE UPDATE OR DELETE ON {tabel} "
            f"FOR EACH ROW EXECUTE FUNCTION lk_audit_append_only()"
        )
    # 3. pas dán de oude functie verwijderen (triggers wijzen er niet meer naar)
    op.execute("DROP FUNCTION IF EXISTS cd_audit_append_only()")


def downgrade() -> None:
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
    for tabel in _TABELLEN:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tabel}_append_only ON {tabel}")
        op.execute(
            f"CREATE TRIGGER trg_{tabel}_append_only "
            f"BEFORE UPDATE OR DELETE ON {tabel} "
            f"FOR EACH ROW EXECUTE FUNCTION cd_audit_append_only()"
        )
    op.execute("DROP FUNCTION IF EXISTS lk_audit_append_only()")
