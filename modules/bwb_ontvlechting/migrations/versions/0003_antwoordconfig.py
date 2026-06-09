"""ADR-019 — configureerbaar antwoordveld per checklistvraag (additief).

Revision ID: 0003_antwoordconfig
Revises: 0002_platform_tenant
Create Date: 2026-06-09

Volledig ADDITIEF (geen wijziging aan bestaande kolommen/logica):
  (a) `antwoordtype` op `checklistvraag` (enum, NOT NULL server_default 'geen'
      → bestaande 89 rijen blijven geldig, geen backfill);
  (b) nieuwe referentietabel `checklistvraag_optie` (optie-catalogus, GEEN RLS);
  (c) `antwoord_waarde` (jsonb, nullable) op `checklistscore`.

Grants (R2, least-privilege): de catalogus is platform-beheerd. `cd_app` mag
alleen LEZEN (validatie van het antwoord in het tenant-pad); `cd_platform` mag
SELECT/INSERT/UPDATE (beheer + soft-deactivate, komt in fase 2D). `cd_platform`
mag `checklistvraag` lezen + bijwerken (antwoordtype/labels). De score-/blokkade-/
lifecycle-engine wordt niet geraakt.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_antwoordconfig"
down_revision: Union[str, Sequence[str], None] = "0002_platform_tenant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    antwoordtype = postgresql.ENUM(
        "geen", "enkelvoudige_keuze", "meerkeuze", "getal",
        name="antwoordtype_enum", create_type=False,
    )
    antwoordtype.create(bind, checkfirst=True)

    # (a) antwoordtype op checklistvraag — additief, default 'geen'.
    op.add_column(
        "checklistvraag",
        sa.Column("antwoordtype", antwoordtype, nullable=False, server_default=sa.text("'geen'")),
    )

    # (b) optie-catalogus (referentiedata, geen RLS).
    op.create_table(
        "checklistvraag_optie",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("vraag_code", sa.String(10), sa.ForeignKey("checklistvraag.code"), nullable=False),
        sa.Column("optie_sleutel", sa.String(60), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("volgorde", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("actief", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("afgeleid_bron", sa.String(40), nullable=True),
        sa.UniqueConstraint("vraag_code", "optie_sleutel", name="uq_checklistvraag_optie"),
    )
    op.create_index("ix_checklistvraag_optie_vraag", "checklistvraag_optie", ["vraag_code"])

    # (c) antwoord_waarde op checklistscore (tenant-tabel; erft RLS + cd_app-grants).
    op.add_column("checklistscore", sa.Column("antwoord_waarde", postgresql.JSONB(), nullable=True))

    # --- Grants (R2, least-privilege) ---
    # Catalogus: cd_app LEEST alleen (validatie); cd_platform beheert.
    op.execute("REVOKE ALL ON checklistvraag_optie FROM cd_app")
    op.execute("GRANT SELECT ON checklistvraag_optie TO cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON checklistvraag_optie TO cd_platform")
    # checklistvraag: cd_platform mag antwoordtype/labels beheren (lezen + wijzigen).
    op.execute("GRANT SELECT, UPDATE ON checklistvraag TO cd_platform")


def downgrade() -> None:
    bind = op.get_bind()
    op.execute("REVOKE ALL ON checklistvraag FROM cd_platform")
    op.drop_column("checklistscore", "antwoord_waarde")
    op.drop_index("ix_checklistvraag_optie_vraag", table_name="checklistvraag_optie")
    op.drop_table("checklistvraag_optie")
    op.drop_column("checklistvraag", "antwoordtype")
    postgresql.ENUM(name="antwoordtype_enum").drop(bind, checkfirst=True)
