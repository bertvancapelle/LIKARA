"""Tests — ADR-051 (gate 3): het gap-signaal per plek.

Offline: model (geen_systeem + oordeel + de twee CHECKs + de geen-systeem-indexen), enum, schema
(oordeel gesloten set), RBAC (geen-systeem = AANMAKEN, oordeel = WIJZIGEN, verwijderen erft WIJZIGEN).

Live (skip-if-no-DB): de "precies één van beide"-CHECK op DB-niveau (geen van beide / allebei /
oordeel-op-bevinding geweigerd); registreer geen-systeem + de coëxistentie-guards; zet/wis oordeel;
de VIJF standen (gat · via_boven · hier · werkvoorraad · niets) uitputtend + de OMHOOG-cue met
terugval + de hier/werkvoorraad-split (gebruikersgroep aanwezig vs. ontbreekt — ADR-043 gate 4
brok 1) + de leeslaag-vlag `heeft_gebruikersgroep`. Live-tests ruimen hun element-rijen op (finally).
"""
import asyncio
import inspect
import uuid

import pytest

import app.core.audit  # noqa: F401
import app.core.database  # noqa: F401
from app.core.tenant_context import (
    reset_audit_context, reset_tenant_context, zet_audit_context, zet_tenant_context,
)

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline ──────────────────────────────────────────────────────────────────────

def test_model_geen_systeem_oordeel_en_checks():
    from models.models import Functievervulling, FunctievervullingOordeel

    kols = Functievervulling.__table__.columns
    assert "geen_systeem" in kols and "oordeel" in kols
    assert kols["component_id"].nullable is True
    checks = {c.name for c in Functievervulling.__table__.constraints if c.__class__.__name__ == "CheckConstraint"}
    assert "ck_functievervulling_component_xor_geen" in checks
    assert "ck_functievervulling_oordeel_alleen_component" in checks
    idx = {i.name for i in Functievervulling.__table__.indexes}
    assert {"uq_functievervulling_geen_grof", "uq_functievervulling_geen_fijn"} <= idx
    assert {o.value for o in FunctievervullingOordeel} == {"naar_behoren", "noodoplossing"}


def test_schema_oordeel_gesloten_set():
    from pydantic import ValidationError
    from schemas.functievervulling import FunctievervullingAanmaken, GeenSysteemAanmaken, OordeelWijzigen

    assert FunctievervullingAanmaken(component_id=uuid.uuid4(), functie_id=uuid.uuid4(), oordeel="noodoplossing")
    assert OordeelWijzigen(oordeel=None).oordeel is None  # leeg = nog niet beoordeeld
    with pytest.raises(ValidationError):
        OordeelWijzigen(oordeel="ongeveer_ok")  # geen sentinel/onbekend
    assert GeenSysteemAanmaken(functie_id=uuid.uuid4()).ouder_functie_id is None


def test_rbac_geen_systeem_oordeel_verwijderen():
    from app.core.rbac import Actie, Entiteit, heeft_permissie, verwijder_actie

    # ADR-050 — vastleggen/terugnemen van een uitkomst/oordeel is registratie → medewerker.
    assert heeft_permissie(["medewerker"], Entiteit.FUNCTIEVERVULLING, Actie.AANMAKEN)   # geen-systeem
    assert heeft_permissie(["medewerker"], Entiteit.FUNCTIEVERVULLING, Actie.WIJZIGEN)   # oordeel
    assert verwijder_actie(Entiteit.FUNCTIEVERVULLING) == Actie.WIJZIGEN                 # terugnemen
    assert heeft_permissie(["viewer"], Entiteit.FUNCTIEVERVULLING, Actie.LEZEN)          # standen lezen
    assert not heeft_permissie(["viewer"], Entiteit.FUNCTIEVERVULLING, Actie.AANMAKEN)


def test_plek_standen_afleiding_leeft_in_de_service():
    """ADR-051 besluit 5 + ADR-043 gate 4 — de vijf standen + de omhoog-cue worden in de service
    afgeleid (één bron)."""
    from services import functievervulling_service as fvs

    src = inspect.getsource(fvs.plek_standen)
    for kern in ("via_boven", "_dichtstbijzijnde_dragers", "via_aantal", "gat", "niets", "hier", "werkvoorraad"):
        assert kern in src


def test_standen_afleiding_niet_gedupliceerd_in_de_vue():
    """ADR-051 besluit 5 — de vier standen én de teller komen uit `plek_standen`; beide vensters
    (boom + centrale signalering) LEZEN die (roepen `standen` aan) en leiden geen stand of telling
    zelf af. Bronscan: een tweede implementatie in een `.vue` faalt hier (les LI038)."""
    import pathlib

    views = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "views"
    boom = (views / "BedrijfsfunctieLijst.vue").read_text(encoding="utf-8")
    venster2 = (views / "WerkvoorraadPlekView.vue").read_text(encoding="utf-8")
    for vue in (boom, venster2):
        assert "functievervullingen.standen" in vue  # leest de gedeelde afleiding
        # De afleiding-internals mogen niet in de .vue leven (comment-verwijzingen naar de
        # endpoint-naam zijn toegestaan — het gaat om de implementatie).
        for verboden in ("_dichtstbijzijnde_dragers", "functies_met_koppeling"):
            assert verboden not in vue, f"stand-afleiding gedupliceerd in de .vue: {verboden}"
    # De teller in venster 2 komt uit de gedeelde `tellers`, niet uit een eigen telling van de lijst.
    assert "tellers.value.gat" in venster2


# ── Live ─────────────────────────────────────────────────────────────────────────

def _db() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _c():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                return (await c.execute(text("SELECT to_regclass('functievervulling')"))).scalar() is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_c())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db(), reason="lk_app-DB niet bereikbaar")


async def _run(fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tt = zet_tenant_context(_TID)
    at = zet_audit_context("test:bert", "test:bert@test")
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_audit_context(at)
        reset_tenant_context(tt)
        await eng.dispose()


async def _functie(s, naam):
    from models.models import Bedrijfsfunctie, Element, ElementType
    e = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.bedrijfsfunctie)
    s.add(e); await s.flush()
    s.add(Bedrijfsfunctie(id=e.id, tenant_id=uuid.UUID(_TID), naam=naam)); await s.commit()
    return e.id


async def _component(s, naam):
    from models.models import Component, Element, ElementType, HostingModel
    e = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
    s.add(e); await s.flush()
    s.add(Component(id=e.id, tenant_id=uuid.UUID(_TID), naam=naam, componenttype="applicatie",
                    hostingmodel=HostingModel.on_premise)); await s.commit()
    return e.id


async def _plek(s, ouder, kind):
    from models.models import Relatie
    s.add(Relatie(tenant_id=uuid.UUID(_TID), bron_id=ouder, doel_id=kind, relatietype="aggregation", kenmerken={}))
    await s.commit()


async def _serving_gg(s, component_id):
    """ADR-043 gate 4 brok 1 — geef `component_id` een gebruikersgroep via de BESTAANDE serving-
    relatie (bron=component → doel=gebruikersgroep, ADR-023) — dezelfde relatie/richting die
    `componenten_met_gebruikersgroep` leest. Retourneert het gebruikersgroep-element-id (opruimen)."""
    from models.models import Element, ElementType, Relatie
    gg = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.gebruikersgroep)
    s.add(gg); await s.flush()
    s.add(Relatie(tenant_id=uuid.UUID(_TID), bron_id=component_id, doel_id=gg.id,
                  relatietype="serving", kenmerken={}))
    await s.commit()
    return gg.id


async def _ruim(s, ids):
    from sqlalchemy import text
    for i in reversed(ids):
        await s.execute(text("DELETE FROM element WHERE id=:i"), {"i": str(i)})
    await s.commit()


@integratie
def test_gg_signaal_leest_bron_niet_doel_live():
    """feitcheck-serving-richting — de gg-signalering leest de serving op **bron=component**
    (ADR-023, gedeelde richting-bron). Een component MÉT gebruikersgroep valt uit
    `component_zonder_gebruikersgroep` én draagt geen `component_zonder_gebruikersgroep`-badge; een
    component ZÓNDER valt er wél in. Deze test faalt zodra iemand de lezing terugdraait naar
    `doel_id` (dan vlagt élk component onterecht)."""
    from services import registratiegaten_service as rgs

    _SIG = "component_zonder_gebruikersgroep"

    async def _flow(s):
        ids = []
        try:
            met = await _component(s, "SR Met gg")
            zonder = await _component(s, "SR Zonder gg")
            ids += [met, zonder]
            gg = await _serving_gg(s, met)   # serving bron=component → doel=gebruikersgroep
            ids.append(gg)
            lijst = {r["id"] for r in await rgs.component_zonder_gebruikersgroep(s, _TID)}
            badge_met = await rgs.badge_voor_component(s, _TID, met)
            badge_zonder = await rgs.badge_voor_component(s, _TID, zonder)
            return met, zonder, lijst, badge_met, badge_zonder
        finally:
            await _ruim(s, ids)

    met, zonder, lijst, badge_met, badge_zonder = asyncio.run(_run(_flow))
    # Component MÉT gebruikersgroep: niet in de signaallijst, geen gg-badge.
    assert met not in lijst
    assert _SIG not in badge_met["signalen"]
    # Component ZÓNDER: wél in de signaallijst, wél gg-badge.
    assert zonder in lijst
    assert _SIG in badge_zonder["signalen"]


@integratie
def test_check_precies_een_van_beide_op_db_niveau():
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    async def _flow(s):
        ids = []
        try:
            f = await _functie(s, "GS-Check Functie"); ids.append(f)
            fouten = {}
            # geen van beide: component NULL én geen_systeem false → XOR-CHECK weigert.
            for kolommen, label in (
                ("(tenant_id, functie_id) VALUES (:t, :f)", "geen_van_beide"),
                ("(tenant_id, functie_id, component_id, geen_systeem) VALUES (:t, :f, :f, true)", "allebei"),
                ("(tenant_id, functie_id, geen_systeem, oordeel) VALUES (:t, :f, true, 'noodoplossing')", "oordeel_op_bevinding"),
            ):
                try:
                    await s.execute(text(f"INSERT INTO functievervulling {kolommen}"), {"t": _TID, "f": str(f)})
                    await s.commit()
                except IntegrityError as e:
                    await s.rollback()
                    fouten[label] = "ck_functievervulling" in str(e.orig)
            return fouten
        finally:
            await _ruim(s, ids)

    assert asyncio.run(_run(_flow)) == {"geen_van_beide": True, "allebei": True, "oordeel_op_bevinding": True}


@integratie
def test_geen_systeem_coexistentie_en_oordeel_live():
    from services import functievervulling_service as svc
    from services.errors import OngeldigeRegistratie, RegistratieConflict

    async def _flow(s):
        ids = []
        try:
            comp = await _component(s, "GS-Co Component")
            ouder = await _functie(s, "GS-Co Ouder")
            kind = await _functie(s, "GS-Co Kind")
            ids += [comp, ouder, kind]
            await _plek(s, ouder, kind)
            fouten = {}
            # Registreer "geen systeem" op de plek (kind onder ouder).
            bev = await svc.registreer_geen_systeem(s, _TID, kind, ouder)
            # Daar nu koppelen ⇒ 409 (tegengesteld).
            try:
                await svc.maak_aan(s, _TID, comp, kind, ouder)
            except RegistratieConflict as e:
                fouten["koppel_op_bevinding"] = e.code
            # Dubbele bevinding ⇒ 409.
            try:
                await svc.registreer_geen_systeem(s, _TID, kind, ouder)
            except RegistratieConflict as e:
                fouten["dubbel"] = e.code
            # Oordeel op een bevinding ⇒ 422.
            try:
                await svc.zet_oordeel(s, _TID, bev["vervulling_id"], "naar_behoren")
            except OngeldigeRegistratie as e:
                fouten["oordeel_op_bevinding"] = e.code
            # Grove koppeling op een ANDERE functie + oordeel zetten/wissen.
            los = await _functie(s, "GS-Co Los"); ids.append(los)
            kop = await svc.maak_aan(s, _TID, comp, los, None, None, "noodoplossing")
            gewist = await svc.zet_oordeel(s, _TID, kop["vervulling_id"], None)
            # "geen systeem" waar al gekoppeld is ⇒ 409.
            try:
                await svc.registreer_geen_systeem(s, _TID, los, None)
            except RegistratieConflict as e:
                fouten["bevinding_op_koppeling"] = e.code
            return bev["herkomst"], kop["oordeel"], gewist["oordeel"], fouten
        finally:
            await _ruim(s, ids)

    herkomst, kop_oordeel, gewist, fouten = asyncio.run(_run(_flow))
    assert herkomst == "geen_systeem"
    assert kop_oordeel == "noodoplossing" and gewist is None
    assert fouten == {
        "koppel_op_bevinding": "PLEK_IS_GEEN_SYSTEEM",   # koppelen waar "niets" vastligt
        "dubbel": "BEVINDING_BESTAAT",
        "oordeel_op_bevinding": "OORDEEL_OP_BEVINDING",
        "bevinding_op_koppeling": "PLEK_HEEFT_KOPPELING",  # "niets" waar al gekoppeld is
    }


@integratie
def test_vier_standen_en_omhoog_cue_live():
    """De omhoog-cue: koppel hoog → een plek diep eronder meldt 'via_boven'; koppel daar direct →
    'hier'; haal weg → terug naar 'via_boven' (niet 'gat'). Plus 'niets' en uitputtendheid."""
    from services import functievervulling_service as svc

    async def _flow(s):
        ids = []
        try:
            comp = await _component(s, "ST Component")
            gg = await _serving_gg(s, comp)          # gg aanwezig → gedekte plekken blijven 'hier'
            top = await _functie(s, "ST Top")        # wortel
            mid = await _functie(s, "ST Mid")
            laag = await _functie(s, "ST Laag")
            ids += [comp, gg, top, mid, laag]
            await _plek(s, top, mid)                 # plek (mid, top)
            await _plek(s, mid, laag)                # plek (laag, mid)

            def standen():
                async def _q(s2):
                    r = await svc.plek_standen(s2, _TID)
                    return ({(p["functie_id"], p["ouder_functie_id"]): p for p in r["plekken"]}, r["tellers"])
                return _q

            # 0. Niets gekoppeld: alle drie plekken 'gat'.
            p0, t0 = await standen()(s)
            # 1. Grof koppelen op TOP → mid en laag krijgen de omhoog-cue.
            await svc.maak_aan(s, _TID, comp, top, None)
            p1, _ = await standen()(s)
            # 2. Direct koppelen op MID → (mid,top) wordt 'hier'; (laag,mid) via = mid (dichtstbij).
            kop = await svc.maak_aan(s, _TID, comp, mid, top)
            p2, _ = await standen()(s)
            # 3. Die koppeling weghalen → (mid,top) valt TERUG op de cue, niet op gat.
            await svc.verwijder(s, _TID, kop["vervulling_id"])
            p3, _ = await standen()(s)
            # 4. Op (laag,mid) "geen systeem" vastleggen → 'niets'.
            await svc.registreer_geen_systeem(s, _TID, laag, mid)
            p4, t4 = await standen()(s)
            return (top, mid, laag), p0, t0, p1, p2, p3, p4, t4
        finally:
            await _ruim(s, ids)

    (top, mid, laag), p0, t0, p1, p2, p3, p4, t4 = asyncio.run(_run(_flow))
    # 0 — alles gat; uitputtend (elke plek precies één stand uit de vier).
    assert p0[(mid, top)]["stand"] == "gat" and p0[(laag, mid)]["stand"] == "gat"
    assert set(p0[(mid, top)]) >= {"stand", "via_functie_id"}
    # 1 — omhoog-cue op mid en laag; top zelf 'hier'.
    assert p1[(top, None)]["stand"] == "hier"
    assert p1[(mid, top)]["stand"] == "via_boven" and p1[(mid, top)]["via_functie_id"] == top
    assert p1[(laag, mid)]["stand"] == "via_boven" and p1[(laag, mid)]["via_functie_id"] == top
    # 2 — direct koppelen op mid: (mid,top) 'hier'; (laag,mid) via = mid (dichterbij dan top).
    assert p2[(mid, top)]["stand"] == "hier"
    assert p2[(laag, mid)]["stand"] == "via_boven" and p2[(laag, mid)]["via_functie_id"] == mid
    # 3 — weghalen → terug naar de cue (via top), NIET gat.
    assert p3[(mid, top)]["stand"] == "via_boven" and p3[(mid, top)]["via_functie_id"] == top
    # 4 — "geen systeem" → 'niets'; teller telt.
    assert p4[(laag, mid)]["stand"] == "niets"
    assert t4["niets"] >= 1 and t4["via_boven"] >= 1 and t4["hier"] >= 1


@integratie
def test_omhoog_cue_plek_specifiek_en_gelijke_afstand_telt_live():
    """§1-reparatie: de walk volgt het pad van DÉZE plek (niet alle ouders van de functie), en bij
    meerdere dragers op gelijke afstand telt de cue i.p.v. een willekeurige naam te kiezen."""
    from services import functievervulling_service as svc

    async def _flow(s):
        ids = []
        try:
            comp = await _component(s, "PS Component")
            # F staat op TWEE plekken: onder P1 en onder P2. Alleen boven P1 hangt iets.
            p1 = await _functie(s, "PS P1")
            p2 = await _functie(s, "PS P2")
            f = await _functie(s, "PS F")
            ids += [comp, p1, p2, f]
            await _plek(s, p1, f)
            await _plek(s, p2, f)
            await svc.maak_aan(s, _TID, comp, p1, None)  # grof op P1

            # G onder Q; Q onder R1 én R2 — beide dragen: gelijke afstand, twee dragers.
            r1 = await _functie(s, "PS R1")
            r2 = await _functie(s, "PS R2")
            q = await _functie(s, "PS Q")
            g = await _functie(s, "PS G")
            ids += [r1, r2, q, g]
            await _plek(s, r1, q)
            await _plek(s, r2, q)
            await _plek(s, q, g)
            await svc.maak_aan(s, _TID, comp, r1, None)
            await svc.maak_aan(s, _TID, comp, r2, None)

            r = await svc.plek_standen(s, _TID)
            per = {(p["functie_id"], p["ouder_functie_id"]): p for p in r["plekken"]}
            return per, (p1, p2, f, q, g)
        finally:
            await _ruim(s, ids)

    per, (p1, p2, f, q, g) = asyncio.run(_run(_flow))
    # Plek-specifiek: alleen F-onder-P1 krijgt de cue (via P1); F-onder-P2 is 'gat'.
    assert per[(f, p1)]["stand"] == "via_boven" and per[(f, p1)]["via_functie_id"] == p1
    assert per[(f, p2)]["stand"] == "gat"
    # Gelijke afstand, twee dragers: telling, geen willekeurige naam.
    assert per[(g, q)]["stand"] == "via_boven"
    assert per[(g, q)]["via_functie_id"] is None and per[(g, q)]["via_aantal"] == 2


@integratie
def test_hier_vs_werkvoorraad_split_en_leeslaag_live():
    """ADR-043 gate 4 brok 1 — een gedekte plek is 'hier' als ÁLLE dekkende systemen een
    gebruikersgroep dragen, en 'werkvoorraad' zodra ≥1 dekkend systeem er géén draagt (streng).
    Plus de leeslaag-vlag `heeft_gebruikersgroep` per component in `dekking_overzicht`."""
    from services import functievervulling_service as svc

    async def _flow(s):
        ids = []
        try:
            comp_met = await _component(s, "WV Met")
            gg = await _serving_gg(s, comp_met)
            comp_zonder = await _component(s, "WV Zonder")
            root = await _functie(s, "WV Root")
            fa = await _functie(s, "WV A")   # alleen comp_met  → hier
            fb = await _functie(s, "WV B")   # alleen comp_zonder → werkvoorraad
            fc = await _functie(s, "WV C")   # beide → werkvoorraad (streng: één zonder gg volstaat)
            ids += [comp_met, gg, comp_zonder, root, fa, fb, fc]
            await _plek(s, root, fa)         # plekken (fa,root) (fb,root) (fc,root)
            await _plek(s, root, fb)
            await _plek(s, root, fc)
            await svc.maak_aan(s, _TID, comp_met, fa, None)
            await svc.maak_aan(s, _TID, comp_zonder, fb, None)
            await svc.maak_aan(s, _TID, comp_met, fc, None)
            await svc.maak_aan(s, _TID, comp_zonder, fc, None)

            r = await svc.plek_standen(s, _TID)
            per = {(p["functie_id"], p["ouder_functie_id"]): p for p in r["plekken"]}
            dekking = await svc.dekking_overzicht(s, _TID)
            gg_per_comp = {}
            for d in dekking:
                for c in d["componenten"]:
                    gg_per_comp[c["component_id"]] = c["heeft_gebruikersgroep"]
            return per, r["tellers"], gg_per_comp, (root, fa, fb, fc, comp_met, comp_zonder)
        finally:
            await _ruim(s, ids)

    per, tellers, gg_per_comp, (root, fa, fb, fc, comp_met, comp_zonder) = asyncio.run(_run(_flow))
    # De split: volledig belegd → 'hier'; ≥1 systeem zonder gg → 'werkvoorraad'.
    assert per[(fa, root)]["stand"] == "hier"
    assert per[(fb, root)]["stand"] == "werkvoorraad"
    assert per[(fc, root)]["stand"] == "werkvoorraad"   # streng: één zonder gg volstaat
    assert tellers["hier"] >= 1 and tellers["werkvoorraad"] >= 2
    # De leeslaag-vlag per component (read-only, uit de serving-relatie).
    assert gg_per_comp[comp_met] is True
    assert gg_per_comp[comp_zonder] is False
