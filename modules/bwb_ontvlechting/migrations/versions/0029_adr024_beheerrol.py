"""ADR-024 slice 2b — `beheerrol`-dimensie in de relatie-kenmerk-catalogus.

Revision ID: 0029_adr024_beheerrol
Revises: 0028_adr024_partij_lidmaatschap
Create Date: 2026-06-18

Voegt de dimensie `beheerrol` toe aan `relatiekenmerk_dimensie_enum` + een startset van 7
beheerrollen aan `relatiekenmerk_optie` (functioneel/technisch/applicatie-/contractbeheer,
product owner, eigenaar, proceseigenaar). Dit is de vocabulaire voor de rol-toewijzing
(`roltoewijzing`-tabel, migratie 0030).

PostgreSQL-enum-gegeven: een enum-waarde valt niet te droppen — `beheerrol` blijft bij een
downgrade als (dan ongebruikte) waarde op de enum staan (onschadelijk; fresh deploy = model
zonder die waarde is schoon). De seed is idempotent (`ON CONFLICT DO NOTHING`) en draait ook
via `platform_init`; deze migratie is de contract/backfill voor bestaande DB's.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029_adr024_beheerrol"
down_revision: Union[str, Sequence[str], None] = "0028_adr024_partij_lidmaatschap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BEHEERROL = [
    ("functioneel_beheer", "Functioneel beheer"),
    ("technisch_beheer", "Technisch beheer"),
    ("applicatiebeheer", "Applicatiebeheer"),
    ("contractbeheer", "Contractbeheer"),
    ("product_owner", "Product owner"),
    ("eigenaar", "Eigenaar"),
    ("proceseigenaar", "Proceseigenaar"),
]


def upgrade() -> None:
    # (a) beheerrol als dimensie-waarde op de relatie-kenmerk-enum (buiten transactie).
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE relatiekenmerk_dimensie_enum ADD VALUE IF NOT EXISTS 'beheerrol'"
        )
    # (b) startset beheerrollen.
    for volgorde, (sleutel, label) in enumerate(_BEHEERROL):
        op.execute(
            sa.text(
                "INSERT INTO relatiekenmerk_optie (dimensie, optie_sleutel, label, volgorde, actief) "
                "VALUES ('beheerrol', :s, :l, :v, true) "
                "ON CONFLICT (dimensie, optie_sleutel) DO NOTHING"
            ).bindparams(s=sleutel, l=label, v=volgorde)
        )


def downgrade() -> None:
    # De enum-waarde blijft staan (PostgreSQL kan een enum-waarde niet droppen) — alleen de rijen weg.
    op.execute("DELETE FROM relatiekenmerk_optie WHERE dimensie::text = 'beheerrol'")
