"""HTTP-routes — referentiemodel inlezen (tenant-zijde, gate 1b §2.2).

Niets landt stil: de beheerder ziet eerst het VOORBEELD (dry-run — POST `/voorbeeld`,
schrijft niets) en bevestigt daarna expliciet (POST `/inlezen`). Beide zijn POST zonder
body: het model komt uit het gecureerde aanbod (repo-route), er is geen payload.

RBAC (besloten kader gate 1b): **inlezen = beheerder** — voorbeeld én inlezen guarden op
`REFERENTIEMODEL.AANMAKEN` (beheerder-only in de matrix; het voorbeeld is de eerste stap
van diezelfde handeling en toont de werklijst — geen apart recht). Het overzicht (wat is
er ingelezen) guardt op LEZEN — dat mag iedereen.

Dunne handlers; de regels (ONBEKEND_MODEL 422, MODELBESTAND_ONGELDIG 422, dry-run =
uitvoering via één plan) handhaaft `referentiemodel_import_service`.
"""
from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import Actie, Entiteit
from app.middleware.auth import AuthenticatedUser
from app.middleware.authz import vereist_permissie
from app.middleware.tenant import get_tenant_session
from schemas.referentiemodel import ImportResultaat, ImportVoorbeeld, ReferentiemodelAanbodItem
from services import referentiemodel_import_service as svc

router = APIRouter(prefix="/referentiemodellen", tags=["bwb:referentiemodel"])

# De sleutel is een catalogus-optie_sleutel (lowercase snake_case) — vorm op de API-rand.
_SLEUTEL = Path(pattern=r"^[a-z][a-z0-9_]*$", max_length=60)


@router.get("", response_model=list[ReferentiemodelAanbodItem])
async def aanbod(
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.REFERENTIEMODEL, Actie.LEZEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Het gecureerde aanbod + wat déze tenant ervan heeft (ingelezen snapshot,
    tellingen). Begrensd klein (gecureerd aanbod) — bewust ongepagineerd."""
    return await svc.overzicht(session, user.tenant_id)


@router.post("/{model_sleutel}/voorbeeld", response_model=ImportVoorbeeld)
async def voorbeeld(
    model_sleutel: str = _SLEUTEL,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.REFERENTIEMODEL, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Droog draaien (schrijft niets): wat zou er gebeuren — nieuw · bijgewerkt ·
    vervallen (mét naam + in-gebruik) · overgeslagen. Het voorbeeldscherm."""
    return await svc.dry_run(session, user.tenant_id, model_sleutel)


@router.post("/{model_sleutel}/inlezen", response_model=ImportResultaat)
async def inlezen(
    model_sleutel: str = _SLEUTEL,
    user: AuthenticatedUser = Depends(vereist_permissie(Entiteit.REFERENTIEMODEL, Actie.AANMAKEN)),
    session: AsyncSession = Depends(get_tenant_session),
):
    """Voer de import uit — exact het plan dat het voorbeeld toonde (één codepad).
    Idempotent; kan tientallen seconden duren (de UI toont een bezig-indicatie)."""
    return await svc.voer_uit(session, user.tenant_id, model_sleutel)
