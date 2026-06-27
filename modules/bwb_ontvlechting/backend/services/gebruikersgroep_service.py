"""Service-laag voor de entiteit Gebruikersgroep (ADR-009; ADR-023 B-mig-2 slice 4).

ADR-023: gebruikersgroep is een **zelfstandig element** (business actor/role); de band met de
applicatie is een **serving**-relatie (applicatie → gebruikersgroep), niet langer een
`applicatie_id`-kolom. De API blijft stabiel: `applicatie_id` wordt afgeleid uit de
serving-relatie. CASCADE-wijziging (Besluit 13): een applicatie verwijderen laat de
gebruikersgroep bestaan — alleen de relatie vervalt.
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, delete, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import Component, Element, ElementType, Gebruikersgroep, Partij, Relatie
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

# UX-B6-a — `organisatie` sorteert op de naam van de gekoppelde organisatie-partij (per-call
# alias in `lijst`); de dict-waarde hier is een placeholder voor de allowlist-synctest.
_SORTEERBARE_KOLOMMEN = {
    "created_at": Gebruikersgroep.created_at,
    "organisatie": Gebruikersgroep.organisatie_id,
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


def _lees(obj: Gebruikersgroep, applicatie_id, organisatie_naam=None) -> dict:
    """API-vorm (applicatie_id afgeleid uit de serving-relatie; None = wees). UX-B6-a:
    organisatie als verwijzing + geresolveerde naam."""
    return {
        "id": obj.id, "applicatie_id": applicatie_id,
        "organisatie_id": obj.organisatie_id, "organisatie_naam": organisatie_naam,
        "afdeling": obj.afdeling, "aantal_gebruikers": obj.aantal_gebruikers,
        "created_at": obj.created_at, "updated_at": obj.updated_at,
    }


async def _org_naam(session: AsyncSession, tid: uuid.UUID, organisatie_id) -> str | None:
    """Naam van de gekoppelde organisatie-partij (None als niet gezet)."""
    if organisatie_id is None:
        return None
    return (
        await session.execute(
            select(Partij.naam).where(Partij.id == organisatie_id, Partij.tenant_id == tid)
        )
    ).scalar_one_or_none()


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


def _escape_like(term: str) -> str:
    """LIKE/ILIKE-wildcard-escaping (volgorde \\ → % → _), zoals de andere zoek-endpoints (CD017)."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def contexten(session: AsyncSession, tenant_id, *, zoek: str | None = None) -> list[dict]:
    """Fase B slice 2a (LI022) — distinct `(organisatie, afdeling)`-gebruikercontexten over alle
    gebruikersgroepen, met geresolveerde organisatie-naam + een telling van bijbehorende componenten
    (distinct applicatie-bron van de serving-relatie). Doorzoekbaar (vrije term op organisatie-naam
    OF afdeling). Bewust een BEGRENSDE afgeleide lijst (géén keyset): het aantal distinct contexten is
    klein/begrensd — consistent met de andere context-sub-endpoints (`/partijen/{id}/componenten`,
    `/contracten/{id}/componenten`) die óók ongepagineerd zijn. Read-only."""
    tid = _tenant_uuid(tenant_id)
    org = aliased(Partij)
    serv = aliased(Relatie)
    stmt = (
        select(
            Gebruikersgroep.organisatie_id.label("organisatie_id"),
            org.naam.label("organisatie_naam"),
            Gebruikersgroep.afdeling.label("afdeling"),
            func.count(distinct(serv.bron_id)).label("aantal_componenten"),
        )
        .select_from(Gebruikersgroep)
        .outerjoin(org, and_(org.id == Gebruikersgroep.organisatie_id, org.tenant_id == tid))
        .outerjoin(serv, and_(serv.doel_id == Gebruikersgroep.id, serv.tenant_id == tid, serv.relatietype == _SERVING))
        .where(Gebruikersgroep.tenant_id == tid)
        .group_by(Gebruikersgroep.organisatie_id, org.naam, Gebruikersgroep.afdeling)
        .order_by(org.naam.nulls_last(), Gebruikersgroep.afdeling.nulls_last())
    )
    if zoek and zoek.strip():
        like = f"%{_escape_like(zoek.strip())}%"
        stmt = stmt.where(or_(org.naam.ilike(like, escape="\\"), Gebruikersgroep.afdeling.ilike(like, escape="\\")))
    rijen = (await session.execute(stmt)).all()
    return [
        {
            "organisatie_id": r.organisatie_id, "organisatie_naam": r.organisatie_naam,
            "afdeling": r.afdeling, "aantal_componenten": r.aantal_componenten,
        }
        for r in rijen
    ]


async def componenten_voor_context(
    session: AsyncSession, tenant_id, *, organisatie_id: uuid.UUID | None, afdeling: str | None
) -> list[dict]:
    """Fase B slice 2a (LI022) — distinct componenten (de applicatie-bron van de serving-relatie) van de
    gebruikersgroepen die EXACT op deze `(organisatie, afdeling)`-context matchen. Nullable-veilige match
    (`IS NOT DISTINCT FROM`) zodat de lege-organisatie-/lege-afdeling-casus (bv. "— / Burgers") klopt.
    Read-only; levert component-ids + naam + type voor de subgraaf."""
    tid = _tenant_uuid(tenant_id)
    rijen = (
        await session.execute(
            select(
                Component.id.label("component_id"),
                Component.naam.label("component_naam"),
                Component.componenttype.label("componenttype"),
            )
            .select_from(Gebruikersgroep)
            .join(Relatie, and_(Relatie.doel_id == Gebruikersgroep.id, Relatie.relatietype == _SERVING, Relatie.tenant_id == tid))
            .join(Component, and_(Component.id == Relatie.bron_id, Component.tenant_id == tid))
            .where(
                Gebruikersgroep.tenant_id == tid,
                Gebruikersgroep.organisatie_id.is_not_distinct_from(organisatie_id),
                Gebruikersgroep.afdeling.is_not_distinct_from(afdeling),
            )
            .distinct()
            .order_by(Component.naam, Component.id)
        )
    ).all()
    return [
        {"component_id": r.component_id, "component_naam": r.component_naam, "componenttype": r.componenttype}
        for r in rijen
    ]


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
    # UX-B6-a — LEFT JOIN de organisatie-partij voor naam-in-read + sortering op de org-naam.
    org = aliased(Partij)
    kolom = org.naam if sort == "organisatie" else _SORTEERBARE_KOLOMMEN[sort]

    stmt = (
        select(Gebruikersgroep, org.naam.label("organisatie_naam"))
        .outerjoin(org, and_(org.id == Gebruikersgroep.organisatie_id, org.tenant_id == tid))
        .where(Gebruikersgroep.tenant_id == tid)
    )
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

    rijen = list((await session.execute(stmt)).all())  # (Gebruikersgroep, organisatie_naam|None)
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    app_map = await _applicaties_van(session, tid, [g.id for (g, _n) in items])
    out = [_lees(g, app_map.get(g.id), org_naam) for (g, org_naam) in items]
    if heeft_meer:
        laatste_g, laatste_org = items[-1]
        waarde = laatste_org if sort == "organisatie" else getattr(laatste_g, kolom.key)
        volgende = encode_sort_cursor_nullable(sort=sort, order=order, waarde=waarde, id=laatste_g.id)
    else:
        volgende = None
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
    return _lees(obj, app_map.get(obj.id), await _org_naam(session, tid, obj.organisatie_id))


async def maak_aan(session: AsyncSession, tenant_id, data: GebruikersgroepCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    await applicatie_service.haal_op(session, tenant_id, data.applicatie_id)  # ouder 404 buiten tenant
    # UX-B6-a — valideer dat een opgegeven organisatie een organisatie-partij is (optioneel).
    if data.organisatie_id is not None:
        from services import partij_service
        await partij_service.valideer_organisatie(session, tid, data.organisatie_id)
    velden = data.model_dump(exclude={"applicatie_id"})
    elem = Element(tenant_id=tid, element_type=ElementType.gebruikersgroep)
    session.add(elem)
    await session.flush()
    obj = Gebruikersgroep(id=elem.id, tenant_id=tid, **velden)
    session.add(obj)
    session.add(Relatie(tenant_id=tid, bron_id=data.applicatie_id, doel_id=elem.id, relatietype=_SERVING))
    await session.commit()
    await session.refresh(obj)
    return _lees(obj, data.applicatie_id, await _org_naam(session, tid, obj.organisatie_id))


async def werk_bij(session: AsyncSession, tenant_id, gebruikersgroep_id, data: GebruikersgroepUpdate) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, gebruikersgroep_id)
    velden = data.model_dump(exclude_unset=True)
    # UX-B6-a — organisatie wijzigen: valideer aard=organisatie als een id wordt gezet.
    if "organisatie_id" in velden and velden["organisatie_id"] is not None:
        from services import partij_service
        await partij_service.valideer_organisatie(session, tid, velden["organisatie_id"])
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    app_map = await _applicaties_van(session, tid, [obj.id])
    return _lees(obj, app_map.get(obj.id), await _org_naam(session, tid, obj.organisatie_id))


async def verwijder(session: AsyncSession, tenant_id, gebruikersgroep_id) -> None:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, gebruikersgroep_id)
    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == gebruikersgroep_id))
    await session.commit()
