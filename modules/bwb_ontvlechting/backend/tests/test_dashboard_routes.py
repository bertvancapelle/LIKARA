"""Integratie-tests — dashboard-route (CD014, #9).

Offline guard-integratiepatroon (complidata-tests): mini-`FastAPI()` met de echte
router + handlers; `decode_token` gemonkeypatcht; `get_tenant_session` overschreven
(geen DB); de service gestubd. Gedekt: geen sessie → 401, geauthenticeerd zonder
matchende rol → 403, viewer (LEZEN) → 200 met de juiste respons-vorm.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings

TENANT_A = "11111111-1111-1111-1111-111111111111"

_DASHBOARD = {
    "lifecycle_telling": {
        "concept": 2,
        "in_inventarisatie": 1,
        "geblokkeerd": 0,
        "migratieklaar": 0,
    },
    "open_blokkades": 0,
    "recent_gewijzigd": [],
}


def _maak_app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.dashboard import router
    from services import dashboard_service as svc
    from types import SimpleNamespace

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)

    async def _ok_dashboard(*a, **k):
        return _DASHBOARD

    monkeypatch.setattr(svc, "haal_dashboard", _ok_dashboard)

    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.include_router(router, prefix="/api/v1")

    async def _fake_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_tenant_session] = _fake_session
    return app, svc


def _client(app, *, met_sessie=True):
    client = TestClient(app)
    if met_sessie:
        client.cookies.set(settings.cookie_name, "dummy-token")
    return client


def _payload(rollen):
    return {"sub": "u-1", "tenant_id": TENANT_A, "realm_access": {"roles": rollen}}


def test_geen_sessie_geeft_401(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload(["viewer"]))
    client = _client(app, met_sessie=False)
    resp = client.get("/api/v1/dashboard")
    assert resp.status_code == 401


def test_geauthenticeerd_zonder_rol_geeft_403(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload([]))
    client = _client(app)
    resp = client.get("/api/v1/dashboard")
    assert resp.status_code == 403
    assert resp.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


@pytest.mark.parametrize("rol", ["viewer", "medewerker", "beheerder", "auditor"])
def test_lezen_rol_geeft_200(monkeypatch, rol):
    """Elke tenant-rol heeft LEZEN op APPLICATIE → dashboard toegankelijk."""
    app, _ = _maak_app(monkeypatch, _payload([rol]))
    client = _client(app)
    resp = client.get("/api/v1/dashboard")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body["lifecycle_telling"]) == {
        "concept",
        "in_inventarisatie",
        "geblokkeerd",
        "migratieklaar",
    }
    assert body["open_blokkades"] == 0
    assert body["recent_gewijzigd"] == []
