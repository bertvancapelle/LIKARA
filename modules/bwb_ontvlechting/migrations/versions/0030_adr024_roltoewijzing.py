"""ADR-024 slice 2b — tabel `roltoewijzing` (partij vervult rol op object).

Revision ID: 0030_adr024_roltoewijzing
Revises: 0029_adr024_beheerrol
Create Date: 2026-06-18

Eigen tenant-scoped registratie-tabel (GEEN element-subtype — een toewijzing is een feit, geen
ArchiMate-element). Uniciteit `(tenant_id, partij_id, object_id, rol)`: dezelfde rol niet dubbel,
maar wél meerdere rollen per (partij, object) en meerdere partijen met dezelfde rol op één object.

- `partij_id`/`object_id` → composiet-FK `(tenant_id, <kol>) → element(tenant_id, id)` ON DELETE
  CASCADE (toewijzing verdwijnt met de partij of het object);
- `rol` = tekst-sleutel naar de `beheerrol`-catalogus (app-side geborgd; geen harde FK);
- FORCE RLS + `tenant_isolation`-policy + REVOKE/GRANT conform db-skill;
- reverse-lookup-indexen (object → toewijzingen; partij → toewijzingen).

Engine onaangeroerd — registratief, geen lifecycle/score/blokkade.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030_adr024_roltoewijzing"
down_revision: Union[str, Sequence[str], None] = "0029_adr024_beheerrol"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roltoewijzing",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partij_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "partij_id", "object_id", "rol", name="uq_roltoewijzing"),
    )
    op.create_index("ix_roltoewijzing_tenant", "roltoewijzing", ["tenant_id"])
    op.create_index("ix_roltoewijzing_tenant_object", "roltoewijzing", ["tenant_id", "object_id"])
    op.create_index("ix_roltoewijzing_tenant_partij", "roltoewijzing", ["tenant_id", "partij_id"])
    op.create_foreign_key(
        "fk_roltoewijzing_partij", "roltoewijzing", "element",
        ["tenant_id", "partij_id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_roltoewijzing_object", "roltoewijzing", "element",
        ["tenant_id", "object_id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.execute("ALTER TABLE roltoewijzing ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE roltoewijzing FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON roltoewijzing "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON roltoewijzing FROM cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON roltoewijzing TO cd_app")


def downgrade() -> None:
    op.drop_table("roltoewijzing")
