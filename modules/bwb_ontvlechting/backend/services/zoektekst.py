r"""Eén bron voor het zoeken op door gebruikers ingetypte tekst (LI051).

Vóór deze bron was de LIKE-escape **negen keer** gekopieerd over de services — en een tiende
kopie of een afwijkend zoekveld zou stil ander gedrag geven. Alle naam-/tekst-zoekvelden lopen nu
door `zoek_clause`; de bronscan (`test_zoektekst_een_bron_li051`) faalt zodra een service opnieuw
zelf `.ilike(...)` aanroept of een eigen escape definieert.

Twee eigenschappen, hier één keer geborgd:

- **Accent-ongevoelig** (besluit Bert): `unaccent(kolom) ILIKE unaccent(patroon)` — wie "jose"
  typt vindt *José*, wie "bevolkerung" typt vindt *Bevölkerungsregister*. `unaccent` raakt alleen
  de VERGELIJKING; de opgeslagen naam verandert niet (*José* blijft *José* op het scherm). De
  `unaccent`-DB-functie wordt door de migratie geïnstalleerd en bij het opstarten gecontroleerd
  (`app.core.zoekfunctie`) — ontbreekt hij, dan start LIKARA niet.
- **Jokertekens blijven letterlijk**: `%` en `_` in de zoekterm worden ge-escapet (volgorde
  `\` → `%` → `_`), zodat wie een procentteken typt daar letterlijk op zoekt. `unaccent` laat die
  ASCII-tekens (incl. de escape `\`) ongemoeid, dus de escape overleeft de accent-vouwing.
"""
import sqlalchemy as sa

from schemas import tekstschoning

# De LIKE-escape (was 9× gekopieerd; nu één plek). Backslash — Postgres-default.
_LIKE_ESCAPE = "\\"


def schoon_zoekterm(term: str) -> str:
    r"""Schoon een ingetypte/geplakte zoekterm op — **zoeken weigert nooit** (besluit Bert, LI051).

    De gedeelde categorie-regel (`schemas/tekstschoning`), met bij zoeken: stuurtekens (`Cc`) ook weg
    (weigert nooit). Volgorde:

    1. **NFC** + **`Zs`-spaties → gewone spatie** + **`Cf`-opmaaktekens weg** (`vervang_onzichtbaar`).
       De woordgrens blijft dus staan: `zaak<vaste spatie>systeem` → `zaak systeem`.
    2. **Stuurtekens (`Cc`) weg** — nultekens, regelovergangen, tabs (bij zoeken verwijderd, niet
       geweigerd). Dit voorkomt óók de kale encoding-storing die een NUL in een LIKE-bindparameter
       zou geven.
    3. **Spaties samenvouwen + trimmen** (`vouw_spaties`).

    Idempotent. Blijft er niets over, dan is de teruggave leeg — een lege zoekopdracht (geen filter),
    geen fout. Dezelfde regel als het vastleggen (`schemas/_validators`) en de voorkant
    (`frontend/src/zoekterm.js`); de gedeelde gelijkheidsreeks bewaakt dat ze niet uiteen groeien.
    """
    tussen = tekstschoning.vervang_onzichtbaar(term)
    tussen = "".join(ch for ch in tussen if not tekstschoning.is_stuurteken(ch))
    return tekstschoning.vouw_spaties(tussen)


def escape_like(term: str) -> str:
    """Maak `%`/`_` in een zoekterm letterlijk. Volgorde telt: eerst de escape zelf verdubbelen,
    dan de jokertekens ontsnappen (anders zou de tweede stap de eerste ontsnappen)."""
    return term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")


def zoek_clause(kolom, term: str):
    r"""Een accent- én hoofdletterongevoelige 'bevat'-match op `kolom` voor `term`.

    De term wordt eerst opgeschoond (`schoon_zoekterm` — onzichtbare tekens weg, NFC), dan
    ge-escapet en in `%…%` gewikkeld. Rendert `unaccent(<kolom>) ILIKE unaccent(:patroon)
    ESCAPE '\'`; `unaccent` op beide kanten maakt accenten irrelevant. Blijft er na het opschonen
    niets over, dan matcht `%%` alles — een lege zoekopdracht is geen filter, geen fout.
    """
    term = schoon_zoekterm(term)
    patroon = f"%{escape_like(term)}%"
    return sa.func.unaccent(kolom).ilike(sa.func.unaccent(patroon), escape=_LIKE_ESCAPE)
