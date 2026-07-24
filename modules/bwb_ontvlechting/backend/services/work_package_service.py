"""Service-laag — Work Package (ADR-023 Fase E, E2).

Work Package is een element-subtype (shared-PK), hiërarchisch via `bovenliggend_id`
(composiet self-FK). CRUD volgt het plateau-patroon (`Element('work_package')` → subtype-rij;
delete via het element-supertype). De hiërarchie-regels worden **server-side** gehandhaafd:

- **Cycluspreventie** (E-4): een werkpakket kan niet zijn eigen (transitieve) voorouder zijn
  en niet onder zichzelf hangen — visited-set-traversal langs de ouder-keten (zelfde idee als
  de contract-mantel-cycluspreventie). Géén DB-trigger. → 422 `CYCLISCHE_HIERARCHIE`.
- **Verwijdergedrag**: een werkpakket met directe subpakketten kan niet verwijderd worden
  (geen stilzwijgend wegvagen van de subboom). De service pre-checkt en geeft 409
  `HEEFT_SUBPAKKETTEN`; de self-FK `ON DELETE RESTRICT` is de DB-backstop.

Niets hier raakt lifecycle/score/blokkade — er is bewust géén engine-import (score blijft
de enige lifecycle-driver).
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from services import zoektekst

from models.models import Element, ElementType, WorkPackage
from schemas.work_package import WorkPackageCreate, WorkPackageUpdate
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict
from services.pagination import decode_sort_cursor, encode_sort_cursor

_ENTITEIT = "work_package"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100



def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def haal_op(session: AsyncSession, tenant_id, work_package_id) -> WorkPackage:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(WorkPackage).where(
                WorkPackage.id == work_package_id, WorkPackage.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, work_package_id)
    return obj


def _lees(obj: WorkPackage) -> dict:
    return {
        "id": obj.id,
        "naam": obj.naam,
        "toelichting": obj.toelichting,
        "bovenliggend_id": obj.bovenliggend_id,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


async def _zou_kring_maken(
    session: AsyncSession, tid: uuid.UUID, wp_id, nieuw_bovenliggend_id
) -> bool:
    """True als `wp_id` als bovenliggende `nieuw_bovenliggend_id` zou krijgen er een kring
    ontstaat: loop de ouder-keten vanaf de voorgestelde ouder omhoog; raken we `wp_id`, dan
    is `wp_id` een (transitieve) voorouder van die ouder → kring. Visited-set = cyclus-veilig."""
    huidige = nieuw_bovenliggend_id
    visited: set = set()
    while huidige is not None:
        if huidige == wp_id:
            return True
        if huidige in visited:
            break  # vangnet tegen een (niet zou mogen bestaan) bestaande kring
        visited.add(huidige)
        huidige = (
            await session.execute(
                select(WorkPackage.bovenliggend_id).where(
                    WorkPackage.tenant_id == tid, WorkPackage.id == huidige
                )
            )
        ).scalar_one_or_none()
    return False


async def _valideer_bovenliggend(
    session: AsyncSession, tid: uuid.UUID, wp_id, bovenliggend_id
) -> None:
    """Bovenliggende moet binnen de tenant bestaan; geen self-parent; geen transitieve kring."""
    if bovenliggend_id is None:
        return
    if bovenliggend_id == wp_id:
        raise OngeldigeRegistratie(
            "CYCLISCHE_HIERARCHIE", "Een werkpakket kan niet onder zichzelf hangen."
        )
    await haal_op(session, tid, bovenliggend_id)  # 404 als de ouder niet (in tenant) bestaat
    if wp_id is not None and await _zou_kring_maken(session, tid, wp_id, bovenliggend_id):
        raise OngeldigeRegistratie(
            "CYCLISCHE_HIERARCHIE",
            "Dit bovenliggende werkpakket is een afstammeling — dat zou een kring maken.",
        )


async def maak_aan(session: AsyncSession, tenant_id, data: WorkPackageCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    # Een nieuw werkpakket kan nog niemands voorouder zijn → alleen het bestaan van de
    # bovenliggende valideren (wp_id=None ⇒ geen kring-check nodig).
    await _valideer_bovenliggend(session, tid, None, data.bovenliggend_id)
    elem = Element(tenant_id=tid, element_type=ElementType.work_package)
    session.add(elem)
    await session.flush()
    obj = WorkPackage(
        id=elem.id, tenant_id=tid, naam=data.naam, toelichting=data.toelichting,
        bovenliggend_id=data.bovenliggend_id,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj)


async def lees_detail(session: AsyncSession, tenant_id, work_package_id) -> dict:
    return _lees(await haal_op(session, tenant_id, work_package_id))


async def werk_bij(session: AsyncSession, tenant_id, work_package_id, data: WorkPackageUpdate) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, work_package_id)
    velden = data.model_dump(exclude_unset=True)
    if "bovenliggend_id" in velden:
        await _valideer_bovenliggend(session, tid, obj.id, velden["bovenliggend_id"])
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj)


async def verwijder(session: AsyncSession, tenant_id, work_package_id) -> None:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, work_package_id)  # 404 kruis-tenant
    # Verwijdergedrag: een werkpakket met directe subpakketten wordt niet (stilzwijgend)
    # met zijn subboom weggevaagd. Pre-check ⇒ 409; de self-FK RESTRICT is de DB-backstop.
    heeft_kind = (
        await session.execute(
            select(WorkPackage.id).where(
                WorkPackage.tenant_id == tid, WorkPackage.bovenliggend_id == work_package_id
            ).limit(1)
        )
    ).scalar_one_or_none()
    if heeft_kind is not None:
        raise RegistratieConflict(
            "HEEFT_SUBPAKKETTEN",
            "Dit werkpakket heeft subpakketten; ontkoppel of verwijder die eerst.",
        )
    # Verwijder via het element-supertype (cascade element → work_package-subtype).
    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == work_package_id))
    await session.commit()


async def lijst(
    session: AsyncSession, tenant_id, *, limit: int = _STANDAARD_LIMIT, after: str | None = None,
    zoek: str | None = None,
) -> tuple[list[dict], str | None]:
    """Vlakke keyset-lijst binnen de tenant (created_at oplopend). `zoek` = ge-escapete
    ILIKE op `naam` (voor het "bovenliggend werkpakket"-keuzeveld). Cursor-mismatch ⇒ ValueError (400)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)
    stmt = select(WorkPackage).where(WorkPackage.tenant_id == tid)
    if zoek:
        stmt = stmt.where(zoektekst.zoek_clause(WorkPackage.naam, zoek))
    if after:
        _s, _o, waarde_str, c_id = decode_sort_cursor(after)
        c_waarde = datetime.fromisoformat(waarde_str)
        stmt = stmt.where(
            or_(
                WorkPackage.created_at > c_waarde,
                and_(WorkPackage.created_at == c_waarde, WorkPackage.id > c_id),
            )
        )
    stmt = stmt.order_by(WorkPackage.created_at.asc(), WorkPackage.id.asc()).limit(limit + 1)
    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor(sort="created_at", order="asc", waarde=items[-1].created_at, id=items[-1].id)
        if heeft_meer else None
    )
    return [_lees(o) for o in items], volgende


async def subboom(session: AsyncSession, tenant_id, work_package_id) -> list[dict]:
    """Read-traversal van de subboom (alle afstammelingen) vanaf één werkpakket. Iteratieve
    BFS per niveau met visited-set (cyclus-veilig; geeft de kortste afstand `niveau` + het
    pad). Read-only — geen schrijfpaden, geen engine-koppeling."""
    tid = _tenant_uuid(tenant_id)
    wortel = await haal_op(session, tenant_id, work_package_id)  # 404 kruis-tenant
    geraakt: list[dict] = []
    visited = {work_package_id}
    frontier = [(work_package_id, [wortel.naam])]
    niveau = 0
    while frontier:
        niveau += 1
        ouder_pad = {n: pad for (n, pad) in frontier}
        rijen = (
            await session.execute(
                select(WorkPackage)
                .where(
                    WorkPackage.tenant_id == tid,
                    WorkPackage.bovenliggend_id.in_(list(ouder_pad.keys())),
                )
                .order_by(WorkPackage.naam, WorkPackage.id)
            )
        ).scalars().all()
        volgende = []
        for r in rijen:
            if r.id in visited:
                continue
            visited.add(r.id)
            pad = ouder_pad[r.bovenliggend_id] + [r.naam]
            geraakt.append({
                "id": r.id, "naam": r.naam, "bovenliggend_id": r.bovenliggend_id,
                "niveau": niveau, "pad": pad,
            })
            volgende.append((r.id, pad))
        frontier = volgende
    return geraakt
