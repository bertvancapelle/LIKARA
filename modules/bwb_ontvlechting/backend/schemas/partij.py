"""Pydantic v2-schemas voor het partij-beheer (ADR-024 slice 2a; vervangt externe_partij).

Eén beheerpad voor alle partij-aarden (externe_partij / organisatie / organisatie_eenheid /
persoon). Gescheiden Create/Update/Read, `extra='forbid'`. `email`/`telefoon` zijn gewone `str`
(geen formaatvalidatie). `soort` is **optioneel** (platform-catalogus `partijsoort_optie`,
app-side gevalideerd in de service). `aard` is **verplicht bij aanmaken** en daarna **niet
wijzigbaar** (ontbreekt in Update). `naam` is het enige verplichte inhoudsveld; de overige
contactvelden zijn optioneel en gedeeld over alle aarden (geen aard-eigen velden).
"""
import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from models.models import PartijAard, PartijScope
from schemas._validators import _optionele_tekst, _verplichte_tekst


class PartijSorteerveld(str, Enum):
    """Allowlist van sorteerbare velden (ADR-017). `plaats` is nullable (v2n-NULLS-LAST)."""

    created_at = "created_at"
    naam = "naam"
    plaats = "plaats"
    aard = "aard"


_VERPLICHTE_VELDEN = frozenset({"naam"})


class PartijCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aard: PartijAard  # verplicht; daarna niet wijzigbaar (ontbreekt in Update)
    naam: str
    straat_huisnummer: str | None = None
    postcode: str | None = None
    plaats: str | None = None
    contactpersoon: str | None = None
    telefoon: str | None = None
    mobiel: str | None = None
    email: str | None = None
    # ADR-024 (Optie 1) — persoon-only contactveld (de service weigert het bij andere aarden).
    functietitel: str | None = None
    omschrijving: str | None = None
    soort: str | None = None  # platform-catalogus partijsoort_optie; service valideert
    # ADR-024 slice 2a-bis — lidmaatschap. Structuur (verplicht/verboden per aard) hieronder;
    # de fijnere aard-/laag-consistentie van de doelen valideert de service (cross-row).
    organisatie_id: uuid.UUID | None = None
    afdeling_id: uuid.UUID | None = None
    # ADR-038 — intern/extern. Optioneel bij aanmaken: organisatie zonder waarde → default extern
    # (service). Alleen op organisatie wijzigbaar; externe_partij is vast extern; afdeling/persoon
    # dragen het niet (moeten leeg zijn). De aard-bewuste borging staat in de service.
    scope: PartijScope | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @model_validator(mode="after")
    def _v_lidmaatschap(self) -> "PartijCreate":
        heeft_org_ouder = self.aard in (PartijAard.persoon, PartijAard.organisatie_eenheid)
        if heeft_org_ouder and self.organisatie_id is None:
            raise ValueError("Een persoon of afdeling hoort verplicht bij een organisatie.")
        if not heeft_org_ouder and self.organisatie_id is not None:
            raise ValueError("Een organisatie/externe partij hoort niet onder een andere partij.")
        if self.afdeling_id is not None and self.aard != PartijAard.persoon:
            raise ValueError("Alleen een persoon kan bij een afdeling horen.")
        # ADR-038 — intern/extern alleen op organisatie (wijzigbaar) / externe_partij (vast extern).
        if self.aard == PartijAard.externe_partij and self.scope == PartijScope.intern:
            raise ValueError("Een externe partij kan niet intern zijn.")
        if self.aard in (PartijAard.persoon, PartijAard.organisatie_eenheid) and self.scope is not None:
            raise ValueError("Alleen een organisatie draagt een intern/extern-kenmerk.")
        return self

    @field_validator("postcode")
    @classmethod
    def _v_postcode(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 20)

    @field_validator("telefoon", "mobiel")
    @classmethod
    def _v_tel(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 40)

    @field_validator("straat_huisnummer", "plaats", "contactpersoon", "email")
    @classmethod
    def _v_opt_255(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @field_validator("soort")
    @classmethod
    def _v_soort(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 60)

    @field_validator("functietitel")
    @classmethod
    def _v_functietitel(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 150)

    @field_validator("omschrijving")
    @classmethod
    def _v_omschrijving(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)


class PartijUpdate(BaseModel):
    """Partiële update (PATCH). `naam` mag weggelaten, maar niet op null gezet. `aard` ontbreekt
    bewust — de aard ligt vast na aanmaken (een persoon blijft een persoon)."""

    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    straat_huisnummer: str | None = None
    postcode: str | None = None
    plaats: str | None = None
    contactpersoon: str | None = None
    telefoon: str | None = None
    mobiel: str | None = None
    email: str | None = None
    functietitel: str | None = None
    omschrijving: str | None = None
    soort: str | None = None
    # ADR-024 slice 2a-bis — lidmaatschap kan wijzigen (bv. persoon verhuist); de service
    # valideert aard-bewust (de aard zelf ligt vast).
    organisatie_id: uuid.UUID | None = None
    afdeling_id: uuid.UUID | None = None
    # ADR-038 — intern/extern wijzigen (alleen zinvol op organisatie; de service borgt aard-bewust:
    # externe_partij vast extern, afdeling/persoon dragen het niet). `aard` is hier onbekend → de
    # cross-veld-borging leeft in de service.
    scope: PartijScope | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 255)

    @field_validator("postcode")
    @classmethod
    def _v_postcode(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 20)

    @field_validator("telefoon", "mobiel")
    @classmethod
    def _v_tel(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 40)

    @field_validator("straat_huisnummer", "plaats", "contactpersoon", "email")
    @classmethod
    def _v_opt_255(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 255)

    @field_validator("soort")
    @classmethod
    def _v_soort(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 60)

    @field_validator("functietitel")
    @classmethod
    def _v_functietitel(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 150)

    @field_validator("omschrijving")
    @classmethod
    def _v_omschrijving(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000)

    @model_validator(mode="after")
    def _verbied_null_op_verplicht(self) -> "PartijUpdate":
        for veld in _VERPLICHTE_VELDEN:
            if veld in self.model_fields_set and getattr(self, veld) is None:
                raise ValueError(f"{veld} mag niet op null worden gezet")
        return self


class PartijRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    aard: str
    naam: str
    straat_huisnummer: str | None
    postcode: str | None
    plaats: str | None
    contactpersoon: str | None
    telefoon: str | None
    mobiel: str | None
    email: str | None
    functietitel: str | None
    omschrijving: str | None
    soort: str | None
    organisatie_id: uuid.UUID | None
    afdeling_id: uuid.UUID | None
    # ADR-038 — intern/extern zoals opgeslagen: gezet voor organisatie/externe_partij, None voor
    # afdeling/persoon (die leiden af van hun ouder-organisatie; nog geen consument in Slice 1a,
    # daarom bewust niet in deze read afgeleid — zie gate-rapport).
    scope: str | None = None
    # ADR-037 — optionele afgeleide namen voor identiteit "afdeling — organisatie" /
    # "persoon — afdeling — organisatie" (bv. in de verantwoordelijke-picker). Alleen de lijst-read
    # vult ze (via joins); overige paden laten ze None (backward-compatible).
    organisatie_naam: str | None = None
    afdeling_naam: str | None = None
    created_at: datetime
    updated_at: datetime


class PartijPagina(BaseModel):
    items: list[PartijRead]
    volgende_cursor: str | None = None


class LeverancierComponentRead(BaseModel):
    """LI019 — een component dat via een contract aan deze leverancier hangt (read-only).
    Eén regel per (component, contract)-paar; een component met meerdere contracten verschijnt vaker."""

    model_config = {"from_attributes": True}

    component_id: uuid.UUID
    component_naam: str
    contract_id: uuid.UUID
    contract_naam: str
