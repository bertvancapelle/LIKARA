"""Catalogus-lookup/-validatie voor de relatie-kenmerk-vocabulaire (ADR-023 Fase E).

Spiegel van `contractconfig_catalog`, maar voor de platform-brede catalogus
`relatiekenmerk_optie` — de algemene plek voor beheerbare relatie-kenmerk-waardenlijsten
(nu `dispositie`), losgekoppeld van de contract-configuratie. De tenant-sessie (`cd_app`)
mag deze catalogus LEZEN (SELECT-grant). Valideren tegen de **actieve** opties van de
**juiste dimensie**; uitlezen resolvet ook gedeactiveerde sleutels (historie).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import RelatieKenmerkDimensie, RelatieKenmerkOptie
from services.errors import OngeldigeRegistratie


async def _opties(session: AsyncSession, dimensie: RelatieKenmerkDimensie, *, alleen_actief: bool):
    stmt = select(
        RelatieKenmerkOptie.optie_sleutel,
        RelatieKenmerkOptie.label,
        RelatieKenmerkOptie.actief,
    ).where(RelatieKenmerkOptie.dimensie == dimensie)
    if alleen_actief:
        stmt = stmt.where(RelatieKenmerkOptie.actief.is_(True))
    return list((await session.execute(stmt)).all())


async def actieve_sleutels(session: AsyncSession, dimensie: RelatieKenmerkDimensie) -> set[str]:
    return {r.optie_sleutel for r in await _opties(session, dimensie, alleen_actief=True)}


async def labels(
    session: AsyncSession, dimensie: RelatieKenmerkDimensie
) -> dict[str, tuple[str, bool]]:
    """`{optie_sleutel: (label, actief)}` voor ALLE opties (incl. inactieve)."""
    return {r.optie_sleutel: (r.label, r.actief) for r in await _opties(session, dimensie, alleen_actief=False)}


async def valideer_sleutels(
    session: AsyncSession, dimensie: RelatieKenmerkDimensie, sleutels: list[str]
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


def resolveer_een(sleutel: str, label_map: dict[str, tuple[str, bool]]) -> str:
    """Resolveer één sleutel naar zijn label (fallback: de sleutel zelf)."""
    return label_map.get(sleutel, (sleutel, False))[0]


async def actieve_opties_per_dimensie(session: AsyncSession) -> dict[str, list[dict]]:
    """Actieve opties per dimensie (beheer-/formuliergebruik), per dimensie gesorteerd op
    `volgorde`. Alleen-actief."""
    rijen = (
        await session.execute(
            select(
                RelatieKenmerkOptie.dimensie,
                RelatieKenmerkOptie.optie_sleutel,
                RelatieKenmerkOptie.label,
                RelatieKenmerkOptie.volgorde,
            )
            .where(RelatieKenmerkOptie.actief.is_(True))
            .order_by(
                RelatieKenmerkOptie.dimensie,
                RelatieKenmerkOptie.volgorde,
                RelatieKenmerkOptie.id,
            )
        )
    ).all()
    uit: dict[str, list[dict]] = {d.value: [] for d in RelatieKenmerkDimensie}
    for r in rijen:
        dim = r.dimensie.value if hasattr(r.dimensie, "value") else str(r.dimensie)
        uit[dim].append(
            {"optie_sleutel": r.optie_sleutel, "label": r.label, "volgorde": r.volgorde}
        )
    return uit
