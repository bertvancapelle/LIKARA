"""Accent-ongevoelig zoeken (LI051, weg 1) — gedeelde bron + de twee wachters.

Besluit Bert: wie "jose" typt vindt *José*. De gedeelde bron `services/zoektekst.py` doet
`unaccent(kolom) ILIKE unaccent(patroon)`; de opgeslagen naam verandert niet en jokertekens blijven
letterlijk. Dit bestand borgt: het gedrag (live, twee verschillende zoekvelden), de joker-escape,
de onveranderde naam, de blok-B-bronscan (één bron, geen tiende kopie) en de blok-D-startupwachter.
"""
import ast
import asyncio
import pathlib
import re
import uuid

import pytest
from sqlalchemy import literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_ROOT = pathlib.Path(__file__).resolve().parents[4]
_SERVICES = _ROOT / "modules" / "bwb_ontvlechting" / "backend" / "services"


def _db_bereikbaar() -> bool:
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


async def _app_run(fn):
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


# ── 1. Live: het gedrag zelf, over TWEE verschillende zoekvelden ────────────────

@integratie
def test_zoeken_negeert_accenten_op_twee_zoekvelden():
    """Component-zoek én partij-zoek: zonder accent vindt mét accent (en andersom), en de
    getoonde naam blijft ongewijzigd. Twee velden = "overal hetzelfde" aantoonbaar."""
    from schemas.component import ComponentCreate
    from schemas.partij import PartijCreate
    from services import component_service, partij_service

    sfx = uuid.uuid4().hex[:6]
    comp_naam = f"Bévölkerung-{sfx}"   # component-zoekveld
    part_naam = f"José-{sfx}"          # partij-zoekveld

    async def _flow(s):
        ids = []
        try:
            c = await component_service.maak_aan(
                s, _TID, ComponentCreate(naam=comp_naam, componenttype="applicatie"))
            ids.append(("element", c["id"]))
            p = await partij_service.maak_aan(
                s, _TID, PartijCreate(aard="externe_partij", naam=part_naam))
            ids.append(("element", p["id"] if isinstance(p, dict) else p.id))

            async def comp_namen(zoek):
                items, _ = await component_service.lijst(s, _TID, zoek=zoek)
                return {i["naam"] if isinstance(i, dict) else i.naam for i in items}

            async def part_namen(zoek):
                items, _ = await partij_service.lijst(s, _TID, zoek=zoek)
                return {i["naam"] if isinstance(i, dict) else i.naam for i in items}

            # Component: zonder accent vindt mét accent.
            assert comp_naam in await comp_namen(f"bevolkerung-{sfx}"), "accentloos zoeken vond component niet"
            assert comp_naam in await comp_namen(f"Bévölkerung-{sfx}"), "zoeken mét accent vond component niet"
            # Partij: idem — hetzelfde gedrag op een ander veld.
            assert part_naam in await part_namen(f"jose-{sfx}"), "accentloos zoeken vond partij niet"
            assert part_naam in await part_namen(f"José-{sfx}"), "zoeken mét accent vond partij niet"

            # De getoonde/opgeslagen naam is ONVERANDERD (dit gaat alleen over wat je vindt).
            comp_terug = next(iter(await comp_namen(f"bevolkerung-{sfx}")))
            assert comp_terug == comp_naam == f"Bévölkerung-{sfx}"
        finally:
            for _t, eid in ids:
                await s.execute(text("delete from element where id = :i"), {"i": eid})
            await s.commit()

    asyncio.run(_app_run(_flow))


@integratie
def test_jokertekens_blijven_letterlijk():
    """De escape blijft intact: wie een procentteken typt zoekt daar LETTERLIJK op — hij krijgt
    niet ineens alles. Bewezen op literal-waarden (geen fixture nodig)."""
    async def _flow(s):
        from services import zoektekst
        # "%" matcht alleen een naam die écht een % bevat, niet een willekeurige.
        assert bool((await s.execute(select(zoektekst.zoek_clause(literal("50% korting"), "%")))).scalar())
        assert not bool((await s.execute(select(zoektekst.zoek_clause(literal("geen teken"), "%")))).scalar())
        # "_" idem: letterlijk, geen "elk teken".
        assert bool((await s.execute(select(zoektekst.zoek_clause(literal("a_b"), "_")))).scalar())
        assert not bool((await s.execute(select(zoektekst.zoek_clause(literal("abc"), "_")))).scalar())
    asyncio.run(_app_run(_flow))


@integratie
def test_hoofdletters_blijven_genegeerd():
    async def _flow(s):
        from services import zoektekst
        assert bool((await s.execute(select(zoektekst.zoek_clause(literal("ABC"), "abc")))).scalar())
    asyncio.run(_app_run(_flow))


# ── 2. Pure: de clause-vorm ─────────────────────────────────────────────────────

def test_clause_wikkelt_beide_kanten_in_unaccent():
    from sqlalchemy import Column, String
    from services import zoektekst
    sql = str(zoektekst.zoek_clause(Column("naam", String), "x")).lower()
    # ilike rendert als `lower(...) like lower(...)` — accent-vouwing op BEIDE kanten (unaccent),
    # hoofdletterongevoelig (lower), met de joker-escape.
    assert "unaccent" in sql and "like" in sql and "escape" in sql
    assert sql.count("unaccent") >= 2  # kolom én patroon


def test_escape_like_volgorde():
    from services import zoektekst
    # `\` eerst verdubbeld, dan %/_ ontsnapt — anders zou de tweede stap de eerste ontsnappen.
    assert zoektekst.escape_like(r"50%_\x") == r"50\%\_\\x"


# ── 3. Blok B — één bron, geen tiende kopie, geen omzeiling ─────────────────────

def _service_bestanden():
    for pad in _SERVICES.glob("*.py"):
        if pad.name in ("__init__.py", "zoektekst.py"):
            continue
        yield pad


def test_zoektekst_een_bron_li051():
    """Blok B — élk zoeken loopt via `zoektekst.zoek_clause`: geen enkele service roept nog
    rechtstreeks `.ilike(...)` aan en geen enkele definieert een eigen `_escape_like`. Afgeleid
    bereik (alle services), geen bestandslijst; een tiende kopie of een omzeiling faalt hier."""
    ilike_overtreders, escape_overtreders = [], []
    for pad in _service_bestanden():
        bron = pad.read_text(encoding="utf-8")
        if re.search(r"\.ilike\s*\(", bron):
            ilike_overtreders.append(pad.name)
        if re.search(r"def _escape_like\b", bron):
            escape_overtreders.append(pad.name)
    assert not ilike_overtreders, f"deze services zoeken buiten de gedeelde bron om (.ilike): {ilike_overtreders}"
    assert not escape_overtreders, f"deze services hebben een eigen escape-kopie: {escape_overtreders}"


def test_blok_b_scan_bijt():
    """Zelftest — een rauwe `.ilike(` en een eigen `_escape_like` worden herkend."""
    assert re.search(r"\.ilike\s*\(", 'Component.naam.ilike("%x%")')
    assert re.search(r"def _escape_like\b", "def _escape_like(term):\n    return term")
    assert not re.search(r"\.ilike\s*\(", "zoektekst.zoek_clause(Component.naam, zoek)")


# ── 4. Blok D — startup weigert zonder de zoekfunctie ───────────────────────────

def test_startup_weigert_zonder_unaccent(monkeypatch):
    """Blok D — ontbreekt `unaccent`, dan faalt de start met een begrijpelijke NL-melding
    (geen kale fout). Gesimuleerd door de DB-check te laten falen."""
    from app.core import zoekfunctie

    class _Sessie:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def execute(self, *a, **k):
            raise Exception("function unaccent(unknown) does not exist")

    monkeypatch.setattr(zoekfunctie, "async_session_factory", lambda: _Sessie())
    with pytest.raises(zoekfunctie.ZoekfunctieOntbreekt) as exc:
        asyncio.run(zoekfunctie.valideer_zoekfunctie())
    m = str(exc.value)
    assert "zoekfunctie 'unaccent' is niet beschikbaar" in m
    assert "CREATE EXTENSION IF NOT EXISTS unaccent" in m
    assert "Value error" not in m  # geen technische/Engelse kale fout


def test_startup_slaagt_met_unaccent(monkeypatch):
    """Positief pad — is de functie aanroepbaar, dan geen fout (de wachter bijt niet vals)."""
    from app.core import zoekfunctie

    class _Sessie:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def execute(self, *a, **k): return None

    monkeypatch.setattr(zoekfunctie, "async_session_factory", lambda: _Sessie())
    asyncio.run(zoekfunctie.valideer_zoekfunctie())  # geen raise
