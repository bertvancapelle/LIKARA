"""HTTP-routes voor Component (ADR-021 Fase B). Dunne handlers; RBAC via
`vereist_permissie(Entiteit.COMPONENT, …)`. Bevat de CRUD, de catalogus-opties
(statisch vóór `/{id}`), het beide-richtingen-structuuroverzicht en het
component→contracten-overzicht.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, Response

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from models.models import HostingModel
from schemas.applicatie import ApplicatieStatusFilter
from schemas.component import (
    ComponentCreate,
    ComponentImpact,
    ComponentOpties,
    ComponentPagina,
    ComponentRead,
    ComponentSorteerveld,
    ComponentStructuurOverzicht,
    ComponentUpdate,
    ComponentVerwijderImpact,
)
from schemas.component_contract import ContractVoorComponent
from services import component_contract_service as cc_svc
from services import component_service as svc
from services.pagination import Sorteerrichting

router = APIRouter(prefix="/componenten", tags=["bwb:component"])


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("", response_model=ComponentPagina)
async def lijst_componenten(
    limit: int = Query(25, ge=1, le=100),
    after: str | None = Query(None),
    sort: ComponentSorteerveld = Query(ComponentSorteerveld.created_at),
    order: Sorteerrichting = Query(Sorteerrichting.asc),
    componenttype: str | None = Query(None, max_length=60),
    laag: str | None = Query(None, max_length=40),
    status: list[ApplicatieStatusFilter] = Query(default=[]),
    hostingmodel: HostingModel | None = Query(None),
    eigenaar_organisatie_id: uuid.UUID | None = Query(None),
    zoek: str | None = Query(None, max_length=255),
    # ADR-027 slice 3 — dashboard-doorklik: klaarverklaring=klaar / afwijking=1 (allowlist).
    klaarverklaring: str | None = Query(None, pattern="^klaar$"),
    afwijking: bool = Query(False),
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    try:
        items, volgende = await svc.lijst(
            session, user.tenant_id, limit=limit, after=after, sort=sort.value, order=order.value,
            componenttype=componenttype, laag=laag, status=[s.value for s in status] or None,
            hostingmodel=hostingmodel.value if hostingmodel else None,
            eigenaar_organisatie_id=eigenaar_organisatie_id, zoek=zoek,
            klaarverklaring=klaarverklaring, afwijking=afwijking,
        )
    except ValueError:
        return _fout(400, "ONGELDIGE_CURSOR", "De sorteer-/paginatieparameters zijn ongeldig.")
    return {"items": items, "volgende_cursor": volgende}


@router.get("/opties", response_model=ComponentOpties)
async def catalogus_opties(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Actieve componentcatalogus-opties per dimensie (formulier-databron). Statisch
    subpad vóór `/{component_id}`."""
    return await svc.opties(session)


@router.get("/{component_id}", response_model=ComponentRead)
async def haal_component(
    component_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.lees_detail(session, user.tenant_id, component_id)


@router.get("/{component_id}/structuur", response_model=ComponentStructuurOverzicht)
async def structuur_overzicht(
    component_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.structuur_overzicht(session, user.tenant_id, component_id)


@router.get("/{component_id}/contracten", response_model=list[ContractVoorComponent])
async def contracten_van_component(
    component_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await cc_svc.contracten_van_component(session, user.tenant_id, component_id)


@router.get("/{component_id}/verwijder-impact", response_model=ComponentVerwijderImpact)
async def verwijder_impact(
    component_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Read-only "wat verdwijnt"-samenvatting (ADR-022 Fase C): tellingen van wat een
    verwijdering zou wissen. Muteert niets; tenant-scoped; onbekend ⇒ 404."""
    return await svc.wat_verdwijnt(session, user.tenant_id, component_id)


@router.get("/{component_id}/impact", response_model=ComponentImpact)
async def impact_analyse(
    component_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Read-only impactanalyse (ADR-021 Fase E): wie steunt — direct/transitief — op
    dit component, met readiness- (lifecycle/blokkades) en contractcontext."""
    return await svc.impact_analyse(session, user.tenant_id, component_id)


@router.post("", response_model=ComponentRead, status_code=201)
async def maak_component(
    body: ComponentCreate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.maak_aan(session, user.tenant_id, body)


@router.post("/{component_id}/start-beoordeling", response_model=ComponentRead)
async def start_beoordeling(
    component_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """ADR-022 Fase E — type-generieke "start beoordeling" (concept → in_inventarisatie)
    voor een checklist-dragend component. Niet checklist-dragend ⇒ 404; niet vanuit
    `concept` ⇒ 409 `ONGELDIGE_STATUSOVERGANG`."""
    return await svc.start_beoordeling(session, user.tenant_id, component_id)


@router.patch("/{component_id}", response_model=ComponentRead)
async def werk_component_bij(
    component_id: uuid.UUID,
    body: ComponentUpdate,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.werk_bij(session, user.tenant_id, component_id, body)


@router.delete("/{component_id}", status_code=204)
async def verwijder_component(
    component_id: uuid.UUID,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT, Actie.VERWIJDEREN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    await svc.verwijder(session, user.tenant_id, component_id)
    return Response(status_code=204)
