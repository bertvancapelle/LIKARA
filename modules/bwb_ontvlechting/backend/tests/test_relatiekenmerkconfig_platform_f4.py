"""Tests — platform-beheer relatie-kenmerk-catalogus (ADR-023 Fase F / F-4).

Service-laag offline (DB gemockt) + guard/RBAC via een test-app. Spiegelt CD053
(`test_componentconfig_platform_cd053`), maar ZONDER beschermde systeem-sleutel: álle
waarden zijn vrij soft-deactiveerbaar.
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


async def _async(val):
    return val


def _optie(id=1, dimensie=None, optie_sleutel="migreren", label="Migreren", volgorde=0, actief=True):
    from models.models import RelatieKenmerkDimensie
    return SimpleNamespace(
        id=id, dimensie=dimensie or RelatieKenmerkDimensie.dispositie,
        optie_sleutel=optie_sleutel, label=label, volgorde=volgorde, actief=actief,
    )


# ── Schemas ─────────────────────────────────────────────────────────────────────

def test_create_patroon_en_immutability():
    from schemas.relatiekenmerkconfig import RelatieKenmerkOptieCreate, RelatieKenmerkOptieUpdate

    ok = RelatieKenmerkOptieCreate(dimensie="dispositie", optie_sleutel="herzien", label="Herzien")
    assert ok.optie_sleutel == "herzien" and ok.volgorde is None
    for slecht in ("Hoofdletter", "met spatie", "1leading"):
        with pytest.raises(ValidationError):
            RelatieKenmerkOptieCreate(dimensie="dispositie", optie_sleutel=slecht, label="X")
    with pytest.raises(ValidationError):
        RelatieKenmerkOptieCreate(dimensie="onzin", optie_sleutel="x", label="X")
    # dimensie/optie_sleutel immutable in Update
    assert RelatieKenmerkOptieUpdate(actief=False).actief is False
    with pytest.raises(ValidationError):
        RelatieKenmerkOptieUpdate(dimensie="dispositie")
    with pytest.raises(ValidationError):
        RelatieKenmerkOptieUpdate(optie_sleutel="x")


# ── Service ─────────────────────────────────────────────────────────────────────

def test_voeg_toe_default_volgorde_en_duplicaat():
    from schemas.relatiekenmerkconfig import RelatieKenmerkOptieCreate
    from services import relatiekenmerkconfig_service as svc
    from services.errors import ConfiguratieConflict

    session = AsyncMock()
    session.execute.side_effect = [_result(None), _scalar_one(2)]
    toegevoegd = []
    session.add = lambda o: toegevoegd.append(o)
    asyncio.run(svc.voeg_toe(session, RelatieKenmerkOptieCreate(
        dimensie="dispositie", optie_sleutel="herzien", label="Herzien")))
    assert toegevoegd[0].volgorde == 3 and toegevoegd[0].actief is True

    session2 = AsyncMock()
    session2.execute.return_value = _result(99)  # bestaat al
    with pytest.raises(ConfiguratieConflict):
        asyncio.run(svc.voeg_toe(session2, RelatieKenmerkOptieCreate(
            dimensie="dispositie", optie_sleutel="migreren", label="Migreren")))
    session2.commit.assert_not_awaited()


def test_wijzig_label_volgorde_en_soft_deactivate_reactivate():
    from schemas.relatiekenmerkconfig import RelatieKenmerkOptieUpdate
    from services import relatiekenmerkconfig_service as svc

    # Label + volgorde.
    optie = _optie(optie_sleutel="migreren", label="Migreren", volgorde=1, actief=True)
    session = AsyncMock()
    session.execute.return_value = _result(optie)
    asyncio.run(svc.wijzig(session, optie.id, RelatieKenmerkOptieUpdate(label="Migreren →", volgorde=5)))
    assert optie.label == "Migreren →" and optie.volgorde == 5

    # Soft-deactivate — ÉLKE waarde mag (geen beschermde sleutel).
    optie2 = _optie(optie_sleutel="behouden", actief=True)
    session2 = AsyncMock()
    session2.execute.return_value = _result(optie2)
    asyncio.run(svc.wijzig(session2, optie2.id, RelatieKenmerkOptieUpdate(actief=False)))
    assert optie2.actief is False

    # Reactivate.
    optie3 = _optie(optie_sleutel="behouden", actief=False)
    session3 = AsyncMock()
    session3.execute.return_value = _result(optie3)
    asyncio.run(svc.wijzig(session3, optie3.id, RelatieKenmerkOptieUpdate(actief=True)))
    assert optie3.actief is True


def test_wijzig_onbekend_id_404():
    from schemas.relatiekenmerkconfig import RelatieKenmerkOptieUpdate
    from services import relatiekenmerkconfig_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    session.execute.return_value = _result(None)
    with pytest.raises(NietGevonden):
        asyncio.run(svc.wijzig(session, 123, RelatieKenmerkOptieUpdate(actief=False)))


def test_geen_hard_delete_functie():
    # Dubbele borging: er is geen delete-pad in de service (mirror componentconfig).
    from services import relatiekenmerkconfig_service as svc

    assert not hasattr(svc, "verwijder")


# ── Guard / RBAC-integratie ─────────────────────────────────────────────────────

def _app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_platform_session
    from routes.relatiekenmerkconfig import router
    from services import relatiekenmerkconfig_service as svc

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
    assert c.get("/api/v1/platform/relatiekenmerkconfig").status_code == 401


def test_403_voor_tenantrol(monkeypatch):
    r = _client(monkeypatch, _TENANT).get("/api/v1/platform/relatiekenmerkconfig")
    assert r.status_code == 403 and r.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


def test_operator_leest_wel_schrijft_niet(monkeypatch):
    assert _client(monkeypatch, _PO).get("/api/v1/platform/relatiekenmerkconfig").status_code == 200
    assert _client(monkeypatch, _PO).post(
        "/api/v1/platform/relatiekenmerkconfig",
        json={"dimensie": "dispositie", "optie_sleutel": "x", "label": "X"},
    ).status_code == 403
    assert _client(monkeypatch, _PO).patch(
        "/api/v1/platform/relatiekenmerkconfig/1", json={"actief": False}
    ).status_code == 403
    # Geen DELETE-endpoint.
    assert _client(monkeypatch, _PO).delete(
        "/api/v1/platform/relatiekenmerkconfig/1"
    ).status_code == 405


def test_beheerder_mag_toevoegen(monkeypatch):
    from services import relatiekenmerkconfig_service as svc

    monkeypatch.setattr(svc, "voeg_toe", lambda *_a, **_k: _async(_optie(optie_sleutel="herzien", label="Herzien")))
    r = _client(monkeypatch, _PB).post(
        "/api/v1/platform/relatiekenmerkconfig",
        json={"dimensie": "dispositie", "optie_sleutel": "herzien", "label": "Herzien"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["optie_sleutel"] == "herzien"
