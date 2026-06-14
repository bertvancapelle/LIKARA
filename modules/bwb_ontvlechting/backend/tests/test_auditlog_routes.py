"""ADR-006 Fase E — auditlog-lees-route (offline, gemockte service).

Dekt: RBAC (alleen AUDITLOG-LEZEN: beheerder/auditor), correlatie-gegroepeerde
response-vorm, 400 bij een ongeldige cursor, en dat er géén schrijf-routes zijn
(append-only).
"""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings

TENANT_A = "11111111-1111-1111-1111-111111111111"
_CORR = "55555555-5555-5555-5555-555555555555"
_COMP = "33333333-3333-3333-3333-333333333333"


def _fake_record(actie, entiteit_type, entiteit_id):
    return {
        "id": uuid.uuid4(),
        "tijdstip": datetime(2026, 6, 14, 10, 0, tzinfo=timezone.utc),
        "actor_sub": "u-1",
        "actor_email": "u1@example.test",
        "entiteit_type": entiteit_type,
        "entiteit_id": uuid.UUID(entiteit_id),
        "actie": actie,
        "wijziging": {"score": {"oud": "ja", "nieuw": "nee"}},
        "correlatie_id": uuid.UUID(_CORR),
        "record_hash": "h" * 64,
        "vorige_hash": None,
    }


def _fake_gebeurtenis():
    """Eén handeling: driver (checklistscore) + afgeleide gevolgen (blokkade,
    component_profiel) onder hetzelfde correlatie_id."""
    return {
        "correlatie_id": uuid.UUID(_CORR),
        "tijdstip": datetime(2026, 6, 14, 10, 0, tzinfo=timezone.utc),
        "actor_sub": "u-1",
        "actor_email": "u1@example.test",
        "records": [
            _fake_record("update", "checklistscore", str(uuid.uuid4())),
            _fake_record("derive", "blokkade", _COMP),
            _fake_record("derive", "component_profiel", _COMP),
        ],
    }


def _maak_app(monkeypatch, payload, *, lijst_impl=None):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.auditlog import router
    from services import auditlog_service as svc

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)

    async def _ok_lijst(*a, **k):
        return ([_fake_gebeurtenis()], None)

    monkeypatch.setattr(svc, "lijst", lijst_impl or _ok_lijst)

    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.include_router(router, prefix="/api/v1")

    async def _fake_session():
        from types import SimpleNamespace
        yield SimpleNamespace()

    app.dependency_overrides[get_tenant_session] = _fake_session
    return app, svc


def _client(app):
    client = TestClient(app)
    client.cookies.set(settings.cookie_name, "dummy")
    return client


def _payload(rol):
    return {"sub": "u-1", "tenant_id": TENANT_A, "realm_access": {"roles": [rol]}}


@pytest.mark.parametrize("rol,mag_lezen", [
    ("viewer", False), ("medewerker", False), ("beheerder", True), ("auditor", True),
])
def test_rbac_alleen_beheerder_en_auditor_lezen(monkeypatch, rol, mag_lezen):
    app, _ = _maak_app(monkeypatch, _payload(rol))
    resp = _client(app).get("/api/v1/auditlog")
    if mag_lezen:
        assert resp.status_code == 200, resp.text
    else:
        assert resp.status_code == 403, resp.text
        assert resp.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


def test_correlatie_groepering_in_response(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("auditor"))
    resp = _client(app).get("/api/v1/auditlog")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["volgende_cursor"] is None
    geb = body["items"][0]
    assert geb["correlatie_id"] == _CORR
    # Driver + afgeleide gevolgen samen onder één gebeurtenis.
    acties = [r["actie"] for r in geb["records"]]
    assert acties == ["update", "derive", "derive"]
    typen = {r["entiteit_type"] for r in geb["records"]}
    assert typen == {"checklistscore", "blokkade", "component_profiel"}


def test_ongeldige_cursor_geeft_400(monkeypatch):
    async def _raise(*a, **k):
        raise ValueError("ongeldige cursor")

    app, _ = _maak_app(monkeypatch, _payload("beheerder"), lijst_impl=_raise)
    resp = _client(app).get("/api/v1/auditlog?after=rommel")
    assert resp.status_code == 400
    assert resp.json()["fout"]["code"] == "ONGELDIGE_CURSOR"


def test_geen_schrijf_route(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("beheerder"))
    client = _client(app)
    # Append-only: POST/PATCH/DELETE bestaan niet ⇒ 405.
    assert client.post("/api/v1/auditlog", json={}).status_code == 405
    assert client.patch("/api/v1/auditlog", json={}).status_code == 405
    assert client.request("DELETE", "/api/v1/auditlog").status_code == 405
