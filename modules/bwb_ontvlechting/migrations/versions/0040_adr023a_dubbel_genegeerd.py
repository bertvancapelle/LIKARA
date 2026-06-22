"""ADR-023a — markering 'dubbel-waarschuwing genegeerd' op `relatie`.

Revision ID: 0040_adr023a_dubbel_genegeerd
Revises: 0039_adr023a_flow_meervoud
Create Date: 2026-06-22

Fase 2-aanvulling: voeg `dubbel_waarschuwing_genegeerd boolean NOT NULL DEFAULT false` toe.
De servicelaag zet dit op true wanneer een flow wordt aangemaakt terwijl er een identieke
bestond (op `omschrijving` na) ÉN de gebruiker de KOPPELING_DUBBEL-waarschuwing bewust
overrulede. De audit-diff (ADR-006, `bouw_wijziging`) capture't mapped columns automatisch →
de override is naspeurbaar in de objecthistorie van de koppeling. Geen aparte audit-gebeurtenis.

Puur schema (alleen testdata aanwezig; geen databehoud-migratie). Registratief — engine
onaangeroerd. Reversibel: down dropt de kolom.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0040_adr023a_dubbel_genegeerd"
down_revision: Union[str, Sequence[str], None] = "0039_adr023a_flow_meervoud"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "relatie",
        sa.Column(
            "dubbel_waarschuwing_genegeerd", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("relatie", "dubbel_waarschuwing_genegeerd")
