"""Tests — platform-config-API (ADR-019 fase 2D, ADR-012 Addendum A).

Service-laag offline (DB gemockt) + guard/RBAC-integratie via een test-app.
"""
import asyncio
import pathlib
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings


def _result(waarde):
    r = MagicMock()
    r.scalar_one_or_none.return_value = waarde
    return r


def _scalars(rijen):
    r = MagicMock()
    r.scalars.return_value.all.return_value = rijen
    return r


async def _async(waarde):
    return waarde


def _vraag(code, antwoordtype):
    return SimpleNamespace(code=code, vraag="?", antwoordtype=antwoordtype)


def _optie(afgeleid_bron=None, actief=True, label="L", volgorde=0):
    return SimpleNamespace(
        id=uuid.uuid4(), vraag_code="9.1", optie_sleutel="s", label=label,
        volgorde=volgorde, actief=actief, afgeleid_bron=afgeleid_bron,
    )


# ── Orphan-bescherming: antwoordtype alleen vanuit `geen` ───────────────────────

def test_zet_antwoordtype_vanuit_geen_mag():
    from models.models import AntwoordType
    from schemas.checklistconfig import AntwoordTypeUpdate
    from services import checklistconfig_service as svc

    vraag = _vraag("9.1", AntwoordType.geen)
    session = AsyncMock()
    session.execute.side_effect = [_result(vraag), _scalars([])]
    out = asyncio.run(svc.zet_antwoordtype(session, "9.1", AntwoordTypeUpdate(antwoordtype="getal")))
    assert vraag.antwoordtype == AntwoordType.getal
    assert out["antwoordtype"] == AntwoordType.getal


def test_zet_antwoordtype_op_getypeerde_vraag_geweigerd():
    from models.models import AntwoordType
    from schemas.checklistconfig import AntwoordTypeUpdate
    from services import checklistconfig_service as svc
    from services.errors import ConfiguratieConflict

    vraag = _vraag("2.1", AntwoordType.enkelvoudige_keuze)
    session = AsyncMock()
    session.execute.return_value = _result(vraag)
    with pytest.raises(ConfiguratieConflict):
        asyncio.run(svc.zet_antwoordtype(session, "2.1", AntwoordTypeUpdate(antwoordtype="getal")))


def test_zet_antwoordtype_zelfde_waarde_mag():
    from models.models import AntwoordType
    from schemas.checklistconfig import AntwoordTypeUpdate
    from services import checklistconfig_service as svc

    vraag = _vraag("2.1", AntwoordType.enkelvoudige_keuze)
    session = AsyncMock()
    session.execute.side_effect = [_result(vraag), _scalars([])]
    out = asyncio.run(
        svc.zet_antwoordtype(session, "2.1", AntwoordTypeUpdate(antwoordtype="enkelvoudige_keuze"))
    )
    assert out["antwoordtype"] == AntwoordType.enkelvoudige_keuze


def test_zet_antwoordtype_onbekende_vraag_404():
    from schemas.checklistconfig import AntwoordTypeUpdate
    from services import checklistconfig_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    session.execute.return_value = _result(None)
    with pytest.raises(NietGevonden):
        asyncio.run(svc.zet_antwoordtype(session, "x", AntwoordTypeUpdate(antwoordtype="getal")))


# ── Optie toevoegen ─────────────────────────────────────────────────────────────

def test_voeg_optie_aan_afgeleide_set_geweigerd():
    from models.models import AntwoordType
    from schemas.checklistconfig import OptieCreate
    from services import checklistconfig_service as svc
    from services.errors import ConfiguratieConflict

    session = AsyncMock()
    # _haal_vraag → vraag; _is_afgeleide_set → truthy id
    session.execute.side_effect = [_result(_vraag("2.1", AntwoordType.enkelvoudige_keuze)), _result(uuid.uuid4())]
    with pytest.raises(ConfiguratieConflict):
        asyncio.run(svc.voeg_optie_toe(session, "2.1", OptieCreate(optie_sleutel="x", label="X")))


def test_voeg_optie_dubbele_sleutel_geweigerd():
    from models.models import AntwoordType
    from schemas.checklistconfig import OptieCreate
    from services import checklistconfig_service as svc
    from services.errors import ConfiguratieConflict

    session = AsyncMock()
    # vraag; niet-afgeleid (None); uniciteit → bestaand id
    session.execute.side_effect = [_result(_vraag("9.1", AntwoordType.enkelvoudige_keuze)), _result(None), _result(uuid.uuid4())]
    with pytest.raises(ConfiguratieConflict):
        asyncio.run(svc.voeg_optie_toe(session, "9.1", OptieCreate(optie_sleutel="ja", label="Ja")))


def test_voeg_optie_ok_stabiele_actieve_optie():
    from models.models import AntwoordType
    from schemas.checklistconfig import OptieCreate
    from services import checklistconfig_service as svc

    session = AsyncMock()
    session.execute.side_effect = [_result(_vraag("9.1", AntwoordType.enkelvoudige_keuze)), _result(None), _result(None)]
    toegevoegd = []
    session.add = lambda o: toegevoegd.append(o)
    asyncio.run(svc.voeg_optie_toe(session, "9.1", OptieCreate(optie_sleutel="ja", label="Ja", volgorde=2)))
    assert len(toegevoegd) == 1
    assert toegevoegd[0].optie_sleutel == "ja"
    assert toegevoegd[0].volgorde == 2
    assert toegevoegd[0].actief is True
    assert toegevoegd[0].afgeleid_bron is None


# ── Optie wijzigen / soft-deactiveren (afgeleid = label-only, geen hard delete) ──

def test_wijzig_afgeleide_optie_volgorde_geweigerd():
    from schemas.checklistconfig import OptieUpdate
    from services import checklistconfig_service as svc
    from services.errors import ConfiguratieConflict

    session = AsyncMock()
    session.execute.return_value = _result(_optie(afgeleid_bron="HostingModel"))
    with pytest.raises(ConfiguratieConflict):
        asyncio.run(svc.wijzig_optie(session, uuid.uuid4(), OptieUpdate(volgorde=5)))


def test_wijzig_afgeleide_optie_label_mag():
    from schemas.checklistconfig import OptieUpdate
    from services import checklistconfig_service as svc

    optie = _optie(afgeleid_bron="HostingModel", label="SaaS")
    session = AsyncMock()
    session.execute.return_value = _result(optie)
    asyncio.run(svc.wijzig_optie(session, optie.id, OptieUpdate(label="SaaS (cloud)")))
    assert optie.label == "SaaS (cloud)"


def test_deactiveer_afgeleide_optie_geweigerd():
    from services import checklistconfig_service as svc
    from services.errors import ConfiguratieConflict

    session = AsyncMock()
    session.execute.return_value = _result(_optie(afgeleid_bron="NiveauEnum"))
    with pytest.raises(ConfiguratieConflict):
        asyncio.run(svc.deactiveer_optie(session, uuid.uuid4()))


def test_deactiveer_vrije_optie_zet_actief_false():
    from services import checklistconfig_service as svc

    optie = _optie(afgeleid_bron=None, actief=True)
    session = AsyncMock()
    session.execute.return_value = _result(optie)
    asyncio.run(svc.deactiveer_optie(session, optie.id))
    assert optie.actief is False  # soft-deactivate, geen hard delete


def test_deactiveer_onbekende_optie_404():
    from services import checklistconfig_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    session.execute.return_value = _result(None)
    with pytest.raises(NietGevonden):
        asyncio.run(svc.deactiveer_optie(session, uuid.uuid4()))


def test_config_service_raakt_engine_niet():
    """Structureel (AST, geen docstrings): de config-service verwijst nergens naar
    het score-/engine-pad — alleen `ChecklistVraag(Optie)`-referentiedata."""
    import ast

    root = pathlib.Path(__file__).resolve().parents[1]
    bron = (root / "services" / "checklistconfig_service.py").read_text(encoding="utf-8")
    tree = ast.parse(bron)
    namen = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    namen |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            namen |= {a.name for a in node.names}

    for verboden in ("Checklistscore", "lifecycle_service", "Blokkade", "herbereken_lifecycle"):
        assert verboden not in namen, f"config-service raakt {verboden}"


# ── Guard / RBAC-integratie ─────────────────────────────────────────────────────

def _config_app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_platform_session
    from routes.checklistconfig import router
    from services import checklistconfig_service as svc

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)
    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.include_router(router, prefix="/api/v1")

    async def _fake_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_platform_session] = _fake_session
    # Service gemockt → de guard wordt geïsoleerd getest.
    monkeypatch.setattr(svc, "lijst_config", lambda *_a, **_k: _async([]))
    return app


_PB = {"sub": "pb", "realm_access": {"roles": ["platformbeheerder"]}}
_PO = {"sub": "po", "realm_access": {"roles": ["platformoperator"]}}
_TENANT = {"sub": "tb", "tenant_id": "t1", "realm_access": {"roles": ["beheerder"]}}


def _client(monkeypatch, payload):
    c = TestClient(_config_app(monkeypatch, payload))
    c.cookies.set(settings.cookie_name, "tok")
    return c


def test_config_lijst_401_zonder_sessie(monkeypatch):
    c = TestClient(_config_app(monkeypatch, _PB))  # geen cookie
    assert c.get("/api/v1/platform/checklistconfig").status_code == 401


def test_config_lijst_403_voor_tenantrol(monkeypatch):
    r = _client(monkeypatch, _TENANT).get("/api/v1/platform/checklistconfig")
    assert r.status_code == 403
    assert r.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


def test_config_operator_leest_wel(monkeypatch):
    assert _client(monkeypatch, _PO).get("/api/v1/platform/checklistconfig").status_code == 200


def test_config_operator_mag_niet_wijzigen(monkeypatch):
    r = _client(monkeypatch, _PO).patch(
        "/api/v1/platform/checklistconfig/vragen/9.1", json={"antwoordtype": "getal"}
    )
    assert r.status_code == 403
    assert r.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


def test_config_operator_mag_niet_toevoegen(monkeypatch):
    r = _client(monkeypatch, _PO).post(
        "/api/v1/platform/checklistconfig/vragen/9.1/opties",
        json={"optie_sleutel": "ja", "label": "Ja"},
    )
    assert r.status_code == 403


def test_config_beheerder_mag_toevoegen(monkeypatch):
    from services import checklistconfig_service as svc

    optie = _optie(afgeleid_bron=None, label="Ja")
    monkeypatch.setattr(svc, "voeg_optie_toe", lambda *_a, **_k: _async(optie))
    r = _client(monkeypatch, _PB).post(
        "/api/v1/platform/checklistconfig/vragen/9.1/opties",
        json={"optie_sleutel": "ja", "label": "Ja"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["optie_sleutel"] == "s"
