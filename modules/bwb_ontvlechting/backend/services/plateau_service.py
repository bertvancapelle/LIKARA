"""Service-laag — Plateau + plateau-lidmaatschap (ADR-023 Fase E, E1).

Plateau is een element-subtype (shared-PK); CRUD volgt het bestaande patroon
(`Element(element_type='plateau')` → subtype-rij; delete via het element-supertype,
cascade). Lidmaatschap is een **facade over het unified relatiemodel** (zoals
`component_contract_service` over `Relatie`): een `aggregation`-relatie bron=plateau →
doel=lid, met de dispositie (catalogus-kenmerk) + contractuele bevestiging (registratie-
kenmerken) in `kenmerken`. Toegestane leden in deze slice: component en contract.

Niets hier raakt lifecycle/score/blokkade — er is bewust géén import van de engine
(score blijft de enige lifecycle-driver). `bevestigd_door`/`bevestigd_op` worden
server-side uit de actor-context gevuld op het moment dat de bevestiging op `ja` gaat —
registratie, geen afdwinging.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import huidige_actor
from models.models import (
    Component,
    Contract,
    Element,
    ElementType,
    Plateau,
    Relatie,
    RelatieKenmerkDimensie,
)
from schemas.plateau import (
    PlateauCreate,
    PlateauLidCreate,
    PlateauLidUpdate,
    PlateauUpdate,
)
from services import actor_resolutie
from services import relatiekenmerk_catalog as catalog
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict
from services.pagination import decode_sort_cursor, encode_sort_cursor

_ENTITEIT = "plateau"
_AGGREGATION = "aggregation"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100
_LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    return term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")

# Toegestane lid-element-typen in deze slice (E1). Datatype/gebruikersgroep later additief.
_TOEGESTANE_LID_TYPES = frozenset({ElementType.component.value, ElementType.contract.value})


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


# ── Plateau-CRUD (element-subtype) ───────────────────────────────────────────────

async def haal_op(session: AsyncSession, tenant_id, plateau_id) -> Plateau:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Plateau).where(Plateau.id == plateau_id, Plateau.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, plateau_id)
    return obj


def _lees(obj: Plateau) -> dict:
    return {
        "id": obj.id,
        "naam": obj.naam,
        "toelichting": obj.toelichting,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


async def maak_aan(session: AsyncSession, tenant_id, data: PlateauCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    # Element-identiteit eerst (shared-PK), daarna de subtype-rij met dezelfde id.
    elem = Element(tenant_id=tid, element_type=ElementType.plateau)
    session.add(elem)
    await session.flush()
    obj = Plateau(id=elem.id, tenant_id=tid, naam=data.naam, toelichting=data.toelichting)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj)


async def lees_detail(session: AsyncSession, tenant_id, plateau_id) -> dict:
    return _lees(await haal_op(session, tenant_id, plateau_id))


async def werk_bij(session: AsyncSession, tenant_id, plateau_id, data: PlateauUpdate) -> dict:
    obj = await haal_op(session, tenant_id, plateau_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj)


async def verwijder(session: AsyncSession, tenant_id, plateau_id) -> None:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, plateau_id)  # 404 kruis-tenant
    # Verwijder via het element-supertype: cascade element → plateau (subtype) én de
    # aggregation-lidmaatschapsrelaties (relatie-FK's → element, ON DELETE CASCADE).
    from sqlalchemy import delete

    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == plateau_id))
    await session.commit()


async def lijst(
    session: AsyncSession, tenant_id, *, limit: int = _STANDAARD_LIMIT, after: str | None = None,
    zoek: str | None = None,
) -> tuple[list[dict], str | None]:
    """Keyset-lijst binnen de tenant (created_at oplopend). `zoek` = ge-escapete ILIKE op `naam`
    (voor het plateau-koppelveld in de deliverable-keten). Cursor-mismatch ⇒ ValueError (400)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)
    stmt = select(Plateau).where(Plateau.tenant_id == tid)
    if zoek:
        stmt = stmt.where(Plateau.naam.ilike(f"%{_escape_like(zoek)}%", escape=_LIKE_ESCAPE))
    if after:
        _s, _o, waarde_str, c_id = decode_sort_cursor(after)
        c_waarde = datetime.fromisoformat(waarde_str)
        stmt = stmt.where(
            or_(
                Plateau.created_at > c_waarde,
                and_(Plateau.created_at == c_waarde, Plateau.id > c_id),
            )
        )
    stmt = stmt.order_by(Plateau.created_at.asc(), Plateau.id.asc()).limit(limit + 1)
    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor(sort="created_at", order="asc", waarde=items[-1].created_at, id=items[-1].id)
        if heeft_meer else None
    )
    return [_lees(o) for o in items], volgende


# ── Lidmaatschap (facade over Relatie: aggregation bron=plateau → doel=lid) ───────

async def _lid_element_type(session: AsyncSession, tid: uuid.UUID, lid_id) -> str:
    et = (
        await session.execute(
            select(Element.element_type).where(Element.tenant_id == tid, Element.id == lid_id)
        )
    ).scalar_one_or_none()
    if et is None:
        raise NietGevonden("element", lid_id)
    return et.value if hasattr(et, "value") else str(et)


async def _lid_naam(session: AsyncSession, tid: uuid.UUID, lid_id) -> str | None:
    """Naam van het lid (component → naam, contract → contractnaam)."""
    naam = (
        await session.execute(
            select(Component.naam).where(Component.id == lid_id, Component.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if naam is not None:
        return naam
    return (
        await session.execute(
            select(Contract.contractnaam).where(Contract.id == lid_id, Contract.tenant_id == tid)
        )
    ).scalar_one_or_none()


async def actieve_disposities(session: AsyncSession) -> list[dict]:
    """Actieve `dispositie`-opties (voor het lid-koppel-dropdown), gesorteerd op volgorde."""
    return (await catalog.actieve_opties_per_dimensie(session)).get(
        RelatieKenmerkDimensie.dispositie.value, []
    )


def _bevestiging_kenmerken(contractueel_bevestigd: bool, aantal: int | None) -> dict:
    """Bouw de bevestigingskenmerken; bij `ja` worden wie/wanneer server-side gestempeld
    (registratie, geen afdwinging). Bij `nee` géén stempel (en bestaande wordt gewist)."""
    kenmerken: dict = {"contractueel_bevestigd": bool(contractueel_bevestigd)}
    if aantal is not None:
        kenmerken["bevestigd_aantal_gebruikers"] = aantal
    if contractueel_bevestigd:
        actor_sub, actor_email = huidige_actor()
        # ADR-029 Fase 3b — stempel {sub, email}: sub = stabiele sleutel (naam-resolutie),
        # email = leesbare fallback. Historische kale strings worden read-side ook nog afgehandeld.
        kenmerken["bevestigd_door"] = {"sub": actor_sub, "email": actor_email}
        kenmerken["bevestigd_op"] = datetime.now(timezone.utc).isoformat()
    return kenmerken


async def _haal_lid(session: AsyncSession, tid: uuid.UUID, plateau_id, lid_relatie_id) -> Relatie:
    obj = (
        await session.execute(
            select(Relatie).where(
                Relatie.id == lid_relatie_id, Relatie.tenant_id == tid,
                Relatie.relatietype == _AGGREGATION, Relatie.bron_id == plateau_id,
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden("plateau_lid", lid_relatie_id)
    return obj


async def _lees_lid(session: AsyncSession, tid: uuid.UUID, obj: Relatie) -> dict:
    rol_labels = await catalog.labels(session, RelatieKenmerkDimensie.dispositie)
    k = obj.kenmerken or {}
    dispositie = k.get("dispositie")
    # ADR-029 Fase 3b — `bevestigd_door` is nu {sub,email} (nieuw) of een kale e-mailstring
    # (historisch). Exposeer de e-mail als `bevestigd_door` (schema-compat) + de geresolveerde naam.
    _sub, _email = actor_resolutie.pak_sub_email(k.get("bevestigd_door"))
    return {
        "id": obj.id,
        "plateau_id": obj.bron_id,
        "lid_id": obj.doel_id,
        "lid_element_type": await _lid_element_type(session, tid, obj.doel_id),
        "lid_naam": await _lid_naam(session, tid, obj.doel_id),
        "dispositie": dispositie,
        "dispositie_label": catalog.resolveer_een(dispositie, rol_labels),
        "contractueel_bevestigd": bool(k.get("contractueel_bevestigd", False)),
        "bevestigd_aantal_gebruikers": k.get("bevestigd_aantal_gebruikers"),
        "bevestigd_door": _email,
        "bevestigd_door_naam": await actor_resolutie.resolveer_naam(session, tid, sub=_sub, email=_email),
        "bevestigd_op": k.get("bevestigd_op"),
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


async def maak_lid(session: AsyncSession, tenant_id, plateau_id, data: PlateauLidCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, plateau_id)  # 404 kruis-tenant
    lid_type = await _lid_element_type(session, tid, data.lid_id)
    if lid_type not in _TOEGESTANE_LID_TYPES:
        raise OngeldigeRegistratie(
            "ONGELDIG_LID",
            "Alleen componenten en contracten kunnen lid van een plateau zijn.",
        )
    await catalog.valideer_sleutels(session, RelatieKenmerkDimensie.dispositie, [data.dispositie])

    kenmerken = {"dispositie": data.dispositie, **_bevestiging_kenmerken(
        data.contractueel_bevestigd, data.bevestigd_aantal_gebruikers
    )}
    obj = Relatie(
        tenant_id=tid, bron_id=plateau_id, doel_id=data.lid_id,
        relatietype=_AGGREGATION, kenmerken=kenmerken,
    )
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise RegistratieConflict("LID_BESTAAT", "Dit lid zit al in dit plateau.") from exc
    await session.refresh(obj)
    return await _lees_lid(session, tid, obj)


async def werk_lid_bij(
    session: AsyncSession, tenant_id, plateau_id, lid_relatie_id, data: PlateauLidUpdate
) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await _haal_lid(session, tid, plateau_id, lid_relatie_id)
    velden = data.model_dump(exclude_unset=True)
    k = dict(obj.kenmerken or {})

    if "dispositie" in velden:
        await catalog.valideer_sleutels(session, RelatieKenmerkDimensie.dispositie, [velden["dispositie"]])
        k["dispositie"] = velden["dispositie"]

    # Contractuele bevestiging is registratie: herbereken de stempels uit de eindtoestand.
    raakt_bevestiging = "contractueel_bevestigd" in velden or "bevestigd_aantal_gebruikers" in velden
    if raakt_bevestiging:
        bevestigd = velden.get("contractueel_bevestigd", k.get("contractueel_bevestigd", False))
        aantal = velden.get("bevestigd_aantal_gebruikers", k.get("bevestigd_aantal_gebruikers"))
        # Verwijder oude bevestigingssleutels en zet ze opnieuw conform de eindtoestand.
        for sleutel in ("contractueel_bevestigd", "bevestigd_aantal_gebruikers", "bevestigd_door", "bevestigd_op"):
            k.pop(sleutel, None)
        k.update(_bevestiging_kenmerken(bevestigd, aantal))

    obj.kenmerken = k
    await session.commit()
    await session.refresh(obj)
    return await _lees_lid(session, tid, obj)


async def verwijder_lid(session: AsyncSession, tenant_id, plateau_id, lid_relatie_id) -> None:
    tid = _tenant_uuid(tenant_id)
    obj = await _haal_lid(session, tid, plateau_id, lid_relatie_id)
    await session.delete(obj)
    await session.commit()


async def lijst_leden(session: AsyncSession, tenant_id, plateau_id) -> list[dict]:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, plateau_id)  # 404 kruis-tenant
    rol_labels = await catalog.labels(session, RelatieKenmerkDimensie.dispositie)
    lid_naam = func.coalesce(Component.naam, Contract.contractnaam).label("lid_naam")
    rijen = (
        await session.execute(
            select(Relatie, Element.element_type, lid_naam)
            .join(Element, and_(Element.id == Relatie.doel_id, Element.tenant_id == tid))
            .outerjoin(Component, Component.id == Relatie.doel_id)
            .outerjoin(Contract, Contract.id == Relatie.doel_id)
            .where(
                Relatie.tenant_id == tid, Relatie.bron_id == plateau_id,
                Relatie.relatietype == _AGGREGATION,
            )
            .order_by(Relatie.created_at.asc(), Relatie.id.asc())
        )
    ).all()
    uit = []
    for rel, et, naam in rijen:
        k = rel.kenmerken or {}
        dispositie = k.get("dispositie")
        uit.append({
            "id": rel.id, "plateau_id": rel.bron_id, "lid_id": rel.doel_id,
            "lid_element_type": et.value if hasattr(et, "value") else str(et),
            "lid_naam": naam,
            "dispositie": dispositie,
            "dispositie_label": catalog.resolveer_een(dispositie, rol_labels),
            "contractueel_bevestigd": bool(k.get("contractueel_bevestigd", False)),
            "bevestigd_aantal_gebruikers": k.get("bevestigd_aantal_gebruikers"),
            "bevestigd_door": k.get("bevestigd_door"),
            "bevestigd_op": k.get("bevestigd_op"),
            "created_at": rel.created_at, "updated_at": rel.updated_at,
        })
    return uit
