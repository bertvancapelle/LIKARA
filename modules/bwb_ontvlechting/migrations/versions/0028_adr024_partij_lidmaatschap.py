"""ADR-024 slice 2a-bis — partij-lidmaatschap ("hoort bij").

Voegt twee nullable FK-kolommen toe aan `partij`:
- `organisatie_id` → element (de organisatie(-achtige) partij waar een persoon/afdeling bij hoort);
- `afdeling_id` → element (optioneel: de afdeling binnen die organisatie waar een persoon bij hoort).

Composiet-FK's `(tenant_id, <kol>) → element(tenant_id, id)` ON DELETE RESTRICT (tenant-consistent;
een organisatie/afdeling met leden verdwijnt niet stil). Twee CHECK-backstops:
- organisatie verplicht voor `persoon` + `organisatie_eenheid`, verboden voor `organisatie` +
  `externe_partij` (de top staat op zichzelf);
- `afdeling_id` alleen voor een `persoon`.

De fijnere laag-consistentie (organisatie_id is organisatie-achtig; afdeling_id is een
`organisatie_eenheid` binnen die organisatie) borgt de service (422). Engine onaangeroerd —
registratie/relationeel, geen lifecycle/score/blokkade.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028_adr024_partij_lidmaatschap"
down_revision: Union[str, Sequence[str], None] = "0027_adr024_partij_subtype"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("partij", sa.Column("organisatie_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("partij", sa.Column("afdeling_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.create_foreign_key(
        "fk_partij_organisatie", "partij", "element",
        ["tenant_id", "organisatie_id"], ["tenant_id", "id"], ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_partij_afdeling", "partij", "element",
        ["tenant_id", "afdeling_id"], ["tenant_id", "id"], ondelete="RESTRICT",
    )
    # Reverse-lookup-indexen (organisatie → leden; afdeling → personen).
    op.create_index("ix_partij_tenant_organisatie", "partij", ["tenant_id", "organisatie_id"])
    op.create_index("ix_partij_tenant_afdeling", "partij", ["tenant_id", "afdeling_id"])

    op.create_check_constraint(
        "ck_partij_organisatie_verplicht", "partij",
        "(aard IN ('persoon', 'organisatie_eenheid')) = (organisatie_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_partij_afdeling_alleen_persoon", "partij",
        "afdeling_id IS NULL OR aard = 'persoon'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_partij_afdeling_alleen_persoon", "partij", type_="check")
    op.drop_constraint("ck_partij_organisatie_verplicht", "partij", type_="check")
    op.drop_index("ix_partij_tenant_afdeling", table_name="partij")
    op.drop_index("ix_partij_tenant_organisatie", table_name="partij")
    op.drop_constraint("fk_partij_afdeling", "partij", type_="foreignkey")
    op.drop_constraint("fk_partij_organisatie", "partij", type_="foreignkey")
    op.drop_column("partij", "afdeling_id")
    op.drop_column("partij", "organisatie_id")
