"""Pydantic v2-schemas voor de entiteit Blokkade (ADR-009/013).

Blokkades zijn systeem-afgeleid (Model A): er is **geen** Create — ze ontstaan
automatisch uit een blokkerende Checklistscore. De gebruiker beheert alleen de
opvolging via Update (`status`, `toelichting`, `eigenaar`). `opgelost_op` is
server-beheerd (afgeleid uit `status`) en zit niet in Update.
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from models.models import BlokkadeStatus, ChecklistScore
from schemas._validators import _optionele_tekst

_VERPLICHTE_VELDEN = frozenset({"status"})


class BlokkadeStatusFilter(str, Enum):
    """Statusfilter voor het tenant-brede overzicht (CD016).

    `actief` = de gedeelde `ACTIEVE_BLOKKADE_STATUSSEN` (open + in_behandeling) —
    de werklijst; `alle` = geen filter. Een onbekende waarde ⇒ 422 (API-rand).
    """

    actief = "actief"
    open = "open"
    in_behandeling = "in_behandeling"
    opgelost = "opgelost"
    alle = "alle"


class BlokkadeSorteerveld(str, Enum):
    """Allowlist van sorteerbare overzicht-velden (ADR-017 B2).

    Dekt alle getoonde kolommen. NOT NULL: `applicatie_naam`/`vraag_code` (join),
    `status`, `gewijzigd_op`. Nullable (NULLS LAST, ADR-017 B5): `toelichting`,
    `eigenaar`, `opgelost_op`. De service mapt deze namen 1-op-1 op een kolom; een
    test borgt de synchroniteit.
    """

    applicatie_naam = "applicatie_naam"
    vraag_code = "vraag_code"
    status = "status"
    toelichting = "toelichting"
    eigenaar = "eigenaar"
    opgelost_op = "opgelost_op"
    gewijzigd_op = "gewijzigd_op"


class BlokkadeLijstSorteerveld(str, Enum):
    """Allowlist van sorteerbare velden voor de **per-applicatie** blokkade-lijst
    (`GET /blokkades`, retrofit CD020). Dit is de overzicht-allowlist mínus de
    join-only velden (`applicatie_naam`/`vraag_code`) — die zijn betekenisloos in
    een sectie van één applicatie (de per-app `lijst` joint niet). NOT NULL:
    `status`, `gewijzigd_op`, `created_at`. Nullable (NULLS LAST): `toelichting`,
    `eigenaar`, `opgelost_op`. `gewijzigd_op` mapt op `updated_at`.
    """

    created_at = "created_at"
    status = "status"
    toelichting = "toelichting"
    eigenaar = "eigenaar"
    opgelost_op = "opgelost_op"
    gewijzigd_op = "gewijzigd_op"


class BlokkadeUpdate(BaseModel):
    """Handmatige opvolging. `opgelost_op` wordt server-zijdig uit `status` afgeleid."""

    model_config = ConfigDict(extra="forbid")

    status: BlokkadeStatus | None = None
    toelichting: str | None = None
    eigenaar: str | None = None

    @field_validator("toelichting")
    @classmethod
    def _v_toelichting(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)

    @field_validator("eigenaar")
    @classmethod
    def _v_eigenaar(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @model_validator(mode="after")
    def _verbied_null_op_verplicht(self) -> "BlokkadeUpdate":
        for veld in _VERPLICHTE_VELDEN:
            if veld in self.model_fields_set and getattr(self, veld) is None:
                raise ValueError(f"{veld} mag niet op null worden gezet")
        return self


class BlokkadeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    checklistscore_id: uuid.UUID
    component_id: uuid.UUID
    status: BlokkadeStatus
    toelichting: str | None
    eigenaar: str | None
    opgelost_op: datetime | None
    created_at: datetime
    updated_at: datetime


class BlokkadePagina(BaseModel):
    items: list[BlokkadeRead]
    volgende_cursor: str | None = None


class BlokkadeLijstItem(BlokkadeRead):
    """Per-component blokkade verrijkt met de **bron-vraag** (herkomst-traceerbaarheid).

    Superset van `BlokkadeRead`: dezelfde velden + de veroorzakende vraag (`vraag_code`
    + `vraag`-tekst) en de blokkerende `score` (nee/deels), herleid via de bestaande
    verplichte FK-keten `Blokkade.checklistscore_id → Checklistscore → ChecklistVraag`.
    Read-only; geen schema-/engine-wijziging."""

    checklistvraag_id: uuid.UUID
    vraag_code: str
    vraag: str
    score: ChecklistScore | None


class BlokkadeLijstPagina(BaseModel):
    items: list[BlokkadeLijstItem]
    volgende_cursor: str | None = None


class BlokkadeOverzichtItem(BaseModel):
    """Eén blokkade in het tenant-brede overzicht — verrijkt met component-naam + -type
    (join op component) en de veroorzakende `vraag_code` (join op ChecklistVraag). ADR-024-
    vervolg: het type voedt de type-tag + de type-afhankelijke doorklik (applicatie vs.
    generiek component-detail). `applicatie_naam` is het interne veld voor de component-naam."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    component_id: uuid.UUID
    applicatie_naam: str  # component-naam (intern veld; user-facing kop = "Component")
    componenttype: str
    componenttype_label: str
    vraag_code: str
    status: BlokkadeStatus
    toelichting: str | None
    eigenaar: str | None
    opgelost_op: datetime | None
    gewijzigd_op: datetime


class BlokkadeOverzichtPagina(BaseModel):
    items: list[BlokkadeOverzichtItem]
    volgende_cursor: str | None = None


class BlokkadeOpties(BaseModel):
    """Read-only keuzewaarden per enumveld (voor de frontend-dropdowns)."""

    status: list[str]
