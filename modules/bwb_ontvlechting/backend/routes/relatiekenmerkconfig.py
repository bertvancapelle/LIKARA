"""Platform-beheer-endpoints — relatie-kenmerk-catalogus (ADR-023 Fase F / F-4).

Geautoriseerd via `vereist_platform_permissie(RELATIEKENMERKCONFIG, …)` (platform-rollen) op
`get_platform_session` (cd_platform, géén tenant-/RLS-context). Beheert referentiedata
(`relatiekenmerk_optie`, dimensies dispositie/relatie_rol); raakt de tenant-data NIET.
Géén DELETE (soft-deactivate via `actief`). Spiegel van `routes/componentconfig`.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.platform_rbac import PlatformEntiteit
from app.core.rbac import Actie
from app.middleware.authz import vereist_platform_permissie
from app.middleware.tenant import get_platform_session
from models.models import RelatieKenmerkDimensie
from schemas.relatiekenmerkconfig import (
    RelatieKenmerkOptieCreate,
    RelatieKenmerkOptieRead,
    RelatieKenmerkOptieUpdate,
)
from services import relatiekenmerkconfig_service as svc

router = APIRouter(prefix="/platform/relatiekenmerkconfig", tags=["platform:relatiekenmerkconfig"])

_LEZEN = vereist_platform_permissie(PlatformEntiteit.RELATIEKENMERKCONFIG, Actie.LEZEN)
_AANMAKEN = vereist_platform_permissie(PlatformEntiteit.RELATIEKENMERKCONFIG, Actie.AANMAKEN)
_WIJZIGEN = vereist_platform_permissie(PlatformEntiteit.RELATIEKENMERKCONFIG, Actie.WIJZIGEN)


@router.get("", response_model=list[RelatieKenmerkOptieRead])
async def lijst(
    dimensie: RelatieKenmerkDimensie | None = Query(None),
    _user=Depends(_LEZEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Alle catalogus-opties (incl. inactieve), optioneel per `?dimensie=`."""
    return await svc.lijst(session, dimensie.value if dimensie else None)


@router.post("", response_model=RelatieKenmerkOptieRead, status_code=201)
async def voeg_toe(
    body: RelatieKenmerkOptieCreate,
    _user=Depends(_AANMAKEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Voeg een optie toe; duplicaat `(dimensie, optie_sleutel)` ⇒ 409."""
    return await svc.voeg_toe(session, body)


@router.patch("/{optie_id}", response_model=RelatieKenmerkOptieRead)
async def wijzig(
    optie_id: int,
    body: RelatieKenmerkOptieUpdate,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Wijzig label/volgorde/actief; deactiveren én reactiveren vrij toegestaan
    (geen beschermde sleutel). Onbekend id ⇒ 404."""
    return await svc.wijzig(session, optie_id, body)
