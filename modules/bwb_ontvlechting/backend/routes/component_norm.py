"""HTTP-routes — tenant-norm harde feiten: de per-component "is dit vastgesteld?"-status
(ADR-052 slice 3). RBAC via `Entiteit.COMPONENT_NORM` (LEZEN — iedereen mag de norm-status zien;
de norm bepaalt "compleet"). Dunne handler; logica in `component_norm_service`.

Deze status is de LIVE leesbron voor de klaarverklaring-dialog én het "N verplichte feiten
open"-badge — één norm-definitie, tegen de actuele veldwaarden (badge = nu; de bevroren snapshot
leeft op de klaarverklaring zelf).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.component_norm import NormVerplichtZet
from services import component_norm_beheer_service as beheer_svc
from services import component_norm_service as svc

router = APIRouter(prefix="/component-normen", tags=["bwb:component-norm"])


@router.get("/status/{component_id}")
async def norm_status(
    component_id: uuid.UUID,
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_NORM, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Per VERPLICHT feit de vastgesteld-status voor dit component ({feiten: {feit: status}}).
    Live afleiding; component buiten de tenant ⇒ lege `feiten` (geen lek)."""
    return await svc.norm_status(session, _user.tenant_id, component_id)


# ── ADR-052 besluiten 8-11 (LI045) — de verschoven lat onderscheiden van de bewuste afwijking ─────
# Statisch subpad vóór de dynamische `/{...}`-paden.
@router.get("/verschoven-lat")
async def verschoven_lat(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.ARCHITECTUUR, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Werkvoorraad: per verplicht gesteld feit de klaar-verklaarde componenten waar de lat
    verschoof (feit nu verplicht+open, maar niet in hun bevroren snapshot). Tenant-breed inzicht
    (hergebruik `ARCHITECTUUR.LEZEN`, zoals de registratiegaten). Leeg ⇒ geen sectie."""
    return await svc.verschoven_lat_overzicht(session, _user.tenant_id)


@router.get("/afwijking/{component_id}")
async def afwijking(
    component_id: uuid.UUID,
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_NORM, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Per component het onderscheid voor de levende klaarverklaring:
    ``{bewust:[...], verschoven:[...]}`` — bewust = bij het verklaren afgewogen (amber),
    verschoven = de lat verschoof sindsdien (neutraal). Niet klaar ⇒ beide leeg (geen lek)."""
    return await svc.afwijking_voor_component(session, _user.tenant_id, component_id)


# ── ADR-052 slice 4b — het norm-beheerscherm (de gemeente legt haar eigen lat) ────────────────────
@router.get("")
async def norm_definitie(
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_NORM, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """De volledige norm: per hard feit of het verplicht is + of er een 'bewust geen'-antwoord
    mogelijk is. Leesbaar voor iedereen (de lat bepaalt 'compleet'); bewerken alleen beheerder."""
    return await svc.norm_definitie(session, _user.tenant_id)


@router.get("/{feit_sleutel}/impact")
async def impact(
    feit_sleutel: str,
    verplicht: bool = Query(..., description="Doelstand: aanzetten (true) of uitzetten (false)."),
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_NORM, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Voorspelling vóór opslaan (besluit 3): hoeveel componenten/klaarverklaringen geraakt worden —
    geen blokkade, alleen inzicht. Dezelfde afleiding als de norm (geen tweede telling)."""
    return await beheer_svc.impact_voor_feit(session, _user.tenant_id, feit_sleutel, verplicht)


@router.put("/{feit_sleutel}")
async def zet_verplicht(
    feit_sleutel: str,
    body: NormVerplichtZet,
    _user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.COMPONENT_NORM, Actie.WIJZIGEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Zet de verplicht-vlag voor één hard feit — alléén de beheerder (`WIJZIGEN`). ORM → geaudit
    (wie/wanneer, besluit 5). Onbekend feit ⇒ 404."""
    return await beheer_svc.zet_verplicht(session, _user.tenant_id, feit_sleutel, body.verplicht)
