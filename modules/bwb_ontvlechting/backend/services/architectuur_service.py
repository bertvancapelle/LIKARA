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

from sqlalchemy import String, and_, case, cast, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import (
    Component,
    ComponentConfigDimensie,
    ComponentConfigOptie,
    Contract,
    Datatype,
    Deliverable,
    Element,
    ElementType,
    Gap,
    Gebruikersgroep,
    Partij,
    Plateau,
    WorkPackage,
)
from services import componentconfig_catalog as catalog
from services.archimate_typing import ELEMENT_ARCHIMATE_TYPING, typing_voor
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"

# ADR-017 — allowlist van sorteervelden (single source náást de route-enum; een test borgt
# de synchroniteit). De SQL-expressies zelf worden per-call gebouwd (ze refereren aan de
# join-alias + subtype-tabellen) in `_sorteer_expressies`. `naam`/`laag`/`aspect`/`soort`
# zijn read-only afgeleid in SQL — geen opgeslagen tweede bron.
_SORTEERVELDEN = frozenset({"created_at", "naam", "type", "laag", "aspect", "soort"})
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "naam": str, "type": str, "laag": str, "aspect": str, "soort": str,
}


def _static_typing_case(veld: str):
    """SQL-CASE voor de VASTE element-typing, dynamisch uit `ELEMENT_ARCHIMATE_TYPING`
    gebouwd (single source — geen hand-gekopieerde mapping). `component` zit er niet in →
    NULL → de coalesce valt terug op de catalogus-typing (per componenttype)."""
    whens = [(Element.element_type == et, typing[veld]) for et, typing in ELEMENT_ARCHIMATE_TYPING.items()]
    return case(*whens, else_=None)


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
        if r.gg_org_naam:
            naam = f"{r.gg_org_naam} — {r.gg_afdeling}" if r.gg_afdeling else r.gg_org_naam
    elif et == "plateau":
        naam = r.plateau_naam
    elif et == "gap":
        naam = r.gap_naam
    elif et == "work_package":
        naam = r.wp_naam
    elif et == "deliverable":
        naam = r.deliverable_naam
    elif et == "partij":
        naam = r.partij_naam
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
        # ADR-024 — alleen voor partij-elementen: de aard (organisatie/persoon/externe_partij/…).
        "partij_aard": (_et_value(r.partij_aard)
                        if _et_value(r.element_type) == "partij" and r.partij_aard is not None else None),
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
    sort: str = _STANDAARD_SORT,
    order: str = _STANDAARD_ORDER,
) -> tuple[list[dict], str | None]:
    """Cross-element laagprojectie, server-side sorteerbaar (ADR-017 v2n-keyset) op
    `naam`/`type`/`laag`/`aspect`/`soort` (+ default `created_at`). Naam/laag/aspect/soort
    worden in SQL afgeleid (coalesce over subtype-naamkolommen resp. de vaste typing-CASE +
    de componenttype-catalogus) — read-only, geen opgeslagen tweede bron. Filters `laag`/
    `aspect`/`type` ongewijzigd. Onbekend sort/order of cursor-mismatch ⇒ `ValueError`."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)
    if sort not in _SORTEERVELDEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    catalog_typing = await catalog.archimate_typing(session)

    # Catalogus-typing per componenttype via een join (component-tak van de coalesce).
    cc = aliased(ComponentConfigOptie)
    # UX-B6-a — gebruikersgroep-organisatie is nu een partij-verwijzing; join voor de display-naam.
    gg_org = aliased(Partij)
    partij_self = aliased(Partij)  # partij-element zelf (element.id == partij.id) — eigen naam/aard
    naam_expr = func.coalesce(
        Component.naam, Contract.contractnaam, cast(Datatype.categorie, String),
        gg_org.naam, Plateau.naam, Gap.naam, WorkPackage.naam, Deliverable.naam,
        partij_self.naam,
    )
    laag_expr = func.coalesce(_static_typing_case("laag"), cc.laag)
    aspect_expr = func.coalesce(_static_typing_case("aspect"), cc.aspect)
    soort_expr = func.coalesce(_static_typing_case("archimate_element"), cc.archimate_element)
    sorteer = {
        "created_at": Element.created_at, "naam": naam_expr, "type": cast(Element.element_type, String),
        "laag": laag_expr, "aspect": aspect_expr, "soort": soort_expr,
    }
    kolom = sorteer[sort]

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
            gg_org.naam.label("gg_org_naam"),
            Gebruikersgroep.afdeling.label("gg_afdeling"),
            Plateau.naam.label("plateau_naam"),
            Gap.naam.label("gap_naam"),
            WorkPackage.naam.label("wp_naam"),
            Deliverable.naam.label("deliverable_naam"),
            partij_self.naam.label("partij_naam"),
            partij_self.aard.label("partij_aard"),
            kolom.label("sorteerwaarde"),
        )
        .outerjoin(Component, and_(Component.id == Element.id, Component.tenant_id == tid))
        .outerjoin(Contract, and_(Contract.id == Element.id, Contract.tenant_id == tid))
        .outerjoin(Datatype, and_(Datatype.id == Element.id, Datatype.tenant_id == tid))
        .outerjoin(Gebruikersgroep, and_(Gebruikersgroep.id == Element.id, Gebruikersgroep.tenant_id == tid))
        .outerjoin(gg_org, and_(gg_org.id == Gebruikersgroep.organisatie_id, gg_org.tenant_id == tid))
        .outerjoin(Plateau, and_(Plateau.id == Element.id, Plateau.tenant_id == tid))
        .outerjoin(Gap, and_(Gap.id == Element.id, Gap.tenant_id == tid))
        .outerjoin(WorkPackage, and_(WorkPackage.id == Element.id, WorkPackage.tenant_id == tid))
        .outerjoin(Deliverable, and_(Deliverable.id == Element.id, Deliverable.tenant_id == tid))
        .outerjoin(partij_self, and_(partij_self.id == Element.id, partij_self.tenant_id == tid))
        .outerjoin(cc, and_(cc.dimensie == ComponentConfigDimensie.componenttype, cc.optie_sleutel == Component.componenttype))
        .where(Element.tenant_id == tid)
    )

    if type:
        stmt = stmt.where(Element.element_type == ElementType(type))
    if laag:
        stmt = stmt.where(_laag_aspect_cond("laag", laag, catalog_typing))
    if aspect:
        stmt = stmt.where(_laag_aspect_cond("aspect", aspect, catalog_typing))
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(kolom, Element.id, order=order, is_null=c_is_null, waarde=c_waarde, cursor_id=c_id)
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Element.id, order)).limit(limit + 1)

    rijen = (await session.execute(stmt)).all()
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor_nullable(sort=sort, order=order, waarde=items[-1].sorteerwaarde, id=items[-1].id)
        if heeft_meer else None
    )
    return [_lees(r, catalog_typing) for r in items], volgende
