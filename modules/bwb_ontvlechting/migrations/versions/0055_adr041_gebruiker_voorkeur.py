"""ADR-041 slice 1 — persoonlijke gebruikersvoorkeuren ("onthoud als mijn standaard").

Eén nieuwe tenant-scoped tabel `gebruiker_voorkeur` (RLS + FORCE): een generieke key/value-laag met
één rij per `(tenant_id, sub, voorkeur_sleutel)`. De `sub` is de Keycloak-`sub` (server-side
gestempeld); `waarde` een klein JSON-blob (JSONB). Additief — geen bestaande data geraakt; registratie
naast de engine.

Revision ID: 0055_adr041_gebruiker_voorkeur
Revises: 0054_contactpersoon_ref
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0055_adr041_gebruiker_voorkeur"
down_revision: Union[str, Sequence[str], None] = "0054_contactpersoon_ref"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gebruiker_voorkeur",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sub", sa.String(255), nullable=False),
        sa.Column("voorkeur_sleutel", sa.String(100), nullable=False),
        sa.Column("waarde", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Precies één rij per gebruiker per voorkeur-sleutel (upsert-doel).
        sa.UniqueConstraint("tenant_id", "sub", "voorkeur_sleutel", name="uq_gebruiker_voorkeur_sub_sleutel"),
    )
    op.create_index("ix_gebruiker_voorkeur_tenant", "gebruiker_voorkeur", ["tenant_id"])
    op.create_index("ix_gebruiker_voorkeur_tenant_sub", "gebruiker_voorkeur", ["tenant_id", "sub"])
    op.execute("ALTER TABLE gebruiker_voorkeur ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE gebruiker_voorkeur FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON gebruiker_voorkeur "
        "USING (tenant_id = current_setting('app.tenant_id')::uuid)"
    )
    op.execute("REVOKE ALL ON gebruiker_voorkeur FROM lk_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON gebruiker_voorkeur TO lk_app")


def downgrade() -> None:
    op.drop_table("gebruiker_voorkeur")
