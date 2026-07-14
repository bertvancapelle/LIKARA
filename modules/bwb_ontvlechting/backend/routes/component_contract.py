"""HTTP-routes voor ComponentContract (ADR-021 Besluit 7 — Fase B).

RBAC via `Entiteit.COMPONENT_CONTRACT` (de contract-koppeling generaliseerde naar
component-niveau, ADR-021 Fase D). Het component→contracten-overzicht hangt aan de
component-router (`/componenten/{id}/contracten`). De oude `/applicatie-contracten`-paden
zijn vervallen (CD054 padconsolidatie) — de frontend gebruikt uitsluitend deze paden.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.rbac import Actie, Entiteit, verwijder_actie
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.component_contract import (
    ComponentContractCreate,
    ComponentContractRead,
    ComponentContractUpdate,
)
from services import component_contract_service as svc

router = APIRouter(prefix="/component-contracten", tags=["bwb:component-contract"])


@router.post("", response_model=ComponentContractRead, status_code=201)
async def maak_koppeling(
    body: ComponentContractCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_CONTRACT, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.patch("/{koppeling_id}", response_model=ComponentContractRead)
async def werk_koppeling_bij(
    koppeling_id: uuid.UUID,
    body: ComponentContractUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_CONTRACT, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, koppeling_id, body)


@router.delete("/{koppeling_id}", status_code=204)
async def verwijder_koppeling(
    koppeling_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_CONTRACT, verwijder_actie(Entiteit.COMPONENT_CONTRACT))),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, koppeling_id)
    return Response(status_code=204)
