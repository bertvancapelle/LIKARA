"""Tests — ADR-042 slice 1: Proces-element + boom.

Offline: model (element-subtype + composiet self-FK RESTRICT + CHECK), schema,
ArchiMate-typing (business_process in de whitelist; tweede gemarkeerde
behavior-afwijking naast work_package), sorteer-allowlist-sync, RBAC,
audit-allowlist + de regressie-borging dat de proces-laag de engine NIET raakt.
Live (skip-if-no-DB): CRUD, boom + subboom, cycluspreventie (self-parent +
transitieve kring + geldige herhang = verplaatsen), verwijdergedrag (RESTRICT/409 +
kind niet geweesd), zoek + sortering, RLS-isolatie, audit-capture. Live-tests ruimen
hun element-rijen structureel op (element-supertype, leaf→root, in finally).
"""
import asyncio
import uuid

import pytest

import app.core.audit  # noqa: F401 — registreert de audit-capture-hook
import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import (
    reset_audit_context,
    reset_tenant_context,
    zet_audit_context,
    zet_tenant_context,
)

_TID = "11111111-1111-1111-1111-111111111111"
_TID_B = "22222222-2222-2222-2222-222222222222"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline: model + schema ──────────────────────────────────────────────────────

def test_proces_is_element_subtype_met_self_fk():
    from models.models import Proces

    assert Proces.__tablename__ == "proces"
    fks = {
        con.name: con
        for con in Proces.__table__.constraints
        if con.__class__.__name__ == "ForeignKeyConstraint"
    }
    # shared-PK → element(tenant_id,id), cascade.
    assert "fk_proces_element" in fks
    assert fks["fk_proces_element"].ondelete == "CASCADE"
    # composiet self-FK met RESTRICT (subboom niet stilzwijgend wegvagen).
    assert "fk_proces_ouder" in fks
    assert fks["fk_proces_ouder"].ondelete == "RESTRICT"
    kols = Proces.__table__.columns
    assert "naam" in kols and "toelichting" in kols and "ouder_id" in kols


def test_proces_check_geen_self_parent():
    from models.models import Proces

    checks = [
        con.name for con in Proces.__table__.constraints
        if con.__class__.__name__ == "CheckConstraint"
    ]
    assert "ck_proces_geen_self_parent" in checks


def test_proces_schema_validatie():
    from pydantic import ValidationError
    from schemas.proces import ProcesCreate

    ok = ProcesCreate(naam="Vergunningverlening")
    assert ok.ouder_id is None
    ProcesCreate(naam="Aanvraag behandelen", ouder_id=uuid.uuid4())
    with pytest.raises(ValidationError):  # naam verplicht
        ProcesCreate(naam="  ")
    with pytest.raises(ValidationError):  # extra veld verboden
        ProcesCreate(naam="X", onbekend="y")


# ── Offline: ArchiMate-typing (ADR-042 besluit 1) ────────────────────────────────

def test_proces_typing_business_process_behavior():
    """Proces = business_process / business / behavior — de TWEEDE gemarkeerde
    behavior-afwijking op OK-3, naast work_package. (ADR-043 voegde de DERDE toe:
    bedrijfsfunctie — zie test_bedrijfsfunctie_adr043.)"""
    from models.models import ElementType
    from services.archimate_typing import TOEGESTANE_ELEMENTEN, typing_voor

    assert "business_process" in TOEGESTANE_ELEMENTEN
    assert typing_voor(ElementType.proces) == {
        "archimate_element": "business_process", "laag": "business", "aspect": "behavior",
    }
    # Precies DRIE behavior-elementen (work_package + proces + bedrijfsfunctie, ADR-043)
    # — een vierde is opnieuw een bewust besluit.
    from services.archimate_typing import ELEMENT_ARCHIMATE_TYPING

    behavior = {et for et, t in ELEMENT_ARCHIMATE_TYPING.items() if t["aspect"] == "behavior"}
    assert behavior == {ElementType.work_package, ElementType.proces, ElementType.bedrijfsfunctie}


def test_proces_business_function_via_adr043_aanwezig():
    """HISTORIE-UPDATE (gate 1a): ADR-042 besluit 1 parkeerde de bedrijfsfunctie-as
    ("business_function bewust afwezig" — de vorige vorm van deze test); ADR-043 heeft
    die as heropend. De whitelist-entry bestaat nu dus WÉL; de geparkeerde set blijft
    leeg (bedrijfsfunctie is gerealiseerd, niet geparkeerd)."""
    from models.models import ElementType
    from services.archimate_typing import (
        ELEMENT_TYPEN_NOG_NIET_GEREALISEERD,
        TOEGESTANE_ELEMENTEN,
    )

    assert "business_function" in TOEGESTANE_ELEMENTEN
    assert ELEMENT_TYPEN_NOG_NIET_GEREALISEERD == frozenset()
    assert any(e.value == "bedrijfsfunctie" for e in ElementType)


def test_proces_sorteer_allowlist_synchroon():
    """ADR-017 — schema-enum ⟺ service-allowlist ⟺ parsers blijven 1-op-1."""
    from schemas.proces import ProcesSorteerveld
    from services import proces_service as svc

    assert {e.value for e in ProcesSorteerveld} == set(svc._SORTEERBARE_KOLOMMEN)
    assert set(svc._SORTEERBARE_KOLOMMEN) == set(svc._WAARDE_PARSERS)


# ── Offline: RBAC + audit + regressie ────────────────────────────────────────────

def test_proces_in_audit_allowlist():
    from app.core.audit import AUDIT_TENANT_ENTITEITEN

    assert "proces" in AUDIT_TENANT_ENTITEITEN


def test_proces_in_rbac_inhoud_patroon():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    assert heeft_permissie(["medewerker"], Entiteit.PROCES, Actie.AANMAKEN)
    assert heeft_permissie(["beheerder"], Entiteit.PROCES, Actie.VERWIJDEREN)
    assert not heeft_permissie(["viewer"], Entiteit.PROCES, Actie.AANMAKEN)
    assert heeft_permissie(["auditor"], Entiteit.PROCES, Actie.LEZEN)


def test_proces_service_raakt_engine_niet():
    """ADR-042-invariant: score blijft de enige lifecycle-driver — de proces-service
    importeert géén engine-onderdeel."""
    import services.proces_service as ps

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(ps, naam), f"proces_service mag de engine niet importeren: {naam!r}"


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                # De proces-tabel moet bestaan (migratie 0057 toegepast), anders skippen.
                res = (await c.execute(text("SELECT to_regclass('proces')"))).scalar()
            return res is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB/proces-tabel niet bereikbaar")


async def _run_rls(tenant, actor, fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    ttok = zet_tenant_context(tenant)
    atok = zet_audit_context(actor, f"{actor}@test")
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_audit_context(atok)
        reset_tenant_context(ttok)
        await eng.dispose()


async def _ruim(s, ids):
    """Verwijder de proces-element-rijen leaf→root (RESTRICT-veilig), via het supertype."""
    from sqlalchemy import text as _text

    for eid in reversed(ids):  # ids in aanmaakvolgorde root→leaf → omgekeerd opruimen
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    await s.commit()


@integratie
def test_proces_crud_boom_en_subboom_live():
    from schemas.proces import ProcesCreate
    from services import proces_service as svc

    async def _flow(s):
        ids = []
        try:
            a = await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-Test Vergunningverlening"))
            ids.append(a["id"])
            b = await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-Test Aanvraag behandelen", ouder_id=a["id"]))
            ids.append(b["id"])
            c = await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-Test Besluit vastleggen", ouder_id=b["id"]))
            ids.append(c["id"])
            subboom = await svc.subboom(s, _TID, a["id"])
            return a, b, c, subboom
        finally:
            await _ruim(s, ids)

    a, b, c, subboom = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert b["ouder_id"] == a["id"] and c["ouder_id"] == b["id"]
    per_id = {x["id"]: x for x in subboom}
    assert per_id[b["id"]]["niveau"] == 1 and per_id[c["id"]]["niveau"] == 2
    assert per_id[c["id"]]["pad"][-1] == "PR-Test Besluit vastleggen"


@integratie
def test_proces_cycluspreventie_en_verplaatsen_live():
    from schemas.proces import ProcesCreate, ProcesUpdate
    from services import proces_service as svc
    from services.errors import OngeldigeRegistratie

    async def _flow(s):
        ids = []
        try:
            a = await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-Cyc A"))
            ids.append(a["id"])
            b = await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-Cyc B", ouder_id=a["id"]))
            ids.append(b["id"])
            c = await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-Cyc C", ouder_id=b["id"]))
            ids.append(c["id"])
            fouten = {}
            # Self-parent.
            try:
                await svc.werk_bij(s, _TID, a["id"], ProcesUpdate(ouder_id=a["id"]))
            except OngeldigeRegistratie as e:
                fouten["self"] = e.code
            # Transitieve kring: A onder C (C is deelproces-van-deelproces van A).
            try:
                await svc.werk_bij(s, _TID, a["id"], ProcesUpdate(ouder_id=c["id"]))
            except OngeldigeRegistratie as e:
                fouten["kring"] = e.code
            # Geldig verplaatsen: C los van B naar direct onder A (één veldwijziging).
            herhang = await svc.werk_bij(s, _TID, c["id"], ProcesUpdate(ouder_id=a["id"]))
            # En loskoppelen tot top-level (expliciet null).
            los = await svc.werk_bij(s, _TID, c["id"], ProcesUpdate(ouder_id=None))
            return fouten, herhang, los
        finally:
            await _ruim(s, ids)

    fouten, herhang, los = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert fouten == {"self": "CYCLISCHE_HIERARCHIE", "kring": "CYCLISCHE_HIERARCHIE"}
    assert herhang["ouder_id"] is not None  # geldige herhang slaagde
    assert los["ouder_id"] is None          # loskoppelen tot top-level slaagde


@integratie
def test_proces_verwijdergedrag_live():
    from sqlalchemy import text as _text
    from schemas.proces import ProcesCreate
    from services import proces_service as svc
    from services.errors import RegistratieConflict

    async def _flow(s):
        ids = []
        try:
            p = await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-Del Ouder"))
            ids.append(p["id"])
            kind = await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-Del Kind", ouder_id=p["id"]))
            ids.append(kind["id"])
            # Ouder met deelproces → 409, geen wegvagen.
            geweigerd = None
            try:
                await svc.verwijder(s, _TID, p["id"])
            except RegistratieConflict as e:
                geweigerd = e.code
            # Kind bestaat nog én is niet geweesd (ouder_id intact).
            na = (await s.execute(_text(
                "SELECT ouder_id FROM proces WHERE id=:i"), {"i": str(kind["id"])})).scalar()
            # Kind eerst weg, dan ouder → mag.
            await svc.verwijder(s, _TID, kind["id"])
            ids.remove(kind["id"])
            await svc.verwijder(s, _TID, p["id"])
            ids.remove(p["id"])
            return geweigerd, na, p["id"]
        finally:
            await _ruim(s, ids)

    geweigerd, kind_ouder, ouder_id = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert geweigerd == "HEEFT_DEELPROCESSEN"
    assert str(kind_ouder) == str(ouder_id)  # kind niet geweesd door de element-cascade


@integratie
def test_proces_zoek_en_sortering_live():
    """`zoek` (ILIKE op naam) + server-side sortering (v2n, ADR-017)."""
    from schemas.proces import ProcesCreate
    from services import proces_service as svc

    async def _flow(s):
        ids = []
        try:
            a = await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-Zoek Alpha uniek"))
            ids.append(a["id"])
            b = await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-Zoek Beta uniek"))
            ids.append(b["id"])
            gezocht, _ = await svc.lijst(s, _TID, zoek="alpha uniek")
            gesorteerd, _ = await svc.lijst(s, _TID, zoek="PR-Zoek", sort="naam", order="desc")
            return [i["naam"] for i in gezocht], [i["naam"] for i in gesorteerd]
        finally:
            await _ruim(s, ids)

    gezocht, gesorteerd = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert "PR-Zoek Alpha uniek" in gezocht
    assert "PR-Zoek Beta uniek" not in gezocht  # ILIKE filtert op naam
    assert gesorteerd == ["PR-Zoek Beta uniek", "PR-Zoek Alpha uniek"]  # naam desc


@integratie
def test_proces_rls_isolatie_live():
    from sqlalchemy import text as _text
    from schemas.proces import ProcesCreate
    from services import proces_service as svc

    async def _maak(s):
        return (await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-RLS")))["id"]

    async def _zicht(s, pid):
        return (await s.execute(_text("SELECT count(*) FROM proces WHERE id=:i"), {"i": str(pid)})).scalar()

    pid = asyncio.run(_run_rls(_TID, "test:bert", _maak))
    try:
        zicht_b = asyncio.run(_run_rls(_TID_B, "test:bert", lambda s: _zicht(s, pid)))
        zicht_a = asyncio.run(_run_rls(_TID, "test:bert", lambda s: _zicht(s, pid)))
    finally:
        asyncio.run(_run_rls(_TID, "test:bert", lambda s: _ruim(s, [pid])))
    assert zicht_b == 0 and zicht_a == 1


@integratie
def test_proces_audit_en_geen_engine_live():
    from sqlalchemy import text as _text
    from schemas.proces import ProcesCreate
    from services import proces_service as svc

    async def _flow(s):
        ids = []
        try:
            pr = await svc.maak_aan(s, _TID, ProcesCreate(naam="PR-Audit"))
            ids.append(pr["id"])
            audit = (await s.execute(_text(
                "SELECT count(*) FROM audit_log WHERE entiteit_type='proces' AND entiteit_id=:i"),
                {"i": str(pr["id"])})).scalar()
            # Geen engine-state: een proces krijgt geen component_profiel.
            profiel = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": str(pr["id"])})).scalar()
            return audit, profiel
        finally:
            await _ruim(s, ids)

    audit, profiel = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert audit >= 1 and profiel == 0
