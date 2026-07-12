"""ADR-023 Fase D — vaste ArchiMate-typing van de element-typen (laag-borging).

Anders dan de **componenttypen** (waarvan de typing tenant-/beheer-configureerbaar in de
catalogus `componentconfig_optie` staat, dim `componenttype`), ligt de typing van de
**element-typen** architectonisch **vast** — niet per tenant aan te passen. Daarom een
code-constante (single source) i.p.v. een catalogus.

Bron van waarheid: de model-docstrings (`models.py`): datatype = ArchiMate data object,
gebruikersgroep = business actor/role, contract = business-laag (contract).

Een dekkingstest (`test_archimate_fase_d.py`) bewaakt dat **elk** `ElementType` óf een
volledige vaste typing draagt, óf bewust geparkeerd is (migratielaag, Fase E), óf zijn
typing via de componenttype-catalogus krijgt (`component`). Zo kan een vergeten indeling
niet ongemerkt ontstaan wanneer Fase E nieuwe element-typen realiseert.
"""
from models.models import ElementType

# Toegestane waardelijsten (ADR-023 OK-3). OK-3 stelde `behavior` oorspronkelijk "leeg";
# die lijn is inmiddels driemaal bewust en gemarkeerd doorbroken: work_package (Fase E,
# ArchiMate-gedragselement), proces (ADR-042, ArchiMate Business Process) en
# bedrijfsfunctie (ADR-043, ArchiMate Business Function).
TOEGESTANE_LAGEN = frozenset({"business", "application", "technology", "implementation_migration"})
TOEGESTANE_ASPECTEN = frozenset({"active", "passive", "behavior"})

# ADR-026 Besluit 1 — gesloten, gedeelde, platform-brede whitelist van geldige
# `archimate_element`-namen (snake_case). Ruim opgezet zodat de platformbeheerder per
# componenttype kan typeren zonder code-wijziging; de fysieke wereld (facility/equipment/
# material) is bewust NIET opgenomen. Enige bron; de Pydantic field-validators en de
# dekkingstest leunen hierop. Een element buiten deze set ⇒ 422.
TOEGESTANE_ELEMENTEN = frozenset({
    # Application layer
    "application_component", "application_service", "data_object",
    # Technology layer
    "node", "device", "system_software", "technology_service", "artifact",
    "communication_network",
    # Business layer
    "business_actor", "business_role", "business_service", "contract", "business_object",
    # ADR-042 — procesregister (gedragselement; expliciete uitbreiding van de gesloten lijst).
    "business_process",
    # ADR-043 — bedrijfsfunctie-as (gedragselement; heropent de door ADR-042 geparkeerde as).
    "business_function",
    # Implementation & Migration layer
    "plateau", "gap", "work_package", "deliverable",
})

# Vaste typing per element-type: {archimate_element, laag, aspect}.
# `component` ontbreekt hier bewust — zie ELEMENT_TYPEN_VIA_COMPONENTTYPE.
ELEMENT_ARCHIMATE_TYPING: dict[ElementType, dict[str, str]] = {
    # Contract: business-laag, passieve structuur (ArchiMate Contract ⊂ Business Object).
    ElementType.contract: {"archimate_element": "contract", "laag": "business", "aspect": "passive"},
    # Datatype: applicatielaag, passieve structuur (ArchiMate Data Object).
    ElementType.datatype: {"archimate_element": "data_object", "laag": "application", "aspect": "passive"},
    # Gebruikersgroep: business-laag, actieve structuur (ArchiMate Business Role/Actor).
    ElementType.gebruikersgroep: {"archimate_element": "business_role", "laag": "business", "aspect": "active"},
    # ADR-024 slice 1 — Partij: business-laag, actieve structuur (ArchiMate Business Actor).
    ElementType.partij: {"archimate_element": "business_actor", "laag": "business", "aspect": "active"},
    # ── ADR-023 Fase E (E0) — migratielaag (Implementation & Migration) ────────────
    # `laag = implementation_migration` is vast (OK-3). Plateau/gap/deliverable zijn
    # (passieve) structuur; Work Package is in ArchiMate een GEDRAGSelement → aspect
    # `behavior`. GEMARKEERDE AFWIJKING: OK-3 stelde dat `behavior` "nu leeg" is; deze
    # slice doorbreekt dat bewust, conform de ArchiMate-standaard (Work Package = gedrag).
    ElementType.plateau: {"archimate_element": "plateau", "laag": "implementation_migration", "aspect": "passive"},
    ElementType.gap: {"archimate_element": "gap", "laag": "implementation_migration", "aspect": "passive"},
    ElementType.work_package: {"archimate_element": "work_package", "laag": "implementation_migration", "aspect": "behavior"},
    ElementType.deliverable: {"archimate_element": "deliverable", "laag": "implementation_migration", "aspect": "passive"},
    # ── ADR-042 slice 1 — procesregister ───────────────────────────────────────────
    # Proces: business-laag, GEDRAGSelement (ArchiMate Business Process) — de TWEEDE
    # gemarkeerde behavior-afwijking op OK-3, naast work_package (zie het comment boven
    # TOEGESTANE_LAGEN).
    ElementType.proces: {"archimate_element": "business_process", "laag": "business", "aspect": "behavior"},
    # ── ADR-043 gate 1a — bedrijfsfunctie-as ─────────────────────────────────────────
    # Bedrijfsfunctie: business-laag, GEDRAGSelement (ArchiMate Business Function) — de
    # DERDE gemarkeerde behavior-afwijking op OK-3, naast work_package en proces. Dit
    # heropent de door ADR-042 besluit 1 geparkeerde as (ADR-043: de bedrijfsfunctie
    # wordt de logische ruggengraat; het procesregister wordt de verdieping eronder).
    ElementType.bedrijfsfunctie: {"archimate_element": "business_function", "laag": "business", "aspect": "behavior"},
}

# Element-typen die de `ElementType`-enum al kent maar die in het huidige model nog GEEN
# subtype-tabel hebben (ADR-023 migratielaag). Sinds Fase E (E0) zijn de migratie-typen
# getypeerd; de set is daarmee leeg. Een nieuw, nog-niet-gerealiseerd element-type wordt
# hier geparkeerd zodat de dekkingstest het niet stil doorheen laat vallen.
ELEMENT_TYPEN_NOG_NIET_GEREALISEERD: frozenset[ElementType] = frozenset()

# `component` krijgt zijn ArchiMate-typing PER componenttype uit de catalogus
# (`componentconfig_optie`, dim `componenttype`) — geborgd door
# `test_dekkingstest_elk_componenttype_heeft_mapping`. Het kent dus geen één vaste waarde.
ELEMENT_TYPEN_VIA_COMPONENTTYPE: frozenset[ElementType] = frozenset({ElementType.component})


def typing_voor(element_type: ElementType) -> dict[str, str] | None:
    """De vaste ArchiMate-typing van een element-type, of None als die niet vast is
    (`component`: per componenttype) of nog niet gerealiseerd (migratielaag, Fase E)."""
    return ELEMENT_ARCHIMATE_TYPING.get(element_type)
