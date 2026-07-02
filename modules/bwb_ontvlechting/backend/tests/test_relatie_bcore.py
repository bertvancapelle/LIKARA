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

    ok = RelatieCreate(bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL), relatietype="flow", naam="StUF")
    assert ok.kenmerken == {} and ok.relatietype == "flow" and ok.naam == "StUF"
    assert ok.negeer_waarschuwing is False
    with pytest.raises(ValidationError):
        RelatieCreate(bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL), relatietype="flow", naam="x", onbekend=1)
    with pytest.raises(ValidationError):
        RelatieCreate(bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL), relatietype="  ", naam="x")


def test_naam_verplicht_voor_flow_optioneel_voor_andere_typen():
    """ADR-023a — (d) naam ontbreekt bij flow → validatiefout; (e) naam optioneel bij niet-flow."""
    from pydantic import ValidationError

    from schemas.relatie import RelatieCreate

    with pytest.raises(ValidationError):  # (d) flow zonder naam
        RelatieCreate(bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL), relatietype="flow")
    with pytest.raises(ValidationError):  # flow met lege naam
        RelatieCreate(bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL), relatietype="flow", naam="   ")
    # (e) niet-flow zonder naam → toegestaan
    ok = RelatieCreate(bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL), relatietype="association")
    assert ok.naam is None


# ── Route + RBAC (offline, gemockte service) ─────────────────────────────────────

def _fake_relatie():
    from datetime import datetime, timezone
    return SimpleNamespace(
        id=uuid.UUID(_REL), bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL),
        relatietype="flow", naam="StUF-berichtenverkeer", kenmerken={"protocol": "api"}, omschrijving=None,
        dubbel_waarschuwing_genegeerd=False,
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
    ("A", "POST", "/api/v1/relaties", {"bron_id": _BRON, "doel_id": _DOEL, "relatietype": "flow", "naam": "StUF"}, 201),
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

_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


def _relatie_tabel_bestaat() -> bool:
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
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
    from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict

    async def _comp(s, tid, naam):
        elem = Element(tenant_id=tid, element_type=ElementType.component)
        s.add(elem); await s.flush()
        c = Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="integratievoorziening",
                      hostingmodel="on_premise")
        s.add(c); await s.flush()
        return c.id

    async def _run():
        eng = create_async_engine(_LK_APP_URL)
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
                    # geldige flow-relatie met kenmerk protocol (naam verplicht voor flow, ADR-023a)
                    rel = await relatie_service.maak_aan(
                        s, TENANT_A,
                        RelatieCreate(bron_id=a, doel_id=b, relatietype="flow", naam="StUF",
                                      kenmerken={"protocol": "api"}),
                    )
                    resultaten = {"created": rel.id, "bron": rel.bron_id, "doel": rel.doel_id}
                    # bron≠doel
                    try:
                        await relatie_service.maak_aan(
                            s, TENANT_A, RelatieCreate(bron_id=a, doel_id=a, relatietype="flow", naam="X"))
                        resultaten["zelf"] = "GEEN_FOUT"
                    except OngeldigeRegistratie as e:
                        resultaten["zelf"] = e.code
                    # onbekend relatietype (niet-flow → naam niet vereist)
                    try:
                        await relatie_service.maak_aan(
                            s, TENANT_A, RelatieCreate(bron_id=a, doel_id=b, relatietype="bestaat_niet"))
                        resultaten["type"] = "GEEN_FOUT"
                    except OngeldigeRegistratie as e:
                        resultaten["type"] = e.code
                    # ongeldig kenmerk (protocol-waarde fout)
                    try:
                        await relatie_service.maak_aan(
                            s, TENANT_A, RelatieCreate(bron_id=b, doel_id=a, relatietype="flow", naam="X",
                                                       kenmerken={"protocol": "telepathie"}))
                        resultaten["kenmerk"] = "GEEN_FOUT"
                    except OngeldigeRegistratie as e:
                        resultaten["kenmerk"] = e.code
                    # niet-bestaand endpoint
                    try:
                        await relatie_service.maak_aan(
                            s, TENANT_A, RelatieCreate(bron_id=a, doel_id=uuid.uuid4(), relatietype="flow", naam="X"))
                        resultaten["endpoint"] = "GEEN_FOUT"
                    except NietGevonden:
                        resultaten["endpoint"] = "NIET_GEVONDEN"

                    # ADR-023a (a) — tweede flow a→b met ANDERE naam → toegestaan (meervoud).
                    rel_a = await relatie_service.maak_aan(
                        s, TENANT_A, RelatieCreate(bron_id=a, doel_id=b, relatietype="flow",
                                                   naam="Andere koppeling", kenmerken={"protocol": "api"}))
                    resultaten["tweede_naam"] = "OK" if rel_a.id != rel.id else "ZELFDE"
                    # (b) — flow identiek op alles BEHALVE omschrijving → KOPPELING_DUBBEL.
                    try:
                        await relatie_service.maak_aan(
                            s, TENANT_A, RelatieCreate(bron_id=a, doel_id=b, relatietype="flow", naam="StUF",
                                                       kenmerken={"protocol": "api"}, omschrijving="andere toelichting"))
                        resultaten["dubbel"] = "GEEN_FOUT"
                    except RegistratieConflict as e:
                        resultaten["dubbel"] = e.code
                    # (c) — zelfde dubbel mét negeer_waarschuwing=True → tóch aangemaakt + markering.
                    rel_c = await relatie_service.maak_aan(
                        s, TENANT_A, RelatieCreate(bron_id=a, doel_id=b, relatietype="flow", naam="StUF",
                                                   kenmerken={"protocol": "api"}, negeer_waarschuwing=True))
                    resultaten["overrule"] = "OK" if rel_c.id else "FAAL"
                    resultaten["overrule_markering"] = rel_c.dubbel_waarschuwing_genegeerd
                    # negeer_waarschuwing=True ZONDER bestaande dubbel → markering blijft false.
                    rel_d = await relatie_service.maak_aan(
                        s, TENANT_A, RelatieCreate(bron_id=a, doel_id=b, relatietype="flow",
                                                   naam="Geen-dubbel", kenmerken={"protocol": "api"},
                                                   negeer_waarschuwing=True))
                    resultaten["geen_dubbel_markering"] = rel_d.dubbel_waarschuwing_genegeerd
                    # non-flow blijft uniek: tweede association a→b → RELATIE_BESTAAT.
                    await relatie_service.maak_aan(
                        s, TENANT_A, RelatieCreate(bron_id=a, doel_id=b, relatietype="association"))
                    try:
                        await relatie_service.maak_aan(
                            s, TENANT_A, RelatieCreate(bron_id=a, doel_id=b, relatietype="association"))
                        resultaten["assoc_dubbel"] = "GEEN_FOUT"
                    except RegistratieConflict as e:
                        resultaten["assoc_dubbel"] = e.code
                    # Engine onaangeroerd: het aanmaken van flows liet GEEN component_profiel ontstaan.
                    resultaten["profielen"] = (
                        await s.execute(text("SELECT count(*) FROM component_profiel WHERE id IN (:a,:b)"),
                                        {"a": str(a), "b": str(b)})
                    ).scalar()
                    # opruimen (element-delete cascadeert de relaties)
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
    # ADR-023a
    assert r["tweede_naam"] == "OK"          # (a) tweede flow met andere naam toegestaan
    assert r["dubbel"] == "KOPPELING_DUBBEL"  # (b) identiek (omschrijving uitgezonderd) → signalering
    assert r["overrule"] == "OK"             # (c) negeer_waarschuwing=True → tóch aangemaakt
    assert r["assoc_dubbel"] == "RELATIE_BESTAAT"  # non-flow blijft uniek
    assert r["profielen"] == 0               # engine onaangeroerd (geen component_profiel)
    assert r["overrule_markering"] is True   # echte override → markering gezet
    assert r["geen_dubbel_markering"] is False  # geen dubbel → geen markering


@live
def test_relatie_paar_filter_symmetrie_live():
    """ADR-023a Fase 3 — `paar_bron_id`+`paar_doel_id` filtert op het ONGEORDENDE paar:
    (A,B) levert exact dezelfde flows als (B,A), inclusief beide richtingen; het gerichte
    `bron_id`-filter levert daarentegen alleen één richting."""
    from app.core import tenant_context as tc
    from app.core.database import _markeer_rls
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from models.models import Component, Element, ElementType, Relatie
    from services import relatie_service

    async def _comp(s, tid, naam):
        elem = Element(tenant_id=tid, element_type=ElementType.component)
        s.add(elem); await s.flush()
        s.add(Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="integratievoorziening",
                        hostingmodel="on_premise"))
        await s.flush()
        return elem.id

    async def _run():
        eng = create_async_engine(_LK_APP_URL)
        smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        tid = uuid.UUID(TENANT_A)
        try:
            tok = tc.zet_tenant_context(TENANT_A); atok = tc.zet_audit_context("system:dev_seed")
            try:
                async with smf() as s:
                    _markeer_rls(s)
                    a = await _comp(s, tid, f"PAAR-A-{uuid.uuid4().hex[:6]}")
                    b = await _comp(s, tid, f"PAAR-B-{uuid.uuid4().hex[:6]}")
                    # twee flows a→b + één flow b→a (direct ORM; naam nullable in DB)
                    s.add(Relatie(tenant_id=tid, bron_id=a, doel_id=b, relatietype="flow", naam="f1"))
                    s.add(Relatie(tenant_id=tid, bron_id=a, doel_id=b, relatietype="flow", naam="f2"))
                    s.add(Relatie(tenant_id=tid, bron_id=b, doel_id=a, relatietype="flow", naam="f3"))
                    await s.commit()

                    ab, _ = await relatie_service.lijst(s, TENANT_A, paar_bron_id=a, paar_doel_id=b, relatietype="flow")
                    ba, _ = await relatie_service.lijst(s, TENANT_A, paar_bron_id=b, paar_doel_id=a, relatietype="flow")
                    gericht, _ = await relatie_service.lijst(s, TENANT_A, bron_id=a, doel_id=b, relatietype="flow")
                    r = {
                        "paar_ab": sorted(str(x.id) for x in ab),
                        "paar_ba": sorted(str(x.id) for x in ba),
                        "paar_aantal": len(ab),
                        "gericht_aantal": len(gericht),
                    }
                    await s.execute(text("DELETE FROM element WHERE id IN (:a,:b)"), {"a": str(a), "b": str(b)})
                    await s.commit()
                    return r
            finally:
                tc.reset_audit_context(atok); tc.reset_tenant_context(tok)
        finally:
            await eng.dispose()

    r = asyncio.run(_run())
    assert r["paar_ab"] == r["paar_ba"]   # ongeordend: (A,B) ≡ (B,A)
    assert r["paar_aantal"] == 3          # beide richtingen samen
    assert r["gericht_aantal"] == 2       # gericht bron=a,doel=b: alleen die richting


# ── Sortering: allowlist (offline) + cursor-mismatch (offline, vóór session-gebruik) ──

@pytest.mark.parametrize("query", ["sort=bogus", "order=zijwaarts", "sort=naam&order=krom"])
def test_lijst_sort_order_allowlist_422(monkeypatch, query):
    """Onbekende sort/order → 422 op de API-rand (Query-pattern), svc wordt niet bereikt."""
    app = _maak_app(monkeypatch, _payload("viewer"))
    resp = _client(app).get(f"/api/v1/relaties?{query}")
    assert resp.status_code == 422, resp.text


@pytest.mark.parametrize("query", ["sort=naam", "sort=naam&order=desc", "sort=created_at&order=asc"])
def test_lijst_sort_order_geldig_200(monkeypatch, query):
    app = _maak_app(monkeypatch, _payload("viewer"))
    assert _client(app).get(f"/api/v1/relaties?{query}").status_code == 200


def test_lijst_cursor_mismatch_400(monkeypatch):
    """Een v2n naam-cursor bij een sort=created_at-request → 400 ONGELDIGE_CURSOR (de service
    detecteert de versie-/sort-mismatch vóór enige DB-toegang; echte svc, dummy-sessie)."""
    import app.middleware.auth as auth_mod
    from app.middleware.tenant import get_tenant_session
    from routes.relatie import router
    from services.pagination import encode_sort_cursor_nullable

    monkeypatch.setattr(auth_mod, "decode_token", lambda token: _payload("viewer"))
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def _fake_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_tenant_session] = _fake_session
    bad = encode_sort_cursor_nullable(sort="naam", order="asc", waarde="X", id=uuid.UUID(_REL))
    resp = _client(app).get(f"/api/v1/relaties?after={bad}&sort=created_at")
    assert resp.status_code == 400, resp.text
    assert resp.json()["fout"]["code"] == "ONGELDIGE_CURSOR"


@live
def test_lijst_naam_sort_v2n_live():
    """ADR-023a Fase 4 — v2n naam-sortering: asc oplopend, desc aflopend, NULL altijd achteraan,
    en keyset-paginering levert de juiste vervolgpagina."""
    from app.core import tenant_context as tc
    from app.core.database import _markeer_rls
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from models.models import Component, Element, ElementType, Relatie
    from services import relatie_service

    async def _comp(s, tid, naam):
        elem = Element(tenant_id=tid, element_type=ElementType.component); s.add(elem); await s.flush()
        s.add(Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="integratievoorziening",
                        hostingmodel="on_premise")); await s.flush()
        return elem.id

    async def _run():
        eng = create_async_engine(_LK_APP_URL)
        smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        tid = uuid.UUID(TENANT_A)
        try:
            tok = tc.zet_tenant_context(TENANT_A); atok = tc.zet_audit_context("system:dev_seed")
            try:
                async with smf() as s:
                    _markeer_rls(s)
                    a = await _comp(s, tid, f"NS-A-{uuid.uuid4().hex[:6]}")
                    b = await _comp(s, tid, f"NS-B-{uuid.uuid4().hex[:6]}")
                    # 3 named flows + 1 zonder naam (direct ORM; naam nullable). Verschillende namen
                    # → geen dubbel. Gescoped via paar-filter zodat alleen deze 4 meetellen.
                    for nm in ("Naam-B", "Naam-A", "Naam-C", None):
                        s.add(Relatie(tenant_id=tid, bron_id=a, doel_id=b, relatietype="flow", naam=nm))
                    await s.commit()
                    kw = dict(paar_bron_id=a, paar_doel_id=b, relatietype="flow")

                    asc, _ = await relatie_service.lijst(s, TENANT_A, sort="naam", order="asc", **kw)
                    desc, _ = await relatie_service.lijst(s, TENANT_A, sort="naam", order="desc", **kw)
                    p1, cur1 = await relatie_service.lijst(s, TENANT_A, sort="naam", order="asc", limit=2, **kw)
                    p2, _ = await relatie_service.lijst(s, TENANT_A, sort="naam", order="asc", limit=2, after=cur1, **kw)
                    r = {
                        "asc": [x.naam for x in asc],
                        "desc": [x.naam for x in desc],
                        "p1": [x.naam for x in p1],
                        "p2": [x.naam for x in p2],
                        "cur1": cur1,
                    }
                    await s.execute(text("DELETE FROM element WHERE id IN (:a,:b)"), {"a": str(a), "b": str(b)})
                    await s.commit()
                    return r
            finally:
                tc.reset_audit_context(atok); tc.reset_tenant_context(tok)
        finally:
            await eng.dispose()

    r = asyncio.run(_run())
    assert r["asc"] == ["Naam-A", "Naam-B", "Naam-C", None]   # oplopend, NULL achteraan
    assert r["desc"] == ["Naam-C", "Naam-B", "Naam-A", None]  # aflopend, NULL nog steeds achteraan
    assert r["p1"] == ["Naam-A", "Naam-B"] and r["cur1"]      # eerste pagina + vervolgcursor
    assert r["p2"] == ["Naam-C", None]                        # tweede pagina (keyset over NULL-grens)


def test_audit_capture_dubbel_markering():
    """ADR-023a — de override-markering is een mapped column → de audit-diff (bouw_wijziging)
    capture't hem automatisch, dus de override verschijnt in de objecthistorie van de koppeling."""
    from app.core.audit import AUDIT_TENANT_ENTITEITEN, AuditActie, bouw_wijziging
    from models.models import Relatie

    obj = Relatie(
        tenant_id=uuid.UUID(TENANT_A), bron_id=uuid.UUID(_BRON), doel_id=uuid.UUID(_DOEL),
        relatietype="flow", naam="StUF", kenmerken={}, dubbel_waarschuwing_genegeerd=True,
    )
    w = bouw_wijziging(obj, AuditActie.create)
    assert "dubbel_waarschuwing_genegeerd" in w
    assert w["dubbel_waarschuwing_genegeerd"]["nieuw"] is True
    assert "relatie" in AUDIT_TENANT_ENTITEITEN


def test_relatie_service_engine_vrij():
    """Engine-borging (offline): relatie_service importeert geen lifecycle/score/blokkade-symbolen."""
    from services import relatie_service as m

    for naam in ("lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
                 "ComponentProfiel", "Blokkade", "Checklistscore"):
        assert not hasattr(m, naam), f"relatie_service mag {naam} niet importeren"
