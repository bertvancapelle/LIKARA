"""Service-laag voor Component (ADR-021 Besluit 1/4/6/9 — Fase B).

Tenant-scoped (RLS + expliciet `tenant_id`-filter; OP-6 kruis-tenant → 404). Het type
`applicatie` is een beschermde systeem-sleutel: applicaties ontstaan/verdwijnen uitsluitend
via het applicatie-pad (CD051). `componenttype`/`relatietype` worden tegen de actieve
componentcatalogus gevalideerd.
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from models.models import (
    Applicatie,
    Blokkade,
    BlokkadeStatus,
    Checklistscore,
    Component,
    ComponentConfigDimensie,
    ComponentContract,
    ComponentProfiel,
    ComponentStructuur,
    Datatype,
    Gebruikersgroep,
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
    # ADR-022 Fase A: lifecycle_status leeft op het generieke profiel (shared-PK).
    "lifecycle_status": ComponentProfiel.lifecycle_status,
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
    datatypes = await _count(
        select(func.count()).select_from(Datatype).where(
            Datatype.tenant_id == tid, Datatype.applicatie_id == component_id
        )
    )
    gebruikersgroepen = await _count(
        select(func.count()).select_from(Gebruikersgroep).where(
            Gebruikersgroep.tenant_id == tid, Gebruikersgroep.applicatie_id == component_id
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
        # ADR-022 Fase C: capability-hint voor de UI (de PATCH herevalueert zelf).
        "type_wijzigbaar": not (await _toestand_tellingen(session, tid, obj.id))["gevuld"],
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


async def lees_detail(session: AsyncSession, tenant_id, component_id) -> dict:
    tid = _tenant_uuid(tenant_id)
    return await _lees(session, tid, await haal_op(session, tenant_id, component_id))


def _sorteer_waarde(comp: Component, app: Applicatie | None, lifecycle, sort: str):
    """Sleutelwaarde voor de cursor: subtype-kolommen van het (mogelijk afwezige)
    subtype, `lifecycle_status` van het profiel, overige van de component."""
    if sort == "lifecycle_status":
        return lifecycle
    if sort in ("complexiteit", "prioriteit"):
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
        # ADR-022 Fase A: lifecycle_status komt expliciet uit het profiel; de
        # Applicatie-eager-load van `profiel` wordt onderdrukt (`lazyload`) zodat de
        # query één join naar component_profiel houdt.
        select(Component, Applicatie, ComponentProfiel.lifecycle_status.label("lifecycle_status"))
        .outerjoin(Applicatie, and_(Applicatie.id == Component.id, Applicatie.tenant_id == tid))
        .outerjoin(ComponentProfiel, and_(ComponentProfiel.id == Component.id, ComponentProfiel.tenant_id == tid))
        .options(lazyload(Applicatie.profiel))
        .where(Component.tenant_id == tid)
    )
    if componenttype:
        stmt = stmt.where(Component.componenttype == componenttype)
    if status:
        stmt = stmt.where(ComponentProfiel.lifecycle_status.in_([LifecycleStatus(s) for s in status]))
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

    rijen = list((await session.execute(stmt)).all())  # rijen van (Component, Applicatie|None, lifecycle|None)
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
            "lifecycle_status": lc,
        }
        for (c, a, lc) in items
    ]
    if heeft_meer:
        laatste_comp, laatste_app, laatste_lc = items[-1]
        volgende = encode_sort_cursor_nullable(
            sort=sort, order=order,
            waarde=_sorteer_waarde(laatste_comp, laatste_app, laatste_lc, sort), id=laatste_comp.id,
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


async def _wissel_type(session: AsyncSession, tid: uuid.UUID, obj: Component, nieuw: str) -> None:
    """Toestand-gebaseerde type-wissel (ADR-022 Fase C). Backend = bron van waarheid:
    transactie-lokaal herwaarderen en de invariant afdwingen.

    - Gevuld → `SUBTYPE_HEEFT_DATA` (422), met tellingen in het bericht.
    - Leeg → schone lei: een leeg profiel + applicatie-subtype (+ lege, niet-beantwoorde
      score-rijen via CASCADE) worden verwijderd; géén overdracht van oude scores. Is het
      doeltype checklist-dragend (`applicatie`), dan ontstaat een vers profiel met defaults
      (lifecycle `concept`, conform de Fase B-vloer). Doeltype kaal ⇒ geen profiel.
    """
    await catalog.valideer_sleutel(session, ComponentConfigDimensie.componenttype, nieuw)
    t = await _toestand_tellingen(session, tid, obj.id, lock=True)
    if t["gevuld"]:
        raise OngeldigeRegistratie("SUBTYPE_HEEFT_DATA", _heeft_data_bericht(t))

    # Leeg: ruim een eventueel (leeg) profiel + applicatie-subtype op. Het verwijderen
    # van het profiel cascadeert eventuele niet-beantwoorde score-rijen/blokkades; het
    # verwijderen van het subtype cascadeert (afwezige) datatypes/gebruikersgroepen.
    if await _heeft_subtype(session, tid, obj.id):
        await session.execute(delete(ComponentProfiel).where(ComponentProfiel.id == obj.id))
        await session.execute(delete(Applicatie).where(Applicatie.id == obj.id))
        await session.flush()

    obj.componenttype = nieuw

    if nieuw == _APPLICATIE_TYPE:
        # Promotie naar het checklist-dragende type: vers subtype + profiel (defaults).
        session.add(Applicatie(id=obj.id, tenant_id=tid, **_SUBTYPE_DEFAULTS))
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


async def impact_analyse(session: AsyncSession, tenant_id, component_id) -> dict:
    """Read-only impactanalyse (ADR-021 Besluit 10 / Fase E).

    Volgt de structuurgraaf in de richting `gebruikt_door` (wie steunt — direct of
    transitief — op dít component), over álle relatietypen. Iteratieve BFS per niveau
    (registratief leeswerk, geen prestatiekritiek pad): dat geeft van nature de
    **kortste afstand** (`niveau`, 1=direct) en is **cyclus-veilig** via een visited-set
    (B3 staat cycli toe; de traversal mag nooit hangen). Per geraakt component het pad
    (namen bron→component), het relatietype van de eerste stap, en — uitsluitend bij
    applicatie-subtypen — lifecycle + open-blokkade-telling. Schrijft niets."""
    from services import component_contract_service as cc_svc

    tid = _tenant_uuid(tenant_id)
    bron = await haal_op(session, tenant_id, component_id)  # 404 kruis-tenant (OP-6)
    type_labels = await catalog.labels(session, ComponentConfigDimensie.componenttype)
    rel_labels = await catalog.labels(session, ComponentConfigDimensie.structuurrelatie_type)

    geraakt: dict = {}
    visited = {component_id}  # incl. de bron → cyclus-veilig + nooit dubbel
    # frontier-item: (node_id, pad_namen, eerste_stap_relatietype_label | None)
    frontier = [(component_id, [bron.naam], None)]
    niveau = 0
    while frontier:
        niveau += 1
        ouder = {n: (pad, eerste) for (n, pad, eerste) in frontier}
        rijen = (
            await session.execute(
                select(
                    ComponentStructuur.component_id.label("dep_id"),
                    ComponentStructuur.op_component_id.label("op_id"),
                    ComponentStructuur.relatietype.label("relatietype"),
                    Component.naam.label("naam"),
                    Component.componenttype.label("componenttype"),
                )
                .join(Component, Component.id == ComponentStructuur.component_id)
                .where(
                    ComponentStructuur.tenant_id == tid,
                    ComponentStructuur.op_component_id.in_(list(ouder.keys())),
                )
                .order_by(Component.naam, ComponentStructuur.id)
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
