"""HTTP-routes voor de entiteit Datatype (P5-vervolg, ADR-009/010).

Dunne handlers; zelfde patroon als `routes/applicatie.py`, zonder lifecycle.
Optionele tenant-scoped lijst-filter `?applicatie_id=`.

Foutgedrag: 401 (geen sessie) · 403 `ONVOLDOENDE_RECHTEN` · 404 `NIET_GEVONDEN`
(record óf ouder buiten tenant) · 400 `ONGELDIGE_CURSOR` · 422 (Pydantic).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.datatype import (
    DatatypeCreate,
    DatatypeOpties,
    DatatypePagina,
    DatatypeRead,
    DatatypeSorteerveld,
    DatatypeUpdate,
)
from services import datatype_service as svc
from services.pagination import Sorteerrichting

router = APIRouter(prefix="/datatypes", tags=["bwb:datatype"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    """Canoniek foutformaat — geen stacktraces of architectuurdetails."""
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=DatatypePagina)
async def lijst_datatypes(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    applicatie_id: uuid.UUID | None = Query(None),
    sort: DatatypeSorteerveld = Query(DatatypeSorteerveld.created_at),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DATATYPE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Server-side sorteerbare keyset-lijst (ADR-017 + CD020). `sort`/`order`
    optioneel; weglaten = `created_at` oplopend (pre-CD020-gedrag). Onbekend
    sorteerveld/ongeldige richting ⇒ 422; cursor die niet bij `sort`/`order` past
    ⇒ 400 `ONGELDIGE_CURSOR`."""
    try:
        items, volgende = await svc.lijst(
            session,
            user.tenant_id,
            limit=limit,
            after=after,
            applicatie_id=applicatie_id,
            sort=sort.value,
            order=order.value,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.get("/opties", response_model=DatatypeOpties)
async def datatype_opties(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DATATYPE, Actie.LEZEN)),
):
    """Read-only keuzewaarden per enumveld. Vóór `/{id}` (geen UUID-parse op 'opties')."""
    return svc.enum_opties()


@router.get("/{datatype_id}", response_model=DatatypeRead)
async def haal_datatype(
    datatype_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DATATYPE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lees_detail(session, user.tenant_id, datatype_id)


@router.post("", response_model=DatatypeRead, status_code=201)
async def maak_datatype(
    body: DatatypeCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DATATYPE, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Maak een datatype; de ouder-applicatie moet binnen de tenant bestaan."""
    return await svc.maak_aan(session, user.tenant_id, body)


@router.patch("/{datatype_id}", response_model=DatatypeRead)
async def werk_datatype_bij(
    datatype_id: uuid.UUID,
    body: DatatypeUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DATATYPE, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, datatype_id, body)


@router.delete("/{datatype_id}", status_code=204)
async def verwijder_datatype(
    datatype_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DATATYPE, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, datatype_id)
    return Response(status_code=204)
