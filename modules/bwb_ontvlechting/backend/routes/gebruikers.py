"""HTTP-routes — gebruikersbeheer (ADR-029 Fase 2).

LIKARA is de primaire ingang voor gebruikers. `POST /gebruikers` maakt persoon + Keycloak-account
+ koppelrij en geeft het tijdelijk wachtwoord éénmalig terug. RBAC via de `GEBRUIKERSBEHEER`-
entiteit (alleen Beheerder = LAWV). Dunne handlers; logica in de service.
Route-volgorde: lijst (`""`) vóór eventuele dynamische subpaden.
"""
import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.gebruiker import (
    GebruikerAangemaaktResponse,
    GebruikerAanmakenRequest,
    GebruikerCorrectieRequest,
    GebruikerPersoonRead,
    GebruikerRolWijzigRequest,
    GebruikerStatusRequest,
    GebruikerWachtwoordResponse,
)
from services import gebruiker_service as svc

router = APIRouter(prefix="/gebruikers", tags=["bwb:gebruikers"])


@router.get("", response_model=list[GebruikerPersoonRead])
async def lijst_gebruikers(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSBEHEER, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Gekoppelde gebruikers binnen de tenant (join koppelrij ↔ persoon), gesorteerd op naam."""
    items, _volgende = await svc.lijst_gebruikers(session, user.tenant_id, limit=limit, after=after)
    return items


@router.post("", response_model=GebruikerAangemaaktResponse, status_code=201)
async def maak_gebruiker(
    body: GebruikerAanmakenRequest,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSBEHEER, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Maak een gebruiker aan (persoon + Keycloak-account + koppeling). Geeft het tijdelijk
    wachtwoord éénmalig terug — beheerder communiceert het, het wordt niet opgeslagen/gelogd."""
    gebruiker, wachtwoord = await svc.maak_gebruiker(
        session, user.tenant_id, naam=body.naam, email=body.email,
        afdeling_id=body.afdeling_id, functietitel=body.functietitel, rol=body.rol,
    )
    return GebruikerAangemaaktResponse(gebruiker=gebruiker, tijdelijk_wachtwoord=wachtwoord)


# ── ADR-029 Fase 2b — beheeracties op een bestaande gebruiker (alleen Beheerder, WIJZIGEN) ──

@router.post("/{gebruiker_id}/wachtwoord-reset", response_model=GebruikerWachtwoordResponse)
async def reset_wachtwoord(
    gebruiker_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSBEHEER, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Nieuw eenmalig wachtwoord (verplicht wijzigen bij eerste login); één keer getoond."""
    wachtwoord = await svc.reset_wachtwoord(session, user.tenant_id, gebruiker_id)
    return GebruikerWachtwoordResponse(tijdelijk_wachtwoord=wachtwoord)


@router.patch("/{gebruiker_id}/rol", status_code=204)
async def wijzig_rol(
    gebruiker_id: uuid.UUID,
    body: GebruikerRolWijzigRequest,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSBEHEER, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Rol wijzigen (viewer/medewerker/beheerder/auditor). Guards: eigen beheerrol + laatste beheerder."""
    await svc.wijzig_rol(session, user.tenant_id, gebruiker_id, body.rol)
    return Response(status_code=204)


@router.patch("/{gebruiker_id}/status", status_code=204)
async def wijzig_status(
    gebruiker_id: uuid.UUID,
    body: GebruikerStatusRequest,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSBEHEER, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """In-/uitschakelen (nooit verwijderen); bij uitschakelen wordt de sessie direct afgekapt."""
    await svc.zet_actief(session, user.tenant_id, gebruiker_id, body.actief)
    return Response(status_code=204)


@router.patch("/{gebruiker_id}", response_model=GebruikerPersoonRead)
async def corrigeer_gegevens(
    gebruiker_id: uuid.UUID,
    body: GebruikerCorrectieRequest,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSBEHEER, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Naam/e-mail (+ optioneel afdeling/organisatie) corrigeren op de persoon-partij én het
    Keycloak-account (naam/e-mail)."""
    return await svc.corrigeer_gegevens(
        session, user.tenant_id, gebruiker_id,
        naam=body.naam, email=body.email, afdeling_id=body.afdeling_id,
    )
