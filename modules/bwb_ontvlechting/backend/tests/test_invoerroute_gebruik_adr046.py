"""ADR-046 stuk 2 — de invoerroute voor het grove organisatiegebruik.

Dekt: het verwijder-gedrag bij verfijning (409 GEBRUIK_HEEFT_VERFIJNING — de FK is
RESTRICT sinds ADR-038, dus een stille cascade over veldwerk is structureel onmogelijk;
de pre-check maakt er een nette fout van, de DB is de backstop), de afdelingen-verrijking
op `lijst_voor_applicatie` (N+1-vrij, leeg = "afdeling onbekend") en de schema-vorm.

GEEN engine-borging nodig: deze slice voegt alleen een invoerroute/leesverrijking op een
registratie-feit toe; de bestaande import-afwezigheidstest
(`test_engine_niet_geimporteerd_in_organisatiegebruik_service`) blijft de borging.
"""
import asyncio
import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = uuid.UUID("11111111-1111-1111-1111-111111111111")
_LK_APP_URL = os.environ.get(
    "LK_APP_TEST_URL",
    "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara",
)


# ── Offline — verwijder-gedrag ─────────────────────────────────────────────────────

def _haal_result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


def _count_result(n):
    r = MagicMock()
    r.scalar_one.return_value = n
    return r


def test_verwijder_met_verfijning_weigert_409_voor_delete():
    """Een grof feit mét gebruikersgroepen ⇒ 409 GEBRUIK_HEEFT_VERFIJNING mét telling —
    en de delete wordt niet eens geprobeerd (veldwerk verdwijnt nooit stil)."""
    from services import organisatiegebruik_service as svc
    from services.errors import RegistratieConflict

    obj = SimpleNamespace(id=uuid.uuid4(), organisatie_id=uuid.uuid4(), applicatie_id=uuid.uuid4())
    session = AsyncMock()
    session.execute.side_effect = [_haal_result(obj), _count_result(2)]
    with pytest.raises(RegistratieConflict) as e:
        asyncio.run(svc.verwijder(session, _TID, obj.id))
    assert e.value.code == "GEBRUIK_HEEFT_VERFIJNING"
    assert "2 gebruikersgroep" in e.value.bericht
    session.delete.assert_not_called()
    session.commit.assert_not_awaited()


def test_verwijder_zonder_verfijning_slaagt():
    from services import organisatiegebruik_service as svc

    obj = SimpleNamespace(id=uuid.uuid4(), organisatie_id=uuid.uuid4(), applicatie_id=uuid.uuid4())
    session = AsyncMock()
    session.execute.side_effect = [_haal_result(obj), _count_result(0)]
    asyncio.run(svc.verwijder(session, _TID, obj.id))
    session.delete.assert_called_once_with(obj)
    session.commit.assert_awaited_once()


# ── Offline — schema + afdelingen-verrijking ───────────────────────────────────────

def test_read_schema_draagt_afdelingen_default_leeg():
    from schemas.organisatiegebruik import OrganisatiegebruikRead

    assert OrganisatiegebruikRead.model_fields["afdelingen"].default_factory is not None or (
        OrganisatiegebruikRead.model_fields["afdelingen"].default == []
    )


def test_afdelingen_per_gebruik_batcht_en_dedupliceert():
    """Eén batch-query; dubbele afdelingsnamen (twee groepen, zelfde afdeling) één keer."""
    from services import organisatiegebruik_service as svc

    g1, g2 = uuid.uuid4(), uuid.uuid4()
    rows = MagicMock()
    rows.all.return_value = [(g1, "Burgerzaken"), (g1, "Burgerzaken"), (g1, "Publiekszaken"), (g2, "IT")]
    session = AsyncMock()
    session.execute.return_value = rows
    uit = asyncio.run(svc._afdelingen_per_gebruik(session, _TID, [g1, g2]))
    assert uit[g1] == ["Burgerzaken", "Publiekszaken"]
    assert uit[g2] == ["IT"]
    session.execute.assert_awaited_once()  # N+1-vrij


def test_afdelingen_per_gebruik_lege_input_geen_query():
    from services import organisatiegebruik_service as svc

    session = AsyncMock()
    assert asyncio.run(svc._afdelingen_per_gebruik(session, _TID, [])) == {}
    session.execute.assert_not_awaited()


# ── Live (skip-if-no-DB) ───────────────────────────────────────────────────────────

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


@integratie
def test_verwijder_met_en_zonder_verfijning_live():
    """End-to-end op de echte DB: (1) een grof feit mét verfijnende groep weigert met
    409 en de rij BLIJFT staan; (2) na het verwijderen van de groep slaagt de delete.
    Self-contained WT-fixtures, opruiming in finally (leaf→root)."""
    from sqlalchemy import delete as sa_delete
    from sqlalchemy import select, text

    from models.models import Element, Gebruikersgroep, Organisatiegebruik
    from schemas.gebruikersgroep import GebruikersgroepCreate
    from services import gebruikersgroep_service
    from services import organisatiegebruik_service as svc
    from services.errors import RegistratieConflict

    # Harnas-helpers uit de zuster-testmodule (zelfde fixtures, geen duplicatie).
    from test_organisatiegebruik_adr036 import _maak_app, _maak_org

    async def _run(s):
        import app.core.audit  # noqa: F401 — capture-hook actief voor de audit-context
        from app.core.tenant_context import zet_audit_context

        tok = zet_audit_context("system:test_adr046", "test@local")
        ids: list[uuid.UUID] = []
        try:
            org_id = await _maak_org(s, _TID, "WT-ADR046-Org")
            ids.append(org_id)
            app_id = await _maak_app(s, _TID, "WT-ADR046-App")
            ids.append(app_id)
            # Verfijnde groep → het grove feit ontstaat automatisch (ensure).
            groep = await gebruikersgroep_service.maak_aan(
                s, _TID,
                GebruikersgroepCreate(component_id=app_id, organisatie_id=org_id),
            )
            groep_id = groep["id"] if isinstance(groep, dict) else groep.id
            ids.append(groep_id)
            gebruik_id = (
                await s.execute(
                    select(Organisatiegebruik.id).where(
                        Organisatiegebruik.tenant_id == _TID,
                        Organisatiegebruik.organisatie_id == org_id,
                        Organisatiegebruik.applicatie_id == app_id,
                    )
                )
            ).scalar_one()

            # (1) mét verfijning: 409 + de rij blijft.
            with pytest.raises(RegistratieConflict) as e:
                await svc.verwijder(s, _TID, gebruik_id)
            assert e.value.code == "GEBRUIK_HEEFT_VERFIJNING"
            nog = (
                await s.execute(
                    select(Organisatiegebruik.id).where(Organisatiegebruik.id == gebruik_id)
                )
            ).scalar_one_or_none()
            assert nog is not None, "het grove feit mag niet stil verdwijnen"

            # De read levert de afdelingen-sleutel (hier leeg: groep zonder afdeling).
            rijen = await svc.lijst_voor_applicatie(s, _TID, app_id)
            mijn = next(r for r in rijen if r["id"] == gebruik_id)
            assert mijn["heeft_verfijning"] is True
            assert mijn["afdelingen"] == []  # groep zonder afdeling ⇒ "afdeling onbekend"

            # (2) groep bewust weg (element-supertype) → delete slaagt.
            await s.execute(sa_delete(Element).where(Element.tenant_id == _TID, Element.id == groep_id))
            await s.commit()
            ids.remove(groep_id)
            await svc.verwijder(s, _TID, gebruik_id)
            weg = (
                await s.execute(
                    select(Organisatiegebruik.id).where(Organisatiegebruik.id == gebruik_id)
                )
            ).scalar_one_or_none()
            assert weg is None
        finally:
            for eid in reversed(ids):
                await s.execute(text("DELETE FROM element WHERE tenant_id = :t AND id = :i"),
                                {"t": str(_TID), "i": str(eid)})
            await s.commit()
            from app.core.tenant_context import reset_audit_context
            reset_audit_context(tok)

    asyncio.run(_run_rls(_run))
