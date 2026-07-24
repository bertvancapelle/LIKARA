"""De gedeelde tekst-schoonregel per categorie (LI051 — tekenset-verbreden).

Borgt de regel ZELF (niet een lijst codes): élk teken uit `Zs`/`Cf`/`Cc` wordt afgehandeld, over het
hele Unicode-bereik. Plus: de woordgrens blijft (blok A), spaties vouwen samen, en bij het vastleggen
(blok B) wordt een vaste spatie een gewone — zodat een opgeslagen naam vindbaar blijft met een gewone
spatie. Onzichtbare tekens worden uit hun code point opgebouwd (`chr`), nooit letterlijk.
"""
import asyncio
import sys
import unicodedata

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database  # noqa: F401
from app.core.tenant_context import reset_tenant_context, zet_tenant_context
from schemas import tekstschoning
from schemas._validators import _verplichte_tekst
from services import zoektekst

NBSP = chr(0x00A0)
EMSP = chr(0x2003)
NNBSP = chr(0x202F)
IDSP = chr(0x3000)
ZWSP = chr(0x200B)
WJ = chr(0x2060)
BOM = chr(0xFEFF)

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── 1. De regel per categorie, over het hele Unicode-bereik ─────────────────────

def test_regel_dekt_elke_categorie_niet_een_lijst_codes():
    """Élk teken uit `Zs` → gewone spatie; élk teken uit `Cf`/`Cc` → weg. Zo glipt een teken dat
    niemand opschreef er niet doorheen. We lopen het hele bereik langs (surrogaten overgeslagen)."""
    fout = []
    for cp in range(0, sys.maxunicode + 1):
        if 0xD800 <= cp <= 0xDFFF:
            continue
        ch = chr(cp)
        cat = unicodedata.category(ch)
        if cat == "Zs":
            if zoektekst.schoon_zoekterm("a" + ch + "b") != "a b":
                fout.append(("Zs", hex(cp)))
        elif cat in ("Cf", "Cc"):
            if zoektekst.schoon_zoekterm("a" + ch + "b") != "ab":
                fout.append((cat, hex(cp)))
        if len(fout) > 5:
            break
    assert fout == [], f"onafgehandelde tekens: {fout}"


def test_woordgrens_blijft_bij_zoeken():
    """Blok A — een vaste spatie wordt een gewone spatie: zaak<NBSP>systeem zoekt op 'zaak systeem',
    NIET op 'zaaksysteem'."""
    for sp in (NBSP, EMSP, NNBSP, IDSP):
        assert zoektekst.schoon_zoekterm("zaak" + sp + "systeem") == "zaak systeem"


def test_opmaaktekens_weg_spaties_samengevouwen():
    assert zoektekst.schoon_zoekterm("zaak" + ZWSP + "systeem") == "zaaksysteem"
    assert zoektekst.schoon_zoekterm("zaak" + WJ + "systeem") == "zaaksysteem"
    assert zoektekst.schoon_zoekterm(BOM + "zaaksysteem") == "zaaksysteem"
    assert zoektekst.schoon_zoekterm("zaak  systeem") == "zaak systeem"          # dubbele spatie
    assert zoektekst.schoon_zoekterm("zaak" + NBSP + NBSP + "systeem") == "zaak systeem"


# ── 2. Blok B — vastleggen: vaste spatie -> gewone, en vindbaar ─────────────────

def test_vastleggen_vaste_spatie_wordt_gewone_spatie():
    """Blok B — de invoervalidator schoont met dezelfde regel: een naam met een vaste spatie wordt
    opgeslagen met een gewone. Stuurtekens blijven wél geweigerd."""
    assert _verplichte_tekst("Zaak" + NBSP + "systeem", "naam", 150) == "Zaak systeem"
    assert _verplichte_tekst("Zaak" + ZWSP + "systeem", "naam", 150) == "Zaaksysteem"  # Cf weg
    assert _verplichte_tekst("Zaak  systeem", "naam", 150) == "Zaak systeem"            # samengevouwen
    with pytest.raises(ValueError):  # een regelovergang blijft een plakfout
        _verplichte_tekst("Zaak\nsysteem", "naam", 150)


def test_vastleggen_en_zoeken_komen_op_dezelfde_tekst_uit():
    """De kern van blok B: wat is opgeslagen (naam met vaste spatie → gewone) en waarop gezocht wordt
    (gewone spatie) leveren dezelfde tekst — dus vindbaar. Offline bewijs (geen DB nodig)."""
    opgeslagen = _verplichte_tekst("Zaak" + NBSP + "systeem", "naam", 150)
    gezocht = zoektekst.schoon_zoekterm("zaak systeem")
    assert opgeslagen.lower() == gezocht.lower() == "zaak systeem"


# ── 3. Live: opgeslagen met vaste spatie, gevonden met gewone ───────────────────

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


@integratie
def test_live_naam_met_vaste_spatie_is_vindbaar_met_gewone():
    from schemas.component import ComponentCreate
    from services import component_service
    import uuid

    sfx = uuid.uuid4().hex[:6]
    naam_in = "Zaak" + NBSP + f"systeem-{sfx}"  # vaste spatie bij het vastleggen

    async def _flow(s):
        eid = None
        try:
            c = await component_service.maak_aan(
                s, _TID, ComponentCreate(naam=naam_in, componenttype="applicatie"))
            eid = c["id"]
            # Opgeslagen mét gewone spatie.
            assert c["naam"] == f"Zaak systeem-{sfx}"
            # Gevonden met een GEWONE spatie.
            items, _ = await component_service.lijst(s, _TID, zoek=f"zaak systeem-{sfx}")
            namen = {i["naam"] if isinstance(i, dict) else i.naam for i in items}
            assert f"Zaak systeem-{sfx}" in namen
        finally:
            if eid:
                await s.execute(text("delete from element where id = :i"), {"i": eid})
                await s.commit()

    asyncio.run(_app_run(_flow))
