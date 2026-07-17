"""Tests — ADR-052 slice 1: tenant-norm harde componentfeiten (opslag + default + leesbron).

Offline: de kiesbare set + de meegeleverde default-vijf, de signaal-mapping (één bron), de
uitgestelde toetsing (contract/koppelingen), de seed (idempotent), en de engine-borging
(import-afwezigheid + read-only bronscan). Live (skip-if-no-DB): de seed zaait exact de default,
en `norm_status` leest "vastgesteld ≠ gevuld" correct (incl. de hostingmodel-sentinel).
"""
import asyncio
import inspect
import pathlib
import uuid
from unittest.mock import AsyncMock

import pytest

from services import component_norm_service as cn
from services import registratiegaten_service as rg

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline — de kiesbare set + default ────────────────────────────────────────────────────────

def test_kiesbare_set_en_default_vijf():
    # 10 harde feiten; componentrol valt bewust af (nooit leeg → moot).
    assert len(cn.HARDE_FEITEN) == 10
    assert len(set(cn.HARDE_FEITEN)) == 10
    assert "componentrol" not in cn.HARDE_FEITEN
    # De meegeleverde platform-default = exact deze vijf (generiek, geen tenant-uitzondering).
    assert cn.DEFAULT_VERPLICHT == {
        cn.FEIT_EIGENAAR, cn.FEIT_VERANTWOORDELIJKE, cn.FEIT_BIV,
        cn.FEIT_CONTRACT, cn.FEIT_KOPPELINGEN,
    }
    assert cn.DEFAULT_VERPLICHT <= set(cn.HARDE_FEITEN)
    # De andere vijf staan default op niet-verplicht.
    assert set(cn.HARDE_FEITEN) - cn.DEFAULT_VERPLICHT == {
        cn.FEIT_GEBRUIKERSGROEP, cn.FEIT_BEDRIJFSFUNCTIE,
        cn.FEIT_LEVENSFASE, cn.FEIT_BEDOELING, cn.FEIT_HOSTING,
    }


def test_signaal_mapping_is_een_bron():
    """De vijf signaal-gedekte feiten verwijzen RECHTSTREEKS naar de signaal-constanten van
    registratiegaten_service — geen tweede, driftende afleiding."""
    assert cn._FEIT_SIGNAAL == {
        cn.FEIT_EIGENAAR: rg._SIG_EIGENAAR,
        cn.FEIT_VERANTWOORDELIJKE: rg._SIG_VERANTWOORDELIJKE,
        cn.FEIT_BIV: rg._SIG_BIV,
        cn.FEIT_GEBRUIKERSGROEP: rg._SIG_GG,
        cn.FEIT_BEDRIJFSFUNCTIE: rg._SIG_GEEN_BF,
    }


def test_contract_en_koppelingen_zijn_uitgesteld():
    # ADR-052: hun toetsing hangt af van "bewust geen" (slice 2) — nu expliciet TOETSING_VOLGT.
    assert cn._UITGESTELD == {cn.FEIT_CONTRACT, cn.FEIT_KOPPELINGEN}
    assert cn.FEIT_CONTRACT not in cn._FEIT_SIGNAAL
    assert cn.FEIT_KOPPELINGEN not in cn._FEIT_SIGNAAL


def test_seed_component_norm_idempotent():
    from services.seed import seed_component_norm

    session = AsyncMock()
    assert asyncio.run(seed_component_norm(session, uuid.uuid4())) == len(cn.HARDE_FEITEN)
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()
    # Tweede (idempotente) run — geen fout, zelfde returnwaarde.
    session2 = AsyncMock()
    assert asyncio.run(seed_component_norm(session2, uuid.uuid4())) == len(cn.HARDE_FEITEN)


# ── Offline — engine-borging (dubbel: import-afwezigheid + read-only bronscan) ──────────────────

def test_engine_import_afwezig():
    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(cn, naam), f"component_norm_service mag {naam} niet importeren"


def test_read_only_bronscan():
    """De service muteert niets: geen enkel schrijf-primitief in de bron."""
    src = inspect.getsource(cn)
    for verboden in ("session.add", ".commit(", ".flush(", "session.delete", ".delete("):
        assert verboden not in src, f"read-only-schending: {verboden} in component_norm_service"


# ── Live (skip-if-no-DB) ───────────────────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
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


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar")


async def _run_rls(fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.core.tenant_context import reset_tenant_context, zet_tenant_context

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    ttok = zet_tenant_context(_TID)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_tenant_context(ttok)
        await eng.dispose()


@integratie
def test_seed_zaait_default_en_haal_norm_live():
    from sqlalchemy import text
    from services.seed import seed_component_norm

    async def _flow(s):
        await s.execute(text("DELETE FROM component_norm WHERE tenant_id = :t"), {"t": _TID})
        await s.commit()
        try:
            aantal = await seed_component_norm(s, _TID)
            norm = await cn.haal_norm(s, _TID)
            # exact de default-vijf op true, de rest false
            verplicht = {f for f, v in norm.items() if v}
            return aantal, verplicht, set(norm)
        finally:
            await s.execute(text("DELETE FROM component_norm WHERE tenant_id = :t"), {"t": _TID})
            await s.commit()

    aantal, verplicht, alle = asyncio.run(_run_rls(_flow))
    assert aantal == 10
    assert verplicht == cn.DEFAULT_VERPLICHT
    assert alle == set(cn.HARDE_FEITEN)


@integratie
def test_norm_status_vastgesteld_is_niet_gevuld_live():
    from sqlalchemy import text
    from models.models import Component, ComponentNorm, Element, ElementType, HostingModel

    async def _flow(s):
        eid = None
        try:
            # Raw component (geen engine-pad): hostingmodel = sentinel, geen eigenaar/relaties.
            elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
            s.add(elem)
            await s.flush()
            eid = elem.id
            s.add(Component(
                id=eid, tenant_id=uuid.UUID(_TID), naam="WT-Norm-Comp",
                componenttype="applicatie", hostingmodel=HostingModel.onbekend,
            ))
            # Zet ALLE harde feiten verplicht (test ook de niet-default-feiten).
            for feit in cn.HARDE_FEITEN:
                s.add(ComponentNorm(tenant_id=uuid.UUID(_TID), feit_sleutel=feit, verplicht=True))
            await s.commit()

            status_leeg = (await cn.norm_status(s, _TID, eid))["feiten"]

            # Vul hosting + levensfase + bedoeling → die drie moeten kantelen naar vastgesteld.
            await s.execute(text(
                "UPDATE component SET hostingmodel='saas', levensfase='in_productie', "
                "migratiepad='herbouw' WHERE id=:i"), {"i": str(eid)})
            await s.commit()
            status_gevuld = (await cn.norm_status(s, _TID, eid))["feiten"]
            return status_leeg, status_gevuld
        finally:
            await s.execute(text("DELETE FROM component_norm WHERE tenant_id = :t"), {"t": _TID})
            if eid is not None:
                await s.execute(text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    leeg, gevuld = asyncio.run(_run_rls(_flow))
    # Alle 10 feiten verplicht → alle 10 in de uitkomst.
    assert set(leeg) == set(cn.HARDE_FEITEN)
    # Contract + koppelingen: toetsing volgt (slice 2), ongeacht de stand.
    assert leeg[cn.FEIT_CONTRACT] == cn.TOETSING_VOLGT
    assert leeg[cn.FEIT_KOPPELINGEN] == cn.TOETSING_VOLGT
    # Kale component: sentinel + lege velden + geen relaties = niet vastgesteld.
    for feit in (cn.FEIT_EIGENAAR, cn.FEIT_VERANTWOORDELIJKE, cn.FEIT_BIV,
                 cn.FEIT_GEBRUIKERSGROEP, cn.FEIT_BEDRIJFSFUNCTIE,
                 cn.FEIT_HOSTING, cn.FEIT_LEVENSFASE, cn.FEIT_BEDOELING):
        assert leeg[feit] == cn.NIET_VASTGESTELD, feit
    # Na vullen: hosting/levensfase/bedoeling vastgesteld; de relationele blijven ongemoeid.
    assert gevuld[cn.FEIT_HOSTING] == cn.VASTGESTELD
    assert gevuld[cn.FEIT_LEVENSFASE] == cn.VASTGESTELD
    assert gevuld[cn.FEIT_BEDOELING] == cn.VASTGESTELD
    assert gevuld[cn.FEIT_EIGENAAR] == cn.NIET_VASTGESTELD
