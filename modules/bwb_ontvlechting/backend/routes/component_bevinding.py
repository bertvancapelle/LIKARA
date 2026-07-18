"""HTTP-routes — component-bevinding "bewust geen" (ADR-052 slice 2).

Eigen registratie-feit (eigen tabel/service). RBAC via `Entiteit.COMPONENT_BEVINDING`
(_INHOUD-patroon; registratie-feit — ADR-050). Registreren = AANMAKEN (medewerker+); intrekken
guardt op `verwijder_actie(COMPONENT_BEVINDING)` = WIJZIGEN (de medewerker neemt zijn eigen
uitspraak terug). Dunne handlers; logica in de service. `component_id`/`soort` reizen via het pad.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.rbac import Actie, Entiteit, verwijder_actie
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.component_bevinding import BevindingCreate, BevindingRead
from services import component_bevinding_service as svc

router = APIRouter(prefix="/component-bevindingen", tags=["bwb:component-bevinding"])


@router.get("/component/{component_id}", response_model=list[BevindingRead])
async def lijst_bevindingen(
    component_id: uuid.UUID,
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_BEVINDING, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """De 'bewust geen'-bevindingen van één component (0–2)."""
    return await svc.lijst_voor_component(session, _user.tenant_id, component_id)


@router.post("/component/{component_id}", response_model=BevindingRead, status_code=201)
async def registreer_bevinding(
    component_id: uuid.UUID,
    body: BevindingCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_BEVINDING, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Leg vast: "dit component heeft bewust geen <soort>." 409 bij een echte registratie of dubbel."""
    return await svc.registreer_geen(
        session, user.tenant_id, component_id, body.soort, body.toelichting
    )


@router.delete("/component/{component_id}/{soort}", status_code=204)
async def trek_bevinding_in(
    component_id: uuid.UUID,
    soort: str,
    user: AuthenticatedUser = Depends(
        vereist_permissie(Entiteit.COMPONENT_BEVINDING, verwijder_actie(Entiteit.COMPONENT_BEVINDING))
    ),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Trek de bevinding in (ADR-050: registratie-feit → WIJZIGEN — de medewerker neemt zijn
    uitspraak terug). De feit-toets valt daarna terug op 'nog niet vastgesteld' (tenzij er intussen
    een echte koppeling/contract is)."""
    await svc.verwijder(session, user.tenant_id, component_id, soort)
    return Response(status_code=204)
