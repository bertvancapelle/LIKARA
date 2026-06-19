"""Service-laag — component-klaarverklaring (ADR-027).

Niet-scorende verklaring "component Y is beoordeeld en migratieklaar", als eigen tenant-scoped
registratie-feit (`ComponentKlaarverklaring`). Eén levende verklaring per component;
statushandelingen (klaar↔open) vereisen een reden en herstempelen `verklaard_door`/`verklaard_op`
server-side. Tenant-scoped (RLS + expliciet `tenant_id`-filter).

Validatie: component bestaat binnen de tenant (→ 404), dubbel → 409 `KLAARVERKLARING_BESTAAT_AL`.
Lege reden wordt al in het schema afgevangen (422 native). Geen categorie-dimensie meer.

Puur registratief — RAAKT DE ENGINE NOOIT: importeert géén `lifecycle_service`/`herbereken_lifecycle`/
`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/`Checklistscore` en schrijft niets in lifecycle-/
score-/blokkade-state.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import huidige_actor
from models.models import ComponentKlaarverklaring, Component, KlaarverklaringStatus
from schemas.component_klaarverklaring import KlaarverklaringCreate, KlaarverklaringStatusWijzig
from services import actor_resolutie
from services.errors import NietGevonden, RegistratieConflict

_ENTITEIT = "component_klaarverklaring"


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _stempel() -> tuple[str | None, str | None, datetime]:
    """Server-side actor + tijdstip (registratie, niet door client aanleverbaar). ADR-029 Fase 3b:
    `sub` = stabiele sleutel (naam-resolutie), `email` = leesbare fallback."""
    actor_sub, actor_email = huidige_actor()
    return (actor_sub, actor_email, datetime.now(timezone.utc))


async def _zet_naam(session: AsyncSession, tid: uuid.UUID, obj: ComponentKlaarverklaring) -> ComponentKlaarverklaring:
    """Transient `verklaard_door_naam` (ADR-029): sub → persoon.naam, anders e-mail-fallback."""
    obj.verklaard_door_naam = await actor_resolutie.resolveer_naam(
        session, tid, sub=obj.verklaard_door_sub, email=obj.verklaard_door
    )
    return obj


async def _component_bestaat(session: AsyncSession, tid: uuid.UUID, component_id) -> None:
    """Component binnen de tenant; niet gevonden ⇒ 404 (geen lek)."""
    gevonden = (
        await session.execute(
            select(Component.id).where(Component.id == component_id, Component.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if gevonden is None:
        raise NietGevonden("component", component_id)


async def maak_aan(session: AsyncSession, tenant_id, data: KlaarverklaringCreate) -> ComponentKlaarverklaring:
    tid = _tenant_uuid(tenant_id)
    await _component_bestaat(session, tid, data.component_id)
    sub, email, op = _stempel()
    obj = ComponentKlaarverklaring(
        tenant_id=tid,
        component_id=data.component_id,
        status=KlaarverklaringStatus.klaar,
        reden=data.reden,
        verklaard_door_sub=sub,
        verklaard_door=email,
        verklaard_op=op,
    )
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise RegistratieConflict(
            "KLAARVERKLARING_BESTAAT_AL",
            "Er bestaat al een klaarverklaring voor dit component; gebruik de statuswijziging.",
        )
    await session.refresh(obj)
    return await _zet_naam(session, tid, obj)


async def haal_op(session: AsyncSession, tenant_id, klaarverklaring_id) -> ComponentKlaarverklaring:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(ComponentKlaarverklaring).where(
                ComponentKlaarverklaring.id == klaarverklaring_id,
                ComponentKlaarverklaring.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, klaarverklaring_id)
    return await _zet_naam(session, _tenant_uuid(tenant_id), obj)


async def wijzig_status(
    session: AsyncSession, tenant_id, klaarverklaring_id, data: KlaarverklaringStatusWijzig
) -> ComponentKlaarverklaring:
    """Symmetrisch klaar↔open; nieuwe reden verplicht (schema), herstempelt wie/wanneer."""
    obj = await haal_op(session, tenant_id, klaarverklaring_id)
    sub, email, op = _stempel()
    obj.status = KlaarverklaringStatus(data.status)
    obj.reden = data.reden
    obj.verklaard_door_sub = sub
    obj.verklaard_door = email
    obj.verklaard_op = op
    await session.commit()
    await session.refresh(obj)
    return await _zet_naam(session, _tenant_uuid(tenant_id), obj)


async def lijst(session: AsyncSession, tenant_id, *, component_id=None) -> list[ComponentKlaarverklaring]:
    """Tenant-scoped (RLS + expliciet filter); optioneel per component.

    Bewust géén keyset-paginering: een begrensde sub-lijst (max één rij per component),
    niet de generieke lijst-norm.
    """
    tid = _tenant_uuid(tenant_id)
    stmt = select(ComponentKlaarverklaring).where(ComponentKlaarverklaring.tenant_id == tid)
    if component_id is not None:
        stmt = stmt.where(ComponentKlaarverklaring.component_id == component_id)
    stmt = stmt.order_by(ComponentKlaarverklaring.component_id)
    rijen = list((await session.execute(stmt)).scalars().all())
    # Batch naam-resolutie (één query) → transient `verklaard_door_naam` per rij; fallback e-mail.
    naam_map = await actor_resolutie.resolveer_namen(session, tid, {r.verklaard_door_sub for r in rijen})
    for r in rijen:
        r.verklaard_door_naam = naam_map.get(r.verklaard_door_sub) or r.verklaard_door
    return rijen
