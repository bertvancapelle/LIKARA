"""HTTP-routes voor de entiteit Applicatie (P5, ADR-009/010).

Dunne handlers: autorisatie via `vereist_permissie(Entiteit.APPLICATIE, …)`,
tenant-sessie via `get_tenant_session` (RLS), business-logica in de service.

Foutgedrag:
- geen/ongeldige sessie         → 401 (auth-laag; `{"detail":{…}}`, OP-7)
- geldige sessie, te weinig recht → 403 `ONVOLDOENDE_RECHTEN`
- id buiten de tenant            → 404 `NIET_GEVONDEN` (OP-6; geen lek)
- ongeldige statusovergang       → 409 `ONGELDIGE_STATUSOVERGANG`
- ongeldige paginacursor         → 400 `ONGELDIGE_CURSOR`
- ongeldige invoer (Pydantic)    → 422 (FastAPI-validatie)
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.applicatie import (
    ApplicatieCreate,
    ApplicatiePagina,
    ApplicatieRead,
    ApplicatieUpdate,
)
from services import applicatie_service as svc

router = APIRouter(prefix="/applicaties", tags=["bwb:applicatie"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    """Canoniek foutformaat — geen stacktraces of architectuurdetails."""
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=ApplicatiePagina)
async def lijst_applicaties(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.APPLICATIE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Cursor-gepagineerde lijst binnen de tenant."""
    try:
        items, volgende = await svc.lijst(session, user.tenant_id, limit=limit, after=after)
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.get("/{applicatie_id}", response_model=ApplicatieRead)
async def haal_applicatie(
    applicatie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.APPLICATIE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Eén applicatie binnen de tenant; onbekend/ander-tenant ⇒ 404."""
    return await svc.haal_op(session, user.tenant_id, applicatie_id)


@router.post("", response_model=ApplicatieRead, status_code=201)
async def maak_applicatie(
    body: ApplicatieCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.APPLICATIE, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Maak een applicatie aan (start in lifecycle `concept`)."""
    return await svc.maak_aan(session, user.tenant_id, body)


@router.patch("/{applicatie_id}", response_model=ApplicatieRead)
async def werk_applicatie_bij(
    applicatie_id: uuid.UUID,
    body: ApplicatieUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.APPLICATIE, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Partiële update; `lifecycle_status` blijft server-beheerd."""
    return await svc.werk_bij(session, user.tenant_id, applicatie_id, body)


@router.post("/{applicatie_id}/start-inventarisatie", response_model=ApplicatieRead)
async def start_inventarisatie(
    applicatie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.APPLICATIE, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Lifecycle-overgang `concept → in_inventarisatie`; anders 409."""
    return await svc.start_inventarisatie(session, user.tenant_id, applicatie_id)


@router.delete("/{applicatie_id}", status_code=204)
async def verwijder_applicatie(
    applicatie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.APPLICATIE, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Verwijder binnen de tenant; kind-records cascaden via de DB."""
    await svc.verwijder(session, user.tenant_id, applicatie_id)
    return Response(status_code=204)
