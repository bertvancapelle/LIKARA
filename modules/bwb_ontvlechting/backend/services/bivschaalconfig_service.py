"""Service-laag — platform-beheer van de BIV-schaal-catalogus (ADR-028 slice 1).

Enkel-doel (geen `dimensie`), spiegel van `partijsoortconfig_service` op `get_platform_session`
(lk_platform). Beheert `biv_schaal_optie`. Geen hard delete; soft-deactivate via `actief`.
Geen systeem-sleutel (elke optie deactiveerbaar/uitbreidbaar). ORDINAAL: `volgorde` is de
rangdrager — nieuwe niveaus krijgen hun plek via `volgorde` (default max+1).
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import BivSchaalOptie
from schemas.bivschaalconfig import BivSchaalOptieCreate, BivSchaalOptieUpdate
from services.errors import ConfiguratieConflict, NietGevonden


async def lijst(session: AsyncSession) -> list[BivSchaalOptie]:
    stmt = select(BivSchaalOptie).order_by(BivSchaalOptie.volgorde, BivSchaalOptie.id)
    return list((await session.execute(stmt)).scalars().all())


async def _haal(session: AsyncSession, optie_id: int) -> BivSchaalOptie:
    obj = (
        await session.execute(select(BivSchaalOptie).where(BivSchaalOptie.id == optie_id))
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden("biv_schaal_optie", optie_id)
    return obj


async def voeg_toe(session: AsyncSession, data: BivSchaalOptieCreate) -> BivSchaalOptie:
    """Voeg een optie toe. Duplicaat `optie_sleutel` ⇒ 409. `volgorde` default = max+1
    (nieuw niveau achteraan de ordinale schaal)."""
    bestaat = (
        await session.execute(
            select(BivSchaalOptie.id).where(BivSchaalOptie.optie_sleutel == data.optie_sleutel)
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise ConfiguratieConflict("Een optie met deze sleutel bestaat al.")

    if data.volgorde is None:
        huidige_max = (await session.execute(select(func.max(BivSchaalOptie.volgorde)))).scalar_one()
        volgorde = 0 if huidige_max is None else huidige_max + 1
    else:
        volgorde = data.volgorde

    obj = BivSchaalOptie(
        optie_sleutel=data.optie_sleutel, label=data.label, volgorde=volgorde, actief=True
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def wijzig(session: AsyncSession, optie_id: int, data: BivSchaalOptieUpdate) -> BivSchaalOptie:
    """Wijzig label / volgorde / actief. Soft-deactivate én reactivate vrij. Onbekend id ⇒ 404."""
    obj = await _haal(session, optie_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj
