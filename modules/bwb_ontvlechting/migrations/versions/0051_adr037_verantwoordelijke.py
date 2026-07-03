"""ADR-037 — verantwoordelijke per checklistantwoord: vrije tekst → verwijzing naar een partij.

Revision ID: 0051_adr037_verantw
Revises: 0050_adr036a_gg_afdeling
Create Date: 2026-07-03

Vervangt het vrije-tekstveld `checklistscore.eigenaar` (String(255)) door een optionele composiet-FK
`(tenant_id, verantwoordelijke_id) → element(tenant_id, id)` naar een partij met aard
organisatie_eenheid (afdeling) óf persoon (app-side geborgd, spiegel van
`component.eigenaar_organisatie_id`). ON DELETE **SET NULL** — kolom-specifiek op
`verantwoordelijke_id` (PostgreSQL 15+); een kale SET NULL zou óók de gedeelde `tenant_id` (NOT NULL)
nullen. Reverse-lookup-index. Geen backfill (ontwikkelmodus: alleen testdata → reseed).

Laat tevens `blokkade.eigenaar` (String(255)) vervallen: de blokkade-verantwoordelijke wordt in de
leeslaag AFGELEID van de verantwoordelijke van het onderliggende antwoord
(`blokkade.checklistscore_id` → `checklistscore.verantwoordelijke_id`). Geen kolom, geen schrijfpad.

RLS/FORCE op de bestaande tabellen blijft ongewijzigd (kolom-mutaties erven de tabel-policy).
Engine onaangeroerd — registratief; score blijft de enige lifecycle-driver.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0051_adr037_verantw"
down_revision: Union[str, Sequence[str], None] = "0050_adr036a_gg_afdeling"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # checklistscore: vrije tekst → partij-FK.
    op.add_column(
        "checklistscore",
        sa.Column("verantwoordelijke_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # Kolom-specifieke SET NULL: alleen verantwoordelijke_id nullen, niet de gedeelde tenant_id.
    op.execute(
        "ALTER TABLE checklistscore ADD CONSTRAINT fk_checklistscore_verantwoordelijke "
        "FOREIGN KEY (tenant_id, verantwoordelijke_id) REFERENCES element (tenant_id, id) "
        "ON DELETE SET NULL (verantwoordelijke_id)"
    )
    op.create_index(
        "ix_checklistscore_tenant_verantwoordelijke",
        "checklistscore",
        ["tenant_id", "verantwoordelijke_id"],
    )
    op.drop_column("checklistscore", "eigenaar")

    # blokkade: eigenaar vervalt (wordt afgeleid uit de antwoord-verantwoordelijke).
    op.drop_column("blokkade", "eigenaar")


def downgrade() -> None:
    op.add_column("blokkade", sa.Column("eigenaar", sa.String(255), nullable=True))

    op.add_column("checklistscore", sa.Column("eigenaar", sa.String(255), nullable=True))
    op.drop_index("ix_checklistscore_tenant_verantwoordelijke", table_name="checklistscore")
    op.drop_constraint("fk_checklistscore_verantwoordelijke", "checklistscore", type_="foreignkey")
    op.drop_column("checklistscore", "verantwoordelijke_id")
