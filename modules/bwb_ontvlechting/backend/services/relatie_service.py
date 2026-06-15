"""Service-laag — unified getypeerd relatiemodel (ADR-023 Besluit 1/6/12).

Tenant-scoped (RLS + expliciete `tenant_id`-filter). Een relatie is gericht
(`bron_id` → `doel_id`) tussen twee elementen; integriteit is schema-afgedwongen
(composiet-FK naar `element`, CHECK `bron≠doel`, UNIQUE). De service valideert vooraf:
beide endpoints binnen de tenant (404), `relatietype` tegen de actieve catalogus (422),
en de `kenmerken` tegen de per-relatietype property-definities (OK-2, 422). Richting is
GEEN kenmerk — ze zit in de bron→doel-oriëntatie + het relatietype.
"""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    ComponentConfigDimensie,
    ContractConfigDimensie,
    Element,
    ImpactVerbreking,
    Koppelrichting,
    Koppelprotocol,
    Relatie,
    RelatieKenmerkDimensie,
)
from schemas.relatie import RelatieCreate, RelatieUpdate
from services import componentconfig_catalog as catalog
from services import contractconfig_catalog as contract_catalog
from services import relatiekenmerk_catalog
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict
from services.pagination import (
    decode_sort_cursor,
    encode_sort_cursor,
)

_ENTITEIT = "relatie"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100

# OK-2: enum-namen in de kenmerk-definitie → de werkelijke model-enums.
_KENMERK_ENUMS = {
    "koppelprotocol": Koppelprotocol,
    "impact_verbreking": ImpactVerbreking,
    "koppelrichting": Koppelrichting,
}


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def _element_bestaat(session: AsyncSession, tid: uuid.UUID, element_id) -> bool:
    return (
        await session.execute(
            select(Element.id).where(Element.tenant_id == tid, Element.id == element_id)
        )
    ).scalar_one_or_none() is not None


async def _valideer_kenmerken(session: AsyncSession, relatietype: str, kenmerken: dict) -> None:
    """OK-2 — de aangeboden kenmerken moeten een subset zijn van de per-relatietype
    gedefinieerde properties; per kenmerk wordt de waarde tegen zijn type gevalideerd
    (enum-waarde of catalogus-sleutel). Ongeldig ⇒ 422 `ONGELDIG_KENMERK`."""
    if not kenmerken:
        return
    definitie = await catalog.kenmerk_definitie(session, relatietype)
    onbekend = [k for k in kenmerken if k not in definitie]
    if onbekend:
        raise OngeldigeRegistratie(
            "ONGELDIG_KENMERK",
            f"Onbekend kenmerk voor relatietype '{relatietype}': {', '.join(sorted(onbekend))}.",
        )
    for sleutel, waarde in kenmerken.items():
        spec = definitie[sleutel]
        if spec.get("type") == "enum":
            enum_cls = _KENMERK_ENUMS.get(spec.get("enum"))
            geldig = {e.value for e in enum_cls} if enum_cls else set()
            if waarde not in geldig:
                raise OngeldigeRegistratie(
                    "ONGELDIG_KENMERK", f"Ongeldige waarde voor kenmerk '{sleutel}'."
                )
        elif spec.get("type") == "catalogus":
            # Routeer naar de juiste vocabulaire-catalogus: `contractconfig` (default,
            # bv. relatie_rol) of `relatiekenmerk` (de algemene relatie-kenmerk-catalogus,
            # bv. dispositie). Losgekoppeld zodat migratie-kenmerken niet onder de
            # contract-configuratie vallen.
            if spec.get("catalogus") == "relatiekenmerk":
                geldig = await relatiekenmerk_catalog.actieve_sleutels(
                    session, RelatieKenmerkDimensie(spec["dimensie"])
                )
            else:
                geldig = await contract_catalog.actieve_sleutels(
                    session, ContractConfigDimensie(spec["dimensie"])
                )
            if waarde not in geldig:
                raise OngeldigeRegistratie(
                    "ONGELDIG_KENMERK",
                    f"Onbekende of inactieve catalogus-waarde voor kenmerk '{sleutel}'.",
                )
        elif spec.get("type") == "registratie":
            # Vrije registratiegegevens (geen vocabulaire-validatie) — bewust geaccepteerd.
            continue


async def haal_op(session: AsyncSession, tenant_id, relatie_id) -> Relatie:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Relatie).where(Relatie.id == relatie_id, Relatie.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, relatie_id)
    return obj


async def maak_aan(session: AsyncSession, tenant_id, data: RelatieCreate) -> Relatie:
    tid = _tenant_uuid(tenant_id)
    if data.bron_id == data.doel_id:
        raise OngeldigeRegistratie("ZELFVERWIJZING", "Bron en doel mogen niet gelijk zijn.")
    # Beide endpoints binnen de tenant (404 — geen lek van cross-tenant bestaan; OP-6).
    for kant, eid in (("bron", data.bron_id), ("doel", data.doel_id)):
        if not await _element_bestaat(session, tid, eid):
            raise NietGevonden("element", eid)
    await catalog.valideer_sleutel(session, ComponentConfigDimensie.archimate_relatie, data.relatietype)
    await _valideer_kenmerken(session, data.relatietype, data.kenmerken)

    obj = Relatie(
        tenant_id=tid, bron_id=data.bron_id, doel_id=data.doel_id,
        relatietype=data.relatietype, kenmerken=data.kenmerken, omschrijving=data.omschrijving,
    )
    session.add(obj)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise RegistratieConflict(
            "RELATIE_BESTAAT", "Deze relatie (bron, doel, type) bestaat al."
        ) from exc
    await session.commit()
    await session.refresh(obj)
    return obj


async def werk_bij(session: AsyncSession, tenant_id, relatie_id, data: RelatieUpdate) -> Relatie:
    """Partieel: alleen `kenmerken`/`omschrijving` zijn muteerbaar. Endpoints + relatietype
    zijn immutabel (een andere relatie = een nieuwe relatie)."""
    obj = await haal_op(session, tenant_id, relatie_id)
    velden = data.model_dump(exclude_unset=True)
    if "kenmerken" in velden:
        await _valideer_kenmerken(session, obj.relatietype, velden["kenmerken"] or {})
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj


async def verwijder(session: AsyncSession, tenant_id, relatie_id) -> None:
    obj = await haal_op(session, tenant_id, relatie_id)
    await session.delete(obj)
    await session.commit()


async def wezen(session: AsyncSession, tenant_id) -> list[dict]:
    """ADR-023 Besluit 13 — "wezen": elementen zonder énige relatie (bron noch doel).
    Bv. een datatype/gebruikersgroep waarvan de applicatie is verwijderd (de access/
    serving-relatie cascadeerde mee, het element bleef). Tenant-scoped (RLS)."""
    from sqlalchemy import exists

    tid = _tenant_uuid(tenant_id)
    heeft_relatie = exists().where(
        Relatie.tenant_id == tid,
        (Relatie.bron_id == Element.id) | (Relatie.doel_id == Element.id),
    )
    rijen = (
        await session.execute(
            select(Element.id, Element.element_type)
            .where(Element.tenant_id == tid, ~heeft_relatie)
            .order_by(Element.element_type, Element.id)
        )
    ).all()
    return [
        {"id": r.id, "element_type": getattr(r.element_type, "value", r.element_type)}
        for r in rijen
    ]


async def lijst(
    session: AsyncSession, tenant_id, *, limit: int = _STANDAARD_LIMIT, after: str | None = None,
    bron_id: uuid.UUID | None = None, doel_id: uuid.UUID | None = None,
    relatietype: str | None = None,
) -> tuple[list[Relatie], str | None]:
    """Keyset-lijst binnen de tenant (created_at oplopend), filterbaar op
    bron/doel/relatietype. Cursor-mismatch ⇒ `ValueError` (route ⇒ 400)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)
    stmt = select(Relatie).where(Relatie.tenant_id == tid)
    if bron_id is not None:
        stmt = stmt.where(Relatie.bron_id == bron_id)
    if doel_id is not None:
        stmt = stmt.where(Relatie.doel_id == doel_id)
    if relatietype:
        stmt = stmt.where(Relatie.relatietype == relatietype)
    if after:
        _s, _o, waarde_str, c_id = decode_sort_cursor(after)
        c_waarde = datetime.fromisoformat(waarde_str)
        from sqlalchemy import and_, or_, tuple_
        stmt = stmt.where(
            or_(
                Relatie.created_at > c_waarde,
                and_(Relatie.created_at == c_waarde, Relatie.id > c_id),
            )
        )
    stmt = stmt.order_by(Relatie.created_at.asc(), Relatie.id.asc()).limit(limit + 1)
    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor(sort="created_at", order="asc", waarde=items[-1].created_at, id=items[-1].id)
        if heeft_meer else None
    )
    return items, volgende
