"""Seed — default relatie-kenmerk-vocabulaire-catalogus (ADR-023 Fase E).

Platform-brede referentiedata (één tabel `relatiekenmerk_optie`). Idempotent via
`ON CONFLICT (dimensie, optie_sleutel) DO NOTHING`. Draait UITSLUITEND via
`platform_init` (init-container). `bouw_relatiekenmerk()` is puur (DB-vrij) en testbaar.

De `dispositie`-dimensie (plateau-lidmaatschap) is met ADR-046 besluit 2 SOFT-
gedeactiveerd: het plateau draagt geen eigen bedoeling meer (die leeft op het component,
`migratiepad`). De rijen blijven geseed mét `actief=False` — historische kenmerk-waarden
op bestaande relaties blijven zo label-resolvebaar (nooit hard weg); nieuwe registratie
kan niet (de aggregation-kenmerkdefinitie noemt `dispositie` niet meer). Toekomstige
relatie-kenmerken (gap/work_package/deliverable) landen hier eveneens.
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import RelatieKenmerkDimensie, RelatieKenmerkOptie

# ADR-046 — soft-gedeactiveerd (actief=False in `bouw_relatiekenmerk`); zie de docstring.
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
    ("account_manager", "Account Manager"),
    ("service_delivery_manager", "Service Delivery Manager"),
]

_CATALOGUS: list[tuple[RelatieKenmerkDimensie, list[tuple[str, str]]]] = [
    (RelatieKenmerkDimensie.dispositie, _DISPOSITIE),
    (RelatieKenmerkDimensie.relatie_rol, _RELATIE_ROL),
    (RelatieKenmerkDimensie.beheerrol, _BEHEERROL),
]


def bouw_relatiekenmerk() -> list[dict]:
    """Puur (DB-vrij): geordende lijst optie-rijen. Deterministisch. De dispositie-
    dimensie wordt vanaf ADR-046 soft-gedeactiveerd geseed (label-resolutie blijft;
    geen actieve optie meer)."""
    rijen: list[dict] = []
    for dimensie, paren in _CATALOGUS:
        for volgorde, (sleutel, label) in enumerate(paren):
            rijen.append({
                "dimensie": dimensie,
                "optie_sleutel": sleutel,
                "label": label,
                "volgorde": volgorde,
                "actief": dimensie is not RelatieKenmerkDimensie.dispositie,
            })
    return rijen


async def seed_relatiekenmerk(session) -> int:
    """Zaai de default-catalogus (idempotent). Geeft het aantal optie-rijen terug
    (vast 16 = 4 dispositie + 3 relatie_rol + 9 beheerrol, ook bij een tweede idempotente run)."""
    rijen = bouw_relatiekenmerk()
    stmt = pg_insert(RelatieKenmerkOptie).values(rijen).on_conflict_do_nothing(
        index_elements=["dimensie", "optie_sleutel"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(rijen)
