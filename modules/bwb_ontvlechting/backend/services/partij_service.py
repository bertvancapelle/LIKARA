"""Service-laag — partij-beheer (ADR-024 slice 2a; vervangt externe_partij_service).

Eén beheerpad voor alle partij-aarden (externe_partij / organisatie / organisatie_eenheid /
persoon). Een partij is een **element-backed** record: aanmaak schrijft een `element`-rij
(shared-PK) + een `partij`-rij in één tenant-transactie; verwijderen loopt via het
**element-supertype** (`DELETE FROM element`) → CASCADE neemt de partij-rij mee, géén wees-element
(les commit 109ced8). Tenant-scoped (RLS + expliciet `tenant_id`-filter). De `aard` wordt bij
aanmaken gezet en is daarna niet wijzigbaar (geen `aard` in Update). Puur registratief — geen
engine-koppeling. v2n-keyset-paginering (`plaats` nullable).
"""
import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Contract, Element, ElementType, Partij, PartijAard
from schemas.partij import PartijCreate, PartijUpdate
from services import partijsoort_catalog
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict

# ADR-024 slice 2a-bis — organisatie-achtige aarden waar een persoon/afdeling onder kan hangen.
_ORGANISATIE_ACHTIG = (PartijAard.organisatie, PartijAard.externe_partij)
_HEEFT_ORG_OUDER = (PartijAard.persoon, PartijAard.organisatie_eenheid)
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "partij"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"

_SORTEERBARE_KOLOMMEN = {
    "created_at": Partij.created_at,
    "naam": Partij.naam,
    "plaats": Partij.plaats,
    # ADR-024 — `aard` server-side sorteerbaar (leden-overzicht). Keyset op de enum-kolom
    # werkt (enum heeft ordening); de cursorwaarde is de enum-sleutel (str).
    "aard": Partij.aard,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "naam": str,
    "plaats": str,
    "aard": str,
}

_LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    return term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def _valideer_lidmaatschap(session, tid, aard, organisatie_id, afdeling_id) -> None:
    """ADR-024 slice 2a-bis — borgt het "hoort bij"-verband (aard-bewust; tevens het update-pad
    waar het schema de aard niet kent). Structuur (verplicht/verboden per aard) + cross-row
    laag-consistentie (organisatie-achtig; afdeling = organisatie_eenheid binnen die organisatie)."""
    heeft_org_ouder = aard in _HEEFT_ORG_OUDER
    if heeft_org_ouder and organisatie_id is None:
        raise OngeldigeRegistratie(
            "ORGANISATIE_VERPLICHT", "Een persoon of afdeling hoort verplicht bij een organisatie."
        )
    if not heeft_org_ouder and organisatie_id is not None:
        raise OngeldigeRegistratie(
            "ONGELDIG_LIDMAATSCHAP", "Een organisatie/externe partij hoort niet onder een andere partij."
        )
    if afdeling_id is not None and aard != PartijAard.persoon:
        raise OngeldigeRegistratie(
            "ONGELDIG_LIDMAATSCHAP", "Alleen een persoon kan bij een afdeling horen."
        )
    if organisatie_id is not None:
        org = (
            await session.execute(
                select(Partij).where(Partij.id == organisatie_id, Partij.tenant_id == tid)
            )
        ).scalar_one_or_none()
        if org is None or org.aard not in _ORGANISATIE_ACHTIG:
            raise OngeldigeRegistratie(
                "ONGELDIGE_ORGANISATIE",
                "De organisatie moet een bestaande organisatie of externe partij zijn.",
            )
    if afdeling_id is not None:
        afd = (
            await session.execute(
                select(Partij).where(Partij.id == afdeling_id, Partij.tenant_id == tid)
            )
        ).scalar_one_or_none()
        if afd is None or afd.aard != PartijAard.organisatie_eenheid:
            raise OngeldigeRegistratie("ONGELDIGE_AFDELING", "De afdeling moet een bestaande afdeling zijn.")
        if afd.organisatie_id != organisatie_id:
            raise OngeldigeRegistratie(
                "ONGELDIGE_AFDELING", "De afdeling hoort niet bij de gekozen organisatie."
            )


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    aard: PartijAard | None = None,
    organisatie_id=None,
    afdeling_id=None,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    sort: str = _STANDAARD_SORT,
    order: str = _STANDAARD_ORDER,
    zoek: str | None = None,
) -> tuple[list[Partij], str | None]:
    """v2n-keyset-lijst binnen de tenant. `aard=None` ⇒ alle aarden; anders gefilterd.
    `organisatie_id`/`afdeling_id` filteren op het "hoort bij"-verband (leden van een
    organisatie/afdeling). `zoek` = ge-escapete ILIKE op `naam`."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]

    stmt = select(Partij).where(Partij.tenant_id == tid)
    if aard is not None:
        stmt = stmt.where(Partij.aard == aard)
    if organisatie_id is not None:
        stmt = stmt.where(Partij.organisatie_id == organisatie_id)
    if afdeling_id is not None:
        stmt = stmt.where(Partij.afdeling_id == afdeling_id)
    if zoek:
        stmt = stmt.where(Partij.naam.ilike(f"%{_escape_like(zoek)}%", escape=_LIKE_ESCAPE))
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, Partij.id, order=order, is_null=c_is_null, waarde=c_waarde, cursor_id=c_id
            )
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Partij.id, order)).limit(limit + 1)

    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor_nullable(sort=sort, order=order, waarde=getattr(items[-1], sort), id=items[-1].id)
        if heeft_meer
        else None
    )
    return items, volgende


async def haal_op(session: AsyncSession, tenant_id, partij_id) -> Partij:
    """Eén partij binnen de tenant (aard-agnostisch); niet gevonden ⇒ `NietGevonden` (404)."""
    tid = _tenant_uuid(tenant_id)
    stmt = select(Partij).where(Partij.id == partij_id, Partij.tenant_id == tid)
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, partij_id)
    return obj


async def maak_aan(session: AsyncSession, tenant_id, data: PartijCreate) -> Partij:
    tid = _tenant_uuid(tenant_id)
    await partijsoort_catalog.valideer_soort(session, data.soort)
    await _valideer_lidmaatschap(session, tid, data.aard, data.organisatie_id, data.afdeling_id)
    # Element-identiteit eerst (shared-PK), dan de partij-subtype-rij. `aard` uit de invoer.
    elem = Element(tenant_id=tid, element_type=ElementType.partij)
    session.add(elem)
    await session.flush()
    obj = Partij(id=elem.id, tenant_id=tid, **data.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def werk_bij(session: AsyncSession, tenant_id, partij_id, data: PartijUpdate) -> Partij:
    """Wijzig contactvelden/soort. `aard` is niet wijzigbaar (ontbreekt in PartijUpdate)."""
    obj = await haal_op(session, tenant_id, partij_id)
    tid = _tenant_uuid(tenant_id)
    velden = data.model_dump(exclude_unset=True)
    if "soort" in velden:
        await partijsoort_catalog.valideer_soort(session, velden["soort"])
    # Lidmaatschap aard-bewust valideren (de aard zelf ligt vast); effectieve waarden ná de update.
    if "organisatie_id" in velden or "afdeling_id" in velden:
        nieuw_org = velden.get("organisatie_id", obj.organisatie_id)
        nieuw_afd = velden.get("afdeling_id", obj.afdeling_id)
        await _valideer_lidmaatschap(session, tid, obj.aard, nieuw_org, nieuw_afd)
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj


async def verwijder(session: AsyncSession, tenant_id, partij_id) -> None:
    """Verwijder binnen de tenant. Een partij met contracten (als leverancier/tegenpartij)
    wordt geweigerd (409 `IN_GEBRUIK`) — nette app-fout vóór de FK `RESTRICT`. Verwijderen loopt
    via het element-supertype (CASCADE naar de partij-rij) → geen wees-element."""
    obj = await haal_op(session, tenant_id, partij_id)
    tid = _tenant_uuid(tenant_id)
    aantal = (
        await session.execute(
            select(func.count())
            .select_from(Contract)
            .where(Contract.tenant_id == tid, Contract.leverancier_id == obj.id)
        )
    ).scalar_one()
    if aantal:
        raise RegistratieConflict(
            "IN_GEBRUIK", "Deze partij heeft nog contracten en kan niet worden verwijderd."
        )
    # Via het element-supertype (CASCADE wist de partij-subtype-rij) — geen wees-element.
    await session.execute(delete(Element).where(Element.id == obj.id, Element.tenant_id == tid))
    await session.commit()
