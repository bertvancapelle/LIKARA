"""Service-laag — platform-beheer van de relatie-kenmerk-catalogus (ADR-023 Fase F / F-4).

Spiegel van `componentconfig_service` op `get_platform_session` (cd_platform). Beheert de
platform-brede referentiedata `relatiekenmerk_optie` (dimensies `dispositie`/`relatie_rol`).
Geen hard delete (geen endpoint + ontbrekende DB-grant = dubbele borging).

Anders dan componentconfig is er GEEN beschermde systeem-sleutel: álle waarden zijn
soft-deactiveerbaar (de catalog resolvet labels óók voor inactieve waarden, dus bestaande
relaties blijven correct weergegeven; een gedeactiveerde waarde verdwijnt alleen uit nieuwe
dropdowns). `optie_sleutel`/`dimensie` zijn generiek immutabel (niet in het Update-schema).
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import RelatieKenmerkDimensie, RelatieKenmerkOptie
from schemas.relatiekenmerkconfig import RelatieKenmerkOptieCreate, RelatieKenmerkOptieUpdate
from services.errors import ConfiguratieConflict, NietGevonden


async def lijst(session: AsyncSession, dimensie: str | None = None) -> list[RelatieKenmerkOptie]:
    stmt = select(RelatieKenmerkOptie)
    if dimensie:
        stmt = stmt.where(RelatieKenmerkOptie.dimensie == RelatieKenmerkDimensie(dimensie))
    stmt = stmt.order_by(
        RelatieKenmerkOptie.dimensie, RelatieKenmerkOptie.volgorde, RelatieKenmerkOptie.id
    )
    return list((await session.execute(stmt)).scalars().all())


async def _haal(session: AsyncSession, optie_id: int) -> RelatieKenmerkOptie:
    obj = (
        await session.execute(
            select(RelatieKenmerkOptie).where(RelatieKenmerkOptie.id == optie_id)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden("relatiekenmerk_optie", optie_id)
    return obj


async def voeg_toe(session: AsyncSession, data: RelatieKenmerkOptieCreate) -> RelatieKenmerkOptie:
    """Voeg een optie toe. Duplicaat `(dimensie, optie_sleutel)` ⇒ 409. `volgorde`
    default = max(volgorde)+1 binnen de dimensie."""
    bestaat = (
        await session.execute(
            select(RelatieKenmerkOptie.id).where(
                RelatieKenmerkOptie.dimensie == data.dimensie,
                RelatieKenmerkOptie.optie_sleutel == data.optie_sleutel,
            )
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise ConfiguratieConflict("Een optie met deze sleutel bestaat al in deze dimensie.")

    if data.volgorde is None:
        huidige_max = (
            await session.execute(
                select(func.max(RelatieKenmerkOptie.volgorde)).where(
                    RelatieKenmerkOptie.dimensie == data.dimensie
                )
            )
        ).scalar_one()
        volgorde = 0 if huidige_max is None else huidige_max + 1
    else:
        volgorde = data.volgorde

    obj = RelatieKenmerkOptie(
        dimensie=data.dimensie,
        optie_sleutel=data.optie_sleutel,
        label=data.label,
        volgorde=volgorde,
        actief=True,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def wijzig(
    session: AsyncSession, optie_id: int, data: RelatieKenmerkOptieUpdate
) -> RelatieKenmerkOptie:
    """Wijzig label / volgorde / actief. Soft-deactivate én reactivate vrij toegestaan
    (geen beschermde sleutel). Onbekend id ⇒ 404."""
    obj = await _haal(session, optie_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj
