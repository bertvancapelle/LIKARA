"""ADR-042 slice 2 — applicatiefunctie-catalogus (platform-breed, additief).

Revision ID: 0058_adr042_appfunctie
Revises: 0057_adr042_proces
Create Date: 2026-07-08

Platform-brede `applicatiefunctie_optie`-catalogus (GEEN RLS) — het componentrol-recept
(0048) 1-op-1: id-PK, `optie_sleutel` UNIQUE, label/volgorde/actief; grants lk_app
SELECT-only, lk_platform SELECT/INSERT/UPDATE + sequence, GEEN DELETE (soft-deactivate
via `actief`). GEMMA-geënte startset (registreren/raadplegen/archiveren/gegevens_leveren/
ondersteunen) — géén systeem-sleutel (alles deactiveerbaar, ADR-042 besluit 3). De seed is
byte-gelijk aan `seed_applicatiefunctie` (idempotent, ON CONFLICT DO NOTHING);
platform_init zaait dezelfde stand. Engine onaangeroerd.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0058_adr042_appfunctie"
down_revision: Union[str, Sequence[str], None] = "0057_adr042_proces"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Byte-gelijk aan services/seed_applicatiefunctie.py (_FUNCTIES).
_FUNCTIES = [
    ("registreren", "Registreren"),
    ("raadplegen", "Raadplegen"),
    ("archiveren", "Archiveren"),
    ("gegevens_leveren", "Gegevens leveren"),
    ("ondersteunen", "Ondersteunen"),
]


def upgrade() -> None:
    op.create_table(
        "applicatiefunctie_optie",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("optie_sleutel", sa.String(60), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("volgorde", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("actief", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("optie_sleutel", name="uq_applicatiefunctie_optie"),
    )
    op.execute("REVOKE ALL ON applicatiefunctie_optie FROM lk_app")
    op.execute("GRANT SELECT ON applicatiefunctie_optie TO lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON applicatiefunctie_optie TO lk_platform")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE applicatiefunctie_optie_id_seq TO lk_platform")
    for volgorde, (sleutel, label) in enumerate(_FUNCTIES):
        op.execute(
            sa.text(
                "INSERT INTO applicatiefunctie_optie (optie_sleutel, label, volgorde, actief) "
                "VALUES (:s, :l, :v, true) ON CONFLICT (optie_sleutel) DO NOTHING"
            ).bindparams(s=sleutel, l=label, v=volgorde)
        )


def downgrade() -> None:
    op.drop_table("applicatiefunctie_optie")
