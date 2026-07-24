"""De gedeelde tekst-schoonregel, per Unicode-categorie (LI051 — tekenset-verbreden).

De vorige aanpak kende alleen de "leerboek"-stuurtekens (C0/C1). Precies wat er bij plakken uit Word,
Excel en PDF meekomt — vaste spaties, brede spaties, zero-width tekens, de bytemarkering — viel
daarbuiten en overleefde de hele keten. De les: **benoem de regel in categorieën, niet als
handgeschreven lijst codes** — een lijst mist morgen weer een teken.

Dé regel, afgeleid uit de Unicode-categorie van elk teken:

- **`Zs` (spatie-separator) → één gewone spatie.** Vaste spatie (NBSP), smalle vaste spatie,
  en/em-spatie, ideografische spatie. Wie een spatie intypte, bedoelde een spatie — die woordgrens
  blijft dus staan.
- **`Cf` (opmaakteken) → weg.** Zero-width spatie/joiner, de woordverbinder, de bytemarkering (BOM).
  Onzichtbaar en betekenisloos.
- **`Cc` (stuurteken) → hier blijven staan; de caller beslist:** zoeken verwijdert ze (weigert
  nooit), invoer weigert ze met een melding (een regelovergang in een naam is een plakfout).
- **Daarna: opeenvolgende gewone spaties samenvouwen tot één, en begin/eind trimmen.** Anders lost
  het ene onvindbare geval op en ontstaat het volgende (`zaak␣␣systeem` vindt `Zaaksysteem Tiel` niet).

Dit is DE ene bron voor zowel het zoeken (`services/zoektekst.schoon_zoekterm`) als het vastleggen
(`schemas/_validators`). De voorkant (`frontend/src/zoekterm.js`) spiegelt exact dezelfde regel; de
gedeelde gelijkheidsreeks (`frontend/tests/fixtures/zoekterm_gelijkheid.json`) bewaakt dat ze niet
uiteen groeien.
"""
import re
import unicodedata

_MEERDERE_SPATIES = re.compile(r" {2,}")


def is_stuurteken(ch: str) -> bool:
    """Een teken uit categorie `Cc` (C0/C1-stuurtekens, incl. NUL, regelovergang, tab, DEL)."""
    return unicodedata.category(ch) == "Cc"


def vervang_onzichtbaar(waarde: str) -> str:
    """NFC-normaliseer; elke `Zs`-spatie → gewone spatie; elk `Cf`-opmaakteken → weg. Stuurtekens
    (`Cc`) blijven staan — de caller beslist wat ermee gebeurt (zoeken verwijdert, invoer weigert)."""
    uit = []
    for ch in unicodedata.normalize("NFC", waarde):
        cat = unicodedata.category(ch)
        if cat == "Cf":
            continue
        uit.append(" " if cat == "Zs" else ch)
    return "".join(uit)


def vouw_spaties(waarde: str) -> str:
    """Runs van gewone spaties → één; begin/eind getrimd. Andere witruimte (een regelovergang of tab
    in een meerregelig veld) blijft ongemoeid — alleen spaties worden samengevouwen."""
    return _MEERDERE_SPATIES.sub(" ", waarde).strip()
