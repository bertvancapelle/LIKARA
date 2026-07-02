"""Service-laag voor de entiteit Datatype (ADR-009; ADR-023 B-mig-2 slice 4).

ADR-023: datatype is een **zelfstandig element** (data object); de band met de applicatie
is een **access**-relatie (applicatie → datatype), niet langer een `applicatie_id`-kolom.
De API blijft stabiel: `applicatie_id` wordt afgeleid uit de access-relatie. CASCADE-wijziging
(Besluit 13): een applicatie verwijderen laat het datatype bestaan — alleen de relatie vervalt.
Tenant-bescherming: RLS + expliciete `tenant_id`-filter; ouder buiten de tenant ⇒ 404 (OP-6).
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Datatype, DatatypeCategorie, Element, ElementType, Relatie
from schemas.datatype import DatatypeCreate, DatatypeUpdate
from services import component_service

_APPLICATIE_TYPE = "applicatie"
from services.errors import NietGevonden
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "datatype"
_ACCESS = "access"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"

_SORTEERBARE_KOLOMMEN = {
    "created_at": Datatype.created_at,
    "categorie": Datatype.categorie,
    "omschrijving": Datatype.omschrijving,
    "omvang_indicatie": Datatype.omvang_indicatie,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "categorie": DatatypeCategorie,
    "omschrijving": str,
    "omvang_indicatie": str,
}


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def enum_opties() -> dict[str, list[str]]:
    return {"categorie": [e.value for e in DatatypeCategorie]}


def _lees(obj: Datatype, applicatie_id) -> dict:
    """API-vorm (applicatie_id afgeleid uit de access-relatie; kan None zijn = 'wees')."""
    return {
        "id": obj.id, "applicatie_id": applicatie_id, "categorie": obj.categorie,
        "omschrijving": obj.omschrijving, "omvang_indicatie": obj.omvang_indicatie,
        "created_at": obj.created_at, "updated_at": obj.updated_at,
    }


async def _applicaties_van(session: AsyncSession, tid: uuid.UUID, ids: list) -> dict:
    """{datatype_id: applicatie_id} uit de access-relaties (doel = datatype)."""
    if not ids:
        return {}
    rijen = (
        await session.execute(
            select(Relatie.doel_id, Relatie.bron_id).where(
                Relatie.tenant_id == tid, Relatie.relatietype == _ACCESS, Relatie.doel_id.in_(ids)
            )
        )
    ).all()
    return {r.doel_id: r.bron_id for r in rijen}


async def lijst(
    session: AsyncSession, tenant_id, *, limit: int = _STANDAARD_LIMIT, after: str | None = None,
    applicatie_id: uuid.UUID | None = None, sort: str = _STANDAARD_SORT, order: str = _STANDAARD_ORDER,
) -> tuple[list[dict], str | None]:
    """Keyset-lijst binnen de tenant; optioneel gefilterd op de applicatie (access-relatie)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)
    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]

    stmt = select(Datatype).where(Datatype.tenant_id == tid)
    if applicatie_id is not None:
        stmt = stmt.join(
            Relatie,
            and_(
                Relatie.doel_id == Datatype.id, Relatie.tenant_id == tid,
                Relatie.relatietype == _ACCESS, Relatie.bron_id == applicatie_id,
            ),
        )
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(kolom, Datatype.id, order=order, is_null=c_is_null, waarde=c_waarde, cursor_id=c_id)
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Datatype.id, order)).limit(limit + 1)

    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    app_map = await _applicaties_van(session, tid, [d.id for d in items])
    out = [_lees(d, app_map.get(d.id)) for d in items]
    volgende = (
        encode_sort_cursor_nullable(sort=sort, order=order, waarde=getattr(items[-1], kolom.key), id=items[-1].id)
        if heeft_meer else None
    )
    return out, volgende


async def haal_op(session: AsyncSession, tenant_id, datatype_id) -> Datatype:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Datatype).where(Datatype.id == datatype_id, Datatype.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, datatype_id)
    return obj


async def lees_detail(session: AsyncSession, tenant_id, datatype_id) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, datatype_id)
    app_map = await _applicaties_van(session, tid, [obj.id])
    return _lees(obj, app_map.get(obj.id))


async def maak_aan(session: AsyncSession, tenant_id, data: DatatypeCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    # LI059 Slice 3: ouder is een component met type 'applicatie' (geen subtabel meer).
    # Zelfde 404-no-leak: buiten tenant / niet-applicatie ⇒ NietGevonden.
    _ouder = await component_service.haal_op(session, tenant_id, data.applicatie_id)
    if _ouder.componenttype != _APPLICATIE_TYPE:
        raise NietGevonden(_APPLICATIE_TYPE, data.applicatie_id)
    velden = data.model_dump(exclude={"applicatie_id"})
    # ADR-023: element-identiteit eerst (shared-PK), dan datatype, dan de access-relatie.
    elem = Element(tenant_id=tid, element_type=ElementType.datatype)
    session.add(elem)
    await session.flush()
    obj = Datatype(id=elem.id, tenant_id=tid, **velden)
    session.add(obj)
    session.add(Relatie(tenant_id=tid, bron_id=data.applicatie_id, doel_id=elem.id, relatietype=_ACCESS))
    await session.commit()
    await session.refresh(obj)
    return _lees(obj, data.applicatie_id)


async def werk_bij(session: AsyncSession, tenant_id, datatype_id, data: DatatypeUpdate) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, datatype_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    app_map = await _applicaties_van(session, tid, [obj.id])
    return _lees(obj, app_map.get(obj.id))


async def verwijder(session: AsyncSession, tenant_id, datatype_id) -> None:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, datatype_id)  # 404 kruis-tenant
    # ADR-023: verwijder via het element (cascade datatype + access-relatie).
    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == datatype_id))
    await session.commit()
