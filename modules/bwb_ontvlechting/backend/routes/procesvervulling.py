"""HTTP-routes — procesvervulling (ADR-042 slice 3).

Dunne handlers; RBAC via een eigen `Entiteit.PROCESVERVULLING` (_INHOUD-patroon —
ADR-042 "Gevolgen": nieuwe entiteiten; anders dan roltoewijzing, dat op PARTIJ meelift,
heeft de koppelregel géén eenduidige "bron"-kant om op mee te liften). Verbreken van een
regel guardt — zoals bij roltoewijzing — op WIJZIGEN: het opheffen van een registratie-
feit is registratiebeheer (medewerker-werk), geen verwijdering van een inhouds-object.
Route-volgorde: statisch `/functies` vóór de dynamische `/{vervulling_id}`.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.procesvervulling import (
    ProcesvervullingAanmaken,
    ProcesvervullingUit,
    ProcesvervullingWijzigen,
)
from services import procesvervulling_service as svc

router = APIRouter(prefix="/procesvervullingen", tags=["bwb:procesvervulling"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("/functies")
async def lijst_functies(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PROCESVERVULLING, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Actieve applicatiefunctie-opties voor het keuze-dropdown."""
    return await svc.actieve_functies(session)


@router.get("", response_model=list[ProcesvervullingUit])
async def lijst_procesvervullingen(
    proces_id: uuid.UUID | None = Query(None),
    component_id: uuid.UUID | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PROCESVERVULLING, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Koppelregels van één proces (`?proces_id=`) óf van één component (`?component_id=`).
    Precies één van beide is verplicht."""
    if (proces_id is None) == (component_id is None):
        return _fout(422, "FILTER_VEREIST", "Geef precies één van proces_id of component_id op.")
    if proces_id is not None:
        return await svc.lijst_voor_proces(session, user.tenant_id, proces_id)
    return await svc.lijst_voor_component(session, user.tenant_id, component_id)


@router.post("", response_model=ProcesvervullingUit, status_code=201)
async def maak_procesvervulling(
    body: ProcesvervullingAanmaken,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PROCESVERVULLING, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(
        session, user.tenant_id, body.component_id, body.proces_id,
        body.applicatiefunctie, body.toelichting,
    )


@router.patch("/{vervulling_id}", response_model=ProcesvervullingUit)
async def werk_procesvervulling_bij(
    vervulling_id: uuid.UUID,
    body: ProcesvervullingWijzigen,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PROCESVERVULLING, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Wijzig de kenmerk-velden (applicatiefunctie/toelichting); de ankers
    component/proces zijn onwijzigbaar (regel-acties-patroon)."""
    return await svc.werk_bij(session, user.tenant_id, vervulling_id, body)


@router.delete("/{vervulling_id}", status_code=204)
async def verwijder_procesvervulling(
    vervulling_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PROCESVERVULLING, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, vervulling_id)
    return Response(status_code=204)
