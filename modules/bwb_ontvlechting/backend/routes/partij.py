"""HTTP-routes voor het partij-beheer (ADR-024 slice 2a; vervangt routes/externe_partij).

Eén beheerpad voor alle aarden onder `/partijen`, met een optioneel `?aard=`-filter. Dunne
handlers: autorisatie via `vereist_permissie(Entiteit.PARTIJ, …)`, tenant-sessie via
`get_tenant_session` (RLS), business-logica in de service. Foutgedrag conform de
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
from models.models import PartijAard
from schemas.partij import (
    PartijCreate,
    PartijPagina,
    PartijRead,
    PartijSorteerveld,
    PartijUpdate,
)
from services import partij_service as svc
from services import partijsoort_catalog
from services.pagination import Sorteerrichting

router = APIRouter(prefix="/partijen", tags=["bwb:partij"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("/soorten")
async def lijst_soorten(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PARTIJ, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """ADR-024 — actieve partijsoorten voor het optionele soort-dropdown."""
    return await partijsoort_catalog.actieve_opties(session)


@router.get("", response_model=PartijPagina)
async def lijst_partijen(
    aard: PartijAard | None = Query(None),
    aard_in: list[PartijAard] | None = Query(None),
    organisatie_id: uuid.UUID | None = Query(None),
    afdeling_id: uuid.UUID | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    sort: PartijSorteerveld = Query(PartijSorteerveld.created_at),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    zoek: str | None = Query(None, max_length=255),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PARTIJ, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    try:
        items, volgende = await svc.lijst(
            session, user.tenant_id,
            aard=aard, aard_in=aard_in, organisatie_id=organisatie_id, afdeling_id=afdeling_id,
            limit=limit, after=after, sort=sort.value, order=order.value, zoek=zoek,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.get("/{partij_id}", response_model=PartijRead)
async def haal_partij(
    partij_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PARTIJ, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.haal_op(session, user.tenant_id, partij_id)


@router.post("", response_model=PartijRead, status_code=201)
async def maak_partij(
    body: PartijCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PARTIJ, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.patch("/{partij_id}", response_model=PartijRead)
async def werk_partij_bij(
    partij_id: uuid.UUID,
    body: PartijUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PARTIJ, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, partij_id, body)


@router.delete("/{partij_id}", status_code=204)
async def verwijder_partij(
    partij_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PARTIJ, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, partij_id)
    return Response(status_code=204)
