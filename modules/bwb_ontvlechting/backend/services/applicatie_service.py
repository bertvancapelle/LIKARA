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

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from models.models import (
    Applicatie,
    Component,
    ComponentProfiel,
    HostingModel,
    LifecycleStatus,
    Migratiepad,
    NiveauEnum,
)

# Velden die op de component leven (ADR-021 herfundering) — voor mutatie-routering.
_COMPONENTVELDEN = frozenset(
    {"naam", "beschrijving", "hostingmodel", "eigenaar_organisatie", "eigenaar_naam", "leverancier"}
)
from schemas.applicatie import ApplicatieCreate, ApplicatieUpdate
from services.errors import NietGevonden, OngeldigeStatusovergang
from services.pagination import decode_sort_cursor, encode_sort_cursor

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
    "eigenaar_organisatie": Component.eigenaar_organisatie,
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


def volgende_status_na_start(huidige: LifecycleStatus) -> LifecycleStatus:
    """Pure overgangsregel voor 'start inventarisatie'.

    Alleen `concept → in_inventarisatie` is geldig; elke andere uitgangsstatus
    levert `OngeldigeStatusovergang`. Apart en puur gehouden, zodat de regel
    zonder DB testbaar is.
    """
    if huidige != LifecycleStatus.concept:
        raise OngeldigeStatusovergang(huidige, LifecycleStatus.in_inventarisatie)
    return LifecycleStatus.in_inventarisatie


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
    eigenaar: str | None = None,
    zoek: str | None = None,
) -> tuple[list[Applicatie], str | None]:
    """Server-side sorteerbare, **filterbare** keyset-lijst binnen de tenant
    (ADR-017 + CD017).

    Sorteert op `(kolom, id)` met dezelfde richting voor kolom én tiebreaker, zodat
    één `tuple_`-rijvergelijking de seek uitdrukt (`>` asc, `<` desc). De cursor is
    zelfbeschrijvend: een `after` die niet bij `sort`/`order` past ⇒ `ValueError`
    (route ⇒ 400). Default (`created_at`/`asc`, geen filters) = exact het CD015-gedrag.

    Filters (AND-gecombineerd, alle optioneel): `status` (lijst reële lifecycle-
    statussen → `IN`), `hostingmodel` (enum-gelijkheid), `eigenaar`/`zoek`
    (ge-escapete `ILIKE`-contains op `eigenaar_organisatie` resp. `naam`). De
    enum-/lengtevalidatie zit op de API-rand; de checks hier zijn een backstop.
    """
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]
    oplopend = order == "asc"

    stmt = (
        select(Applicatie)
        .join(Component, Applicatie.id == Component.id)
        .join(ComponentProfiel, Applicatie.id == ComponentProfiel.id)
        .options(contains_eager(Applicatie.component), contains_eager(Applicatie.profiel))
        .where(Applicatie.tenant_id == tid)
    )

    # Filters (AND). Lege/afwezige filters voegen GEEN clause toe → default-pad
    # identiek aan CD015. Lege statuslijst = geen filter (toon alles).
    if status:
        stmt = stmt.where(
            ComponentProfiel.lifecycle_status.in_([LifecycleStatus(s) for s in status])
        )
    if hostingmodel:
        stmt = stmt.where(Component.hostingmodel == HostingModel(hostingmodel))
    if eigenaar:
        stmt = stmt.where(_ilike_contains(Component.eigenaar_organisatie, eigenaar))
    if zoek:
        stmt = stmt.where(_ilike_contains(Component.naam, zoek))

    if after:
        c_sort, c_order, c_waarde_str, c_id = decode_sort_cursor(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = _WAARDE_PARSERS[sort](c_waarde_str)
        if oplopend:
            stmt = stmt.where(tuple_(kolom, Applicatie.id) > (c_waarde, c_id))
        else:
            stmt = stmt.where(tuple_(kolom, Applicatie.id) < (c_waarde, c_id))

    if oplopend:
        stmt = stmt.order_by(kolom.asc(), Applicatie.id.asc())
    else:
        stmt = stmt.order_by(kolom.desc(), Applicatie.id.desc())
    stmt = stmt.limit(limit + 1)

    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor(sort=sort, order=order, waarde=getattr(items[-1], sort), id=items[-1].id)
        if heeft_meer
        else None
    )
    return items, volgende


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
    return obj


async def maak_applicatie_subtype(
    session: AsyncSession,
    tid: uuid.UUID,
    *,
    naam: str,
    beschrijving: str | None,
    hostingmodel: HostingModel,
    eigenaar_organisatie: str,
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
    comp = Component(
        tenant_id=tid,
        naam=naam,
        componenttype="applicatie",
        hostingmodel=hostingmodel,
        eigenaar_organisatie=eigenaar_organisatie,
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
    return await maak_applicatie_subtype(
        session,
        tid,
        naam=d["naam"],
        beschrijving=d["beschrijving"],
        hostingmodel=d["hostingmodel"],
        eigenaar_organisatie=d["eigenaar_organisatie"],
        eigenaar_naam=d["eigenaar_naam"],
        leverancier=d["leverancier"],
        migratiepad=d["migratiepad"],
        complexiteit=d["complexiteit"],
        prioriteit=d["prioriteit"],
    )


async def werk_bij(
    session: AsyncSession, tenant_id, applicatie_id, data: ApplicatieUpdate
) -> Applicatie:
    """Partiële update binnen de tenant. `lifecycle_status` blijft onaangeraakt.

    Component-velden (naam/hosting/eigenaar/leverancier/beschrijving) worden op de
    component gezet, de overige op het subtype (ADR-021 herfundering)."""
    obj = await haal_op(session, tenant_id, applicatie_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        doel = obj.component if veld in _COMPONENTVELDEN else obj
        setattr(doel, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj


async def verwijder(session: AsyncSession, tenant_id, applicatie_id) -> None:
    """Verwijder een applicatie binnen de tenant (atomair, via de component).

    De component verwijderen cascadeert naar het subtype én alle engine-kinderen
    (datatype, gebruikersgroep, koppeling, checklistscore, blokkade) — alles onder
    dezelfde tenant-scope (RLS)."""
    obj = await haal_op(session, tenant_id, applicatie_id)
    await session.delete(obj.component)
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
    # ADR-022 Fase A: lifecycle leeft op het profiel (shared-PK); schrijven gaat
    # via obj.profiel (de read-only proxy obj.lifecycle_status blijft leesbaar).
    obj.profiel.lifecycle_status = volgende_status_na_start(obj.profiel.lifecycle_status)
    # Additief: herleid de canonieke status uit de feiten (transitie zelf blijft).
    await lifecycle_service.herbereken_lifecycle(session, tenant_id, applicatie_id)
    await session.commit()
    await session.refresh(obj)
    return obj
