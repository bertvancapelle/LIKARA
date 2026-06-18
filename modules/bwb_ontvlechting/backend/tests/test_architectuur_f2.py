"""Tests — cross-element laagprojectie (ADR-023 Fase F / F-2).

Offline: naam-resolutie per subtype, de typing-branch (catalogus vs. vaste mapping),
engine-import-afwezigheid, RBAC. Live (skip-if-no-DB): de wide cross-element query met
de twee typing-bronnen samengevoegd + de laag/type-filters, met structurele opruim.
"""
import asyncio
import uuid
from types import SimpleNamespace

import pytest

import app.core.audit  # noqa: F401 — registreert de audit-capture-hook
import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"


# ── Offline: naam-resolutie per subtype ──────────────────────────────────────────

def _rij(element_type, **kw):
    from models.models import ElementType
    base = dict(
        id=uuid.uuid4(), element_type=ElementType(element_type), created_at=None,
        component_naam=None, componenttype=None, contract_naam=None,
        datatype_categorie=None, datatype_omschrijving=None,
        gg_org_naam=None, gg_afdeling=None,
        plateau_naam=None, gap_naam=None, wp_naam=None, deliverable_naam=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_naam_resolutie_per_subtype():
    from models.models import DatatypeCategorie
    from services.architectuur_service import _naam, _naam_secundair

    assert _naam(_rij("component", component_naam="Zaaksysteem")) == "Zaaksysteem"
    assert _naam(_rij("contract", contract_naam="Oracle licentie")) == "Oracle licentie"
    assert _naam(_rij("plateau", plateau_naam="Doel")) == "Doel"
    assert _naam(_rij("work_package", wp_naam="WP-1")) == "WP-1"
    # datatype → categorie als primaire naam; omschrijving secundair.
    dt = _rij("datatype", datatype_categorie=DatatypeCategorie.gestructureerd_db, datatype_omschrijving="Klantgegevens")
    assert _naam(dt) == "gestructureerd_db"
    assert _naam_secundair(dt) == "Klantgegevens"
    # gebruikersgroep → organisatie-naam (uit de partij-join, UX-B6-a) (+ afdeling).
    assert _naam(_rij("gebruikersgroep", gg_org_naam="Publiekszaken", gg_afdeling="Burgerzaken")) == "Publiekszaken — Burgerzaken"
    assert _naam(_rij("gebruikersgroep", gg_org_naam="ICT", gg_afdeling=None)) == "ICT"
    # fallback: nooit leeg.
    leeg = _rij("contract", contract_naam=None)
    assert _naam(leeg).startswith("contract ")


def test_typing_branch_catalogus_vs_vaste_mapping():
    from services.architectuur_service import _typing

    # component → catalogus (per componenttype).
    cat = {"database": {"archimate_element": "system_software", "laag": "technology", "aspect": "active"}}
    comp = _rij("component", componenttype="database")
    assert _typing(comp, cat) == cat["database"]
    # niet-component → vaste mapping ELEMENT_ARCHIMATE_TYPING.
    contract = _rij("contract")
    t = _typing(contract, cat)
    assert t["laag"] == "business" and t["aspect"] == "passive"
    wp = _rij("work_package")
    assert _typing(wp, cat)["aspect"] == "behavior"  # bewuste afwijking (work_package = gedrag)


def test_architectuur_service_raakt_engine_niet():
    import services.architectuur_service as a

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(a, naam), f"architectuur_service mag de engine niet importeren: {naam!r}"


def test_architectuur_rbac_alleen_lezen():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    for rol in ("viewer", "medewerker", "beheerder", "auditor"):
        assert heeft_permissie([rol], Entiteit.ARCHITECTUUR, Actie.LEZEN)
        for actie in (Actie.AANMAKEN, Actie.WIJZIGEN, Actie.VERWIJDEREN):
            assert not heeft_permissie([rol], Entiteit.ARCHITECTUUR, actie)


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def test_sorteerveld_allowlist_synchroon_met_enum():
    """De route-enum, de service-allowlist en de waardeparsers blijven 1-op-1 (geen rauwe
    kolomnaam in ORDER BY; geen half toegevoegd sorteerveld)."""
    from schemas.architectuur import ArchitectuurSorteerveld
    from services.architectuur_service import _SORTEERVELDEN, _WAARDE_PARSERS

    assert {e.value for e in ArchitectuurSorteerveld} == set(_SORTEERVELDEN) == set(_WAARDE_PARSERS)


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


async def _run_rls(fn):
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


async def _maak_component(s, tid, naam, componenttype="database"):
    from models.models import Component, Element, ElementType, HostingModel
    elem = Element(tenant_id=tid, element_type=ElementType.component)
    s.add(elem); await s.flush()
    s.add(Component(id=elem.id, tenant_id=tid, naam=naam, componenttype=componenttype,
                    hostingmodel=HostingModel.on_premise))
    await s.flush()
    return elem.id


async def _maak_contract(s, tid, naam):
    from models.models import Contract, ContractType, Element, ElementType, Partij, PartijAard
    lev_elem = Element(tenant_id=tid, element_type=ElementType.partij); s.add(lev_elem); await s.flush()
    lev = Partij(id=lev_elem.id, tenant_id=tid, aard=PartijAard.externe_partij, naam=f"{naam}-lev")
    s.add(lev); await s.flush()
    elem = Element(tenant_id=tid, element_type=ElementType.contract)
    s.add(elem); await s.flush()
    s.add(Contract(id=elem.id, tenant_id=tid, leverancier_id=lev.id,
                   contracttype=ContractType.los_contract, contractnaam=naam))
    await s.flush()
    return elem.id


async def _maak_plateau(s, tid, naam):
    from models.models import Element, ElementType, Plateau
    elem = Element(tenant_id=tid, element_type=ElementType.plateau)
    s.add(elem); await s.flush()
    s.add(Plateau(id=elem.id, tenant_id=tid, naam=naam)); await s.flush()
    return elem.id


async def _ruim(s, ids):
    from sqlalchemy import text as _text
    for eid in ids:
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    try:
        await s.execute(_text("DELETE FROM element WHERE id IN (SELECT id FROM partij WHERE naam LIKE 'WT-F2%')"))
    except Exception:
        pass
    await s.commit()


@integratie
def test_cross_element_projectie_en_filters_live():
    from services import architectuur_service as svc

    tid = uuid.UUID(_TID)

    async def _alle(s, **kw):
        # Pagineer volledig door (de dev-DB kan >1 pagina elementen bevatten).
        out, cursor = [], None
        while True:
            items, cursor = await svc.lijst(s, _TID, limit=100, after=cursor, **kw)
            out += items
            if not cursor:
                return out

    async def _flow(s):
        ids = []
        try:
            comp = await _maak_component(s, tid, "WT-F2-comp")       # technology / active
            con = await _maak_contract(s, tid, "WT-F2-contract")     # business / passive
            pl = await _maak_plateau(s, tid, "WT-F2-plateau")        # implementation_migration / passive
            await s.commit()
            ids += [comp, con, pl]

            per_id = {i["id"]: i for i in await _alle(s)}
            tech = {i["id"] for i in await _alle(s, laag="technology")}
            biz = {i["id"] for i in await _alle(s, laag="business")}
            mig = {i["id"] for i in await _alle(s, type="plateau")}
            return per_id, tech, biz, mig, (comp, con, pl)
        finally:
            await _ruim(s, ids)

    per_id, tech_ids, biz_ids, mig_ids, (comp, con, pl) = asyncio.run(_run_rls(_flow))

    # Projectie per element-type (twee bronnen samengevoegd):
    assert per_id[comp]["laag"] == "technology" and per_id[comp]["naam"] == "WT-F2-comp"
    assert per_id[con]["laag"] == "business" and per_id[con]["aspect"] == "passive"
    assert per_id[con]["naam"] == "WT-F2-contract"  # contractnaam
    assert per_id[pl]["laag"] == "implementation_migration"
    # Laag-filter overspant beide bronnen:
    assert comp in tech_ids and con not in tech_ids
    assert con in biz_ids and comp not in biz_ids
    # Type-filter (element_type):
    assert mig_ids and pl in mig_ids and comp not in mig_ids and con not in mig_ids


@integratie
def test_architectuur_sortering_en_keyset_live():
    """Server-side sorteren op naam (over paginagrenzen, limit=1) + op laag (afgeleid uit
    BEIDE typing-bronnen: contract via de vaste CASE, component via de catalogus)."""
    from services import architectuur_service as svc

    tid = uuid.UUID(_TID)

    async def _collect(s, **kw):
        out, cursor = [], None
        while True:  # limit=1 dwingt de keyset over paginagrenzen heen
            items, cursor = await svc.lijst(s, _TID, limit=1, after=cursor, **kw)
            out += items
            if not cursor:
                return out

    async def _flow(s):
        ids = []
        try:
            a = await _maak_contract(s, tid, "WT-F2s-Alpha")     # business
            b = await _maak_plateau(s, tid, "WT-F2s-Bravo")      # implementation_migration
            c = await _maak_component(s, tid, "WT-F2s-Charlie")  # technology
            await s.commit()
            ids += [a, b, c]
            mijn = lambda lijst: [i for i in lijst if i["naam"].startswith("WT-F2s-")]
            asc = [i["naam"] for i in mijn(await _collect(s, sort="naam", order="asc"))]
            desc = [i["naam"] for i in mijn(await _collect(s, sort="naam", order="desc"))]
            laag = [i["laag"] for i in mijn(await _collect(s, sort="laag", order="asc"))]
            return asc, desc, laag
        finally:
            await _ruim(s, ids)

    asc, desc, laag = asyncio.run(_run_rls(_flow))
    assert asc == ["WT-F2s-Alpha", "WT-F2s-Bravo", "WT-F2s-Charlie"]
    assert desc == ["WT-F2s-Charlie", "WT-F2s-Bravo", "WT-F2s-Alpha"]
    # laag oplopend, afgeleid uit beide bronnen: business < implementation_migration < technology.
    assert laag == ["business", "implementation_migration", "technology"]
