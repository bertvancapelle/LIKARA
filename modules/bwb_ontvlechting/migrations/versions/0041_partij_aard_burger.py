"""ADR-024 — `partij_aard_enum` ADD VALUE 'burger'.

Burgers worden een volwaardige partij-aard (geen organisatie_id/afdeling_id, geen leden).
`ALTER TYPE … ADD VALUE` mag in Postgres niet in dezelfde transactie als waar de waarde
benut wordt → `autocommit_block`. Additief; geen tabel-/data-wijziging. De bestaande
CHECK-constraints blijven gelden zonder wijziging: burger valt buiten
`aard IN ('persoon','organisatie_eenheid')` (organisatie_id NULL → voldoet) en
`afdeling_id IS NULL OR aard = 'persoon'` (afdeling_id NULL → voldoet).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0041_partij_aard_burger"
down_revision: Union[str, Sequence[str], None] = "0040_adr023a_dubbel_genegeerd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE partij_aard_enum ADD VALUE IF NOT EXISTS 'burger'")


def downgrade() -> None:
    # Een enumwaarde verwijderen vergt type-herbouw; additieve waarde → no-op bij downgrade.
    pass
