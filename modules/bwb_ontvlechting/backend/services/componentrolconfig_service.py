"""Service-laag — platform-beheer van de componentrol-catalogus (ADR-028 slice 1).

Enkel-doel (geen `dimensie`), spiegel van `partijsoortconfig_service` op `get_platform_session`
(lk_platform). Beheert `componentrol_optie`. Geen hard delete; soft-deactivate via `actief`.
Systeem-sleutel `interne_applicatie` (de beschermde default) is NIET deactiveerbaar
(⇒ 422 `SYSTEEM_SLEUTEL_BESCHERMD`); label/volgorde wijzigen mag wél.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import ComponentrolOptie
from schemas.componentrolconfig import ComponentrolOptieCreate, ComponentrolOptieUpdate
from services.errors import ConfiguratieConflict, NietGevonden, OngeldigeRegistratie

_SYSTEEM_SLEUTEL = "interne_applicatie"


async def lijst(session: AsyncSession) -> list[ComponentrolOptie]:
    stmt = select(ComponentrolOptie).order_by(ComponentrolOptie.volgorde, ComponentrolOptie.id)
    return list((await session.execute(stmt)).scalars().all())


async def _haal(session: AsyncSession, optie_id: int) -> ComponentrolOptie:
    obj = (
        await session.execute(select(ComponentrolOptie).where(ComponentrolOptie.id == optie_id))
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden("componentrol_optie", optie_id)
    return obj


async def voeg_toe(session: AsyncSession, data: ComponentrolOptieCreate) -> ComponentrolOptie:
    """Voeg een optie toe. Duplicaat `optie_sleutel` ⇒ 409. `volgorde` default = max+1."""
    bestaat = (
        await session.execute(
            select(ComponentrolOptie.id).where(ComponentrolOptie.optie_sleutel == data.optie_sleutel)
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise ConfiguratieConflict("Een optie met deze sleutel bestaat al.")

    if data.volgorde is None:
        huidige_max = (await session.execute(select(func.max(ComponentrolOptie.volgorde)))).scalar_one()
        volgorde = 0 if huidige_max is None else huidige_max + 1
    else:
        volgorde = data.volgorde

    obj = ComponentrolOptie(
        optie_sleutel=data.optie_sleutel, label=data.label, volgorde=volgorde, actief=True
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def wijzig(session: AsyncSession, optie_id: int, data: ComponentrolOptieUpdate) -> ComponentrolOptie:
    """Wijzig label / volgorde / actief. Onbekend id ⇒ 404. De systeem-sleutel
    `interne_applicatie` mag NIET gedeactiveerd worden (⇒ 422 `SYSTEEM_SLEUTEL_BESCHERMD`)."""
    obj = await _haal(session, optie_id)
    velden = data.model_dump(exclude_unset=True)
    if velden.get("actief") is False and obj.optie_sleutel == _SYSTEEM_SLEUTEL:
        raise OngeldigeRegistratie(
            "SYSTEEM_SLEUTEL_BESCHERMD",
            "De componentrol 'interne_applicatie' is een systeem-sleutel en kan niet worden gedeactiveerd.",
        )
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj
