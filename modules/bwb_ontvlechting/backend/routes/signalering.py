"""HTTP-routes — Signalering registratiegaten (ADR-035, Slice 1).

Read-only inzichtlaag, los van de bestaande plaatsingssignalen (`/signalen`). Het centrale
overzicht is tenant-breed inzicht → `vereist_permissie(ARCHITECTUUR, LEZEN)` (hergebruik, geen
nieuwe entiteit). De badge volgt het object → `COMPONENT, LEZEN`. Engine onaangeroerd; geen
schema/migratie; bewust geen paginering (begrensd afgeleid overzicht).
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.signalering import BadgeRead
from services import registratiegaten_service as svc

router = APIRouter(prefix="/signalering", tags=["bwb:signalering"])


@router.get("/registratiegaten")
async def lijst_registratiegaten(
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.ARCHITECTUUR, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Alle actieve registratiegaten, gegroepeerd per ernst (kritiek/aandacht). Read-only."""
    return await svc.registratiegaten(session, user.tenant_id)


@router.get("/badges/component/{component_id}", response_model=BadgeRead)
async def badge_component(
    component_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Badge-info (signalen + tellingen) voor één component. Read-only."""
    return await svc.badge_voor_component(session, user.tenant_id, component_id)
