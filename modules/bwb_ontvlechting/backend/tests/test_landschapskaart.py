"""Tests — Landschapskaart (ADR-025, read-only grafprojectie).

Offline: engine-import-afwezigheid + RBAC (ARCHITECTUUR.LEZEN, alleen-lezen).
Live (skip-if-no-DB): de volledige graaf met de vier ring-edge-types + lifecycle op een
applicatie-node, met structurele opruim.
"""
import asyncio
import uuid

import pytest

import app.core.audit  # noqa: F401
import app.core.database  # noqa: F401
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline: engine onaangeroerd ─────────────────────────────────────────────────
def test_landschapskaart_service_raakt_engine_niet():
    import services.landschapskaart_service as s

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(s, naam), f"landschapskaart_service mag de engine niet importeren: {naam!r}"


def test_landschapsnode_heeft_v3_velden():
    """ADR-025 v3 — de node-verrijking (domein/leverancier/hosting/blokkades) zit in het schema."""
    from schemas.landschapskaart import LandschapsNode

    velden = LandschapsNode.model_fields
    for veld in ("domein", "leverancier_naam", "leverancier_id", "hosting_model", "blokkades_open"):
        assert veld in velden, f"LandschapsNode mist het v3-veld {veld!r}"
    # blokkades_open is een int met default 0 (geen open blokkades → 0).
    n = LandschapsNode(id=uuid.uuid4(), naam="X", element_type="applicatie")
    assert n.blokkades_open == 0 and n.hosting_model is None


def test_landschaps_v4_velden_in_schema():
    """ADR-025 v4 — edge-koppelingsdetails + node-migratieplaatsing in het schema."""
    from schemas.landschapskaart import LandschapsEdge, LandschapsNode

    assert {"richting", "protocol"} <= set(LandschapsEdge.model_fields)
    assert {"plateau_naam", "plateau_dispositie"} <= set(LandschapsNode.model_fields)


def test_landschaps_adr031_velden_in_schema():
    """ADR-031 — gebruikersgroep-node-velden (organisatie_id + aantal_leden) in het schema."""
    from schemas.landschapskaart import LandschapsNode

    velden = LandschapsNode.model_fields
    assert {"organisatie_id", "aantal_leden"} <= set(velden)
    n = LandschapsNode(id=uuid.uuid4(), naam="X", element_type="gebruikersgroep")
    assert n.aantal_leden == 0 and n.organisatie_id is None


def test_landschaps_adr024_organisatie_scope_velden_in_schema():
    """ADR-024 organisatie-scope — bezit/gebruik-velden op de node + lege/None-defaults."""
    from schemas.landschapskaart import LandschapsNode

    velden = LandschapsNode.model_fields
    assert {"eigenaar_organisatie_id", "gebruikt_door_organisaties"} <= set(velden)
    # ADR-038 — `gebruikt_door_organisatieloos` is verwijderd (een groep heeft nu altijd een organisatie).
    assert "gebruikt_door_organisatieloos" not in velden
    n = LandschapsNode(id=uuid.uuid4(), naam="X", element_type="applicatie")
    assert n.eigenaar_organisatie_id is None  # zonder eigenaar herkenbaar
    assert n.gebruikt_door_organisaties == []


def test_landschapskaart_serveert_gebruikers_ring():
    """ADR-031 — de service projecteert gebruikersgroepen + de 'gebruikers'-serving-ring."""
    import inspect

    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    assert "ring=\"gebruikers\"" in bron and "Gebruikersgroep" in bron
    assert "gebruikt door" in bron


def test_landschapskaart_serveert_gebruikt_ring():
    """LI033b — de service projecteert het grove feit `organisatiegebruik` als 'gebruikt'-edge
    (organisatie → applicatie), spiegel van de eigenaar-edge; read-only, geen nieuwe relatie."""
    import inspect

    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    assert 'ring="gebruikt"' in bron and 'label="gebruikt"' in bron
    assert 'relatietype="gebruikt"' in bron
    # Dangling-guard: alleen als beide endpoints als knoop meekomen.
    assert "r_og.organisatie_id in partij_info and r_og.applicatie_id in comp_node" in bron


def test_landschapskaart_serveert_contract_leverancier_edge():
    """LI034 slice 3 — de service projecteert `contract.leverancier_id` als 'contracten'-ring-edge
    contract → leverancier ("geleverd door"), spiegel van de eigenaar-/gebruikt-edge; read-only, geen
    nieuwe relatie. Met P4-scope-add (leverancier-partij) én dangling-guard (beide endpoints als knoop)."""
    import inspect

    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    assert 'ring="contracten"' in bron and 'label="geleverd door"' in bron
    assert 'relatietype="leverancier"' in bron
    # Dangling-guard: alleen als contract én leverancier-partij als knoop meekomen.
    assert "r.id in contract_ids and r.leverancier_id in partij_info" in bron
    # P4 scope-add: de leverancier-partij van contracten-in-scope komt in de subgraaf-scope.
    assert "Contract.id.in_(scope_ids), Contract.leverancier_id.isnot(None)" in bron


def test_landschapskaart_serveert_samenstelling_ring():
    """ADR-033 1b — de service projecteert component↔component aggregatie als 'samenstelling'-edge,
    met een guard die plateau-lidmaatschap (bron=plateau) uitsluit (alleen-lezen, niets afgeleid)."""
    import inspect

    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    assert 'ring="samenstelling"' in bron and 'label="bestaat uit"' in bron
    # Guard: uitsluitend wanneer bron én doel componenten zijn → plateau-lidmaatschap valt buiten.
    assert 'rt == "aggregation" and r.bron_id in component_ids and r.doel_id in component_ids' in bron


def test_landschapskaart_serveert_organisatiestructuur_ring():
    """ADR-024 — de service projecteert de geregistreerde "hoort bij"-FK's (partij.organisatie_id/
    afdeling_id) als 'organisatiestructuur'-edge; alleen personen-met-rol, van onderaf, geen afleiding."""
    import inspect

    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    assert 'ring="organisatiestructuur"' in bron and 'label="hoort bij"' in bron
    # Afbakening: rol-vervulling = roltoewijzing-bron; alleen aard=persoon (van onderaf).
    assert "rol_partij_ids = {r.partij_id for r in rt_rijen}" in bron
    assert "info.aard != PartijAard.persoon" in bron


def test_landschapskaart_geen_schrijfpad_in_bron():
    """Read-only: de servicebron bevat geen schrijf-operaties op de sessie."""
    import inspect

    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    for verboden in ("session.add(", "session.commit(", "session.flush(", "session.delete("):
        assert verboden not in bron, f"read-only service mag geen {verboden!r} bevatten"


# ── Offline: RBAC (ARCHITECTUUR.LEZEN, alleen-lezen) ─────────────────────────────
def test_landschapskaart_rbac_alleen_lezen():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    for rol in ("viewer", "medewerker", "beheerder", "auditor"):
        assert heeft_permissie([rol], Entiteit.ARCHITECTUUR, Actie.LEZEN)
    # Een rol zonder enige tenant-rol heeft geen leesrecht → route zou 403 geven.
    assert not heeft_permissie([], Entiteit.ARCHITECTUUR, Actie.LEZEN)


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


@integratie
def test_landschapskaart_graf_vier_ringen_en_lifecycle_live():
    from sqlalchemy import text as _text

    from models.models import (
        Contract, ContractType, Element, ElementType, HostingModel, Migratiepad,
        NiveauEnum, Partij, PartijAard, PartijScope, Plateau, Relatie, RelatieKenmerkDimensie, Roltoewijzing,
    )
    from schemas.component import ComponentCreate
    from schemas.component import ComponentCreate
    from services import component_service, landschapskaart_service as svc
    from services import partij_service
    from services import relatiekenmerk_catalog as rk

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            # Applicatie (krijgt een profiel → lifecycle_status) + een database-component.
            app = await component_service.maak_aan(
                s, tid, ComponentCreate(componenttype="applicatie", 
                    naam="WT-LK-App", hostingmodel="saas", migratiepad="onbekend",
                    complexiteit="midden", prioriteit="midden"))
            comp = await component_service.maak_aan(s, tid, ComponentCreate(naam="WT-LK-DB", componenttype="database"))
            app_id, comp_id = app["id"], comp["id"]
            ids += [app_id, comp_id]

            # Organisatie-partij + contract (leverancier = de organisatie).
            oe = Element(tenant_id=tid, element_type=ElementType.partij); s.add(oe); await s.flush()
            s.add(Partij(id=oe.id, tenant_id=tid, aard=PartijAard.organisatie, naam="WT-LK-Org", scope=PartijScope.extern)); await s.flush()
            ce = Element(tenant_id=tid, element_type=ElementType.contract); s.add(ce); await s.flush()
            s.add(Contract(id=ce.id, tenant_id=tid, leverancier_id=oe.id,
                           contracttype=ContractType.los_contract, contractnaam="WT-LK-Contract"))
            await s.flush()

            # Plateau + aggregation-lidmaatschap (bron=plateau → doel=app) met dispositie.
            pe = Element(tenant_id=tid, element_type=ElementType.plateau); s.add(pe); await s.flush()
            s.add(Plateau(id=pe.id, tenant_id=tid, naam="WT-LK-Plateau")); await s.flush()

            # Vier ringen: flow (app→db, met kenmerken), assignment (db host→app), association
            # (app→contract), roltoewijzing (org→app) + aggregation (plateau→app).
            s.add(Relatie(tenant_id=tid, bron_id=app_id, doel_id=comp_id, relatietype="flow",
                          kenmerken={"richting": "eenrichting", "protocol": "rest"}))
            s.add(Relatie(tenant_id=tid, bron_id=comp_id, doel_id=app_id, relatietype="assignment"))
            s.add(Relatie(tenant_id=tid, bron_id=app_id, doel_id=ce.id, relatietype="association"))
            s.add(Relatie(tenant_id=tid, bron_id=pe.id, doel_id=app_id, relatietype="aggregation",
                          kenmerken={"dispositie": "migreren"}))
            rol = sorted(await rk.actieve_sleutels(s, RelatieKenmerkDimensie.beheerrol))[0]
            s.add(Roltoewijzing(tenant_id=tid, partij_id=oe.id, object_id=app_id, rol=rol))
            await s.commit()
            ids += [ce.id, oe.id, pe.id]

            graf = await svc.haal_grafdata_op(s, _TID)
            # `diepte` is server-side een no-op (volledige graaf; stap-diepte is client-side) —
            # diepte=2 levert dezelfde nodes als diepte=1.
            graf2 = await svc.haal_grafdata_op(s, _TID, diepte=2)
            assert len(graf2.nodes) == len(graf.nodes)
            # LI019 — componenten van de leverancier (oe) via de contract-keten (Taak 2).
            lev_comp = await partij_service.componenten_via_contracten(s, _TID, oe.id)
            return graf, app_id, comp_id, oe.id, ce.id, lev_comp
        finally:
            # Contract eerst (leverancier-RESTRICT), dan de rest.
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    graf, app_id, comp_id, org_id, contract_id, lev_comp = asyncio.run(_run_rls(_flow))

    node_per_id = {n.id: n for n in graf.nodes}
    # Nodes: applicatie met lifecycle, partij met soort, contract.
    assert node_per_id[app_id].element_type == "applicatie"
    assert node_per_id[app_id].lifecycle_status == "concept"   # uit component_profiel (read-only)
    # v3-verrijking op de applicatie-node: hosting (enum-waarde), domein-label, geen open blokkades.
    assert node_per_id[app_id].hosting_model == "saas"
    assert node_per_id[app_id].domein  # componenttype-label gevuld
    assert node_per_id[app_id].blokkades_open == 0
    # LI019 (Taak 3) — leverancier afgeleid via de contract-keten (geen directe roltoewijzing-
    # leverancier: oe is aard=organisatie, geen externe_partij) → node draagt tóch de leverancier.
    assert node_per_id[app_id].leverancier_id == org_id
    assert node_per_id[app_id].leverancier_naam == "WT-LK-Org"
    # LI019 (Taak 2) — componenten van de leverancier via contracten: de app via dit contract.
    assert any(c["component_id"] == app_id and c["contract_id"] == contract_id for c in lev_comp)
    # v4 — migratieplaatsing op de applicatie-node (eerste plateau via aggregation + dispositie-label).
    assert node_per_id[app_id].plateau_naam == "WT-LK-Plateau"
    assert node_per_id[app_id].plateau_dispositie == "Migreren"
    # v4 — koppelingsdetails op de flow-edge (uit kenmerken).
    flow = [e for e in graf.edges if e.ring == "applicaties" and e.bron_id == app_id and e.doel_id == comp_id]
    assert flow and flow[0].richting == "eenrichting" and flow[0].protocol == "rest"
    assert node_per_id[org_id].element_type == "partij" and node_per_id[org_id].soort == "organisatie"
    assert node_per_id[org_id].laag == "business"
    assert node_per_id[contract_id].element_type == "contract"

    # Alle vier de ringen aanwezig in de edges (beperkt tot onze testrelaties).
    mijn_ids = {app_id, comp_id, org_id, contract_id}
    ringen = {e.ring for e in graf.edges if e.bron_id in mijn_ids and e.doel_id in mijn_ids}
    assert {"applicaties", "infrastructuur", "contracten", "beheerorganisatie"} <= ringen
    # De beheerorganisatie-edge draagt de rol-naam als label.
    beheer = [e for e in graf.edges if e.ring == "beheerorganisatie" and e.bron_id == org_id]
    assert beheer and beheer[0].label


@integratie
def test_landschapskaart_contract_leverancier_edge_live():
    """LI034 slice 3 — afgeleide read-only edge contract → leverancier (ring 'contracten'):
    in de SUBGRAAF (gescoopt op de app) komt de leverancier-partij via de P4-scope-add mee en de edge
    wordt geëmit met leesbaar label. (NB: `contract.leverancier_id` is NOT NULL — elk contract heeft
    per schema een leverancier; de dangling-guard is een render-vangnet, geborgd via de bronscan.)"""
    from sqlalchemy import text as _text

    from models.models import (
        Contract, ContractType, Element, ElementType, Partij, PartijAard, PartijScope, Relatie,
    )
    from schemas.component import ComponentCreate
    from services import component_service, landschapskaart_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            app = await component_service.maak_aan(
                s, tid, ComponentCreate(componenttype="applicatie", naam="WT-CL-App", hostingmodel="saas",
                                        migratiepad="onbekend", complexiteit="midden", prioriteit="midden"))
            app_id = app["id"]; ids.append(app_id)
            # Leverancier-partij (externe_partij → géén org-balk-effect).
            le = Element(tenant_id=tid, element_type=ElementType.partij); s.add(le); await s.flush()
            s.add(Partij(id=le.id, tenant_id=tid, aard=PartijAard.externe_partij, naam="WT-CL-Lev",
                         scope=PartijScope.extern)); await s.flush()
            # Contract MÉT leverancier + association app→contract.
            ce = Element(tenant_id=tid, element_type=ElementType.contract); s.add(ce); await s.flush()
            s.add(Contract(id=ce.id, tenant_id=tid, leverancier_id=le.id,
                           contracttype=ContractType.los_contract, contractnaam="WT-CL-Con")); await s.flush()
            s.add(Relatie(tenant_id=tid, bron_id=app_id, doel_id=ce.id, relatietype="association"))
            await s.commit()
            # Verwijdervolgorde: contract vóór leverancier (contract.leverancier_id is RESTRICT).
            ids += [ce.id, le.id]
            # SUBGRAAF gescoopt op de app → dwingt de scope-add-tak af (leverancier zit NIET in S).
            graf = await svc.haal_grafdata_op(s, _TID, component_ids=[app_id])
            return graf, app_id, le.id, ce.id
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    graf, app_id, lev_id, con_id = asyncio.run(_run_rls(_flow))
    node_ids = {n.id for n in graf.nodes}
    # P4-scope-add: de leverancier-partij is als knoop meegekomen ondanks dat alleen de app in S zat.
    assert lev_id in node_ids, "scope-add: leverancier-partij hoort in de subgraaf-scope"
    assert con_id in node_ids
    # Afgeleide edge contract→leverancier (ring 'contracten', label 'geleverd door').
    lev_edges = [e for e in graf.edges if e.ring == "contracten" and e.relatietype == "leverancier"]
    assert any(e.bron_id == con_id and e.doel_id == lev_id and e.label == "geleverd door" for e in lev_edges)


@integratie
def test_landschapskaart_flows_gegroepeerd_per_paar_live():
    """ADR-023a Fase 3 — meerdere flows tussen hetzelfde gerichte paar worden tot één
    LandschapsEdge samengetrokken met `aantal=N`; gemengde richting → 'bidirectioneel',
    gemengd protocol → None; een enkele flow blijft `aantal=1` met eigen richting/protocol."""
    from sqlalchemy import text as _text

    from models.models import Component, Element, ElementType, Relatie
    from services import landschapskaart_service as svc

    tid = uuid.UUID(_TID)

    async def _comp(s, naam):
        elem = Element(tenant_id=tid, element_type=ElementType.component); s.add(elem); await s.flush()
        s.add(Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="integratievoorziening",
                        hostingmodel="on_premise")); await s.flush()
        return elem.id

    async def _flow(s):
        ids = []
        try:
            a = await _comp(s, "WT-GRP-A"); b = await _comp(s, "WT-GRP-B")
            ids += [a, b]
            # 3 flows a→b: 2× (eenrichting, rest) + 1× (tweerichting, soap) → niet-uniform.
            s.add(Relatie(tenant_id=tid, bron_id=a, doel_id=b, relatietype="flow", naam="g1",
                          kenmerken={"richting": "eenrichting", "protocol": "rest"}))
            s.add(Relatie(tenant_id=tid, bron_id=a, doel_id=b, relatietype="flow", naam="g2",
                          kenmerken={"richting": "eenrichting", "protocol": "rest"}))
            s.add(Relatie(tenant_id=tid, bron_id=a, doel_id=b, relatietype="flow", naam="g3",
                          kenmerken={"richting": "tweerichting", "protocol": "soap"}))
            # 1 flow b→a → eigen edge, aantal=1, uniforme waarden behouden.
            s.add(Relatie(tenant_id=tid, bron_id=b, doel_id=a, relatietype="flow", naam="g4",
                          kenmerken={"richting": "eenrichting", "protocol": "rest"}))
            await s.commit()
            graf = await svc.haal_grafdata_op(s, _TID)
            return graf, a, b
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    graf, a, b = asyncio.run(_run_rls(_flow))
    ab = [e for e in graf.edges if e.ring == "applicaties" and e.bron_id == a and e.doel_id == b]
    ba = [e for e in graf.edges if e.ring == "applicaties" and e.bron_id == b and e.doel_id == a]
    # Per gericht paar exact één samengetrokken edge.
    assert len(ab) == 1 and len(ba) == 1
    assert ab[0].aantal == 3                       # N flows → aantal=N
    assert ab[0].richting == "bidirectioneel"      # gemengde richting → fallback
    assert ab[0].protocol is None                  # gemengd protocol → None
    assert ba[0].aantal == 1                       # enkele flow → aantal=1
    assert ba[0].richting == "eenrichting" and ba[0].protocol == "rest"


@integratie
def test_landschapskaart_samenstelling_edge_live():
    """ADR-033 1b — component↔component aggregatie verschijnt als 'samenstelling'-edge
    (bron=geheel → doel=onderdeel); plateau-lidmaatschap levert GEEN samenstelling-edge."""
    from sqlalchemy import text as _text

    from models.models import Component, Element, ElementType, Plateau, Relatie
    from services import landschapskaart_service as svc

    tid = uuid.UUID(_TID)

    async def _comp(s, naam):
        elem = Element(tenant_id=tid, element_type=ElementType.component); s.add(elem); await s.flush()
        s.add(Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="integratievoorziening",
                        hostingmodel="on_premise")); await s.flush()
        return elem.id

    async def _flow(s):
        ids = []
        try:
            geheel = await _comp(s, "WT-SMS-Geheel")
            deel = await _comp(s, "WT-SMS-Deel")
            ids += [geheel, deel]
            # Samenstelling: geheel → onderdeel (component↔component aggregatie).
            s.add(Relatie(tenant_id=tid, bron_id=geheel, doel_id=deel, relatietype="aggregation"))
            # Plateau-lidmaatschap (bron=plateau → doel=geheel): mag GEEN samenstelling-edge worden.
            pe = Element(tenant_id=tid, element_type=ElementType.plateau); s.add(pe); await s.flush()
            s.add(Plateau(id=pe.id, tenant_id=tid, naam="WT-SMS-Plateau")); await s.flush()
            s.add(Relatie(tenant_id=tid, bron_id=pe.id, doel_id=geheel, relatietype="aggregation"))
            await s.commit()
            ids.append(pe.id)
            graf = await svc.haal_grafdata_op(s, _TID)
            return graf, geheel, deel, pe.id
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    graf, geheel, deel, plateau_id = asyncio.run(_run_rls(_flow))
    sms = [e for e in graf.edges if e.ring == "samenstelling"]
    # Exact één samenstelling-edge geheel → deel; leesbaar label, geregistreerd relatietype.
    mijn = [e for e in sms if e.bron_id == geheel and e.doel_id == deel]
    assert len(mijn) == 1 and mijn[0].relatietype == "aggregation" and mijn[0].label == "bestaat uit"
    # Plateau-lidmaatschap leverde GEEN samenstelling-edge (bron=plateau is geen component).
    assert not any(e.bron_id == plateau_id for e in sms)


@integratie
def test_landschapskaart_organisatiestructuur_edges_live():
    """ADR-024 — hoort-bij-projectie (read-only): persoon-MET-rol → afdeling → organisatie;
    persoon direct onder de organisatie (afdeling NULL) → organisatie; persoon ZONDER rol levert
    geen edge; een afdeling/organisatie zonder rol-persoon in de keten verschijnt niet."""
    from sqlalchemy import text as _text

    from models.models import (
        Component, Element, ElementType, PartijAard, RelatieKenmerkDimensie, Roltoewijzing,
    )
    from schemas.partij import PartijCreate
    from services import landschapskaart_service as svc, partij_service
    from services import relatiekenmerk_catalog as rk

    tid = uuid.UUID(_TID)

    async def _comp(s, naam):
        elem = Element(tenant_id=tid, element_type=ElementType.component); s.add(elem); await s.flush()
        s.add(Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="integratievoorziening",
                        hostingmodel="on_premise")); await s.flush()
        return elem.id

    async def _mk(s, aard, naam, **velden):
        return await partij_service.maak_aan(s, tid, PartijCreate(aard=aard, naam=naam, **velden))

    async def _flow(s):
        ids = []
        try:
            # Keten MET rol-persoon: org → afd → persoon-met-rol + persoon-zonder-rol; en een
            # persoon-met-rol direct onder de organisatie (afdeling NULL).
            org = await _mk(s, PartijAard.organisatie, "WT-OS-Org")
            afd = await _mk(s, PartijAard.organisatie_eenheid, "WT-OS-Afd", organisatie_id=org.id)
            p_rol = await _mk(s, PartijAard.persoon, "WT-OS-PersRol", organisatie_id=org.id, afdeling_id=afd.id)
            p_geen = await _mk(s, PartijAard.persoon, "WT-OS-PersGeen", organisatie_id=org.id, afdeling_id=afd.id)
            p_direct = await _mk(s, PartijAard.persoon, "WT-OS-PersDirect", organisatie_id=org.id)  # afdeling NULL
            # Keten ZONDER enige rol-persoon: org2 → afd2 → persoon-zonder-rol → mag NIET verschijnen.
            org2 = await _mk(s, PartijAard.organisatie, "WT-OS-Org2")
            afd2 = await _mk(s, PartijAard.organisatie_eenheid, "WT-OS-Afd2", organisatie_id=org2.id)
            p_geen2 = await _mk(s, PartijAard.persoon, "WT-OS-PersGeen2", organisatie_id=org2.id, afdeling_id=afd2.id)
            comp = await _comp(s, "WT-OS-Comp")
            rol = sorted(await rk.actieve_sleutels(s, RelatieKenmerkDimensie.beheerrol))[0]
            # Rol uitsluitend voor p_rol + p_direct (p_geen / p_geen2 krijgen er geen).
            s.add(Roltoewijzing(tenant_id=tid, partij_id=p_rol.id, object_id=comp, rol=rol))
            s.add(Roltoewijzing(tenant_id=tid, partij_id=p_direct.id, object_id=comp, rol=rol))
            await s.commit()
            # Cleanup-volgorde: personen → component → afdelingen → organisaties (lidmaatschap-RESTRICT).
            ids += [p_rol.id, p_geen.id, p_direct.id, p_geen2.id, comp, afd.id, afd2.id, org.id, org2.id]
            graf = await svc.haal_grafdata_op(s, _TID)
            return graf, {
                "org": org.id, "afd": afd.id, "p_rol": p_rol.id, "p_geen": p_geen.id,
                "p_direct": p_direct.id, "org2": org2.id, "afd2": afd2.id, "p_geen2": p_geen2.id,
            }
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    graf, X = asyncio.run(_run_rls(_flow))
    os_edges = [e for e in graf.edges if e.ring == "organisatiestructuur"]
    paren = {(e.bron_id, e.doel_id) for e in os_edges}
    # Persoon-met-rol → afdeling → organisatie.
    assert (X["p_rol"], X["afd"]) in paren
    assert (X["afd"], X["org"]) in paren
    # Persoon direct onder de organisatie (afdeling NULL) → organisatie (geen tussenstap).
    assert (X["p_direct"], X["org"]) in paren
    # Persoon ZONDER rol levert geen enkele hoort-bij-edge.
    assert not any(e.bron_id == X["p_geen"] for e in os_edges)
    # Keten zonder rol-persoon (org2/afd2/p_geen2) verschijnt NIET in deze ring (geen lege takken).
    leeg = {X["org2"], X["afd2"], X["p_geen2"]}
    assert not any(e.bron_id in leeg or e.doel_id in leeg for e in os_edges)
    # Geregistreerd, niet afgeleid: relatietype/label exact.
    assert all(e.relatietype == "hoort_bij" and e.label == "hoort bij" for e in os_edges)


@integratie
def test_landschapskaart_organisatie_scope_live():
    """ADR-024 organisatie-scope (read-projectie): bezit via eigenaar_organisatie_id, gebruik via
    serving × gebruikersgroep-organisatie; gaten (zonder eigenaar / organisatieloze groep) herkenbaar;
    aard=organisatie-partijen identificeerbaar voor de frontend."""
    from sqlalchemy import text as _text

    from models.models import (
        Component, Element, ElementType, Gebruikersgroep, Organisatiegebruik, Partij, PartijAard,
        PartijScope, Relatie,
    )
    from services import landschapskaart_service as svc

    tid = uuid.UUID(_TID)

    async def _comp(s, naam, *, eigenaar=None):
        elem = Element(tenant_id=tid, element_type=ElementType.component); s.add(elem); await s.flush()
        s.add(Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="integratievoorziening",
                        hostingmodel="on_premise", eigenaar_organisatie_id=eigenaar)); await s.flush()
        return elem.id

    async def _groep(s, *, naam, organisatie_id, applicatie_id):
        # ADR-036/038 — organisatie leeft op het grove feit; een groep heeft altijd een organisatie
        # (verwijst via gebruik_id). Deze org-scope-test toetst de organisatie-toerekening zonder
        # afdeling (afdeling_id NULL).
        og = Organisatiegebruik(tenant_id=tid, organisatie_id=organisatie_id, applicatie_id=applicatie_id)
        s.add(og); await s.flush()
        elem = Element(tenant_id=tid, element_type=ElementType.gebruikersgroep); s.add(elem); await s.flush()
        s.add(Gebruikersgroep(id=elem.id, tenant_id=tid, gebruik_id=og.id,
                              aantal_gebruikers=10)); await s.flush()
        return elem.id

    async def _flow(s):
        ids = []
        try:
            # Organisatie-partij (aard=organisatie) — de "eigen organisatie".
            oe = Element(tenant_id=tid, element_type=ElementType.partij); s.add(oe); await s.flush()
            s.add(Partij(id=oe.id, tenant_id=tid, aard=PartijAard.organisatie, naam="WT-OS-Org-Scope", scope=PartijScope.extern)); await s.flush()
            # Bezit: component MET eigenaar vs ZONDER eigenaar.
            c_bezit = await _comp(s, "WT-OS-Bezit", eigenaar=oe.id)
            c_geen_eig = await _comp(s, "WT-OS-GeenEig")
            # Gebruik: component via een groep MET organisatie (ADR-038 — org-loos bestaat niet meer).
            c_gebruik = await _comp(s, "WT-OS-Gebruik")
            g_org = await _groep(s, naam="WT-OS-Groep", organisatie_id=oe.id, applicatie_id=c_gebruik)
            s.add(Relatie(tenant_id=tid, bron_id=c_gebruik, doel_id=g_org, relatietype="serving"))
            await s.commit()
            # RESTRICT-volgorde (ADR-038): de groep vóór de app/organisatie wier verwijdering het
            # grove feit cascadeert (fk_gebruikersgroep_gebruik = RESTRICT).
            ids += [g_org, c_bezit, c_geen_eig, c_gebruik, oe.id]
            graf = await svc.haal_grafdata_op(s, _TID)
            return graf, {"org": oe.id, "bezit": c_bezit, "geen_eig": c_geen_eig,
                          "gebruik": c_gebruik}
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    graf, X = asyncio.run(_run_rls(_flow))
    per_id = {n.id: n for n in graf.nodes}

    # 1. Bezit: eigenaar_organisatie_id meegeleverd; zonder eigenaar = None (herkenbaar gat).
    assert per_id[X["bezit"]].eigenaar_organisatie_id == X["org"]
    assert per_id[X["geen_eig"]].eigenaar_organisatie_id is None

    # 2. Gebruik: component via een org-groep → die organisatie in de set.
    assert X["org"] in per_id[X["gebruik"]].gebruikt_door_organisaties
    # Een component zonder serving heeft geen gebruik-toerekening.
    assert per_id[X["bezit"]].gebruikt_door_organisaties == []

    # 3. De aard=organisatie-partij is identificeerbaar voor de frontend (soort='organisatie').
    org_node = per_id[X["org"]]
    assert org_node.element_type == "partij" and org_node.soort == "organisatie" and org_node.naam == "WT-OS-Org-Scope"


@integratie
def test_landschapskaart_gebruikt_edge_live():
    """LI033b — een organisatie die een applicatie GEBRUIKT (grof feit `organisatiegebruik`) krijgt een
    'gebruikt'-edge (org → app). Bezit + gebruik levert TWEE lijnen (eigenaar + gebruikt), niet onderdrukt."""
    from sqlalchemy import text as _text

    from models.models import (
        Component, Element, ElementType, Organisatiegebruik, Partij, PartijAard, PartijScope,
    )
    from services import landschapskaart_service as svc

    tid = uuid.UUID(_TID)

    async def _comp(s, naam, *, eigenaar=None):
        elem = Element(tenant_id=tid, element_type=ElementType.component); s.add(elem); await s.flush()
        s.add(Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="applicatie",
                        hostingmodel="on_premise", eigenaar_organisatie_id=eigenaar)); await s.flush()
        return elem.id

    async def _org(s, naam):
        elem = Element(tenant_id=tid, element_type=ElementType.partij); s.add(elem); await s.flush()
        s.add(Partij(id=elem.id, tenant_id=tid, aard=PartijAard.organisatie, naam=naam,
                     scope=PartijScope.extern)); await s.flush()
        return elem.id

    async def _flow(s):
        ids = []
        try:
            org = await _org(s, "WT-GBR-Org")
            app_gebruikt = await _comp(s, "WT-GBR-AppGebruikt")                 # alleen gebruikt
            app_beide = await _comp(s, "WT-GBR-AppBeide", eigenaar=org)          # bezit + gebruik
            s.add(Organisatiegebruik(tenant_id=tid, organisatie_id=org, applicatie_id=app_gebruikt))
            s.add(Organisatiegebruik(tenant_id=tid, organisatie_id=org, applicatie_id=app_beide))
            await s.commit()
            ids += [app_gebruikt, app_beide, org]
            graf = await svc.haal_grafdata_op(s, _TID)
            return graf, {"org": org, "gebruikt": app_gebruikt, "beide": app_beide}
        finally:
            # organisatiegebruik-FK's zijn ON DELETE CASCADE → element-delete ruimt de grove feiten mee.
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    graf, X = asyncio.run(_run_rls(_flow))

    def _edges(bron, doel):
        return [e for e in graf.edges if e.bron_id == bron and e.doel_id == doel]

    # gebruikt-edge org → app (label/ring/relatietype).
    g = _edges(X["org"], X["gebruikt"])
    assert any(e.relatietype == "gebruikt" and e.ring == "gebruikt" and e.label == "gebruikt" for e in g)
    # Bezit + gebruik = twee lijnen (eigenaar + gebruikt), beide aanwezig (niet onderdrukt).
    ringen_beide = {e.ring for e in _edges(X["org"], X["beide"])}
    assert {"eigenaar", "gebruikt"} <= ringen_beide


@integratie
def test_landschapskaart_gebruikt_scoped_live():
    """LI033b — een gebruiker-organisatie (gebruikt, niet bezit/beheert) komt in de SUBGRAAF-scope zodra
    haar gebruikte applicatie in de set zit → de org-node verschijnt (scope-add) en de gebruikt-edge is
    niet-dangling."""
    from sqlalchemy import text as _text

    from models.models import (
        Component, Element, ElementType, Organisatiegebruik, Partij, PartijAard, PartijScope,
    )
    from services import landschapskaart_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            oe = Element(tenant_id=tid, element_type=ElementType.partij); s.add(oe); await s.flush()
            s.add(Partij(id=oe.id, tenant_id=tid, aard=PartijAard.organisatie, naam="WT-GBRS-Org",
                         scope=PartijScope.extern)); await s.flush()
            ce = Element(tenant_id=tid, element_type=ElementType.component); s.add(ce); await s.flush()
            s.add(Component(id=ce.id, tenant_id=tid, naam="WT-GBRS-App", componenttype="applicatie",
                            hostingmodel="on_premise")); await s.flush()  # geen eigenaar → puur gebruik
            s.add(Organisatiegebruik(tenant_id=tid, organisatie_id=oe.id, applicatie_id=ce.id))
            await s.commit()
            ids += [ce.id, oe.id]
            graf = await svc.haal_grafdata_op(s, tid, component_ids=[ce.id])
            return graf, {"org": oe.id, "app": ce.id}
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    graf, X = asyncio.run(_run_rls(_flow))
    per_id = {n.id: n for n in graf.nodes}
    # De org-node kwam via de scope-add mee (ze bezit/beheert niets — alleen gebruik).
    assert X["org"] in per_id
    # De gebruikt-edge tekent tussen bestaande zichtbare nodes (niet-dangling).
    assert any(e.bron_id == X["org"] and e.doel_id == X["app"] and e.ring == "gebruikt" for e in graf.edges)


@integratie
def test_landschapskaart_blokkades_open_telling_live():
    """Een via de engine ontstane open blokkade (score 'nee') telt mee in `blokkades_open`."""
    from sqlalchemy import select as _select, text as _text

    from models.models import ChecklistVraag
    from schemas.component import ComponentCreate
    from schemas.checklistscore import ChecklistscoreCreate
    from services import component_service, checklistscore_service, landschapskaart_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            app = await component_service.maak_aan(
                s, tid, ComponentCreate(componenttype="applicatie", naam="WT-LK-Blok", hostingmodel="saas", migratiepad="onbekend",
                                         complexiteit="midden", prioriteit="midden"))
            ids.append(app["id"])
            await component_service.start_beoordeling(s, tid, app["id"])
            vraag_id = (await s.execute(
                _select(ChecklistVraag.id).where(ChecklistVraag.componenttype == "applicatie").limit(1)
            )).scalar_one()
            # Score 'nee' → de engine genereert een open blokkade (read-only geteld door de kaart).
            await checklistscore_service.maak_aan(
                s, tid, ChecklistscoreCreate(component_id=app["id"], checklistvraag_id=vraag_id, score="nee"))
            graf = await svc.haal_grafdata_op(s, _TID)
            return next(n for n in graf.nodes if n.id == app["id"])
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    node = asyncio.run(_run_rls(_flow))
    assert node.blokkades_open >= 1  # de open blokkade wordt geteld


# ── LI021 Fase A — set-scoped subgraaf + leverancier-filter + eigenaar-edge ───────
def test_subgraaf_signatuur_en_schema_en_route():
    """A1 — service parametriseerbaar met `component_ids` (default None = volledige graaf,
    back-compat); SubgraafRequest (extra=forbid); POST-route bedrade op de body."""
    import inspect

    import routes.landschapskaart as r
    import services.landschapskaart_service as s
    from schemas.landschapskaart import SubgraafRequest

    sig = inspect.signature(s.haal_grafdata_op)
    assert "component_ids" in sig.parameters
    assert sig.parameters["component_ids"].default is None  # None = volledige graaf
    assert SubgraafRequest.model_config.get("extra") == "forbid"
    assert {"component_ids", "diepte"} <= set(SubgraafRequest.model_fields)
    rbron = inspect.getsource(r)
    assert '"/subgraaf"' in rbron and "component_ids=body.component_ids" in rbron


def test_eigenaar_edge_is_context_geen_impact():
    """A3 — de eigenaar-edge ('is eigendom van') zit in de bron als context-ring 'eigenaar'.
    ADR-040 F1 — de Impact-verkenner is afgeschaft: er is geen frontend `IMPACT_RINGEN` meer (geen
    aparte impact-propagatielijst). Context-ringen (eigenaar/gebruikt) doen mee via de ego-kring."""
    import inspect
    import pathlib

    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    assert 'ring="eigenaar"' in bron and 'label="is eigendom van"' in bron
    vue = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "views" / "LandschapskaartView.vue"
    assert "IMPACT_RINGEN = new Set" not in vue.read_text()  # ADR-040 — impact-machinerie afgeschaft


def _ac(naam):
    from schemas.component import ComponentCreate
    return ComponentCreate(componenttype="applicatie", naam=naam, hostingmodel="saas", migratiepad="onbekend",
                            complexiteit="midden", prioriteit="midden")


@integratie
def test_subgraaf_set_scoped_s_plus_1hop_live():
    """A1 — set-scoped: S + directe buren (1 hop) + edges daartussen; een losse node valt buiten;
    `component_ids=None` levert nog de volledige graaf (back-compat)."""
    from sqlalchemy import text as _text

    from models.models import Relatie
    from services import component_service, landschapskaart_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            a1 = await component_service.maak_aan(s, tid, _ac("WT-SUB-A1"))
            a2 = await component_service.maak_aan(s, tid, _ac("WT-SUB-A2"))
            a3 = await component_service.maak_aan(s, tid, _ac("WT-SUB-A3-ISOL"))
            ids += [a1["id"], a2["id"], a3["id"]]
            # a1 → a2 (flow): a2 is een 1-hop-buur van a1; a3 staat los.
            s.add(Relatie(tenant_id=tid, bron_id=a1["id"], doel_id=a2["id"], relatietype="flow",
                          kenmerken={"richting": "eenrichting", "protocol": "rest"}))
            await s.commit()
            sub = await svc.haal_grafdata_op(s, _TID, component_ids=[a1["id"]])
            vol = await svc.haal_grafdata_op(s, _TID)
            return ({n.id for n in sub.nodes}, {n.id for n in vol.nodes},
                    a1["id"], a2["id"], a3["id"], sub.edges)
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    sub_ids, vol_ids, a1, a2, a3, sub_edges = asyncio.run(_run_rls(_flow))
    assert a1 in sub_ids and a2 in sub_ids          # S + directe buur
    assert a3 not in sub_ids                        # buiten S∪buren → niet in de subgraaf
    assert {a1, a2, a3} <= vol_ids                  # back-compat: volledige graaf bevat alles
    assert any(e.bron_id == a1 and e.doel_id == a2 and e.ring == "applicaties" for e in sub_edges)


@integratie
def test_subgraaf_organisatiestructuur_alleen_s_rol_personen_live():
    """A1 — de organisatiestructuur-ring is set-scoped: alleen de rol-personen van S (+ hun
    organisatie), niet die van een ander component."""
    from sqlalchemy import text as _text

    from models.models import (
        Element, ElementType, Partij, PartijAard, PartijScope, RelatieKenmerkDimensie, Roltoewijzing,
    )
    from services import component_service, landschapskaart_service as svc
    from services import relatiekenmerk_catalog as rk

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            a1 = await component_service.maak_aan(s, tid, _ac("WT-OS-A1"))
            a2 = await component_service.maak_aan(s, tid, _ac("WT-OS-A2"))
            ids += [a1["id"], a2["id"]]

            async def _org(naam):
                e = Element(tenant_id=tid, element_type=ElementType.partij); s.add(e); await s.flush()
                s.add(Partij(id=e.id, tenant_id=tid, aard=PartijAard.organisatie, naam=naam, scope=PartijScope.extern)); await s.flush()
                return e.id

            async def _pers(naam, org_id):
                e = Element(tenant_id=tid, element_type=ElementType.partij); s.add(e); await s.flush()
                s.add(Partij(id=e.id, tenant_id=tid, aard=PartijAard.persoon, naam=naam,
                             organisatie_id=org_id)); await s.flush()
                return e.id

            o1, o2 = await _org("WT-OS-Org1"), await _org("WT-OS-Org2")
            p1 = await _pers("WT-OS-P1", o1)
            p2 = await _pers("WT-OS-P2", o2)
            rol = sorted(await rk.actieve_sleutels(s, RelatieKenmerkDimensie.beheerrol))[0]
            s.add(Roltoewijzing(tenant_id=tid, partij_id=p1, object_id=a1["id"], rol=rol))
            s.add(Roltoewijzing(tenant_id=tid, partij_id=p2, object_id=a2["id"], rol=rol))
            await s.commit()
            ids += [p1, p2, o1, o2]  # personen vóór organisaties (FK-volgorde bij opruim)
            sub = await svc.haal_grafdata_op(s, _TID, component_ids=[a1["id"]])
            return ({n.id for n in sub.nodes},
                    [e for e in sub.edges if e.ring == "organisatiestructuur"], p1, o1, p2, o2)
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    node_ids, os_edges, p1, o1, p2, o2 = asyncio.run(_run_rls(_flow))
    assert p1 in node_ids and o1 in node_ids        # rol-persoon van S + zijn organisatie
    assert p2 not in node_ids and o2 not in node_ids  # die van a2 vallen buiten S
    assert any(e.bron_id == p1 and e.doel_id == o1 for e in os_edges)
    assert all(e.bron_id != p2 for e in os_edges)


@integratie
def test_eigenaar_edge_live():
    """A3 — een component MÉT eigenaar levert de edge organisatie→component 'is eigendom van';
    een component ZONDER eigenaar niet. In de subgraaf komt de eigenaar-org als 1-hop-context mee."""
    from sqlalchemy import text as _text

    from models.models import Component, Element, ElementType, HostingModel, Partij, PartijAard, PartijScope
    from services import landschapskaart_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            oe = Element(tenant_id=tid, element_type=ElementType.partij); s.add(oe); await s.flush()
            s.add(Partij(id=oe.id, tenant_id=tid, aard=PartijAard.organisatie, naam="WT-EIG-Org", scope=PartijScope.extern)); await s.flush()

            async def _comp(naam, eig):
                e = Element(tenant_id=tid, element_type=ElementType.component); s.add(e); await s.flush()
                s.add(Component(id=e.id, tenant_id=tid, naam=naam, componenttype="database",
                                hostingmodel=HostingModel.on_premise, eigenaar_organisatie_id=eig)); await s.flush()
                return e.id

            c1 = await _comp("WT-EIG-Met", oe.id)
            c2 = await _comp("WT-EIG-Zonder", None)
            await s.commit()
            ids += [c1, c2, oe.id]  # componenten vóór de organisatie (eigenaar-FK)
            vol = await svc.haal_grafdata_op(s, _TID)
            sub = await svc.haal_grafdata_op(s, _TID, component_ids=[c1])
            return (vol.edges, sub.edges, {n.id for n in sub.nodes}, oe.id, c1, c2)
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    vol_edges, sub_edges, sub_nodes, org, c1, c2 = asyncio.run(_run_rls(_flow))
    eig = [e for e in vol_edges if e.ring == "eigenaar"]
    assert any(e.bron_id == org and e.doel_id == c1 and e.label == "is eigendom van" for e in eig)
    assert not any(e.doel_id == c2 for e in eig)    # zonder eigenaar → geen edge
    assert org in sub_nodes                          # eigenaar-org als 1-hop-context in de subgraaf
    assert any(e.bron_id == org and e.doel_id == c1 for e in sub_edges if e.ring == "eigenaar")


@integratie
def test_component_leverancier_filter_beide_paden_live():
    """A2 — leverancier-filter op /componenten via beide afleidingspaden (roltoewijzing-rol én
    contract-keten); een component zonder die leverancier valt buiten; paginering-vorm intact."""
    from sqlalchemy import text as _text

    from models.models import (
        Component, Contract, ContractType, Element, ElementType, HostingModel,
        Partij, PartijAard, PartijScope, Relatie, Roltoewijzing,
    )
    from services import component_service

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            xe = Element(tenant_id=tid, element_type=ElementType.partij); s.add(xe); await s.flush()
            s.add(Partij(id=xe.id, tenant_id=tid, aard=PartijAard.externe_partij, naam="WT-LEV-X", scope=PartijScope.extern)); await s.flush()

            async def _comp(naam):
                e = Element(tenant_id=tid, element_type=ElementType.component); s.add(e); await s.flush()
                s.add(Component(id=e.id, tenant_id=tid, naam=naam, componenttype="database",
                                hostingmodel=HostingModel.on_premise)); await s.flush()
                return e.id

            c_rol = await _comp("WT-LEV-ViaRol")
            c_contract = await _comp("WT-LEV-ViaContract")
            c_other = await _comp("WT-LEV-Geen")
            # Pad (a): roltoewijzing-leverancierrol op c_rol door X.
            s.add(Roltoewijzing(tenant_id=tid, partij_id=xe.id, object_id=c_rol, rol="technisch_beheer"))
            # Pad (b): association → contract met leverancier X, op c_contract.
            ce = Element(tenant_id=tid, element_type=ElementType.contract); s.add(ce); await s.flush()
            s.add(Contract(id=ce.id, tenant_id=tid, leverancier_id=xe.id,
                           contracttype=ContractType.los_contract, contractnaam="WT-LEV-Contract")); await s.flush()
            s.add(Relatie(tenant_id=tid, bron_id=c_contract, doel_id=ce.id, relatietype="association"))
            await s.commit()
            ids += [c_rol, c_contract, c_other, ce.id, xe.id]  # contract vóór X (leverancier-RESTRICT)
            items, cursor = await component_service.lijst(s, _TID, leverancier_id=xe.id, limit=50)
            return ({i["id"] for i in items}, c_rol, c_contract, c_other, cursor)
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    gevonden, c_rol, c_contract, c_other, cursor = asyncio.run(_run_rls(_flow))
    assert c_rol in gevonden and c_contract in gevonden   # beide afleidingspaden
    assert c_other not in gevonden                        # geen leverancier-link → buiten
    # paginering-vorm intact (tuple items+cursor; cursor None of een string).
    assert cursor is None or isinstance(cursor, str)
