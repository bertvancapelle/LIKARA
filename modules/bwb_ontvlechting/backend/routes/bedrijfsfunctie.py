"""HTTP-routes — Bedrijfsfunctie (ADR-043 gate 1a; ADR-044 gate 1a-bis).

Dunne handlers; RBAC via `vereist_permissie(Entiteit.BEDRIJFSFUNCTIE, …)`. CRUD +
plaatsings-endpoints (ADR-044: de boom leeft in aggregation-plaatsingen; meerdere
ouders mogelijk) + een subboom-lees-traversal. De regels (modelinhoud read-only,
vervallen niet koppelbaar, cycluspreventie) handhaaft de service — de route voegt daar
niets aan toe. Statische subpaden vóór de dynamische `/{functie_id}` (route-volgorde-norm).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.bedrijfsfunctie import (
    BedrijfsfunctieBoomItem,
    BedrijfsfunctieCreate,
    BedrijfsfunctiePagina,
    BedrijfsfunctieRead,
    BedrijfsfunctieSorteerveld,
    BedrijfsfunctieUpdate,
    PlaatsingCreate,
)
from services import bedrijfsfunctie_service as svc
from services.pagination import Sorteerrichting

router = APIRouter(prefix="/bedrijfsfuncties", tags=["bwb:bedrijfsfunctie"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=BedrijfsfunctiePagina)
async def lijst_bedrijfsfuncties(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    sort: BedrijfsfunctieSorteerveld = Query(BedrijfsfunctieSorteerveld.created_at),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    zoek: str | None = Query(None, max_length=255),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BEDRIJFSFUNCTIE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    # ADR-044: het vroegere `ouder_id`-filter is vervallen — "directe deelfuncties van X"
    # is een plaatsings-vraag en wordt beantwoord door GET /{id}/subboom (niveau 1).
    try:
        items, volgende = await svc.lijst(
            session, user.tenant_id, limit=limit, after=after,
            sort=sort.value, order=order.value, zoek=zoek,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.post("", response_model=BedrijfsfunctieRead, status_code=201)
async def maak_bedrijfsfunctie(
    body: BedrijfsfunctieCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BEDRIJFSFUNCTIE, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Maakt een EIGEN functie (geen bronsleutel — modelinhoud komt uitsluitend via het
    inlees-pad, gate 1b). Mag onder elke niet-vervallen functie én als wortel."""
    return await svc.maak_aan(session, user.tenant_id, body)


@router.get("/{functie_id}", response_model=BedrijfsfunctieRead)
async def haal_bedrijfsfunctie(
    functie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BEDRIJFSFUNCTIE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lees_detail(session, user.tenant_id, functie_id)


@router.get("/{functie_id}/subboom", response_model=list[BedrijfsfunctieBoomItem])
async def subboom(
    functie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BEDRIJFSFUNCTIE, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Read-only subboom (deelfuncties op alle niveaus, met niveau + pad + vervallen)."""
    return await svc.subboom(session, user.tenant_id, functie_id)


@router.post("/{functie_id}/plaatsingen", response_model=BedrijfsfunctieRead, status_code=201)
async def plaats_bedrijfsfunctie(
    functie_id: uuid.UUID,
    body: PlaatsingCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BEDRIJFSFUNCTIE, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """ADR-044 — plaatsing toevoegen: hang deze functie (óók) onder `ouder_id`. Meerdere
    ouders = meerdere plaatsingen, alle gelijkwaardig. Alleen op eigen functies (de
    plaatsingen van modelinhoud komen uit de bron — 422 MODELINHOUD_BESCHERMD)."""
    return await svc.plaats(session, user.tenant_id, functie_id, body.ouder_id)


@router.delete("/{functie_id}/plaatsingen/{ouder_id}", response_model=BedrijfsfunctieRead)
async def verwijder_plaatsing(
    functie_id: uuid.UUID,
    ouder_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BEDRIJFSFUNCTIE, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """ADR-044 — één plaatsing weghalen (de functie blijft bestaan; zonder plaatsingen
    wordt ze een wortel). Guard op WIJZIGEN: een plaatsing weghalen is een
    structuurwijziging van de functie, geen destructie (het roltoewijzing-/
    procesvervulling-precedent)."""
    return await svc.verwijder_plaatsing(session, user.tenant_id, functie_id, ouder_id)


@router.patch("/{functie_id}", response_model=BedrijfsfunctieRead)
async def werk_bedrijfsfunctie_bij(
    functie_id: uuid.UUID,
    body: BedrijfsfunctieUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BEDRIJFSFUNCTIE, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, functie_id, body)


@router.delete("/{functie_id}", status_code=204)
async def verwijder_bedrijfsfunctie(
    functie_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.BEDRIJFSFUNCTIE, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, functie_id)
    return Response(status_code=204)
