"""Pydantic v2-schemas voor de platform-beheer-API van de componentcatalogus
(ADR-021 Besluit 8, ADR-012 Addendum C; ADR-026). Spiegel van `schemas/contractconfig`.

`dimensie` en `optie_sleutel` zijn immutable (stabiele sleutel) — ze ontbreken in Update;
meesturen ⇒ 422 (`extra='forbid'`).

ADR-026: de ArchiMate-typering (`archimate_element`/`archimate_laag`/`archimate_aspect`) is
beheerbaar. Elk veld wordt afzonderlijk gevalideerd tegen zijn gesloten set
(`TOEGESTANE_ELEMENTEN`/`TOEGESTANE_LAGEN`/`TOEGESTANE_ASPECTEN`) — GEEN combinatievalidatie
(welk element bij welke laag/aspect hoort wordt niet afgedwongen). Voor dimensie
`componenttype` zijn de drie velden verplicht bij aanmaken (Besluit 4); andere dimensies
laten ze leeg. De DB-CHECK (migratie 0025) is de structurele backstop.
"""
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.models import ComponentConfigDimensie
from schemas._validators import _verplichte_tekst
from services.archimate_typing import (
    TOEGESTANE_ASPECTEN,
    TOEGESTANE_ELEMENTEN,
    TOEGESTANE_LAGEN,
)

_SLEUTEL_PATROON = re.compile(r"^[a-z][a-z0-9_]*$")


def _v_sleutel(v: str) -> str:
    v = _verplichte_tekst(v, "optie_sleutel", 60)
    if not _SLEUTEL_PATROON.match(v):
        raise ValueError("optie_sleutel moet lowercase snake_case zijn (a-z, 0-9, _)")
    return v


def _v_uit_set(v: str | None, toegestaan: frozenset[str], veld: str) -> str | None:
    """Valideer één optionele typering-waarde tegen zijn gesloten set. None/'' blijft None
    (volledigheid voor componenttype wordt door de model-validator afgedwongen, niet hier)."""
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    if v not in toegestaan:
        raise ValueError(f"{veld} '{v}' valt buiten de toegestane waarden")
    return v


class ComponentConfigOptieCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dimensie: ComponentConfigDimensie
    optie_sleutel: str
    label: str
    volgorde: int | None = None  # None ⇒ service plaatst achteraan binnen de dimensie
    # ADR-026 — ArchiMate-typering; verplicht voor dimensie componenttype (model-validator).
    archimate_element: str | None = None
    archimate_laag: str | None = None
    archimate_aspect: str | None = None
    # ADR-045 besluit 4 — een componenttype wordt in ÉÉN handeling volledig ingericht:
    # beide vlaggen zijn verplicht voor dimensie componenttype (model-validator) en
    # geweerd voor andere dimensies. Dit repareert het 422-gat: het beheerscherm stuurde
    # `checklist_dragend` al mee bij aanmaken, terwijl dit schema (extra='forbid') het
    # veld niet kende — "componenttype toevoegen" faalde daardoor altijd.
    checklist_dragend: bool | None = None
    ondersteunt_werk: bool | None = None

    @field_validator("optie_sleutel")
    @classmethod
    def _sleutel(cls, v: str) -> str:
        return _v_sleutel(v)

    @field_validator("label")
    @classmethod
    def _label(cls, v: str) -> str:
        return _verplichte_tekst(v, "label", 120)

    @field_validator("archimate_element")
    @classmethod
    def _element(cls, v: str | None) -> str | None:
        return _v_uit_set(v, TOEGESTANE_ELEMENTEN, "archimate_element")

    @field_validator("archimate_laag")
    @classmethod
    def _laag(cls, v: str | None) -> str | None:
        return _v_uit_set(v, TOEGESTANE_LAGEN, "archimate_laag")

    @field_validator("archimate_aspect")
    @classmethod
    def _aspect(cls, v: str | None) -> str | None:
        return _v_uit_set(v, TOEGESTANE_ASPECTEN, "archimate_aspect")

    @model_validator(mode="after")
    def _typering_verplicht_voor_componenttype(self) -> "ComponentConfigOptieCreate":
        # Besluit 4: een componenttype draagt ALTIJD een volledige typing; andere dimensies
        # (structuurrelatie_type, archimate_relatie) laten de velden leeg.
        if self.dimensie == ComponentConfigDimensie.componenttype and not (
            self.archimate_element and self.archimate_laag and self.archimate_aspect
        ):
            raise ValueError(
                "Een componenttype vereist archimate_element, archimate_laag en archimate_aspect."
            )
        return self

    @model_validator(mode="after")
    def _vlaggen_horen_bij_componenttype(self) -> "ComponentConfigOptieCreate":
        # ADR-045 besluit 4 — in één handeling volledig inrichten: beide vlaggen
        # verplicht (niet None) voor een componenttype; andere dimensies dragen ze niet
        # (meesturen ⇒ 422, spiegel van de typering-regel; de DB-CHECK van 0065 is de
        # structurele backstop voor `ondersteunt_werk`).
        if self.dimensie == ComponentConfigDimensie.componenttype:
            if self.checklist_dragend is None or self.ondersteunt_werk is None:
                raise ValueError(
                    "Een componenttype vereist checklist_dragend en ondersteunt_werk."
                )
        elif self.checklist_dragend is not None or self.ondersteunt_werk is not None:
            raise ValueError(
                "checklist_dragend en ondersteunt_werk gelden alleen voor de dimensie componenttype."
            )
        return self


class ComponentConfigOptieUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    volgorde: int | None = None
    actief: bool | None = None
    # ADR-027 — markeert (alleen zinvol op dimensie componenttype) of het type een checklist draagt.
    checklist_dragend: bool | None = None
    # ADR-045 — markeert of het type werk ondersteunt (koppelbaar aan de functie-as).
    # De service weigert beide vlaggen op een niet-componenttype-rij (422); de DB-CHECK
    # (0065) is de structurele backstop voor `ondersteunt_werk`.
    ondersteunt_werk: bool | None = None
    # ADR-026 — typering corrigeren naar geldige waarden. Leegmaken (None) voor een
    # componenttype wordt in de service geweigerd (Besluit 5) + door de DB-CHECK afgevangen.
    archimate_element: str | None = None
    archimate_laag: str | None = None
    archimate_aspect: str | None = None

    @field_validator("label")
    @classmethod
    def _label(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "label", 120)

    @field_validator("archimate_element")
    @classmethod
    def _element(cls, v: str | None) -> str | None:
        return _v_uit_set(v, TOEGESTANE_ELEMENTEN, "archimate_element")

    @field_validator("archimate_laag")
    @classmethod
    def _laag(cls, v: str | None) -> str | None:
        return _v_uit_set(v, TOEGESTANE_LAGEN, "archimate_laag")

    @field_validator("archimate_aspect")
    @classmethod
    def _aspect(cls, v: str | None) -> str | None:
        return _v_uit_set(v, TOEGESTANE_ASPECTEN, "archimate_aspect")


class ComponentConfigOptieRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dimensie: ComponentConfigDimensie
    optie_sleutel: str
    label: str
    volgorde: int
    actief: bool
    # ADR-022/027 — of het type een checklist draagt (alleen zinvol op dimensie componenttype).
    checklist_dragend: bool = False
    # ADR-045 — of het type werk ondersteunt (alleen zinvol op dimensie componenttype).
    ondersteunt_werk: bool = False
    # ADR-026 — typering meegeven. De model-kolommen heten `laag`/`aspect`; de API-velden
    # dragen het `archimate_`-voorvoegsel (validation_alias mapt de ORM-attributen).
    archimate_element: str | None = None
    archimate_laag: str | None = Field(default=None, validation_alias="laag")
    archimate_aspect: str | None = Field(default=None, validation_alias="aspect")
    # ADR-027 Deel 4 — read-only inzage: de (code-eigen) kenmerk-definitie per relatietype
    # (dimensie archimate_relatie). Niet bewerkbaar via de API; alleen ter inzage in de UI.
    kenmerk_definitie: dict = {}
