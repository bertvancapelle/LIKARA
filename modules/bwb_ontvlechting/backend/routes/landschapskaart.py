"""HTTP-route — Landschapskaart (ADR-025, read-only grafprojectie).

Levert de volledige landschapsgraaf (nodes + edges) in één call, geguard op
`vereist_permissie(Entiteit.ARCHITECTUUR, Actie.LEZEN)` (hergebruik — geen nieuwe entiteit).

**Bewuste afwijking van de lijst-paginering-norm**: de kaart laadt het volledige landschap in
één respons (een graaf is pas betekenisvol als geheel; deelpagina's leveren geen zinvolle
sub-graaf). Read-only; geen schema/migratie; engine onaangeroerd.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.landschapskaart import LandschapskaartResponse
from services import landschapskaart_service as svc

router = APIRouter(prefix="/landschapskaart", tags=["bwb:landschapskaart"])


@router.get("", response_model=LandschapskaartResponse)
async def haal_landschapskaart(
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.ARCHITECTUUR, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Volledige landschapsgraaf (nodes + edges) voor de tenant. Geen paginering (bewust)."""
    return await svc.haal_grafdata_op(session, user.tenant_id)
