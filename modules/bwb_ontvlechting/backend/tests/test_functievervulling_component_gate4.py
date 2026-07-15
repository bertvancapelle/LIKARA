"""Tests — ADR-043 gate 4 slice 1 (blok 1, backend): koppelen vanuit het component + het gat.

Offline:
- INVARIANT (niet-onderhandelbaar): `overzicht_voor_component` LEEST de gedeelde leesregel
  `dekking_overzicht` en bevat GÉÉN eigen rauwe `select(Functievervulling`-query (de tweede-
  waarheid-val — een naïeve `where component_id` zou "geldt overal" tonen terwijl een plek
  verdrongen is). Bronscan, faalt zodra een consument de leeslaag omzeilt.
- Het werkvoorraad-gat-signaal bestaat, hangt aan `ondersteunt_werk` (geen vals gat op een
  niet-koppelbaar type) en staat in de aggregator; de api-laag draagt de component-leesmethode.

Live (skip-if-no-DB): de component-lezer weerspiegelt de verdringing (grof telt af, `verdrongen_op`
loopt op) — bewijs dat ze door de leeslaag gaat; het gat-signaal + de lijstfilter + de badge tonen
"nog geen bedrijfsfunctie" alleen voor werk-ondersteunende systemen zonder koppeling.
"""
import asyncio
import inspect
import pathlib
import uuid

import pytest

import app.core.audit  # noqa: F401 — registreert de audit-capture-hook
import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import (
    reset_audit_context,
    reset_tenant_context,
    zet_audit_context,
    zet_tenant_context,
)

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_API = pathlib.Path(__file__).resolve().parents[4] / "frontend" / "src" / "api.js"
_SECTIE_VUE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "frontend" / "views" / "ComponentBedrijfsfunctieSectie.vue"
)


# ── Offline: de invariant (één leesbron, geen tweede waarheid) ────────────────────

def test_component_lezer_gaat_door_de_leeslaag_niet_rauw():
    """De richting component → plekken leest de gedeelde afleiding; ze bouwt de grof/fijn-
    resolutie NIET zelf na met een rauwe `where component_id`-query."""
    import services.functievervulling_service as svc

    src = inspect.getsource(svc.overzicht_voor_component)
    assert "dekking_overzicht(" in src, "de component-lezer moet de gedeelde leesregel lezen"
    assert "select(Functievervulling" not in src, (
        "GEEN rauwe functievervulling-query in de component-lezer — dat zou de verdringing missen"
    )
    # De resolutie 'fijn verdringt grof' leeft nog steeds op ÉÉN plek (dekking_overzicht), niet hier.
    assert "fijn_per_plek" not in src and "grof_per_functie" not in src


def test_api_laag_draagt_de_component_leesmethode():
    api = _API.read_text(encoding="utf-8")
    assert "componentKoppelingen" in api and "/functievervullingen/component/" in api


def test_component_sectie_leest_de_leeslaag_en_rekent_niet_zelf():
    """De componentdetail-sectie LEEST de gedeelde afleiding (roept `componentKoppelingen` aan) en
    reproduceert de grof/fijn-resolutie of de verdringing NIET zelf — dezelfde borging als de boom
    (LI041): een tweede resolutie in de .vue moet FALEN."""
    vue = _SECTIE_VUE.read_text(encoding="utf-8")
    assert "functievervullingen.componentKoppelingen" in vue, "de sectie moet de leeslaag lezen"
    for verboden in ("fijn_per_plek", "grof_per_functie", "totaal_plekken_per_functie", "verfijnd_per_functie"):
        assert verboden not in vue, (
            f"de sectie mag de resolutie/telling niet dupliceren ({verboden}) — die leeslaag hoort server-side"
        )


def test_werkvoorraad_gat_signaal_bestaat_en_hangt_aan_ondersteunt_werk():
    import services.registratiegaten_service as rgs

    assert rgs._SIG_GEEN_BF == "component_zonder_bedrijfsfunctie"
    # Het gat hangt aan de catalogus-eigenschap `ondersteunt_werk` (geen hardcoded typelijst,
    # geen vals gat op een niet-koppelbaar type).
    bron = inspect.getsource(rgs.component_zonder_bedrijfsfunctie)
    assert "_ondersteunt_werk_typen()" in bron
    # Staat in de centrale aggregator (aandacht) — één afleiding, één plek.
    agg = inspect.getsource(rgs.registratiegaten)
    assert "_SIG_GEEN_BF: await component_zonder_bedrijfsfunctie" in agg


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                res = (await c.execute(text("SELECT to_regclass('functievervulling')"))).scalar()
            return res is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB/functievervulling-tabel niet bereikbaar")


async def _run_rls(actor, fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    ttok = zet_tenant_context(_TID)
    atok = zet_audit_context(actor, f"{actor}@test")
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_audit_context(atok)
        reset_tenant_context(ttok)
        await eng.dispose()


async def _maak_component(s, naam, componenttype="applicatie"):
    from models.models import Component, Element, ElementType, HostingModel

    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    s.add(Component(id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam, componenttype=componenttype,
                    hostingmodel=HostingModel.on_premise))
    await s.commit()
    return elem.id


async def _maak_functie(s, naam):
    from models.models import Bedrijfsfunctie, Element, ElementType

    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.bedrijfsfunctie)
    s.add(elem)
    await s.flush()
    s.add(Bedrijfsfunctie(id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam, vervallen=False))
    await s.commit()
    return elem.id


async def _maak_plek(s, ouder_id, functie_id):
    from models.models import Relatie

    s.add(Relatie(tenant_id=uuid.UUID(_TID), bron_id=ouder_id, doel_id=functie_id,
                  relatietype="aggregation", kenmerken={}))
    await s.commit()


async def _ruim(s, ids):
    from sqlalchemy import text as _text

    for eid in reversed(ids):
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    await s.commit()


@integratie
def test_component_lezer_weerspiegelt_verdringing_live():
    """Vanaf het systeem bekeken: grof "geldt overal" telt af zodra een plek fijn wordt verdrongen,
    en `verdrongen_op` loopt op — waarden die alleen uit de leeslaag komen (een rauwe
    where-component_id-query kent geen verdringing/reikwijdte)."""
    from services import functievervulling_service as svc

    async def _flow(s):
        ids = []
        try:
            handh = await _maak_component(s, "G4 Handhaving", "applicatie")
            insp = await _maak_component(s, "G4 Inspectie-app", "applicatie")
            ids += [handh, insp]
            milieu = await _maak_functie(s, "G4 Milieu")
            bouw = await _maak_functie(s, "G4 Bouwen")
            toezicht = await _maak_functie(s, "G4 Toezicht")
            ids += [milieu, bouw, toezicht]
            await _maak_plek(s, milieu, toezicht)
            await _maak_plek(s, bouw, toezicht)

            await svc.maak_aan(s, _TID, handh, toezicht, None)  # grof, geldt overal
            voor = await svc.overzicht_voor_component(s, _TID, handh)
            await svc.maak_aan(s, _TID, insp, toezicht, milieu)  # fijn onder Milieu
            na_handh = await svc.overzicht_voor_component(s, _TID, handh)
            na_insp = await svc.overzicht_voor_component(s, _TID, insp)
            return voor, na_handh, na_insp, (toezicht, milieu)
        finally:
            await _ruim(s, ids)

    voor, na_handh, na_insp, (toezicht, milieu) = asyncio.run(_run_rls("test:bert", _flow))
    # Vóór verfijnen: één grove koppeling, geldt op 2 van 2 plekken, niets verdrongen.
    assert len(voor) == 1 and voor[0]["herkomst"] == "grof"
    assert voor[0]["functie_id"] == toezicht
    assert voor[0]["grof_totaal_plekken"] == 2 and voor[0]["grof_geldt_op"] == 2
    assert voor[0]["verdrongen_op"] == 0
    # Ná verfijnen elders: het grove van Handhaving geldt nog op 1 van 2 én is op 1 plek verdrongen.
    g = na_handh[0]
    assert g["herkomst"] == "grof" and g["grof_geldt_op"] == 1 and g["verdrongen_op"] == 1
    # De inspectie-app leest als een FIJNE koppeling op de plek (Toezicht onder Milieu).
    assert len(na_insp) == 1 and na_insp[0]["herkomst"] == "fijn"
    assert na_insp[0]["functie_id"] == toezicht and na_insp[0]["ouder_functie_id"] == milieu


@integratie
def test_werkvoorraad_gat_filter_en_badge_live():
    """"Nog geen bedrijfsfunctie": alleen werk-ondersteunende systemen zonder koppeling; een
    database (geen werk) is nooit een gat; koppelen laat het gat verdwijnen — zichtbaar in het
    signaal, de lijstfilter én de per-component badge."""
    from services import component_service as cs
    from services import functievervulling_service as fvs
    from services import registratiegaten_service as rgs

    async def _flow(s):
        ids = []
        try:
            los = await _maak_component(s, "G4 Los systeem", "applicatie")   # werk, ongekoppeld → gat
            db = await _maak_component(s, "G4 Losse database", "database")   # geen werk → nooit gat
            ids += [los, db]
            functie = await _maak_functie(s, "G4 Vergunningverlening")
            ids.append(functie)

            gat_ids_voor = {r["id"] for r in await rgs.component_zonder_bedrijfsfunctie(s, _TID)}
            filter_ids_voor, _ = await cs.lijst(s, _TID, limit=100, zonder_bedrijfsfunctie=True)
            badge_los_voor = await rgs.badge_voor_component(s, _TID, los)
            badge_db = await rgs.badge_voor_component(s, _TID, db)

            await fvs.maak_aan(s, _TID, los, functie, None)  # koppel het losse systeem
            gat_ids_na = {r["id"] for r in await rgs.component_zonder_bedrijfsfunctie(s, _TID)}
            filter_ids_na, _ = await cs.lijst(s, _TID, limit=100, zonder_bedrijfsfunctie=True)
            badge_los_na = await rgs.badge_voor_component(s, _TID, los)
            return (los, db, gat_ids_voor, gat_ids_na,
                    {c["id"] for c in filter_ids_voor}, {c["id"] for c in filter_ids_na},
                    badge_los_voor, badge_db, badge_los_na)
        finally:
            await _ruim(s, ids)

    (los, db, gat_voor, gat_na, filt_voor, filt_na,
     badge_los_voor, badge_db, badge_los_na) = asyncio.run(_run_rls("test:bert", _flow))
    # Vóór koppelen: het losse werk-systeem is een gat; de database niet.
    assert los in gat_voor and db not in gat_voor
    assert los in filt_voor and db not in filt_voor
    assert "component_zonder_bedrijfsfunctie" in badge_los_voor["signalen"]
    assert "component_zonder_bedrijfsfunctie" not in badge_db["signalen"]
    # Ná koppelen: het gat is weg — overal (één afleiding).
    assert los not in gat_na and los not in filt_na
    assert "component_zonder_bedrijfsfunctie" not in badge_los_na["signalen"]
