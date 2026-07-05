"""HTTP-routes voor het grove gebruiksfeit `organisatiegebruik` (ADR-036, stap A).

Dunne handlers. Read = per applicatie (`?applicatie_id=`); losse aanmaak van een feit (409 bij
duplicaat); delete. Geen PATCH — het feit ís (organisatie, applicatie) = zijn identiteit; beheer
loopt via aanmaak/verwijderen (net als `roltoewijzing`)."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.organisatiegebruik import (
    OrganisatieComponentRead,
    OrganisatiegebruikCreate,
    OrganisatiegebruikRead,
)
from services import organisatiegebruik_service as svc

router = APIRouter(prefix="/organisatiegebruik", tags=["bwb:organisatiegebruik"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    """Canoniek foutformaat — geen stacktraces of architectuurdetails."""
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


# response_model=None: de twee filter-takken leveren bewust verschillende vormen
# (org-centrisch vs. applicatie/component-centrisch); elke tak construeert zijn eigen
# gevalideerde schema hieronder.
@router.get("", response_model=None)
async def lijst_organisatiegebruik(
    applicatie_id: uuid.UUID | None = Query(None),
    organisatie_id: uuid.UUID | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.ORGANISATIEGEBRUIK, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Grove gebruiksfeiten, gefilterd op **precies één** van:

    - `applicatie_id` → welke **organisaties** gebruiken deze applicatie (`OrganisatiegebruikRead`,
      met organisatie-naam + of er een verfijning onder hangt);
    - `organisatie_id` → welke **applicaties** gebruikt deze organisatie (`OrganisatieComponentRead`:
      component-naam + type + `verfijnd`-vlag — grof-only incluis; gedeeld met het "Gebruikte
      applicaties"-blok én de Landschapskaart-subgraaf).

    Precies één filter vereist (geen of beide ⇒ 400 `ONGELDIGE_FILTER`). Begrensde afgeleide
    lijst (bewust geen keyset) — zie service."""
    if (applicatie_id is None) == (organisatie_id is None):
        return _fout(400, "ONGELDIGE_FILTER", "Geef precies één van applicatie_id of organisatie_id op.")
    if applicatie_id is not None:
        rijen = await svc.lijst_voor_applicatie(session, user.tenant_id, applicatie_id)
        return [OrganisatiegebruikRead.model_validate(r) for r in rijen]
    rijen = await svc.lijst_voor_organisatie(session, user.tenant_id, organisatie_id)
    return [OrganisatieComponentRead.model_validate(r) for r in rijen]


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
