"""Service-laag — Proces (ADR-042 slice 1).

Proces is een element-subtype (shared-PK), nestbaar via `ouder_id` (composiet self-FK) —
het work_package-recept 1-op-1. CRUD volgt het plateau-patroon (`Element('proces')` →
subtype-rij; delete via het element-supertype). De hiërarchie-regels worden
**server-side** gehandhaafd:

- **Cycluspreventie**: een proces kan niet zijn eigen (transitieve) voorouder zijn en
  niet onder zichzelf hangen — visited-set-traversal langs de ouder-keten (zelfde recept
  als work_package_service). Géén DB-trigger. → 422 `CYCLISCHE_HIERARCHIE`.
- **Verwijdergedrag**: een proces met directe deelprocessen kan niet verwijderd worden
  (geen stilzwijgend wegvagen van de subboom). De service pre-checkt en geeft 409
  `HEEFT_DEELPROCESSEN`; de self-FK `ON DELETE RESTRICT` is de DB-backstop.
- **Verplaatsen** = `ouder_id` wijzigen via `werk_bij` (incl. `null` = top-level).

De lijst is server-side sorteerbaar (ADR-017, v2n-keyset) + `zoek`-ILIKE, conform de
vaste lijst-normen (het Processen-scherm van slice 4 leunt hierop).

Niets hier raakt lifecycle/score/blokkade — er is bewust géén engine-import (score
blijft de enige lifecycle-driver; ADR-042-invariant).
"""
import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Element, ElementType, Proces
from schemas.proces import ProcesCreate, ProcesUpdate
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "proces"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"
_LIKE_ESCAPE = "\\"

# ADR-017 — sorteer-allowlist (rauwe kolomnaam komt NOOIT in ORDER BY); v2n-keyset
# (uniform, CD020) — beide kolommen zijn NOT NULL, de null-tak is dan een no-op.
_SORTEERBARE_KOLOMMEN = {
    "created_at": Proces.created_at,
    "naam": Proces.naam,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "naam": str,
}


def _escape_like(term: str) -> str:
    return term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def haal_op(session: AsyncSession, tenant_id, proces_id) -> Proces:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Proces).where(Proces.id == proces_id, Proces.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, proces_id)
    return obj


def _lees(obj: Proces) -> dict:
    return {
        "id": obj.id,
        "naam": obj.naam,
        "toelichting": obj.toelichting,
        "ouder_id": obj.ouder_id,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


async def _zou_kring_maken(
    session: AsyncSession, tid: uuid.UUID, proces_id, nieuw_ouder_id
) -> bool:
    """True als `proces_id` met ouder `nieuw_ouder_id` een kring zou vormen: loop de
    ouder-keten vanaf de voorgestelde ouder omhoog; raken we `proces_id`, dan is
    `proces_id` een (transitieve) voorouder van die ouder → kring. Visited-set =
    cyclus-veilig (work_package-recept)."""
    huidige = nieuw_ouder_id
    visited: set = set()
    while huidige is not None:
        if huidige == proces_id:
            return True
        if huidige in visited:
            break  # vangnet tegen een (niet zou mogen bestaan) bestaande kring
        visited.add(huidige)
        huidige = (
            await session.execute(
                select(Proces.ouder_id).where(Proces.tenant_id == tid, Proces.id == huidige)
            )
        ).scalar_one_or_none()
    return False


async def _valideer_ouder(session: AsyncSession, tid: uuid.UUID, proces_id, ouder_id) -> None:
    """Ouder moet binnen de tenant bestaan (404 no-leak); geen self-parent; geen kring."""
    if ouder_id is None:
        return
    if ouder_id == proces_id:
        raise OngeldigeRegistratie(
            "CYCLISCHE_HIERARCHIE", "Een proces kan niet onder zichzelf hangen."
        )
    await haal_op(session, tid, ouder_id)  # 404 als de ouder niet (in tenant) bestaat
    if proces_id is not None and await _zou_kring_maken(session, tid, proces_id, ouder_id):
        raise OngeldigeRegistratie(
            "CYCLISCHE_HIERARCHIE",
            "Dit ouder-proces is een deelproces van dit proces — dat zou een kring maken.",
        )


async def maak_aan(session: AsyncSession, tenant_id, data: ProcesCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    # Een nieuw proces kan nog niemands voorouder zijn → alleen het bestaan van de
    # ouder valideren (proces_id=None ⇒ geen kring-check nodig).
    await _valideer_ouder(session, tid, None, data.ouder_id)
    elem = Element(tenant_id=tid, element_type=ElementType.proces)
    session.add(elem)
    await session.flush()
    obj = Proces(
        id=elem.id, tenant_id=tid, naam=data.naam, toelichting=data.toelichting,
        ouder_id=data.ouder_id,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj)


async def lees_detail(session: AsyncSession, tenant_id, proces_id) -> dict:
    return _lees(await haal_op(session, tenant_id, proces_id))


async def werk_bij(session: AsyncSession, tenant_id, proces_id, data: ProcesUpdate) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, proces_id)
    velden = data.model_dump(exclude_unset=True)
    if "ouder_id" in velden:
        # Verplaatsen = één veldwijziging; server-side cycluspreventie.
        await _valideer_ouder(session, tid, obj.id, velden["ouder_id"])
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj)


async def verwijder(session: AsyncSession, tenant_id, proces_id) -> None:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, proces_id)  # 404 kruis-tenant
    # Verwijdergedrag: een proces met directe deelprocessen wordt niet (stilzwijgend)
    # met zijn subboom weggevaagd. Pre-check ⇒ 409; de self-FK RESTRICT is de DB-backstop.
    heeft_kind = (
        await session.execute(
            select(Proces.id).where(
                Proces.tenant_id == tid, Proces.ouder_id == proces_id
            ).limit(1)
        )
    ).scalar_one_or_none()
    if heeft_kind is not None:
        raise RegistratieConflict(
            "HEEFT_DEELPROCESSEN",
            "Dit proces heeft deelprocessen; verplaats of verwijder die eerst.",
        )
    # Verwijder via het element-supertype (cascade element → proces-subtype).
    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == proces_id))
    await session.commit()


async def lijst(
    session: AsyncSession, tenant_id, *,
    limit: int = _STANDAARD_LIMIT, after: str | None = None,
    sort: str = _STANDAARD_SORT, order: str = _STANDAARD_ORDER,
    zoek: str | None = None, ouder_id=None,
) -> tuple[list[dict], str | None]:
    """v2n-keyset-lijst binnen de tenant (ADR-017; default = created_at oplopend). `zoek` =
    ge-escapete ILIKE op `naam`; `ouder_id` filtert op directe deelprocessen (boom-opbouw
    per niveau in slice 4). Onbekend sort/order of cursor-mismatch ⇒ ValueError (route:
    422 via de enum resp. 400 ONGELDIGE_CURSOR)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]

    stmt = select(Proces).where(Proces.tenant_id == tid)
    if ouder_id is not None:
        stmt = stmt.where(Proces.ouder_id == ouder_id)
    if zoek:
        stmt = stmt.where(Proces.naam.ilike(f"%{_escape_like(zoek)}%", escape=_LIKE_ESCAPE))
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, Proces.id, order=order, is_null=c_is_null, waarde=c_waarde, cursor_id=c_id
            )
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Proces.id, order)).limit(limit + 1)

    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor_nullable(sort=sort, order=order, waarde=getattr(items[-1], sort), id=items[-1].id)
        if heeft_meer else None
    )
    return [_lees(o) for o in items], volgende


async def subboom(session: AsyncSession, tenant_id, proces_id) -> list[dict]:
    """Read-traversal van de subboom (alle deelprocessen, alle niveaus) vanaf één proces.
    Iteratieve BFS per niveau met visited-set (cyclus-veilig; kortste afstand `niveau` +
    pad). Read-only — geen schrijfpaden, geen engine-koppeling. Dit is tevens de
    leesbasis voor het roll-up-inzicht (ADR-042 slice 5)."""
    tid = _tenant_uuid(tenant_id)
    wortel = await haal_op(session, tenant_id, proces_id)  # 404 kruis-tenant
    geraakt: list[dict] = []
    visited = {proces_id}
    frontier = [(proces_id, [wortel.naam])]
    niveau = 0
    while frontier:
        niveau += 1
        ouder_pad = {n: pad for (n, pad) in frontier}
        rijen = (
            await session.execute(
                select(Proces)
                .where(
                    Proces.tenant_id == tid,
                    Proces.ouder_id.in_(list(ouder_pad.keys())),
                )
                .order_by(Proces.naam, Proces.id)
            )
        ).scalars().all()
        volgende = []
        for r in rijen:
            if r.id in visited:
                continue
            visited.add(r.id)
            pad = ouder_pad[r.ouder_id] + [r.naam]
            geraakt.append({
                "id": r.id, "naam": r.naam, "ouder_id": r.ouder_id,
                "niveau": niveau, "pad": pad,
            })
            volgende.append((r.id, pad))
        frontier = volgende
    return geraakt
