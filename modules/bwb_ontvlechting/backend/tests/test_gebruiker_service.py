"""Tests — gebruikersbeheer (ADR-029 Fase 2).

Offline: schema-validatie, engine-import-afwezigheid, RBAC (GEBRUIKERSBEHEER), wachtwoord-
generator, en de service-foutpaden (email-duplicaat / Keycloak-fout-rollback / commit-fout-
cleanup) met gemockte sessie + gemockte Keycloak. Live (skip-if-no-DB): happy aanmaak + naam-join
+ engine-geen-mutatie. Keycloak wordt overal gemockt — geen live IAM in de tests.
"""
import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

import app.core.audit  # noqa: F401  (capture-hook)
import app.core.database  # noqa: F401
from app.core.tenant_context import (
    reset_audit_context,
    reset_tenant_context,
    zet_audit_context,
    zet_tenant_context,
)

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


def _result(val):
    r = MagicMock()
    r.scalar_one_or_none.return_value = val
    return r


# ── Offline: schema's ─────────────────────────────────────────────────────────
def test_request_geen_wachtwoordveld_en_extra_forbid():
    from schemas.gebruiker import GebruikerAanmakenRequest

    ok = GebruikerAanmakenRequest(naam="Jan Jansen", email="Jan@Org.NL")
    assert ok.email == "jan@org.nl" and ok.rol == "medewerker"  # genormaliseerd + default
    with pytest.raises(ValidationError):  # wachtwoord meesturen mag niet (extra=forbid)
        GebruikerAanmakenRequest(naam="Jan", email="jan@org.nl", tijdelijk_wachtwoord="x")
    with pytest.raises(ValidationError):  # ongeldig e-mailadres
        GebruikerAanmakenRequest(naam="Jan", email="geen-email")
    with pytest.raises(ValidationError):  # rol buiten de allowlist
        GebruikerAanmakenRequest(naam="Jan", email="jan@org.nl", rol="beheerder")


def test_read_schema_bevat_geen_wachtwoord():
    from schemas.gebruiker import GebruikerPersoonRead

    assert "tijdelijk_wachtwoord" not in GebruikerPersoonRead.model_fields
    assert "wachtwoord" not in GebruikerPersoonRead.model_fields


# ── Offline: engine-borging (import-afwezigheid) ───────────────────────────────
def test_gebruiker_service_raakt_engine_niet():
    import services.gebruiker_service as s

    for naam in ("lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
                 "ComponentProfiel", "Blokkade", "Checklistscore"):
        assert not hasattr(s, naam), f"gebruiker-service mag de engine niet importeren: {naam!r}"


# ── Offline: RBAC ──────────────────────────────────────────────────────────────
def test_gebruikersbeheer_alleen_beheerder():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    assert heeft_permissie(["beheerder"], Entiteit.GEBRUIKERSBEHEER, Actie.AANMAKEN)
    assert heeft_permissie(["beheerder"], Entiteit.GEBRUIKERSBEHEER, Actie.LEZEN)
    assert heeft_permissie(["beheerder"], Entiteit.GEBRUIKERSBEHEER, Actie.WIJZIGEN)  # 2b — beheeracties
    for rol in ("viewer", "medewerker", "auditor"):
        assert not heeft_permissie([rol], Entiteit.GEBRUIKERSBEHEER, Actie.LEZEN)
        assert not heeft_permissie([rol], Entiteit.GEBRUIKERSBEHEER, Actie.AANMAKEN)
        assert not heeft_permissie([rol], Entiteit.GEBRUIKERSBEHEER, Actie.WIJZIGEN)


# ── Offline: 2b-schema's ────────────────────────────────────────────────────────
def test_2b_schemas_validatie():
    from schemas.gebruiker import (
        GebruikerCorrectieRequest, GebruikerRolWijzigRequest, GebruikerStatusRequest,
    )

    for r in ("viewer", "medewerker", "beheerder", "auditor"):
        assert GebruikerRolWijzigRequest(rol=r).rol == r
    with pytest.raises(ValidationError):
        GebruikerRolWijzigRequest(rol="root")  # buiten de allowlist
    assert GebruikerStatusRequest(actief=False).actief is False
    ok = GebruikerCorrectieRequest(naam="Nieuwe Naam", email="Nieuw@Org.NL")
    assert ok.email == "nieuw@org.nl"  # genormaliseerd
    with pytest.raises(ValidationError):
        GebruikerCorrectieRequest(naam="X", email="geen-email")
    with pytest.raises(ValidationError):  # geen serverbeheerd veld meesturen (extra=forbid)
        GebruikerCorrectieRequest(naam="X", email="x@org.nl", rol="beheerder")


# ── Offline: wachtwoord-generator ──────────────────────────────────────────────
def test_wachtwoord_generator_sterk_en_uniek():
    from app.core.keycloak import genereer_tijdelijk_wachtwoord

    pws = {genereer_tijdelijk_wachtwoord() for _ in range(20)}
    assert len(pws) == 20  # willekeurig (geen botsingen)
    for pw in pws:
        assert len(pw) >= 16
        assert any(c.isupper() for c in pw) and any(c.isdigit() for c in pw)


# ── Offline: provisioning-PUT-payload (LI032 — geen username meesturen) ─────────
def test_werk_keycloak_gegevens_bij_stuurt_geen_username(monkeypatch):
    """De update-PUT synct ALLEEN email/firstName/lastName — NOOIT `username`. Een username-
    wijziging (username≠email) faalt onder editUsernameAllowed=False; login gaat via e-mail en
    de identiteit hangt aan `sub`, dus username hoort niet in de payload (LI032)."""
    from app.core import keycloak

    monkeypatch.setattr(keycloak, "get_provisioning_token", AsyncMock(return_value="tok"))
    put_mock = AsyncMock(return_value=SimpleNamespace(status_code=204))
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=SimpleNamespace(put=put_mock))
    client.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(keycloak.httpx, "AsyncClient", lambda *a, **k: client)

    asyncio.run(keycloak.werk_keycloak_gegevens_bij("sub-x", naam="Jan de Vries", email="jan@org.test"))

    put_mock.assert_awaited_once()
    payload = put_mock.await_args.kwargs["json"]
    assert "username" not in payload  # kern van de fix
    assert payload == {"email": "jan@org.test", "firstName": "Jan", "lastName": "de Vries"}


# ── Offline: service-foutpaden (gemockte sessie + Keycloak) ─────────────────────
def _patch_kc(monkeypatch, *, sub="kc-sub-1", fout=False):
    import services.gebruiker_service as svc

    async def _maak(**_k):
        if fout:
            from app.core.keycloak import KeycloakProvisioningFout
            raise KeycloakProvisioningFout("KC down", 502)
        return sub

    monkeypatch.setattr(svc.keycloak, "maak_keycloak_gebruiker", _maak)
    monkeypatch.setattr(svc.keycloak, "deactiveer_keycloak_gebruiker", AsyncMock())
    return svc


def test_maak_gebruiker_email_al_in_gebruik(monkeypatch):
    svc = _patch_kc(monkeypatch)
    from services.errors import OngeldigeRegistratie

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result(uuid.uuid4()))  # email al gekoppeld
    with pytest.raises(OngeldigeRegistratie) as exc:
        asyncio.run(svc.maak_gebruiker(
            session, _TID, naam="Jan", email="jan@org.nl", afdeling_id=uuid.uuid4(),
            functietitel=None, rol="medewerker"))
    assert exc.value.code == "EMAIL_AL_IN_GEBRUIK"


def test_maak_gebruiker_kc_fout_rollt_terug(monkeypatch):
    svc = _patch_kc(monkeypatch, fout=True)
    from services.errors import KeycloakNietBeschikbaar

    async def _persoon(*a, **k):
        return SimpleNamespace(id=uuid.uuid4(), naam="Jan", email="jan@org.nl")

    monkeypatch.setattr(svc.partij_service, "maak_persoon_flush", _persoon)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result(None))  # email vrij
    with pytest.raises(KeycloakNietBeschikbaar):
        asyncio.run(svc.maak_gebruiker(
            session, _TID, naam="Jan", email="jan@org.nl", afdeling_id=uuid.uuid4(),
            functietitel=None, rol="medewerker"))
    session.rollback.assert_awaited()           # DB teruggerold (geen half-aangemaakte persoon)
    session.commit.assert_not_awaited()


def test_maak_gebruiker_commit_fout_deactiveert_kc(monkeypatch):
    svc = _patch_kc(monkeypatch, sub="kc-sub-9")
    from services.errors import KeycloakNietBeschikbaar

    async def _persoon(*a, **k):
        return SimpleNamespace(id=uuid.uuid4(), naam="Jan", email="jan@org.nl")

    monkeypatch.setattr(svc.partij_service, "maak_persoon_flush", _persoon)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_result(None))
    session.add = MagicMock()
    session.commit = AsyncMock(side_effect=RuntimeError("commit faalt"))
    with pytest.raises(KeycloakNietBeschikbaar):
        asyncio.run(svc.maak_gebruiker(
            session, _TID, naam="Jan", email="jan@org.nl", afdeling_id=uuid.uuid4(),
            functietitel=None, rol="medewerker"))
    # Orphan-cleanup: het al-aangemaakte KC-account wordt gedeactiveerd.
    svc.keycloak.deactiveer_keycloak_gebruiker.assert_awaited_once_with("kc-sub-9")


# ── Live (skip-if-no-DB) ───────────────────────────────────────────────────────
def _db_bereikbaar() -> bool:
    async def _probe():
        from sqlalchemy.ext.asyncio import create_async_engine

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


async def _run_rls(fn, tid=_TID):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tok = zet_tenant_context(tid)
    audit_tok = zet_audit_context(actor_sub="test:adr029", actor_email="adr029@test", correlatie_id=None)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_audit_context(audit_tok)
        reset_tenant_context(tok)
        await eng.dispose()


@integratie
def test_maak_gebruiker_live_happy_en_geen_mutatie(monkeypatch):
    """Volledige flow tegen de DB met gemockte Keycloak: persoon + koppelrij ontstaan, naam-join
    klopt, en de lifecycle van een los component blijft ongewijzigd (engine onaangeroerd)."""
    from sqlalchemy import text as _text

    from schemas.component import ComponentCreate
    from schemas.partij import PartijCreate
    from services import component_service, gebruiker_service, partij_service
    from models.models import PartijAard

    # KC-provisioning mocken (geen live IAM): vaste sub.
    async def _kc(**_k):
        return f"kc-{uuid.uuid4()}"

    monkeypatch.setattr(gebruiker_service.keycloak, "maak_keycloak_gebruiker", _kc)

    tid = uuid.UUID(_TID)
    email = f"wt-{uuid.uuid4().hex[:8]}@org.test"

    async def _flow(s):
        ids = []
        try:
            org = await partij_service.maak_aan(s, tid, PartijCreate(aard=PartijAard.organisatie, naam="WT-Org"))
            afd = await partij_service.maak_aan(s, tid, PartijCreate(
                aard=PartijAard.organisatie_eenheid, naam="WT-Afd", organisatie_id=org.id))
            app = await component_service.maak_aan(s, tid, ComponentCreate(componenttype="applicatie", 
                naam="WT-GebrApp", hostingmodel="saas", migratiepad="onbekend",
                complexiteit="midden", prioriteit="midden"))
            ids += [org.id, afd.id, app["id"]]
            lc_voor = (await s.execute(
                _text("SELECT lifecycle_status FROM component_profiel WHERE id=:i"), {"i": str(app["id"])}
            )).scalar_one()

            read, wachtwoord = await gebruiker_service.maak_gebruiker(
                s, tid, naam="Wendy Test", email=email, afdeling_id=afd.id,
                functietitel="Analist", rol="medewerker")
            ids.append(read.persoon_id)

            assert read.naam == "Wendy Test" and read.email == email
            assert wachtwoord and len(wachtwoord) >= 16
            n = (await s.execute(_text(
                "SELECT count(*) FROM gebruiker_persoon WHERE persoon_id=:p"), {"p": str(read.persoon_id)}
            )).scalar_one()
            assert n == 1

            lc_na = (await s.execute(
                _text("SELECT lifecycle_status FROM component_profiel WHERE id=:i"), {"i": str(app["id"])}
            )).scalar_one()
            assert lc_na == lc_voor  # engine onaangeroerd

            # lijst toont de gebruiker met naam
            items, _ = await gebruiker_service.lijst_gebruikers(s, tid, limit=100, verrijk=False)
            assert any(i.persoon_id == read.persoon_id and i.naam == "Wendy Test" for i in items)
        finally:
            # Leaf-first: persoon (→ cascade koppelrij) + app, dán afdeling, dán org —
            # `fk_partij_organisatie`/lidmaatschap is ON DELETE RESTRICT (reversed = persoon,app,afd,org).
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


# ── Live (skip-if-no-DB) — ADR-029 Fase 2b beheeracties (Keycloak gemockt) ─────────
async def _maak_koppel(s, tid, *, sub, naam="Doel Gebruiker", email=None):
    """Maak org+afd+persoon + een gebruiker_persoon-koppel met de gegeven `sub`. Geeft
    (koppel, [element-ids voor leaf-first cleanup]) terug."""
    from models.models import GebruikerPersoon, PartijAard
    from schemas.partij import PartijCreate
    from services import partij_service

    email = email or f"wt-{uuid.uuid4().hex[:8]}@org.test"
    org = await partij_service.maak_aan(s, tid, PartijCreate(aard=PartijAard.organisatie, naam="WT-Org2b"))
    afd = await partij_service.maak_aan(s, tid, PartijCreate(
        aard=PartijAard.organisatie_eenheid, naam="WT-Afd2b", organisatie_id=org.id))
    persoon = await partij_service.maak_aan(s, tid, PartijCreate(
        aard=PartijAard.persoon, naam=naam, email=email, organisatie_id=org.id, afdeling_id=afd.id))
    koppel = GebruikerPersoon(tenant_id=tid, keycloak_sub=sub, persoon_id=persoon.id)
    s.add(koppel)
    await s.commit()
    await s.refresh(koppel)
    return koppel, [org.id, afd.id, persoon.id]


@integratie
def test_reset_wachtwoord_live(monkeypatch):
    """Nieuw eenmalig wachtwoord (≥16) + KC-reset-call + auditrecord ZONDER het wachtwoord."""
    from sqlalchemy import text as _text
    from unittest.mock import AsyncMock as _AM

    from services import gebruiker_service as svc

    reset_mock = _AM()
    monkeypatch.setattr(svc.keycloak, "reset_keycloak_wachtwoord", reset_mock)
    tid = uuid.UUID(_TID)

    async def _flow(s):
        koppel, ids = await _maak_koppel(s, tid, sub="kc-reset")
        try:
            pw = await svc.reset_wachtwoord(s, tid, koppel.id)
            assert pw and len(pw) >= 16
            assert reset_mock.await_args.args[0] == "kc-reset"  # juiste sub
            rij = (await s.execute(_text(
                "SELECT wijziging::text FROM audit_log WHERE entiteit_type='gebruiker_persoon' "
                "AND entiteit_id=:i ORDER BY tijdstip DESC LIMIT 1"), {"i": str(koppel.id)})).scalar_one()
            assert "wachtwoord" in rij and pw not in rij  # feit gelogd, wachtwoord NERGENS
        finally:
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_wijzig_rol_alle_vier_live(monkeypatch):
    """Alle vier rollen toewijsbaar: elke wijziging (≠ huidige) roept de KC-rol-swap aan."""
    from sqlalchemy import text as _text
    from unittest.mock import AsyncMock as _AM

    from services import gebruiker_service as svc

    rol_mock = _AM()
    monkeypatch.setattr(svc.keycloak, "wijzig_keycloak_rol", rol_mock)
    monkeypatch.setattr(svc.keycloak, "lees_keycloak_gebruiker",
                        _AM(return_value={"enabled": True, "rollen": ["viewer"]}))
    tid = uuid.UUID(_TID)

    async def _flow(s):
        koppel, ids = await _maak_koppel(s, tid, sub="kc-rol")
        try:
            for nieuw in ("medewerker", "beheerder", "auditor"):  # elk ≠ huidige 'viewer'
                rol_mock.reset_mock()
                await svc.wijzig_rol(s, tid, koppel.id, nieuw)
                rol_mock.assert_awaited_once_with("kc-rol", nieuw)
        finally:
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_zet_actief_disable_logout_en_enable_live(monkeypatch):
    """Uitschakelen → enabled=false + sessie afkappen (logout); inschakelen → enabled=true, geen logout."""
    from sqlalchemy import text as _text
    from unittest.mock import AsyncMock as _AM

    from services import gebruiker_service as svc

    enabled_mock, logout_mock = _AM(), _AM()
    monkeypatch.setattr(svc.keycloak, "zet_keycloak_enabled", enabled_mock)
    monkeypatch.setattr(svc.keycloak, "logout_keycloak_gebruiker", logout_mock)
    monkeypatch.setattr(svc.keycloak, "lees_keycloak_gebruiker",
                        _AM(return_value={"enabled": True, "rollen": ["medewerker"]}))
    tid = uuid.UUID(_TID)

    async def _flow(s):
        koppel, ids = await _maak_koppel(s, tid, sub="kc-actief")
        try:
            await svc.zet_actief(s, tid, koppel.id, False)
            enabled_mock.assert_awaited_once_with("kc-actief", False)
            logout_mock.assert_awaited_once_with("kc-actief")  # sessie direct afgekapt
            enabled_mock.reset_mock(); logout_mock.reset_mock()
            await svc.zet_actief(s, tid, koppel.id, True)
            enabled_mock.assert_awaited_once_with("kc-actief", True)
            logout_mock.assert_not_awaited()  # geen logout bij inschakelen
        finally:
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_corrigeer_gegevens_live(monkeypatch):
    """Naam/e-mail bijgewerkt op de persoon-partij (+ KC-call); partij-diff geauditeerd."""
    from sqlalchemy import text as _text
    from unittest.mock import AsyncMock as _AM

    from services import gebruiker_service as svc

    werk_mock = _AM()
    monkeypatch.setattr(svc.keycloak, "werk_keycloak_gegevens_bij", werk_mock)
    tid = uuid.UUID(_TID)

    async def _flow(s):
        koppel, ids = await _maak_koppel(s, tid, sub="kc-corr", naam="Oude Naam")
        nieuw_email = f"nw-{uuid.uuid4().hex[:8]}@org.test"
        try:
            read = await svc.corrigeer_gegevens(s, tid, koppel.id, naam="Nieuwe Naam", email=nieuw_email)
            assert read.naam == "Nieuwe Naam" and read.email == nieuw_email
            # Naam/e-mail wijzigen → account WÉL gesynct, met de juiste sub/naam/e-mail.
            werk_mock.assert_awaited_once_with("kc-corr", naam="Nieuwe Naam", email=nieuw_email)
            row = (await s.execute(_text("SELECT naam, email FROM partij WHERE id=:i"),
                                   {"i": str(koppel.persoon_id)})).first()
            assert row.naam == "Nieuwe Naam" and row.email == nieuw_email
            rij = (await s.execute(_text(
                "SELECT wijziging::text FROM audit_log WHERE entiteit_type='partij' "
                "AND entiteit_id=:i ORDER BY tijdstip DESC LIMIT 1"), {"i": str(koppel.persoon_id)})).scalar_one()
            assert "naam" in rij and "email" in rij
        finally:
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_guard_eigen_account_en_eigen_beheerrol_live(monkeypatch):
    """Self-lockout-guards: je eigen account niet uitschakelen, jezelf niet de-beheerrollen."""
    from sqlalchemy import text as _text
    from unittest.mock import AsyncMock as _AM

    from services import gebruiker_service as svc
    from services.errors import RegistratieConflict

    monkeypatch.setattr(svc.keycloak, "lees_keycloak_gebruiker",
                        _AM(return_value={"enabled": True, "rollen": ["beheerder"]}))
    monkeypatch.setattr(svc.keycloak, "zet_keycloak_enabled", _AM())
    monkeypatch.setattr(svc.keycloak, "wijzig_keycloak_rol", _AM())
    tid = uuid.UUID(_TID)

    async def _flow(s):
        # sub == de harness-actor ("test:adr029") → het eigen account.
        koppel, ids = await _maak_koppel(s, tid, sub="test:adr029")
        try:
            with pytest.raises(RegistratieConflict) as e1:
                await svc.zet_actief(s, tid, koppel.id, False)
            assert e1.value.code == "EIGEN_ACCOUNT"
            with pytest.raises(RegistratieConflict) as e2:
                await svc.wijzig_rol(s, tid, koppel.id, "medewerker")
            assert e2.value.code == "EIGEN_BEHEERROL"
        finally:
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_guard_laatste_beheerder_live(monkeypatch):
    """De laatste (actieve) beheerder kan niet worden uitgeschakeld/de-rold."""
    from sqlalchemy import text as _text

    from services import gebruiker_service as svc
    from services.errors import RegistratieConflict

    # Doel = beheerder; alle andere tenant-gebruikers tellen NIET als beheerder.
    async def _lees(sub):
        return {"enabled": True, "rollen": ["beheerder"] if sub == "kc-laatste" else ["medewerker"]}

    monkeypatch.setattr(svc.keycloak, "lees_keycloak_gebruiker", _lees)
    tid = uuid.UUID(_TID)

    async def _flow(s):
        koppel, ids = await _maak_koppel(s, tid, sub="kc-laatste")  # ≠ self
        try:
            with pytest.raises(RegistratieConflict) as e:
                await svc.zet_actief(s, tid, koppel.id, False)
            assert e.value.code == "LAATSTE_BEHEERDER"
        finally:
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_lijst_verrijkt_met_rol_en_status_live(monkeypatch):
    """De lijst verrijkt elke gebruiker met de huidige rol + enabled-status uit Keycloak."""
    from sqlalchemy import text as _text
    from unittest.mock import AsyncMock as _AM

    from services import gebruiker_service as svc

    monkeypatch.setattr(svc.keycloak, "lees_keycloak_gebruiker",
                        _AM(return_value={"enabled": False, "rollen": ["auditor"]}))
    tid = uuid.UUID(_TID)

    async def _flow(s):
        koppel, ids = await _maak_koppel(s, tid, sub="kc-verrijk")
        try:
            items, _ = await svc.lijst_gebruikers(s, tid, limit=100)  # verrijk=True (default)
            mij = next(i for i in items if i.id == koppel.id)
            assert mij.rol == "auditor" and mij.enabled is False
        finally:
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


# ── LI032 — gebruiker bewerken: organisatie/afdeling ──────────────────────────────

def test_correctie_request_accepteert_afdeling_en_read_verrijkt():
    """Schema: `afdeling_id` op de correctie-request; org/afdeling (id + naam) op de read."""
    from schemas.gebruiker import GebruikerCorrectieRequest, GebruikerPersoonRead

    assert "afdeling_id" in GebruikerCorrectieRequest.model_fields
    for veld in ("organisatie_id", "organisatie_naam", "afdeling_id", "afdeling"):
        assert veld in GebruikerPersoonRead.model_fields


@integratie
def test_corrigeer_wijzigt_afdeling_en_read_verrijkt_live(monkeypatch):
    """Afdeling wijzigen binnen dezelfde organisatie: persoon.afdeling_id verandert, organisatie
    blijft; de read (detail + lijst) levert organisatie/afdeling (id + naam)."""
    from sqlalchemy import text as _text
    from unittest.mock import AsyncMock as _AM

    from schemas.partij import PartijCreate
    from services import gebruiker_service as svc, partij_service
    from models.models import PartijAard

    werk_mock = _AM()
    monkeypatch.setattr(svc.keycloak, "werk_keycloak_gegevens_bij", werk_mock)
    tid = uuid.UUID(_TID)
    mail = f"corr-{uuid.uuid4().hex[:8]}@org.test"

    async def _flow(s):
        koppel, ids = await _maak_koppel(s, tid, sub="kc-corr-afd", naam="Doel Gebruiker", email=mail)
        org_id, afd1_id, persoon_id = ids
        afd2 = await partij_service.maak_aan(s, tid, PartijCreate(
            aard=PartijAard.organisatie_eenheid, naam="WT-Afd2b-tweede", organisatie_id=org_id))
        try:
            read = await svc.corrigeer_gegevens(
                s, tid, koppel.id, naam="Doel Gebruiker", email=mail, afdeling_id=afd2.id)
            # LI032 — afdeling-only wissel (naam/e-mail ongewijzigd): het account wordt NIET aangeroepen.
            werk_mock.assert_not_awaited()
            assert read.afdeling_id == afd2.id and read.afdeling == "WT-Afd2b-tweede"
            assert read.organisatie_id == org_id and read.organisatie_naam == "WT-Org2b"
            row = (await s.execute(
                _text("SELECT organisatie_id, afdeling_id FROM partij WHERE id=:i"), {"i": str(persoon_id)}
            )).one()
            assert str(row[0]) == str(org_id) and str(row[1]) == str(afd2.id)  # org onveranderd, afd gewijzigd
            items, _ = await svc.lijst_gebruikers(s, tid, limit=100, verrijk=False)
            it = next(i for i in items if i.persoon_id == persoon_id)
            assert it.organisatie_naam == "WT-Org2b" and it.afdeling == "WT-Afd2b-tweede"
        finally:
            for eid in [persoon_id, afd1_id, afd2.id, org_id]:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_corrigeer_ongeldige_afdeling_live(monkeypatch):
    """Een niet-afdeling als `afdeling_id` (bv. een organisatie-id) → 422 ONGELDIGE_AFDELING."""
    from sqlalchemy import text as _text
    from unittest.mock import AsyncMock as _AM

    from services import gebruiker_service as svc
    from services.errors import OngeldigeRegistratie

    monkeypatch.setattr(svc.keycloak, "werk_keycloak_gegevens_bij", _AM())
    tid = uuid.UUID(_TID)
    mail = f"corr-{uuid.uuid4().hex[:8]}@org.test"

    async def _flow(s):
        koppel, ids = await _maak_koppel(s, tid, sub="kc-corr-ong", email=mail)
        org_id, afd1_id, persoon_id = ids
        try:
            with pytest.raises(OngeldigeRegistratie) as ei:
                await svc.corrigeer_gegevens(
                    s, tid, koppel.id, naam="Doel Gebruiker", email=mail, afdeling_id=org_id)  # org, geen afdeling
            assert ei.value.code == "ONGELDIGE_AFDELING"
        finally:
            for eid in [persoon_id, afd1_id, org_id]:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_corrigeer_org_wissel_geblokkeerd_door_aanspreekpunt_live(monkeypatch):
    """Verplaats geen persoon die nog aanspreekpunt is van een achtergelaten partij → 409
    AANSPREEKPUNT_BLOKKEERT_VERPLAATSING met de partijnaam; GEEN mutatie."""
    from sqlalchemy import text as _text
    from unittest.mock import AsyncMock as _AM

    from schemas.partij import PartijCreate, PartijUpdate
    from services import gebruiker_service as svc, partij_service
    from services.errors import RegistratieConflict
    from models.models import PartijAard

    monkeypatch.setattr(svc.keycloak, "werk_keycloak_gegevens_bij", _AM())
    tid = uuid.UUID(_TID)
    mail = f"blok-{uuid.uuid4().hex[:8]}@org.test"

    async def _flow(s):
        koppel, ids = await _maak_koppel(s, tid, sub="kc-corr-blok", email=mail)
        org1_id, afd1_id, persoon_id = ids
        # Maak de persoon aanspreekpunt van zijn eigen organisatie (org1).
        await partij_service.werk_bij(s, tid, org1_id, PartijUpdate(contactpersoon_id=persoon_id))
        # Tweede organisatie + afdeling om naartoe te verplaatsen.
        org2 = await partij_service.maak_aan(s, tid, PartijCreate(aard=PartijAard.organisatie, naam="WT-Org2b-ander"))
        afd2 = await partij_service.maak_aan(s, tid, PartijCreate(
            aard=PartijAard.organisatie_eenheid, naam="WT-Afd2b-ander", organisatie_id=org2.id))
        try:
            with pytest.raises(RegistratieConflict) as ei:
                await svc.corrigeer_gegevens(
                    s, tid, koppel.id, naam="Doel Gebruiker", email=mail, afdeling_id=afd2.id)
            assert ei.value.code == "AANSPREEKPUNT_BLOKKEERT_VERPLAATSING"
            assert "WT-Org2b-ander" not in ei.value.bericht  # het is de ACHTERGELATEN partij (org1)
            # Geen mutatie: persoon nog bij org1/afd1.
            row = (await s.execute(
                _text("SELECT organisatie_id, afdeling_id FROM partij WHERE id=:i"), {"i": str(persoon_id)}
            )).one()
            assert str(row[0]) == str(org1_id) and str(row[1]) == str(afd1_id)
        finally:
            # persoon eerst (nullt org1.contactpersoon_id via SET NULL + geeft afd's vrij), dan afd's, dan orgs.
            for eid in [persoon_id, afd1_id, afd2.id, org1_id, org2.id]:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_corrigeer_afdeling_only_overleeft_account_storing_live(monkeypatch):
    """LI032 — bij een afdeling-only wissel wordt het account niet aangeroepen; zelfs als de
    account-sync ZOU falen, blijft de afdelingswijziging behouden (geen rollback van interne data)."""
    from sqlalchemy import text as _text
    from unittest.mock import AsyncMock as _AM

    from schemas.partij import PartijCreate
    from services import gebruiker_service as svc, partij_service
    from models.models import PartijAard

    # Account-sync gooit ALTIJD — mag nooit worden aangeroepen bij een afdeling-only edit.
    def _ontplof(*_a, **_k):
        raise svc.keycloak.KeycloakProvisioningFout("KC down", 503)

    werk_mock = _AM(side_effect=_ontplof)
    monkeypatch.setattr(svc.keycloak, "werk_keycloak_gegevens_bij", werk_mock)
    tid = uuid.UUID(_TID)
    mail = f"corr-{uuid.uuid4().hex[:8]}@org.test"

    async def _flow(s):
        koppel, ids = await _maak_koppel(s, tid, sub="kc-corr-storing", naam="Doel Gebruiker", email=mail)
        org_id, afd1_id, persoon_id = ids
        afd2 = await partij_service.maak_aan(s, tid, PartijCreate(
            aard=PartijAard.organisatie_eenheid, naam="WT-Afd2b-storing", organisatie_id=org_id))
        try:
            read = await svc.corrigeer_gegevens(
                s, tid, koppel.id, naam="Doel Gebruiker", email=mail, afdeling_id=afd2.id)
            werk_mock.assert_not_awaited()  # account niet geraakt → storing niet relevant
            assert read.afdeling_id == afd2.id and read.afdeling == "WT-Afd2b-storing"
            # Wijziging daadwerkelijk gepersisteerd (niet teruggerold).
            row = (await s.execute(
                _text("SELECT afdeling_id FROM partij WHERE id=:i"), {"i": str(persoon_id)}
            )).one()
            assert str(row[0]) == str(afd2.id)
        finally:
            for eid in [persoon_id, afd1_id, afd2.id, org_id]:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))
