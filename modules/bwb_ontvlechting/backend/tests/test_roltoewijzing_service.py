"""Tests — rol-toewijzing (ADR-024 slice 2b).

Offline (mocked) service-asserts + structuur (uniciteit per (partij, object, rol)) +
engine-onaangeroerd (import-afwezigheid) + guard/RBAC-integratie op de echte router.
Live: geen trigger op `roltoewijzing`, geen mutatie van component_profiel/lifecycle.
"""
import asyncio
import pathlib
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings


def _result(val):
    r = MagicMock()
    r.scalar_one_or_none.return_value = val
    return r


def _first(val):
    r = MagicMock()
    r.first.return_value = val
    return r


def _all(rows):
    r = MagicMock()
    r.all.return_value = rows
    return r


def _async(val=None):
    async def _c(*_a, **_k):
        return val
    return _c()


# ── Structuur: uniciteit per (partij, object, rol) = meerdere rollen mogelijk ────

def test_unieke_sleutel_bevat_rol():
    """De UNIQUE bevat `rol` → dezelfde rol niet dubbel, maar wél meerdere rollen per
    (partij, object) als losse regels."""
    from models.models import Roltoewijzing

    uq = next(c for c in Roltoewijzing.__table__.constraints if getattr(c, "name", "") == "uq_roltoewijzing")
    assert {c.name for c in uq.columns} == {"tenant_id", "partij_id", "object_id", "rol"}


def test_beheerrol_dimensie_bestaat():
    from models.models import RelatieKenmerkDimensie

    assert "beheerrol" in {e.value for e in RelatieKenmerkDimensie}


def test_seed_bevat_zeven_beheerrollen():
    from services.seed_relatiekenmerk import _BEHEERROL, bouw_relatiekenmerk

    assert len(_BEHEERROL) == 7
    rijen = bouw_relatiekenmerk()
    beheer = [r for r in rijen if getattr(r["dimensie"], "value", r["dimensie"]) == "beheerrol"]
    assert len(beheer) == 7
    assert len(rijen) == 14  # 4 dispositie + 3 relatie_rol + 7 beheerrol


# ── Service: happy path + foutpaden ──────────────────────────────────────────────

def _patch_catalog(monkeypatch, *, actief=("eigenaar",), labels=None):
    from services import roltoewijzing_service as svc

    monkeypatch.setattr(svc.catalog, "actieve_sleutels", AsyncMock(return_value=set(actief)))
    monkeypatch.setattr(
        svc.catalog, "labels",
        AsyncMock(return_value=labels or {"eigenaar": ("Eigenaar", True)}),
    )


def test_maak_aan_happy_path(monkeypatch):
    from models.models import ElementType, PartijAard
    from services import roltoewijzing_service as svc

    _patch_catalog(monkeypatch)
    monkeypatch.setattr(
        svc, "_element_type",
        AsyncMock(side_effect=[ElementType.partij.value, ElementType.component.value, ElementType.component.value]),
    )
    monkeypatch.setattr(svc, "_object_naam", AsyncMock(return_value="Comp A"))

    session = AsyncMock()
    toegevoegd = []
    session.add = lambda o: toegevoegd.append(o)
    session.execute.return_value = _first(SimpleNamespace(naam="Jan", aard=PartijAard.persoon))

    uit = asyncio.run(svc.maak_aan(session, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "eigenaar"))
    assert toegevoegd[0].rol == "eigenaar"
    assert uit["rol"] == "eigenaar" and uit["rol_label"] == "Eigenaar"
    assert uit["partij_naam"] == "Jan" and uit["partij_aard"] == "persoon"
    assert uit["object_naam"] == "Comp A" and uit["object_type"] == ElementType.component.value
    session.commit.assert_awaited_once()


def test_maak_aan_ongeldige_bron(monkeypatch):
    from models.models import ElementType
    from services import roltoewijzing_service as svc
    from services.errors import OngeldigeRegistratie

    monkeypatch.setattr(svc, "_element_type", AsyncMock(side_effect=[ElementType.contract.value]))
    session = AsyncMock()
    with pytest.raises(OngeldigeRegistratie) as ei:
        asyncio.run(svc.maak_aan(session, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "eigenaar"))
    assert ei.value.code == "ONGELDIGE_BRON"
    session.commit.assert_not_awaited()


def test_maak_aan_ongeldig_doel(monkeypatch):
    from models.models import ElementType
    from services import roltoewijzing_service as svc
    from services.errors import OngeldigeRegistratie

    monkeypatch.setattr(
        svc, "_element_type",
        AsyncMock(side_effect=[ElementType.partij.value, ElementType.datatype.value]),
    )
    session = AsyncMock()
    with pytest.raises(OngeldigeRegistratie) as ei:
        asyncio.run(svc.maak_aan(session, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "eigenaar"))
    assert ei.value.code == "ONGELDIG_DOEL"


def test_maak_aan_ongeldige_rol(monkeypatch):
    from models.models import ElementType
    from services import roltoewijzing_service as svc
    from services.errors import OngeldigeRegistratie

    _patch_catalog(monkeypatch, actief=("eigenaar",))
    monkeypatch.setattr(
        svc, "_element_type",
        AsyncMock(side_effect=[ElementType.partij.value, ElementType.component.value]),
    )
    session = AsyncMock()
    with pytest.raises(OngeldigeRegistratie) as ei:
        asyncio.run(svc.maak_aan(session, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "onzin"))
    assert ei.value.code == "ONGELDIGE_ROL"


def test_maak_aan_dubbel_geeft_conflict(monkeypatch):
    from models.models import ElementType
    from services import roltoewijzing_service as svc
    from services.errors import RegistratieConflict

    _patch_catalog(monkeypatch)
    monkeypatch.setattr(
        svc, "_element_type",
        AsyncMock(side_effect=[ElementType.partij.value, ElementType.component.value]),
    )
    session = AsyncMock()
    session.add = lambda o: None
    session.flush.side_effect = IntegrityError("dup", {}, Exception("uq_roltoewijzing"))
    with pytest.raises(RegistratieConflict) as ei:
        asyncio.run(svc.maak_aan(session, uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "eigenaar"))
    assert ei.value.code == "TOEWIJZING_BESTAAT"
    session.rollback.assert_awaited_once()


def test_verwijder_niet_gevonden(monkeypatch):
    from services import roltoewijzing_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    session.execute.return_value = _result(None)
    with pytest.raises(NietGevonden):
        asyncio.run(svc.verwijder(session, uuid.uuid4(), uuid.uuid4()))


def test_lijst_voor_object_verrijkt_partij_en_rol(monkeypatch):
    from models.models import PartijAard
    from services import roltoewijzing_service as svc

    monkeypatch.setattr(svc.catalog, "labels", AsyncMock(return_value={"eigenaar": ("Eigenaar", True)}))
    tid_row = SimpleNamespace(
        toewijzing_id=uuid.uuid4(), rol="eigenaar", partij_id=uuid.uuid4(),
        partij_naam="Jan", partij_aard=PartijAard.persoon,
    )
    session = AsyncMock()
    session.execute.return_value = _all([tid_row])
    uit = asyncio.run(svc.lijst_voor_object(session, uuid.uuid4(), uuid.uuid4()))
    assert uit[0]["partij_naam"] == "Jan" and uit[0]["rol_label"] == "Eigenaar"
    assert uit[0]["partij_aard"] == "persoon"


def test_lijst_voor_partij_verrijkt_object_en_rol(monkeypatch):
    from models.models import ElementType
    from services import roltoewijzing_service as svc

    monkeypatch.setattr(svc.catalog, "labels", AsyncMock(return_value={"contractbeheer": ("Contractbeheer", True)}))
    row = SimpleNamespace(
        toewijzing_id=uuid.uuid4(), rol="contractbeheer", object_id=uuid.uuid4(),
        object_type=ElementType.contract, object_naam="Mantel A",
    )
    session = AsyncMock()
    session.execute.return_value = _all([row])
    uit = asyncio.run(svc.lijst_voor_partij(session, uuid.uuid4(), uuid.uuid4()))
    assert uit[0]["object_naam"] == "Mantel A" and uit[0]["object_type"] == "contract"
    assert uit[0]["rol_label"] == "Contractbeheer"


# ── Engine-onaangeroerd (offline import-afwezigheid) ─────────────────────────────

def test_engine_niet_geimporteerd_in_roltoewijzing_service():
    base = pathlib.Path(__file__).resolve().parents[1] / "services"
    verboden = ("lifecycle_service", "herbereken_lifecycle", "ComponentProfiel", "Blokkade", "Checklistscore")
    importregels = [
        r for r in (base / "roltoewijzing_service.py").read_text(encoding="utf-8").splitlines()
        if r.lstrip().startswith(("import ", "from "))
    ]
    blob = "\n".join(importregels)
    for term in verboden:
        assert term not in blob, f"roltoewijzing_service importeert onverwacht {term}"


# ── Guard / RBAC-integratie op de echte router ───────────────────────────────────

def _app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.auth import NietGeauthenticeerd, niet_geauthenticeerd_handler
    from app.middleware.tenant import get_tenant_session
    from routes.roltoewijzing import router
    from services import roltoewijzing_service as svc

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)
    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.add_exception_handler(NietGeauthenticeerd, niet_geauthenticeerd_handler)
    app.include_router(router, prefix="/api/v1")

    async def _fake_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_tenant_session] = _fake_session
    monkeypatch.setattr(svc, "lijst_voor_object", lambda *_a, **_k: _async([]))
    monkeypatch.setattr(svc, "lijst_voor_partij", lambda *_a, **_k: _async([]))
    monkeypatch.setattr(svc, "actieve_rollen", lambda *_a, **_k: _async([]))
    monkeypatch.setattr(
        svc, "maak_aan",
        lambda *_a, **_k: _async({"toewijzing_id": str(uuid.uuid4()), "rol": "eigenaar", "rol_label": "Eigenaar"}),
    )
    monkeypatch.setattr(svc, "verwijder", lambda *_a, **_k: _async(None))
    return app


_VIEWER = {"sub": "v", "tenant_id": "t1", "realm_access": {"roles": ["viewer"]}}
_MEDEW = {"sub": "m", "tenant_id": "t1", "realm_access": {"roles": ["medewerker"]}}
_OBJ = str(uuid.uuid4())
_PARTIJ = str(uuid.uuid4())


def _client(monkeypatch, payload):
    c = TestClient(_app(monkeypatch, payload))
    c.cookies.set(settings.cookie_name, "tok")
    return c


def test_401_zonder_sessie(monkeypatch):
    c = TestClient(_app(monkeypatch, _VIEWER))
    assert c.get(f"/api/v1/roltoewijzingen?object_id={_OBJ}").status_code == 401


def test_lezen_mag_viewer(monkeypatch):
    r = _client(monkeypatch, _VIEWER).get(f"/api/v1/roltoewijzingen?object_id={_OBJ}")
    assert r.status_code == 200
    assert _client(monkeypatch, _VIEWER).get("/api/v1/roltoewijzingen/rollen").status_code == 200


def test_filter_vereist_precies_een(monkeypatch):
    # Geen filter ⇒ 422 FILTER_VEREIST; beide ⇒ idem.
    c = _client(monkeypatch, _VIEWER)
    assert c.get("/api/v1/roltoewijzingen").status_code == 422
    r = c.get(f"/api/v1/roltoewijzingen?object_id={_OBJ}&partij_id={_PARTIJ}")
    assert r.status_code == 422 and r.json()["fout"]["code"] == "FILTER_VEREIST"


def test_aanmaken_vereist_wijzigen(monkeypatch):
    body = {"partij_id": _PARTIJ, "object_id": _OBJ, "rol": "eigenaar"}
    assert _client(monkeypatch, _VIEWER).post("/api/v1/roltoewijzingen", json=body).status_code == 403
    assert _client(monkeypatch, _MEDEW).post("/api/v1/roltoewijzingen", json=body).status_code == 201


def test_verwijderen_vereist_wijzigen(monkeypatch):
    tid = str(uuid.uuid4())
    assert _client(monkeypatch, _VIEWER).delete(f"/api/v1/roltoewijzingen/{tid}").status_code == 403
    assert _client(monkeypatch, _MEDEW).delete(f"/api/v1/roltoewijzingen/{tid}").status_code == 204


# ── Live (na DB-reset / migratie 0029+0030) ──────────────────────────────────────

_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"
_DEV_TENANT = "11111111-1111-1111-1111-111111111111"


def _roltoewijzing_tabel_bestaat() -> bool:
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_CD_APP_URL)
        try:
            async with eng.connect() as c:
                return (await c.execute(text("SELECT to_regclass('roltoewijzing')"))).scalar() is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


live = pytest.mark.skipif(
    not _roltoewijzing_tabel_bestaat(),
    reason="roltoewijzing-tabel niet bereikbaar (migratie 0030 niet toegepast)",
)


@live
def test_live_geen_trigger_op_roltoewijzing():
    """Engine-onaangeroerd (live): geen trigger op `roltoewijzing` → een write kan geen
    component_profiel/lifecycle-state laten ontstaan (geen cascade-pad)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _run():
        eng = create_async_engine(_CD_APP_URL)
        try:
            async with eng.connect() as c:
                return (await c.execute(text(
                    "SELECT count(*) FROM pg_trigger t JOIN pg_class cl ON cl.oid = t.tgrelid "
                    "WHERE cl.relname = 'roltoewijzing' AND NOT t.tgisinternal"
                ))).scalar()
        finally:
            await eng.dispose()
    assert asyncio.run(_run()) == 0
