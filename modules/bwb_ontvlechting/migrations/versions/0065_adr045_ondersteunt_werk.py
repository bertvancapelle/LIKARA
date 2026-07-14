"""ADR-045 — "ondersteunt werk" als beheerbare eigenschap van het componenttype.

Revision ID: 0065_adr045_ondersteunt_werk
Revises: 0064_gate1b_inlees_voltooid
Create Date: 2026-07-13

- Kolom `ondersteunt_werk` op `componentconfig_optie`: boolean, NOT NULL,
  `server_default false` (spiegel van `componentrol`/0048 en `checklist_dragend`/0009 —
  bestaande rijen vullen zich vanzelf; geen derde stand).
- Conditionele CHECK (0025-vorm, strakker dan het `checklist_dragend`-precedent):
  de eigenschap kan structureel niet op een andere dimensie belanden — buiten
  `componenttype` blijft de kolom op zijn default (`false`).
- Data-reconcile (0023/0046-patroon): de vijf werkondersteunende typen (ADR-045
  besluit 2, bewust ruim — incl. fileshare/client_software: de G-schijf-werkelijkheid
  moet vastlegbaar zijn) expliciet op `true`; database/server_compute/
  integratievoorziening blijven `false`. De seed (`seed_componentconfig`) zet dezelfde
  stand op fresh deploys (byte-gelijk — geen drift).

Engine onaangeroerd — dit raakt uitsluitend platform-catalogusdata; geen tenant-/
RLS-/lifecycle-tabel. Grants ongewijzigd (kolom erft de tabel-grants).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0065_adr045_ondersteunt_werk"
down_revision: Union[str, Sequence[str], None] = "0064_gate1b_inlees_voltooid"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CK_NAAM = "ck_componentconfig_ondersteunt_werk_dim"
_CK_CONDITIE = "dimensie = 'componenttype' OR ondersteunt_werk = false"

# ADR-045 besluit 2 — bewust ruim.
_WERK_TRUE = (
    "applicatie", "saas_dienst", "landelijke_voorziening", "fileshare", "client_software",
)


def upgrade() -> None:
    op.add_column(
        "componentconfig_optie",
        sa.Column("ondersteunt_werk", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_check_constraint(_CK_NAAM, "componentconfig_optie", _CK_CONDITIE)
    # Reconcile: expliciete beginstand (defensief — raakt 0 rijen op een fresh deploy
    # waar de seed nog moet draaien; de seed zet dezelfde waarden).
    op.execute(
        sa.text(
            "UPDATE componentconfig_optie SET ondersteunt_werk = true "
            "WHERE dimensie = 'componenttype' AND optie_sleutel = ANY(:sleutels)"
        ).bindparams(sa.bindparam("sleutels", value=list(_WERK_TRUE)))
    )


def downgrade() -> None:
    op.drop_constraint(_CK_NAAM, "componentconfig_optie", type_="check")
    op.drop_column("componentconfig_optie", "ondersteunt_werk")
