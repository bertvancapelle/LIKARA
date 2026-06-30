"""Origin-header check middleware.

Valideert Origin-header op state-muterende requests (POST, PUT, PATCH, DELETE).
Origin moet exact overeenkomen met platform_origin uit config.
"""
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class OriginCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method not in _MUTATING_METHODS:
            return await call_next(request)

        origin = request.headers.get("origin")

        if not origin:
            if settings.likara_test_mode:
                return await call_next(request)
            return JSONResponse(
                status_code=403,
                content={"fout": {
                    "code": "ORIGIN_GEWEIGERD",
                    "http_status": 403,
                    "bericht": "Origin header vereist voor muterende requests",
                }},
            )

        if origin != settings.platform_origin:
            return JSONResponse(
                status_code=403,
                content={"fout": {
                    "code": "ORIGIN_GEWEIGERD",
                    "http_status": 403,
                    "bericht": "Origin komt niet overeen met platform configuratie",
                }},
            )

        return await call_next(request)
