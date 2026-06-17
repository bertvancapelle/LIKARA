"""Service-laag — platform-beheer van de componentcatalogus (ADR-021 Besluit 8,
ADR-012 Addendum C). Spiegel van `contractconfig_service` op `get_platform_session`
(cd_platform). Geen hard delete (Addendum C + ontbrekende DB-grant — dubbele borging).

Systeem-sleutel-bescherming (Addendum C Besluit 5): de rij `componenttype.applicatie`
hangt aan het subtype-mechanisme (ADR-021) en kan NIET worden gedeactiveerd
(`actief=false` ⇒ 422 `SYSTEEM_SLEUTEL_BESCHERMD`). Label/volgorde wijzigen mag wél;
sleutel/dimensie zijn al generiek immutabel.
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import ComponentConfigDimensie, ComponentConfigOptie
from schemas.componentconfig import ComponentConfigOptieCreate, ComponentConfigOptieUpdate
from services.errors import ConfiguratieConflict, NietGevonden, OngeldigeRegistratie

_SYSTEEM_DIMENSIE = ComponentConfigDimensie.componenttype
_SYSTEEM_SLEUTEL = "applicatie"

# ADR-026 — de API-velden dragen het `archimate_`-voorvoegsel; de model-kolommen heten
# `archimate_element`/`laag`/`aspect`. Eén mapping voor create én update.
_TYPERING_MAP = {
    "archimate_element": "archimate_element",
    "archimate_laag": "laag",
    "archimate_aspect": "aspect",
}


async def lijst(session: AsyncSession, dimensie: str | None = None) -> list[ComponentConfigOptie]:
    stmt = select(ComponentConfigOptie)
    if dimensie:
        stmt = stmt.where(ComponentConfigOptie.dimensie == ComponentConfigDimensie(dimensie))
    stmt = stmt.order_by(
        ComponentConfigOptie.dimensie, ComponentConfigOptie.volgorde, ComponentConfigOptie.id
    )
    return list((await session.execute(stmt)).scalars().all())


async def _haal(session: AsyncSession, optie_id: int) -> ComponentConfigOptie:
    obj = (
        await session.execute(
            select(ComponentConfigOptie).where(ComponentConfigOptie.id == optie_id)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden("componentconfig_optie", optie_id)
    return obj


async def voeg_toe(session: AsyncSession, data: ComponentConfigOptieCreate) -> ComponentConfigOptie:
    """Voeg een optie toe. Duplicaat `(dimensie, optie_sleutel)` ⇒ 409. `volgorde`
    default = max(volgorde)+1 binnen de dimensie."""
    bestaat = (
        await session.execute(
            select(ComponentConfigOptie.id).where(
                ComponentConfigOptie.dimensie == data.dimensie,
                ComponentConfigOptie.optie_sleutel == data.optie_sleutel,
            )
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise ConfiguratieConflict("Een optie met deze sleutel bestaat al in deze dimensie.")

    if data.volgorde is None:
        huidige_max = (
            await session.execute(
                select(func.max(ComponentConfigOptie.volgorde)).where(
                    ComponentConfigOptie.dimensie == data.dimensie
                )
            )
        ).scalar_one()
        volgorde = 0 if huidige_max is None else huidige_max + 1
    else:
        volgorde = data.volgorde

    obj = ComponentConfigOptie(
        dimensie=data.dimensie,
        optie_sleutel=data.optie_sleutel,
        label=data.label,
        volgorde=volgorde,
        actief=True,
        # ADR-026 — typering meezetten (dicht het lek: voorheen bleven deze NULL). Voor
        # dimensie componenttype is volledigheid al door het schema afgedwongen; andere
        # dimensies leveren None.
        archimate_element=data.archimate_element,
        laag=data.archimate_laag,
        aspect=data.archimate_aspect,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def wijzig(
    session: AsyncSession, optie_id: int, data: ComponentConfigOptieUpdate
) -> ComponentConfigOptie:
    """Wijzig label / volgorde / actief. Soft-deactivate/reactivate toegestaan, BEHALVE
    deactiveren van de systeem-sleutel `componenttype.applicatie` (422
    `SYSTEEM_SLEUTEL_BESCHERMD`). Onbekend id ⇒ 404."""
    obj = await _haal(session, optie_id)
    velden = data.model_dump(exclude_unset=True)
    if (
        velden.get("actief") is False
        and obj.dimensie == _SYSTEEM_DIMENSIE
        and obj.optie_sleutel == _SYSTEEM_SLEUTEL
    ):
        raise OngeldigeRegistratie(
            "SYSTEEM_SLEUTEL_BESCHERMD",
            "Het componenttype 'applicatie' is een systeem-sleutel en kan niet worden gedeactiveerd.",
        )
    # ADR-026 Besluit 5 — typering corrigeren mag; LEEGMAKEN van een componenttype-typering
    # (expliciet None/'' meesturen) wordt geweigerd. Mappt de `archimate_`-API-velden op de
    # model-kolommen. De DB-CHECK (0025) is de backstop.
    for api_veld, model_veld in _TYPERING_MAP.items():
        if api_veld in velden:
            waarde = velden.pop(api_veld)
            if obj.dimensie == _SYSTEEM_DIMENSIE and not waarde:
                raise OngeldigeRegistratie(
                    "TYPERING_VERPLICHT",
                    "Een componenttype moet een volledige ArchiMate-typering houden; "
                    "de typering kan niet worden leeggemaakt.",
                )
            setattr(obj, model_veld, waarde)
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj
