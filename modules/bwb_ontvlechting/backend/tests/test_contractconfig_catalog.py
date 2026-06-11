"""Unit-tests — ADR-020 catalogus-validatie/-resolutie (DB gemockt/monkeypatched)."""
import asyncio
from unittest.mock import AsyncMock

import pytest


def test_resolveer_incl_inactief_en_fallback():
    from services import contractconfig_catalog as catalog

    label_map = {"hosting": ("Hosting", True), "oud": ("Oud model", False)}
    out = catalog.resolveer(["hosting", "oud", "weg"], label_map)
    assert out == [
        {"optie_sleutel": "hosting", "label": "Hosting", "actief": True},
        {"optie_sleutel": "oud", "label": "Oud model", "actief": False},
        {"optie_sleutel": "weg", "label": "weg", "actief": False},  # niet meer in catalogus → fallback
    ]
    assert catalog.resolveer_een("hosting", label_map) == "Hosting"
    assert catalog.resolveer_een("weg", label_map) == "weg"


def test_valideer_sleutels_weigert_onbekend_of_inactief(monkeypatch):
    from models.models import ContractConfigDimensie
    from services import contractconfig_catalog as catalog
    from services.errors import OngeldigeRegistratie

    async def _actief(session, dimensie):
        return {"hosting", "onderhoud_support"}

    monkeypatch.setattr(catalog, "actieve_sleutels", _actief)
    session = AsyncMock()

    # geldig (subset van actief) — geen fout, lege lijst is no-op
    asyncio.run(catalog.valideer_sleutels(session, ContractConfigDimensie.dekking, ["hosting"]))
    asyncio.run(catalog.valideer_sleutels(session, ContractConfigDimensie.dekking, []))

    with pytest.raises(OngeldigeRegistratie) as exc:
        asyncio.run(catalog.valideer_sleutels(session, ContractConfigDimensie.dekking, ["hosting", "spook"]))
    assert exc.value.code == "ONGELDIGE_OPTIE"
