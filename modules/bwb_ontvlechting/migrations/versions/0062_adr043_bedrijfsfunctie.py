"""ADR-043 gate 1a — Bedrijfsfunctie: nestbaar functie-element met herkomst + vervallen (additief).

Revision ID: 0062_adr043_bedrijfsfunctie
Revises: 0061_adr043_referentiemodel
Create Date: 2026-07-12

Voegt de subtype-tabel `bedrijfsfunctie` toe — het proces-recept (0057) 1-op-1
(element-subtype: shared-PK composiet-FK → element CASCADE, FORCE RLS, composiet
self-FK `ouder_id` RESTRICT + CHECK self-parent), plus de drie ADR-043-eigen velden:

- **Herkomst**: `bron_model_id` (composiet-FK → `referentiemodel`, RESTRICT — een
  ingelezen model met functies verdwijnt niet stil) + `bron_sleutel`. Samen gezet =
  modelinhoud (read-only), samen leeg = eigen functie (CHECK `ck_…_bron_paar`).
  `UNIQUE(tenant_id, bron_model_id, bron_sleutel)` — NULL is distinct in Postgres, dus
  uniciteit geldt alléén op niet-NULL (het `checklistvraag.betekenis`-precedent; geen
  partial index nodig) en eigen functies blijven onbeperkt mogelijk.
- **`vervallen`** (boolean, default false — besluit LI039-6): "bestaat niet meer in het
  ingelezen model"; zichtbaar mét markering, niet meer koppelbaar (servicelaag).

Type-eigen velden verder: `naam` (verplicht) + `definitie` (vrije tekst,
toelichting-spiegel). `element_type_enum` kreeg 'bedrijfsfunctie' in 0060 (ADD
VALUE-precedent). Geen datamigratie (testdata volgt via de dev-seed). Engine
onaangeroerd.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0062_adr043_bedrijfsfunctie"
down_revision: Union[str, Sequence[str], None] = "0061_adr043_referentiemodel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bedrijfsfunctie",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("naam", sa.String(255), nullable=False),
        sa.Column("definitie", sa.Text(), nullable=True),
        sa.Column("ouder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bron_model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("bron_sleutel", sa.String(120), nullable=True),
        sa.Column("vervallen", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Composiet-FK-target voor de self-FK (tenant-consistent).
        sa.UniqueConstraint("tenant_id", "id", name="uq_bedrijfsfunctie_tenant_id"),
        # Bronsleutel = identiteit binnen één ingelezen model (NULL distinct → eigen
        # functies onbeperkt; geen partial index nodig).
        sa.UniqueConstraint("tenant_id", "bron_model_id", "bron_sleutel",
                            name="uq_bedrijfsfunctie_bron"),
        sa.CheckConstraint(
            "ouder_id IS NULL OR ouder_id <> id",
            name="ck_bedrijfsfunctie_geen_self_parent",
        ),
        sa.CheckConstraint(
            "(bron_model_id IS NULL) = (bron_sleutel IS NULL)",
            name="ck_bedrijfsfunctie_bron_paar",
        ),
    )
    op.create_index("ix_bedrijfsfunctie_tenant", "bedrijfsfunctie", ["tenant_id"])
    op.create_index("ix_bedrijfsfunctie_tenant_ouder", "bedrijfsfunctie", ["tenant_id", "ouder_id"])
    op.create_index("ix_bedrijfsfunctie_tenant_bron", "bedrijfsfunctie", ["tenant_id", "bron_model_id"])
    # Shared-PK: composiet-FK (tenant_id, id) → element (cross-tenant uitgesloten, cascade).
    op.create_foreign_key(
        "fk_bedrijfsfunctie_element", "bedrijfsfunctie", "element",
        ["tenant_id", "id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    # Hiërarchie: composiet self-FK met RESTRICT (subboom niet stilzwijgend wegvagen).
    op.create_foreign_key(
        "fk_bedrijfsfunctie_ouder", "bedrijfsfunctie", "bedrijfsfunctie",
        ["tenant_id", "ouder_id"], ["tenant_id", "id"], ondelete="RESTRICT",
    )
    # Herkomst: een ingelezen model met functies verdwijnt niet stil (RESTRICT-backstop).
    op.create_foreign_key(
        "fk_bedrijfsfunctie_bron_model", "bedrijfsfunctie", "referentiemodel",
        ["tenant_id", "bron_model_id"], ["tenant_id", "id"], ondelete="RESTRICT",
    )
    op.execute("ALTER TABLE bedrijfsfunctie ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE bedrijfsfunctie FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON bedrijfsfunctie "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON bedrijfsfunctie FROM lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON bedrijfsfunctie TO lk_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON bedrijfsfunctie")
    op.drop_constraint("fk_bedrijfsfunctie_bron_model", "bedrijfsfunctie", type_="foreignkey")
    op.drop_constraint("fk_bedrijfsfunctie_ouder", "bedrijfsfunctie", type_="foreignkey")
    op.drop_constraint("fk_bedrijfsfunctie_element", "bedrijfsfunctie", type_="foreignkey")
    op.drop_index("ix_bedrijfsfunctie_tenant_bron", table_name="bedrijfsfunctie")
    op.drop_index("ix_bedrijfsfunctie_tenant_ouder", table_name="bedrijfsfunctie")
    op.drop_index("ix_bedrijfsfunctie_tenant", table_name="bedrijfsfunctie")
    op.drop_table("bedrijfsfunctie")
