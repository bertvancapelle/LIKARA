"""ADR-023 Fase B-mig-2 slice 2 — component_structuur → assignment/aggregation (cutover).

Revision ID: 0015_adr023_cutover_structuur
Revises: 0014_adr023_cutover_koppeling
Create Date: 2026-06-14

`draait_op` → **assignment**, oriëntatie **host→gehoste** (bron=op_component, doel=component)
— **omgedraaid** t.o.v. de oude opslag (component_id "draait op" op_component_id, OK-1).
`maakt_deel_uit_van` → **aggregation** (deel→geheel: bron=component, doel=op_component, geen
flip). id hergebruikt (1-op-1). Daarna `component_structuur` droppen.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_adr023_cutover_structuur"
down_revision: Union[str, Sequence[str], None] = "0014_adr023_cutover_koppeling"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # draait_op → assignment, host→gehoste (bron=op_component, doel=component) — FLIP.
    op.execute(
        """
        INSERT INTO relatie (id, tenant_id, bron_id, doel_id, relatietype, omschrijving, created_at, updated_at)
        SELECT id, tenant_id, op_component_id, component_id, 'assignment', omschrijving, created_at, updated_at
        FROM component_structuur WHERE relatietype = 'draait_op'
        ON CONFLICT (tenant_id, bron_id, doel_id, relatietype) DO NOTHING
        """
    )
    # maakt_deel_uit_van → aggregation, deel→geheel (bron=component, doel=op_component) — geen flip.
    op.execute(
        """
        INSERT INTO relatie (id, tenant_id, bron_id, doel_id, relatietype, omschrijving, created_at, updated_at)
        SELECT id, tenant_id, component_id, op_component_id, 'aggregation', omschrijving, created_at, updated_at
        FROM component_structuur WHERE relatietype = 'maakt_deel_uit_van'
        ON CONFLICT (tenant_id, bron_id, doel_id, relatietype) DO NOTHING
        """
    )
    op.drop_table("component_structuur")


def downgrade() -> None:
    """Best-effort terug (pre-prod): herstel component_structuur met de oude oriëntatie."""
    op.create_table(
        "component_structuur",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("op_component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relatietype", sa.String(60), nullable=False),
        sa.Column("omschrijving", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("component_id <> op_component_id", name="ck_component_structuur_self"),
    )
    # assignment terug naar draait_op (de-flip: component=doel, op_component=bron).
    op.execute(
        "INSERT INTO component_structuur (id, tenant_id, component_id, op_component_id, relatietype, omschrijving, created_at, updated_at) "
        "SELECT id, tenant_id, doel_id, bron_id, 'draait_op', omschrijving, created_at, updated_at "
        "FROM relatie WHERE relatietype = 'assignment'"
    )
    op.execute(
        "INSERT INTO component_structuur (id, tenant_id, component_id, op_component_id, relatietype, omschrijving, created_at, updated_at) "
        "SELECT id, tenant_id, bron_id, doel_id, 'maakt_deel_uit_van', omschrijving, created_at, updated_at "
        "FROM relatie WHERE relatietype = 'aggregation'"
    )
    op.execute("ALTER TABLE component_structuur ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE component_structuur FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON component_structuur "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("DELETE FROM relatie WHERE relatietype IN ('assignment', 'aggregation')")
