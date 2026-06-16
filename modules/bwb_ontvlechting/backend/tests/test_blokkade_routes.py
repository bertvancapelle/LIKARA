"""Integratie-tests — Blokkade-routes (ADR-013, offline guard-patroon).

Afwijkend CRUD: alleen GET (lijst + id) en PATCH; geen POST/DELETE.
"""
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
_SCORE_ID = "44444444-4444-4444-4444-444444444444"
_VRAAG_ID = "55555555-5555-5555-5555-555555555555"


def _fake_blokkade():
    return SimpleNamespace(
        id=uuid.UUID(_ID),
        checklistscore_id=uuid.UUID(_SCORE_ID),
        component_id=uuid.UUID(_APP_ID),
        status="open",
        toelichting=None,
        eigenaar=None,
        opgelost_op=None,
        created_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        # Herkomst-verrijking (per-component lijst → BlokkadeLijstItem).
        checklistvraag_id=uuid.UUID(_VRAAG_ID),
        vraag_code="1.1",
        vraag="Wat is de naam van de applicatie?",
        score="nee",
    )


def _maak_app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.blokkade import router
    from services import blokkade_service as svc
    from services.errors import (
        NietGevonden,
        OngeldigeStatusovergang,
        niet_gevonden_handler,
        ongeldige_statusovergang_handler,
    )

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)

    async def _ok_lijst(*a, **k):
        return ([_fake_blokkade()], None)

    async def _ok_obj(*a, **k):
        return _fake_blokkade()

    monkeypatch.setattr(svc, "lijst", _ok_lijst)
    monkeypatch.setattr(svc, "haal_op", _ok_obj)
    monkeypatch.setattr(svc, "werk_bij", _ok_obj)

    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.add_exception_handler(NietGevonden, niet_gevonden_handler)
    app.add_exception_handler(OngeldigeStatusovergang, ongeldige_statusovergang_handler)
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
    ("L", "GET", "/api/v1/blokkades", None, 200),
    ("L", "GET", f"/api/v1/blokkades/{_ID}", None, 200),
    ("W", "PATCH", f"/api/v1/blokkades/{_ID}", {"status": "in_behandeling"}, 200),
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


def test_handmatig_opgelost_geeft_409(monkeypatch):
    # ADR-016: handmatige status=opgelost → 409 canoniek (auto-pad ongemoeid).
    app, svc = _maak_app(monkeypatch, _payload("medewerker"))
    from services.errors import OngeldigeStatusovergang

    async def _raise(*a, **k):
        raise OngeldigeStatusovergang("open", "opgelost")

    monkeypatch.setattr(svc, "werk_bij", _raise)
    resp = _client(app).patch(f"/api/v1/blokkades/{_ID}", json={"status": "opgelost"})
    assert resp.status_code == 409
    assert resp.json()["fout"]["code"] == "ONGELDIGE_STATUSOVERGANG"


def test_geen_post_op_collectie(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("beheerder"))
    resp = _client(app).post("/api/v1/blokkades", json={"status": "open"})
    assert resp.status_code == 405  # Method Not Allowed (geen handmatige aanmaak)


def test_geen_delete_op_item(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("beheerder"))
    resp = _client(app).delete(f"/api/v1/blokkades/{_ID}")
    assert resp.status_code == 405  # Method Not Allowed (geen handmatige verwijdering)


def test_geen_sessie_geeft_401(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("beheerder"))
    resp = _client(app, met_sessie=False).get("/api/v1/blokkades")
    assert resp.status_code == 401


def test_kruis_tenant_id_geeft_404(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("medewerker"))
    from services.errors import NietGevonden

    async def _raise(*a, **k):
        raise NietGevonden("blokkade", _ID)

    monkeypatch.setattr(svc, "haal_op", _raise)
    resp = _client(app).get(f"/api/v1/blokkades/{_ID}")
    assert resp.status_code == 404
    assert resp.json()["fout"]["code"] == "NIET_GEVONDEN"


def test_ongeldige_cursor_geeft_400(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("viewer"))

    async def _raise(*a, **k):
        raise ValueError("ongeldige cursor")

    monkeypatch.setattr(svc, "lijst", _raise)
    resp = _client(app).get("/api/v1/blokkades?after=onzin")
    assert resp.status_code == 400
    assert resp.json()["fout"]["code"] == "ONGELDIGE_CURSOR"


def test_lijst_filters_doorgegeven(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("viewer"))
    ontvangen = {}

    async def _capture(session, tenant_id, *, limit, after, component_id, status, sort=None, order=None):
        ontvangen["component_id"] = component_id
        ontvangen["status"] = status
        return ([], None)

    monkeypatch.setattr(svc, "lijst", _capture)
    resp = _client(app).get(f"/api/v1/blokkades?component_id={_APP_ID}&status=open")
    assert resp.status_code == 200
    assert str(ontvangen["component_id"]) == _APP_ID
    assert ontvangen["status"].value == "open"


def test_ongeldige_status_filter_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("viewer"))
    resp = _client(app).get("/api/v1/blokkades?status=onzin")
    assert resp.status_code == 422
