"""Platform-beheer-endpoints — applicatiefunctie-catalogus (platform-laag, ADR-042 slice 2).

Geautoriseerd via `vereist_platform_permissie(APPLICATIEFUNCTIECONFIG, …)` (platform-rollen)
op `get_platform_session` (lk_platform). Beheert `applicatiefunctie_optie`; raakt tenant-data
NIET. Géén DELETE (soft-deactivate via `actief`). Spiegel van `routes/componentrolconfig`.
Het beheerscherm volgt in ADR-042 slice 4.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.platform_rbac import PlatformEntiteit
from app.core.rbac import Actie
from app.middleware.authz import vereist_platform_permissie
from app.middleware.tenant import get_platform_session
from schemas.applicatiefunctieconfig import (
    ApplicatiefunctieOptieCreate,
    ApplicatiefunctieOptieRead,
    ApplicatiefunctieOptieUpdate,
)
from services import applicatiefunctieconfig_service as svc

router = APIRouter(prefix="/platform/applicatiefunctieconfig", tags=["platform:applicatiefunctieconfig"])

_LEZEN = vereist_platform_permissie(PlatformEntiteit.APPLICATIEFUNCTIECONFIG, Actie.LEZEN)
_AANMAKEN = vereist_platform_permissie(PlatformEntiteit.APPLICATIEFUNCTIECONFIG, Actie.AANMAKEN)
_WIJZIGEN = vereist_platform_permissie(PlatformEntiteit.APPLICATIEFUNCTIECONFIG, Actie.WIJZIGEN)


@router.get("", response_model=list[ApplicatiefunctieOptieRead])
async def lijst(_user=Depends(_LEZEN), session: AsyncSession = Depends(get_platform_session)):
    """Alle applicatiefunctie-opties (incl. inactieve)."""
    return await svc.lijst(session)


@router.post("", response_model=ApplicatiefunctieOptieRead, status_code=201)
async def voeg_toe(
    body: ApplicatiefunctieOptieCreate,
    _user=Depends(_AANMAKEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Voeg een applicatiefunctie-optie toe; duplicaat `optie_sleutel` ⇒ 409."""
    return await svc.voeg_toe(session, body)


@router.patch("/{optie_id}", response_model=ApplicatiefunctieOptieRead)
async def wijzig(
    optie_id: int,
    body: ApplicatiefunctieOptieUpdate,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Wijzig label/volgorde/actief (geen systeem-sleutel — alles deactiveerbaar).
    Onbekend id ⇒ 404."""
    return await svc.wijzig(session, optie_id, body)
