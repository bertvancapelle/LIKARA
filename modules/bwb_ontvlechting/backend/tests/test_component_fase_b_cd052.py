"""Tests — ADR-021 Fase B component-/structuurrelatie-CRUD (CD052).

Offline-invarianten (subtype-bescherming, self-ref, catalogus-groepering) + live-
integratie (CRUD round-trip, subtype-delete-bescherming, beide-richtingen-structuur)
tegen de geseede cd_app-DB (skip indien onbereikbaar).
"""
import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

_TID = "11111111-1111-1111-1111-111111111111"
_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"


# ── Offline-invarianten ─────────────────────────────────────────────────────────

def test_maak_aan_applicatie_type_convergeert(monkeypatch):
    # CD054b W1: type 'applicatie' via het component-pad wordt NIET geweigerd, maar
    # maakt atomair het subtype met defaults via dezelfde service-kern.
    from models.models import Migratiepad, NiveauEnum
    from schemas.component import ComponentCreate
    from services import applicatie_service, component_service as svc

    vastgelegd = {}

    async def _kern(session, tid, **kw):
        vastgelegd.update(kw)
        return SimpleNamespace(component=SimpleNamespace(id=uuid.uuid4()))

    async def _lees(session, tid, comp):
        return {"id": comp.id, "heeft_applicatie_subtype": True}

    monkeypatch.setattr(applicatie_service, "maak_applicatie_subtype", _kern)
    monkeypatch.setattr(svc, "_lees", _lees)

    out = asyncio.run(svc.maak_aan(AsyncMock(), _TID, ComponentCreate(naam="Nieuwe app", componenttype="applicatie")))
    assert out["heeft_applicatie_subtype"] is True
    assert vastgelegd["naam"] == "Nieuwe app"
    assert vastgelegd["eigenaar_organisatie"] == ""  # leeg toegestaan (bewerkbaar op detail)
    assert vastgelegd["migratiepad"] == Migratiepad.onbekend
    assert vastgelegd["complexiteit"] == NiveauEnum.midden
    assert vastgelegd["prioriteit"] == NiveauEnum.midden


def test_component_sort_allowlist_synchroon():
    # ADR-017 B2: de schema-enum en de service-allowlist blijven 1-op-1.
    from schemas.component import ComponentSorteerveld
    from services import component_service as svc

    assert {e.value for e in ComponentSorteerveld} == set(svc._SORTEERBARE_KOLOMMEN)


def test_werk_bij_weigert_subtype_wijziging(monkeypatch):
    from schemas.component import ComponentUpdate
    from services import component_service as svc
    from services.errors import OngeldigeRegistratie

    async def _als(type_, *a, **k):
        return SimpleNamespace(componenttype=type_)

    # naar applicatie
    monkeypatch.setattr(svc, "haal_op", lambda *a, **k: _als("database"))
    with pytest.raises(OngeldigeRegistratie) as ei:
        asyncio.run(svc.werk_bij(AsyncMock(), _TID, uuid.uuid4(), ComponentUpdate(componenttype="applicatie")))
    assert ei.value.code == "SUBTYPE_BESCHERMD"

    # van applicatie
    monkeypatch.setattr(svc, "haal_op", lambda *a, **k: _als("applicatie"))
    with pytest.raises(OngeldigeRegistratie) as ei2:
        asyncio.run(svc.werk_bij(AsyncMock(), _TID, uuid.uuid4(), ComponentUpdate(componenttype="database")))
    assert ei2.value.code == "SUBTYPE_BESCHERMD"


def test_structuur_weigert_zelfverwijzing():
    from schemas.component_structuur import ComponentStructuurCreate
    from services import component_structuur_service as svc
    from services.errors import OngeldigeRegistratie

    cid = uuid.uuid4()
    with pytest.raises(OngeldigeRegistratie) as ei:
        asyncio.run(svc.maak_aan(AsyncMock(), _TID, ComponentStructuurCreate(
            component_id=cid, op_component_id=cid, relatietype="draait_op")))
    assert ei.value.code == "ZELFVERWIJZING"


def test_componentconfig_opties_groepering():
    from models.models import ComponentConfigDimensie as D
    from services import componentconfig_catalog as catalog

    session = AsyncMock()
    res = MagicMock()
    res.all.return_value = [
        SimpleNamespace(dimensie=D.componenttype, optie_sleutel="database", label="Database", volgorde=1),
        SimpleNamespace(dimensie=D.structuurrelatie_type, optie_sleutel="draait_op", label="Draait op", volgorde=0),
    ]
    session.execute.return_value = res
    out = asyncio.run(catalog.actieve_opties_per_dimensie(session))
    assert set(out) == {d.value for d in D}
    assert out["componenttype"][0] == {"optie_sleutel": "database", "label": "Database"}
    assert out["structuurrelatie_type"][0]["label"] == "Draait op"


# ── Live-integratie (cd_app) ─────────────────────────────────────────────────────

import app.core.database  # noqa: E402,F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context  # noqa: E402


def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_CD_APP_URL)
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


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="cd_app-DB niet bereikbaar (offline)")


async def _sessie_run(fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_CD_APP_URL)
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
        comp = await svc.maak_aan(s, _TID, ComponentCreate(naam=naam, componenttype="database", eigenaar_organisatie="IT"))
        assert comp["heeft_applicatie_subtype"] is False
        assert comp["componenttype_label"] == "Database"
        detail = await svc.lees_detail(s, _TID, comp["id"])
        assert detail["naam"] == naam
        items, _ = await svc.lijst(s, _TID, componenttype="database", limit=50)
        assert any(i["id"] == comp["id"] for i in items)
        await svc.verwijder(s, _TID, comp["id"])  # geen relaties → mag

    asyncio.run(_sessie_run(_flow))


def test_subtype_component_delete_convergeert(monkeypatch):
    # CD054b W1: delete van een subtype via het component-pad delegeert naar het
    # applicatie-delete-pad; alleen een onderlegger-relatie (iets draait OP deze
    # applicatie, op_component_id) blokkeert met 409 IN_GEBRUIK.
    from services import applicatie_service, component_service as svc
    from services.errors import RegistratieConflict

    cid = uuid.uuid4()

    async def _haal(*a, **k):
        return SimpleNamespace(id=cid)

    async def _subtype(*a, **k):
        return True

    monkeypatch.setattr(svc, "haal_op", _haal)
    monkeypatch.setattr(svc, "_heeft_subtype", _subtype)

    # geval 1: onderlegger aanwezig → IN_GEBRUIK
    sess1 = AsyncMock()
    row = MagicMock()
    row.scalar_one_or_none.return_value = uuid.uuid4()
    sess1.execute.return_value = row
    with pytest.raises(RegistratieConflict) as ei:
        asyncio.run(svc.verwijder(sess1, _TID, cid))
    assert ei.value.code == "IN_GEBRUIK"

    # geval 2: geen onderlegger → delegeert naar applicatie_service.verwijder
    gedelegeerd = {}

    async def _verwijder(session, tenant_id, aid):
        gedelegeerd["id"] = aid

    monkeypatch.setattr(applicatie_service, "verwijder", _verwijder)
    sess2 = AsyncMock()
    leeg = MagicMock()
    leeg.scalar_one_or_none.return_value = None
    sess2.execute.return_value = leeg
    asyncio.run(svc.verwijder(sess2, _TID, cid))
    assert gedelegeerd["id"] == cid


@integratie
def test_lijst_levert_besturingsvelden_en_statusfilter():
    # CD054b W1: de verenigde lijst joint het subtype — besturingsvelden gevuld voor
    # applicaties, null voor kale infra; status-filter matcht alleen subtypen.
    from services import component_service as svc

    async def _flow(s):
        items, _ = await svc.lijst(s, _TID, limit=100)
        per_naam = {i["naam"]: i for i in items}
        app = per_naam["Belastingsysteem"]
        infra = per_naam["Oracle FIN-DB"]
        gefilterd, _ = await svc.lijst(s, _TID, limit=100, status=["concept", "in_inventarisatie", "geblokkeerd", "migratieklaar"])
        return app, infra, gefilterd

    app, infra, gefilterd = asyncio.run(_sessie_run(_flow))
    assert app["heeft_applicatie_subtype"] is True
    assert app["lifecycle_status"] is not None and app["complexiteit"] is not None
    assert infra["heeft_applicatie_subtype"] is False
    assert infra["lifecycle_status"] is None and infra["complexiteit"] is None
    # status-filter levert uitsluitend subtypen (kale infra heeft geen lifecycle).
    assert gefilterd and all(i["heeft_applicatie_subtype"] for i in gefilterd)


@integratie
def test_structuur_overzicht_beide_richtingen():
    from sqlalchemy import text
    from services import component_service as svc

    async def _flow(s):
        row = (await s.execute(text("select id from component where naam='Oracle FIN-DB'"))).first()
        ov = await svc.structuur_overzicht(s, _TID, row[0])
        return {x["naam"] for x in ov["gebruikt_door"]}, ov["draait_op"]

    gebruikt_door, draait_op = asyncio.run(_sessie_run(_flow))
    assert {"Belastingsysteem", "Financieel"} <= gebruikt_door  # de DB wordt door beide gebruikt
    assert draait_op == []  # de DB steunt zelf nergens op


@integratie
def test_component_contract_op_niet_applicatie_component():
    """Oracle-licentie-casus: een contract op een database-component (geen applicatie)."""
    from sqlalchemy import text
    from schemas.component import ComponentCreate
    from schemas.component_contract import ComponentContractCreate
    from services import component_contract_service as cc
    from services import component_service

    naam = f"CD052-db-{uuid.uuid4().hex[:8]}"

    async def _flow(s):
        comp = await component_service.maak_aan(
            s, _TID, ComponentCreate(naam=naam, componenttype="database", eigenaar_organisatie="IT")
        )
        cid = (await s.execute(
            text("select id from contract where contractnaam='GeoWorks Licentieovereenkomst'")
        )).first()[0]
        kop = await cc.maak_aan(
            s, _TID, ComponentContractCreate(component_id=comp["id"], contract_id=cid, relatie_rol="valt_onder")
        )
        lijst = await cc.contracten_van_component(s, _TID, comp["id"])
        assert any(r["contract_id"] == cid for r in lijst)
        await cc.verwijder(s, _TID, kop["id"])          # opruimen: koppeling
        await component_service.verwijder(s, _TID, comp["id"])  # dan component
        return True

    assert asyncio.run(_sessie_run(_flow))
