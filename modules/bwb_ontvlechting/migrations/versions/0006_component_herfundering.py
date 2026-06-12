"""ADR-021 — component-herfundering (pre-productie, géén datamigratie).

Revision ID: 0006_component_herfundering
Revises: 0005_contractregister
Create Date: 2026-06-12

Herfundeert het centrale object naar supertype `component` + subtype `applicatie`
(CD051 Optie 2: shared-PK — `applicatie.id` is tegelijk PK én FK → `component.id`).
De graaf herankert op componentniveau: `koppeling.bron/doel` worden component-FK's
(velden ongewijzigd), nieuwe `component_structuur` (opbouw/afhankelijkheid) en
`component_contract` (vervangt `applicatie_contract`). Nieuwe platform-catalogus
`componentconfig_optie` (geen RLS), dimensies {componenttype, structuurrelatie_type}.

Pre-productie (ADR-021 Besluit 11): de migratie verplaatst GEEN data — de
applicatie-laag wordt geleegd (`TRUNCATE applicatie CASCADE`) en `dev_seed_testdata.py`
herseedt. Velden naam/hostingmodel/eigenaar/leverancier/beschrijving verhuizen naar
`component`; lifecycle/migratiepad/complexiteit/prioriteit blijven op `applicatie`.
Grants/RLS conform CD040.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_component_herfundering"
down_revision: Union[str, Sequence[str], None] = "0005_contractregister"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NIEUWE_TENANT_TABELLEN = ["component", "component_structuur", "component_contract"]
_APP_VERHUIST = ["naam", "beschrijving", "hostingmodel", "eigenaar_organisatie",
                 "eigenaar_naam", "leverancier"]


def upgrade() -> None:
    bind = op.get_bind()

    dimensie = postgresql.ENUM(
        "componenttype", "structuurrelatie_type",
        name="componentconfig_dimensie_enum", create_type=False,
    )
    dimensie.create(bind, checkfirst=True)
    hostingmodel = postgresql.ENUM(name="hostingmodel_enum", create_type=False)

    # --- (a) Platform-brede componentcatalogus (referentiedata, GEEN RLS) ---
    op.create_table(
        "componentconfig_optie",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dimensie", dimensie, nullable=False),
        sa.Column("optie_sleutel", sa.String(60), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("volgorde", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("actief", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("dimensie", "optie_sleutel", name="uq_componentconfig_optie"),
    )

    # --- (b) Supertype component (tenant-scoped) ---
    op.create_table(
        "component",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("naam", sa.String(255), nullable=False),
        sa.Column("componenttype", sa.String(60), nullable=False),
        sa.Column("hostingmodel", hostingmodel, nullable=False),
        sa.Column("eigenaar_organisatie", sa.String(120), nullable=False),
        sa.Column("eigenaar_naam", sa.String(255), nullable=True),
        sa.Column("leverancier", sa.String(255), nullable=True),
        sa.Column("beschrijving", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # --- (c) applicatie_contract vervalt; pre-prod: applicatie-laag leegmaken ---
    op.drop_table("applicatie_contract")
    op.execute("TRUNCATE applicatie CASCADE")  # cascadeert naar checklistscore/blokkade/datatype/gebruikersgroep/koppeling

    # --- (d) applicatie herfunderen tot shared-PK-subtype van component ---
    for kolom in _APP_VERHUIST:
        op.drop_column("applicatie", kolom)
    op.alter_column("applicatie", "id", server_default=None)  # id komt nu van component
    op.create_foreign_key(
        "fk_applicatie_component", "applicatie", "component",
        ["id"], ["id"], ondelete="CASCADE",
    )

    # --- (e) koppeling: bron/doel-FK's herankeren applicatie → component ---
    for kant in ("bron", "doel"):
        op.execute(f"ALTER TABLE koppeling DROP CONSTRAINT IF EXISTS koppeling_{kant}_applicatie_id_fkey")
        op.create_foreign_key(
            f"fk_koppeling_{kant}_component", "koppeling", "component",
            [f"{kant}_applicatie_id"], ["id"], ondelete="CASCADE",
        )

    # --- (f) component_structuur (opbouw/afhankelijkheid) ---
    op.create_table(
        "component_structuur",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("component.id", ondelete="CASCADE"), nullable=False),
        sa.Column("op_component_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("component.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("relatietype", sa.String(60), nullable=False),
        sa.Column("omschrijving", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("component_id <> op_component_id", name="ck_component_structuur_self"),
        sa.UniqueConstraint("tenant_id", "component_id", "op_component_id", "relatietype", name="uq_component_structuur"),
    )

    # --- (g) component_contract (vervangt applicatie_contract) ---
    op.create_table(
        "component_contract",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("component.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contract.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relatie_rol", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "component_id", "contract_id", name="uq_component_contract"),
    )

    # --- (h) indexen (tenant_id voorop) ---
    op.create_index("ix_component_tenant_naam", "component", ["tenant_id", "naam"])
    op.create_index("ix_component_tenant_type", "component", ["tenant_id", "componenttype"])
    op.create_index("ix_component_structuur_tenant_component", "component_structuur", ["tenant_id", "component_id"])
    op.create_index("ix_component_structuur_tenant_op", "component_structuur", ["tenant_id", "op_component_id"])
    op.create_index("ix_component_contract_tenant_component", "component_contract", ["tenant_id", "component_id"])
    op.create_index("ix_component_contract_tenant_contract", "component_contract", ["tenant_id", "contract_id"])

    # --- (i) RLS + grants op de nieuwe tenant-tabellen (CD040-boilerplate) ---
    for tabel in _NIEUWE_TENANT_TABELLEN:
        op.execute(f"ALTER TABLE {tabel} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabel} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {tabel} "
            f"USING (tenant_id = current_setting('app.tenant_id')::uuid)"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabel} TO cd_app")

    # --- (j) catalogus-grants (identiek aan contractconfig_optie) ---
    op.execute("REVOKE ALL ON componentconfig_optie FROM cd_app")
    op.execute("GRANT SELECT ON componentconfig_optie TO cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON componentconfig_optie TO cd_platform")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE componentconfig_optie_id_seq TO cd_platform")


def downgrade() -> None:
    bind = op.get_bind()
    # Best effort terug naar 0005 (pre-prod, géén data-herstel).
    op.execute("TRUNCATE applicatie CASCADE")
    op.drop_table("component_contract")
    op.drop_table("component_structuur")

    # koppeling-FK's terug naar applicatie
    for kant in ("bron", "doel"):
        op.execute(f"ALTER TABLE koppeling DROP CONSTRAINT IF EXISTS fk_koppeling_{kant}_component")
        op.create_foreign_key(
            f"koppeling_{kant}_applicatie_id_fkey", "koppeling", "applicatie",
            [f"{kant}_applicatie_id"], ["id"], ondelete="CASCADE",
        )

    # applicatie terug naar zelfstandige tabel met de verhuisde kolommen
    op.execute("ALTER TABLE applicatie DROP CONSTRAINT IF EXISTS fk_applicatie_component")
    op.alter_column("applicatie", "id", server_default=sa.text("gen_random_uuid()"))
    hostingmodel = postgresql.ENUM(name="hostingmodel_enum", create_type=False)
    op.add_column("applicatie", sa.Column("naam", sa.String(255), nullable=False, server_default=""))
    op.add_column("applicatie", sa.Column("beschrijving", sa.Text(), nullable=True))
    op.add_column("applicatie", sa.Column("hostingmodel", hostingmodel, nullable=False, server_default="onbekend"))
    op.add_column("applicatie", sa.Column("eigenaar_organisatie", sa.String(120), nullable=False, server_default=""))
    op.add_column("applicatie", sa.Column("eigenaar_naam", sa.String(255), nullable=True))
    op.add_column("applicatie", sa.Column("leverancier", sa.String(255), nullable=True))

    # applicatie_contract terug
    op.create_table(
        "applicatie_contract",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applicatie_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contract.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relatie_rol", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "applicatie_id", "contract_id", name="uq_applicatie_contract"),
    )
    op.execute("ALTER TABLE applicatie_contract ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE applicatie_contract FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY tenant_isolation ON applicatie_contract USING (tenant_id = current_setting('app.tenant_id')::uuid)")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON applicatie_contract TO cd_app")

    op.drop_table("component")
    op.drop_table("componentconfig_optie")
    postgresql.ENUM(name="componentconfig_dimensie_enum").drop(bind, checkfirst=True)
