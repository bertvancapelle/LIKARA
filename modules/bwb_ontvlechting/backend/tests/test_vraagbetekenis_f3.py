"""Tests — ADR-023 Fase F (F-3) stap 1: betekenis-markering checklistvraag.

Offline: de betekenis-catalogus-seed (expand) draagt `technische_plaatsing`; de baseline-
seed zet de betekenis op de 2.2-applicatievraag (fresh-deploy = gemigreerde stand); de
migratie raakt uitsluitend de catalogus + `checklistvraag.betekenis` (geen engine/profiel/
score); de catalogus-helper + seed importeren geen engine-symbolen; `zet_betekenis`
valideert tegen de catalogus en doet GÉÉN fan-out. Live (skip-if-no-DB): de catalogus is
geseed, de applicatie-plaatsingsvraag draagt `technische_plaatsing` (en geen andere vraag),
de uniciteit `(tenant, componenttype, betekenis)` wordt afgedwongen (NULL onbeperkt), en het
zetten/wissen raakt profiel/score niet. Live-tests herstellen de seed-stand structureel.
"""
import asyncio
import inspect
import pathlib
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

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
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"

_MIGRATIE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "migrations" / "versions" / "0024_adr023_vraagbetekenis.py"
)


# ── Offline: seed (expand) = gemigreerde stand ──────────────────────────────────

def test_betekenis_catalogus_seed_bevat_technische_plaatsing():
    from services.seed_vraagbetekenis import bouw_vraagbetekenis

    rijen = bouw_vraagbetekenis()
    sleutels = {r["optie_sleutel"] for r in rijen}
    assert "technische_plaatsing" in sleutels
    assert all(r["actief"] is True for r in rijen)


def test_baseline_22_draagt_betekenis():
    """Fresh deploy: de 2.2-applicatievraag krijgt `technische_plaatsing` via de seed."""
    from services.seed import CHECKLIST_VRAGEN

    per_code = {v["code"]: v for v in CHECKLIST_VRAGEN}
    assert per_code["2.2"].get("betekenis") == "technische_plaatsing"
    # Geen enkele andere baseline-vraag draagt een betekenis.
    overig = [v["code"] for v in CHECKLIST_VRAGEN if v["code"] != "2.2" and v.get("betekenis")]
    assert overig == [], overig


# ── Offline: migratie raakt alleen catalogus + checklistvraag.betekenis ─────────

def test_migratie_raakt_geen_engine_tabellen():
    bron = _MIGRATIE.read_text(encoding="utf-8")
    assert "create_table(" in bron and "vraagbetekenis_optie" in bron
    assert "uq_checklistvraag_betekenis" in bron
    assert "UPDATE checklistvraag SET betekenis = 'technische_plaatsing'" in bron
    # Geen DML op engine-/score-tabellen (alleen de op.execute-/SQL-regels tellen).
    sql_regels = [r for r in bron.splitlines() if "op.execute" in r or r.strip().startswith('"')]
    sql = " ".join(sql_regels)
    for verboden in ("component_profiel", "checklistscore", "blokkade"):
        for dml in ("UPDATE", "INSERT INTO", "DELETE FROM"):
            assert f"{dml} {verboden}" not in sql, f"migratie mag geen {dml} op {verboden!r} doen"


# ── Offline: engine-onaangeroerd (import-afwezigheid + geen fan-out) ────────────

def test_catalogus_en_seed_importeren_geen_engine():
    """De nieuwe modules raken de engine niet — geen import van lifecycle/profiel/score."""
    verboden = ("lifecycle_service", "herbereken_lifecycle", "ComponentProfiel",
                "Checklistscore", "Blokkade")
    for mod in ("services/vraagbetekenis_catalog.py", "services/seed_vraagbetekenis.py"):
        bron = (pathlib.Path(__file__).resolve().parents[1] / mod).read_text(encoding="utf-8")
        for sym in verboden:
            assert sym not in bron, f"{mod} mag {sym!r} niet importeren/gebruiken"


def test_zet_betekenis_doet_geen_fanout():
    """`zet_betekenis` roept geen lifecycle-herberekening aan (classificatie, geen telling)."""
    from services import checklistconfig_service as svc

    bron = inspect.getsource(svc.zet_betekenis)
    assert "herbereken_type" not in bron
    assert "herbereken_lifecycle" not in bron


# ── Offline service: validatie + wis (DB gemockt) ───────────────────────────────

def _result(waarde):
    r = MagicMock()
    r.scalar_one_or_none.return_value = waarde
    return r


def _scalars(rijen):
    r = MagicMock()
    r.scalars.return_value.all.return_value = rijen
    return r


def _all(rijen):
    r = MagicMock()
    r.all.return_value = rijen
    return r


# LI050: de categorie is een verwijzing; de read resolvet naam/volgorde via _haal_categorie.
_CAT = SimpleNamespace(id=uuid.uuid4(), componenttype="applicatie", naam="x", volgorde=1)


def _vraag():
    from models.models import ChecklistPrioriteit

    return SimpleNamespace(
        id=uuid.uuid4(), code="9.1", componenttype="applicatie", categorie_id=_CAT.id,
        vraag="?", prioriteit=ChecklistPrioriteit.midden,
        antwoordtype="geen", actief=True, betekenis=None,
    )


def test_zet_betekenis_geldig_zet_de_waarde():
    from schemas.checklistconfig import BetekenisUpdate
    from services import checklistconfig_service as svc

    vraag = _vraag()
    session = AsyncMock()
    # _haal_vraag → vraag; valideer_sleutel→actieve_sleutels → rij; _opties_van → [];
    # _haal_categorie → cat (LI050).
    session.execute.side_effect = [
        _result(vraag),
        _all([SimpleNamespace(optie_sleutel="technische_plaatsing")]),
        _scalars([]),
        _result(_CAT),
    ]
    out = asyncio.run(svc.zet_betekenis(session, vraag.id, BetekenisUpdate(betekenis="technische_plaatsing")))
    assert vraag.betekenis == "technische_plaatsing"
    assert out["betekenis"] == "technische_plaatsing"


def test_zet_betekenis_onbekend_weigert_422():
    from schemas.checklistconfig import BetekenisUpdate
    from services import checklistconfig_service as svc
    from services.errors import OngeldigeRegistratie

    vraag = _vraag()
    session = AsyncMock()
    session.execute.side_effect = [
        _result(vraag),
        _all([SimpleNamespace(optie_sleutel="technische_plaatsing")]),  # actieve sleutels
    ]
    with pytest.raises(OngeldigeRegistratie):
        asyncio.run(svc.zet_betekenis(session, vraag.id, BetekenisUpdate(betekenis="onbekend")))


def test_zet_betekenis_wis_valideert_niet():
    from schemas.checklistconfig import BetekenisUpdate
    from services import checklistconfig_service as svc

    vraag = _vraag()
    vraag.betekenis = "technische_plaatsing"
    session = AsyncMock()
    # wis (None): _haal_vraag → vraag; (geen validatie); _opties_van → []; _haal_categorie (LI050).
    session.execute.side_effect = [_result(vraag), _scalars([]), _result(_CAT)]
    out = asyncio.run(svc.zet_betekenis(session, vraag.id, BetekenisUpdate(betekenis=None)))
    assert vraag.betekenis is None
    assert out["betekenis"] is None


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


@integratie
def test_catalogus_geseed_live():
    """Borging #4-bron: de betekenis-catalogus is platform-breed geseed (lk_app mag lezen)."""
    from services import vraagbetekenis_catalog as cat

    sleutels = asyncio.run(_run_rls(_TID, "test:bert", cat.actieve_sleutels))
    assert "technische_plaatsing" in sleutels


@integratie
def test_22_draagt_betekenis_en_uniek_live():
    """Borging #2: in de tenant draagt precies de applicatie-plaatsingsvraag (2.2) de
    betekenis `technische_plaatsing`; geen andere vraag draagt die. + NULL onbeperkt."""
    from sqlalchemy import text as _text

    async def _meet(s):
        dragers = (await s.execute(_text(
            "SELECT code, componenttype FROM checklistvraag "
            "WHERE betekenis = 'technische_plaatsing' ORDER BY componenttype, code"
        ))).all()
        nul_app = (await s.execute(_text(
            "SELECT count(*) FROM checklistvraag "
            "WHERE componenttype = 'applicatie' AND betekenis IS NULL"
        ))).scalar()
        return dragers, nul_app

    dragers, nul_app = asyncio.run(_run_rls(_TID, "test:bert", _meet))
    assert dragers == [("2.2", "applicatie")], dragers
    assert nul_app > 1, nul_app  # vele applicatie-vragen zonder betekenis (NULL distinct)


@integratie
def test_uniciteit_afgedwongen_live():
    """Borging #3: een tweede applicatievraag dezelfde betekenis geven ⇒ 409 (constraint)."""
    from sqlalchemy import text as _text

    from schemas.checklistconfig import BetekenisUpdate
    from services import checklistconfig_service as svc
    from services.errors import ConfiguratieConflict

    async def _flow(s):
        rij = (await s.execute(_text(
            "SELECT id FROM checklistvraag "
            "WHERE componenttype = 'applicatie' AND code = '9.1' LIMIT 1"
        ))).first()
        if rij is None:
            pytest.skip("baseline-vraag 9.1 niet aanwezig op deze DB")
        try:
            await svc.zet_betekenis(s, rij[0], BetekenisUpdate(betekenis="technische_plaatsing"))
            return "geen_fout"
        except ConfiguratieConflict:
            return "conflict"

    uitkomst = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert uitkomst == "conflict", uitkomst


@integratie
def test_zetten_en_wissen_raakt_engine_niet_live():
    """Borging #1 (live): wissen (2.2) + toekennen (9.1) van een betekenis muteert geen
    `component_profiel`/`checklistscore`. Herstelt de seed-stand structureel (finally)."""
    from sqlalchemy import text as _text

    from schemas.checklistconfig import BetekenisUpdate
    from services import checklistconfig_service as svc

    async def _ids_en_count(s):
        async def cnt(tabel):
            return (await s.execute(_text(f"SELECT count(*) FROM {tabel}"))).scalar()
        ids = {}
        for code in ("2.2", "9.1"):
            r = (await s.execute(_text(
                "SELECT id FROM checklistvraag WHERE componenttype='applicatie' AND code=:c LIMIT 1"
            ), {"c": code})).first()
            ids[code] = r[0] if r else None
        return ids, await cnt("component_profiel"), await cnt("checklistscore")

    async def _flow(s):
        ids, prof0, score0 = await _ids_en_count(s)
        if ids["2.2"] is None or ids["9.1"] is None:
            pytest.skip("baseline-vragen 2.2/9.1 niet aanwezig op deze DB")
        try:
            await svc.zet_betekenis(s, ids["2.2"], BetekenisUpdate(betekenis=None))      # wissen
            await svc.zet_betekenis(s, ids["9.1"], BetekenisUpdate(betekenis="technische_plaatsing"))  # toekennen
            prof1 = (await s.execute(_text("SELECT count(*) FROM component_profiel"))).scalar()
            score1 = (await s.execute(_text("SELECT count(*) FROM checklistscore"))).scalar()
        finally:
            await svc.zet_betekenis(s, ids["9.1"], BetekenisUpdate(betekenis=None))
            await svc.zet_betekenis(s, ids["2.2"], BetekenisUpdate(betekenis="technische_plaatsing"))
        return prof0, prof1, score0, score1

    prof0, prof1, score0, score1 = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert prof1 == prof0, (prof0, prof1)
    assert score1 == score0, (score0, score1)
