"""Platform-beheer-endpoints — componentrol-catalogus (platform-laag, ADR-028 slice 1).

Geautoriseerd via `vereist_platform_permissie(COMPONENTROLCONFIG, …)` (platform-rollen) op
`get_platform_session` (lk_platform). Beheert `componentrol_optie`; raakt tenant-data NIET.
Géén DELETE (soft-deactivate via `actief`). Spiegel van `routes/partijsoortconfig`.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.platform_rbac import PlatformEntiteit
from app.core.rbac import Actie
from app.middleware.authz import vereist_platform_permissie
from app.middleware.tenant import get_platform_session
from schemas.componentrolconfig import (
    ComponentrolOptieCreate,
    ComponentrolOptieRead,
    ComponentrolOptieUpdate,
)
from services import componentrolconfig_service as svc

router = APIRouter(prefix="/platform/componentrolconfig", tags=["platform:componentrolconfig"])

_LEZEN = vereist_platform_permissie(PlatformEntiteit.COMPONENTROLCONFIG, Actie.LEZEN)
_AANMAKEN = vereist_platform_permissie(PlatformEntiteit.COMPONENTROLCONFIG, Actie.AANMAKEN)
_WIJZIGEN = vereist_platform_permissie(PlatformEntiteit.COMPONENTROLCONFIG, Actie.WIJZIGEN)


@router.get("", response_model=list[ComponentrolOptieRead])
async def lijst(_user=Depends(_LEZEN), session: AsyncSession = Depends(get_platform_session)):
    """Alle componentrol-opties (incl. inactieve)."""
    return await svc.lijst(session)


@router.post("", response_model=ComponentrolOptieRead, status_code=201)
async def voeg_toe(
    body: ComponentrolOptieCreate,
    _user=Depends(_AANMAKEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Voeg een componentrol-optie toe; duplicaat `optie_sleutel` ⇒ 409."""
    return await svc.voeg_toe(session, body)


@router.patch("/{optie_id}", response_model=ComponentrolOptieRead)
async def wijzig(
    optie_id: int,
    body: ComponentrolOptieUpdate,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Wijzig label/volgorde/actief. Systeem-sleutel `interne_applicatie` niet deactiveerbaar
    (⇒ 422). Onbekend id ⇒ 404."""
    return await svc.wijzig(session, optie_id, body)
