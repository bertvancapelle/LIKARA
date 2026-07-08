"""Seed — default applicatiefunctie-catalogus (ADR-042 slice 2).

Platform-brede referentiedata (tabel `applicatiefunctie_optie`). Idempotent via
`ON CONFLICT (optie_sleutel) DO NOTHING`. Draait via `platform_init` (init-container);
migratie 0058 zaait byte-gelijk voor fresh deploys. `bouw_applicatiefunctie()` is puur
(DB-vrij). GEMMA-geënte startset (subknoop 4) — géén systeem-sleutel: alles
deactiveerbaar, vrij uitbreidbaar door de platformbeheerder. Voedt de engine NIET.
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import ApplicatiefunctieOptie

_FUNCTIES: list[tuple[str, str]] = [
    ("registreren", "Registreren"),
    ("raadplegen", "Raadplegen"),
    ("archiveren", "Archiveren"),
    ("gegevens_leveren", "Gegevens leveren"),
    ("ondersteunen", "Ondersteunen"),
]


def bouw_applicatiefunctie() -> list[dict]:
    """Puur (DB-vrij): geordende lijst optie-rijen. Deterministisch."""
    return [
        {"optie_sleutel": sleutel, "label": label, "volgorde": volgorde, "actief": True}
        for volgorde, (sleutel, label) in enumerate(_FUNCTIES)
    ]


async def seed_applicatiefunctie(session) -> int:
    """Zaai de default-catalogus (idempotent). Geeft het aantal optie-rijen terug."""
    rijen = bouw_applicatiefunctie()
    stmt = pg_insert(ApplicatiefunctieOptie).values(rijen).on_conflict_do_nothing(
        index_elements=["optie_sleutel"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(rijen)
