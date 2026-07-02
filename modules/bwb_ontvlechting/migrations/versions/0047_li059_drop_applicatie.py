"""LI059 (Slice 3) — applicatie-subtabel opheffen; component = enige bron.

Sinds LI057 (0045) leven `migratiepad`/`complexiteit`/`prioriteit` op het basis-`component`;
de `applicatie`-subtabel hield ze nog als (dual-write) spiegel. LI059 Slice 3 maakt `component`
de énige bron: de service-laag is een dunne facade over `component` (`componenttype='applicatie'`)
geworden en de subtabel is nergens meer gequeryd. Deze migratie dropt de nu-kale subtabel
(domeinmodel §9-7: een subtype zonder type-eigen velden vervalt).

Semantiek (geverifieerd tegen de code + live DB):
- Applicatie-componenten dragen `element_type='component'` (er is GEEN `applicatie`-ElementType);
  hun ArchiMate-typing komt via de componenttype-catalogus (ADR-026). De drop raakt de
  `element`- en `component`-rijen dus NIET en vergt geen `element_type`-opruiming/enum-wijziging.
- Geen inkomende FK's naar `applicatie` (datatype/gebruikersgroep hangen via relaties — Besluit 13;
  checklistscore/blokkade ankeren op `component_profiel`), dus drop_table zonder CASCADE volstaat.
- De enum-types `migratiepad_enum`/`niveau_enum` blijven: `component` gebruikt ze (niet-exclusief).

Testdata-regel (DC016): er is uitsluitend testdata → GEEN databehoud-migratie. De downgrade
bouwt de tabel schema-reversibel terug (geen backfill); data komt uit de reseed.

Revision ID: 0047_li059_drop_applicatie
Revises: 0046_database_beoordeeld
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0047_li059_drop_applicatie"
down_revision: Union[str, Sequence[str], None] = "0046_database_beoordeeld"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Bestaande DB-enumtypes (gedeeld met `component`) — hier alléén refereren, niet (her)creëren/droppen.
_migratiepad = postgresql.ENUM(name="migratiepad_enum", create_type=False)
_niveau = postgresql.ENUM(name="niveau_enum", create_type=False)


def upgrade() -> None:
    # Drop de kale subtabel. Bijbehorende PK/FK (fk_applicatie_component), index
    # (ix_applicatie_tenant) en RLS-policy (tenant_isolation) vervallen automatisch mee.
    op.drop_table("applicatie")


def downgrade() -> None:
    # Schema-reversibel terugbouwen (GEEN databehoud/backfill — reseed levert de data).
    op.create_table(
        "applicatie",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("migratiepad", _migratiepad, nullable=False),
        sa.Column("complexiteit", _niveau, nullable=False),
        sa.Column("prioriteit", _niveau, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="applicatie_pkey"),
        sa.ForeignKeyConstraint(
            ["id"], ["component.id"], name="fk_applicatie_component", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_applicatie_tenant", "applicatie", ["tenant_id"])
    # RLS (likara-db boilerplate) + least-privilege grant voor lk_app.
    op.execute("ALTER TABLE applicatie ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE applicatie FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON applicatie "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON applicatie TO lk_app")
