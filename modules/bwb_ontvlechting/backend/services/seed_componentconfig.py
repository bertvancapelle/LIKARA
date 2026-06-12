"""Seed — default componentcatalogus (ADR-021 Besluit 8, ADR-012 Addendum C).

Platform-brede referentiedata (één tabel `componentconfig_optie`, twee dimensies:
`componenttype` + `structuurrelatie_type`). Idempotent via
`ON CONFLICT (dimensie, optie_sleutel) DO NOTHING`. Draait UITSLUITEND via
`platform_init` (init-container, cd_admin). `componenttype.applicatie` is een
systeem-sleutel (Fase C borgt de service-bescherming); hier alleen seeden.
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import ComponentConfigDimensie, ComponentConfigOptie

_COMPONENTTYPE: list[tuple[str, str]] = [
    ("applicatie", "Applicatie"),
    ("database", "Database"),
    ("applicatieserver", "Applicatieserver"),
    ("client_software", "Client-software"),
    ("saas_dienst", "SaaS-dienst"),
    ("middleware", "Middleware"),
    ("fileshare", "Fileshare"),
]
_STRUCTUURRELATIE: list[tuple[str, str]] = [
    ("draait_op", "Draait op"),
    ("maakt_deel_uit_van", "Maakt deel uit van"),
]

_CATALOGUS: list[tuple[ComponentConfigDimensie, list[tuple[str, str]]]] = [
    (ComponentConfigDimensie.componenttype, _COMPONENTTYPE),
    (ComponentConfigDimensie.structuurrelatie_type, _STRUCTUURRELATIE),
]


def bouw_componentconfig() -> list[dict]:
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


async def seed_componentconfig(session) -> int:
    """Zaai de default-componentcatalogus (idempotent). Geeft het aantal optie-rijen
    terug (vast 9: 7 componenttypen + 2 structuurrelatie-typen)."""
    rijen = bouw_componentconfig()
    stmt = pg_insert(ComponentConfigOptie).values(rijen).on_conflict_do_nothing(
        index_elements=["dimensie", "optie_sleutel"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(rijen)
