"""ADR-023 Fase B-core — unified getypeerd relatiemodel (additief).

Revision ID: 0012_adr023_relatiemodel
Revises: 0011_adr023_element_identiteit
Create Date: 2026-06-14

Eén relatie-tabel met echte composiet-FK's (tenant+id) naar de element-identiteit
(Besluit 1/12 — cross-tenant structureel uitgesloten); `relatietype` uit de catalogus
(dim `archimate_relatie`); kenmerken in jsonb (OK-2); `UNIQUE(tenant, bron, doel,
relatietype)`; CHECK `bron≠doel`; FORCE RLS. Additief: de bestaande koppeling/
component_structuur/component_contract blijven (datamigratie + drop volgt in B-migrate).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_adr023_relatiemodel"
down_revision: Union[str, Sequence[str], None] = "0011_adr023_element_identiteit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "relatie",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bron_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relatietype", sa.String(40), nullable=False),
        sa.Column("kenmerken", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("omschrijving", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("bron_id <> doel_id", name="ck_relatie_bron_ne_doel"),
        sa.UniqueConstraint("tenant_id", "bron_id", "doel_id", "relatietype", name="uq_relatie"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "bron_id"], ["element.tenant_id", "element.id"],
            name="fk_relatie_bron_element", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "doel_id"], ["element.tenant_id", "element.id"],
            name="fk_relatie_doel_element", ondelete="CASCADE",
        ),
    )
    op.create_index("ix_relatie_tenant_bron", "relatie", ["tenant_id", "bron_id"])
    op.create_index("ix_relatie_tenant_doel", "relatie", ["tenant_id", "doel_id"])
    op.create_index("ix_relatie_tenant_type", "relatie", ["tenant_id", "relatietype"])

    op.execute("ALTER TABLE relatie ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE relatie FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON relatie "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON relatie FROM cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON relatie TO cd_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON relatie")
    op.drop_index("ix_relatie_tenant_type", table_name="relatie")
    op.drop_index("ix_relatie_tenant_doel", table_name="relatie")
    op.drop_index("ix_relatie_tenant_bron", table_name="relatie")
    op.drop_table("relatie")
