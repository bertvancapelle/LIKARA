"""Tests — ADR-021 Fase B component-/structuurrelatie-CRUD (CD052).

Offline-invarianten (subtype-bescherming, self-ref, catalogus-groepering) + live-
integratie (CRUD round-trip, subtype-delete-bescherming, beide-richtingen-structuur)
tegen de geseede lk_app-DB (skip indien onbereikbaar).
"""
import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline-invarianten ─────────────────────────────────────────────────────────

def test_maak_aan_applicatie_type_convergeert(monkeypatch):
    # CD054b W1: type 'applicatie' via het component-pad wordt NIET geweigerd, maar
    # maakt atomair het subtype met defaults via dezelfde service-kern.
    from models.models import Migratiepad, NiveauEnum
    from schemas.component import ComponentCreate
    from services import component_service as svc

    vastgelegd = {}

    async def _kern(session, tid, **kw):
        vastgelegd.update(kw)
        # LI059: de creatie-kern levert het component zélf terug (geen subtype-wrapper).
        return SimpleNamespace(id=uuid.uuid4())

    async def _lees(session, tid, comp):
        return {"id": comp.id, "heeft_applicatie_subtype": True}

    async def _geen_classificatie_check(session, data):
        return None  # ADR-028: catalogus-validatie is elders getest (buiten deze convergentie-scope).

    # LI059 facade-purge: de kern woont nu in component_service (was applicatie_service).
    monkeypatch.setattr(svc, "maak_applicatie_component", _kern)
    monkeypatch.setattr(svc, "_lees", _lees)
    monkeypatch.setattr(svc, "_valideer_classificatie", _geen_classificatie_check)

    out = asyncio.run(svc.maak_aan(AsyncMock(), _TID, ComponentCreate(naam="Nieuwe app", componenttype="applicatie")))
    assert out["heeft_applicatie_subtype"] is True
    assert vastgelegd["naam"] == "Nieuwe app"
    assert vastgelegd["eigenaar_organisatie_id"] is None  # optioneel (UX-B6-b)
    # LI040 — geen verzonnen antwoorden meer: weggelaten = None ("nog niet vastgelegd")
    # voor bedoeling ÉN de oordelen complexiteit/prioriteit (migratie 0067/0068).
    assert vastgelegd["migratiepad"] is None
    assert vastgelegd["complexiteit"] is None
    assert vastgelegd["prioriteit"] is None
    # ADR-028 — de default-rol wordt door de convergente aanmaak doorgegeven aan de kern.
    assert vastgelegd["componentrol"] == "interne_applicatie"


def test_component_sort_allowlist_synchroon():
    # ADR-017 B2: de schema-enum, de service-allowlist én de parsers blijven 1-op-1.
    from schemas.component import ComponentSorteerveld
    from services import component_service as svc

    enum_namen = {e.value for e in ComponentSorteerveld}
    assert enum_namen == set(svc._SORTEERBARE_KOLOMMEN)
    assert enum_namen == set(svc._WAARDE_PARSERS)
    # De twee additieve velden zitten in de allowlist.
    assert {"eigenaar", "hostingmodel"} <= enum_namen
    # UX-B6-b — `eigenaar` is de placeholder-FK-kolom (gesorteerd wordt op de org-naam via de join).
    assert svc._SORTEERBARE_KOLOMMEN["eigenaar"].key == "eigenaar_organisatie_id"
    assert svc._SORTEERBARE_KOLOMMEN["hostingmodel"].key == "hostingmodel"


def test_sorteer_waarde_mapt_eigenaar_en_hostingmodel():
    # Cursor-sleutel: `eigenaar` → de gejoinde organisatie-naam (eig_naam); hostingmodel direct.
    from models.models import HostingModel
    from services.component_service import _sorteer_waarde

    # LI059 Slice 3: signatuur `_sorteer_waarde(comp, lifecycle, eig_naam, sort)` (geen subtype-arg meer).
    comp = SimpleNamespace(hostingmodel=HostingModel.saas)
    assert _sorteer_waarde(comp, None, "Gemeente X", "eigenaar") == "Gemeente X"
    assert _sorteer_waarde(comp, None, None, "hostingmodel") == HostingModel.saas


# De statische SUBTYPE_BESCHERMD-type-guard is vervangen door de toestand-gebaseerde
# type-lock (ADR-022 Fase C); zie test_typelock_adr022_fasec.py (integratie).


# ADR-023: de zelfstandige component_structuur-CRUD is vervangen door het relatiemodel;
# `bron≠doel` (ZELFVERWIJZING) wordt nu door `relatie_service` afgedwongen (zie test_relatie_bcore).


def test_componentconfig_opties_groepering():
    from models.models import ComponentConfigDimensie as D
    from services import componentconfig_catalog as catalog

    session = AsyncMock()
    res = MagicMock()
    res.all.return_value = [
        SimpleNamespace(dimensie=D.componenttype, optie_sleutel="database", label="Database", volgorde=1, checklist_dragend=False, ondersteunt_werk=False, archimate_element="system_software", laag="technology"),
        SimpleNamespace(dimensie=D.structuurrelatie_type, optie_sleutel="draait_op", label="Draait op", volgorde=0, checklist_dragend=False, ondersteunt_werk=False, archimate_element=None, laag=None),
    ]
    session.execute.return_value = res
    out = asyncio.run(catalog.actieve_opties_per_dimensie(session))
    assert set(out) == {d.value for d in D}
    # ADR-022 Fase E: opties dragen `checklist_dragend` mee; ADR-023 Fase C: laag/element.
    # ADR-045 — het read-pad draagt óók `ondersteunt_werk` (tenant-vlag voor filter/picker).
    assert out["componenttype"][0] == {
        "optie_sleutel": "database", "label": "Database", "checklist_dragend": False,
        "ondersteunt_werk": False,
        "archimate_element": "system_software", "laag": "technology",
    }
    assert out["structuurrelatie_type"][0]["label"] == "Draait op"


# ── Live-integratie (lk_app) ─────────────────────────────────────────────────────

import app.core.database  # noqa: E402,F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context  # noqa: E402


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


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar (offline)")


async def _sessie_run(fn):
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
def test_component_crud_roundtrip():
    from schemas.component import ComponentCreate
    from services import component_service as svc

    naam = f"CD052-test-{uuid.uuid4().hex[:8]}"

    async def _flow(s):
        comp = await svc.maak_aan(s, _TID, ComponentCreate(naam=naam, componenttype="database"))
        assert comp["heeft_applicatie_subtype"] is False
        assert comp["componenttype_label"] == "Database"
        detail = await svc.lees_detail(s, _TID, comp["id"])
        assert detail["naam"] == naam
        items, _ = await svc.lijst(s, _TID, componenttype="database", limit=50)
        assert any(i["id"] == comp["id"] for i in items)
        await svc.verwijder(s, _TID, comp["id"])  # geen relaties → mag

    asyncio.run(_sessie_run(_flow))


def test_component_delete_via_element(monkeypatch):
    # LI059 Slice 3: één delete-pad voor élk component (applicatie of kaal) — verwijderen via
    # het element-supertype (cascade element → component → engine-kinderen). Geen subtype-tak
    # / applicatie-delegatie meer. ADR-023 (Besluit 13): relaties blokkeren de delete niet.
    from services import component_service as svc

    cid = uuid.uuid4()

    async def _haal(*a, **k):
        return SimpleNamespace(id=cid)

    monkeypatch.setattr(svc, "haal_op", _haal)

    uitgevoerd = []
    session = AsyncMock()

    async def _execute(stmt):
        uitgevoerd.append(str(stmt))

    session.execute = _execute
    asyncio.run(svc.verwijder(session, _TID, cid))
    assert len(uitgevoerd) == 1
    assert uitgevoerd[0].lower().startswith("delete from element")
    session.commit.assert_awaited_once()


@integratie
def test_lijst_levert_besturingsvelden_en_statusfilter():
    # CD054b W1: de verenigde lijst joint het subtype — besturingsvelden gevuld voor
    # applicaties, null voor kale infra; status-filter matcht alleen subtypen.
    from services import component_service as svc

    async def _flow(s):
        items, _ = await svc.lijst(s, _TID, limit=100)
        per_naam = {i["naam"]: i for i in items}
        app = per_naam["Zaaksysteem"]          # applicatie-subtype (besturingsvelden gevuld)
        infra = per_naam["Shared fileshare"]   # LI058 — nog niet-beoordeeld type (geen profiel/lifecycle)
        gefilterd, _ = await svc.lijst(s, _TID, limit=100, status=["concept", "in_inventarisatie", "geblokkeerd", "migratieklaar"])
        return app, infra, gefilterd

    app, infra, gefilterd = asyncio.run(_sessie_run(_flow))
    assert app["heeft_applicatie_subtype"] is True
    # LI040 — de lijst LEVERT de oordeel-velden (sleutels aanwezig), maar zonder gezet
    # oordeel zijn ze None ("nog niet vastgelegd") — geen gratis 'midden' meer.
    assert app["lifecycle_status"] is not None and "complexiteit" in app
    assert infra["heeft_applicatie_subtype"] is False
    # lifecycle_status blijft None (geen profiel: niet checklist-dragend).
    assert infra["lifecycle_status"] is None
    # LI040 — geen gratis 'midden' meer: een ongemoeid component draagt géén oordeel.
    assert infra["complexiteit"] is None
    # ADR-022 Fase E: het status-filter matcht elk checklist-dragend component (heeft een
    # profiel ⇒ lifecycle), niet langer uitsluitend applicatie-subtypen. Invariant: alle
    # gefilterde rijen hebben een lifecycle_status (kale infra zonder profiel valt eruit).
    assert gefilterd and all(i["lifecycle_status"] is not None for i in gefilterd)


@integratie
def test_lijst_laag_filter_en_projectie():
    # ADR-023 Fase C: het laag-filter (read-only catalogus-typing) levert alleen de
    # technologielaag-componenten; elke rij draagt de laag/element-projectie.
    from services import component_service as svc

    async def _flow(s):
        tech, _ = await svc.lijst(s, _TID, limit=200, laag="technology")
        alle, _ = await svc.lijst(s, _TID, limit=200)
        return tech, {i["naam"]: i for i in alle}

    tech, per_naam = asyncio.run(_sessie_run(_flow))
    namen = {i["naam"] for i in tech}
    assert "Shared DB-server" in namen         # database = technologielaag
    assert "Zaaksysteem" not in namen          # applicatie = applicatielaag (uitgefilterd)
    assert tech and all(i["laag"] == "technology" for i in tech)
    # Projectie aanwezig in de ongefilterde lijst (beide lagen).
    assert per_naam["Zaaksysteem"]["laag"] == "application"
    assert per_naam["Shared DB-server"]["archimate_element"] == "system_software"


@integratie
def test_structuur_overzicht_beide_richtingen():
    from sqlalchemy import text
    from services import component_service as svc

    async def _flow(s):
        row = (await s.execute(text("select id from component where naam='Shared DB-server'"))).first()
        ov = await svc.structuur_overzicht(s, _TID, row[0])
        return {x["naam"] for x in ov["gebruikt_door"]}, ov["draait_op"]

    gebruikt_door, draait_op = asyncio.run(_sessie_run(_flow))
    assert {"Zaaksysteem", "BRP", "DMS"} <= gebruikt_door  # de gedeelde DB draagt deze shared-apps
    assert draait_op == []  # de DB steunt zelf nergens op


@integratie
def test_component_contract_op_niet_applicatie_component():
    """Casus: een contract op een database-component (geen applicatie)."""
    from sqlalchemy import text
    from schemas.component import ComponentCreate
    from schemas.component_contract import ComponentContractCreate
    from services import component_contract_service as cc
    from services import component_service

    naam = f"CD052-db-{uuid.uuid4().hex[:8]}"

    async def _flow(s):
        comp = await component_service.maak_aan(
            s, _TID, ComponentCreate(naam=naam, componenttype="database")
        )
        kop = None
        try:
            cid = (await s.execute(
                text("select id from contract where contractnaam='Burgerzaken-suite licentie 2023–2026'")
            )).first()[0]
            kop = await cc.maak_aan(
                s, _TID, ComponentContractCreate(component_id=comp["id"], contract_id=cid, relatie_rol="valt_onder")
            )
            lijst = await cc.contracten_van_component(s, _TID, comp["id"])
            assert any(r["contract_id"] == cid for r in lijst)
            return True
        finally:
            # Opruimen draait ALTIJD (ook bij een falende assert/exception): koppeling vóór
            # component (anders IN_GEBRUIK), zodat een gefaalde run geen wees-component achterlaat.
            if kop is not None:
                await cc.verwijder(s, _TID, kop["id"])          # opruimen: koppeling
            await component_service.verwijder(s, _TID, comp["id"])  # dan component

    assert asyncio.run(_sessie_run(_flow))


@integratie
def test_server_side_sort_eigenaar_en_hostingmodel_live():
    """Server-side keyset-sortering op de twee additieve velden, beide richtingen.
    Eigenaar = alfabetisch; hostingmodel = enum-definitievolgorde. `zoek` isoleert de
    drie testcomponenten. Onbekend/afgeleid sorteerveld (Laag) ⇒ ValueError (route → 400)."""
    from models.models import HostingModel
    from schemas.component import ComponentCreate
    from services import component_service as svc

    sfx = f"SORT{uuid.uuid4().hex[:8]}"
    # (eigenaar, hostingmodel) — bewust niet vooraf gesorteerd.
    rijen = [
        (f"{sfx}-een", "MMM-org", HostingModel.saas),
        (f"{sfx}-twee", "AAA-org", HostingModel.on_premise),
        (f"{sfx}-drie", "ZZZ-org", HostingModel.iaas),
    ]

    async def _flow(s):
        # UX-B6-b — eigenaar-organisatie is een verwijzing; maak eerst de organisatie-partijen.
        from sqlalchemy import text as _text
        from models.models import Element, ElementType, Partij, PartijAard, PartijScope

        tid = uuid.UUID(_TID)
        ids, org_ids, orgs = [], [], {}
        try:
            for label in ("MMM-org", "AAA-org", "ZZZ-org"):
                oe = Element(tenant_id=tid, element_type=ElementType.partij)
                s.add(oe); await s.flush()
                s.add(Partij(id=oe.id, tenant_id=tid, aard=PartijAard.organisatie, naam=label, scope=PartijScope.extern))
                await s.flush()
                orgs[label] = oe.id; org_ids.append(oe.id)
            await s.commit()

            for naam, eig, host in rijen:
                c = await svc.maak_aan(
                    s, _TID,
                    ComponentCreate(naam=naam, componenttype="database",
                                    eigenaar_organisatie_id=orgs[eig], hostingmodel=host),
                )
                ids.append(c["id"])

            async def _eig(order):
                items, _ = await svc.lijst(s, _TID, sort="eigenaar", order=order, zoek=sfx, limit=50)
                return [i["eigenaar_organisatie_naam"] for i in items if i["id"] in ids]

            async def _host(order):
                items, _ = await svc.lijst(s, _TID, sort="hostingmodel", order=order, zoek=sfx, limit=50)
                return [i["hostingmodel"] for i in items if i["id"] in ids]

            eig_asc, eig_desc = await _eig("asc"), await _eig("desc")
            host_asc, host_desc = await _host("asc"), await _host("desc")

            onbekend = None
            try:
                await svc.lijst(s, _TID, sort="laag", order="asc", zoek=sfx)
            except ValueError as e:
                onbekend = str(e)
            return eig_asc, eig_desc, host_asc, host_desc, onbekend
        finally:
            for cid in ids:
                await svc.verwijder(s, _TID, cid)
            for oid in org_ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(oid)})
            await s.commit()

    eig_asc, eig_desc, host_asc, host_desc, onbekend = asyncio.run(_sessie_run(_flow))

    # Eigenaar alfabetisch (NULLS-LAST no-op; alle NOT NULL).
    assert eig_asc == ["AAA-org", "MMM-org", "ZZZ-org"]
    assert eig_desc == ["ZZZ-org", "MMM-org", "AAA-org"]
    # Hostingmodel op enum-definitievolgorde: on_premise < saas < iaas.
    _idx = {h: i for i, h in enumerate(HostingModel)}
    assert host_asc == sorted(host_asc, key=lambda h: _idx[HostingModel(h)])
    assert host_desc == list(reversed(host_asc))
    assert host_asc[0] == HostingModel.on_premise.value  # vroegst in de enum
    # Afgeleide kolom (Laag) is geen sorteerveld → geweigerd (route geeft 400).
    assert onbekend is not None
