"""Tests — ADR-042 slice 5: roll-up-inzicht + organisatie-proceskijk (pure leeslaag).

Offline: schema-vorm (herkomst-pad + organisatie-procesbeeld), read-only-bronscan van
beide leespaden (geen schrijf-primitieven) en de dubbele engine-borging
(import-afwezigheid op moduleniveau bestaat al; hier per-functie herbevestigd).
Live (skip-if-no-DB): subboom-rollup over meerdere niveaus (herkomst + pad kloppen, de
eigen regels van de wortel doen NIET mee, blad zonder kinderen ⇒ leeg),
organisatie-afleiding (eigendom + gebruik samengenomen, dedupe per proces — ook bij
eigendom+gebruik tegelijk en bij meerdere functies), RLS-isolatie (404 no-leak) en
geen-mutatie-bewijs (tellingen vóór/na de lees-calls identiek). Live-tests ruimen hun
element-rijen structureel op (finally).
"""
import ast
import asyncio
import inspect
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


# ── Offline: schema-vorm ─────────────────────────────────────────────────────────

def test_rollup_schema_draagt_herkomstpad():
    from schemas.procesvervulling import ProcesvervullingUit

    velden = ProcesvervullingUit.model_fields
    assert "proces_pad" in velden
    assert "tak_id" in velden  # groepeersleutel: het directe deelproces van de tak
    # Optioneel: alleen de roll-up-lezing vult pad + tak; de bestaande lezingen niet.
    assert velden["proces_pad"].default is None
    assert velden["tak_id"].default is None


def test_organisatie_proces_schema_vorm():
    from schemas.procesvervulling import OrganisatieProcesComponent, OrganisatieProcesUit

    velden = OrganisatieProcesUit.model_fields
    for veld in ("proces_id", "proces_naam", "proces_ouder_naam", "component_aantal", "componenten"):
        assert veld in velden, f"OrganisatieProcesUit mist veld {veld!r}"
    assert set(OrganisatieProcesComponent.model_fields) == {
        "component_id", "component_naam", "componenttype", "componenttype_label",
    }


# ── Offline: read-only + engine-borging (per functie) ────────────────────────────

def _src_zonder_docstring(fn) -> str:
    """Broncode met de docstring gestript (ast) — een uitleg-docstring die een verboden
    woord noemt geeft dan geen vals-positief (LI022-patroon)."""
    src = inspect.getsource(fn)
    mod = ast.parse(src)
    functie = mod.body[0]
    if (
        functie.body
        and isinstance(functie.body[0], ast.Expr)
        and isinstance(functie.body[0].value, ast.Constant)
        and isinstance(functie.body[0].value.value, str)
    ):
        functie.body = functie.body[1:]
    return ast.unparse(functie)


def test_leespaden_zijn_read_only():
    """De slice-5-paden zijn PURE leespaden: geen enkel schrijf-primitief in de bron."""
    from services import procesvervulling_service as svc

    for fn in (svc.rollup_voor_proces, svc.processen_voor_organisatie):
        src = _src_zonder_docstring(fn)
        for verboden in ("session.add", ".commit(", ".delete(", "insert(", "update(", "delete("):
            assert verboden not in src, (
                f"{fn.__qualname__} bevat {verboden!r} — het roll-up-inzicht is een leeslaag, "
                "er wordt niets opgeslagen of gemuteerd."
            )


def test_leespaden_raken_engine_niet():
    """Dubbele borging naast de bestaande module-import-test: ook de functie-bron zelf
    refereert nergens aan de lifecycle-engine (score blijft de enige driver)."""
    from services import procesvervulling_service as svc

    # Module-brede import-afwezigheid (bestaande invariant, hier herbevestigd).
    for naam in ("lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle"):
        assert not hasattr(svc, naam)
    for fn in (svc.rollup_voor_proces, svc.processen_voor_organisatie):
        src = _src_zonder_docstring(fn)
        for sym in ("herbereken", "bepaal_lifecycle", "Checklistscore", "Blokkade"):
            assert sym not in src


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                res = (await c.execute(text("SELECT to_regclass('procesvervulling')"))).scalar()
            return res is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB/procesvervulling-tabel niet bereikbaar")


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


async def _maak_component(s, naam, eigenaar_organisatie_id=None):
    from models.models import Component, Element, ElementType, HostingModel

    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    s.add(Component(
        id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam, componenttype="database",
        hostingmodel=HostingModel.on_premise, eigenaar_organisatie_id=eigenaar_organisatie_id,
    ))
    await s.commit()
    return elem.id


async def _maak_organisatie(s, naam):
    from models.models import Element, ElementType, Partij, PartijAard, PartijScope

    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.partij)
    s.add(elem)
    await s.flush()
    s.add(Partij(
        id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam,
        aard=PartijAard.organisatie, scope=PartijScope.intern,
    ))
    await s.commit()
    return elem.id


async def _maak_proces(s, naam, ouder_id=None):
    from schemas.proces import ProcesCreate
    from services import proces_service

    return (await proces_service.maak_aan(s, _TID, ProcesCreate(naam=naam, ouder_id=ouder_id)))["id"]


async def _maak_vervulling(s, component_id, proces_id, functie="registreren"):
    from services import procesvervulling_service as svc

    return await svc.maak_aan(s, _TID, component_id, proces_id, functie)


async def _registreer_gebruik(s, organisatie_id, component_id):
    from models.models import Organisatiegebruik

    s.add(Organisatiegebruik(
        tenant_id=uuid.UUID(_TID), organisatie_id=organisatie_id, applicatie_id=component_id,
    ))
    await s.commit()


async def _ruim(s, ids):
    from sqlalchemy import text as _text

    for eid in reversed(ids):
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    await s.commit()


async def _tel(s, tabel):
    from sqlalchemy import text as _text

    return (await s.execute(_text(f"SELECT count(*) FROM {tabel}"))).scalar()


@integratie
def test_rollup_diepe_boom_herkomst_en_leeg_blad_live():
    from services import procesvervulling_service as svc
    from services.errors import NietGevonden

    async def _flow(s):
        ids = []
        try:
            top = await _maak_proces(s, "RU-Test Vergunningverlening")
            ids.append(top)
            a = await _maak_proces(s, "RU-Test Aanvraag behandelen", ouder_id=top)
            ids.append(a)
            b = await _maak_proces(s, "RU-Test Besluit vastleggen", ouder_id=a)
            ids.append(b)
            c1 = await _maak_component(s, "RU-Comp Direct")
            ids.append(c1)
            c2 = await _maak_component(s, "RU-Comp NiveauEen")
            ids.append(c2)
            c3 = await _maak_component(s, "RU-Comp NiveauTwee")
            ids.append(c3)
            # Direct op de wortel (mag NIET in de roll-up), plus regels op beide niveaus;
            # c3 vervult twee functies (twee losse regels).
            await _maak_vervulling(s, c1, top)
            await _maak_vervulling(s, c2, a)
            await _maak_vervulling(s, c3, b, "registreren")
            await _maak_vervulling(s, c3, b, "raadplegen")

            regels = await svc.rollup_voor_proces(s, _TID, top)
            assert len(regels) == 3  # c2 (1×) + c3 (2×); de wortel-eigen regel niet
            assert all(r["component_id"] != c1 for r in regels)
            per_comp = {}
            for r in regels:
                per_comp.setdefault(r["component_id"], []).append(r)
            # Herkomst niveau 1: naam + pad = het directe deelproces; tak = dat deelproces.
            (r2,) = per_comp[c2]
            assert r2["proces_naam"] == "RU-Test Aanvraag behandelen"
            assert r2["proces_pad"] == ["RU-Test Aanvraag behandelen"]
            assert r2["tak_id"] == a
            # Herkomst niveau 2: pad loopt van het directe deelproces naar beneden;
            # de tak blijft het DIRECTE deelproces (groepeersleutel).
            assert len(per_comp[c3]) == 2
            for r in per_comp[c3]:
                assert r["proces_naam"] == "RU-Test Besluit vastleggen"
                assert r["proces_pad"] == ["RU-Test Aanvraag behandelen", "RU-Test Besluit vastleggen"]
                assert r["tak_id"] == a
            # Deel-rollup vanaf niveau 1: alleen de diepere regels, pad + tak relatief.
            deel = await svc.rollup_voor_proces(s, _TID, a)
            assert {r["component_id"] for r in deel} == {c3}
            assert deel[0]["proces_pad"] == ["RU-Test Besluit vastleggen"]
            assert deel[0]["tak_id"] == b
            # Blad zonder deelprocessen ⇒ leeg (frontend toont dan géén blok).
            assert await svc.rollup_voor_proces(s, _TID, b) == []
            # Onbekend proces ⇒ 404 (no-leak).
            try:
                await svc.rollup_voor_proces(s, _TID, uuid.uuid4())
                raise AssertionError("verwachtte NietGevonden")
            except NietGevonden:
                pass
        finally:
            await _ruim(s, ids)

    asyncio.run(_run_rls(_TID, "rollup-test", _flow))


@integratie
def test_organisatie_afleiding_eigendom_gebruik_dedupe_live():
    from services import procesvervulling_service as svc

    async def _flow(s):
        ids = []
        try:
            org = await _maak_organisatie(s, "RU-Org Gemeente")
            ids.append(org)
            ander = await _maak_organisatie(s, "RU-Org Andere")
            ids.append(ander)
            c_eig = await _maak_component(s, "RU-OC Eigendom", eigenaar_organisatie_id=org)
            ids.append(c_eig)
            c_geb = await _maak_component(s, "RU-OC Gebruik")
            ids.append(c_geb)
            c_beide = await _maak_component(s, "RU-OC Beide", eigenaar_organisatie_id=org)
            ids.append(c_beide)
            c_vreemd = await _maak_component(s, "RU-OC Vreemd", eigenaar_organisatie_id=ander)
            ids.append(c_vreemd)
            await _registreer_gebruik(s, org, c_geb)
            await _registreer_gebruik(s, org, c_beide)  # eigendom ÉN gebruik → telt 1×
            p1 = await _maak_proces(s, "RU-OP Vergunningverlening")
            ids.append(p1)
            p2 = await _maak_proces(s, "RU-OP Aanvraag behandelen", ouder_id=p1)
            ids.append(p2)
            await _maak_vervulling(s, c_eig, p1)
            await _maak_vervulling(s, c_geb, p1)
            await _maak_vervulling(s, c_beide, p1, "registreren")
            await _maak_vervulling(s, c_beide, p1, "raadplegen")  # 2e functie → tóch 1 component
            await _maak_vervulling(s, c_beide, p2)
            await _maak_vervulling(s, c_vreemd, p1)  # andere organisatie → telt hier niet

            beeld = await svc.processen_voor_organisatie(s, _TID, org)
            per_proces = {p["proces_id"]: p for p in beeld}
            assert set(per_proces) == {p1, p2}
            assert per_proces[p1]["component_aantal"] == 3  # dedupe: c_beide 1×, c_vreemd niet
            assert {c["component_id"] for c in per_proces[p1]["componenten"]} == {c_eig, c_geb, c_beide}
            assert per_proces[p2]["component_aantal"] == 1
            assert per_proces[p2]["proces_ouder_naam"] == "RU-OP Vergunningverlening"
            # De andere organisatie ziet alléén haar eigen brug (c_vreemd → p1).
            beeld_ander = await svc.processen_voor_organisatie(s, _TID, ander)
            assert [p["proces_id"] for p in beeld_ander] == [p1]
            assert {c["component_id"] for c in beeld_ander[0]["componenten"]} == {c_vreemd}
            # Organisatie zonder componenten ⇒ rustig leeg beeld.
            leeg = await _maak_organisatie(s, "RU-Org Leeg")
            ids.append(leeg)
            assert await svc.processen_voor_organisatie(s, _TID, leeg) == []
        finally:
            await _ruim(s, ids)

    asyncio.run(_run_rls(_TID, "rollup-test", _flow))


@integratie
def test_rls_isolatie_en_geen_mutatie_live():
    from services import procesvervulling_service as svc
    from services.errors import NietGevonden

    async def _bouw(s):
        ids = []
        org = await _maak_organisatie(s, "RU-RLS Org")
        ids.append(org)
        top = await _maak_proces(s, "RU-RLS Proces")
        ids.append(top)
        kind = await _maak_proces(s, "RU-RLS Deelproces", ouder_id=top)
        ids.append(kind)
        comp = await _maak_component(s, "RU-RLS Comp", eigenaar_organisatie_id=org)
        ids.append(comp)
        await _maak_vervulling(s, comp, kind)
        return ids, org, top

    async def _flow(s):
        ids, org, top = await _bouw(s)
        try:
            # Geen-mutatie-bewijs: tellingen vóór/na de lees-calls identiek.
            voor = (await _tel(s, "element"), await _tel(s, "procesvervulling"), await _tel(s, "audit_log"))
            regels = await svc.rollup_voor_proces(s, _TID, top)
            beeld = await svc.processen_voor_organisatie(s, _TID, org)
            assert len(regels) == 1 and len(beeld) == 1
            na = (await _tel(s, "element"), await _tel(s, "procesvervulling"), await _tel(s, "audit_log"))
            assert voor == na, "een leespad heeft data gemuteerd"

            # RLS/no-leak: vanuit tenant B bestaan proces én organisatie niet (404).
            async def _vreemd(s_b):
                for aanroep in (
                    svc.rollup_voor_proces(s_b, _TID_B, top),
                    svc.processen_voor_organisatie(s_b, _TID_B, org),
                ):
                    try:
                        await aanroep
                        raise AssertionError("verwachtte NietGevonden (no-leak)")
                    except NietGevonden:
                        pass
            await _run_rls(_TID_B, "rollup-test-b", _vreemd)
        finally:
            await _ruim(s, ids)

    asyncio.run(_run_rls(_TID, "rollup-test", _flow))
