"""Tests — Applicatie opties-endpoint (read-only enum-metadata)."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings

TENANT_A = "11111111-1111-1111-1111-111111111111"


# ── Pure helper (single source) ─────────────────────────────────────────────

def test_enum_opties_geeft_exact_de_enum_waarden():
    from models.models import HostingModel, Migratiepad, NiveauEnum
    from services.applicatie_service import enum_opties

    o = enum_opties()
    assert o["hostingmodel"] == [e.value for e in HostingModel]
    assert o["migratiepad"] == [e.value for e in Migratiepad]
    assert o["complexiteit"] == [e.value for e in NiveauEnum]
    assert o["prioriteit"] == [e.value for e in NiveauEnum]
    # spotchecks
    assert "saas" in o["hostingmodel"]
    assert "tijdelijk_gedeeld" in o["migratiepad"]
    assert o["complexiteit"] == ["laag", "midden", "hoog"]


# ── Route ───────────────────────────────────────────────────────────────────

def _maak_app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from routes.applicatie import router

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)
    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.include_router(router, prefix="/api/v1")
    return app


def _payload(rol):
    return {"sub": "u-1", "tenant_id": TENANT_A, "realm_access": {"roles": [rol]}}


def test_opties_route_geeft_enums_voor_viewer(monkeypatch):
    app = _maak_app(monkeypatch, _payload("viewer"))
    client = TestClient(app)
    client.cookies.set(settings.cookie_name, "dummy")

    resp = client.get("/api/v1/applicaties/opties")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) == {"hostingmodel", "migratiepad", "complexiteit", "prioriteit"}
    assert "saas" in body["hostingmodel"]
    assert body["prioriteit"] == ["laag", "midden", "hoog"]


def test_opties_route_vereist_auth(monkeypatch):
    app = _maak_app(monkeypatch, _payload("viewer"))
    client = TestClient(app)  # geen sessie-cookie
    resp = client.get("/api/v1/applicaties/opties")
    assert resp.status_code == 401


def test_opties_pad_wordt_niet_als_uuid_geparsed(monkeypatch):
    # Bevestigt de route-ordening: 'opties' raakt niet de /{id}-route (zou 422 geven).
    app = _maak_app(monkeypatch, _payload("beheerder"))
    client = TestClient(app)
    client.cookies.set(settings.cookie_name, "dummy")
    resp = client.get("/api/v1/applicaties/opties")
    assert resp.status_code == 200
