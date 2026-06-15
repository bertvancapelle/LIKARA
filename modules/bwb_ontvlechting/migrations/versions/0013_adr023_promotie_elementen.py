"""ADR-023 Fase B-mig-1 — datatype/gebruikersgroep/contract → element-subtypes (additief).

Revision ID: 0013_adr023_promotie_elementen
Revises: 0012_adr023_relatiemodel
Create Date: 2026-06-14

Promoveert datatype/gebruikersgroep/contract tot eersteklas elementen (shared-PK):
backfill van een element-rij per bestaand subtype + composiet-FK `(tenant_id, id)` →
`element` (cross-tenant uitgesloten). **Additief**: oude tabellen/kolommen + de
applicatie-band blijven (de cutover naar het relatiemodel volgt in B-mig-2). Plus de
OK-2-verfijning: `richting` als kenmerk op het `flow`-relatietype.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0013_adr023_promotie_elementen"
down_revision: Union[str, Sequence[str], None] = "0012_adr023_relatiemodel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SUBTYPES = ("datatype", "gebruikersgroep", "contract")


def upgrade() -> None:
    # OK-2-verfijning (v3): richting als kenmerk op flow (bestaande DB's).
    op.execute(
        "UPDATE componentconfig_optie "
        "SET kenmerk_definitie = kenmerk_definitie || "
        "'{\"richting\": {\"type\": \"enum\", \"enum\": \"koppelrichting\"}}'::jsonb "
        "WHERE dimensie = 'archimate_relatie' AND optie_sleutel = 'flow'"
    )
    # Promotie: backfill element-rij per subtype (zelfde id) + composiet-FK.
    for tabel in _SUBTYPES:
        op.execute(
            f"INSERT INTO element (id, tenant_id, element_type, created_at, updated_at) "
            f"SELECT id, tenant_id, '{tabel}', created_at, updated_at FROM {tabel}"
        )
        op.create_foreign_key(
            f"fk_{tabel}_element", tabel, "element",
            ["tenant_id", "id"], ["tenant_id", "id"], ondelete="CASCADE",
        )


def downgrade() -> None:
    for tabel in _SUBTYPES:
        op.drop_constraint(f"fk_{tabel}_element", tabel, type_="foreignkey")
        op.execute(f"DELETE FROM element WHERE element_type = '{tabel}'")
    op.execute(
        "UPDATE componentconfig_optie "
        "SET kenmerk_definitie = kenmerk_definitie - 'richting' "
        "WHERE dimensie = 'archimate_relatie' AND optie_sleutel = 'flow'"
    )
