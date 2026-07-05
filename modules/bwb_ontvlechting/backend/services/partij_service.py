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

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import (
    Component, Contract, Element, ElementType, Partij, PartijAard, PartijScope, Relatie,
)
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


async def valideer_organisatie(session: AsyncSession, tenant_id, partij_id) -> None:
    """UX-B6 — een organisatie-verwijzing (bv. gebruikersgroep-/eigenaar-organisatie) moet een
    bestaande partij met aard=organisatie zijn (anders 422 `ONGELDIGE_ORGANISATIE`). `None` =
    optioneel, handelt de caller zelf af. Spiegelt `contract_service._valideer_contractpartij`."""
    tid = _tenant_uuid(tenant_id)
    aard = (
        await session.execute(
            select(Partij.aard).where(Partij.id == partij_id, Partij.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if aard is None or aard != PartijAard.organisatie:
        raise OngeldigeRegistratie(
            "ONGELDIGE_ORGANISATIE", "De gekozen organisatie moet een bestaande organisatie zijn."
        )


async def valideer_verantwoordelijke(session: AsyncSession, tenant_id, partij_id) -> None:
    """ADR-037 — een antwoord-verantwoordelijke moet een bestaande partij binnen de tenant zijn met
    aard ∈ {organisatie_eenheid (afdeling), persoon} (anders 422 `ONGELDIGE_VERANTWOORDELIJKE`).
    `None` = optioneel (leeg mag), handelt de caller af. Spiegelt `valideer_organisatie` /
    `_valideer_lidmaatschap` — structurele aard-borging op de plek waar de aard kan leven."""
    tid = _tenant_uuid(tenant_id)
    aard = (
        await session.execute(
            select(Partij.aard).where(Partij.id == partij_id, Partij.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if aard is None or aard not in (PartijAard.organisatie_eenheid, PartijAard.persoon):
        raise OngeldigeRegistratie(
            "ONGELDIGE_VERANTWOORDELIJKE",
            "De verantwoordelijke moet een bestaande afdeling of persoon zijn.",
        )


async def _valideer_contactpersoon(session: AsyncSession, tid, partij_id, contactpersoon_id) -> None:
    """ADR-039 — het aanspreekpunt moet een bestaande persoon-partij binnen de tenant
    zijn die **bij deze partij hoort** (aard=persoon én persoon.organisatie_id == deze partij).
    Anders 422 `ONGELDIGE_CONTACTPERSOON`. `None` = leeg (registratiegat), handelt de caller af.
    Spiegel van `valideer_verantwoordelijke`, met de extra "hoort-bij-deze-partij"-eis."""
    persoon = (
        await session.execute(
            select(Partij).where(Partij.id == contactpersoon_id, Partij.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if (
        persoon is None
        or persoon.aard != PartijAard.persoon
        or persoon.organisatie_id != partij_id
    ):
        raise OngeldigeRegistratie(
            "ONGELDIGE_CONTACTPERSOON",
            "Het aanspreekpunt moet een persoon zijn die bij deze partij hoort.",
        )


async def resolve_verantwoordelijken(session: AsyncSession, tenant_id, ids) -> dict:
    """ADR-037 — resolveer verantwoordelijke-partij-ids → `{id: {"naam", "afdeling"}}` voor de
    leeslaag. `afdeling` = naam van de afdeling-partij (alleen bij aard=persoon; een afdeling-partij
    draagt zelf geen afdeling → None). Onbekende/`None` id's zitten niet in de dict. Read-only."""
    tid = _tenant_uuid(tenant_id)
    unieke = {i for i in ids if i is not None}
    if not unieke:
        return {}
    afd = aliased(Partij)
    org = aliased(Partij)
    rijen = (
        await session.execute(
            select(
                Partij.id, Partij.naam,
                afd.naam.label("afdeling"),
                org.naam.label("organisatie"),
            )
            .join(afd, and_(afd.id == Partij.afdeling_id, afd.tenant_id == tid), isouter=True)
            .join(org, and_(org.id == Partij.organisatie_id, org.tenant_id == tid), isouter=True)
            .where(Partij.id.in_(unieke), Partij.tenant_id == tid)
        )
    ).all()
    return {
        r.id: {"naam": r.naam, "afdeling": r.afdeling, "organisatie": r.organisatie}
        for r in rijen
    }


async def _verrijk_context(session: AsyncSession, tid: uuid.UUID, items: list) -> None:
    """ADR-037/039 — hang de afgeleide `organisatie_naam` (+ `afdeling_naam` bij een persoon) én
    `contactpersoon_naam` (het aanspreekpunt) op de partij-lijst-items, zodat de identiteit "afdeling
    — organisatie" / "persoon — afdeling — organisatie" en het aanspreekpunt toonbaar zijn. Transient
    attrs (niet gemapt) die `PartijRead` (from_attributes) uitleest; één batch-query op de namen."""
    ids = {p.organisatie_id for p in items if p.organisatie_id}
    ids |= {p.afdeling_id for p in items if p.afdeling_id}
    ids |= {p.contactpersoon_id for p in items if p.contactpersoon_id}
    namen: dict = {}
    if ids:
        namen = dict(
            (
                await session.execute(
                    select(Partij.id, Partij.naam).where(Partij.id.in_(ids), Partij.tenant_id == tid)
                )
            ).all()
        )
    for p in items:
        p.organisatie_naam = namen.get(p.organisatie_id)
        p.afdeling_naam = namen.get(p.afdeling_id)
        p.contactpersoon_naam = namen.get(p.contactpersoon_id)


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    aard: PartijAard | None = None,
    aard_in: list[PartijAard] | None = None,
    scope: PartijScope | None = None,
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
    if aard_in:
        stmt = stmt.where(Partij.aard.in_(aard_in))
    # ADR-038 — intern/extern-filter (bv. de gebruiker-organisatie-picker = alleen interne
    # organisaties). Guarded: alleen toevoegen als er een scope is (default-pad byte-identiek).
    if scope is not None:
        stmt = stmt.where(Partij.scope == scope)
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
    await _verrijk_context(session, tid, items)  # ADR-037: afgeleide organisatie-/afdeling-namen
    return items, volgende


async def haal_op(session: AsyncSession, tenant_id, partij_id) -> Partij:
    """Eén partij binnen de tenant (aard-agnostisch); niet gevonden ⇒ `NietGevonden` (404)."""
    tid = _tenant_uuid(tenant_id)
    stmt = select(Partij).where(Partij.id == partij_id, Partij.tenant_id == tid)
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, partij_id)
    return obj


async def componenten_via_contracten(session: AsyncSession, tenant_id, partij_id) -> list[dict]:
    """LI019 — componenten die via een contract aan deze leverancier (partij) hangen.

    Keten: `contract.leverancier_id == partij` → association-relatie (bron=component → doel=contract)
    → component. Read-only; één regel per (component, contract)-paar, alfabetisch. Onbekende partij
    binnen de tenant ⇒ 404 (geen lek van cross-tenant bestaan)."""
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, partij_id)
    rijen = (
        await session.execute(
            select(
                Component.id.label("component_id"),
                Component.naam.label("component_naam"),
                Contract.id.label("contract_id"),
                Contract.contractnaam.label("contract_naam"),
            )
            .join(
                Relatie,
                and_(Relatie.doel_id == Contract.id, Relatie.relatietype == "association", Relatie.tenant_id == tid),
            )
            .join(Component, Component.id == Relatie.bron_id)
            .where(Contract.tenant_id == tid, Contract.leverancier_id == partij_id)
            .order_by(Component.naam, Contract.contractnaam)
        )
    ).all()
    return [
        {
            "component_id": r.component_id,
            "component_naam": r.component_naam,
            "contract_id": r.contract_id,
            "contract_naam": r.contract_naam,
        }
        for r in rijen
    ]


def _effectieve_scope(aard: PartijAard, scope: PartijScope | None) -> PartijScope | None:
    """ADR-038 — de op te slaan intern/extern-waarde, aard-bewust. Organisatie: keuze, default
    `extern` bij leeg. Externe partij: altijd `extern` (vast). Afdeling/persoon: geen eigen waarde
    (None → leiden af van hun ouder-organisatie)."""
    if aard == PartijAard.organisatie:
        return scope or PartijScope.extern
    if aard == PartijAard.externe_partij:
        return PartijScope.extern
    return None


def _valideer_scope(aard: PartijAard, scope: PartijScope | None) -> None:
    """ADR-038 — borg de op te slaan intern/extern-waarde tegen de aard (spiegel van de CHECK-
    backstops): organisatie ⇒ intern|extern; externe_partij ⇒ vast extern (nooit intern);
    afdeling/persoon ⇒ geen eigen waarde. 422 bij overtreding."""
    if aard == PartijAard.organisatie:
        if scope not in (PartijScope.intern, PartijScope.extern):
            raise OngeldigeRegistratie("ONGELDIGE_SCOPE", "Een organisatie is intern of extern.")
    elif aard == PartijAard.externe_partij:
        if scope != PartijScope.extern:
            raise OngeldigeRegistratie(
                "EXTERNE_PARTIJ_ALTIJD_EXTERN", "Een externe partij is altijd extern."
            )
    elif scope is not None:
        raise OngeldigeRegistratie(
            "SCOPE_ALLEEN_ORGANISATIE", "Alleen een organisatie draagt een intern/extern-kenmerk."
        )


def _valideer_functietitel(aard: PartijAard, functietitel: str | None) -> None:
    """ADR-024 (Optie 1) — `functietitel` geldt uitsluitend voor een persoon (422 bij andere aarden).
    E-mail/telefoon blijven gedeelde contactvelden; alleen de functietitel is persoon-eigen."""
    if functietitel is not None and aard != PartijAard.persoon:
        raise OngeldigeRegistratie(
            "FUNCTIETITEL_ALLEEN_PERSOON",
            "Een functietitel kan alleen voor een persoon worden vastgelegd.",
        )


def _valideer_contactpersoon_aard(aard: PartijAard, contactpersoon_id) -> None:
    """ADR-039 — een aanspreekpunt geldt uitsluitend voor een organisatie of externe
    partij (die dragen een eigen aanspreekpunt; spiegel van hoe `functietitel` alleen op persoon
    leeft). 422 `CONTACTPERSOON_ALLEEN_PARTIJ` bij een afdeling of persoon."""
    if contactpersoon_id is not None and aard not in _ORGANISATIE_ACHTIG:
        raise OngeldigeRegistratie(
            "CONTACTPERSOON_ALLEEN_PARTIJ",
            "Een aanspreekpunt kan alleen voor een organisatie of externe partij worden vastgelegd.",
        )


async def maak_aan(session: AsyncSession, tenant_id, data: PartijCreate) -> Partij:
    tid = _tenant_uuid(tenant_id)
    await partijsoort_catalog.valideer_soort(session, data.soort)
    await _valideer_lidmaatschap(session, tid, data.aard, data.organisatie_id, data.afdeling_id)
    _valideer_functietitel(data.aard, data.functietitel)
    _valideer_contactpersoon_aard(data.aard, data.contactpersoon_id)  # ADR-039 — aard-restrictie
    # ADR-038 — bepaal + borg de effectieve intern/extern-waarde (default extern op organisatie).
    scope = _effectieve_scope(data.aard, data.scope)
    _valideer_scope(data.aard, scope)
    # Element-identiteit eerst (shared-PK), dan de partij-subtype-rij. `aard` uit de invoer.
    elem = Element(tenant_id=tid, element_type=ElementType.partij)
    session.add(elem)
    await session.flush()
    # ADR-039 — een aanspreekpunt moet een persoon zijn die bij déze partij hoort (elem.id ná flush).
    # Bij aanmaken bestaat de partij nog niet, dus er kan nog geen persoon bij horen: een gezette
    # contactpersoon_id levert hier terecht 422 op (het aanspreekpunt wordt in de bewerk-flow gezet).
    if data.contactpersoon_id is not None:
        await _valideer_contactpersoon(session, tid, elem.id, data.contactpersoon_id)
    velden = data.model_dump()
    velden["scope"] = scope  # de effectieve waarde vervangt de rauwe invoer
    obj = Partij(id=elem.id, tenant_id=tid, **velden)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def maak_persoon_flush(
    session: AsyncSession, tid: uuid.UUID, *, naam: str, email: str | None,
    afdeling_id: uuid.UUID | None, functietitel: str | None,
) -> Partij:
    """ADR-029 — maak een persoon-partij aan binnen een GROtere transactie (flush, GEEN commit),
    zodat de caller (gebruiker_service) bij een latere fout kan terugrollen. Hergebruikt dezelfde
    lidmaatschap-/functietitel-validatie als `maak_aan`. De caller commit zelf.
    `organisatie_id` wordt afgeleid: een afdeling impliceert een organisatie (de afdeling hoort
    daarbij); zonder afdeling is `organisatie_id` verplicht — daarom valideert deze helper dat
    `afdeling_id` gezet is (gebruiker-aanmaak hangt een persoon onder een afdeling)."""
    if afdeling_id is None:
        raise OngeldigeRegistratie(
            "AFDELING_VERPLICHT", "Een gebruiker (persoon) hoort verplicht bij een afdeling."
        )
    # Leid de organisatie van de afdeling af (een persoon hoort bij dezelfde organisatie).
    afdeling = (
        await session.execute(select(Partij).where(Partij.id == afdeling_id, Partij.tenant_id == tid))
    ).scalar_one_or_none()
    if afdeling is None or afdeling.aard != PartijAard.organisatie_eenheid:
        raise OngeldigeRegistratie("ONGELDIGE_AFDELING", "De afdeling moet een bestaande afdeling zijn.")
    organisatie_id = afdeling.organisatie_id

    await _valideer_lidmaatschap(session, tid, PartijAard.persoon, organisatie_id, afdeling_id)
    _valideer_functietitel(PartijAard.persoon, functietitel)
    elem = Element(tenant_id=tid, element_type=ElementType.partij)
    session.add(elem)
    await session.flush()
    persoon = Partij(
        id=elem.id, tenant_id=tid, aard=PartijAard.persoon, naam=naam, email=email,
        functietitel=functietitel, organisatie_id=organisatie_id, afdeling_id=afdeling_id,
    )
    session.add(persoon)
    await session.flush()
    return persoon


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
    if "functietitel" in velden:
        _valideer_functietitel(obj.aard, velden["functietitel"])  # aard ligt vast
    if "contactpersoon_id" in velden:
        # ADR-039 — aard-restrictie + "hoort bij déze partij" (aard ligt vast; partij bestaat).
        _valideer_contactpersoon_aard(obj.aard, velden["contactpersoon_id"])
        if velden["contactpersoon_id"] is not None:
            await _valideer_contactpersoon(session, tid, obj.id, velden["contactpersoon_id"])
    if "scope" in velden:
        _valideer_scope(obj.aard, velden["scope"])  # ADR-038 — aard-bewust (aard ligt vast)
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
