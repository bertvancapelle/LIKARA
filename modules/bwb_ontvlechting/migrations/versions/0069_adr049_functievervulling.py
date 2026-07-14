"""ADR-049 (gate 2a) — functievervulling: koppelregel component→bedrijfsfunctie (kaal, additief).

Revision ID: 0069_adr049_functievervulling
Revises: 0068_li040_geen_oordeel
Create Date: 2026-07-14

Eigen tenant-scoped registratie-feit (het procesvervulling-recept), mét één verschil: de as is
KAAL — géén applicatiefunctie. Het anker is het ADRES van de plek (ADR-049 besluit 2):
`functie_id` (de ondersteunde functie) + `ouder_functie_id` (onder welke functie; NULL = grof,
gevuld = fijn) — GEEN verwijzing naar `relatie.id`. Drie composiet-FK's → element (CASCADE).

Uniciteit STRUCTUREEL, in twee partiële vormen (NULL is distinct in Postgres — een gewone
UNIQUE zou grove dubbelen toelaten; precedent uq_relatie, 0039):
- uq_functievervulling_grof: één grove per (component, functie)      WHERE ouder NULL;
- uq_functievervulling_fijn: één fijne per (component, functie, plek) WHERE ouder NOT NULL.

Wie/wanneer server-stamped (`verklaard_door_sub` + `verklaard_door`; created_at = wanneer);
optionele `toelichting`. FORCE RLS + tenant_isolation + grants lk_app. Engine onaangeroerd.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0069_adr049_functievervulling"
down_revision: Union[str, Sequence[str], None] = "0068_li040_geen_oordeel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "functievervulling",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("functie_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ouder_functie_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("toelichting", sa.Text(), nullable=True),
        sa.Column("verklaard_door_sub", sa.String(255), nullable=True),
        sa.Column("verklaard_door", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # Twee partiële unieke indexen — het NULL-distinct-gat structureel dicht.
    op.create_index(
        "uq_functievervulling_grof", "functievervulling",
        ["tenant_id", "component_id", "functie_id"],
        unique=True, postgresql_where=sa.text("ouder_functie_id IS NULL"),
    )
    op.create_index(
        "uq_functievervulling_fijn", "functievervulling",
        ["tenant_id", "component_id", "functie_id", "ouder_functie_id"],
        unique=True, postgresql_where=sa.text("ouder_functie_id IS NOT NULL"),
    )
    op.create_index("ix_functievervulling_tenant_functie", "functievervulling", ["tenant_id", "functie_id"])
    op.create_index("ix_functievervulling_tenant_component", "functievervulling", ["tenant_id", "component_id"])
    op.create_foreign_key(
        "fk_functievervulling_component", "functievervulling", "element",
        ["tenant_id", "component_id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_functievervulling_functie", "functievervulling", "element",
        ["tenant_id", "functie_id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_functievervulling_ouder", "functievervulling", "element",
        ["tenant_id", "ouder_functie_id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.execute("ALTER TABLE functievervulling ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE functievervulling FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON functievervulling "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON functievervulling FROM lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON functievervulling TO lk_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON functievervulling")
    op.drop_constraint("fk_functievervulling_ouder", "functievervulling", type_="foreignkey")
    op.drop_constraint("fk_functievervulling_functie", "functievervulling", type_="foreignkey")
    op.drop_constraint("fk_functievervulling_component", "functievervulling", type_="foreignkey")
    op.drop_index("ix_functievervulling_tenant_component", table_name="functievervulling")
    op.drop_index("ix_functievervulling_tenant_functie", table_name="functievervulling")
    op.drop_index("uq_functievervulling_fijn", table_name="functievervulling")
    op.drop_index("uq_functievervulling_grof", table_name="functievervulling")
    op.drop_table("functievervulling")
