"""Seed — default relatie-kenmerk-vocabulaire-catalogus (ADR-023 Fase E).

Platform-brede referentiedata (één tabel `relatiekenmerk_optie`). Idempotent via
`ON CONFLICT (dimensie, optie_sleutel) DO NOTHING`. Draait UITSLUITEND via
`platform_init` (init-container). `bouw_relatiekenmerk()` is puur (DB-vrij) en testbaar.

Nu: de `dispositie`-waardenlijst van het plateau-lidmaatschap (behouden/migreren/
vervangen/uitfaseren). Toekomstige relatie-kenmerken (gap/work_package/deliverable)
landen hier eveneens.
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import RelatieKenmerkDimensie, RelatieKenmerkOptie

_DISPOSITIE: list[tuple[str, str]] = [
    ("behouden", "Behouden"),
    ("migreren", "Migreren"),
    ("vervangen", "Vervangen"),
    ("uitfaseren", "Uitfaseren"),
]

_CATALOGUS: list[tuple[RelatieKenmerkDimensie, list[tuple[str, str]]]] = [
    (RelatieKenmerkDimensie.dispositie, _DISPOSITIE),
]


def bouw_relatiekenmerk() -> list[dict]:
    """Puur (DB-vrij): geordende lijst optie-rijen. Deterministisch."""
    rijen: list[dict] = []
    for dimensie, paren in _CATALOGUS:
        for volgorde, (sleutel, label) in enumerate(paren):
            rijen.append({
                "dimensie": dimensie,
                "optie_sleutel": sleutel,
                "label": label,
                "volgorde": volgorde,
                "actief": True,
            })
    return rijen


async def seed_relatiekenmerk(session) -> int:
    """Zaai de default-catalogus (idempotent). Geeft het aantal optie-rijen terug
    (vast 4 = de dispositie-waarden, ook bij een tweede idempotente run)."""
    rijen = bouw_relatiekenmerk()
    stmt = pg_insert(RelatieKenmerkOptie).values(rijen).on_conflict_do_nothing(
        index_elements=["dimensie", "optie_sleutel"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(rijen)
