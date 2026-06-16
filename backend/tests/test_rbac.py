"""Tests — RBAC rollenstructuur + rechtenmatrix + guard (ADR-010), offline."""
import asyncio

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rbac import (
    Actie,
    Entiteit,
    Rol,
    extract_rollen,
    heeft_permissie,
)
from app.middleware.auth import (
    AuthenticatedUser,
    NietGeauthenticeerd,
    _load_roles,
    niet_geauthenticeerd_handler,
)
from app.middleware.authz import (
    OnvoldoendeRechten,
    onvoldoende_rechten_handler,
    vereist_permissie,
)

# ── Onafhankelijke her-codering van de vastgestelde matrix (= spec) ───────────

_L = {Actie.LEZEN}
_LAW = {Actie.LEZEN, Actie.AANMAKEN, Actie.WIJZIGEN}
_LAWV = {Actie.LEZEN, Actie.AANMAKEN, Actie.WIJZIGEN, Actie.VERWIJDEREN}
_GEEN: set = set()

_INHOUD = {Rol.VIEWER: _L, Rol.MEDEWERKER: _LAW, Rol.BEHEERDER: _LAWV, Rol.AUDITOR: _L}

VERWACHT = {
    Entiteit.APPLICATIE: _INHOUD,
    Entiteit.DATATYPE: _INHOUD,
    Entiteit.GEBRUIKERSGROEP: _INHOUD,
    Entiteit.KOPPELING: _INHOUD,
    Entiteit.CHECKLISTSCORE: _INHOUD,
    Entiteit.BLOKKADE: _INHOUD,
    Entiteit.LEVERANCIER: _INHOUD,
    Entiteit.CONTRACT: _INHOUD,
    Entiteit.COMPONENT_CONTRACT: _INHOUD,
    Entiteit.COMPONENT: _INHOUD,            # ADR-021 Fase B (CD052)
    Entiteit.COMPONENT_STRUCTUUR: _INHOUD,  # ADR-021 Fase B (CD052)
    Entiteit.RELATIE: _INHOUD,              # ADR-023 — unified relatiemodel
    Entiteit.PLATEAU: _INHOUD,              # ADR-023 Fase E — migratielaag
    Entiteit.WORK_PACKAGE: _INHOUD,         # ADR-023 Fase E — migratielaag
    Entiteit.DELIVERABLE: _INHOUD,          # ADR-023 Fase E — migratielaag
    Entiteit.GAP: _INHOUD,                  # ADR-023 Fase E — migratielaag (E4)
    # ADR-023 Fase F / F-2: read-only laagprojectie — élke rol alleen LEZEN.
    Entiteit.ARCHITECTUUR: {
        Rol.VIEWER: _L, Rol.MEDEWERKER: _L, Rol.BEHEERDER: _L, Rol.AUDITOR: _L,
    },
    Entiteit.CHECKLISTVRAAG: _INHOUD,  # ADR-022 W1: tenant-eigen vragenset (CRUD)
    Entiteit.AUDITLOG: {
        Rol.VIEWER: _GEEN, Rol.MEDEWERKER: _GEEN, Rol.BEHEERDER: _L, Rol.AUDITOR: _L,
    },
    Entiteit.GEBRUIKERSBEHEER: {
        Rol.VIEWER: _GEEN, Rol.MEDEWERKER: _GEEN, Rol.BEHEERDER: _LAWV, Rol.AUDITOR: _GEEN,
    },
    Entiteit.TENANT_INSTELLINGEN: {
        Rol.VIEWER: _GEEN, Rol.MEDEWERKER: _GEEN, Rol.BEHEERDER: _LAWV, Rol.AUDITOR: _GEEN,
    },
}


def test_matrix_volledig_inclusief_negatief():
    """Elke entiteit × rol × actie (18×4×4 = 288 combinaties) tegen de spec."""
    assert set(VERWACHT) == set(Entiteit)  # geen entiteit gemist
    for entiteit, per_rol in VERWACHT.items():
        for rol in Rol:
            toegestaan = per_rol[rol]
            for actie in Actie:
                verwacht = actie in toegestaan
                assert heeft_permissie([rol.value], entiteit, actie) is verwacht, (
                    entiteit, rol, actie
                )


def test_kernregels_expliciet():
    # Medewerker mag NIET verwijderen (V is uitsluitend Beheerder)
    assert not heeft_permissie(["medewerker"], Entiteit.APPLICATIE, Actie.VERWIJDEREN)
    assert heeft_permissie(["beheerder"], Entiteit.APPLICATIE, Actie.VERWIJDEREN)
    # Viewer en Auditor muteren nooit
    for rol in ("viewer", "auditor"):
        for actie in (Actie.AANMAKEN, Actie.WIJZIGEN, Actie.VERWIJDEREN):
            assert not heeft_permissie([rol], Entiteit.CHECKLISTSCORE, actie)
    # Viewer geen auditlog; Beheerder/Auditor wel lezen
    assert not heeft_permissie(["viewer"], Entiteit.AUDITLOG, Actie.LEZEN)
    assert heeft_permissie(["auditor"], Entiteit.AUDITLOG, Actie.LEZEN)
    # Alleen Beheerder beheer (gebruikersbeheer + tenant-instellingen)
    for entiteit in (Entiteit.GEBRUIKERSBEHEER, Entiteit.TENANT_INSTELLINGEN):
        assert heeft_permissie(["beheerder"], entiteit, Actie.AANMAKEN)
        for rol in ("viewer", "medewerker", "auditor"):
            assert not heeft_permissie([rol], entiteit, Actie.LEZEN)
    # ADR-022 W1: de vragenset is tenant-eigendom — vraagbeheer volgt het inhoud-
    # patroon (medewerker mag muteren, viewer/auditor alleen lezen).
    for rol in ("viewer", "medewerker", "beheerder", "auditor"):
        assert heeft_permissie([rol], Entiteit.CHECKLISTVRAAG, Actie.LEZEN)
    assert heeft_permissie(["medewerker"], Entiteit.CHECKLISTVRAAG, Actie.WIJZIGEN)
    assert heeft_permissie(["beheerder"], Entiteit.CHECKLISTVRAAG, Actie.VERWIJDEREN)
    assert not heeft_permissie(["viewer"], Entiteit.CHECKLISTVRAAG, Actie.WIJZIGEN)
    assert not heeft_permissie(["auditor"], Entiteit.CHECKLISTVRAAG, Actie.WIJZIGEN)


def test_fail_secure_geen_of_onbekende_rol():
    assert not heeft_permissie([], Entiteit.APPLICATIE, Actie.LEZEN)
    assert not heeft_permissie(["root"], Entiteit.APPLICATIE, Actie.LEZEN)
    assert not heeft_permissie(["Viewer"], Entiteit.APPLICATIE, Actie.LEZEN)  # hoofdletter ≠ canoniek


# ── Keycloak-rolmapping ────────────────────────────────────────────────────────

def test_extract_realm_en_client_rollen_gesorteerd():
    payload = {
        "realm_access": {"roles": ["viewer", "offline_access"]},
        "resource_access": {settings.keycloak_client_id: {"roles": ["beheerder"]}},
    }
    assert extract_rollen(payload) == ["beheerder", "viewer"]


def test_extract_onbekende_rollen_genegeerd():
    assert extract_rollen({"realm_access": {"roles": ["uma_authorization", "x"]}}) == []
    assert extract_rollen({}) == []


def test_extract_met_role_prefix(monkeypatch):
    monkeypatch.setattr(settings, "keycloak_role_prefix", "cd-")
    payload = {"realm_access": {"roles": ["cd-beheerder", "beheerder", "cd-onbekend"]}}
    # Alleen geprefixte, bekende rol wordt geaccepteerd en ontdaan van prefix
    assert extract_rollen(payload) == ["beheerder"]


def test_load_roles_async_mapt_claims():
    rollen = asyncio.run(_load_roles({"realm_access": {"roles": ["auditor"]}}))
    assert rollen == ["auditor"]
    assert asyncio.run(_load_roles({})) == []  # fail-secure


# ── Enforcement-guard (integratie op een test-endpoint) ──────────────────────

def _maak_test_app():
    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.add_exception_handler(NietGeauthenticeerd, niet_geauthenticeerd_handler)

    @app.get("/verwijder-applicatie")
    async def _verwijder(
        user: AuthenticatedUser = Depends(
            vereist_permissie(Entiteit.APPLICATIE, Actie.VERWIJDEREN)
        ),
    ):
        return {"ok": True, "roles": user.roles}

    return app


def _payload(rollen):
    return {"sub": "u", "tenant_id": "tenant-1", "realm_access": {"roles": rollen}}


def test_guard_401_zonder_sessie():
    c = TestClient(_maak_test_app())
    r = c.get("/verwijder-applicatie")
    assert r.status_code == 401
    # Canoniek fout-envelope (ADR-014 B1): geen detail meer.
    assert r.json()["fout"]["code"] == "NIET_GEAUTHENTICEERD"
    assert r.json()["fout"]["http_status"] == 401
    assert "detail" not in r.json()


def test_guard_403_onvoldoende_rechten(monkeypatch):
    monkeypatch.setattr("app.middleware.auth.decode_token", lambda t: _payload(["medewerker"]))
    c = TestClient(_maak_test_app())
    c.cookies.set(settings.cookie_name, "tok")
    r = c.get("/verwijder-applicatie")
    assert r.status_code == 403
    assert r.json() == {
        "fout": {
            "code": "ONVOLDOENDE_RECHTEN",
            "http_status": 403,
            "bericht": "Onvoldoende rechten voor deze actie.",
        }
    }


def test_guard_200_voldoende_rechten(monkeypatch):
    monkeypatch.setattr("app.middleware.auth.decode_token", lambda t: _payload(["beheerder"]))
    c = TestClient(_maak_test_app())
    c.cookies.set(settings.cookie_name, "tok")
    r = c.get("/verwijder-applicatie")
    assert r.status_code == 200
    assert "beheerder" in r.json()["roles"]
