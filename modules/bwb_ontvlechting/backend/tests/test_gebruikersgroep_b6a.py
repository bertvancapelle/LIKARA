"""Tests — UX-B6-a: gebruikersgroep-organisatie als verwijzing naar een organisatie-partij.

Offline: `valideer_organisatie` weigert aard ≠ organisatie / onbekend, accepteert organisatie.
Live (skip-if-no-DB): organisatie zetten levert de naam in read; aard ≠ organisatie ⇒ 422;
ON DELETE SET NULL bij verwijderen van de organisatie-partij; de architectuur-projectie toont
de organisatie-naam als gebruikersgroep-naam (B2-afleiding blijft kloppen).
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.core.audit  # noqa: F401
import app.core.database  # noqa: F401
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline: aard-validatie ──────────────────────────────────────────────────────
def _mock_session_met_aard(aard):
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncMock(spec=AsyncSession)
    res = MagicMock()
    res.scalar_one_or_none.return_value = aard
    session.execute.return_value = res
    return session


def test_valideer_organisatie_accepteert_organisatie():
    from models.models import PartijAard
    from services import partij_service

    session = _mock_session_met_aard(PartijAard.organisatie)
    asyncio.run(partij_service.valideer_organisatie(session, uuid.uuid4(), uuid.uuid4()))  # geen exception


def test_valideer_organisatie_weigert_andere_aard():
    from models.models import PartijAard
    from services import partij_service
    from services.errors import OngeldigeRegistratie

    session = _mock_session_met_aard(PartijAard.externe_partij)
    with pytest.raises(OngeldigeRegistratie):
        asyncio.run(partij_service.valideer_organisatie(session, uuid.uuid4(), uuid.uuid4()))


def test_valideer_organisatie_weigert_onbekend():
    from services import partij_service
    from services.errors import OngeldigeRegistratie

    session = _mock_session_met_aard(None)
    with pytest.raises(OngeldigeRegistratie):
        asyncio.run(partij_service.valideer_organisatie(session, uuid.uuid4(), uuid.uuid4()))


# ── Live (skip-if-no-DB) ───────────────────────────────────────────────────────
def _db_bereikbaar() -> bool:
    import asyncio as _a

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
        return _a.run(_probe())
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


async def _maak_org(s, tid, naam, aard=None):
    from models.models import Element, ElementType, Partij, PartijAard, PartijScope

    elem = Element(tenant_id=tid, element_type=ElementType.partij)
    s.add(elem); await s.flush()
    _aard = aard or PartijAard.organisatie
    _scope = PartijScope.extern if _aard in (PartijAard.organisatie, PartijAard.externe_partij) else None
    s.add(Partij(id=elem.id, tenant_id=tid, aard=_aard, naam=naam, scope=_scope))
    await s.flush()
    return elem.id


async def _maak_app(s, tid):
    from models.models import HostingModel, Migratiepad, NiveauEnum
    from services import component_service

    # LI059 facade-purge: de creatie-kern woont in component_service (component = enige bron).
    comp = await component_service.maak_applicatie_component(
        s, tid, naam="WT-B6a-App", beschrijving=None, hostingmodel=HostingModel.on_premise,
        eigenaar_organisatie_id=None,
        migratiepad=Migratiepad.onbekend, complexiteit=NiveauEnum.midden, prioriteit=NiveauEnum.midden,
    )
    return comp.id


@integratie
def test_organisatie_zetten_lezen_en_restrict_live():
    from sqlalchemy import text as _text
    from sqlalchemy.exc import IntegrityError

    from schemas.gebruikersgroep import GebruikersgroepCreate
    from services import architectuur_service, gebruikersgroep_service as svc
    from services.errors import OngeldigeRegistratie

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            org_id = await _maak_org(s, tid, "WT-B6a-Organisatie")
            app_id = await _maak_app(s, tid)
            await s.commit()
            ids += [org_id, app_id]

            # Happy path: organisatie zetten → read levert de naam.
            groep = await svc.maak_aan(s, tid, GebruikersgroepCreate(applicatie_id=app_id, organisatie_id=org_id))
            gid = groep["id"]; ids.append(gid)
            assert groep["organisatie_id"] == org_id
            assert groep["organisatie_naam"] == "WT-B6a-Organisatie"

            # Architectuur-projectie: gebruikersgroep-naam = organisatie-naam (B2-afleiding).
            arch, _ = await architectuur_service.lijst(s, _TID, limit=100, type="gebruikersgroep")
            mijn = next((e for e in arch if e["id"] == gid), None)
            assert mijn is not None and mijn["naam"] == "WT-B6a-Organisatie"

            # aard ≠ organisatie ⇒ 422 (ONGELDIGE_ORGANISATIE).
            from models.models import PartijAard
            ext_id = await _maak_org(s, tid, "WT-B6a-Extern", aard=PartijAard.externe_partij)
            await s.commit(); ids.append(ext_id)
            try:
                await svc.maak_aan(s, tid, GebruikersgroepCreate(applicatie_id=app_id, organisatie_id=ext_id))
                raise AssertionError("verwachtte OngeldigeRegistratie")
            except OngeldigeRegistratie as e:
                assert e.code == "ONGELDIGE_ORGANISATIE"
            await s.rollback()

            # ADR-038 — ON DELETE RESTRICT: een organisatie met groepen kan niet stil verdwijnen.
            # (Verwijderen van de org cascadeert het grove feit, dat door de groep wordt geblokkeerd.)
            try:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(org_id)})
                await s.flush()
                raise AssertionError("verwachtte IntegrityError (RESTRICT)")
            except IntegrityError:
                await s.rollback()
            na = await svc.lees_detail(s, tid, gid)
            assert na["organisatie_id"] == org_id  # organisatie ongewijzigd
            return True
        finally:
            # RESTRICT-volgorde: groep(en) eerst, dan afdeling/app/organisatie.
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_run_rls(_flow)) is True


@integratie
def test_werk_bij_organisatie_null_geweigerd_live():
    """ADR-038 — een groep-organisatie mag niet op null worden gezet (organisatie verplicht)."""
    from sqlalchemy import text as _text

    from schemas.gebruikersgroep import GebruikersgroepCreate, GebruikersgroepUpdate
    from services import gebruikersgroep_service as svc
    from services.errors import OngeldigeRegistratie

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            org_id = await _maak_org(s, tid, "WT-038-Org")
            app_id = await _maak_app(s, tid)
            await s.commit(); ids += [org_id, app_id]
            groep = await svc.maak_aan(s, tid, GebruikersgroepCreate(applicatie_id=app_id, organisatie_id=org_id))
            gid = groep["id"]; ids.append(gid)
            try:
                await svc.werk_bij(s, tid, gid, GebruikersgroepUpdate(organisatie_id=None))
                raise AssertionError("verwachtte OngeldigeRegistratie")
            except OngeldigeRegistratie as e:
                assert e.code == "ORGANISATIE_VERPLICHT"
            await s.rollback()
            return True
        finally:
            # RESTRICT-volgorde: groep vóór app/organisatie.
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_run_rls(_flow)) is True
