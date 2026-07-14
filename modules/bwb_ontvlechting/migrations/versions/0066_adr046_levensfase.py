"""ADR-046 besluit 1+2 (stuk 1) — levensfase op het component; bedoeling opgeschoond.

Vier schemastappen:
1. `levensfase_enum` (in_ontwikkeling/in_productie/uitfaseren) + nullable kolom
   `component.levensfase` ZONDER default en ZONDER backfill (vormkeuze B: een default
   "in productie" zou een uitspraak zijn die niemand deed; ontbrekend = "nog niet
   vastgelegd", leeg ≠ fout).
2. `migratiepad_enum` zonder `uitfaseren` (fase-taal, geen bestemming) — PostgreSQL kent
   geen DROP VALUE → type-recreate (precedent 0053). Datakost nul (gemeten V040: 19/19
   op `onbekend`); een defensieve UPDATE vangt eventueel dev-residu. Let op: de
   server_default `'onbekend'` is aan het oude type gebonden → rond de swap droppen en
   herzetten.
3. Plateau-dispositie afgebouwd als bestemmingsveld (besluit 2): het `dispositie`-kenmerk
   verdwijnt uit de aggregation-kenmerkdefinitie (nieuwe registratie kan niet meer) en de
   catalogus-dimensie wordt SOFT-gedeactiveerd (`actief=false` — historische waarden
   blijven resolvebaar, nooit hard weg). Bestaande relatie-rijen behouden hun kenmerk
   (read-only historie); de bevestigingskenmerken blijven ongemoeid.
4. Geen datamigratie verder — ontwikkelmodus (alleen testdata; reseed vult het verhaal).

Engine onaangeroerd: registratieve velden, geen lifecycle/score/blokkade.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0066_adr046_levensfase"
down_revision: Union[str, Sequence[str], None] = "0065_adr045_ondersteunt_werk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PADEN_ZONDER_UITFASEREN = "'lift_and_shift', 'herbouw', 'vervangen', 'gedeeld', 'onbekend'"
_PADEN_MET_UITFASEREN = "'lift_and_shift', 'herbouw', 'vervangen', 'uitfaseren', 'gedeeld', 'onbekend'"


def _herbouw_migratiepad_enum(waarden: str) -> None:
    """Type-recreate (0053-precedent). De server_default is aan het type gebonden →
    droppen vóór en herzetten ná de swap (anders faalt de USING-cast op de default)."""
    op.execute("ALTER TABLE component ALTER COLUMN migratiepad DROP DEFAULT")
    op.execute("ALTER TYPE migratiepad_enum RENAME TO migratiepad_enum_old")
    op.execute(f"CREATE TYPE migratiepad_enum AS ENUM ({waarden})")
    op.execute(
        "ALTER TABLE component ALTER COLUMN migratiepad TYPE migratiepad_enum "
        "USING migratiepad::text::migratiepad_enum"
    )
    op.execute("DROP TYPE migratiepad_enum_old")
    op.execute("ALTER TABLE component ALTER COLUMN migratiepad SET DEFAULT 'onbekend'")


def upgrade() -> None:
    # 1. Levensfase: enum + nullable kolom, GEEN default, GEEN backfill (vormkeuze B).
    levensfase = postgresql.ENUM(
        "in_ontwikkeling", "in_productie", "uitfaseren",
        name="levensfase_enum", create_type=False,
    )
    levensfase.create(op.get_bind(), checkfirst=True)
    op.add_column("component", sa.Column("levensfase", levensfase, nullable=True))

    # 2. `uitfaseren` uit de bedoeling. Defensieve opruiming eerst (gemeten 0 rijen op de
    # dev-DB; idempotent no-op) zodat de recreate nooit op een residu-rij kan stranden.
    op.execute("UPDATE component SET migratiepad = 'onbekend' WHERE migratiepad = 'uitfaseren'")
    _herbouw_migratiepad_enum(_PADEN_ZONDER_UITFASEREN)

    # 3. Plateau-dispositie afbouwen als bestemmingsveld (contract-stap; de seed is de
    # expand voor verse deploys — zie seed_componentconfig/seed_relatiekenmerk).
    op.execute(
        "UPDATE componentconfig_optie SET kenmerk_definitie = kenmerk_definitie - 'dispositie' "
        "WHERE dimensie = 'archimate_relatie' AND optie_sleutel = 'aggregation'"
    )
    op.execute("UPDATE relatiekenmerk_optie SET actief = false WHERE dimensie = 'dispositie'")


def downgrade() -> None:
    # 3'. Dispositie-kenmerk terug in de aggregation-definitie + catalogus weer actief.
    op.execute(
        "UPDATE componentconfig_optie SET kenmerk_definitie = kenmerk_definitie || "
        "'{\"dispositie\": {\"type\": \"catalogus\", \"catalogus\": \"relatiekenmerk\", "
        "\"dimensie\": \"dispositie\"}}'::jsonb "
        "WHERE dimensie = 'archimate_relatie' AND optie_sleutel = 'aggregation'"
    )
    op.execute("UPDATE relatiekenmerk_optie SET actief = true WHERE dimensie = 'dispositie'")

    # 2'. `uitfaseren` terug in de bedoeling.
    _herbouw_migratiepad_enum(_PADEN_MET_UITFASEREN)

    # 1'. Levensfase-kolom + enum weg.
    op.drop_column("component", "levensfase")
    postgresql.ENUM(name="levensfase_enum").drop(op.get_bind(), checkfirst=True)
