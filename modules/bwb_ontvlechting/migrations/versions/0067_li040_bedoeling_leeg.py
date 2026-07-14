"""LI040 — "nog niet vastgelegd" is een uitkomst: de bedoeling wordt écht leeg.

De sentinel `onbekend` in `migratiepad` oogde als een antwoord terwijl er niets was
vastgelegd (gemeten V040: 19/19 rijen). Afwezigheid krijgt één taal (ADR-046 vormkeuze
B, addendum A): de kolom wordt NULLABLE zonder default — identiek aan `levensfase` —
en `onbekend` verdwijnt uit de enum via type-recreate (PostgreSQL kent geen DROP
VALUE; precedent 0053/0066, incl. de default-drop-valkuil: de kolom-default is aan het
oude type gebonden en vervalt hier definitief).

Stappen: default weg → kolom nullable → `onbekend`-rijen → NULL (dev-data; gemeten
vóór/ná in het gate-rapport) → enum-recreate zonder `onbekend` (NULL-rijen passeren de
USING-cast onaangeroerd). Engine onaangeroerd — registratief veld; score blijft de
enige lifecycle-driver.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0067_li040_bedoeling_leeg"
down_revision: Union[str, Sequence[str], None] = "0066_adr046_levensfase"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PADEN_ZONDER_ONBEKEND = "'lift_and_shift', 'herbouw', 'vervangen', 'gedeeld'"
_PADEN_MET_ONBEKEND = "'lift_and_shift', 'herbouw', 'vervangen', 'gedeeld', 'onbekend'"


def _herbouw_migratiepad_enum(waarden: str) -> None:
    """Type-recreate (0053/0066-precedent). NULL-rijen passeren de USING-cast als NULL."""
    op.execute("ALTER TYPE migratiepad_enum RENAME TO migratiepad_enum_old")
    op.execute(f"CREATE TYPE migratiepad_enum AS ENUM ({waarden})")
    op.execute(
        "ALTER TABLE component ALTER COLUMN migratiepad TYPE migratiepad_enum "
        "USING migratiepad::text::migratiepad_enum"
    )
    op.execute("DROP TYPE migratiepad_enum_old")


def upgrade() -> None:
    # 1. Default weg (aan het oude type gebonden) + kolom nullable — vormkeuze B.
    op.execute("ALTER TABLE component ALTER COLUMN migratiepad DROP DEFAULT")
    op.execute("ALTER TABLE component ALTER COLUMN migratiepad DROP NOT NULL")
    # 2. De sentinel wordt échte leegte (dev-data; 19/19 gemeten — nul echte bedoelingen).
    op.execute("UPDATE component SET migratiepad = NULL WHERE migratiepad = 'onbekend'")
    # 3. `onbekend` uit de enum.
    _herbouw_migratiepad_enum(_PADEN_ZONDER_ONBEKEND)


def downgrade() -> None:
    # 3'. `onbekend` terug in de enum.
    _herbouw_migratiepad_enum(_PADEN_MET_ONBEKEND)
    # 2'. Leegte terug naar de sentinel + NOT NULL + default (pre-LI040-vorm).
    op.execute("UPDATE component SET migratiepad = 'onbekend' WHERE migratiepad IS NULL")
    op.execute("ALTER TABLE component ALTER COLUMN migratiepad SET NOT NULL")
    op.execute("ALTER TABLE component ALTER COLUMN migratiepad SET DEFAULT 'onbekend'")
