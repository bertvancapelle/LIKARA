"""Seed — default componentrol-catalogus (ADR-028 slice 1).

Platform-brede referentiedata (tabel `componentrol_optie`). Idempotent via
`ON CONFLICT (optie_sleutel) DO NOTHING`. Draait via `platform_init` (init-container);
migratie 0048 zaait byte-gelijk voor fresh deploys. `bouw_componentrol()` is puur (DB-vrij).
Voedt de engine NIET — `componentrol` is een registratief component-attribuut.
`interne_applicatie` is de beschermde systeem-sleutel (default).
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import ComponentrolOptie

_ROLLEN: list[tuple[str, str]] = [
    ("interne_applicatie", "Interne applicatie"),
    ("interne_dataprovider", "Interne dataprovider"),
    ("externe_dataprovider", "Externe dataprovider"),
    ("koppelvlak", "Koppelvlak"),
]


def bouw_componentrol() -> list[dict]:
    """Puur (DB-vrij): geordende lijst optie-rijen. Deterministisch."""
    return [
        {"optie_sleutel": sleutel, "label": label, "volgorde": volgorde, "actief": True}
        for volgorde, (sleutel, label) in enumerate(_ROLLEN)
    ]


async def seed_componentrol(session) -> int:
    """Zaai de default-catalogus (idempotent). Geeft het aantal optie-rijen terug."""
    rijen = bouw_componentrol()
    stmt = pg_insert(ComponentrolOptie).values(rijen).on_conflict_do_nothing(
        index_elements=["optie_sleutel"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(rijen)
