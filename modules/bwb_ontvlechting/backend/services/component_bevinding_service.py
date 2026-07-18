"""Service — component-bevinding "bewust geen" (ADR-052 slice 2).

Per component een uitspreekbare bevinding "vastgesteld — dit component heeft geen koppelingen /
geen contract", streng onderscheiden van "nog nooit naar gekeken" (= geen rij). Registratiefeit:
wie/wanneer server-gestempeld + optionele toelichting; intrekbaar (verwijderen).

**Geen stille tegenspraak (mirror `functievervulling._weiger_tegengesteld`):** "bewust geen" mag
niet náást een échte registratie bestaan. Write-side: `registreer_geen` weigert (409) als er al een
echte koppeling/contract is. Read-side: een échte registratie WINT — `is_vastgesteld` telt een feit
als vastgesteld zodra er een echte registratie is, ongeacht een (achterhaalde) bevinding. Zo is de
afgeleide/getoonde waarheid nooit tegenstrijdig, en de generieke relatie-/contract-schrijfpaden
hoeven niet aangeraakt te worden.

Puur registratief — RAAKT DE ENGINE NOOIT: importeert géén lifecycle/score/blokkade/profiel-symbolen.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import huidige_actor
from models.models import (
    Component,
    ComponentBevinding,
    ComponentBevindingSoort,
    Contract,
    Relatie,
)
from services import actor_resolutie
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict

_ENTITEIT = "component_bevinding"
_FLOW = "flow"
_ASSOCIATION = "association"


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _valideer_soort(soort) -> ComponentBevindingSoort:
    if isinstance(soort, ComponentBevindingSoort):
        return soort
    try:
        return ComponentBevindingSoort(soort)
    except ValueError as e:
        raise OngeldigeRegistratie("ONGELDIGE_SOORT", "Onbekende bevinding-soort.") from e


async def _component_bestaat(session: AsyncSession, tid: uuid.UUID, component_id) -> None:
    gevonden = (
        await session.execute(
            select(Component.id).where(Component.id == component_id, Component.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if gevonden is None:
        raise NietGevonden("component", component_id)  # 404 no-leak kruis-tenant


async def heeft_echte_registratie(session: AsyncSession, tenant_id, component_id, soort) -> bool:
    """Bestaat er een ÉCHTE koppeling/contract op dit component (de tegenpool van 'bewust geen')?

    - koppelingen = een `flow`-relatie met bron óf doel = dit component;
    - contract = een `association`-relatie van dit component (bron) naar een contract (doel).

    De single-source "heeft koppeling/contract"-lezer voor deze twee feiten (gebruikt door de
    write-guard hier én door de norm-toetsing in `component_norm_service`). Read-only."""
    tid = _tenant_uuid(tenant_id)
    s = _valideer_soort(soort)
    if s == ComponentBevindingSoort.koppelingen:
        stmt = select(Relatie.id).where(
            Relatie.tenant_id == tid,
            Relatie.relatietype == _FLOW,
            or_(Relatie.bron_id == component_id, Relatie.doel_id == component_id),
        )
    else:  # contract
        stmt = (
            select(Relatie.id)
            .join(Contract, and_(Contract.id == Relatie.doel_id, Contract.tenant_id == tid))
            .where(
                Relatie.tenant_id == tid,
                Relatie.relatietype == _ASSOCIATION,
                Relatie.bron_id == component_id,
            )
        )
    return (await session.execute(stmt.limit(1))).first() is not None


async def soorten_van_component(session: AsyncSession, tenant_id, component_id) -> set[str]:
    """De soorten waarvoor dit component een 'bewust geen'-bevinding draagt. Read-only."""
    tid = _tenant_uuid(tenant_id)
    rijen = (
        await session.execute(
            select(ComponentBevinding.soort).where(
                ComponentBevinding.tenant_id == tid,
                ComponentBevinding.component_id == component_id,
            )
        )
    ).all()
    return {getattr(r.soort, "value", r.soort) for r in rijen}


async def _lees(session: AsyncSession, tid: uuid.UUID, obj: ComponentBevinding) -> dict:
    naam = await actor_resolutie.resolveer_naam(
        session, tid, sub=obj.verklaard_door_sub, email=obj.verklaard_door
    )
    return {
        "id": obj.id,
        "component_id": obj.component_id,
        "soort": obj.soort.value if hasattr(obj.soort, "value") else obj.soort,
        "verklaard_door": obj.verklaard_door,
        "verklaard_door_naam": naam,
        "verklaard_op": obj.verklaard_op,
        "toelichting": obj.toelichting,
    }


async def registreer_geen(
    session: AsyncSession, tenant_id, component_id, soort, toelichting: str | None = None
) -> dict:
    """Leg vast: "dit component heeft geen <soort> — vastgesteld." 409 als er al een échte
    registratie is (geen tegenspraak) of al een bevinding (dubbel)."""
    tid = _tenant_uuid(tenant_id)
    await _component_bestaat(session, tid, component_id)
    s = _valideer_soort(soort)
    if await heeft_echte_registratie(session, tid, component_id, s):
        raise RegistratieConflict(
            "REGISTRATIE_BESTAAT",
            f"Dit component heeft {s.value}; 'bewust geen' kan niet naast een echte registratie.",
        )
    actor_sub, actor_email = huidige_actor()
    obj = ComponentBevinding(
        tenant_id=tid, component_id=component_id, soort=s,
        verklaard_door_sub=actor_sub, verklaard_door=actor_email,
        verklaard_op=datetime.now(timezone.utc), toelichting=toelichting,
    )
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise RegistratieConflict(
            "BEVINDING_BESTAAT", "Deze bevinding bestaat al voor dit component."
        )
    await session.refresh(obj)
    return await _lees(session, tid, obj)


async def verwijder(session: AsyncSession, tenant_id, component_id, soort) -> None:
    """Trek de bevinding in (herroepen). 404 als ze er niet is."""
    tid = _tenant_uuid(tenant_id)
    s = _valideer_soort(soort)
    obj = (
        await session.execute(
            select(ComponentBevinding).where(
                ComponentBevinding.tenant_id == tid,
                ComponentBevinding.component_id == component_id,
                ComponentBevinding.soort == s,
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, f"{component_id}/{s.value}")
    await session.delete(obj)
    await session.commit()


async def lijst_voor_component(session: AsyncSession, tenant_id, component_id) -> list[dict]:
    """De bevindingen van één component (0–2). Read-only; 404 als het component niet bestaat."""
    tid = _tenant_uuid(tenant_id)
    await _component_bestaat(session, tid, component_id)
    rijen = list(
        (
            await session.execute(
                select(ComponentBevinding).where(
                    ComponentBevinding.tenant_id == tid,
                    ComponentBevinding.component_id == component_id,
                ).order_by(ComponentBevinding.soort)
            )
        ).scalars().all()
    )
    return [await _lees(session, tid, r) for r in rijen]
