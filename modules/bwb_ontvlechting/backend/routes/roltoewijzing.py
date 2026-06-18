"""HTTP-routes voor rol-toewijzing (ADR-024 slice 2b).

Eigen routebestand (`/roltoewijzingen`) — los van `partij.py`, omdat een toewijzing een eigen
registratie-feit is (eigen tabel/service), niet een partij-attribuut. RBAC hergebruikt de
`PARTIJ`-rechten (besluit 5): lezen = PARTIJ·LEZEN; toevoegen/verwijderen = PARTIJ·WIJZIGEN
(aanmaken/verwijderen van een toewijzing is een wijziging aan het partijenregister, geen nieuw
partij-record → WIJZIGEN i.p.v. AANMAKEN). Dunne handlers; business-logica in de service.
Foutgedrag conform de module-conventie (401/403/404/409-envelope; 422 native of envelope).

Route-volgorde: statisch `/rollen` vóór de dynamische `/{toewijzing_id}`.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.roltoewijzing import RoltoewijzingAanmaken, RoltoewijzingUit
from services import roltoewijzing_service as svc

router = APIRouter(prefix="/roltoewijzingen", tags=["bwb:roltoewijzing"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("/rollen")
async def lijst_rollen(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PARTIJ, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Actieve `beheerrol`-opties voor het rol-dropdown."""
    return await svc.actieve_rollen(session)


@router.get("", response_model=list[RoltoewijzingUit])
async def lijst_roltoewijzingen(
    object_id: uuid.UUID | None = Query(None),
    partij_id: uuid.UUID | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PARTIJ, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Toewijzingen van één object (`?object_id=`) óf van één partij (`?partij_id=`). Precies één
    van beide is verplicht."""
    if (object_id is None) == (partij_id is None):
        return _fout(422, "FILTER_VEREIST", "Geef precies één van object_id of partij_id op.")
    if object_id is not None:
        return await svc.lijst_voor_object(session, user.tenant_id, object_id)
    return await svc.lijst_voor_partij(session, user.tenant_id, partij_id)


@router.post("", response_model=RoltoewijzingUit, status_code=201)
async def maak_roltoewijzing(
    body: RoltoewijzingAanmaken,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PARTIJ, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body.partij_id, body.object_id, body.rol)


@router.delete("/{toewijzing_id}", status_code=204)
async def verwijder_roltoewijzing(
    toewijzing_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.PARTIJ, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, toewijzing_id)
    return Response(status_code=204)
