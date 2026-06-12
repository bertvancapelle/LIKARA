"""Service-laag voor Component (ADR-021 Besluit 1/4/6/9 — Fase B).

Tenant-scoped (RLS + expliciet `tenant_id`-filter; OP-6 kruis-tenant → 404). Het type
`applicatie` is een beschermde systeem-sleutel: applicaties ontstaan/verdwijnen uitsluitend
via het applicatie-pad (CD051). `componenttype`/`relatietype` worden tegen de actieve
componentcatalogus gevalideerd.
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Applicatie,
    Component,
    ComponentConfigDimensie,
    ComponentContract,
    ComponentStructuur,
    HostingModel,
    Koppeling,
    LifecycleStatus,
    Migratiepad,
    NiveauEnum,
)
from schemas.component import ComponentCreate, ComponentUpdate
from services import componentconfig_catalog as catalog
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "component"
_APPLICATIE_TYPE = "applicatie"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100
_LIKE_ESCAPE = "\\"

# Allowlist (ADR-017 B2). De drie subtype-kolommen zijn nullable (LEFT JOIN op het
# subtype) → de hele lijst draait op de NULLS-LAST-cursor (v2n); de helper werkt
# uniform ook voor de NOT NULL-kolommen. `ComponentSorteerveld` (schema-enum) blijft
# hiermee synchroon — geborgd door `test_component_sort`.
_SORTEERBARE_KOLOMMEN = {
    "created_at": Component.created_at,
    "naam": Component.naam,
    "componenttype": Component.componenttype,
    "complexiteit": Applicatie.complexiteit,
    "prioriteit": Applicatie.prioriteit,
    "lifecycle_status": Applicatie.lifecycle_status,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "naam": str,
    "componenttype": str,
    "complexiteit": NiveauEnum,
    "prioriteit": NiveauEnum,
    "lifecycle_status": LifecycleStatus,
}

# Convergente aanmaak (CD054b W1): een component met type `applicatie` maakt atomair
# het subtype met deze defaults; eigenaar leeg toegestaan ("" — bewerkbaar op het detail).
_SUBTYPE_DEFAULTS = {
    "migratiepad": Migratiepad.onbekend,
    "complexiteit": NiveauEnum.midden,
    "prioriteit": NiveauEnum.midden,
}


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _escape_like(term: str) -> str:
    return term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")


async def _heeft_subtype(session: AsyncSession, tid: uuid.UUID, component_id) -> bool:
    return (
        await session.execute(
            select(Applicatie.id).where(Applicatie.tenant_id == tid, Applicatie.id == component_id)
        )
    ).scalar_one_or_none() is not None


async def haal_op(session: AsyncSession, tenant_id, component_id) -> Component:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Component).where(Component.id == component_id, Component.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, component_id)
    return obj


async def _lees(session: AsyncSession, tid: uuid.UUID, obj: Component) -> dict:
    type_labels = await catalog.labels(session, ComponentConfigDimensie.componenttype)
    return {
        "id": obj.id,
        "naam": obj.naam,
        "componenttype": obj.componenttype,
        "componenttype_label": catalog.resolveer_een(obj.componenttype, type_labels),
        "hostingmodel": obj.hostingmodel,
        "eigenaar_organisatie": obj.eigenaar_organisatie,
        "eigenaar_naam": obj.eigenaar_naam,
        "leverancier": obj.leverancier,
        "beschrijving": obj.beschrijving,
        "heeft_applicatie_subtype": await _heeft_subtype(session, tid, obj.id),
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


async def lees_detail(session: AsyncSession, tenant_id, component_id) -> dict:
    tid = _tenant_uuid(tenant_id)
    return await _lees(session, tid, await haal_op(session, tenant_id, component_id))


def _sorteer_waarde(comp: Component, app: Applicatie | None, sort: str):
    """Sleutelwaarde voor de cursor: subtype-kolommen van het (mogelijk afwezige)
    subtype, overige van de component."""
    if sort in ("complexiteit", "prioriteit", "lifecycle_status"):
        return getattr(app, sort) if app is not None else None
    return getattr(comp, sort)


async def lijst(
    session: AsyncSession, tenant_id, *, limit: int = _STANDAARD_LIMIT, after: str | None = None,
    sort: str = "created_at", order: str = "asc", componenttype: str | None = None,
    status: list[str] | None = None, hostingmodel: str | None = None,
    eigenaar: str | None = None, zoek: str | None = None,
) -> tuple[list[dict], str | None]:
    """Server-side sorteerbare, **filterbare** keyset-lijst (ADR-017 + CD017).

    Verenigd werkscherm (CD054b W1): LEFT JOIN op het applicatie-subtype levert de
    besturingsvelden (`eigenaar_organisatie`/`complexiteit`/`prioriteit`/
    `lifecycle_status` — null voor niet-subtypen). Sortering op een nullable
    subtype-kolom plaatst NULLs altijd achteraan (NULLS-LAST, v2n-cursor).

    Filters (AND, alle optioneel): `componenttype` (gelijkheid), `status` (reële
    lifecycle-statussen → IN, alleen subtypen matchen), `hostingmodel` (enum-
    gelijkheid), `eigenaar`/`zoek` (ge-escapete ILIKE-contains)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)
    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in ("asc", "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]

    stmt = (
        select(Component, Applicatie)
        .outerjoin(Applicatie, and_(Applicatie.id == Component.id, Applicatie.tenant_id == tid))
        .where(Component.tenant_id == tid)
    )
    if componenttype:
        stmt = stmt.where(Component.componenttype == componenttype)
    if status:
        stmt = stmt.where(Applicatie.lifecycle_status.in_([LifecycleStatus(s) for s in status]))
    if hostingmodel:
        stmt = stmt.where(Component.hostingmodel == HostingModel(hostingmodel))
    if eigenaar:
        stmt = stmt.where(
            Component.eigenaar_organisatie.ilike(f"%{_escape_like(eigenaar)}%", escape=_LIKE_ESCAPE)
        )
    if zoek:
        stmt = stmt.where(Component.naam.ilike(f"%{_escape_like(zoek)}%", escape=_LIKE_ESCAPE))
    if after:
        c_sort, c_order, c_isnull, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_isnull else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, Component.id, order=order, is_null=c_isnull, waarde=c_waarde, cursor_id=c_id
            )
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Component.id, order)).limit(limit + 1)

    rijen = list((await session.execute(stmt)).all())  # rijen van (Component, Applicatie|None)
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    type_labels = await catalog.labels(session, ComponentConfigDimensie.componenttype)
    out = [
        {
            "id": c.id, "naam": c.naam, "componenttype": c.componenttype,
            "componenttype_label": catalog.resolveer_een(c.componenttype, type_labels),
            "hostingmodel": c.hostingmodel,
            "heeft_applicatie_subtype": a is not None,
            "eigenaar_organisatie": c.eigenaar_organisatie,
            "complexiteit": a.complexiteit if a is not None else None,
            "prioriteit": a.prioriteit if a is not None else None,
            "lifecycle_status": a.lifecycle_status if a is not None else None,
        }
        for (c, a) in items
    ]
    if heeft_meer:
        laatste_comp, laatste_app = items[-1]
        volgende = encode_sort_cursor_nullable(
            sort=sort, order=order,
            waarde=_sorteer_waarde(laatste_comp, laatste_app, sort), id=laatste_comp.id,
        )
    else:
        volgende = None
    return out, volgende


async def maak_aan(session: AsyncSession, tenant_id, data: ComponentCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    if data.componenttype == _APPLICATIE_TYPE:
        # Convergente aanmaak (CD054b W1): atomair het applicatie-subtype met defaults,
        # via dezelfde service-kern als het applicatie-pad. Eigenaar mag leeg ("").
        from services import applicatie_service

        obj = await applicatie_service.maak_applicatie_subtype(
            session, tid,
            naam=data.naam, beschrijving=data.beschrijving, hostingmodel=data.hostingmodel,
            eigenaar_organisatie=data.eigenaar_organisatie or "",
            eigenaar_naam=data.eigenaar_naam, leverancier=data.leverancier,
            **_SUBTYPE_DEFAULTS,
        )
        return await _lees(session, tid, obj.component)
    await catalog.valideer_sleutel(session, ComponentConfigDimensie.componenttype, data.componenttype)
    obj = Component(
        tenant_id=tid, naam=data.naam, componenttype=data.componenttype,
        hostingmodel=data.hostingmodel,
        eigenaar_organisatie=data.eigenaar_organisatie or "",
        eigenaar_naam=data.eigenaar_naam, leverancier=data.leverancier,
        beschrijving=data.beschrijving,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return await _lees(session, tid, obj)


async def werk_bij(session: AsyncSession, tenant_id, component_id, data: ComponentUpdate) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, component_id)
    velden = data.model_dump(exclude_unset=True)
    if "componenttype" in velden and velden["componenttype"] is not None:
        nieuw = velden["componenttype"]
        if _APPLICATIE_TYPE in (nieuw, obj.componenttype):
            raise OngeldigeRegistratie(
                "SUBTYPE_BESCHERMD",
                "Een componenttype kan niet van of naar 'applicatie' worden gewijzigd.",
            )
        await catalog.valideer_sleutel(session, ComponentConfigDimensie.componenttype, nieuw)
    for veld, waarde in velden.items():
        if veld == "eigenaar_organisatie" and waarde is None:
            waarde = ""
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return await _lees(session, tid, obj)


async def verwijder(session: AsyncSession, tenant_id, component_id) -> None:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, component_id)

    if await _heeft_subtype(session, tid, component_id):
        # Convergent (CD054b W1): een subtype verwijdert via het applicatie-delete-pad —
        # eigen contracten/draait_op-structuur + engine-kinderen cascaden (bestaand gedrag).
        # Alleen de RESTRICT-relatie blokkeert: iets anders draait OP deze applicatie
        # (op_component_id) → 409 IN_GEBRUIK, vóór de DB-RESTRICT.
        onderlegger = select(ComponentStructuur.id).where(
            ComponentStructuur.tenant_id == tid, ComponentStructuur.op_component_id == component_id
        )
        if (await session.execute(onderlegger.limit(1))).scalar_one_or_none() is not None:
            raise RegistratieConflict(
                "IN_GEBRUIK", "Andere componenten draaien op deze applicatie; verwijderen niet toegestaan."
            )
        from services import applicatie_service

        await applicatie_service.verwijder(session, tenant_id, component_id)
        return

    # Kaal component: relaties beschermen (409 IN_GEBRUIK) — koppelingen, structuurrelaties
    # (beide richtingen), contract-koppelingen — vóór de DB CASCADE/RESTRICT.
    checks = [
        select(Koppeling.id).where(
            Koppeling.tenant_id == tid,
            or_(Koppeling.bron_applicatie_id == component_id, Koppeling.doel_applicatie_id == component_id),
        ),
        select(ComponentStructuur.id).where(
            ComponentStructuur.tenant_id == tid,
            or_(ComponentStructuur.component_id == component_id, ComponentStructuur.op_component_id == component_id),
        ),
        select(ComponentContract.id).where(
            ComponentContract.tenant_id == tid, ComponentContract.component_id == component_id
        ),
    ]
    for stmt in checks:
        if (await session.execute(stmt.limit(1))).scalar_one_or_none() is not None:
            raise RegistratieConflict(
                "IN_GEBRUIK", "Dit component heeft nog relaties en kan niet worden verwijderd."
            )
    obj = await haal_op(session, tenant_id, component_id)
    await session.delete(obj)
    await session.commit()


async def opties(session: AsyncSession) -> dict:
    """Actieve componentcatalogus-opties per dimensie (formulier-databron)."""
    return await catalog.actieve_opties_per_dimensie(session)


async def structuur_overzicht(session: AsyncSession, tenant_id, component_id) -> dict:
    """Beide richtingen van de structuurgraaf rond één component (ADR-021 Besluit 6)."""
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, component_id)
    rel_labels = await catalog.labels(session, ComponentConfigDimensie.structuurrelatie_type)

    async def _kant(eigen_fk, buur_fk) -> list[dict]:
        rijen = (
            await session.execute(
                select(
                    ComponentStructuur.id.label("structuur_id"),
                    buur_fk.label("buur_id"),
                    Component.naam.label("naam"),
                    Component.componenttype.label("componenttype"),
                    ComponentStructuur.relatietype.label("relatietype"),
                    ComponentStructuur.omschrijving.label("omschrijving"),
                )
                .join(Component, Component.id == buur_fk)
                .where(ComponentStructuur.tenant_id == tid, eigen_fk == component_id)
                .order_by(Component.naam, ComponentStructuur.id)
            )
        ).all()
        return [
            {
                "structuur_id": r.structuur_id, "component_id": r.buur_id, "naam": r.naam,
                "componenttype": r.componenttype, "relatietype": r.relatietype,
                "relatietype_label": catalog.resolveer_een(r.relatietype, rel_labels),
                "omschrijving": r.omschrijving,
            }
            for r in rijen
        ]

    return {
        "draait_op": await _kant(ComponentStructuur.component_id, ComponentStructuur.op_component_id),
        "gebruikt_door": await _kant(ComponentStructuur.op_component_id, ComponentStructuur.component_id),
    }
