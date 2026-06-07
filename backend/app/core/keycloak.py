import logging
from urllib.parse import urlencode

import httpx
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger("cd.keycloak")

OIDC_BASE = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect"
OIDC_EXTERNAL_BASE = f"{settings.keycloak_external_url or settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect"
JWKS_URL = f"{OIDC_BASE}/certs"
TOKEN_URL = f"{OIDC_BASE}/token"
USERINFO_URL = f"{OIDC_BASE}/userinfo"
ADMIN_BASE = f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}"

# Browser-facing authorization-endpoint (gebruiker wordt hierheen geredirect).
AUTHORIZATION_URL = f"{OIDC_EXTERNAL_BASE}/auth"
# Issuer zoals door de browser gezien — voor iss-validatie van id/access tokens.
ISSUER = f"{settings.keycloak_external_url or settings.keycloak_url}/realms/{settings.keycloak_realm}"


@lru_cache(maxsize=1)
def get_jwks_client():
    """Lazy import — jwt is only needed at runtime."""
    import jwt

    return jwt.PyJWKClient(JWKS_URL, cache_keys=True)


def decode_token(token: str) -> dict:
    """Decode and verify a Keycloak JWT access token."""
    import jwt

    jwks_client = get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.keycloak_client_id,
        issuer=f"{settings.keycloak_external_url or settings.keycloak_url}/realms/{settings.keycloak_realm}",
    )


async def exchange_code_for_tokens(
    code: str, redirect_uri: str, code_verifier: str | None = None
) -> dict:
    """Wissel de authorization code in voor tokens — uitsluitend server-side.

    `code_verifier` voegt de PKCE-bevestiging toe (RFC 7636). `client_secret`
    blijft server-side; tokens worden nooit naar de client gelekt.
    """
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": settings.keycloak_client_id,
        "client_secret": settings.keycloak_client_secret,
    }
    if code_verifier is not None:
        data["code_verifier"] = code_verifier

    async with httpx.AsyncClient() as client:
        resp = await client.post(TOKEN_URL, data=data)
        resp.raise_for_status()
        return resp.json()


def decode_id_token(token: str, expected_nonce: str | None = None) -> dict:
    """Valideer een Keycloak id_token via JWKS: handtekening, iss, aud, exp, nonce.

    Signature/iss/aud/exp worden door `jwt.decode` afgedwongen; de nonce wordt
    expliciet vergeleken met de waarde uit de oorspronkelijke login-aanvraag
    (replay-bescherming).
    """
    import jwt

    jwks_client = get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.keycloak_client_id,
        issuer=ISSUER,
    )
    if expected_nonce is not None and claims.get("nonce") != expected_nonce:
        raise ValueError("nonce komt niet overeen")
    return claims


def get_end_session_url(id_token_hint: str | None = None) -> str:
    """Bouw de Keycloak end-session URL voor RP-initiated logout (OP-4).

    Browser-facing (`OIDC_EXTERNAL_BASE`). Zonder `id_token_hint` gebruiken we
    `client_id` + `post_logout_redirect_uri` — Keycloak accepteert die combinatie
    en valideert de redirect tegen `post.logout.redirect.uris` van de client. De
    `post_logout_redirect_uri` is server-config (geen user-input → geen open
    redirect).
    """
    params = {
        "post_logout_redirect_uri": (
            settings.post_logout_redirect_uri or f"{settings.platform_origin}/login"
        ),
        "client_id": settings.keycloak_client_id,
    }
    if id_token_hint:
        params["id_token_hint"] = id_token_hint
    return f"{OIDC_EXTERNAL_BASE}/logout?{urlencode(params)}"


async def get_admin_token() -> str:
    """Verkrijg een Keycloak Admin API token via master realm."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.keycloak_url}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": settings.keycloak_admin_user,
                "password": settings.keycloak_admin_password,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def refresh_access_token(refresh_token: str) -> dict:
    """Use refresh token to obtain a new access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
            },
        )
        resp.raise_for_status()
        return resp.json()
