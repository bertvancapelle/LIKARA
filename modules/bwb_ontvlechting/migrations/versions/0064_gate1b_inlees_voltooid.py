"""Gate 1b-afronding — `referentiemodel.inlees_voltooid`: een onvoltooide inlees mag
nooit stil blijven.

Revision ID: 0064_gate1b_inlees_voltooid
Revises: 0063_adr044_plaatsing
Create Date: 2026-07-13

De import schrijft per functie/plaatsing een eigen transactie (het facade-hergebruik,
gate 1b blok 1); een afgebroken inlees laat dus een halve boom achter — functioneel
herstelbaar (idempotente herstart), maar onzichtbaar voor de gebruiker, en de
vervallen-markering (laatste stap) kan dan nog ontbreken. Deze additieve vlag maakt
begin en eind expliciet: `voer_uit` zet hem False vóór de eerste schrijfactie en True
ná de laatste; False bij het openen van het scherm = eerlijk signaal "de vorige inlees
is niet afgerond". Echte kolom → audit-naspeurbaar (DC016-precedent).

Schemastap: alleen de kolom (server_default true — bestaande rijen zijn per definitie
niet-halverwege: vóór deze vlag bestond het begin/eind-onderscheid niet; testdata-regel:
geen datamigratie, de dev-seed eindigt sowieso met een voltooide import).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0064_gate1b_inlees_voltooid"
down_revision: Union[str, None] = "0063_adr044_plaatsing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "referentiemodel",
        sa.Column(
            "inlees_voltooid", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
    )


def downgrade() -> None:
    op.drop_column("referentiemodel", "inlees_voltooid")
