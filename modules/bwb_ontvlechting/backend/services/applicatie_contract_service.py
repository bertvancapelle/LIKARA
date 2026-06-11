"""Service-laag voor de koppeltabel ApplicatieContract (ADR-020 Besluit 5).

Tenant-scoped; applicatie/contract worden bij aanmaken tenant-scoped geresolved
(404 buiten de tenant). `relatie_rol` wordt tegen de actieve catalogus-dimensie
`relatie_rol` gevalideerd (422 `ONGELDIGE_OPTIE`). Een dubbele `(applicatie, contract)`
⇒ 409 `KOPPELING_BESTAAT` (nette app-fout vóór het UNIQUE-constraint).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Applicatie,
    ApplicatieContract,
    Contract,
    ContractConfigDimensie,
    Leverancier,
)
from schemas.applicatie_contract import (
    ApplicatieContractCreate,
    ApplicatieContractUpdate,
)
from services import applicatie_service, contract_service
from services import contractconfig_catalog as catalog
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict

_ENTITEIT = "applicatie_contract"


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def haal_op(session: AsyncSession, tenant_id, koppeling_id) -> ApplicatieContract:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(ApplicatieContract).where(
                ApplicatieContract.id == koppeling_id, ApplicatieContract.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, koppeling_id)
    return obj


async def _lees(session: AsyncSession, tenant_id, obj: ApplicatieContract) -> dict:
    rol_labels = await catalog.labels(session, ContractConfigDimensie.relatie_rol)
    return {
        "id": obj.id,
        "applicatie_id": obj.applicatie_id,
        "contract_id": obj.contract_id,
        "relatie_rol": obj.relatie_rol,
        "relatie_rol_label": catalog.resolveer_een(obj.relatie_rol, rol_labels),
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


async def maak_aan(session: AsyncSession, tenant_id, data: ApplicatieContractCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    # Beide kanten tenant-scoped valideren (ontbrekend/kruis-tenant ⇒ 404).
    await applicatie_service.haal_op(session, tenant_id, data.applicatie_id)
    await contract_service.haal_op(session, tenant_id, data.contract_id)
    await catalog.valideer_sleutels(session, ContractConfigDimensie.relatie_rol, [data.relatie_rol])

    bestaat = (
        await session.execute(
            select(ApplicatieContract.id).where(
                ApplicatieContract.tenant_id == tid,
                ApplicatieContract.applicatie_id == data.applicatie_id,
                ApplicatieContract.contract_id == data.contract_id,
            )
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise RegistratieConflict(
            "KOPPELING_BESTAAT", "Deze applicatie is al aan dit contract gekoppeld."
        )

    obj = ApplicatieContract(tenant_id=tid, **data.model_dump())
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError as exc:  # backstop voor het UNIQUE-constraint
        await session.rollback()
        raise RegistratieConflict(
            "KOPPELING_BESTAAT", "Deze applicatie is al aan dit contract gekoppeld."
        ) from exc
    await session.refresh(obj)
    return await _lees(session, tenant_id, obj)


async def werk_bij(session: AsyncSession, tenant_id, koppeling_id, data: ApplicatieContractUpdate) -> dict:
    obj = await haal_op(session, tenant_id, koppeling_id)
    await catalog.valideer_sleutels(session, ContractConfigDimensie.relatie_rol, [data.relatie_rol])
    obj.relatie_rol = data.relatie_rol
    await session.commit()
    await session.refresh(obj)
    return await _lees(session, tenant_id, obj)


async def verwijder(session: AsyncSession, tenant_id, koppeling_id) -> None:
    obj = await haal_op(session, tenant_id, koppeling_id)
    await session.delete(obj)
    await session.commit()


async def contracten_van_applicatie(session: AsyncSession, tenant_id, applicatie_id) -> list[dict]:
    """'App → waar valt hij onder': gekoppelde contracten (met rol + leverancier).
    Applicatie onbekend ⇒ 404."""
    tid = _tenant_uuid(tenant_id)
    await applicatie_service.haal_op(session, tenant_id, applicatie_id)
    rol_labels = await catalog.labels(session, ContractConfigDimensie.relatie_rol)
    rijen = (
        await session.execute(
            select(
                ApplicatieContract.id.label("koppeling_id"),
                Contract.id.label("contract_id"),
                Contract.contractnaam.label("contractnaam"),
                Contract.contracttype.label("contracttype"),
                Contract.leverancier_id.label("leverancier_id"),
                Leverancier.naam.label("leverancier_naam"),
                ApplicatieContract.relatie_rol.label("relatie_rol"),
            )
            .join(Contract, Contract.id == ApplicatieContract.contract_id)
            .join(Leverancier, Leverancier.id == Contract.leverancier_id)
            .where(ApplicatieContract.tenant_id == tid, ApplicatieContract.applicatie_id == applicatie_id)
            .order_by(Contract.contractnaam, ApplicatieContract.id)
        )
    ).all()
    return [
        {
            "koppeling_id": r.koppeling_id,
            "contract_id": r.contract_id,
            "contractnaam": r.contractnaam,
            "contracttype": r.contracttype,
            "leverancier_id": r.leverancier_id,
            "leverancier_naam": r.leverancier_naam,
            "relatie_rol": r.relatie_rol,
            "relatie_rol_label": catalog.resolveer_een(r.relatie_rol, rol_labels),
        }
        for r in rijen
    ]
