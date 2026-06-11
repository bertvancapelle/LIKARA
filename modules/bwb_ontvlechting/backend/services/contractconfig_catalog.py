"""Catalogus-lookup/-validatie voor het contractregister (ADR-020 Besluit 6/10).

De tenant-sessie (`cd_app`) mag de platform-brede catalogus `contractconfig_optie`
LEZEN (SELECT-grant, CD040 geverifieerd). Bij opslaan worden sleutels gevalideerd
tegen de **actieve** opties van de **juiste dimensie**; bij uitlezen resolvet elke
opgeslagen sleutel — ook een gedeactiveerde — naar zijn label, zodat historische
registraties leesbaar blijven (analoog aan ADR-019 fase 2B).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import ContractConfigDimensie, ContractConfigOptie
from services.errors import OngeldigeRegistratie


async def _opties(session: AsyncSession, dimensie: ContractConfigDimensie, *, alleen_actief: bool):
    stmt = select(
        ContractConfigOptie.optie_sleutel,
        ContractConfigOptie.label,
        ContractConfigOptie.actief,
    ).where(ContractConfigOptie.dimensie == dimensie)
    if alleen_actief:
        stmt = stmt.where(ContractConfigOptie.actief.is_(True))
    return list((await session.execute(stmt)).all())


async def actieve_sleutels(session: AsyncSession, dimensie: ContractConfigDimensie) -> set[str]:
    """De sleutels van de actieve opties binnen de dimensie."""
    return {r.optie_sleutel for r in await _opties(session, dimensie, alleen_actief=True)}


async def labels(
    session: AsyncSession, dimensie: ContractConfigDimensie
) -> dict[str, tuple[str, bool]]:
    """`{optie_sleutel: (label, actief)}` voor ALLE opties (incl. inactieve)."""
    return {r.optie_sleutel: (r.label, r.actief) for r in await _opties(session, dimensie, alleen_actief=False)}


async def valideer_sleutels(
    session: AsyncSession, dimensie: ContractConfigDimensie, sleutels: list[str]
) -> None:
    """Weiger onbekende/inactieve/verkeerd-gedimensioneerde sleutels ⇒ 422 `ONGELDIGE_OPTIE`."""
    if not sleutels:
        return
    actief = await actieve_sleutels(session, dimensie)
    ongeldig = [s for s in sleutels if s not in actief]
    if ongeldig:
        raise OngeldigeRegistratie(
            "ONGELDIGE_OPTIE",
            f"Onbekende of inactieve optie(s) voor dimensie '{dimensie.value}': "
            f"{', '.join(sorted(ongeldig))}.",
        )


def resolveer(sleutels: list[str], label_map: dict[str, tuple[str, bool]]) -> list[dict]:
    """Map opgeslagen sleutels naar `{optie_sleutel, label, actief}` (volgorde-stabiel).
    Een sleutel die (uitzonderlijk) niet meer in de catalogus staat, valt terug op
    zichzelf als label met `actief=False`."""
    out: list[dict] = []
    for s in sleutels:
        label, actief = label_map.get(s, (s, False))
        out.append({"optie_sleutel": s, "label": label, "actief": actief})
    return out


def resolveer_een(sleutel: str, label_map: dict[str, tuple[str, bool]]) -> str:
    """Resolveer één sleutel naar zijn label (fallback: de sleutel zelf)."""
    return label_map.get(sleutel, (sleutel, False))[0]
