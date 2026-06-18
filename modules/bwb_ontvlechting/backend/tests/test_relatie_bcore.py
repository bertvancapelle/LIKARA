"""ADR-023 Fase B-core — unified relatiemodel (route/schema offline + CRUD/validatie live)."""
import asyncio
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import settings

TENANT_A = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"
_BRON = "33333333-3333-3333-3333-333333333333"
_DOEL = "44444444-4444-4444-4444-444444444444"
_REL = "55555555-5555-5555-5555-555555555555"


# ── Schema (offline) ─────────────────────────────────────────────────────────────

def test_relatie_create_extra_forbid_en_type_verplicht():
    from pydantic import ValidationError

    from schemas.relatie import RelatieCreate

    ok = RelatieCreate(bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL), relatietype="flow")
    assert ok.kenmerken == {} and ok.relatietype == "flow"
    with pytest.raises(ValidationError):
        RelatieCreate(bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL), relatietype="flow", onbekend=1)
    with pytest.raises(ValidationError):
        RelatieCreate(bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL), relatietype="  ")


# ── Route + RBAC (offline, gemockte service) ─────────────────────────────────────

def _fake_relatie():
    from datetime import datetime, timezone
    return SimpleNamespace(
        id=uuid.UUID(_REL), bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL),
        relatietype="flow", kenmerken={"protocol": "api"}, omschrijving=None,
        created_at=datetime(2026, 6, 14, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 14, tzinfo=timezone.utc),
    )


def _maak_app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.relatie import router
    from services import relatie_service as svc

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)

    async def _ok_lijst(*a, **k):
        return ([_fake_relatie()], None)

    async def _ok_obj(*a, **k):
        return _fake_relatie()

    monkeypatch.setattr(svc, "lijst", _ok_lijst)
    monkeypatch.setattr(svc, "haal_op", _ok_obj)
    monkeypatch.setattr(svc, "maak_aan", _ok_obj)
    monkeypatch.setattr(svc, "werk_bij", _ok_obj)

    async def _ok_del(*a, **k):
        return None

    monkeypatch.setattr(svc, "verwijder", _ok_del)

    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.include_router(router, prefix="/api/v1")

    async def _fake_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_tenant_session] = _fake_session
    return app


def _client(app):
    c = TestClient(app)
    c.cookies.set(settings.cookie_name, "dummy")
    return c


def _payload(rol):
    return {"sub": "u-1", "tenant_id": TENANT_A, "realm_access": {"roles": [rol]}}


_ROL_RECHTEN = {"viewer": set("L"), "medewerker": set("LAW"), "beheerder": set("LAWV"), "auditor": set("L")}
_ENDPOINTS = [
    ("L", "GET", "/api/v1/relaties", None, 200),
    ("A", "POST", "/api/v1/relaties", {"bron_id": _BRON, "doel_id": _DOEL, "relatietype": "flow"}, 201),
    ("L", "GET", f"/api/v1/relaties/{_REL}", None, 200),
    ("W", "PATCH", f"/api/v1/relaties/{_REL}", {"omschrijving": "x"}, 200),
    ("V", "DELETE", f"/api/v1/relaties/{_REL}", None, 204),
]


@pytest.mark.parametrize("rol", ["viewer", "medewerker", "beheerder", "auditor"])
@pytest.mark.parametrize("actie,method,pad,body,ok_code", _ENDPOINTS)
def test_rbac_matrix_relatie(monkeypatch, rol, actie, method, pad, body, ok_code):
    app = _maak_app(monkeypatch, _payload(rol))
    resp = _client(app).request(method, pad, json=body)
    if actie in _ROL_RECHTEN[rol]:
        assert resp.status_code == ok_code, resp.text
    else:
        assert resp.status_code == 403, resp.text
        assert resp.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


# ── Live: CRUD + integriteit + validatie ─────────────────────────────────────────

_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"


def _relatie_tabel_bestaat() -> bool:
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_CD_APP_URL)
        try:
            async with eng.connect() as c:
                return (await c.execute(text("SELECT to_regclass('relatie')"))).scalar() is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


live = pytest.mark.skipif(
    not _relatie_tabel_bestaat(), reason="relatie-tabel niet bereikbaar (migratie 0012 niet toegepast)"
)


@live
def test_relatie_crud_en_integriteit_live():
    from app.core import tenant_context as tc
    from app.core.database import _markeer_rls
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from models.models import Component, Element, ElementType
    from schemas.relatie import RelatieCreate
    from services import relatie_service
    from services.errors import NietGevonden, OngeldigeRegistratie

    async def _comp(s, tid, naam):
        elem = Element(tenant_id=tid, element_type=ElementType.component)
        s.add(elem); await s.flush()
        c = Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="middleware",
                      hostingmodel="on_premise")
        s.add(c); await s.flush()
        return c.id

    async def _run():
        eng = create_async_engine(_CD_APP_URL)
        smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        tid = uuid.UUID(TENANT_A)
        try:
            tok = tc.zet_tenant_context(TENANT_A); atok = tc.zet_audit_context("system:dev_seed")
            try:
                async with smf() as s:
                    _markeer_rls(s)
                    a = await _comp(s, tid, f"REL-A-{uuid.uuid4().hex[:6]}")
                    b = await _comp(s, tid, f"REL-B-{uuid.uuid4().hex[:6]}")
                    await s.commit()
                    # geldige flow-relatie met kenmerk protocol
                    rel = await relatie_service.maak_aan(
                        s, TENANT_A,
                        RelatieCreate(bron_id=a, doel_id=b, relatietype="flow",
                                      kenmerken={"protocol": "api"}),
                    )
                    resultaten = {"created": rel.id, "bron": rel.bron_id, "doel": rel.doel_id}
                    # bron≠doel
                    try:
                        await relatie_service.maak_aan(
                            s, TENANT_A, RelatieCreate(bron_id=a, doel_id=a, relatietype="flow"))
                        resultaten["zelf"] = "GEEN_FOUT"
                    except OngeldigeRegistratie as e:
                        resultaten["zelf"] = e.code
                    # onbekend relatietype
                    try:
                        await relatie_service.maak_aan(
                            s, TENANT_A, RelatieCreate(bron_id=a, doel_id=b, relatietype="bestaat_niet"))
                        resultaten["type"] = "GEEN_FOUT"
                    except OngeldigeRegistratie as e:
                        resultaten["type"] = e.code
                    # ongeldig kenmerk (protocol-waarde fout)
                    try:
                        await relatie_service.maak_aan(
                            s, TENANT_A, RelatieCreate(bron_id=b, doel_id=a, relatietype="flow",
                                                       kenmerken={"protocol": "telepathie"}))
                        resultaten["kenmerk"] = "GEEN_FOUT"
                    except OngeldigeRegistratie as e:
                        resultaten["kenmerk"] = e.code
                    # niet-bestaand endpoint
                    try:
                        await relatie_service.maak_aan(
                            s, TENANT_A, RelatieCreate(bron_id=a, doel_id=uuid.uuid4(), relatietype="flow"))
                        resultaten["endpoint"] = "GEEN_FOUT"
                    except NietGevonden:
                        resultaten["endpoint"] = "NIET_GEVONDEN"
                    # opruimen (element-delete cascadeert de relatie)
                    await s.execute(text("DELETE FROM element WHERE id IN (:a,:b)"),
                                    {"a": str(a), "b": str(b)})
                    await s.commit()
                    return resultaten
            finally:
                tc.reset_audit_context(atok); tc.reset_tenant_context(tok)
        finally:
            await eng.dispose()

    r = asyncio.run(_run())
    assert r["created"] is not None and r["bron"] != r["doel"]
    assert r["zelf"] == "ZELFVERWIJZING"
    assert r["type"] == "ONGELDIGE_OPTIE"
    assert r["kenmerk"] == "ONGELDIG_KENMERK"
    assert r["endpoint"] == "NIET_GEVONDEN"
