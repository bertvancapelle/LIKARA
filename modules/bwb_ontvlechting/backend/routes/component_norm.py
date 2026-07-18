"""HTTP-routes — tenant-norm harde feiten: de per-component "is dit vastgesteld?"-status
(ADR-052 slice 3). RBAC via `Entiteit.COMPONENT_NORM` (LEZEN — iedereen mag de norm-status zien;
de norm bepaalt "compleet"). Dunne handler; logica in `component_norm_service`.

Deze status is de LIVE leesbron voor de klaarverklaring-dialog én het "N verplichte feiten
open"-badge — één norm-definitie, tegen de actuele veldwaarden (badge = nu; de bevroren snapshot
leeft op de klaarverklaring zelf).
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from services import component_norm_service as svc

router = APIRouter(prefix="/component-normen", tags=["bwb:component-norm"])


@router.get("/status/{component_id}")
async def norm_status(
    component_id: uuid.UUID,
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_NORM, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Per VERPLICHT feit de vastgesteld-status voor dit component ({feiten: {feit: status}}).
    Live afleiding; component buiten de tenant ⇒ lege `feiten` (geen lek)."""
    return await svc.norm_status(session, _user.tenant_id, component_id)


# ── ADR-052 besluiten 8-11 (LI045) — de verschoven lat onderscheiden van de bewuste afwijking ─────
# Statisch subpad vóór de dynamische `/{...}`-paden.
@router.get("/verschoven-lat")
async def verschoven_lat(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.ARCHITECTUUR, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Werkvoorraad: per verplicht gesteld feit de klaar-verklaarde componenten waar de lat
    verschoof (feit nu verplicht+open, maar niet in hun bevroren snapshot). Tenant-breed inzicht
    (hergebruik `ARCHITECTUUR.LEZEN`, zoals de registratiegaten). Leeg ⇒ geen sectie."""
    return await svc.verschoven_lat_overzicht(session, _user.tenant_id)


@router.get("/afwijking/{component_id}")
async def afwijking(
    component_id: uuid.UUID,
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_NORM, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Per component het onderscheid voor de levende klaarverklaring:
    ``{bewust:[...], verschoven:[...]}`` — bewust = bij het verklaren afgewogen (amber),
    verschoven = de lat verschoof sindsdien (neutraal). Niet klaar ⇒ beide leeg (geen lek)."""
    return await svc.afwijking_voor_component(session, _user.tenant_id, component_id)
