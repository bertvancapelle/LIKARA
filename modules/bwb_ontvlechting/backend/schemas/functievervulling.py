"""Pydantic v2-schemas — functievervulling (ADR-049, gate 2a).

`FunctievervullingAanmaken` = invoer (component_id, functie_id, optioneel ouder_functie_id +
toelichting), `extra='forbid'`. Leeg `ouder_functie_id` = GROF ("geldt overal"); gevuld = FIJN
(déze plek). De as is KAAL — géén applicatiefunctie/werkwoord (ADR-049 besluit 3).

`FunctievervullingUit` = één koppelregel na aanmaak (verrijkt). `PlekDekkingUit` = de LEESREGEL-
uitkomst per plek: "welke componenten dragen déze plek" mét `herkomst` (fijn verdringt grof —
ADR-049 besluit 1/5); consumenten lezen dit, ze rekenen niet zelf.
"""
import uuid

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _optionele_tekst


_OORDELEN = {"naar_behoren", "noodoplossing"}


def _v_oordeel(v: str | None) -> str | None:
    """ADR-051 — optioneel; leeg = nog niet beoordeeld; anders uit de gesloten set."""
    if v is None:
        return None
    v = v.strip()
    if v not in _OORDELEN:
        raise ValueError("onbekend oordeel")
    return v


class FunctievervullingAanmaken(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: uuid.UUID
    functie_id: uuid.UUID
    # Leeg = grove koppeling (geldt overal); gevuld = fijne koppeling op díé plek (onder deze ouder).
    ouder_functie_id: uuid.UUID | None = None
    toelichting: str | None = None
    # ADR-051 — optioneel oordeel bij het koppelen (naar_behoren / noodoplossing); leeg = nog niet beoordeeld.
    oordeel: str | None = None

    @field_validator("toelichting")
    @classmethod
    def _vt(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000, meerregelig=True)

    @field_validator("oordeel")
    @classmethod
    def _vo(cls, v: str | None) -> str | None:
        return _v_oordeel(v)


class GeenSysteemAanmaken(BaseModel):
    """ADR-051 besluit 2 — leg vast: "hier draait geen systeem — vastgesteld" (een bevinding)."""

    model_config = ConfigDict(extra="forbid")

    functie_id: uuid.UUID
    ouder_functie_id: uuid.UUID | None = None
    toelichting: str | None = None

    @field_validator("toelichting")
    @classmethod
    def _vt(cls, v: str | None) -> str | None:
        return _optionele_tekst(v, 10_000, meerregelig=True)


class OordeelWijzigen(BaseModel):
    """ADR-051 besluit 3/4 — zet of wis (None) het oordeel op een component-koppeling."""

    model_config = ConfigDict(extra="forbid")

    oordeel: str | None = None

    @field_validator("oordeel")
    @classmethod
    def _vo(cls, v: str | None) -> str | None:
        return _v_oordeel(v)


class DekkingComponent(BaseModel):
    """Eén dragend component binnen de dekking van een plek."""

    model_config = ConfigDict(from_attributes=True)

    vervulling_id: uuid.UUID
    component_id: uuid.UUID
    component_naam: str
    componenttype: str
    componenttype_label: str
    toelichting: str | None = None
    oordeel: str | None = None  # naar_behoren / noodoplossing / None (nog niet beoordeeld)
    # ADR-043 gate 4 brok 1 — draagt dit dekkende systeem ≥1 gebruikersgroep? (afgeleid uit de
    # serving-leeslaag; voedt de 'werkvoorraad'-stand). Read-only, nooit opgeslagen.
    heeft_gebruikersgroep: bool = False


class FunctievervullingUit(BaseModel):
    """Eén registratie ná aanmaak: een component-koppeling óf een "geen systeem"-bevinding
    (dan zijn de component-velden leeg). `herkomst` = 'grof' | 'fijn' | 'geen_systeem'."""

    model_config = ConfigDict(from_attributes=True)

    vervulling_id: uuid.UUID
    component_id: uuid.UUID | None = None
    component_naam: str | None = None
    componenttype: str | None = None
    componenttype_label: str | None = None
    toelichting: str | None = None
    oordeel: str | None = None
    functie_id: uuid.UUID
    ouder_functie_id: uuid.UUID | None = None
    herkomst: str
    geen_systeem: bool = False
    verklaard_door_naam: str | None = None


class PlekDekkingUit(BaseModel):
    """De leesregel-uitkomst voor één plek: fijn verdringt grof (ADR-049). `herkomst` = 'fijn'
    als deze plek een eigen antwoord draagt, anders 'grof' (het geldt-overal-antwoord van de
    functie). `componenten` is nooit leeg (plekken zonder dekking staan niet in de lijst).

    De verdringing benoemt zichzelf (LI041): op een fijne plek draagt `verdrongen` het grove
    antwoord dat hier verborgen is (read-only — het bestaat nog, ADR-049 besluit 1; géén actie
    op deze plek). Op een grove plek tellen `grof_totaal_plekken` (N) en `grof_geldt_op` (M) de
    reikwijdte voor het getelde label — beide uit dezelfde afleiding, nooit opgeslagen."""

    model_config = ConfigDict(from_attributes=True)

    functie_id: uuid.UUID
    ouder_functie_id: uuid.UUID | None = None
    herkomst: str  # 'grof' | 'fijn' | 'geen_systeem'
    componenten: list[DekkingComponent]  # leeg bij 'geen_systeem'
    # LI041 — de verdringing benoemt zichzelf.
    verdrongen: list[DekkingComponent] = []
    grof_totaal_plekken: int | None = None
    grof_geldt_op: int | None = None
    # ADR-051 — het id van de "geen systeem"-bevinding op deze plek (om terug te nemen).
    bevinding_id: uuid.UUID | None = None


class ComponentKoppelingUit(BaseModel):
    """ADR-043 gate 4 (G2/G9) — één koppeling van dít component, gelezen uit de leesregel
    `dekking_overzicht` (fijn verdringt grof; nooit een rauwe `where component_id`-query).

    `herkomst` = 'grof' (geldt overal) of 'fijn' (één plek). Bij grof dragen `grof_totaal_plekken`
    (N) / `grof_geldt_op` (M) de reikwijdte ("geldt nog op M van de N plekken") en `verdrongen_op`
    het aantal plekken waar een fijner antwoord dit grove hier verbergt (het bestaat nog — ADR-049
    besluit 1). Bij fijn dragen `ouder_functie_id`/`ouder_naam` de plek-context."""

    model_config = ConfigDict(from_attributes=True)

    vervulling_id: uuid.UUID
    herkomst: str  # 'grof' | 'fijn'
    functie_id: uuid.UUID
    functie_naam: str | None = None
    ouder_functie_id: uuid.UUID | None = None
    ouder_naam: str | None = None
    oordeel: str | None = None
    grof_totaal_plekken: int | None = None
    grof_geldt_op: int | None = None
    verdrongen_op: int = 0


class PlekStandUit(BaseModel):
    """ADR-051 — de stand van één plek: 'gat' · 'via_boven' · 'hier' · 'niets'. Bij 'via_boven',
    langs het pad van DEZE plek: `via_functie_id` = de dichtstbijzijnde dragende voorouder als er
    precies één op die afstand hangt; bij meerdere op gelijke afstand is `via_functie_id` leeg en
    telt `via_aantal` ze (geen willekeurige keuze — ADR-044-les)."""

    model_config = ConfigDict(from_attributes=True)

    functie_id: uuid.UUID
    ouder_functie_id: uuid.UUID | None = None
    stand: str
    via_functie_id: uuid.UUID | None = None
    via_aantal: int = 0


class PlekStandenUit(BaseModel):
    """ADR-051 besluit 5 — één afleiding, twee vensters: de boom-cue leest `plekken`, de centrale
    signalering leest dezelfde lijst + de gedeelde `tellers` (read-only, nooit opgeslagen)."""

    model_config = ConfigDict(from_attributes=True)

    plekken: list[PlekStandUit]
    tellers: dict[str, int]
