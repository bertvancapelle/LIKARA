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
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
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
    """ADR-046 besluit 2 — de BEDOELING van een component ("waar gaat het heen"):
    uitsluitend bestemmingen. `uitfaseren` is met migratie 0066 verwijderd (fase-taal →
    `Levensfase`); `onbekend` met migratie 0067 (LI040 — leegte-taal: een sentinel die
    als antwoord oogde; afwezigheid is nu écht NULL = "nog niet vastgelegd", identiek
    aan de levensfase). Beide via enum-recreate (precedent 0053)."""

    lift_and_shift = "lift_and_shift"
    herbouw = "herbouw"
    vervangen = "vervangen"
    gedeeld = "gedeeld"  # LI057 — hernoemd van `tijdelijk_gedeeld` (Slice 1); DB: ALTER TYPE RENAME VALUE


class Levensfase(str, Enum):
    """ADR-046 besluit 1 — de LEVENSFASE van een component: een feit over het component
    zelf ("het draait"), los van de bedoeling (`migratiepad`). Bewust een vaste set van
    drie (GEEN beheerbare catalogus): elke waarde draagt betekenis op de kaart en in de
    signalering — een vierde beheerder-waarde zou een woord zonder gedrag zijn. De kolom
    is nullable ZONDER default: ontbrekend = "nog niet vastgelegd" (leeg ≠ fout); LIKARA
    doet nooit zelf de uitspraak. Voedt de engine NIET (score blijft de enige
    lifecycle-driver)."""

    in_ontwikkeling = "in_ontwikkeling"
    in_productie = "in_productie"
    uitfaseren = "uitfaseren"


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
    # ADR-042 slice 1 — procesregister (business process). Nestbaar via een ouder-self-FK
    # op de subtabel; de plek in de boom ís het niveau (geen niveau-label).
    proces = "proces"
    # ADR-043 gate 1a — bedrijfsfunctie-as (business function): de logische ruggengraat
    # van de kaart. Nestbaar via een ouder-self-FK (proces-recept); topgroeperingen
    # (Besturend/Primair/Ondersteunend) zijn gewone wortelknopen (besluit LI039-4).
    bedrijfsfunctie = "bedrijfsfunctie"


class PartijAard(str, Enum):
    """ADR-024 — aard van een partij (discriminator op de `partij`-subtabel). Slice 1
    gebruikt alleen `externe_partij`; de overige aarden zijn structureel voorzien maar
    nog niet gerealiseerd. Geen combinatie-/businessregels — alleen geldigheid."""

    externe_partij = "externe_partij"
    organisatie = "organisatie"
    organisatie_eenheid = "organisatie_eenheid"
    persoon = "persoon"
    # ADR-038 — de aparte `burger`-aard is verwijderd: burger-doelgroepen zijn gewone externe
    # organisaties (`aard=organisatie` + `scope=extern`) met afdelingen eronder.


class PartijScope(str, Enum):
    """ADR-038 — intern/extern-kenmerk op een partij ("onze organisatie" vs. "erbuiten").

    Alleen betekenisvol op `aard=organisatie` (wijzigbaar) en `aard=externe_partij` (vast
    `extern`). Afdeling (`organisatie_eenheid`) en persoon dragen het NIET zelf — ze leiden het
    read-side af van hun ouder-organisatie (kolom NULL). Zo is een tegenstrijdige toestand
    (interne afdeling onder externe organisatie) structureel onmogelijk. Registratie-attribuut —
    voedt de engine/score/blokkade nooit."""

    intern = "intern"
    extern = "extern"


# Gedeelde sa.Enum-typeobjecten (één type per naam; migratie beheert de DDL).
# `create_type=False`: de ORM emit nooit zelf CREATE TYPE — de migratie doet dat.
hostingmodel_enum = sa.Enum(HostingModel, name="hostingmodel_enum")
lifecycle_status_enum = sa.Enum(LifecycleStatus, name="lifecycle_status_enum")
niveau_enum = sa.Enum(NiveauEnum, name="niveau_enum")
migratiepad_enum = sa.Enum(Migratiepad, name="migratiepad_enum")
levensfase_enum = sa.Enum(Levensfase, name="levensfase_enum")
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
partij_scope_enum = sa.Enum(PartijScope, name="partij_scope_enum")


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
        # ADR-023a — uniciteit per (bron,doel,type) blijft voor alle relatietypen BEHALVE flow:
        # tussen twee systemen mogen meerdere flow-koppelingen bestaan (eigen protocol/functie).
        # Partiële unieke index (WHERE relatietype <> 'flow'); zie migratie 0039.
        Index(
            "uq_relatie", "tenant_id", "bron_id", "doel_id", "relatietype",
            unique=True, postgresql_where=text("relatietype <> 'flow'"),
        ),
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
    # ADR-023a — identificerende, sorteerbare naam van een koppeling. DB-nullable; app-verplicht
    # voor flow volgt in Fase 2 (hier nog geen validatie).
    naam: Mapped[str | None] = mapped_column(String(150), nullable=True)
    kenmerken: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    omschrijving: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ADR-023a — markering dat een KOPPELING_DUBBEL-waarschuwing bij aanmaak bewust is overruled
    # (alleen flow). Audit-native: de diff-capture neemt deze mapped column automatisch mee.
    dubbel_waarschuwing_genegeerd: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=text("false")
    )


class Component(Base, TenantMixin, TimestampMixin):
    """ADR-021 — knooppunt van de landschapsgraaf. ADR-023: subtype van `element`
    (shared-PK via composiet-FK `(tenant_id, id)` → `element`; cross-tenant uitgesloten).

    Draagt de technische identiteit (naam, type, hosting, eigenaarschap, leverancier).
    `componenttype` is een tekst-sleutel uit de componentcatalogus (dimensie
    `componenttype`); `applicatie` is daarin een beschermde systeem-sleutel (niet
    deactiveerbaar). Sinds LI059 draagt het GEEN eigen subtype-rij meer — een component
    met `componenttype='applicatie'` ÍS de applicatie (zie de noot onder deze class)."""

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
    # LI057 (Slice 1) — component-brede transitie-attributen: verhuisd van de applicatie-subtabel naar
    # het basis-component (élk componenttype), NOT NULL met defaults. De engine leest deze NIET
    # (lifecycle-driver blijft de score). De `applicatie`-subtabel houdt (voorlopig) spiegel-kolommen
    # tot de contract-slice; de service dual-writet zodat ze niet driften.
    # LI040 — de bedoeling is, net als de levensfase, NULLABLE zonder default (vormkeuze
    # B): ontbrekend = "nog niet vastgelegd" (leeg ≠ fout, wél vindbaar via het
    # ontbreekt-filter). De vroegere sentinel `onbekend` oogde als antwoord en is weg.
    migratiepad: Mapped[Migratiepad | None] = mapped_column(migratiepad_enum, nullable=True)
    # ADR-046 besluit 1 — levensfase: geregistreerd feit ("het draait"), NULLABLE zonder
    # default (vormkeuze B): een default zou LIKARA een uitspraak laten doen die niemand
    # deed. Ontbrekend toont als "nog niet vastgelegd". Puur registratief; engine leest
    # dit NIET (score blijft de enige lifecycle-driver).
    levensfase: Mapped[Levensfase | None] = mapped_column(levensfase_enum, nullable=True)
    # LI040 — complexiteit/prioriteit zijn OORDELEN: wie een waarde zet doet een
    # uitspraak; wie hem leeg laat heeft er nog niet naar gekeken. Daarom — net als
    # levensfase/bedoeling (migratie 0067-patroon) — NULLABLE zonder default: de
    # vroegere default `midden` was een verzonnen oordeel dat elk component ongevraagd
    # kreeg (en oogde als "iemand vond dit gemiddeld"). De enum-waarden zelf blijven
    # (midden is een geldig oordeel — het wordt alleen niet meer gratis uitgedeeld).
    complexiteit: Mapped[NiveauEnum | None] = mapped_column(niveau_enum, nullable=True)
    prioriteit: Mapped[NiveauEnum | None] = mapped_column(niveau_enum, nullable=True)
    # ADR-028 — componentclassificatie (puur registratief; engine onaangeroerd). `componentrol`
    # is een tekst-sleutel uit `componentrol_optie`, NOT NULL met server_default `interne_applicatie`
    # (elk component heeft altijd een rol; geen lege staat, geen rol-registratiegat). De drie
    # BIV-velden zijn tekst-sleutels uit `biv_schaal_optie`, nullable (optioneel; leeg = het
    # registratiegat dat de signalering zichtbaar maakt). App-side gevalideerd tegen de actieve
    # catalogus (zoals `componenttype`).
    componentrol: Mapped[str] = mapped_column(
        String(60), nullable=False, server_default=text("'interne_applicatie'")
    )
    biv_beschikbaarheid: Mapped[str | None] = mapped_column(String(60), nullable=True)
    biv_integriteit: Mapped[str | None] = mapped_column(String(60), nullable=True)
    biv_vertrouwelijkheid: Mapped[str | None] = mapped_column(String(60), nullable=True)


# LI059 (Slice 3) — de `Applicatie`-subtype-class is opgeheven (migratie 0047). Een component
# met `componenttype='applicatie'` ÍS de applicatie (domeinmodel §9-7: een subtype zonder
# type-eigen velden vervalt). De transitie-attributen leven op `Component` (LI057); de
# engine-state (`lifecycle_status`) op `ComponentProfiel`. `applicatie_service` is een dunne
# facade over `component` geworden; de oude `/applicaties`-API blijft byte-identiek.


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


class Organisatiegebruik(Base, TenantMixin, TimestampMixin):
    """ADR-036 — grof gebruiksfeit: "organisatie gebruikt applicatie".

    Eigen tenant-scoped registratie-feit (GEEN ArchiMate-element, dus geen element-subtype) —
    vorm identiek aan `roltoewijzing`. Eén feit per (organisatie, applicatie), schema-geborgd via
    `UNIQUE(tenant_id, organisatie_id, applicatie_id)`. Onvolledig = geldig: organisatie + applicatie
    volstaat, verder niets verplicht; LIKARA laat het staan en blokkeert niets. De gebruikersgroep
    is de fijne verfijning en verwijst hiernaar (`gebruikersgroep.gebruik_id`) — daarom óók
    `UNIQUE(tenant_id, id)` als composiet-FK-doel.

    `organisatie_id` → een partij met aard=organisatie (app-side geborgd via
    `partij_service.valideer_organisatie`); `applicatie_id` → een bestaand **component,
    élk componenttype** (ADR-041-herziening: het gebruik-slot is component-breed —
    app-side geborgd via `organisatiegebruik_service.valideer_component`; de kolomnaam
    is historisch). Beide composiet-FK's naar `element` (ON DELETE CASCADE: het feit
    verdwijnt met de organisatie of het component). Puur registratief — geen
    engine-koppeling. Tenant-scoped (FORCE RLS)."""

    __tablename__ = "organisatiegebruik"
    __table_args__ = (
        UniqueConstraint("tenant_id", "organisatie_id", "applicatie_id", name="uq_organisatiegebruik"),
        # Composiet-FK-doel voor gebruikersgroep.gebruik_id → (tenant_id, id).
        UniqueConstraint("tenant_id", "id", name="uq_organisatiegebruik_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "organisatie_id"], ["element.tenant_id", "element.id"],
            name="fk_organisatiegebruik_organisatie", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "applicatie_id"], ["element.tenant_id", "element.id"],
            name="fk_organisatiegebruik_applicatie", ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    organisatie_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    applicatie_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class Gebruikersgroep(Base, TenantMixin, TimestampMixin):
    """ADR-023 B-mig-1: subtype van `element` (shared-PK, ArchiMate business actor/role).

    ADR-036: de organisatie leeft niet langer als eigen kolom op de groep, maar op het grove
    gebruiksfeit `organisatiegebruik` waarnaar `gebruik_id` verwijst — **single source of truth**.
    Een groep is de fijne verfijning ván dat grove feit. ADR-038: `gebruik_id` is **verplicht**
    (NOT NULL) — een groep hoort altijd bij een organisatie; de org-loze uitzondering vervalt.
    De band met de applicatie blijft de `serving`-relatie (applicatie → gebruikersgroep)."""

    __tablename__ = "gebruikersgroep"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_gebruikersgroep_element", ondelete="CASCADE",
        ),
        # ADR-036/038 — verfijning-van het grove gebruiksfeit; `gebruik_id` is verplicht (NOT NULL,
        # geen org-loze groep meer). ON DELETE RESTRICT: een grof feit (en daarmee de organisatie)
        # met groepen verdwijnt niet stil — spiegel van `afdeling_id`. Vervangt de oude SET NULL,
        # die met NOT NULL zou botsen.
        ForeignKeyConstraint(
            ["tenant_id", "gebruik_id"], ["organisatiegebruik.tenant_id", "organisatiegebruik.id"],
            name="fk_gebruikersgroep_gebruik", ondelete="RESTRICT",
        ),
        # ADR-036a — afdeling structureel: verwijzing naar een `organisatie_eenheid`-partij (element),
        # spiegel van het persoon→afdeling-patroon (ADR-024). ON DELETE RESTRICT: een afdeling met
        # groepen verdwijnt niet stil. De aard/organisatie-consistentie (org-eenheid binnen de
        # grove-feit-organisatie) borgt de service.
        ForeignKeyConstraint(
            ["tenant_id", "afdeling_id"], ["element.tenant_id", "element.id"],
            name="fk_gebruikersgroep_afdeling", ondelete="RESTRICT",
        ),
    )

    # ADR-023 B-mig-2 slice 4: de band met de applicatie is een `serving`-relatie geworden.
    id: Mapped[uuid.UUID] = _pk()
    # ADR-036/038 — verwijzing naar het grove gebruiksfeit (de organisatie leeft daar). Verplicht:
    # een groep hoort altijd bij een organisatie (geen org-loze groep meer).
    gebruik_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # ADR-036a — afdeling als structurele referentie (organisatie_eenheid-partij); NULL = geen afdeling.
    afdeling_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
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


class Proces(Base, TenantMixin, TimestampMixin):
    """ADR-042 slice 1 — procesregister-element: wat de organisatie dóét, nestbaar van grof
    naar fijn (bedrijfsproces → werkproces → desgewenst processtap; de plek in de boom ís
    het niveau — geen niveau-label). Element-subtype (shared-PK via composiet-FK
    `(tenant_id, id)` → `element`, FORCE RLS via de migratie; cross-tenant uitgesloten).

    Type-eigen velden: `naam` (verplicht) + `toelichting` (plateau-spiegel). `ouder_id` is
    een **composiet self-FK** `(tenant_id, ouder_id)` → `proces(tenant_id, id)`
    (tenant-consistent) met **`ON DELETE RESTRICT`**: een proces met deelprocessen kan niet
    verwijderd worden (geen stilzwijgend wegvagen van de subboom — de service geeft 409
    `HEEFT_DEELPROCESSEN`; RESTRICT is de DB-backstop). Cycluspreventie (zelf-ouder +
    transitieve kring) zit in de servicelaag (work_package-recept); de DB-CHECK borgt
    alléén de directe self-parent als extra vangnet. Puur registratief — geen
    engine-koppeling (ADR-042-invariant: score blijft de enige lifecycle-driver)."""

    __tablename__ = "proces"
    __table_args__ = (
        # Composiet-FK-target voor de self-FK (tenant-consistent).
        UniqueConstraint("tenant_id", "id", name="uq_proces_tenant_id"),
        CheckConstraint(
            "ouder_id IS NULL OR ouder_id <> id",
            name="ck_proces_geen_self_parent",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_proces_element", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "ouder_id"], ["proces.tenant_id", "proces.id"],
            name="fk_proces_ouder", ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    toelichting: Mapped[str | None] = mapped_column(Text, nullable=True)
    ouder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class Procesvervulling(Base, TenantMixin, TimestampMixin):
    """ADR-042 slice 3 — koppelregel: "component X vervult applicatiefunctie Y in proces Z".

    Eigen tenant-scoped registratie-feit (GEEN ArchiMate-element) — het roltoewijzing-recept
    1-op-1: bewust los van het unified `relatie`-model, dat `UNIQUE(tenant,bron,doel,type)`
    afdwingt en daarmee "meerdere applicatiefuncties van hetzelfde component in hetzelfde
    proces als losse regels" onmogelijk maakt. Hier is de uniciteit exact het tripel
    `(tenant, component, proces, applicatiefunctie)`: dezelfde functie niet dubbel, maar wél
    meerdere functies per (component, proces) en meerdere componenten per proces.

    `component_id`/`proces_id` zijn composiet-FK's naar `element` (CASCADE: de regel
    verdwijnt met het component of het proces); dat het écht een component resp. proces is
    dwingt de service af (422). `applicatiefunctie` is een tekst-sleutel naar de
    `applicatiefunctie_optie`-catalogus (geen harde FK — sleutel stabiel,
    soft-deactiveerbaar; app-side gevalideerd op actief). Component-breed: élk
    componenttype is koppelbaar (ADR-042 besluit 3). Optionele `toelichting`
    (subknoop 2-default). Puur registratief — geen engine-koppeling. FORCE RLS."""

    __tablename__ = "procesvervulling"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "component_id", "proces_id", "applicatiefunctie",
            name="uq_procesvervulling",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "component_id"], ["element.tenant_id", "element.id"],
            name="fk_procesvervulling_component", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "proces_id"], ["element.tenant_id", "element.id"],
            name="fk_procesvervulling_proces", ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    proces_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    applicatiefunctie: Mapped[str] = mapped_column(String(60), nullable=False)
    toelichting: Mapped[str | None] = mapped_column(Text, nullable=True)


class FunctievervullingOordeel(str, Enum):
    """ADR-051 besluit 3 — oordeel over de KOPPELING (de plek), niet over het componenttype.
    Optioneel (besluit 4): leeg = "nog niet beoordeeld" (een eigen, vindbare stand — geen sentinel)."""
    naar_behoren = "naar_behoren"
    noodoplossing = "noodoplossing"


class Functievervulling(Base, TenantMixin, TimestampMixin):
    """ADR-049 (gate 2a) — koppelregel: "component X ondersteunt bedrijfsfunctie Y".

    Het procesvervulling-recept, mét één verschil: de as is KAAL — géén applicatiefunctie,
    géén werkwoord (dat blijft bij het proces). Het anker is het ADRES van de plek, niet
    `relatie.id` (ADR-049 besluit 2): `functie_id` = de ondersteunde functie, `ouder_functie_id`
    = onder welke functie ze staat. Leeg adres (`ouder_functie_id IS NULL`) = GROF ("nog niet
    nagevraagd wáár precies"); gevuld = FIJN (déze plek). Eén soort registratie, plek optioneel
    (ADR-049 besluit 3).

    Uniciteit structureel in TWEE partiële vormen — Postgres telt NULL als *distinct*, dus een
    gewone `UNIQUE(..., ouder_functie_id)` zou onbeperkt grove dubbelen toelaten:
    - `uq_functievervulling_grof`  : één grove per (component, functie)      WHERE ouder NULL;
    - `uq_functievervulling_fijn`  : één fijne per (component, functie, plek) WHERE ouder NOT NULL.
    Meerdere componenten per plek is normaal (ander `component_id` botst niet).

    Drie composiet-FK's → `element` (CASCADE): het component, de functie én de ouder-functie
    (nullable). Dat het écht een component/bedrijfsfunctie is, en dat de plek bestaat, dwingt de
    service af (422). Optionele `toelichting`; server-stamped `verklaard_door_sub`/`verklaard_door`
    (wie), `created_at` (wanneer). Puur registratief — géén engine-koppeling. FORCE RLS.
    De leesregel "fijn verdringt grof" wordt NIET opgeslagen; ze leeft één keer in de service
    (`dekking_overzicht`) als leeslaag (ADR-049 besluit 1/5)."""

    __tablename__ = "functievervulling"
    __table_args__ = (
        # Component-koppelingen: uniek per (component, functie[, plek]). `component_id IS NOT NULL`
        # in de WHERE zodat de geen-systeem-rijen (component_id NULL) hier buiten vallen.
        Index(
            "uq_functievervulling_grof", "tenant_id", "component_id", "functie_id",
            unique=True, postgresql_where=text("ouder_functie_id IS NULL AND component_id IS NOT NULL"),
        ),
        Index(
            "uq_functievervulling_fijn", "tenant_id", "component_id", "functie_id", "ouder_functie_id",
            unique=True, postgresql_where=text("ouder_functie_id IS NOT NULL AND component_id IS NOT NULL"),
        ),
        # ADR-051 — "hier draait niets — vastgesteld": hoogstens ÉÉN geen-systeem-bevinding per plek.
        # De component-indexen vangen deze niet (component_id NULL → NULL-distinct), dus eigen partiële
        # indexen — hetzelfde NULL-distinct-gat als bij gate 2a, nu voor de geen-systeem-kant.
        Index(
            "uq_functievervulling_geen_grof", "tenant_id", "functie_id",
            unique=True, postgresql_where=text("ouder_functie_id IS NULL AND geen_systeem"),
        ),
        Index(
            "uq_functievervulling_geen_fijn", "tenant_id", "functie_id", "ouder_functie_id",
            unique=True, postgresql_where=text("ouder_functie_id IS NOT NULL AND geen_systeem"),
        ),
        Index("ix_functievervulling_tenant_functie", "tenant_id", "functie_id"),
        Index("ix_functievervulling_tenant_component", "tenant_id", "component_id"),
        # ADR-051 besluit 2 — precies ÉÉN van beide: een component óf de uitkomst "geen systeem".
        # Nooit geen van beide, nooit allebei (XOR). Structureel, niet in de servicelaag.
        CheckConstraint(
            "(component_id IS NOT NULL) <> geen_systeem",
            name="ck_functievervulling_component_xor_geen",
        ),
        # ADR-051 besluit 3/4 — een oordeel hoort bij een component-koppeling; op "geen systeem"
        # is het betekenisloos en mag het niet staan.
        CheckConstraint(
            "oordeel IS NULL OR geen_systeem = false",
            name="ck_functievervulling_oordeel_alleen_component",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "component_id"], ["element.tenant_id", "element.id"],
            name="fk_functievervulling_component", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "functie_id"], ["element.tenant_id", "element.id"],
            name="fk_functievervulling_functie", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "ouder_functie_id"], ["element.tenant_id", "element.id"],
            name="fk_functievervulling_ouder", ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    # ADR-051 besluit 2 — nullable: een geen-systeem-bevinding draagt géén component (XOR-CHECK).
    component_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    functie_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ouder_functie_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # ADR-051 besluit 2 — de uitkomst "hier draait geen systeem — vastgesteld" (een bevinding,
    # geen ontbrekende registratie). Precies-één-van-beide met `component_id` via de XOR-CHECK.
    geen_systeem: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=text("false"))
    # ADR-051 besluit 3/4 — oordeel over de koppeling (optioneel; leeg = nog niet beoordeeld).
    oordeel: Mapped[FunctievervullingOordeel | None] = mapped_column(
        sa.Enum(FunctievervullingOordeel, name="functievervulling_oordeel_enum"), nullable=True,
    )
    toelichting: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ADR-049 punt 2 — wie/wanneer, server-stamped (nooit uit de payload). `sub` = stabiele
    # actor-sleutel (naam-resolutie via ADR-029), `verklaard_door` = e-mail-fallback; `created_at`
    # (TimestampMixin) is het "wanneer".
    verklaard_door_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verklaard_door: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Referentiemodel(Base, TenantMixin, TimestampMixin):
    """ADR-043 gate 1a — de INGELEZEN referentiemodel-instantie van déze tenant (wélk
    model, welke versie, wanneer ingelezen). Tenant-scoped registratie-feit (FORCE RLS
    via de migratie) — GEEN ArchiMate-element, dus geen element-subtype.

    Twee lagen (besluit LI039-5): het AANBOD is platform-gecureerd
    (`referentiemodel_optie`, platform-catalogus); het INLEZEN doet de tenant-beheerder
    en de ingelezen inhoud ís het landschap van de gemeente (tenant-tabel).
    `model_sleutel` verwijst app-side naar `referentiemodel_optie.optie_sleutel` (geen
    harde FK — catalogus-conventie); `naam`/`versie` zijn de ingelezen snapshot.
    `UNIQUE(tenant_id, model_sleutel)`: een herinlees wérkt de bestaande instantie bij
    (versie), er ontstaat geen tweede rij per model. Engine onaangeroerd."""

    __tablename__ = "referentiemodel"
    __table_args__ = (
        # Composiet-FK-target voor `bedrijfsfunctie.bron_model_id` (tenant-consistent).
        UniqueConstraint("tenant_id", "id", name="uq_referentiemodel_tenant_id"),
        UniqueConstraint("tenant_id", "model_sleutel", name="uq_referentiemodel_sleutel"),
    )

    id: Mapped[uuid.UUID] = _pk()
    model_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)
    naam: Mapped[str] = mapped_column(String(150), nullable=False)
    versie: Mapped[str] = mapped_column(String(60), nullable=False)
    ingelezen_op: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    # Gate 1b-afronding — de inlees heeft een BEGIN en een EIND, en het verschil is
    # zichtbaar: `voer_uit` zet de vlag op False vóór de eerste schrijfactie en pas op
    # True ná de laatste (incl. de vervallen-markering). False = een afgebroken inlees:
    # het model staat er mogelijk half en vervallen functies kunnen nog als geldig
    # getoond worden — het scherm meldt dat eerlijk ("niets landt stil"). Een ECHTE
    # kolom (geen jsonb/afgeleide) zodat de audit de omslag per import naspeurbaar
    # capture't (het `dubbel_waarschuwing_genegeerd`-precedent, DC016). Migratie 0064.
    inlees_voltooid: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=text("true")
    )


class Bedrijfsfunctie(Base, TenantMixin, TimestampMixin):
    """ADR-043 gate 1a / ADR-044 gate 1a-bis — bedrijfsfunctie-element: de logische
    ruggengraat van de kaart (wat de organisatie hóórt te doen — GEMMA
    Basisarchitectuur). Element-subtype (shared-PK via composiet-FK `(tenant_id, id)` →
    `element`, FORCE RLS via de migratie), plus de ADR-043-eigen velden:

    - **Herkomst** (`bron_model_id` + `bron_sleutel`): beide gezet = modelinhoud (naam/
      definitie/plaatsing read-only, bijgewerkt door een herinlees op de bronsleutel —
      nooit op naam); beide leeg = eigen functie van de gemeente (een import raakt haar
      nooit aan). Samen-gezet-of-samen-leeg is een CHECK (harde invariant → schema);
      `UNIQUE(tenant_id, bron_model_id, bron_sleutel)` dwingt uniciteit alléén op
      niet-NULL af (NULL is distinct — het `checklistvraag.betekenis`-precedent).
    - **`vervallen`** (besluit LI039-6): "bestaat niet meer in het ingelezen model" —
      zichtbaar blijven mét markering, NIET meer koppelbaar; nooit hard verwijderen.

    **ADR-044 — de boom is GEEN kolom meer.** De vroegere `ouder_id`-self-FK is
    verwijderd (migratie 0063): de plaatsing ("functie hoort onder functie") is een
    eerste-klas feit, gedragen door **`aggregation`-relaties** (bron = ouder/geheel,
    doel = kind/deel) in het unified relatiemodel, via de dunne facade in
    `bedrijfsfunctie_service` (plateau-spiegel). Eén functie kan daardoor op MEERDERE
    plekken staan (GEMMA: 7 functies met 2–4 ouders); `UNIQUE(tenant, bron, doel, type)`
    borgt precies één plaatsing per (ouder, functie)-paar. Cycluspreventie blijft
    servicelaag. Puur registratief — geen engine-koppeling (score blijft de enige
    lifecycle-driver)."""

    __tablename__ = "bedrijfsfunctie"
    __table_args__ = (
        # Composiet-FK-target (tenant-consistent; o.a. voor toekomstige verfijnings-ankers).
        UniqueConstraint("tenant_id", "id", name="uq_bedrijfsfunctie_tenant_id"),
        # Bronsleutel = identiteit binnen één ingelezen model; NULL distinct ⇒ onbeperkt
        # veel eigen functies (geen partial index nodig — betekenis-precedent).
        UniqueConstraint(
            "tenant_id", "bron_model_id", "bron_sleutel", name="uq_bedrijfsfunctie_bron"
        ),
        # Herkomst is een paar: model + sleutel samen gezet, of samen leeg (eigen functie).
        CheckConstraint(
            "(bron_model_id IS NULL) = (bron_sleutel IS NULL)",
            name="ck_bedrijfsfunctie_bron_paar",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "id"], ["element.tenant_id", "element.id"],
            name="fk_bedrijfsfunctie_element", ondelete="CASCADE",
        ),
        # Een ingelezen model met functies verdwijnt niet stil (geen delete-endpoint;
        # RESTRICT is de backstop — een vervallen model blijft resolvebaar).
        ForeignKeyConstraint(
            ["tenant_id", "bron_model_id"],
            ["referentiemodel.tenant_id", "referentiemodel.id"],
            name="fk_bedrijfsfunctie_bron_model", ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    definitie: Mapped[str | None] = mapped_column(Text, nullable=True)
    bron_model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    bron_sleutel: Mapped[str | None] = mapped_column(String(120), nullable=True)
    vervallen: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=text("false")
    )


# ADR-023 B-mig-2 slice 1: het `Koppeling`-model is vervangen door `flow`-relaties in het
# unified relatiemodel (`Relatie`). De enums Koppelrichting/Koppelprotocol/ImpactVerbreking
# blijven — ze typeren nu de flow-kenmerken (richting/protocol/impact_bij_verbreking).


# ADR-023 B-mig-2 slice 2: `ComponentStructuur` is vervangen door `assignment`/`aggregation`-
# relaties in het unified relatiemodel (`Relatie`). De catalogus-dimensie `structuurrelatie_type`
# blijft historisch staan (labels resolvebaar); nieuwe structuurrelaties zijn ArchiMate-relaties.


class ChecklistCategorie(Base, TenantMixin):
    """ADR-022 W3 / LI050 — de checklist-categorie als eigen tenant-entiteit (RLS + FORCE).

    Vóór LI050 bestond een categorie niet: elke vraag droeg zelf `categorie_nr` +
    `categorie_naam` (gedenormaliseerd), waardoor hernoemen tot 89 losse bewerkingen
    kostte en twee vragen ongemerkt hetzelfde nummer met een andere naam konden dragen.
    Nu: één rij per categorie, per componenttype; de vraag verwijst (`categorie_id`).
    - Identiteit = **naam** binnen `(tenant, componenttype)` (schema-afgedwongen);
      `volgorde` is puur presentatievolgorde, geen betekenis en geen identiteit.
    - `UNIQUE(tenant_id, id)` is het composiet-FK-target voor `checklistvraag`.
    - Verwijderen met vragen eronder wordt geweigerd (service 409 + telling); de
      RESTRICT-FK op de vraag is de schema-backstop."""

    __tablename__ = "checklist_categorie"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "componenttype", "naam", name="uq_checklist_categorie_naam"
        ),
        UniqueConstraint("tenant_id", "id", name="uq_checklist_categorie_tenant_id"),
    )

    id: Mapped[uuid.UUID] = _pk()
    componenttype: Mapped[str] = mapped_column(String(60), nullable=False)
    naam: Mapped[str] = mapped_column(String(120), nullable=False)
    volgorde: Mapped[int] = mapped_column(Integer, nullable=False)


class ChecklistVraag(Base, TenantMixin):
    """ADR-022 Wijziging W1 — **tenant-scoped** vragenset (RLS + FORCE), eigendom van
    de tenant. Surrogate UUID-PK (`id`), `componenttype`-discriminator (één vraag →
    één componenttype; app-side gevalideerd tegen de componentcatalogus). Identiteit:
    `UNIQUE(tenant_id, componenttype, code)`. `actief` (default true): "verwijderen" =
    soft-deactivatie — een inactieve vraag valt uit de actieve set én uit `aantal_vragen`,
    bestaande scores blijven historie. `UNIQUE(tenant_id, id)` is het composiet-FK-target
    voor de kind-FK's (Knoop 1). LI050 (W3): de categorie is een verwijzing
    (`categorie_id` → `checklist_categorie`, RESTRICT); de oude gedenormaliseerde
    `categorie_nr`/`categorie_naam`-kolommen zijn vervallen. LI050 (W4): de code is
    INTERN — systeem-toegekend bij aanmaken, nergens meer op het scherm; hij blijft
    het stabiele markeer-anker (deeplink) en de standaardvolgorde binnen een categorie."""

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
        # LI050: tenant-consistente verwijzing naar de categorie; RESTRICT = een categorie
        # met vragen kan structureel niet verdwijnen (de service-409 is de nette melding).
        ForeignKeyConstraint(
            ["tenant_id", "categorie_id"],
            ["checklist_categorie.tenant_id", "checklist_categorie.id"],
            name="fk_checklistvraag_categorie",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    componenttype: Mapped[str] = mapped_column(String(60), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    categorie_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # LI050 (W5): eigen volgorde binnen de categorie — de gebruiker sleept; de code is
    # louter identiteit en draagt geen positie meer. Nieuwe vraag = achteraan (service).
    volgorde: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
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
        # ADR-037 — verantwoordelijke per antwoord (vervangt het vrije-tekstveld `eigenaar`):
        # composiet-FK naar een partij-element (aard organisatie_eenheid/persoon, app-side geborgd).
        # Optioneel; ON DELETE SET NULL (kolom-specifiek op verantwoordelijke_id in de migratie —
        # een kale SET NULL zou óók de gedeelde tenant_id nullen). Spiegel van
        # `component.eigenaar_organisatie_id`. Puur registratief: de engine leest dit NOOIT.
        ForeignKeyConstraint(
            ["tenant_id", "verantwoordelijke_id"], ["element.tenant_id", "element.id"],
            name="fk_checklistscore_verantwoordelijke", ondelete="SET NULL",
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
    # ADR-037 — verantwoordelijke (afdeling-dan-persoon) via composiet-FK (zie __table_args__).
    verantwoordelijke_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
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
    # ADR-037 — de blokkade-eigenaar is niet langer een eigen (vrije-tekst) veld: hij wordt in de
    # leeslaag AFGELEID van de verantwoordelijke van het onderliggende antwoord
    # (`checklistscore_id` → `Checklistscore.verantwoordelijke_id`). Geen kolom, geen schrijfpad.
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
        # Aanspreekpunt (ADR-039 voorgesteld) — een organisatie/externe partij verwijst optioneel
        # naar een persoon-partij die bij háár hoort (persoon.organisatie_id == deze partij; app-side
        # geborgd). Composiet-FK naar het partij-element; ON DELETE SET NULL (kolom-specifiek op
        # contactpersoon_id in de migratie — een kale SET NULL zou óók de gedeelde tenant_id nullen).
        # Spiegel van `component.eigenaar_organisatie_id`. Puur registratief: de engine leest dit NOOIT.
        ForeignKeyConstraint(
            ["tenant_id", "contactpersoon_id"], ["element.tenant_id", "element.id"],
            name="fk_partij_contactpersoon", ondelete="SET NULL",
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
        # ADR-038 — intern/extern-kenmerk: exact gezet voor organisatie + externe_partij, NULL voor
        # afdeling/persoon (die leiden af van hun ouder-organisatie → geen tegenstrijdige toestand).
        CheckConstraint(
            "(aard IN ('organisatie', 'externe_partij')) = (scope IS NOT NULL)",
            name="ck_partij_scope_aanwezig",
        ),
        # Een externe partij kan nooit intern zijn (vast op extern).
        CheckConstraint(
            "aard <> 'externe_partij' OR scope = 'extern'",
            name="ck_partij_externe_partij_extern",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    aard: Mapped[PartijAard] = mapped_column(partij_aard_enum, nullable=False)
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    straat_huisnummer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postcode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plaats: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    # ADR-039 — aanspreekpunt: verwijzing naar een persoon-partij die bij deze partij
    # hoort (alleen op organisatie/externe_partij; service dwingt af). Zie __table_args__ voor de FK.
    contactpersoon_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # ADR-038 — intern/extern-kenmerk. Nullable op tabelniveau; de CHECK
    # `ck_partij_scope_aanwezig` maakt hem verplicht voor organisatie + externe_partij en verbiedt
    # hem voor afdeling/persoon (die leiden af). Default (organisatie) = extern, in de service gezet.
    scope: Mapped[PartijScope | None] = mapped_column(partij_scope_enum, nullable=True)


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


class ComponentrolOptie(Base):
    """ADR-028 — platform-brede componentrol-catalogus (GEEN RLS, GEEN tenant_id). Enkel-doel
    (geen dimensie-discriminator), spiegel van `partijsoort_optie`. De rol is een instance-
    eigenschap op het component (intern / interne-dataprovider / externe-dataprovider /
    koppelvlak) — puur registratief, voedt de engine NIET. `interne_applicatie` is de beschermde
    systeem-sleutel (default; niet deactiveerbaar). Grants/soft-deactivate identiek aan
    `partijsoort_optie`."""

    __tablename__ = "componentrol_optie"
    __table_args__ = (
        UniqueConstraint("optie_sleutel", name="uq_componentrol_optie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    optie_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    volgorde: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    actief: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=text("true"))


class BivSchaalOptie(Base):
    """ADR-028 — platform-brede BIV-schaal-catalogus (GEEN RLS, GEEN tenant_id). Enkel-doel,
    spiegel van `partijsoort_optie`. ORDINALE schaal: `volgorde` is de rangdrager (laag<midden<
    hoog) zodat "hoog en hoger"-filtering op `volgorde` klopt — géén apart rangnummer. Draagt de
    drie BIV-velden (beschikbaarheid/integriteit/vertrouwelijkheid) op het component; puur
    registratief, voedt de engine NIET. Geen systeem-sleutel (elke optie deactiveerbaar)."""

    __tablename__ = "biv_schaal_optie"
    __table_args__ = (
        UniqueConstraint("optie_sleutel", name="uq_biv_schaal_optie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    optie_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    volgorde: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    actief: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=text("true"))


class ApplicatiefunctieOptie(Base):
    """ADR-042 slice 2 — platform-brede applicatiefunctie-catalogus (GEEN RLS, GEEN
    tenant_id). Enkel-doel, spiegel van `componentrol_optie`. De applicatiefunctie is het
    wát-veld op de koppelregel component→proces ("Zaaksysteem vervult *zaken registreren*
    in *Vergunningverlening*") — bewust de lichte catalogusvorm i.p.v. een eigen
    ArchiMate-element (gemarkeerde deviatie, ADR-042 besluit 3). GEMMA-geënte startset,
    vrij uitbreidbaar; GEEN systeem-sleutel (alles deactiveerbaar). Grants/soft-deactivate
    identiek aan `componentrol_optie`. Voedt de engine NIET."""

    __tablename__ = "applicatiefunctie_optie"
    __table_args__ = (
        UniqueConstraint("optie_sleutel", name="uq_applicatiefunctie_optie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    optie_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    volgorde: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    actief: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=text("true"))


class ReferentiemodelOptie(Base):
    """ADR-043 gate 1a — platform-gecureerd AANBOD van referentiemodellen (GEEN RLS, GEEN
    tenant_id): welke modellen LIKARA aanbiedt (naam, herkomst, versie). Het
    catalogus-recept (`applicatiefunctie_optie`-spiegel) met twee model-eigen kolommen
    (`herkomst`, `versie`). Soft-deactivate via `actief` (geen DELETE-grant/-endpoint);
    grants lk_app SELECT-only, lk_platform S/I/U. De TENANT-zijde (wélk model is
    ingelezen) is de aparte `referentiemodel`-tabel — besluit LI039-5: aanbod =
    platform, ingelezen inhoud = tenant. Voedt de engine NIET."""

    __tablename__ = "referentiemodel_optie"
    __table_args__ = (
        UniqueConstraint("optie_sleutel", name="uq_referentiemodel_optie"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    optie_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    herkomst: Mapped[str] = mapped_column(String(255), nullable=False)
    versie: Mapped[str] = mapped_column(String(60), nullable=False)
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
    ontstaat bij gebruiker-aanmaak via LIKARA (sub uit de Keycloak Admin API). Puur registratief —
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


class GebruikerVoorkeur(Base, TenantMixin, TimestampMixin):
    """ADR-041 slice 1 — persoonlijke, herroepbare gebruikersvoorkeur ("onthoud als mijn standaard").

    Generieke, tenant-scoped key/value-laag (FORCE RLS): één rij per `(tenant, sub, voorkeur_sleutel)`.
    De sleutel is de Keycloak-`sub` (server-side gestempeld via `huidige_actor()`, NOOIT client-
    aanleverbaar — spiegel van `ImpactView.maker_sub`); `waarde` is een klein JSON-blob. Deze laag kent
    de BETEKENIS van een voorkeur niet — semantische validatie (welke waarde geldig is) hoort bij de
    consument (slice 2); hier alleen een vorm-/grootte-guard op het blob.

    Persoonlijk, nooit gedeeld: een gebruiker leest/schrijft uitsluitend zijn eigen voorkeuren (RLS =
    tenant-grens; de `sub`-eigen-scope zit in de servicelaag). Puur registratie/weergave — RAAKT DE
    ENGINE NOOIT: importeert géén `lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/
    `ComponentProfiel`/`Blokkade`/`Checklistscore` en raakt geen lifecycle-/score-/blokkade-state."""

    __tablename__ = "gebruiker_voorkeur"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sub", "voorkeur_sleutel", name="uq_gebruiker_voorkeur_sub_sleutel"),
    )

    id: Mapped[uuid.UUID] = _pk()
    sub: Mapped[str] = mapped_column(String(255), nullable=False)
    voorkeur_sleutel: Mapped[str] = mapped_column(String(100), nullable=False)
    waarde: Mapped[dict] = mapped_column(JSONB, nullable=False)


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
    # ADR-052 slice 3 — bevroren snapshot: de verplichte norm-feiten die op het moment van klaar
    # verklaren NIET vastgesteld waren (server-berekend uit `component_norm_service.norm_status`).
    # Leeg = geen afwijking. `verklaard_op` = de peildatum. Echte kolom → de audit vangt de omslag
    # (het auditeerbare wilsbesluit "kreeg deze open feiten voorgelegd en verklaarde toch klaar").
    open_feiten: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )


class ComponentNorm(Base, TenantMixin, TimestampMixin):
    """ADR-052 slice 1 — tenant-norm voor harde componentfeiten.

    Per hard feit (`feit_sleutel`, uit de code-eigen kiesbare set `HARDE_FEITEN` in
    `component_norm_service`) legt de tenant vast of het feit **bekend moet zijn** voordat een
    component migratieklaar verklaard mag worden — MVP: alleen ja/nee (`verplicht`), geen weging.
    Eén rij per `(tenant_id, feit_sleutel)`. Tenant-eigen governance-configuratie (geen
    per-component registratie): tenant-scoped, RLS + FORCE.

    De norm is een LAT, geen poort: ze gatet uitsluitend de menselijke klaarverklaring (ADR-027,
    al engine-gescheiden) en RAAKT DE ENGINE NOOIT — geen import van/schrijf naar
    `lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/
    `Checklistscore`. De engine-status `migratieklaar` blijft puur checklist-gedreven."""

    __tablename__ = "component_norm"
    __table_args__ = (
        UniqueConstraint("tenant_id", "feit_sleutel", name="uq_component_norm_feit"),
    )

    id: Mapped[uuid.UUID] = _pk()
    feit_sleutel: Mapped[str] = mapped_column(String(60), nullable=False)
    verplicht: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=text("false"))


class ComponentBevindingSoort(str, Enum):
    """ADR-052 slice 2 — waarvoor een "bewust geen"-bevinding op een component geldt."""

    koppelingen = "koppelingen"
    contract = "contract"


component_bevinding_soort_enum = sa.Enum(
    ComponentBevindingSoort, name="component_bevinding_soort_enum"
)


class ComponentBevinding(Base, TenantMixin, TimestampMixin):
    """ADR-052 slice 2 — "bewust geen"-bevinding op een component (koppelingen / contract).

    Een uitspreekbare BEVINDING: "vastgesteld — dit component heeft er geen." Streng onderscheiden
    van "nog nooit naar gekeken" (= geen rij). Component-verankerd (spiegel van de bedrijfsfunctie-
    "bewust niets", ADR-044/049, die plek-verankerd in `functievervulling.geen_systeem` leeft) —
    zelfde VORM (registratiefeit: wie/wanneer/toelichting, intrekbaar, XOR met de echte registratie),
    eigen tabel omdat het anker het component is i.p.v. een functie-plek.

    Eén bevinding per (component, soort): `UNIQUE(tenant_id, component_id, soort)`. `component_id` is
    een composiet-FK `(tenant_id, component_id) → element(tenant_id, id)` ON DELETE CASCADE (zelfde
    vorm als roltoewijzing/klaarverklaring). Herroepbaar (intrekken = de rij verwijderen).

    Puur registratief — RAAKT DE ENGINE NOOIT: importeert géén `lifecycle_service`/
    `herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/`Checklistscore`."""

    __tablename__ = "component_bevinding"
    __table_args__ = (
        UniqueConstraint("tenant_id", "component_id", "soort", name="uq_component_bevinding"),
        ForeignKeyConstraint(
            ["tenant_id", "component_id"], ["element.tenant_id", "element.id"],
            name="fk_component_bevinding_component", ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    soort: Mapped[ComponentBevindingSoort] = mapped_column(
        component_bevinding_soort_enum, nullable=False
    )
    # ADR-029-lijn: stabiele actor-sleutel (Keycloak-sub) + e-mail-fallback, server-gestempeld.
    verklaard_door_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verklaard_door: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verklaard_op: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    toelichting: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImpactView(Base, TenantMixin, TimestampMixin):
    """ADR-033 slice 2 — opgeslagen Impact-verkenner-view (bewaarde startselectie).

    Eigen tenant-scoped registratie-feit (GEEN element-subtype): een naam + de componenten die op het
    moment van opslaan in de actieve set zaten (via de junctie `impact_view_component`). De
    drill-down-staat wordt NIET bewaard — een view is een startpunt, geen bevroren verkenning.
    `gedeeld=false` = privé (alleen de maker ziet 'm); `gedeeld=true` = zichtbaar voor de hele tenant,
    maar bewerken/verwijderen blijft aan de maker (servicelaag-guard bovenop RLS). De maker is de
    stabiele Keycloak-`sub` (`maker_sub`) + e-mail-fallback (`maker_email`), server-side gestempeld —
    nooit client-aanleverbaar.

    `UNIQUE(tenant_id, id)` maakt de composiet-FK vanuit de junctie mogelijk (zelfde vorm als de
    work_package self-FK); `UNIQUE(tenant_id, maker_sub, naam)` verbiedt twee gelijknamige views per
    maker. Puur registratief — RAAKT DE ENGINE NOOIT: importeert géén `lifecycle_service`/
    `herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/`Checklistscore`."""

    __tablename__ = "impact_view"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_impact_view_tenant_id"),
        UniqueConstraint("tenant_id", "maker_sub", "naam", name="uq_impact_view_maker_naam"),
    )

    id: Mapped[uuid.UUID] = _pk()
    naam: Mapped[str] = mapped_column(String(150), nullable=False)
    maker_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    maker_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gedeeld: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=text("false"))


class ImpactViewComponent(Base, TenantMixin):
    """ADR-033 slice 2 — junctie: één component in de startselectie van een opgeslagen view.

    Twee composiet-FK's, beide ON DELETE CASCADE:
    - `(tenant_id, view_id) → impact_view(tenant_id, id)`: view verwijderd ⇒ selectie verdwijnt mee;
    - `(tenant_id, component_id) → element(tenant_id, id)`: component verwijderd ⇒ valt uit de selectie.
    `UNIQUE(tenant_id, view_id, component_id)` voorkomt dubbele opname. Geen TimestampMixin: een
    junctie-rij wordt niet gemuteerd (alleen ge-insert/ge-delete bij een selectie-wijziging)."""

    __tablename__ = "impact_view_component"
    __table_args__ = (
        UniqueConstraint("tenant_id", "view_id", "component_id", name="uq_impact_view_component"),
        ForeignKeyConstraint(
            ["tenant_id", "view_id"], ["impact_view.tenant_id", "impact_view.id"],
            name="fk_impact_view_component_view", ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "component_id"], ["element.tenant_id", "element.id"],
            name="fk_impact_view_component_element", ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    view_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


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


class ContractBandDekking(Base, TenantMixin, TimestampMixin):
    """ADR-030 — per-band (component↔contract) dekking, náást de contract-brede dekking
    (`ContractDekking`). Eén rij per (contract, component); `dekking_sleutels` (array) verwijst
    naar de actieve catalogus (dimensie `dekking`), app-side gevalideerd — geen harde FK (de
    catalogus is platform-referentiedata zonder tenant_id). Composiet-FK's naar `element`
    (contract + component zijn element-subtypes) met ON DELETE CASCADE."""

    __tablename__ = "contract_band_dekking"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "contract_id", "component_id", name="uq_contract_band_dekking"
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    component_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dekking_sleutels: Mapped[list[str]] = mapped_column(
        ARRAY(String(60)), nullable=False, server_default=text("'{}'")
    )


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
    # ADR-045 — markeert een `componenttype` als werkondersteunend (koppelbaar aan een
    # bedrijfsfunctie-plaatsing, gate 2). Enige bron; anders dan `checklist_dragend` is
    # de dimensie-binding hier SCHEMA-afgedwongen (CHECK, migratie 0065): buiten
    # dim=`componenttype` blijft de kolom structureel `false`. Registratief — geen engine.
    ondersteunt_werk: Mapped[bool] = mapped_column(
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
