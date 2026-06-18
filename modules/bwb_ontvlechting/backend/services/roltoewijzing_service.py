"""Service-laag — rol-toewijzing (ADR-024 slice 2b).

"Partij X vervult rol Y op object Z" als eigen tenant-scoped registratie-feit
(`Roltoewijzing`), bewust LOS van het unified `relatie`-model (zie het model-docstring):
de uniciteit is exact `(tenant, partij, object, rol)`, dus meerdere rollen per (partij, object)
zijn losse regels. Tenant-scoped (RLS + expliciet `tenant_id`-filter). Validatie:
bron = partij-element (422 `ONGELDIGE_BRON`), doel = component/contract (422 `ONGELDIG_DOEL`),
rol = actieve `beheerrol`-optie (422 `ONGELDIGE_ROL`), dubbel ⇒ 409 `TOEWIJZING_BESTAAT`.

Puur registratief — GEEN engine-koppeling (geen lifecycle/score/blokkade/profiel). Importeert
daarom géén `lifecycle_service`/`herbereken_lifecycle`/`ComponentProfiel`/`Blokkade`/`Checklistscore`.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Component,
    Contract,
    Element,
    ElementType,
    Partij,
    RelatieKenmerkDimensie,
    Roltoewijzing,
)
from services import relatiekenmerk_catalog as catalog
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict

_ENTITEIT = "roltoewijzing"
_DIM = RelatieKenmerkDimensie.beheerrol
_OBJECT_TYPES = frozenset({ElementType.component.value, ElementType.contract.value})


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def _element_type(session: AsyncSession, tid: uuid.UUID, element_id) -> str | None:
    rij = (
        await session.execute(
            select(Element.element_type).where(Element.tenant_id == tid, Element.id == element_id)
        )
    ).scalar_one_or_none()
    return getattr(rij, "value", rij)


async def actieve_rollen(session: AsyncSession) -> list[dict]:
    """Actieve `beheerrol`-opties (voor de frontend rol-dropdown), gesorteerd op volgorde."""
    return (await catalog.actieve_opties_per_dimensie(session)).get(_DIM.value, [])


async def maak_aan(session: AsyncSession, tenant_id, partij_id, object_id, rol: str) -> dict:
    tid = _tenant_uuid(tenant_id)
    # Bron moet een partij-element zijn (niet-bestaand of ander type ⇒ 422, geen lek).
    if await _element_type(session, tid, partij_id) != ElementType.partij.value:
        raise OngeldigeRegistratie("ONGELDIGE_BRON", "De toewijzing moet vanuit een partij gebeuren.")
    # Doel moet een component of contract zijn.
    if await _element_type(session, tid, object_id) not in _OBJECT_TYPES:
        raise OngeldigeRegistratie(
            "ONGELDIG_DOEL", "Een rol kan alleen aan een component of contract worden toegewezen."
        )
    # Rol moet een actieve beheerrol-optie zijn.
    if rol not in await catalog.actieve_sleutels(session, _DIM):
        raise OngeldigeRegistratie("ONGELDIGE_ROL", "De gekozen rol is onbekend of niet actief.")

    obj = Roltoewijzing(tenant_id=tid, partij_id=partij_id, object_id=object_id, rol=rol)
    session.add(obj)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise RegistratieConflict(
            "TOEWIJZING_BESTAAT", "Deze partij heeft deze rol al op dit object."
        ) from exc
    await session.commit()
    await session.refresh(obj)
    return await _lees_een(session, obj)


async def verwijder(session: AsyncSession, tenant_id, toewijzing_id) -> None:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Roltoewijzing).where(
                Roltoewijzing.id == toewijzing_id, Roltoewijzing.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, toewijzing_id)
    await session.delete(obj)
    await session.commit()


async def _lees_een(session: AsyncSession, obj: Roltoewijzing) -> dict:
    """Verrijk één zojuist aangemaakte toewijzing (beide zijden gevuld) voor de respons."""
    rol_labels = await catalog.labels(session, _DIM)
    tid = obj.tenant_id
    partij = (
        await session.execute(
            select(Partij.naam, Partij.aard).where(Partij.id == obj.partij_id, Partij.tenant_id == tid)
        )
    ).first()
    object_type = await _element_type(session, tid, obj.object_id)
    object_naam = await _object_naam(session, tid, obj.object_id)
    return {
        "toewijzing_id": obj.id,
        "rol": obj.rol,
        "rol_label": catalog.resolveer_een(obj.rol, rol_labels),
        "partij_id": obj.partij_id,
        "partij_naam": partij.naam if partij else None,
        "partij_aard": getattr(partij.aard, "value", partij.aard) if partij else None,
        "object_id": obj.object_id,
        "object_naam": object_naam,
        "object_type": object_type,
    }


async def _object_naam(session: AsyncSession, tid: uuid.UUID, object_id) -> str | None:
    """Naam van het doel-object (component → naam, contract → contractnaam)."""
    naam = (
        await session.execute(
            select(Component.naam).where(Component.id == object_id, Component.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if naam is not None:
        return naam
    return (
        await session.execute(
            select(Contract.contractnaam).where(Contract.id == object_id, Contract.tenant_id == tid)
        )
    ).scalar_one_or_none()


async def lijst_voor_object(session: AsyncSession, tenant_id, object_id) -> list[dict]:
    """Alle rol-toewijzingen ván partijen óp dit object (component/contract). Geeft per regel de
    partij-naam/-aard + rol-label terug, gesorteerd op rol-label dan partij-naam."""
    tid = _tenant_uuid(tenant_id)
    rol_labels = await catalog.labels(session, _DIM)
    rijen = (
        await session.execute(
            select(
                Roltoewijzing.id.label("toewijzing_id"),
                Roltoewijzing.rol.label("rol"),
                Roltoewijzing.partij_id.label("partij_id"),
                Partij.naam.label("partij_naam"),
                Partij.aard.label("partij_aard"),
            )
            .join(Partij, Partij.id == Roltoewijzing.partij_id)
            .where(Roltoewijzing.tenant_id == tid, Roltoewijzing.object_id == object_id)
            .order_by(Roltoewijzing.rol, Partij.naam, Roltoewijzing.id)
        )
    ).all()
    return [
        {
            "toewijzing_id": r.toewijzing_id,
            "rol": r.rol,
            "rol_label": catalog.resolveer_een(r.rol, rol_labels),
            "partij_id": r.partij_id,
            "partij_naam": r.partij_naam,
            "partij_aard": getattr(r.partij_aard, "value", r.partij_aard),
        }
        for r in rijen
    ]


async def lijst_voor_partij(session: AsyncSession, tenant_id, partij_id) -> list[dict]:
    """Alle objecten (component/contract) waarop deze partij een rol heeft. Geeft per regel de
    object-naam/-type + rol-label terug, gesorteerd op object-naam dan rol."""
    tid = _tenant_uuid(tenant_id)
    rol_labels = await catalog.labels(session, _DIM)
    object_naam = func.coalesce(Component.naam, Contract.contractnaam).label("object_naam")
    rijen = (
        await session.execute(
            select(
                Roltoewijzing.id.label("toewijzing_id"),
                Roltoewijzing.rol.label("rol"),
                Roltoewijzing.object_id.label("object_id"),
                Element.element_type.label("object_type"),
                object_naam,
            )
            .join(Element, (Element.tenant_id == Roltoewijzing.tenant_id) & (Element.id == Roltoewijzing.object_id))
            .outerjoin(Component, Component.id == Roltoewijzing.object_id)
            .outerjoin(Contract, Contract.id == Roltoewijzing.object_id)
            .where(Roltoewijzing.tenant_id == tid, Roltoewijzing.partij_id == partij_id)
            .order_by(object_naam, Roltoewijzing.rol, Roltoewijzing.id)
        )
    ).all()
    return [
        {
            "toewijzing_id": r.toewijzing_id,
            "rol": r.rol,
            "rol_label": catalog.resolveer_een(r.rol, rol_labels),
            "object_id": r.object_id,
            "object_naam": r.object_naam,
            "object_type": getattr(r.object_type, "value", r.object_type),
        }
        for r in rijen
    ]
