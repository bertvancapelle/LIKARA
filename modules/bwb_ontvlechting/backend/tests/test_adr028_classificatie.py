"""Tests — ADR-028 slice 1: componentclassificatie (componentrol + BIV).

Offline: model/kolommen, seed-builders, config-schemas + CRUD (mock), systeem-sleutel-
bescherming, RBAC + audit-allowlist, component-schema-velden, en de ENGINE-INVARIANT
(de nieuwe catalogus-modules raken de engine niet; `_valideer_classificatie` is puur).
Live (skip-if-no-DB): catalogus-stand na reseed, create/patch-validatie (422), default-rol,
label-resolutie, en de live engine-invariant (rol/BIV op een niet-beoordeeld type geeft géén
profiel/lifecycle).
"""
import ast
import asyncio
import inspect
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

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


# ── Offline: model + kolommen ────────────────────────────────────────────────────
def test_catalogus_modellen_geen_rls_geen_tenant():
    from models.models import BivSchaalOptie, ComponentrolOptie

    for model in (ComponentrolOptie, BivSchaalOptie):
        kols = model.__table__.columns
        assert {"id", "optie_sleutel", "label", "volgorde", "actief"} <= set(kols.keys())
        assert "tenant_id" not in kols  # platform-breed, geen RLS
        uniques = [
            tuple(c.name for c in con.columns)
            for con in model.__table__.constraints
            if con.__class__.__name__ == "UniqueConstraint"
        ]
        assert ("optie_sleutel",) in uniques


def test_component_vier_classificatie_kolommen():
    from models.models import Component

    kols = Component.__table__.columns
    rol = kols["componentrol"]
    assert rol.type.length == 60 and rol.nullable is False
    assert "interne_applicatie" in str(rol.server_default.arg)
    for veld in ("biv_beschikbaarheid", "biv_integriteit", "biv_vertrouwelijkheid"):
        assert kols[veld].nullable is True and kols[veld].server_default is None


# ── Offline: seed-builders ───────────────────────────────────────────────────────
def test_seed_componentrol_vier_incl_beschermde_default():
    from services.seed_componentrol import bouw_componentrol

    rijen = bouw_componentrol()
    sleutels = [r["optie_sleutel"] for r in rijen]
    assert sleutels == [
        "interne_applicatie", "interne_dataprovider", "externe_dataprovider", "koppelvlak"
    ]
    assert rijen[0]["optie_sleutel"] == "interne_applicatie"  # de beschermde default vooraan


def test_seed_bivschaal_drie_ordinaal():
    from services.seed_bivschaal import bouw_bivschaal

    rijen = bouw_bivschaal()
    assert [r["optie_sleutel"] for r in rijen] == ["laag", "midden", "hoog"]
    # ORDINAAL: volgorde 0<1<2 draagt laag<midden<hoog (filter "hoog en hoger" vergelijkt volgorde).
    assert [r["volgorde"] for r in rijen] == [0, 1, 2]


# ── Offline: config-schemas + service-CRUD (beide catalogi) ──────────────────────
_MODS = ["componentrolconfig", "bivschaalconfig"]


def _result(val):
    r = MagicMock()
    r.scalar_one_or_none.return_value = val
    return r


def _scalar_one(val):
    r = MagicMock()
    r.scalar_one.return_value = val
    return r


def _svc_en_schemas(mod):
    import importlib

    svc = importlib.import_module(f"services.{mod}_service")
    schemas = importlib.import_module(f"schemas.{mod}")
    Create = getattr(schemas, [n for n in dir(schemas) if n.endswith("OptieCreate")][0])
    Update = getattr(schemas, [n for n in dir(schemas) if n.endswith("OptieUpdate")][0])
    return svc, Create, Update


@pytest.mark.parametrize("mod", _MODS)
def test_schema_patroon_en_immutability(mod):
    _, Create, Update = _svc_en_schemas(mod)
    ok = Create(optie_sleutel="nieuw_niveau", label="Nieuw")
    assert ok.optie_sleutel == "nieuw_niveau" and ok.volgorde is None
    for slecht in ("Hoofdletter", "met spatie", "1leading"):
        with pytest.raises(ValidationError):
            Create(optie_sleutel=slecht, label="X")
    assert Update(actief=False).actief is False
    with pytest.raises(ValidationError):  # optie_sleutel immutable (niet in Update)
        Update(optie_sleutel="x")


@pytest.mark.parametrize("mod", _MODS)
def test_voeg_toe_happy_en_duplicaat(mod):
    from services.errors import ConfiguratieConflict

    svc, Create, _ = _svc_en_schemas(mod)
    session = AsyncMock()
    session.execute.side_effect = [_result(None), _scalar_one(4)]  # geen duplicaat, max(volgorde)=4
    session.add = lambda o: None
    asyncio.run(svc.voeg_toe(session, Create(optie_sleutel="nieuw", label="Nieuw")))
    session.commit.assert_awaited()

    session2 = AsyncMock()
    session2.execute.side_effect = [_result(7)]  # sleutel bestaat al
    with pytest.raises(ConfiguratieConflict):
        asyncio.run(svc.voeg_toe(session2, Create(optie_sleutel="bestaat", label="X")))


@pytest.mark.parametrize("mod", _MODS)
def test_wijzig_soft_deactivate_en_404(mod):
    from services.errors import NietGevonden

    svc, _, Update = _svc_en_schemas(mod)
    obj = SimpleNamespace(id=1, optie_sleutel="koppelvlak", label="X", volgorde=0, actief=True)
    session = AsyncMock()
    session.execute.side_effect = [_result(obj)]
    asyncio.run(svc.wijzig(session, 1, Update(actief=False)))
    assert obj.actief is False  # soft-deactivate (geen hard delete)

    session2 = AsyncMock()
    session2.execute.side_effect = [_result(None)]
    with pytest.raises(NietGevonden):
        asyncio.run(svc.wijzig(session2, 999, Update(label="X")))


def test_componentrol_systeem_sleutel_beschermd():
    """`interne_applicatie` mag NIET gedeactiveerd worden (SYSTEEM_SLEUTEL_BESCHERMD);
    label/volgorde wijzigen mag wél; een andere rol deactiveren mag."""
    from schemas.componentrolconfig import ComponentrolOptieUpdate
    from services import componentrolconfig_service as svc
    from services.errors import OngeldigeRegistratie

    beschermd = SimpleNamespace(id=1, optie_sleutel="interne_applicatie", label="Interne applicatie", volgorde=0, actief=True)
    session = AsyncMock()
    session.execute.side_effect = [_result(beschermd)]
    with pytest.raises(OngeldigeRegistratie) as exc:
        asyncio.run(svc.wijzig(session, 1, ComponentrolOptieUpdate(actief=False)))
    assert exc.value.code == "SYSTEEM_SLEUTEL_BESCHERMD"

    # label wijzigen op de systeem-sleutel is toegestaan
    beschermd2 = SimpleNamespace(id=1, optie_sleutel="interne_applicatie", label="Interne applicatie", volgorde=0, actief=True)
    session2 = AsyncMock()
    session2.execute.side_effect = [_result(beschermd2)]
    asyncio.run(svc.wijzig(session2, 1, ComponentrolOptieUpdate(label="Intern")))
    assert beschermd2.label == "Intern"

    # een ANDERE rol deactiveren mag
    ander = SimpleNamespace(id=2, optie_sleutel="koppelvlak", label="Koppelvlak", volgorde=3, actief=True)
    session3 = AsyncMock()
    session3.execute.side_effect = [_result(ander)]
    asyncio.run(svc.wijzig(session3, 2, ComponentrolOptieUpdate(actief=False)))
    assert ander.actief is False


# ── Offline: RBAC + audit-allowlist ──────────────────────────────────────────────
def test_rbac_nieuwe_entiteiten_law_geen_v():
    from app.core.platform_rbac import Actie, PlatformEntiteit, heeft_platform_permissie

    for ent in (PlatformEntiteit.COMPONENTROLCONFIG, PlatformEntiteit.BIVSCHAALCONFIG):
        assert heeft_platform_permissie(["platformbeheerder"], ent, Actie.WIJZIGEN)
        assert heeft_platform_permissie(["platformbeheerder"], ent, Actie.AANMAKEN)
        assert heeft_platform_permissie(["platformoperator"], ent, Actie.LEZEN)
        assert not heeft_platform_permissie(["platformoperator"], ent, Actie.WIJZIGEN)
        for rol in ("platformbeheerder", "platformoperator"):
            assert not heeft_platform_permissie([rol], ent, Actie.VERWIJDEREN)


def test_audit_platform_allowlist_bevat_catalogi():
    from app.core.audit import AUDIT_PLATFORM_ENTITEITEN, AUDIT_TENANT_ENTITEITEN

    assert "componentrol_optie" in AUDIT_PLATFORM_ENTITEITEN
    assert "biv_schaal_optie" in AUDIT_PLATFORM_ENTITEITEN
    # De vier component-kolommen belanden via het bestaande component-spoor in de tenant-audit.
    assert "component" in AUDIT_TENANT_ENTITEITEN


# ── Offline: component-schema-velden ─────────────────────────────────────────────
def test_component_schemas_rol_default_en_biv_optioneel():
    from schemas.component import ComponentCreate, ComponentLijstItem, ComponentRead

    c = ComponentCreate(naam="X", componenttype="applicatie")
    assert c.componentrol == "interne_applicatie"
    assert c.biv_beschikbaarheid is None and c.biv_vertrouwelijkheid is None
    with pytest.raises(ValidationError):  # extra='forbid'
        ComponentCreate(naam="X", componenttype="applicatie", onbekend=1)
    for veld in ("componentrol", "rol_label", "biv_integriteit", "biv_integriteit_label"):
        assert veld in ComponentRead.model_fields
        assert veld in ComponentLijstItem.model_fields


# ── Offline: ENGINE-INVARIANT (classificatie voedt de engine niet) ───────────────
_ENGINE_NAMEN = ("lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
                 "ComponentProfiel", "Blokkade", "Checklistscore")


@pytest.mark.parametrize("modname", [
    "services.componentrol_catalog", "services.bivschaal_catalog",
    "services.componentrolconfig_service", "services.bivschaalconfig_service",
    "services.seed_componentrol", "services.seed_bivschaal",
])
def test_catalogus_modules_raken_engine_niet(modname):
    import importlib

    bron = inspect.getsource(importlib.import_module(modname))
    for naam in _ENGINE_NAMEN:
        assert naam not in bron, f"{modname} verwijst naar engine-symbool {naam!r}"


def test_valideer_classificatie_is_puur():
    """`component_service` raakt de engine elders WEL — daarom een function-bronscan
    (docstring gestript) op de classificatie-validatie zelf: geen engine-symbolen."""
    from services import component_service

    src = inspect.getsource(component_service._valideer_classificatie)
    tree = ast.parse(src)
    # strip de docstring zodat toelichting niet meetelt
    func = tree.body[0]
    if (func.body and isinstance(func.body[0], ast.Expr)
            and isinstance(func.body[0].value, ast.Constant)):
        func.body = func.body[1:]
    code = ast.unparse(tree)
    for naam in _ENGINE_NAMEN + ("herbereken", "profiel", "ComponentProfiel"):
        assert naam not in code, f"_valideer_classificatie verwijst naar {naam!r}"


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


async def _run_rls(fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    ttok = zet_tenant_context(_TID)
    atok = zet_audit_context("test:adr028", "adr028@test")
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_audit_context(atok)
        reset_tenant_context(ttok)
        await eng.dispose()


@integratie
def test_catalogi_geseed_na_reseed():
    from sqlalchemy import text as _t

    async def _flow(s):
        rollen = (await s.execute(_t(
            "SELECT optie_sleutel FROM componentrol_optie ORDER BY volgorde"))).scalars().all()
        biv = (await s.execute(_t(
            "SELECT optie_sleutel, volgorde FROM biv_schaal_optie ORDER BY volgorde"))).all()
        return list(rollen), [(r[0], r[1]) for r in biv]

    rollen, biv = asyncio.run(_run_rls(_flow))
    assert rollen == ["interne_applicatie", "interne_dataprovider", "externe_dataprovider", "koppelvlak"]
    assert biv == [("laag", 0), ("midden", 1), ("hoog", 2)]


@integratie
def test_opties_endpoint_levert_rol_en_biv_ordinaal():
    """ADR-028 slice 2 — het component-opties-endpoint levert additief de actieve rol-opties
    en de BIV-niveaus, ordinaal (laag → hoog) op `volgorde`."""
    from services import component_service as cs

    async def _flow(s):
        return await cs.opties(s)

    uit = asyncio.run(_run_rls(_flow))
    rollen = [o["optie_sleutel"] for o in uit["componentrol_opties"]]
    assert rollen == ["interne_applicatie", "interne_dataprovider", "externe_dataprovider", "koppelvlak"]
    biv = [o["optie_sleutel"] for o in uit["biv_niveaus"]]
    assert biv == ["laag", "midden", "hoog"]  # ordinaal op volgorde
    # labels aanwezig voor het dropdown
    assert all("label" in o for o in uit["componentrol_opties"] + uit["biv_niveaus"])


@integratie
def test_create_geldig_en_default_en_labels():
    from schemas.component import ComponentCreate
    from services import component_service as cs
    from sqlalchemy import text as _t

    async def _flow(s):
        ids = []
        try:
            # (a) expliciete rol + BIV → geaccepteerd, labels resolven
            c1 = await cs.maak_aan(s, _TID, ComponentCreate(
                naam="ADR028-a", componenttype="fileshare",
                componentrol="externe_dataprovider", biv_vertrouwelijkheid="hoog"))
            ids.append(c1["id"])
            # (b) geen rol opgegeven → default interne_applicatie; BIV leeg
            c2 = await cs.maak_aan(s, _TID, ComponentCreate(naam="ADR028-b", componenttype="fileshare"))
            ids.append(c2["id"])
            return c1, c2
        finally:
            for i in ids:
                await s.execute(_t("DELETE FROM element WHERE id=:i"), {"i": str(i)})
            await s.commit()

    c1, c2 = asyncio.run(_run_rls(_flow))
    assert c1["componentrol"] == "externe_dataprovider" and c1["rol_label"] == "Externe dataprovider"
    assert c1["biv_vertrouwelijkheid"] == "hoog" and c1["biv_vertrouwelijkheid_label"] == "Hoog"
    assert c1["biv_beschikbaarheid"] is None and c1["biv_beschikbaarheid_label"] is None
    assert c2["componentrol"] == "interne_applicatie" and c2["rol_label"] == "Interne applicatie"
    assert c2["biv_integriteit"] is None


@integratie
def test_create_ongeldige_rol_en_biv_422():
    from schemas.component import ComponentCreate
    from services import component_service as cs
    from services.errors import OngeldigeRegistratie

    async def _flow_rol(s):
        await cs.maak_aan(s, _TID, ComponentCreate(
            naam="ADR028-x", componenttype="fileshare", componentrol="bestaat_niet"))

    async def _flow_biv(s):
        await cs.maak_aan(s, _TID, ComponentCreate(
            naam="ADR028-y", componenttype="fileshare", biv_integriteit="extreem"))

    with pytest.raises(OngeldigeRegistratie) as e1:
        asyncio.run(_run_rls(_flow_rol))
    assert e1.value.code == "ONGELDIGE_ROL"
    with pytest.raises(OngeldigeRegistratie) as e2:
        asyncio.run(_run_rls(_flow_biv))
    assert e2.value.code == "ONGELDIGE_BIV"


@integratie
def test_lijst_filter_rol_in_en_biv_drempel():
    """ADR-028 slice 3 (herzien LI040) — server-side lijst-filter: rol-IN (multi-select) +
    BIV-drempel op de HOOGSTE van de drie assen (`biv_min`, ordinaal op volgorde). Een
    component zonder enige BIV-waarde valt weg bij een drempel, en is vindbaar via
    `biv_ontbreekt` (het registratiegat)."""
    from schemas.component import ComponentCreate
    from services import component_service as cs
    from sqlalchemy import text as _t

    sfx = f"F28{uuid.uuid4().hex[:8]}"

    async def _flow(s):
        ids = []
        try:
            # (a) externe dataprovider, vertrouwelijkheid hoog
            a = await cs.maak_aan(s, _TID, ComponentCreate(
                naam=f"{sfx}-a", componenttype="fileshare",
                componentrol="externe_dataprovider", biv_vertrouwelijkheid="hoog"))
            # (b) interne applicatie, vertrouwelijkheid laag
            b = await cs.maak_aan(s, _TID, ComponentCreate(
                naam=f"{sfx}-b", componenttype="fileshare",
                componentrol="interne_applicatie", biv_vertrouwelijkheid="laag"))
            # (c) externe dataprovider, GEEN vertrouwelijkheid
            c = await cs.maak_aan(s, _TID, ComponentCreate(
                naam=f"{sfx}-c", componenttype="fileshare", componentrol="externe_dataprovider"))
            ids += [a["id"], b["id"], c["id"]]

            async def _namen(**kw):
                items, _ = await cs.lijst(s, _TID, zoek=sfx, limit=50, **kw)
                return {i["naam"] for i in items}

            # rol-IN: alleen de twee externe dataproviders
            rol = await _namen(componentrol=["externe_dataprovider"])
            # LI040 — hoogste-as ≥ midden: alleen 'a' (V=hoog); 'b' (V=laag) + 'c' (leeg) vallen weg
            biv = await _namen(biv_min="midden")
            # LI040 — het registratiegat: exact de componenten zonder enige BIV-waarde
            gat = await _namen(biv_ontbreekt=True)
            # combinatie AND
            combi = await _namen(componentrol=["externe_dataprovider"], biv_min="midden")
            return rol, biv, gat, combi
        finally:
            for i in ids:
                await s.execute(_t("DELETE FROM element WHERE id=:i"), {"i": str(i)})
            await s.commit()

    rol, biv, gat, combi = asyncio.run(_run_rls(_flow))
    assert rol == {f"{sfx}-a", f"{sfx}-c"}
    assert biv == {f"{sfx}-a"}
    assert gat == {f"{sfx}-c"}
    assert combi == {f"{sfx}-a"}


@integratie
def test_lijst_ongeldige_biv_drempel_422():
    from services import component_service as cs
    from services.errors import OngeldigeRegistratie

    async def _flow(s):
        await cs.lijst(s, _TID, biv_min="bestaat_niet", limit=5)

    with pytest.raises(OngeldigeRegistratie) as e:
        asyncio.run(_run_rls(_flow))
    assert e.value.code == "ONGELDIGE_BIV"


def test_landschapskaart_projectie_read_only_bronscan():
    """ADR-028 slice 3 — de kaartprojectie is read-only (geen DB-schrijf) en engine-vrij."""
    import services.landschapskaart_service as lk

    src = inspect.getsource(lk.haal_grafdata_op)
    for verboden in ("session.add(", ".commit(", ".flush(", "session.delete("):
        assert verboden not in src, f"kaartprojectie mag niet schrijven: {verboden}"
    modbron = inspect.getsource(lk)
    for naam in _ENGINE_NAMEN:
        # alléén code (niet docstring/comments): grove check op import-/gebruik-vorm
        assert f"import {naam}" not in modbron and f"{naam}(" not in modbron


@integratie
def test_landschapskaart_node_draagt_rol_en_biv():
    from schemas.component import ComponentCreate
    from services import component_service as cs
    from services import landschapskaart_service as lk
    from sqlalchemy import text as _t

    naam = f"LK28-{uuid.uuid4().hex[:8]}"

    async def _flow(s):
        cid = None
        try:
            c = await cs.maak_aan(s, _TID, ComponentCreate(
                naam=naam, componenttype="applicatie",
                componentrol="externe_dataprovider", biv_vertrouwelijkheid="hoog"))
            cid = c["id"]
            resp = await lk.haal_grafdata_op(s, _TID, component_ids=[cid])
            node = next(n for n in resp.nodes if str(n.id) == str(cid))
            return node.componentrol, node.biv_vertrouwelijkheid
        finally:
            if cid is not None:
                await s.execute(_t("DELETE FROM element WHERE id=:i"), {"i": str(cid)})
                await s.commit()

    rol, bivv = asyncio.run(_run_rls(_flow))
    assert rol == "externe_dataprovider"
    assert bivv == "hoog"


@integratie
def test_patch_rol_en_biv_wissen_en_engine_invariant():
    """Patch een geldige rol/BIV; wis een BIV-veld (registratiegat); en borg live dat rol/BIV
    op een niet-beoordeeld type (fileshare) GÉÉN profiel/lifecycle laat ontstaan."""
    from schemas.component import ComponentCreate, ComponentUpdate
    from services import component_service as cs
    from services.errors import OngeldigeRegistratie
    from sqlalchemy import text as _t

    async def _flow(s):
        cid = None
        try:
            c = await cs.maak_aan(s, _TID, ComponentCreate(
                naam="ADR028-p", componenttype="fileshare",
                componentrol="interne_applicatie", biv_beschikbaarheid="laag"))
            cid = c["id"]
            # geen profiel/lifecycle (fileshare is niet-beoordeeld — rol/BIV veranderen dat niet)
            prof0 = (await s.execute(_t("SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": str(cid)})).scalar()
            # geldige patch
            g = await cs.werk_bij(s, _TID, cid, ComponentUpdate(
                componentrol="koppelvlak", biv_beschikbaarheid=None, biv_integriteit="midden"))
            prof1 = (await s.execute(_t("SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": str(cid)})).scalar()
            # ongeldige patch → 422
            ongeldig = False
            try:
                await cs.werk_bij(s, _TID, cid, ComponentUpdate(componentrol="zzz"))
            except OngeldigeRegistratie as e:
                ongeldig = (e.code == "ONGELDIGE_ROL")
                await s.rollback()
            return prof0, g, prof1, ongeldig
        finally:
            if cid is not None:
                await s.execute(_t("DELETE FROM element WHERE id=:i"), {"i": str(cid)})
                await s.commit()

    prof0, g, prof1, ongeldig = asyncio.run(_run_rls(_flow))
    assert prof0 == 0 and prof1 == 0  # engine-invariant: geen profiel door rol/BIV
    assert g["componentrol"] == "koppelvlak"
    assert g["biv_beschikbaarheid"] is None      # gewist (registratiegat)
    assert g["biv_integriteit"] == "midden"
    assert g["lifecycle_status"] is None          # geen lifecycle (niet-beoordeeld type)
    assert ongeldig
