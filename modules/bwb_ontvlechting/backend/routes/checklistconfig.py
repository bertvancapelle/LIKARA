"""Tenant-beheer-endpoints — checklist-vragenset + antwoordconfiguratie
(ADR-019 fase 2D; ADR-022 Wijziging W1).

ADR-022 W1: de vragenset is **tenant-eigendom**. Geautoriseerd via
`vereist_permissie(CHECKLISTVRAAG, …)` (tenant-rollen) op `get_tenant_session`
(`cd_app`, RLS-context). Vragen worden geadresseerd op hun `id`. Het toevoegen of
(de)activeren van een vraag herberekent in-tenant de lifecycle van componenten van
dat type (atomair).

Foutgedrag: 401 · 403 `ONVOLDOENDE_RECHTEN` · 404 `NIET_GEVONDEN` · 409
`CONFIGURATIE_CONFLICT` / `CHECKLISTVRAAG_BESTAAT` · 422 (Pydantic / `ONGELDIGE_OPTIE`).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.checklistconfig import (
    ActiefUpdate,
    AntwoordTypeUpdate,
    ConfigOptieRead,
    ConfigVraagRead,
    OptieCreate,
    OptieUpdate,
    VraagCreate,
    VraagImpact,
    VraagUpdate,
)
from services import checklistconfig_service as svc

router = APIRouter(prefix="/checklistconfig", tags=["bwb:checklistconfig"])

_LEZEN = vereist_permissie(Entiteit.CHECKLISTVRAAG, Actie.LEZEN)
_AANMAKEN = vereist_permissie(Entiteit.CHECKLISTVRAAG, Actie.AANMAKEN)
_WIJZIGEN = vereist_permissie(Entiteit.CHECKLISTVRAAG, Actie.WIJZIGEN)


@router.get("", response_model=list[ConfigVraagRead])
async def lijst_config(
    _user=Depends(_LEZEN),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Alle tenant-vragen + antwoordtype + ALLE opties (incl. inactieve)."""
    return await svc.lijst_config(session)


@router.get("/impact", response_model=VraagImpact)
async def impact(
    componenttype: str = Query(..., max_length=60),
    _user=Depends(_LEZEN),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Read-only "raakt N componenten" — aantal eigen componenten van dit type
    (vóór toevoegen/(de)activeren). Statisch subpad vóór `/vragen/{id}`."""
    return {"aantal_componenten": await svc.impact_telling(session, componenttype)}


@router.post("/vragen", response_model=ConfigVraagRead, status_code=201)
async def maak_vraag(
    body: VraagCreate,
    user: AuthenticatedUser = Depends(_AANMAKEN),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Voeg een tenant-vraag toe (componenttype+code = identiteit); herberekent
    in-tenant de lifecycle van bestaande componenten van dat type."""
    return await svc.maak_vraag(session, user.tenant_id, body)


@router.patch("/vragen/{checklistvraag_id}", response_model=ConfigVraagRead)
async def werk_vraag_bij(
    checklistvraag_id: uuid.UUID,
    body: VraagUpdate,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Bewerk niet-tellende velden (tekst/categorie/prioriteit); type+code immutable."""
    return await svc.werk_vraag_bij(session, checklistvraag_id, body)


@router.patch("/vragen/{checklistvraag_id}/antwoordtype", response_model=ConfigVraagRead)
async def zet_antwoordtype(
    checklistvraag_id: uuid.UUID,
    body: AntwoordTypeUpdate,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.zet_antwoordtype(session, checklistvraag_id, body)


@router.post("/vragen/{checklistvraag_id}/actief", response_model=ConfigVraagRead)
async def zet_actief(
    checklistvraag_id: uuid.UUID,
    body: ActiefUpdate,
    user: AuthenticatedUser = Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_tenant_session),
):
    """(De)activeer een vraag (soft-deactivatie); herberekent in-tenant de lifecycle."""
    return await svc.zet_actief(session, user.tenant_id, checklistvraag_id, body.actief)


@router.post("/vragen/{checklistvraag_id}/opties", response_model=ConfigOptieRead, status_code=201)
async def voeg_optie_toe(
    checklistvraag_id: uuid.UUID,
    body: OptieCreate,
    user: AuthenticatedUser = Depends(_AANMAKEN),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.voeg_optie_toe(session, user.tenant_id, checklistvraag_id, body)


@router.patch("/opties/{optie_id}", response_model=ConfigOptieRead)
async def wijzig_optie(
    optie_id: uuid.UUID,
    body: OptieUpdate,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.wijzig_optie(session, optie_id, body)


@router.post("/opties/{optie_id}/deactiveren", response_model=ConfigOptieRead)
async def deactiveer_optie(
    optie_id: uuid.UUID,
    _user=Depends(_WIJZIGEN),
    session: AsyncSession = Depends(get_tenant_session),
):
    return await svc.deactiveer_optie(session, optie_id)
