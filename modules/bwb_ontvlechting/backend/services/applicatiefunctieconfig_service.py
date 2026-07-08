"""Service-laag — platform-beheer van de applicatiefunctie-catalogus (ADR-042 slice 2).

Enkel-doel (geen `dimensie`), spiegel van `componentrolconfig_service` op
`get_platform_session` (lk_platform). Beheert `applicatiefunctie_optie`. Geen hard delete;
soft-deactivate via `actief`. Er is GEEN systeem-sleutel (elke optie is deactiveerbaar —
ADR-042 besluit 3: niets is verplicht); historische koppelregels blijven leesbaar omdat de
tenant-leeszijde óók gedeactiveerde sleutels resolvet.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import ApplicatiefunctieOptie
from schemas.applicatiefunctieconfig import (
    ApplicatiefunctieOptieCreate,
    ApplicatiefunctieOptieUpdate,
)
from services.errors import ConfiguratieConflict, NietGevonden


async def lijst(session: AsyncSession) -> list[ApplicatiefunctieOptie]:
    stmt = select(ApplicatiefunctieOptie).order_by(
        ApplicatiefunctieOptie.volgorde, ApplicatiefunctieOptie.id
    )
    return list((await session.execute(stmt)).scalars().all())


async def _haal(session: AsyncSession, optie_id: int) -> ApplicatiefunctieOptie:
    obj = (
        await session.execute(
            select(ApplicatiefunctieOptie).where(ApplicatiefunctieOptie.id == optie_id)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden("applicatiefunctie_optie", optie_id)
    return obj


async def voeg_toe(session: AsyncSession, data: ApplicatiefunctieOptieCreate) -> ApplicatiefunctieOptie:
    """Voeg een optie toe. Duplicaat `optie_sleutel` ⇒ 409. `volgorde` default = max+1."""
    bestaat = (
        await session.execute(
            select(ApplicatiefunctieOptie.id).where(
                ApplicatiefunctieOptie.optie_sleutel == data.optie_sleutel
            )
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise ConfiguratieConflict("Een optie met deze sleutel bestaat al.")

    if data.volgorde is None:
        huidige_max = (
            await session.execute(select(func.max(ApplicatiefunctieOptie.volgorde)))
        ).scalar_one()
        volgorde = 0 if huidige_max is None else huidige_max + 1
    else:
        volgorde = data.volgorde

    obj = ApplicatiefunctieOptie(
        optie_sleutel=data.optie_sleutel, label=data.label, volgorde=volgorde, actief=True
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def wijzig(
    session: AsyncSession, optie_id: int, data: ApplicatiefunctieOptieUpdate
) -> ApplicatiefunctieOptie:
    """Wijzig label / volgorde / actief. Onbekend id ⇒ 404. Geen systeem-sleutel —
    elke optie mag gedeactiveerd worden (soft-deactivate; nooit hard weg)."""
    obj = await _haal(session, optie_id)
    velden = data.model_dump(exclude_unset=True)
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj
