"""Service-laag — platform-beheer van het referentiemodel-aanbod (gate 1b §2.1).

Spiegel van `applicatiefunctieconfig_service` op `get_platform_session` (lk_platform),
zónder `voeg_toe`: het aanbod is gesloten (repo-route — nieuw aanbod = release-curatie,
zie `referentiemodellen/HERKOMST.md`). Beheert `referentiemodel_optie`: label/volgorde/
actief (soft-deactivate; geen hard delete). Raakt tenant-data niet; voedt de engine niet.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import ReferentiemodelOptie
from schemas.referentiemodelconfig import ReferentiemodelOptieUpdate
from services.errors import NietGevonden


async def lijst(session: AsyncSession) -> list[ReferentiemodelOptie]:
    stmt = select(ReferentiemodelOptie).order_by(
        ReferentiemodelOptie.volgorde, ReferentiemodelOptie.id
    )
    return list((await session.execute(stmt)).scalars().all())


async def wijzig(
    session: AsyncSession, optie_id: int, data: ReferentiemodelOptieUpdate
) -> ReferentiemodelOptie:
    """Wijzig label / volgorde / actief. Onbekend id ⇒ 404. Sleutel, herkomst en versie
    zijn de gecureerde identiteit (niet in het Update-schema)."""
    obj = (
        await session.execute(
            select(ReferentiemodelOptie).where(ReferentiemodelOptie.id == optie_id)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden("referentiemodel_optie", optie_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj
