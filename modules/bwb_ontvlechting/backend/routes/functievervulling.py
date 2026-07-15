"""HTTP-routes — functievervulling (ADR-049, gate 2a).

Dunne handlers; RBAC via een eigen `Entiteit.FUNCTIEVERVULLING` (_INHOUD-patroon — de koppelregel
heeft geen eenduidige "bron"-kant om op mee te liften, net als procesvervulling). ANDERS dan
procesvervulling guardt het verwijderen hier op VERWIJDEREN (beheerder), niet op WIJZIGEN
(opdracht gate 2a §4/§6.7: destructief = beheerder). Route-volgorde: statisch `/dekking` vóór
de dynamische `/{vervulling_id}`.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.rbac import Actie, Entiteit, verwijder_actie
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.functievervulling import (
    ComponentKoppelingUit,
    FunctievervullingAanmaken,
    FunctievervullingUit,
    GeenSysteemAanmaken,
    OordeelWijzigen,
    PlekDekkingUit,
    PlekStandenUit,
)
from services import functievervulling_service as svc

router = APIRouter(prefix="/functievervullingen", tags=["bwb:functievervulling"])


@router.get("/dekking", response_model=list[PlekDekkingUit])
async def dekking(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.FUNCTIEVERVULLING, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """De leesregel per plek: "welke componenten dragen déze plek" (fijn verdringt grof)."""
    return await svc.dekking_overzicht(session, _user.tenant_id)


@router.get("/standen", response_model=PlekStandenUit)
async def standen(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.FUNCTIEVERVULLING, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """ADR-051 — de vier standen per plek + de gedeelde tellers (één afleiding, twee vensters)."""
    return await svc.plek_standen(session, _user.tenant_id)


@router.get("/component/{component_id}", response_model=list[ComponentKoppelingUit])
async def component_koppelingen(
    component_id: uuid.UUID,
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.FUNCTIEVERVULLING, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """ADR-043 gate 4 (G2) — "waarvoor dient dit systeem": de koppelingen van één component,
    gelezen uit de gedeelde leesregel (fijn verdringt grof), her-geïndexeerd op het component."""
    return await svc.overzicht_voor_component(session, _user.tenant_id, component_id)


@router.post("", response_model=FunctievervullingUit, status_code=201)
async def maak_functievervulling(
    body: FunctievervullingAanmaken,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.FUNCTIEVERVULLING, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Koppel een component aan een functie. Leeg `ouder_functie_id` = grof (geldt overal);
    gevuld = fijn (déze plek). Optioneel `oordeel` (naar_behoren/noodoplossing)."""
    return await svc.maak_aan(
        session, user.tenant_id, body.component_id, body.functie_id,
        body.ouder_functie_id, body.toelichting, body.oordeel,
    )


@router.post("/geen-systeem", response_model=FunctievervullingUit, status_code=201)
async def registreer_geen_systeem(
    body: GeenSysteemAanmaken,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.FUNCTIEVERVULLING, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """ADR-051 besluit 2 — leg vast: "hier draait geen systeem — vastgesteld" (een bevinding)."""
    return await svc.registreer_geen_systeem(
        session, user.tenant_id, body.functie_id, body.ouder_functie_id, body.toelichting,
    )


@router.patch("/{vervulling_id}/oordeel", response_model=FunctievervullingUit)
async def wijzig_oordeel(
    vervulling_id: uuid.UUID,
    body: OordeelWijzigen,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.FUNCTIEVERVULLING, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """ADR-051 besluit 3/4 — zet of wis het oordeel op een koppeling (registratie-feit → WIJZIGEN)."""
    return await svc.zet_oordeel(session, user.tenant_id, vervulling_id, body.oordeel)


@router.delete("/{vervulling_id}", status_code=204)
async def verwijder_functievervulling(
    vervulling_id: uuid.UUID,
    user: AuthenticatedUser = Depends(
        vereist_permissie(Entiteit.FUNCTIEVERVULLING, verwijder_actie(Entiteit.FUNCTIEVERVULLING))
    ),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Verwijder een koppeling. ADR-050: een koppeling is een registratie-feit — de medewerker
    die 'm legt, neemt 'm terug (WIJZIGEN). Een fijne koppeling weghalen maakt het grove
    antwoord op die plek weer leesbaar — er wordt nooit iets weggeschreven."""
    await svc.verwijder(session, user.tenant_id, vervulling_id)
    return Response(status_code=204)
