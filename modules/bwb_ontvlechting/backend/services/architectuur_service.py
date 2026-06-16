"""Service-laag — cross-element laagprojectie (ADR-023 Fase F / F-2).

Eén read over de element-supertabel die ELK element-type uniform projecteert op zijn
ArchiMate-(archimate_element, laag, aspect), afgeleid uit de TWEE bestaande typing-bronnen:
- component → de catalogus (`componentconfig_catalog.archimate_typing`, per componenttype);
- alle overige element-typen → de vaste mapping `ELEMENT_ARCHIMATE_TYPING`.

De weergavenaam wordt per subtype afgeleid (geen `naam`-kolom op `element`): component/
plateau/gap/work_package/deliverable → `naam`, contract → `contractnaam`, datatype →
`categorie` (+ omschrijving secundair), gebruikersgroep → `organisatie`(+ afdeling).
Fallback `type id8` zodat een rij nooit leeg is.

Puur read-only, afgeleid — geen schema/migratie, engine onaangeroerd (bewust GEEN import
van lifecycle/profiel/blokkade/score). Keyset-paginering (`created_at`/`id`), RLS scoopt
op de tenant. Spiegelt het `relatie_service.lijst`-keysetpatroon.
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Component,
    Contract,
    Datatype,
    Deliverable,
    Element,
    ElementType,
    Gap,
    Gebruikersgroep,
    Plateau,
    WorkPackage,
)
from services import componentconfig_catalog as catalog
from services.archimate_typing import ELEMENT_ARCHIMATE_TYPING, typing_voor
from services.pagination import decode_sort_cursor, encode_sort_cursor

_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _et_value(et) -> str:
    return et.value if hasattr(et, "value") else str(et)


def _laag_aspect_cond(veld: str, waarde: str, catalog_typing: dict):
    """SQL-conditie voor een laag-/aspect-filter dat BEIDE typing-bronnen overspant:
    niet-component-typen via de vaste mapping, component via de catalogus-componenttypen."""
    vaste = [et for et, t in ELEMENT_ARCHIMATE_TYPING.items() if t.get(veld) == waarde]
    comp_types = [ct for ct, t in catalog_typing.items() if t.get(veld) == waarde]
    conds = []
    if vaste:
        conds.append(Element.element_type.in_(vaste))
    if comp_types:
        conds.append(
            and_(Element.element_type == ElementType.component, Component.componenttype.in_(comp_types))
        )
    return or_(*conds) if conds else false()


def _naam(r) -> str:
    """Weergavenaam per subtype (afgeleid). Fallback: `type id8`."""
    et = _et_value(r.element_type)
    naam = None
    if et == "component":
        naam = r.component_naam
    elif et == "contract":
        naam = r.contract_naam
    elif et == "datatype":
        naam = _et_value(r.datatype_categorie) if r.datatype_categorie is not None else None
    elif et == "gebruikersgroep":
        if r.gg_organisatie:
            naam = f"{r.gg_organisatie} — {r.gg_afdeling}" if r.gg_afdeling else r.gg_organisatie
    elif et == "plateau":
        naam = r.plateau_naam
    elif et == "gap":
        naam = r.gap_naam
    elif et == "work_package":
        naam = r.wp_naam
    elif et == "deliverable":
        naam = r.deliverable_naam
    return naam or f"{et} {str(r.id)[:8]}"


def _naam_secundair(r) -> str | None:
    """Tweede regel/tooltip: voor datatype de omschrijving (categorie is de primaire naam)."""
    if _et_value(r.element_type) == "datatype":
        return r.datatype_omschrijving
    return None


def _typing(r, catalog_typing: dict) -> dict:
    if _et_value(r.element_type) == "component":
        return catalog_typing.get(r.componenttype, {}) or {}
    return typing_voor(r.element_type) or {}


def _lees(r, catalog_typing: dict) -> dict:
    t = _typing(r, catalog_typing)
    return {
        "id": r.id,
        "element_type": _et_value(r.element_type),
        "naam": _naam(r),
        "naam_secundair": _naam_secundair(r),
        "archimate_element": t.get("archimate_element"),
        "laag": t.get("laag"),
        "aspect": t.get("aspect"),
    }


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    laag: str | None = None,
    aspect: str | None = None,
    type: str | None = None,
) -> tuple[list[dict], str | None]:
    """Cross-element laagprojectie (keyset op `created_at`/`id`). Filters `laag`/`aspect`
    (afgeleid uit beide typing-bronnen) + `type` (element_type). Cursor-mismatch ⇒
    `ValueError` (route ⇒ 400)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)
    catalog_typing = await catalog.archimate_typing(session)

    stmt = (
        select(
            Element.id,
            Element.element_type,
            Element.created_at,
            Component.naam.label("component_naam"),
            Component.componenttype.label("componenttype"),
            Contract.contractnaam.label("contract_naam"),
            Datatype.categorie.label("datatype_categorie"),
            Datatype.omschrijving.label("datatype_omschrijving"),
            Gebruikersgroep.organisatie.label("gg_organisatie"),
            Gebruikersgroep.afdeling.label("gg_afdeling"),
            Plateau.naam.label("plateau_naam"),
            Gap.naam.label("gap_naam"),
            WorkPackage.naam.label("wp_naam"),
            Deliverable.naam.label("deliverable_naam"),
        )
        .outerjoin(Component, and_(Component.id == Element.id, Component.tenant_id == tid))
        .outerjoin(Contract, and_(Contract.id == Element.id, Contract.tenant_id == tid))
        .outerjoin(Datatype, and_(Datatype.id == Element.id, Datatype.tenant_id == tid))
        .outerjoin(Gebruikersgroep, and_(Gebruikersgroep.id == Element.id, Gebruikersgroep.tenant_id == tid))
        .outerjoin(Plateau, and_(Plateau.id == Element.id, Plateau.tenant_id == tid))
        .outerjoin(Gap, and_(Gap.id == Element.id, Gap.tenant_id == tid))
        .outerjoin(WorkPackage, and_(WorkPackage.id == Element.id, WorkPackage.tenant_id == tid))
        .outerjoin(Deliverable, and_(Deliverable.id == Element.id, Deliverable.tenant_id == tid))
        .where(Element.tenant_id == tid)
    )

    if type:
        stmt = stmt.where(Element.element_type == ElementType(type))
    if laag:
        stmt = stmt.where(_laag_aspect_cond("laag", laag, catalog_typing))
    if aspect:
        stmt = stmt.where(_laag_aspect_cond("aspect", aspect, catalog_typing))
    if after:
        _s, _o, waarde_str, c_id = decode_sort_cursor(after)
        c_waarde = datetime.fromisoformat(waarde_str)
        stmt = stmt.where(
            or_(
                Element.created_at > c_waarde,
                and_(Element.created_at == c_waarde, Element.id > c_id),
            )
        )
    stmt = stmt.order_by(Element.created_at.asc(), Element.id.asc()).limit(limit + 1)

    rijen = (await session.execute(stmt)).all()
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor(sort="created_at", order="asc", waarde=items[-1].created_at, id=items[-1].id)
        if heeft_meer else None
    )
    return [_lees(r, catalog_typing) for r in items], volgende
