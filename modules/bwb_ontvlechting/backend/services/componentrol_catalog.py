"""Catalogus-lookup/-validatie voor de platform-brede componentrol-catalogus (ADR-028 slice 1).

De tenant-sessie (`lk_app`) mag de platform-brede catalogus LEZEN (SELECT-grant). `componentrol`
op een component is NOT NULL (default `interne_applicatie`); validatie draait tegen de **actieve**
opties. Uitlezen resolvet ook gedeactiveerde sleutels (soft-deactivate-leespad). Spiegel van
`partijsoort_catalog`. Engine onaangeroerd — puur registratief.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import ComponentrolOptie
from services.errors import OngeldigeRegistratie


async def actieve_sleutels(session: AsyncSession) -> set[str]:
    rijen = (
        await session.execute(
            select(ComponentrolOptie.optie_sleutel).where(ComponentrolOptie.actief.is_(True))
        )
    ).scalars().all()
    return set(rijen)


async def actieve_opties(session: AsyncSession) -> list[dict]:
    """Actieve rollen voor het formulier-dropdown, op `volgorde`."""
    rijen = (
        await session.execute(
            select(ComponentrolOptie.optie_sleutel, ComponentrolOptie.label)
            .where(ComponentrolOptie.actief.is_(True))
            .order_by(ComponentrolOptie.volgorde, ComponentrolOptie.id)
        )
    ).all()
    return [{"optie_sleutel": r.optie_sleutel, "label": r.label} for r in rijen]


async def labels(session: AsyncSession) -> dict[str, tuple[str, bool]]:
    """`{optie_sleutel: (label, actief)}` voor ALLE opties (incl. inactieve) — leespad."""
    rijen = (
        await session.execute(select(ComponentrolOptie.optie_sleutel, ComponentrolOptie.label, ComponentrolOptie.actief))
    ).all()
    return {r.optie_sleutel: (r.label, r.actief) for r in rijen}


def resolveer_een(sleutel: str | None, label_map: dict[str, tuple[str, bool]]) -> str | None:
    """Resolveer één sleutel naar zijn label (fallback: de sleutel zelf). None ⇒ None."""
    if sleutel is None:
        return None
    return label_map.get(sleutel, (sleutel, False))[0]


async def valideer_rol(session: AsyncSession, rol: str | None) -> None:
    """None ⇒ ok (server_default vult). Onbekende/inactieve rol ⇒ 422 `ONGELDIGE_ROL`."""
    if rol is None:
        return
    if rol not in await actieve_sleutels(session):
        raise OngeldigeRegistratie(
            "ONGELDIGE_ROL", f"Onbekende of inactieve componentrol '{rol}'."
        )
