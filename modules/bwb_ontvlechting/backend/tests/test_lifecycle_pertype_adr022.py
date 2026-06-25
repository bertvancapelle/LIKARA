"""Tests — ADR-022 Fase B: per-type vragenset-scoping + type-bewuste validatie.

De pure beslisregel (lege vragenset → niet-groen) staat in `test_lifecycle.py`.
Hier de live-integratie tegen de geseede lk_app-DB (skip indien onbereikbaar):

- **Per-type scoping**: een `checklistvraag` van een ánder componenttype telt NIET
  mee voor de lifecycle van een applicatie (een volledig gescoorde applicatie blijft
  `migratieklaar` ook al bestaat er een vraag van een ander type).
- **Type-bewuste validatie**: een score op een applicatie die verwijst naar een
  `checklistvraag` van een ander type wordt geweigerd (`NietGevonden`).

De tijdelijke vraag van het andere type wordt als `lk_admin` (fixture-rol)
toegevoegd en opgeruimd — `lk_app` is SELECT-only op `checklistvraag` (Beslissing 8)
en `lk_platform` mag niet DELETE'n.
"""
import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_CD_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_CD_ADMIN_URL = "postgresql+asyncpg://lk_admin:changeme_dev@localhost:5432/likara"


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


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar (offline)")


async def _app_sessie_run(fn):
    """Draai `fn(session)` als lk_app onder RLS-/tenant-context."""
    eng = create_async_engine(_CD_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tok = zet_tenant_context(_TID)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_tenant_context(tok)
        await eng.dispose()


async def _admin_exec(sql: str, params: dict | None = None, *, fetch: bool = False):
    """Voer DDL/DML uit als lk_admin (fixture-rol; buiten het app-rolmodel)."""
    eng = create_async_engine(_CD_ADMIN_URL)
    try:
        async with eng.begin() as c:
            res = await c.execute(text(sql), params or {})
            return res.first() if fetch else None
    finally:
        await eng.dispose()


# ADR-022 W1: checklistvraag is tenant-scoped (tenant_id NOT NULL). De fixture-INSERT
# (als lk_admin) zet expliciet de dev-tenant zodat de RLS-gescopete telling als lk_app
# binnen die tenant de rij ziet.
_INSERT_VRAAG = (
    "INSERT INTO checklistvraag (tenant_id, componenttype, code, categorie_nr, categorie_naam, vraag, prioriteit) "
    "VALUES (:tenant_id, 'database', :code, 1, 'Fase B test', 'Fase B test', 'hoog') RETURNING id"
)


@integratie
def test_pertype_scoping_negeert_ander_type():
    """Een database-type vraag mag de applicatie-lifecycle niet beïnvloeden:
    BRP (89/89 gescoord, geen blokkade) blijft `migratieklaar`, niet
    `in_inventarisatie` (wat zou gebeuren bij een globale telling)."""
    from models.models import LifecycleStatus
    from services import lifecycle_service as ls

    code = f"DB{uuid.uuid4().hex[:6]}"  # <= varchar(10)

    async def _flow():
        await _admin_exec(_INSERT_VRAAG, {"tenant_id": _TID, "code": code}, fetch=True)
        try:
            async def _run(s):
                r = (await s.execute(text("select id from component where naam='BRP'"))).first()
                nieuwe = await ls.herbereken_lifecycle(s, _TID, r[0])
                await s.commit()
                return nieuwe

            nieuwe = await _app_sessie_run(_run)
            assert nieuwe == LifecycleStatus.migratieklaar
        finally:
            await _admin_exec("DELETE FROM checklistvraag WHERE code = :code", {"code": code})

    asyncio.run(_flow())


@integratie
def test_type_bewuste_validatie_weigert_andere_type_vraag():
    """Een score op een applicatie die verwijst naar een database-type vraag wordt
    geweigerd (`NietGevonden`) — de vraag is geen geldige checklistvraag voor dít
    componenttype."""
    from schemas.checklistscore import ChecklistscoreCreate
    from services import checklistscore_service as svc
    from services.errors import NietGevonden

    code = f"DB{uuid.uuid4().hex[:6]}"  # <= varchar(10)

    async def _flow():
        row = await _admin_exec(_INSERT_VRAAG, {"tenant_id": _TID, "code": code}, fetch=True)
        vraag_id = row[0]
        try:
            async def _run(s):
                r = (await s.execute(text("select id from component where naam='DMS'"))).first()
                with pytest.raises(NietGevonden):
                    await svc.maak_aan(
                        s, _TID,
                        ChecklistscoreCreate(component_id=r[0], checklistvraag_id=vraag_id, score="ja"),
                    )
                await s.rollback()

            await _app_sessie_run(_run)
        finally:
            await _admin_exec("DELETE FROM checklistvraag WHERE code = :code", {"code": code})

    asyncio.run(_flow())
