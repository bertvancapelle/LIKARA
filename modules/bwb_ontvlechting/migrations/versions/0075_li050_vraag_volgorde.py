"""LI050 (W5) — vragen krijgen een eigen volgorde binnen hun categorie (slepen).

De positie van een vraag volgde de onzichtbare code; daardoor verscheen een nieuwe
vraag altijd onderaan en was herordenen onmogelijk. Nu: eigen `volgorde`-kolom.
De vulling neemt de volgorde over die vragen vandaag FEITELIJK hebben (numerieke
code-orde binnen de categorie) — er verspringt niets. Alleen testdata; de vulling is
de minimale landing op een gevulde dev-DB (0 rijen op fresh deploy), reseed = norm.

Revision ID: 0075_li050_vraag_volgorde
Revises: 0074_li050_checklist_categorie
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0075_li050_vraag_volgorde"
down_revision: Union[str, Sequence[str], None] = "0074_li050_checklist_categorie"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "checklistvraag",
        sa.Column("volgorde", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    # De feitelijke volgorde van vandaag = numerieke code-orde binnen de categorie
    # ("1.2" vóór "1.10"; een kale toegekende code als "13" sorteert op zijn geheel).
    op.execute(
        "UPDATE checklistvraag v SET volgorde = r.rn FROM ("
        "  SELECT id, ROW_NUMBER() OVER ("
        "    PARTITION BY tenant_id, categorie_id "
        "    ORDER BY split_part(code, '.', 1)::int, "
        "             COALESCE(NULLIF(split_part(code, '.', 2), ''), '0')::int"
        "  ) AS rn FROM checklistvraag"
        ") r WHERE r.id = v.id"
    )


def downgrade() -> None:
    op.drop_column("checklistvraag", "volgorde")
