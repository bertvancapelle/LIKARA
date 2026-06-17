"""Platform-beheer-endpoints — componentcatalogus (ADR-021 Besluit 8, ADR-012 Addendum C).

Geautoriseerd via `vereist_platform_permissie(COMPONENTCONFIG, …)` (platform-rollen) op
`get_platform_session` (cd_platform, géén tenant-/RLS-context). Beheert referentiedata
(`componentconfig_optie`); raakt de tenant-data NIET. Géén DELETE (Addendum C Besluit 3).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.platform_rbac import PlatformEntiteit
from app.core.rbac import Actie
from app.middleware.authz import vereist_platform_permissie
from app.middleware.tenant import get_platform_session
from models.models import ComponentConfigDimensie
from schemas.componentconfig import (
    ComponentConfigOptieCreate,
    ComponentConfigOptieRead,
    ComponentConfigOptieUpdate,
)
from services import componentconfig_service as svc
from services.archimate_typing import (
    TOEGESTANE_ASPECTEN,
    TOEGESTANE_ELEMENTEN,
    TOEGESTANE_LAGEN,
)

router = APIRouter(prefix="/platform/componentconfig", tags=["platform:componentconfig"])

_LEZEN = vereist_platform_permissie(PlatformEntiteit.COMPONENTCONFIG, Actie.LEZEN)
_AANMAKEN = vereist_platform_permissie(PlatformEntiteit.COMPONENTCONFIG, Actie.AANMAKEN)
_WIJZIGEN = vereist_platform_permissie(PlatformEntiteit.COMPONENTCONFIG, Actie.WIJZIGEN)


@router.get("/typering-opties")
async def typering_opties(_user=Depends(_LEZEN)):
    """ADR-026 — de gesloten keuzelijsten voor de ArchiMate-typering van een componenttype.
    Enige bron = `services/archimate_typing` (de frontend hardcodeert de lijsten niet)."""
    return {
        "elementen": sorted(TOEGESTANE_ELEMENTEN),
        "lagen": sorted(TOEGESTANE_LAGEN),
        "aspecten": sorted(TOEGESTANE_ASPECTEN),
    }


@router.get("", response_model=list[ComponentConfigOptieRead])
async def lijst(
    dimensie: ComponentConfigDimensie | None = Query(None),
    _user=Depends(_LEZEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Alle catalogus-opties (incl. inactieve), optioneel per `?dimensie=`."""
    return await svc.lijst(session, dimensie.value if dimensie else None)


@router.post("", response_model=ComponentConfigOptieRead, status_code=201)
async def voeg_toe(
    body: ComponentConfigOptieCreate,
    _user=Depends(_AANMAKEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Voeg een optie toe; duplicaat `(dimensie, optie_sleutel)` ⇒ 409."""
    return await svc.voeg_toe(session, body)


@router.patch("/{optie_id}", response_model=ComponentConfigOptieRead)
async def wijzig(
    optie_id: int,
    body: ComponentConfigOptieUpdate,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Wijzig label/volgorde/actief; deactiveren én reactiveren toegestaan, behalve op de
    systeem-sleutel `componenttype.applicatie` (422 `SYSTEEM_SLEUTEL_BESCHERMD`)."""
    return await svc.wijzig(session, optie_id, body)
