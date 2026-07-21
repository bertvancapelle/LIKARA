"""Tests — objecthistorie ('i'-knop, ADR-029).

Offline (route, gemockt): toegang volgt het object — geen AUDITLOG-recht nodig (viewer 200),
geen leesrecht op het type → 403, object buiten tenant → 404 (no-leak), onbekend type → 400.
Plus engine-import-afwezigheid. Live (skip-if-no-DB): component-historie + actor_naam-verrijking.
"""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings

TENANT_A = "11111111-1111-1111-1111-111111111111"
_COMP = "33333333-3333-3333-3333-333333333333"


def _payload(rollen):
    return {"sub": "u-1", "tenant_id": TENANT_A, "realm_access": {"roles": rollen}}


def _gebeurtenis():
    return {
        "correlatie_id": uuid.uuid4(),
        "tijdstip": datetime(2026, 6, 19, 10, 0, tzinfo=timezone.utc),
        "actor_sub": "u-1", "actor_email": "u1@test", "actor_naam": "Jan Tester",
        "records": [{
            "id": uuid.uuid4(), "tijdstip": datetime(2026, 6, 19, 10, 0, tzinfo=timezone.utc),
            "actor_sub": "u-1", "actor_email": "u1@test", "actor_naam": "Jan Tester",
            "entiteit_type": "component", "entiteit_id": uuid.UUID(_COMP), "actie": "update",
            "wijziging": {"naam": {"oud": "A", "nieuw": "B"}},
            "correlatie_id": uuid.uuid4(), "record_hash": "h" * 64, "vorige_hash": None,
        }],
    }


def _maak_app(monkeypatch, payload, *, haal_op_impl=None, lijst_impl=None):
    import app.middleware.auth as auth_mod
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from services.errors import NietGevonden, niet_gevonden_handler
    from routes import objecthistorie as route
    from services import auditlog_service as svc

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: payload)

    async def _ok_haal(*a, **k):
        return object()

    async def _ok_lijst(*a, **k):
        return ([_gebeurtenis()], None)

    from app.core.rbac import Entiteit
    monkeypatch.setitem(route._TYPES, "component",
                        (Entiteit.COMPONENT, haal_op_impl or _ok_haal, "component"))
    monkeypatch.setattr(svc, "lijst", lijst_impl or _ok_lijst)

    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.add_exception_handler(NietGevonden, niet_gevonden_handler)
    app.include_router(route.router, prefix="/api/v1")

    async def _fake_session():
        from types import SimpleNamespace
        yield SimpleNamespace()

    app.dependency_overrides[get_tenant_session] = _fake_session
    return app


def _client(app):
    c = TestClient(app)
    c.cookies.set(settings.cookie_name, "dummy")
    return c


def test_toegang_volgt_object_viewer_zonder_auditlogrecht(monkeypatch):
    """Viewer heeft COMPONENT.LEZEN maar GEEN AUDITLOG.LEZEN → krijgt tóch de objecthistorie."""
    app = _maak_app(monkeypatch, _payload(["viewer"]))
    resp = _client(app).get(f"/api/v1/objecthistorie/component/{_COMP}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"][0]["actor_naam"] == "Jan Tester"


def test_geen_leesrecht_op_type_403(monkeypatch):
    app = _maak_app(monkeypatch, _payload([]))  # geen rollen → geen COMPONENT.LEZEN
    resp = _client(app).get(f"/api/v1/objecthistorie/component/{_COMP}")
    assert resp.status_code == 403, resp.text
    assert resp.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


def test_object_buiten_tenant_404_no_leak(monkeypatch):
    from services.errors import NietGevonden

    async def _raise(*a, **k):
        raise NietGevonden("component", _COMP)

    app = _maak_app(monkeypatch, _payload(["beheerder"]), haal_op_impl=_raise)
    resp = _client(app).get(f"/api/v1/objecthistorie/component/{_COMP}")
    assert resp.status_code == 404, resp.text


def test_onbekend_entiteit_type_400(monkeypatch):
    app = _maak_app(monkeypatch, _payload(["beheerder"]))
    resp = _client(app).get(f"/api/v1/objecthistorie/onzin/{_COMP}")
    assert resp.status_code == 400, resp.text
    assert resp.json()["fout"]["code"] == "ONGELDIG_ENTITEIT_TYPE"


def test_objecthistorie_route_raakt_engine_niet():
    from routes import objecthistorie as route

    for naam in ("lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
                 "ComponentProfiel", "Blokkade", "Checklistscore"):
        assert not hasattr(route, naam), f"objecthistorie mag de engine niet importeren: {naam!r}"


def _maak_app_type(monkeypatch, payload, typ, *, haal_op_impl=None):
    """Als _maak_app, maar overschrijft de haal_op van een willekeurig type (eigen Entiteit blijft)."""
    from routes import objecthistorie as route

    async def _ok_haal(*a, **k):
        return object()

    ent, _real, modus = route._TYPES[typ]
    monkeypatch.setitem(route._TYPES, typ, (ent, haal_op_impl or _ok_haal, modus))
    # Hergebruik _maak_app voor de auth/handlers/session; die patcht 'component' los — onschadelijk.
    return _maak_app(monkeypatch, payload)


@pytest.mark.parametrize("typ", ["plateau", "work_package", "deliverable", "gap"])
def test_nieuwe_types_toegang_volgt_object(monkeypatch, typ):
    from services.errors import NietGevonden

    comp_id = "44444444-4444-4444-4444-444444444444"

    # 200 — viewer heeft leesrecht op de migratielaag (en géén AUDITLOG-recht nodig).
    app = _maak_app_type(monkeypatch, _payload(["viewer"]), typ)
    assert _client(app).get(f"/api/v1/objecthistorie/{typ}/{comp_id}").status_code == 200

    # 403 — geen rol → geen leesrecht op het type.
    app = _maak_app_type(monkeypatch, _payload([]), typ)
    r = _client(app).get(f"/api/v1/objecthistorie/{typ}/{comp_id}")
    assert r.status_code == 403 and r.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"

    # 404 — object buiten de tenant (no-leak).
    async def _raise(*a, **k):
        raise NietGevonden(typ, comp_id)

    app = _maak_app_type(monkeypatch, _payload(["beheerder"]), typ, haal_op_impl=_raise)
    assert _client(app).get(f"/api/v1/objecthistorie/{typ}/{comp_id}").status_code == 404


# ── Live ───────────────────────────────────────────────────────────────────────
import asyncio  # noqa: E402

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.core import tenant_context as tc  # noqa: E402

_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


def _db_bereikbaar() -> bool:
    async def _probe():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect():
                return True
        except Exception:
            return False
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_probe())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar (offline)")


@integratie
def test_objecthistorie_component_live_met_naam():
    from sqlalchemy import text as _text

    from app.core.database import _markeer_rls
    from models.models import GebruikerPersoon, PartijAard
    from schemas.component import ComponentCreate, ComponentUpdate
    from schemas.partij import PartijCreate
    from services import component_service, partij_service
    from services import auditlog_service as svc

    tid = uuid.UUID(TENANT_A)
    merk = uuid.uuid4().hex[:8]

    async def _flow():
        eng = create_async_engine(_LK_APP_URL)
        smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        t_tok = tc.zet_tenant_context(TENANT_A)
        ids = []
        try:
            async with smf() as s:
                _markeer_rls(s)
                a = tc.zet_audit_context(f"oh:jan:{merk}", "jan.oh@test")
                try:
                    org = await partij_service.maak_aan(s, tid, PartijCreate(aard=PartijAard.organisatie, naam=f"OHOrg-{merk}"))
                    persoon = await partij_service.maak_aan(s, tid, PartijCreate(
                        aard=PartijAard.persoon, naam=f"Jan OH {merk}", email=f"j.{merk}@org.test", organisatie_id=org.id))
                    s.add(GebruikerPersoon(tenant_id=tid, keycloak_sub=f"oh:jan:{merk}", persoon_id=persoon.id))
                    app_obj = await component_service.maak_aan(s, tid, ComponentCreate(componenttype="applicatie", 
                        naam=f"OHApp-{merk}", hostingmodel="saas", migratiepad=None,
                        complexiteit="midden", prioriteit="midden"))
                    await component_service.werk_bij(s, tid, app_obj["id"], ComponentUpdate(beschrijving="gewijzigd"))
                    ids += [org.id, persoon.id, app_obj["id"]]

                    items, _ = await svc.lijst(s, tid, component_id=app_obj["id"])
                    # De objecthistorie toont de gebeurtenissen van dít component, met geresolveerde naam.
                    assert items, "verwacht ≥1 gebeurtenis voor het component"
                    naam = f"Jan OH {merk}"
                    assert any(g["actor_naam"] == naam for g in items)
                finally:
                    tc.reset_audit_context(a)
        finally:
            async with smf() as s:
                _markeer_rls(s)
                a = tc.zet_audit_context("test:teardown", "td@test")
                try:
                    for eid in reversed(ids):
                        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
                    await s.commit()
                finally:
                    tc.reset_audit_context(a)
            tc.reset_tenant_context(t_tok)
            await eng.dispose()

    asyncio.run(_flow())


@integratie
def test_partijhistorie_bevat_een_LOSSE_roltoewijzing():
    """LI048 — het echte geval: de rol wordt in een APARTE handeling toegekend.

    Zat de roltoewijzing in dezelfde handeling als de partij-aanmaak, dan kwam hij altijd al mee
    via de correlatie-groepering — en dan oefent de toets zijn geval niet. Daarom hier twee
    gescheiden audit-contexten met een commit ertussen: dat levert twee correlaties op, en pas
    dan bewijst dit iets. (Het demolandschap bevat géén los geval; alle 75 roltoewijzingen op
    bestaande partijen ontstonden samen met hun partij.)
    """
    import uuid as _uuid

    from sqlalchemy import text as _text

    from app.core.database import _markeer_rls
    from models.models import PartijAard
    from schemas.component import ComponentCreate
    from schemas.partij import PartijCreate
    from services import auditlog_service as svc
    from services import component_service, partij_service, roltoewijzing_service

    tid = _uuid.UUID(TENANT_A)
    merk = _uuid.uuid4().hex[:8]

    async def _flow():
        eng = create_async_engine(_LK_APP_URL)
        smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        t_tok = tc.zet_tenant_context(TENANT_A)
        ids = []
        try:
            # Handeling 1: de partij en een component aanmaken.
            async with smf() as s:
                _markeer_rls(s)
                a = tc.zet_audit_context(f"rol:{merk}", f"rol.{merk}@test")
                try:
                    partij = await partij_service.maak_aan(s, tid, PartijCreate(
                        aard=PartijAard.externe_partij, naam=f"RolLev-{merk}"))
                    comp = await component_service.maak_aan(s, tid, ComponentCreate(
                        componenttype="applicatie", naam=f"RolApp-{merk}", hostingmodel="saas",
                        migratiepad=None, complexiteit="midden", prioriteit="midden"))
                    await s.commit()
                    ids += [partij.id, comp["id"]]
                finally:
                    tc.reset_audit_context(a)

            # Handeling 2 — APART, dus een eigen correlatie: de rol toekennen.
            async with smf() as s:
                _markeer_rls(s)
                a = tc.zet_audit_context(f"rol:{merk}", f"rol.{merk}@test")
                try:
                    await roltoewijzing_service.maak_aan(
                        s, tid, partij.id, _uuid.UUID(str(comp["id"])), "contractbeheer")
                    await s.commit()
                finally:
                    tc.reset_audit_context(a)

            # De partijhistorie moet die losse rol bevatten.
            async with smf() as s:
                _markeer_rls(s)
                items, _ = await svc.lijst(
                    s, tid, entiteit_type="partij", entiteit_id=partij.id, limit=50)
                soorten = {r.entiteit_type for g in items for r in g["records"]}
                assert "partij" in soorten, "de aanmaak van de partij zelf hoort er nog in"
                assert "roltoewijzing" in soorten, (
                    "een in een APARTE handeling toegekende rol hoort in de partijhistorie — "
                    f"gevonden soorten: {sorted(soorten)}"
                )
            return ids
        finally:
            async with smf() as s:
                _markeer_rls(s)
                a = tc.zet_audit_context("test:teardown", "td@test")
                try:
                    for eid in reversed(ids):
                        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
                    await s.commit()
                finally:
                    tc.reset_audit_context(a)
            tc.reset_tenant_context(t_tok)
            await eng.dispose()

    asyncio.run(_flow())
