"""ADR-023a — meervoudige flow-koppelingen + naam-kolom op `relatie`.

Revision ID: 0039_adr023a_flow_meervoud
Revises: 0038_adr029_kv_actor_sub
Create Date: 2026-06-22

Fase 1 (schema) van de meervoudige-koppelingen-uitbreiding:
- Voeg `naam` (String 150, NULLABLE op DB-niveau) toe aan `relatie` — een identificerend,
  sorteerbaar veld voor een koppeling. App-verplicht-voor-flow volgt in Fase 2 (hier GEEN
  validatie). Nullable zodat bestaande/niet-flow-rijen niet breken (geen backfill nodig:
  er komt een nieuwe seed).
- Verruim de uniciteit SELECTIEF voor `flow`: vervang de constraint
  `uq_relatie UNIQUE(tenant_id, bron_id, doel_id, relatietype)` door een PARTIËLE unieke
  index met `WHERE relatietype <> 'flow'`. Andere relatietypen (association/assignment/
  aggregation/realization/…) blijven uniek per (bron, doel, type); flow mag voortaan
  meervoud (meerdere koppelingen tussen dezelfde twee systemen, eigen protocol/functie).

Registratief — engine onaangeroerd (raakt alleen de relatie-tabel; geen lifecycle/score/
blokkade). Reversibel: down herstelt de oude constraint en dropt de kolom.
Feitelijk geverifieerd vóór bouw: 0 bestaande (tenant,bron,doel,flow)-paren met >1 rij →
de partiële index landt schoon.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0039_adr023a_flow_meervoud"
down_revision: Union[str, Sequence[str], None] = "0038_adr029_kv_actor_sub"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLS = ["tenant_id", "bron_id", "doel_id", "relatietype"]


def upgrade() -> None:
    op.add_column("relatie", sa.Column("naam", sa.String(150), nullable=True))
    # All-types-uniciteit → partiële uniciteit (flow uitgezonderd).
    op.drop_constraint("uq_relatie", "relatie", type_="unique")
    op.create_index(
        "uq_relatie", "relatie", _COLS,
        unique=True, postgresql_where=sa.text("relatietype <> 'flow'"),
    )


def downgrade() -> None:
    op.drop_index("uq_relatie", table_name="relatie")
    op.create_unique_constraint("uq_relatie", "relatie", _COLS)
    op.drop_column("relatie", "naam")
