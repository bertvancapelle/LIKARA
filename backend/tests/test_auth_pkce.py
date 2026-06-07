"""Tests — Keycloak PKCE login/callback (ADR-002), offline (Keycloak gemockt)."""
import base64
import hashlib
import json
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from app.core import pkce
from app.core.config import settings
from app.main import app

_UNRESERVED = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)


# ── Test-fixtures / fakes ────────────────────────────────────────────────────


class FakeRedis:
    """In-memory async Redis-vervanger (set/getdel/incr/expire)."""

    def __init__(self):
        self.store = {}

    async def set(self, k, v, ex=None):
        self.store[k] = v

    async def get(self, k):
        return self.store.get(k)

    async def getdel(self, k):
        return self.store.pop(k, None)

    async def delete(self, k):
        return 1 if self.store.pop(k, None) is not None else 0

    async def incr(self, k):
        self.store[k] = int(self.store.get(k, 0)) + 1
        return self.store[k]

    async def expire(self, k, t):
        return True


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_redis(monkeypatch):
    fr = FakeRedis()

    async def _get():
        return fr

    monkeypatch.setattr("app.api.v1.auth.get_redis", _get)
    return fr


@pytest.fixture
def fail_counter(monkeypatch):
    calls = []

    async def _fake(ip_hash):
        calls.append(ip_hash)

    monkeypatch.setattr("app.api.v1.auth._increment_fail_counter", _fake)
    return calls


def _doe_login(client):
    """Voer /login uit en geef (state, nonce) uit de redirect terug."""
    resp = client.get("/api/v1/auth/login", follow_redirects=False)
    assert resp.status_code == 302
    q = parse_qs(urlparse(resp.headers["location"]).query)
    return q["state"][0], q["nonce"][0]


# ── PKCE-helper ──────────────────────────────────────────────────────────────


def test_pkce_code_challenge_is_s256():
    v = pkce.generate_code_verifier()
    assert 43 <= len(v) <= 128
    assert set(v) <= _UNRESERVED
    verwacht = (
        base64.urlsafe_b64encode(hashlib.sha256(v.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    assert pkce.code_challenge_s256(v) == verwacht
    assert "=" not in pkce.code_challenge_s256(v)


def test_pkce_state_en_nonce_uniek():
    assert pkce.generate_state() != pkce.generate_state()
    assert pkce.generate_nonce() != pkce.generate_nonce()


# ── /login ───────────────────────────────────────────────────────────────────


def test_login_redirect_met_pkce_en_serverside_state(client, fake_redis):
    resp = client.get("/api/v1/auth/login", follow_redirects=False)
    assert resp.status_code == 302
    loc = resp.headers["location"]
    q = parse_qs(urlparse(loc).query)

    assert q["response_type"] == ["code"]
    assert q["scope"] == ["openid"]
    assert q["code_challenge_method"] == ["S256"]
    assert q["client_id"] == [settings.keycloak_client_id]
    assert q["redirect_uri"] == [
        settings.oidc_redirect_uri
        or f"{settings.platform_origin}/api/v1/auth/callback"
    ]
    # verifier/nonce mogen NIET in de browser-zichtbare redirect staan
    assert "code_verifier" not in loc

    state = q["state"][0]
    opslag = json.loads(fake_redis.store[f"auth_login:{state}"])
    assert set(opslag) == {"verifier", "nonce", "next"}
    # challenge in de URL hoort bij de server-side verifier
    assert q["code_challenge"][0] == pkce.code_challenge_s256(opslag["verifier"])
    assert q["nonce"][0] == opslag["nonce"]


def test_login_weigert_onbekende_queryparam(client, fake_redis):
    resp = client.get("/api/v1/auth/login?foo=bar", follow_redirects=False)
    assert resp.status_code == 400
    assert resp.json()["fout"]["code"] == "LOGIN_PARAMS_ONGELDIG"


def test_login_next_open_redirect_genormaliseerd(client, fake_redis):
    resp = client.get(
        "/api/v1/auth/login?next=https://kwaad.example/x", follow_redirects=False
    )
    state = parse_qs(urlparse(resp.headers["location"]).query)["state"][0]
    assert json.loads(fake_redis.store[f"auth_login:{state}"])["next"] == "/"


def test_login_next_relatief_pad_behouden(client, fake_redis):
    resp = client.get("/api/v1/auth/login?next=/dashboard", follow_redirects=False)
    state = parse_qs(urlparse(resp.headers["location"]).query)["state"][0]
    assert json.loads(fake_redis.store[f"auth_login:{state}"])["next"] == "/dashboard"


# ── /callback — succes ───────────────────────────────────────────────────────


def test_callback_succes_zet_cd_session_cookie(client, fake_redis, monkeypatch):
    state, nonce = _doe_login(client)
    gezien = {}

    async def fake_exchange(code, redirect_uri, code_verifier=None):
        gezien["code"] = code
        gezien["verifier"] = code_verifier
        return {"access_token": "acc-token", "id_token": "id-token"}

    def fake_decode_id(token, expected_nonce=None):
        gezien["nonce"] = expected_nonce
        return {"sub": "user-1", "nonce": expected_nonce}

    monkeypatch.setattr("app.api.v1.auth.exchange_code_for_tokens", fake_exchange)
    monkeypatch.setattr("app.api.v1.auth.decode_id_token", fake_decode_id)

    resp = client.get(
        f"/api/v1/auth/callback?code=auth-code-123&state={state}",
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert gezien["code"] == "auth-code-123"
    assert gezien["verifier"]  # PKCE code_verifier server-side meegestuurd
    assert gezien["nonce"] == nonce  # nonce uit login server-side teruggekoppeld

    setcookie = resp.headers["set-cookie"].lower()
    assert f"{settings.cookie_name}=acc-token".lower() in setcookie
    assert "httponly" in setcookie
    assert "secure" in setcookie
    assert "samesite=strict" in setcookie


def test_callback_succes_dan_me_geeft_gebruiker(client, fake_redis, monkeypatch):
    state, _ = _doe_login(client)

    async def fake_exchange(code, redirect_uri, code_verifier=None):
        return {"access_token": "acc-token", "id_token": "id-token"}

    monkeypatch.setattr("app.api.v1.auth.exchange_code_for_tokens", fake_exchange)
    monkeypatch.setattr(
        "app.api.v1.auth.decode_id_token", lambda t, expected_nonce=None: {"sub": "u"}
    )

    r = client.get(
        f"/api/v1/auth/callback?code=x&state={state}", follow_redirects=False
    )
    assert r.status_code == 303

    # /me met de sessie-cookie → gebruiker (decode_token gemockt)
    monkeypatch.setattr(
        "app.middleware.auth.decode_token",
        lambda t: {"sub": "user-1", "tenant_id": "tenant-1", "email": "u@x.nl"},
    )
    client.cookies.set(settings.cookie_name, "acc-token")
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["tenant_id"] == "tenant-1"


def test_me_zonder_cookie_401(client):
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 401
    # ADR-014 B1: 401 in het canonieke fout-envelope (geen detail meer).
    body = me.json()
    assert body["fout"]["code"] == "NIET_GEAUTHENTICEERD"
    assert body["fout"]["http_status"] == 401
    assert body["fout"]["bericht"]
    assert "detail" not in body


# ── /callback — foutpaden ────────────────────────────────────────────────────


def test_callback_state_ongeldig_geen_sessie(client, fake_redis, fail_counter):
    # Syntactisch geldige maar onbekende state → geen sessie, fail-counter+1
    resp = client.get(
        "/api/v1/auth/callback?code=x&state=" + "A" * 24, follow_redirects=False
    )
    assert resp.status_code == 400
    assert resp.json()["fout"]["code"] == "STATE_ONGELDIG"
    assert "set-cookie" not in resp.headers
    assert fail_counter  # IP-gepseudonimiseerde teller aangeroepen


def test_callback_replay_state_is_eenmalig(client, fake_redis, monkeypatch):
    state, _ = _doe_login(client)

    async def fake_exchange(code, redirect_uri, code_verifier=None):
        return {"access_token": "acc", "id_token": "id"}

    monkeypatch.setattr("app.api.v1.auth.exchange_code_for_tokens", fake_exchange)
    monkeypatch.setattr(
        "app.api.v1.auth.decode_id_token", lambda t, expected_nonce=None: {"sub": "u"}
    )

    eerste = client.get(
        f"/api/v1/auth/callback?code=x&state={state}", follow_redirects=False
    )
    assert eerste.status_code == 303
    tweede = client.get(
        f"/api/v1/auth/callback?code=x&state={state}", follow_redirects=False
    )
    assert tweede.status_code == 400
    assert tweede.json()["fout"]["code"] == "STATE_ONGELDIG"


def test_callback_token_exchange_mislukt(client, fake_redis, fail_counter, monkeypatch):
    state, _ = _doe_login(client)

    async def fake_exchange_fail(code, redirect_uri, code_verifier=None):
        raise RuntimeError("keycloak onbereikbaar")

    monkeypatch.setattr("app.api.v1.auth.exchange_code_for_tokens", fake_exchange_fail)

    resp = client.get(
        f"/api/v1/auth/callback?code=x&state={state}", follow_redirects=False
    )
    assert resp.status_code == 502
    assert resp.json()["fout"]["code"] == "TOKEN_UITWISSELING_MISLUKT"
    assert "set-cookie" not in resp.headers
    assert fail_counter


def test_callback_id_token_ongeldig(client, fake_redis, fail_counter, monkeypatch):
    state, _ = _doe_login(client)

    async def fake_exchange(code, redirect_uri, code_verifier=None):
        return {"access_token": "acc", "id_token": "id"}

    def fake_decode_bad(token, expected_nonce=None):
        raise ValueError("nonce/aud/exp ongeldig")

    monkeypatch.setattr("app.api.v1.auth.exchange_code_for_tokens", fake_exchange)
    monkeypatch.setattr("app.api.v1.auth.decode_id_token", fake_decode_bad)

    resp = client.get(
        f"/api/v1/auth/callback?code=x&state={state}", follow_redirects=False
    )
    assert resp.status_code == 401
    assert resp.json()["fout"]["code"] == "ID_TOKEN_ONGELDIG"
    assert "set-cookie" not in resp.headers
    assert fail_counter


def test_callback_keycloak_error_param(client, fake_redis):
    resp = client.get(
        "/api/v1/auth/callback?error=access_denied&error_description=geweigerd&state="
        + "A" * 24,
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert resp.json()["fout"]["code"] == "AUTH_GEWEIGERD"
    assert "set-cookie" not in resp.headers


def test_callback_weigert_onbekende_queryparam(client, fake_redis):
    resp = client.get(
        "/api/v1/auth/callback?code=x&state=" + "A" * 24 + "&foo=bar",
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert resp.json()["fout"]["code"] == "CALLBACK_PARAMS_ONGELDIG"


# ── /auth/refresh (OP-3 / ADR-015) ───────────────────────────────────────────


def test_callback_bewaart_refresh_token_in_redis(client, fake_redis, monkeypatch):
    """Regressie + opvang: callback gooit het refresh_token niet meer weg."""
    state, _ = _doe_login(client)

    async def fake_exchange(code, redirect_uri, code_verifier=None):
        return {"access_token": "acc", "id_token": "id", "refresh_token": "rt-1"}

    monkeypatch.setattr("app.api.v1.auth.exchange_code_for_tokens", fake_exchange)
    monkeypatch.setattr(
        "app.api.v1.auth.decode_id_token", lambda t, expected_nonce=None: {"sub": "u"}
    )

    resp = client.get(f"/api/v1/auth/callback?code=c&state={state}", follow_redirects=False)
    assert resp.status_code == 303
    setcookie = resp.headers["set-cookie"].lower()
    assert settings.refresh_cookie_name.lower() in setcookie  # cd_refresh-cookie gezet
    handles = {k: v for k, v in fake_redis.store.items() if k.startswith("auth_refresh:")}
    opgeslagen = json.loads(list(handles.values())[0])  # JSON {refresh_token, id_token}
    assert opgeslagen["refresh_token"] == "rt-1"
    assert opgeslagen["id_token"] == "id"  # id_token meebewaard voor logout-hint


def test_refresh_geldig_handle_rouleert_en_zet_nieuwe_sessie(client, fake_redis, monkeypatch):
    fake_redis.store["auth_refresh:sid-1"] = json.dumps(
        {"refresh_token": "rt-old", "id_token": "id-old"}
    )
    client.cookies.set(settings.refresh_cookie_name, "sid-1")

    async def fake_refresh(refresh_token):
        assert refresh_token == "rt-old"
        return {"access_token": "acc-new", "refresh_token": "rt-new", "id_token": "id-new"}

    monkeypatch.setattr("app.api.v1.auth.refresh_access_token", fake_refresh)

    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 204
    setcookie = resp.headers["set-cookie"].lower()
    assert f"{settings.cookie_name}=acc-new".lower() in setcookie  # nieuw cd_session
    assert "httponly" in setcookie
    # rotatie: nieuwste refresh + ververst id_token bewaard
    opgeslagen = json.loads(fake_redis.store["auth_refresh:sid-1"])
    assert opgeslagen["refresh_token"] == "rt-new"
    assert opgeslagen["id_token"] == "id-new"


def test_refresh_zonder_cookie_401_canoniek(client, fake_redis):
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
    body = resp.json()
    assert body["fout"]["code"] == "NIET_GEAUTHENTICEERD"
    assert "detail" not in body


def test_refresh_onbekend_handle_401(client, fake_redis):
    client.cookies.set(settings.refresh_cookie_name, "sid-x")
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["fout"]["code"] == "NIET_GEAUTHENTICEERD"


def test_refresh_keycloak_weigert_ruimt_handle_op(client, fake_redis, monkeypatch):
    fake_redis.store["auth_refresh:sid-2"] = "rt-bad"
    client.cookies.set(settings.refresh_cookie_name, "sid-2")

    async def fake_refresh_fail(refresh_token):
        raise RuntimeError("token revoked")

    monkeypatch.setattr("app.api.v1.auth.refresh_access_token", fake_refresh_fail)

    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
    assert resp.json()["fout"]["code"] == "NIET_GEAUTHENTICEERD"
    assert "auth_refresh:sid-2" not in fake_redis.store  # onbruikbaar handle opgeruimd (B5)


# ── /auth/logout — RP-initiated (OP-4) ───────────────────────────────────────


def test_logout_wist_beide_cookies_en_redis_handle(client, fake_redis):
    fake_redis.store["auth_refresh:sid-9"] = "rt"
    client.cookies.set(settings.refresh_cookie_name, "sid-9")

    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    body = resp.json()

    # Redis-refresh-handle verwijderd (ADR-015-raakvlak)
    assert "auth_refresh:sid-9" not in fake_redis.store

    # beide cookies gewist
    rauw = " ".join(resp.headers.get_list("set-cookie")).lower()
    assert f"{settings.cookie_name}=".lower() in rauw
    assert f"{settings.refresh_cookie_name}=".lower() in rauw

    # Keycloak end-session-URL: endpoint + post_logout_redirect_uri + client_id
    url = body["keycloak_logout_url"]
    assert "/protocol/openid-connect/logout" in url
    assert "post_logout_redirect_uri=" in url
    assert f"client_id={settings.keycloak_client_id}" in url


def test_logout_idempotent_zonder_sessie(client, fake_redis):
    # Geen cd_refresh-cookie / geen handle → geen fout, wel keycloak_logout_url.
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert "keycloak_logout_url" in resp.json()


def test_logout_redirect_uri_is_serverconfig_geen_userinput(client, fake_redis):
    # post_logout_redirect_uri komt uit config (platform_origin/login), niet uit
    # een query-param → geen open redirect.
    resp = client.post("/api/v1/auth/logout?post_logout_redirect_uri=https://kwaad.example")
    url = resp.json()["keycloak_logout_url"]
    assert "kwaad.example" not in url
    q = parse_qs(urlparse(url).query)
    assert q["post_logout_redirect_uri"][0] == f"{settings.platform_origin}/login"


# ── 403 TENANT_MISMATCH — canoniek (CD009 / ADR-014) ─────────────────────────


def test_me_token_zonder_tenant_403_canoniek(client, monkeypatch):
    # Geldig token maar zonder tenant_id-claim → auth-grens 403, canoniek envelope.
    monkeypatch.setattr("app.middleware.auth.decode_token", lambda t: {"sub": "u"})
    client.cookies.set(settings.cookie_name, "acc-token")
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 403
    body = me.json()
    assert body["fout"]["code"] == "TENANT_MISMATCH"
    assert body["fout"]["http_status"] == 403
    assert "detail" not in body  # geen oude detail-vorm meer


def test_logout_met_id_token_zet_hint_in_url(client, fake_redis):
    # Handle mét id_token → id_token_hint in de end-session-URL (naadloze logout).
    fake_redis.store["auth_refresh:sid-h"] = json.dumps(
        {"refresh_token": "rt", "id_token": "ID-TOK"}
    )
    client.cookies.set(settings.refresh_cookie_name, "sid-h")
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    url = resp.json()["keycloak_logout_url"]
    q = parse_qs(urlparse(url).query)
    assert q["id_token_hint"][0] == "ID-TOK"
    assert "auth_refresh:sid-h" not in fake_redis.store  # handle opgeruimd


def test_logout_zonder_id_token_valt_terug_op_client_id(client, fake_redis):
    # Oud/edge handle zonder id_token → geen hint, client_id-fallback (backward-compat).
    fake_redis.store["auth_refresh:sid-n"] = json.dumps({"refresh_token": "rt", "id_token": None})
    client.cookies.set(settings.refresh_cookie_name, "sid-n")
    url = client.post("/api/v1/auth/logout").json()["keycloak_logout_url"]
    q = parse_qs(urlparse(url).query)
    assert "id_token_hint" not in q
    assert q["client_id"][0] == settings.keycloak_client_id
