"""Service-laag — Deliverable + realisatieketen (ADR-023 Fase E, E3).

Deliverable is een element-subtype (shared-PK); CRUD volgt het plateau-patroon
(`Element('deliverable')` → subtype-rij; delete via het element-supertype). De
realisatieketen **work_package → deliverable → plateau** loopt via het bestaande
relatietype `realization` in het unified relatiemodel — een dunne facade over `Relatie`
(zoals `component_contract_service`/`plateau_service`):

- **work_package → deliverable**: bron = work_package (realiseert), doel = deliverable;
- **deliverable → plateau**: bron = deliverable (realiseert), doel = plateau.

Koppelingen zijn **expliciet en optioneel** (Besluit 8): er wordt géén verplichte/complete
keten afgedwongen en het systeem leidt nooit zelf relaties af. Een ongeldig bron/doel-type
voor de richting → 422 `ONGELDIGE_REALISATIE`; een dubbele koppeling → 409
`REALISATIE_BESTAAT`.

Niets hier raakt lifecycle/score/blokkade — geen engine-import (score blijft de enige
lifecycle-driver).
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Deliverable, Element, ElementType, Plateau, Relatie, WorkPackage
from schemas.deliverable import DeliverableCreate, DeliverableUpdate
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict
from services.pagination import decode_sort_cursor, encode_sort_cursor

_ENTITEIT = "deliverable"
_REALIZATION = "realization"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


# ── Deliverable-CRUD (element-subtype) ───────────────────────────────────────────

async def haal_op(session: AsyncSession, tenant_id, deliverable_id) -> Deliverable:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Deliverable).where(
                Deliverable.id == deliverable_id, Deliverable.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, deliverable_id)
    return obj


def _lees(obj: Deliverable) -> dict:
    return {
        "id": obj.id, "naam": obj.naam, "toelichting": obj.toelichting,
        "created_at": obj.created_at, "updated_at": obj.updated_at,
    }


async def maak_aan(session: AsyncSession, tenant_id, data: DeliverableCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    elem = Element(tenant_id=tid, element_type=ElementType.deliverable)
    session.add(elem)
    await session.flush()
    obj = Deliverable(id=elem.id, tenant_id=tid, naam=data.naam, toelichting=data.toelichting)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj)


async def lees_detail(session: AsyncSession, tenant_id, deliverable_id) -> dict:
    return _lees(await haal_op(session, tenant_id, deliverable_id))


async def werk_bij(session: AsyncSession, tenant_id, deliverable_id, data: DeliverableUpdate) -> dict:
    obj = await haal_op(session, tenant_id, deliverable_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj)


async def verwijder(session: AsyncSession, tenant_id, deliverable_id) -> None:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, deliverable_id)
    # Verwijder via het element-supertype: cascade element → deliverable-subtype + de
    # realization-relaties (relatie-FK's → element, ON DELETE CASCADE).
    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == deliverable_id))
    await session.commit()


async def lijst(
    session: AsyncSession, tenant_id, *, limit: int = _STANDAARD_LIMIT, after: str | None = None
) -> tuple[list[dict], str | None]:
    """Keyset-lijst binnen de tenant (created_at oplopend). Cursor-mismatch ⇒ ValueError (400)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)
    stmt = select(Deliverable).where(Deliverable.tenant_id == tid)
    if after:
        _s, _o, waarde_str, c_id = decode_sort_cursor(after)
        c_waarde = datetime.fromisoformat(waarde_str)
        stmt = stmt.where(
            or_(
                Deliverable.created_at > c_waarde,
                and_(Deliverable.created_at == c_waarde, Deliverable.id > c_id),
            )
        )
    stmt = stmt.order_by(Deliverable.created_at.asc(), Deliverable.id.asc()).limit(limit + 1)
    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor(sort="created_at", order="asc", waarde=items[-1].created_at, id=items[-1].id)
        if heeft_meer else None
    )
    return [_lees(o) for o in items], volgende


# ── Realisatieketen (facade over Relatie: realization) ───────────────────────────

async def _element_type(session: AsyncSession, tid: uuid.UUID, eid) -> str:
    et = (
        await session.execute(
            select(Element.element_type).where(Element.tenant_id == tid, Element.id == eid)
        )
    ).scalar_one_or_none()
    if et is None:
        raise NietGevonden("element", eid)
    return et.value if hasattr(et, "value") else str(et)


async def _maak_realization(session: AsyncSession, tid: uuid.UUID, bron, doel) -> Relatie:
    obj = Relatie(tenant_id=tid, bron_id=bron, doel_id=doel, relatietype=_REALIZATION, kenmerken={})
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise RegistratieConflict("REALISATIE_BESTAAT", "Deze realisatie-koppeling bestaat al.") from exc
    await session.refresh(obj)
    return obj


async def _naam(session: AsyncSession, tid: uuid.UUID, model, eid) -> str:
    return (
        await session.execute(select(model.naam).where(model.tenant_id == tid, model.id == eid))
    ).scalar_one()


async def koppel_werkpakket(session: AsyncSession, tenant_id, deliverable_id, work_package_id) -> dict:
    """work_package → deliverable (het werkpakket realiseert deze deliverable)."""
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, deliverable_id)  # 404; borgt dat het een deliverable is
    if await _element_type(session, tid, work_package_id) != ElementType.work_package.value:
        raise OngeldigeRegistratie(
            "ONGELDIGE_REALISATIE", "Alleen een werkpakket kan een deliverable opleveren."
        )
    obj = await _maak_realization(session, tid, bron=work_package_id, doel=deliverable_id)
    return {"relatie_id": obj.id, "element_id": work_package_id,
            "naam": await _naam(session, tid, WorkPackage, work_package_id)}


async def koppel_plateau(session: AsyncSession, tenant_id, deliverable_id, plateau_id) -> dict:
    """deliverable → plateau (deze deliverable helpt het plateau realiseren)."""
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, deliverable_id)
    if await _element_type(session, tid, plateau_id) != ElementType.plateau.value:
        raise OngeldigeRegistratie(
            "ONGELDIGE_REALISATIE", "Een deliverable kan alleen een plateau realiseren."
        )
    obj = await _maak_realization(session, tid, bron=deliverable_id, doel=plateau_id)
    return {"relatie_id": obj.id, "element_id": plateau_id,
            "naam": await _naam(session, tid, Plateau, plateau_id)}


async def _ontkoppel(session: AsyncSession, tid: uuid.UUID, relatie_id, *, bron=None, doel=None) -> None:
    cond = [Relatie.id == relatie_id, Relatie.tenant_id == tid, Relatie.relatietype == _REALIZATION]
    if bron is not None:
        cond.append(Relatie.bron_id == bron)
    if doel is not None:
        cond.append(Relatie.doel_id == doel)
    obj = (await session.execute(select(Relatie).where(*cond))).scalar_one_or_none()
    if obj is None:
        raise NietGevonden("realisatie", relatie_id)
    await session.delete(obj)
    await session.commit()


async def ontkoppel_werkpakket(session: AsyncSession, tenant_id, deliverable_id, relatie_id) -> None:
    await _ontkoppel(session, _tenant_uuid(tenant_id), relatie_id, doel=deliverable_id)


async def ontkoppel_plateau(session: AsyncSession, tenant_id, deliverable_id, relatie_id) -> None:
    await _ontkoppel(session, _tenant_uuid(tenant_id), relatie_id, bron=deliverable_id)


async def keten_van_deliverable(session: AsyncSession, tenant_id, deliverable_id) -> dict:
    """De keten rond één deliverable: realiserende werkpakketten + gerealiseerde plateaus."""
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, deliverable_id)
    wp = (
        await session.execute(
            select(Relatie.id, WorkPackage.id, WorkPackage.naam)
            .join(WorkPackage, and_(WorkPackage.id == Relatie.bron_id, WorkPackage.tenant_id == tid))
            .where(Relatie.tenant_id == tid, Relatie.relatietype == _REALIZATION,
                   Relatie.doel_id == deliverable_id)
            .order_by(WorkPackage.naam, Relatie.id)
        )
    ).all()
    pl = (
        await session.execute(
            select(Relatie.id, Plateau.id, Plateau.naam)
            .join(Plateau, and_(Plateau.id == Relatie.doel_id, Plateau.tenant_id == tid))
            .where(Relatie.tenant_id == tid, Relatie.relatietype == _REALIZATION,
                   Relatie.bron_id == deliverable_id)
            .order_by(Plateau.naam, Relatie.id)
        )
    ).all()
    return {
        "werkpakketten": [{"relatie_id": r[0], "element_id": r[1], "naam": r[2]} for r in wp],
        "plateaus": [{"relatie_id": r[0], "element_id": r[1], "naam": r[2]} for r in pl],
    }


async def realisatieketen_van_werkpakket(session: AsyncSession, tenant_id, work_package_id) -> dict:
    """Read-traversal: vanaf een werkpakket → de deliverables die het oplevert → de
    plateaus die daarmee worden gerealiseerd. Read-only, afgeleid over realization-relaties."""
    tid = _tenant_uuid(tenant_id)
    if await _element_type(session, tid, work_package_id) != ElementType.work_package.value:
        raise NietGevonden("work_package", work_package_id)
    deliverables = (
        await session.execute(
            select(Deliverable.id, Deliverable.naam)
            .join(Relatie, and_(Relatie.doel_id == Deliverable.id, Relatie.tenant_id == tid,
                                Relatie.relatietype == _REALIZATION, Relatie.bron_id == work_package_id))
            .order_by(Deliverable.naam, Deliverable.id)
        )
    ).all()
    uit = []
    for d_id, d_naam in deliverables:
        plateaus = (
            await session.execute(
                select(Plateau.id, Plateau.naam)
                .join(Relatie, and_(Relatie.doel_id == Plateau.id, Relatie.tenant_id == tid,
                                    Relatie.relatietype == _REALIZATION, Relatie.bron_id == d_id))
                .order_by(Plateau.naam, Plateau.id)
            )
        ).all()
        uit.append({
            "deliverable_id": d_id, "naam": d_naam,
            "plateaus": [{"plateau_id": p[0], "naam": p[1]} for p in plateaus],
        })
    return {"work_package_id": work_package_id, "deliverables": uit}
