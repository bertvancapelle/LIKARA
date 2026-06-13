"""ADR-022 Wijziging W1 — tenant-eigendom van de vragenset (pre-productie, géén datamigratie).

Revision ID: 0008_adr022_w1_tenant_vragenset
Revises: 0007_adr022_beoordelingsprofiel
Create Date: 2026-06-13

`checklistvraag` (+ `checklistvraag_optie`) worden **tenant-scoped** (RLS + FORCE),
eigendom van de tenant met volledige CRUD via `cd_app`. Identiteit van een vraag:
`UNIQUE(tenant_id, componenttype, code)`; `UNIQUE(tenant_id, id)` is het composiet-
FK-target. Kind-FK's (`checklistscore`, `checklistvraag_optie`) worden composiet
`(tenant_id, checklistvraag_id)` → `checklistvraag(tenant_id, id)` — het schema dwingt
tenant-gelijkheid af (Knoop 1). `checklistvraag.actief` (default true) draagt de
soft-deactivatie. Grants flippen van `cd_platform`-CRUD naar `cd_app`-CRUD onder RLS.

Pre-productie: de vragenset is tenant-data geworden → `TRUNCATE checklistvraag CASCADE`
(wist opties/scores/blokkades) en `dev_seed_testdata.py` herseedt de baseline **per
tenant** als `cd_app`. `platform_init` zaait deze tabellen niet meer.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_adr022_w1_tenant_vragenset"
down_revision: Union[str, Sequence[str], None] = "0007_adr022_beoordelingsprofiel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RLS_TABELLEN = ["checklistvraag", "checklistvraag_optie"]


def upgrade() -> None:
    # --- (a) tenant-laag legen (pre-prod) — TRUNCATE vóór het droppen van de FK's,
    # zodat de cascade nog langs de kind-tabellen loopt: checklistvraag CASCADE →
    # checklistvraag_optie, checklistscore (→ blokkade). Daarna pas de FK's los. ---
    op.execute("TRUNCATE checklistvraag CASCADE")
    op.execute("ALTER TABLE checklistscore DROP CONSTRAINT IF EXISTS checklistscore_checklistvraag_id_fkey")
    op.execute("ALTER TABLE checklistvraag_optie DROP CONSTRAINT IF EXISTS checklistvraag_optie_checklistvraag_id_fkey")

    # --- (b) checklistvraag: tenant-scoped + actief + nieuwe uniciteit/target ---
    op.add_column("checklistvraag", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.add_column("checklistvraag", sa.Column("actief", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    op.drop_constraint("uq_checklistvraag_type_code", "checklistvraag", type_="unique")
    op.create_unique_constraint("uq_checklistvraag_type_code", "checklistvraag", ["tenant_id", "componenttype", "code"])
    op.create_unique_constraint("uq_checklistvraag_tenant_id", "checklistvraag", ["tenant_id", "id"])

    # --- (c) checklistvraag_optie: tenant-scoped + composiet-FK + uniciteit ---
    op.add_column("checklistvraag_optie", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.drop_index("ix_checklistvraag_optie_vraag", table_name="checklistvraag_optie")
    op.drop_constraint("uq_checklistvraag_optie", "checklistvraag_optie", type_="unique")
    op.create_unique_constraint(
        "uq_checklistvraag_optie", "checklistvraag_optie", ["tenant_id", "checklistvraag_id", "optie_sleutel"]
    )
    op.create_foreign_key(
        "fk_checklistvraag_optie_vraag", "checklistvraag_optie", "checklistvraag",
        ["tenant_id", "checklistvraag_id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.create_index(
        "ix_checklistvraag_optie_vraag", "checklistvraag_optie", ["tenant_id", "checklistvraag_id"]
    )

    # --- (d) checklistscore: composiet-FK naar de tenant-scoped vraag (geen cascade) ---
    op.create_foreign_key(
        "fk_checklistscore_vraag", "checklistscore", "checklistvraag",
        ["tenant_id", "checklistvraag_id"], ["tenant_id", "id"],
    )

    # --- (e) RLS + FORCE + policy + grants-flip ---
    for tabel in _RLS_TABELLEN:
        op.execute(f"ALTER TABLE {tabel} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabel} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {tabel} "
            f"USING (tenant_id = current_setting('app.tenant_id')::uuid)"
        )
        op.execute(f"REVOKE ALL ON {tabel} FROM cd_platform")
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabel} TO cd_app")

    op.create_index("ix_checklistvraag_tenant_type", "checklistvraag", ["tenant_id", "componenttype"])


def downgrade() -> None:
    """Best effort terug naar 0007 (pre-prod, géén data-herstel)."""
    op.execute("TRUNCATE checklistvraag CASCADE")
    op.drop_index("ix_checklistvraag_tenant_type", table_name="checklistvraag")

    for tabel in _RLS_TABELLEN:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {tabel}")
        op.execute(f"ALTER TABLE {tabel} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabel} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE INSERT, UPDATE, DELETE ON {tabel} FROM cd_app")
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON {tabel} TO cd_platform")

    # checklistscore composiet-FK weg
    op.execute("ALTER TABLE checklistscore DROP CONSTRAINT IF EXISTS fk_checklistscore_vraag")
    op.create_foreign_key(
        "checklistscore_checklistvraag_id_fkey", "checklistscore", "checklistvraag",
        ["checklistvraag_id"], ["id"],
    )

    # checklistvraag_optie terug naar enkelvoudig
    op.execute("ALTER TABLE checklistvraag_optie DROP CONSTRAINT IF EXISTS fk_checklistvraag_optie_vraag")
    op.drop_index("ix_checklistvraag_optie_vraag", table_name="checklistvraag_optie")
    op.drop_constraint("uq_checklistvraag_optie", "checklistvraag_optie", type_="unique")
    op.create_unique_constraint("uq_checklistvraag_optie", "checklistvraag_optie", ["checklistvraag_id", "optie_sleutel"])
    op.create_foreign_key(
        "checklistvraag_optie_checklistvraag_id_fkey", "checklistvraag_optie", "checklistvraag",
        ["checklistvraag_id"], ["id"],
    )
    op.create_index("ix_checklistvraag_optie_vraag", "checklistvraag_optie", ["checklistvraag_id"])
    op.drop_column("checklistvraag_optie", "tenant_id")

    # checklistvraag terug
    op.drop_constraint("uq_checklistvraag_tenant_id", "checklistvraag", type_="unique")
    op.drop_constraint("uq_checklistvraag_type_code", "checklistvraag", type_="unique")
    op.create_unique_constraint("uq_checklistvraag_type_code", "checklistvraag", ["componenttype", "code"])
    op.drop_column("checklistvraag", "actief")
    op.drop_column("checklistvraag", "tenant_id")
