"""ADR-036a — gebruikersgroep-afdeling structureel: tekstkolom → `afdeling_id` (FK org-eenheid).

Revision ID: 0050_adr036a_gg_afdeling
Revises: 0049_adr036_organisatiegebruik
Create Date: 2026-07-03

Vervangt `gebruikersgroep.afdeling` (String) door `afdeling_id`: een composiet-FK
`(tenant_id, afdeling_id) → element(tenant_id, id)` naar een `organisatie_eenheid`-partij
(aard app-side geborgd), ON DELETE **RESTRICT** (een afdeling met groepen verdwijnt niet stil) —
spiegel van het persoon→afdeling-patroon (ADR-024, `partij.afdeling_id`). Nullable = geen afdeling.

RLS/FORCE op de bestaande `gebruikersgroep`-tabel blijft ongewijzigd. De partij-CHECK
`afdeling_id IS NULL OR aard='persoon'` is NIET geraakt (die zit op de `partij`-tabel).

Ontwikkelmodus: uitsluitend testdata → schone schemastap, geen databehoud-migratie (reseed maakt
echte afdeling-partijen aan en verwijst ernaar). Engine onaangeroerd — registratief.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0050_adr036a_gg_afdeling"
down_revision: Union[str, Sequence[str], None] = "0049_adr036_organisatiegebruik"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("gebruikersgroep", sa.Column("afdeling_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_gebruikersgroep_afdeling", "gebruikersgroep", "element",
        ["tenant_id", "afdeling_id"], ["tenant_id", "id"], ondelete="RESTRICT",
    )
    op.create_index("ix_gebruikersgroep_tenant_afdeling", "gebruikersgroep", ["tenant_id", "afdeling_id"])
    op.drop_column("gebruikersgroep", "afdeling")


def downgrade() -> None:
    op.add_column("gebruikersgroep", sa.Column("afdeling", sa.String(255), nullable=True))
    op.drop_index("ix_gebruikersgroep_tenant_afdeling", table_name="gebruikersgroep")
    op.drop_constraint("fk_gebruikersgroep_afdeling", "gebruikersgroep", type_="foreignkey")
    op.drop_column("gebruikersgroep", "afdeling_id")
