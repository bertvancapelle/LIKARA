"""Service-laag voor de entiteit Applicatie — dunne **facade over `component`** (LI059 Slice 3).

Sinds LI059 Slice 3 bestaat er GEEN `applicatie`-subtabel meer: een component met
`componenttype='applicatie'` ÍS de applicatie (domeinmodel §9-7 — een "kaal" subtype
zonder type-eigen velden vervalt). Deze module houdt de bestaande `/applicaties`-API
**byte-identiek** in stand door alles op het generieke `component` (+ `component_profiel`
voor `lifecycle_status`) te laten leunen. Slice 4 vervangt de frontend en ruimt deze
facade daarna op.

Elke query draait binnen de tenant-sessie (RLS-context via `get_tenant_session`) ÉN
filtert expliciet op `tenant_id` — dubbele tenant-bescherming (likara-security).

OP-6 (tenant-scoped): een id buiten de tenant — of een component dat geen `applicatie`
is — is niet vindbaar ⇒ `NietGevonden` (HTTP 404). Geen lek.

De service levert **Component**-objecten terug met drie transient attributen
(`lifecycle_status`, `eigenaar_organisatie_naam`, `checklist_dragend`) die `ApplicatieRead`
via `from_attributes` uitleest — exact de velden die de oude subtabel-proxies leverden.
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import (
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
from schemas.applicatie import ApplicatieCreate, ApplicatieUpdate
from services.errors import NietGevonden
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "applicatie"
_APPLICATIE_TYPE = "applicatie"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100

# Default-sortering = exact het pre-ADR-017-gedrag (created_at oplopend).
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"

# Sentinel voor "nog niet meegegeven — moet ik zelf ophalen" (onderscheid van None-waarde).
_ONBEKEND = object()

# Allowlist-kolommen (ADR-017 B2) — single source naast de schema-enum
# `ApplicatieSorteerveld`; `test_applicatie_sort` borgt dat beide gelijk zijn.
# LI059 Slice 3: alle velden leven op `component` (was subtabel); lifecycle op het profiel.
_SORTEERBARE_KOLOMMEN = {
    "created_at": Component.created_at,
    "naam": Component.naam,
    # UX-B6-b — `eigenaar_organisatie` sorteert op de naam van de gekoppelde organisatie-partij
    # (per-call alias in `lijst`); de dict-waarde hier is een placeholder voor de allowlist-test.
    "eigenaar_organisatie": Component.eigenaar_organisatie_id,
    "hostingmodel": Component.hostingmodel,
    "complexiteit": Component.complexiteit,
    "prioriteit": Component.prioriteit,
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


async def _verrijk(
    session: AsyncSession,
    tid: uuid.UUID,
    comp: Component,
    *,
    lifecycle=_ONBEKEND,
    eig_naam=_ONBEKEND,
    met_dragend: bool = True,
) -> Component:
    """Hang de transient read-attributen aan een `component`-object zodat `ApplicatieRead`
    (via `from_attributes`) exact de oude subtabel-proxy-velden leest:

    - `lifecycle_status` uit het generieke profiel (shared-PK) — verplicht in `ApplicatieRead`;
    - `eigenaar_organisatie_naam` (UX-B6-b) — geresolveerde organisatie-partij-naam;
    - `checklist_dragend` (ADR-027) — alleen waar de oude service het zette (detail/mutatie),
      niet in `lijst`/`maak_aan` (dáár bleef het de `False`-default — byte-compat).

    `lifecycle`/`eig_naam` mogen vooraf-berekend meegegeven worden (bv. uit de lijst-join)
    om extra queries te vermijden.
    """
    if lifecycle is _ONBEKEND:
        lifecycle = (
            await session.execute(
                select(ComponentProfiel.lifecycle_status).where(
                    ComponentProfiel.id == comp.id, ComponentProfiel.tenant_id == tid
                )
            )
        ).scalar_one_or_none()
    comp.lifecycle_status = lifecycle
    comp.eigenaar_organisatie_naam = (
        await _org_naam(session, tid, comp.eigenaar_organisatie_id)
        if eig_naam is _ONBEKEND
        else eig_naam
    )
    if met_dragend:
        from services import componentconfig_catalog as _cfg

        comp.checklist_dragend = await _cfg.is_checklist_dragend(session, _APPLICATIE_TYPE)
    return comp


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
) -> tuple[list[Component], str | None]:
    """Server-side sorteerbare, **filterbare** v2n-keyset-lijst van applicatie-componenten
    binnen de tenant (ADR-017 + CD017; NULLS-LAST voor de nullable eigenaar-organisatie-sleutel).

    De cursor is zelfbeschrijvend: een `after` die niet bij `sort`/`order` past ⇒
    `ValueError` (route ⇒ 400). Filters (AND, alle optioneel): `status` (reële
    lifecycle-statussen → `IN`), `hostingmodel` (enum-gelijkheid),
    `eigenaar_organisatie_id` (gelijkheid op de FK), `zoek` (ge-escapete `ILIKE` op `naam`).
    UX-B6-b: `eigenaar_organisatie` sorteert op de naam van de gejoinde organisatie-partij."""
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
        select(
            Component,
            ComponentProfiel.lifecycle_status.label("lifecycle_status"),
            eig.naam.label("eigenaar_organisatie_naam"),
        )
        # Applicatie = component met type 'applicatie' + verplicht profiel (INNER join).
        .join(ComponentProfiel, and_(ComponentProfiel.id == Component.id, ComponentProfiel.tenant_id == tid))
        .outerjoin(eig, and_(eig.id == Component.eigenaar_organisatie_id, eig.tenant_id == tid))
        .where(Component.tenant_id == tid, Component.componenttype == _APPLICATIE_TYPE)
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
            keyset_seek_nulls_last(kolom, Component.id, order=order, is_null=c_isnull, waarde=c_waarde, cursor_id=c_id)
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Component.id, order)).limit(limit + 1)

    rijen = list((await session.execute(stmt)).all())  # (Component, lifecycle, eigenaar_organisatie_naam|None)
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    out = []
    for comp, lc, eig_naam in items:
        # lijst zette (oud) `checklist_dragend` NIET → default False in ApplicatieRead (byte-compat).
        out.append(await _verrijk(session, tid, comp, lifecycle=lc, eig_naam=eig_naam, met_dragend=False))
    if heeft_meer:
        laatste_comp, laatste_lc, laatste_eig = items[-1]
        if sort == "eigenaar_organisatie":
            waarde = laatste_eig
        elif sort == "lifecycle_status":
            waarde = laatste_lc
        else:
            waarde = getattr(laatste_comp, sort)
        volgende = encode_sort_cursor_nullable(sort=sort, order=order, waarde=waarde, id=laatste_comp.id)
    else:
        volgende = None
    return out, volgende


async def haal_op(session: AsyncSession, tenant_id, applicatie_id) -> Component:
    """Haal één applicatie (= component met type 'applicatie') binnen de tenant;
    onbekend / ander-tenant / niet-applicatie ⇒ `NietGevonden` (OP-6, geen lek)."""
    tid = _tenant_uuid(tenant_id)
    stmt = select(Component).where(
        Component.id == applicatie_id,
        Component.tenant_id == tid,
        Component.componenttype == _APPLICATIE_TYPE,
    )
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, applicatie_id)
    return await _verrijk(session, tid, obj)


async def maak_applicatie_component(
    session: AsyncSession,
    tid: uuid.UUID,
    *,
    naam: str,
    beschrijving: str | None,
    hostingmodel: HostingModel,
    eigenaar_organisatie_id: uuid.UUID | None,
    migratiepad: Migratiepad,
    complexiteit: NiveauEnum,
    prioriteit: NiveauEnum,
) -> Component:
    """Service-kern: maak element + applicatie-component + generiek profiel atomair.

    Eén implementatie achter twee routes (ADR-021 W1/CD054b): het applicatie-pad
    (`ApplicatieCreate`, alle velden verplicht) én de convergente aanmaak via het
    component-pad (`componenttype='applicatie'`, met defaults). LI059 Slice 3: er is
    GEEN subtype-rij meer — de component ÍS de applicatie. Elke applicatie krijgt
    atomair haar generieke profiel (engine-state `lifecycle_status`, start `concept`)."""
    # ADR-023 Besluit 1: de component is een subtype van `element` (shared-PK). Eerst de
    # element-identiteit, daarna de component met dezelfde id.
    elem = Element(tenant_id=tid, element_type=ElementType.component)
    session.add(elem)
    await session.flush()  # elem.id beschikbaar
    comp = Component(
        id=elem.id,
        tenant_id=tid,
        naam=naam,
        componenttype=_APPLICATIE_TYPE,
        hostingmodel=hostingmodel,
        eigenaar_organisatie_id=eigenaar_organisatie_id,
        beschrijving=beschrijving,
        migratiepad=migratiepad,
        complexiteit=complexiteit,
        prioriteit=prioriteit,
    )
    session.add(comp)
    await session.flush()  # comp.id beschikbaar voor de shared-PK van het profiel
    # ADR-022 Fase A: elke applicatie krijgt atomair haar generieke profiel — de
    # drager van de engine-state (lifecycle_status, start `concept`).
    session.add(
        ComponentProfiel(id=comp.id, tenant_id=tid, lifecycle_status=LifecycleStatus.concept)
    )
    await session.commit()
    await session.refresh(comp)
    return comp


async def maak_aan(session: AsyncSession, tenant_id, data: ApplicatieCreate) -> Component:
    """Maak een applicatie aan (ADR-021): applicatie-component + profiel, atomair.

    Start altijd in lifecycle `concept`. Byte-compat: de POST-respons zette (oud)
    `checklist_dragend` NIET → default `False` in `ApplicatieRead`."""
    tid = _tenant_uuid(tenant_id)
    d = data.model_dump()
    # UX-B6-b — valideer dat een opgegeven eigenaar-organisatie een organisatie-partij is (optioneel).
    if d["eigenaar_organisatie_id"] is not None:
        from services import partij_service
        await partij_service.valideer_organisatie(session, tid, d["eigenaar_organisatie_id"])
    comp = await maak_applicatie_component(
        session,
        tid,
        naam=d["naam"],
        beschrijving=d["beschrijving"],
        hostingmodel=d["hostingmodel"],
        eigenaar_organisatie_id=d["eigenaar_organisatie_id"],
        migratiepad=d["migratiepad"],
        complexiteit=d["complexiteit"],
        prioriteit=d["prioriteit"],
    )
    # Verse applicatie ⇒ lifecycle `concept`; eigenaar-naam uit de zojuist-gezette id.
    comp.lifecycle_status = LifecycleStatus.concept
    comp.eigenaar_organisatie_naam = await _org_naam(session, tid, d["eigenaar_organisatie_id"])
    return comp


async def werk_bij(
    session: AsyncSession, tenant_id, applicatie_id, data: ApplicatieUpdate
) -> Component:
    """Partiële update binnen de tenant. `lifecycle_status` blijft onaangeraakt.

    Alle applicatie-velden leven op het component (LI059 Slice 3) — er is geen
    subtabel/dual-write meer; elk meegestuurd veld wordt direct op de component gezet."""
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, applicatie_id)
    velden = data.model_dump(exclude_unset=True)
    # UX-B6-b — eigenaar-organisatie wijzigen: valideer aard=organisatie als een id wordt gezet.
    if velden.get("eigenaar_organisatie_id") is not None:
        from services import partij_service
        await partij_service.valideer_organisatie(session, tid, velden["eigenaar_organisatie_id"])
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return await _verrijk(session, tid, obj)


async def verwijder(session: AsyncSession, tenant_id, applicatie_id) -> None:
    """Verwijder een applicatie binnen de tenant (atomair, via het element-supertype).

    Het element verwijderen cascadeert naar de component én alle engine-kinderen
    (profiel, checklistscore, blokkade) en relatie-endpoints — alles onder dezelfde
    tenant-scope (RLS). De losse component-rij verwijderen zou een wees-element achterlaten."""
    obj = await haal_op(session, tenant_id, applicatie_id)
    tid = _tenant_uuid(tenant_id)
    await session.execute(
        delete(Element).where(Element.tenant_id == tid, Element.id == obj.id)
    )
    await session.commit()


async def start_inventarisatie(session: AsyncSession, tenant_id, applicatie_id) -> Component:
    """Lifecycle-overgang `concept → in_inventarisatie` (handmatige start).

    Ongeldige uitgangsstatus ⇒ `OngeldigeStatusovergang` (HTTP 409).

    Ná de transitie volgt een herberekening (ADR-013), zodat een applicatie die
    vóór de start al volledig gescoord is direct op de juiste afgeleide status
    (`geblokkeerd`/`migratieklaar`) landt i.p.v. pas bij de eerstvolgende mutatie.
    De herberekening zet de status nooit terug naar `concept`.
    """
    from services import lifecycle_service

    obj = await haal_op(session, tenant_id, applicatie_id)
    # ADR-022 Fase E: de start is type-generiek — dezelfde kern (`start_beoordeling` zet
    # `concept → in_inventarisatie` op het profiel + herleidt).
    await lifecycle_service.start_beoordeling(session, tenant_id, applicatie_id)
    await session.commit()
    await session.refresh(obj)
    return await _verrijk(session, _tenant_uuid(tenant_id), obj)
