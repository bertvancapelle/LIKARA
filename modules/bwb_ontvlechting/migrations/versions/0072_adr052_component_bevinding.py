"""ADR-052 slice 2 — "bewust geen"-bevinding op een component (`component_bevinding`).

Component-verankerde bevinding voor koppelingen/contract: "vastgesteld — dit component heeft er
geen." Eigen tenant-scoped tabel met het standaard RLS-recept. Eén bevinding per (component, soort).
Additief; geen datamigratie.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0072_adr052_component_bevinding"
down_revision: Union[str, Sequence[str], None] = "0071_adr052_component_norm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_soort = postgresql.ENUM(
    "koppelingen", "contract", name="component_bevinding_soort_enum", create_type=False,
)


def upgrade() -> None:
    _soort.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "component_bevinding",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), primary_key=True,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("soort", _soort, nullable=False),
        sa.Column("verklaard_door_sub", sa.String(length=255), nullable=True),
        sa.Column("verklaard_door", sa.String(length=255), nullable=True),
        sa.Column("verklaard_op", sa.DateTime(timezone=True), nullable=False),
        sa.Column("toelichting", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "component_id"], ["element.tenant_id", "element.id"],
            name="fk_component_bevinding_component", ondelete="CASCADE",
        ),
        sa.UniqueConstraint("tenant_id", "component_id", "soort", name="uq_component_bevinding"),
    )
    op.create_index("ix_component_bevinding_tenant", "component_bevinding", ["tenant_id"])
    op.create_index(
        "ix_component_bevinding_tenant_component", "component_bevinding",
        ["tenant_id", "component_id"],
    )
    op.execute("ALTER TABLE component_bevinding ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE component_bevinding FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON component_bevinding "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON component_bevinding FROM lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON component_bevinding TO lk_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON component_bevinding")
    op.drop_index("ix_component_bevinding_tenant_component", table_name="component_bevinding")
    op.drop_index("ix_component_bevinding_tenant", table_name="component_bevinding")
    op.drop_table("component_bevinding")
    _soort.drop(op.get_bind(), checkfirst=True)
