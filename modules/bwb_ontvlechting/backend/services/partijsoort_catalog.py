"""Catalogus-lookup voor de platform-brede partijsoort-catalogus (ADR-024 slice 1).

De tenant-sessie (`cd_app`) mag de platform-brede catalogus LEZEN (SELECT-grant). `soort`
op een partij is **optioneel** (registratiegat) — validatie alleen wanneer een soort is
opgegeven. Spiegelt het bestaande catalogus-lookup-patroon (vraagbetekenis/componentconfig).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import PartijsoortOptie
from services.errors import OngeldigeRegistratie


async def actieve_sleutels(session: AsyncSession) -> set[str]:
    rijen = (
        await session.execute(
            select(PartijsoortOptie.optie_sleutel).where(PartijsoortOptie.actief.is_(True))
        )
    ).scalars().all()
    return set(rijen)


async def actieve_opties(session: AsyncSession) -> list[dict]:
    """Actieve soorten voor het formulier-dropdown, op `volgorde`."""
    rijen = (
        await session.execute(
            select(PartijsoortOptie.optie_sleutel, PartijsoortOptie.label)
            .where(PartijsoortOptie.actief.is_(True))
            .order_by(PartijsoortOptie.volgorde, PartijsoortOptie.id)
        )
    ).all()
    return [{"optie_sleutel": r.optie_sleutel, "label": r.label} for r in rijen]


async def valideer_soort(session: AsyncSession, soort: str | None) -> None:
    """None ⇒ ok (optioneel). Onbekende/inactieve soort ⇒ 422 `ONGELDIGE_SOORT`."""
    if soort is None:
        return
    if soort not in await actieve_sleutels(session):
        raise OngeldigeRegistratie(
            "ONGELDIGE_SOORT", f"Onbekende of inactieve partijsoort '{soort}'."
        )
