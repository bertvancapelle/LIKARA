"""Service-laag voor de entiteit Gebruikersgroep (ADR-009; ADR-023 B-mig-2 slice 4).

ADR-023: gebruikersgroep is een **zelfstandig element** (business actor/role); de band met de
applicatie is een **serving**-relatie (applicatie → gebruikersgroep), niet langer een
`applicatie_id`-kolom. De API blijft stabiel: `applicatie_id` wordt afgeleid uit de
serving-relatie. CASCADE-wijziging (Besluit 13): een applicatie verwijderen laat de
gebruikersgroep bestaan — alleen de relatie vervalt.
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Element, ElementType, Gebruikersgroep, Relatie
from schemas.gebruikersgroep import GebruikersgroepCreate, GebruikersgroepUpdate
from services import applicatie_service
from services.errors import NietGevonden
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "gebruikersgroep"
_SERVING = "serving"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"

_SORTEERBARE_KOLOMMEN = {
    "created_at": Gebruikersgroep.created_at,
    "organisatie": Gebruikersgroep.organisatie,
    "afdeling": Gebruikersgroep.afdeling,
    "aantal_gebruikers": Gebruikersgroep.aantal_gebruikers,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "organisatie": str,
    "afdeling": str,
    "aantal_gebruikers": int,
}


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _lees(obj: Gebruikersgroep, applicatie_id) -> dict:
    """API-vorm (applicatie_id afgeleid uit de serving-relatie; None = wees)."""
    return {
        "id": obj.id, "applicatie_id": applicatie_id, "organisatie": obj.organisatie,
        "afdeling": obj.afdeling, "aantal_gebruikers": obj.aantal_gebruikers,
        "created_at": obj.created_at, "updated_at": obj.updated_at,
    }


async def _applicaties_van(session: AsyncSession, tid: uuid.UUID, ids: list) -> dict:
    if not ids:
        return {}
    rijen = (
        await session.execute(
            select(Relatie.doel_id, Relatie.bron_id).where(
                Relatie.tenant_id == tid, Relatie.relatietype == _SERVING, Relatie.doel_id.in_(ids)
            )
        )
    ).all()
    return {r.doel_id: r.bron_id for r in rijen}


async def lijst(
    session: AsyncSession, tenant_id, *, limit: int = _STANDAARD_LIMIT, after: str | None = None,
    applicatie_id: uuid.UUID | None = None, sort: str = _STANDAARD_SORT, order: str = _STANDAARD_ORDER,
) -> tuple[list[dict], str | None]:
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)
    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]

    stmt = select(Gebruikersgroep).where(Gebruikersgroep.tenant_id == tid)
    if applicatie_id is not None:
        stmt = stmt.join(
            Relatie,
            and_(
                Relatie.doel_id == Gebruikersgroep.id, Relatie.tenant_id == tid,
                Relatie.relatietype == _SERVING, Relatie.bron_id == applicatie_id,
            ),
        )
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(kolom, Gebruikersgroep.id, order=order, is_null=c_is_null, waarde=c_waarde, cursor_id=c_id)
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Gebruikersgroep.id, order)).limit(limit + 1)

    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    app_map = await _applicaties_van(session, tid, [g.id for g in items])
    out = [_lees(g, app_map.get(g.id)) for g in items]
    volgende = (
        encode_sort_cursor_nullable(sort=sort, order=order, waarde=getattr(items[-1], kolom.key), id=items[-1].id)
        if heeft_meer else None
    )
    return out, volgende


async def haal_op(session: AsyncSession, tenant_id, gebruikersgroep_id) -> Gebruikersgroep:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Gebruikersgroep).where(
                Gebruikersgroep.id == gebruikersgroep_id, Gebruikersgroep.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, gebruikersgroep_id)
    return obj


async def lees_detail(session: AsyncSession, tenant_id, gebruikersgroep_id) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, gebruikersgroep_id)
    app_map = await _applicaties_van(session, tid, [obj.id])
    return _lees(obj, app_map.get(obj.id))


async def maak_aan(session: AsyncSession, tenant_id, data: GebruikersgroepCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    await applicatie_service.haal_op(session, tenant_id, data.applicatie_id)  # ouder 404 buiten tenant
    velden = data.model_dump(exclude={"applicatie_id"})
    elem = Element(tenant_id=tid, element_type=ElementType.gebruikersgroep)
    session.add(elem)
    await session.flush()
    obj = Gebruikersgroep(id=elem.id, tenant_id=tid, **velden)
    session.add(obj)
    session.add(Relatie(tenant_id=tid, bron_id=data.applicatie_id, doel_id=elem.id, relatietype=_SERVING))
    await session.commit()
    await session.refresh(obj)
    return _lees(obj, data.applicatie_id)


async def werk_bij(session: AsyncSession, tenant_id, gebruikersgroep_id, data: GebruikersgroepUpdate) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, gebruikersgroep_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    app_map = await _applicaties_van(session, tid, [obj.id])
    return _lees(obj, app_map.get(obj.id))


async def verwijder(session: AsyncSession, tenant_id, gebruikersgroep_id) -> None:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, gebruikersgroep_id)
    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == gebruikersgroep_id))
    await session.commit()
