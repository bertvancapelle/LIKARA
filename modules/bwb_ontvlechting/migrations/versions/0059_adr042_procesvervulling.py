"""ADR-042 slice 3 — procesvervulling: koppelregel component→proces (additief).

Revision ID: 0059_adr042_procesvervulling
Revises: 0058_adr042_appfunctie
Create Date: 2026-07-08

Eigen tenant-scoped registratie-feit (het roltoewijzing-recept, 0029/0030): uniek tripel
`(tenant, component, proces, applicatiefunctie)` — meerdere applicatiefuncties per
(component, proces) als losse regels; twee composiet-FK's → element (CASCADE: de regel
verdwijnt met het component of het proces). `applicatiefunctie` is een catalogus-sleutel
zonder harde FK (app-side gevalideerd op actief). Optionele `toelichting`. FORCE RLS +
tenant_isolation + grants lk_app. Engine onaangeroerd (geen lifecycle/profiel/score).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0059_adr042_procesvervulling"
down_revision: Union[str, Sequence[str], None] = "0058_adr042_appfunctie"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "procesvervulling",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proces_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applicatiefunctie", sa.String(60), nullable=False),
        sa.Column("toelichting", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "tenant_id", "component_id", "proces_id", "applicatiefunctie",
            name="uq_procesvervulling",
        ),
    )
    op.create_index("ix_procesvervulling_tenant", "procesvervulling", ["tenant_id"])
    op.create_index("ix_procesvervulling_tenant_component", "procesvervulling", ["tenant_id", "component_id"])
    op.create_index("ix_procesvervulling_tenant_proces", "procesvervulling", ["tenant_id", "proces_id"])
    op.create_foreign_key(
        "fk_procesvervulling_component", "procesvervulling", "element",
        ["tenant_id", "component_id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_procesvervulling_proces", "procesvervulling", "element",
        ["tenant_id", "proces_id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.execute("ALTER TABLE procesvervulling ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE procesvervulling FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON procesvervulling "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON procesvervulling FROM lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON procesvervulling TO lk_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON procesvervulling")
    op.drop_constraint("fk_procesvervulling_proces", "procesvervulling", type_="foreignkey")
    op.drop_constraint("fk_procesvervulling_component", "procesvervulling", type_="foreignkey")
    op.drop_index("ix_procesvervulling_tenant_proces", table_name="procesvervulling")
    op.drop_index("ix_procesvervulling_tenant_component", table_name="procesvervulling")
    op.drop_index("ix_procesvervulling_tenant", table_name="procesvervulling")
    op.drop_table("procesvervulling")
