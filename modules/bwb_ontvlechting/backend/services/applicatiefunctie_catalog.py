"""Catalogus-lookup/-validatie voor de platform-brede applicatiefunctie-catalogus (ADR-042).

De tenant-sessie (`lk_app`) mag de platform-brede catalogus LEZEN (SELECT-grant). De
koppelregel (`procesvervulling.applicatiefunctie`) valideert tegen de **actieve** opties;
uitlezen resolvet ook gedeactiveerde sleutels (soft-deactivate-leespad — historische regels
blijven leesbaar). Spiegel van `componentrol_catalog`. Engine onaangeroerd.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import ApplicatiefunctieOptie
from services.errors import OngeldigeRegistratie


async def actieve_sleutels(session: AsyncSession) -> set[str]:
    rijen = (
        await session.execute(
            select(ApplicatiefunctieOptie.optie_sleutel).where(ApplicatiefunctieOptie.actief.is_(True))
        )
    ).scalars().all()
    return set(rijen)


async def actieve_opties(session: AsyncSession) -> list[dict]:
    """Actieve applicatiefuncties voor het keuze-dropdown, op `volgorde`."""
    rijen = (
        await session.execute(
            select(ApplicatiefunctieOptie.optie_sleutel, ApplicatiefunctieOptie.label)
            .where(ApplicatiefunctieOptie.actief.is_(True))
            .order_by(ApplicatiefunctieOptie.volgorde, ApplicatiefunctieOptie.id)
        )
    ).all()
    return [{"optie_sleutel": r.optie_sleutel, "label": r.label} for r in rijen]


async def labels(session: AsyncSession) -> dict[str, tuple[str, bool]]:
    """`{optie_sleutel: (label, actief)}` voor ALLE opties (incl. inactieve) — leespad."""
    rijen = (
        await session.execute(
            select(
                ApplicatiefunctieOptie.optie_sleutel,
                ApplicatiefunctieOptie.label,
                ApplicatiefunctieOptie.actief,
            )
        )
    ).all()
    return {r.optie_sleutel: (r.label, r.actief) for r in rijen}


def resolveer_een(sleutel: str | None, label_map: dict[str, tuple[str, bool]]) -> str | None:
    """Resolveer één sleutel naar zijn label (fallback: de sleutel zelf). None ⇒ None."""
    if sleutel is None:
        return None
    return label_map.get(sleutel, (sleutel, False))[0]


async def valideer_functie(session: AsyncSession, functie: str) -> None:
    """Onbekende/inactieve applicatiefunctie ⇒ 422 `ONGELDIGE_APPLICATIEFUNCTIE`."""
    if functie not in await actieve_sleutels(session):
        raise OngeldigeRegistratie(
            "ONGELDIGE_APPLICATIEFUNCTIE",
            f"Onbekende of inactieve applicatiefunctie '{functie}'.",
        )
