"""HTTP-routes — Deliverable + realisatieketen (ADR-023 Fase E, E3).

Dunne handlers; RBAC via `vereist_permissie(Entiteit.DELIVERABLE, …)`. CRUD + het leggen/
ontkoppelen van de realisatieketen (work_package → deliverable → plateau, via `realization`)
+ read-traversals. Koppelingen zijn expliciet en optioneel (Besluit 8).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.deliverable import (
    DeliverableCreate,
    DeliverableKeten,
    DeliverablePagina,
    DeliverableRead,
    DeliverableUpdate,
    KoppelPlateau,
    KoppelWerkpakket,
    RealisatieKoppeling,
    WerkpakketKeten,
)
from services import deliverable_service as svc

router = APIRouter(prefix="/deliverables", tags=["bwb:deliverable"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=DeliverablePagina)
async def lijst_deliverables(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DELIVERABLE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    try:
        items, volgende = await svc.lijst(session, user.tenant_id, limit=limit, after=after)
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.post("", response_model=DeliverableRead, status_code=201)
async def maak_deliverable(
    body: DeliverableCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DELIVERABLE, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.get("/realisatieketen/{work_package_id}", response_model=WerkpakketKeten)
async def realisatieketen(
    work_package_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DELIVERABLE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Read-traversal vanaf een werkpakket → deliverables → gerealiseerde plateaus.
    Statisch subpad vóór `/{deliverable_id}`."""
    return await svc.realisatieketen_van_werkpakket(session, user.tenant_id, work_package_id)


@router.get("/{deliverable_id}", response_model=DeliverableRead)
async def haal_deliverable(
    deliverable_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DELIVERABLE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lees_detail(session, user.tenant_id, deliverable_id)


@router.get("/{deliverable_id}/keten", response_model=DeliverableKeten)
async def keten(
    deliverable_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DELIVERABLE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.keten_van_deliverable(session, user.tenant_id, deliverable_id)


@router.patch("/{deliverable_id}", response_model=DeliverableRead)
async def werk_deliverable_bij(
    deliverable_id: uuid.UUID,
    body: DeliverableUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DELIVERABLE, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, deliverable_id, body)


@router.delete("/{deliverable_id}", status_code=204)
async def verwijder_deliverable(
    deliverable_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DELIVERABLE, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, deliverable_id)
    return Response(status_code=204)


# ── Ketenkoppelingen (realization) ───────────────────────────────────────────────

@router.post("/{deliverable_id}/werkpakketten", response_model=RealisatieKoppeling, status_code=201)
async def koppel_werkpakket(
    deliverable_id: uuid.UUID,
    body: KoppelWerkpakket,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DELIVERABLE, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.koppel_werkpakket(session, user.tenant_id, deliverable_id, body.work_package_id)


@router.delete("/{deliverable_id}/werkpakketten/{relatie_id}", status_code=204)
async def ontkoppel_werkpakket(
    deliverable_id: uuid.UUID,
    relatie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DELIVERABLE, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.ontkoppel_werkpakket(session, user.tenant_id, deliverable_id, relatie_id)
    return Response(status_code=204)


@router.post("/{deliverable_id}/plateaus", response_model=RealisatieKoppeling, status_code=201)
async def koppel_plateau(
    deliverable_id: uuid.UUID,
    body: KoppelPlateau,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DELIVERABLE, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.koppel_plateau(session, user.tenant_id, deliverable_id, body.plateau_id)


@router.delete("/{deliverable_id}/plateaus/{relatie_id}", status_code=204)
async def ontkoppel_plateau(
    deliverable_id: uuid.UUID,
    relatie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.DELIVERABLE, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.ontkoppel_plateau(session, user.tenant_id, deliverable_id, relatie_id)
    return Response(status_code=204)
