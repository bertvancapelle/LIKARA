"""Integratie-tests — Applicatie-routes (P5).

Offline guard-integratiepatroon (complidata-tests): kleine `FastAPI()`-test-app
met de echte router + handlers; `decode_token` gemonkeypatcht voor payloads
met/zonder `tenant_id` en `realm_access.roles`; `get_tenant_session`
overschreven (geen DB); de service-functies gestubd zodat het route-, guard-,
handler- en serialisatiegedrag geïsoleerd wordt getest.

Gedekt: rol-matrix (rol × actie → 200/201/204/403), geen sessie → 401,
kruis-tenant → 404 (geen 403, geen lek), ongeldige statusovergang → 409,
ongeldige cursor → 400, en de paginerings-mechaniek + cascade-contract.
"""
import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings

TENANT_A = "11111111-1111-1111-1111-111111111111"
_ID = "22222222-2222-2222-2222-222222222222"

_CREATE_BODY = {
    "naam": "Zaaksysteem",
    "hostingmodel": "saas",
    "eigenaar_organisatie": "Gemeente Veldendam",
    "migratiepad": "herbouw",
    "complexiteit": "midden",
    "prioriteit": "hoog",
}


def _fake_applicatie():
    """Read-serialiseerbaar stand-in object (from_attributes)."""
    return SimpleNamespace(
        id=uuid.UUID(_ID),
        naam="Zaaksysteem",
        beschrijving=None,
        hostingmodel="saas",
        eigenaar_organisatie="Gemeente Veldendam",
        eigenaar_naam=None,
        leverancier=None,
        migratiepad="herbouw",
        complexiteit="midden",
        prioriteit="hoog",
        lifecycle_status="concept",
        created_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 6, tzinfo=timezone.utc),
    )


def _maak_app(monkeypatch, payload):
    """Bouw een test-app met de echte router/handlers; auth + DB geïsoleerd.

    Service-functies worden default op succes gestubd; tests overschrijven
    waar nodig (404/409/400-paden).
    """
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.applicatie import router
    from services import applicatie_service as svc
    from services.errors import (
        NietGevonden,
        OngeldigeStatusovergang,
        niet_gevonden_handler,
        ongeldige_statusovergang_handler,
    )

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)

    async def _ok_lijst(*a, **k):
        return ([_fake_applicatie()], None)

    async def _ok_obj(*a, **k):
        return _fake_applicatie()

    async def _ok_none(*a, **k):
        return None

    monkeypatch.setattr(svc, "lijst", _ok_lijst)
    monkeypatch.setattr(svc, "haal_op", _ok_obj)
    monkeypatch.setattr(svc, "maak_aan", _ok_obj)
    monkeypatch.setattr(svc, "werk_bij", _ok_obj)
    monkeypatch.setattr(svc, "start_inventarisatie", _ok_obj)
    monkeypatch.setattr(svc, "verwijder", _ok_none)

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
        client.cookies.set(settings.cookie_name, "dummy-token")
    return client


def _payload(rol):
    return {"sub": "u-1", "tenant_id": TENANT_A, "realm_access": {"roles": [rol]}}


# ── Rol-matrix (Viewer=L · Medewerker=LAW · Beheerder=LAWV · Auditor=L) ──────

_ROL_RECHTEN = {
    "viewer": set("L"),
    "medewerker": set("LAW"),
    "beheerder": set("LAWV"),
    "auditor": set("L"),
}

# (actie, method, pad, body, succescode)
_ENDPOINTS = [
    ("L", "GET", "/api/v1/applicaties", None, 200),
    ("L", "GET", f"/api/v1/applicaties/{_ID}", None, 200),
    ("A", "POST", "/api/v1/applicaties", _CREATE_BODY, 201),
    ("W", "PATCH", f"/api/v1/applicaties/{_ID}", {"naam": "Nieuw"}, 200),
    ("W", "POST", f"/api/v1/applicaties/{_ID}/start-inventarisatie", None, 200),
    ("V", "DELETE", f"/api/v1/applicaties/{_ID}", None, 204),
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


# ── 401 / 404 / 409 / 400 ───────────────────────────────────────────────────

def test_geen_sessie_geeft_401(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("beheerder"))
    client = _client(app, met_sessie=False)
    resp = client.get("/api/v1/applicaties")
    assert resp.status_code == 401


def test_kruis_tenant_id_geeft_404(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("medewerker"))
    from services.errors import NietGevonden

    async def _raise(*a, **k):
        raise NietGevonden("applicatie", _ID)

    monkeypatch.setattr(svc, "haal_op", _raise)
    client = _client(app)
    resp = client.get(f"/api/v1/applicaties/{_ID}")
    assert resp.status_code == 404
    assert resp.json()["fout"]["code"] == "NIET_GEVONDEN"


def test_ongeldige_statusovergang_geeft_409(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("medewerker"))
    from models.models import LifecycleStatus
    from services.errors import OngeldigeStatusovergang

    async def _raise(*a, **k):
        raise OngeldigeStatusovergang(
            LifecycleStatus.checklist_compleet, LifecycleStatus.in_inventarisatie
        )

    monkeypatch.setattr(svc, "start_inventarisatie", _raise)
    client = _client(app)
    resp = client.post(f"/api/v1/applicaties/{_ID}/start-inventarisatie")
    assert resp.status_code == 409
    assert resp.json()["fout"]["code"] == "ONGELDIGE_STATUSOVERGANG"


def test_ongeldige_cursor_geeft_400(monkeypatch):
    app, svc = _maak_app(monkeypatch, _payload("viewer"))

    async def _raise(*a, **k):
        raise ValueError("ongeldige cursor")

    monkeypatch.setattr(svc, "lijst", _raise)
    client = _client(app)
    resp = client.get("/api/v1/applicaties?after=onzin")
    assert resp.status_code == 400
    assert resp.json()["fout"]["code"] == "ONGELDIGE_CURSOR"


def test_ongeldige_uuid_pad_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("viewer"))
    client = _client(app)
    resp = client.get("/api/v1/applicaties/geen-uuid")
    assert resp.status_code == 422


# ── Sorteren (ADR-017): allowlist-validatie op de API-rand ──────────────────

def test_geldige_sort_en_order_geeft_200(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("viewer"))
    client = _client(app)
    resp = client.get("/api/v1/applicaties?sort=naam&order=desc")
    assert resp.status_code == 200, resp.text


def test_onbekend_sortveld_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("viewer"))
    client = _client(app)
    resp = client.get("/api/v1/applicaties?sort=geheim_veld")
    assert resp.status_code == 422


def test_ongeldige_order_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("viewer"))
    client = _client(app)
    resp = client.get("/api/v1/applicaties?order=zijwaarts")
    assert resp.status_code == 422


# ── Registerfilters (CD017): allowlist + lengtevalidatie op de API-rand ─────

def test_geldige_filters_geven_200(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("viewer"))
    client = _client(app)
    resp = client.get(
        "/api/v1/applicaties?status=concept&status=geblokkeerd"
        "&hostingmodel=saas&eigenaar=tiel&zoek=zaak"
    )
    assert resp.status_code == 200, resp.text


def test_ongeldig_statusfilter_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("viewer"))
    client = _client(app)
    # checklist_compleet is transient en zit bewust niet in de filter-allowlist
    assert client.get("/api/v1/applicaties?status=onzin").status_code == 422
    assert client.get("/api/v1/applicaties?status=checklist_compleet").status_code == 422


def test_ongeldig_hostingmodel_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("viewer"))
    client = _client(app)
    resp = client.get("/api/v1/applicaties?hostingmodel=mainframe")
    assert resp.status_code == 422


def test_te_lange_zoekterm_geeft_422(monkeypatch):
    app, _ = _maak_app(monkeypatch, _payload("viewer"))
    client = _client(app)
    assert client.get(f"/api/v1/applicaties?zoek={'a' * 101}").status_code == 422
    assert client.get(f"/api/v1/applicaties?eigenaar={'b' * 121}").status_code == 422


# ── Paginerings-mechaniek (service met fake-sessie; keyset is DB-zijdig) ─────

class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, stmt):
        return _FakeResult(self._rows)


def _rij(i):
    return SimpleNamespace(
        created_at=datetime(2026, 6, 6, 12, 0, i, tzinfo=timezone.utc),
        id=uuid.uuid4(),
    )


def test_lijst_geeft_cursor_bij_volgende_pagina():
    from services import applicatie_service as svc
    from services.pagination import decode_sort_cursor

    rows = [_rij(i) for i in range(26)]  # limit 25 → 26 rijen ⇒ er is meer
    items, cursor = asyncio.run(svc.lijst(_FakeSession(rows), TENANT_A, limit=25))
    assert len(items) == 25
    assert cursor is not None
    # White-box: de Applicatie-service geeft het zelfbeschrijvende v2-formaat uit
    # (ADR-017). Default-pad = created_at/asc (regressie: gedrag ongewijzigd).
    sort, order, _waarde, ident = decode_sort_cursor(cursor)
    assert (sort, order) == ("created_at", "asc")
    assert ident == items[-1].id  # cursor verwijst naar laatste geziene rij


def test_lijst_laatste_pagina_zonder_cursor():
    from services import applicatie_service as svc

    rows = [_rij(i) for i in range(10)]
    items, cursor = asyncio.run(svc.lijst(_FakeSession(rows), TENANT_A, limit=25))
    assert len(items) == 10
    assert cursor is None


# ── Cascade-contract (offline: structurele verificatie van ON DELETE CASCADE) ─

def test_kind_fks_cascaden_op_applicatie():
    """De DB dwingt cascade af; offline verifiëren we het FK-contract: elke
    directe FK naar `applicatie.id` heeft `ondelete='CASCADE'`."""
    from models.models import (
        Blokkade,
        Checklistscore,
        Datatype,
        Gebruikersgroep,
        Koppeling,
    )

    kinderen = [Datatype, Gebruikersgroep, Koppeling, Checklistscore, Blokkade]
    fks_naar_app = 0
    for model in kinderen:
        for kolom in model.__table__.columns:
            for fk in kolom.foreign_keys:
                if fk.column.table.name == "applicatie":
                    fks_naar_app += 1
                    assert fk.ondelete == "CASCADE", f"{model.__name__}.{kolom.name}"
    assert fks_naar_app >= 5  # datatype, gebruikersgroep, koppeling×2, checklistscore, blokkade
