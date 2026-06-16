"""Tests — ADR-023 Fase F (F-6): reconcile van de `checklist_dragend`-vlag.

Offline: de seed (expand) zet de vlag expliciet en correct (applicatie=true, overige=false);
de reconcile-migratie (contract) raakt uitsluitend de catalogus (geen engine/profiel/score).
Live (skip-if-no-DB): de gemeten vlag-stand na reconcile, en het gedrag van het generieke
component-pad (applicatieserver → géén profiel; applicatie → wél, via het hardgecodeerde
convergente pad). Live-tests ruimen hun element-rijen structureel op.
"""
import asyncio
import pathlib

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
_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"

# tests/ -> backend/ -> bwb_ontvlechting/ ; migraties onder bwb_ontvlechting/migrations/.
_MIGRATIE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "migrations" / "versions" / "0023_checklist_dragend_fix.py"
)


# ── Offline: seed zet de vlag expliciet en correct (fresh-deploy = reconcile-stand) ──

def test_seed_zet_checklist_dragend_expliciet():
    from services.seed_componentconfig import bouw_componentconfig

    rijen = bouw_componentconfig()
    typen = {r["optie_sleutel"]: r["checklist_dragend"]
             for r in rijen if r["dimensie"].value == "componenttype"}
    # Beoogde eindstand: applicatie = true, alle overige (incl. applicatieserver) = false.
    assert typen["applicatie"] is True
    assert typen["applicatieserver"] is False
    assert all(v is False for k, v in typen.items() if k != "applicatie")
    # Niet-componenttype-dimensies dragen de vlag false (kolom is alleen zinvol voor types).
    overig = [r["checklist_dragend"] for r in rijen if r["dimensie"].value != "componenttype"]
    assert overig and all(v is False for v in overig)


def test_reconcile_migratie_raakt_alleen_catalogus():
    """Engine-onaangeroerd + bestaande data ongemoeid: de reconcile-migratie muteert
    uitsluitend `componentconfig_optie` — geen `component_profiel`/`checklistscore`/lifecycle."""
    bron = _MIGRATIE.read_text(encoding="utf-8")
    assert "UPDATE componentconfig_optie SET checklist_dragend = true" in bron
    assert "UPDATE componentconfig_optie SET checklist_dragend = false" in bron
    # De UITGEVOERDE SQL (op.execute-statements) mag geen engine-/score-tabel raken; mentions
    # in de docstring/comments tellen niet mee — kijk alleen naar de op.execute-regels.
    sql_regels = [r for r in bron.splitlines() if "op.execute" in r or r.strip().startswith('"')]
    sql = " ".join(sql_regels)
    for verboden in ("component_profiel", "checklistscore", "blokkade"):
        for dml in ("UPDATE", "INSERT INTO", "DELETE FROM"):
            assert f"{dml} {verboden}" not in sql, f"reconcile mag geen {dml} op {verboden!r} doen"


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


async def _vlag_stand(s):
    from sqlalchemy import text as _text

    rijen = (await s.execute(_text(
        "SELECT optie_sleutel, checklist_dragend FROM componentconfig_optie "
        "WHERE dimensie='componenttype' ORDER BY optie_sleutel"
    ))).all()
    return {r[0]: r[1] for r in rijen}


@integratie
def test_vlag_stand_kernfix_live():
    """Borging #2 (kernfix op de dev-DB): applicatie=true, en de twee opdracht-genoemde
    fout-types staan nu correct op false (applicatieserver, database). De structurele
    'alle overige false'-default wordt offline geborgd via `bouw_componentconfig`; op de
    dev-DB staat daarnaast bewust het demo-type `client_software` op true (zie hieronder)."""
    stand = asyncio.run(_run_rls(_TID, "test:bert", _vlag_stand))
    assert stand.get("applicatie") is True, stand
    assert stand.get("applicatieserver") is False, stand
    assert stand.get("database") is False, stand


@integratie
def test_dev_reseed_duurzaamheid_live():
    """Borging #4: na een volledige dev-reseed (incl. dev_seed_testdata.py) is het tweede
    checklist-dragend type `client_software` (true) — en `applicatieserver`/`database`
    blijven false. Bewijst dat de dev-seed de fix niet meer ondermijnt (geen leugen op
    applicatieserver). Skip als de dev-seed-demo (nog) niet is geladen."""
    stand = asyncio.run(_run_rls(_TID, "test:bert", _vlag_stand))
    if stand.get("client_software") is not True:
        pytest.skip("dev-seed-demo (client_software) niet geladen op deze DB")
    assert stand.get("applicatieserver") is False, stand
    assert stand.get("database") is False, stand
    assert stand.get("applicatie") is True, stand


@integratie
def test_generiek_pad_profiel_volgt_vlag_live():
    """Na de fix: een generiek `applicatieserver`-component krijgt GÉÉN component_profiel
    (vlag=false); een `applicatie` (convergent/hardgecodeerd pad) krijgt er WÉL een."""
    from sqlalchemy import text as _text
    from schemas.component import ComponentCreate
    from services import component_service as comp

    async def _flow(s):
        ids = []
        try:
            srv = await comp.maak_aan(s, _TID, ComponentCreate(
                naam="WT-F6-srv", componenttype="applicatieserver", eigenaar_organisatie="ICT"))
            app = await comp.maak_aan(s, _TID, ComponentCreate(
                naam="WT-F6-app", componenttype="applicatie", eigenaar_organisatie="ICT"))
            ids += [srv["id"], app["id"]]
            prof_srv = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": str(srv["id"])})).scalar()
            prof_app = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": str(app["id"])})).scalar()
            return srv, app, prof_srv, prof_app
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    srv, app, prof_srv, prof_app = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    # applicatieserver: vlag=false ⇒ geen profiel, geen lifecycle.
    assert prof_srv == 0
    assert srv["checklist_dragend"] is False and srv["lifecycle_status"] is None
    # applicatie: hardgecodeerd convergent pad ⇒ wél profiel + lifecycle concept.
    assert prof_app == 1
    assert app["checklist_dragend"] is True and app["lifecycle_status"] == "concept"
