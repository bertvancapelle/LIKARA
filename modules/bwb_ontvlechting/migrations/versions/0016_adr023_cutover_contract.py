"""ADR-023 Fase B-mig-2 slice 3 — component_contract → association-relatie (cutover).

Revision ID: 0016_adr023_cutover_contract
Revises: 0015_adr023_cutover_structuur
Create Date: 2026-06-14

`component_contract` → één `association`-relatie (bron=component, doel=contract; `relatie_rol`
als kenmerk). id hergebruikt (1-op-1). Contract is sinds B-mig-1 een element → de composiet-FK
naar `element` klopt voor beide endpoints. Daarna `component_contract` droppen.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_adr023_cutover_contract"
down_revision: Union[str, Sequence[str], None] = "0015_adr023_cutover_structuur"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO relatie (id, tenant_id, bron_id, doel_id, relatietype, kenmerken, created_at, updated_at)
        SELECT id, tenant_id, component_id, contract_id, 'association',
               jsonb_build_object('relatie_rol', relatie_rol), created_at, updated_at
        FROM component_contract
        ON CONFLICT (tenant_id, bron_id, doel_id, relatietype) DO NOTHING
        """
    )
    op.drop_table("component_contract")


def downgrade() -> None:
    """Best-effort terug (pre-prod): herstel component_contract uit de association-relaties."""
    op.create_table(
        "component_contract",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relatie_rol", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "component_id", "contract_id", name="uq_component_contract"),
    )
    op.execute(
        "INSERT INTO component_contract (id, tenant_id, component_id, contract_id, relatie_rol, created_at, updated_at) "
        "SELECT id, tenant_id, bron_id, doel_id, kenmerken->>'relatie_rol', created_at, updated_at "
        "FROM relatie WHERE relatietype = 'association'"
    )
    op.execute("ALTER TABLE component_contract ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE component_contract FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON component_contract "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("DELETE FROM relatie WHERE relatietype = 'association'")
