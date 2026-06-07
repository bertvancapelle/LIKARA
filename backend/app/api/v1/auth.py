"""Auth endpoints — login/callback (PKCE), sessie-introspectie + logout.

`/auth/login` start de OAuth2 Authorization Code-flow met PKCE (ADR-002):
`code_verifier`/`state`/`nonce` worden server-side in Redis bewaard (gekoppeld
via `state`, nooit client-leesbaar) en de gebruiker wordt naar Keycloak
geredirect. `/auth/callback` wisselt de code server-side in, valideert het
id_token (nonce/iss/aud/exp) en zet de `cd_session` httpOnly cookie die door
`/auth/me` wordt gevalideerd.
"""
import json
import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, Request, Response
from pydantic import ValidationError
from starlette.responses import JSONResponse, RedirectResponse
from urllib.parse import urlencode

from app.core.config import settings
from app.core.keycloak import (
    AUTHORIZATION_URL,
    decode_id_token,
    exchange_code_for_tokens,
    get_end_session_url,
    refresh_access_token,
)
from app.core.pkce import (
    code_challenge_s256,
    generate_code_verifier,
    generate_nonce,
    generate_state,
)
from app.core.redis import get_redis
from app.middleware.auth import (
    AuthenticatedUser,
    NietGeauthenticeerd,
    _increment_fail_counter,
    get_current_user,
)
from app.schemas.auth import CallbackParams, LoginParams
from app.utils.crypto import hash_waarde

router = APIRouter(prefix="/auth", tags=["auth"])

_log = logging.getLogger("cd.auth")

_STATE_PREFIX = "auth_login:"
_REFRESH_PREFIX = "auth_refresh:"


def _zet_session_cookie(response: Response | RedirectResponse, access_token: str) -> None:
    """Zet de httpOnly `cd_session`-cookie (access-token, 15 min)."""
    response.set_cookie(
        key=settings.cookie_name,
        value=access_token,
        max_age=settings.access_token_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )


def _zet_refresh_cookie(response: Response | RedirectResponse, sessie_id: str) -> None:
    """Zet de httpOnly `cd_refresh`-cookie (opake sessie-id; nooit client-leesbaar)."""
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=sessie_id,
        max_age=settings.refresh_token_max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )


def _effective_redirect_uri() -> str:
    """OAuth2 redirect_uri — configureerbaar, anders afgeleid van platform_origin."""
    return settings.oidc_redirect_uri or f"{settings.platform_origin}/api/v1/auth/callback"


def _valideer_next(bestemming: str | None) -> str:
    """Open-redirect-bescherming: sta alleen een same-origin relatief pad toe."""
    if not bestemming:
        return "/"
    if (
        bestemming.startswith("/")
        and not bestemming.startswith("//")
        and "\\" not in bestemming
        and "://" not in bestemming
    ):
        return bestemming
    return "/"


def _fout(http_status: int, code: str, bericht: str) -> JSONResponse:
    """Canoniek foutformaat — geen stacktraces of architectuurdetails."""
    return JSONResponse(
        status_code=http_status,
        content={"fout": {"code": code, "http_status": http_status, "bericht": bericht}},
    )


@router.get("/login")
async def login(request: Request):
    """Start de Authorization Code + PKCE-flow; redirect naar Keycloak."""
    try:
        params = LoginParams(**dict(request.query_params))
    except ValidationError:
        return _fout(400, "LOGIN_PARAMS_ONGELDIG", "Ongeldige login-parameters.")

    veilige_next = _valideer_next(params.next)
    verifier = generate_code_verifier()
    challenge = code_challenge_s256(verifier)
    state = generate_state()
    nonce = generate_nonce()

    r = await get_redis()
    await r.set(
        f"{_STATE_PREFIX}{state}",
        json.dumps({"verifier": verifier, "nonce": nonce, "next": veilige_next}),
        ex=settings.auth_state_ttl,
    )

    query = urlencode(
        {
            "client_id": settings.keycloak_client_id,
            "redirect_uri": _effective_redirect_uri(),
            "response_type": "code",
            "scope": "openid",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "nonce": nonce,
        }
    )
    return RedirectResponse(url=f"{AUTHORIZATION_URL}?{query}", status_code=302)


@router.get("/callback")
async def callback(request: Request):
    """Verwerk de Keycloak-redirect: valideer state, wissel code in, zet sessie."""
    ip_hash = hash_waarde(request.client.host if request.client else None) or "unknown"

    try:
        params = CallbackParams(**dict(request.query_params))
    except ValidationError:
        return _fout(400, "CALLBACK_PARAMS_ONGELDIG", "Ongeldige callback-parameters.")

    if params.error:
        return _fout(400, "AUTH_GEWEIGERD", "Authenticatie is geweigerd.")
    if not params.code or not params.state:
        return _fout(400, "CALLBACK_PARAMS_ONGELDIG", "Ontbrekende code of state.")

    # State eenmalig consumeren (CSRF + replay-bescherming).
    r = await get_redis()
    ruw = await r.getdel(f"{_STATE_PREFIX}{params.state}")
    if not ruw:
        await _increment_fail_counter(ip_hash)
        return _fout(400, "STATE_ONGELDIG", "Sessie-aanvraag verlopen of ongeldig.")
    opslag = json.loads(ruw)

    redirect_uri = _effective_redirect_uri()
    try:
        tokens = await exchange_code_for_tokens(params.code, redirect_uri, opslag["verifier"])
    except Exception:
        await _increment_fail_counter(ip_hash)
        _log.warning("AUTH_FAIL: token-uitwisseling mislukt (ip_hash=%s)", ip_hash)
        return _fout(502, "TOKEN_UITWISSELING_MISLUKT", "Inloggen mislukt.")

    id_token = tokens.get("id_token")
    access_token = tokens.get("access_token")
    if not id_token or not access_token:
        await _increment_fail_counter(ip_hash)
        return _fout(502, "TOKEN_UITWISSELING_MISLUKT", "Inloggen mislukt.")

    try:
        decode_id_token(id_token, opslag["nonce"])
    except Exception:
        await _increment_fail_counter(ip_hash)
        _log.warning("AUTH_FAIL: id_token-validatie mislukt (ip_hash=%s)", ip_hash)
        return _fout(401, "ID_TOKEN_ONGELDIG", "Inloggen mislukt.")

    bestemming = _valideer_next(opslag.get("next"))
    response = RedirectResponse(url=bestemming, status_code=303)
    _zet_session_cookie(response, access_token)

    # Refresh-token server-side bewaren (ADR-015 B2): in Redis onder een opake
    # sessie-identifier; de identifier in een httpOnly cookie, nooit client-leesbaar.
    refresh_token = tokens.get("refresh_token")
    if refresh_token:
        sessie_id = generate_state()
        await r.set(
            f"{_REFRESH_PREFIX}{sessie_id}", refresh_token, ex=settings.refresh_token_max_age
        )
        _zet_refresh_cookie(response, sessie_id)
    return response


@router.post("/refresh")
async def refresh(request: Request):
    """Verleng de sessie stil via Keycloak (ADR-015 B5).

    Leest de opake sessie-identifier (cookie) → haalt het refresh_token uit Redis
    → wisselt bij Keycloak (`grant_type=refresh_token`, server-side) → zet een
    nieuw `cd_session` en bewaart het GEROTEERDE refresh_token (B3). Falen
    (afwezig/verlopen/door-Keycloak-geweigerd) ⇒ 401 canoniek (ADR-014).
    """
    sessie_id = request.cookies.get(settings.refresh_cookie_name)
    if not sessie_id:
        raise NietGeauthenticeerd("Geen sessie om te verversen.")

    r = await get_redis()
    sleutel = f"{_REFRESH_PREFIX}{sessie_id}"
    refresh_token = await r.get(sleutel)
    if not refresh_token:
        raise NietGeauthenticeerd("Sessie verlopen.")

    try:
        tokens = await refresh_access_token(refresh_token)
    except Exception:
        await r.delete(sleutel)  # onbruikbaar geworden handle opruimen (B5)
        raise NietGeauthenticeerd("Sessie verlopen.")

    access_token = tokens.get("access_token")
    if not access_token:
        await r.delete(sleutel)
        raise NietGeauthenticeerd("Sessie verlopen.")

    # Rotatie (B3): bewaar het nieuwste refresh_token; overschrijf het oude.
    nieuw_refresh = tokens.get("refresh_token")
    if nieuw_refresh:
        await r.set(sleutel, nieuw_refresh, ex=settings.refresh_token_max_age)

    response = Response(status_code=204)
    _zet_session_cookie(response, access_token)
    return response


@router.get("/me")
async def me(
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Geef de huidige geauthenticeerde gebruiker terug (401 zonder geldige sessie)."""
    return asdict(user)


def _wis_cookie(response: Response, naam: str) -> None:
    """Wis een cookie met dezelfde attributen als bij het zetten."""
    response.delete_cookie(
        key=naam,
        domain=settings.cookie_domain,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        httponly=True,
        path="/",
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    """RP-initiated logout (OP-4): lokale intrekking + Keycloak end-session.

    1. Verwijder het Redis-refresh-handle (ADR-015-raakvlak; het OP-3-token mag
       niet blijven leven), idempotent. 2. Wis `cd_session` én `cd_refresh`.
       3. Geef de Keycloak end-session-URL terug; de frontend navigeert ernaartoe
       zodat ook de SSO-sessie eindigt (anders logt de volgende /login stil weer in).
    """
    sessie_id = request.cookies.get(settings.refresh_cookie_name)
    if sessie_id:
        r = await get_redis()
        await r.delete(f"{_REFRESH_PREFIX}{sessie_id}")  # idempotent

    _wis_cookie(response, settings.cookie_name)
    _wis_cookie(response, settings.refresh_cookie_name)

    return {"status": "uitgelogd", "keycloak_logout_url": get_end_session_url()}
