"""ADR-023 Fase E (E3) — Deliverable: op te leveren resultaat (additief).

Revision ID: 0021_adr023_deliverable
Revises: 0020_adr023_workpackage
Create Date: 2026-06-15

Voegt de subtype-tabel `deliverable` toe (element-subtype: shared-PK composiet-FK →
element, FORCE RLS). De realisatieketen (work_package → deliverable → plateau) loopt via
het bestaande relatietype `realization` in het unified relatiemodel — géén schema hier.

`element_type_enum` bevat 'deliverable' al sinds 0011 → geen enum-wijziging. Geen
datamigratie (er is geen bestaande deliverable-data).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_adr023_deliverable"
down_revision: Union[str, Sequence[str], None] = "0020_adr023_workpackage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deliverable",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("naam", sa.String(255), nullable=False),
        sa.Column("toelichting", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_deliverable_tenant", "deliverable", ["tenant_id"])
    op.create_foreign_key(
        "fk_deliverable_element", "deliverable", "element",
        ["tenant_id", "id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.execute("ALTER TABLE deliverable ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE deliverable FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON deliverable "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON deliverable FROM cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON deliverable TO cd_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON deliverable")
    op.drop_constraint("fk_deliverable_element", "deliverable", type_="foreignkey")
    op.drop_index("ix_deliverable_tenant", table_name="deliverable")
    op.drop_table("deliverable")
