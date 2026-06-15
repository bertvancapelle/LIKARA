"""Tests — ADR-023 Fase D: ArchiMate-laag-borging van de element-typen.

Offline dekkingstest (analoog aan `test_dekkingstest_elk_componenttype_heeft_mapping` voor
componenttypen): elk `ElementType` is geclassificeerd — óf vaste typing, óf bewust geparkeerd
(migratielaag, Fase E), óf via de componenttype-catalogus (`component`). Een vergeten
indeling (nieuw element-type zonder classificatie) faalt hierdoor zichtbaar.

Fase D is volledig additief: geen schema-/migratie-/RLS-/enginewijziging.
"""


def test_dekkingstest_elk_elementtype_is_geclassificeerd():
    """Besluit 9-lijn: elk `ElementType` is geclassificeerd — geen stil gat. De drie
    classificatie-verzamelingen partitioneren de enum exact (geen overlap, geen ontbrekend)."""
    from models.models import ElementType
    from services.archimate_typing import (
        ELEMENT_ARCHIMATE_TYPING,
        ELEMENT_TYPEN_NOG_NIET_GEREALISEERD,
        ELEMENT_TYPEN_VIA_COMPONENTTYPE,
    )

    getypeerd = set(ELEMENT_ARCHIMATE_TYPING)
    geparkeerd = set(ELEMENT_TYPEN_NOG_NIET_GEREALISEERD)
    via_componenttype = set(ELEMENT_TYPEN_VIA_COMPONENTTYPE)

    # 1. Volledige dekking: samen exact de hele enum (een nieuw, niet-geclassificeerd type faalt hier).
    assert getypeerd | geparkeerd | via_componenttype == set(ElementType)
    # 2. Disjunct: geen type in twee categorieën tegelijk (geen dubbele/tegenstrijdige classificatie).
    assert getypeerd.isdisjoint(geparkeerd)
    assert getypeerd.isdisjoint(via_componenttype)
    assert geparkeerd.isdisjoint(via_componenttype)


def test_vaste_typing_is_volledig_en_binnen_toegestane_waarden():
    """Elk getypeerd element-type draagt een volledige element+laag+aspect-mapping binnen
    de toegestane waardelijsten (ADR-023 OK-3)."""
    from services.archimate_typing import (
        ELEMENT_ARCHIMATE_TYPING,
        TOEGESTANE_ASPECTEN,
        TOEGESTANE_LAGEN,
        typing_voor,
    )

    for element_type, typing in ELEMENT_ARCHIMATE_TYPING.items():
        assert typing_voor(element_type) == typing  # helper = single source
        assert typing["archimate_element"], element_type
        assert typing["laag"] in TOEGESTANE_LAGEN, element_type
        assert typing["aspect"] in TOEGESTANE_ASPECTEN, element_type


def test_realiseerbare_element_typen_concreet():
    """De gerealiseerde element-typen dragen de vastgelegde typing — de business-/
    applicatie-elementen (contract/datatype/gebruikersgroep) én sinds Fase E (E0) de
    migratie-elementen (plateau/gap/work_package/deliverable, implementation_migration)."""
    from models.models import ElementType
    from services.archimate_typing import typing_voor

    assert typing_voor(ElementType.contract) == {
        "archimate_element": "contract", "laag": "business", "aspect": "passive",
    }
    assert typing_voor(ElementType.datatype)["archimate_element"] == "data_object"
    assert typing_voor(ElementType.datatype)["laag"] == "application"
    assert typing_voor(ElementType.gebruikersgroep)["laag"] == "business"
    assert typing_voor(ElementType.gebruikersgroep)["aspect"] == "active"
    # ADR-023 Fase E (E0): migratielaag.
    for et in (ElementType.plateau, ElementType.gap, ElementType.work_package, ElementType.deliverable):
        assert typing_voor(et)["laag"] == "implementation_migration"
    # Work Package = gedragselement (bewuste afwijking op OK-3 "behavior leeg").
    assert typing_voor(ElementType.work_package)["aspect"] == "behavior"
    assert typing_voor(ElementType.plateau)["aspect"] == "passive"


def test_niet_vast_getypeerde_typen_geven_none():
    """Alleen `component` levert géén vaste typing (typing via componenttype-catalogus).
    Sinds Fase E (E0) zijn de migratie-elementen wél getypeerd; de geparkeerde set is leeg."""
    from models.models import ElementType
    from services.archimate_typing import (
        ELEMENT_TYPEN_NOG_NIET_GEREALISEERD,
        typing_voor,
    )

    assert typing_voor(ElementType.component) is None
    assert ELEMENT_TYPEN_NOG_NIET_GEREALISEERD == frozenset()
