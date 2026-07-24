"""ADR-056 snede 1 — de formulering wordt bevroren bij het antwoord.

Drie additieve kolommen:
- `checklistscore.vraag_bevroren` (TEXT NOT NULL) — wat er gevraagd werd toen het
  antwoord gegeven werd; "verouderd" is de vergelijking met de huidige vraagtekst
  (besluit 4), geen tweede administratie.
- `checklistscore.vraag_verduidelijkt_op` (timestamptz NULL) — de stille notitie
  bij een verduidelijking (besluit 6).
- `checklistvraag.laatste_wijzigingsaard` (varchar(20) NULL) — de keuze van de
  beheerder (verduidelijking | wijziging) als echte kolom, zodat hij in de
  audit-diff van de tekstwijziging landt (besluit 2; DC016-precedent).

Vulling = het nulpunt (besluit 18): bestaande antwoorden gelden als gegeven op de
HUIDIGE vraagstelling — de backfill kopieert de huidige tekst. Cross-tenant als
lk_admin (superuser bypasst FORCE RLS; het F-3-precedent). Alleen testdata; op een
fresh deploy raakt de backfill 0 rijen en zet de service de kolom bij elk antwoord.

Revision ID: 0076_adr056_vraag_bevroren
Revises: 0075_li050_vraag_volgorde
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0076_adr056_vraag_bevroren"
down_revision: Union[str, Sequence[str], None] = "0075_li050_vraag_volgorde"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("checklistscore", sa.Column("vraag_bevroren", sa.Text(), nullable=True))
    # Nulpunt (besluit 18): elk bestaand antwoord geldt als gegeven op de huidige
    # formulering. Tenant-gelijkheid zit in de join (composiet-FK-semantiek).
    op.execute(
        "UPDATE checklistscore s SET vraag_bevroren = v.vraag "
        "FROM checklistvraag v "
        "WHERE v.tenant_id = s.tenant_id AND v.id = s.checklistvraag_id"
    )
    op.alter_column("checklistscore", "vraag_bevroren", nullable=False)
    op.add_column(
        "checklistscore",
        sa.Column("vraag_verduidelijkt_op", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "checklistvraag",
        sa.Column("laatste_wijzigingsaard", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("checklistvraag", "laatste_wijzigingsaard")
    op.drop_column("checklistscore", "vraag_verduidelijkt_op")
    op.drop_column("checklistscore", "vraag_bevroren")
