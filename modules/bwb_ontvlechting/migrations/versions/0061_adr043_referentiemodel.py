"""ADR-043 gate 1a — referentiemodel: platform-aanbod + tenant-ingelezen-instantie (additief).

Revision ID: 0061_adr043_referentiemodel
Revises: 0060_adr043_elemtype_bfunctie
Create Date: 2026-07-12

Twee lagen (besluit LI039-5):
- `referentiemodel_optie` (PLATFORM-aanbod, GEEN RLS) — het catalogus-recept (0058)
  1-op-1 plus twee model-eigen kolommen (`herkomst`, `versie`): grants lk_app
  SELECT-only, lk_platform SELECT/INSERT/UPDATE + sequence, GEEN DELETE
  (soft-deactivate via `actief`). Seed byte-gelijk aan
  `services/seed_referentiemodel.py`; `platform_init` zaait dezelfde stand.
- `referentiemodel` (TENANT-instantie, FORCE RLS) — wélk model déze tenant heeft
  ingelezen (sleutel + naam/versie-snapshot + `ingelezen_op`). `UNIQUE(tenant_id,
  model_sleutel)`: een herinlees wérkt de bestaande instantie bij, geen tweede rij.
  `UNIQUE(tenant_id, id)` is het composiet-FK-target voor
  `bedrijfsfunctie.bron_model_id` (0062).

Engine onaangeroerd (registratie + leeslaag).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0061_adr043_referentiemodel"
down_revision: Union[str, Sequence[str], None] = "0060_adr043_elemtype_bfunctie"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Byte-gelijk aan services/seed_referentiemodel.py (_MODELLEN).
_MODELLEN = [
    (
        "gemma_bedrijfsfuncties",
        "GEMMA Bedrijfsfuncties",
        "VNG Realisatie — GEMMA Basisarchitectuur (gemmaonline.nl)",
        "GEMMA 2 (2025)",
    ),
]


def upgrade() -> None:
    # ── Platform-aanbod (catalogus-recept 0058) ─────────────────────────────────────
    op.create_table(
        "referentiemodel_optie",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("optie_sleutel", sa.String(60), nullable=False),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("herkomst", sa.String(255), nullable=False),
        sa.Column("versie", sa.String(60), nullable=False),
        sa.Column("volgorde", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("actief", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("optie_sleutel", name="uq_referentiemodel_optie"),
    )
    op.execute("REVOKE ALL ON referentiemodel_optie FROM lk_app")
    op.execute("GRANT SELECT ON referentiemodel_optie TO lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON referentiemodel_optie TO lk_platform")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE referentiemodel_optie_id_seq TO lk_platform")
    for volgorde, (sleutel, label, herkomst, versie) in enumerate(_MODELLEN):
        op.execute(
            sa.text(
                "INSERT INTO referentiemodel_optie "
                "(optie_sleutel, label, herkomst, versie, volgorde, actief) "
                "VALUES (:s, :l, :h, :ver, :v, true) "
                "ON CONFLICT (optie_sleutel) DO NOTHING"
            ).bindparams(s=sleutel, l=label, h=herkomst, ver=versie, v=volgorde)
        )

    # ── Tenant-ingelezen-instantie (FORCE RLS) ──────────────────────────────────────
    op.create_table(
        "referentiemodel",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_sleutel", sa.String(60), nullable=False),
        sa.Column("naam", sa.String(150), nullable=False),
        sa.Column("versie", sa.String(60), nullable=False),
        sa.Column("ingelezen_op", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Composiet-FK-target voor bedrijfsfunctie.bron_model_id (tenant-consistent).
        sa.UniqueConstraint("tenant_id", "id", name="uq_referentiemodel_tenant_id"),
        # Eén ingelezen instantie per model per tenant (herinlees = bijwerken).
        sa.UniqueConstraint("tenant_id", "model_sleutel", name="uq_referentiemodel_sleutel"),
    )
    op.create_index("ix_referentiemodel_tenant", "referentiemodel", ["tenant_id"])
    op.execute("ALTER TABLE referentiemodel ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE referentiemodel FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON referentiemodel "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON referentiemodel FROM lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON referentiemodel TO lk_app")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON referentiemodel")
    op.drop_index("ix_referentiemodel_tenant", table_name="referentiemodel")
    op.drop_table("referentiemodel")
    op.drop_table("referentiemodel_optie")
