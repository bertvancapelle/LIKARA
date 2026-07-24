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

# De LIKE-escape (was 9× gekopieerd; nu één plek). Backslash — Postgres-default.
_LIKE_ESCAPE = "\\"


def escape_like(term: str) -> str:
    """Maak `%`/`_` in een zoekterm letterlijk. Volgorde telt: eerst de escape zelf verdubbelen,
    dan de jokertekens ontsnappen (anders zou de tweede stap de eerste ontsnappen)."""
    return term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")


def zoek_clause(kolom, term: str):
    """Een accent- én hoofdletterongevoelige 'bevat'-match op `kolom` voor `term`.

    Rendert `unaccent(<kolom>) ILIKE unaccent(:patroon) ESCAPE '\\'`. De term wordt eerst
    ge-escapet en in `%…%` gewikkeld; `unaccent` op beide kanten maakt accenten irrelevant.
    Geef een niet-lege, gestripte term — de caller filtert lege termen al weg (geen clause = alles).
    """
    patroon = f"%{escape_like(term)}%"
    return sa.func.unaccent(kolom).ilike(sa.func.unaccent(patroon), escape=_LIKE_ESCAPE)
