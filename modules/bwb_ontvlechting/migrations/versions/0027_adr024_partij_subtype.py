"""ADR-024 slice 1 — partij-subtype (vervangt leverancier) + partijsoort-catalogus.

Additief + verse seed (geen backfill): er is geen productiedata; de dev-DB wordt gereset.
- `partij_aard_enum` + `partij`-subtabel (element-subtype-recept: shared-PK composiet-FK
  `(tenant_id,id)→element` CASCADE, FORCE RLS + `tenant_isolation` + REVOKE/GRANT);
- platform-brede `partijsoort_optie`-catalogus (GEEN RLS) + default-seed
  (leverancier/partner/ketenpartner) — grants identiek aan `contractconfig_optie`;
- **contract-koppeling optie A**: de term/kolomnaam `leverancier_id` blijft; alleen de
  FK-target verschuift van de vervallen `leverancier`-tabel naar het **partij-element**
  (composiet `(tenant_id, leverancier_id) → element(tenant_id,id)` ON DELETE RESTRICT);
- `leverancier`-tabel vervalt.

`element_type_enum` ADD VALUE 'partij' is de aparte voorafgaande migratie 0026. Engine
onaangeroerd — geen lifecycle/profiel/score/blokkade geraakt.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027_adr024_partij_subtype"
down_revision: Union[str, Sequence[str], None] = "0026_adr024_elementtype_partij"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PARTIJSOORTEN = [("leverancier", "Leverancier"), ("partner", "Partner"), ("ketenpartner", "Ketenpartner")]


def upgrade() -> None:
    bind = op.get_bind()

    # --- (a) partij_aard_enum -------------------------------------------------------
    partij_aard = postgresql.ENUM(
        "externe_partij", "organisatie", "organisatie_eenheid", "persoon",
        name="partij_aard_enum", create_type=False,
    )
    partij_aard.create(bind, checkfirst=True)

    # --- (b) partij-subtabel (element-subtype-recept) -------------------------------
    op.create_table(
        "partij",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aard", partij_aard, nullable=False),
        sa.Column("naam", sa.String(255), nullable=False),
        sa.Column("straat_huisnummer", sa.String(255), nullable=True),
        sa.Column("postcode", sa.String(20), nullable=True),
        sa.Column("plaats", sa.String(255), nullable=True),
        sa.Column("contactpersoon", sa.String(255), nullable=True),
        sa.Column("telefoon", sa.String(40), nullable=True),
        sa.Column("mobiel", sa.String(40), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("omschrijving", sa.Text(), nullable=True),
        sa.Column("soort", sa.String(60), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_partij_tenant", "partij", ["tenant_id"])
    op.create_foreign_key(
        "fk_partij_element", "partij", "element",
        ["tenant_id", "id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.execute("ALTER TABLE partij ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE partij FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON partij "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON partij FROM cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON partij TO cd_app")

    # --- (c) platform-brede partijsoort-catalogus (GEEN RLS) + default-seed ---------
    op.create_table(
        "partijsoort_optie",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("optie_sleutel", sa.String(60), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("volgorde", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("actief", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("optie_sleutel", name="uq_partijsoort_optie"),
    )
    op.execute("REVOKE ALL ON partijsoort_optie FROM cd_app")
    op.execute("GRANT SELECT ON partijsoort_optie TO cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON partijsoort_optie TO cd_platform")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE partijsoort_optie_id_seq TO cd_platform")
    for volgorde, (sleutel, label) in enumerate(_PARTIJSOORTEN):
        op.execute(
            sa.text(
                "INSERT INTO partijsoort_optie (optie_sleutel, label, volgorde, actief) "
                "VALUES (:s, :l, :v, true) ON CONFLICT (optie_sleutel) DO NOTHING"
            ).bindparams(s=sleutel, l=label, v=volgorde)
        )

    # --- (d) contract-koppeling omhangen (optie A: kolomnaam blijft) ----------------
    op.drop_constraint("contract_leverancier_id_fkey", "contract", type_="foreignkey")
    op.create_foreign_key(
        "fk_contract_leverancier_partij", "contract", "element",
        ["tenant_id", "leverancier_id"], ["tenant_id", "id"], ondelete="RESTRICT",
    )

    # --- (e) leverancier-tabel vervalt ----------------------------------------------
    op.drop_table("leverancier")


def downgrade() -> None:
    bind = op.get_bind()

    # (e') leverancier-tabel terug (zoals 0005) + RLS/grants.
    op.create_table(
        "leverancier",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("naam", sa.String(255), nullable=False),
        sa.Column("straat_huisnummer", sa.String(255), nullable=True),
        sa.Column("postcode", sa.String(20), nullable=True),
        sa.Column("plaats", sa.String(255), nullable=True),
        sa.Column("contactpersoon", sa.String(255), nullable=True),
        sa.Column("telefoon", sa.String(40), nullable=True),
        sa.Column("mobiel", sa.String(40), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("omschrijving", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_leverancier_tenant", "leverancier", ["tenant_id"])
    op.execute("ALTER TABLE leverancier ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE leverancier FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON leverancier "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON leverancier FROM cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON leverancier TO cd_app")

    # (d') contract-FK terug naar leverancier.
    op.drop_constraint("fk_contract_leverancier_partij", "contract", type_="foreignkey")
    op.create_foreign_key(
        "contract_leverancier_id_fkey", "contract", "leverancier",
        ["leverancier_id"], ["id"], ondelete="RESTRICT",
    )

    # (c') partijsoort-catalogus weg.
    op.drop_table("partijsoort_optie")

    # (b') partij-subtabel weg (FK/policy/index vallen met de tabel).
    op.drop_table("partij")

    # (a') partij_aard_enum weg.
    postgresql.ENUM(name="partij_aard_enum").drop(bind, checkfirst=True)
