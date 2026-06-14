"""Tenant context middleware.

Zet de PostgreSQL session-variabele `app.tenant_id` zodat Row Level
Security alle queries filtert op de geauthenticeerde tenant.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import (
    _markeer_rls,
    async_session_factory,
    platform_session_factory,
)
from app.core.tenant_context import (
    reset_audit_context,
    reset_tenant_context,
    zet_audit_context,
    zet_tenant_context,
)
from app.middleware.auth import (
    AuthenticatedUser,
    PlatformUser,
    get_current_platform_user,
    get_current_user,
)


async def get_tenant_session(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AsyncSession:
    """Yield a DB session scoped to the authenticated user's tenant.

    De tenant-id gaat in een request-scoped ContextVar; de `after_begin`-hook
    (app.core.database) zet `app.tenant_id` per transactie transactie-lokaal (CD048).
    Geen eenmalige sessie-`set_config` meer — die overleefde de mid-request
    commit/connection-checkout niet (CD047). ADR-006: de actor (Keycloak-`sub` +
    e-mail) + één correlatie-id gaan mee in de ContextVar voor het audit-spoor.
    """
    token = zet_tenant_context(user.tenant_id)
    audit_tokens = zet_audit_context(user.sub, user.email)
    try:
        async with async_session_factory() as session:
            _markeer_rls(session)
            try:
                yield session
            finally:
                await session.close()
    finally:
        reset_audit_context(audit_tokens)
        reset_tenant_context(token)


async def get_platform_session(
    user: PlatformUser = Depends(get_current_platform_user),
):
    """Platform-sessie op cd_platform (ADR-012) — voor platform-endpoints
    (tenant-provisioning, platforminstellingen).

    cd_platform is non-superuser, heeft GEEN RLS-/tenant-context en GEEN toegang
    tot tenant-tabellen; cd_admin komt hier NIET aan te pas (OP-11). Geen
    tenant-scoped werk — dat loopt via `get_tenant_session` onder RLS. ADR-006: de
    platform-actor (Keycloak-`sub`) gaat mee voor het `platform_audit_log`-spoor.
    """
    audit_tokens = zet_audit_context(user.sub, user.email)
    try:
        async with platform_session_factory() as session:
            yield session
    finally:
        reset_audit_context(audit_tokens)
