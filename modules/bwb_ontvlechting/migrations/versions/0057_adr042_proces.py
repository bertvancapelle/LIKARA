"""ADR-042 slice 1 — Proces: nestbaar procesregister-element (additief).

Revision ID: 0057_adr042_proces
Revises: 0056_adr042_elemtype_proces
Create Date: 2026-07-08

Voegt de subtype-tabel `proces` toe (element-subtype: shared-PK composiet-FK → element,
FORCE RLS) — het work_package-recept (0020) 1-op-1. Hiërarchie via een composiet self-FK
`(tenant_id, ouder_id)` → `proces(tenant_id, id)` met **ON DELETE RESTRICT** (een proces
met deelprocessen kan niet verwijderd worden — de subboom wordt niet stilzwijgend
weggevaagd). Een DB-CHECK weert de directe self-parent; transitieve cycluspreventie zit
in de service. Type-eigen velden: `naam` (verplicht) + `toelichting` (plateau-spiegel).

`element_type_enum` kreeg 'proces' in de voorafgaande 0056 (ADD VALUE-precedent 0026).
Geen datamigratie (er is geen bestaande proces-data; testdata volgt in slice 3).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0057_adr042_proces"
down_revision: Union[str, Sequence[str], None] = "0056_adr042_elemtype_proces"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "proces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("naam", sa.String(255), nullable=False),
        sa.Column("toelichting", sa.Text(), nullable=True),
        sa.Column("ouder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Composiet-FK-target voor de self-FK (tenant-consistent).
        sa.UniqueConstraint("tenant_id", "id", name="uq_proces_tenant_id"),
        sa.CheckConstraint(
            "ouder_id IS NULL OR ouder_id <> id",
            name="ck_proces_geen_self_parent",
        ),
    )
    op.create_index("ix_proces_tenant", "proces", ["tenant_id"])
    op.create_index("ix_proces_tenant_ouder", "proces", ["tenant_id", "ouder_id"])
    # Shared-PK: composiet-FK (tenant_id, id) → element (cross-tenant uitgesloten, cascade).
    op.create_foreign_key(
        "fk_proces_element", "proces", "element",
        ["tenant_id", "id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    # Hiërarchie: composiet self-FK met RESTRICT (subboom niet stilzwijgend wegvagen).
    op.create_foreign_key(
        "fk_proces_ouder", "proces", "proces",
        ["tenant_id", "ouder_id"], ["tenant_id", "id"], ondelete="RESTRICT",
    )
    op.execute("ALTER TABLE proces ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE proces FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON proces "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON proces FROM lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON proces TO lk_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON proces")
    op.drop_constraint("fk_proces_ouder", "proces", type_="foreignkey")
    op.drop_constraint("fk_proces_element", "proces", type_="foreignkey")
    op.drop_index("ix_proces_tenant_ouder", table_name="proces")
    op.drop_index("ix_proces_tenant", table_name="proces")
    op.drop_table("proces")
