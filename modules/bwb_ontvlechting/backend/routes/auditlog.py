"""HTTP-routes — audit-spoor lezen (ADR-006 Fase E).

Read-only, tenant-scoped, keyset-paginering. Levert correlatie-gegroepeerde
gebeurtenissen (driver + afgeleide gevolgen), filterbaar op actor / entiteit-type /
component / periode. RBAC: alleen `AUDITLOG` LEZEN (beheerder/auditor).

Foutgedrag: 401 · 403 `ONVOLDOENDE_RECHTEN` · 400 `ONGELDIGE_CURSOR` · 422 (Pydantic).
Het spoor is append-only — er zijn bewust géén schrijf-routes.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.auditlog import AuditLogPagina
from services import auditlog_service as svc

router = APIRouter(prefix="/auditlog", tags=["bwb:auditlog"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=AuditLogPagina)
async def lijst_auditlog(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    actor: str | None = Query(None, max_length=255),
    entiteit_type: str | None = Query(None, max_length=60),
    component_id: uuid.UUID | None = Query(None),
    van: datetime | None = Query(None),
    tot: datetime | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.AUDITLOG, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Correlatie-gegroepeerde audit-gebeurtenissen (nieuwste eerst), keyset-cursor.

    Filters zijn optioneel en AND-gecombineerd; een groep telt mee zodra ≥1 record
    matcht — de afgeleide gevolgen komen volledig mee. Cursor-mismatch ⇒ 400.
    """
    try:
        items, volgende = await svc.lijst(
            session,
            user.tenant_id,
            limit=limit,
            after=after,
            actor=actor,
            entiteit_type=entiteit_type,
            component_id=component_id,
            van=van,
            tot=tot,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}
