"""Seed — default referentiemodel-aanbod (ADR-043 gate 1a).

Platform-brede referentiedata (tabel `referentiemodel_optie`): welke modellen LIKARA
aanbiedt. Idempotent via `ON CONFLICT (optie_sleutel) DO NOTHING`. Draait via
`platform_init` (init-container); migratie 0061 zaait byte-gelijk voor fresh deploys.
`bouw_referentiemodel()` is puur (DB-vrij). Startaanbod: GEMMA Bedrijfsfuncties
(instantie 1, ADR-043 besluit 3) — géén systeem-sleutel (soft-deactivate via `actief`,
beheerd door de platformbeheerder). Voedt de engine NIET.
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import ReferentiemodelOptie

_MODELLEN: list[tuple[str, str, str, str]] = [
    (
        "gemma_bedrijfsfuncties",
        "GEMMA Bedrijfsfuncties",
        "VNG Realisatie — GEMMA Basisarchitectuur (gemmaonline.nl)",
        "GEMMA 2 (2025)",
    ),
]


def bouw_referentiemodel() -> list[dict]:
    """Puur (DB-vrij): geordende lijst aanbod-rijen. Deterministisch."""
    return [
        {
            "optie_sleutel": sleutel, "label": label, "herkomst": herkomst,
            "versie": versie, "volgorde": volgorde, "actief": True,
        }
        for volgorde, (sleutel, label, herkomst, versie) in enumerate(_MODELLEN)
    ]


async def seed_referentiemodel(session) -> int:
    """Zaai het default-aanbod (idempotent). Geeft het aantal aanbod-rijen terug."""
    rijen = bouw_referentiemodel()
    stmt = pg_insert(ReferentiemodelOptie).values(rijen).on_conflict_do_nothing(
        index_elements=["optie_sleutel"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(rijen)
