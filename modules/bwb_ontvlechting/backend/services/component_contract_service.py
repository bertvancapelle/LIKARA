"""Service-laag voor component↔contract-koppeling (ADR-021 Besluit 7; ADR-023).

ADR-023 B-mig-2 slice 3: de koppeling leeft nu als **association**-relatie in het unified
relatiemodel (`Relatie`: bron=component, doel=contract, `relatie_rol` als kenmerk). Deze
service is een domeinspecifieke facade over `Relatie` — de route/het schema/dev_seed blijven
ongewijzigd. Component + contract tenant-scoped resolven (404); `relatie_rol` tegen de
catalogus-dimensie `relatie_rol`; dubbele `(component, contract)` ⇒ 409 `KOPPELING_BESTAAT`.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Contract, ContractConfigDimensie, Leverancier, Relatie
from schemas.component_contract import ComponentContractCreate, ComponentContractUpdate
from services import component_service, contract_service
from services import contractconfig_catalog as catalog
from services.errors import NietGevonden, RegistratieConflict

_ENTITEIT = "component_contract"
_ASSOCIATION = "association"


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def haal_op(session: AsyncSession, tenant_id, koppeling_id) -> Relatie:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Relatie).where(
                Relatie.id == koppeling_id, Relatie.tenant_id == tid,
                Relatie.relatietype == _ASSOCIATION,
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, koppeling_id)
    return obj


async def _lees(session: AsyncSession, obj: Relatie) -> dict:
    rol_labels = await catalog.labels(session, ContractConfigDimensie.relatie_rol)
    rol = (obj.kenmerken or {}).get("relatie_rol")
    return {
        "id": obj.id,
        "component_id": obj.bron_id,
        "contract_id": obj.doel_id,
        "relatie_rol": rol,
        "relatie_rol_label": catalog.resolveer_een(rol, rol_labels),
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


async def maak_aan(session: AsyncSession, tenant_id, data: ComponentContractCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    await component_service.haal_op(session, tenant_id, data.component_id)  # élk type, 404 buiten tenant
    await contract_service.haal_op(session, tenant_id, data.contract_id)
    await catalog.valideer_sleutels(session, ContractConfigDimensie.relatie_rol, [data.relatie_rol])

    bestaat = (
        await session.execute(
            select(Relatie.id).where(
                Relatie.tenant_id == tid, Relatie.bron_id == data.component_id,
                Relatie.doel_id == data.contract_id, Relatie.relatietype == _ASSOCIATION,
            )
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise RegistratieConflict("KOPPELING_BESTAAT", "Dit component is al aan dit contract gekoppeld.")

    obj = Relatie(
        tenant_id=tid, bron_id=data.component_id, doel_id=data.contract_id,
        relatietype=_ASSOCIATION, kenmerken={"relatie_rol": data.relatie_rol},
    )
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise RegistratieConflict("KOPPELING_BESTAAT", "Dit component is al aan dit contract gekoppeld.") from exc
    await session.refresh(obj)
    return await _lees(session, obj)


async def werk_bij(session: AsyncSession, tenant_id, koppeling_id, data: ComponentContractUpdate) -> dict:
    obj = await haal_op(session, tenant_id, koppeling_id)
    await catalog.valideer_sleutels(session, ContractConfigDimensie.relatie_rol, [data.relatie_rol])
    obj.kenmerken = {**(obj.kenmerken or {}), "relatie_rol": data.relatie_rol}
    await session.commit()
    await session.refresh(obj)
    return await _lees(session, obj)


async def verwijder(session: AsyncSession, tenant_id, koppeling_id) -> None:
    obj = await haal_op(session, tenant_id, koppeling_id)
    await session.delete(obj)
    await session.commit()


async def contracten_van_component(session: AsyncSession, tenant_id, component_id) -> list[dict]:
    """'Component → contracten': gekoppelde contracten (met rol + leverancier) via de
    association-relaties. Component onbekend ⇒ 404."""
    tid = _tenant_uuid(tenant_id)
    await component_service.haal_op(session, tenant_id, component_id)
    rol_labels = await catalog.labels(session, ContractConfigDimensie.relatie_rol)
    rijen = (
        await session.execute(
            select(
                Relatie.id.label("koppeling_id"),
                Contract.id.label("contract_id"),
                Contract.contractnaam.label("contractnaam"),
                Contract.contracttype.label("contracttype"),
                Contract.leverancier_id.label("leverancier_id"),
                Leverancier.naam.label("leverancier_naam"),
                Contract.begindatum.label("begindatum"),
                Contract.einddatum.label("einddatum"),
                Relatie.kenmerken.label("kenmerken"),
            )
            .join(Contract, Contract.id == Relatie.doel_id)
            .join(Leverancier, Leverancier.id == Contract.leverancier_id)
            .where(
                Relatie.tenant_id == tid, Relatie.bron_id == component_id,
                Relatie.relatietype == _ASSOCIATION,
            )
            .order_by(Contract.contractnaam, Relatie.id)
        )
    ).all()
    return [
        {
            "koppeling_id": r.koppeling_id, "contract_id": r.contract_id,
            "contractnaam": r.contractnaam, "contracttype": r.contracttype,
            "leverancier_id": r.leverancier_id, "leverancier_naam": r.leverancier_naam,
            "begindatum": r.begindatum, "einddatum": r.einddatum,
            "relatie_rol": (r.kenmerken or {}).get("relatie_rol"),
            "relatie_rol_label": catalog.resolveer_een((r.kenmerken or {}).get("relatie_rol"), rol_labels),
        }
        for r in rijen
    ]
