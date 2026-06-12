"""HTTP-routes voor de entiteit Blokkade (ADR-009/010/013).

Afwijkend CRUD: blokkades zijn systeem-afgeleid → alléén `GET` (lijst + id) en
`PATCH`. Geen `POST`/`DELETE` (auto-creatie via Checklistscore + DB-cascade).

Foutgedrag: 401 · 403 `ONVOLDOENDE_RECHTEN` · 404 `NIET_GEVONDEN` ·
400 `ONGELDIGE_CURSOR` · 422 (Pydantic). POST/DELETE ⇒ 405 (niet ondersteund).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from models.models import BlokkadeStatus
from schemas.blokkade import (
    BlokkadeLijstSorteerveld,
    BlokkadeOpties,
    BlokkadeOverzichtPagina,
    BlokkadePagina,
    BlokkadeRead,
    BlokkadeSorteerveld,
    BlokkadeStatusFilter,
    BlokkadeUpdate,
)
from services import blokkade_service as svc
from services.pagination import Sorteerrichting

router = APIRouter(prefix="/blokkades", tags=["bwb:blokkade"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    """Canoniek foutformaat — geen stacktraces of architectuurdetails."""
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=BlokkadePagina)
async def lijst_blokkades(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    component_id: uuid.UUID | None = Query(None),
    status: BlokkadeStatus | None = Query(None),
    sort: BlokkadeLijstSorteerveld = Query(BlokkadeLijstSorteerveld.created_at),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BLOKKADE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Per-applicatie blokkade-lijst (ADR-017 + CD020). `sort`/`order` additief;
    weglaten = `created_at` oplopend (pre-CD020-gedrag). Onbekend sorteerveld/
    ongeldige richting ⇒ 422; cursor-mismatch ⇒ 400 `ONGELDIGE_CURSOR`. Het
    tenant-brede `/overzicht` is een aparte route en blijft ongemoeid."""
    try:
        items, volgende = await svc.lijst(
            session,
            user.tenant_id,
            limit=limit,
            after=after,
            component_id=component_id,
            status=status,
            sort=sort.value,
            order=order.value,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.get("/opties", response_model=BlokkadeOpties)
async def blokkade_opties(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BLOKKADE, Actie.LEZEN)),
):
    """Read-only keuzewaarden (status). Vóór `/{id}` (geen UUID-parse op 'opties')."""
    return svc.enum_opties()


@router.get("/overzicht", response_model=BlokkadeOverzichtPagina)
async def overzicht_blokkades(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    status: BlokkadeStatusFilter = Query(BlokkadeStatusFilter.actief),
    sort: BlokkadeSorteerveld = Query(BlokkadeSorteerveld.applicatie_naam),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BLOKKADE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Tenant-breed blokkadesoverzicht over alle applicaties (CD016, ADR-017).

    Statische route — vóór `/{blokkade_id}` zodat 'overzicht' niet als UUID wordt
    geparsed. Statusfilter (`actief` default), server-side sorteerbaar (allowlist;
    onbekend `status`/`sort`/`order` ⇒ 422), keyset-cursor (mismatch ⇒ 400).
    """
    try:
        items, volgende = await svc.lijst_overzicht(
            session,
            user.tenant_id,
            limit=limit,
            after=after,
            status_filter=status.value,
            sort=sort.value,
            order=order.value,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.get("/{blokkade_id}", response_model=BlokkadeRead)
async def haal_blokkade(
    blokkade_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BLOKKADE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.haal_op(session, user.tenant_id, blokkade_id)


@router.patch("/{blokkade_id}", response_model=BlokkadeRead)
async def werk_blokkade_bij(
    blokkade_id: uuid.UUID,
    body: BlokkadeUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BLOKKADE, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, blokkade_id, body)
