"""Service-laag voor Component (ADR-021 Besluit 1/4/6/9 — Fase B).

Tenant-scoped (RLS + expliciet `tenant_id`-filter; OP-6 kruis-tenant → 404). Het type
`applicatie` is een beschermde systeem-sleutel: applicaties ontstaan/verdwijnen uitsluitend
via het applicatie-pad (CD051). `componenttype`/`relatietype` worden tegen de actieve
componentcatalogus gevalideerd.
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, case, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, lazyload

from models.models import (
    Applicatie,
    Blokkade,
    BlokkadeStatus,
    Checklistscore,
    Component,
    ComponentConfigDimensie,
    ComponentKlaarverklaring,
    ComponentProfiel,
    Contract,
    Datatype,
    Element,
    ElementType,
    Gebruikersgroep,
    HostingModel,
    KlaarverklaringStatus,
    LifecycleStatus,
    Migratiepad,
    NiveauEnum,
    Partij,
    Relatie,
    Roltoewijzing,
)

# Rollen waaruit een externe partij als "leverancier" geldt (zelfde keten als landschapskaart-lev_map).
_LEVERANCIER_ROLLEN = ("technisch_beheer", "contractbeheer")

# ADR-023 — structurele relaties leven nu in `Relatie`: `assignment` (draait_op,
# oriëntatie host→gehoste = bron→doel) en `aggregation` (maakt_deel_uit_van, deel→geheel).
_STRUCTUUR_TYPES = ("assignment", "aggregation")
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
    # ADR-024 UX-B6-b — `eigenaar` sorteert op de naam van de gekoppelde organisatie-partij
    # (per-call alias in `lijst`); de dict-waarde hier is een placeholder voor de allowlist-test.
    "eigenaar": Component.eigenaar_organisatie_id,
    "hostingmodel": Component.hostingmodel,
    "complexiteit": Applicatie.complexiteit,
    "prioriteit": Applicatie.prioriteit,
    # ADR-022 Fase A: lifecycle_status leeft op het generieke profiel (shared-PK).
    "lifecycle_status": ComponentProfiel.lifecycle_status,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "naam": str,
    "componenttype": str,
    "eigenaar": str,
    "hostingmodel": HostingModel,  # enum (cursor round-trip via .value)
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


async def _toestand_tellingen(
    session: AsyncSession, tid: uuid.UUID, component_id, *, lock: bool = False
) -> dict:
    """Tel wat een component "gevuld" maakt (ADR-022 Fase C, Beslissing-drempel):
    beantwoorde scores (`score IS NOT NULL`), blokkades, gekoppelde datatypes/
    gebruikersgroepen (applicatie-only, Beslissing 5b), plus de profiel-lifecycle.
    Transactie-lokaal: met `lock=True` wordt het profiel `FOR UPDATE` gelezen zodat
    de toestand tijdens een type-wissel niet onder ons kan veranderen."""
    async def _count(stmt) -> int:
        return (await session.execute(stmt)).scalar_one()

    beantwoorde_scores = await _count(
        select(func.count()).select_from(Checklistscore).where(
            Checklistscore.tenant_id == tid,
            Checklistscore.component_id == component_id,
            Checklistscore.score.is_not(None),
        )
    )
    blokkades = await _count(
        select(func.count()).select_from(Blokkade).where(
            Blokkade.tenant_id == tid, Blokkade.component_id == component_id
        )
    )
    # ADR-023 slice 4: datatype/gebruikersgroep hangen nu via access/serving-relaties aan
    # de applicatie (bron = dit component) i.p.v. een applicatie_id-kolom.
    datatypes = await _count(
        select(func.count()).select_from(Relatie).where(
            Relatie.tenant_id == tid, Relatie.bron_id == component_id, Relatie.relatietype == "access"
        )
    )
    gebruikersgroepen = await _count(
        select(func.count()).select_from(Relatie).where(
            Relatie.tenant_id == tid, Relatie.bron_id == component_id, Relatie.relatietype == "serving"
        )
    )
    lc_stmt = select(ComponentProfiel.lifecycle_status).where(
        ComponentProfiel.tenant_id == tid, ComponentProfiel.id == component_id
    )
    if lock:
        lc_stmt = lc_stmt.with_for_update()
    lifecycle = (await session.execute(lc_stmt)).scalar_one_or_none()
    return {
        "beantwoorde_scores": beantwoorde_scores,
        "blokkades": blokkades,
        "datatypes": datatypes,
        "gebruikersgroepen": gebruikersgroepen,
        "lifecycle_status": lifecycle,
        # Bron van waarheid: een component is gevuld (type vergrendeld) als er engine-
        # data is óf de lifecycle de `concept`-vloer voorbij is.
        "gevuld": (
            beantwoorde_scores > 0 or blokkades > 0 or datatypes > 0 or gebruikersgroepen > 0
            or (lifecycle is not None and lifecycle != LifecycleStatus.concept)
        ),
    }


def _heeft_data_bericht(t: dict) -> str:
    """Canoniek SUBTYPE_HEEFT_DATA-bericht dat opsomt wát het type vergrendelt."""
    delen = []
    if t["beantwoorde_scores"]:
        delen.append(f"{t['beantwoorde_scores']} beantwoorde score(s)")
    if t["blokkades"]:
        delen.append(f"{t['blokkades']} blokkade(s)")
    if t["datatypes"]:
        delen.append(f"{t['datatypes']} datatype(s)")
    if t["gebruikersgroepen"]:
        delen.append(f"{t['gebruikersgroepen']} gebruikersgroep(en)")
    if t["lifecycle_status"] is not None and t["lifecycle_status"] != LifecycleStatus.concept:
        delen.append("een lifecycle voorbij 'concept'")
    kern = ", ".join(delen) if delen else "bestaande gegevens"
    return f"Type vergrendeld: dit component heeft {kern} en kan niet van type wisselen."


async def wat_verdwijnt(session: AsyncSession, tenant_id, component_id) -> dict:
    """Read-only samenvatting van wat een verwijdering zou wissen (geen mutatie,
    geen audit — ADR-006 volgt). Tenant-scoped; onbekend component ⇒ 404."""
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, component_id)  # 404 kruis-tenant (OP-6)
    t = await _toestand_tellingen(session, tid, component_id)
    return {
        "beantwoorde_scores": t["beantwoorde_scores"],
        "blokkades": t["blokkades"],
        "datatypes": t["datatypes"],
        "gebruikersgroepen": t["gebruikersgroepen"],
    }


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
    # ADR-023 Fase C: ArchiMate-typing (laag/element) uit de catalogus — read-only projectie.
    typing = (await catalog.archimate_typing(session)).get(obj.componenttype, {})
    return {
        "id": obj.id,
        "naam": obj.naam,
        "componenttype": obj.componenttype,
        "componenttype_label": catalog.resolveer_een(obj.componenttype, type_labels),
        "archimate_element": typing.get("archimate_element"),
        "laag": typing.get("laag"),
        "hostingmodel": obj.hostingmodel,
        "eigenaar_organisatie_id": obj.eigenaar_organisatie_id,
        "eigenaar_organisatie_naam": (
            (
                await session.execute(
                    select(Partij.naam).where(
                        Partij.id == obj.eigenaar_organisatie_id, Partij.tenant_id == tid
                    )
                )
            ).scalar_one_or_none()
            if obj.eigenaar_organisatie_id is not None
            else None
        ),
        "beschrijving": obj.beschrijving,
        "heeft_applicatie_subtype": await _heeft_subtype(session, tid, obj.id),
        # ADR-022 Fase E: of dit componenttype checklist-dragend is (UI toont dan de
        # checklist-sectie + start-knop ook voor niet-`applicatie`-componenten).
        "checklist_dragend": await catalog.is_checklist_dragend(session, obj.componenttype),
        # ADR-022 Fase E: lifecycle uit het generieke profiel (null als geen profiel) —
        # voedt de status-indicator + de "Start beoordeling"-knop (zichtbaar bij `concept`).
        "lifecycle_status": (
            await session.execute(
                select(ComponentProfiel.lifecycle_status).where(
                    ComponentProfiel.id == obj.id, ComponentProfiel.tenant_id == tid
                )
            )
        ).scalar_one_or_none(),
        # ADR-022 Fase C: capability-hint voor de UI (de PATCH herevalueert zelf).
        "type_wijzigbaar": not (await _toestand_tellingen(session, tid, obj.id))["gevuld"],
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


async def start_beoordeling(session: AsyncSession, tenant_id, component_id) -> dict:
    """ADR-022 Fase E — type-generieke "start beoordeling" (concept → in_inventarisatie)
    op een checklist-dragend component. Onbekend component ⇒ 404; geen profiel
    (niet checklist-dragend) ⇒ 404; niet vanuit `concept` ⇒ 409 (in lifecycle_service)."""
    from services import lifecycle_service

    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, component_id)  # 404 kruis-tenant (OP-6)
    await lifecycle_service.start_beoordeling(session, tid, component_id)
    await session.commit()
    await session.refresh(obj)
    return await _lees(session, tid, obj)


async def lees_detail(session: AsyncSession, tenant_id, component_id) -> dict:
    tid = _tenant_uuid(tenant_id)
    return await _lees(session, tid, await haal_op(session, tenant_id, component_id))


def _sorteer_waarde(comp: Component, app: Applicatie | None, lifecycle, eig_naam, sort: str):
    """Sleutelwaarde voor de cursor: subtype-kolommen van het (mogelijk afwezige) subtype,
    `lifecycle_status` van het profiel, `eigenaar` = de organisatie-naam (gejoind), overige
    van de component."""
    if sort == "lifecycle_status":
        return lifecycle
    if sort in ("complexiteit", "prioriteit"):
        return getattr(app, sort) if app is not None else None
    if sort == "eigenaar":
        return eig_naam  # UX-B6-b: sorteren op de naam van de gekoppelde organisatie-partij
    return getattr(comp, sort)  # naam / componenttype / hostingmodel / created_at


async def lijst(
    session: AsyncSession, tenant_id, *, limit: int = _STANDAARD_LIMIT, after: str | None = None,
    sort: str = "created_at", order: str = "asc", componenttype: str | None = None,
    laag: str | None = None, status: list[str] | None = None, hostingmodel: str | None = None,
    eigenaar_organisatie_id: uuid.UUID | None = None, leverancier_id: uuid.UUID | None = None,
    zoek: str | None = None,
    klaarverklaring: str | None = None, afwijking: bool = False,
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
    # UX-B6-b — eigenaar-organisatie als gejoinde partij; `eigenaar` sorteert op de org-naam.
    eig = aliased(Partij)
    kolom = eig.naam if sort == "eigenaar" else _SORTEERBARE_KOLOMMEN[sort]

    stmt = (
        # ADR-022 Fase A: lifecycle_status komt expliciet uit het profiel; de
        # Applicatie-eager-load van `profiel` wordt onderdrukt (`lazyload`) zodat de
        # query één join naar component_profiel houdt. UX-B6-b: LEFT JOIN de eigenaar-org-partij
        # voor naam-in-read + sortering op naam.
        select(Component, Applicatie, ComponentProfiel.lifecycle_status.label("lifecycle_status"),
               eig.naam.label("eigenaar_organisatie_naam"))
        .outerjoin(Applicatie, and_(Applicatie.id == Component.id, Applicatie.tenant_id == tid))
        .outerjoin(ComponentProfiel, and_(ComponentProfiel.id == Component.id, ComponentProfiel.tenant_id == tid))
        .outerjoin(eig, and_(eig.id == Component.eigenaar_organisatie_id, eig.tenant_id == tid))
        .options(lazyload(Applicatie.profiel))
        .where(Component.tenant_id == tid)
    )
    # ADR-023 Fase C: ArchiMate-typing voor het laag-filter (read-only) + per-rij projectie.
    typing = await catalog.archimate_typing(session)
    if componenttype:
        stmt = stmt.where(Component.componenttype == componenttype)
    if laag:
        # Resolveer de laag naar de componenttypen die erin vallen (catalogus-typing) en
        # filter daarop. Geen componenttype in deze laag ⇒ lege set ⇒ geen resultaten.
        typen_in_laag = [t for t, info in typing.items() if info.get("laag") == laag]
        stmt = stmt.where(Component.componenttype.in_(typen_in_laag))
    if status:
        stmt = stmt.where(ComponentProfiel.lifecycle_status.in_([LifecycleStatus(s) for s in status]))
    if hostingmodel:
        stmt = stmt.where(Component.hostingmodel == HostingModel(hostingmodel))
    if eigenaar_organisatie_id:
        stmt = stmt.where(Component.eigenaar_organisatie_id == eigenaar_organisatie_id)
    if leverancier_id:
        # Leverancier is GEEN Component-kolom — afgeleid (zelfde keten als landschapskaart_service.lev_map):
        # (a) roltoewijzing technisch_beheer/contractbeheer op dit component door deze externe partij, OF
        # (b) association → contract met deze leverancier. EXISTS-subqueries → geen extra join, paginering intact.
        _rt_lev = (
            select(Roltoewijzing.id).where(
                Roltoewijzing.tenant_id == tid, Roltoewijzing.object_id == Component.id,
                Roltoewijzing.partij_id == leverancier_id, Roltoewijzing.rol.in_(_LEVERANCIER_ROLLEN))
        ).exists()
        _ct_lev = (
            select(Relatie.id).join(Contract, Contract.id == Relatie.doel_id).where(
                Relatie.tenant_id == tid, Relatie.bron_id == Component.id,
                Relatie.relatietype == "association", Contract.leverancier_id == leverancier_id)
        ).exists()
        stmt = stmt.where(or_(_rt_lev, _ct_lev))
    if zoek:
        stmt = stmt.where(Component.naam.ilike(f"%{_escape_like(zoek)}%", escape=_LIKE_ESCAPE))
    # ADR-027 slice 3 — klaarverklaring-filters (doorklik vanaf het dashboard). `afwijking`
    # impliceert de klaar-join + lifecycle ∉ {migratieklaar, geblokkeerd} (de vragen-stand uit
    # de bestaande engine-status; geen tweede telling). Engine ongemoeid (read-only filter).
    if klaarverklaring == KlaarverklaringStatus.klaar.value or afwijking:
        stmt = stmt.join(
            ComponentKlaarverklaring,
            and_(
                ComponentKlaarverklaring.component_id == Component.id,
                ComponentKlaarverklaring.tenant_id == tid,
                ComponentKlaarverklaring.status == KlaarverklaringStatus.klaar,
            ),
        )
    if afwijking:
        stmt = stmt.where(
            ComponentProfiel.lifecycle_status.notin_(
                [LifecycleStatus.migratieklaar, LifecycleStatus.geblokkeerd]
            )
        )
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

    rijen = list((await session.execute(stmt)).all())  # (Component, Applicatie|None, lifecycle|None, eigenaar_org_naam|None)
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    type_labels = await catalog.labels(session, ComponentConfigDimensie.componenttype)
    out = [
        {
            "id": c.id, "naam": c.naam, "componenttype": c.componenttype,
            "componenttype_label": catalog.resolveer_een(c.componenttype, type_labels),
            "archimate_element": typing.get(c.componenttype, {}).get("archimate_element"),
            "laag": typing.get(c.componenttype, {}).get("laag"),
            "hostingmodel": c.hostingmodel,
            "heeft_applicatie_subtype": a is not None,
            "eigenaar_organisatie_id": c.eigenaar_organisatie_id,
            "eigenaar_organisatie_naam": eig_naam,
            "complexiteit": a.complexiteit if a is not None else None,
            "prioriteit": a.prioriteit if a is not None else None,
            "lifecycle_status": lc,
        }
        for (c, a, lc, eig_naam) in items
    ]
    if heeft_meer:
        laatste_comp, laatste_app, laatste_lc, laatste_eig = items[-1]
        volgende = encode_sort_cursor_nullable(
            sort=sort, order=order,
            waarde=_sorteer_waarde(laatste_comp, laatste_app, laatste_lc, laatste_eig, sort),
            id=laatste_comp.id,
        )
    else:
        volgende = None
    return out, volgende


async def maak_aan(session: AsyncSession, tenant_id, data: ComponentCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    # UX-B6-b — als een eigenaar-organisatie is opgegeven, valideer dat het een organisatie-partij is.
    if data.eigenaar_organisatie_id is not None:
        from services import partij_service
        await partij_service.valideer_organisatie(session, tid, data.eigenaar_organisatie_id)
    if data.componenttype == _APPLICATIE_TYPE:
        # Convergente aanmaak (CD054b W1): atomair het applicatie-subtype met defaults,
        # via dezelfde service-kern als het applicatie-pad. Eigenaar-organisatie optioneel.
        from services import applicatie_service

        obj = await applicatie_service.maak_applicatie_subtype(
            session, tid,
            naam=data.naam, beschrijving=data.beschrijving, hostingmodel=data.hostingmodel,
            eigenaar_organisatie_id=data.eigenaar_organisatie_id,
            **_SUBTYPE_DEFAULTS,
        )
        return await _lees(session, tid, obj.component)
    await catalog.valideer_sleutel(session, ComponentConfigDimensie.componenttype, data.componenttype)
    # ADR-023: element-identiteit eerst (shared-PK), daarna de component met dezelfde id.
    elem = Element(tenant_id=tid, element_type=ElementType.component)
    session.add(elem)
    await session.flush()
    obj = Component(
        id=elem.id, tenant_id=tid, naam=data.naam, componenttype=data.componenttype,
        hostingmodel=data.hostingmodel,
        eigenaar_organisatie_id=data.eigenaar_organisatie_id,
        beschrijving=data.beschrijving,
    )
    session.add(obj)
    await session.flush()  # obj.id beschikbaar voor een eventueel profiel
    # ADR-022 Fase E (Besluit 1+2): een checklist-dragend (niet-`applicatie`) type krijgt
    # een generiek profiel ZONDER subtype-tabel; engine-state start in `concept`.
    if await catalog.is_checklist_dragend(session, data.componenttype):
        session.add(
            ComponentProfiel(id=obj.id, tenant_id=tid, lifecycle_status=LifecycleStatus.concept)
        )
    await session.commit()
    await session.refresh(obj)
    return await _lees(session, tid, obj)


async def _wissel_type(session: AsyncSession, tid: uuid.UUID, obj: Component, nieuw: str) -> None:
    """Toestand-gebaseerde type-wissel (ADR-022 Fase C). Backend = bron van waarheid:
    transactie-lokaal herwaarderen en de invariant afdwingen.

    - Gevuld → `SUBTYPE_HEEFT_DATA` (422), met tellingen in het bericht.
    - Leeg → schone lei: een leeg profiel (+ applicatie-subtype indien aanwezig, + lege
      niet-beantwoorde score-rijen via CASCADE) wordt verwijderd; géén overdracht van oude
      scores. ADR-022 Fase E (Besluit 2): is het doeltype checklist-dragend, dan ontstaat een
      vers profiel met defaults (lifecycle `concept`, Fase B-vloer); alléén `applicatie` krijgt
      daarnaast zijn subtype-rij. Niet-checklist-dragend doeltype ⇒ geen profiel.
    """
    await catalog.valideer_sleutel(session, ComponentConfigDimensie.componenttype, nieuw)
    t = await _toestand_tellingen(session, tid, obj.id, lock=True)
    if t["gevuld"]:
        raise OngeldigeRegistratie("SUBTYPE_HEEFT_DATA", _heeft_data_bericht(t))

    # Leeg: ruim een eventueel (leeg) profiel én applicatie-subtype op — onafhankelijk
    # van elkaar, want een niet-`applicatie` checklist-dragend type heeft wél een profiel
    # maar géén subtype. Profiel-delete cascadeert niet-beantwoorde scores/blokkades;
    # subtype-delete cascadeert (afwezige) datatypes/gebruikersgroepen.
    await session.execute(delete(ComponentProfiel).where(ComponentProfiel.id == obj.id))
    await session.execute(delete(Applicatie).where(Applicatie.id == obj.id))
    await session.flush()

    obj.componenttype = nieuw

    if nieuw == _APPLICATIE_TYPE:
        # Promotie naar `applicatie`: subtype-rij (type-eigen velden) + generiek profiel.
        session.add(Applicatie(id=obj.id, tenant_id=tid, **_SUBTYPE_DEFAULTS))
        session.add(
            ComponentProfiel(id=obj.id, tenant_id=tid, lifecycle_status=LifecycleStatus.concept)
        )
        await session.flush()
    elif await catalog.is_checklist_dragend(session, nieuw):
        # Promotie naar een ander checklist-dragend type: alléén het generieke profiel.
        session.add(
            ComponentProfiel(id=obj.id, tenant_id=tid, lifecycle_status=LifecycleStatus.concept)
        )
        await session.flush()


async def werk_bij(session: AsyncSession, tenant_id, component_id, data: ComponentUpdate) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, component_id)
    velden = data.model_dump(exclude_unset=True)
    nieuw_type = velden.pop("componenttype", None)
    if nieuw_type is not None and nieuw_type != obj.componenttype:
        await _wissel_type(session, tid, obj, nieuw_type)
    # UX-B6-b — eigenaar-organisatie wijzigen: valideer aard=organisatie als een id wordt gezet.
    if velden.get("eigenaar_organisatie_id") is not None:
        from services import partij_service
        await partij_service.valideer_organisatie(session, tid, velden["eigenaar_organisatie_id"])
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return await _lees(session, tid, obj)


async def verwijder(session: AsyncSession, tenant_id, component_id) -> None:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, component_id)

    if await _heeft_subtype(session, tid, component_id):
        # Convergent (CD054b W1): een subtype verwijdert via het applicatie-delete-pad.
        # ADR-023 B-mig-2 slice 2 (Besluit 13): structurele relaties (assignment/aggregation)
        # blokkeren een delete NIET meer — ze cascaden via het element. Geen onderlegger-check.
        from services import applicatie_service

        await applicatie_service.verwijder(session, tenant_id, component_id)
        return

    # Kaal component: ADR-023 (Besluit 13) — álle relaties (flow/assignment/aggregation/
    # association) cascaden via het element en blokkeren een delete niet meer.
    # ADR-023: verwijder via het element-supertype (cascade element → component → kinderen);
    # de losse component-rij zou een wees-element achterlaten.
    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == component_id))
    await session.commit()


async def opties(session: AsyncSession) -> dict:
    """Actieve componentcatalogus-opties per dimensie (formulier-databron)."""
    return await catalog.actieve_opties_per_dimensie(session)


async def structuur_overzicht(session: AsyncSession, tenant_id, component_id) -> dict:
    """Beide richtingen van de structuurgraaf rond één component (ADR-023 op `Relatie`).

    `draait_op` = uitgaand (self is afhankelijk: assignment doel=self / aggregation bron=self);
    `gebruikt_door` = inkomend (self is host/geheel: assignment bron=self / aggregation
    doel=self). De API-vorm blijft gelijk (`structuur_id` = nu de relatie-id)."""
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, component_id)
    rel_labels = await catalog.labels(session, ComponentConfigDimensie.archimate_relatie)

    async def _kant(uitgaand: bool) -> list[dict]:
        if uitgaand:
            buur = case((Relatie.relatietype == "assignment", Relatie.bron_id), else_=Relatie.doel_id)
            cond = or_(
                and_(Relatie.relatietype == "assignment", Relatie.doel_id == component_id),
                and_(Relatie.relatietype == "aggregation", Relatie.bron_id == component_id),
            )
        else:
            buur = case((Relatie.relatietype == "assignment", Relatie.doel_id), else_=Relatie.bron_id)
            cond = or_(
                and_(Relatie.relatietype == "assignment", Relatie.bron_id == component_id),
                and_(Relatie.relatietype == "aggregation", Relatie.doel_id == component_id),
            )
        rijen = (
            await session.execute(
                select(
                    Relatie.id.label("relatie_id"),
                    buur.label("buur_id"),
                    Component.naam.label("naam"),
                    Component.componenttype.label("componenttype"),
                    Relatie.relatietype.label("relatietype"),
                    Relatie.omschrijving.label("omschrijving"),
                )
                .join(Component, Component.id == buur)
                .where(Relatie.tenant_id == tid, Relatie.relatietype.in_(_STRUCTUUR_TYPES), cond)
                .order_by(Component.naam, Relatie.id)
            )
        ).all()
        return [
            {
                "structuur_id": r.relatie_id, "component_id": r.buur_id, "naam": r.naam,
                "componenttype": r.componenttype, "relatietype": r.relatietype,
                "relatietype_label": catalog.resolveer_een(r.relatietype, rel_labels),
                "omschrijving": r.omschrijving,
            }
            for r in rijen
        ]

    return {
        "draait_op": await _kant(uitgaand=True),
        "gebruikt_door": await _kant(uitgaand=False),
    }


async def impact_analyse(session: AsyncSession, tenant_id, component_id) -> dict:
    """Read-only impactanalyse (ADR-021 Besluit 10 / Fase E).

    Volgt de afhankelijkheidsgraaf in de richting `gebruikt_door` (wie steunt — direct of
    transitief — op dít component). Getraverseerde relatietypen: `assignment` (host→gehoste),
    `aggregation` (deel→geheel) en `flow` (koppeling — bidirectioneel: de afhankelijke is de
    andere endpoint, ongeacht bron/doel; LI019). Iteratieve BFS per niveau
    (registratief leeswerk, geen prestatiekritiek pad): dat geeft van nature de
    **kortste afstand** (`niveau`, 1=direct) en is **cyclus-veilig** via een visited-set
    (B3 staat cycli toe; de traversal mag nooit hangen). Per geraakt component het pad
    (namen bron→component), het relatietype van de eerste stap, en — uitsluitend bij
    applicatie-subtypen — lifecycle + open-blokkade-telling. Schrijft niets."""
    from services import component_contract_service as cc_svc

    tid = _tenant_uuid(tenant_id)
    bron = await haal_op(session, tenant_id, component_id)  # 404 kruis-tenant (OP-6)
    type_labels = await catalog.labels(session, ComponentConfigDimensie.componenttype)
    rel_labels = await catalog.labels(session, ComponentConfigDimensie.archimate_relatie)

    geraakt: dict = {}
    visited = {component_id}  # incl. de bron → cyclus-veilig + nooit dubbel
    # frontier-item: (node_id, pad_namen, eerste_stap_relatietype_label | None)
    frontier = [(component_id, [bron.naam], None)]
    niveau = 0
    while frontier:
        niveau += 1
        ouder = {n: (pad, eerste) for (n, pad, eerste) in frontier}
        front = list(ouder.keys())
        # ADR-023: volg de afhankelijkheid type-bewust. `assignment` (host→gehoste): wie hangt
        # aan een host = doel waar bron in de frontier zit. `aggregation` (deel→geheel): de delen
        # van een geheel = bron waar doel in de frontier zit. `flow` (koppeling, LI019): geldt
        # bidirectioneel — de afhankelijke is de andere endpoint, dus de kant die NIET in de
        # frontier zit. `dep` = de afhankelijke (volgende laag); `via` = de frontier-knoop
        # (de ouder in het pad). De relatietype-takken vóór de flow-takken: zo bepaalt bij flow
        # uitsluitend de frontier-positie de richting.
        _dep = case(
            (Relatie.relatietype == "assignment", Relatie.doel_id),
            (Relatie.relatietype == "aggregation", Relatie.bron_id),
            (Relatie.bron_id.in_(front), Relatie.doel_id),  # flow met bron in frontier → dep = doel
            else_=Relatie.bron_id,                          # flow met doel in frontier → dep = bron
        )
        _via = case(
            (Relatie.relatietype == "assignment", Relatie.bron_id),
            (Relatie.relatietype == "aggregation", Relatie.doel_id),
            (Relatie.bron_id.in_(front), Relatie.bron_id),  # flow: de frontier-knoop is de bron
            else_=Relatie.doel_id,                          # flow: de frontier-knoop is de doel
        )
        rijen = (
            await session.execute(
                select(
                    _dep.label("dep_id"),
                    _via.label("op_id"),
                    Relatie.relatietype.label("relatietype"),
                    Component.naam.label("naam"),
                    Component.componenttype.label("componenttype"),
                )
                .join(Component, Component.id == _dep)
                .where(
                    Relatie.tenant_id == tid,
                    or_(
                        and_(Relatie.relatietype == "assignment", Relatie.bron_id.in_(front)),
                        and_(Relatie.relatietype == "aggregation", Relatie.doel_id.in_(front)),
                        and_(Relatie.relatietype == "flow",
                             or_(Relatie.bron_id.in_(front), Relatie.doel_id.in_(front))),
                    ),
                )
                .order_by(Component.naam, Relatie.id)
            )
        ).all()
        volgende = []
        for r in rijen:
            if r.dep_id in visited:
                continue  # reeds (op ≤ dit niveau) gevonden of cyclus → overslaan
            visited.add(r.dep_id)
            ouder_pad, ouder_eerste = ouder[r.op_id]
            eerste_rel = ouder_eerste if ouder_eerste is not None else catalog.resolveer_een(r.relatietype, rel_labels)
            pad = ouder_pad + [r.naam]
            geraakt[r.dep_id] = {
                "component_id": r.dep_id, "naam": r.naam, "componenttype": r.componenttype,
                "componenttype_label": catalog.resolveer_een(r.componenttype, type_labels),
                "niveau": niveau, "pad": pad, "relatietype_label": eerste_rel,
                "lifecycle_status": None, "open_blokkades": None,
            }
            volgende.append((r.dep_id, pad, eerste_rel))
        frontier = volgende

    # Applicatie-verrijking (alleen subtypen): lifecycle + open-blokkade-telling.
    ids = list(geraakt.keys())
    if ids:
        for aid, lc in (
            await session.execute(
                select(ComponentProfiel.id, ComponentProfiel.lifecycle_status).where(
                    ComponentProfiel.tenant_id == tid, ComponentProfiel.id.in_(ids)
                )
            )
        ).all():
            geraakt[aid]["lifecycle_status"] = lc
            geraakt[aid]["open_blokkades"] = 0
        for aid, aantal in (
            await session.execute(
                select(Blokkade.component_id, func.count())
                .where(
                    Blokkade.tenant_id == tid, Blokkade.component_id.in_(ids),
                    Blokkade.status != BlokkadeStatus.opgelost,
                )
                .group_by(Blokkade.component_id)
            )
        ).all():
            geraakt[aid]["open_blokkades"] = aantal

    lijst_geraakt = sorted(geraakt.values(), key=lambda g: (g["niveau"], g["naam"]))
    aantal_app = sum(1 for g in lijst_geraakt if g["lifecycle_status"] is not None)
    aantal_geblokkeerd = sum(1 for g in lijst_geraakt if g["lifecycle_status"] == LifecycleStatus.geblokkeerd)
    return {
        "component": {
            "id": bron.id, "naam": bron.naam,
            "componenttype_label": catalog.resolveer_een(bron.componenttype, type_labels),
        },
        "contracten": await cc_svc.contracten_van_component(session, tenant_id, component_id),
        "geraakt": lijst_geraakt,
        "samenvatting": {
            "aantal_geraakt": len(lijst_geraakt),
            "aantal_applicaties": aantal_app,
            "aantal_geblokkeerd": aantal_geblokkeerd,
        },
    }
