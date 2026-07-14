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
    FunctievervullingAanmaken,
    FunctievervullingUit,
    PlekDekkingUit,
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


@router.post("", response_model=FunctievervullingUit, status_code=201)
async def maak_functievervulling(
    body: FunctievervullingAanmaken,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.FUNCTIEVERVULLING, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Koppel een component aan een functie. Leeg `ouder_functie_id` = grof (geldt overal);
    gevuld = fijn (déze plek)."""
    return await svc.maak_aan(
        session, user.tenant_id, body.component_id, body.functie_id,
        body.ouder_functie_id, body.toelichting,
    )


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
