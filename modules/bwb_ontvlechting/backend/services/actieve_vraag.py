"""LI050 — dé afleiding "hoort dit bij een vraag die nog gesteld wordt?" (besluit Bert).

> Een uitgezette vraag bestaat voor de beoordeling niet: haar antwoord telt niet mee,
> en het knelpunt dat eruit voortkwam telt niet mee — zolang de vraag uit staat.
> Er wordt niets vernietigd of opgelost: het antwoord en het knelpunt blijven bestaan
> en tellen vanzelf weer mee zodra de vraag weer aan gaat.

Deze module is de ENIGE plek waar die afleiding leeft (één bron voor tellen én tonen —
twee plekken die zelf beslissen wat "actief" betekent lopen stil uiteen). Elke telling of
weergave van antwoorden/knelpunten filtert via deze twee EXISTS-clausules; een bronscan-test
(`test_uitgezette_vraag_li050.py`) borgt dat de consumenten niet zelf een tweede
actief-filter bouwen.

Bewust **core-constructen** (`table()`/`column()`, geen ORM-import): zo kan óók de
engine-naburige `landschapskaart_service` (die geen engine-ORM-symbolen mag importeren,
DC013-patroon) dezelfde bron gebruiken. Puur lezend — geen session, geen mutatie.
"""
from sqlalchemy import column, exists, select, table

_vraag_t = table("checklistvraag", column("id"), column("actief"))
_score_t = table("checklistscore", column("id"), column("checklistvraag_id"))


def score_telt_mee(checklistvraag_id_kolom):
    """EXISTS: de vraag van dit antwoord staat aan. Toepasbaar op elke query met een
    `checklistvraag_id`-kolom (ORM-attribuut of core-kolom)."""
    return exists(
        select(1).where(
            _vraag_t.c.id == checklistvraag_id_kolom,
            _vraag_t.c.actief.is_(True),
        )
    )


def blokkade_telt_mee(checklistscore_id_kolom):
    """EXISTS: het antwoord waaruit dit knelpunt voortkwam hoort bij een vraag die aan
    staat. Toepasbaar op elke query met een `checklistscore_id`-kolom."""
    return exists(
        select(1)
        .select_from(
            _score_t.join(_vraag_t, _vraag_t.c.id == _score_t.c.checklistvraag_id)
        )
        .where(
            _score_t.c.id == checklistscore_id_kolom,
            _vraag_t.c.actief.is_(True),
        )
    )
