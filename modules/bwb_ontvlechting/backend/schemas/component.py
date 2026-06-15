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

from models.models import HostingModel, LifecycleStatus, NiveauEnum
from schemas.applicatie import _verplichte_tekst


class ComponentSorteerveld(str, Enum):
    """Allowlist van sorteerbare component-velden (ADR-017 B2). De drie subtype-
    kolommen zijn nullable (LEFT JOIN) → NULLS-LAST. `test_component_sort` borgt
    dat dit 1-op-1 synchroon loopt met `component_service._SORTEERBARE_KOLOMMEN`."""

    created_at = "created_at"
    naam = "naam"
    componenttype = "componenttype"
    complexiteit = "complexiteit"
    prioriteit = "prioriteit"
    lifecycle_status = "lifecycle_status"


class ComponentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str
    componenttype: str
    hostingmodel: HostingModel = HostingModel.onbekend
    eigenaar_organisatie: str | None = None
    eigenaar_naam: str | None = None
    leverancier: str | None = None
    beschrijving: str | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @field_validator("componenttype")
    @classmethod
    def _v_type(cls, v: str) -> str:
        return _verplichte_tekst(v, "componenttype", 60)


class ComponentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    componenttype: str | None = None
    hostingmodel: HostingModel | None = None
    eigenaar_organisatie: str | None = None
    eigenaar_naam: str | None = None
    leverancier: str | None = None
    beschrijving: str | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 255)

    @field_validator("componenttype")
    @classmethod
    def _v_type(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "componenttype", 60)


class ComponentRead(BaseModel):
    id: uuid.UUID
    naam: str
    componenttype: str
    componenttype_label: str
    hostingmodel: HostingModel
    eigenaar_organisatie: str
    eigenaar_naam: str | None
    leverancier: str | None
    beschrijving: str | None
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
    # Besturingsvelden uit het subtype (CD054b W1) — null voor niet-applicatie-typen.
    eigenaar_organisatie: str | None = None
    complexiteit: NiveauEnum | None = None
    prioriteit: NiveauEnum | None = None
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
    # ADR-023 Fase C: ArchiMate-typing per componenttype (read-only) — voedt het
    # laag-filter van de componentlijst. Null voor andere dimensies.
    archimate_element: str | None = None
    laag: str | None = None


class ComponentOpties(BaseModel):
    """Actieve catalogus-opties per dimensie (formulier-databron, CD052 §5)."""

    componenttype: list[ComponentKeuze] = []
    structuurrelatie_type: list[ComponentKeuze] = []


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
