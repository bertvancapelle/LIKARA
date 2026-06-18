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
# `relatie_rol` — de rol van een contract in zijn association met een component. Met de
# consistentie-opruim verhuisd vanuit ContractConfig (zelfde waarden/labels/betekenis).
_RELATIE_ROL: list[tuple[str, str]] = [
    ("valt_onder", "Valt onder / aanschaf"),
    ("onderhoud", "Onderhoud"),
    ("hosting", "Hosting"),
]
# `beheerrol` (ADR-024 slice 2b) — de rol die een partij vervult op een component/contract
# (rol-toewijzing). Startset van 7; beheerbaar (toevoegen/hernoemen/deactiveren) door de
# platformbeheerder via de relatiekenmerk-catalogus.
_BEHEERROL: list[tuple[str, str]] = [
    ("functioneel_beheer", "Functioneel beheer"),
    ("technisch_beheer", "Technisch beheer"),
    ("applicatiebeheer", "Applicatiebeheer"),
    ("contractbeheer", "Contractbeheer"),
    ("product_owner", "Product owner"),
    ("eigenaar", "Eigenaar"),
    ("proceseigenaar", "Proceseigenaar"),
]

_CATALOGUS: list[tuple[RelatieKenmerkDimensie, list[tuple[str, str]]]] = [
    (RelatieKenmerkDimensie.dispositie, _DISPOSITIE),
    (RelatieKenmerkDimensie.relatie_rol, _RELATIE_ROL),
    (RelatieKenmerkDimensie.beheerrol, _BEHEERROL),
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
    (vast 14 = 4 dispositie + 3 relatie_rol + 7 beheerrol, ook bij een tweede idempotente run)."""
    rijen = bouw_relatiekenmerk()
    stmt = pg_insert(RelatieKenmerkOptie).values(rijen).on_conflict_do_nothing(
        index_elements=["dimensie", "optie_sleutel"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(rijen)
