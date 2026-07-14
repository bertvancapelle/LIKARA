"""Pydantic v2-schemas voor Component (ADR-021 Besluit 1/4/9).

`componenttype` is een tekst-sleutel (app-side gevalideerd tegen de actieve
componentcatalogus). Het type `applicatie` is beschermd: components met dat type
ontstaan/verdwijnen uitsluitend via het applicatie-pad (CD051). `eigenaar_organisatie`
is in de DB NOT NULL maar API-optioneel — de service defaultt None → "" voor kale infra.
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

from models.models import HostingModel, Levensfase, LifecycleStatus, Migratiepad, NiveauEnum
from schemas._validators import _optionele_tekst, _verplichte_tekst

# ADR-028 — de beschermde default-componentrol (systeem-sleutel in `componentrol_optie`).
_DEFAULT_ROL = "interne_applicatie"


class ComponentSorteerveld(str, Enum):
    """Allowlist van sorteerbare component-velden (ADR-017 B2). De drie subtype-
    kolommen zijn nullable (LEFT JOIN) → NULLS-LAST. `test_component_sort` borgt
    dat dit 1-op-1 synchroon loopt met `component_service._SORTEERBARE_KOLOMMEN`."""

    created_at = "created_at"
    naam = "naam"
    componenttype = "componenttype"
    eigenaar = "eigenaar"            # eigenaar_organisatie (tekst, alfabetisch)
    hostingmodel = "hostingmodel"   # enum-volgorde (PostgreSQL enum-definitievolgorde)
    complexiteit = "complexiteit"
    prioriteit = "prioriteit"
    levensfase = "levensfase"       # ADR-046 — nullable (NULLS-LAST via v2n)
    lifecycle_status = "lifecycle_status"


class ComponentStatusFilter(str, Enum):
    """Allowlist voor het `?status=`-filter (CD017) — de 4 reële lifecycle-statussen.
    LI059: verhuisd uit `schemas/applicatie.py` (facade-purge). De transiënte
    `checklist_compleet` (ADR-013 B4) ontbreekt bewust (wordt nooit opgeslagen).
    Onbekende waarde ⇒ 422 (API-rand); multi-select → `IN`-clause."""

    concept = "concept"
    in_inventarisatie = "in_inventarisatie"
    geblokkeerd = "geblokkeerd"
    migratieklaar = "migratieklaar"


class ComponentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str
    componenttype: str
    hostingmodel: HostingModel = HostingModel.onbekend
    # ADR-024 UX-B6-b — optionele verwijzing naar de eigenaar-organisatie (partij, aard=organisatie).
    eigenaar_organisatie_id: uuid.UUID | None = None
    beschrijving: str | None = None
    # LI057 (Slice 1) — component-brede transitie-attributen, met defaults (verplicht in de DB).
    migratiepad: Migratiepad = Migratiepad.onbekend
    # ADR-046 besluit 1 — levensfase (vormkeuze B): optioneel ZONDER default; weggelaten =
    # "nog niet vastgelegd" (LIKARA doet die uitspraak nooit zelf).
    levensfase: Levensfase | None = None
    complexiteit: NiveauEnum = NiveauEnum.midden
    prioriteit: NiveauEnum = NiveauEnum.midden
    # ADR-028 — componentclassificatie (app-side gevalideerd tegen de actieve catalogi in de
    # service). `componentrol` heeft de beschermde default; de drie BIV-velden zijn optioneel.
    componentrol: str = _DEFAULT_ROL
    biv_beschikbaarheid: str | None = None
    biv_integriteit: str | None = None
    biv_vertrouwelijkheid: str | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @field_validator("componenttype")
    @classmethod
    def _v_type(cls, v: str) -> str:
        return _verplichte_tekst(v, "componenttype", 60)

    @field_validator("componentrol")
    @classmethod
    def _v_rol(cls, v: str) -> str:
        return _verplichte_tekst(v, "componentrol", 60)

    @field_validator("biv_beschikbaarheid", "biv_integriteit", "biv_vertrouwelijkheid")
    @classmethod
    def _v_biv(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 60)


class ComponentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    componenttype: str | None = None
    hostingmodel: HostingModel | None = None
    eigenaar_organisatie_id: uuid.UUID | None = None
    beschrijving: str | None = None
    # LI057 (Slice 1) — component-brede transitie-attributen (PATCH: optioneel, niet expliciet null).
    migratiepad: Migratiepad | None = None
    # ADR-046 — levensfase mag wél expliciet op null (terug naar "nog niet vastgelegd":
    # een registratie moet corrigeerbaar zijn; exclude_unset onderscheidt weggelaten/null).
    levensfase: Levensfase | None = None
    complexiteit: NiveauEnum | None = None
    prioriteit: NiveauEnum | None = None
    # ADR-028 — componentclassificatie (PATCH). `componentrol` blijft NOT NULL: None = "niet
    # meegegeven" (ongewijzigd), nooit gewist. Een BIV-veld mag wél expliciet op null (registratiegat).
    componentrol: str | None = None
    biv_beschikbaarheid: str | None = None
    biv_integriteit: str | None = None
    biv_vertrouwelijkheid: str | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 255)

    @field_validator("componenttype")
    @classmethod
    def _v_type(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "componenttype", 60)

    @field_validator("componentrol")
    @classmethod
    def _v_rol(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "componentrol", 60)

    @field_validator("biv_beschikbaarheid", "biv_integriteit", "biv_vertrouwelijkheid")
    @classmethod
    def _v_biv(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 60)


class ComponentRead(BaseModel):
    id: uuid.UUID
    naam: str
    componenttype: str
    componenttype_label: str
    hostingmodel: HostingModel
    # ADR-024 UX-B6-b — eigenaar-organisatie als verwijzing + geresolveerde naam (read).
    eigenaar_organisatie_id: uuid.UUID | None = None
    eigenaar_organisatie_naam: str | None = None
    beschrijving: str | None
    # LI057 (Slice 1) — component-brede transitie-attributen (nu op élk component, NOT NULL).
    migratiepad: Migratiepad
    # ADR-046 — levensfase: null = "nog niet vastgelegd" (leeg ≠ fout, UI toont gedempt).
    levensfase: Levensfase | None = None
    complexiteit: NiveauEnum
    prioriteit: NiveauEnum
    # ADR-028 — componentclassificatie (registratief): rol (+ label) en de drie BIV-velden
    # (+ labels; null als niet geregistreerd). Labels resolven ook gedeactiveerde sleutels.
    componentrol: str
    rol_label: str
    biv_beschikbaarheid: str | None = None
    biv_beschikbaarheid_label: str | None = None
    biv_integriteit: str | None = None
    biv_integriteit_label: str | None = None
    biv_vertrouwelijkheid: str | None = None
    biv_vertrouwelijkheid_label: str | None = None
    heeft_applicatie_subtype: bool
    # ADR-023 Fase C: ArchiMate-typing uit de catalogus (read-only projectie) — laag-label
    # op het detail; null als het type geen mapping draagt.
    archimate_element: str | None = None
    laag: str | None = None
    # ADR-022 Fase E: of dit componenttype checklist-dragend is (UI toont dan de checklist).
    checklist_dragend: bool
    # ADR-022 Fase E: lifecycle uit het generieke profiel (null als geen profiel) —
    # voedt de status-indicator + "Start beoordeling"-knop (zichtbaar bij `concept`).
    lifecycle_status: LifecycleStatus | None = None
    # ADR-022 Fase C: capability-hint — het type is vrij wijzigbaar zolang het
    # component niet "gevuld" is. De UI is hint; de PATCH herevalueert server-side.
    type_wijzigbaar: bool
    created_at: datetime
    updated_at: datetime


class ComponentVerwijderImpact(BaseModel):
    """ADR-022 Fase C — read-only "wat verdwijnt"-samenvatting bij verwijderen
    (geen mutatie, geen audit). Applicatie-only tellingen (Beslissing 5b)."""

    beantwoorde_scores: int
    blokkades: int
    datatypes: int
    gebruikersgroepen: int


class ComponentLijstItem(BaseModel):
    id: uuid.UUID
    naam: str
    componenttype: str
    componenttype_label: str
    hostingmodel: HostingModel
    heeft_applicatie_subtype: bool
    # ADR-023 Fase C: ArchiMate-typing uit de catalogus (read-only projectie) — laag-/
    # element-label + laag-filter in de lijst; null als het type geen mapping draagt.
    archimate_element: str | None = None
    laag: str | None = None
    # ADR-024 UX-B6-b — eigenaar-organisatie als verwijzing + geresolveerde naam (lijst).
    eigenaar_organisatie_id: uuid.UUID | None = None
    eigenaar_organisatie_naam: str | None = None
    # LI057 (Slice 1) — nu op élk component (was nullable via applicatie-LEFT-JOIN).
    migratiepad: Migratiepad
    # ADR-046 — levensfase (null = "nog niet vastgelegd"); lijstkolom + filter.
    levensfase: Levensfase | None = None
    complexiteit: NiveauEnum
    prioriteit: NiveauEnum
    # ADR-028 — componentclassificatie (registratief): rol + BIV (+ labels).
    componentrol: str
    rol_label: str
    biv_beschikbaarheid: str | None = None
    biv_beschikbaarheid_label: str | None = None
    biv_integriteit: str | None = None
    biv_integriteit_label: str | None = None
    biv_vertrouwelijkheid: str | None = None
    biv_vertrouwelijkheid_label: str | None = None
    lifecycle_status: LifecycleStatus | None = None


class ComponentPagina(BaseModel):
    items: list[ComponentLijstItem]
    volgende_cursor: str | None = None


class ComponentKeuze(BaseModel):
    optie_sleutel: str
    label: str
    # ADR-022 Fase E: per componenttype of het checklist-dragend is (krijgt profiel +
    # checklist). Voor andere dimensies (structuurrelatie_type) altijd false.
    checklist_dragend: bool = False
    # ADR-045: per componenttype of het werk ondersteunt (koppelbaar aan de functie-as,
    # gate 2). Voor andere dimensies altijd false.
    ondersteunt_werk: bool = False
    # ADR-023 Fase C: ArchiMate-typing per componenttype (read-only) — voedt het
    # laag-filter van de componentlijst. Null voor andere dimensies.
    archimate_element: str | None = None
    laag: str | None = None


class OptieKeuze(BaseModel):
    """Minimale (sleutel, label)-keuze voor een formulier-dropdown (ADR-028)."""

    optie_sleutel: str
    label: str


class ComponentOpties(BaseModel):
    """Actieve catalogus-opties per dimensie (formulier-databron, CD052 §5)."""

    componenttype: list[ComponentKeuze] = []
    structuurrelatie_type: list[ComponentKeuze] = []
    # ADR-028 — componentclassificatie (additief): actieve rol-opties + ordinale BIV-niveaus
    # (`biv_niveaus` staat op `volgorde` van laag → hoog; de lijstvolgorde ís de ordinale schaal).
    componentrol_opties: list[OptieKeuze] = []
    biv_niveaus: list[OptieKeuze] = []


class StructuurRelatieItem(BaseModel):
    """Eén buur-component in het structuur-overzicht (met relatietype-label)."""

    structuur_id: uuid.UUID
    component_id: uuid.UUID
    naam: str
    componenttype: str
    relatietype: str
    relatietype_label: str
    omschrijving: str | None


class ComponentStructuurOverzicht(BaseModel):
    """Beide richtingen in één respons (ADR-021 Besluit 6, Fase D/E-databron)."""

    draait_op: list[StructuurRelatieItem] = []      # waar dit component op steunt
    gebruikt_door: list[StructuurRelatieItem] = []  # wie op dit component steunt


# ── ADR-021 Besluit 10 / Fase E — impactanalyse (read-only afgeleide view) ──────

class ImpactBron(BaseModel):
    """Het bronobject van de analyse."""

    id: uuid.UUID
    naam: str
    componenttype_label: str


class GeraaktComponent(BaseModel):
    """Eén afhankelijk component (direct/transitief) met readiness-context."""

    component_id: uuid.UUID
    naam: str
    componenttype_label: str
    niveau: int                       # 1 = direct afhankelijk
    pad: list[str]                    # componentnamen van bron → dit component
    relatietype_label: str            # relatietype van de eerste stap van het pad
    # Uitsluitend bij applicatie-subtypen; null voor kale infra.
    lifecycle_status: LifecycleStatus | None = None
    open_blokkades: int | None = None


class ImpactSamenvatting(BaseModel):
    aantal_geraakt: int
    aantal_applicaties: int
    aantal_geblokkeerd: int


class ComponentImpact(BaseModel):
    """Afgeleide, read-only impact-respons (geen schrijfpaden, geen engine-koppeling)."""

    component: ImpactBron
    contracten: list["ContractVoorComponent"]
    geraakt: list[GeraaktComponent]
    samenvatting: ImpactSamenvatting


# Laat-geïmporteerd om een schema-importcyclus te vermijden; herbouwt het model.
from schemas.component_contract import ContractVoorComponent  # noqa: E402

ComponentImpact.model_rebuild()
