"""Pydantic v2-schemas voor de platform-beheer-API van de checklist-
antwoordconfiguratie (ADR-019 fase 2D, ADR-012 Addendum A).

Beheer-read (incl. inactieve opties + optie-`id` + `afgeleid_bron`), apart van de
tenant-facing `ChecklistVraagRead` (2B): de beheerder adresseert opties op `id` en
moet de read-only-status van afgeleide sets kunnen tonen.
"""
import uuid
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

from models.models import AntwoordType, ChecklistPrioriteit
from schemas._validators import _optionele_tekst, _verplichte_tekst


class WijzigingsAard(str, Enum):
    """ADR-056 besluit 2 — de beheerder zegt zelf wat een tekstwijziging is.
    LIKARA leidt dit nooit uit de tekst af (geen diff-heuristiek)."""

    verduidelijking = "verduidelijking"
    wijziging = "wijziging"


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
    # LI050 (W3): de categorie is een verwijzing; naam + volgorde reizen mee in de read.
    categorie_id: uuid.UUID
    categorie_naam: str
    categorie_volgorde: int
    # LI050 (W5): de sleep-volgorde van de vraag binnen haar categorie.
    volgorde: int
    vraag: str
    prioriteit: ChecklistPrioriteit
    antwoordtype: AntwoordType
    actief: bool
    # ADR-023 Fase F (F-3): toegekende betekenis (optie_sleutel) of None.
    betekenis: str | None = None
    opties: list[ConfigOptieRead] = []


class CategorieRead(BaseModel):
    """LI050 (ADR-022 W3) — één checklist-categorie + het aantal vragen eronder
    (voedt de beheer-UI én de verwijder-weigering voorspelbaar)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    componenttype: str
    naam: str
    volgorde: int
    aantal_vragen: int


class CategorieCreate(BaseModel):
    """LI050 — nieuwe categorie. Naam uniek binnen (tenant, componenttype) —
    schema-afgedwongen; `volgorde` is puur presentatievolgorde."""

    model_config = ConfigDict(extra="forbid")

    componenttype: str
    naam: str
    # LI050 (W5): geen invoer meer — None = achteraan (service kent toe); het veld blijft
    # in het contract voor gerichte plaatsing door een toekomstige consument.
    volgorde: int | None = None

    @field_validator("componenttype")
    @classmethod
    def _v_type(cls, v: str) -> str:
        return _verplichte_tekst(v, "componenttype", 60)

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 120)


class CategorieUpdate(BaseModel):
    """LI050 — hernoemen en/of volgorde wijzigen (partieel); `componenttype` is
    immutable (een categorie verhuist niet van type)."""

    model_config = ConfigDict(extra="forbid")

    naam: str | None = None
    volgorde: int | None = None

    @field_validator("naam")
    @classmethod
    def _v_naam(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "naam", 120)


class VraagCreate(BaseModel):
    """ADR-022 W1 — nieuwe tenant-vraag. `componenttype`+`code` vormen samen de
    identiteit (set-once); `componenttype` wordt tegen de catalogus gevalideerd.
    LI050 (W3): de vraag KIEST een bestaande categorie (`categorie_id`, zelfde
    componenttype); LI050 (W4): de code wordt door het systeem TOEGEKEND — geen
    invoerveld meer (de code is intern: identiteits-anker voor de deeplink, geen
    zichtbare positie)."""

    model_config = ConfigDict(extra="forbid")

    componenttype: str
    vraag: str
    categorie_id: uuid.UUID
    prioriteit: ChecklistPrioriteit = ChecklistPrioriteit.midden
    antwoordtype: AntwoordType = AntwoordType.geen

    @field_validator("componenttype")
    @classmethod
    def _v_type(cls, v: str) -> str:
        return _verplichte_tekst(v, "componenttype", 60)

    @field_validator("vraag")
    @classmethod
    def _v_vraag(cls, v: str) -> str:
        return _verplichte_tekst(v, "vraag", 2000)


class VraagUpdate(BaseModel):
    """ADR-022 W1 — bewerkbare velden; `componenttype`+`code` zijn immutable
    (identiteit). LI050: herplaatsen naar een andere categorie mag via `categorie_id`
    (zelfde componenttype, servicelaag).

    ADR-056: een wijziging van de VRAAGTEKST heeft gevolgen — de beheerder duidt haar
    via `wijzigingsaard` (verplicht bij een tekstwijziging, servicelaag): een
    `verduidelijking` schuift de bevroren formulering bij de antwoorden mee (mét
    stille notitie); een `wijziging` laat bestaande antwoorden als verouderd lezen.
    Categorie/volgorde/prioriteit blijven aard-loos (geen betekenis-verschuiving)."""

    model_config = ConfigDict(extra="forbid")

    vraag: str | None = None
    # ADR-056 besluit 2 — verplicht zodra `vraag` daadwerkelijk wijzigt (servicelaag).
    wijzigingsaard: WijzigingsAard | None = None
    categorie_id: uuid.UUID | None = None
    # LI050 (W5): de sleep-bouwsteen bewaart de nieuwe volgorde via dit veld.
    volgorde: int | None = None
    prioriteit: ChecklistPrioriteit | None = None

    @field_validator("vraag")
    @classmethod
    def _v_vraag(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "vraag", 2000)


class ActiefUpdate(BaseModel):
    """(De)activeren van een vraag (soft-deactivatie). Wijzigt `aantal_vragen` → fan-out."""

    model_config = ConfigDict(extra="forbid")

    actief: bool


class VraagImpact(BaseModel):
    """Read-only "raakt N componenten"-telling voor een componenttype (in-tenant)."""

    aantal_componenten: int


class VraagAntwoordImpact(BaseModel):
    """ADR-056 besluit 12 — read-only "dit raakt N antwoorden"-telling voor één vraag.
    De voorspelling vóór het opslaan; dezelfde service-telling voedt straks (snede 3)
    het beeld erná — nooit twee afleidingen."""

    aantal_antwoorden: int


class AntwoordTypeUpdate(BaseModel):
    """Antwoordtype van een vraag zetten."""

    model_config = ConfigDict(extra="forbid")

    antwoordtype: AntwoordType


class BetekenisOptieRead(BaseModel):
    """Eén betekenis uit de platform-brede catalogus (keuzeveld, read-only)."""

    model_config = ConfigDict(from_attributes=True)

    optie_sleutel: str
    label: str
    volgorde: int


class BetekenisUpdate(BaseModel):
    """ADR-023 Fase F (F-3) — de betekenis van een vraag (her)toekennen of wissen.
    `betekenis=None` wist de toekenning; een waarde wordt tegen de actieve catalogus
    gevalideerd. Geen fan-out (classificatie, voedt de engine niet)."""

    model_config = ConfigDict(extra="forbid")

    betekenis: str | None = None

    @field_validator("betekenis")
    @classmethod
    def _v_betekenis(cls, v: str | None) -> str | None:
        return v if v is None else _optionele_tekst(v, 60)


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
