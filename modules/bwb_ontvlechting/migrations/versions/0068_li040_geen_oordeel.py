"""LI040 — "Midden" is geen oordeel als niemand het heeft gegeven.

`complexiteit` en `prioriteit` droegen een server_default `midden`: een verzonnen
oordeel dat elk component ongevraagd kreeg en — anders dan het zojuist opgeruimde
"Onbekend" — als échte uitspraak oogde ("iemand vond dit gemiddeld"). Precies de
kolommen waarop een bestuurder sorteert om te bepalen waar hij begint.

Zelfde patroon als 0067 (vormkeuze B, ADR-046): beide kolommen NULLABLE zonder default;
de bestaande default-rijen worden échte leegte (gemeten V040: 19/19 `midden` op beide —
géén bewust gezette hoog/laag, dus zuiver een default; het stop-punt uit de opdracht is
niet geraakt). De `niveau_enum` zelf blijft ONGEWIJZIGD (laag/midden/hoog — midden is
een geldig oordeel; alleen de gratis uitdeling verdwijnt, dus geen enum-recreate nodig).
Engine onaangeroerd — registratieve velden; score blijft de enige lifecycle-driver.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0068_li040_geen_oordeel"
down_revision: Union[str, Sequence[str], None] = "0067_li040_bedoeling_leeg"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_KOLOMMEN = ("complexiteit", "prioriteit")


def upgrade() -> None:
    for kolom in _KOLOMMEN:
        # Default weg (de 0066/0067-valkuil: de default moet expliciet mee) + nullable.
        op.execute(f"ALTER TABLE component ALTER COLUMN {kolom} DROP DEFAULT")
        op.execute(f"ALTER TABLE component ALTER COLUMN {kolom} DROP NOT NULL")
        # De default-rijen worden échte leegte ("nog niet vastgelegd").
        op.execute(f"UPDATE component SET {kolom} = NULL WHERE {kolom} = 'midden'")


def downgrade() -> None:
    for kolom in _KOLOMMEN:
        op.execute(f"UPDATE component SET {kolom} = 'midden' WHERE {kolom} IS NULL")
        op.execute(f"ALTER TABLE component ALTER COLUMN {kolom} SET NOT NULL")
        op.execute(f"ALTER TABLE component ALTER COLUMN {kolom} SET DEFAULT 'midden'")
