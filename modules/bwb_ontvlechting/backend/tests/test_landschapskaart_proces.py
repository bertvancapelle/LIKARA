"""Tests — Landschapskaart proces-projectie (LI036 slice 2 · stap 1, read-only).

Offline: additief schema (herkomst) + de projectie zit in de servicebron (ring 'processen').
Live (skip-if-no-DB): bottom-up doorrol naar het HOOFDproces (ook bij een koppeling op een diep
deelproces), samentrekking per (component, hoofdproces) met `aantal`+`herkomst`, cyclus-veiligheid,
geen proces-nodes zonder vervulling, en de bestaande node-/edge-set + engine ongemoeid.
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
    """De service projecteert hoofdprocessen + doorgerolde vervul-edges (ring 'processen')."""
    import inspect

    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    assert 'ring="processen"' in bron
    assert 'relatietype="procesvervulling"' in bron
    assert 'element_type="proces"' in bron
    # Eén roll-up-definitie: het blok verwijst expliciet naar de rollup-semantiek (zelfde bron).
    assert "rollup_voor_proces" in bron


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
def test_proces_projectie_rolt_door_naar_hoofdproces_live():
    """(a)+(b)+(d)+(e): koppeling op een diep deelproces → HOOFDproces-node + één samengetrokken
    edge (aantal=2, herkomst uitgesplitst); component zonder vervulling krijgt niets; de bestaande
    node-/edge-set en de engine blijven ongemoeid."""
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
                    naam="WT-PL-App", hostingmodel="saas", migratiepad="onbekend",
                    complexiteit="midden", prioriteit="midden"))
            los = await component_service.maak_aan(s, tid, ComponentCreate(naam="WT-PL-Los", componenttype="database"))
            app_id, los_id = app["id"], los["id"]
            ids += [app_id, los_id]

            # Procesboom: hoofd → deel → subdeel (drie niveaus — de klim moet twee stappen maken).
            hoofd = await _maak_proces(s, tid, "WT-PL-Hoofd")
            deel = await _maak_proces(s, tid, "WT-PL-Deel", ouder_id=hoofd)
            subdeel = await _maak_proces(s, tid, "WT-PL-Subdeel", ouder_id=deel)
            ids += [hoofd, deel, subdeel]
            await s.commit()

            # Baseline vóór de vervullingen + engine-telling.
            graf0 = await svc.haal_grafdata_op(s, _TID)
            profielen0 = (await s.execute(_text("SELECT count(*) FROM component_profiel"))).scalar_one()

            # (b) Twee vervul-regels van dezelfde component, op verschillende dieptes/functies.
            s.add(Procesvervulling(tenant_id=tid, component_id=app_id, proces_id=subdeel, applicatiefunctie="registreren"))
            s.add(Procesvervulling(tenant_id=tid, component_id=app_id, proces_id=deel, applicatiefunctie="raadplegen"))
            await s.commit()

            graf1 = await svc.haal_grafdata_op(s, _TID)
            sub = await svc.haal_grafdata_op(s, _TID, component_ids=[app_id])
            profielen1 = (await s.execute(_text("SELECT count(*) FROM component_profiel"))).scalar_one()
            return graf0, graf1, sub, app_id, los_id, hoofd, deel, subdeel, profielen0, profielen1
        finally:
            # Self-FK op proces is RESTRICT → leaf→root wissen (kinderen zijn ná hun ouder aangemaakt).
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    graf0, graf1, sub, app_id, los_id, hoofd, deel, subdeel, prof0, prof1 = asyncio.run(_run_rls(_flow))

    # (d) Vóór de vervullingen: géén proces-nodes voor onze boom (verrijking alleen bij koppeling).
    ids0 = {n.id for n in graf0.nodes}
    assert hoofd not in ids0 and deel not in ids0 and subdeel not in ids0

    # (a) Ná de vervullingen: ALLEEN het hoofdproces als node (deel/subdeel niet), met typing.
    proces_nodes = {n.id: n for n in graf1.nodes if n.element_type == "proces"}
    assert hoofd in proces_nodes and deel not in proces_nodes and subdeel not in proces_nodes
    assert proces_nodes[hoofd].naam == "WT-PL-Hoofd"
    assert proces_nodes[hoofd].laag == "business"
    assert proces_nodes[hoofd].archimate_element == "business_process"

    # (b) Eén samengetrokken edge component→hoofdproces: aantal=2, gemengde functies → label 'vervult',
    # herkomst uitgesplitst (deelproces-namen + functie-labels). Self-contained (LI021): asserteer
    # uitsluitend op de EIGEN fixtures — de dev-DB draagt ook geseede vervullingen.
    pv_edges = [e for e in graf1.edges if e.ring == "processen" and e.bron_id == app_id]
    assert len(pv_edges) == 1
    e = pv_edges[0]
    assert e.doel_id == hoofd
    assert e.relatietype == "procesvervulling" and e.aantal == 2 and e.label == "vervult"
    assert {h.proces_naam for h in e.herkomst} == {"WT-PL-Deel", "WT-PL-Subdeel"}
    assert all(h.applicatiefunctie_label for h in e.herkomst)

    # (d) De losse component draagt géén procesvervulling-edge.
    assert not any(x.ring == "processen" and x.bron_id == los_id for x in graf1.edges)

    # Subgraaf-variant (set = de app): zelfde projectie werkt set-scoped.
    assert hoofd in {n.id for n in sub.nodes if n.element_type == "proces"}
    assert any(x.ring == "processen" and x.bron_id == app_id for x in sub.edges)

    # (e) De bestaande node-/edge-set is ongemoeid: zónder onze proces-toevoeging is graf1 = graf0
    # (incl. eventuele geseede proces-nodes/-edges, die in beide calls identiek meekomen).
    assert {n.id for n in graf1.nodes} - {hoofd} == ids0
    sig = lambda edges: sorted(  # noqa: E731
        (str(x.bron_id), str(x.doel_id), x.ring) for x in edges
        if not (x.ring == "processen" and x.bron_id == app_id))
    assert sig(graf1.edges) == sig(graf0.edges)

    # Engine onaangeroerd: de projectie maakt/muteert geen profielen; lifecycle blijft leesbaar 'concept'.
    assert prof0 == prof1
    app_node = {n.id: n for n in graf1.nodes}[app_id]
    assert app_node.lifecycle_status == "concept"


@integratie
def test_proces_projectie_cyclus_veilig_live():
    """(c) Een (via direct SQL geconstrueerde) ouder-lus mag de projectie nooit laten hangen:
    de klim eindigt deterministisch op een pseudo-wortel binnen de lus."""
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

    # De projectie is geëindigd (geen hang) en levert precies één pseudo-wortel uit de lus.
    proces_nodes = [n for n in graf.nodes if n.element_type == "proces" and n.id in {p1, p2}]
    assert len(proces_nodes) == 1
    edge = [e for e in graf.edges if e.ring == "processen" and e.bron_id == comp_id]
    assert len(edge) == 1 and edge[0].aantal == 1
    # Eén functie → het applicatiefunctie-label op de lijn (niet het generieke 'vervult').
    assert edge[0].label and edge[0].label != "vervult"
