"""Startup-wachter: de zoekfunctie `unaccent` moet aanwezig zijn (LI051).

Accent-ongevoelig zoeken (`services/zoektekst.py`) leunt op de PostgreSQL-functie `unaccent`. Die
komt uit de `unaccent`-extensie, die migratie 0077 installeert. Op een omgeving waar de migratie
niet is gedraaid (bv. een handmatig aangemaakte database) zou élk zoekveld pas bij de eerste
zoekopdracht knappen. Dat weigeren we: net als bij ontbrekende verplichte configuratie
(`validate_startup_config`) stopt LIKARA bij het opstarten met een leesbare melding.

Aangeroepen in de `lifespan` van `app.main`, ná `validate_startup_config()` — dezelfde plek,
hetzelfde `RuntimeError`-patroon, geen tweede mechanisme ernaast.
"""
from sqlalchemy import text

from app.core.database import async_session_factory


class ZoekfunctieOntbreekt(RuntimeError):
    """De `unaccent`-DB-functie is niet beschikbaar — LIKARA start niet."""


_MELDING = (
    "\n\n"
    + "=" * 56 + "\n"
    + "  LIKARA — DATABASE-FUNCTIE ONTBREEKT bij opstarten\n"
    + "=" * 56 + "\n"
    + "  De zoekfunctie 'unaccent' is niet beschikbaar in de database.\n"
    + "  Zonder deze functie kan er niet accent-ongevoelig gezocht worden\n"
    + "  (zoeken op 'jose' hoort 'José' te vinden).\n\n"
    + "  Wat de beheerder moet doen:\n"
    + "    - Draai de databasemigraties (deze installeren de extensie),\n"
    + "      of installeer haar met superuser-rechten:\n"
    + "          CREATE EXTENSION IF NOT EXISTS unaccent;\n"
    + "    - Herstart LIKARA.\n"
    + "=" * 56 + "\n"
)


async def valideer_zoekfunctie() -> None:
    """Controleer dat `unaccent(...)` aanroepbaar is. Ontbreekt de functie (of faalt de aanroep),
    dan een leesbare `ZoekfunctieOntbreekt` — LIKARA start niet."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT unaccent('x')"))
    except Exception as exc:  # functie onbekend / DB-fout op de check
        raise ZoekfunctieOntbreekt(_MELDING) from exc
