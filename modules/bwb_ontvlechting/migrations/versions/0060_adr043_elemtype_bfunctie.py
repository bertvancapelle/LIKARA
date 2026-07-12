"""ADR-043 gate 1a — `element_type_enum` ADD VALUE 'bedrijfsfunctie' (aparte, voorafgaande stap).

Revision ID: 0060_adr043_elemtype_bfunctie
Revises: 0059_adr042_procesvervulling
Create Date: 2026-07-12

Precedent: 0056 (ADD VALUE 'proces') / 0026 ('partij'). PostgreSQL staat
`ALTER TYPE … ADD VALUE` niet toe in dezelfde transactie als het eerste gebruik van de
nieuwe waarde → de enum-uitbreiding is een eigen migratie vóór de subtype-migratie
(0062). `IF NOT EXISTS` maakt hem idempotent. Downgrade: PostgreSQL kan een enum-waarde
niet droppen — de waarde blijft (ongebruikt) staan; gedocumenteerd, geen actie.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0060_adr043_elemtype_bfunctie"
down_revision: Union[str, Sequence[str], None] = "0059_adr042_procesvervulling"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Buiten de transactie uitvoeren (ADD VALUE-beperking) — het 0026/0056-patroon.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE element_type_enum ADD VALUE IF NOT EXISTS 'bedrijfsfunctie'")


def downgrade() -> None:
    # PostgreSQL kan een enum-waarde niet verwijderen; 'bedrijfsfunctie' blijft als
    # ongebruikte waarde staan (zelfde gedocumenteerde beperking als 0026/0056).
    pass
