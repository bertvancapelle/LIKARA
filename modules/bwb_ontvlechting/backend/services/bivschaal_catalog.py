"""Catalogus-lookup/-validatie voor de platform-brede BIV-schaal-catalogus (ADR-028 slice 1).

De tenant-sessie (`lk_app`) mag de platform-brede catalogus LEZEN (SELECT-grant). De drie
BIV-velden op een component zijn optioneel (nullable) — validatie alleen wanneer een waarde is
opgegeven. ORDINAAL: `volgorde` is de rangdrager (laag<midden<hoog). Uitlezen resolvet ook
gedeactiveerde sleutels. Spiegel van `partijsoort_catalog`. Engine onaangeroerd — puur registratief.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import BivSchaalOptie
from services.errors import OngeldigeRegistratie


async def actieve_sleutels(session: AsyncSession) -> set[str]:
    rijen = (
        await session.execute(
            select(BivSchaalOptie.optie_sleutel).where(BivSchaalOptie.actief.is_(True))
        )
    ).scalars().all()
    return set(rijen)


async def actieve_opties(session: AsyncSession) -> list[dict]:
    """Actieve BIV-niveaus voor het formulier-dropdown, ordinaal op `volgorde`."""
    rijen = (
        await session.execute(
            select(BivSchaalOptie.optie_sleutel, BivSchaalOptie.label, BivSchaalOptie.volgorde)
            .where(BivSchaalOptie.actief.is_(True))
            .order_by(BivSchaalOptie.volgorde, BivSchaalOptie.id)
        )
    ).all()
    return [{"optie_sleutel": r.optie_sleutel, "label": r.label, "volgorde": r.volgorde} for r in rijen]


async def labels(session: AsyncSession) -> dict[str, tuple[str, bool]]:
    """`{optie_sleutel: (label, actief)}` voor ALLE opties (incl. inactieve) — leespad."""
    rijen = (
        await session.execute(select(BivSchaalOptie.optie_sleutel, BivSchaalOptie.label, BivSchaalOptie.actief))
    ).all()
    return {r.optie_sleutel: (r.label, r.actief) for r in rijen}


def resolveer_een(sleutel: str | None, label_map: dict[str, tuple[str, bool]]) -> str | None:
    """Resolveer één sleutel naar zijn label (fallback: de sleutel zelf). None ⇒ None."""
    if sleutel is None:
        return None
    return label_map.get(sleutel, (sleutel, False))[0]


async def valideer_niveau(session: AsyncSession, niveau: str | None) -> None:
    """None ⇒ ok (optioneel). Onbekend/inactief niveau ⇒ 422 `ONGELDIGE_BIV`."""
    if niveau is None:
        return
    if niveau not in await actieve_sleutels(session):
        raise OngeldigeRegistratie(
            "ONGELDIGE_BIV", f"Onbekende of inactieve BIV-waarde '{niveau}'."
        )
