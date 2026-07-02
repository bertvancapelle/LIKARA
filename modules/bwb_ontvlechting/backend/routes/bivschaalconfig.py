"""Platform-beheer-endpoints — BIV-schaal-catalogus (platform-laag, ADR-028 slice 1).

Geautoriseerd via `vereist_platform_permissie(BIVSCHAALCONFIG, …)` (platform-rollen) op
`get_platform_session` (lk_platform). Beheert `biv_schaal_optie`; raakt tenant-data NIET.
Géén DELETE (soft-deactivate via `actief`). Spiegel van `routes/partijsoortconfig`.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.platform_rbac import PlatformEntiteit
from app.core.rbac import Actie
from app.middleware.authz import vereist_platform_permissie
from app.middleware.tenant import get_platform_session
from schemas.bivschaalconfig import (
    BivSchaalOptieCreate,
    BivSchaalOptieRead,
    BivSchaalOptieUpdate,
)
from services import bivschaalconfig_service as svc

router = APIRouter(prefix="/platform/bivschaalconfig", tags=["platform:bivschaalconfig"])

_LEZEN = vereist_platform_permissie(PlatformEntiteit.BIVSCHAALCONFIG, Actie.LEZEN)
_AANMAKEN = vereist_platform_permissie(PlatformEntiteit.BIVSCHAALCONFIG, Actie.AANMAKEN)
_WIJZIGEN = vereist_platform_permissie(PlatformEntiteit.BIVSCHAALCONFIG, Actie.WIJZIGEN)


@router.get("", response_model=list[BivSchaalOptieRead])
async def lijst(_user=Depends(_LEZEN), session: AsyncSession = Depends(get_platform_session)):
    """Alle BIV-schaal-opties (incl. inactieve), ordinaal op `volgorde`."""
    return await svc.lijst(session)


@router.post("", response_model=BivSchaalOptieRead, status_code=201)
async def voeg_toe(
    body: BivSchaalOptieCreate,
    _user=Depends(_AANMAKEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Voeg een BIV-schaal-optie toe; duplicaat `optie_sleutel` ⇒ 409."""
    return await svc.voeg_toe(session, body)


@router.patch("/{optie_id}", response_model=BivSchaalOptieRead)
async def wijzig(
    optie_id: int,
    body: BivSchaalOptieUpdate,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Wijzig label/volgorde/actief; deactiveren én reactiveren vrij. Onbekend id ⇒ 404."""
    return await svc.wijzig(session, optie_id, body)
