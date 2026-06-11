import uuid
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tenant_context import (
    huidige_tenant_id,
    reset_tenant_context,
    zet_tenant_context,
)

# pool_pre_ping (CD048): stale verbindingen na een herstart/recreate worden stilzwijgend
# ververst i.p.v. dat ze requests laten falen (koude-pool-hardening).
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Platform-engine op cd_platform (ADR-012) — voor platform-endpoints. Non-superuser,
# géén RLS-/tenant-context, géén toegang tot tenant-tabellen. cd_admin komt NIET
# meer in de app-laag voor (OP-11).
platform_engine = create_async_engine(
    settings.platform_database_url, echo=False, pool_pre_ping=True
)
platform_session_factory = async_sessionmaker(
    platform_engine, class_=AsyncSession, expire_on_commit=False
)


@event.listens_for(Session, "after_begin")
def _pas_tenant_context_toe(session, transaction, connection):
    """Zet `app.tenant_id` transactie-lokaal bij elke transactie van een RLS-sessie (CD048).

    Alleen sessies die expliciet als RLS-scoped gemarkeerd zijn (`session.info['rls']`)
    krijgen tenant-context — platform-/init-sessies (cd_platform/cd_admin) blijven
    ongemoeid. `is_local=true` ⇒ context geldt alleen voor deze transactie en lekt niet
    naar de volgende pool-checkout. Ontbreekt de tenant-context op een RLS-sessie ⇒
    fail-fast (expliciete fout i.p.v. een cryptische `''::uuid` verderop).
    """
    if not session.info.get("rls"):
        return
    tid = huidige_tenant_id()
    if tid is None:
        raise RuntimeError(
            "RLS-sessie zonder tenant-context: app.tenant_id-ContextVar ontbreekt "
            "(tenant-context niet gezet voor gebruik van de sessie)."
        )
    connection.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tid})


def _markeer_rls(session: AsyncSession) -> None:
    """Markeer een AsyncSession als RLS-scoped zodat de after_begin-hook context zet."""
    session.sync_session.info["rls"] = True


async def get_session(tenant_id: str):
    """Yield een RLS-sessie; tenant-context wordt per transactie door de hook gezet."""
    token = zet_tenant_context(tenant_id)
    try:
        async with async_session_factory() as session:
            _markeer_rls(session)
            yield session
    finally:
        reset_tenant_context(token)


@asynccontextmanager
async def get_worker_session(tenant_id: uuid.UUID):
    """AsyncSession met RLS-context voor achtergrond-workers/seed.

    Verse sessie per event; de tenant-context staat in de ContextVar en wordt per
    transactie (transactie-lokaal) door de after_begin-hook toegepast — geen lek tussen
    tenants.
    """
    token = zet_tenant_context(tenant_id)
    try:
        async with async_session_factory() as session:
            _markeer_rls(session)
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
    finally:
        reset_tenant_context(token)


@asynccontextmanager
async def get_platform_db_session():
    """AsyncSession zonder RLS-context — alleen voor platform-brede queries."""
    async with async_session_factory() as session:
        yield session
