"""Zoekterm-opschoning (LI051) — zoeken weigert nooit, het schoont op en zoekt met wat overblijft.

Besluit Bert: bij zoeken hoort nooit een foutmelding. Onzichtbare tekens (nul-/stuurtekens,
regelovergang, tab) worden uit de zoekterm *gehaald*, niet geweigerd — één regel voor alle rommel.
De term wordt naar dezelfde schrijfwijze (NFC) genormaliseerd als de opgeslagen namen.

Dit bestand borgt de databasekant (`services/zoektekst.schoon_zoekterm` + `zoek_clause`):
- de pure opschoning (stuurtekens weg, NFC, idempotent, leeg blijft leeg);
- live: een zoekterm mét een nulteken levert een gewoon resultaat op — **geen kale storing**;
- live: een zoekterm mét stuurtekens vindt hetzelfde als dezelfde term zonder.
De melding zelf leeft aan de schermkant (frontend, `MeldingBanner`); dit bestand raakt die niet.
"""
import asyncio
import inspect

import pytest
from sqlalchemy import literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context
from services import zoektekst

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


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


# ── 1. Pure opschoning ──────────────────────────────────────────────────────────

def test_stuurtekens_worden_verwijderd_niet_geweigerd():
    """Nul-, stuur-, regelovergang- en tab-tekens gaan eruit; de leesbare tekst blijft staan.
    Geen exception — zoeken weigert nooit."""
    assert zoektekst.schoon_zoekterm("zaak\x00systeem") == "zaaksysteem"
    assert zoektekst.schoon_zoekterm("zaak\x07systeem") == "zaaksysteem"   # BEL (C0)
    assert zoektekst.schoon_zoekterm("zaak\x85systeem") == "zaaksysteem"   # NEL (C1)
    assert zoektekst.schoon_zoekterm("regel1\nregel2") == "regel1regel2"
    assert zoektekst.schoon_zoekterm("kol1\tkol2") == "kol1kol2"


def test_zichtbare_tekst_blijft_ongemoeid():
    """Emoji, ampersand, punthaken, accenten — legitieme zoekinhoud, blijft staan."""
    assert zoektekst.schoon_zoekterm("Select & Go 🚀") == "Select & Go 🚀"
    assert zoektekst.schoon_zoekterm("<adres>") == "<adres>"
    assert zoektekst.schoon_zoekterm("José") == "José"


def test_nfc_normalisatie_zelfde_schrijfwijze_als_opslag():
    """De losse (gedecomponeerde) accentvorm wordt dezelfde tekst als de samengestelde —
    net als bij het opslaan van een naam (`schemas/_validators._normaliseer`)."""
    import unicodedata
    los = "Jose" + "́"                    # e + combining acute
    assert zoektekst.schoon_zoekterm(los) == unicodedata.normalize("NFC", los) == "José"


def test_opschoning_is_idempotent():
    """Tweemaal opschonen = eenmaal — nodig omdat de frontend de al-opgeschoonde term terugstuurt
    en `zoek_clause` haar dan nogmaals opschoont; beide kanten leveren dezelfde term."""
    for ruw in ("zaak\x00systeem", "José", "  Select & Go 🚀  ", "\x00\x07"):
        een = zoektekst.schoon_zoekterm(ruw)
        assert zoektekst.schoon_zoekterm(een) == een


def test_alleen_rommel_wordt_lege_zoekopdracht():
    """Blijft er na opschonen niets over, dan is dat een lege zoekopdracht (leeg), geen fout."""
    assert zoektekst.schoon_zoekterm("\x00\x07\x1f") == ""
    assert zoektekst.schoon_zoekterm("   ") == ""


def test_zoek_clause_schoont_de_term_op():
    """Blok E, achterkant (offline borging): de gedeelde bron `zoek_clause` MOET de term opschonen —
    zo kan de opschoning niet stil uit het ene punt verdwijnen waar élk zoeken langskomt. Dat élk
    zoeken via `zoek_clause` loopt, borgt `test_zoektekst_een_bron_li051`."""
    assert "schoon_zoekterm" in inspect.getsource(zoektekst.zoek_clause)


# ── 2. Live: geen storing, en stuurtekens vinden hetzelfde als zonder ────────────

@integratie
def test_nulteken_geen_storing_gewoon_resultaat():
    """De bijt-test: een zoekterm mét een nulteken knapt NIET (asyncpg zou op een rauwe NUL in een
    bindparameter een kale storing geven). Via `zoek_clause` wordt de NUL eerst weggeschoond."""
    async def _flow(s):
        # Nulteken middenin: matcht de literal alsof de NUL er niet stond.
        r = (await s.execute(select(zoektekst.zoek_clause(literal("Zaaksysteem"), "zaak\x00systeem")))).scalar()
        assert r is True
        # Zoekterm die ná opschonen leeg is: geen storing, matcht alles (lege zoekopdracht).
        r2 = (await s.execute(select(zoektekst.zoek_clause(literal("wat dan ook"), "\x00")))).scalar()
        assert r2 is True
    asyncio.run(_app_run(_flow))


@integratie
def test_stuurtekens_vinden_hetzelfde_als_zonder():
    """Dezelfde term met en zonder stuurtekens levert dezelfde treffer — de rommel is genegeerd."""
    async def _flow(s):
        met = (await s.execute(select(zoektekst.zoek_clause(literal("Bevolkerung"), "bev\x85olker\tung")))).scalar()
        zonder = (await s.execute(select(zoektekst.zoek_clause(literal("Bevolkerung"), "bevolkerung")))).scalar()
        assert met == zonder is True
    asyncio.run(_app_run(_flow))
