"""HTTP-routes — Plateau + plateau-lidmaatschap (ADR-023 Fase E, E1).

Dunne handlers; RBAC via `vereist_permissie(Entiteit.PLATEAU, …)`. CRUD op het plateau
zelf + leden toevoegen/wijzigen/verwijderen (dispositie + contractuele bevestiging).
Lidmaatschap loopt onder water via het unified relatiemodel (aggregation).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.plateau import (
    PlateauCreate,
    PlateauLidCreate,
    PlateauLidRead,
    PlateauLidUpdate,
    PlateauPagina,
    PlateauRead,
    PlateauUpdate,
)
from services import plateau_service as svc

router = APIRouter(prefix="/plateaus", tags=["bwb:plateau"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=PlateauPagina)
async def lijst_plateaus(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    zoek: str | None = Query(None, max_length=255),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PLATEAU, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    try:
        items, volgende = await svc.lijst(session, user.tenant_id, limit=limit, after=after, zoek=zoek)
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.post("", response_model=PlateauRead, status_code=201)
async def maak_plateau(
    body: PlateauCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PLATEAU, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.get("/disposities")
async def lijst_disposities(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PLATEAU, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Actieve `dispositie`-opties voor het lid-koppel-dropdown (statisch subpad vóór /{id})."""
    return await svc.actieve_disposities(session)


@router.get("/{plateau_id}", response_model=PlateauRead)
async def haal_plateau(
    plateau_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PLATEAU, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lees_detail(session, user.tenant_id, plateau_id)


@router.patch("/{plateau_id}", response_model=PlateauRead)
async def werk_plateau_bij(
    plateau_id: uuid.UUID,
    body: PlateauUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PLATEAU, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, plateau_id, body)


@router.delete("/{plateau_id}", status_code=204)
async def verwijder_plateau(
    plateau_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PLATEAU, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, plateau_id)
    return Response(status_code=204)


# ── Leden (dispositie + contractuele bevestiging) ────────────────────────────────

@router.get("/{plateau_id}/leden", response_model=list[PlateauLidRead])
async def lijst_leden(
    plateau_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PLATEAU, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lijst_leden(session, user.tenant_id, plateau_id)


@router.post("/{plateau_id}/leden", response_model=PlateauLidRead, status_code=201)
async def voeg_lid_toe(
    plateau_id: uuid.UUID,
    body: PlateauLidCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PLATEAU, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_lid(session, user.tenant_id, plateau_id, body)


@router.patch("/{plateau_id}/leden/{lid_relatie_id}", response_model=PlateauLidRead)
async def werk_lid_bij(
    plateau_id: uuid.UUID,
    lid_relatie_id: uuid.UUID,
    body: PlateauLidUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PLATEAU, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_lid_bij(session, user.tenant_id, plateau_id, lid_relatie_id, body)


@router.delete("/{plateau_id}/leden/{lid_relatie_id}", status_code=204)
async def verwijder_lid(
    plateau_id: uuid.UUID,
    lid_relatie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PLATEAU, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder_lid(session, user.tenant_id, plateau_id, lid_relatie_id)
    return Response(status_code=204)
