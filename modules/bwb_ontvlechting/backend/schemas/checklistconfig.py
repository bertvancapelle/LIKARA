"""Pydantic v2-schemas voor de platform-beheer-API van de checklist-
antwoordconfiguratie (ADR-019 fase 2D, ADR-012 Addendum A).

Beheer-read (incl. inactieve opties + optie-`id` + `afgeleid_bron`), apart van de
tenant-facing `ChecklistVraagRead` (2B): de beheerder adresseert opties op `id` en
moet de read-only-status van afgeleide sets kunnen tonen.
"""
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from models.models import AntwoordType, ChecklistPrioriteit
from schemas.applicatie import _optionele_tekst, _verplichte_tekst


class ConfigOptieRead(BaseModel):
    """Eén optie uit de catalogus, beheer-perspectief."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    optie_sleutel: str
    label: str
    volgorde: int
    actief: bool
    afgeleid_bron: str | None


class ConfigVraagRead(BaseModel):
    """Eén vraag + antwoordtype + ALLE opties (incl. inactieve). ADR-022 W1:
    tenant-eigen vraag — adresseerbaar op `id`, met `componenttype`/`actief`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    componenttype: str
    code: str
    categorie_nr: int
    categorie_naam: str
    vraag: str
    prioriteit: ChecklistPrioriteit
    antwoordtype: AntwoordType
    actief: bool
    opties: list[ConfigOptieRead] = []


class VraagCreate(BaseModel):
    """ADR-022 W1 — nieuwe tenant-vraag. `componenttype`+`code` vormen samen de
    identiteit (set-once); `componenttype` wordt tegen de catalogus gevalideerd."""

    model_config = ConfigDict(extra="forbid")

    componenttype: str
    code: str
    vraag: str
    categorie_nr: int
    categorie_naam: str
    prioriteit: ChecklistPrioriteit = ChecklistPrioriteit.midden
    antwoordtype: AntwoordType = AntwoordType.geen

    @field_validator("componenttype")
    @classmethod
    def _v_type(cls, v: str) -> str:
        return _verplichte_tekst(v, "componenttype", 60)

    @field_validator("code")
    @classmethod
    def _v_code(cls, v: str) -> str:
        return _verplichte_tekst(v, "code", 10)

    @field_validator("vraag")
    @classmethod
    def _v_vraag(cls, v: str) -> str:
        return _verplichte_tekst(v, "vraag", 2000)

    @field_validator("categorie_naam")
    @classmethod
    def _v_cat(cls, v: str) -> str:
        return _verplichte_tekst(v, "categorie_naam", 120)


class VraagUpdate(BaseModel):
    """ADR-022 W1 — bewerkbare (niet-tellende) velden; `componenttype`+`code` zijn
    immutable (identiteit). Geen fan-out nodig."""

    model_config = ConfigDict(extra="forbid")

    vraag: str | None = None
    categorie_nr: int | None = None
    categorie_naam: str | None = None
    prioriteit: ChecklistPrioriteit | None = None

    @field_validator("vraag")
    @classmethod
    def _v_vraag(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "vraag", 2000)

    @field_validator("categorie_naam")
    @classmethod
    def _v_cat(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "categorie_naam", 120)


class ActiefUpdate(BaseModel):
    """(De)activeren van een vraag (soft-deactivatie). Wijzigt `aantal_vragen` → fan-out."""

    model_config = ConfigDict(extra="forbid")

    actief: bool


class VraagImpact(BaseModel):
    """Read-only "raakt N componenten"-telling voor een componenttype (in-tenant)."""

    aantal_componenten: int


class AntwoordTypeUpdate(BaseModel):
    """Antwoordtype van een vraag zetten."""

    model_config = ConfigDict(extra="forbid")

    antwoordtype: AntwoordType


class OptieCreate(BaseModel):
    """Nieuwe optie toevoegen aan een (niet-afgeleide) vraag."""

    model_config = ConfigDict(extra="forbid")

    optie_sleutel: str
    label: str
    volgorde: int = 0

    @field_validator("optie_sleutel")
    @classmethod
    def _v_sleutel(cls, v: str) -> str:
        return _verplichte_tekst(v, "optie_sleutel", 60)

    @field_validator("label")
    @classmethod
    def _v_label(cls, v: str) -> str:
        return _verplichte_tekst(v, "label", 120)


class OptieUpdate(BaseModel):
    """Label en/of volgorde van een optie wijzigen (partieel)."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    volgorde: int | None = None

    @field_validator("label")
    @classmethod
    def _v_label(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "label", 120)
