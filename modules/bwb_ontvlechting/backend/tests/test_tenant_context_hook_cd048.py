"""Tests — transactie-lokale tenant-context via after_begin-hook (CD048).

Unit-tests (offline): de hook-logica (skip non-RLS, fail-fast, set_config-lokaal) + de
ContextVar-helpers. Integratie-tests (live cd_app-DB, skip indien onbereikbaar): het
CD047-mechanisme zelf — post-commit refresh op een verse verbinding, geen context-lek,
en cross-tenant-isolatie onder hergebruik van dezelfde poolverbinding.
"""
import asyncio
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Importeren registreert de globale after_begin-hook op Session.
from app.core.database import _pas_tenant_context_toe  # noqa: F401
from app.core import tenant_context as tc

_TENANT_A = "11111111-1111-1111-1111-111111111111"
_TENANT_B = "22222222-2222-2222-2222-222222222222"
_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"


# ── Unit: hook-logica + ContextVar-helpers ──────────────────────────────────────

def _fake_session(rls: bool):
    s = MagicMock()
    s.info = {"rls": True} if rls else {}
    return s


def test_contextvar_zet_reset_huidige():
    assert tc.huidige_tenant_id() is None
    token = tc.zet_tenant_context("abc-123")
    try:
        assert tc.huidige_tenant_id() == "abc-123"
    finally:
        tc.reset_tenant_context(token)
    assert tc.huidige_tenant_id() is None


def test_hook_slaat_niet_rls_sessie_over():
    conn = MagicMock()
    _pas_tenant_context_toe(_fake_session(False), MagicMock(), conn)
    conn.execute.assert_not_called()


def test_hook_failfast_op_rls_sessie_zonder_context():
    conn = MagicMock()
    assert tc.huidige_tenant_id() is None
    with pytest.raises(RuntimeError):
        _pas_tenant_context_toe(_fake_session(True), MagicMock(), conn)
    conn.execute.assert_not_called()


def test_hook_zet_set_config_transactie_lokaal_met_tid():
    conn = MagicMock()
    token = tc.zet_tenant_context(_TENANT_A)
    try:
        _pas_tenant_context_toe(_fake_session(True), MagicMock(), conn)
    finally:
        tc.reset_tenant_context(token)
    assert conn.execute.call_count == 1
    args, _ = conn.execute.call_args
    sql = str(args[0])
    assert "set_config('app.tenant_id'" in sql and "true" in sql  # is_local=true
    assert args[1] == {"tid": _TENANT_A}


# ── Integratie (live cd_app) ────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    async def _check():
        eng = create_async_engine(_CD_APP_URL)
        try:
            async with eng.connect() as c:
                await c.execute(text("SELECT 1"))
            return True
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


_DB = _db_bereikbaar()
integratie = pytest.mark.skipif(not _DB, reason="cd_app-DB niet bereikbaar (offline run)")


def _smf(**engine_kwargs):
    eng = create_async_engine(_CD_APP_URL, **engine_kwargs)
    return eng, async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)


async def _verwijder(smf, naam):
    token = tc.zet_tenant_context(_TENANT_A)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            await s.execute(text("DELETE FROM leverancier WHERE naam = :n"), {"n": naam})
            await s.commit()
    finally:
        tc.reset_tenant_context(token)


@integratie
def test_post_commit_refresh_op_verse_verbinding_slaagt():
    """NullPool ⇒ de refresh ná commit treft gegarandeerd een VERSE verbinding —
    exact het CD047-scenario. De hook herstelt de context per transactie ⇒ slaagt."""
    from models.models import Leverancier

    eng, smf = _smf(poolclass=NullPool)
    naam = f"CD048-checkout-{uuid.uuid4().hex[:8]}"

    async def _run():
        token = tc.zet_tenant_context(_TENANT_A)
        try:
            async with smf() as s:
                s.sync_session.info["rls"] = True
                obj = Leverancier(tenant_id=uuid.UUID(_TENANT_A), naam=naam)
                s.add(obj)
                await s.commit()      # verbinding terug naar (Null)pool
                await s.refresh(obj)  # VERSE verbinding → hook → SELECT slaagt
                return obj.id
        finally:
            tc.reset_tenant_context(token)

    try:
        new_id = asyncio.run(_run())
        assert new_id is not None
    finally:
        asyncio.run(_verwijder(smf, naam))
        asyncio.run(eng.dispose())


@integratie
def test_context_lekt_niet_naar_volgende_checkout():
    """pool_size=1 ⇒ dezelfde fysieke verbinding wordt hergebruikt. Na een RLS-transactie
    (is_local=true) is `app.tenant_id` in een vólgende, niet-RLS transactie leeg."""
    eng, smf = _smf(pool_size=1, max_overflow=0)

    async def _run():
        token = tc.zet_tenant_context(_TENANT_A)
        try:
            async with smf() as s:
                s.sync_session.info["rls"] = True
                await s.execute(text("SELECT 1"))
                await s.commit()
        finally:
            tc.reset_tenant_context(token)
        # Volgende checkout (zelfde verbinding), GEEN rls-marker, GEEN context:
        async with smf() as s2:
            return (await s2.execute(text("SELECT current_setting('app.tenant_id', true)"))).scalar()

    try:
        waarde = asyncio.run(_run())
        assert waarde in (None, "")  # transactie-lokaal: geen lek
    finally:
        asyncio.run(eng.dispose())


@integratie
def test_wisseltest_tenants_zien_alleen_eigen_rijen():
    """Insert als tenant A; daarna A→B→A op dezelfde pool (size 1). Elke transactie krijgt
    via de hook uitsluitend de eigen context ⇒ B ziet A's rij niet, A wel."""
    from models.models import Leverancier

    eng, smf = _smf(pool_size=1, max_overflow=0)
    naam = f"CD048-wissel-{uuid.uuid4().hex[:8]}"

    async def _met(tenant, fn):
        # Eén event loop voor het hele scenario: de pool_size=1-verbinding wordt binnen
        # dezelfde loop hergebruikt (asyncpg-verbindingen zijn loop-gebonden).
        token = tc.zet_tenant_context(tenant)
        try:
            async with smf() as s:
                s.sync_session.info["rls"] = True
                return await fn(s)
        finally:
            tc.reset_tenant_context(token)

    async def _scenario():
        async def _insert(s):
            s.add(Leverancier(tenant_id=uuid.UUID(_TENANT_A), naam=naam))
            await s.commit()

        async def _count(s):
            return (
                await s.execute(
                    select(func.count()).select_from(Leverancier).where(Leverancier.naam == naam)
                )
            ).scalar()

        async def _delete(s):
            await s.execute(text("DELETE FROM leverancier WHERE naam = :n"), {"n": naam})
            await s.commit()

        await _met(_TENANT_A, _insert)
        n_b = await _met(_TENANT_B, _count)   # B ziet A's rij niet
        n_a = await _met(_TENANT_A, _count)   # A wel
        await _met(_TENANT_A, _delete)        # opruimen
        return n_b, n_a

    try:
        n_b, n_a = asyncio.run(_scenario())
        assert n_b == 0
        assert n_a == 1
    finally:
        asyncio.run(eng.dispose())
