"""Tests — ADR-023 Fase E (E1): Plateau + plateau-lidmaatschap.

Offline: model/schema/seed/audit-allowlist + de regressie-borging dat de plateau-laag
de engine NIET raakt (score blijft de enige lifecycle-driver). Live (skip-if-no-DB):
plateau-CRUD, lidmaatschap (component + contract) met dispositie + contractuele
bevestiging (server-side wie/wanneer), RLS-isolatie, audit-capture. Live-tests ruimen
hun eigen element-rijen structureel op (V009-follow-up a).
"""
import asyncio
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
_TID_B = "22222222-2222-2222-2222-222222222222"
_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"


# ── Offline: model + schema ──────────────────────────────────────────────────────

def test_plateau_is_element_subtype_composiet_fk():
    from models.models import Plateau

    assert Plateau.__tablename__ == "plateau"
    fks = [
        sorted(c.name for c in con.columns)
        for con in Plateau.__table__.constraints
        if con.__class__.__name__ == "ForeignKeyConstraint"
    ]
    assert ["id", "tenant_id"] in fks  # shared-PK → element(tenant_id,id)
    kols = Plateau.__table__.columns
    assert "naam" in kols and "toelichting" in kols


def test_plateau_lid_schema_validatie():
    from pydantic import ValidationError
    from schemas.plateau import PlateauLidCreate

    ok = PlateauLidCreate(lid_id=uuid.uuid4(), dispositie="migreren")
    assert ok.contractueel_bevestigd is False  # default

    with pytest.raises(ValidationError):  # negatief aantal geweigerd
        PlateauLidCreate(lid_id=uuid.uuid4(), dispositie="migreren", bevestigd_aantal_gebruikers=-1)
    with pytest.raises(ValidationError):  # extra veld verboden
        PlateauLidCreate(lid_id=uuid.uuid4(), dispositie="migreren", onbekend="x")


# ── Offline: dispositie-catalogus + aggregation-kenmerken ────────────────────────

def test_dispositie_in_relatiekenmerk_catalogus_niet_in_contractconfig():
    """Correctie v2: dispositie hoort in de algemene relatie-kenmerk-catalogus, NIET in
    de contract-configuratie. De contract-keuzelijsten blijven ongemoeid."""
    from models.models import ContractConfigDimensie
    from services.seed_contractconfig import bouw_contractconfig
    from services.seed_relatiekenmerk import bouw_relatiekenmerk

    from models.models import RelatieKenmerkDimensie

    rk = bouw_relatiekenmerk()
    # In de relatie-kenmerk-catalogus: dispositie én (sinds de consistentie-opruim) relatie_rol.
    disp = [r["optie_sleutel"] for r in rk if r["dimensie"] == RelatieKenmerkDimensie.dispositie]
    rol = [r["optie_sleutel"] for r in rk if r["dimensie"] == RelatieKenmerkDimensie.relatie_rol]
    assert disp == ["behouden", "migreren", "vervangen", "uitfaseren"]
    assert rol == ["valt_onder", "onderhoud", "hosting"]
    # NIET (meer) in de contractconfig — die draagt uitsluitend dekking + kostenmodel.
    assert {d.value for d in ContractConfigDimensie} == {"dekking", "kostenmodel"}
    assert all(
        str(r["dimensie"]).split(".")[-1] in {"dekking", "kostenmodel"}
        for r in bouw_contractconfig()
    )


def test_aggregation_dispositie_verwijst_naar_relatiekenmerk_catalogus():
    from services.seed_componentconfig import bouw_componentconfig

    aggr = next(
        r for r in bouw_componentconfig()
        if r["dimensie"].value == "archimate_relatie" and r["optie_sleutel"] == "aggregation"
    )
    kd = aggr["kenmerk_definitie"]
    # dispositie = catalogus, gerouteerd naar de relatiekenmerk-catalogus (niet ContractConfig).
    assert kd["dispositie"] == {
        "type": "catalogus", "catalogus": "relatiekenmerk", "dimensie": "dispositie",
    }
    # Contractuele bevestiging = registratie (niet gevalideerd/vergeleken).
    for sleutel in ("contractueel_bevestigd", "bevestigd_aantal_gebruikers", "bevestigd_door", "bevestigd_op"):
        assert kd[sleutel]["type"] == "registratie"


def test_relatiekenmerk_catalog_valideert_dispositie():
    """De nieuwe relatie-kenmerk-catalogus valideert dispositie-sleutels (geldig ok,
    onbekend ⇒ 422 ONGELDIGE_OPTIE)."""
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from models.models import RelatieKenmerkDimensie
    from services import relatiekenmerk_catalog as rk
    from services.errors import OngeldigeRegistratie

    rows = [SimpleNamespace(optie_sleutel="migreren", label="Migreren", actief=True)]
    session = AsyncMock()
    session.execute.return_value = SimpleNamespace(all=lambda: rows)

    asyncio.run(rk.valideer_sleutels(session, RelatieKenmerkDimensie.dispositie, ["migreren"]))
    with pytest.raises(OngeldigeRegistratie):
        asyncio.run(rk.valideer_sleutels(session, RelatieKenmerkDimensie.dispositie, ["onbekend"]))


# ── Offline: audit-allowlist + RBAC ──────────────────────────────────────────────

def test_plateau_in_audit_allowlist():
    from app.core.audit import AUDIT_TENANT_ENTITEITEN

    assert "plateau" in AUDIT_TENANT_ENTITEITEN


def test_plateau_in_rbac_inhoud_patroon():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    assert heeft_permissie(["medewerker"], Entiteit.PLATEAU, Actie.AANMAKEN)
    assert heeft_permissie(["beheerder"], Entiteit.PLATEAU, Actie.VERWIJDEREN)
    assert not heeft_permissie(["viewer"], Entiteit.PLATEAU, Actie.AANMAKEN)
    assert heeft_permissie(["viewer"], Entiteit.PLATEAU, Actie.LEZEN)


# ── Offline: REGRESSIE — de plateau-laag raakt de engine NIET ────────────────────

def test_plateau_service_raakt_engine_niet():
    """Score blijft de enige lifecycle-driver: de plateau-service importeert géén
    engine-onderdeel (geen tweede driver via de migratielaag). Import-afwezigheid is
    een harder bewijs dan een tekstscan (die over docstrings zou struikelen)."""
    import services.plateau_service as ps

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(ps, naam), f"plateau_service mag de engine niet importeren: {naam!r}"


def test_bevestiging_kenmerken_stempelt_server_side():
    """`contractueel_bevestigd=ja` stempelt wie/wanneer uit de actor-context (registratie);
    `nee` zet géén stempel."""
    from services.plateau_service import _bevestiging_kenmerken

    atok = zet_audit_context("test:bert", "bert@vancapelle.com")
    try:
        ja = _bevestiging_kenmerken(True, 250)
        assert ja["contractueel_bevestigd"] is True
        assert ja["bevestigd_aantal_gebruikers"] == 250
        assert ja["bevestigd_door"] == "bert@vancapelle.com"
        assert ja["bevestigd_op"]  # ISO-timestamp aanwezig
        nee = _bevestiging_kenmerken(False, None)
        assert nee == {"contractueel_bevestigd": False}  # geen stempel, geen aantal
    finally:
        reset_audit_context(atok)


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

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


async def _run_rls(tenant, actor, fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_CD_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    ttok = zet_tenant_context(tenant)
    atok = zet_audit_context(actor, f"{actor}@test")
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_audit_context(atok)
        reset_tenant_context(ttok)
        await eng.dispose()


async def _maak_component(s, tid, naam):
    """Maak een kale database-component direct (element + component) als testlid."""
    from models.models import Component, Element, ElementType, HostingModel

    elem = Element(tenant_id=tid, element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    comp = Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="database",
                     hostingmodel=HostingModel.on_premise, eigenaar_organisatie="WT-Test")
    s.add(comp)
    await s.flush()
    return elem.id


async def _maak_contract(s, tid, naam):
    """Maak een contract direct (leverancier + element + contract) als testlid."""
    from models.models import Contract, ContractType, Element, ElementType, Leverancier

    lev = Leverancier(tenant_id=tid, naam=f"{naam}-lev")
    s.add(lev)
    await s.flush()
    elem = Element(tenant_id=tid, element_type=ElementType.contract)
    s.add(elem)
    await s.flush()
    con = Contract(id=elem.id, tenant_id=tid, leverancier_id=lev.id,
                   contracttype=ContractType.los_contract, contractnaam=naam)
    s.add(con)
    await s.flush()
    return elem.id, lev.id


@integratie
def test_plateau_lidmaatschap_component_en_contract_live():
    from sqlalchemy import text as _text
    from schemas.plateau import PlateauCreate, PlateauLidCreate, PlateauLidUpdate
    from services import plateau_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        opgeruimd_ids = []
        try:
            plateau = await svc.maak_aan(s, _TID, PlateauCreate(naam="WT-Plateau Huidig", toelichting="test"))
            opgeruimd_ids.append(plateau["id"])
            comp_id = await _maak_component(s, tid, "WT-Plateau-comp")
            con_id, lev_id = await _maak_contract(s, tid, "WT-Plateau-contract")
            await s.commit()
            opgeruimd_ids += [comp_id, con_id]

            # Component-lid met dispositie 'migreren', niet contractueel bevestigd.
            lid_comp = await svc.maak_lid(
                s, _TID, plateau["id"],
                PlateauLidCreate(lid_id=comp_id, dispositie="migreren"),
            )
            # Contract-lid met dispositie 'behouden' + contractuele bevestiging (250 gebruikers).
            lid_con = await svc.maak_lid(
                s, _TID, plateau["id"],
                PlateauLidCreate(lid_id=con_id, dispositie="behouden",
                                 contractueel_bevestigd=True, bevestigd_aantal_gebruikers=250),
            )
            leden = await svc.lijst_leden(s, _TID, plateau["id"])

            # Bevestiging wissen via update → stempels weg.
            na_update = await svc.werk_lid_bij(
                s, _TID, plateau["id"], lid_con["id"],
                PlateauLidUpdate(contractueel_bevestigd=False),
            )

            # Audit: plateau-create + de twee aggregation-lidmaatschapsrelaties geregistreerd.
            audit_plateau = (await s.execute(_text(
                "SELECT count(*) FROM audit_log WHERE entiteit_type='plateau' AND entiteit_id=:i"
            ), {"i": str(plateau["id"])})).scalar()
            audit_rel = (await s.execute(_text(
                "SELECT count(*) FROM audit_log WHERE entiteit_type='relatie' AND entiteit_id IN (:a,:b)"
            ), {"a": str(lid_comp["id"]), "b": str(lid_con["id"])})).scalar()

            return {
                "comp": lid_comp, "con": lid_con, "leden": leden,
                "na_update": na_update, "audit_plateau": audit_plateau, "audit_rel": audit_rel,
            }
        finally:
            # Structurele opruim: verwijder de element-rijen (cascade subtype + relaties)
            # + de losse leverancier. Laat geen residu achter (V009-follow-up a).
            for eid in opgeruimd_ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            try:
                await s.execute(_text("DELETE FROM leverancier WHERE naam LIKE 'WT-Plateau%'"))
            except Exception:
                pass
            await s.commit()

    r = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert r["comp"]["dispositie"] == "migreren" and r["comp"]["lid_element_type"] == "component"
    assert r["comp"]["dispositie_label"] == "Migreren"
    assert r["con"]["lid_element_type"] == "contract"
    assert r["con"]["contractueel_bevestigd"] is True
    assert r["con"]["bevestigd_aantal_gebruikers"] == 250
    assert r["con"]["bevestigd_door"] == "test:bert@test"  # server-side actor (harness-email)
    assert r["con"]["bevestigd_op"]
    assert len(r["leden"]) == 2
    assert r["na_update"]["contractueel_bevestigd"] is False
    assert r["na_update"]["bevestigd_door"] is None and r["na_update"]["bevestigd_op"] is None
    assert r["audit_plateau"] >= 1 and r["audit_rel"] >= 2


@integratie
def test_plateau_rls_isolatie_live():
    from sqlalchemy import text as _text
    from schemas.plateau import PlateauCreate
    from services import plateau_service as svc

    async def _maak(s):
        p = await svc.maak_aan(s, _TID, PlateauCreate(naam="WT-Plateau-RLS"))
        return p["id"]

    async def _zicht_b(s, pid):
        return (await s.execute(_text("SELECT count(*) FROM plateau WHERE id=:i"), {"i": str(pid)})).scalar()

    async def _ruim(s, pid):
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(pid)})
        await s.commit()

    pid = asyncio.run(_run_rls(_TID, "test:bert", _maak))
    try:
        zicht_b = asyncio.run(_run_rls(_TID_B, "test:bert", lambda s: _zicht_b(s, pid)))
        zicht_a = asyncio.run(_run_rls(_TID, "test:bert", lambda s: _zicht_b(s, pid)))
    finally:
        asyncio.run(_run_rls(_TID, "test:bert", lambda s: _ruim(s, pid)))
    assert zicht_b == 0  # tenant B ziet plateau van tenant A niet (FORCE RLS)
    assert zicht_a == 1


@integratie
def test_plateau_lid_raakt_lifecycle_niet_live():
    """REGRESSIE live: een component als plateau-lid hangen wijzigt zijn lifecycle niet
    (score blijft de enige driver)."""
    from sqlalchemy import text as _text
    from schemas.plateau import PlateauCreate, PlateauLidCreate
    from services import plateau_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            comp_id = await _maak_component(s, tid, "WT-Plateau-lc")
            await s.commit()
            ids.append(comp_id)
            # Kale database-component: geen profiel → geen lifecycle. Bewijs: vóór en ná het
            # lidmaatschap is er geen component_profiel-rij voor dit component.
            voor = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": str(comp_id)})).scalar()
            p = await svc.maak_aan(s, _TID, PlateauCreate(naam="WT-Plateau-lc-p"))
            ids.append(p["id"])
            await svc.maak_lid(s, _TID, p["id"], PlateauLidCreate(lid_id=comp_id, dispositie="behouden"))
            na = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": str(comp_id)})).scalar()
            return voor, na
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    voor, na = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert voor == 0 and na == 0  # geen profiel/engine-state ontstaan door het lidmaatschap
