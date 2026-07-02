"""Seed — default BIV-schaal-catalogus (ADR-028 slice 1).

Platform-brede referentiedata (tabel `biv_schaal_optie`). Idempotent via
`ON CONFLICT (optie_sleutel) DO NOTHING`. Draait via `platform_init` (init-container);
migratie 0048 zaait byte-gelijk voor fresh deploys. `bouw_bivschaal()` is puur (DB-vrij).
ORDINAAL: `volgorde` (0/1/2 → laag<midden<hoog) is de rangdrager voor "hoog en hoger"-
filtering. Voedt de engine NIET — de drie BIV-velden zijn registratieve component-attributen.
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import BivSchaalOptie

_NIVEAUS: list[tuple[str, str]] = [
    ("laag", "Laag"),
    ("midden", "Midden"),
    ("hoog", "Hoog"),
]


def bouw_bivschaal() -> list[dict]:
    """Puur (DB-vrij): geordende lijst optie-rijen (ordinaal via `volgorde`). Deterministisch."""
    return [
        {"optie_sleutel": sleutel, "label": label, "volgorde": volgorde, "actief": True}
        for volgorde, (sleutel, label) in enumerate(_NIVEAUS)
    ]


async def seed_bivschaal(session) -> int:
    """Zaai de default-catalogus (idempotent). Geeft het aantal optie-rijen terug."""
    rijen = bouw_bivschaal()
    stmt = pg_insert(BivSchaalOptie).values(rijen).on_conflict_do_nothing(
        index_elements=["optie_sleutel"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(rijen)
