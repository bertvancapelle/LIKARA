"""LIKARA API — applicatie-entrypoint.

Framework-basis: security-middleware + rate limiting + health/auth routers.
Module-routers worden hier geregistreerd onder `/api/v1` zodra modules
worden gebouwd (zie `modules/`).
"""
import logging
import pathlib
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded

from app.api.v1 import auth, health, platform
from app.core.config import validate_startup_config
from app.middleware.auth import (
    NietGeauthenticeerd,
    TenantMismatch,
    niet_geauthenticeerd_handler,
    tenant_mismatch_handler,
)
from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
from app.middleware.origin_check import OriginCheckMiddleware
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from app.middleware.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger("cd.main")

# Module-backend op sys.path zodat de module-routers/-excepties importeerbaar
# zijn (zelfde patroon als `app.platform_init`). In de api-container wordt
# ./modules op /modules gemount (docker-compose) — parents[2] is dan `/`.
_MOD_BACKEND = (
    pathlib.Path(__file__).resolve().parents[2]
    / "modules"
    / "bwb_ontvlechting"
    / "backend"
)
if str(_MOD_BACKEND) not in sys.path:
    sys.path.insert(0, str(_MOD_BACKEND))

from routes.auditlog import router as auditlog_router  # noqa: E402
from routes.objecthistorie import router as objecthistorie_router  # noqa: E402
from routes.blokkade import router as blokkade_router  # noqa: E402
from routes.checklistconfig import router as checklistconfig_router  # noqa: E402
from routes.checklistscore import router as checklistscore_router  # noqa: E402
from routes.component import router as component_router  # noqa: E402
from routes.component_contract import router as component_contract_router  # noqa: E402
from routes.componentconfig import router as componentconfig_router  # noqa: E402
from routes.relatiekenmerkconfig import router as relatiekenmerkconfig_router  # noqa: E402
from routes.vraagbetekenisconfig import router as vraagbetekenisconfig_router  # noqa: E402
from routes.partijsoortconfig import router as partijsoortconfig_router  # noqa: E402
from routes.componentrolconfig import router as componentrolconfig_router  # noqa: E402
from routes.bivschaalconfig import router as bivschaalconfig_router  # noqa: E402
from routes.contract import router as contract_router  # noqa: E402
from routes.contractconfig import router as contractconfig_router  # noqa: E402
from routes.dashboard import router as dashboard_router  # noqa: E402
from routes.checklistvraag import router as checklistvraag_router  # noqa: E402
from routes.datatype import router as datatype_router  # noqa: E402
from routes.gebruikersgroep import router as gebruikersgroep_router  # noqa: E402
from routes.organisatiegebruik import router as organisatiegebruik_router  # noqa: E402
from routes.partij import router as partij_router  # noqa: E402
from routes.relatie import router as relatie_router  # noqa: E402
from routes.roltoewijzing import router as roltoewijzing_router  # noqa: E402
from routes.architectuur import router as architectuur_router  # noqa: E402
from routes.landschapskaart import router as landschapskaart_router  # noqa: E402
from routes.component_klaarverklaring import router as klaarverklaring_router  # noqa: E402
from routes.impact_view import router as impact_view_router  # noqa: E402
from routes.voorkeur import router as voorkeur_router  # noqa: E402
from routes.gebruikers import router as gebruikers_router  # noqa: E402
from routes.plaatsingsignaal import router as plaatsingsignaal_router  # noqa: E402
from routes.signalering import router as signalering_router  # noqa: E402
from routes.plateau import router as plateau_router  # noqa: E402
from routes.work_package import router as work_package_router  # noqa: E402
from routes.deliverable import router as deliverable_router  # noqa: E402
from routes.gap import router as gap_router  # noqa: E402
from routes.proces import router as proces_router  # noqa: E402
from services.errors import (  # noqa: E402
    ChecklistscoreConflict,
    ConfiguratieConflict,
    KeycloakNietBeschikbaar,
    KoppelingConflict,
    NietGevonden,
    OngeldigAntwoord,
    OngeldigeRegistratie,
    OngeldigeStatusovergang,
    RegistratieConflict,
    checklistscore_conflict_handler,
    configuratie_conflict_handler,
    keycloak_niet_beschikbaar_handler,
    koppeling_conflict_handler,
    niet_gevonden_handler,
    ongeldig_antwoord_handler,
    ongeldige_registratie_handler,
    ongeldige_statusovergang_handler,
    registratie_conflict_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Leesbare foutmelding bij ontbrekende verplichte configuratie
    validate_startup_config()
    yield


app = FastAPI(
    title="LIKARA API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Security-middleware — buitenste eerst
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(OriginCheckMiddleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Authenticatie — 401 in canoniek foutformaat (ADR-014 / OP-7)
app.add_exception_handler(NietGeauthenticeerd, niet_geauthenticeerd_handler)
# Tenant-grens — 403 in canoniek foutformaat (ADR-014 / CD009)
app.add_exception_handler(TenantMismatch, tenant_mismatch_handler)

# Autorisatie (RBAC, ADR-010) — 403 bij onvoldoende rechten
app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)

# Module-domeinfouten (bwb_ontvlechting) — canoniek foutformaat
app.add_exception_handler(NietGevonden, niet_gevonden_handler)
app.add_exception_handler(OngeldigeStatusovergang, ongeldige_statusovergang_handler)
app.add_exception_handler(KoppelingConflict, koppeling_conflict_handler)
app.add_exception_handler(ChecklistscoreConflict, checklistscore_conflict_handler)
app.add_exception_handler(OngeldigAntwoord, ongeldig_antwoord_handler)
app.add_exception_handler(ConfiguratieConflict, configuratie_conflict_handler)
# ADR-020 contractregister (fase B) — 422-/409-envelope met code op de raise-site
app.add_exception_handler(OngeldigeRegistratie, ongeldige_registratie_handler)
app.add_exception_handler(RegistratieConflict, registratie_conflict_handler)
app.add_exception_handler(KeycloakNietBeschikbaar, keycloak_niet_beschikbaar_handler)

# Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(platform.router, prefix="/api/v1")
app.include_router(partij_router, prefix="/api/v1")
app.include_router(roltoewijzing_router, prefix="/api/v1")
app.include_router(contract_router, prefix="/api/v1")
app.include_router(component_router, prefix="/api/v1")
app.include_router(component_contract_router, prefix="/api/v1")
app.include_router(datatype_router, prefix="/api/v1")
app.include_router(gebruikersgroep_router, prefix="/api/v1")
app.include_router(organisatiegebruik_router, prefix="/api/v1")
app.include_router(checklistscore_router, prefix="/api/v1")
app.include_router(blokkade_router, prefix="/api/v1")
app.include_router(auditlog_router, prefix="/api/v1")
app.include_router(objecthistorie_router, prefix="/api/v1")
app.include_router(relatie_router, prefix="/api/v1")
app.include_router(architectuur_router, prefix="/api/v1")
app.include_router(landschapskaart_router, prefix="/api/v1")
app.include_router(klaarverklaring_router, prefix="/api/v1")
app.include_router(impact_view_router, prefix="/api/v1")
app.include_router(voorkeur_router, prefix="/api/v1")
app.include_router(gebruikers_router, prefix="/api/v1")
app.include_router(plaatsingsignaal_router, prefix="/api/v1")
app.include_router(signalering_router, prefix="/api/v1")
app.include_router(plateau_router, prefix="/api/v1")
app.include_router(work_package_router, prefix="/api/v1")
app.include_router(deliverable_router, prefix="/api/v1")
app.include_router(gap_router, prefix="/api/v1")
app.include_router(proces_router, prefix="/api/v1")
app.include_router(checklistvraag_router, prefix="/api/v1")
app.include_router(checklistconfig_router, prefix="/api/v1")
app.include_router(contractconfig_router, prefix="/api/v1")
app.include_router(componentconfig_router, prefix="/api/v1")
app.include_router(relatiekenmerkconfig_router, prefix="/api/v1")
app.include_router(vraagbetekenisconfig_router, prefix="/api/v1")
app.include_router(partijsoortconfig_router, prefix="/api/v1")
app.include_router(componentrolconfig_router, prefix="/api/v1")
app.include_router(bivschaalconfig_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
