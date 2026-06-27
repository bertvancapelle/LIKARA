"""HTTP-routes voor de entiteit Contract (ADR-020 fase B).

Dunne handlers; autorisatie via `vereist_permissie(Entiteit.CONTRACT, …)`. Bevat
naast de CRUD ook de sub-overzichten deelcontracten en gekoppelde applicaties.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from models.models import ContractType
from schemas.applicatie_contract import ApplicatieVoorContract
from schemas.gebruiker_context import ContextComponentRead
from schemas.contract import (
    CatalogusOpties,
    ContractCreate,
    ContractLijstItem,
    ContractPagina,
    ContractRead,
    ContractSorteerveld,
    ContractUpdate,
    DeelcontractItem,
)
from services import contract_service as svc
from services import contractconfig_catalog as catalog
from services import relatiekenmerk_catalog
from services.pagination import Sorteerrichting

router = APIRouter(prefix="/contracten", tags=["bwb:contract"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=ContractPagina)
async def lijst_contracten(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    sort: ContractSorteerveld = Query(ContractSorteerveld.created_at),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    leverancier_id: uuid.UUID | None = Query(None),
    contracttype: ContractType | None = Query(None),
    dekking: str | None = Query(None, max_length=60),
    kostenmodel: str | None = Query(None, max_length=60),
    zoek: str | None = Query(None, max_length=255),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CONTRACT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    try:
        items, volgende = await svc.lijst(
            session, user.tenant_id,
            limit=limit, after=after, sort=sort.value, order=order.value,
            leverancier_id=leverancier_id,
            contracttype=contracttype.value if contracttype else None,
            dekking=dekking, kostenmodel=kostenmodel, zoek=zoek,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De opgegeven paginacursor is ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.get("/opties", response_model=CatalogusOpties)
async def catalogus_opties(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CONTRACT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Tenant-leeszijde voor de contractformulieren: actieve dekking-/kostenmodel-opties
    (uit ContractConfig) + relatie_rol-opties (uit de relatie-kenmerk-catalogus, na de
    consistentie-opruim). Respons-vorm ongewijzigd ({dekking, kostenmodel, relatie_rol});
    alleen de bron van de relatie_rol-lijst is verschoven. Statisch subpad vóór `/{contract_id}`."""
    opties = await catalog.actieve_opties_per_dimensie(session)
    relatiekenmerken = await relatiekenmerk_catalog.actieve_opties_per_dimensie(session)
    opties["relatie_rol"] = relatiekenmerken.get("relatie_rol", [])
    return opties


@router.get("/{contract_id}", response_model=ContractRead)
async def haal_contract(
    contract_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CONTRACT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lees_detail(session, user.tenant_id, contract_id)


@router.get("/{contract_id}/deelcontracten", response_model=list[DeelcontractItem])
async def deelcontracten(
    contract_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CONTRACT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.deelcontracten(session, user.tenant_id, contract_id)


@router.get("/{contract_id}/applicaties", response_model=list[ApplicatieVoorContract])
async def gekoppelde_applicaties(
    contract_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CONTRACT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.applicaties(session, user.tenant_id, contract_id)


@router.get("/{contract_id}/componenten", response_model=list[ContextComponentRead])
async def gekoppelde_componenten(
    contract_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CONTRACT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Fase B slice 2a (LI022) — ALLE aan dit contract gekoppelde componenten (context-route naar
    de subgraaf), incl. kale/profielloze componenten die `/applicaties` weglaat. Read-only."""
    return await svc.componenten(session, user.tenant_id, contract_id)


@router.post("", response_model=ContractRead, status_code=201)
async def maak_contract(
    body: ContractCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CONTRACT, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.patch("/{contract_id}", response_model=ContractRead)
async def werk_contract_bij(
    contract_id: uuid.UUID,
    body: ContractUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CONTRACT, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, contract_id, body)


@router.delete("/{contract_id}", status_code=204)
async def verwijder_contract(
    contract_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.CONTRACT, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, contract_id)
    return Response(status_code=204)
