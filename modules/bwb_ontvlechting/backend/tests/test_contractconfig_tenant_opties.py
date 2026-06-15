"""Tests — tenant-leesbare catalogus-opties-endpoint (CD043 §0)."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings


def _row(dim, sleutel, label, volgorde):
    return SimpleNamespace(dimensie=dim, optie_sleutel=sleutel, label=label, volgorde=volgorde)


def test_actieve_opties_groepeert_per_dimensie_en_behoudt_volgorde():
    from models.models import ContractConfigDimensie as D
    from services import contractconfig_catalog as catalog

    session = AsyncMock()
    res = MagicMock()
    res.all.return_value = [
        _row(D.dekking, "licentie_aanschaf", "Licentie/aanschaf", 0),
        _row(D.dekking, "hosting", "Hosting", 2),
        _row(D.kostenmodel, "volume", "Volumemodel", 1),
    ]
    session.execute.return_value = res

    out = asyncio.run(catalog.actieve_opties_per_dimensie(session))
    # ADR-023 opruim: ContractConfig draagt nog uitsluitend dekking + kostenmodel.
    assert set(out) == {d.value for d in D}  # {dekking, kostenmodel}
    assert [o["optie_sleutel"] for o in out["dekking"]] == ["licentie_aanschaf", "hosting"]
    assert out["kostenmodel"][0]["label"] == "Volumemodel"


def test_query_filtert_actief_en_sorteert_op_volgorde():
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    bron = (root / "services" / "contractconfig_catalog.py").read_text(encoding="utf-8")
    assert "actief.is_(True)" in bron        # alleen-actief
    assert "ContractConfigOptie.volgorde" in bron  # sortering op volgorde


# ── Guard / RBAC-integratie ─────────────────────────────────────────────────────

def _app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.auth import (
        NietGeauthenticeerd,
        TenantMismatch,
        niet_geauthenticeerd_handler,
        tenant_mismatch_handler,
    )
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.contract import router
    from services import contractconfig_catalog as catalog
    from services import relatiekenmerk_catalog

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)
    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.add_exception_handler(NietGeauthenticeerd, niet_geauthenticeerd_handler)
    app.add_exception_handler(TenantMismatch, tenant_mismatch_handler)
    app.include_router(router, prefix="/api/v1")

    async def _sess():
        yield SimpleNamespace()

    app.dependency_overrides[get_tenant_session] = _sess

    async def _opt(*_a, **_k):
        return {"dekking": [], "kostenmodel": []}

    async def _relkenmerk_opt(*_a, **_k):
        # ADR-023 opruim: de endpoint componeert relatie_rol uit de relatie-kenmerk-catalogus.
        return {"dispositie": [], "relatie_rol": []}

    monkeypatch.setattr(catalog, "actieve_opties_per_dimensie", _opt)
    monkeypatch.setattr(relatiekenmerk_catalog, "actieve_opties_per_dimensie", _relkenmerk_opt)
    return app


_VIEWER = {"sub": "v", "tenant_id": "t1", "realm_access": {"roles": ["viewer"]}}
_PLATFORM = {"sub": "pb", "realm_access": {"roles": ["platformbeheerder"]}}


def _client(monkeypatch, payload):
    c = TestClient(_app(monkeypatch, payload))
    c.cookies.set(settings.cookie_name, "tok")
    return c


def test_opties_200_voor_tenant_leesrol(monkeypatch):
    r = _client(monkeypatch, _VIEWER).get("/api/v1/contracten/opties")
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"dekking", "kostenmodel", "relatie_rol"}


def test_opties_401_zonder_sessie(monkeypatch):
    c = TestClient(_app(monkeypatch, _VIEWER))  # geen cookie
    assert c.get("/api/v1/contracten/opties").status_code == 401


def test_opties_403_voor_platformrol(monkeypatch):
    # platform-account heeft geen tenant_id → de tenant-guard weigert (403).
    r = _client(monkeypatch, _PLATFORM).get("/api/v1/contracten/opties")
    assert r.status_code == 403
