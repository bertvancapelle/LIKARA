"""Tests — ADR-038 intern/extern-kenmerk op een partij (Slice 1a, additief).

Offline: `_effectieve_scope`/`_valideer_scope` (aard-bewust), schema-validatie (create), read-veld.
Live (skip-if-no-DB): default extern op organisatie, forced extern op externe_partij, NULL voor
afdeling/persoon, werk_bij-toggle + 422-paden, de twee CHECK-backstops, en audit-capture van scope.
Elke live-test ruimt zijn eigen rijen op (element-CASCADE) — geen wees-elementen, geen count-drift.
"""
import asyncio
import uuid

import pytest
from sqlalchemy import text

import app.core.audit  # noqa: F401  (registreert de audit-event-listeners)
import app.core.database  # noqa: F401  (registreert de RLS-set_config-hook)
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_TID = "11111111-1111-1111-1111-111111111111"


# ── Offline: aard-bewuste scope-logica ───────────────────────────────────────────

def test_effectieve_scope_aard_bewust():
    from models.models import PartijAard, PartijScope
    from services import partij_service as svc

    O, E, P, A = (PartijAard.organisatie, PartijAard.externe_partij,
                  PartijAard.persoon, PartijAard.organisatie_eenheid)
    # organisatie: leeg → default extern; expliciet behouden.
    assert svc._effectieve_scope(O, None) == PartijScope.extern
    assert svc._effectieve_scope(O, PartijScope.intern) == PartijScope.intern
    assert svc._effectieve_scope(O, PartijScope.extern) == PartijScope.extern
    # externe_partij: altijd extern (ook bij None).
    assert svc._effectieve_scope(E, None) == PartijScope.extern
    assert svc._effectieve_scope(E, PartijScope.intern) == PartijScope.extern
    # afdeling/persoon: geen eigen waarde.
    assert svc._effectieve_scope(P, None) is None
    assert svc._effectieve_scope(A, None) is None


def test_valideer_scope_ok_en_422():
    from models.models import PartijAard, PartijScope
    from services import partij_service as svc
    from services.errors import OngeldigeRegistratie

    O, E, P, A = (PartijAard.organisatie, PartijAard.externe_partij,
                  PartijAard.persoon, PartijAard.organisatie_eenheid)
    # OK-paden.
    svc._valideer_scope(O, PartijScope.intern)
    svc._valideer_scope(O, PartijScope.extern)
    svc._valideer_scope(E, PartijScope.extern)
    svc._valideer_scope(P, None)
    svc._valideer_scope(A, None)
    # 422-paden.
    for aard, scope, code in (
        (O, None, "ONGELDIGE_SCOPE"),
        (E, PartijScope.intern, "EXTERNE_PARTIJ_ALTIJD_EXTERN"),
        (E, None, "EXTERNE_PARTIJ_ALTIJD_EXTERN"),
        (P, PartijScope.intern, "SCOPE_ALLEEN_ORGANISATIE"),
        (A, PartijScope.extern, "SCOPE_ALLEEN_ORGANISATIE"),
    ):
        with pytest.raises(OngeldigeRegistratie) as exc:
            svc._valideer_scope(aard, scope)
        assert exc.value.code == code


def test_schema_create_scope_consistentie():
    from pydantic import ValidationError

    from models.models import PartijAard, PartijScope
    from schemas.partij import PartijCreate

    # organisatie zonder scope → geldig (service vult default extern).
    assert PartijCreate(aard=PartijAard.organisatie, naam="X").scope is None
    # organisatie met intern → geldig.
    assert PartijCreate(aard=PartijAard.organisatie, naam="X", scope=PartijScope.intern).scope == PartijScope.intern
    # externe_partij + intern → geweigerd.
    with pytest.raises(ValidationError):
        PartijCreate(aard=PartijAard.externe_partij, naam="X", scope=PartijScope.intern)
    # persoon + scope → geweigerd (draagt geen kenmerk).
    with pytest.raises(ValidationError):
        PartijCreate(aard=PartijAard.persoon, naam="X", organisatie_id=uuid.uuid4(), scope=PartijScope.extern)
    # persoon zonder scope onder een organisatie → geldig.
    ok = PartijCreate(aard=PartijAard.persoon, naam="X", organisatie_id=uuid.uuid4())
    assert ok.scope is None


def test_read_heeft_scope_veld():
    from schemas.partij import PartijRead

    assert "scope" in PartijRead.model_fields


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _probe():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                return (await c.execute(text("SELECT to_regclass('partij')"))).scalar() is not None
        except Exception:
            return False
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_probe())
    except Exception:
        return False


live = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar (offline)")


async def _run_rls(fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tok = zet_tenant_context(_TID)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_tenant_context(tok)
        await eng.dispose()


async def _opruimen(s, ids):
    """Verwijder de aangemaakte partijen via het element-supertype (CASCADE) — geen wees-element."""
    from models.models import Element

    from sqlalchemy import delete as _delete
    # Omgekeerde volgorde: kinderen (persoon/afdeling) vóór hun ouder-organisatie — de
    # partij-lidmaatschap-FK's zijn ON DELETE RESTRICT.
    for _id in reversed(ids):
        await s.execute(_delete(Element).where(Element.id == _id, Element.tenant_id == uuid.UUID(_TID)))
    await s.commit()


@live
def test_live_organisatie_default_extern_en_intern():
    from models.models import PartijAard, PartijScope
    from schemas.partij import PartijCreate
    from services import partij_service as svc

    async def _flow(s):
        ids = []
        try:
            zonder = await svc.maak_aan(s, _TID, PartijCreate(aard=PartijAard.organisatie, naam="WT-Scope-Default"))
            ids.append(zonder.id)
            assert zonder.scope == PartijScope.extern  # default
            met = await svc.maak_aan(s, _TID, PartijCreate(
                aard=PartijAard.organisatie, naam="WT-Scope-Intern", scope=PartijScope.intern))
            ids.append(met.id)
            assert met.scope == PartijScope.intern
        finally:
            await _opruimen(s, ids)

    asyncio.run(_run_rls(_flow))


@live
def test_live_externe_partij_altijd_extern():
    from models.models import PartijAard, PartijScope
    from schemas.partij import PartijCreate
    from services import partij_service as svc

    async def _flow(s):
        ids = []
        try:
            ext = await svc.maak_aan(s, _TID, PartijCreate(aard=PartijAard.externe_partij, naam="WT-Scope-Ext"))
            ids.append(ext.id)
            assert ext.scope == PartijScope.extern  # geforceerd, ook zonder invoer
        finally:
            await _opruimen(s, ids)

    asyncio.run(_run_rls(_flow))


@live
def test_live_afdeling_en_persoon_scope_null():
    from models.models import PartijAard
    from schemas.partij import PartijCreate
    from services import partij_service as svc

    async def _flow(s):
        ids = []
        try:
            org = await svc.maak_aan(s, _TID, PartijCreate(aard=PartijAard.organisatie, naam="WT-Scope-Org"))
            ids.append(org.id)
            afd = await svc.maak_aan(s, _TID, PartijCreate(
                aard=PartijAard.organisatie_eenheid, naam="WT-Scope-Afd", organisatie_id=org.id))
            ids.append(afd.id)
            assert afd.scope is None  # afdeling draagt geen eigen kenmerk (leidt af)
            per = await svc.maak_aan(s, _TID, PartijCreate(
                aard=PartijAard.persoon, naam="WT-Scope-Persoon", organisatie_id=org.id, afdeling_id=afd.id))
            ids.append(per.id)
            assert per.scope is None
        finally:
            await _opruimen(s, ids)

    asyncio.run(_run_rls(_flow))


@live
def test_live_werk_bij_toggle_en_422():
    from models.models import PartijAard, PartijScope
    from schemas.partij import PartijCreate, PartijUpdate
    from services import partij_service as svc
    from services.errors import OngeldigeRegistratie

    async def _flow(s):
        ids = []
        try:
            org = await svc.maak_aan(s, _TID, PartijCreate(aard=PartijAard.organisatie, naam="WT-Scope-Toggle"))
            ids.append(org.id)
            bij = await svc.werk_bij(s, _TID, org.id, PartijUpdate(scope=PartijScope.intern))
            assert bij.scope == PartijScope.intern
            bij2 = await svc.werk_bij(s, _TID, org.id, PartijUpdate(scope=PartijScope.extern))
            assert bij2.scope == PartijScope.extern
            # externe_partij scope wijzigen naar intern → 422.
            ext = await svc.maak_aan(s, _TID, PartijCreate(aard=PartijAard.externe_partij, naam="WT-Scope-ExtToggle"))
            ids.append(ext.id)
            try:
                await svc.werk_bij(s, _TID, ext.id, PartijUpdate(scope=PartijScope.intern))
                raise AssertionError("verwachtte OngeldigeRegistratie")
            except OngeldigeRegistratie as e:
                assert e.code == "EXTERNE_PARTIJ_ALTIJD_EXTERN"
            await s.rollback()
        finally:
            await _opruimen(s, ids)

    asyncio.run(_run_rls(_flow))


@live
def test_live_check_backstops():
    """De CHECK-constraints vangen een directe (service-omzeilende) schending af."""
    from sqlalchemy.exc import IntegrityError

    from models.models import Element, ElementType, Partij, PartijAard, PartijScope

    async def _org_zonder_scope(s):
        elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.partij)
        s.add(elem); await s.flush()
        s.add(Partij(id=elem.id, tenant_id=uuid.UUID(_TID), aard=PartijAard.organisatie, naam="WT-CK-1", scope=None))
        await s.flush()

    async def _externe_intern(s):
        elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.partij)
        s.add(elem); await s.flush()
        s.add(Partij(id=elem.id, tenant_id=uuid.UUID(_TID), aard=PartijAard.externe_partij,
                     naam="WT-CK-2", scope=PartijScope.intern))
        await s.flush()

    async def _flow(s):
        for fn, ck in ((_org_zonder_scope, "ck_partij_scope_aanwezig"),
                       (_externe_intern, "ck_partij_externe_partij_extern")):
            try:
                await fn(s)
                raise AssertionError(f"verwachtte IntegrityError ({ck})")
            except IntegrityError as e:
                assert ck in str(e.orig)
            await s.rollback()

    asyncio.run(_run_rls(_flow))


@live
def test_live_audit_bevat_scope():
    """ADR-006/038 — een scope-wijziging op een organisatie belandt in het audit-spoor (partij)."""
    from sqlalchemy import select

    from models.models import AuditLog, PartijAard, PartijScope
    from schemas.partij import PartijCreate, PartijUpdate
    from services import partij_service as svc

    async def _flow(s):
        ids = []
        try:
            org = await svc.maak_aan(s, _TID, PartijCreate(aard=PartijAard.organisatie, naam="WT-Scope-Audit"))
            ids.append(org.id)
            await svc.werk_bij(s, _TID, org.id, PartijUpdate(scope=PartijScope.intern))
            rijen = (await s.execute(
                select(AuditLog.wijziging).where(
                    AuditLog.entiteit_type == "partij", AuditLog.entiteit_id == org.id,
                    AuditLog.tenant_id == uuid.UUID(_TID),
                )
            )).scalars().all()
            # de update-diff bevat het scope-veld (extern → intern).
            assert any("scope" in (w or {}) for w in rijen)
        finally:
            await _opruimen(s, ids)

    asyncio.run(_run_rls(_flow))
