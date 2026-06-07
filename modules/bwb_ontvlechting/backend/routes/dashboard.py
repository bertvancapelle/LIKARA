"""HTTP-route voor het tenant-brede dashboard (CD014, #9).

Dunne handler: autorisatie via `vereist_permissie(Entiteit.APPLICATIE, LEZEN)`
(viewer-niveau — een dashboard is een lees-overzicht over applicaties),
tenant-sessie via `get_tenant_session` (RLS), aggregatie in de service.

Plaatsing — bewust in de **module** (niet platform): de getoonde data is
BWB-ontvlechtingsspecifiek (lifecycle-statussen, blokkades). Een toekomstig
platform-dashboard zou bij meerdere modules de per-module-dashboards composeren;
zolang er één module is, hoort dit overzicht hier. Additief read-endpoint binnen
bestaande patronen — geen ADR vereist.

Statische route (geen `/{id}`) → geen volgorde-conflict.

Foutgedrag:
- geen/ongeldige sessie          → 401 (auth-laag; `{"detail":{…}}`, OP-7)
- geldige sessie, te weinig recht → 403 `ONVOLDOENDE_RECHTEN`
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.dashboard import DashboardRead
from services import dashboard_service as svc

router = APIRouter(prefix="/dashboard", tags=["bwb:dashboard"])


@router.get("", response_model=DashboardRead)
async def haal_dashboard(
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.APPLICATIE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Tenant-breed overzicht: lifecycle-telling, open blokkades, recent gewijzigd."""
    return await svc.haal_dashboard(session, user.tenant_id)
