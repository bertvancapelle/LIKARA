"""Service-laag — procesvervulling: "component X vervult applicatiefunctie Y in proces Z"
(ADR-042 slice 3, het roltoewijzing-recept).

Tenant-scoped (RLS + expliciete `tenant_id`-filter). Validatie vooraf (fail-secure,
404 no-leak buiten de tenant):
- component-kant = een bestaand `component`-element — élk componenttype, component-breed
  (ADR-042 besluit 3) ⇒ anders 422 `ONGELDIG_COMPONENT`;
- proces-kant = een bestaand `proces`-element ⇒ anders 422 `ONGELDIG_PROCES`;
- `applicatiefunctie` = actieve catalogus-optie ⇒ anders 422 `ONGELDIGE_APPLICATIEFUNCTIE`;
- dubbel tripel ⇒ 409 `VERVULLING_BESTAAT` (pre-check; de UNIQUE is de DB-backstop).

Leesbaar in beide richtingen (per proces de componenten, per component de processen) met
naam-verrijking via joins + één label-map per lijst (geen N+1). Puur registratief — geen
engine-import (score blijft de enige lifecycle-driver; ADR-042-invariant).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import (
    Component,
    ComponentConfigDimensie,
    Element,
    ElementType,
    Proces,
    Procesvervulling,
)
from services import applicatiefunctie_catalog as af_catalog
from services import componentconfig_catalog as cc_catalog
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict

_ENTITEIT = "procesvervulling"


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def _element_type(session: AsyncSession, tid: uuid.UUID, element_id) -> str | None:
    rij = (
        await session.execute(
            select(Element.element_type).where(Element.tenant_id == tid, Element.id == element_id)
        )
    ).scalar_one_or_none()
    return getattr(rij, "value", rij) if rij is not None else None


async def actieve_functies(session: AsyncSession) -> list[dict]:
    """Actieve applicatiefunctie-opties voor het keuze-dropdown."""
    return await af_catalog.actieve_opties(session)


async def maak_aan(
    session: AsyncSession, tenant_id, component_id, proces_id, applicatiefunctie: str,
    toelichting: str | None = None,
) -> dict:
    tid = _tenant_uuid(tenant_id)
    # Component-kant: een bestaand component-element — élk componenttype (component-breed).
    if await _element_type(session, tid, component_id) != ElementType.component.value:
        raise OngeldigeRegistratie(
            "ONGELDIG_COMPONENT", "De component-kant moet een bestaand component zijn."
        )
    # Proces-kant: een bestaand proces-element.
    if await _element_type(session, tid, proces_id) != ElementType.proces.value:
        raise OngeldigeRegistratie(
            "ONGELDIG_PROCES", "De proces-kant moet een bestaand proces zijn."
        )
    await af_catalog.valideer_functie(session, applicatiefunctie)
    # Dubbel tripel ⇒ 409 (pre-check; de UNIQUE-constraint is de DB-backstop).
    bestaat = (
        await session.execute(
            select(Procesvervulling.id).where(
                Procesvervulling.tenant_id == tid,
                Procesvervulling.component_id == component_id,
                Procesvervulling.proces_id == proces_id,
                Procesvervulling.applicatiefunctie == applicatiefunctie,
            )
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise RegistratieConflict(
            "VERVULLING_BESTAAT",
            "Dit component vervult deze applicatiefunctie al in dit proces.",
        )
    obj = Procesvervulling(
        tenant_id=tid, component_id=component_id, proces_id=proces_id,
        applicatiefunctie=applicatiefunctie, toelichting=toelichting,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return await _lees_een(session, obj)


async def verwijder(session: AsyncSession, tenant_id, vervulling_id) -> None:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Procesvervulling).where(
                Procesvervulling.id == vervulling_id, Procesvervulling.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, vervulling_id)  # 404 no-leak kruis-tenant
    await session.delete(obj)
    await session.commit()


async def _lees_een(session: AsyncSession, obj: Procesvervulling) -> dict:
    """Volledige read van één regel (na aanmaak): beide zijden verrijkt."""
    tid = obj.tenant_id
    af_labels = await af_catalog.labels(session)
    comp = (
        await session.execute(
            select(Component.naam, Component.componenttype).where(
                Component.id == obj.component_id, Component.tenant_id == tid
            )
        )
    ).one_or_none()
    type_labels = await cc_catalog.labels(session, ComponentConfigDimensie.componenttype)
    ouder = aliased(Proces)
    pr = (
        await session.execute(
            select(Proces.naam, ouder.naam.label("ouder_naam"))
            .outerjoin(ouder, (ouder.id == Proces.ouder_id) & (ouder.tenant_id == tid))
            .where(Proces.id == obj.proces_id, Proces.tenant_id == tid)
        )
    ).one_or_none()
    return {
        "vervulling_id": obj.id,
        "applicatiefunctie": obj.applicatiefunctie,
        "applicatiefunctie_label": af_catalog.resolveer_een(obj.applicatiefunctie, af_labels),
        "toelichting": obj.toelichting,
        "component_id": obj.component_id,
        "component_naam": comp.naam if comp else None,
        "componenttype": comp.componenttype if comp else None,
        "componenttype_label": cc_catalog.resolveer_een(comp.componenttype, type_labels) if comp else None,
        "proces_id": obj.proces_id,
        "proces_naam": pr.naam if pr else None,
        "proces_ouder_naam": pr.ouder_naam if pr else None,
    }


async def lijst_voor_proces(session: AsyncSession, tenant_id, proces_id) -> list[dict]:
    """"Componenten in dit proces": de koppelregels van één proces, verrijkt met
    component-naam + type(-label) + functie-label; gesorteerd op component-naam dan
    functie. Onbekend proces binnen de tenant ⇒ 404 (no-leak)."""
    tid = _tenant_uuid(tenant_id)
    if await _element_type(session, tid, proces_id) != ElementType.proces.value:
        raise NietGevonden("proces", proces_id)
    af_labels = await af_catalog.labels(session)
    type_labels = await cc_catalog.labels(session, ComponentConfigDimensie.componenttype)
    rijen = (
        await session.execute(
            select(
                Procesvervulling.id,
                Procesvervulling.applicatiefunctie,
                Procesvervulling.toelichting,
                Procesvervulling.component_id,
                Component.naam.label("component_naam"),
                Component.componenttype.label("componenttype"),
            )
            .join(
                Component,
                (Component.id == Procesvervulling.component_id) & (Component.tenant_id == tid),
            )
            .where(Procesvervulling.tenant_id == tid, Procesvervulling.proces_id == proces_id)
            .order_by(Component.naam, Procesvervulling.applicatiefunctie, Procesvervulling.id)
        )
    ).all()
    return [
        {
            "vervulling_id": r.id,
            "applicatiefunctie": r.applicatiefunctie,
            "applicatiefunctie_label": af_catalog.resolveer_een(r.applicatiefunctie, af_labels),
            "toelichting": r.toelichting,
            "component_id": r.component_id,
            "component_naam": r.component_naam,
            "componenttype": r.componenttype,
            "componenttype_label": cc_catalog.resolveer_een(r.componenttype, type_labels),
        }
        for r in rijen
    ]


async def lijst_voor_component(session: AsyncSession, tenant_id, component_id) -> list[dict]:
    """"Vervult een rol in": de koppelregels van één component, verrijkt met proces-naam
    + procescontext (ouder-naam) + functie-label; gesorteerd op proces-naam dan functie.
    Onbekend component binnen de tenant ⇒ 404 (no-leak)."""
    tid = _tenant_uuid(tenant_id)
    if await _element_type(session, tid, component_id) != ElementType.component.value:
        raise NietGevonden("component", component_id)
    af_labels = await af_catalog.labels(session)
    ouder = aliased(Proces)
    rijen = (
        await session.execute(
            select(
                Procesvervulling.id,
                Procesvervulling.applicatiefunctie,
                Procesvervulling.toelichting,
                Procesvervulling.proces_id,
                Proces.naam.label("proces_naam"),
                ouder.naam.label("proces_ouder_naam"),
            )
            .join(Proces, (Proces.id == Procesvervulling.proces_id) & (Proces.tenant_id == tid))
            .outerjoin(ouder, (ouder.id == Proces.ouder_id) & (ouder.tenant_id == tid))
            .where(Procesvervulling.tenant_id == tid, Procesvervulling.component_id == component_id)
            .order_by(Proces.naam, Procesvervulling.applicatiefunctie, Procesvervulling.id)
        )
    ).all()
    return [
        {
            "vervulling_id": r.id,
            "applicatiefunctie": r.applicatiefunctie,
            "applicatiefunctie_label": af_catalog.resolveer_een(r.applicatiefunctie, af_labels),
            "toelichting": r.toelichting,
            "proces_id": r.proces_id,
            "proces_naam": r.proces_naam,
            "proces_ouder_naam": r.proces_ouder_naam,
        }
        for r in rijen
    ]
