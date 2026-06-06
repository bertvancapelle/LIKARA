"""Service-laag voor de entiteit Applicatie (P5, ADR-009).

Bevat alle business-logica; de route-handlers blijven dun. Elke query draait
binnen de tenant-sessie (RLS-context via `get_tenant_session`) ÉN filtert
expliciet op `tenant_id` — dubbele tenant-bescherming (complidata-security).

OP-6 (tenant-scoped, besluit Bert): record-resolutie strikt binnen de tenant.
Een id buiten de tenant is niet vindbaar (RLS + expliciete filter) ⇒ `NietGevonden`
(HTTP 404). Geen onderscheid 'bestaat niet' vs 'andere tenant' — geen lek.

Lifecycle (ADR-009): nieuw ⇒ `concept`. In P5 is uitsluitend de overgang
`concept → in_inventarisatie` afdwingbaar. De afgeleide statussen
`geblokkeerd`/`migratieklaar` vallen BUITEN scope — die worden herberekend
zodra Checklistscore-/Blokkade-CRUD bestaat.
"""
import uuid

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Applicatie, LifecycleStatus
from schemas.applicatie import ApplicatieCreate, ApplicatieUpdate
from services.errors import NietGevonden, OngeldigeStatusovergang
from services.pagination import decode_cursor, encode_cursor

_ENTITEIT = "applicatie"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100


def _tenant_uuid(tenant_id) -> uuid.UUID:
    """Normaliseer de tenant-id (uit de sessie een str) naar UUID."""
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def volgende_status_na_start(huidige: LifecycleStatus) -> LifecycleStatus:
    """Pure overgangsregel voor 'start inventarisatie'.

    Alleen `concept → in_inventarisatie` is geldig; elke andere uitgangsstatus
    levert `OngeldigeStatusovergang`. Apart en puur gehouden, zodat de regel
    zonder DB testbaar is.
    """
    if huidige != LifecycleStatus.concept:
        raise OngeldigeStatusovergang(huidige, LifecycleStatus.in_inventarisatie)
    return LifecycleStatus.in_inventarisatie


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
) -> tuple[list[Applicatie], str | None]:
    """Cursor-gepagineerde lijst binnen de tenant, gesorteerd op (created_at, id).

    Returnt `(items, volgende_cursor)`; `volgende_cursor` is None op de laatste
    pagina. Een ongeldige `after`-cursor levert `ValueError` (route ⇒ 400).
    """
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    stmt = select(Applicatie).where(Applicatie.tenant_id == tid)
    if after:
        cursor_created_at, cursor_id = decode_cursor(after)
        stmt = stmt.where(
            tuple_(Applicatie.created_at, Applicatie.id) > (cursor_created_at, cursor_id)
        )
    stmt = stmt.order_by(Applicatie.created_at, Applicatie.id).limit(limit + 1)

    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = encode_cursor(items[-1]) if heeft_meer else None
    return items, volgende


async def haal_op(session: AsyncSession, tenant_id, applicatie_id) -> Applicatie:
    """Haal één applicatie binnen de tenant; niet gevonden ⇒ `NietGevonden` (OP-6)."""
    tid = _tenant_uuid(tenant_id)
    stmt = select(Applicatie).where(
        Applicatie.id == applicatie_id,
        Applicatie.tenant_id == tid,
    )
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, applicatie_id)
    return obj


async def maak_aan(session: AsyncSession, tenant_id, data: ApplicatieCreate) -> Applicatie:
    """Maak een applicatie aan; start altijd in lifecycle `concept`."""
    tid = _tenant_uuid(tenant_id)
    obj = Applicatie(
        tenant_id=tid,
        lifecycle_status=LifecycleStatus.concept,
        **data.model_dump(),
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def werk_bij(
    session: AsyncSession, tenant_id, applicatie_id, data: ApplicatieUpdate
) -> Applicatie:
    """Partiële update binnen de tenant. `lifecycle_status` blijft onaangeraakt."""
    obj = await haal_op(session, tenant_id, applicatie_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj


async def verwijder(session: AsyncSession, tenant_id, applicatie_id) -> None:
    """Verwijder een applicatie binnen de tenant.

    Kind-records (datatype, gebruikersgroep, koppeling, checklistscore,
    blokkade) verdwijnen mee via `ON DELETE CASCADE` — alles onder dezelfde
    tenant-scope (RLS).
    """
    obj = await haal_op(session, tenant_id, applicatie_id)
    await session.delete(obj)
    await session.commit()


async def start_inventarisatie(session: AsyncSession, tenant_id, applicatie_id) -> Applicatie:
    """Lifecycle-overgang `concept → in_inventarisatie` (handmatige start).

    Ongeldige uitgangsstatus ⇒ `OngeldigeStatusovergang` (HTTP 409).
    """
    obj = await haal_op(session, tenant_id, applicatie_id)
    obj.lifecycle_status = volgende_status_na_start(obj.lifecycle_status)
    await session.commit()
    await session.refresh(obj)
    return obj
