"""ADR-022 W3 / LI050 — de checklist-categorie wordt een eigen tenant-entiteit.

Vóór deze stap droeg elke vraag zelf `categorie_nr` + `categorie_naam` (gedenormaliseerd).
Nu: eigen tabel `checklist_categorie` (RLS + FORCE, `UNIQUE(tenant, componenttype, naam)`);
de vraag verwijst via een tenant-consistente composiet-FK met **RESTRICT** (een categorie
met vragen kan structureel niet verdwijnen).

Er is uitsluitend testdata (geen databehoud-eis). De drie vul-statements hieronder zijn
géén databehoud-machinerie maar de minimale stap die de NOT NULL-kolom op een gevulde
dev-DB laat landen (lk_admin bypasst RLS → één statement raakt alle tenants, het
0024-precedent); op een fresh deploy raken ze 0 rijen. Reseed blijft de norm.

Revision ID: 0074_li050_checklist_categorie
Revises: 0073_adr052_klaarverkl_snapshot
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0074_li050_checklist_categorie"
down_revision: Union[str, Sequence[str], None] = "0073_adr052_klaarverkl_snapshot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "checklist_categorie",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("componenttype", sa.String(60), nullable=False),
        sa.Column("naam", sa.String(120), nullable=False),
        sa.Column("volgorde", sa.Integer(), nullable=False),
        # Identiteit = naam binnen (tenant, componenttype) — schema-afgedwongen (LI050).
        sa.UniqueConstraint("tenant_id", "componenttype", "naam",
                            name="uq_checklist_categorie_naam"),
        # Composiet-FK-target voor checklistvraag.
        sa.UniqueConstraint("tenant_id", "id", name="uq_checklist_categorie_tenant_id"),
    )
    op.create_index("ix_checklist_categorie_tenant", "checklist_categorie", ["tenant_id"])
    op.execute("ALTER TABLE checklist_categorie ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE checklist_categorie FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON checklist_categorie "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON checklist_categorie FROM lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON checklist_categorie TO lk_app")

    # Vulling uit de bestaande gedenormaliseerde kolommen (0 rijen op fresh deploy).
    # min(categorie_nr) als volgorde: de meting vond 0 nummers met meerdere namen.
    op.execute(
        "INSERT INTO checklist_categorie (tenant_id, componenttype, naam, volgorde) "
        "SELECT tenant_id, componenttype, categorie_naam, min(categorie_nr) "
        "FROM checklistvraag GROUP BY tenant_id, componenttype, categorie_naam"
    )
    op.add_column("checklistvraag",
                  sa.Column("categorie_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        "UPDATE checklistvraag v SET categorie_id = c.id FROM checklist_categorie c "
        "WHERE c.tenant_id = v.tenant_id AND c.componenttype = v.componenttype "
        "AND c.naam = v.categorie_naam"
    )
    op.alter_column("checklistvraag", "categorie_id", nullable=False)
    op.create_foreign_key(
        "fk_checklistvraag_categorie", "checklistvraag", "checklist_categorie",
        ["tenant_id", "categorie_id"], ["tenant_id", "id"], ondelete="RESTRICT",
    )
    op.drop_column("checklistvraag", "categorie_naam")
    op.drop_column("checklistvraag", "categorie_nr")


def downgrade() -> None:
    op.add_column("checklistvraag", sa.Column("categorie_nr", sa.Integer(), nullable=True))
    op.add_column("checklistvraag",
                  sa.Column("categorie_naam", sa.String(120), nullable=True))
    op.execute(
        "UPDATE checklistvraag v SET categorie_nr = c.volgorde, categorie_naam = c.naam "
        "FROM checklist_categorie c WHERE c.id = v.categorie_id"
    )
    op.alter_column("checklistvraag", "categorie_nr", nullable=False)
    op.alter_column("checklistvraag", "categorie_naam", nullable=False)
    op.drop_constraint("fk_checklistvraag_categorie", "checklistvraag", type_="foreignkey")
    op.drop_column("checklistvraag", "categorie_id")
    op.drop_table("checklist_categorie")
