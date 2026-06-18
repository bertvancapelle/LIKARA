"""Service-laag voor de entiteit Applicatie (P5, ADR-009).

Bevat alle business-logica; de route-handlers blijven dun. Elke query draait
binnen de tenant-sessie (RLS-context via `get_tenant_session`) ÉN filtert
expliciet op `tenant_id` — dubbele tenant-bescherming (complidata-security).

OP-6 (tenant-scoped, besluit Bert): record-resolutie strikt binnen de tenant.
Een id buiten de tenant is niet vindbaar (RLS + expliciete filter) ⇒ `NietGevonden`
(HTTP 404). Geen onderscheid 'bestaat niet' vs 'andere tenant' — geen lek.

Lifecycle (ADR-009): nieuw ⇒ `concept`. In P5 is uitsluitend de overgang
`concept → in_inventarisatie` afdwingbaar. De afgeleide statussen
`geblokkeerd`/`migratieklaar` vallen BUITEN scope — die worden herberekend
zodra Checklistscore-/Blokkade-CRUD bestaat.
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, contains_eager

from models.models import (
    Applicatie,
    Component,
    ComponentProfiel,
    Element,
    ElementType,
    HostingModel,
    LifecycleStatus,
    Migratiepad,
    NiveauEnum,
    Partij,
)

# Velden die op de component leven (ADR-021 herfundering) — voor mutatie-routering.
_COMPONENTVELDEN = frozenset(
    {"naam", "beschrijving", "hostingmodel", "eigenaar_organisatie_id", "eigenaar_naam", "leverancier"}
)
from schemas.applicatie import ApplicatieCreate, ApplicatieUpdate
from services.errors import NietGevonden, OngeldigeStatusovergang
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "applicatie"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100

# Default-sortering = exact het pre-ADR-017-gedrag (created_at oplopend).
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"

# Allowlist-kolommen (ADR-017 B2) — single source naast de schema-enum
# `ApplicatieSorteerveld`; `test_applicatie_sort` borgt dat beide gelijk zijn.
# naam/eigenaar/hosting verhuizen naar component (ADR-021); de keyset joint component.
_SORTEERBARE_KOLOMMEN = {
    "created_at": Applicatie.created_at,
    "naam": Component.naam,
    # UX-B6-b — `eigenaar_organisatie` sorteert op de naam van de gekoppelde organisatie-partij
    # (per-call alias in `lijst`); de dict-waarde hier is een placeholder voor de allowlist-test.
    "eigenaar_organisatie": Component.eigenaar_organisatie_id,
    "hostingmodel": Component.hostingmodel,
    "complexiteit": Applicatie.complexiteit,
    "prioriteit": Applicatie.prioriteit,
    # ADR-022 Fase A: lifecycle_status leeft op het generieke profiel (shared-PK).
    "lifecycle_status": ComponentProfiel.lifecycle_status,
}

# Parsers die een cursor-waarde (tekst) terug naar het kolomtype brengen voor de
# keyset-seek (`tuple_`-vergelijking bindt het juiste type).
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "naam": str,
    "eigenaar_organisatie": str,
    "hostingmodel": HostingModel,
    "complexiteit": NiveauEnum,
    "prioriteit": NiveauEnum,
    "lifecycle_status": LifecycleStatus,
}

_LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    """Escape LIKE/ILIKE-metatekens zodat gebruikersinvoer letterlijk matcht (CD017).

    Volgorde is essentieel: eerst het escape-teken zelf (`\\`), daarna de wildcards
    (`%`, `_`). Resultaat wordt met `ilike(..., escape='\\')` gebruikt, zodat een `%`
    of `_` in de zoekterm geen wildcard wordt (geen wildcard-injectie).
    """
    return term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")


def _ilike_contains(kolom, term: str):
    """`kolom ILIKE '%<escaped>%' ESCAPE '\\'` — veilige contains-match."""
    return kolom.ilike(f"%{_escape_like(term)}%", escape=_LIKE_ESCAPE)


def _tenant_uuid(tenant_id) -> uuid.UUID:
    """Normaliseer de tenant-id (uit de sessie een str) naar UUID."""
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def enum_opties() -> dict[str, list[str]]:
    """Read-only metadata: de keuzewaarden per Applicatie-enumveld (single source).

    Pure (DB-vrij). Voert de frontend-dropdowns aan; de Nederlandse labels zijn
    een frontend-presentatiezaak. `lifecycle_status` valt hier bewust buiten —
    die is server-beheerd, geen invoerveld.
    """
    return {
        "hostingmodel": [e.value for e in HostingModel],
        "migratiepad": [e.value for e in Migratiepad],
        "complexiteit": [e.value for e in NiveauEnum],
        "prioriteit": [e.value for e in NiveauEnum],
    }


# ADR-022 Fase E: de pure start-regel is verhuisd naar de generieke lifecycle-laag
# (type-generieke "start beoordeling"). Hier ge-re-exporteerd voor bestaande callers/tests.
from services.lifecycle_service import volgende_status_na_start  # noqa: E402,F401


async def _org_naam(session: AsyncSession, tid: uuid.UUID, organisatie_id) -> str | None:
    """Naam van de gekoppelde eigenaar-organisatie-partij (None als niet gezet)."""
    if organisatie_id is None:
        return None
    return (
        await session.execute(
            select(Partij.naam).where(Partij.id == organisatie_id, Partij.tenant_id == tid)
        )
    ).scalar_one_or_none()


async def _met_org_naam(session: AsyncSession, tid: uuid.UUID, obj: Applicatie) -> Applicatie:
    """UX-B6-b — hang de geresolveerde eigenaar-organisatie-naam als transient attribuut aan de
    ORM-applicatie (naam-in-read; `ApplicatieRead` leest het via `from_attributes`)."""
    obj.eigenaar_organisatie_naam = await _org_naam(session, tid, obj.eigenaar_organisatie_id)
    return obj


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    sort: str = _STANDAARD_SORT,
    order: str = _STANDAARD_ORDER,
    status: list[str] | None = None,
    hostingmodel: str | None = None,
    eigenaar_organisatie_id: uuid.UUID | None = None,
    zoek: str | None = None,
) -> tuple[list[Applicatie], str | None]:
    """Server-side sorteerbare, **filterbare** v2n-keyset-lijst binnen de tenant
    (ADR-017 + CD017; NULLS-LAST voor de nullable eigenaar-organisatie-sleutel).

    De cursor is zelfbeschrijvend: een `after` die niet bij `sort`/`order` past ⇒
    `ValueError` (route ⇒ 400). Filters (AND, alle optioneel): `status` (reële
    lifecycle-statussen → `IN`), `hostingmodel` (enum-gelijkheid),
    `eigenaar_organisatie_id` (gelijkheid op de FK), `zoek` (ge-escapete `ILIKE` op `naam`).
    UX-B6-b: `eigenaar_organisatie` sorteert op de naam van de gejoinde organisatie-partij;
    de read levert die naam mee (transient attribuut)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    # UX-B6-b — LEFT JOIN de eigenaar-organisatie-partij voor naam-in-read + sortering op naam.
    eig = aliased(Partij)
    kolom = eig.naam if sort == "eigenaar_organisatie" else _SORTEERBARE_KOLOMMEN[sort]

    stmt = (
        select(Applicatie, eig.naam.label("eigenaar_organisatie_naam"))
        .join(Component, Applicatie.id == Component.id)
        .join(ComponentProfiel, Applicatie.id == ComponentProfiel.id)
        .outerjoin(eig, and_(eig.id == Component.eigenaar_organisatie_id, eig.tenant_id == tid))
        .options(contains_eager(Applicatie.component), contains_eager(Applicatie.profiel))
        .where(Applicatie.tenant_id == tid)
    )

    # Filters (AND). Lege/afwezige filters voegen GEEN clause toe → default-pad identiek aan CD015.
    if status:
        stmt = stmt.where(
            ComponentProfiel.lifecycle_status.in_([LifecycleStatus(s) for s in status])
        )
    if hostingmodel:
        stmt = stmt.where(Component.hostingmodel == HostingModel(hostingmodel))
    if eigenaar_organisatie_id:
        stmt = stmt.where(Component.eigenaar_organisatie_id == eigenaar_organisatie_id)
    if zoek:
        stmt = stmt.where(_ilike_contains(Component.naam, zoek))

    if after:
        c_sort, c_order, c_isnull, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_isnull else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(kolom, Applicatie.id, order=order, is_null=c_isnull, waarde=c_waarde, cursor_id=c_id)
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Applicatie.id, order)).limit(limit + 1)

    rijen = list((await session.execute(stmt)).all())  # (Applicatie, eigenaar_organisatie_naam|None)
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    out = []
    for app, eig_naam in items:
        app.eigenaar_organisatie_naam = eig_naam
        out.append(app)
    if heeft_meer:
        laatste_app, laatste_eig = items[-1]
        waarde = laatste_eig if sort == "eigenaar_organisatie" else getattr(laatste_app, sort)
        volgende = encode_sort_cursor_nullable(sort=sort, order=order, waarde=waarde, id=laatste_app.id)
    else:
        volgende = None
    return out, volgende


async def haal_op(session: AsyncSession, tenant_id, applicatie_id) -> Applicatie:
    """Haal één applicatie binnen de tenant; niet gevonden ⇒ `NietGevonden` (OP-6)."""
    tid = _tenant_uuid(tenant_id)
    stmt = select(Applicatie).where(
        Applicatie.id == applicatie_id,
        Applicatie.tenant_id == tid,
    )
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, applicatie_id)
    return await _met_org_naam(session, tid, obj)


async def maak_applicatie_subtype(
    session: AsyncSession,
    tid: uuid.UUID,
    *,
    naam: str,
    beschrijving: str | None,
    hostingmodel: HostingModel,
    eigenaar_organisatie_id: uuid.UUID | None,
    eigenaar_naam: str | None,
    leverancier: str | None,
    migratiepad: Migratiepad,
    complexiteit: NiveauEnum,
    prioriteit: NiveauEnum,
) -> Applicatie:
    """Service-kern: maak component-supertype + applicatie-subtype atomair (shared-PK).

    Eén implementatie achter twee routes (ADR-021 W1/CD054b): het applicatie-pad
    (`ApplicatieCreate`, alle velden verplicht) én de convergente aanmaak via het
    component-pad (`componenttype='applicatie'`, met defaults). Start altijd in
    lifecycle `concept`. De aanroeper heeft de waarden al gevalideerd/gedefault."""
    # ADR-023 Besluit 1: de component is een subtype van `element` (shared-PK). Eerst de
    # element-identiteit, daarna de component met dezelfde id.
    elem = Element(tenant_id=tid, element_type=ElementType.component)
    session.add(elem)
    await session.flush()  # elem.id beschikbaar
    comp = Component(
        id=elem.id,
        tenant_id=tid,
        naam=naam,
        componenttype="applicatie",
        hostingmodel=hostingmodel,
        eigenaar_organisatie_id=eigenaar_organisatie_id,
        eigenaar_naam=eigenaar_naam,
        leverancier=leverancier,
        beschrijving=beschrijving,
    )
    session.add(comp)
    await session.flush()  # comp.id beschikbaar voor de shared-PK
    obj = Applicatie(
        id=comp.id,
        tenant_id=tid,
        migratiepad=migratiepad,
        complexiteit=complexiteit,
        prioriteit=prioriteit,
    )
    session.add(obj)
    # ADR-022 Fase A: elke applicatie krijgt atomair haar generieke profiel — de
    # drager van de engine-state (lifecycle_status, start `concept`).
    session.add(
        ComponentProfiel(id=comp.id, tenant_id=tid, lifecycle_status=LifecycleStatus.concept)
    )
    await session.commit()
    await session.refresh(obj)
    return obj


async def maak_aan(session: AsyncSession, tenant_id, data: ApplicatieCreate) -> Applicatie:
    """Maak een applicatie aan (ADR-021): component-supertype + subtype, atomair.

    De component (componenttype `applicatie`) draagt naam/hosting/eigenaar/leverancier/
    beschrijving; het subtype draagt lifecycle/migratiepad/complexiteit/prioriteit en
    deelt zijn PK met de component (shared-PK). Start altijd in lifecycle `concept`."""
    tid = _tenant_uuid(tenant_id)
    d = data.model_dump()
    # UX-B6-b — valideer dat een opgegeven eigenaar-organisatie een organisatie-partij is (optioneel).
    if d["eigenaar_organisatie_id"] is not None:
        from services import partij_service
        await partij_service.valideer_organisatie(session, tid, d["eigenaar_organisatie_id"])
    obj = await maak_applicatie_subtype(
        session,
        tid,
        naam=d["naam"],
        beschrijving=d["beschrijving"],
        hostingmodel=d["hostingmodel"],
        eigenaar_organisatie_id=d["eigenaar_organisatie_id"],
        eigenaar_naam=d["eigenaar_naam"],
        leverancier=d["leverancier"],
        migratiepad=d["migratiepad"],
        complexiteit=d["complexiteit"],
        prioriteit=d["prioriteit"],
    )
    # Resolveer de naam uit de zojuist-gezette id (niet via de proxy — die vergt een geladen component).
    obj.eigenaar_organisatie_naam = await _org_naam(session, tid, d["eigenaar_organisatie_id"])
    return obj


async def werk_bij(
    session: AsyncSession, tenant_id, applicatie_id, data: ApplicatieUpdate
) -> Applicatie:
    """Partiële update binnen de tenant. `lifecycle_status` blijft onaangeraakt.

    Component-velden (naam/hosting/eigenaar/leverancier/beschrijving) worden op de
    component gezet, de overige op het subtype (ADR-021 herfundering)."""
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, applicatie_id)
    velden = data.model_dump(exclude_unset=True)
    # UX-B6-b — eigenaar-organisatie wijzigen: valideer aard=organisatie als een id wordt gezet.
    if velden.get("eigenaar_organisatie_id") is not None:
        from services import partij_service
        await partij_service.valideer_organisatie(session, tid, velden["eigenaar_organisatie_id"])
    for veld, waarde in velden.items():
        doel = obj.component if veld in _COMPONENTVELDEN else obj
        setattr(doel, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return await _met_org_naam(session, tid, obj)


async def verwijder(session: AsyncSession, tenant_id, applicatie_id) -> None:
    """Verwijder een applicatie binnen de tenant (atomair, via de component).

    De component verwijderen cascadeert naar het subtype én alle engine-kinderen
    (datatype, gebruikersgroep, koppeling, checklistscore, blokkade) — alles onder
    dezelfde tenant-scope (RLS)."""
    obj = await haal_op(session, tenant_id, applicatie_id)
    # ADR-023: het element is de supertype-eigenaar van de delete-cascade
    # (element → component → subtype/engine-kinderen). Het element verwijderen ruimt
    # alles op; de component-rij alleen zou een wees-element achterlaten.
    tid = _tenant_uuid(tenant_id)
    await session.execute(
        delete(Element).where(Element.tenant_id == tid, Element.id == obj.id)
    )
    await session.commit()


async def start_inventarisatie(session: AsyncSession, tenant_id, applicatie_id) -> Applicatie:
    """Lifecycle-overgang `concept → in_inventarisatie` (handmatige start).

    Ongeldige uitgangsstatus ⇒ `OngeldigeStatusovergang` (HTTP 409).

    Ná de transitie volgt een herberekening (ADR-013), zodat een applicatie die
    vóór de start al volledig gescoord is direct op de juiste afgeleide status
    (`geblokkeerd`/`migratieklaar`) landt i.p.v. pas bij de eerstvolgende mutatie.
    De herberekening zet de status nooit terug naar `concept`.
    """
    from services import lifecycle_service

    obj = await haal_op(session, tenant_id, applicatie_id)
    # ADR-022 Fase E: de start is type-generiek geworden — applicatie loopt via dezelfde
    # kern (`start_beoordeling` zet `concept → in_inventarisatie` op het profiel + herleidt).
    await lifecycle_service.start_beoordeling(session, tenant_id, applicatie_id)
    await session.commit()
    await session.refresh(obj)
    return await _met_org_naam(session, _tenant_uuid(tenant_id), obj)
