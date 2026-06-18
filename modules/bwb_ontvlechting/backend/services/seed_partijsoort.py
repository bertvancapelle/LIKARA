"""Seed — default partijsoort-catalogus (ADR-024 slice 1).

Platform-brede referentiedata (tabel `partijsoort_optie`). Idempotent via
`ON CONFLICT (optie_sleutel) DO NOTHING`. Draait via `platform_init` (init-container);
migratie 0027 zaait byte-gelijk voor fresh deploys. `bouw_partijsoort()` is puur (DB-vrij).
Voedt de engine NIET — `soort` is een optioneel element-attribuut.
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import PartijsoortOptie

_SOORTEN: list[tuple[str, str]] = [
    ("leverancier", "Leverancier"),
    ("partner", "Partner"),
    ("ketenpartner", "Ketenpartner"),
]


def bouw_partijsoort() -> list[dict]:
    """Puur (DB-vrij): geordende lijst optie-rijen. Deterministisch."""
    return [
        {"optie_sleutel": sleutel, "label": label, "volgorde": volgorde, "actief": True}
        for volgorde, (sleutel, label) in enumerate(_SOORTEN)
    ]


async def seed_partijsoort(session) -> int:
    """Zaai de default-catalogus (idempotent). Geeft het aantal optie-rijen terug."""
    rijen = bouw_partijsoort()
    stmt = pg_insert(PartijsoortOptie).values(rijen).on_conflict_do_nothing(
        index_elements=["optie_sleutel"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(rijen)
