"""Integratie-tests — blokkade-overzicht-route (CD016, offline guard-patroon).

Gedekt: `LEZEN`-gating (401 zonder sessie, 403 zonder rol), allowlist-validatie op
de API-rand (ongeldig `status`/`sort`/`order` → 422), en de statische route-volgorde
(`/overzicht` wordt niet als UUID geparsed).
"""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings

TENANT_A = "11111111-1111-1111-1111-111111111111"

_ITEM = {
    "id": uuid.uuid4(),
    "applicatie_id": uuid.uuid4(),
    "applicatie_naam": "Zaaksysteem",
    "vraag_code": "A1",
    "status": "open",
    "toelichting": None,
    "eigenaar": None,
    "opgelost_op": None,
    "gewijzigd_op": datetime(2026, 6, 7, tzinfo=timezone.utc),
}


def _maak_app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.blokkade import router
    from services import blokkade_service as svc

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)

    async def _ok_overzicht(*a, **k):
        return ([_ITEM], None)

    monkeypatch.setattr(svc, "lijst_overzicht", _ok_overzicht)

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
    resp = _client(app, met_sessie=False).get("/api/v1/blokkades/overzicht")
    assert resp.status_code == 401


def test_zonder_rol_geeft_403(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload([]))
    resp = _client(app).get("/api/v1/blokkades/overzicht")
    assert resp.status_code == 403
    assert resp.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


@pytest.mark.parametrize("rol", ["viewer", "medewerker", "beheerder", "auditor"])
def test_lezen_rol_geeft_200(monkeypatch, rol):
    app, _ = _maak_app(monkeypatch, _payload([rol]))
    resp = _client(app).get("/api/v1/blokkades/overzicht")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["items"][0]["applicatie_naam"] == "Zaaksysteem"
    assert body["volgende_cursor"] is None


def test_default_en_expliciete_filters_200(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload(["viewer"]))
    client = _client(app)
    assert client.get("/api/v1/blokkades/overzicht").status_code == 200
    assert client.get(
        "/api/v1/blokkades/overzicht?status=opgelost&sort=gewijzigd_op&order=desc"
    ).status_code == 200


def test_ongeldige_status_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload(["viewer"]))
    resp = _client(app).get("/api/v1/blokkades/overzicht?status=onzin")
    assert resp.status_code == 422


def test_onbekend_sortveld_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload(["viewer"]))
    resp = _client(app).get("/api/v1/blokkades/overzicht?sort=geheim")
    assert resp.status_code == 422


def test_ongeldige_order_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload(["viewer"]))
    resp = _client(app).get("/api/v1/blokkades/overzicht?order=zijwaarts")
    assert resp.status_code == 422


def test_route_volgorde_overzicht_niet_als_uuid(monkeypatch):
    """`/overzicht` matcht de statische route, niet `/{blokkade_id}` (geen 422-UUID)."""
    app, _ = _maak_app(monkeypatch, _payload(["viewer"]))
    resp = _client(app).get("/api/v1/blokkades/overzicht")
    assert resp.status_code == 200
