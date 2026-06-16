"""HTTP-routes — cross-element laagprojectie (ADR-023 Fase F / F-2).

Read-only architectuuroverzicht over álle element-typen, geguard op
`vereist_permissie(Entiteit.ARCHITECTUUR, Actie.LEZEN)`. Filters laag/aspect/type;
keyset-paginering. Geen schema/migratie; engine onaangeroerd.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from models.models import ElementType
from schemas.architectuur import ArchitectuurPagina
from services import architectuur_service as svc

router = APIRouter(prefix="/architectuur", tags=["bwb:architectuur"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("/elementen", response_model=ArchitectuurPagina)
async def lijst_elementen(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    laag: str | None = Query(None, max_length=40),
    aspect: str | None = Query(None, max_length=40),
    type: ElementType | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.ARCHITECTUUR, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Gelaagde projectie over alle elementen (incl. de migratielaag). Onbekend `type` ⇒ 422
    (FastAPI-enum); cursor-mismatch ⇒ 400 `ONGELDIGE_CURSOR`."""
    try:
        items, volgende = await svc.lijst(
            session, user.tenant_id, limit=limit, after=after,
            laag=laag, aspect=aspect, type=type.value if type else None,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}
