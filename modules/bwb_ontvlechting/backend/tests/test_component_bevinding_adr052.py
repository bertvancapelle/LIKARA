"""Tests — ADR-052 slice 2: "bewust geen"-bevinding op een component (koppelingen/contract).

Offline: engine-borging (import-afwezigheid + geen engine-symbolen in de bron) + schema-validatie.
Live (skip-if-no-DB): de norm-toets is niet meer `toetsing_volgt` maar echt — zonder registratie én
zonder bevinding = niet_vastgesteld; met bevinding = vastgesteld; met échte koppeling/contract =
vastgesteld (die wint); en 'bewust geen' náást een echte registratie wordt geweigerd (geen tegenspraak).
"""
import asyncio
import inspect
import uuid

import pytest

import app.core.database  # noqa: F401 — registreert de after_begin RLS-hook
from services import component_bevinding_service as cb
from services import component_norm_service as cn

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline — engine-borging + schema ──────────────────────────────────────────────────────────

def test_engine_import_afwezig():
    for naam in ("lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
                 "ComponentProfiel", "Blokkade", "Checklistscore"):
        assert not hasattr(cb, naam), f"component_bevinding_service mag {naam} niet importeren"


def test_geen_engine_symbolen_in_bron():
    src = inspect.getsource(cb)
    for verboden in ("lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
                     "ComponentProfiel", "Blokkade", "Checklistscore", "lifecycle_status"):
        assert verboden not in src, f"engine-symbool {verboden} in component_bevinding_service"


def test_schema_soort_validatie():
    from schemas.component_bevinding import BevindingCreate

    assert BevindingCreate(soort="koppelingen").soort == "koppelingen"
    assert BevindingCreate(soort="contract", toelichting="  x  ").toelichting == "x"
    assert BevindingCreate(soort="koppelingen", toelichting="   ").toelichting is None
    with pytest.raises(Exception):
        BevindingCreate(soort="onzin")


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


async def _maak_component(s, naam):
    from models.models import Component, Element, ElementType, HostingModel
    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    s.add(Component(id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam,
                    componenttype="applicatie", hostingmodel=HostingModel.onbekend))
    await s.flush()
    return elem.id


async def _norm_alles_verplicht(s):
    from sqlalchemy import text
    from models.models import ComponentNorm
    await s.execute(text("DELETE FROM component_norm WHERE tenant_id=:t"), {"t": _TID})
    for f in cn.HARDE_FEITEN:
        s.add(ComponentNorm(tenant_id=uuid.UUID(_TID), feit_sleutel=f, verplicht=True))
    await s.flush()


def _status(session_result, feit):
    return session_result["feiten"][feit]


@integratie
def test_koppelingen_bevinding_cyclus_live():
    from sqlalchemy import text

    async def _flow(s):
        ids = []
        try:
            await _norm_alles_verplicht(s)
            cid = await _maak_component(s, "WT-Bev-Koppel")
            ids.append(cid)
            await s.commit()

            # 1. zonder koppeling én zonder bevinding → niet_vastgesteld
            v0 = _status(await cn.norm_status(s, _TID, cid), cn.FEIT_KOPPELINGEN)
            # 2. bewust geen → vastgesteld
            await cb.registreer_geen(s, _TID, cid, "koppelingen")
            v1 = _status(await cn.norm_status(s, _TID, cid), cn.FEIT_KOPPELINGEN)
            soorten = await cb.soorten_van_component(s, _TID, cid)
            # 3. intrekken → weer niet_vastgesteld
            await cb.verwijder(s, _TID, cid, "koppelingen")
            v2 = _status(await cn.norm_status(s, _TID, cid), cn.FEIT_KOPPELINGEN)
            return v0, v1, soorten, v2
        finally:
            await s.execute(text("DELETE FROM component_norm WHERE tenant_id=:t"), {"t": _TID})
            for eid in ids:
                await s.execute(text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    v0, v1, soorten, v2 = asyncio.run(_run_rls(_flow))
    assert v0 == cn.NIET_VASTGESTELD
    assert v1 == cn.VASTGESTELD
    assert "koppelingen" in soorten
    assert v2 == cn.NIET_VASTGESTELD


@integratie
def test_echte_koppeling_wint_en_weigert_bevinding_live():
    from sqlalchemy import text
    from models.models import Relatie
    from services.errors import RegistratieConflict

    async def _flow(s):
        ids = []
        conflict = None
        try:
            await _norm_alles_verplicht(s)
            a = await _maak_component(s, "WT-Bev-A")
            b = await _maak_component(s, "WT-Bev-B")
            ids += [a, b]
            s.add(Relatie(tenant_id=uuid.UUID(_TID), bron_id=a, doel_id=b,
                          relatietype="flow", naam="WT-flow", kenmerken={}))
            await s.commit()

            echt = await cb.heeft_echte_registratie(s, _TID, a, "koppelingen")
            v = _status(await cn.norm_status(s, _TID, a), cn.FEIT_KOPPELINGEN)
            try:
                await cb.registreer_geen(s, _TID, a, "koppelingen")
            except RegistratieConflict as e:
                conflict = e.code
                await s.rollback()
            return echt, v, conflict
        finally:
            await s.execute(text("DELETE FROM component_norm WHERE tenant_id=:t"), {"t": _TID})
            for eid in ids:
                await s.execute(text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    echt, v, conflict = asyncio.run(_run_rls(_flow))
    assert echt is True
    assert v == cn.VASTGESTELD           # echte koppeling wint
    assert conflict == "REGISTRATIE_BESTAAT"  # 'bewust geen' geweigerd naast een echte koppeling


@integratie
def test_contract_echt_en_bevinding_live():
    from sqlalchemy import text
    from models.models import (
        Component, Contract, ContractType, Element, ElementType, HostingModel,
        Partij, PartijAard, PartijScope, Relatie,
    )
    from services.errors import RegistratieConflict

    async def _flow(s):
        ids = []
        conflict = None
        try:
            await _norm_alles_verplicht(s)
            # Leverancier (org) + contract + component-mét-contract (association).
            lev = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.partij)
            s.add(lev); await s.flush()
            s.add(Partij(id=lev.id, tenant_id=uuid.UUID(_TID), aard=PartijAard.organisatie,
                         naam="WT-Bev-Leverancier", scope=PartijScope.extern))
            con = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.contract)
            s.add(con); await s.flush()
            s.add(Contract(id=con.id, tenant_id=uuid.UUID(_TID), leverancier_id=lev.id,
                           contracttype=ContractType.los_contract, contractnaam="WT-Bev-Contract"))
            cmet = await _maak_component(s, "WT-Bev-MetContract")
            s.add(Relatie(tenant_id=uuid.UUID(_TID), bron_id=cmet, doel_id=con.id,
                          relatietype="association", kenmerken={}))
            czonder = await _maak_component(s, "WT-Bev-ZonderContract")
            ids += [lev.id, con.id, cmet, czonder]
            await s.commit()

            echt_met = await cb.heeft_echte_registratie(s, _TID, cmet, "contract")
            v_met = _status(await cn.norm_status(s, _TID, cmet), cn.FEIT_CONTRACT)
            try:
                await cb.registreer_geen(s, _TID, cmet, "contract")
            except RegistratieConflict as e:
                conflict = e.code
                await s.rollback()

            echt_zonder = await cb.heeft_echte_registratie(s, _TID, czonder, "contract")
            await cb.registreer_geen(s, _TID, czonder, "contract")
            v_zonder = _status(await cn.norm_status(s, _TID, czonder), cn.FEIT_CONTRACT)
            return echt_met, v_met, conflict, echt_zonder, v_zonder
        finally:
            await s.execute(text("DELETE FROM component_norm WHERE tenant_id=:t"), {"t": _TID})
            # Omgekeerde volgorde: componenten + contract vóór de leverancier-partij
            # (contract.leverancier_id → element is ON DELETE RESTRICT).
            for eid in reversed(ids):
                await s.execute(text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    echt_met, v_met, conflict, echt_zonder, v_zonder = asyncio.run(_run_rls(_flow))
    assert echt_met is True and v_met == cn.VASTGESTELD
    assert conflict == "REGISTRATIE_BESTAAT"
    assert echt_zonder is False
    assert v_zonder == cn.VASTGESTELD  # bewust geen contract → vastgesteld
