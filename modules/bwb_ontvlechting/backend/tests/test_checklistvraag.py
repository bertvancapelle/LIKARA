"""Tests — GET /checklistvragen (read-only, platform-brede referentiedata)."""
import uuid
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings

TENANT_A = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"


def _vraag(code, nr=1):
    return SimpleNamespace(
        id=uuid.uuid4(), code=code, componenttype="applicatie", categorie_nr=nr,
        categorie_naam="Cat", vraag="?", prioriteit="hoog",
        antwoordtype="geen", opties=[],
    )


def _maak_app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.checklistvraag import router

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)
    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.include_router(router, prefix="/api/v1")

    async def _fake_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_tenant_session] = _fake_session
    return app


def _payload(tenant_id, rollen):
    return {"sub": "u-1", "tenant_id": tenant_id, "realm_access": {"roles": rollen}}


def test_checklistvraag_model_is_niet_tenant_scoped():
    # Structureel bewijs platform-breed: geen tenant_id-kolom op het model.
    from models.models import ChecklistVraag

    assert "tenant_id" not in ChecklistVraag.__table__.columns


def test_service_lijst_alle_zonder_tenantfilter():
    import asyncio
    from unittest.mock import AsyncMock, MagicMock

    from services.checklistvraag_service import lijst_alle

    vragen = [_vraag("1.1"), _vraag("1.2")]
    optie = SimpleNamespace(
        checklistvraag_id=vragen[0].id, optie_sleutel="a", label="A", volgorde=0,
        actief=True, afgeleid_bron=None
    )
    vres = MagicMock()
    vres.scalars.return_value.all.return_value = vragen
    ores = MagicMock()
    ores.scalars.return_value.all.return_value = [optie]
    session = AsyncMock()
    # twee queries: vragen, daarna opties (geen tenant_id in de signatuur)
    session.execute.side_effect = [vres, ores]

    out = asyncio.run(lijst_alle(session))
    assert [r["code"] for r in out] == ["1.1", "1.2"]
    assert out[0]["antwoordtype"] == "geen"
    assert out[0]["opties"] == [optie]  # gegroepeerd op checklistvraag_id
    assert out[1]["opties"] == []


def test_route_geeft_vragen_voor_viewer(monkeypatch):
    from services import checklistvraag_service as svc

    monkeypatch.setattr(svc, "lijst_alle", lambda *_a, **_k: _async([_vraag("1.1"), _vraag("2.1", 2)]))
    client = TestClient(_maak_app(monkeypatch, _payload(TENANT_A, ["viewer"])))
    client.cookies.set(settings.cookie_name, "dummy")
    resp = client.get("/api/v1/checklistvragen")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [r["code"] for r in body] == ["1.1", "2.1"]
    assert set(body[0].keys()) == {
        "id", "code", "componenttype", "categorie_nr", "categorie_naam", "vraag", "prioriteit",
        "antwoordtype", "opties",
    }


def test_route_cross_tenant_identieke_set(monkeypatch):
    from services import checklistvraag_service as svc

    vaste_set = [_vraag("1.1"), _vraag("1.2"), _vraag("2.1", 2)]
    monkeypatch.setattr(svc, "lijst_alle", lambda *_a, **_k: _async(list(vaste_set)))

    a = TestClient(_maak_app(monkeypatch, _payload(TENANT_A, ["beheerder"])))
    a.cookies.set(settings.cookie_name, "dummy")
    b = TestClient(_maak_app(monkeypatch, _payload(TENANT_B, ["viewer"])))
    b.cookies.set(settings.cookie_name, "dummy")

    ra, rb = a.get("/api/v1/checklistvragen"), b.get("/api/v1/checklistvragen")
    assert ra.status_code == rb.status_code == 200
    assert ra.json() == rb.json()  # platform-breed: zelfde set voor beide tenants


def test_route_403_zonder_leesrecht(monkeypatch):
    # Lege rollenlijst → fail-secure → geen LEZEN → 403.
    client = TestClient(_maak_app(monkeypatch, _payload(TENANT_A, [])))
    client.cookies.set(settings.cookie_name, "dummy")
    resp = client.get("/api/v1/checklistvragen")
    assert resp.status_code == 403
    assert resp.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


def test_route_vereist_auth(monkeypatch):
    client = TestClient(_maak_app(monkeypatch, _payload(TENANT_A, ["viewer"])))  # geen cookie
    assert client.get("/api/v1/checklistvragen").status_code == 401


async def _async(waarde):
    return waarde
