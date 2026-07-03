"""ADR-036 — grof gebruiksfeit `organisatiegebruik` + gebruikersgroep-verfijning.

Revision ID: 0049_adr036_organisatiegebruik
Revises: 0048_adr028_classificatie
Create Date: 2026-07-03

Voert het grove gebruiksfeit "organisatie gebruikt applicatie" in als eigen tenant-scoped
registratie-tabel (vorm = `roltoewijzing`; GEEN element-subtype). `UNIQUE(tenant, organisatie,
applicatie)` borgt structureel één feit per (organisatie, applicatie). Beide endpoints zijn
composiet-FK's naar `element` (ON DELETE CASCADE). Extra `UNIQUE(tenant_id, id)` als doel voor
de verfijning-FK vanuit de gebruikersgroep.

De gebruikersgroep verschuift naar de **single source of truth** (ADR-036): de eigen
`organisatie_id`-kolom (+ FK/index) vervalt; er komt `gebruik_id` (nullable) → een composiet-FK
naar `organisatiegebruik` met **kolom-specifieke** `ON DELETE SET NULL` (PostgreSQL 15+; een kale
SET NULL zou ook de gedeelde NOT NULL `tenant_id` nullen). `gebruik_id` NULL = organisatie-loze
groep. De `serving`-relatie (applicatie → gebruikersgroep) blijft ongewijzigd de applicatie-band.

Ontwikkelmodus: uitsluitend testdata → schone schemastap, geen databehoud-migratie (reseed).
Engine onaangeroerd — registratief, geen lifecycle/score/blokkade.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0049_adr036_organisatiegebruik"
down_revision: Union[str, Sequence[str], None] = "0048_adr028_classificatie"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Grof gebruiksfeit `organisatiegebruik` (eigen tenant-tabel, geen element-subtype) ──
    op.create_table(
        "organisatiegebruik",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organisatie_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applicatie_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "organisatie_id", "applicatie_id", name="uq_organisatiegebruik"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_organisatiegebruik_tenant_id"),
    )
    op.create_index("ix_organisatiegebruik_tenant", "organisatiegebruik", ["tenant_id"])
    op.create_index("ix_organisatiegebruik_tenant_app", "organisatiegebruik", ["tenant_id", "applicatie_id"])
    op.create_index("ix_organisatiegebruik_tenant_org", "organisatiegebruik", ["tenant_id", "organisatie_id"])
    op.create_foreign_key(
        "fk_organisatiegebruik_organisatie", "organisatiegebruik", "element",
        ["tenant_id", "organisatie_id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_organisatiegebruik_applicatie", "organisatiegebruik", "element",
        ["tenant_id", "applicatie_id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.execute("ALTER TABLE organisatiegebruik ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE organisatiegebruik FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON organisatiegebruik "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON organisatiegebruik FROM lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON organisatiegebruik TO lk_app")

    # ── 2. Gebruikersgroep → single source of truth: verfijning-FK + oude org-kolom weg ──
    op.add_column("gebruikersgroep", sa.Column("gebruik_id", postgresql.UUID(as_uuid=True), nullable=True))
    # Composiet-FK (tenant_id, gebruik_id) → organisatiegebruik. Kolom-specifieke SET NULL zodat
    # ALLEEN gebruik_id genulld wordt (niet de gedeelde NOT NULL tenant_id). PostgreSQL 15+.
    op.execute(
        "ALTER TABLE gebruikersgroep ADD CONSTRAINT fk_gebruikersgroep_gebruik "
        "FOREIGN KEY (tenant_id, gebruik_id) REFERENCES organisatiegebruik (tenant_id, id) "
        "ON DELETE SET NULL (gebruik_id)"
    )
    op.create_index("ix_gebruikersgroep_tenant_gebruik", "gebruikersgroep", ["tenant_id", "gebruik_id"])
    # Oude eigen organisatie-koppeling vervalt (organisatie leeft nu op het grove feit).
    op.drop_index("ix_gebruikersgroep_tenant_organisatie", table_name="gebruikersgroep")
    op.drop_constraint("fk_gebruikersgroep_organisatie", "gebruikersgroep", type_="foreignkey")
    op.drop_column("gebruikersgroep", "organisatie_id")


def downgrade() -> None:
    # Gebruikersgroep terug naar de eigen organisatie_id-kolom (ADR-024-vorm).
    op.add_column("gebruikersgroep", sa.Column("organisatie_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        "ALTER TABLE gebruikersgroep ADD CONSTRAINT fk_gebruikersgroep_organisatie "
        "FOREIGN KEY (tenant_id, organisatie_id) REFERENCES element (tenant_id, id) "
        "ON DELETE SET NULL (organisatie_id)"
    )
    op.create_index("ix_gebruikersgroep_tenant_organisatie", "gebruikersgroep", ["tenant_id", "organisatie_id"])
    op.drop_index("ix_gebruikersgroep_tenant_gebruik", table_name="gebruikersgroep")
    op.drop_constraint("fk_gebruikersgroep_gebruik", "gebruikersgroep", type_="foreignkey")
    op.drop_column("gebruikersgroep", "gebruik_id")

    # Grof gebruiksfeit weg.
    op.drop_table("organisatiegebruik")
