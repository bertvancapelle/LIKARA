"""Blok D (LI051) — voorkant en achterkant schonen dezelfde term identiek op.

Doordat de voorkant nu óók opschoont (`frontend/src/zoekterm.js`), bestaat dezelfde regel op twee
plaatsen. Twee versies lopen op termijn gegarandeerd uiteen — dan haalt de ene wél weg wat de andere
laat staan, een verschil dat niemand ziet. Daarom draaien BEIDE kanten dezelfde reeks voorbeelden uit
één bestand (`frontend/tests/fixtures/zoekterm_gelijkheid.json`) en asserten tegen dezelfde 'uit'.
Wijkt de achterkant af, dan valt deze test om; wijkt de voorkant af, dan valt de vitest om
(`frontend/tests/zoekterm.test.js`). Zo kunnen ze niet stil uiteen groeien.

Deze test dekt de ACHTERKANT (`services/zoektekst.schoon_zoekterm`). Het is bewust een backend-test
die een frontend-fixture leest: die fixture is de ene gedeelde bron van waarheid voor beide kanten.
"""
import json
import pathlib

import pytest

from services import zoektekst

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_FIXTURE = _ROOT / "frontend" / "tests" / "fixtures" / "zoekterm_gelijkheid.json"


def _gevallen():
    doc = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return [(g["in"], g["uit"]) for g in doc["gevallen"]]


@pytest.mark.parametrize("ruw,verwacht", _gevallen())
def test_achterkant_schoont_gelijk_aan_gedeelde_reeks(ruw, verwacht):
    """Elke 'in' uit de gedeelde reeks schoont de achterkant naar exact dezelfde 'uit' die de
    voorkant-vitest ook afdwingt — inclusief de randgevallen (alleen rommel -> leeg, leeg,
    tekst zonder rommel, losse accent-/umlautvorm)."""
    assert zoektekst.schoon_zoekterm(ruw) == verwacht


def test_reeks_bevat_de_randgevallen():
    """Vangnet: de gedeelde reeks blijft de randgevallen dekken (anders zegt 'groen' te weinig)."""
    ins = [i for i, _ in _gevallen()]
    assert "" in ins                                   # lege invoer
    assert any("\x00" in i for i in ins)               # nulteken (de storing-veroorzaker)
    assert any(i and zoektekst.schoon_zoekterm(i) == "" for i in ins)  # alleen rommel -> leeg
    assert any("́" in i or "̈" in i for i in ins)  # losse (gedecomponeerde) accentvorm
