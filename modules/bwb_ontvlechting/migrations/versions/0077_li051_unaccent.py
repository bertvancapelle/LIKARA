"""LI051 — accent-ongevoelig zoeken: installeer de `unaccent`-extensie.

Zoeken op "jose" moet "José" vinden (besluit Bert). De gedeelde zoek-bron
(`services/zoektekst.py`) doet `unaccent(kolom) ILIKE unaccent(patroon)`; die DB-functie komt uit
de `unaccent`-contrib-extensie. Deze migratie installeert haar, zodat elke omgeving haar krijgt door
gewoon op te starten (de init-container draait de migraties af, ADR-011) — de beheerder hoeft niets
te onthouden. De app-startup weigert bovendien te starten als de functie ontbreekt
(`app.core.zoekfunctie`), zodat een ontbrekende extensie meteen zichtbaar is i.p.v. pas bij de eerste
zoekopdracht.

`CREATE EXTENSION IF NOT EXISTS` is idempotent: draait de migratie op een database waar `unaccent`
al staat, dan gebeurt er niets (geen fout). De migratie draait als `lk_admin` (superuser, ADR-011) —
`CREATE EXTENSION` op unaccent vergt superuser; lk_app/lk_platform kunnen (en hoeven) dat niet.

Revision ID: 0077_li051_unaccent
Revises: 0076_adr056_vraag_bevroren
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0077_li051_unaccent"
down_revision: Union[str, Sequence[str], None] = "0076_adr056_vraag_bevroren"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")


def downgrade() -> None:
    # De extensie is een DB-brede capaciteit; bij downgrade laten staan zou geen kwaad, maar
    # symmetrisch verwijderen we haar. DROP faalt als iets haar nog gebruikt — in dev geen issue.
    op.execute("DROP EXTENSION IF EXISTS unaccent")
