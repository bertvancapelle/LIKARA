"""Service-laag voor de entiteit Leverancier (ADR-020 Besluit 1).

Tenant-scoped (RLS + expliciet `tenant_id`-filter); record buiten de tenant ⇒
`NietGevonden` (404, OP-6). Puur registratief — geen afgeleide logica, geen
engine-koppeling. v2n-keyset-paginering (ADR-017; `plaats` nullable).
"""
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Contract, Leverancier
from schemas.leverancier import LeverancierCreate, LeverancierUpdate
from services.errors import NietGevonden, RegistratieConflict
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "leverancier"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"

_SORTEERBARE_KOLOMMEN = {
    "created_at": Leverancier.created_at,
    "naam": Leverancier.naam,
    "plaats": Leverancier.plaats,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "naam": str,
    "plaats": str,
}

_LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    return term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    sort: str = _STANDAARD_SORT,
    order: str = _STANDAARD_ORDER,
    zoek: str | None = None,
) -> tuple[list[Leverancier], str | None]:
    """v2n-keyset-lijst binnen de tenant. `zoek` = ge-escapete ILIKE op `naam`."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]

    stmt = select(Leverancier).where(Leverancier.tenant_id == tid)
    if zoek:
        stmt = stmt.where(Leverancier.naam.ilike(f"%{_escape_like(zoek)}%", escape=_LIKE_ESCAPE))
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, Leverancier.id, order=order, is_null=c_is_null, waarde=c_waarde, cursor_id=c_id
            )
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Leverancier.id, order)).limit(limit + 1)

    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor_nullable(sort=sort, order=order, waarde=getattr(items[-1], sort), id=items[-1].id)
        if heeft_meer
        else None
    )
    return items, volgende


async def haal_op(session: AsyncSession, tenant_id, leverancier_id) -> Leverancier:
    tid = _tenant_uuid(tenant_id)
    stmt = select(Leverancier).where(
        Leverancier.id == leverancier_id, Leverancier.tenant_id == tid
    )
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, leverancier_id)
    return obj


async def maak_aan(session: AsyncSession, tenant_id, data: LeverancierCreate) -> Leverancier:
    tid = _tenant_uuid(tenant_id)
    obj = Leverancier(tenant_id=tid, **data.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def werk_bij(
    session: AsyncSession, tenant_id, leverancier_id, data: LeverancierUpdate
) -> Leverancier:
    obj = await haal_op(session, tenant_id, leverancier_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj


async def verwijder(session: AsyncSession, tenant_id, leverancier_id) -> None:
    """Verwijder binnen de tenant. Een leverancier met contracten wordt geweigerd
    (409 `IN_GEBRUIK`) — nette app-fout vóór de FK `RESTRICT` (I4)."""
    obj = await haal_op(session, tenant_id, leverancier_id)
    tid = _tenant_uuid(tenant_id)
    aantal = (
        await session.execute(
            select(func.count())
            .select_from(Contract)
            .where(Contract.tenant_id == tid, Contract.leverancier_id == leverancier_id)
        )
    ).scalar_one()
    if aantal:
        raise RegistratieConflict(
            "IN_GEBRUIK", "Deze leverancier heeft nog contracten en kan niet worden verwijderd."
        )
    await session.delete(obj)
    await session.commit()
