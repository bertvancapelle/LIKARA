"""Service-laag voor de entiteit Gebruikersgroep (ADR-009; ADR-023 B-mig-2 slice 4; ADR-036/036a).

ADR-023: gebruikersgroep is een **zelfstandig element** (business actor/role); de band met de
applicatie is een **serving**-relatie (applicatie → gebruikersgroep). `applicatie_id` wordt afgeleid
uit de serving-relatie.

ADR-036: de organisatie leeft op het grove gebruiksfeit `organisatiegebruik` waar `gebruik_id` naar
verwijst (single source of truth). `organisatie_id` blijft een Create/Update/Read-veld, intern
vertaald naar een grof feit (get-or-create via `organisatiegebruik_service.ensure`).

ADR-036a: de afdeling is een **structurele referentie** `afdeling_id` naar een `organisatie_eenheid`-
partij binnen de organisatie van het grove feit (spiegel van het persoon→afdeling-patroon, ADR-024).
Optioneel; een organisatie-loze groep draagt geen afdeling. De read geeft `afdeling_id` + de
geresolveerde partij-naam (`afdeling`).
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, delete, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import (
    Component,
    Element,
    ElementType,
    Gebruikersgroep,
    Organisatiegebruik,
    Partij,
    PartijAard,
    Relatie,
)
from schemas.gebruikersgroep import GebruikersgroepCreate, GebruikersgroepUpdate
from services import component_service, organisatiegebruik_service

_APPLICATIE_TYPE = "applicatie"
from services.errors import NietGevonden, OngeldigeRegistratie
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "gebruikersgroep"
_SERVING = "serving"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"

# `organisatie`/`afdeling` sorteren op de naam van de gekoppelde partij (per-call join in `lijst`);
# de dict-waarde hier is een placeholder voor de allowlist-synctest (ADR-036/036a: geen eigen
# organisatie-/afdeling-tekstkolom meer — beide via een verwijzing).
_SORTEERBARE_KOLOMMEN = {
    "created_at": Gebruikersgroep.created_at,
    "organisatie": Gebruikersgroep.gebruik_id,
    "afdeling": Gebruikersgroep.afdeling_id,
    "aantal_gebruikers": Gebruikersgroep.aantal_gebruikers,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "organisatie": str,
    "afdeling": str,
    "aantal_gebruikers": int,
}


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def identiteit(afdeling: str | None, organisatie_naam: str | None) -> str:
    """ADR-036 stap D — een afdeling toont zich overal als "afdeling — organisatie"
    (bv. "Burgerzaken — Tiel"), zodat gelijknamige afdelingen van verschillende organisaties niet
    op één hoop vallen. Terugvallen: alleen afdeling (org-loos), alleen organisatie (afdeling
    ontbreekt), of een generieke naam (geen van beide — bv. een burger-groep)."""
    afdeling = (afdeling or "").strip() or None
    organisatie_naam = (organisatie_naam or "").strip() or None
    if afdeling and organisatie_naam:
        return f"{afdeling} — {organisatie_naam}"
    return afdeling or organisatie_naam or "Gebruikersgroep"


def _lees(obj: Gebruikersgroep, applicatie_id, organisatie_id=None, organisatie_naam=None, afdeling_naam=None) -> dict:
    """API-vorm. applicatie_id afgeleid uit serving; organisatie via het grove feit (ADR-036);
    afdeling via de afdeling-partij (ADR-036a). None = wees/organisatie-loos/geen afdeling."""
    return {
        "id": obj.id, "applicatie_id": applicatie_id,
        "organisatie_id": organisatie_id, "organisatie_naam": organisatie_naam,
        "afdeling_id": obj.afdeling_id, "afdeling": afdeling_naam,
        "aantal_gebruikers": obj.aantal_gebruikers,
        "created_at": obj.created_at, "updated_at": obj.updated_at,
    }


async def _org_voor_gebruik(session: AsyncSession, tid: uuid.UUID, gebruik_id):
    """(organisatie_id, organisatie_naam) van het grove feit waar deze groep onder hangt.
    `gebruik_id` None ⇒ (None, None) = organisatie-loze groep."""
    if gebruik_id is None:
        return None, None
    row = (
        await session.execute(
            select(Organisatiegebruik.organisatie_id, Partij.naam)
            .join(Partij, and_(Partij.id == Organisatiegebruik.organisatie_id, Partij.tenant_id == tid))
            .where(Organisatiegebruik.id == gebruik_id, Organisatiegebruik.tenant_id == tid)
        )
    ).first()
    return (row.organisatie_id, row.naam) if row else (None, None)


async def _afdeling_naam(session: AsyncSession, tid: uuid.UUID, afdeling_id):
    """Naam van de gekoppelde afdeling-partij (None als niet gezet)."""
    if afdeling_id is None:
        return None
    return (
        await session.execute(
            select(Partij.naam).where(Partij.id == afdeling_id, Partij.tenant_id == tid)
        )
    ).scalar_one_or_none()


async def _valideer_afdeling(session: AsyncSession, tid: uuid.UUID, afdeling_id, gebruik_id) -> None:
    """ADR-036a — een afdeling moet een bestaande `organisatie_eenheid`-partij zijn **binnen de
    organisatie van het grove feit** (`gebruik_id`). Een organisatie-loze groep (`gebruik_id` None)
    mag geen afdeling dragen. Spiegelt `partij_service._valideer_lidmaatschap` → 422 `ONGELDIGE_AFDELING`."""
    if afdeling_id is None:
        return
    if gebruik_id is None:
        raise OngeldigeRegistratie(
            "ONGELDIGE_AFDELING", "Een organisatie-loze groep kan geen afdeling dragen."
        )
    org_id = (
        await session.execute(
            select(Organisatiegebruik.organisatie_id).where(
                Organisatiegebruik.id == gebruik_id, Organisatiegebruik.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    afd = (
        await session.execute(
            select(Partij.aard, Partij.organisatie_id).where(
                Partij.id == afdeling_id, Partij.tenant_id == tid
            )
        )
    ).first()
    if afd is None or afd.aard != PartijAard.organisatie_eenheid:
        raise OngeldigeRegistratie("ONGELDIGE_AFDELING", "De afdeling moet een bestaande afdeling zijn.")
    if afd.organisatie_id != org_id:
        raise OngeldigeRegistratie(
            "ONGELDIGE_AFDELING", "De afdeling hoort niet bij de organisatie van deze groep."
        )


async def _applicaties_van(session: AsyncSession, tid: uuid.UUID, ids: list) -> dict:
    if not ids:
        return {}
    rijen = (
        await session.execute(
            select(Relatie.doel_id, Relatie.bron_id).where(
                Relatie.tenant_id == tid, Relatie.relatietype == _SERVING, Relatie.doel_id.in_(ids)
            )
        )
    ).all()
    return {r.doel_id: r.bron_id for r in rijen}


def _escape_like(term: str) -> str:
    """LIKE/ILIKE-wildcard-escaping (volgorde \\ → % → _), zoals de andere zoek-endpoints (CD017)."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def contexten(session: AsyncSession, tenant_id, *, zoek: str | None = None) -> list[dict]:
    """Fase B slice 2a (LI022) — distinct `(organisatie, afdeling)`-gebruikercontexten over alle
    gebruikersgroepen, met geresolveerde namen + een telling van bijbehorende componenten (distinct
    applicatie-bron van de serving-relatie). ADR-036: organisatie via het grove feit; ADR-036a:
    afdeling via de afdeling-partij. Doorzoekbaar (organisatie- OF afdeling-naam). Bewust BEGRENSDE
    afgeleide lijst (géén keyset). Read-only."""
    tid = _tenant_uuid(tenant_id)
    og = aliased(Organisatiegebruik)
    org = aliased(Partij)
    afd = aliased(Partij)
    serv = aliased(Relatie)
    stmt = (
        select(
            og.organisatie_id.label("organisatie_id"),
            org.naam.label("organisatie_naam"),
            afd.id.label("afdeling_id"),
            afd.naam.label("afdeling"),
            func.count(distinct(serv.bron_id)).label("aantal_componenten"),
        )
        .select_from(Gebruikersgroep)
        .outerjoin(og, and_(og.id == Gebruikersgroep.gebruik_id, og.tenant_id == tid))
        .outerjoin(org, and_(org.id == og.organisatie_id, org.tenant_id == tid))
        .outerjoin(afd, and_(afd.id == Gebruikersgroep.afdeling_id, afd.tenant_id == tid))
        .outerjoin(serv, and_(serv.doel_id == Gebruikersgroep.id, serv.tenant_id == tid, serv.relatietype == _SERVING))
        .where(Gebruikersgroep.tenant_id == tid)
        .group_by(og.organisatie_id, org.naam, afd.id, afd.naam)
        .order_by(org.naam.nulls_last(), afd.naam.nulls_last())
    )
    if zoek and zoek.strip():
        like = f"%{_escape_like(zoek.strip())}%"
        stmt = stmt.where(or_(org.naam.ilike(like, escape="\\"), afd.naam.ilike(like, escape="\\")))
    rijen = (await session.execute(stmt)).all()
    return [
        {
            "organisatie_id": r.organisatie_id, "organisatie_naam": r.organisatie_naam,
            "afdeling_id": r.afdeling_id, "afdeling": r.afdeling, "aantal_componenten": r.aantal_componenten,
        }
        for r in rijen
    ]


async def componenten_voor_context(
    session: AsyncSession, tenant_id, *, organisatie_id: uuid.UUID | None, afdeling_id: uuid.UUID | None
) -> list[dict]:
    """Fase B slice 2a (LI022) — distinct componenten (de applicatie-bron van de serving-relatie) van de
    gebruikersgroepen die EXACT op deze `(organisatie, afdeling)`-context matchen. ADR-036: organisatie
    via het grove feit; ADR-036a: afdeling via `afdeling_id`. Nullable-veilige match
    (`IS NOT DISTINCT FROM`) zodat de lege-organisatie-/lege-afdeling-casus (bv. "— / burgers") klopt."""
    tid = _tenant_uuid(tenant_id)
    og = aliased(Organisatiegebruik)
    rijen = (
        await session.execute(
            select(
                Component.id.label("component_id"),
                Component.naam.label("component_naam"),
                Component.componenttype.label("componenttype"),
            )
            .select_from(Gebruikersgroep)
            .outerjoin(og, and_(og.id == Gebruikersgroep.gebruik_id, og.tenant_id == tid))
            .join(Relatie, and_(Relatie.doel_id == Gebruikersgroep.id, Relatie.relatietype == _SERVING, Relatie.tenant_id == tid))
            .join(Component, and_(Component.id == Relatie.bron_id, Component.tenant_id == tid))
            .where(
                Gebruikersgroep.tenant_id == tid,
                og.organisatie_id.is_not_distinct_from(organisatie_id),
                Gebruikersgroep.afdeling_id.is_not_distinct_from(afdeling_id),
            )
            .distinct()
            .order_by(Component.naam, Component.id)
        )
    ).all()
    return [
        {"component_id": r.component_id, "component_naam": r.component_naam, "componenttype": r.componenttype}
        for r in rijen
    ]


async def lijst(
    session: AsyncSession, tenant_id, *, limit: int = _STANDAARD_LIMIT, after: str | None = None,
    applicatie_id: uuid.UUID | None = None, sort: str = _STANDAARD_SORT, order: str = _STANDAARD_ORDER,
) -> tuple[list[dict], str | None]:
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)
    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    # ADR-036/036a — LEFT JOIN het grove feit (org-naam) + de afdeling-partij (afdeling-naam) voor
    # naam-in-read + sortering op de gejoinde namen.
    og = aliased(Organisatiegebruik)
    org = aliased(Partij)
    afd = aliased(Partij)
    if sort == "organisatie":
        kolom = org.naam
    elif sort == "afdeling":
        kolom = afd.naam
    else:
        kolom = _SORTEERBARE_KOLOMMEN[sort]

    stmt = (
        select(
            Gebruikersgroep,
            og.organisatie_id.label("organisatie_id"),
            org.naam.label("organisatie_naam"),
            afd.naam.label("afdeling_naam"),
        )
        .outerjoin(og, and_(og.id == Gebruikersgroep.gebruik_id, og.tenant_id == tid))
        .outerjoin(org, and_(org.id == og.organisatie_id, org.tenant_id == tid))
        .outerjoin(afd, and_(afd.id == Gebruikersgroep.afdeling_id, afd.tenant_id == tid))
        .where(Gebruikersgroep.tenant_id == tid)
    )
    if applicatie_id is not None:
        stmt = stmt.join(
            Relatie,
            and_(
                Relatie.doel_id == Gebruikersgroep.id, Relatie.tenant_id == tid,
                Relatie.relatietype == _SERVING, Relatie.bron_id == applicatie_id,
            ),
        )
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(kolom, Gebruikersgroep.id, order=order, is_null=c_is_null, waarde=c_waarde, cursor_id=c_id)
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Gebruikersgroep.id, order)).limit(limit + 1)

    rijen = list((await session.execute(stmt)).all())  # (Gebruikersgroep, org_id|None, org_naam|None, afd_naam|None)
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    app_map = await _applicaties_van(session, tid, [g.id for (g, _oid, _on, _an) in items])
    out = [_lees(g, app_map.get(g.id), oid, on, an) for (g, oid, on, an) in items]
    if heeft_meer:
        laatste_g, _laatste_oid, laatste_on, laatste_an = items[-1]
        if sort == "organisatie":
            waarde = laatste_on
        elif sort == "afdeling":
            waarde = laatste_an
        else:
            waarde = getattr(laatste_g, kolom.key)
        volgende = encode_sort_cursor_nullable(sort=sort, order=order, waarde=waarde, id=laatste_g.id)
    else:
        volgende = None
    return out, volgende


async def haal_op(session: AsyncSession, tenant_id, gebruikersgroep_id) -> Gebruikersgroep:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Gebruikersgroep).where(
                Gebruikersgroep.id == gebruikersgroep_id, Gebruikersgroep.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, gebruikersgroep_id)
    return obj


async def lees_detail(session: AsyncSession, tenant_id, gebruikersgroep_id) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, gebruikersgroep_id)
    app_map = await _applicaties_van(session, tid, [obj.id])
    org_id, org_naam = await _org_voor_gebruik(session, tid, obj.gebruik_id)
    afd_naam = await _afdeling_naam(session, tid, obj.afdeling_id)
    return _lees(obj, app_map.get(obj.id), org_id, org_naam, afd_naam)


async def maak_aan(session: AsyncSession, tenant_id, data: GebruikersgroepCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    # LI059 Slice 3: ouder is een component met type 'applicatie' (geen subtabel meer).
    _ouder = await component_service.haal_op(session, tenant_id, data.applicatie_id)
    if _ouder.componenttype != _APPLICATIE_TYPE:
        raise NietGevonden(_APPLICATIE_TYPE, data.applicatie_id)
    # ADR-036 — organisatie zetten = het grove feit (organisatie, applicatie) get-or-create'n.
    gebruik_id = None
    if data.organisatie_id is not None:
        gebruik_id = await organisatiegebruik_service.ensure(session, tid, data.organisatie_id, data.applicatie_id)
    # ADR-036a — afdeling moet een org-eenheid binnen de grove-feit-organisatie zijn (of leeg).
    await _valideer_afdeling(session, tid, data.afdeling_id, gebruik_id)
    velden = data.model_dump(exclude={"applicatie_id", "organisatie_id"})  # {afdeling_id, aantal_gebruikers}
    elem = Element(tenant_id=tid, element_type=ElementType.gebruikersgroep)
    session.add(elem)
    await session.flush()
    obj = Gebruikersgroep(id=elem.id, tenant_id=tid, gebruik_id=gebruik_id, **velden)
    session.add(obj)
    session.add(Relatie(tenant_id=tid, bron_id=data.applicatie_id, doel_id=elem.id, relatietype=_SERVING))
    await session.commit()
    await session.refresh(obj)
    org_id, org_naam = await _org_voor_gebruik(session, tid, obj.gebruik_id)
    afd_naam = await _afdeling_naam(session, tid, obj.afdeling_id)
    return _lees(obj, data.applicatie_id, org_id, org_naam, afd_naam)


async def werk_bij(session: AsyncSession, tenant_id, gebruikersgroep_id, data: GebruikersgroepUpdate) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, gebruikersgroep_id)
    velden = data.model_dump(exclude_unset=True)
    # ADR-036 — organisatie wijzigen verschuift de verfijning-verwijzing (gebruik_id).
    if "organisatie_id" in velden:
        org_id = velden.pop("organisatie_id")
        if org_id is None:
            obj.gebruik_id = None
            obj.afdeling_id = None  # ADR-036a — organisatie-loze groep draagt geen afdeling
        else:
            app_map = await _applicaties_van(session, tid, [obj.id])
            app_id = app_map.get(obj.id)
            if app_id is None:
                raise OngeldigeRegistratie(
                    "GROEP_ZONDER_APPLICATIE",
                    "Deze groep hangt aan geen applicatie meer; een organisatie kan pas worden gekoppeld met een applicatie.",
                )
            obj.gebruik_id = await organisatiegebruik_service.ensure(session, tid, org_id, app_id)
    # ADR-036a — afdeling valideren tegen de (mogelijk gewijzigde) organisatie van het grove feit.
    if "afdeling_id" in velden:
        await _valideer_afdeling(session, tid, velden["afdeling_id"], obj.gebruik_id)
    elif obj.afdeling_id is not None:
        await _valideer_afdeling(session, tid, obj.afdeling_id, obj.gebruik_id)
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    app_map = await _applicaties_van(session, tid, [obj.id])
    org_id, org_naam = await _org_voor_gebruik(session, tid, obj.gebruik_id)
    afd_naam = await _afdeling_naam(session, tid, obj.afdeling_id)
    return _lees(obj, app_map.get(obj.id), org_id, org_naam, afd_naam)


async def verwijder(session: AsyncSession, tenant_id, gebruikersgroep_id) -> None:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, gebruikersgroep_id)
    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == gebruikersgroep_id))
    await session.commit()
