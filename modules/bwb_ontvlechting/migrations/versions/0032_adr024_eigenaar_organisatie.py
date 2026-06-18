"""ADR-024 UX-B6-b — eigenaar-organisatie (component): vrije tekst → verwijzing naar een organisatie-partij.

Revision ID: 0032_adr024_eigenaar_org
Revises: 0031_adr024_groep_org
Create Date: 2026-06-18

Vervangt `component.eigenaar_organisatie` (String NOT NULL) door een optionele composiet-FK
`(tenant_id, eigenaar_organisatie_id) → element(tenant_id, id)` naar een partij met aard=organisatie
(app-side geborgd, zoals de contract-leverancier). ON DELETE **SET NULL** — kolom-specifiek op
`eigenaar_organisatie_id` (PostgreSQL 15+); een kale SET NULL zou óók de gedeelde `tenant_id`
(NOT NULL) nullen. Reverse-lookup-index. Geen backfill (besluit Bert: geen te behouden data).

`eigenaar_naam` blijft ongemoeid (aparte vrije tekst). Engine onaangeroerd. Sluit B6 af (na B6-a
voor gebruikersgroep, 0031).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0032_adr024_eigenaar_org"
down_revision: Union[str, Sequence[str], None] = "0031_adr024_groep_org"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("component", sa.Column("eigenaar_organisatie_id", postgresql.UUID(as_uuid=True), nullable=True))
    # Kolom-specifieke SET NULL: alleen eigenaar_organisatie_id nullen, niet de gedeelde tenant_id.
    op.execute(
        "ALTER TABLE component ADD CONSTRAINT fk_component_eigenaar_organisatie "
        "FOREIGN KEY (tenant_id, eigenaar_organisatie_id) REFERENCES element (tenant_id, id) "
        "ON DELETE SET NULL (eigenaar_organisatie_id)"
    )
    op.create_index("ix_component_tenant_eigenaar_org", "component", ["tenant_id", "eigenaar_organisatie_id"])
    op.drop_column("component", "eigenaar_organisatie")


def downgrade() -> None:
    op.add_column("component", sa.Column("eigenaar_organisatie", sa.String(120), nullable=False, server_default=""))
    op.alter_column("component", "eigenaar_organisatie", server_default=None)
    op.drop_index("ix_component_tenant_eigenaar_org", table_name="component")
    op.drop_constraint("fk_component_eigenaar_organisatie", "component", type_="foreignkey")
    op.drop_column("component", "eigenaar_organisatie_id")
