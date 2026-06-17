"""ADR-026 — structurele volledigheids-borging van de componenttype-typering.

Voegt een conditionele CHECK-constraint toe op `componentconfig_optie`: een rij met
dimensie `componenttype` MOET element + laag + aspect alle drie dragen; andere dimensies
(`structuurrelatie_type`, `archimate_relatie`) mogen ze NULL laten. De volledigheid geldt
ONVOORWAARDELIJK (geen `actief`-afhankelijkheid) — een gedeactiveerd componenttype blijft
historisch resolvebaar en moet dus ook getypeerd zijn.

Dit is de backstop onder de app-laag (Pydantic-validators + service): zelfs een directe
INSERT/UPDATE buiten de applicatie kan geen ongetypeerd componenttype achterlaten — het lek
dat de seed-only dekkingstest niet ving, is hiermee structureel gedicht.

Landt schoon: bij oplevering 0 overtredende rijen (alle 7 seed-componenttypen volledig
getypeerd). Engine onaangeroerd — geen tenant-/RLS-/lifecycle-tabel geraakt.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0025_adr026_typering_volledig"
down_revision: Union[str, Sequence[str], None] = "0024_adr023_vraagbetekenis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CK_NAAM = "ck_componentconfig_typering_volledig"
_CK_CONDITIE = (
    "dimensie <> 'componenttype' "
    "OR (archimate_element IS NOT NULL AND laag IS NOT NULL AND aspect IS NOT NULL)"
)


def upgrade() -> None:
    op.create_check_constraint(_CK_NAAM, "componentconfig_optie", _CK_CONDITIE)


def downgrade() -> None:
    op.drop_constraint(_CK_NAAM, "componentconfig_optie", type_="check")
