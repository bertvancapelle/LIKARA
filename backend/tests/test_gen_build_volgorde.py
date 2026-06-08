"""CD018 — borgt de volgorde-fix in gen_build.py (OP-18).

De bug: gen_sessie_briefing.py leest het BOUWSTATUS-blok uit CLAUDE.md; stond
`update_claude_bouwstatus` ná de briefing-generatie, dan kreeg de briefing een
stale blok. De fix verplaatst die update naar vóór de generators.

Beide tests draaien ZONDER build-bijwerkingen: de generators worden via importlib
van pad geladen (module-import heeft geen side-effects — main() zit achter
`if __name__ == "__main__"`), en de write-then-read draait op een temp-CLAUDE.md.
De echte CLAUDE.md, build_counter.json en sessie-start-bestanden worden niet geraakt.
"""
import importlib.util
import inspect
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
GEN = REPO / "docs" / "_generators"

OUD_BLOK = """<!-- BOUWSTATUS_START -->
## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V004 |
| Datum | June 2026 |
| Commit | 237b036 |
| Tests | 362 backend + 83 frontend groen |
| TST-rapport | TST-V004-Validatierapport.md |
| Kritieke bevindingen | 0 |

<!-- BOUWSTATUS_END -->"""


def _laad(naam):
    """Laad een generator-module van pad zonder side-effects."""
    spec = importlib.util.spec_from_file_location(naam, GEN / f"{naam}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_briefing_krijgt_nieuwe_bouwstatus_na_update(tmp_path, monkeypatch):
    """Gefixte volgorde: update_claude_bouwstatus -> daarna leest de briefing
    het NIEUWE blok (geen stale body)."""
    claude = tmp_path / "CLAUDE.md"
    claude.write_text(f"# CompliData\n\n{OUD_BLOK}\n\neinde\n")

    gb = _laad("gen_build")
    sb = _laad("gen_sessie_briefing")

    # 1) bouwstatus-update op de temp-kopie
    monkeypatch.setattr(gb, "CLAUDE_MD", claude)
    gb.update_claude_bouwstatus("V005", "430 backend + 105 frontend groen", "0")

    # 2) briefing leest hetzelfde bestand
    monkeypatch.setattr(sb, "CLAUDE_MD", claude)
    blok = sb.lees_bouwstatus()

    assert "V005" in blok
    assert "430 backend + 105 frontend groen" in blok
    assert "V004" not in blok  # geen stale body meer


def test_main_werkt_bouwstatus_bij_voor_briefing():
    """Statische volgorde-guard: in main() staat de bouwstatus-update vóór de
    briefing-generatie. Keert de bug terug (herordening), dan faalt deze test."""
    gb = _laad("gen_build")
    src = inspect.getsource(gb.main)
    i_update = src.index("update_claude_bouwstatus(")
    i_briefing = src.index('"gen_sessie_briefing.py"')
    assert i_update < i_briefing, "update_claude_bouwstatus moet vóór de briefing-generatie staan"
