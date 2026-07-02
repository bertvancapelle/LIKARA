"""ADR-028 slice 1 — componentclassificatie: componentrol + BIV.

Additief + verse seed (geen backfill; dev-only testdata, de dev-DB wordt gereset):
- platform-brede `componentrol_optie`-catalogus (GEEN RLS) + default-seed
  (interne_applicatie/interne_dataprovider/externe_dataprovider/koppelvlak); grants
  identiek aan `partijsoort_optie`/`componentconfig_optie` (lk_app SELECT; lk_platform
  SELECT/INSERT/UPDATE + sequence; GEEN DELETE — soft-deactivate via `actief`);
- platform-brede `biv_schaal_optie`-catalogus (GEEN RLS) + default-seed (laag/midden/hoog,
  ORDINAAL via `volgorde` 1/2/3); zelfde grants;
- vier kolommen op `component`: `componentrol` (NOT NULL, server_default `interne_applicatie`
  → bestaande rijen vullen zich vanzelf) + `biv_beschikbaarheid`/`biv_integriteit`/
  `biv_vertrouwelijkheid` (nullable).

Engine onaangeroerd — classificatie is puur registratief; geen lifecycle/profiel/score/
blokkade geraakt. De seeds zijn byte-gelijk aan `seed_componentrol`/`seed_bivschaal`
(idempotent, `ON CONFLICT (optie_sleutel) DO NOTHING`); platform_init zaait dezelfde stand.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0048_adr028_classificatie"
down_revision: Union[str, Sequence[str], None] = "0047_li059_drop_applicatie"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ROLLEN = [
    ("interne_applicatie", "Interne applicatie"),
    ("interne_dataprovider", "Interne dataprovider"),
    ("externe_dataprovider", "Externe dataprovider"),
    ("koppelvlak", "Koppelvlak"),
]
_BIV = [("laag", "Laag"), ("midden", "Midden"), ("hoog", "Hoog")]


def _seed(tabel: str, rijen: list[tuple[str, str]]) -> None:
    for volgorde, (sleutel, label) in enumerate(rijen):
        op.execute(
            sa.text(
                f"INSERT INTO {tabel} (optie_sleutel, label, volgorde, actief) "
                "VALUES (:s, :l, :v, true) ON CONFLICT (optie_sleutel) DO NOTHING"
            ).bindparams(s=sleutel, l=label, v=volgorde)
        )


def _catalogus(tabel: str, uq: str) -> None:
    op.create_table(
        tabel,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("optie_sleutel", sa.String(60), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("volgorde", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("actief", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("optie_sleutel", name=uq),
    )
    op.execute(f"REVOKE ALL ON {tabel} FROM lk_app")
    op.execute(f"GRANT SELECT ON {tabel} TO lk_app")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON {tabel} TO lk_platform")
    op.execute(f"GRANT USAGE, SELECT ON SEQUENCE {tabel}_id_seq TO lk_platform")


def upgrade() -> None:
    # --- (a) platform-brede catalogi (GEEN RLS) + default-seed ----------------------
    _catalogus("componentrol_optie", "uq_componentrol_optie")
    _seed("componentrol_optie", _ROLLEN)
    _catalogus("biv_schaal_optie", "uq_biv_schaal_optie")
    _seed("biv_schaal_optie", _BIV)

    # --- (b) vier component-kolommen (server_default vult bestaande rijen) -----------
    op.add_column(
        "component",
        sa.Column(
            "componentrol", sa.String(60), nullable=False,
            server_default=sa.text("'interne_applicatie'"),
        ),
    )
    op.add_column("component", sa.Column("biv_beschikbaarheid", sa.String(60), nullable=True))
    op.add_column("component", sa.Column("biv_integriteit", sa.String(60), nullable=True))
    op.add_column("component", sa.Column("biv_vertrouwelijkheid", sa.String(60), nullable=True))


def downgrade() -> None:
    op.drop_column("component", "biv_vertrouwelijkheid")
    op.drop_column("component", "biv_integriteit")
    op.drop_column("component", "biv_beschikbaarheid")
    op.drop_column("component", "componentrol")
    op.drop_table("biv_schaal_optie")
    op.drop_table("componentrol_optie")
