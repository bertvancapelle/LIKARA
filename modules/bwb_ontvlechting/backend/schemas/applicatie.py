"""Pydantic v2-schemas voor de entiteit Applicatie (P5, ADR-009).

Gescheiden Create / Update / Read. `extra='forbid'` op alle invoer-schemas;
field validators op elk invoerveld (niet-lege verplichte tekst, max-lengtes,
enum-validatie via de model-enums als single source).

Server-beheerde velden (`id`, `tenant_id`, `created_at`, `updated_at`,
`lifecycle_status`) staan NOOIT in Create/Update — lifecycle is server-beheerd
(zie de service-laag). `tenant_id` wordt ook in Read niet geëxposeerd.

De enum-types worden uit het SQLAlchemy-model hergebruikt (één bron van
waarheid); een ongeldige waarde wordt door Pydantic automatisch geweigerd.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from models.models import HostingModel, LifecycleStatus, Migratiepad, NiveauEnum

# Verplichte, niet-nullbare tekstvelden mogen bij een PATCH niet expliciet op
# null worden gezet (zou een DB NOT NULL-overtreding lekken).
_VERPLICHTE_VELDEN = frozenset(
    {"naam", "hostingmodel", "eigenaar_organisatie", "migratiepad", "complexiteit", "prioriteit"}
)


def _verplichte_tekst(waarde: str | None, veld: str, maxlen: int) -> str:
    """Niet-lege, gestripte tekst met max-lengte (verplicht veld)."""
    if waarde is None:
        raise ValueError(f"{veld} is verplicht")
    waarde = waarde.strip()
    if not waarde:
        raise ValueError(f"{veld} mag niet leeg zijn")
    if len(waarde) > maxlen:
        raise ValueError(f"{veld} mag maximaal {maxlen} tekens bevatten")
    return waarde


def _optionele_tekst(waarde: str | None, maxlen: int) -> str | None:
    """Gestripte optionele tekst; leeg ⇒ None; max-lengte afgedwongen."""
    if waarde is None:
        return None
    waarde = waarde.strip()
    if not waarde:
        return None
    if len(waarde) > maxlen:
        raise ValueError(f"mag maximaal {maxlen} tekens bevatten")
    return waarde


class ApplicatieCreate(BaseModel):
    """Invoer voor het aanmaken van een applicatie."""

    model_config = ConfigDict(extra="forbid")

    naam: str
    beschrijving: str | None = None
    hostingmodel: HostingModel
    eigenaar_organisatie: str
    eigenaar_naam: str | None = None
    leverancier: str | None = None
    migratiepad: Migratiepad
    complexiteit: NiveauEnum
    prioriteit: NiveauEnum

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @field_validator("eigenaar_organisatie")
    @classmethod
    def _v_eigenaar_organisatie(cls, v: str) -> str:
        # Vrije tekst (configureerbaar per tenant) — geen enum.
        return _verplichte_tekst(v, "eigenaar_organisatie", 120)

    @field_validator("eigenaar_naam", "leverancier")
    @classmethod
    def _v_opt_255(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @field_validator("beschrijving")
    @classmethod
    def _v_beschrijving(cls, v: str | None) -> str | None:
        # Text-kolom (geen DB-limiet) — defensieve max-lengte tegen misbruik.
        return _optionele_tekst(v, 10_000)


class ApplicatieUpdate(BaseModel):
    """Partiële update (PATCH). Alle velden optioneel; alleen meegestuurde
    velden worden toegepast (`model_dump(exclude_unset=True)` in de service).

    `lifecycle_status` ontbreekt bewust — die is server-beheerd en wordt
    uitsluitend via de lifecycle-overgangen gewijzigd.
    """

    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    beschrijving: str | None = None
    hostingmodel: HostingModel | None = None
    eigenaar_organisatie: str | None = None
    eigenaar_naam: str | None = None
    leverancier: str | None = None
    migratiepad: Migratiepad | None = None
    complexiteit: NiveauEnum | None = None
    prioriteit: NiveauEnum | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 255)

    @field_validator("eigenaar_organisatie")
    @classmethod
    def _v_eigenaar_organisatie(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "eigenaar_organisatie", 120)

    @field_validator("eigenaar_naam", "leverancier")
    @classmethod
    def _v_opt_255(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @field_validator("beschrijving")
    @classmethod
    def _v_beschrijving(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)

    @model_validator(mode="after")
    def _verbied_null_op_verplicht(self) -> "ApplicatieUpdate":
        # Een verplicht veld mag wel weggelaten, maar niet expliciet op null gezet.
        for veld in _VERPLICHTE_VELDEN:
            if veld in self.model_fields_set and getattr(self, veld) is None:
                raise ValueError(f"{veld} mag niet op null worden gezet")
        return self


class ApplicatieRead(BaseModel):
    """Volledige weergave van een applicatie. `tenant_id` wordt niet geëxposeerd."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    naam: str
    beschrijving: str | None
    hostingmodel: HostingModel
    eigenaar_organisatie: str
    eigenaar_naam: str | None
    leverancier: str | None
    migratiepad: Migratiepad
    complexiteit: NiveauEnum
    prioriteit: NiveauEnum
    lifecycle_status: LifecycleStatus
    created_at: datetime
    updated_at: datetime


class ApplicatiePagina(BaseModel):
    """Cursor-gepagineerde lijst. `volgende_cursor` is None op de laatste pagina."""

    items: list[ApplicatieRead]
    volgende_cursor: str | None = None


class ApplicatieOpties(BaseModel):
    """Read-only keuzewaarden per enumveld (voor de frontend-dropdowns)."""

    hostingmodel: list[str]
    migratiepad: list[str]
    complexiteit: list[str]
    prioriteit: list[str]
