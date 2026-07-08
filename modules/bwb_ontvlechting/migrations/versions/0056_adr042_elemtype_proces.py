"""ADR-042 slice 1 — `element_type_enum` ADD VALUE 'proces' (aparte, voorafgaande stap).

Revision ID: 0056_adr042_elemtype_proces
Revises: 0055_adr041_gebruiker_voorkeur
Create Date: 2026-07-08

Precedent: 0026 (ADD VALUE 'partij'). PostgreSQL staat `ALTER TYPE … ADD VALUE` niet toe
in dezelfde transactie als het eerste gebruik van de nieuwe waarde → de enum-uitbreiding
is een eigen migratie vóór de subtype-migratie (0057). `IF NOT EXISTS` maakt hem
idempotent. Downgrade: PostgreSQL kan een enum-waarde niet droppen — de waarde blijft
(ongebruikt) staan; gedocumenteerd, geen actie.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0056_adr042_elemtype_proces"
down_revision: Union[str, Sequence[str], None] = "0055_adr041_gebruiker_voorkeur"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Buiten de transactie uitvoeren (ADD VALUE-beperking) — het 0026-patroon.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE element_type_enum ADD VALUE IF NOT EXISTS 'proces'")


def downgrade() -> None:
    # PostgreSQL kan een enum-waarde niet verwijderen; 'proces' blijft als ongebruikte
    # waarde staan (zelfde gedocumenteerde beperking als bij 0026/'partij').
    pass
