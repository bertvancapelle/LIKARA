"""ADR-023 Fase B-mig-2 slice 4 — datatype/gebruikersgroep-band → access/serving (cutover).

Revision ID: 0017_adr023_cutover_band
Revises: 0016_adr023_cutover_contract
Create Date: 2026-06-14

De `applicatie_id`-band wordt een relatie: datatype → **access** (applicatie → datatype),
gebruikersgroep → **serving** (applicatie → gebruikersgroep). Daarna de `applicatie_id`-kolommen
droppen. CASCADE-wijziging (Besluit 13): een applicatie verwijderen cascadeert voortaan alleen
de relatie (relatie-FK → element), niet het datatype/gebruikersgroep-element — "wezen" blijven
bestaan.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_adr023_cutover_band"
down_revision: Union[str, Sequence[str], None] = "0016_adr023_cutover_contract"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO relatie (id, tenant_id, bron_id, doel_id, relatietype, created_at, updated_at)
        SELECT gen_random_uuid(), tenant_id, applicatie_id, id, 'access', created_at, updated_at
        FROM datatype
        ON CONFLICT (tenant_id, bron_id, doel_id, relatietype) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO relatie (id, tenant_id, bron_id, doel_id, relatietype, created_at, updated_at)
        SELECT gen_random_uuid(), tenant_id, applicatie_id, id, 'serving', created_at, updated_at
        FROM gebruikersgroep
        ON CONFLICT (tenant_id, bron_id, doel_id, relatietype) DO NOTHING
        """
    )
    op.drop_column("datatype", "applicatie_id")
    op.drop_column("gebruikersgroep", "applicatie_id")


def downgrade() -> None:
    """Best-effort terug (pre-prod): herstel de applicatie_id-kolommen uit de relaties."""
    op.add_column("datatype", sa.Column("applicatie_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("gebruikersgroep", sa.Column("applicatie_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        "UPDATE datatype d SET applicatie_id = r.bron_id FROM relatie r "
        "WHERE r.doel_id = d.id AND r.relatietype = 'access'"
    )
    op.execute(
        "UPDATE gebruikersgroep g SET applicatie_id = r.bron_id FROM relatie r "
        "WHERE r.doel_id = g.id AND r.relatietype = 'serving'"
    )
    op.execute("DELETE FROM relatie WHERE relatietype IN ('access', 'serving')")
    op.create_foreign_key("datatype_applicatie_id_fkey", "datatype", "applicatie",
                          ["applicatie_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("gebruikersgroep_applicatie_id_fkey", "gebruikersgroep", "applicatie",
                          ["applicatie_id"], ["id"], ondelete="CASCADE")
