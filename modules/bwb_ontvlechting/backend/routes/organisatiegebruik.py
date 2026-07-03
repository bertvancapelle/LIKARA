"""HTTP-routes voor het grove gebruiksfeit `organisatiegebruik` (ADR-036, stap A).

Dunne handlers. Read = per applicatie (`?applicatie_id=`); losse aanmaak van een feit (409 bij
duplicaat); delete. Geen PATCH — het feit ís (organisatie, applicatie) = zijn identiteit; beheer
loopt via aanmaak/verwijderen (net als `roltoewijzing`)."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.organisatiegebruik import OrganisatiegebruikCreate, OrganisatiegebruikRead
from services import organisatiegebruik_service as svc

router = APIRouter(prefix="/organisatiegebruik", tags=["bwb:organisatiegebruik"])


@router.get("", response_model=list[OrganisatiegebruikRead])
async def lijst_organisatiegebruik(
    applicatie_id: uuid.UUID = Query(...),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.ORGANISATIEGEBRUIK, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """De grove gebruiksfeiten van één applicatie (welke organisaties gebruiken haar) — met
    organisatie-naam en of er een verfijning (afdeling) onder hangt. Begrensde afgeleide lijst
    (bewust geen keyset) — zie service."""
    return await svc.lijst_voor_applicatie(session, user.tenant_id, applicatie_id)


@router.post("", response_model=OrganisatiegebruikRead, status_code=201)
async def maak_organisatiegebruik(
    body: OrganisatiegebruikCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.ORGANISATIEGEBRUIK, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Leg een grof gebruiksfeit vast (organisatie gebruikt applicatie). Onvolledig = geldig;
    bestaand (organisatie, applicatie) ⇒ 409 `GEBRUIK_BESTAAT`."""
    return await svc.maak_aan(session, user.tenant_id, body)


@router.delete("/{gebruik_id}", status_code=204)
async def verwijder_organisatiegebruik(
    gebruik_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.ORGANISATIEGEBRUIK, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Verwijder een grof feit. Onderliggende groepen worden organisatie-loos (ON DELETE SET NULL)."""
    await svc.verwijder(session, user.tenant_id, gebruik_id)
    return Response(status_code=204)
