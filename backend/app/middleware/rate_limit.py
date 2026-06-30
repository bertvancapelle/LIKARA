"""Rate limiting middleware.

Gebruikt SlowAPI met Redis als teller-backend.
Drempelwaarden worden gelezen uit config.
"""
import logging

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.utils.crypto import hash_waarde

logger = logging.getLogger("cd.ratelimit")


def _get_key(request: Request) -> str:
    """Bepaal rate limit key: tenant_id uit request state, of IP als fallback."""
    if settings.likara_test_mode:
        return get_remote_address(request)

    if hasattr(request.state, "user") and request.state.user:
        return getattr(request.state.user, "tenant_id", get_remote_address(request))

    return get_remote_address(request)


def _get_ip_key(request: Request) -> str:
    """Altijd IP als key (voor auth-endpoints)."""
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_key,
    storage_uri=settings.redis_url,
    default_limits=[],
)

AUTH_LIMIT = f"{settings.rate_limit_auth}/minute"
WRITE_LIMIT = f"{settings.rate_limit_write}/minute"
READ_LIMIT = f"{settings.rate_limit_read}/minute"
ADMIN_LIMIT = f"{settings.rate_limit_admin}/minute"


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handler voor HTTP 429 responses."""
    ip_hash = hash_waarde(request.client.host if request.client else None)
    logger.warning("Rate limit exceeded: %s %s (ip_hash=%s)", request.method, request.url.path, ip_hash)

    return JSONResponse(
        status_code=429,
        content={"fout": {
            "code": "RATE_LIMIT_OVERSCHREDEN",
            "http_status": 429,
            "bericht": "Te veel verzoeken — probeer het later opnieuw",
        }},
    )
