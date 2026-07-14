"""Tests — ADR-023 Fase E (E4): Gap + gap-leden + readiness-rollup.

Offline: model (element-subtype + 2-ariteit baseline/doel + CHECK), schema, RBAC,
audit-allowlist, de pure readiness-helper, de `_MIGRATIEKLAAR`-constante-synchroniteit én
de **engine-import-afwezigheid** (dubbele regressie-borging deel a). Live (skip-if-no-DB):
CRUD, baseline≠doel (422), plateau-type-validatie (422), leden (component/contract,
ONGELDIG_LID, LID_BESTAAT), de twee gescheiden readiness-cijfers (technisch: profiel +
migratieklaar; contractueel: doel-plateau-bevestiging), lege noemer ⇒ percentage None,
RLS-isolatie en de **live engine-borging** (geen component_profiel ontstaat/muteert).
Live-tests ruimen hun element-rijen + relaties structureel op — residu-check 0.
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
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline: model + schema ──────────────────────────────────────────────────────

def test_gap_is_element_subtype_met_2_ariteit():
    from models.models import Gap

    assert Gap.__tablename__ == "gap"
    fks = [
        sorted(c.name for c in con.columns)
        for con in Gap.__table__.constraints
        if con.__class__.__name__ == "ForeignKeyConstraint"
    ]
    assert ["id", "tenant_id"] in fks  # shared-PK → element(tenant_id,id)
    assert ["baseline_plateau_id", "tenant_id"] in fks  # 2-ariteit: baseline → element
    assert ["doel_plateau_id", "tenant_id"] in fks       # 2-ariteit: doel → element
    kols = Gap.__table__.columns
    assert "naam" in kols and "toelichting" in kols
    assert kols["baseline_plateau_id"].nullable is False
    assert kols["doel_plateau_id"].nullable is False
    # DB-CHECK baseline <> doel als backstop op de service-validatie.
    checks = [c.name for c in Gap.__table__.constraints if c.__class__.__name__ == "CheckConstraint"]
    assert "ck_gap_baseline_ne_doel" in checks


def test_gap_schema_validatie():
    from pydantic import ValidationError
    from schemas.gap import GapCreate, GapLidCreate, GapUpdate

    GapCreate(naam="Kloof Huidig→Doel", baseline_plateau_id=uuid.uuid4(), doel_plateau_id=uuid.uuid4())
    with pytest.raises(ValidationError):
        GapCreate(naam="  ", baseline_plateau_id=uuid.uuid4(), doel_plateau_id=uuid.uuid4())
    with pytest.raises(ValidationError):  # extra veld verboden
        GapCreate(naam="x", baseline_plateau_id=uuid.uuid4(), doel_plateau_id=uuid.uuid4(), onbekend="y")
    with pytest.raises(ValidationError):
        GapLidCreate(lid_id="geen-uuid")
    # UX-A4-4-aanvulling: baseline/doel zijn nu óók wijzigbaar (naast naam/toelichting).
    assert set(GapUpdate.model_fields) == {"naam", "toelichting", "baseline_plateau_id", "doel_plateau_id"}


# ── Offline: RBAC + audit ────────────────────────────────────────────────────────

def test_gap_in_audit_allowlist():
    from app.core.audit import AUDIT_TENANT_ENTITEITEN

    assert "gap" in AUDIT_TENANT_ENTITEITEN


def test_gap_in_rbac_inhoud_patroon():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    assert heeft_permissie(["medewerker"], Entiteit.GAP, Actie.AANMAKEN)
    assert heeft_permissie(["beheerder"], Entiteit.GAP, Actie.VERWIJDEREN)
    assert not heeft_permissie(["viewer"], Entiteit.GAP, Actie.AANMAKEN)
    assert heeft_permissie(["auditor"], Entiteit.GAP, Actie.LEZEN)
    assert heeft_permissie(["viewer"], Entiteit.GAP, Actie.LEZEN)


# ── Offline: REGRESSIE — de gap-laag raakt de engine NIET (borging deel a) ────────

def test_gap_service_raakt_engine_niet():
    """Score blijft de enige lifecycle-driver: de gap-service importeert géén engine-
    onderdeel. Import-afwezigheid is een harder bewijs dan een tekstscan (die over
    docstrings/SQL-strings zou struikelen)."""
    import services.gap_service as gs

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(gs, naam), f"gap_service mag de engine niet importeren: {naam!r}"


def test_migratieklaar_constante_in_sync_met_enum():
    """De string-constante (gekozen om de engine-enum niet te hoeven importeren) moet
    exact `LifecycleStatus.migratieklaar` spiegelen — borgt tegen stille drift."""
    from models.models import LifecycleStatus
    from services.gap_service import _MIGRATIEKLAAR

    assert _MIGRATIEKLAAR == LifecycleStatus.migratieklaar.value


# ── Offline: pure readiness-helper (geen DB) ──────────────────────────────────────

def test_cijfer_helper_lege_en_gevulde_noemer():
    from services.gap_service import _cijfer

    # Lege noemer ⇒ percentage None (niet 0), aantallen 0.
    assert _cijfer(0, 0) == {"aantal_klaar": 0, "aantal_totaal": 0, "percentage": None}
    # Gevuld: percentage = klaar/totaal × 100, afgerond op 1 decimaal.
    assert _cijfer(1, 2) == {"aantal_klaar": 1, "aantal_totaal": 2, "percentage": 50.0}
    assert _cijfer(1, 3)["percentage"] == 33.3
    assert _cijfer(3, 3)["percentage"] == 100.0


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

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


async def _run_rls(tenant, actor, fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_LK_APP_URL)
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


async def _maak_component(s, tid, naam, status=None):
    """Component (element + component); optioneel met een component_profiel (lifecycle-state)."""
    from models.models import Component, ComponentProfiel, Element, ElementType, HostingModel

    elem = Element(tenant_id=tid, element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    comp = Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="database",
                     hostingmodel=HostingModel.on_premise)
    s.add(comp)
    await s.flush()
    if status is not None:
        s.add(ComponentProfiel(id=elem.id, tenant_id=tid, lifecycle_status=status))
        await s.flush()
    return elem.id


async def _maak_contract(s, tid, naam):
    # ADR-024 slice 1: de contract-"leverancier" is een element-backed partij (externe_partij).
    from models.models import Contract, ContractType, Element, ElementType, Partij, PartijAard, PartijScope

    lev_elem = Element(tenant_id=tid, element_type=ElementType.partij)
    s.add(lev_elem)
    await s.flush()
    lev = Partij(id=lev_elem.id, tenant_id=tid, aard=PartijAard.externe_partij, naam=f"{naam}-lev", scope=PartijScope.extern)
    s.add(lev)
    await s.flush()
    elem = Element(tenant_id=tid, element_type=ElementType.contract)
    s.add(elem)
    await s.flush()
    con = Contract(id=elem.id, tenant_id=tid, leverancier_id=lev.id,
                   contracttype=ContractType.los_contract, contractnaam=naam)
    s.add(con)
    await s.flush()
    return elem.id


async def _maak_datatype(s, tid, naam):
    from models.models import Datatype, DatatypeCategorie, Element, ElementType

    elem = Element(tenant_id=tid, element_type=ElementType.datatype)
    s.add(elem)
    await s.flush()
    dt = Datatype(id=elem.id, tenant_id=tid, categorie=DatatypeCategorie.gestructureerd_db,
                  omschrijving=naam)
    s.add(dt)
    await s.flush()
    return elem.id


async def _ruim(s, ids):
    from sqlalchemy import text as _text

    # De gap-baseline/doel-FK's zijn RESTRICT → verwijder eerst de gap-subtype-rijen, zodat
    # de plateau-elementen daarna vrij verwijderbaar zijn (leaf→root). Het gap-element zelf
    # verdwijnt in de element-pass (cascade subtype al weg + association-relaties).
    for eid in ids:
        await s.execute(_text("DELETE FROM gap WHERE id=:i"), {"i": str(eid)})
    for eid in ids:
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    try:
        await s.execute(_text("DELETE FROM element WHERE id IN (SELECT id FROM partij WHERE naam LIKE 'WT-Gap%')"))
    except Exception:
        pass
    await s.commit()


@integratie
def test_gap_crud_en_plateau_validatie_live():
    from schemas.gap import GapCreate
    from schemas.plateau import PlateauCreate
    from services import gap_service as gsvc
    from services import plateau_service as psvc
    from services.errors import OngeldigeRegistratie

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            base = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap Baseline"))
            doel = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap Doel"))
            ids += [base["id"], doel["id"]]
            comp_id = await _maak_component(s, tid, "WT-Gap-comp-val")
            await s.commit()
            ids.append(comp_id)

            gap = await gsvc.maak_aan(s, _TID, GapCreate(
                naam="WT-Gap K1", toelichting="kloof",
                baseline_plateau_id=base["id"], doel_plateau_id=doel["id"],
            ))
            ids.append(gap["id"])
            detail = await gsvc.lees_detail(s, _TID, gap["id"])

            fouten = {}
            try:  # baseline == doel → 422
                await gsvc.maak_aan(s, _TID, GapCreate(
                    naam="WT-Gap zelfde", baseline_plateau_id=base["id"], doel_plateau_id=base["id"]))
            except OngeldigeRegistratie as e:
                fouten["zelfde"] = e.code
            try:  # niet-plateau (component) als baseline → 422
                await gsvc.maak_aan(s, _TID, GapCreate(
                    naam="WT-Gap fout", baseline_plateau_id=comp_id, doel_plateau_id=doel["id"]))
            except OngeldigeRegistratie as e:
                fouten["geen_plateau"] = e.code
            return gap, detail, fouten
        finally:
            await _ruim(s, ids)

    gap, detail, fouten = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert gap["naam"] == "WT-Gap K1"
    assert detail["baseline_plateau_id"] == gap["baseline_plateau_id"]
    # Lege gap: beide cijfers leeg (percentage None, aantallen 0); nooit vermengd.
    assert detail["readiness_technisch"] == {"aantal_klaar": 0, "aantal_totaal": 0, "percentage": None}
    assert detail["readiness_contractueel"] == {"aantal_klaar": 0, "aantal_totaal": 0, "percentage": None}
    assert fouten == {"zelfde": "BASELINE_GELIJK_AAN_DOEL", "geen_plateau": "ONGELDIG_PLATEAU"}


@integratie
def test_gap_baseline_doel_wijzigen_live():
    """UX-A4-4-aanvulling: baseline/doel wijzigen via update (happy + baseline=doel 422 +
    niet-plateau 422), met behoud van de gekoppelde leden."""
    from schemas.gap import GapCreate, GapUpdate
    from schemas.plateau import PlateauCreate
    from services import gap_service as gsvc
    from services import plateau_service as psvc
    from services.errors import OngeldigeRegistratie

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            base = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-GapW Base"))
            doel = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-GapW Doel"))
            doel2 = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-GapW Doel2"))
            comp_id = await _maak_component(s, tid, "WT-GapW-comp")
            await s.commit()
            ids += [base["id"], doel["id"], doel2["id"], comp_id]

            gap = await gsvc.maak_aan(s, _TID, GapCreate(
                naam="WT-GapW", baseline_plateau_id=base["id"], doel_plateau_id=doel["id"]))
            ids.append(gap["id"])
            lid = await gsvc.maak_lid(s, _TID, gap["id"], comp_id)

            # Happy: doel verleggen naar doel2.
            na = await gsvc.werk_bij(s, _TID, gap["id"], GapUpdate(doel_plateau_id=doel2["id"]))
            # Lid behouden?
            leden_na = await gsvc.lijst_leden(s, _TID, gap["id"])

            fouten = {}
            try:  # baseline := huidig doel2 (== doel na update) → 422
                await gsvc.werk_bij(s, _TID, gap["id"], GapUpdate(baseline_plateau_id=doel2["id"]))
            except OngeldigeRegistratie as e:
                fouten["zelfde"] = e.code
            try:  # baseline := een component → 422
                await gsvc.werk_bij(s, _TID, gap["id"], GapUpdate(baseline_plateau_id=comp_id))
            except OngeldigeRegistratie as e:
                fouten["geen_plateau"] = e.code
            return na, [l["lid_id"] for l in leden_na], fouten, lid["lid_id"]
        finally:
            await _ruim(s, ids)

    na, leden_na, fouten, lid_id = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert na["doel_plateau_id"] is not None  # doel verlegd
    assert leden_na == [lid_id]  # leden behouden bij het wijzigen van het doel
    assert fouten == {"zelfde": "BASELINE_GELIJK_AAN_DOEL", "geen_plateau": "ONGELDIG_PLATEAU"}


@integratie
def test_gap_leden_live():
    from schemas.gap import GapCreate
    from schemas.plateau import PlateauCreate
    from services import gap_service as gsvc
    from services import plateau_service as psvc
    from services.errors import OngeldigeRegistratie, RegistratieConflict

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            base = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap-Led Baseline"))
            doel = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap-Led Doel"))
            comp_id = await _maak_component(s, tid, "WT-Gap-led-comp")
            con_id = await _maak_contract(s, tid, "WT-Gap-led-con")
            dt_id = await _maak_datatype(s, tid, "WT-Gap-led-dt")
            await s.commit()
            ids += [base["id"], doel["id"], comp_id, con_id, dt_id]

            gap = await gsvc.maak_aan(s, _TID, GapCreate(
                naam="WT-Gap-Led", baseline_plateau_id=base["id"], doel_plateau_id=doel["id"]))
            ids.append(gap["id"])
            lid_comp = await gsvc.maak_lid(s, _TID, gap["id"], comp_id)
            lid_con = await gsvc.maak_lid(s, _TID, gap["id"], con_id)
            leden = await gsvc.lijst_leden(s, _TID, gap["id"])

            fouten = {}
            try:  # datatype is geen toegestaan lid → 422
                await gsvc.maak_lid(s, _TID, gap["id"], dt_id)
            except OngeldigeRegistratie as e:
                fouten["lid_type"] = e.code
            try:  # dubbel → 409
                await gsvc.maak_lid(s, _TID, gap["id"], comp_id)
            except RegistratieConflict as e:
                fouten["dubbel"] = e.code

            # Lid verwijderen werkt.
            await gsvc.verwijder_lid(s, _TID, gap["id"], lid_con["id"])
            na = await gsvc.lijst_leden(s, _TID, gap["id"])
            return lid_comp, lid_con, leden, fouten, na
        finally:
            await _ruim(s, ids)

    lid_comp, lid_con, leden, fouten, na = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert lid_comp["lid_element_type"] == "component" and lid_comp["naam"] == "WT-Gap-led-comp"
    assert lid_con["lid_element_type"] == "contract" and lid_con["naam"] == "WT-Gap-led-con"
    assert {l["lid_element_type"] for l in leden} == {"component", "contract"}
    assert fouten == {"lid_type": "ONGELDIG_LID", "dubbel": "LID_BESTAAT"}
    assert [l["lid_id"] for l in na] == [lid_comp["lid_id"]]  # contract-lid verwijderd


@integratie
def test_gap_readiness_technisch_live():
    """Technisch: noemer = component-leden mét lifecycle-state; teller = migratieklaar.
    Component-lid zonder profiel valt buiten de noemer."""
    from models.models import LifecycleStatus
    from schemas.gap import GapCreate
    from schemas.plateau import PlateauCreate
    from services import gap_service as gsvc
    from services import plateau_service as psvc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            base = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap-Tech Baseline"))
            doel = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap-Tech Doel"))
            klaar = await _maak_component(s, tid, "WT-Gap-tech-klaar", LifecycleStatus.migratieklaar)
            niet = await _maak_component(s, tid, "WT-Gap-tech-niet", LifecycleStatus.in_inventarisatie)
            geen_profiel = await _maak_component(s, tid, "WT-Gap-tech-geenprofiel")  # buiten noemer
            await s.commit()
            ids += [base["id"], doel["id"], klaar, niet, geen_profiel]

            gap = await gsvc.maak_aan(s, _TID, GapCreate(
                naam="WT-Gap-Tech", baseline_plateau_id=base["id"], doel_plateau_id=doel["id"]))
            ids.append(gap["id"])
            for c in (klaar, niet, geen_profiel):
                await gsvc.maak_lid(s, _TID, gap["id"], c)
            detail = await gsvc.lees_detail(s, _TID, gap["id"])
            return detail
        finally:
            await _ruim(s, ids)

    detail = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    # 2 component-leden mét profiel (geen_profiel valt buiten de noemer); 1 migratieklaar.
    assert detail["readiness_technisch"] == {"aantal_klaar": 1, "aantal_totaal": 2, "percentage": 50.0}
    # Geen contract-leden ⇒ contractueel leeg (gescheiden, niet vermengd).
    assert detail["readiness_contractueel"]["percentage"] is None


@integratie
def test_gap_readiness_contractueel_live():
    """Contractueel: noemer = contract-leden mét doel-plateau-lidmaatschap; teller = bevestigd.
    Contract-lid zonder doel-plateau-lidmaatschap valt buiten de noemer."""
    from schemas.gap import GapCreate
    from schemas.plateau import PlateauCreate, PlateauLidCreate
    from services import gap_service as gsvc
    from services import plateau_service as psvc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            base = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap-Con Baseline"))
            doel = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap-Con Doel"))
            con_ja = await _maak_contract(s, tid, "WT-Gap-con-ja")
            con_nee = await _maak_contract(s, tid, "WT-Gap-con-nee")
            con_los = await _maak_contract(s, tid, "WT-Gap-con-los")  # geen doel-plateau-lid → buiten noemer
            await s.commit()
            ids += [base["id"], doel["id"], con_ja, con_nee, con_los]

            # Doel-plateau-lidmaatschap (de ENIGE bron van het bevestigd-signaal).
            await psvc.maak_lid(s, _TID, doel["id"],
                                PlateauLidCreate(lid_id=con_ja, contractueel_bevestigd=True))
            await psvc.maak_lid(s, _TID, doel["id"],
                                PlateauLidCreate(lid_id=con_nee, contractueel_bevestigd=False))

            gap = await gsvc.maak_aan(s, _TID, GapCreate(
                naam="WT-Gap-Con", baseline_plateau_id=base["id"], doel_plateau_id=doel["id"]))
            ids.append(gap["id"])
            for c in (con_ja, con_nee, con_los):
                await gsvc.maak_lid(s, _TID, gap["id"], c)
            detail = await gsvc.lees_detail(s, _TID, gap["id"])
            return detail
        finally:
            await _ruim(s, ids)

    detail = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    # con_ja + con_nee in de noemer (doel-plateau-lid); con_los buiten; con_ja bevestigd.
    assert detail["readiness_contractueel"] == {"aantal_klaar": 1, "aantal_totaal": 2, "percentage": 50.0}
    assert detail["readiness_technisch"]["percentage"] is None  # geen component-leden


@integratie
def test_gap_engine_onaangeroerd_live():
    """REGRESSIE live: een gap aanmaken + leden leggen + readiness opvragen doet géén
    component_profiel/lifecycle-state ontstaan of muteren (readiness is read-only afgeleid)."""
    from sqlalchemy import text as _text
    from models.models import LifecycleStatus
    from schemas.gap import GapCreate
    from schemas.plateau import PlateauCreate
    from services import gap_service as gsvc
    from services import plateau_service as psvc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            base = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap-Eng Baseline"))
            doel = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap-Eng Doel"))
            comp = await _maak_component(s, tid, "WT-Gap-eng-comp", LifecycleStatus.in_inventarisatie)
            await s.commit()
            ids += [base["id"], doel["id"], comp]
            voor = (await s.execute(_text(
                "SELECT lifecycle_status FROM component_profiel WHERE id=:i"), {"i": str(comp)})).scalar()
            profiel_voor = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel"))).scalar()

            gap = await gsvc.maak_aan(s, _TID, GapCreate(
                naam="WT-Gap-Eng", baseline_plateau_id=base["id"], doel_plateau_id=doel["id"]))
            ids.append(gap["id"])
            await gsvc.maak_lid(s, _TID, gap["id"], comp)
            await gsvc.lees_detail(s, _TID, gap["id"])  # readiness leest read-only

            na = (await s.execute(_text(
                "SELECT lifecycle_status FROM component_profiel WHERE id=:i"), {"i": str(comp)})).scalar()
            profiel_na = (await s.execute(_text("SELECT count(*) FROM component_profiel"))).scalar()
            # Voor de gap zelf bestaat nooit een profiel (gap is geen checklist-dragend component).
            gap_profiel = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": str(gap["id"])})).scalar()
            return voor, na, profiel_voor, profiel_na, gap_profiel
        finally:
            await _ruim(s, ids)

    voor, na, profiel_voor, profiel_na, gap_profiel = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert voor == na == "in_inventarisatie"   # lifecycle-state ongemoeid
    assert profiel_voor == profiel_na          # geen profiel ontstaan/verdwenen
    assert gap_profiel == 0                     # gap krijgt geen engine-state


@integratie
def test_gap_rls_isolatie_live():
    from sqlalchemy import text as _text
    from schemas.gap import GapCreate
    from schemas.plateau import PlateauCreate
    from services import gap_service as gsvc
    from services import plateau_service as psvc

    async def _maak(s):
        base = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap-RLS Base"))
        doel = await psvc.maak_aan(s, _TID, PlateauCreate(naam="WT-Gap-RLS Doel"))
        gap = await gsvc.maak_aan(s, _TID, GapCreate(
            naam="WT-Gap-RLS", baseline_plateau_id=base["id"], doel_plateau_id=doel["id"]))
        return gap["id"], base["id"], doel["id"]

    async def _zicht(s, gid):
        return (await s.execute(_text("SELECT count(*) FROM gap WHERE id=:i"), {"i": str(gid)})).scalar()

    gid, base_id, doel_id = asyncio.run(_run_rls(_TID, "test:bert", _maak))
    try:
        zicht_b = asyncio.run(_run_rls(_TID_B, "test:bert", lambda s: _zicht(s, gid)))
        zicht_a = asyncio.run(_run_rls(_TID, "test:bert", lambda s: _zicht(s, gid)))
    finally:
        asyncio.run(_run_rls(_TID, "test:bert", lambda s: _ruim(s, [gid, base_id, doel_id])))
    assert zicht_b == 0 and zicht_a == 1
