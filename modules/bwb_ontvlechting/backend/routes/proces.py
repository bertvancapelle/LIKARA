"""HTTP-routes — Proces (ADR-042 slice 1).

Dunne handlers; RBAC via `vereist_permissie(Entiteit.PROCES, …)`. CRUD + verplaatsen
(ouder wijzigen, met server-side cycluspreventie) + een subboom-lees-traversal.
Statische subpaden vóór de dynamische `/{proces_id}` (route-volgorde-norm).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.proces import (
    ProcesBoomItem,
    ProcesCreate,
    ProcesPagina,
    ProcesRead,
    ProcesSorteerveld,
    ProcesUpdate,
)
from services import proces_service as svc
from services.pagination import Sorteerrichting

router = APIRouter(prefix="/processen", tags=["bwb:proces"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=ProcesPagina)
async def lijst_processen(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    sort: ProcesSorteerveld = Query(ProcesSorteerveld.created_at),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    zoek: str | None = Query(None, max_length=255),
    ouder_id: uuid.UUID | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PROCES, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    try:
        items, volgende = await svc.lijst(
            session, user.tenant_id, limit=limit, after=after,
            sort=sort.value, order=order.value, zoek=zoek, ouder_id=ouder_id,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.post("", response_model=ProcesRead, status_code=201)
async def maak_proces(
    body: ProcesCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PROCES, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.get("/{proces_id}", response_model=ProcesRead)
async def haal_proces(
    proces_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PROCES, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lees_detail(session, user.tenant_id, proces_id)


@router.get("/{proces_id}/subboom", response_model=list[ProcesBoomItem])
async def subboom(
    proces_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PROCES, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Read-only subboom (deelprocessen op alle niveaus, met niveau + pad)."""
    return await svc.subboom(session, user.tenant_id, proces_id)


@router.patch("/{proces_id}", response_model=ProcesRead)
async def werk_proces_bij(
    proces_id: uuid.UUID,
    body: ProcesUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PROCES, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, proces_id, body)


@router.delete("/{proces_id}", status_code=204)
async def verwijder_proces(
    proces_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PROCES, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, proces_id)
    return Response(status_code=204)
