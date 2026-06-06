"""CompliData API — applicatie-entrypoint.

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

from routes.applicatie import router as applicatie_router  # noqa: E402
from services.errors import (  # noqa: E402
    NietGevonden,
    OngeldigeStatusovergang,
    niet_gevonden_handler,
    ongeldige_statusovergang_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Leesbare foutmelding bij ontbrekende verplichte configuratie
    validate_startup_config()
    yield


app = FastAPI(
    title="CompliData API",
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

# Autorisatie (RBAC, ADR-010) — 403 bij onvoldoende rechten
app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)

# Module-domeinfouten (bwb_ontvlechting) — canoniek foutformaat
app.add_exception_handler(NietGevonden, niet_gevonden_handler)
app.add_exception_handler(OngeldigeStatusovergang, ongeldige_statusovergang_handler)

# Routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(platform.router, prefix="/api/v1")
app.include_router(applicatie_router, prefix="/api/v1")
