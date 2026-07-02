"""Tests — ADR-023 Fase C: technologielaag-zicht (laag-typing-projectie + laag-filter).

Offline: de read-only ArchiMate-typing-helper + de laag-grouping uit de seed (de basis
van het laag-filter). De draait-op-aanmaak (assignment, host→gehoste) en de
beide-richtingen-traversal worden frontend-zijdig (vitest) resp. live getest
(`test_component_fase_b_cd052.py::test_structuur_overzicht_beide_richtingen` en
`::test_lijst_laag_filter_en_projectie`).

Fase C is volledig additief: geen schema-/migratie-/RLS-/relatieservice-wijziging.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock


def test_archimate_typing_projecteert_element_laag_aspect():
    """De helper levert per componenttype de catalogus-typing (read-only projectie)."""
    from services import componentconfig_catalog as catalog

    rows = [
        SimpleNamespace(
            optie_sleutel="database", archimate_element="system_software",
            laag="technology", aspect="active",
        ),
        SimpleNamespace(
            optie_sleutel="applicatie", archimate_element="application_component",
            laag="application", aspect="active",
        ),
    ]
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(all=lambda: rows)

    out = asyncio.run(catalog.archimate_typing(session))
    assert out["database"] == {
        "archimate_element": "system_software", "laag": "technology", "aspect": "active",
    }
    assert out["applicatie"]["laag"] == "application"


def test_laag_grouping_uit_seed_is_basis_van_het_filter():
    """De laag→componenttypen-grouping (filter-basis) klopt met de gecureerde mapping
    (Besluit 5 / OK-3): system_software + node = technology; saas_dienst = application."""
    from services.seed_componentconfig import bouw_componentconfig

    typing = {
        r["optie_sleutel"]: r
        for r in bouw_componentconfig()
        if r["dimensie"].value == "componenttype"
    }
    technology = {t for t, r in typing.items() if r["laag"] == "technology"}
    application = {t for t, r in typing.items() if r["laag"] == "application"}

    # LI060 — applicatieserver→server_compute (blijft technology); middleware→integratievoorziening
    # (system_software, technology-band: eigen ESB/broker); nieuw landelijke_voorziening
    # (application_service, application-band: extern afgenomen).
    assert technology == {"database", "client_software", "server_compute", "fileshare", "integratievoorziening"}
    assert application == {"applicatie", "saas_dienst", "landelijke_voorziening"}
    # saas_dienst valt bewust BUITEN de technologielaag (applicatielaag).
    assert "saas_dienst" not in technology


def test_actieve_opties_dragen_laag_voor_het_frontend_filter():
    """`actieve_opties_per_dimensie` levert laag/element per componenttype mee zodat de
    componentlijst het laag-filter kan opbouwen (read-only projectie)."""
    from services import componentconfig_catalog as catalog
    from models.models import ComponentConfigDimensie

    rows = [
        SimpleNamespace(
            dimensie=ComponentConfigDimensie.componenttype, optie_sleutel="database",
            label="Database", volgorde=1, checklist_dragend=False,
            archimate_element="system_software", laag="technology",
        ),
    ]
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(all=lambda: rows)

    out = asyncio.run(catalog.actieve_opties_per_dimensie(session))
    rij = out["componenttype"][0]
    assert rij["laag"] == "technology"
    assert rij["archimate_element"] == "system_software"
