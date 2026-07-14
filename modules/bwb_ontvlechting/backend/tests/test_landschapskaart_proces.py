"""Tests — Landschapskaart proces-projectie (LI036 slice 2 → LI037 fase 1, read-only).

Offline: additief schema (herkomst) + de subboom-projectie zit in de servicebron (ring 'processen',
hiërarchie-edges, subboom-verwijzing). Live (skip-if-no-DB): deelprocessen als eerste-klas knopen
(de VOLLEDIGE subboom onder de geraakte wortel, incl. de ondersteuningsloze schakel), vervult-edges
op het GEREGISTREERDE (deel)proces (geen wortel-dubbeling), hiërarchie-edges kind→ouder,
selectie-schaal (een niet-geraakte boom komt niet mee), cyclus-veiligheid, en de bestaande
node-/edge-set + engine ongemoeid.
De engine-import-afwezigheid + read-only-bronscan voor deze service zijn module-breed geborgd in
`test_landschapskaart.py` en dekken dit blok automatisch mee.
"""
import asyncio
import uuid

import pytest

import app.core.audit  # noqa: F401  (audit-capture-hook actief bij live ORM-mutaties)
import app.core.database  # noqa: F401
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline ──────────────────────────────────────────────────────────────────────
def test_landschaps_edge_herkomst_veld_additief():
    """LI036 slice 2 — `herkomst` is additief + nullable (bestaande edges dragen None)."""
    from schemas.landschapskaart import LandschapsEdge, ProcesHerkomstItem

    assert "herkomst" in LandschapsEdge.model_fields
    e = LandschapsEdge(bron_id=uuid.uuid4(), doel_id=uuid.uuid4(), relatietype="flow",
                       label="koppeling", ring="applicaties")
    assert e.herkomst is None  # default: geen herkomst (niet-proces-edges ongewijzigd)
    item = ProcesHerkomstItem(proces_id=uuid.uuid4(), proces_naam="Deel", applicatiefunctie_label="Registreren")
    assert item.proces_naam == "Deel"


def test_landschapskaart_serveert_processen_ring():
    """De service projecteert de subboom-verrijkte proces-projectie (ring 'processen'):
    eerste-klas proces-knopen, hiërarchie-edges én vervult-edges op het geregistreerde proces."""
    import inspect

    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    assert 'ring="processen"' in bron
    assert 'relatietype="procesvervulling"' in bron
    assert 'relatietype="proces_hierarchie"' in bron  # LI037 fase 1 — de boomlijnen
    assert 'element_type="proces"' in bron
    # Eén roll-up-definitie: het blok verwijst expliciet naar de rollup-/subboom-semantiek
    # (zelfde bron als de proces-leespaden — nooit een tweede boom-definitie).
    assert "rollup_voor_proces" in bron
    assert "subboom" in bron


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────
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


def _maak_proces(s, tid, naam, ouder_id=None):
    from models.models import Element, ElementType, Proces

    async def _do():
        pe = Element(tenant_id=tid, element_type=ElementType.proces)
        s.add(pe)
        await s.flush()
        s.add(Proces(id=pe.id, tenant_id=tid, naam=naam, ouder_id=ouder_id))
        await s.flush()
        return pe.id

    return _do()


@integratie
def test_proces_projectie_subboom_eerste_klas_live():
    """LI037 fase 1 — (a) deelprocessen als eerste-klas knopen: de VOLLEDIGE subboom onder de
    geraakte wortel komt mee, incl. de ondersteuningsloze schakel; (b) vervult-edges landen op het
    GEREGISTREERDE (deel)proces (geen wortel-dubbeling); (c) hiërarchie-edges kind→ouder; (d) een
    niet-geraakte boom komt niet mee (selectie-schaal) en een component zonder vervulling krijgt
    niets; (e) de bestaande node-/edge-set en de engine blijven ongemoeid."""
    from sqlalchemy import text as _text

    from models.models import Procesvervulling
    from schemas.component import ComponentCreate
    from services import component_service, landschapskaart_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            app = await component_service.maak_aan(
                s, tid, ComponentCreate(componenttype="applicatie",
                    naam="WT-PL-App", hostingmodel="saas", migratiepad=None,
                    complexiteit="midden", prioriteit="midden"))
            los = await component_service.maak_aan(s, tid, ComponentCreate(naam="WT-PL-Los", componenttype="database"))
            app_id, los_id = app["id"], los["id"]
            ids += [app_id, los_id]

            # Geraakte boom: hoofd → deel → subdeel (3 niveaus) + een ONDERSTEUNINGSLOZE tak
            # (kaal, onder hoofd — geen vervulling; moet tóch als knoop meekomen).
            hoofd = await _maak_proces(s, tid, "WT-PL-Hoofd")
            deel = await _maak_proces(s, tid, "WT-PL-Deel", ouder_id=hoofd)
            subdeel = await _maak_proces(s, tid, "WT-PL-Subdeel", ouder_id=deel)
            kaal = await _maak_proces(s, tid, "WT-PL-Kaal", ouder_id=hoofd)
            # NIET-geraakte boom (geen enkele vervulling): mag niet meekomen (selectie-schaal).
            ander = await _maak_proces(s, tid, "WT-PL-Ander")
            ander_deel = await _maak_proces(s, tid, "WT-PL-AnderDeel", ouder_id=ander)
            ids += [hoofd, deel, subdeel, kaal, ander, ander_deel]
            await s.commit()

            # Baseline vóór de vervullingen + engine-telling.
            graf0 = await svc.haal_grafdata_op(s, _TID)
            profielen0 = (await s.execute(_text("SELECT count(*) FROM component_profiel"))).scalar_one()

            # Vervul-regels van dezelfde component op TWEE dieptes (subdeel + deel).
            s.add(Procesvervulling(tenant_id=tid, component_id=app_id, proces_id=subdeel, applicatiefunctie="registreren"))
            s.add(Procesvervulling(tenant_id=tid, component_id=app_id, proces_id=deel, applicatiefunctie="raadplegen"))
            await s.commit()

            graf1 = await svc.haal_grafdata_op(s, _TID)
            sub = await svc.haal_grafdata_op(s, _TID, component_ids=[app_id])
            profielen1 = (await s.execute(_text("SELECT count(*) FROM component_profiel"))).scalar_one()
            return (graf0, graf1, sub, app_id, los_id,
                    hoofd, deel, subdeel, kaal, ander, ander_deel, profielen0, profielen1)
        finally:
            # Self-FK op proces is RESTRICT → leaf→root wissen (kinderen zijn ná hun ouder aangemaakt).
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    (graf0, graf1, sub, app_id, los_id,
     hoofd, deel, subdeel, kaal, ander, ander_deel, prof0, prof1) = asyncio.run(_run_rls(_flow))

    eigen = {hoofd, deel, subdeel, kaal}

    # Vóór de vervullingen: géén proces-nodes voor onze bomen (verrijking alleen bij koppeling).
    ids0 = {n.id for n in graf0.nodes}
    assert not (eigen | {ander, ander_deel}) & ids0

    # (a) Ná de vervullingen: de HELE geraakte subboom als knopen — incl. de ondersteuningsloze
    # schakel (kaal) — met typing; (d) de niet-geraakte boom blijft buiten beeld.
    proces_nodes = {n.id: n for n in graf1.nodes if n.element_type == "proces"}
    assert eigen <= set(proces_nodes)
    assert ander not in proces_nodes and ander_deel not in proces_nodes
    assert proces_nodes[hoofd].naam == "WT-PL-Hoofd"
    for pid in eigen:
        assert proces_nodes[pid].laag == "business"
        assert proces_nodes[pid].archimate_element == "business_process"

    # (c) Hiërarchie-edges kind→ouder binnen de subboom (de wortel draagt er zelf geen);
    # allemaal in ring 'processen' met label "onderdeel van" (besluit 3: alles togglet samen).
    hier_edges = [x for x in graf1.edges if x.relatietype == "proces_hierarchie"]
    hier = {(x.bron_id, x.doel_id) for x in hier_edges}
    assert {(deel, hoofd), (subdeel, deel), (kaal, hoofd)} <= hier
    assert all(x.ring == "processen" and x.label == "onderdeel van" for x in hier_edges)
    assert not any(b == hoofd for (b, _d) in hier)  # wortel zonder eigen hiërarchie-edge

    # (b) Vervult-edges op het GEREGISTREERDE (deel)proces — twee losse lijnen (subdeel + deel),
    # elk aantal=1 met het functie-label; GEEN edge naar de wortel (geen dubbeling).
    pv_edges = {e.doel_id: e for e in graf1.edges
                if e.relatietype == "procesvervulling" and e.bron_id == app_id}
    assert set(pv_edges) == {subdeel, deel}
    for e in pv_edges.values():
        assert e.ring == "processen" and e.aantal == 1
        assert e.label and e.label != "vervult"  # één functie → functie-label op de lijn
        assert len(e.herkomst) == 1 and e.herkomst[0].applicatiefunctie_label
    assert pv_edges[subdeel].herkomst[0].proces_naam == "WT-PL-Subdeel"

    # (d) De losse component draagt géén procesvervulling-edge.
    assert not any(x.relatietype == "procesvervulling" and x.bron_id == los_id for x in graf1.edges)

    # Subgraaf-variant (set = de app): zelfde subboom-projectie werkt set-scoped.
    sub_proces = {n.id for n in sub.nodes if n.element_type == "proces"}
    assert eigen <= sub_proces and ander not in sub_proces
    assert any(x.relatietype == "procesvervulling" and x.bron_id == app_id for x in sub.edges)
    assert any(x.relatietype == "proces_hierarchie" for x in sub.edges)

    # (e) De bestaande node-/edge-set is ongemoeid: zónder onze proces-toevoegingen is graf1 = graf0.
    assert {n.id for n in graf1.nodes} - eigen == ids0
    sig = lambda edges: sorted(  # noqa: E731
        (str(x.bron_id), str(x.doel_id), x.ring) for x in edges
        if not (x.ring == "processen" and (x.bron_id in ({app_id} | eigen) or x.doel_id in eigen)))
    assert sig(graf1.edges) == sig(graf0.edges)

    # Engine onaangeroerd: de projectie maakt/muteert geen profielen; lifecycle blijft leesbaar 'concept'.
    assert prof0 == prof1
    app_node = {n.id: n for n in graf1.nodes}[app_id]
    assert app_node.lifecycle_status == "concept"


@integratie
def test_proces_projectie_cyclus_veilig_live():
    """(c) Een (via direct SQL geconstrueerde) ouder-lus mag de projectie nooit laten hangen:
    de klim eindigt deterministisch op een pseudo-wortel, en ook de subboom-afdaling termineert
    (visited-set) — beide lus-leden verschijnen als knoop, zonder edge-lus vanaf de pseudo-wortel."""
    from sqlalchemy import text as _text

    from models.models import Procesvervulling
    from schemas.component import ComponentCreate
    from services import component_service, landschapskaart_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            comp = await component_service.maak_aan(s, tid, ComponentCreate(naam="WT-PL-CycComp", componenttype="database"))
            comp_id = comp["id"]
            ids.append(comp_id)
            p1 = await _maak_proces(s, tid, "WT-PL-Cyc1")
            p2 = await _maak_proces(s, tid, "WT-PL-Cyc2", ouder_id=p1)
            ids += [p1, p2]
            # Lus construeren buiten de service-validatie om (de service weigert kringen; B3 staat
            # cycli in de DATA toe — de traversal moet er tegen kunnen).
            await s.execute(_text("UPDATE proces SET ouder_id=:o WHERE id=:i"), {"o": str(p2), "i": str(p1)})
            s.add(Procesvervulling(tenant_id=tid, component_id=comp_id, proces_id=p2, applicatiefunctie="registreren"))
            await s.commit()

            graf = await svc.haal_grafdata_op(s, _TID)
            return graf, comp_id, p1, p2
        finally:
            # Eerst de kring breken (wederzijdse RESTRICT-verwijzing), dan leaf→root wissen.
            await s.execute(_text("UPDATE proces SET ouder_id=NULL WHERE naam LIKE 'WT-PL-Cyc%'"))
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    graf, comp_id, p1, p2 = asyncio.run(_run_rls(_flow))

    # De projectie is geëindigd (geen hang); de subboom-afdaling levert beide lus-leden als knoop
    # (LI037: de pseudo-wortel + zijn "kind" — eerste-klas, deterministisch).
    proces_nodes = [n for n in graf.nodes if n.element_type == "proces" and n.id in {p1, p2}]
    assert len(proces_nodes) == 2
    # De vervult-edge landt op het GEREGISTREERDE proces (p2).
    edge = [e for e in graf.edges if e.relatietype == "procesvervulling" and e.bron_id == comp_id]
    assert len(edge) == 1 and edge[0].doel_id == p2 and edge[0].aantal == 1
    # Eén functie → het applicatiefunctie-label op de lijn (niet het generieke 'vervult').
    assert edge[0].label and edge[0].label != "vervult"
    # Precies ÉÉN hiërarchie-edge binnen de lus (de pseudo-wortel draagt er zelf geen → geen
    # edge-lus; de boom blijft tekenbaar).
    hier = [x for x in graf.edges if x.relatietype == "proces_hierarchie"
            and {x.bron_id, x.doel_id} <= {p1, p2}]
    assert len(hier) == 1
