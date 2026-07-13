"""Platform-beheer-endpoints — referentiemodel-aanbod (gate 1b §2.1).

Geautoriseerd via `vereist_platform_permissie(REFERENTIEMODELCONFIG, …)` op
`get_platform_session` (lk_platform). Spiegel van `routes/applicatiefunctieconfig`,
zónder POST: het aanbod is gesloten (repo-route — een aanbod-rij zonder meegeleverd
bestand is niet inleesbaar; nieuw aanbod = release-curatie). Géén DELETE
(soft-deactivate via `actief`).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.platform_rbac import PlatformEntiteit
from app.core.rbac import Actie
from app.middleware.authz import vereist_platform_permissie
from app.middleware.tenant import get_platform_session
from schemas.referentiemodelconfig import ReferentiemodelOptieRead, ReferentiemodelOptieUpdate
from services import referentiemodelconfig_service as svc

router = APIRouter(prefix="/platform/referentiemodelconfig", tags=["platform:referentiemodelconfig"])

_LEZEN = vereist_platform_permissie(PlatformEntiteit.REFERENTIEMODELCONFIG, Actie.LEZEN)
_WIJZIGEN = vereist_platform_permissie(PlatformEntiteit.REFERENTIEMODELCONFIG, Actie.WIJZIGEN)


@router.get("", response_model=list[ReferentiemodelOptieRead])
async def lijst(_user=Depends(_LEZEN), session: AsyncSession = Depends(get_platform_session)):
    """Het volledige aanbod (incl. gedeactiveerde), met navolgbare herkomst."""
    return await svc.lijst(session)


@router.patch("/{optie_id}", response_model=ReferentiemodelOptieRead)
async def wijzig(
    optie_id: int,
    body: ReferentiemodelOptieUpdate,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_platform_session),
):
    """Wijzig label/volgorde/actief. Sleutel/herkomst/versie zijn read-only
    (gecureerde identiteit). Onbekend id ⇒ 404."""
    return await svc.wijzig(session, optie_id, body)
