"""ADR-024 slice 1 — `element_type_enum` ADD VALUE 'partij' (aparte, voorafgaande stap).

`ALTER TYPE … ADD VALUE` mag in Postgres niet in dezelfde transactie worden gebruikt als
waar de waarde wordt benut → eigen migratie met `autocommit_block`, vóór 0027 die de
`partij`-subtabel aanmaakt. Additief; geen tabel-/data-wijziging.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0026_adr024_elementtype_partij"
down_revision: Union[str, Sequence[str], None] = "0025_adr026_typering_volledig"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE element_type_enum ADD VALUE IF NOT EXISTS 'partij'")


def downgrade() -> None:
    # Een enumwaarde verwijderen is in Postgres niet triviaal (vereist type-herbouw).
    # Additieve waarde → no-op bij downgrade (de waarde blijft ongebruikt achter).
    pass
