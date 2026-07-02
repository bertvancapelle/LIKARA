"""HTTP-routes — objecthistorie (ADR-029): de geschiedenis van één object ('i'-knop).

Werkcontext, geen toezicht: **toegang volgt het object** — NIET de centrale `AUDITLOG`-gate.
Wie het object mag lezen (de bestaande per-type lees-permissie) mag z'n historie lezen. Het
object wordt eerst geresolveerd via de object-service (404 buiten de tenant — no-leak, OP-6).
Hergebruikt de audit-leeslogica + de actor-naam-resolutie; geen tweede audit-leesmechanisme.

Foutgedrag: 401 · 403 `ONVOLDOENDE_RECHTEN` (object-type niet leesbaar) · 404 (object onbekend
binnen de tenant) · 400 `ONGELDIG_ENTITEIT_TYPE` · 400 `ONGELDIGE_CURSOR`.

ENGINE-INVARIANT: read-only; importeert GEEN lifecycle/score-symbolen — alleen de read-`haal_op`
van de object-services voor de toegangscheck.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.rbac import Actie, Entiteit, heeft_permissie
from app.middleware.auth import AuthenticatedUser, get_current_user
from app.middleware.authz import OnvoldoendeRechten
from app.middleware.tenant import get_tenant_session
from schemas.auditlog import AuditLogPagina
from services import auditlog_service as svc
from services import component_service, contract_service, partij_service
from services import deliverable_service, gap_service, plateau_service, work_package_service

router = APIRouter(prefix="/objecthistorie", tags=["bwb:objecthistorie"])

# Per entiteit-type: (lees-permissie, object-resolutie voor de toegangscheck/404, audit-filtermodus).
# Élk type met een eigen detailscherm + `haal_op` + eigen leespermissie is opgenomen. 'component'
# → het rijke component_id-pad (incl. afgeleide profiel/score/blokkade-records via jsonb-diff);
# de overige → een generiek entiteit_id-filter op de directe object-records. LI059: applicaties zijn
# componenten (type 'applicatie') → hun historie loopt via 'component'; de aparte 'applicatie'-tak is weg.
# NIET opgenomen (sub-/afgeleide entiteit zonder eigen scherm — verschijnt in de historie van de
# ouder): component_profiel, checklistscore, blokkade (→ component); contract_dekking/-kostenmodel
# (→ contract); datatype, relatie, roltoewijzing, gebruikersgroep, gebruiker_persoon,
# component_klaarverklaring (geen eigen detailscherm / geen eigenstandige object-read).
_TYPES = {
    "component": (Entiteit.COMPONENT, component_service.haal_op, "component"),
    "contract": (Entiteit.CONTRACT, contract_service.haal_op, "entiteit"),
    "partij": (Entiteit.PARTIJ, partij_service.haal_op, "entiteit"),
    "plateau": (Entiteit.PLATEAU, plateau_service.haal_op, "entiteit"),
    "work_package": (Entiteit.WORK_PACKAGE, work_package_service.haal_op, "entiteit"),
    "deliverable": (Entiteit.DELIVERABLE, deliverable_service.haal_op, "entiteit"),
    "gap": (Entiteit.GAP, gap_service.haal_op, "entiteit"),
}


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("/{entiteit_type}/{entiteit_id}", response_model=AuditLogPagina)
async def objecthistorie(
    entiteit_type: str,
    entiteit_id: uuid.UUID,
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Correlatie-gegroepeerde historie van één object (nieuwste eerst, keyset-cursor).

    Geen `AUDITLOG`-recht vereist: de toegang volgt de lees-permissie van het object-type +
    de tenant-resolutie van het object zelf.
    """
    config = _TYPES.get(entiteit_type)
    if config is None:
        return _fout(400, "ONGELDIG_ENTITEIT_TYPE", "Onbekend objecttype voor historie.")
    permissie, haal_op, modus = config

    # Toegang volgt het object: (1) leesrecht op dit type, (2) object bestaat binnen de tenant.
    if not heeft_permissie(user.roles, permissie, Actie.LEZEN):
        raise OnvoldoendeRechten(permissie, Actie.LEZEN)
    await haal_op(session, user.tenant_id, entiteit_id)  # NietGevonden ⇒ 404 (no-leak)

    try:
        if modus == "component":
            items, volgende = await svc.lijst(session, user.tenant_id, limit=limit, after=after, component_id=entiteit_id)
        else:
            items, volgende = await svc.lijst(
                session, user.tenant_id, limit=limit, after=after,
                entiteit_type=entiteit_type, entiteit_id=entiteit_id,
            )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}
