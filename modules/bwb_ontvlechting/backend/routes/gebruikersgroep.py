"""HTTP-routes voor de entiteit Gebruikersgroep (P5-vervolg, ADR-009/010).

Dunne handlers; identiek patroon aan `routes/datatype.py`. Optionele
tenant-scoped lijst-filter `?component_id=`.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.gebruiker_context import ContextComponentRead, GebruikerContextRead
from schemas.gebruikersgroep import (
    GebruikersgroepCreate,
    GebruikersgroepPagina,
    GebruikersgroepRead,
    GebruikersgroepSorteerveld,
    GebruikersgroepUpdate,
)
from services import gebruikersgroep_service as svc
from services.pagination import Sorteerrichting

router = APIRouter(prefix="/gebruikersgroepen", tags=["bwb:gebruikersgroep"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    """Canoniek foutformaat — geen stacktraces of architectuurdetails."""
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=GebruikersgroepPagina)
async def lijst_gebruikersgroepen(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    component_id: uuid.UUID | None = Query(None),
    sort: GebruikersgroepSorteerveld = Query(GebruikersgroepSorteerveld.created_at),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSGROEP, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Server-side sorteerbare keyset-lijst (ADR-017 + CD020). `sort`/`order`
    optioneel; weglaten = `created_at` oplopend. Onbekend sorteerveld/ongeldige
    richting ⇒ 422; cursor-mismatch ⇒ 400 `ONGELDIGE_CURSOR`."""
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


# ── Fase B slice 2a (LI022) — gebruiker-context-routes (statische subpaden VÓÓR de dynamische /{id}) ──
@router.get("/contexten", response_model=list[GebruikerContextRead])
async def lijst_gebruikercontexten(
    zoek: str | None = Query(None, max_length=255),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSGROEP, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Picker-bron: distinct (organisatie, afdeling)-gebruikercontexten met component-telling.
    Doorzoekbaar op organisatie-naam + afdeling. Begrensde afgeleide lijst (geen keyset) — zie service."""
    return await svc.contexten(session, user.tenant_id, zoek=zoek)


@router.get("/contexten/componenten", response_model=list[ContextComponentRead])
async def gebruikercontext_componenten(
    organisatie_id: uuid.UUID | None = Query(None),
    afdeling_id: uuid.UUID | None = Query(None),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSGROEP, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Componenten voor één gebruikercontext (context-route naar de subgraaf). Nullable composiet-
    sleutel via query-params (ADR-036a: `afdeling_id`): niet-opgegeven = null-match. Read-only."""
    return await svc.componenten_voor_context(
        session, user.tenant_id, organisatie_id=organisatie_id, afdeling_id=afdeling_id
    )


@router.get("/{gebruikersgroep_id}", response_model=GebruikersgroepRead)
async def haal_gebruikersgroep(
    gebruikersgroep_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSGROEP, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lees_detail(session, user.tenant_id, gebruikersgroep_id)


@router.post("", response_model=GebruikersgroepRead, status_code=201)
async def maak_gebruikersgroep(
    body: GebruikersgroepCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSGROEP, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Maak een gebruikersgroep; het ouder-component moet binnen de tenant bestaan."""
    return await svc.maak_aan(session, user.tenant_id, body)


@router.patch("/{gebruikersgroep_id}", response_model=GebruikersgroepRead)
async def werk_gebruikersgroep_bij(
    gebruikersgroep_id: uuid.UUID,
    body: GebruikersgroepUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.GEBRUIKERSGROEP, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, gebruikersgroep_id, body)


@router.delete("/{gebruikersgroep_id}", status_code=204)
async def verwijder_gebruikersgroep(
    gebruikersgroep_id: uuid.UUID,
    user: AuthenticatedUser = Depends(
        vereist_permissie(Entiteit.GEBRUIKERSGROEP, Actie.VERWIJDEREN)
    ),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, gebruikersgroep_id)
    return Response(status_code=204)
