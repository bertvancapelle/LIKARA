"""Tests — platform-beheer componentcatalogus (ADR-021 fase C / Addendum C, CD053).

Service-laag offline (DB gemockt) incl. systeem-sleutel-bescherming + guard/RBAC via een
test-app. Spiegelt CD042 (`test_contractconfig_platform`).
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import settings


def _result(val):
    r = MagicMock()
    r.scalar_one_or_none.return_value = val
    return r


def _scalar_one(val):
    r = MagicMock()
    r.scalar_one.return_value = val
    return r


def _scalars(rows):
    r = MagicMock()
    r.scalars.return_value.all.return_value = rows
    return r


async def _async(val):
    return val


def _optie(id=1, dimensie=None, optie_sleutel="database", label="Database", volgorde=0, actief=True):
    from models.models import ComponentConfigDimensie
    return SimpleNamespace(
        id=id, dimensie=dimensie or ComponentConfigDimensie.componenttype,
        optie_sleutel=optie_sleutel, label=label, volgorde=volgorde, actief=actief,
    )


# ── Schemas ─────────────────────────────────────────────────────────────────────

# ADR-026 — geldige componenttype-typering voor de tests.
_TYP = {"archimate_element": "system_software", "archimate_laag": "technology", "archimate_aspect": "active"}


def test_create_patroon_en_immutability():
    from schemas.componentconfig import ComponentConfigOptieCreate, ComponentConfigOptieUpdate

    ok = ComponentConfigOptieCreate(dimensie="componenttype", optie_sleutel="etl_tool", label="ETL-tool", **_TYP)
    assert ok.optie_sleutel == "etl_tool" and ok.volgorde is None
    for slecht in ("Hoofdletter", "met spatie", "1leading"):
        with pytest.raises(ValidationError):
            ComponentConfigOptieCreate(dimensie="componenttype", optie_sleutel=slecht, label="X", **_TYP)
    with pytest.raises(ValidationError):
        ComponentConfigOptieCreate(dimensie="onzin", optie_sleutel="x", label="X")
    # dimensie/optie_sleutel immutable in Update
    assert ComponentConfigOptieUpdate(actief=False).actief is False
    with pytest.raises(ValidationError):
        ComponentConfigOptieUpdate(dimensie="componenttype")
    with pytest.raises(ValidationError):
        ComponentConfigOptieUpdate(optie_sleutel="x")


# ── Service ─────────────────────────────────────────────────────────────────────

def test_voeg_toe_default_volgorde_en_duplicaat():
    from schemas.componentconfig import ComponentConfigOptieCreate
    from services import componentconfig_service as svc
    from services.errors import ConfiguratieConflict

    session = AsyncMock()
    session.execute.side_effect = [_result(None), _scalar_one(4)]
    toegevoegd = []
    session.add = lambda o: toegevoegd.append(o)
    asyncio.run(svc.voeg_toe(session, ComponentConfigOptieCreate(
        dimensie="componenttype", optie_sleutel="etl_tool", label="ETL-tool", **_TYP)))
    assert toegevoegd[0].volgorde == 5 and toegevoegd[0].actief is True
    # ADR-026 — voeg_toe zet de typering mee (lek dicht).
    assert toegevoegd[0].archimate_element == "system_software"
    assert toegevoegd[0].laag == "technology" and toegevoegd[0].aspect == "active"

    session2 = AsyncMock()
    session2.execute.return_value = _result(99)  # bestaat al
    with pytest.raises(ConfiguratieConflict):
        asyncio.run(svc.voeg_toe(session2, ComponentConfigOptieCreate(
            dimensie="componenttype", optie_sleutel="database", label="Database", **_TYP)))
    session2.commit.assert_not_awaited()


def test_wijzig_label_volgorde_actief():
    from schemas.componentconfig import ComponentConfigOptieUpdate
    from services import componentconfig_service as svc

    optie = _optie(optie_sleutel="database", actief=True)
    session = AsyncMock()
    session.execute.return_value = _result(optie)
    asyncio.run(svc.wijzig(session, optie.id, ComponentConfigOptieUpdate(actief=False)))
    assert optie.actief is False  # gewone optie: soft-deactivate toegestaan


def test_systeem_sleutel_niet_deactiveerbaar():
    from models.models import ComponentConfigDimensie
    from schemas.componentconfig import ComponentConfigOptieUpdate
    from services import componentconfig_service as svc
    from services.errors import OngeldigeRegistratie

    systeem = _optie(dimensie=ComponentConfigDimensie.componenttype, optie_sleutel="applicatie", label="Applicatie")
    session = AsyncMock()
    session.execute.return_value = _result(systeem)
    with pytest.raises(OngeldigeRegistratie) as ei:
        asyncio.run(svc.wijzig(session, systeem.id, ComponentConfigOptieUpdate(actief=False)))
    assert ei.value.code == "SYSTEEM_SLEUTEL_BESCHERMD"
    session.commit.assert_not_awaited()


def test_systeem_sleutel_label_volgorde_mag_wel():
    from models.models import ComponentConfigDimensie
    from schemas.componentconfig import ComponentConfigOptieUpdate
    from services import componentconfig_service as svc

    systeem = _optie(dimensie=ComponentConfigDimensie.componenttype, optie_sleutel="applicatie", label="Applicatie")
    session = AsyncMock()
    session.execute.return_value = _result(systeem)
    asyncio.run(svc.wijzig(session, systeem.id, ComponentConfigOptieUpdate(label="App", volgorde=9)))
    assert systeem.label == "App" and systeem.volgorde == 9
    session.commit.assert_awaited_once()


def test_structuurrelatie_optie_wel_deactiveerbaar():
    from models.models import ComponentConfigDimensie
    from schemas.componentconfig import ComponentConfigOptieUpdate
    from services import componentconfig_service as svc

    rel = _optie(dimensie=ComponentConfigDimensie.structuurrelatie_type, optie_sleutel="draait_op", actief=True)
    session = AsyncMock()
    session.execute.return_value = _result(rel)
    asyncio.run(svc.wijzig(session, rel.id, ComponentConfigOptieUpdate(actief=False)))
    assert rel.actief is False


# ── Guard / RBAC-integratie ─────────────────────────────────────────────────────

def _app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_platform_session
    from routes.componentconfig import router
    from services import componentconfig_service as svc

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)
    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.include_router(router, prefix="/api/v1")

    async def _fake_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_platform_session] = _fake_session
    monkeypatch.setattr(svc, "lijst", lambda *_a, **_k: _async([]))
    return app


_PB = {"sub": "pb", "realm_access": {"roles": ["platformbeheerder"]}}
_PO = {"sub": "po", "realm_access": {"roles": ["platformoperator"]}}
_TENANT = {"sub": "tb", "tenant_id": "t1", "realm_access": {"roles": ["beheerder"]}}


def _client(monkeypatch, payload):
    c = TestClient(_app(monkeypatch, payload))
    c.cookies.set(settings.cookie_name, "tok")
    return c


def test_401_zonder_sessie(monkeypatch):
    c = TestClient(_app(monkeypatch, _PB))
    assert c.get("/api/v1/platform/componentconfig").status_code == 401


def test_403_voor_tenantrol(monkeypatch):
    r = _client(monkeypatch, _TENANT).get("/api/v1/platform/componentconfig")
    assert r.status_code == 403 and r.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


def test_operator_leest_wel_schrijft_niet(monkeypatch):
    assert _client(monkeypatch, _PO).get("/api/v1/platform/componentconfig").status_code == 200
    assert _client(monkeypatch, _PO).post(
        "/api/v1/platform/componentconfig",
        json={"dimensie": "componenttype", "optie_sleutel": "x", "label": "X"},
    ).status_code == 403
    assert _client(monkeypatch, _PO).patch(
        "/api/v1/platform/componentconfig/1", json={"actief": False}
    ).status_code == 403


def test_beheerder_mag_toevoegen(monkeypatch):
    from services import componentconfig_service as svc

    monkeypatch.setattr(svc, "voeg_toe", lambda *_a, **_k: _async(_optie(optie_sleutel="etl_tool", label="ETL-tool")))
    r = _client(monkeypatch, _PB).post(
        "/api/v1/platform/componentconfig",
        json={"dimensie": "componenttype", "optie_sleutel": "etl_tool", "label": "ETL-tool",
              "archimate_element": "system_software", "archimate_laag": "technology", "archimate_aspect": "active"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["optie_sleutel"] == "etl_tool"
