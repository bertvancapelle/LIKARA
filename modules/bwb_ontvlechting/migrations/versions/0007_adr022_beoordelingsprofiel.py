"""ADR-022 Fase A — generiek beoordelingsprofiel (pre-productie, géén datamigratie).

Revision ID: 0007_adr022_beoordelingsprofiel
Revises: 0006_component_herfundering
Create Date: 2026-06-12

Fase A van ADR-022: brengt het datamodel in de doelvorm zonder engine-semantiek
te wijzigen (per-type scoping volgt in Fase B).

- Nieuwe tenant-tabel `component_profiel` (shared-PK met `component`): drager van
  de engine-state (`lifecycle_status`); RLS + FORCE + cd_app-grants (CD040-stijl).
- `lifecycle_status` VERHUIST van `applicatie` → `component_profiel`.
- `checklistvraag` herstructureert naar een surrogate UUID-PK (`id`), met
  `componenttype`-discriminator (backfill `'applicatie'`) en `UNIQUE(componenttype,
  code)` i.p.v. de globale `UNIQUE(code)` (Knoop 3 Optie B). Grants → catalogus-
  patroon: cd_app SELECT-only, cd_platform SELECT/INSERT/UPDATE (geen sequence: uuid).
- Kind-FK's retargeten naar `checklistvraag.id`: `checklistvraag_optie.vraag_code`
  en `checklistscore.vraag_code` → `checklistvraag_id`.
- `checklistscore`/`blokkade` herankeren `applicatie_id` → `component_id`
  (FK → `component_profiel.id`).

Pre-productie (ADR-021 Besluit 11-stijl): de tenant-laag wordt geleegd
(`TRUNCATE component CASCADE`) en `dev_seed_testdata.py` herseedt; `checklistvraag`
en `checklistvraag_optie` (platform-referentiedata) blijven behouden en worden
ge-backfilld. Geen productie-datamigratiepad (eenmalig, geaccepteerd).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_adr022_beoordelingsprofiel"
down_revision: Union[str, Sequence[str], None] = "0006_component_herfundering"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    lifecycle = postgresql.ENUM(name="lifecycle_status_enum", create_type=False)

    # === (a) component_profiel (tenant-scoped, shared-PK met component) ===
    op.create_table(
        "component_profiel",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("component.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lifecycle_status", lifecycle, nullable=False, server_default=sa.text("'concept'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_component_profiel_tenant_lifecycle", "component_profiel",
        ["tenant_id", "lifecycle_status"],
    )
    op.execute("ALTER TABLE component_profiel ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE component_profiel FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON component_profiel "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON component_profiel TO cd_app")

    # === (b) pre-prod: tenant-laag legen (cascadeert via component) ===
    # component CASCADE → applicatie, component_profiel, koppeling, component_structuur,
    # component_contract, datatype, gebruikersgroep, checklistscore, blokkade.
    op.execute("TRUNCATE component CASCADE")

    # === (c) lifecycle_status van applicatie verwijderen (verhuisd naar profiel) ===
    op.drop_index("ix_applicatie_tenant_lifecycle", table_name="applicatie")
    op.drop_column("applicatie", "lifecycle_status")

    # === (d) checklistscore herankeren (truncated → drop/add, geen backfill) ===
    op.drop_constraint("uq_checklistscore_app_vraag", "checklistscore", type_="unique")
    op.drop_index("ix_checklistscore_tenant_app", table_name="checklistscore")
    op.execute("ALTER TABLE checklistscore DROP CONSTRAINT IF EXISTS checklistscore_applicatie_id_fkey")
    op.execute("ALTER TABLE checklistscore DROP CONSTRAINT IF EXISTS checklistscore_vraag_code_fkey")
    op.drop_column("checklistscore", "applicatie_id")
    op.drop_column("checklistscore", "vraag_code")
    op.add_column("checklistscore", sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.add_column("checklistscore", sa.Column("checklistvraag_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key(
        "checklistscore_component_id_fkey", "checklistscore", "component_profiel",
        ["component_id"], ["id"], ondelete="CASCADE",
    )

    # === (e) blokkade herankeren (truncated → drop/add) ===
    op.drop_index("ix_blokkade_tenant_app", table_name="blokkade")
    op.execute("ALTER TABLE blokkade DROP CONSTRAINT IF EXISTS blokkade_applicatie_id_fkey")
    op.drop_column("blokkade", "applicatie_id")
    op.add_column("blokkade", sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key(
        "blokkade_component_id_fkey", "blokkade", "component_profiel",
        ["component_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_blokkade_tenant_app", "blokkade", ["tenant_id", "component_id"])

    # === (f) checklistvraag_optie: vraag_code-bindingen losmaken (backfill later) ===
    op.drop_constraint("uq_checklistvraag_optie", "checklistvraag_optie", type_="unique")
    op.drop_index("ix_checklistvraag_optie_vraag", table_name="checklistvraag_optie")
    op.execute("ALTER TABLE checklistvraag_optie DROP CONSTRAINT IF EXISTS checklistvraag_optie_vraag_code_fkey")
    op.add_column("checklistvraag_optie", sa.Column("checklistvraag_id", postgresql.UUID(as_uuid=True), nullable=True))

    # === (g) checklistvraag: surrogate UUID-PK + componenttype-discriminator ===
    op.add_column("checklistvraag", sa.Column("componenttype", sa.String(60), nullable=True))
    op.execute("UPDATE checklistvraag SET componenttype = 'applicatie'")
    op.alter_column("checklistvraag", "componenttype", nullable=False)
    op.drop_constraint("uq_checklistvraag_code", "checklistvraag", type_="unique")
    op.drop_constraint("checklistvraag_pkey", "checklistvraag", type_="primary")
    op.drop_column("checklistvraag", "id")  # int-id + sequence vervallen
    op.add_column(
        "checklistvraag",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
    )
    op.create_primary_key("checklistvraag_pkey", "checklistvraag", ["id"])
    op.create_unique_constraint("uq_checklistvraag_type_code", "checklistvraag", ["componenttype", "code"])

    # === (h) checklistvraag_optie: backfill checklistvraag_id uit code, dan finaliseren ===
    op.execute(
        "UPDATE checklistvraag_optie o SET checklistvraag_id = v.id "
        "FROM checklistvraag v WHERE v.code = o.vraag_code"
    )
    op.alter_column("checklistvraag_optie", "checklistvraag_id", nullable=False)
    op.create_foreign_key(
        "checklistvraag_optie_checklistvraag_id_fkey", "checklistvraag_optie",
        "checklistvraag", ["checklistvraag_id"], ["id"],
    )
    op.create_unique_constraint(
        "uq_checklistvraag_optie", "checklistvraag_optie", ["checklistvraag_id", "optie_sleutel"]
    )
    op.create_index("ix_checklistvraag_optie_vraag", "checklistvraag_optie", ["checklistvraag_id"])
    op.drop_column("checklistvraag_optie", "vraag_code")

    # === (i) checklistscore: FK naar checklistvraag.id + unieke index + tenant-index ===
    op.create_foreign_key(
        "checklistscore_checklistvraag_id_fkey", "checklistscore",
        "checklistvraag", ["checklistvraag_id"], ["id"],
    )
    op.create_unique_constraint(
        "uq_checklistscore_app_vraag", "checklistscore",
        ["tenant_id", "component_id", "checklistvraag_id"],
    )
    op.create_index("ix_checklistscore_tenant_app", "checklistscore", ["tenant_id", "component_id"])

    # === (j) checklistvraag-grants → catalogus-patroon (Beslissing 8) ===
    op.execute("REVOKE ALL ON checklistvraag FROM cd_app")
    op.execute("GRANT SELECT ON checklistvraag TO cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON checklistvraag TO cd_platform")


def downgrade() -> None:
    """Best effort terug naar 0006 (pre-prod, géén data-herstel)."""
    integer_pk = "checklistvraag_id_seq"

    # grants terug
    op.execute("REVOKE ALL ON checklistvraag FROM cd_platform")
    op.execute("REVOKE ALL ON checklistvraag FROM cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON checklistvraag TO cd_app")
    op.execute("GRANT SELECT, UPDATE ON checklistvraag TO cd_platform")

    op.execute("TRUNCATE component CASCADE")

    # checklistscore terug naar applicatie_id / vraag_code
    op.drop_index("ix_checklistscore_tenant_app", table_name="checklistscore")
    op.drop_constraint("uq_checklistscore_app_vraag", "checklistscore", type_="unique")
    op.execute("ALTER TABLE checklistscore DROP CONSTRAINT IF EXISTS checklistscore_checklistvraag_id_fkey")
    op.execute("ALTER TABLE checklistscore DROP CONSTRAINT IF EXISTS checklistscore_component_id_fkey")
    op.drop_column("checklistscore", "checklistvraag_id")
    op.drop_column("checklistscore", "component_id")

    # blokkade terug naar applicatie_id
    op.drop_index("ix_blokkade_tenant_app", table_name="blokkade")
    op.execute("ALTER TABLE blokkade DROP CONSTRAINT IF EXISTS blokkade_component_id_fkey")
    op.drop_column("blokkade", "component_id")
    op.add_column("blokkade", sa.Column("applicatie_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.create_foreign_key(
        "blokkade_applicatie_id_fkey", "blokkade", "applicatie",
        ["applicatie_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_blokkade_tenant_app", "blokkade", ["tenant_id", "applicatie_id"])

    # checklistvraag_optie terug naar vraag_code
    op.drop_index("ix_checklistvraag_optie_vraag", table_name="checklistvraag_optie")
    op.drop_constraint("uq_checklistvraag_optie", "checklistvraag_optie", type_="unique")
    op.execute("ALTER TABLE checklistvraag_optie DROP CONSTRAINT IF EXISTS checklistvraag_optie_checklistvraag_id_fkey")
    op.add_column("checklistvraag_optie", sa.Column("vraag_code", sa.String(10), nullable=True))
    op.execute(
        "UPDATE checklistvraag_optie o SET vraag_code = v.code "
        "FROM checklistvraag v WHERE v.id = o.checklistvraag_id"
    )

    # checklistvraag terug naar integer-PK + globale UNIQUE(code)
    op.drop_constraint("uq_checklistvraag_type_code", "checklistvraag", type_="unique")
    op.drop_constraint("checklistvraag_pkey", "checklistvraag", type_="primary")
    op.drop_column("checklistvraag", "id")
    op.drop_column("checklistvraag", "componenttype")
    op.add_column(
        "checklistvraag",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
    )
    op.create_primary_key("checklistvraag_pkey", "checklistvraag", ["id"])
    op.create_unique_constraint("uq_checklistvraag_code", "checklistvraag", ["code"])

    # checklistvraag_optie afronden
    op.alter_column("checklistvraag_optie", "vraag_code", nullable=False)
    op.drop_column("checklistvraag_optie", "checklistvraag_id")
    op.create_foreign_key(
        "checklistvraag_optie_vraag_code_fkey", "checklistvraag_optie",
        "checklistvraag", ["vraag_code"], ["code"],
    )
    op.create_unique_constraint(
        "uq_checklistvraag_optie", "checklistvraag_optie", ["vraag_code", "optie_sleutel"]
    )
    op.create_index("ix_checklistvraag_optie_vraag", "checklistvraag_optie", ["vraag_code"])

    # checklistscore terug
    op.add_column("checklistscore", sa.Column("applicatie_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.add_column("checklistscore", sa.Column("vraag_code", sa.String(10), nullable=False))
    op.create_foreign_key(
        "checklistscore_applicatie_id_fkey", "checklistscore", "applicatie",
        ["applicatie_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "checklistscore_vraag_code_fkey", "checklistscore", "checklistvraag",
        ["vraag_code"], ["code"],
    )
    op.create_unique_constraint(
        "uq_checklistscore_app_vraag", "checklistscore",
        ["tenant_id", "applicatie_id", "vraag_code"],
    )
    op.create_index("ix_checklistscore_tenant_app", "checklistscore", ["tenant_id", "applicatie_id"])

    # lifecycle_status terug op applicatie
    lifecycle = postgresql.ENUM(name="lifecycle_status_enum", create_type=False)
    op.add_column(
        "applicatie",
        sa.Column("lifecycle_status", lifecycle, nullable=False, server_default=sa.text("'concept'")),
    )
    op.create_index("ix_applicatie_tenant_lifecycle", "applicatie", ["tenant_id", "lifecycle_status"])

    # component_profiel weg
    op.drop_index("ix_component_profiel_tenant_lifecycle", table_name="component_profiel")
    op.drop_table("component_profiel")
