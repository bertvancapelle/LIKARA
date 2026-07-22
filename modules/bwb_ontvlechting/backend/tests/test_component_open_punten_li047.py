"""Tests — "wat heeft dit component nog nodig?" (LI047, ADR-052 besluiten 1-22).

Offline: engine-borging + de route-afleiding (besluit 8: elk punt een route, en NOOIT een route
zonder landing — ADR-054).
Live (skip-if-no-DB, EIGEN test-tenant — likara-tests §Live-DB-tests): één bron/twee filters (13), teller ≡
lijst (14), de bewuste vaststelling verdwijnt uit blok 1 ÉN blok 3 (9 + 10), en de checklistregel is
gebundeld (3).
"""
import asyncio
import inspect
import uuid

import pytest

import app.core.database  # noqa: F401 — registreert de after_begin RLS-hook
from services import component_norm_service as norm
from services import component_open_punten_service as op

_TID = "99990047-0100-0000-0000-000000000047"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline ────────────────────────────────────────────────────────────────────────────────────

def test_engine_onaangeroerd():
    """ADR-052: de norm is een lat, geen poort — deze afleiding raakt de engine nooit."""
    src = inspect.getsource(op)
    for verboden in ("lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
                     "ComponentProfiel", "Blokkade", "lifecycle_status"):
        assert verboden not in src, f"engine-symbool {verboden} in de open-punten-afleiding"


def test_elk_hard_feit_heeft_een_route_of_bewust_geen():
    """Besluit 8 — elk punt heeft een route naar de plek waar het antwoord landt. Waar dat voor een
    componenttype NIET bestaat, is het antwoord expliciet `None`: liever geen doorklik dan een dode
    link (ADR-054 — nooit een route beloven waar niets te landen valt)."""
    zonder_landing = {
        f for f in norm.HARDE_FEITEN if op._route(f, "applicatie") is None
    }
    # `hosting` staat wél op het Overzicht maar heeft geen veld-anker (detailIngang.js VELD_ANKERS).
    assert zonder_landing == {norm.FEIT_HOSTING}, (
        f"onverwachte feiten zonder landing op een applicatie: {zonder_landing}"
    )


def test_koppelingen_heeft_overal_een_landing():
    """LI047 — het Koppelingen-tabblad is component-breed. De consultant op een fileshare kreeg
    anders een regel in "Dit moet nog" die hij nooit kon wegwerken; dan is het overzicht zijn
    belofte kwijt dat alles wat erin staat af te werken is."""
    for ct in ("applicatie", "fileshare", "database", "saas_dienst"):
        assert op._route(norm.FEIT_KOPPELINGEN, ct) == {"soort": "tab", "tab": "koppelingen"}


def test_vangrail_geen_route_zonder_landing_blijft_werken():
    """De geen-plek-melding is nu nergens nodig, maar de VANGRAIL moet blijven: ontstaat er ooit
    weer een tabblad dat niet overal bestaat, dan levert de afleiding géén route in plaats van een
    dode link (ADR-054). Getoetst door de regel tijdelijk weer te laten gelden."""
    origineel = op._TAB_ALLEEN_APPLICATIE
    try:
        op._TAB_ALLEEN_APPLICATIE = {"koppelingen"}
        assert op._route(norm.FEIT_KOPPELINGEN, "fileshare") is None
        assert op._route(norm.FEIT_KOPPELINGEN, "applicatie") == {"soort": "tab", "tab": "koppelingen"}
    finally:
        op._TAB_ALLEEN_APPLICATIE = origineel
    # ...en in de huidige stand geldt hij voor niets.
    assert op._TAB_ALLEEN_APPLICATIE == set()


def test_gebruikersgroep_heeft_overal_een_landing():
    """ADR-055 — het Gebruikersgroepen-tabblad volgt `ondersteunt_werk`; voor de typen zónder die
    vlag ontstaat het punt niet (het signaal is daar stil). Dus altijd een landing."""
    for t in ("applicatie", "fileshare", "saas_dienst"):
        assert op._route(norm.FEIT_GEBRUIKERSGROEP, t) == {"soort": "tab", "tab": "gebruikersgroepen"}


def test_teller_is_de_lengte_van_de_lijst():
    """Besluit 14 — geen aparte telling naast de lijst. Een tabnaam die '4' zegt terwijl het
    tabblad drie regels toont, liegt zonder dat iemand het merkt."""
    blok = op._blok([{"feit": "a"}, {"feit": "b"}])
    assert blok["aantal"] == len(blok["punten"]) == 2
    assert op._blok([])["aantal"] == 0  # besluit 4 — nul is een uitkomst, geen storing


# ── Live (skip-if-no-DB) ───────────────────────────────────────────────────────────────────────

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


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar")


async def _run_rls(fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.core.tenant_context import reset_tenant_context, zet_tenant_context

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    ttok = zet_tenant_context(_TID)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_tenant_context(ttok)
        await eng.dispose()


async def _maak_component(s, naam, componenttype="applicatie"):
    from models.models import Component, Element, ElementType, HostingModel

    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    s.add(Component(id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam,
                    componenttype=componenttype, hostingmodel=HostingModel.onbekend))
    await s.flush()
    return elem.id


async def _norm(s, verplichte_feiten):
    from sqlalchemy import text
    from models.models import ComponentNorm

    await s.execute(text("DELETE FROM component_norm WHERE tenant_id=:t"), {"t": _TID})
    for f in norm.HARDE_FEITEN:
        s.add(ComponentNorm(tenant_id=uuid.UUID(_TID), feit_sleutel=f,
                            verplicht=f in verplichte_feiten))
    await s.flush()


async def _opruimen(s):
    from sqlalchemy import text

    for tabel in ("component_bevinding", "component_norm", "relatie", "component", "element"):
        await s.execute(text(f"DELETE FROM {tabel} WHERE tenant_id=:t"), {"t": _TID})
    await s.commit()


@integratie
def test_een_bron_twee_filters():
    """Besluit 13 — blok 1 en blok 2 delen één bepaling. Samen dekken ze precies de open feiten;
    verschuif de lat en een punt verhuist van blok naar blok zonder van oordeel te veranderen."""
    async def _fn(s):
        cid = await _maak_component(s, "LI047-filters")
        await _norm(s, {norm.FEIT_EIGENAAR, norm.FEIT_BIV})
        a = await op.open_punten(s, _TID, cid)
        await _norm(s, set())  # niets verplicht → alles zakt naar "netjes" (besluit 1)
        b = await op.open_punten(s, _TID, cid)
        return a, b

    try:
        a, b = asyncio.run(_run_rls(_fn))
    finally:
        asyncio.run(_run_rls(_opruimen))

    def _feiten(blok):
        return {p["feit"] for p in blok["punten"]}

    # Dezelfde verzameling open feiten, alleen anders verdeeld.
    assert _feiten(a[op.MOET_NOG]) | _feiten(a[op.NETJES]) == _feiten(b[op.NETJES])
    assert _feiten(a[op.MOET_NOG]) == {norm.FEIT_EIGENAAR, norm.FEIT_BIV}
    assert b[op.MOET_NOG]["aantal"] == 0  # geen norm ingericht ⇒ blok 1 leeg, blok blijft bestaan
    assert not _feiten(a[op.MOET_NOG]) & _feiten(a[op.NETJES]), "een feit staat in twee blokken"


@integratie
def test_teller_en_lijst_lopen_niet_uiteen():
    """Besluit 14 — op elk blok, in een echte respons."""
    async def _fn(s):
        cid = await _maak_component(s, "LI047-teller")
        await _norm(s, {norm.FEIT_EIGENAAR, norm.FEIT_KOPPELINGEN})
        return await op.open_punten(s, _TID, cid)

    try:
        uit = asyncio.run(_run_rls(_fn))
    finally:
        asyncio.run(_run_rls(_opruimen))
    for blok in (op.MOET_NOG, op.NETJES, op.VALT_OP):
        assert uit[blok]["aantal"] == len(uit[blok]["punten"]), f"{blok}: teller ≠ lijst"


@integratie
def test_bewuste_vaststelling_verdwijnt_uit_blok_1_en_blok_3():
    """Besluiten 9 + 10 — DE kern. "Bewust geen koppelingen" is een ANTWOORD: het feit telt als
    vastgesteld (weg uit blok 1) én "staat los in het landschap" wordt gedempt (weg uit blok 3).
    Zonder die tweede helft zegt het scherm op één component twee tegengestelde dingen over
    hetzelfde feit — en precies op het schone geval."""
    from datetime import datetime, timezone

    from models.models import ComponentBevinding, ComponentBevindingSoort

    async def _fn(s):
        cid = await _maak_component(s, "LI047-bewust")
        await _norm(s, {norm.FEIT_KOPPELINGEN})
        voor = await op.open_punten(s, _TID, cid)
        s.add(ComponentBevinding(
            tenant_id=uuid.UUID(_TID), component_id=cid,
            soort=ComponentBevindingSoort.koppelingen,
            # De vaststelling draagt altijd wie/wanneer (ADR-052: een bewust geen is een
            # verantwoord antwoord, geen leeg veld).
            verklaard_door="toets@likara.test", verklaard_op=datetime.now(timezone.utc),
        ))
        await s.flush()
        na = await op.open_punten(s, _TID, cid)
        return voor, na

    try:
        voor, na = asyncio.run(_run_rls(_fn))
    finally:
        asyncio.run(_run_rls(_opruimen))

    soorten = lambda b: {p["soort"] for p in b[op.VALT_OP]["punten"]}  # noqa: E731
    feiten = lambda b: {p["feit"] for p in b[op.MOET_NOG]["punten"]}  # noqa: E731

    # Vóór de vaststelling: het feit staat open én het component staat los.
    assert norm.FEIT_KOPPELINGEN in feiten(voor)
    assert op.PUNT_ISOLATIE in soorten(voor)
    # Erna: uit BEIDE blokken verdwenen.
    assert norm.FEIT_KOPPELINGEN not in feiten(na), "bewust geen = een antwoord; hoort uit blok 1"
    assert op.PUNT_ISOLATIE not in soorten(na), (
        "besluit 10 — een bewuste vaststelling dempt ook 'staat los in het landschap'; anders "
        "spreekt het scherm zichzelf tegen over hetzelfde feit"
    )


@integratie
def test_onbestaand_component_lekt_niets():
    """Component buiten de tenant / onbestaand ⇒ None (de route maakt er 404 van)."""
    try:
        uit = asyncio.run(_run_rls(lambda s: op.open_punten(s, _TID, uuid.uuid4())))
    finally:
        asyncio.run(_run_rls(_opruimen))
    assert uit is None


