"""Tests — ADR-055: de gebruik-verfijning is component-breed; `ondersteunt_werk` is de grens.

De verfijning "welke afdeling/team gebruikt dit component" was gebonden aan componenttype
`applicatie` — geen domeinregel, maar een restant van de opgeheven applicatie-subtabel (LI059).
ADR-055 heft die op met de catalogus-vlag als grens.

Offline: de aanname mag niet terugkruipen (bron-scan op een typevergelijking in de service).
Live (skip-if-no-DB, EIGEN test-tenant — likara-tests §LI039): de registratie lukt op ÉLK type dat
werk ondersteunt en wordt geweigerd op élk type dat dat niet doet, met een weigering die de
waarheid vertelt (422 "die vraag geldt hier niet", nooit 404 "bestaat niet"). Beide toetsen lopen
OVER DE CATALOGUS, nooit tegen een uitgeschreven typelijst — zo erft een nieuw componenttype de
regel zonder codewijziging.
"""
import asyncio
import inspect
import uuid

import pytest

import app.core.database  # noqa: F401 — registreert de after_begin RLS-hook
from services import gebruikersgroep_service as gg
from services import registratiegaten_service as rg
from services.errors import NietGevonden, OngeldigeRegistratie

# Eigen test-tenant (LI039/LI047): deze suite maakt componenten van élk type aan en ruimt ze op;
# op de dev-tenant zou die opruiming breder vegen dan haar eigen fixtures.
_TID = "99990055-0100-0000-0000-000000000055"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline — de aanname mag niet terugkruipen ─────────────────────────────────────────────────

def test_geen_typevergelijking_meer_in_de_service():
    """De oude beperking was een letterlijke typevergelijking. Die mag niet terugkomen: de grens
    hoort uit de catalogus te komen (`componentconfig_catalog.ondersteunt_werk`), zodat een nieuw
    componenttype de regel erft zonder dat iemand een lijst bijwerkt."""
    src = inspect.getsource(gg)
    assert "_APPLICATIE_TYPE" not in src, "de oude typeconstante is terug in gebruikersgroep_service"
    for verboden in ('componenttype != "applicatie"', "componenttype != 'applicatie'"):
        assert verboden not in src, f"typevergelijking {verboden} terug in gebruikersgroep_service"
    assert "componentconfig_catalog.ondersteunt_werk" in src, (
        "de grens moet uit de catalogus-vlag komen, niet uit een typevergelijking"
    )


def test_signaal_scope_komt_uit_de_catalogus():
    """Beide gg-signaalplekken (badge + tenant-brede lijst) delen de catalogus-subquery met het
    bedrijfsfunctie-signaal — geen tweede, driftende typelijst."""
    src = inspect.getsource(rg)
    assert src.count("_ondersteunt_werk_typen()") >= 4, (
        "verwacht: bedrijfsfunctie (badge + lijst) én gebruikersgroep (badge + lijst) delen de "
        "catalogus-subquery"
    )


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


async def _componenttypen(s) -> dict[str, bool]:
    """{optie_sleutel: ondersteunt_werk} uit de catalogus — DE bron van de verwachting."""
    from sqlalchemy import select
    from models.models import ComponentConfigDimensie, ComponentConfigOptie

    rijen = (
        await s.execute(
            select(ComponentConfigOptie.optie_sleutel, ComponentConfigOptie.ondersteunt_werk).where(
                ComponentConfigOptie.dimensie == ComponentConfigDimensie.componenttype
            )
        )
    ).all()
    return {r.optie_sleutel: bool(r.ondersteunt_werk) for r in rijen}


async def _maak_component(s, naam, componenttype):
    from models.models import Component, Element, ElementType, HostingModel

    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    s.add(Component(id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam,
                    componenttype=componenttype, hostingmodel=HostingModel.onbekend))
    await s.flush()
    return elem.id


async def _maak_organisatie(s, naam="ADR055-Organisatie"):
    from models.models import Element, ElementType, Partij, PartijAard, PartijScope

    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.partij)
    s.add(elem)
    await s.flush()
    s.add(Partij(id=elem.id, tenant_id=uuid.UUID(_TID), aard=PartijAard.organisatie,
                 naam=naam, scope=PartijScope.extern))
    await s.flush()
    return elem.id


async def _opruimen(s):
    from sqlalchemy import text

    for tabel in ("gebruikersgroep", "organisatiegebruik", "relatie", "component", "partij", "element"):
        await s.execute(text(f"DELETE FROM {tabel} WHERE tenant_id=:t"), {"t": _TID})
    await s.commit()


@integratie
def test_registratie_lukt_op_elk_type_dat_werk_ondersteunt():
    """DE tellende toets, over de catalogus i.p.v. een typelijst: op élk werk-ondersteunend type
    lukt de verfijning — óók op de fileshare, het geval waar ADR-055 om begonnen is."""
    from schemas.gebruikersgroep import GebruikersgroepCreate

    async def _fn(s):
        typen = await _componenttypen(s)
        werk = sorted(t for t, ow in typen.items() if ow)
        assert werk, "catalogus levert geen enkel werk-ondersteunend type — fixture-aanname stuk"
        org = await _maak_organisatie(s)
        gelukt = []
        for t in werk:
            cid = await _maak_component(s, f"ADR055-{t}", t)
            uit = await gg.maak_aan(
                s, _TID, GebruikersgroepCreate(component_id=cid, organisatie_id=org,
                                               aantal_gebruikers=3)
            )
            assert uit["id"] is not None
            gelukt.append(t)
        return werk, gelukt

    try:
        werk, gelukt = asyncio.run(_run_rls(_fn))
    finally:
        asyncio.run(_run_rls(_opruimen))
    assert gelukt == werk, f"niet op elk werk-ondersteunend type gelukt: {set(werk) - set(gelukt)}"
    assert "fileshare" in gelukt, "de gedeelde fileshare is HET geval uit ADR-055"


@integratie
def test_weigering_zegt_de_waarheid_niet_bestaat_niet():
    """Op een type dat geen werk ondersteunt wordt geweigerd — maar met "die vraag geldt hier niet"
    (422), NOOIT met "bestaat niet" (404). Het component bestaat; de gebruiker moet niet op zoek
    naar iets dat er wel is."""
    from schemas.gebruikersgroep import GebruikersgroepCreate

    async def _fn(s):
        typen = await _componenttypen(s)
        geen_werk = sorted(t for t, ow in typen.items() if not ow)
        assert geen_werk, "catalogus levert geen enkel niet-werk-ondersteunend type"
        org = await _maak_organisatie(s)
        codes = {}
        for t in geen_werk:
            cid = await _maak_component(s, f"ADR055-nw-{t}", t)
            try:
                await gg.maak_aan(
                    s, _TID, GebruikersgroepCreate(component_id=cid, organisatie_id=org)
                )
            except NietGevonden as e:  # pragma: no cover — dit is precies de fout die we opheffen
                pytest.fail(f"{t} geweigerd met 'bestaat niet' (404) i.p.v. 422: {e}")
            except OngeldigeRegistratie as e:
                codes[t] = e.code
            else:  # pragma: no cover
                pytest.fail(f"{t} ondersteunt geen werk maar de registratie werd toegestaan")
        return geen_werk, codes

    try:
        geen_werk, codes = asyncio.run(_run_rls(_fn))
    finally:
        asyncio.run(_run_rls(_opruimen))
    assert sorted(codes) == geen_werk
    assert set(codes.values()) == {"COMPONENT_ONDERSTEUNT_GEEN_WERK"}, codes


@integratie
def test_signaal_zwijgt_waar_de_vraag_niet_geldt():
    """Het registratiegat-signaal volgt dezelfde grens: op een type zonder `ondersteunt_werk` is
    "nog geen gebruikersgroep" géén open punt (er valt niets af te vinken), op een werk-
    ondersteunend type zónder verfijning wél."""
    async def _fn(s):
        typen = await _componenttypen(s)
        werk_t = next(t for t, ow in typen.items() if ow)
        geen_werk_t = next(t for t, ow in typen.items() if not ow)
        wid = await _maak_component(s, "ADR055-sig-werk", werk_t)
        nid = await _maak_component(s, "ADR055-sig-geenwerk", geen_werk_t)
        w = await rg.badge_voor_component(s, _TID, wid)
        n = await rg.badge_voor_component(s, _TID, nid)
        return set(w.get("signalen", [])), set(n.get("signalen", []))

    try:
        werk_sig, geen_werk_sig = asyncio.run(_run_rls(_fn))
    finally:
        asyncio.run(_run_rls(_opruimen))
    assert rg._SIG_GG in werk_sig, "werk-ondersteunend component zonder verfijning hoort het punt te dragen"
    assert rg._SIG_GG not in geen_werk_sig, (
        "een component waarmee niet gewerkt wordt hoort dit punt NIET te dragen — anders staat er "
        "een taak op de lijst die niemand kan afvinken"
    )
