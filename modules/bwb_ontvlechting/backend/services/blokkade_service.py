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

from models.models import (
    ACTIEVE_BLOKKADE_STATUSSEN,
    Applicatie,
    Blokkade,
    BlokkadeStatus,
    Checklistscore,
)
from schemas.blokkade import BlokkadeUpdate
from services import lifecycle_service
from services.errors import NietGevonden, OngeldigeStatusovergang
from services.pagination import (
    decode_cursor,
    decode_sort_cursor_nullable,
    encode_cursor,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "blokkade"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100

# ── Tenant-breed overzicht (CD016, consument ADR-017) ───────────────────────────

_STANDAARD_OVERZICHT_SORT = "applicatie_naam"
_STANDAARD_OVERZICHT_ORDER = "asc"

# Allowlist-kolommen (ADR-017 B2) — single source naast de schema-enum
# `BlokkadeSorteerveld`. `applicatie_naam`/`vraag_code` zijn gejoinde kolommen;
# de keyset-tiebreaker blijft `Blokkade.id`. `gewijzigd_op` mapt op `updated_at`.
_OVERZICHT_KOLOMMEN = {
    "applicatie_naam": Applicatie.naam,
    "vraag_code": Checklistscore.vraag_code,
    "status": Blokkade.status,
    "toelichting": Blokkade.toelichting,
    "eigenaar": Blokkade.eigenaar,
    "opgelost_op": Blokkade.opgelost_op,
    "gewijzigd_op": Blokkade.updated_at,
}

# Parsers die een cursor-waarde (tekst) terug naar het kolomtype brengen.
_OVERZICHT_PARSERS = {
    "applicatie_naam": str,
    "vraag_code": str,
    "status": BlokkadeStatus,
    "toelichting": str,
    "eigenaar": str,
    "opgelost_op": datetime.fromisoformat,
    "gewijzigd_op": datetime.fromisoformat,
}


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


def _pas_statusfilter_toe(stmt, status_filter: str):
    """Statusfilter voor het overzicht. `actief` = gedeelde constante; `alle` = niets."""
    if status_filter == "actief":
        return stmt.where(Blokkade.status.in_(ACTIEVE_BLOKKADE_STATUSSEN))
    if status_filter == "alle":
        return stmt
    return stmt.where(Blokkade.status == BlokkadeStatus(status_filter))


async def lijst_overzicht(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    status_filter: str = "actief",
    sort: str = _STANDAARD_OVERZICHT_SORT,
    order: str = _STANDAARD_OVERZICHT_ORDER,
) -> tuple[list[dict], str | None]:
    """Tenant-breed blokkadesoverzicht over alle applicaties (CD016, ADR-017).

    Join op `Applicatie` (naam) en `Checklistscore` (vraag_code). Server-side
    sorteerbaar met NULLS-LAST-keyset (nullable: `toelichting`/`eigenaar`/
    `opgelost_op`); `Blokkade.id` is de stabiele tiebreaker. Tenant-scoped via RLS
    + expliciete `tenant_id`-filter (dubbele bescherming). Een `after` die niet bij
    `sort`/`order` past ⇒ `ValueError` (route ⇒ 400).
    """
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _OVERZICHT_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_OVERZICHT_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _OVERZICHT_KOLOMMEN[sort]

    stmt = (
        select(
            Blokkade.id.label("id"),
            Blokkade.applicatie_id.label("applicatie_id"),
            Applicatie.naam.label("applicatie_naam"),
            Checklistscore.vraag_code.label("vraag_code"),
            Blokkade.status.label("status"),
            Blokkade.toelichting.label("toelichting"),
            Blokkade.eigenaar.label("eigenaar"),
            Blokkade.opgelost_op.label("opgelost_op"),
            Blokkade.updated_at.label("gewijzigd_op"),
        )
        .join(Applicatie, Applicatie.id == Blokkade.applicatie_id)
        .join(Checklistscore, Checklistscore.id == Blokkade.checklistscore_id)
        .where(Blokkade.tenant_id == tid)
    )
    stmt = _pas_statusfilter_toe(stmt, status_filter)

    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _OVERZICHT_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, Blokkade.id, order=order, is_null=c_is_null, waarde=c_waarde, cursor_id=c_id
            )
        )

    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Blokkade.id, order)).limit(limit + 1)

    rijen = (await session.execute(stmt)).all()
    heeft_meer = len(rijen) > limit
    zichtbaar = rijen[:limit]
    items = [
        {
            "id": r.id,
            "applicatie_id": r.applicatie_id,
            "applicatie_naam": r.applicatie_naam,
            "vraag_code": r.vraag_code,
            "status": r.status,
            "toelichting": r.toelichting,
            "eigenaar": r.eigenaar,
            "opgelost_op": r.opgelost_op,
            "gewijzigd_op": r.gewijzigd_op,
        }
        for r in zichtbaar
    ]
    volgende = (
        encode_sort_cursor_nullable(
            sort=sort, order=order, waarde=getattr(zichtbaar[-1], sort), id=zichtbaar[-1].id
        )
        if heeft_meer
        else None
    )
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
