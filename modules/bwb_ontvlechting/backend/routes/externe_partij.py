"""HTTP-routes voor het externe-partij-beheer (ADR-024 slice 1). Vervangt routes/leverancier.

Dunne handlers: autorisatie via `vereist_permissie(Entiteit.EXTERNE_PARTIJ, …)`, tenant-sessie
via `get_tenant_session` (RLS), business-logica in de service. Foutgedrag conform de
module-conventie (401/403/404/409-envelope; 422 native; 400 `ONGELDIGE_CURSOR`).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.externe_partij import (
    ExternePartijCreate,
    ExternePartijPagina,
    ExternePartijRead,
    ExternePartijSorteerveld,
    ExternePartijUpdate,
)
from services import externe_partij_service as svc
from services import partijsoort_catalog
from services.pagination import Sorteerrichting

router = APIRouter(prefix="/externe-partijen", tags=["bwb:externe_partij"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("/soorten")
async def lijst_soorten(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.EXTERNE_PARTIJ, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """ADR-024 — actieve partijsoorten voor het optionele soort-dropdown."""
    return await partijsoort_catalog.actieve_opties(session)


@router.get("", response_model=ExternePartijPagina)
async def lijst_externe_partijen(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    sort: ExternePartijSorteerveld = Query(ExternePartijSorteerveld.created_at),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    zoek: str | None = Query(None, max_length=255),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.EXTERNE_PARTIJ, Actie.LEZEN)),
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


@router.get("/{partij_id}", response_model=ExternePartijRead)
async def haal_externe_partij(
    partij_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.EXTERNE_PARTIJ, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.haal_op(session, user.tenant_id, partij_id)


@router.post("", response_model=ExternePartijRead, status_code=201)
async def maak_externe_partij(
    body: ExternePartijCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.EXTERNE_PARTIJ, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.patch("/{partij_id}", response_model=ExternePartijRead)
async def werk_externe_partij_bij(
    partij_id: uuid.UUID,
    body: ExternePartijUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.EXTERNE_PARTIJ, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, partij_id, body)


@router.delete("/{partij_id}", status_code=204)
async def verwijder_externe_partij(
    partij_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.EXTERNE_PARTIJ, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, partij_id)
    return Response(status_code=204)
