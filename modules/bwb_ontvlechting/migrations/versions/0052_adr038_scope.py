"""ADR-038 — intern/extern-kenmerk op een partij (additief, Slice 1a).

Revision ID: 0052_adr038_scope
Revises: 0051_adr037_verantw
Create Date: 2026-07-04

Voegt `partij.scope` toe (`partij_scope_enum` = intern/extern). Het kenmerk is alleen betekenisvol
op `aard=organisatie` (wijzigbaar, default extern) en `aard=externe_partij` (vast extern); afdeling
(`organisatie_eenheid`) en persoon dragen het NIET zelf — ze leiden het read-side af van hun
ouder-organisatie (kolom NULL). Twee CHECK-backstops:
- `ck_partij_scope_aanwezig`: scope exact gezet dan-en-slechts-dan `aard IN (organisatie,
  externe_partij)` — zo kan een afdeling/persoon geen eigen (tegenstrijdige) waarde dragen;
- `ck_partij_externe_partij_extern`: een externe partij kan nooit intern zijn.

Bestaande organisatie-/externe_partij-rijen worden op `extern` gezet (veilige default; ontwikkel-
modus, uitsluitend testdata → reseed markeert de eigen organisatie expliciet als intern). RLS/FORCE
op `partij` blijft ongewijzigd. Engine onaangeroerd — registratie-attribuut, geen lifecycle/score.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0052_adr038_scope"
down_revision: Union[str, Sequence[str], None] = "0051_adr037_verantw"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    partij_scope = postgresql.ENUM("intern", "extern", name="partij_scope_enum", create_type=False)
    partij_scope.create(bind, checkfirst=True)

    op.add_column("partij", sa.Column("scope", partij_scope, nullable=True))

    # Backfill: bestaande organisaties + externe partijen krijgen de veilige default 'extern'.
    op.execute(
        "UPDATE partij SET scope = 'extern' WHERE aard IN ('organisatie', 'externe_partij')"
    )

    op.create_check_constraint(
        "ck_partij_scope_aanwezig", "partij",
        "(aard IN ('organisatie', 'externe_partij')) = (scope IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_partij_externe_partij_extern", "partij",
        "aard <> 'externe_partij' OR scope = 'extern'",
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_constraint("ck_partij_externe_partij_extern", "partij", type_="check")
    op.drop_constraint("ck_partij_scope_aanwezig", "partij", type_="check")
    op.drop_column("partij", "scope")
    postgresql.ENUM(name="partij_scope_enum").drop(bind, checkfirst=True)
