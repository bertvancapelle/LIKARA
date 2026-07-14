"""ADR-051 (gate 3) — functievervulling draagt nu ook "geen systeem" + een oordeel.

Revision ID: 0070_adr051_gapsignaal
Revises: 0069_adr049_functievervulling
Create Date: 2026-07-14

Besluit 2: een rij draagt precies ÉÉN van beide — een component óf de uitkomst "geen systeem —
vastgesteld". `component_id` wordt nullable; `geen_systeem` (bool) erbij; XOR-CHECK borgt structureel
"nooit geen van beide, nooit allebei". Besluit 3/4: `oordeel` (naar_behoren/noodoplossing, optioneel)
bij de koppeling — CHECK weigert een oordeel op een geen-systeem-rij.

De twee partiële UNIQUE-indexen krijgen `component_id IS NOT NULL` (component-koppelingen), en er
komen twee nieuwe voor de geen-systeem-bevindingen (hoogstens één per plek — het NULL-distinct-gat
dat nu ook voor de NULL-component-kant dicht moet). Ontwikkelmodus: schemastap + reseed; geen
datamigratie (alleen testdata).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0070_adr051_gapsignaal"
down_revision: Union[str, Sequence[str], None] = "0069_adr049_functievervulling"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OORDEEL = postgresql.ENUM("naar_behoren", "noodoplossing", name="functievervulling_oordeel_enum")


def upgrade() -> None:
    _OORDEEL.create(op.get_bind(), checkfirst=True)
    op.alter_column("functievervulling", "component_id", nullable=True)
    op.add_column("functievervulling",
                  sa.Column("geen_systeem", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("functievervulling", sa.Column("oordeel", _OORDEEL, nullable=True))

    # Herbouw de component-indexen (component_id IS NOT NULL erbij) + de geen-systeem-indexen.
    op.drop_index("uq_functievervulling_grof", table_name="functievervulling")
    op.drop_index("uq_functievervulling_fijn", table_name="functievervulling")
    op.create_index("uq_functievervulling_grof", "functievervulling",
                    ["tenant_id", "component_id", "functie_id"], unique=True,
                    postgresql_where=sa.text("ouder_functie_id IS NULL AND component_id IS NOT NULL"))
    op.create_index("uq_functievervulling_fijn", "functievervulling",
                    ["tenant_id", "component_id", "functie_id", "ouder_functie_id"], unique=True,
                    postgresql_where=sa.text("ouder_functie_id IS NOT NULL AND component_id IS NOT NULL"))
    op.create_index("uq_functievervulling_geen_grof", "functievervulling",
                    ["tenant_id", "functie_id"], unique=True,
                    postgresql_where=sa.text("ouder_functie_id IS NULL AND geen_systeem"))
    op.create_index("uq_functievervulling_geen_fijn", "functievervulling",
                    ["tenant_id", "functie_id", "ouder_functie_id"], unique=True,
                    postgresql_where=sa.text("ouder_functie_id IS NOT NULL AND geen_systeem"))

    op.create_check_constraint("ck_functievervulling_component_xor_geen", "functievervulling",
                               "(component_id IS NOT NULL) <> geen_systeem")
    op.create_check_constraint("ck_functievervulling_oordeel_alleen_component", "functievervulling",
                               "oordeel IS NULL OR geen_systeem = false")


def downgrade() -> None:
    op.drop_constraint("ck_functievervulling_oordeel_alleen_component", "functievervulling", type_="check")
    op.drop_constraint("ck_functievervulling_component_xor_geen", "functievervulling", type_="check")
    op.drop_index("uq_functievervulling_geen_fijn", table_name="functievervulling")
    op.drop_index("uq_functievervulling_geen_grof", table_name="functievervulling")
    op.drop_index("uq_functievervulling_fijn", table_name="functievervulling")
    op.drop_index("uq_functievervulling_grof", table_name="functievervulling")
    op.create_index("uq_functievervulling_grof", "functievervulling",
                    ["tenant_id", "component_id", "functie_id"], unique=True,
                    postgresql_where=sa.text("ouder_functie_id IS NULL"))
    op.create_index("uq_functievervulling_fijn", "functievervulling",
                    ["tenant_id", "component_id", "functie_id", "ouder_functie_id"], unique=True,
                    postgresql_where=sa.text("ouder_functie_id IS NOT NULL"))
    op.drop_column("functievervulling", "oordeel")
    op.drop_column("functievervulling", "geen_systeem")
    op.alter_column("functievervulling", "component_id", nullable=False)
    _OORDEEL.drop(op.get_bind(), checkfirst=True)
