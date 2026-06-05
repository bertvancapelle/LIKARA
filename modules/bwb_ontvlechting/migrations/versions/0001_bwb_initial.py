"""BWB-ontvlechting — initiële tabellen, enums, RLS (ADR-009).

Revision ID: 0001_bwb_initial
Revises:
Create Date: 2026-06-05

Maakt de 7 tabellen van de bwb_ontvlechting-module aan: 6 tenant-scoped
entiteiten (RLS + FORCE + tenant_isolation) en de referentietabel
checklistvraag (geen RLS). Enums worden als PostgreSQL enum-types aangemaakt.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_bwb_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENUMS = {
    "hostingmodel_enum": ["on_premise", "private_cloud", "saas", "iaas", "paas", "hybride", "onbekend"],
    "lifecycle_status_enum": ["concept", "in_inventarisatie", "checklist_compleet", "geblokkeerd", "migratieklaar"],
    "niveau_enum": ["laag", "midden", "hoog"],
    "migratiepad_enum": ["lift_and_shift", "herbouw", "vervangen", "uitfaseren", "tijdelijk_gedeeld", "onbekend"],
    "datatype_categorie_enum": ["gestructureerd_db", "documenten", "email", "spatial", "binair", "combinatie"],
    "koppelrichting_enum": ["eenrichting", "tweerichting"],
    "koppelprotocol_enum": ["api", "bestandsuitwisseling", "database_link", "middleware", "overig"],
    "impact_verbreking_enum": ["laag", "midden", "hoog", "kritiek"],
    "checklist_score_enum": ["ja", "deels", "nee", "nvt"],
    "blokkade_status_enum": ["open", "in_behandeling", "opgelost"],
    "checklist_prioriteit_enum": ["hoog", "midden", "laag"],
}

# Tenant-scoped tabellen (RLS + FORCE + policy + grants)
_TENANT_TABELLEN = ["applicatie", "datatype", "gebruikersgroep", "koppeling", "checklistscore", "blokkade"]


def _ts_cols():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    e = {n: postgresql.ENUM(*v, name=n, create_type=False) for n, v in ENUMS.items()}
    for t in e.values():
        t.create(bind, checkfirst=True)

    # --- applicatie (centraal) ---
    op.create_table(
        "applicatie",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("naam", sa.String(255), nullable=False),
        sa.Column("beschrijving", sa.Text(), nullable=True),
        sa.Column("hostingmodel", e["hostingmodel_enum"], nullable=False),
        sa.Column("eigenaar_organisatie", sa.String(120), nullable=False),
        sa.Column("eigenaar_naam", sa.String(255), nullable=True),
        sa.Column("leverancier", sa.String(255), nullable=True),
        sa.Column("migratiepad", e["migratiepad_enum"], nullable=False),
        sa.Column("complexiteit", e["niveau_enum"], nullable=False),
        sa.Column("prioriteit", e["niveau_enum"], nullable=False),
        sa.Column("lifecycle_status", e["lifecycle_status_enum"], nullable=False, server_default=sa.text("'concept'")),
        *_ts_cols(),
    )

    # --- checklistvraag (referentie, geen tenant/RLS) ---
    op.create_table(
        "checklistvraag",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("categorie_nr", sa.Integer(), nullable=False),
        sa.Column("categorie_naam", sa.String(120), nullable=False),
        sa.Column("vraag", sa.Text(), nullable=False),
        sa.Column("prioriteit", e["checklist_prioriteit_enum"], nullable=False),
        sa.UniqueConstraint("code", name="uq_checklistvraag_code"),
    )

    # --- datatype ---
    op.create_table(
        "datatype",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applicatie_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False),
        sa.Column("categorie", e["datatype_categorie_enum"], nullable=False),
        sa.Column("omschrijving", sa.Text(), nullable=True),
        sa.Column("omvang_indicatie", sa.String(255), nullable=True),
        *_ts_cols(),
    )

    # --- gebruikersgroep ---
    op.create_table(
        "gebruikersgroep",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applicatie_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organisatie", sa.String(120), nullable=False),
        sa.Column("afdeling", sa.String(255), nullable=True),
        sa.Column("aantal_gebruikers", sa.Integer(), nullable=True),
        *_ts_cols(),
    )

    # --- koppeling ---
    op.create_table(
        "koppeling",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bron_applicatie_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doel_applicatie_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False),
        sa.Column("richting", e["koppelrichting_enum"], nullable=False),
        sa.Column("protocol", e["koppelprotocol_enum"], nullable=False),
        sa.Column("impact_bij_verbreking", e["impact_verbreking_enum"], nullable=False),
        sa.Column("omschrijving", sa.Text(), nullable=True),
        sa.CheckConstraint("bron_applicatie_id <> doel_applicatie_id", name="ck_koppeling_bron_ne_doel"),
        *_ts_cols(),
    )

    # --- checklistscore ---
    op.create_table(
        "checklistscore",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applicatie_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vraag_code", sa.String(10), sa.ForeignKey("checklistvraag.code"), nullable=False),
        sa.Column("score", e["checklist_score_enum"], nullable=True),
        sa.Column("bevinding", sa.Text(), nullable=True),
        sa.Column("eigenaar", sa.String(255), nullable=True),
        sa.Column("actie", sa.Text(), nullable=True),
        sa.UniqueConstraint("tenant_id", "applicatie_id", "vraag_code", name="uq_checklistscore_app_vraag"),
        *_ts_cols(),
    )

    # --- blokkade ---
    op.create_table(
        "blokkade",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklistscore_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("checklistscore.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applicatie_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", e["blokkade_status_enum"], nullable=False, server_default=sa.text("'open'")),
        sa.Column("toelichting", sa.Text(), nullable=True),
        sa.Column("eigenaar", sa.String(255), nullable=True),
        sa.Column("opgelost_op", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("checklistscore_id", name="uq_blokkade_checklistscore"),
        *_ts_cols(),
    )

    # --- RLS + grants op tenant-scoped tabellen ---
    for tabel in _TENANT_TABELLEN:
        op.execute(f"ALTER TABLE {tabel} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabel} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {tabel} "
            f"USING (tenant_id = current_setting('app.tenant_id')::uuid)"
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabel} TO cd_app")

    # checklistvraag: geen RLS; cd_app mag lezen + seeden
    op.execute("GRANT SELECT, INSERT, UPDATE ON checklistvraag TO cd_app")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE checklistvraag_id_seq TO cd_app")

    # --- Indexen ---
    op.create_index("ix_applicatie_tenant", "applicatie", ["tenant_id"])
    op.create_index("ix_applicatie_tenant_lifecycle", "applicatie", ["tenant_id", "lifecycle_status"])
    op.create_index("ix_koppeling_tenant_bron", "koppeling", ["tenant_id", "bron_applicatie_id"])
    op.create_index("ix_koppeling_tenant_doel", "koppeling", ["tenant_id", "doel_applicatie_id"])
    op.create_index("ix_checklistscore_tenant_app", "checklistscore", ["tenant_id", "applicatie_id"])
    op.create_index("ix_blokkade_tenant_app", "blokkade", ["tenant_id", "applicatie_id"])
    op.create_index("ix_blokkade_tenant_status", "blokkade", ["tenant_id", "status"])


def downgrade() -> None:
    bind = op.get_bind()
    for tabel in _TENANT_TABELLEN:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {tabel}")

    op.drop_table("blokkade")
    op.drop_table("checklistscore")
    op.drop_table("koppeling")
    op.drop_table("gebruikersgroep")
    op.drop_table("datatype")
    op.drop_table("checklistvraag")
    op.drop_table("applicatie")

    for naam in ENUMS:
        postgresql.ENUM(name=naam).drop(bind, checkfirst=True)
