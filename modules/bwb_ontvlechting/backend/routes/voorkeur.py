"""HTTP-routes — persoonlijke gebruikersvoorkeuren (ADR-041 slice 1).

Eigen registratie-feit → eigen routebestand (`/voorkeuren`). RBAC via de eigen entiteit
`GEBRUIKER_VOORKEUR` (elke tenant-rol beheert zijn eigen voorkeuren). De eigen-scope ("alleen je eigen
`sub`") leeft server-side in de service. Dunne handlers.

De `voorkeur_sleutel` reist via het pad met een strikte vorm (`^[a-z][a-z0-9_]*$`, ≤100) → een
ongeldige sleutel geeft native FastAPI-422 vóór de service.
"""
from fastapi import APIRouter, Depends, Path, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.voorkeur import VoorkeurRead, VoorkeurUpsert
from services import voorkeur_service as svc

router = APIRouter(prefix="/voorkeuren", tags=["bwb:voorkeur"])

_SLEUTEL = Path(..., min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$",
                description="Voorkeur-sleutel, bv. 'gebruikte_componenttypen'.")


@router.get("", response_model=list[VoorkeurRead])
async def lijst_voorkeuren(
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKER_VOORKEUR, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Alle voorkeuren van de HUIDIGE gebruiker (nooit die van een ander)."""
    return await svc.lijst_eigen(session, user.tenant_id)


@router.put("/{sleutel}", response_model=VoorkeurRead)
async def zet_voorkeur(
    body: VoorkeurUpsert,
    sleutel: str = _SLEUTEL,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKER_VOORKEUR, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Zet (aanmaken of vervangen) de eigen voorkeur `sleutel`."""
    return await svc.upsert(session, user.tenant_id, sleutel, body.waarde)


@router.delete("/{sleutel}", status_code=204)
async def herroep_voorkeur(
    sleutel: str = _SLEUTEL,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKER_VOORKEUR, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Herroep de eigen voorkeur `sleutel` (idempotent → altijd 204, terug naar baseline)."""
    await svc.verwijder(session, user.tenant_id, sleutel)
    return Response(status_code=204)
