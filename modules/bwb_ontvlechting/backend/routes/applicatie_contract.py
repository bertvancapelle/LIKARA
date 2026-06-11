"""HTTP-routes voor de koppeling ApplicatieContract (ADR-020 fase B).

Eén router zonder vaste prefix (volle paden), zodat zowel de koppeling-CRUD
(`/applicatie-contracten`) als de twee overzichten (`/applicaties/{id}/contracten`,
respectievelijk `/contracten/{id}/applicaties` — die laatste in de contract-router)
netjes onder hun eigen resource-pad vallen.

RBAC: de koppeling-CRUD valt onder `Entiteit.APPLICATIE_CONTRACT`; het app→contracten-
overzicht is een leesweergave bij de applicatie en gebruikt `Entiteit.APPLICATIE`-LEZEN.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.applicatie_contract import (
    ApplicatieContractCreate,
    ApplicatieContractRead,
    ApplicatieContractUpdate,
    ContractVoorApplicatie,
)
from services import applicatie_contract_service as svc

router = APIRouter(tags=["bwb:applicatie-contract"])


@router.get("/applicaties/{applicatie_id}/contracten", response_model=list[ContractVoorApplicatie])
async def contracten_van_applicatie(
    applicatie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.APPLICATIE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """'App → waar valt hij onder': de gekoppelde contracten (met rol + leverancier)."""
    return await svc.contracten_van_applicatie(session, user.tenant_id, applicatie_id)


@router.post("/applicatie-contracten", response_model=ApplicatieContractRead, status_code=201)
async def maak_koppeling(
    body: ApplicatieContractCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.APPLICATIE_CONTRACT, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.patch("/applicatie-contracten/{koppeling_id}", response_model=ApplicatieContractRead)
async def werk_koppeling_bij(
    koppeling_id: uuid.UUID,
    body: ApplicatieContractUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.APPLICATIE_CONTRACT, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, koppeling_id, body)


@router.delete("/applicatie-contracten/{koppeling_id}", status_code=204)
async def verwijder_koppeling(
    koppeling_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.APPLICATIE_CONTRACT, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, koppeling_id)
    return Response(status_code=204)
