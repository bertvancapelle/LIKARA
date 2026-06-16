"""ADR-023 Fase F (F-6) — reconcile `checklist_dragend` op de componentcatalogus.

Revision ID: 0023_checklist_dragend_fix
Revises: 0022_adr023_gap
Create Date: 2026-06-15

Data-only contract-migratie (expand/contract, zoals CD035 `0004_bio2_bbn`): brengt de
bestaande `componentconfig_optie`-rijen in lijn met de bedoelde stand —
`applicatie = true`, **alle overige componenttypen `false`** (incl. het foutief op `true`
gezette `applicatieserver`). De seed (`seed_componentconfig`, expand) zet voortaan dezelfde
waarden expliciet, zodat fresh deploys meteen correct zijn en seed ↔ migratie niet langer
divergeren.

Geen schema-wijziging (de kolom bestaat sinds 0009). Geen engine-wijziging: dit raakt
uitsluitend catalogus-data. Het herstelt wél welke componenttypen via het generieke
component-pad een `component_profiel` krijgen — precies de bedoeling. Bestaande
`component_profiel`-rijen/scores worden NIET aangeraakt.

Defensief: de UPDATEs raken simpelweg 0 rijen als de catalogus nog niet geseed is (op een
fresh deploy draait deze migratie vóór `platform_init`; de seed dekt die situatie).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0023_checklist_dragend_fix"
down_revision: Union[str, Sequence[str], None] = "0022_adr023_gap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alleen het systeemtype `applicatie` is checklist-dragend.
    op.execute(
        "UPDATE componentconfig_optie SET checklist_dragend = true "
        "WHERE dimensie = 'componenttype' AND optie_sleutel = 'applicatie'"
    )
    # Alle overige componenttypen expliciet niet (incl. het foutief op true gezette
    # `applicatieserver`). Raakt uitsluitend de dimensie `componenttype`.
    op.execute(
        "UPDATE componentconfig_optie SET checklist_dragend = false "
        "WHERE dimensie = 'componenttype' AND optie_sleutel <> 'applicatie'"
    )


def downgrade() -> None:
    # No-op: de oude (foutieve) stand was per definitie inconsistent en niet betekenisvol
    # herstelbaar. Best-effort downgrade = niets doen (pre-prod, data-only reconcile).
    pass
