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


# ── ADR-029 — user-provisioning via dedicated service-account ────────────────────

class KeycloakProvisioningFout(Exception):
    """Een Keycloak Admin API-call voor user-provisioning is mislukt."""

    def __init__(self, bericht: str, status_code: int | None = None):
        super().__init__(bericht)
        self.bericht = bericht
        self.status_code = status_code


async def get_provisioning_token() -> str:
    """Admin-token via client-credentials voor de `likara-user-provisioning`
    service-account (ADR-029). Structureel minimaal-geprivilegieerd (manage-users +
    view-users) — géén brede master-admin-creds."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": "likara-user-provisioning",
                "client_secret": settings.likara_provisioning_secret,
            },
        )
        if resp.status_code != 200:
            raise KeycloakProvisioningFout(
                "Kon geen provisioning-token verkrijgen.", resp.status_code
            )
        return resp.json()["access_token"]


def genereer_tijdelijk_wachtwoord(lengte: int = 20) -> str:
    """Sterk willekeurig tijdelijk wachtwoord (`secrets`, >=16 tekens, mix van
    letters/cijfers/symbolen). Wordt eenmalig teruggegeven, NOOIT gelogd."""
    import secrets

    alfabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%^&*-_=+"
    lengte = max(lengte, 16)
    # Garandeer minstens één teken uit elke klasse, vul de rest willekeurig aan.
    kern = [
        secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ"),
        secrets.choice("abcdefghijkmnpqrstuvwxyz"),
        secrets.choice("23456789"),
        secrets.choice("!@#$%^&*-_=+"),
    ]
    kern += [secrets.choice(alfabet) for _ in range(lengte - len(kern))]
    for i in range(len(kern) - 1, 0, -1):  # Fisher-Yates met secrets
        j = secrets.randbelow(i + 1)
        kern[i], kern[j] = kern[j], kern[i]
    return "".join(kern)


def _splits_naam(naam: str) -> tuple[str, str]:
    """Splits een volledige naam in (firstName, lastName) — best-effort."""
    delen = (naam or "").strip().split()
    if not delen:
        return "", ""
    if len(delen) == 1:
        return delen[0], ""
    return delen[0], " ".join(delen[1:])


async def maak_keycloak_gebruiker(email: str, naam: str, tijdelijk_wachtwoord: str, rol: str) -> str:
    """Maak een Keycloak-gebruiker aan en retourneer de `keycloak_sub` (UUID-string).

    Flow (provisioning-token via `get_provisioning_token`): create-user (201 + Location ->
    sub) -> reset-password (temporary=true) -> realm-rol toewijzen. `UPDATE_PASSWORD` als
    required action -> de gebruiker wijzigt het wachtwoord bij de eerste login.
    NB: het wachtwoord wordt NOOIT gelogd (ook niet bij debug)."""
    token = await get_provisioning_token()
    headers = {"Authorization": f"Bearer {token}"}
    voornaam, achternaam = _splits_naam(naam)
    async with httpx.AsyncClient() as client:
        # 1. Gebruiker aanmaken.
        resp = await client.post(
            f"{ADMIN_BASE}/users",
            headers=headers,
            json={
                "username": email,
                "email": email,
                "firstName": voornaam,
                "lastName": achternaam,
                "enabled": True,
                "emailVerified": True,
                "requiredActions": ["UPDATE_PASSWORD"],
            },
        )
        if resp.status_code != 201:
            raise KeycloakProvisioningFout("Aanmaken Keycloak-gebruiker mislukt.", resp.status_code)
        locatie = resp.headers.get("Location")
        if not locatie:
            raise KeycloakProvisioningFout("Keycloak gaf geen Location-header terug.")
        sub = locatie.rstrip("/").rsplit("/", 1)[-1]

        # 2. Tijdelijk wachtwoord zetten.
        pw = await client.put(
            f"{ADMIN_BASE}/users/{sub}/reset-password",
            headers=headers,
            json={"type": "password", "value": tijdelijk_wachtwoord, "temporary": True},
        )
        if pw.status_code not in (200, 204):
            raise KeycloakProvisioningFout("Zetten tijdelijk wachtwoord mislukt.", pw.status_code)

        # 3. Realm-rol toewijzen.
        rol_resp = await client.get(f"{ADMIN_BASE}/roles/{rol}", headers=headers)
        if rol_resp.status_code != 200:
            raise KeycloakProvisioningFout(f"Realm-rol '{rol}' niet gevonden.", rol_resp.status_code)
        rol_repr = rol_resp.json()
        toewijs = await client.post(
            f"{ADMIN_BASE}/users/{sub}/role-mappings/realm",
            headers=headers,
            json=[{"id": rol_repr["id"], "name": rol_repr["name"]}],
        )
        if toewijs.status_code not in (200, 204):
            raise KeycloakProvisioningFout("Rol-toewijzing mislukt.", toewijs.status_code)

    return sub


async def deactiveer_keycloak_gebruiker(keycloak_sub: str) -> None:
    """Zet `enabled=false` op het Keycloak-account (verwijdert niet). Best-effort:
    fouten worden gelogd maar niet doorgegooid (cleanup-pad bij een mislukte commit)."""
    try:
        token = await get_provisioning_token()
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{ADMIN_BASE}/users/{keycloak_sub}",
                headers={"Authorization": f"Bearer {token}"},
                json={"enabled": False},
            )
            if resp.status_code not in (200, 204):
                logger.warning("KC-cleanup: deactiveren %s gaf status %s", keycloak_sub, resp.status_code)
    except Exception:  # noqa: BLE001 — cleanup mag de oorspronkelijke fout nooit maskeren
        logger.warning("KC-cleanup: deactiveren van %s mislukt", keycloak_sub)


# De vier tenant-realm-rollen (single source voor rol-swap + verrijking).
TENANT_ROLLEN = ("viewer", "medewerker", "beheerder", "auditor")


async def lees_keycloak_gebruiker(keycloak_sub: str) -> dict | None:
    """Lees `{enabled, rollen}` van een bestaand account (voor lijst-verrijking + guards).

    Best-effort: niet-gevonden of een leesfout → None (de caller behandelt dat als
    'onbekend'; de lijst valt dan terug op None voor rol/enabled). Reads vergen alleen
    `view-users` (geverifieerd 200 met het provisioning-account)."""
    try:
        token = await get_provisioning_token()
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            u = await client.get(f"{ADMIN_BASE}/users/{keycloak_sub}", headers=headers)
            if u.status_code != 200:
                return None
            enabled = bool(u.json().get("enabled", False))
            r = await client.get(f"{ADMIN_BASE}/users/{keycloak_sub}/role-mappings/realm", headers=headers)
            rollen = [x["name"] for x in r.json()] if r.status_code == 200 else []
            return {"enabled": enabled, "rollen": rollen}
    except Exception:  # noqa: BLE001 — verrijking mag de lijst nooit laten crashen
        logger.warning("KC-lees: ophalen van %s mislukt", keycloak_sub)
        return None


async def reset_keycloak_wachtwoord(keycloak_sub: str, tijdelijk_wachtwoord: str) -> None:
    """Zet een nieuw tijdelijk wachtwoord (`temporary=true`) + forceer wijzigen bij de eerste
    login (`UPDATE_PASSWORD` required action) — identiek aan de aanmaak-flow. Raise bij fout.
    Het wachtwoord wordt NOOIT gelogd."""
    token = await get_provisioning_token()
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        pw = await client.put(
            f"{ADMIN_BASE}/users/{keycloak_sub}/reset-password",
            headers=headers,
            json={"type": "password", "value": tijdelijk_wachtwoord, "temporary": True},
        )
        if pw.status_code not in (200, 204):
            raise KeycloakProvisioningFout("Zetten nieuw wachtwoord mislukt.", pw.status_code)
        ra = await client.put(
            f"{ADMIN_BASE}/users/{keycloak_sub}",
            headers=headers,
            json={"requiredActions": ["UPDATE_PASSWORD"]},
        )
        if ra.status_code not in (200, 204):
            raise KeycloakProvisioningFout("Zetten required-action mislukt.", ra.status_code)


async def zet_keycloak_enabled(keycloak_sub: str, enabled: bool) -> None:
    """Schakel een account in/uit (`enabled`-flip). Raise bij fout (i.t.t. de best-effort
    `deactiveer_keycloak_gebruiker`-cleanup, die fouten slikt)."""
    token = await get_provisioning_token()
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{ADMIN_BASE}/users/{keycloak_sub}",
            headers={"Authorization": f"Bearer {token}"},
            json={"enabled": enabled},
        )
        if resp.status_code not in (200, 204):
            raise KeycloakProvisioningFout("Wijzigen account-status mislukt.", resp.status_code)


async def logout_keycloak_gebruiker(keycloak_sub: str) -> None:
    """Kap de lopende sessies van een gebruiker direct af (POST .../logout), zodat 'per
    direct geen toegang' echt direct is en niet pas na token-expiry. Raise bij fout."""
    token = await get_provisioning_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{ADMIN_BASE}/users/{keycloak_sub}/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code not in (200, 204):
            raise KeycloakProvisioningFout("Afkappen sessie mislukt.", resp.status_code)


async def werk_keycloak_gegevens_bij(keycloak_sub: str, *, naam: str, email: str) -> None:
    """Corrigeer naam/e-mail op het Keycloak-account, consistent met de persoon-partij. Raise bij fout.

    De `username` wordt BEWUST niet meegestuurd (LI032): onder `editUsernameAllowed=False` zou een
    username-wijziging (username≠email) de PUT laten falen. Inloggen gaat via e-mail
    (`loginWithEmailAllowed=True`) en de identiteit hangt aan het stabiele `sub`, dus een
    afwijkende username is login-neutraal. Alleen email/firstName/lastName syncen."""
    token = await get_provisioning_token()
    voornaam, achternaam = _splits_naam(naam)
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{ADMIN_BASE}/users/{keycloak_sub}",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": email, "firstName": voornaam, "lastName": achternaam},
        )
        if resp.status_code not in (200, 204):
            raise KeycloakProvisioningFout("Bijwerken gebruikersgegevens mislukt.", resp.status_code)


async def wijzig_keycloak_rol(keycloak_sub: str, nieuwe_rol: str) -> None:
    """Vervang de huidige tenant-realm-rol(len) door `nieuwe_rol`: verwijder elke bestaande
    rol uit `TENANT_ROLLEN` en wijs de nieuwe toe. Raise bij fout. Idempotent als de
    nieuwe rol al de enige is."""
    token = await get_provisioning_token()
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        # Huidige realm-rol-mappings (id+name) → te verwijderen tenant-rollen (≠ de nieuwe).
        huidig = await client.get(f"{ADMIN_BASE}/users/{keycloak_sub}/role-mappings/realm", headers=headers)
        if huidig.status_code != 200:
            raise KeycloakProvisioningFout("Lezen rol-mappings mislukt.", huidig.status_code)
        te_verwijderen = [
            {"id": r["id"], "name": r["name"]}
            for r in huidig.json()
            if r.get("name") in TENANT_ROLLEN and r.get("name") != nieuwe_rol
        ]
        if te_verwijderen:
            weg = await client.request(
                "DELETE", f"{ADMIN_BASE}/users/{keycloak_sub}/role-mappings/realm",
                headers=headers, json=te_verwijderen,
            )
            if weg.status_code not in (200, 204):
                raise KeycloakProvisioningFout("Verwijderen oude rol mislukt.", weg.status_code)
        # Nieuwe rol toewijzen (no-op als al aanwezig — Keycloak accepteert dat).
        rol_resp = await client.get(f"{ADMIN_BASE}/roles/{nieuwe_rol}", headers=headers)
        if rol_resp.status_code != 200:
            raise KeycloakProvisioningFout(f"Realm-rol '{nieuwe_rol}' niet gevonden.", rol_resp.status_code)
        rr = rol_resp.json()
        toewijs = await client.post(
            f"{ADMIN_BASE}/users/{keycloak_sub}/role-mappings/realm",
            headers=headers, json=[{"id": rr["id"], "name": rr["name"]}],
        )
        if toewijs.status_code not in (200, 204):
            raise KeycloakProvisioningFout("Toewijzen nieuwe rol mislukt.", toewijs.status_code)


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
