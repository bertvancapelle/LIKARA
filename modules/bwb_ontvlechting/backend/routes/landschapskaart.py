"""HTTP-route — Landschapskaart (ADR-025, read-only grafprojectie).

Levert de volledige landschapsgraaf (nodes + edges) in één call, geguard op
`vereist_permissie(Entiteit.ARCHITECTUUR, Actie.LEZEN)` (hergebruik — geen nieuwe entiteit).

**Bewuste afwijking van de lijst-paginering-norm**: de kaart laadt het volledige landschap in
één respons (een graaf is pas betekenisvol als geheel; deelpagina's leveren geen zinvolle
sub-graaf). Read-only; geen schema/migratie; engine onaangeroerd.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.landschapskaart import LandschapskaartResponse, SubgraafRequest
from services import landschapskaart_service as svc

router = APIRouter(prefix="/landschapskaart", tags=["bwb:landschapskaart"])


@router.get("", response_model=LandschapskaartResponse)
async def haal_landschapskaart(
    diepte: int = Query(1, ge=1, le=2, description="Stap-diepte (1=direct, 2=indirect). Voorbereid; "
                        "de stap-diepte wordt nu client-side op de volledige graaf toegepast."),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.ARCHITECTUUR, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Volledige landschapsgraaf (nodes + edges) voor de tenant. Geen paginering (bewust)."""
    return await svc.haal_grafdata_op(session, user.tenant_id, diepte=diepte)


@router.post("/subgraaf", response_model=LandschapskaartResponse)
async def haal_subgraaf(
    body: SubgraafRequest,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.ARCHITECTUUR, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Set-scoped sub-graaf: de gegeven component-ids (S) + hun directe buren (1 hop) + de edges
    daartussen. Voedt het vertrekpunt-herontwerp (begin leeg → bouw set op → laad alleen die set).
    Read-only; engine onaangeroerd. POST i.v.m. de mogelijk lange id-lijst."""
    return await svc.haal_grafdata_op(
        session, user.tenant_id, component_ids=body.component_ids, diepte=body.diepte)
