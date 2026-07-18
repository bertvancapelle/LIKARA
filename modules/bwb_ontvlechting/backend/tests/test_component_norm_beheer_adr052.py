"""Tests — ADR-052 slice 4b: het norm-beheerscherm (schrijfkant + impact-voorspelling).

Offline: engine-borging op de schrijf-service. Live (skip-if-no-DB, EIGEN test-tenant zodat de
impact — die álle componenten van de tenant telt — deterministisch is): de impact-voorspelling
(componenten/klaarverklaringen geraakt, incl. het nul-geval en 'alsnog compleet' bij uitzetten) en de
zet_verplicht → norm_definitie round-trip.
"""
import asyncio
import uuid

import pytest

import app.core.audit  # noqa: F401 — registreert de audit-capture-hook
import app.core.database  # noqa: F401 — registreert de after_begin RLS-hook
from services import component_norm_beheer_service as bs
from services import component_norm_service as cn

# Eigen test-tenant (isolatie: de impact telt de HELE tenant — geen dev-data ertussen).
_TID = "99990052-4b00-0000-0000-000000000052"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline — engine-borging ─────────────────────────────────────────────────────────────────────

def test_engine_import_afwezig():
    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(bs, naam), f"component_norm_beheer_service mag {naam} niet importeren"


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


async def _maak_component(s, naam, *, levensfase=None, hosting="on_premise"):
    from models.models import Component, Element, ElementType, HostingModel
    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    s.add(Component(
        id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam, componenttype="applicatie",
        hostingmodel=HostingModel(hosting), levensfase=levensfase,
    ))
    await s.flush()
    return elem.id


async def _leeg(s):
    from sqlalchemy import text
    for tbl in ("component_klaarverklaring", "component_norm"):
        await s.execute(text(f"DELETE FROM {tbl} WHERE tenant_id=:t"), {"t": _TID})
    await s.execute(text("DELETE FROM element WHERE tenant_id=:t"), {"t": _TID})  # cascade → component
    await s.commit()


@integratie
def test_impact_voorspelling_incl_nul_en_uitzetten_live():
    from models.models import ComponentNorm
    from schemas.component_klaarverklaring import KlaarverklaringCreate
    from services import component_klaarverklaring_service

    async def _flow(s):
        await _leeg(s)
        try:
            # A: levensfase vastgesteld · B: levensfase open + klaar verklaard. Beide hosting gezet.
            await _maak_component(s, "WT-4b-A", levensfase="in_productie")
            b = await _maak_component(s, "WT-4b-B", levensfase=None)
            # Alléén levensfase verplicht (zo is het B's énige open verplichte feit).
            s.add(ComponentNorm(tenant_id=uuid.UUID(_TID), feit_sleutel="levensfase", verplicht=True))
            await s.commit()
            await component_klaarverklaring_service.maak_aan(
                s, _TID, KlaarverklaringCreate(component_id=b, reden="wt"))

            aan = await bs.impact_voor_feit(s, _TID, "levensfase", True)   # aanzetten
            nul = await bs.impact_voor_feit(s, _TID, "hosting", True)      # beide hosting gezet → nul
            uit = await bs.impact_voor_feit(s, _TID, "levensfase", False)  # uitzetten
            return aan, nul, uit
        finally:
            await _leeg(s)

    aan, nul, uit = asyncio.run(_run_rls(_flow))
    # Aanzetten levensfase: 1 component open (B), en dat is een klaarverklaring.
    assert aan["componenten_geraakt"] == 1
    assert aan["klaarverklaringen_geraakt"] == 1
    assert "componenten_nu_compleet" not in aan
    # Nul-geval: hosting is op beide gezet → niemand geraakt.
    assert nul["componenten_geraakt"] == 0
    assert nul["klaarverklaringen_geraakt"] == 0
    # Uitzetten levensfase: B voldoet alsnog (het was zijn énige open verplichte feit).
    assert uit["componenten_geraakt"] == 1
    assert uit["componenten_nu_compleet"] == 1


@integratie
def test_zet_verplicht_en_norm_definitie_round_trip_live():
    async def _flow(s):
        await _leeg(s)
        try:
            from services.seed import seed_component_norm
            await seed_component_norm(s, _TID)  # default: gebruikersgroep = niet verplicht
            voor = {r["feit"]: r["verplicht"] for r in await cn.norm_definitie(s, _TID)}
            await bs.zet_verplicht(s, _TID, "gebruikersgroep", True)
            defs = await cn.norm_definitie(s, _TID)
            na = {r["feit"]: r["verplicht"] for r in defs}
            bewust = {r["feit"]: r["bewust_geen_mogelijk"] for r in defs}
            return voor, na, bewust
        finally:
            await _leeg(s)

    voor, na, bewust = asyncio.run(_run_rls(_flow))
    assert voor["gebruikersgroep"] is False and na["gebruikersgroep"] is True     # de lat verschoof
    assert na["eigenaar"] is True                                                 # default onaangeroerd
    # "bewust geen" alleen voor de relationele feiten (koppelingen/contract), niet voor eigen velden.
    assert bewust["koppelingen"] is True and bewust["contract"] is True
    assert bewust["levensfase"] is False and bewust["eigenaar"] is False


@integratie
def test_lat_verschoven_metadata_uit_audit_live():
    """Besluit 5 — een toggle via `zet_verplicht` (ORM) wordt geaudit; `_lat_verschoven_metadata`
    leest wanneer/door wie uit dat audit-spoor (geen nieuwe opslag). Bewijst óók de jsonb-query."""
    from app.core.tenant_context import reset_audit_context, zet_audit_context
    from services.seed import seed_component_norm

    async def _flow(s):
        await _leeg(s)
        tok = zet_audit_context("kc-sub-4b", "beheerder@bwb.nl")
        try:
            await seed_component_norm(s, _TID)  # gebruikersgroep = niet verplicht
            await bs.zet_verplicht(s, _TID, "gebruikersgroep", True)  # geaudit met de actor
            return await cn._lat_verschoven_metadata(s, uuid.UUID(_TID), "gebruikersgroep")
        finally:
            reset_audit_context(tok)
            await _leeg(s)

    meta = asyncio.run(_run_rls(_flow))
    assert meta.get("verschoven_door") == "beheerder@bwb.nl"  # geen persoon-koppeling → e-mail-fallback
    assert meta.get("verschoven_op") is not None


def test_onbekend_feit_404():
    """Offline-ish contractcheck op de validatie (geen DB nodig — faalt vóór enige query)."""
    from services.errors import NietGevonden

    async def _flow():
        with pytest.raises(NietGevonden):
            await bs.zet_verplicht(None, _TID, "geen-echt-feit", True)
    asyncio.run(_flow())
