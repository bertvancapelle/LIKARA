"""ADR-027 — klaarverklaring van categorie- naar componentniveau (`component_klaarverklaring`).

Revision ID: 0036_adr027_kv_component
Revises: 0035_adr027_klaarverklaring
Create Date: 2026-06-19

De klaarverklaring verschuift van per (component, categorie_nr) naar **per component**: één
coördinator verklaart een heel component klaar. `categorie_nr` vervalt; de uniciteit wordt
`(tenant_id, component_id)`. Omdat er nog geen productie-data is (dev wordt gereseed) is dit een
schone **drop + recreate** i.p.v. een kolom-/constraint-verbouwing op de oude tabel — minder
migratie-complexiteit, identiek eindresultaat. De enum `klaarverklaring_status_enum` (uit 0035)
blijft bestaan en wordt hergebruikt.

Engine onaangeroerd — registratief, geen lifecycle/score/blokkade.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0036_adr027_kv_component"
down_revision: Union[str, Sequence[str], None] = "0035_adr027_klaarverklaring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Bestaande enum (0035) — hergebruiken zonder opnieuw aan te maken.
_status_enum = postgresql.ENUM("klaar", "open", name="klaarverklaring_status_enum", create_type=False)


def _maak_tabel(naam: str, unieke_kolommen: list[str], extra_kolommen: list[sa.Column]) -> None:
    op.create_table(
        naam,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        *extra_kolommen,
        sa.Column("status", _status_enum, nullable=False, server_default=sa.text("'klaar'")),
        sa.Column("reden", sa.Text(), nullable=False),
        sa.Column("verklaard_door", sa.String(255), nullable=True),
        sa.Column("verklaard_op", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(*unieke_kolommen, name=f"uq_{naam}"),
    )
    op.create_index(f"ix_{naam}_tenant", naam, ["tenant_id"])
    op.create_index(f"ix_{naam}_tenant_component", naam, ["tenant_id", "component_id"])
    op.create_foreign_key(
        f"fk_{naam}_component", naam, "element",
        ["tenant_id", "component_id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.execute(f"ALTER TABLE {naam} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {naam} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON {naam} "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute(f"REVOKE ALL ON {naam} FROM cd_app")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {naam} TO cd_app")


def upgrade() -> None:
    op.drop_table("categorie_klaarverklaring")
    _maak_tabel(
        "component_klaarverklaring",
        unieke_kolommen=["tenant_id", "component_id"],
        extra_kolommen=[],
    )


def downgrade() -> None:
    op.drop_table("component_klaarverklaring")
    _maak_tabel(
        "categorie_klaarverklaring",
        unieke_kolommen=["tenant_id", "component_id", "categorie_nr"],
        extra_kolommen=[sa.Column("categorie_nr", sa.Integer(), nullable=False)],
    )
