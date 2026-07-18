"""ADR-052 slice 3 — snapshot van openstaande verplichte feiten op de klaarverklaring.

Additieve kolom `open_feiten` (TEXT[]) op `component_klaarverklaring`: de verplichte norm-feiten die
op het moment van klaar verklaren NIET vastgesteld waren (het bevroren auditeerbare wilsbesluit).
Leeg = geen afwijking. `verklaard_op` is de peildatum van de snapshot. Geen datamigratie
(bestaande verklaringen krijgen de default lege array).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0073_adr052_klaarverkl_snapshot"
down_revision: Union[str, Sequence[str], None] = "0072_adr052_component_bevinding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "component_klaarverklaring",
        sa.Column(
            "open_feiten", postgresql.ARRAY(sa.Text()),
            nullable=False, server_default=sa.text("'{}'::text[]"),
        ),
    )


def downgrade() -> None:
    op.drop_column("component_klaarverklaring", "open_feiten")
