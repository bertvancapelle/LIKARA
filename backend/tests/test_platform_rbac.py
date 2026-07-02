"""Tests — platform-RBAC + aparte guard + strikte domein-scheiding (ADR-012)."""
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.platform_rbac import (
    PlatformEntiteit,
    PlatformRol,
    extract_platform_rollen,
    heeft_platform_permissie,
)
from app.core.rbac import Actie, Entiteit
from app.middleware.authz import (
    OnvoldoendeRechten,
    onvoldoende_rechten_handler,
    vereist_permissie,
    vereist_platform_permissie,
)

# Onafhankelijke her-codering van de platform-matrix (= spec)
_L = {Actie.LEZEN}
_LAW = {Actie.LEZEN, Actie.AANMAKEN, Actie.WIJZIGEN}
_LAWV = {Actie.LEZEN, Actie.AANMAKEN, Actie.WIJZIGEN, Actie.VERWIJDEREN}
_GEEN: set = set()

VERWACHT = {
    PlatformEntiteit.TENANT: {PlatformRol.PLATFORMBEHEERDER: _LAWV, PlatformRol.PLATFORMOPERATOR: _L},
    PlatformEntiteit.PLATFORMINSTELLINGEN: {PlatformRol.PLATFORMBEHEERDER: _LAWV, PlatformRol.PLATFORMOPERATOR: _GEEN},
    PlatformEntiteit.PLATFORMMETADATA: {PlatformRol.PLATFORMBEHEERDER: _L, PlatformRol.PLATFORMOPERATOR: _L},
    # ADR-012 Addendum A: checklistconfig — beheerder LAW (geen V), operator L.
    PlatformEntiteit.CHECKLISTCONFIG: {PlatformRol.PLATFORMBEHEERDER: _LAW, PlatformRol.PLATFORMOPERATOR: _L},
    # ADR-012 Addendum B: contractconfig — zelfde verdeling (geen V).
    PlatformEntiteit.CONTRACTCONFIG: {PlatformRol.PLATFORMBEHEERDER: _LAW, PlatformRol.PLATFORMOPERATOR: _L},
    # ADR-012 Addendum C: componentconfig — zelfde verdeling (geen V).
    PlatformEntiteit.COMPONENTCONFIG: {PlatformRol.PLATFORMBEHEERDER: _LAW, PlatformRol.PLATFORMOPERATOR: _L},
    # ADR-023 Fase F / F-4: relatiekenmerkconfig — zelfde verdeling (geen V).
    PlatformEntiteit.RELATIEKENMERKCONFIG: {PlatformRol.PLATFORMBEHEERDER: _LAW, PlatformRol.PLATFORMOPERATOR: _L},
    # Catalogi-beheer-schuld: vraagbetekenis + partijsoort — zelfde verdeling (geen V).
    PlatformEntiteit.VRAAGBETEKENISCONFIG: {PlatformRol.PLATFORMBEHEERDER: _LAW, PlatformRol.PLATFORMOPERATOR: _L},
    PlatformEntiteit.PARTIJSOORTCONFIG: {PlatformRol.PLATFORMBEHEERDER: _LAW, PlatformRol.PLATFORMOPERATOR: _L},
    # ADR-028: componentrol- + BIV-schaal-catalogus — zelfde verdeling (geen V, soft-deactivate).
    PlatformEntiteit.COMPONENTROLCONFIG: {PlatformRol.PLATFORMBEHEERDER: _LAW, PlatformRol.PLATFORMOPERATOR: _L},
    PlatformEntiteit.BIVSCHAALCONFIG: {PlatformRol.PLATFORMBEHEERDER: _LAW, PlatformRol.PLATFORMOPERATOR: _L},
}


def test_checklistconfig_geen_verwijderen_voor_wie_dan_ook():
    # Addendum A: soft-deactivate (W), nooit hard delete → V voor niemand.
    for rol in PlatformRol:
        assert not heeft_platform_permissie(
            [rol.value], PlatformEntiteit.CHECKLISTCONFIG, Actie.VERWIJDEREN
        )
    assert heeft_platform_permissie(["platformbeheerder"], PlatformEntiteit.CHECKLISTCONFIG, Actie.WIJZIGEN)
    assert not heeft_platform_permissie(["platformoperator"], PlatformEntiteit.CHECKLISTCONFIG, Actie.WIJZIGEN)


def test_contractconfig_geen_verwijderen_voor_wie_dan_ook():
    # Addendum B: soft-deactivate (W), nooit hard delete → V voor niemand.
    for rol in PlatformRol:
        assert not heeft_platform_permissie(
            [rol.value], PlatformEntiteit.CONTRACTCONFIG, Actie.VERWIJDEREN
        )
    assert heeft_platform_permissie(["platformbeheerder"], PlatformEntiteit.CONTRACTCONFIG, Actie.WIJZIGEN)
    assert not heeft_platform_permissie(["platformoperator"], PlatformEntiteit.CONTRACTCONFIG, Actie.WIJZIGEN)


def test_platform_matrix_volledig_incl_negatief():
    assert set(VERWACHT) == set(PlatformEntiteit)
    for entiteit, per_rol in VERWACHT.items():
        for rol in PlatformRol:
            toegestaan = per_rol[rol]
            for actie in Actie:
                assert heeft_platform_permissie([rol.value], entiteit, actie) is (
                    actie in toegestaan
                ), (entiteit, rol, actie)


def test_platform_kernregels():
    # operator mag NIETS muteren en geen platforminstellingen lezen
    assert not heeft_platform_permissie(["platformoperator"], PlatformEntiteit.TENANT, Actie.AANMAKEN)
    assert not heeft_platform_permissie(["platformoperator"], PlatformEntiteit.PLATFORMINSTELLINGEN, Actie.LEZEN)
    assert heeft_platform_permissie(["platformoperator"], PlatformEntiteit.TENANT, Actie.LEZEN)
    # beheerder volledige CRUD op Tenant + instellingen
    assert heeft_platform_permissie(["platformbeheerder"], PlatformEntiteit.TENANT, Actie.VERWIJDEREN)
    assert heeft_platform_permissie(["platformbeheerder"], PlatformEntiteit.PLATFORMINSTELLINGEN, Actie.AANMAKEN)


def test_platform_fail_secure():
    assert not heeft_platform_permissie([], PlatformEntiteit.TENANT, Actie.LEZEN)
    assert not heeft_platform_permissie(["root"], PlatformEntiteit.TENANT, Actie.LEZEN)
    # tenant-rol telt NIET in het platform-domein
    assert not heeft_platform_permissie(["beheerder"], PlatformEntiteit.TENANT, Actie.LEZEN)


def test_extract_platform_rollen_scheidt_domeinen():
    # platform-rollen worden gelezen; tenant-rollen genegeerd
    assert extract_platform_rollen({"realm_access": {"roles": ["platformbeheerder", "beheerder"]}}) == ["platformbeheerder"]
    assert extract_platform_rollen({"realm_access": {"roles": ["viewer", "auditor"]}}) == []
    assert extract_platform_rollen({}) == []


# ── Guard-integratie + kruis-scheiding ───────────────────────────────────────

def _app():
    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)

    @app.get("/platform/tenant-read")
    async def _pr(u=Depends(vereist_platform_permissie(PlatformEntiteit.TENANT, Actie.LEZEN))):
        return {"roles": u.roles}

    @app.post("/platform/tenant-create")
    async def _pc(u=Depends(vereist_platform_permissie(PlatformEntiteit.TENANT, Actie.AANMAKEN))):
        return {"roles": u.roles}

    @app.delete("/tenant/component")
    async def _td(u=Depends(vereist_permissie(Entiteit.COMPONENT, Actie.VERWIJDEREN))):
        return {"roles": u.roles}

    return app


_PB = {"sub": "pb", "realm_access": {"roles": ["platformbeheerder"]}}
_PO = {"sub": "po", "realm_access": {"roles": ["platformoperator"]}}
_TENANT = {"sub": "tb", "tenant_id": "t1", "realm_access": {"roles": ["beheerder"]}}


def _client(monkeypatch, payload):
    monkeypatch.setattr("app.middleware.auth.decode_token", lambda t: payload)
    c = TestClient(_app())
    c.cookies.set(settings.cookie_name, "tok")
    return c


def test_platform_endpoint_401_zonder_sessie():
    c = TestClient(_app())
    assert c.get("/platform/tenant-read").status_code == 401


def test_platformbeheerder_mag_tenant_aanmaken(monkeypatch):
    r = _client(monkeypatch, _PB).post("/platform/tenant-create")
    assert r.status_code == 200
    assert r.json()["roles"] == ["platformbeheerder"]


def test_platformoperator_leest_wel_maakt_niet(monkeypatch):
    c = _client(monkeypatch, _PO)
    assert c.get("/platform/tenant-read").status_code == 200
    r = c.post("/platform/tenant-create")
    assert r.status_code == 403
    assert r.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


def test_kruis_tenantrol_op_platform_endpoint_403(monkeypatch):
    r = _client(monkeypatch, _TENANT).post("/platform/tenant-create")
    assert r.status_code == 403
    assert r.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"


def test_kruis_platformrol_op_tenant_endpoint_403(monkeypatch):
    # platform-account heeft geen tenant_id ⇒ get_current_user weigert (403)
    r = _client(monkeypatch, _PB).delete("/tenant/component")
    assert r.status_code == 403
