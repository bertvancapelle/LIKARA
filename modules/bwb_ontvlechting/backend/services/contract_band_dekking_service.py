"""Service — ADR-030: per-band (component↔contract) dekking, náást de contract-brede dekking
(`ContractDekking`). Geen lifecycle-raakvlak (geen engine-borging). Array-opslag: één rij per
(contract, component) in `contract_band_dekking`. Sleutels gevalideerd tegen de catalogus-dimensie
`dekking` (app-side; 422 `ONGELDIGE_OPTIE`).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Component,
    Contract,
    ContractBandDekking,
    ContractConfigDimensie,
    ContractDekking,
)
from services import contractconfig_catalog as catalog
from services.errors import NietGevonden

_DEK = ContractConfigDimensie.dekking


def _uuid(v) -> uuid.UUID:
    return v if isinstance(v, uuid.UUID) else uuid.UUID(str(v))


def _bouw_respons(breed_sleutels: list[str], band_sleutels: list[str] | None,
                  labels_map: dict[str, tuple[str, bool]]) -> dict:
    """Pure opbouw van de band-dekking-respons (labels voor weergave; `toon_per_band` op de sleutels).

    - geen band-dekking (`band_sleutels is None`) → `per_band=None`, `toon_per_band=False`;
    - band == contract-breed → `toon_per_band=False` (geen herhaling tonen);
    - band ≠ contract-breed → `toon_per_band=True`.
    """
    def lbl(ss):
        return [labels_map.get(s, (s, False))[0] for s in ss]
    return {
        "contract_breed": lbl(breed_sleutels),
        "per_band": lbl(band_sleutels) if band_sleutels is not None else None,
        "per_band_sleutels": band_sleutels,
        "toon_per_band": band_sleutels is not None and set(band_sleutels) != set(breed_sleutels),
    }


async def _bestaat(session: AsyncSession, tid: uuid.UUID, model, _id: uuid.UUID) -> bool:
    return (
        await session.execute(select(model.id).where(model.tenant_id == tid, model.id == _id))
    ).first() is not None


async def haal_band_dekking_op(session: AsyncSession, tenant_id, contract_id, component_id) -> dict:
    """Contract-brede dekking (labels) + per-band dekking (labels + sleutels) + `toon_per_band`."""
    tid, cid, kid = _uuid(tenant_id), _uuid(contract_id), _uuid(component_id)
    breed = sorted((
        await session.execute(
            select(ContractDekking.optie_sleutel).where(
                ContractDekking.tenant_id == tid, ContractDekking.contract_id == cid
            )
        )
    ).scalars().all())
    rij = (
        await session.execute(
            select(ContractBandDekking.dekking_sleutels).where(
                ContractBandDekking.tenant_id == tid,
                ContractBandDekking.contract_id == cid,
                ContractBandDekking.component_id == kid,
            )
        )
    ).scalar_one_or_none()
    band = sorted(rij) if rij is not None else None
    labels_map = await catalog.labels(session, _DEK)
    return _bouw_respons(breed, band, labels_map)


async def stel_band_dekking_in(session: AsyncSession, tenant_id, contract_id, component_id,
                               dekking_sleutels: list[str]) -> None:
    """Upsert de band-dekking. 404 als contract/component niet bestaan; 422 bij ongeldige sleutel."""
    tid, cid, kid = _uuid(tenant_id), _uuid(contract_id), _uuid(component_id)
    if not await _bestaat(session, tid, Contract, cid):
        raise NietGevonden("contract", contract_id)
    if not await _bestaat(session, tid, Component, kid):
        raise NietGevonden("component", component_id)
    sleutels = sorted(set(dekking_sleutels or []))
    await catalog.valideer_sleutels(session, _DEK, sleutels)  # 422 ONGELDIGE_OPTIE
    # LI035 — ORM-upsert (select → setattr/add) i.p.v. de eerdere core-upsert
    # (insert…on_conflict): de centrale audit-capture (flush-hook) ziet alléén
    # ORM-mutaties; met de core-variant landde een dekking-wijziging nooit in de
    # trail (audit-gat). De UNIQUE-constraint blijft de backstop tegen races.
    bestaand = (
        await session.execute(
            select(ContractBandDekking).where(
                ContractBandDekking.tenant_id == tid,
                ContractBandDekking.contract_id == cid,
                ContractBandDekking.component_id == kid,
            )
        )
    ).scalar_one_or_none()
    if bestaand is not None:
        bestaand.dekking_sleutels = sleutels
    else:
        session.add(ContractBandDekking(
            tenant_id=tid, contract_id=cid, component_id=kid, dekking_sleutels=sleutels,
        ))
    await session.commit()


async def verwijder_band_dekking(session: AsyncSession, tenant_id, contract_id, component_id) -> None:
    """Verwijder de band-dekking (terug naar contract-brede dekking). Idempotent."""
    tid, cid, kid = _uuid(tenant_id), _uuid(contract_id), _uuid(component_id)
    # LI035 — ORM-delete i.p.v. core delete (zelfde audit-reden als bij `stel_band_dekking_in`).
    obj = (
        await session.execute(
            select(ContractBandDekking).where(
                ContractBandDekking.tenant_id == tid,
                ContractBandDekking.contract_id == cid,
                ContractBandDekking.component_id == kid,
            )
        )
    ).scalar_one_or_none()
    if obj is not None:
        await session.delete(obj)
    await session.commit()
