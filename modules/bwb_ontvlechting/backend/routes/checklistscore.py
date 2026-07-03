"""HTTP-routes voor de entiteit Checklistscore (ADR-009/010/013).

Dunne handlers; business-logica (ouder-/vraag_code-validatie, uniciteit,
auto-blokkade-invariant, lifecycle-herberekening) zit in de service.

Foutgedrag: 401 · 403 `ONVOLDOENDE_RECHTEN` · 404 `NIET_GEVONDEN` (record,
ouder-applicatie óf onbekende `vraag_code`) · 409 `CHECKLISTSCORE_BESTAAT_AL`
(dubbele score) · 422 (Pydantic) · 400 `ONGELDIGE_CURSOR`.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.checklistscore import (
    ChecklistscoreCreate,
    ChecklistscoreOpties,
    ChecklistscorePagina,
    ChecklistscoreRead,
    ChecklistscoreSorteerveld,
    ChecklistscoreUpdate,
)
from services import checklistscore_service as svc
from services.pagination import Sorteerrichting

router = APIRouter(prefix="/checklistscores", tags=["bwb:checklistscore"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    """Canoniek foutformaat — geen stacktraces of architectuurdetails."""
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=ChecklistscorePagina)
async def lijst_checklistscores(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    component_id: uuid.UUID | None = Query(None),
    sort: ChecklistscoreSorteerveld = Query(ChecklistscoreSorteerveld.created_at),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CHECKLISTSCORE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Server-side sorteerbare keyset-lijst (ADR-017 + CD020).

    **API-only retrofit** (CD020, beslispunt 2): de sorteerbaarheid maakt dit
    lijst-endpoint uniform met de overige entiteiten, maar de frontend-sectie
    (`ChecklistscoreSectie.vue`) blijft bewust een vraag-gedreven invulformulier
    (89 vragen, inline score-bewerking) — géén sorteerbare tabel. `sort`/`order`
    optioneel; weglaten = `created_at` oplopend. Onbekend sorteerveld/ongeldige
    richting ⇒ 422; cursor-mismatch ⇒ 400 `ONGELDIGE_CURSOR`.
    """
    try:
        items, volgende = await svc.lijst(
            session,
            user.tenant_id,
            limit=limit,
            after=after,
            component_id=component_id,
            sort=sort.value,
            order=order.value,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.get("/opties", response_model=ChecklistscoreOpties)
async def checklistscore_opties(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CHECKLISTSCORE, Actie.LEZEN)),
):
    """Read-only keuzewaarden (score). Vóór `/{id}` (geen UUID-parse op 'opties')."""
    return svc.enum_opties()


@router.get("/{checklistscore_id}", response_model=ChecklistscoreRead)
async def haal_checklistscore(
    checklistscore_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CHECKLISTSCORE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lees_detail(session, user.tenant_id, checklistscore_id)


@router.post("", response_model=ChecklistscoreRead, status_code=201)
async def maak_checklistscore(
    body: ChecklistscoreCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CHECKLISTSCORE, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Maak een score; ouder + vraag_code moeten bestaan, score is uniek per vraag."""
    return await svc.maak_aan(session, user.tenant_id, body)


@router.patch("/{checklistscore_id}", response_model=ChecklistscoreRead)
async def werk_checklistscore_bij(
    checklistscore_id: uuid.UUID,
    body: ChecklistscoreUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CHECKLISTSCORE, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, checklistscore_id, body)


@router.delete("/{checklistscore_id}", status_code=204)
async def verwijder_checklistscore(
    checklistscore_id: uuid.UUID,
    user: AuthenticatedUser = Depends(
        vereist_permissie(Entiteit.CHECKLISTSCORE, Actie.VERWIJDEREN)
    ),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, checklistscore_id)
    return Response(status_code=204)
