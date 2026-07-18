"""Tests — ADR-052 S1 (LI045): het SCHONE geval in de dev-seed.

De demostaat toonde nergens hoe "gewoon in orde" eruitziet — elk klaar-verklaard component droeg een
signaal. Zonder een schoon geval kan geen browsercheck aantonen dat een signaal terécht wégblijft.
Deze test borgt de invariant die de seed vandaag oplevert: de seed-stap `_seed_schoon_geval` maakt een
component volledig norm-compleet (incl. een "bewust geen" op een relationeel feit — een leeg antwoord
is een echt antwoord) en verklaart het klaar, zodat het GEEN norm-signaal draagt — óók niet nadat de
lat verschuift. De test valt om zodra een seedwijziging dat schone geval per ongeluk vervuilt.

Offline: de constanten zijn coherent (bewust-geen op een relationeel feit; geldige bedoeling).
Live (skip-if-no-DB, EIGEN test-tenant): roep de ECHTE seed-stap aan en stel vast dat het component
signaalloos is na de bedoeling-toggle — en dat het signaal terugkeert zodra de bedoeling wegvalt.
"""
import asyncio
import uuid

import pytest

import app.core.audit  # noqa: F401 — registreert de audit-capture-hook
import app.core.database  # noqa: F401 — registreert de after_begin RLS-hook
import dev_seed_testdata as seed
from services import component_bevinding_service
from services import component_norm_beheer_service as bs
from services import component_norm_service as cn
from services.seed import seed_component_norm

# Eigen test-tenant (isolatie van de dev-data; de afwijking/norm zijn zo deterministisch).
_TID = "99990052-5100-0000-0000-000000000051"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline — coherentie van de keuze ──────────────────────────────────────────────────────────

def test_schoon_geval_constanten_coherent():
    from models.models import ComponentBevindingSoort, Migratiepad

    assert seed.SCHOON_GEVAL_NAAM == "HR-systeem"
    # het bewust-geen-feit is een RELATIONEEL feit (koppelingen/contract) — daar kan een leeg
    # antwoord een echt antwoord zijn; op een eigen veld bestaat "bewust geen" niet.
    assert seed.SCHOON_GEVAL_BEWUST_GEEN in {s.value for s in ComponentBevindingSoort}
    assert seed.SCHOON_GEVAL_BEWUST_GEEN in cn.HARDE_FEITEN
    # de bedoeling is een geldige bestemming → de bedoeling-toggle raakt het schone geval niet.
    assert seed.SCHOON_GEVAL_MIGRATIEPAD in {m.value for m in Migratiepad}


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────────────────────

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


async def _leeg(s):
    from sqlalchemy import text
    for tbl in ("component_klaarverklaring", "component_bevinding", "roltoewijzing", "component_norm"):
        await s.execute(text(f"DELETE FROM {tbl} WHERE tenant_id=:t"), {"t": _TID})
    await s.execute(text("DELETE FROM element WHERE tenant_id=:t"), {"t": _TID})  # cascade → component/partij
    await s.commit()


async def _maak_partij(s, naam):
    from models.models import Element, ElementType, Partij, PartijAard, PartijScope
    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.partij)
    s.add(elem)
    await s.flush()
    # aard=organisatie vereist een scope (ck_partij_scope_aanwezig) — een gemeente is intern.
    s.add(Partij(id=elem.id, tenant_id=uuid.UUID(_TID), aard=PartijAard.organisatie,
                 naam=naam, scope=PartijScope.intern))
    await s.flush()
    return elem.id


async def _maak_component(s, naam, *, eigenaar, hosting="saas"):
    from models.models import Component, Element, ElementType, HostingModel
    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    s.add(Component(
        id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam, componenttype="applicatie",
        hostingmodel=HostingModel(hosting), eigenaar_organisatie_id=eigenaar,
    ))
    await s.flush()
    return elem.id


async def _roltoewijzing(s, partij, obj, rol):
    from models.models import Roltoewijzing
    s.add(Roltoewijzing(tenant_id=uuid.UUID(_TID), partij_id=partij, object_id=obj, rol=rol))
    await s.flush()


@integratie
def test_seed_schoon_geval_is_signaalloos_ook_na_latverschuiving():
    """De ECHTE seed-stap `_seed_schoon_geval` levert een component zonder enig norm-signaal, ook nadat
    de lat verschuift — en het signaal keert terug zodra de bedoeling (die de seed zet) wegvalt."""
    from sqlalchemy import select
    from models.models import Component

    async def _flow(s):
        await _leeg(s)
        try:
            # Prerequisites uit het scenario: eigenaar + verantwoordelijke + contract.
            # (contract hier via "bewust geen" — de test toetst de seed-stap, niet hoe contract is belegd.)
            partij = await _maak_partij(s, "Gemeente Culemborg")
            comp = await _maak_component(s, seed.SCHOON_GEVAL_NAAM, eigenaar=partij)
            await _roltoewijzing(s, partij, comp, "functioneel_beheer")     # verantwoordelijke vastgesteld
            await component_bevinding_service.registreer_geen(s, _TID, comp, "contract")
            await seed_component_norm(s, _TID)                              # default-vijf verplicht
            await s.commit()

            # DE seed-stap zelf: BIV + bedoeling + "bewust geen koppelingen" + klaar verklaren (onder default).
            await seed._seed_schoon_geval(s, _TID, comp)

            # Nú verschuift de beheerder de lat: bedoeling verplicht.
            await bs.zet_verplicht(s, _TID, "bedoeling", True)
            na_status = await cn.norm_status(s, _TID, comp)
            na_afw = await cn.afwijking_voor_component(s, _TID, comp)

            # Bite-proof: haal het door de seed gezette feit (bedoeling) weg → precies de vervuiling die
            # deze guard moet vangen. Het neutrale signaal hoort dan terug te keren.
            c = (await s.execute(
                select(Component).where(Component.id == comp, Component.tenant_id == uuid.UUID(_TID)))
            ).scalar_one()
            c.migratiepad = None
            await s.commit()
            vuil_afw = await cn.afwijking_voor_component(s, _TID, comp)
            return na_status, na_afw, vuil_afw
        finally:
            await _leeg(s)

    na_status, na_afw, vuil_afw = asyncio.run(_run_rls(_flow))

    # Alle zes verplichte feiten vastgesteld — incl. bedoeling ná de toggle (koppelingen via bewust geen).
    assert set(na_status["feiten"]) == {
        "eigenaar", "verantwoordelijke", "biv", "contract", "koppelingen", "bedoeling"}
    assert all(v == cn.VASTGESTELD for v in na_status["feiten"].values()), na_status["feiten"]

    # GEEN norm-signaal — amber (bewust) noch neutraal (verschoven) — óók na de latverschuiving.
    assert na_afw["bewust"] == [] and na_afw["verschoven"] == [], na_afw

    # De guard bijt: valt de door de seed gezette bedoeling weg, dan keert het neutrale signaal terug.
    assert vuil_afw["verschoven"] == ["bedoeling"], vuil_afw
    assert vuil_afw["bewust"] == [], vuil_afw
