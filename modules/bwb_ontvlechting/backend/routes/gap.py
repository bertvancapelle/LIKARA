"""HTTP-routes — Gap + gap-leden + readiness (ADR-023 Fase E, E4).

Dunne handlers; RBAC via `vereist_permissie(Entiteit.GAP, …)`. CRUD op de gap zelf (met de
twee verplichte plateau-referenties) + leden toevoegen/verwijderen (component/contract via
`association`). De twee gescheiden readiness-cijfers (technisch + contractueel) zitten
read-only ingebed in de gap-detail-respons — geen apart opgeslagen veld.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.gap import (
    GapCreate,
    GapDetail,
    GapLidCreate,
    GapLidRead,
    GapPagina,
    GapRead,
    GapUpdate,
)
from services import gap_service as svc

router = APIRouter(prefix="/gaps", tags=["bwb:gap"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=GapPagina)
async def lijst_gaps(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GAP, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    try:
        items, volgende = await svc.lijst(session, user.tenant_id, limit=limit, after=after)
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.post("", response_model=GapRead, status_code=201)
async def maak_gap(
    body: GapCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GAP, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.get("/{gap_id}", response_model=GapDetail)
async def haal_gap(
    gap_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GAP, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lees_detail(session, user.tenant_id, gap_id)


@router.patch("/{gap_id}", response_model=GapRead)
async def werk_gap_bij(
    gap_id: uuid.UUID,
    body: GapUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GAP, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, gap_id, body)


@router.delete("/{gap_id}", status_code=204)
async def verwijder_gap(
    gap_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GAP, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, gap_id)
    return Response(status_code=204)


# ── Leden (component/contract via association) ────────────────────────────────────

@router.get("/{gap_id}/leden", response_model=list[GapLidRead])
async def lijst_leden(
    gap_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GAP, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lijst_leden(session, user.tenant_id, gap_id)


@router.post("/{gap_id}/leden", response_model=GapLidRead, status_code=201)
async def voeg_lid_toe(
    gap_id: uuid.UUID,
    body: GapLidCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GAP, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_lid(session, user.tenant_id, gap_id, body.lid_id)


@router.delete("/{gap_id}/leden/{lid_relatie_id}", status_code=204)
async def verwijder_lid(
    gap_id: uuid.UUID,
    lid_relatie_id: uuid.UUID,
    # ADR-050 — een lidmaatschap is een registratie-feit (membership-uitspraak): de medewerker
    # die het legt, neemt het terug → WIJZIGEN (het gap-object zelf vernietigt de beheerder).
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GAP, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder_lid(session, user.tenant_id, gap_id, lid_relatie_id)
    return Response(status_code=204)
