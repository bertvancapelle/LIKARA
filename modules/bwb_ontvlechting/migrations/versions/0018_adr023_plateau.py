"""ADR-023 Fase E (E1) — Plateau: migratielaag-element + relatie-kenmerk-catalogus (additief).

Revision ID: 0018_adr023_plateau
Revises: 0017_adr023_cutover_band
Create Date: 2026-06-15

Voegt toe (geen datamigratie — er is geen bestaande plateau-data):
- subtype-tabel `plateau` (element-subtype: shared-PK composiet-FK → element, FORCE RLS);
- platform-brede **relatie-kenmerk-vocabulaire**-catalogus `relatiekenmerk_optie`
  (losgekoppeld van ContractConfig) + de `dispositie`-waarden
  (behouden/migreren/vervangen/uitfaseren);
- uitbreiding van de `aggregation`-kenmerk-definitie met `dispositie` (→ relatiekenmerk-
  catalogus) + de contractuele-bevestigingskenmerken (registratie; niet gevalideerd).

`element_type_enum` bevat 'plateau' al sinds 0011 → geen enum-wijziging nodig.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_adr023_plateau"
down_revision: Union[str, Sequence[str], None] = "0017_adr023_cutover_band"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DISPOSITIES = [
    ("behouden", "Behouden"),
    ("migreren", "Migreren"),
    ("vervangen", "Vervangen"),
    ("uitfaseren", "Uitfaseren"),
]

# ADR-023 Fase E — lidmaatschap-kenmerken op de aggregation-relatie. `dispositie` =
# catalogus, gerouteerd naar de algemene relatie-kenmerk-catalogus (NIET ContractConfig).
# De bevestigingskenmerken zijn `registratie`: vrije registratiegegevens die het systeem
# NIET valideert/vergelijkt (door de generieke kenmerk-validator geaccepteerd; de
# plateau-facade vult wie/wanneer server-side).
_AGGREGATION_KENMERKEN = (
    '{'
    '"dispositie": {"type": "catalogus", "catalogus": "relatiekenmerk", "dimensie": "dispositie"}, '
    '"contractueel_bevestigd": {"type": "registratie"}, '
    '"bevestigd_aantal_gebruikers": {"type": "registratie"}, '
    '"bevestigd_door": {"type": "registratie"}, '
    '"bevestigd_op": {"type": "registratie"}'
    '}'
)


def upgrade() -> None:
    # --- (a) subtype-tabel `plateau` (tenant-scoped, FORCE RLS) ---------------------
    op.create_table(
        "plateau",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("naam", sa.String(255), nullable=False),
        sa.Column("toelichting", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_plateau_tenant", "plateau", ["tenant_id"])
    op.create_foreign_key(
        "fk_plateau_element", "plateau", "element",
        ["tenant_id", "id"], ["tenant_id", "id"], ondelete="CASCADE",
    )
    op.execute("ALTER TABLE plateau ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE plateau FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON plateau "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON plateau FROM cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON plateau TO cd_app")

    # --- (b) relatie-kenmerk-vocabulaire-catalogus (platform-breed, GEEN RLS) -------
    dimensie = postgresql.ENUM("dispositie", name="relatiekenmerk_dimensie_enum", create_type=False)
    dimensie.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "relatiekenmerk_optie",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dimensie", dimensie, nullable=False),
        sa.Column("optie_sleutel", sa.String(60), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("volgorde", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("actief", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("dimensie", "optie_sleutel", name="uq_relatiekenmerk_optie"),
    )
    # Grants identiek aan contractconfig_optie: cd_app SELECT (validatie), cd_platform beheer.
    op.execute("REVOKE ALL ON relatiekenmerk_optie FROM cd_app")
    op.execute("GRANT SELECT ON relatiekenmerk_optie TO cd_app")
    op.execute("GRANT SELECT, INSERT, UPDATE ON relatiekenmerk_optie TO cd_platform")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE relatiekenmerk_optie_id_seq TO cd_platform")
    for volgorde, (sleutel, label) in enumerate(_DISPOSITIES):
        op.execute(
            sa.text(
                "INSERT INTO relatiekenmerk_optie (dimensie, optie_sleutel, label, volgorde, actief) "
                "VALUES ('dispositie', :s, :l, :v, true) "
                "ON CONFLICT (dimensie, optie_sleutel) DO NOTHING"
            ).bindparams(s=sleutel, l=label, v=volgorde)
        )

    # --- (c) aggregation-kenmerk-definitie uitbreiden (lidmaatschap-kenmerken) ------
    op.execute(
        sa.text(
            "UPDATE componentconfig_optie SET kenmerk_definitie = CAST(:k AS jsonb) "
            "WHERE dimensie = 'archimate_relatie' AND optie_sleutel = 'aggregation'"
        ).bindparams(k=_AGGREGATION_KENMERKEN)
    )


def downgrade() -> None:
    # (c) aggregation terug naar leeg.
    op.execute(
        "UPDATE componentconfig_optie SET kenmerk_definitie = '{}'::jsonb "
        "WHERE dimensie = 'archimate_relatie' AND optie_sleutel = 'aggregation'"
    )
    # (b) relatie-kenmerk-catalogus weg.
    op.drop_table("relatiekenmerk_optie")
    postgresql.ENUM(name="relatiekenmerk_dimensie_enum").drop(op.get_bind(), checkfirst=True)
    # (a) plateau-tabel (de aggregation-lidmaatschapsrelaties cascaden NIET automatisch bij
    # tabel-drop; in een echte downgrade horen ze eerst weg — buiten scope van deze additieve slice).
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON plateau")
    op.drop_constraint("fk_plateau_element", "plateau", type_="foreignkey")
    op.drop_index("ix_plateau_tenant", table_name="plateau")
    op.drop_table("plateau")
