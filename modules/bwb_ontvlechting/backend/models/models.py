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

from app.core.audit import AuditActie, auditactie_enum
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
    """ADR-020 — discriminator van de platform-brede contract-configuratie-catalogus
    `contractconfig_optie`. Uitsluitend contract-eigen classificaties: `dekking` +
    `kostenmodel`. (`relatie_rol` is met de consistentie-opruim verhuisd naar de
    relatie-kenmerk-catalogus — het is een relatie-kenmerk, geen contract-configuratie.)"""

    dekking = "dekking"
    kostenmodel = "kostenmodel"


class RelatieKenmerkDimensie(str, Enum):
    """ADR-023 Fase E — discriminator van de platform-brede **relatie-kenmerk-vocabulaire**-
    catalogus `relatiekenmerk_optie`. Hier horen de beheerbare waardenlijsten van
    relatie-kenmerken thuis — losgekoppeld van de contract-configuratie (`ContractConfig`):
    `dispositie` (plateau-lidmaatschap), `relatie_rol` (rol van een contract in zijn
    association met een component) en `beheerrol` (ADR-024 slice 2b — de rol die een partij
    vervult op een component/contract; gebruikt door de `roltoewijzing`-tabel, niet door het
    relatie-model). Toekomstige relatie-kenmerken landen hier eveneens."""

    dispositie = "dispositie"
    relatie_rol = "relatie_rol"
    beheerrol = "beheerrol"


class ComponentConfigDimensie(str, Enum):
    """ADR-021 / ADR-012 Addendum C — discriminator van de platform-brede
    componentcatalogus `componentconfig_optie`. ADR-023: derde dimensie
    `archimate_relatie` (de gecureerde acht relatietypes)."""

    componenttype = "componenttype"
    structuurrelatie_type = "structuurrelatie_type"
    archimate_relatie = "archimate_relatie"


class ElementType(str, Enum):
    """ADR-023 Besluit 2 — discriminator van de element-supertabel (één
    identiteitsruimte). Subtypes dragen hun type-eigen velden in een eigen tabel."""

    component = "component"
    datatype = "datatype"
    gebruikersgroep = "gebruikersgroep"
    contract = "contract"
    plateau = "plateau"
    gap = "gap"
    work_package = "work_package"
    deliverable = "deliverable"
    # ADR-024 slice 1 — partij-supertype (business actor). Slice 1 realiseert alleen
    # aard `externe_partij`; de andere aarden (organisatie/persoon/…) zijn latere slices.
    partij = "partij"


class PartijAard(str, Enum):
    """ADR-024 — aard van een partij (discriminator op de `partij`-subtabel). Slice 1
    gebruikt alleen `externe_partij`; de overige aarden zijn structureel voorzien maar
    nog niet gerealiseerd. Geen combinatie-/businessregels — alleen geldigheid."""

    externe_partij = "externe_partij"
    organisatie = "organisatie"
    organisatie_eenheid = "organisatie_eenheid"
    persoon = "persoon"


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
relatiekenmerk_dimensie_enum = sa.Enum(
    RelatieKenmerkDimensie, name="relatiekenmerk_dimensie_enum"
)
componentconfig_dimensie_enum = sa.Enum(
    ComponentConfigDimensie, name="componentconfig_dimensie_enum"
)
element_type_enum = sa.Enum(ElementType, name="element_type_enum")
partij_aard_enum = sa.Enum(PartijAard, name="partij_aard_enum")


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


# --------------------------------------------------------------------------
# Modellen
# --------------------------------------------------------------------------

class Element(Base, TenantMixin, TimestampMixin):
    """ADR-023 Besluit 1/2/12 — element-supertype: één identiteitsruimte (ArchiMate-
    leidraad), tenant-scoped (FORCE RLS). `UNIQUE(tenant_id, id)` is het composiet-FK-
    target voor relatie-endpoints én subtype-tabellen (cross-tenant structureel
    uitgesloten). Subtypes (component, datatype, gebruikersgroep, contract, plateau, gap,
    work_package, deliverable) delen de PK via `(tenant_id, id)`-FK."""

    __tablename__ = "element"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_element_tenant_id"),
    )

    id: Mapped[uuid.UUID] = _pk()
    element_type: Mapped[ElementType] = mapped_column(element_type_enum, nullable=False)


class Relatie(Base, TenantMixin, TimestampMixin):
    """ADR-023 Besluit 1/6/12 — één getypeerd relatiemodel (gecureerde ArchiMate-subset).

    Gericht (`bron_id` → `doel_id`); endpoints zijn echte composiet-FK's
    `(tenant_id, bron_id|doel_id)` → `element` (cross-tenant structureel uitgesloten,
    geen polymorfie). `relatietype` uit de catalogus (dim `archimate_relatie`);
    `kenmerken` (jsonb) per relatietype gevalideerd tegen de catalogus-property-definities
    (OK-2 — richting is GEEN kenmerk). `CHECK bron≠doel`; `UNIQUE(tenant, bron, doel, type)`.
    Tenant-scoped (FORCE RLS)."""

    __tablename__ = "relatie"
    __table_args__ = (
        CheckConstraint("bron_id <> doel_id", name="ck_relatie_bron_ne_doel"),
        UniqueConstraint("tenant_id", "bron_id", "doel_id", "relatietype", name="uq_relatie"),
        ForeignKeyConstraint(
            ["tenant_id", "bron_id"], ["element.tenant_id", "element.id"],
            name="fk_relatie_bron_element", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "doel_id"], ["element.tenant_id", "element.id"],
            name="fk_relatie_doel_element", ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    bron_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    doel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relatietype: Mapped[str] = mapped_column(String(40), nullable=False)
    kenmerken: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)


class Component(Base, TenantMixin, TimestampMixin):
    """ADR-021 — knooppunt van de landschapsgraaf. ADR-023: subtype van `element`
    (shared-PK via composiet-FK `(tenant_id, id)` → `element`; cross-tenant uitgesloten).

    Draagt de technische identiteit (naam, type, hosting, eigenaarschap, leverancier).
    `componenttype` is een tekst-sleutel uit de componentcatalogus (dimensie
    `componenttype`); `applicatie` is een systeem-sleutel met een subtype-rij."""

    __tablename__ = "component"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_component_element", ondelete="CASCADE",
        ),
        # ADR-024 UX-B6-b — eigenaar-organisatie verwijst naar een partij-element (aard=organisatie,
        # app-side geborgd). Optioneel; ON DELETE SET NULL (kolom-specifiek op eigenaar_organisatie_id
        # in de migratie — een kale SET NULL zou óók de gedeelde tenant_id nullen).
        ForeignKeyConstraint(
            ["tenant_id", "eigenaar_organisatie_id"], ["element.tenant_id", "element.id"],
            name="fk_component_eigenaar_organisatie", ondelete="SET NULL",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    componenttype: Mapped[str] = mapped_column(String(60), nullable=False)
    hostingmodel: Mapped[HostingModel] = mapped_column(hostingmodel_enum, nullable=False)
    # ADR-024 UX-B6-b — optionele verwijzing naar de eigenaar-organisatie (partij, aard=organisatie).
    eigenaar_organisatie_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
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
    def eigenaar_organisatie_id(self) -> "uuid.UUID | None":
        return self.component.eigenaar_organisatie_id

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
    """ADR-023 B-mig-1: subtype van `element` (shared-PK, ArchiMate data object)."""

    __tablename__ = "datatype"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_datatype_element", ondelete="CASCADE",
        ),
    )

    # ADR-023 B-mig-2 slice 4: de band met de applicatie is een `access`-relatie geworden
    # (geen `applicatie_id`-kolom meer; Besluit 13 — wezen blijven bestaan).
    id: Mapped[uuid.UUID] = _pk()
    categorie: Mapped[DatatypeCategorie] = mapped_column(datatype_categorie_enum, nullable=False)
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)
    omvang_indicatie: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Gebruikersgroep(Base, TenantMixin, TimestampMixin):
    """ADR-023 B-mig-1: subtype van `element` (shared-PK, ArchiMate business actor/role)."""

    __tablename__ = "gebruikersgroep"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_gebruikersgroep_element", ondelete="CASCADE",
        ),
        # ADR-024 UX-B6-a — organisatie verwijst naar een partij-element (aard=organisatie,
        # app-side geborgd). Optioneel; ON DELETE SET NULL → organisatie wordt 'onbekend'
        # als de partij verdwijnt (geen verplichte koppeling).
        ForeignKeyConstraint(
            ["tenant_id", "organisatie_id"], ["element.tenant_id", "element.id"],
            name="fk_gebruikersgroep_organisatie", ondelete="SET NULL",
        ),
    )

    # ADR-023 B-mig-2 slice 4: de band met de applicatie is een `serving`-relatie geworden.
    id: Mapped[uuid.UUID] = _pk()
    # ADR-024 UX-B6-a — optionele verwijzing naar de organisatie (partij, aard=organisatie).
    organisatie_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    afdeling: Mapped[str | None] = mapped_column(String(255), nullable=True)
    aantal_gebruikers: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Plateau(Base, TenantMixin, TimestampMixin):
    """ADR-023 Fase E (Besluit 2/11) — migratielaag-element: een momentopname van het
    landschap (bv. "Huidig"/"Doel"). Element-subtype (shared-PK via composiet-FK
    `(tenant_id, id)` → `element`, FORCE RLS via de migratie; cross-tenant uitgesloten).

    Type-eigen velden: `naam` (het element-supertype draagt geen naam, Besluit 9) +
    `toelichting`. Lidmaatschap loopt via het unified relatiemodel als `aggregation`-relatie
    (bron=plateau/geheel, doel=lid/deel) met de dispositie + contractuele bevestiging als
    kenmerken — géén aparte membership-tabel (Besluit 1/8)."""

    __tablename__ = "plateau"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_plateau_element", ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    toelichting: Mapped[str | None] = mapped_column(Text, nullable=True)


class Deliverable(Base, TenantMixin, TimestampMixin):
    """ADR-023 Fase E (E3, Besluit 2/11) — migratielaag-element: een concreet resultaat dat
    door een werkpakket wordt opgeleverd en dat een plateau mee helpt realiseren. Element-
    subtype (shared-PK via composiet-FK `(tenant_id, id)` → `element`, FORCE RLS via de
    migratie; cross-tenant uitgesloten).

    Type-eigen velden: `naam` (verplicht) + `toelichting`. De realisatieketen
    (work_package → deliverable → plateau) loopt via het unified relatiemodel met het
    bestaande relatietype **`realization`** (bron = realiseerder → doel = gerealiseerde) —
    géén FK-kolommen, géén nieuw relatietype. Koppelingen zijn expliciet en optioneel
    (Besluit 8): een deliverable mag bestaan zonder werkpakket en/of zonder plateau."""

    __tablename__ = "deliverable"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_deliverable_element", ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    toelichting: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkPackage(Base, TenantMixin, TimestampMixin):
    """ADR-023 Fase E (E2, Besluit 2/11) — migratielaag-element: een eenheid van
    migratiewerk, hiërarchisch opdeelbaar in subpakketten. Element-subtype (shared-PK via
    composiet-FK `(tenant_id, id)` → `element`, FORCE RLS via de migratie; cross-tenant
    uitgesloten).

    Type-eigen velden: `naam` (verplicht) + `toelichting`. `bovenliggend_id` is een
    **composiet self-FK** `(tenant_id, bovenliggend_id)` → `work_package(tenant_id, id)`
    (tenant-consistent, Besluit 12) met **`ON DELETE RESTRICT`**: een werkpakket met
    directe subpakketten kan niet verwijderd worden (geen stilzwijgend wegvagen van de
    subboom — de service geeft 409 `HEEFT_SUBPAKKETTEN`; RESTRICT is de DB-backstop).
    Cycluspreventie (zelf-ouder + transitieve kring) zit in de servicelaag (E-4); de
    DB-CHECK borgt alléén de directe self-parent als extra vangnet."""

    __tablename__ = "work_package"
    __table_args__ = (
        # Composiet-FK-target voor de self-FK (tenant-consistent).
        UniqueConstraint("tenant_id", "id", name="uq_work_package_tenant_id"),
        CheckConstraint(
            "bovenliggend_id IS NULL OR bovenliggend_id <> id",
            name="ck_work_package_geen_self_parent",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_work_package_element", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "bovenliggend_id"], ["work_package.tenant_id", "work_package.id"],
            name="fk_work_package_bovenliggend", ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    toelichting: Mapped[str | None] = mapped_column(Text, nullable=True)
    bovenliggend_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class Gap(Base, TenantMixin, TimestampMixin):
    """ADR-023 Fase E (E4, Besluit 2/11) — migratielaag-element: een geregistreerde kloof
    tussen een baseline-situatie en een doel-situatie. Element-subtype (shared-PK via
    composiet-FK `(tenant_id, id)` → `element`, FORCE RLS via de migratie; cross-tenant
    uitgesloten).

    Type-eigen velden: `naam` (verplicht) + `toelichting`. **2-ariteit hard in het schema**
    (Besluit 1): `baseline_plateau_id` en `doel_plateau_id` zijn twee verplichte composiet-FK-
    kolommen `(tenant_id, <kolom>) → element(tenant_id, id)` (NOT NULL). Dat het écht plateaus
    zijn wordt door de service afgedwongen (422 `ONGELDIG_PLATEAU`); baseline ≠ doel is een
    service-check (422 `BASELINE_GELIJK_AAN_DOEL`) met de DB-CHECK als backstop.

    Gap-leden (component/contract) lopen via het unified relatiemodel als `association`-relatie
    (bron=gap → doel=lid) — géén aparte membership-tabel, géén nieuw relatietype (Besluit 8).
    De twee readiness-cijfers (technisch + contractueel) zijn **puur read-only afgeleid** uit
    de bestaande lifecycle resp. de doel-plateau-bevestiging — er wordt niets opgeslagen en de
    engine wordt niet geraakt."""

    __tablename__ = "gap"
    __table_args__ = (
        CheckConstraint("baseline_plateau_id <> doel_plateau_id", name="ck_gap_baseline_ne_doel"),
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_gap_element", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "baseline_plateau_id"], ["element.tenant_id", "element.id"],
            name="fk_gap_baseline_plateau",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "doel_plateau_id"], ["element.tenant_id", "element.id"],
            name="fk_gap_doel_plateau",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    toelichting: Mapped[str | None] = mapped_column(Text, nullable=True)
    baseline_plateau_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    doel_plateau_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


# ADR-023 B-mig-2 slice 1: het `Koppeling`-model is vervangen door `flow`-relaties in het
# unified relatiemodel (`Relatie`). De enums Koppelrichting/Koppelprotocol/ImpactVerbreking
# blijven — ze typeren nu de flow-kenmerken (richting/protocol/impact_bij_verbreking).


# ADR-023 B-mig-2 slice 2: `ComponentStructuur` is vervangen door `assignment`/`aggregation`-
# relaties in het unified relatiemodel (`Relatie`). De catalogus-dimensie `structuurrelatie_type`
# blijft historisch staan (labels resolvebaar); nieuwe structuurrelaties zijn ArchiMate-relaties.


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
        # ADR-023 Fase F (F-3): per (tenant, componenttype) draagt hoogstens één vraag een
        # gegeven betekenis. NULL is distinct in Postgres → onbeperkt veel vragen zonder
        # betekenis; uniciteit geldt alleen voor toegekende (niet-NULL) betekenissen.
        UniqueConstraint(
            "tenant_id", "componenttype", "betekenis", name="uq_checklistvraag_betekenis"
        ),
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
    # ADR-023 Fase F (F-3): optionele **betekenis** (stabiele `optie_sleutel` uit de
    # platform-brede `vraagbetekenis_optie`-catalogus) — classificeert wat de vraag
    # inhoudelijk aanduidt (eerste: 'technische_plaatsing'), zodat de consistentie-
    # signalering op de betekenis leunt i.p.v. op een vast vraagnummer. App-side
    # gevalideerd tegen de catalogus (stabiele sleutel, geen harde FK). Voedt de engine
    # NIET (geen lifecycle/score/blokkade) — louter classificatie.
    betekenis: Mapped[str | None] = mapped_column(String(60), nullable=True)


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

class Partij(Base, TenantMixin, TimestampMixin):
    """ADR-024 slice 1 — partij-supertype als **element-subtype** (vervangt `leverancier`).
    Shared-PK composiet-FK `(tenant_id, id) → element(tenant_id, id)` ON DELETE CASCADE;
    FORCE RLS (migratie). Eén gedeelde contactset; `aard` discrimineert (slice 1: alleen
    `externe_partij`). `soort` is een **optioneel** platform-catalogus-kenmerk
    (`partijsoort_optie`, app-side gevalideerd — geen harde FK, platform-referentiedata).
    Puur registratief: voedt de engine NOOIT."""

    __tablename__ = "partij"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_partij_element", ondelete="CASCADE",
        ),
        # ADR-024 slice 2a-bis — "hoort bij": persoon/afdeling horen verplicht bij een
        # organisatie(-achtige) partij; een persoon optioneel ook bij een afdeling. Composiet-FK's
        # naar het element-supertype (tenant-consistent), RESTRICT zodat een organisatie/afdeling
        # met leden niet stil verdwijnt. Dat het de juiste aard is (organisatie-achtig resp.
        # organisatie_eenheid binnen die organisatie) borgt de service.
        ForeignKeyConstraint(
            ["tenant_id", "organisatie_id"], ["element.tenant_id", "element.id"],
            name="fk_partij_organisatie", ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "afdeling_id"], ["element.tenant_id", "element.id"],
            name="fk_partij_afdeling", ondelete="RESTRICT",
        ),
        # Harde invariant (DB-backstop): organisatie verplicht voor persoon + organisatie_eenheid,
        # en verboden voor organisatie + externe_partij (de top staat op zichzelf).
        CheckConstraint(
            "(aard IN ('persoon', 'organisatie_eenheid')) = (organisatie_id IS NOT NULL)",
            name="ck_partij_organisatie_verplicht",
        ),
        # Een afdelings-koppeling is alleen zinvol voor een persoon.
        CheckConstraint(
            "afdeling_id IS NULL OR aard = 'persoon'",
            name="ck_partij_afdeling_alleen_persoon",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    aard: Mapped[PartijAard] = mapped_column(partij_aard_enum, nullable=False)
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    straat_huisnummer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postcode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plaats: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contactpersoon: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefoon: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mobiel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # ADR-024 (Optie 1) — contactveld dat uitsluitend voor aard=persoon geldt (service dwingt af).
    functietitel: Mapped[str | None] = mapped_column(String(150), nullable=True)
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)
    soort: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # ADR-024 slice 2a-bis — lidmaatschap (zie __table_args__).
    organisatie_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    afdeling_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class PartijsoortOptie(Base):
    """ADR-024 — platform-brede partijsoort-catalogus (GEEN RLS, GEEN tenant_id). Eigen
    catalogus (soort is een element-attribuut, geen relatie-kenmerk). Grants/soft-
    deactivate identiek aan `vraagbetekenis_optie`. Default-seed: leverancier/partner/
    ketenpartner."""

    __tablename__ = "partijsoort_optie"
    __table_args__ = (
        UniqueConstraint("optie_sleutel", name="uq_partijsoort_optie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    optie_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    volgorde: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    actief: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=text("true"))


class Roltoewijzing(Base, TenantMixin, TimestampMixin):
    """ADR-024 slice 2b — rol-toewijzing: "partij X vervult rol Y op object Z".

    Eigen tenant-scoped registratie-feit (GEEN ArchiMate-element, dus geen element-subtype) —
    bewust los van het unified `relatie`-model: dat dwingt `UNIQUE(tenant,bron,doel,relatietype)`
    af en `association` is al in gebruik voor de component↔contract-koppeling (precies één),
    wat "meerdere rollen per partij per object als losse regels" onmogelijk maakt. Hier is de
    uniciteit exact `(tenant, partij, object, rol)`: dezelfde rol niet dubbel, maar wél meerdere
    rollen per (partij, object) en meerdere partijen met dezelfde rol op één object.

    `partij_id`/`object_id` zijn composiet-FK's naar `element` (CASCADE: de toewijzing verdwijnt
    met de partij of het object). `rol` is een tekst-sleutel naar de `beheerrol`-catalogus
    (`relatiekenmerk_optie`); geldigheid is app-side geborgd (geen harde FK — de sleutel is
    stabiel, soft-deactiveerbaar). Puur registratief — geen engine-koppeling. Tenant-scoped
    (FORCE RLS)."""

    __tablename__ = "roltoewijzing"
    __table_args__ = (
        UniqueConstraint("tenant_id", "partij_id", "object_id", "rol", name="uq_roltoewijzing"),
        ForeignKeyConstraint(
            ["tenant_id", "partij_id"], ["element.tenant_id", "element.id"],
            name="fk_roltoewijzing_partij", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "object_id"], ["element.tenant_id", "element.id"],
            name="fk_roltoewijzing_object", ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    partij_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rol: Mapped[str] = mapped_column(String(60), nullable=False)


class GebruikerPersoon(Base, TenantMixin):
    """ADR-029 — brug tussen de Keycloak-login (`keycloak_sub`) en de persoon-partij (ADR-024).

    Tenant-scoped registratie-feit (FORCE RLS), géén ArchiMate-element. Eén login ↔ ten hoogste
    één persoon per tenant en omgekeerd (twee UNIQUE-constraints). `persoon_id` is een composiet-FK
    naar `element(tenant_id, id)` (CASCADE: de koppeling verdwijnt met de persoon). De koppeling
    ontstaat bij gebruiker-aanmaak via KILARA (sub uit de Keycloak Admin API). Puur registratief —
    geen engine-koppeling. Eigen `aangemaakt_op` (geen TimestampMixin: deze rij wordt niet gemuteerd)."""

    __tablename__ = "gebruiker_persoon"
    __table_args__ = (
        UniqueConstraint("tenant_id", "keycloak_sub", name="uq_gebruiker_persoon_sub"),
        UniqueConstraint("tenant_id", "persoon_id", name="uq_gebruiker_persoon_persoon"),
        ForeignKeyConstraint(
            ["tenant_id", "persoon_id"], ["element.tenant_id", "element.id"],
            name="fk_gebruiker_persoon_element", ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    keycloak_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    persoon_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    aangemaakt_op: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class KlaarverklaringStatus(str, Enum):
    klaar = "klaar"
    open = "open"


klaarverklaring_status_enum = sa.Enum(KlaarverklaringStatus, name="klaarverklaring_status_enum")


class ComponentKlaarverklaring(Base, TenantMixin, TimestampMixin):
    """ADR-027 — niet-scorende klaarverklaring op componentniveau.

    Eigen tenant-scoped registratie-feit (GEEN element-subtype): één coördinator verklaart een heel
    component beoordeeld/migratieklaar. Eén levende verklaring per component —
    `UNIQUE(tenant_id, component_id)`. `status` klaar↔open (default `klaar`); elke statushandeling
    vereist een `reden` (verplicht, niet leeg) en herstempelt `verklaard_door`/`verklaard_op`
    server-side. Het klaar→open→klaar-verloop blijft terug te lezen via de append-only audit-trail
    (geen aparte historie-tabel). De per-categorie-dimensie is bewust vervallen — werkverdeling per
    categorie coördineert de mens, het systeem dwingt niets af.

    `component_id` is een composiet-FK `(tenant_id, component_id) → element(tenant_id, id)`
    ON DELETE CASCADE (zelfde vorm als roltoewijzing).

    Puur registratief — RAAKT DE ENGINE NOOIT: importeert géén `lifecycle_service`/
    `herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/`Checklistscore`."""

    __tablename__ = "component_klaarverklaring"
    __table_args__ = (
        UniqueConstraint("tenant_id", "component_id", name="uq_component_klaarverklaring"),
        ForeignKeyConstraint(
            ["tenant_id", "component_id"], ["element.tenant_id", "element.id"],
            name="fk_component_klaarverklaring_component", ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[KlaarverklaringStatus] = mapped_column(
        klaarverklaring_status_enum, nullable=False, server_default=text("'klaar'")
    )
    reden: Mapped[str] = mapped_column(Text, nullable=False)
    # ADR-029 Fase 3b — stabiele actor-sleutel (Keycloak-sub) voor naam-resolutie; `verklaard_door`
    # is voortaan de e-mail-fallback. Historische rijen: sub NULL, e-mail in `verklaard_door`.
    verklaard_door_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verklaard_door: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verklaard_op: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)


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
        # ADR-023 B-mig-1: contract is een element-subtype (shared-PK, business-laag).
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_contract_element", ondelete="CASCADE",
        ),
        # ADR-024 slice 1 (optie A): de term "leverancier" blijft; de FK-target verschuift
        # van de vervallen `leverancier`-tabel naar het **partij-element** (composiet,
        # tenant-consistent). RESTRICT: een partij met contracten is niet verwijderbaar.
        # Dat het écht een partij (aard=externe_partij) is, borgt de service.
        ForeignKeyConstraint(
            ["tenant_id", "leverancier_id"], ["element.tenant_id", "element.id"],
            name="fk_contract_leverancier_partij", ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    leverancier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
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


# ADR-023 B-mig-2 slice 3: `ComponentContract` is vervangen door `association`-relaties
# (bron=component, doel=contract, `relatie_rol` als kenmerk) in het unified relatiemodel.


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


class RelatieKenmerkOptie(Base):
    """ADR-023 Fase E — platform-brede **relatie-kenmerk-vocabulaire**-catalogus (GEEN RLS,
    GEEN tenant_id), één tabel met `dimensie`-discriminator. Zelfde vorm/grants/soft-
    deactivate-semantiek als `contractconfig_optie`/`componentconfig_optie`, maar
    semantisch losgekoppeld van de contract-configuratie: hier horen de waardenlijsten van
    relatie-kenmerken thuis (nu `dispositie` van het plateau-lidmaatschap; later die van de
    gap/work_package/deliverable-relaties). Gevalideerd als kenmerk op de relatie via
    `{"type":"catalogus","catalogus":"relatiekenmerk","dimensie":…}`."""

    __tablename__ = "relatiekenmerk_optie"
    __table_args__ = (
        UniqueConstraint("dimensie", "optie_sleutel", name="uq_relatiekenmerk_optie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dimensie: Mapped[RelatieKenmerkDimensie] = mapped_column(
        relatiekenmerk_dimensie_enum, nullable=False
    )
    optie_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    volgorde: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    actief: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=text("true")
    )


class VraagBetekenisOptie(Base):
    """ADR-023 Fase F (F-3) — platform-brede catalogus van **checklistvraag-betekenissen**
    (GEEN RLS, GEEN tenant_id). Een betekenis classificeert wat een vraag inhoudelijk
    aanduidt (eerste: 'technische_plaatsing' — "waar draait dit op"), zodat de
    consistentie-signalering kan leunen op de betekenis i.p.v. op een vast vraagnummer.
    Zelfde shape/grants/soft-deactivate-semantiek als `relatiekenmerk_optie`, maar ZONDER
    dimensie-discriminator (één doel) — vandaar uniciteit op enkel `optie_sleutel`.
    Gekoppeld vanaf `checklistvraag.betekenis` (stabiele sleutel). Voedt de engine NIET."""

    __tablename__ = "vraagbetekenis_optie"
    __table_args__ = (
        UniqueConstraint("optie_sleutel", name="uq_vraagbetekenis_optie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    # ADR-023 — ArchiMate-mapping (dim `componenttype`: Besluit 4/OK-1/3) resp.
    # kenmerk-definities per relatietype (dim `archimate_relatie`: OK-2). Nullable: niet
    # elke dimensie gebruikt alle velden (dim `structuurrelatie_type` blijft historisch).
    archimate_element: Mapped[str | None] = mapped_column(String(60), nullable=True)
    laag: Mapped[str | None] = mapped_column(String(40), nullable=True)
    aspect: Mapped[str | None] = mapped_column(String(20), nullable=True)
    kenmerk_definitie: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # ADR-022 Fase E (Besluit 1): markeert een `componenttype` als checklist-dragend
    # (krijgt een component_profiel + engine). Enige bron; alléén relevant voor
    # dim=`componenttype`. `applicatie`=true; overige typen default false.
    checklist_dragend: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=text("false")
    )


# --------------------------------------------------------------------------
# ADR-006 — audit-trail (append-only wijzigingsspoor)
#
# Tenant-scoped logboek (FORCE RLS, hash-keten per tenant). Onwijzigbaar: alleen
# SELECT/INSERT-grants + een BEFORE UPDATE/DELETE-trigger (migratie 0010). Records
# worden geschreven door de centrale capture-hook (app.core.audit), nooit via een
# service — dit model dient de LEES-zijde (ADR-006 Fase E). `entiteit_id` is uuid
# (alle tenant-entiteiten hebben een UUID-PK); de polymorfe verwijzing heeft géén FK
# (historie-behoud). De platform-variant `PlatformAuditLog` staat in app/models.
# --------------------------------------------------------------------------

class AuditLog(Base, TenantMixin):
    """ADR-006 — tenant-scoped audit-record (RLS + FORCE, append-only)."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = _pk()
    tijdstip: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    actor_sub: Mapped[str] = mapped_column(Text, nullable=False)
    actor_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    entiteit_type: Mapped[str] = mapped_column(Text, nullable=False)
    entiteit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actie: Mapped[AuditActie] = mapped_column(auditactie_enum, nullable=False)
    wijziging: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correlatie_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    record_hash: Mapped[str] = mapped_column(Text, nullable=False)
    vorige_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
