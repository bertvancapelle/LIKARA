"""ADR-023 Fase A — element-identiteit (supertype) + ArchiMate-typing-catalogus.

Revision ID: 0011_adr023_element_identiteit
Revises: 0010_adr006_audit_trail
Create Date: 2026-06-14

Element-supertabel (één identiteitsruimte, ArchiMate-leidraad). `component` wordt
subtype via shared-PK (composiet-FK `(tenant_id, id)` → `element(tenant_id, id)` — Besluit
1/12, cross-tenant structureel uitgesloten). Bestaande shared-PK-keten
(applicatie/component_profiel) blijft intact. Pre-productie: bestaande componenten krijgen
een backfill-element-rij met dezelfde id.

Typing-catalogus (Besluit 4 + OK-1/3): `archimate_element`/`laag`/`aspect` + `kenmerk_definitie`
(OK-2) op `componentconfig_optie`; nieuwe dimensie `archimate_relatie` met de acht relatietypes.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_adr023_element_identiteit"
down_revision: Union[str, Sequence[str], None] = "0010_adr006_audit_trail"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ELEMENT_TYPES = (
    "component", "datatype", "gebruikersgroep", "contract",
    "plateau", "gap", "work_package", "deliverable",
)

# OK-1/OK-3: ArchiMate-mapping per actief componenttype (archimate_element, laag, aspect).
_TYPE_MAPPING = {
    "applicatie": ("application_component", "application", "active"),
    "applicatieserver": ("node", "technology", "active"),
    "database": ("system_software", "technology", "active"),
    "fileshare": ("node", "technology", "active"),
    "saas_dienst": ("application_component", "application", "active"),
    "client_software": ("system_software", "technology", "active"),
    "middleware": ("system_software", "technology", "active"),
}

# Besluit 6 + OK-1: acht relatietypes; OK-2: kenmerk-definities (jsonb) per type.
_RELATIE_TYPES = [
    ("composition", "Composition", "{}"),
    ("aggregation", "Aggregation", "{}"),
    ("serving", "Serving", "{}"),
    ("assignment", "Assignment", "{}"),
    ("flow", "Flow",
     '{"protocol": {"type": "enum", "enum": "koppelprotocol"}, '
     '"impact_bij_verbreking": {"type": "enum", "enum": "impact_verbreking"}}'),
    ("realization", "Realization", "{}"),
    ("association", "Association",
     '{"relatie_rol": {"type": "catalogus", "dimensie": "relatie_rol"}}'),
    ("access", "Access", "{}"),
]


def upgrade() -> None:
    # --- (a) element-supertabel (tenant-scoped, FORCE RLS, UNIQUE(tenant_id,id)) ----
    element_type = postgresql.ENUM(*_ELEMENT_TYPES, name="element_type_enum", create_type=False)
    element_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "element",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("element_type", element_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "id", name="uq_element_tenant_id"),
    )
    op.create_index("ix_element_tenant", "element", ["tenant_id"])
    op.create_index("ix_element_tenant_type", "element", ["tenant_id", "element_type"])
    op.execute("ALTER TABLE element ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE element FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON element "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON element FROM cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON element TO cd_app")

    # --- (b) backfill: elk bestaand component krijgt een element-rij (zelfde id) -----
    op.execute(
        "INSERT INTO element (id, tenant_id, element_type, created_at, updated_at) "
        "SELECT id, tenant_id, 'component', created_at, updated_at FROM component"
    )

    # --- (c) component wordt subtype: composiet-FK (tenant_id, id) → element ---------
    op.create_foreign_key(
        "fk_component_element", "component", "element",
        ["tenant_id", "id"], ["tenant_id", "id"], ondelete="CASCADE",
    )

    # --- (d) typing-catalogus op componentconfig_optie -----------------------------
    op.add_column("componentconfig_optie", sa.Column("archimate_element", sa.String(60), nullable=True))
    op.add_column("componentconfig_optie", sa.Column("laag", sa.String(40), nullable=True))
    op.add_column("componentconfig_optie", sa.Column("aspect", sa.String(20), nullable=True))
    op.add_column(
        "componentconfig_optie",
        sa.Column("kenmerk_definitie", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    for sleutel, (elem, laag, aspect) in _TYPE_MAPPING.items():
        op.execute(
            sa.text(
                "UPDATE componentconfig_optie SET archimate_element=:e, laag=:l, aspect=:a "
                "WHERE dimensie='componenttype' AND optie_sleutel=:s"
            ).bindparams(e=elem, l=laag, a=aspect, s=sleutel)
        )

    # --- (e) nieuwe catalogus-dimensie archimate_relatie + de acht relatietypes ------
    # ALTER TYPE ... ADD VALUE mag niet in dezelfde transactie gebruikt worden → autocommit.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE componentconfig_dimensie_enum ADD VALUE IF NOT EXISTS 'archimate_relatie'"
        )
    for volgorde, (sleutel, label, kenmerken) in enumerate(_RELATIE_TYPES):
        op.execute(
            sa.text(
                "INSERT INTO componentconfig_optie "
                "(dimensie, optie_sleutel, label, volgorde, actief, checklist_dragend, kenmerk_definitie) "
                "VALUES ('archimate_relatie', :s, :l, :v, true, false, CAST(:k AS jsonb)) "
                "ON CONFLICT (dimensie, optie_sleutel) DO NOTHING"
            ).bindparams(s=sleutel, l=label, v=volgorde, k=kenmerken)
        )


def downgrade() -> None:
    op.execute("DELETE FROM componentconfig_optie WHERE dimensie = 'archimate_relatie'")
    op.drop_column("componentconfig_optie", "kenmerk_definitie")
    op.drop_column("componentconfig_optie", "aspect")
    op.drop_column("componentconfig_optie", "laag")
    op.drop_column("componentconfig_optie", "archimate_element")
    # enum-waarde 'archimate_relatie' blijft (PostgreSQL kan enum-waarden niet droppen) —
    # onschadelijk; downgrade is best-effort (pre-prod).

    op.drop_constraint("fk_component_element", "component", type_="foreignkey")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON element")
    op.drop_index("ix_element_tenant_type", table_name="element")
    op.drop_index("ix_element_tenant", table_name="element")
    op.drop_table("element")
    postgresql.ENUM(name="element_type_enum").drop(op.get_bind(), checkfirst=True)
