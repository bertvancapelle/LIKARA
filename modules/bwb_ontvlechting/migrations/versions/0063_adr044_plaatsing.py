"""ADR-044 gate 1a-bis — plaatsing als eerste-klas feit: `bedrijfsfunctie.ouder_id` vervalt.

Revision ID: 0063_adr044_plaatsing
Revises: 0062_adr043_bedrijfsfunctie
Create Date: 2026-07-12

De functieboom verhuist van een ouder-kolom naar **plaatsingen**: `aggregation`-relaties
(bron = ouder/geheel, doel = kind/deel) in het bestaande unified relatiemodel — exact wat
de GEMMA-bron levert (302 aggregaties; 7 functies met meerdere ouders — de één-ouder-kolom
kon dat niet dragen). `UNIQUE(tenant, bron, doel, relatietype)` op `relatie` borgt één
plaatsing per (ouder, functie)-paar; meerdere ouders = meerdere rijen. Géén nieuwe tabel.

Schemastap: drop van de self-FK, de self-parent-CHECK, de ouder-index en de kolom.
Ontwikkelmodus: testdata — de reseed zaait de boom als plaatsingen (GEEN datamigratie;
de dev-seed is idempotent op bronsleutel en legt ontbrekende plaatsingen aan).

Daarnaast (contract-stap bij de gewijzigde seed, expand/contract-les CD035): het
referentiemodel-aanbod krijgt zijn bekrachtigde, navolgbare herkomst — het verzonnen
"GEMMA 2 (2025)" wordt "release 1 juli 2026" met bron-repository + licentie (EUPL).
De seed (`seed_referentiemodel.py`) is de expand voor fresh deploys; deze UPDATE is de
eenmalige contract voor bestaande databases.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0063_adr044_plaatsing"
down_revision: Union[str, Sequence[str], None] = "0062_adr043_bedrijfsfunctie"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── De boom is geen kolom meer (ADR-044 besluit 1) ──────────────────────────────
    op.drop_constraint("fk_bedrijfsfunctie_ouder", "bedrijfsfunctie", type_="foreignkey")
    op.drop_constraint("ck_bedrijfsfunctie_geen_self_parent", "bedrijfsfunctie", type_="check")
    op.drop_index("ix_bedrijfsfunctie_tenant_ouder", table_name="bedrijfsfunctie")
    op.drop_column("bedrijfsfunctie", "ouder_id")

    # ── Bekrachtigde herkomst van het aanbod (contract; seed = expand) ──────────────
    op.execute(
        sa.text(
            "UPDATE referentiemodel_optie SET "
            "label = :l, herkomst = :h, versie = :v "
            "WHERE optie_sleutel = 'gemma_bedrijfsfuncties'"
        ).bindparams(
            l="GEMMA Bedrijfsfuncties",
            h="VNG-Realisatie/GEMMA-Archi-repository (github.com/VNG-Realisatie/"
              "GEMMA-Archi-repository, export/GEMMA release.xml) — licentie EUPL",
            v="release 1 juli 2026",
        )
    )


def downgrade() -> None:
    # Kolom + borging terug (zonder data — de boom leeft dan weer leeg in de kolom).
    op.add_column(
        "bedrijfsfunctie",
        sa.Column("ouder_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_bedrijfsfunctie_tenant_ouder", "bedrijfsfunctie", ["tenant_id", "ouder_id"])
    op.create_check_constraint(
        "ck_bedrijfsfunctie_geen_self_parent", "bedrijfsfunctie",
        "ouder_id IS NULL OR ouder_id <> id",
    )
    op.create_foreign_key(
        "fk_bedrijfsfunctie_ouder", "bedrijfsfunctie", "bedrijfsfunctie",
        ["tenant_id", "ouder_id"], ["tenant_id", "id"], ondelete="RESTRICT",
    )
