"""ADR-023 Fase B-mig-2 slice 1 — koppeling → flow-relatie (cutover, brekend).

Revision ID: 0014_adr023_cutover_koppeling
Revises: 0013_adr023_promotie_elementen
Create Date: 2026-06-14

`koppeling` → één `flow`-relatie per koppeling (OK-1 + OK-2-v3, 1-op-1): id hergebruikt,
oriëntatie bron→doel behouden, `protocol`/`impact_bij_verbreking`/`richting` als kenmerken.
Daarna `koppeling` droppen. Bron/doel waren al component-FK's = element-id's → de
composiet-FK naar `element` klopt. `ON CONFLICT DO NOTHING` borgt tegen een (zeldzame)
dubbele bron/doel-flow t.o.v. de relatie-UNIQUE.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_adr023_cutover_koppeling"
down_revision: Union[str, Sequence[str], None] = "0013_adr023_promotie_elementen"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO relatie
            (id, tenant_id, bron_id, doel_id, relatietype, kenmerken, omschrijving,
             created_at, updated_at)
        SELECT id, tenant_id, bron_applicatie_id, doel_applicatie_id, 'flow',
               jsonb_build_object(
                   'protocol', protocol::text,
                   'impact_bij_verbreking', impact_bij_verbreking::text,
                   'richting', richting::text),
               omschrijving, created_at, updated_at
        FROM koppeling
        ON CONFLICT (tenant_id, bron_id, doel_id, relatietype) DO NOTHING
        """
    )
    op.drop_table("koppeling")


def downgrade() -> None:
    """Best-effort terug (pre-prod): herstel de koppeling-tabel uit de flow-relaties."""
    koppelrichting = postgresql.ENUM(name="koppelrichting_enum", create_type=False)
    koppelprotocol = postgresql.ENUM(name="koppelprotocol_enum", create_type=False)
    impact = postgresql.ENUM(name="impact_verbreking_enum", create_type=False)
    op.create_table(
        "koppeling",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bron_applicatie_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doel_applicatie_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("richting", koppelrichting, nullable=False),
        sa.Column("protocol", koppelprotocol, nullable=False),
        sa.Column("impact_bij_verbreking", impact, nullable=False),
        sa.Column("omschrijving", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("bron_applicatie_id <> doel_applicatie_id", name="ck_koppeling_bron_ne_doel"),
    )
    op.execute(
        """
        INSERT INTO koppeling
            (id, tenant_id, bron_applicatie_id, doel_applicatie_id, richting, protocol,
             impact_bij_verbreking, omschrijving, created_at, updated_at)
        SELECT id, tenant_id, bron_id, doel_id,
               (kenmerken->>'richting')::koppelrichting_enum,
               (kenmerken->>'protocol')::koppelprotocol_enum,
               (kenmerken->>'impact_bij_verbreking')::impact_verbreking_enum,
               omschrijving, created_at, updated_at
        FROM relatie WHERE relatietype = 'flow'
        """
    )
    op.execute("ALTER TABLE koppeling ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE koppeling FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON koppeling "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("DELETE FROM relatie WHERE relatietype = 'flow'")
