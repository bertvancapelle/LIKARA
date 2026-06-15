"""Integratie-tests — Gebruikersgroep-routes (P5-vervolg, offline guard-patroon)."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings

TENANT_A = "11111111-1111-1111-1111-111111111111"
_ID = "22222222-2222-2222-2222-222222222222"
_APP_ID = "33333333-3333-3333-3333-333333333333"

_CREATE_BODY = {"applicatie_id": _APP_ID, "organisatie": "Gemeente Veldendam"}


def _fake_groep():
    return SimpleNamespace(
        id=uuid.UUID(_ID),
        applicatie_id=uuid.UUID(_APP_ID),
        organisatie="Gemeente Veldendam",
        afdeling=None,
        aantal_gebruikers=None,
        created_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
    )


def _maak_app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.gebruikersgroep import router
    from services import gebruikersgroep_service as svc
    from services.errors import NietGevonden, niet_gevonden_handler

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)

    async def _ok_lijst(*a, **k):
        return ([_fake_groep()], None)

    async def _ok_obj(*a, **k):
        return _fake_groep()

    async def _ok_none(*a, **k):
        return None

    monkeypatch.setattr(svc, "lijst", _ok_lijst)
    monkeypatch.setattr(svc, "haal_op", _ok_obj)
    monkeypatch.setattr(svc, "lees_detail", _ok_obj)  # ADR-023: GET /{id} → lees_detail
    monkeypatch.setattr(svc, "maak_aan", _ok_obj)
    monkeypatch.setattr(svc, "werk_bij", _ok_obj)
    monkeypatch.setattr(svc, "verwijder", _ok_none)

    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.add_exception_handler(NietGevonden, niet_gevonden_handler)
    app.include_router(router, prefix="/api/v1")

    async def _fake_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_tenant_session] = _fake_session
    return app, svc


def _client(app, *, met_sessie=True):
    client = TestClient(app)
    if met_sessie:
        client.cookies.set(settings.cookie_name, "dummy")
    return client


def _payload(rol):
    return {"sub": "u-1", "tenant_id": TENANT_A, "realm_access": {"roles": [rol]}}


_ROL_RECHTEN = {
    "viewer": set("L"),
    "medewerker": set("LAW"),
    "beheerder": set("LAWV"),
    "auditor": set("L"),
}

_ENDPOINTS = [
    ("L", "GET", "/api/v1/gebruikersgroepen", None, 200),
    ("L", "GET", f"/api/v1/gebruikersgroepen/{_ID}", None, 200),
    ("A", "POST", "/api/v1/gebruikersgroepen", _CREATE_BODY, 201),
    ("W", "PATCH", f"/api/v1/gebruikersgroepen/{_ID}", {"afdeling": "Burgerzaken"}, 200),
    ("V", "DELETE", f"/api/v1/gebruikersgroepen/{_ID}", None, 204),
]


@pytest.mark.parametrize("rol", ["viewer", "medewerker", "beheerder", "auditor"])
@pytest.mark.parametrize("actie,method,pad,body,ok_code", _ENDPOINTS)
def test_rolmatrix(monkeypatch, rol, actie, method, pad, body, ok_code):
    app, _ = _maak_app(monkeypatch, _payload(rol))
    client = _client(app)
    resp = client.request(method, pad, json=body)
    if actie in _ROL_RECHTEN[rol]:
        assert resp.status_code == ok_code, resp.text
    else:
        assert resp.status_code == 403, resp.text
        assert resp.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


def test_geen_sessie_geeft_401(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("beheerder"))
    resp = _client(app, met_sessie=False).get("/api/v1/gebruikersgroepen")
    assert resp.status_code == 401


def test_kruis_tenant_id_geeft_404(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("medewerker"))
    from services.errors import NietGevonden

    async def _raise(*a, **k):
        raise NietGevonden("gebruikersgroep", _ID)

    monkeypatch.setattr(svc, "lees_detail", _raise)  # ADR-023: GET /{id} → lees_detail
    resp = _client(app).get(f"/api/v1/gebruikersgroepen/{_ID}")
    assert resp.status_code == 404
    assert resp.json()["fout"]["code"] == "NIET_GEVONDEN"


def test_ouder_buiten_tenant_bij_aanmaken_geeft_404(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("medewerker"))
    from services.errors import NietGevonden

    async def _raise(*a, **k):
        raise NietGevonden("applicatie", _APP_ID)

    monkeypatch.setattr(svc, "maak_aan", _raise)
    resp = _client(app).post("/api/v1/gebruikersgroepen", json=_CREATE_BODY)
    assert resp.status_code == 404
    assert resp.json()["fout"]["code"] == "NIET_GEVONDEN"


def test_aantal_negatief_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("medewerker"))
    body = {**_CREATE_BODY, "aantal_gebruikers": -3}
    resp = _client(app).post("/api/v1/gebruikersgroepen", json=body)
    assert resp.status_code == 422


def test_lijst_filter_applicatie_id_doorgegeven(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("viewer"))
    ontvangen = {}

    async def _capture(session, tenant_id, *, limit, after, applicatie_id, sort=None, order=None):
        ontvangen["applicatie_id"] = applicatie_id
        return ([], None)

    monkeypatch.setattr(svc, "lijst", _capture)
    resp = _client(app).get(f"/api/v1/gebruikersgroepen?applicatie_id={_APP_ID}")
    assert resp.status_code == 200
    assert str(ontvangen["applicatie_id"]) == _APP_ID
