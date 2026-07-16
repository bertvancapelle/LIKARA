"""Tests — Landschapskaart bedrijfsfunctie-PLEK-projectie (ADR-043 gate 4, slice 2, read-only).

De proceslaan is in slice 2 VERVANGEN door de bedrijfsfunctie-laan van plekken (ADR-043 G1); dit
bestand toetst die nieuwe projectie.

Offline: de projectie leest UITSLUITEND de gedeelde leesregel (`dekking_overzicht`/`plek_standen`)
en bevat GÉÉN ruwe koppelregel-query (de invariant, ADR-049 besluit 5); de proces-projectie is weg.
Live (skip-if-no-DB): path-expansie (een functie/voorouder op meerdere plekken → per pad een eigen
plek-knoop), consistente gap over herhalingen (G7 hard-grens 1), verdringing (een verdrongen
antwoord wordt NOOIT als "gedekt" getekend), en scope-volgt-selectie.
De engine-import-afwezigheid + read-only-bronscan zijn module-breed geborgd in `test_landschapskaart.py`.
"""
import asyncio
import inspect
import uuid

import pytest

import app.core.audit  # noqa: F401  (audit-capture-hook actief bij live ORM-mutaties)
import app.core.database  # noqa: F401
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline: de invariant + de swap ────────────────────────────────────────────────

def test_functie_laan_leest_de_leeslaag_en_niet_ruw():
    """De kaart-projectie leest de gedeelde leesregel (fijn verdringt grof) en bouwt de resolutie
    NIET zelf na met een ruwe functievervulling-query. Bronscan op de servicebron."""
    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    # Leest de gedeelde afleiding…
    assert "functievervulling_service.dekking_overzicht(" in bron
    assert "functievervulling_service.plek_standen(" in bron
    # …en bevat GÉÉN eigen rauwe functievervulling-select (dat zou de verdringing missen).
    assert "select(Functievervulling" not in bron
    assert "import Functievervulling" not in bron


def test_bedrijfsfunctie_laan_vervangt_de_proceslaan():
    """De laan tekent bedrijfsfunctie-plekken (ring 'bedrijfsfuncties'); de proceslaan is weg."""
    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    assert 'ring="bedrijfsfuncties"' in bron
    assert 'element_type="bedrijfsfunctie"' in bron
    assert 'relatietype="functievervulling"' in bron   # systeem → plek
    assert 'relatietype="functie_plaatsing"' in bron    # plek-hiërarchie
    # De proceslaan is niet meer getekend (backend-endpoints blijven slapend — G10, slice 3).
    assert 'ring="processen"' not in bron
    assert 'element_type="proces"' not in bron
    assert 'relatietype="procesvervulling"' not in bron


def test_node_draagt_plek_stand_en_functie_id():
    from schemas.landschapskaart import LandschapsNode

    assert {"plek_stand", "functie_id"} <= set(LandschapsNode.model_fields)
    n = LandschapsNode(id=uuid.uuid4(), naam="X", element_type="applicatie")
    assert n.plek_stand is None and n.functie_id is None  # additief, default leeg


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _probe():
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
    from app.core.tenant_context import reset_audit_context, zet_audit_context
    atok = zet_audit_context("test:bert", "test@bert")
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_audit_context(atok)
        reset_tenant_context(tok)
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


async def _maak_plek(s, ouder_id, kind_id):
    from models.models import Relatie

    s.add(Relatie(tenant_id=uuid.UUID(_TID), bron_id=ouder_id, doel_id=kind_id,
                  relatietype="aggregation", kenmerken={}))
    await s.commit()


async def _ruim(s, ids):
    from sqlalchemy import text as _t

    for eid in reversed(ids):
        await s.execute(_t("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    await s.commit()


def _bf_nodes(graf):
    return [n for n in graf.nodes if n.element_type == "bedrijfsfunctie"]


@integratie
def test_functie_op_meerdere_plekken_verschijnt_per_plek_live():
    """G7 — een functie onder twee ouders verschijnt als TWEE plek-knopen (distinct id), elk met
    een systeem→plek-edge; plus de plek-hiërarchie-edges. Geen proces-knopen meer."""
    from services import functievervulling_service as fvs
    from services import landschapskaart_service as svc

    async def _flow(s):
        ids = []
        try:
            app = await _maak_component(s, "S2 App", "applicatie")
            ids.append(app)
            d1 = await _maak_functie(s, "S2 Domein1")
            d2 = await _maak_functie(s, "S2 Domein2")
            f = await _maak_functie(s, "S2 Toezicht")
            ids += [d1, d2, f]
            await _maak_plek(s, d1, f)
            await _maak_plek(s, d2, f)
            await fvs.maak_aan(s, _TID, app, f, None)  # grof — geldt op elke plek van F
            graf = await svc.haal_grafdata_op(s, _TID, component_ids=[app])
            return graf, app, d1, d2, f
        finally:
            await _ruim(s, ids)

    graf, app, d1, d2, f = asyncio.run(_run_rls(_flow))
    # Geen proceslaan meer.
    assert not [n for n in graf.nodes if n.element_type == "proces"]
    # F verschijnt als TWEE distinct plek-knopen (onder D1 en onder D2).
    f_nodes = [n for n in _bf_nodes(graf) if n.functie_id == f]
    assert len(f_nodes) == 2
    assert len({n.id for n in f_nodes}) == 2
    # De app is gekoppeld maar draagt (in deze opzet) geen gebruikersgroep → 'werkvoorraad'
    # (systeem bekend, gebruiker nog niet — ADR-043 gate 4 brok 1).
    assert all(n.naam == "S2 Toezicht" and n.plek_stand == "werkvoorraad" for n in f_nodes)
    # Elk F-plek-knoop draagt een systeem→plek-edge van de app.
    vv = {e.doel_id for e in graf.edges if e.relatietype == "functievervulling" and e.bron_id == app}
    assert {n.id for n in f_nodes} <= vv
    # De domeinen zijn wortel-plekken (stand 'gat' — geen eigen systeem) met plek-hiërarchie-edges.
    plaats = {(e.bron_id, e.doel_id) for e in graf.edges if e.relatietype == "functie_plaatsing"}
    assert len(plaats) == 2  # F→D1, F→D2 (in plek-id-vorm)
    dom_nodes = [n for n in _bf_nodes(graf) if n.functie_id in (d1, d2)]
    assert len(dom_nodes) == 2 and all(n.plek_stand == "gat" for n in dom_nodes)


@integratie
def test_meervoudige_voorouder_herhaalt_plek_met_gelijke_cue_live():
    """G7 hard-grens 1 — staat een VOOROUDER op meerdere plekken, dan herhaalt de onderliggende
    plek per voorouder-tak; alle exemplaren dragen DEZELFDE stand (één plek-waarheid)."""
    from services import functievervulling_service as fvs
    from services import landschapskaart_service as svc

    async def _flow(s):
        ids = []
        try:
            app = await _maak_component(s, "S2b App", "applicatie")
            ids.append(app)
            gp1 = await _maak_functie(s, "S2b GP1")
            gp2 = await _maak_functie(s, "S2b GP2")
            p = await _maak_functie(s, "S2b P")
            f = await _maak_functie(s, "S2b F")
            ids += [gp1, gp2, p, f]
            await _maak_plek(s, gp1, p)
            await _maak_plek(s, gp2, p)
            await _maak_plek(s, p, f)
            await fvs.maak_aan(s, _TID, app, f, None)  # grof op F
            graf = await svc.haal_grafdata_op(s, _TID, component_ids=[app])
            return graf, f
        finally:
            await _ruim(s, ids)

    graf, f = asyncio.run(_run_rls(_flow))
    f_nodes = [n for n in _bf_nodes(graf) if n.functie_id == f]
    # F-onder-P herhaalt zich per grootouder-tak (twee paden gp1>P>F en gp2>P>F).
    assert len(f_nodes) == 2
    # Alle exemplaren dragen dezelfde stand — de kaart spreekt zichzelf niet tegen.
    assert len({n.plek_stand for n in f_nodes}) == 1


@integratie
def test_verdrongen_plek_toont_niet_vals_gedekt_live():
    """De invariant — op een plek waar een fijn antwoord het grove verdringt, tekent de kaart de
    edge van het FIJNE systeem, nooit van het verdrongen grove (de verdringing komt uit de leeslaag)."""
    from services import functievervulling_service as fvs
    from services import landschapskaart_service as svc

    async def _flow(s):
        ids = []
        try:
            a = await _maak_component(s, "S2c A (grof)", "applicatie")
            b = await _maak_component(s, "S2c B (fijn)", "applicatie")
            ids += [a, b]
            p = await _maak_functie(s, "S2c P")
            f = await _maak_functie(s, "S2c F")
            ids += [p, f]
            await _maak_plek(s, p, f)
            await fvs.maak_aan(s, _TID, a, f, None)   # grof A op F
            await fvs.maak_aan(s, _TID, b, f, p)      # fijn B op plek (F onder P) → verdringt A hier
            graf = await svc.haal_grafdata_op(s, _TID, component_ids=[a, b])
            return graf, a, b, f
        finally:
            await _ruim(s, ids)

    graf, a, b, f = asyncio.run(_run_rls(_flow))
    f_nodes = {n.id for n in _bf_nodes(graf) if n.functie_id == f}
    assert f_nodes
    # De edge naar de F-plek komt van B (het fijne antwoord); A is verdrongen en tekent NIET.
    naar_f = [e for e in graf.edges if e.relatietype == "functievervulling" and e.doel_id in f_nodes]
    bronnen = {e.bron_id for e in naar_f}
    assert b in bronnen and a not in bronnen


@integratie
def test_scope_volgt_selectie_live():
    """Scope-keuze A — de laan toont alleen plekken van functies die een IN-BEELD component draagt;
    een functie die alleen door een buiten-beeld-component gedragen wordt, komt niet mee."""
    from services import functievervulling_service as fvs
    from services import landschapskaart_service as svc

    async def _flow(s):
        ids = []
        try:
            app = await _maak_component(s, "S2d App", "applicatie")
            ander = await _maak_component(s, "S2d Ander", "applicatie")
            ids += [app, ander]
            f = await _maak_functie(s, "S2d F")
            g = await _maak_functie(s, "S2d G")
            ids += [f, g]
            await fvs.maak_aan(s, _TID, app, f, None)
            await fvs.maak_aan(s, _TID, ander, g, None)
            sub = await svc.haal_grafdata_op(s, _TID, component_ids=[app])  # alleen 'app' in beeld
            return sub, f, g
        finally:
            await _ruim(s, ids)

    sub, f, g = asyncio.run(_run_rls(_flow))
    functie_ids = {n.functie_id for n in _bf_nodes(sub)}
    assert f in functie_ids       # de functie van de in-beeld app
    assert g not in functie_ids   # de functie van de buiten-beeld app komt niet mee
