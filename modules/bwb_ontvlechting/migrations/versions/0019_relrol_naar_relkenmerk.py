"""ADR-023 consistentie-opruim — relatie_rol: ContractConfig → relatie-kenmerk-catalogus.

Revision ID: 0019_relrol_naar_relkenmerk
Revises: 0018_adr023_plateau
Create Date: 2026-06-15

Verhuist de `relatie_rol`-vocabulaire (valt_onder/onderhoud/hosting) van de contract-
configuratie-catalogus (`contractconfig_optie`) naar de algemene relatie-kenmerk-catalogus
(`relatiekenmerk_optie`) — relatie_rol is een relatie-kenmerk, geen contract-configuratie.

Functioneel verandert er niets: de contract↔component-association blijft `relatie_rol` als
kenmerk dragen met dezelfde drie waarden; alleen de catalogus-herkomst (waartegen ze
gevalideerd/gelabeld worden) verschuift. Bestaande relatie-data wordt NIET herschreven.

PostgreSQL-enum-gegeven: een enum-waarde valt niet te droppen. `relatie_rol` blijft als
(dan ongebruikte) waarde op `contractconfig_dimensie_enum` staan — onschadelijk, want geen
rij/code gebruikt die nog. Een fresh deploy (model zonder die waarde) is schoon.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019_relrol_naar_relkenmerk"
down_revision: Union[str, Sequence[str], None] = "0018_adr023_plateau"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RELATIE_ROL = [
    ("valt_onder", "Valt onder / aanschaf"),
    ("onderhoud", "Onderhoud"),
    ("hosting", "Hosting"),
]

_ASSOCIATION_KENMERKEN = (
    '{"relatie_rol": {"type": "catalogus", "catalogus": "relatiekenmerk", "dimensie": "relatie_rol"}}'
)


def upgrade() -> None:
    # (a) relatie_rol als dimensie-waarde op de relatie-kenmerk-enum (buiten transactie).
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE relatiekenmerk_dimensie_enum ADD VALUE IF NOT EXISTS 'relatie_rol'"
        )
    # (b) relatie_rol-waarden naar relatiekenmerk_optie.
    for volgorde, (sleutel, label) in enumerate(_RELATIE_ROL):
        op.execute(
            sa.text(
                "INSERT INTO relatiekenmerk_optie (dimensie, optie_sleutel, label, volgorde, actief) "
                "VALUES ('relatie_rol', :s, :l, :v, true) "
                "ON CONFLICT (dimensie, optie_sleutel) DO NOTHING"
            ).bindparams(s=sleutel, l=label, v=volgorde)
        )
    # (c) relatie_rol uit ContractConfig verwijderen (blijft dekking + kostenmodel).
    op.execute("DELETE FROM contractconfig_optie WHERE dimensie::text = 'relatie_rol'")
    # (d) association-kenmerk-definitie naar de relatiekenmerk-catalogus laten routeren.
    op.execute(
        sa.text(
            "UPDATE componentconfig_optie SET kenmerk_definitie = CAST(:k AS jsonb) "
            "WHERE dimensie = 'archimate_relatie' AND optie_sleutel = 'association'"
        ).bindparams(k=_ASSOCIATION_KENMERKEN)
    )


def downgrade() -> None:
    # (d) association terug naar de ContractConfig-herkomst.
    op.execute(
        "UPDATE componentconfig_optie "
        "SET kenmerk_definitie = '{\"relatie_rol\": {\"type\": \"catalogus\", \"dimensie\": \"relatie_rol\"}}'::jsonb "
        "WHERE dimensie = 'archimate_relatie' AND optie_sleutel = 'association'"
    )
    # (c) relatie_rol terug in ContractConfig (de enum-waarde stond er nog).
    for volgorde, (sleutel, label) in enumerate(_RELATIE_ROL):
        op.execute(
            sa.text(
                "INSERT INTO contractconfig_optie (dimensie, optie_sleutel, label, volgorde, actief) "
                "VALUES ('relatie_rol', :s, :l, :v, true) "
                "ON CONFLICT (dimensie, optie_sleutel) DO NOTHING"
            ).bindparams(s=sleutel, l=label, v=volgorde)
        )
    # (b) relatie_rol uit relatiekenmerk_optie. (De enum-waarde blijft — niet droppen.)
    op.execute("DELETE FROM relatiekenmerk_optie WHERE dimensie::text = 'relatie_rol'")
