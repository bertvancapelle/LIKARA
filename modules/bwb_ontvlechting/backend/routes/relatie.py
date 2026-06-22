"""HTTP-routes — unified relatiemodel (ADR-023 Fase B).

Tenant-scoped CRUD. Integriteit schema-afgedwongen; service valideert endpoints
(404), relatietype (422 `ONGELDIGE_OPTIE`), kenmerken (422 `ONGELDIG_KENMERK`),
zelfverwijzing (422 `ZELFVERWIJZING`), duplicaat (409 `RELATIE_BESTAAT`).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.relatie import RelatieCreate, RelatiePagina, RelatieRead, RelatieUpdate
from services import relatie_service as svc

router = APIRouter(prefix="/relaties", tags=["bwb:relatie"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=RelatiePagina)
async def lijst_relaties(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    bron_id: uuid.UUID | None = Query(None),
    doel_id: uuid.UUID | None = Query(None),
    relatietype: str | None = Query(None, max_length=40),
    paar_bron_id: uuid.UUID | None = Query(None),
    paar_doel_id: uuid.UUID | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.RELATIE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    try:
        items, volgende = await svc.lijst(
            session, user.tenant_id, limit=limit, after=after,
            bron_id=bron_id, doel_id=doel_id, relatietype=relatietype,
            paar_bron_id=paar_bron_id, paar_doel_id=paar_doel_id,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.post("", response_model=RelatieRead, status_code=201)
async def maak_relatie(
    body: RelatieCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.RELATIE, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.get("/wezen")
async def lijst_wezen(
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.RELATIE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """ADR-023 Besluit 13 — elementen zonder énige relatie (wezen). Statisch pad
    vóór `/{relatie_id}` (geen UUID-parse op 'wezen')."""
    return {"items": await svc.wezen(session, user.tenant_id)}


@router.get("/{relatie_id}", response_model=RelatieRead)
async def haal_relatie(
    relatie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.RELATIE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.haal_op(session, user.tenant_id, relatie_id)


@router.patch("/{relatie_id}", response_model=RelatieRead)
async def werk_relatie_bij(
    relatie_id: uuid.UUID,
    body: RelatieUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.RELATIE, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, relatie_id, body)


@router.delete("/{relatie_id}", status_code=204)
async def verwijder_relatie(
    relatie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.RELATIE, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, relatie_id)
    return Response(status_code=204)
