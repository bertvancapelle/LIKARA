"""SQLAlchemy-modellen — BWB-ontvlechtingsmodule (ADR-009).

Zes tenant-scoped entiteiten (RLS) + één referentietabel (ChecklistVraag).
Enums worden als PostgreSQL enum-types beheerd via de Alembic-migratie;
de hier gedefinieerde `sa.Enum`-typeobjecten delen dezelfde namen.
"""
import uuid
from datetime import date, datetime
from enum import Enum

import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class ContractType(str, Enum):
    """ADR-020 — soort contract. `deelcontract` vereist een mantel (DB-CHECK
    `ck_contract_mantel_consistentie`); `mantelcontract`/`los_contract` hebben er
    juist géén."""

    mantelcontract = "mantelcontract"
    deelcontract = "deelcontract"
    los_contract = "los_contract"


class ContractConfigDimensie(str, Enum):
    """ADR-020 — discriminator van de platform-brede classificatie-catalogus
    `contractconfig_optie` (één tabel, drie dimensies)."""

    dekking = "dekking"
    kostenmodel = "kostenmodel"
    relatie_rol = "relatie_rol"


class ComponentConfigDimensie(str, Enum):
    """ADR-021 / ADR-012 Addendum C — discriminator van de platform-brede
    componentcatalogus `componentconfig_optie` (één tabel, twee dimensies)."""

    componenttype = "componenttype"
    structuurrelatie_type = "structuurrelatie_type"


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
contracttype_enum = sa.Enum(ContractType, name="contracttype_enum")
contractconfig_dimensie_enum = sa.Enum(
    ContractConfigDimensie, name="contractconfig_dimensie_enum"
)
componentconfig_dimensie_enum = sa.Enum(
    ComponentConfigDimensie, name="componentconfig_dimensie_enum"
)


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


# --------------------------------------------------------------------------
# Modellen
# --------------------------------------------------------------------------

class Component(Base, TenantMixin, TimestampMixin):
    """ADR-021 — supertype/knooppunt van de landschapsgraaf (tenant-scoped, RLS).

    Draagt de technische identiteit (naam, type, hosting, eigenaarschap, leverancier).
    `componenttype` is een tekst-sleutel uit de componentcatalogus (dimensie
    `componenttype`); `applicatie` is een systeem-sleutel met een subtype-rij."""

    __tablename__ = "component"

    id: Mapped[uuid.UUID] = _pk()
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    componenttype: Mapped[str] = mapped_column(String(60), nullable=False)
    hostingmodel: Mapped[HostingModel] = mapped_column(hostingmodel_enum, nullable=False)
    # Configureerbaar per tenant — bewust geen hardcoded enum (verboden patronen)
    eigenaar_organisatie: Mapped[str] = mapped_column(String(120), nullable=False)
    eigenaar_naam: Mapped[str | None] = mapped_column(String(255), nullable=True)
    leverancier: Mapped[str | None] = mapped_column(String(255), nullable=True)  # B4
    beschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)


class Applicatie(Base, TenantMixin, TimestampMixin):
    """ADR-021 — subtype van Component (CD051 Optie 2: shared-PK class-table).

    `id` is tegelijk PK én FK → `component.id` (1-op-1; een applicatie-rij kan niet
    bestaan zonder component-rij — de subtype-grens is structureel). Draagt exclusief
    het applicatie-apparaat (engine-relevant): lifecycle/migratiepad/complexiteit/
    prioriteit. De naam en overige identiteit staan op de component."""

    __tablename__ = "applicatie"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("component.id", ondelete="CASCADE"),
        primary_key=True,
    )
    migratiepad: Mapped[Migratiepad] = mapped_column(migratiepad_enum, nullable=False)
    complexiteit: Mapped[NiveauEnum] = mapped_column(niveau_enum, nullable=False)
    prioriteit: Mapped[NiveauEnum] = mapped_column(niveau_enum, nullable=False)

    # Shared-PK relatie naar het supertype (eager): de component draagt de identiteit.
    component: Mapped["Component"] = relationship("Component", lazy="joined")
    # ADR-022 Fase A: de engine-state (lifecycle_status) verhuist naar het generieke
    # ComponentProfiel (shared-PK). Elke applicatie heeft precies één profiel; eager
    # geladen zodat de `lifecycle_status`-proxy zonder async lazy-IO werkt. Geen
    # directe FK applicatie↔profiel (beide delen de component-PK) → expliciete
    # shared-PK-primaryjoin met `foreign()`; viewonly (persist gaat via de service).
    profiel: Mapped["ComponentProfiel"] = relationship(
        "ComponentProfiel",
        primaryjoin="Applicatie.id == foreign(ComponentProfiel.id)",
        uselist=False,
        lazy="joined",
        viewonly=True,
    )

    @property
    def lifecycle_status(self) -> "LifecycleStatus":
        """Read-only proxy → het generieke profiel (ADR-022). Schrijven gaat via
        `obj.profiel.lifecycle_status` (service-laag)."""
        return self.profiel.lifecycle_status

    # Read-only proxy-properties → API-byte-compat (§5): de bestaande ApplicatieRead-
    # velden (naam/hosting/eigenaar/leverancier/beschrijving) lezen door naar de
    # component. Mutaties lopen via de service naar `obj.component.<veld>`.
    @property
    def naam(self) -> str:
        return self.component.naam

    @property
    def beschrijving(self) -> str | None:
        return self.component.beschrijving

    @property
    def hostingmodel(self) -> "HostingModel":
        return self.component.hostingmodel

    @property
    def eigenaar_organisatie(self) -> str:
        return self.component.eigenaar_organisatie

    @property
    def eigenaar_naam(self) -> str | None:
        return self.component.eigenaar_naam

    @property
    def leverancier(self) -> str | None:
        return self.component.leverancier


class ComponentProfiel(Base, TenantMixin, TimestampMixin):
    """ADR-022 — generiek beoordelingsprofiel: drager van de engine-state
    (lifecycle_status; anker voor checklistscores/blokkades), shared-PK met
    `component` (CD051 Optie 2: `id` = PK én FK → `component.id`). Eén profiel per
    component; bestaat alleen voor checklist-dragende typen (in Fase A: `applicatie`).
    Tenant-scoped (RLS). `componenttype` wordt NIET gedenormaliseerd — het type leeft
    op de component (Besluit 1b)."""

    __tablename__ = "component_profiel"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("component.id", ondelete="CASCADE"),
        primary_key=True,
    )
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
    # ADR-021 Besluit 5: bron/doel zijn nu component-FK's (velden ongewijzigd; de FK
    # herankert van applicatie → component). Met de shared-PK (CD051 Optie 2) blijven
    # de bestaande waarden geldig: een applicatie-id ís het component-id.
    bron_applicatie_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("component.id", ondelete="CASCADE"), nullable=False
    )
    doel_applicatie_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("component.id", ondelete="CASCADE"), nullable=False
    )
    richting: Mapped[Koppelrichting] = mapped_column(koppelrichting_enum, nullable=False)
    protocol: Mapped[Koppelprotocol] = mapped_column(koppelprotocol_enum, nullable=False)
    impact_bij_verbreking: Mapped[ImpactVerbreking] = mapped_column(
        impact_verbreking_enum, nullable=False
    )
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)


class ComponentStructuur(Base, TenantMixin, TimestampMixin):
    """ADR-021 Besluit 6 — opbouw/afhankelijkheid (tenant-scoped, RLS).

    `component_id` (de afhankelijke) draait op / maakt deel uit van `op_component_id`.
    `relatietype` is een tekst-sleutel uit de catalogus (dimensie `structuurrelatie_type`).
    Self-FK RESTRICT op `op_component_id` (een onderlegger met afhankelijkheden
    verdwijnt niet stil). B3: cyclusbewaking beperkt tot de self-ref-CHECK."""

    __tablename__ = "component_structuur"
    __table_args__ = (
        CheckConstraint(
            "component_id <> op_component_id", name="ck_component_structuur_self"
        ),
        UniqueConstraint(
            "tenant_id", "component_id", "op_component_id", "relatietype",
            name="uq_component_structuur",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("component.id", ondelete="CASCADE"), nullable=False
    )
    op_component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("component.id", ondelete="RESTRICT"), nullable=False
    )
    relatietype: Mapped[str] = mapped_column(String(60), nullable=False)
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChecklistVraag(Base, TenantMixin):
    """ADR-022 Wijziging W1 — **tenant-scoped** vragenset (RLS + FORCE), eigendom van
    de tenant. Surrogate UUID-PK (`id`), `componenttype`-discriminator (één vraag →
    één componenttype; app-side gevalideerd tegen de componentcatalogus). Identiteit:
    `UNIQUE(tenant_id, componenttype, code)`. `actief` (default true): "verwijderen" =
    soft-deactivatie — een inactieve vraag valt uit de actieve set én uit `aantal_vragen`,
    bestaande scores blijven historie. `UNIQUE(tenant_id, id)` is het composiet-FK-target
    voor de kind-FK's (Knoop 1)."""

    __tablename__ = "checklistvraag"
    __table_args__ = (
        UniqueConstraint("tenant_id", "componenttype", "code", name="uq_checklistvraag_type_code"),
        UniqueConstraint("tenant_id", "id", name="uq_checklistvraag_tenant_id"),
    )

    id: Mapped[uuid.UUID] = _pk()
    componenttype: Mapped[str] = mapped_column(String(60), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
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
    # ADR-022 W1: soft-deactivatie i.p.v. hard-delete.
    actief: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=text("true")
    )


class ChecklistVraagOptie(Base, TenantMixin):
    """Optie-catalogus per checklistvraag (ADR-019, Besluit 10). ADR-022 W1:
    **tenant-scoped** (RLS + FORCE). Stabiel `optie_sleutel` (nooit hernummeren);
    bewerken = soft-deactiveren via `actief` (Besluit 9). `afgeleid_bron` markeert een
    set die uit een model-enum is afgeleid (2.1←HostingModel, 12.1←NiveauEnum) en in de
    beheer-UI structureel read-only is (alleen het label is aanpasbaar). De FK naar de
    vraag is composiet `(tenant_id, checklistvraag_id)` → `checklistvraag(tenant_id, id)`
    (Knoop 1: schema dwingt tenant-gelijkheid af)."""

    __tablename__ = "checklistvraag_optie"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "checklistvraag_id", "optie_sleutel", name="uq_checklistvraag_optie"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "checklistvraag_id"],
            ["checklistvraag.tenant_id", "checklistvraag.id"],
            name="fk_checklistvraag_optie_vraag",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    # ADR-022 W1: composiet-FK via __table_args__ (geen kolom-FK meer).
    checklistvraag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
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
            "tenant_id", "component_id", "checklistvraag_id",
            name="uq_checklistscore_app_vraag",
        ),
        # ADR-022 W1: composiet-FK naar de tenant-scoped vraag (schema dwingt
        # tenant-gelijkheid af). Geen ondelete CASCADE: vragen worden soft-gedeactiveerd
        # (Besluit 4), scores blijven historie.
        ForeignKeyConstraint(
            ["tenant_id", "checklistvraag_id"],
            ["checklistvraag.tenant_id", "checklistvraag.id"],
            name="fk_checklistscore_vraag",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    # ADR-022 Fase A: anker verschuift van applicatie → het generieke profiel
    # (component_profiel.id == component.id == applicatie.id, shared-PK).
    component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("component_profiel.id", ondelete="CASCADE"), nullable=False
    )
    # ADR-022 W1: composiet-FK via __table_args__ (geen kolom-FK meer).
    checklistvraag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
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
    # Gedenormaliseerd voor filtering — ADR-022 Fase A: anker = generiek profiel.
    component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("component_profiel.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[BlokkadeStatus] = mapped_column(
        blokkade_status_enum, nullable=False, server_default=text("'open'")
    )
    toelichting: Mapped[str | None] = mapped_column(Text, nullable=True)
    eigenaar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opgelost_op: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )


# --------------------------------------------------------------------------
# ADR-020 — leverancier-/contractregister (additieve feitenlaag, CD040)
#
# Puur registratief: voedt de lifecycle-/blokkade-engine NOOIT. Vijf tenant-
# scoped tabellen (RLS via de migratie) + één platform-brede catalogus
# (ContractConfigOptie, géén RLS). Cross-row-invarianten (ouder = mantel,
# leverancier-erving, een mantel heeft zelf geen mantel) horen in de service-
# laag van Fase B — hier alleen de DB-borging (CHECK + UNIQUE + FK-ondelete).
# --------------------------------------------------------------------------

class Leverancier(Base, TenantMixin, TimestampMixin):
    """ADR-020 — leverancier (tenant-scoped, RLS). Eén platte contactset;
    0..n contactpersonen is een latere uitbreiding (ADR-020 Niet in scope)."""

    __tablename__ = "leverancier"

    id: Mapped[uuid.UUID] = _pk()
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    straat_huisnummer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postcode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plaats: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contactpersoon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefoon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mobiel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)


class Contract(Base, TenantMixin, TimestampMixin):
    """ADR-020 — contract (tenant-scoped, RLS). `contracttype` + self-FK
    `mantelcontract_id`; de DB-CHECK dwingt type↔mantel_id-consistentie af
    (deelcontract ⇒ mantel verplicht; anders ⇒ géén mantel). Datums zijn puur
    registratief (B4: geen validatie). De leverancier-FK is `RESTRICT` zodat een
    leverancier met contracten niet stil verdwijnt; de self-FK idem (mantel met
    deelcontracten)."""

    __tablename__ = "contract"
    __table_args__ = (
        CheckConstraint(
            "(contracttype = 'deelcontract' AND mantelcontract_id IS NOT NULL) "
            "OR (contracttype <> 'deelcontract' AND mantelcontract_id IS NULL)",
            name="ck_contract_mantel_consistentie",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    leverancier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leverancier.id", ondelete="RESTRICT"), nullable=False
    )
    contracttype: Mapped[ContractType] = mapped_column(contracttype_enum, nullable=False)
    mantelcontract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contract.id", ondelete="RESTRICT"), nullable=True
    )
    contractnaam: Mapped[str] = mapped_column(String(255), nullable=False)
    extern_contract_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    leverancier_contract_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    begindatum: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    einddatum: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    vernieuwingsdatum: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)
    toelichting: Mapped[str | None] = mapped_column(Text, nullable=True)


class ContractDekking(Base, TenantMixin, TimestampMixin):
    """ADR-020 — dekking-tag op een contract (0..n). `optie_sleutel` verwijst naar
    de actieve catalogus (dimensie `dekking`); app-side gevalideerd in Fase B, géén
    harde FK (catalogus is platform-referentiedata zonder tenant_id)."""

    __tablename__ = "contract_dekking"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "contract_id", "optie_sleutel", name="uq_contract_dekking"
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contract.id", ondelete="CASCADE"), nullable=False
    )
    optie_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)


class ContractKostenmodel(Base, TenantMixin, TimestampMixin):
    """ADR-020 — kostenmodel-tag op een contract (0..n). Zie `ContractDekking`
    (dimensie `kostenmodel`)."""

    __tablename__ = "contract_kostenmodel"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "contract_id", "optie_sleutel", name="uq_contract_kostenmodel"
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contract.id", ondelete="CASCADE"), nullable=False
    )
    optie_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)


class ComponentContract(Base, TenantMixin, TimestampMixin):
    """ADR-021 Besluit 7 — koppeling component ↔ contract met precies één `relatie_rol`
    (dimensie `relatie_rol`, app-side gevalideerd). Vervangt `applicatie_contract`:
    élk component kan contracten dragen. Hoogstens één keer hetzelfde contract per
    component (UNIQUE). Met de shared-PK is `component_id` voor een applicatie
    identiek aan zijn applicatie-id — de bestaande API blijft applicatie_id spreken."""

    __tablename__ = "component_contract"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "component_id", "contract_id", name="uq_component_contract"
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("component.id", ondelete="CASCADE"), nullable=False
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contract.id", ondelete="CASCADE"), nullable=False
    )
    relatie_rol: Mapped[str] = mapped_column(String(60), nullable=False)


class ContractConfigOptie(Base):
    """ADR-020 Besluit 6 / ADR-012 Addendum B — platform-brede classificatie-
    catalogus (GEEN RLS, GEEN tenant_id), één tabel met `dimensie`-discriminator
    {dekking, kostenmodel, relatie_rol}. Stabiel `optie_sleutel` per dimensie;
    bewerken = soft-deactiveren via `actief` (nooit hard verwijderen/hernummeren).
    Zelfde soort referentiedata als `checklistvraag_optie` (ADR-019)."""

    __tablename__ = "contractconfig_optie"
    __table_args__ = (
        UniqueConstraint("dimensie", "optie_sleutel", name="uq_contractconfig_optie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dimensie: Mapped[ContractConfigDimensie] = mapped_column(
        contractconfig_dimensie_enum, nullable=False
    )
    optie_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    volgorde: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    actief: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=text("true")
    )


class ComponentConfigOptie(Base):
    """ADR-021 Besluit 8 / ADR-012 Addendum C — platform-brede componentcatalogus
    (GEEN RLS, GEEN tenant_id), één tabel met `dimensie`-discriminator
    {componenttype, structuurrelatie_type}. Zelfde vorm/grants als
    `contractconfig_optie`. De sleutel `componenttype.applicatie` is een
    systeem-sleutel (Fase C borgt de service-bescherming)."""

    __tablename__ = "componentconfig_optie"
    __table_args__ = (
        UniqueConstraint("dimensie", "optie_sleutel", name="uq_componentconfig_optie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dimensie: Mapped[ComponentConfigDimensie] = mapped_column(
        componentconfig_dimensie_enum, nullable=False
    )
    optie_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    volgorde: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    actief: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=text("true")
    )
