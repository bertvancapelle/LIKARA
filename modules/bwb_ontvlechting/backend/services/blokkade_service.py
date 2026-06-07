"""Service-laag voor de entiteit Blokkade (ADR-009/013, Model A).

Blokkades zijn systeem-afgeleid: **geen** `maak_aan`/`verwijder` via de gebruiker
(auto-creatie gebeurt in `checklistscore_service`; opruimen via DB-cascade). De
gebruiker beheert de opvolging via `werk_bij`. `opgelost_op` wordt afgeleid uit
de resulterende `status`. Na elke wijziging draait `herbereken_lifecycle`
(ADR-013): zodra de laatste open blokkade is opgelost en alles gescoord is, wordt
de applicatie `migratieklaar`.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Blokkade, BlokkadeStatus
from schemas.blokkade import BlokkadeUpdate
from services import lifecycle_service
from services.errors import NietGevonden, OngeldigeStatusovergang
from services.pagination import decode_cursor, encode_cursor

_ENTITEIT = "blokkade"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def enum_opties() -> dict[str, list[str]]:
    """Read-only keuzewaarden voor de blokkade-status (single source, DB-vrij)."""
    return {"status": [e.value for e in BlokkadeStatus]}


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    applicatie_id: uuid.UUID | None = None,
    status: BlokkadeStatus | None = None,
) -> tuple[list[Blokkade], str | None]:
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    stmt = select(Blokkade).where(Blokkade.tenant_id == tid)
    if applicatie_id is not None:
        stmt = stmt.where(Blokkade.applicatie_id == applicatie_id)
    if status is not None:
        stmt = stmt.where(Blokkade.status == status)
    if after:
        cursor_created_at, cursor_id = decode_cursor(after)
        stmt = stmt.where(
            tuple_(Blokkade.created_at, Blokkade.id) > (cursor_created_at, cursor_id)
        )
    stmt = stmt.order_by(Blokkade.created_at, Blokkade.id).limit(limit + 1)

    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = encode_cursor(items[-1]) if heeft_meer else None
    return items, volgende


async def haal_op(session: AsyncSession, tenant_id, blokkade_id) -> Blokkade:
    tid = _tenant_uuid(tenant_id)
    stmt = select(Blokkade).where(
        Blokkade.id == blokkade_id,
        Blokkade.tenant_id == tid,
    )
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, blokkade_id)
    return obj


async def werk_bij(
    session: AsyncSession, tenant_id, blokkade_id, data: BlokkadeUpdate
) -> Blokkade:
    """Handmatige statusprogressie + afgeleide `opgelost_op` + herberekening.

    `opgelost` ⇒ `opgelost_op` wordt gezet (behoudt een bestaande tijd bij een
    toelichting-only-edit); terug naar `open`/`in_behandeling` ⇒ `opgelost_op`
    weer leeg.
    """
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, blokkade_id)

    # ADR-016: handmatig alleen `open ↔ in_behandeling`. `opgelost` ontstaat
    # UITSLUITEND via de auto-logica (Checklistscore `ja`/`nvt`), die buiten dit
    # pad om loopt (checklistscore_service._synchroniseer_blokkade).
    if data.status == BlokkadeStatus.opgelost:
        raise OngeldigeStatusovergang(obj.status, BlokkadeStatus.opgelost)

    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)

    if obj.status == BlokkadeStatus.opgelost:
        if obj.opgelost_op is None:
            obj.opgelost_op = datetime.now(timezone.utc)
    else:
        obj.opgelost_op = None

    await session.flush()
    await lifecycle_service.herbereken_lifecycle(session, tid, obj.applicatie_id)
    await session.commit()
    await session.refresh(obj)
    return obj
