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
