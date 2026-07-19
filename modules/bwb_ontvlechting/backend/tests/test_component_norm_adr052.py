"""Tests — ADR-052 slice 1: tenant-norm harde componentfeiten (opslag + default + leesbron).

Offline: de kiesbare set + de meegeleverde default-vijf, de signaal-mapping (één bron), de
uitgestelde toetsing (contract/koppelingen), de seed (idempotent), en de engine-borging
(import-afwezigheid + read-only bronscan). Live (skip-if-no-DB, EIGEN test-tenant zodat de
norm-teardown het demolandschap niet raakt — zie `_TID`): de seed zaait exact de default,
en `norm_status` leest "vastgesteld ≠ gevuld" correct (incl. de hostingmodel-sentinel).
"""
import asyncio
import inspect
import pathlib
import uuid
from unittest.mock import AsyncMock

import pytest

import app.core.database  # noqa: F401 — registreert de after_begin RLS-hook (self-contained live-tests)
from services import component_norm_service as cn
from services import registratiegaten_service as rg

# Eigen test-tenant (LI047). VERPLICHT hier: `component_norm` hangt aan de TENANT, niet aan een
# component — de teardown kan zich dus niet tot eigen fixtures beperken en wist onvermijdelijk de
# hele norm van de tenant waarin hij draait. Op de dev-tenant vaagde dat het demolandschap leeg
# (de norm was na elke suite-run weg; zie docs/Onderzoek-normdrift-en-taal-V047.md deel A).
# Zelfde reden en zelfde vorm als test_component_norm_beheer_adr052.py — norm likara-tests §LI039.
_TID = "99990052-0100-0000-0000-000000000001"
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


def test_contract_en_koppelingen_via_bevinding_pad():
    # ADR-052 slice 2: contract + koppelingen zijn niet signaal-gemapt maar lopen via de
    # bevinding-/echte-registratie-toets (component_bevinding_service). De tijdelijke
    # `toetsing_volgt`-stand uit slice 1 bestaat niet meer.
    assert cn.FEIT_CONTRACT not in cn._FEIT_SIGNAAL
    assert cn.FEIT_KOPPELINGEN not in cn._FEIT_SIGNAAL
    assert not hasattr(cn, "TOETSING_VOLGT")
    assert not hasattr(cn, "_UITGESTELD")


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


# ── Offline — de verschoven lat onderscheiden van de bewuste afwijking (besluiten 8-11, LI045) ────

def test_splits_afwijking_verdeelt_tegen_snapshot():
    """`bewust` = stond in de snapshot (bij het verklaren afgewogen); `verschoven` = stond er niet in
    (de lat verschoof sindsdien). Wat de snapshot niet noemde is nooit een bewust besluit geweest."""
    # pure VERSCHOVEN LAT: lege snapshot → alles verschoven, niets bewust
    assert cn.splits_afwijking(["biv", "eigenaar"], []) == {"bewust": [], "verschoven": ["biv", "eigenaar"]}
    # pure BEWUSTE AFWIJKING: alles stond in de snapshot
    assert cn.splits_afwijking(["biv", "eigenaar"], ["biv", "eigenaar", "contract"]) == {
        "bewust": ["biv", "eigenaar"], "verschoven": []}
    # BEIDE (case D): biv stond erin (bewust), bedoeling niet (verschoven)
    assert cn.splits_afwijking(["biv", "bedoeling"], ["biv", "eigenaar", "verantwoordelijke"]) == {
        "bewust": ["biv"], "verschoven": ["bedoeling"]}
    # geen open feiten → geen enkel signaal
    assert cn.splits_afwijking([], ["biv"]) == {"bewust": [], "verschoven": []}


def test_splits_afwijking_geen_bruikbare_snapshot():
    """Randgeval — geen bruikbare snapshot (None of leeg; bv. klaar verklaard vóór er een norm was):
    niets is bewust afgewogen → alles verschoven. Nooit amber toeschrijven wat niemand accepteerde."""
    assert cn.splits_afwijking(["biv"], None) == {"bewust": [], "verschoven": ["biv"]}
    assert cn.splits_afwijking(["biv"], []) == {"bewust": [], "verschoven": ["biv"]}


def test_uitgezet_feit_valt_buiten_de_afleiding():
    """Randgeval — de beheerder ZET een feit UIT (lat versoepeld): `norm_status` geeft alleen nog
    verplichte feiten, dus het staat niet in de live-open input → het verschijnt in geen van beide
    categorieën (geen signaal). Hier gemodelleerd door 'hosting' niet in de live-open input te zetten."""
    r = cn.splits_afwijking(["biv"], ["biv", "hosting"])
    assert "hosting" not in r["bewust"] and "hosting" not in r["verschoven"]
    assert r == {"bewust": ["biv"], "verschoven": []}


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


async def _norm_alles_verplicht(s):
    from sqlalchemy import text
    from models.models import ComponentNorm
    await s.execute(text("DELETE FROM component_norm WHERE tenant_id=:t"), {"t": _TID})
    for f in cn.HARDE_FEITEN:
        s.add(ComponentNorm(tenant_id=uuid.UUID(_TID), feit_sleutel=f, verplicht=True))
    await s.flush()


async def _maak_component_norm(s, naam, hosting="onbekend"):
    from models.models import Component, Element, ElementType, HostingModel
    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    s.add(Component(id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam,
                    componenttype="applicatie", hostingmodel=HostingModel(hosting)))
    await s.flush()
    return elem.id


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
    # Kale component: sentinel + lege velden + geen relaties + geen bevinding = ALLES niet vastgesteld
    # (slice 2: contract/koppelingen niet meer `toetsing_volgt`, maar echt niet_vastgesteld).
    for feit in cn.HARDE_FEITEN:
        assert leeg[feit] == cn.NIET_VASTGESTELD, feit
    # Na vullen: hosting/levensfase/bedoeling vastgesteld; de relationele blijven ongemoeid.
    assert gevuld[cn.FEIT_HOSTING] == cn.VASTGESTELD
    assert gevuld[cn.FEIT_LEVENSFASE] == cn.VASTGESTELD
    assert gevuld[cn.FEIT_BEDOELING] == cn.VASTGESTELD
    assert gevuld[cn.FEIT_EIGENAAR] == cn.NIET_VASTGESTELD


# ── ADR-052 slice 3 — verrijkte klaarverklaring (snapshot bevriest; badge is live) ──────────────

@integratie
def test_klaarverklaring_snapshot_bevriest_maar_norm_status_leeft_live():
    from sqlalchemy import text
    from schemas.component_klaarverklaring import KlaarverklaringCreate
    from services import component_klaarverklaring_service as kv

    async def _flow(s):
        eid = None
        try:
            await _norm_alles_verplicht(s)
            eid = await _maak_component_norm(s, "WT-KV-Snapshot")  # hosting=onbekend, kaal
            await s.commit()

            # Klaar verklaren MÉT open feiten → snapshot bevriest wat NU open is.
            obj = await kv.maak_aan(s, _TID, KlaarverklaringCreate(component_id=eid, reden="Toch klaar."))
            snapshot = sorted(obj.open_feiten)
            live_bij_akkoord = sorted(
                f for f, st in (await cn.norm_status(s, _TID, eid))["feiten"].items()
                if st == cn.NIET_VASTGESTELD
            )
            # Vul één feit alsnog vast (hosting): live norm-status dooft, snapshot blijft.
            await s.execute(text("UPDATE component SET hostingmodel='saas' WHERE id=:i"), {"i": str(eid)})
            await s.commit()
            live_na = sorted(
                f for f, st in (await cn.norm_status(s, _TID, eid))["feiten"].items()
                if st == cn.NIET_VASTGESTELD
            )
            bewaard = sorted((await kv.lijst(s, _TID, component_id=eid))[0].open_feiten)
            return snapshot, live_bij_akkoord, live_na, bewaard
        finally:
            await s.execute(text("DELETE FROM component_norm WHERE tenant_id=:t"), {"t": _TID})
            if eid is not None:
                await s.execute(text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    snapshot, live_bij_akkoord, live_na, bewaard = asyncio.run(_run_rls(_flow))
    assert snapshot == live_bij_akkoord           # de snapshot = de open feiten op akkoord-moment
    assert "hosting" in snapshot                  # hosting stond open bij verklaren
    assert "hosting" not in live_na               # LIVE: na aanvullen is hosting weg (badge dooft)
    assert "hosting" in bewaard                   # SNAPSHOT: blijft bevroren (historie blijft)


@integratie
def test_klaarverklaring_geen_afwijking_bij_compleet_live():
    from sqlalchemy import text
    from models.models import ComponentNorm, HostingModel  # noqa: F401
    from schemas.component_klaarverklaring import KlaarverklaringCreate
    from services import component_klaarverklaring_service as kv

    async def _flow(s):
        eid = None
        try:
            # Norm: alléén hosting verplicht; component met hosting=saas → compleet.
            await s.execute(text("DELETE FROM component_norm WHERE tenant_id=:t"), {"t": _TID})
            s.add(ComponentNorm(tenant_id=uuid.UUID(_TID), feit_sleutel="hosting", verplicht=True))
            await s.flush()
            eid = await _maak_component_norm(s, "WT-KV-Compleet", hosting="saas")
            await s.commit()
            obj = await kv.maak_aan(s, _TID, KlaarverklaringCreate(component_id=eid, reden="Compleet."))
            return list(obj.open_feiten)
        finally:
            await s.execute(text("DELETE FROM component_norm WHERE tenant_id=:t"), {"t": _TID})
            if eid is not None:
                await s.execute(text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    open_feiten = asyncio.run(_run_rls(_flow))
    assert open_feiten == []  # geen openstaande verplichte feiten → lege snapshot (geen afwijking)
