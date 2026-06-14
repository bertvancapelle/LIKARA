"""ADR-006 Fase B — actor + correlatie in de request-context (offline)."""
import asyncio

from app.core import tenant_context as tc


def test_actor_en_correlatie_zet_en_reset():
    assert tc.huidige_actor() == (None, None)
    assert tc.huidige_correlatie_id() is None
    tokens = tc.zet_audit_context("u-42", "u42@example.test", "corr-1")
    try:
        assert tc.huidige_actor() == ("u-42", "u42@example.test")
        assert tc.huidige_correlatie_id() == "corr-1"
    finally:
        tc.reset_audit_context(tokens)
    assert tc.huidige_actor() == (None, None)
    assert tc.huidige_correlatie_id() is None


def test_correlatie_wordt_gegenereerd_indien_afwezig():
    tokens = tc.zet_audit_context("system:dev_seed")
    try:
        corr = tc.huidige_correlatie_id()
        assert corr is not None and len(corr) == 36  # uuid4
        assert tc.huidige_actor() == ("system:dev_seed", None)
    finally:
        tc.reset_audit_context(tokens)


def test_actor_zichtbaar_over_async_greenlet_bridge():
    """De ContextVar moet binnen dezelfde async-context zichtbaar zijn (zoals de
    tenant-context over de asyncio↔sync-bridge, CD048)."""
    async def _run():
        tokens = tc.zet_audit_context("u-async", "a@b.test")
        try:
            async def _diep():
                return tc.huidige_actor(), tc.huidige_correlatie_id()
            return await _diep()
        finally:
            tc.reset_audit_context(tokens)

    (actor, email), corr = asyncio.run(_run())
    assert actor == "u-async" and email == "a@b.test" and corr is not None
