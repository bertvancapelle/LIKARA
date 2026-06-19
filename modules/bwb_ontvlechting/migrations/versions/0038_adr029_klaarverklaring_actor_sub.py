"""ADR-029 Fase 3b — actor-sub op `component_klaarverklaring` (naam-resolutie).

Revision ID: 0038_adr029_kv_actor_sub
Revises: 0037_adr029_gebruiker_persoon
Create Date: 2026-06-20

Expand (geen data-verlies): voeg `verklaard_door_sub` (stabiele Keycloak-sub-sleutel) toe NAAST
`verklaard_door` (dat voortaan de e-mail-fallback draagt). Nullable — historische rijen hebben
geen sub en behouden hun e-mailstring in `verklaard_door`. Naam wordt read-side geresolveerd via
de gebruiker-persoon-koppeling (ADR-029). Geen backfill. Registratief — engine onaangeroerd.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0038_adr029_kv_actor_sub"
down_revision: Union[str, Sequence[str], None] = "0037_adr029_gebruiker_persoon"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "component_klaarverklaring",
        sa.Column("verklaard_door_sub", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("component_klaarverklaring", "verklaard_door_sub")
