"""Seed — default classificatie-catalogus voor het contractregister (ADR-020, CD040).

Platform-brede referentiedata (één tabel `contractconfig_optie`, drie dimensies).
Idempotent via `ON CONFLICT (dimensie, optie_sleutel) DO NOTHING` — een tweede run
voegt niets toe en dempt door de platformbeheerder toegevoegde opties niet
(geen prune; uitbreiden gebeurt later zonder migratie).

Draait UITSLUITEND via `platform_init` (init-container, cd_admin) — niet in het
tenant-/app-pad. `bouw_contractconfig()` is puur (DB-vrij) en zo testbaar. De
sleutels zijn stabiel + lowercase snake_case; bewerken = soft-deactiveren (`actief`),
nooit hard verwijderen/hernummeren (ADR-020 Besluit 6).
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import ContractConfigDimensie, ContractConfigOptie

# (optie_sleutel, label) per dimensie, in weergavevolgorde. Redelijke startset;
# verder uitbreiden is beheerderswerk (geen release/migratie).
_DEKKING: list[tuple[str, str]] = [
    ("licentie_aanschaf", "Licentie/aanschaf"),
    ("onderhoud_support", "Onderhoud & support"),
    ("hosting", "Hosting"),
]
_KOSTENMODEL: list[tuple[str, str]] = [
    ("saas_pxq", "SaaS — prijs × aantal (p×q)"),
    ("volume", "Volumemodel"),
    ("per_inwoner", "Per inwoner (gemeente)"),
]
# `relatie_rol` is met de consistentie-opruim verhuisd naar de relatie-kenmerk-catalogus
# (seed_relatiekenmerk) — het is een relatie-kenmerk, geen contract-configuratie.
_CATALOGUS: list[tuple[ContractConfigDimensie, list[tuple[str, str]]]] = [
    (ContractConfigDimensie.dekking, _DEKKING),
    (ContractConfigDimensie.kostenmodel, _KOSTENMODEL),
]


def bouw_contractconfig() -> list[dict]:
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


async def seed_contractconfig(session) -> int:
    """Zaai de default-catalogus (idempotent). Geeft het aantal optie-rijen terug
    (vast 6 = 3 dekking + 3 kostenmodel, ook bij een tweede idempotente run)."""
    rijen = bouw_contractconfig()
    stmt = pg_insert(ContractConfigOptie).values(rijen).on_conflict_do_nothing(
        index_elements=["dimensie", "optie_sleutel"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(rijen)
