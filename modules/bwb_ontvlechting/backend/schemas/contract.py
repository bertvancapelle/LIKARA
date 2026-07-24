"""Pydantic v2-schemas voor de entiteit Contract (ADR-020 Besluit 2/4).

Gescheiden Create / Update / Read + lichte LijstItem, `extra='forbid'`. Dekking en
kostenmodel zijn 0..n optie-sleutels (catalogus-dimensies); ze worden bij Create/
Update declaratief als volledige set meegegeven en in de service tegen de actieve
catalogus gevalideerd (ADR-020 Besluit 6/10). Datums zijn puur registratief — GEEN
onderlinge validatie (B4). Self-/cross-row-invarianten zitten in de service-laag.
"""
import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from models.models import ContractType
from schemas._validators import _optionele_tekst, _verplichte_tekst


class ContractSorteerveld(str, Enum):
    """Allowlist van sorteerbare Contract-velden (ADR-017). `begindatum`/`einddatum`
    zijn nullable (v2n-NULLS-LAST); `contractnaam`/`created_at` zijn NOT NULL."""

    created_at = "created_at"
    contractnaam = "contractnaam"
    begindatum = "begindatum"
    einddatum = "einddatum"


_VERPLICHTE_VELDEN = frozenset({"leverancier_id", "contracttype", "contractnaam"})


def _dedup_sleutels(waarde: list[str] | None) -> list[str] | None:
    """Strip, valideer (niet-leeg, ≤60) en dedupliceer optie-sleutels; volgorde-stabiel."""
    if waarde is None:
        return None
    gezien: list[str] = []
    for s in waarde:
        s = (s or "").strip()
        if not s:
            raise ValueError("optie-sleutel mag niet leeg zijn")
        if len(s) > 60:
            raise ValueError("optie-sleutel mag maximaal 60 tekens bevatten")
        if s not in gezien:
            gezien.append(s)
    return gezien


class OptieRef(BaseModel):
    """Geresolveerde catalogus-optie (sleutel + label + actief-vlag). Bij uitlezen
    resolvet elke opgeslagen sleutel — ook een inactieve — naar zijn label, zodat
    historische registraties leesbaar blijven (ADR-020 Besluit 6)."""

    optie_sleutel: str
    label: str
    actief: bool


class ContractCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leverancier_id: uuid.UUID
    contracttype: ContractType
    contractnaam: str
    mantelcontract_id: uuid.UUID | None = None
    extern_contract_id: str | None = None
    leverancier_contract_id: str | None = None
    begindatum: date | None = None
    einddatum: date | None = None
    vernieuwingsdatum: date | None = None
    omschrijving: str | None = None
    toelichting: str | None = None
    dekking: list[str] = []
    kostenmodel: list[str] = []

    @field_validator("contractnaam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "contractnaam", 255)

    @field_validator("extern_contract_id", "leverancier_contract_id")
    @classmethod
    def _v_opt_255(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @field_validator("omschrijving", "toelichting")
    @classmethod
    def _v_tekst(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000, meerregelig=True)

    @field_validator("dekking", "kostenmodel")
    @classmethod
    def _v_sleutels(cls, v: list[str]) -> list[str]:
        return _dedup_sleutels(v) or []


class ContractUpdate(BaseModel):
    """Partiële update. Verplichte velden mogen weggelaten, niet op null gezet.
    `dekking`/`kostenmodel`: weggelaten = ongewijzigd; meegestuurd (ook `[]`) =
    volledige set vervangen (declaratief)."""

    model_config = ConfigDict(extra="forbid")

    leverancier_id: uuid.UUID | None = None
    contracttype: ContractType | None = None
    contractnaam: str | None = None
    mantelcontract_id: uuid.UUID | None = None
    extern_contract_id: str | None = None
    leverancier_contract_id: str | None = None
    begindatum: date | None = None
    einddatum: date | None = None
    vernieuwingsdatum: date | None = None
    omschrijving: str | None = None
    toelichting: str | None = None
    dekking: list[str] | None = None
    kostenmodel: list[str] | None = None

    @field_validator("contractnaam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "contractnaam", 255)

    @field_validator("extern_contract_id", "leverancier_contract_id")
    @classmethod
    def _v_opt_255(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @field_validator("omschrijving", "toelichting")
    @classmethod
    def _v_tekst(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000, meerregelig=True)

    @field_validator("dekking", "kostenmodel")
    @classmethod
    def _v_sleutels(cls, v: list[str] | None) -> list[str] | None:
        return _dedup_sleutels(v)

    @model_validator(mode="after")
    def _verbied_null_op_verplicht(self) -> "ContractUpdate":
        for veld in _VERPLICHTE_VELDEN:
            if veld in self.model_fields_set and getattr(self, veld) is None:
                raise ValueError(f"{veld} mag niet op null worden gezet")
        return self


class ContractRead(BaseModel):
    """Detailweergave incl. geresolveerde dekking/kostenmodel + `leverancier_naam`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    leverancier_id: uuid.UUID
    leverancier_naam: str
    contracttype: ContractType
    mantelcontract_id: uuid.UUID | None
    contractnaam: str
    extern_contract_id: str | None
    leverancier_contract_id: str | None
    begindatum: date | None
    einddatum: date | None
    vernieuwingsdatum: date | None
    omschrijving: str | None
    toelichting: str | None
    dekking: list[OptieRef]
    kostenmodel: list[OptieRef]
    created_at: datetime
    updated_at: datetime


class ContractLijstItem(BaseModel):
    """Lichte lijstweergave (zonder tag-resoluties), met `leverancier_naam`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contractnaam: str
    contracttype: ContractType
    leverancier_id: uuid.UUID
    leverancier_naam: str
    mantelcontract_id: uuid.UUID | None
    begindatum: date | None
    einddatum: date | None
    vernieuwingsdatum: date | None
    created_at: datetime
    updated_at: datetime


class ContractPagina(BaseModel):
    items: list[ContractLijstItem]
    volgende_cursor: str | None = None


class CatalogusKeuze(BaseModel):
    """Eén actieve catalogus-optie voor formuliergebruik (CD043 §0)."""

    optie_sleutel: str
    label: str
    volgorde: int


class CatalogusOpties(BaseModel):
    """Actieve opties per dimensie — tenant-leeszijde van de catalogus (CD043 §0)."""

    dekking: list[CatalogusKeuze] = []
    kostenmodel: list[CatalogusKeuze] = []
    relatie_rol: list[CatalogusKeuze] = []


class ApplicatieKort(BaseModel):
    """Compacte verwijzing naar een gekoppelde applicatie (id + naam) voor overzichten."""

    id: uuid.UUID
    naam: str


class DeelcontractItem(BaseModel):
    """Eigen, rijkere deelcontracten-respons (CD044 §0c) — los van `ContractLijstItem`:
    bevat gelabelde `dekking` (de gedeelde lijst blijft onaangeroerd). LI026: + leverancier +
    de gekoppelde applicaties per deelcontract (mantel→deel→applicaties navigatie)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contractnaam: str
    contracttype: ContractType
    begindatum: date | None
    einddatum: date | None
    vernieuwingsdatum: date | None
    leverancier_naam: str
    dekking: list[OptieRef]
    applicaties: list[ApplicatieKort] = []
