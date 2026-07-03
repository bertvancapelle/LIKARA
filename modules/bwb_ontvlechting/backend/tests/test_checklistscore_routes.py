"""Integratie-tests — Checklistscore-routes (ADR-013, offline guard-patroon)."""
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
_VRAAG_ID = "44444444-4444-4444-4444-444444444444"

_CREATE_BODY = {"component_id": _APP_ID, "checklistvraag_id": _VRAAG_ID, "score": "nee"}


def _fake_score():
    return SimpleNamespace(
        id=uuid.UUID(_ID),
        component_id=uuid.UUID(_APP_ID),
        checklistvraag_id=uuid.UUID(_VRAAG_ID),
        score="nee",
        bevinding=None,
        verantwoordelijke_id=None,
        verantwoordelijke_naam=None,
        verantwoordelijke_afdeling=None,
        actie=None,
        antwoord_waarde=None,
        created_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
    )


def _maak_app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.checklistscore import router
    from services import checklistscore_service as svc
    from services.errors import (
        ChecklistscoreConflict,
        NietGevonden,
        checklistscore_conflict_handler,
        niet_gevonden_handler,
    )

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)

    async def _ok_lijst(*a, **k):
        return ([_fake_score()], None)

    async def _ok_obj(*a, **k):
        return _fake_score()

    async def _ok_none(*a, **k):
        return None

    async def _verrijk_noop(session, tid, obj):  # ADR-037: lees_detail verrijkt via _verrijk
        return obj

    monkeypatch.setattr(svc, "lijst", _ok_lijst)
    monkeypatch.setattr(svc, "haal_op", _ok_obj)
    monkeypatch.setattr(svc, "maak_aan", _ok_obj)
    monkeypatch.setattr(svc, "werk_bij", _ok_obj)
    monkeypatch.setattr(svc, "verwijder", _ok_none)
    monkeypatch.setattr(svc, "_verrijk", _verrijk_noop)

    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.add_exception_handler(NietGevonden, niet_gevonden_handler)
    app.add_exception_handler(ChecklistscoreConflict, checklistscore_conflict_handler)
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
    ("L", "GET", "/api/v1/checklistscores", None, 200),
    ("L", "GET", f"/api/v1/checklistscores/{_ID}", None, 200),
    ("A", "POST", "/api/v1/checklistscores", _CREATE_BODY, 201),
    ("W", "PATCH", f"/api/v1/checklistscores/{_ID}", {"score": "ja"}, 200),
    ("V", "DELETE", f"/api/v1/checklistscores/{_ID}", None, 204),
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
    resp = _client(app, met_sessie=False).get("/api/v1/checklistscores")
    assert resp.status_code == 401


def test_onbekende_checklistvraag_id_geeft_404(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("medewerker"))
    from services.errors import NietGevonden

    async def _raise(*a, **k):
        raise NietGevonden("checklistvraag", str(uuid.uuid4()))

    monkeypatch.setattr(svc, "maak_aan", _raise)
    resp = _client(app).post("/api/v1/checklistscores", json=_CREATE_BODY)
    assert resp.status_code == 404
    assert resp.json()["fout"]["code"] == "NIET_GEVONDEN"


def test_dubbele_score_geeft_409(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("medewerker"))
    from services.errors import ChecklistscoreConflict

    async def _raise(*a, **k):
        raise ChecklistscoreConflict()

    monkeypatch.setattr(svc, "maak_aan", _raise)
    resp = _client(app).post("/api/v1/checklistscores", json=_CREATE_BODY)
    assert resp.status_code == 409
    assert resp.json()["fout"]["code"] == "CHECKLISTSCORE_BESTAAT_AL"


def test_kruis_tenant_id_geeft_404(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("medewerker"))
    from services.errors import NietGevonden

    async def _raise(*a, **k):
        raise NietGevonden("checklistscore", _ID)

    monkeypatch.setattr(svc, "haal_op", _raise)
    resp = _client(app).get(f"/api/v1/checklistscores/{_ID}")
    assert resp.status_code == 404


def test_ongeldige_cursor_geeft_400(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("viewer"))

    async def _raise(*a, **k):
        raise ValueError("ongeldige cursor")

    monkeypatch.setattr(svc, "lijst", _raise)
    resp = _client(app).get("/api/v1/checklistscores?after=onzin")
    assert resp.status_code == 400
    assert resp.json()["fout"]["code"] == "ONGELDIGE_CURSOR"


def test_score_verplicht_in_body_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("medewerker"))
    body = {"component_id": _APP_ID, "checklistvraag_id": _VRAAG_ID}  # geen score
    resp = _client(app).post("/api/v1/checklistscores", json=body)
    assert resp.status_code == 422


def test_lijst_filter_component_id_doorgegeven(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("viewer"))
    ontvangen = {}

    async def _capture(session, tenant_id, *, limit, after, component_id, sort=None, order=None):
        ontvangen["component_id"] = component_id
        return ([], None)

    monkeypatch.setattr(svc, "lijst", _capture)
    resp = _client(app).get(f"/api/v1/checklistscores?component_id={_APP_ID}")
    assert resp.status_code == 200
    assert str(ontvangen["component_id"]) == _APP_ID
