"""HTTP-routes voor de entiteit Leverancier (ADR-020 fase B).

Dunne handlers: autorisatie via `vereist_permissie(Entiteit.LEVERANCIER, …)`,
tenant-sessie via `get_tenant_session` (RLS), business-logica in de service.
Foutgedrag conform de module-conventie (401/403/404/409-envelope; 422 native;
400 `ONGELDIGE_CURSOR`).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.leverancier import (
    LeverancierCreate,
    LeverancierPagina,
    LeverancierRead,
    LeverancierSorteerveld,
    LeverancierUpdate,
)
from services import leverancier_service as svc
from services.pagination import Sorteerrichting

router = APIRouter(prefix="/leveranciers", tags=["bwb:leverancier"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=LeverancierPagina)
async def lijst_leveranciers(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    sort: LeverancierSorteerveld = Query(LeverancierSorteerveld.created_at),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    zoek: str | None = Query(None, max_length=255),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.LEVERANCIER, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    try:
        items, volgende = await svc.lijst(
            session, user.tenant_id,
            limit=limit, after=after, sort=sort.value, order=order.value, zoek=zoek,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.get("/{leverancier_id}", response_model=LeverancierRead)
async def haal_leverancier(
    leverancier_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.LEVERANCIER, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.haal_op(session, user.tenant_id, leverancier_id)


@router.post("", response_model=LeverancierRead, status_code=201)
async def maak_leverancier(
    body: LeverancierCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.LEVERANCIER, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.patch("/{leverancier_id}", response_model=LeverancierRead)
async def werk_leverancier_bij(
    leverancier_id: uuid.UUID,
    body: LeverancierUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.LEVERANCIER, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, leverancier_id, body)


@router.delete("/{leverancier_id}", status_code=204)
async def verwijder_leverancier(
    leverancier_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.LEVERANCIER, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, leverancier_id)
    return Response(status_code=204)
