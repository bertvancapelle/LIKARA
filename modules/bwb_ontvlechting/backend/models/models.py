"""SQLAlchemy-modellen — BWB-ontvlechtingsmodule (ADR-009).

Zes tenant-scoped entiteiten (RLS) + één referentietabel (ChecklistVraag).
Enums worden als PostgreSQL enum-types beheerd via de Alembic-migratie;
de hier gedefinieerde `sa.Enum`-typeobjecten delen dezelfde namen.
"""
import uuid
from datetime import datetime
from enum import Enum

import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


# --------------------------------------------------------------------------
# Enums (Python + PostgreSQL)
# --------------------------------------------------------------------------

class HostingModel(str, Enum):
    on_premise = "on_premise"
    private_cloud = "private_cloud"
    saas = "saas"
    iaas = "iaas"
    paas = "paas"
    hybride = "hybride"
    onbekend = "onbekend"


class LifecycleStatus(str, Enum):
    concept = "concept"
    in_inventarisatie = "in_inventarisatie"
    checklist_compleet = "checklist_compleet"
    geblokkeerd = "geblokkeerd"
    migratieklaar = "migratieklaar"


class NiveauEnum(str, Enum):
    laag = "laag"
    midden = "midden"
    hoog = "hoog"


class Migratiepad(str, Enum):
    lift_and_shift = "lift_and_shift"
    herbouw = "herbouw"
    vervangen = "vervangen"
    uitfaseren = "uitfaseren"
    tijdelijk_gedeeld = "tijdelijk_gedeeld"
    onbekend = "onbekend"


class DatatypeCategorie(str, Enum):
    gestructureerd_db = "gestructureerd_db"
    documenten = "documenten"
    email = "email"
    spatial = "spatial"
    binair = "binair"
    combinatie = "combinatie"


class Koppelrichting(str, Enum):
    eenrichting = "eenrichting"
    tweerichting = "tweerichting"


class Koppelprotocol(str, Enum):
    api = "api"
    bestandsuitwisseling = "bestandsuitwisseling"
    database_link = "database_link"
    middleware = "middleware"
    overig = "overig"


class ImpactVerbreking(str, Enum):
    laag = "laag"
    midden = "midden"
    hoog = "hoog"
    kritiek = "kritiek"


class ChecklistScore(str, Enum):
    ja = "ja"
    deels = "deels"
    nee = "nee"
    nvt = "nvt"


class BlokkadeStatus(str, Enum):
    open = "open"
    in_behandeling = "in_behandeling"
    opgelost = "opgelost"


# Blokkades die nog niet zijn opgelost — de ADR-013-definitie van "open" waarop
# een applicatie op `geblokkeerd` wordt gezet. Single source: zowel de
# lifecycle-herberekening als het dashboard verwijzen hiernaar (geen kopieën die
# stil uit elkaar lopen). Immutable.
ACTIEVE_BLOKKADE_STATUSSEN = frozenset({BlokkadeStatus.open, BlokkadeStatus.in_behandeling})


class ChecklistPrioriteit(str, Enum):
    hoog = "hoog"
    midden = "midden"
    laag = "laag"


class AntwoordType(str, Enum):
    """Type van het additionele gestructureerde antwoordveld per checklistvraag
    (ADR-019). `geen` (default) = alléén de score, zoals vóór ADR-019. De engine
    leest dit type NOOIT — het stuurt enkel de validatie/UI van `antwoord_waarde`."""

    geen = "geen"
    enkelvoudige_keuze = "enkelvoudige_keuze"
    meerkeuze = "meerkeuze"
    getal = "getal"


# Gedeelde sa.Enum-typeobjecten (één type per naam; migratie beheert de DDL).
# `create_type=False`: de ORM emit nooit zelf CREATE TYPE — de migratie doet dat.
hostingmodel_enum = sa.Enum(HostingModel, name="hostingmodel_enum")
lifecycle_status_enum = sa.Enum(LifecycleStatus, name="lifecycle_status_enum")
niveau_enum = sa.Enum(NiveauEnum, name="niveau_enum")
migratiepad_enum = sa.Enum(Migratiepad, name="migratiepad_enum")
datatype_categorie_enum = sa.Enum(DatatypeCategorie, name="datatype_categorie_enum")
koppelrichting_enum = sa.Enum(Koppelrichting, name="koppelrichting_enum")
koppelprotocol_enum = sa.Enum(Koppelprotocol, name="koppelprotocol_enum")
impact_verbreking_enum = sa.Enum(ImpactVerbreking, name="impact_verbreking_enum")
checklist_score_enum = sa.Enum(ChecklistScore, name="checklist_score_enum")
blokkade_status_enum = sa.Enum(BlokkadeStatus, name="blokkade_status_enum")
checklist_prioriteit_enum = sa.Enum(ChecklistPrioriteit, name="checklist_prioriteit_enum")
antwoordtype_enum = sa.Enum(AntwoordType, name="antwoordtype_enum")


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


# --------------------------------------------------------------------------
# Modellen
# --------------------------------------------------------------------------

class Applicatie(Base, TenantMixin, TimestampMixin):
    __tablename__ = "applicatie"

    id: Mapped[uuid.UUID] = _pk()
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    beschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)
    hostingmodel: Mapped[HostingModel] = mapped_column(hostingmodel_enum, nullable=False)
    # Configureerbaar per tenant — bewust geen hardcoded enum (ADR-009 / verboden patronen)
    eigenaar_organisatie: Mapped[str] = mapped_column(String(120), nullable=False)
    eigenaar_naam: Mapped[str | None] = mapped_column(String(255), nullable=True)
    leverancier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    migratiepad: Mapped[Migratiepad] = mapped_column(migratiepad_enum, nullable=False)
    complexiteit: Mapped[NiveauEnum] = mapped_column(niveau_enum, nullable=False)
    prioriteit: Mapped[NiveauEnum] = mapped_column(niveau_enum, nullable=False)
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        lifecycle_status_enum, nullable=False, server_default=text("'concept'")
    )


class Datatype(Base, TenantMixin, TimestampMixin):
    __tablename__ = "datatype"

    id: Mapped[uuid.UUID] = _pk()
    applicatie_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False
    )
    categorie: Mapped[DatatypeCategorie] = mapped_column(datatype_categorie_enum, nullable=False)
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)
    omvang_indicatie: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Gebruikersgroep(Base, TenantMixin, TimestampMixin):
    __tablename__ = "gebruikersgroep"

    id: Mapped[uuid.UUID] = _pk()
    applicatie_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False
    )
    # Configureerbaar per tenant — geen hardcoded enum
    organisatie: Mapped[str] = mapped_column(String(120), nullable=False)
    afdeling: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aantal_gebruikers: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Koppeling(Base, TenantMixin, TimestampMixin):
    __tablename__ = "koppeling"
    __table_args__ = (
        CheckConstraint(
            "bron_applicatie_id <> doel_applicatie_id",
            name="ck_koppeling_bron_ne_doel",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    bron_applicatie_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False
    )
    doel_applicatie_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False
    )
    richting: Mapped[Koppelrichting] = mapped_column(koppelrichting_enum, nullable=False)
    protocol: Mapped[Koppelprotocol] = mapped_column(koppelprotocol_enum, nullable=False)
    impact_bij_verbreking: Mapped[ImpactVerbreking] = mapped_column(
        impact_verbreking_enum, nullable=False
    )
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChecklistVraag(Base):
    """Referentietabel — NIET tenant-scoped, geen RLS. Geseed (89 vragen)."""

    __tablename__ = "checklistvraag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    categorie_nr: Mapped[int] = mapped_column(Integer, nullable=False)
    categorie_naam: Mapped[str] = mapped_column(String(120), nullable=False)
    vraag: Mapped[str] = mapped_column(Text, nullable=False)
    prioriteit: Mapped[ChecklistPrioriteit] = mapped_column(
        checklist_prioriteit_enum, nullable=False
    )
    # ADR-019: type van het additionele antwoordveld. Default `geen` (server_default)
    # → bestaande rijen blijven geldig zonder backfill; voedt de engine NIET.
    antwoordtype: Mapped[AntwoordType] = mapped_column(
        antwoordtype_enum, nullable=False, server_default=text("'geen'")
    )


class ChecklistVraagOptie(Base):
    """Optie-catalogus per checklistvraag (ADR-019, Besluit 10) — platform-brede
    referentiedata, GEEN RLS. Stabiel `optie_sleutel` (nooit hernummeren); bewerken
    = soft-deactiveren via `actief` (Besluit 9). `afgeleid_bron` markeert een set die
    uit een model-enum is afgeleid (2.1←HostingModel, 12.1←NiveauEnum) en in de
    beheerder-UI structureel read-only is (alleen het label is aanpasbaar)."""

    __tablename__ = "checklistvraag_optie"
    __table_args__ = (
        UniqueConstraint("vraag_code", "optie_sleutel", name="uq_checklistvraag_optie"),
    )

    id: Mapped[uuid.UUID] = _pk()
    vraag_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("checklistvraag.code"), nullable=False
    )
    optie_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    volgorde: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    actief: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=text("true")
    )
    afgeleid_bron: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Checklistscore(Base, TenantMixin, TimestampMixin):
    __tablename__ = "checklistscore"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "applicatie_id", "vraag_code",
            name="uq_checklistscore_app_vraag",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    applicatie_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False
    )
    vraag_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("checklistvraag.code"), nullable=False
    )
    score: Mapped[ChecklistScore | None] = mapped_column(checklist_score_enum, nullable=True)
    bevinding: Mapped[str | None] = mapped_column(Text, nullable=True)
    eigenaar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actie: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ADR-019: gestructureerd antwoord (jsonb, nullable). Envelope per antwoordtype:
    # {"optie": "<sleutel>"} / {"opties": ["<sleutel>", …]} / {"getal": <int>}.
    # Voedt de engine NOOIT — alleen `score` stuurt lifecycle/blokkade.
    antwoord_waarde: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class Blokkade(Base, TenantMixin, TimestampMixin):
    __tablename__ = "blokkade"

    id: Mapped[uuid.UUID] = _pk()
    checklistscore_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("checklistscore.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # Gedenormaliseerd voor filtering
    applicatie_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applicatie.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[BlokkadeStatus] = mapped_column(
        blokkade_status_enum, nullable=False, server_default=text("'open'")
    )
    toelichting: Mapped[str | None] = mapped_column(Text, nullable=True)
    eigenaar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opgelost_op: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
