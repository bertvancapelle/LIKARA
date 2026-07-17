"""ADR-052 slice 1 — tenant-norm voor harde componentfeiten (`component_norm`).

Per hard feit een verplicht-vlag (MVP: ja/nee). Tenant-eigen governance-configuratie:
tenant-scoped tabel met het standaard RLS-recept (ENABLE + FORCE + tenant_isolation-policy +
lk_app-grants). Eén rij per (tenant_id, feit_sleutel). Additief; geen datamigratie.

De default-norm (de vijf verplichte feiten voor een verse tenant) wordt NIET hier geseed maar
per tenant via `services.seed.seed_component_norm` (onboarding/dev_seed), analoog aan de
checklist-baseline (ADR-022 W1).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0071_adr052_component_norm"
down_revision: Union[str, Sequence[str], None] = "0070_adr051_gapsignaal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "component_norm",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feit_sleutel", sa.String(length=60), nullable=False),
        sa.Column("verplicht", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "feit_sleutel", name="uq_component_norm_feit"),
    )
    op.create_index("ix_component_norm_tenant", "component_norm", ["tenant_id"])
    op.execute("ALTER TABLE component_norm ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE component_norm FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON component_norm "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON component_norm FROM lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON component_norm TO lk_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON component_norm")
    op.drop_index("ix_component_norm_tenant", table_name="component_norm")
    op.drop_table("component_norm")
