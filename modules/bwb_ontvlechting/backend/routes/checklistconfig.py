"""Platform-beheer-endpoints — checklist-antwoordconfiguratie (ADR-019 fase 2D,
ADR-012 Addendum A).

Geautoriseerd via `vereist_platform_permissie(CHECKLISTCONFIG, …)` (platform-rollen)
op `get_platform_session` (cd_platform, géén tenant-/RLS-context). Beheert
referentiedata (`checklistvraag.antwoordtype` + `checklistvraag_optie`); raakt het
score-/lifecycle-/blokkade-pad NIET.

Foutgedrag: 401 · 403 `ONVOLDOENDE_RECHTEN` · 404 `NIET_GEVONDEN` · 409
`CONFIGURATIE_CONFLICT` (orphan-/afgeleid-/uniciteitsregels) · 422 (Pydantic).
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.platform_rbac import PlatformEntiteit
from app.core.rbac import Actie
from app.middleware.authz import vereist_platform_permissie
from app.middleware.tenant import get_platform_session
from schemas.checklistconfig import (
    AntwoordTypeUpdate,
    ConfigOptieRead,
    ConfigVraagRead,
    OptieCreate,
    OptieUpdate,
)
from services import checklistconfig_service as svc

router = APIRouter(prefix="/platform/checklistconfig", tags=["platform:checklistconfig"])

_LEZEN = vereist_platform_permissie(PlatformEntiteit.CHECKLISTCONFIG, Actie.LEZEN)
_AANMAKEN = vereist_platform_permissie(PlatformEntiteit.CHECKLISTCONFIG, Actie.AANMAKEN)
_WIJZIGEN = vereist_platform_permissie(PlatformEntiteit.CHECKLISTCONFIG, Actie.WIJZIGEN)


@router.get("", response_model=list[ConfigVraagRead])
async def lijst_config(
    _user=Depends(_LEZEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Alle vragen + antwoordtype + ALLE opties (incl. inactieve, met afgeleid_bron)."""
    return await svc.lijst_config(session)


@router.patch("/vragen/{vraag_code}", response_model=ConfigVraagRead)
async def zet_antwoordtype(
    vraag_code: str,
    body: AntwoordTypeUpdate,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Zet het antwoordtype (alleen vanuit `geen` — orphan-bescherming)."""
    return await svc.zet_antwoordtype(session, vraag_code, body)


@router.post("/vragen/{vraag_code}/opties", response_model=ConfigOptieRead, status_code=201)
async def voeg_optie_toe(
    vraag_code: str,
    body: OptieCreate,
    _user=Depends(_AANMAKEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Voeg een optie toe (niet-afgeleide vraag; stabiele, unieke sleutel)."""
    return await svc.voeg_optie_toe(session, vraag_code, body)


@router.patch("/opties/{optie_id}", response_model=ConfigOptieRead)
async def wijzig_optie(
    optie_id: uuid.UUID,
    body: OptieUpdate,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Wijzig label en/of volgorde (afgeleide optie: alleen label)."""
    return await svc.wijzig_optie(session, optie_id, body)


@router.post("/opties/{optie_id}/deactiveren", response_model=ConfigOptieRead)
async def deactiveer_optie(
    optie_id: uuid.UUID,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Soft-deactiveer een optie (`actief=false`; geen hard delete)."""
    return await svc.deactiveer_optie(session, optie_id)
