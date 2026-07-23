"""Tests — tenant-config-API voor de checklist-vragenset + antwoordconfiguratie
(ADR-019 fase 2D; ADR-022 Wijziging W1).

ADR-022 W1: de vragenset is **tenant-eigendom**. De router is tenant-facing
(`/api/v1/checklistconfig`, `get_tenant_session`, `vereist_permissie(
CHECKLISTVRAAG, …)`). Vragen worden geadresseerd op hun `id` (uuid), niet op `code`.

Service-laag offline (DB gemockt) + guard/RBAC-integratie via een test-app.
"""
import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings

# Vaste uuids voor de service-unit-tests (vraag-id + tenant-id).
_VRAAG_ID = uuid.uuid4()
_TENANT_ID = uuid.uuid4()


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


# LI050: de categorie is een verwijzing; reads resolven naam/volgorde via _haal_categorie.
_CAT = SimpleNamespace(id=uuid.uuid4(), componenttype="applicatie", naam="x", volgorde=1)


def _vraag(code, antwoordtype):
    from models.models import ChecklistPrioriteit

    return SimpleNamespace(
        id=uuid.uuid4(),
        code=code,
        componenttype="applicatie",
        categorie_id=_CAT.id,
        vraag="?",
        prioriteit=ChecklistPrioriteit.midden,
        antwoordtype=antwoordtype,
        actief=True,
        betekenis=None,
    )


def _optie(afgeleid_bron=None, actief=True, label="L", volgorde=0):
    return SimpleNamespace(
        id=uuid.uuid4(), checklistvraag_id=uuid.uuid4(), optie_sleutel="s", label=label,
        volgorde=volgorde, actief=actief, afgeleid_bron=afgeleid_bron,
    )


# ── Orphan-bescherming: antwoordtype alleen vanuit `geen` ───────────────────────

def test_zet_antwoordtype_vanuit_geen_mag():
    from models.models import AntwoordType
    from schemas.checklistconfig import AntwoordTypeUpdate
    from services import checklistconfig_service as svc

    vraag = _vraag("9.1", AntwoordType.geen)
    session = AsyncMock()
    # zet_antwoordtype: _haal_vraag + _opties_van + _haal_categorie = 3 execute-calls (LI050).
    session.execute.side_effect = [_result(vraag), _scalars([]), _result(_CAT)]
    out = asyncio.run(svc.zet_antwoordtype(session, _VRAAG_ID, AntwoordTypeUpdate(antwoordtype="getal")))
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
        asyncio.run(svc.zet_antwoordtype(session, _VRAAG_ID, AntwoordTypeUpdate(antwoordtype="getal")))


def test_zet_antwoordtype_zelfde_waarde_mag():
    from models.models import AntwoordType
    from schemas.checklistconfig import AntwoordTypeUpdate
    from services import checklistconfig_service as svc

    vraag = _vraag("2.1", AntwoordType.enkelvoudige_keuze)
    session = AsyncMock()
    session.execute.side_effect = [_result(vraag), _scalars([]), _result(_CAT)]
    out = asyncio.run(
        svc.zet_antwoordtype(session, _VRAAG_ID, AntwoordTypeUpdate(antwoordtype="enkelvoudige_keuze"))
    )
    assert out["antwoordtype"] == AntwoordType.enkelvoudige_keuze


def test_zet_antwoordtype_onbekende_vraag_404():
    from schemas.checklistconfig import AntwoordTypeUpdate
    from services import checklistconfig_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    session.execute.return_value = _result(None)
    with pytest.raises(NietGevonden):
        asyncio.run(svc.zet_antwoordtype(session, _VRAAG_ID, AntwoordTypeUpdate(antwoordtype="getal")))


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
        asyncio.run(svc.voeg_optie_toe(session, _TENANT_ID, _VRAAG_ID, OptieCreate(optie_sleutel="x", label="X")))


def test_voeg_optie_dubbele_sleutel_geweigerd():
    from models.models import AntwoordType
    from schemas.checklistconfig import OptieCreate
    from services import checklistconfig_service as svc
    from services.errors import ConfiguratieConflict

    session = AsyncMock()
    # vraag; niet-afgeleid (None); uniciteit → bestaand id
    session.execute.side_effect = [_result(_vraag("9.1", AntwoordType.enkelvoudige_keuze)), _result(None), _result(uuid.uuid4())]
    with pytest.raises(ConfiguratieConflict):
        asyncio.run(svc.voeg_optie_toe(session, _TENANT_ID, _VRAAG_ID, OptieCreate(optie_sleutel="ja", label="Ja")))


def test_voeg_optie_ok_stabiele_actieve_optie():
    from models.models import AntwoordType
    from schemas.checklistconfig import OptieCreate
    from services import checklistconfig_service as svc

    session = AsyncMock()
    session.execute.side_effect = [_result(_vraag("9.1", AntwoordType.enkelvoudige_keuze)), _result(None), _result(None)]
    toegevoegd = []
    session.add = lambda o: toegevoegd.append(o)
    asyncio.run(svc.voeg_optie_toe(session, _TENANT_ID, _VRAAG_ID, OptieCreate(optie_sleutel="ja", label="Ja", volgorde=2)))
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


def test_config_service_raakt_engine_bewust_wel():
    """ADR-022 W1: de config-service raakt sinds W1 BEWUST de lifecycle-engine.

    Vraag-mutaties die `aantal_vragen` van een componenttype wijzigen
    (toevoegen/(de)activeren) doen een in-tenant atomaire fan-out via
    `lifecycle_service.herbereken_lifecycle`. De voormalige invariant
    (`test_config_service_raakt_engine_niet`) is daarmee achterhaald: hij eiste
    dat de config-service `lifecycle_service`/`herbereken_lifecycle` NERGENS
    importeerde. We borgen nu het tegenovergestelde — de fan-out is gewenst.
    """
    import ast
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    bron = (root / "services" / "checklistconfig_service.py").read_text(encoding="utf-8")
    tree = ast.parse(bron)
    namen = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    namen |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            namen |= {a.name for a in node.names}

    assert "lifecycle_service" in namen, "W1: config-service hoort de engine te raken (fan-out)"
    assert "herbereken_lifecycle" in namen, "W1: config-service roept herbereken_lifecycle aan"


# ── Guard / RBAC-integratie (TENANT) ────────────────────────────────────────────

def _config_app(monkeypatch, payload):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.checklistconfig import router
    from services import checklistconfig_service as svc

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)
    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.include_router(router, prefix="/api/v1")

    async def _fake_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_tenant_session] = _fake_session
    # Service gemockt → de guard wordt geïsoleerd getest.
    monkeypatch.setattr(svc, "lijst_config", lambda *_a, **_k: _async([]))
    return app


_TENANT_A = "11111111-1111-1111-1111-111111111111"
_BEHEERDER = {"sub": "tb", "tenant_id": _TENANT_A, "realm_access": {"roles": ["beheerder"]}}
_VIEWER = {"sub": "tv", "tenant_id": _TENANT_A, "realm_access": {"roles": ["viewer"]}}


def _client(monkeypatch, payload):
    c = TestClient(_config_app(monkeypatch, payload))
    c.cookies.set(settings.cookie_name, "tok")
    return c


def test_config_lijst_401_zonder_sessie(monkeypatch):
    c = TestClient(_config_app(monkeypatch, _BEHEERDER))  # geen cookie
    assert c.get("/api/v1/checklistconfig").status_code == 401


def test_config_viewer_leest_wel(monkeypatch):
    assert _client(monkeypatch, _VIEWER).get("/api/v1/checklistconfig").status_code == 200


def test_config_beheerder_leest_wel(monkeypatch):
    assert _client(monkeypatch, _BEHEERDER).get("/api/v1/checklistconfig").status_code == 200


def test_config_viewer_mag_niet_wijzigen(monkeypatch):
    r = _client(monkeypatch, _VIEWER).patch(
        f"/api/v1/checklistconfig/vragen/{uuid.uuid4()}/antwoordtype", json={"antwoordtype": "getal"}
    )
    assert r.status_code == 403
    assert r.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


def test_config_viewer_mag_niet_toevoegen(monkeypatch):
    r = _client(monkeypatch, _VIEWER).post(
        f"/api/v1/checklistconfig/vragen/{uuid.uuid4()}/opties",
        json={"optie_sleutel": "ja", "label": "Ja"},
    )
    assert r.status_code == 403


def test_config_beheerder_mag_toevoegen(monkeypatch):
    from services import checklistconfig_service as svc

    optie = _optie(afgeleid_bron=None, label="Ja")
    monkeypatch.setattr(svc, "voeg_optie_toe", lambda *_a, **_k: _async(optie))
    r = _client(monkeypatch, _BEHEERDER).post(
        f"/api/v1/checklistconfig/vragen/{uuid.uuid4()}/opties",
        json={"optie_sleutel": "ja", "label": "Ja"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["optie_sleutel"] == "s"
