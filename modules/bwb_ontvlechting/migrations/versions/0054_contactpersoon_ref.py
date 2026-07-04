"""ADR-039 — aanspreekpunt als persoon-verwijzing: vrije tekst → partij-FK.

Revision ID: 0054_contactpersoon_ref
Revises: 0053_adr038_consolidatie
Create Date: 2026-07-04

Vervangt het vrije-tekstveld `partij.contactpersoon` (String(255)) door een optionele composiet-FK
`(tenant_id, contactpersoon_id) → element(tenant_id, id)` naar een persoon-partij die bij deze partij
hoort (persoon.organisatie_id == deze partij; app-side geborgd, alleen op organisatie/externe_partij).
Spiegel van `component.eigenaar_organisatie_id` / `checklistscore.verantwoordelijke_id`.

ON DELETE **SET NULL** — kolom-specifiek op `contactpersoon_id` (PostgreSQL 15+); een kale SET NULL
zou óók de gedeelde `tenant_id` (NOT NULL) nullen. Reverse-lookup-index. Geen backfill
(ontwikkelmodus: alleen testdata → reseed).

RLS/FORCE op `partij` blijft ongewijzigd (kolom-mutaties erven de tabel-policy). Engine
onaangeroerd — registratief; score blijft de enige lifecycle-driver.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0054_contactpersoon_ref"
down_revision: Union[str, Sequence[str], None] = "0053_adr038_consolidatie"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "partij",
        sa.Column("contactpersoon_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # Kolom-specifieke SET NULL: alleen contactpersoon_id nullen, niet de gedeelde tenant_id.
    op.execute(
        "ALTER TABLE partij ADD CONSTRAINT fk_partij_contactpersoon "
        "FOREIGN KEY (tenant_id, contactpersoon_id) REFERENCES element (tenant_id, id) "
        "ON DELETE SET NULL (contactpersoon_id)"
    )
    op.create_index(
        "ix_partij_tenant_contactpersoon",
        "partij",
        ["tenant_id", "contactpersoon_id"],
    )
    op.drop_column("partij", "contactpersoon")


def downgrade() -> None:
    op.add_column("partij", sa.Column("contactpersoon", sa.String(255), nullable=True))
    op.drop_index("ix_partij_tenant_contactpersoon", table_name="partij")
    op.drop_constraint("fk_partij_contactpersoon", "partij", type_="foreignkey")
    op.drop_column("partij", "contactpersoon_id")
