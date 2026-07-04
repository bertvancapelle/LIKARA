"""ADR-038 — gebruikersgroep-consolidatie: groep hoort altijd bij een organisatie; burger-aard weg.

Revision ID: 0053_adr038_consolidatie
Revises: 0052_adr038_scope
Create Date: 2026-07-04

Drie schemastappen + een dev-only defensieve opruiming:
- `gebruikersgroep.gebruik_id` → NOT NULL (een groep hoort altijd bij een organisatie); de FK naar
  `organisatiegebruik` gaat van ON DELETE SET NULL → RESTRICT (SET NULL botst met NOT NULL; een grof
  feit/organisatie met groepen verdwijnt niet stil — spiegel van `afdeling_id`).
- `partij_aard_enum` zonder `burger` (Postgres kent geen DROP VALUE → type recreate). Burger-
  doelgroepen zijn voortaan gewone externe organisaties (aard=organisatie + scope=extern) met
  afdelingen.

Defensieve opruiming (idempotent; no-op op een verse/lege DB) omdat de draaiende dev-DB nog org-loze
groepen (`gebruik_id IS NULL`) en de losse `burger`-partij kan dragen — ontwikkelmodus (V001, geen
prod-data; dev-data is wegwerpbaar, reseed vult het schone verhaal). Verwijdering loopt via het
element-supertype (CASCADE naar subtype-rij + serving-relaties). RLS/FORCE ongewijzigd. Engine
onaangeroerd — registratie/structuur, geen lifecycle/score.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0053_adr038_consolidatie"
down_revision: Union[str, Sequence[str], None] = "0052_adr038_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_AARDEN_ZONDER_BURGER = "'externe_partij', 'organisatie', 'organisatie_eenheid', 'persoon'"
_AARDEN_MET_BURGER = _AARDEN_ZONDER_BURGER + ", 'burger'"

# CHECK-constraints op `partij` die `aard` met een literal vergelijken. Die literals zijn aan het
# oude enum-type gebonden → een type-swap botst ("operator does not exist"). Daarom rond de swap
# droppen en identiek herbouwen (de definities noemen `burger` niet, dus gelijk in beide richtingen).
_AARD_CHECKS = (
    ("ck_partij_organisatie_verplicht",
     "(aard IN ('persoon', 'organisatie_eenheid')) = (organisatie_id IS NOT NULL)"),
    ("ck_partij_afdeling_alleen_persoon",
     "afdeling_id IS NULL OR aard = 'persoon'"),
    ("ck_partij_scope_aanwezig",
     "(aard IN ('organisatie', 'externe_partij')) = (scope IS NOT NULL)"),
    ("ck_partij_externe_partij_extern",
     "aard <> 'externe_partij' OR scope = 'extern'"),
)


def _herbouw_aard_enum(waarden: str) -> None:
    for naam, _ in _AARD_CHECKS:
        op.drop_constraint(naam, "partij", type_="check")
    op.execute("ALTER TYPE partij_aard_enum RENAME TO partij_aard_enum_old")
    op.execute(f"CREATE TYPE partij_aard_enum AS ENUM ({waarden})")
    op.execute(
        "ALTER TABLE partij ALTER COLUMN aard TYPE partij_aard_enum USING aard::text::partij_aard_enum"
    )
    op.execute("DROP TYPE partij_aard_enum_old")
    for naam, conditie in _AARD_CHECKS:
        op.create_check_constraint(naam, "partij", conditie)


def upgrade() -> None:
    # 1. Dev-only opruiming (no-op op lege tabellen).
    op.execute(
        "DELETE FROM element WHERE id IN (SELECT id FROM gebruikersgroep WHERE gebruik_id IS NULL)"
    )
    op.execute("DELETE FROM element WHERE id IN (SELECT id FROM partij WHERE aard = 'burger')")

    # 2. gebruik_id verplicht + FK SET NULL → RESTRICT.
    op.drop_constraint("fk_gebruikersgroep_gebruik", "gebruikersgroep", type_="foreignkey")
    op.alter_column("gebruikersgroep", "gebruik_id", nullable=False)
    op.create_foreign_key(
        "fk_gebruikersgroep_gebruik", "gebruikersgroep", "organisatiegebruik",
        ["tenant_id", "gebruik_id"], ["tenant_id", "id"], ondelete="RESTRICT",
    )

    # 3. partij_aard_enum zonder 'burger'.
    _herbouw_aard_enum(_AARDEN_ZONDER_BURGER)


def downgrade() -> None:
    # 3'. burger terug in de enum.
    _herbouw_aard_enum(_AARDEN_MET_BURGER)

    # 2'. FK terug naar SET NULL + gebruik_id nullable.
    op.drop_constraint("fk_gebruikersgroep_gebruik", "gebruikersgroep", type_="foreignkey")
    op.alter_column("gebruikersgroep", "gebruik_id", nullable=True)
    op.create_foreign_key(
        "fk_gebruikersgroep_gebruik", "gebruikersgroep", "organisatiegebruik",
        ["tenant_id", "gebruik_id"], ["tenant_id", "id"], ondelete="SET NULL",
    )
    # (De data-verwijdering uit upgrade is niet omkeerbaar — dev-data, reseed.)
