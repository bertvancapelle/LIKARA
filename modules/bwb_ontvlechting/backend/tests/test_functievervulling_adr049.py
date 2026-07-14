"""Tests — ADR-049 (gate 2a): functievervulling (kale koppelregel component→bedrijfsfunctie).

Offline: model (twee PARTIËLE unieke indexen + drie CASCADE-FK's + kale as), schema
(extra='forbid', ouder optioneel), RBAC (koppelen=medewerker, verwijderen=beheerder), audit-
allowlist, engine-invariant, en de LEESREGEL-bijt-test (fijn-verdringt-grof leeft één keer;
de boom-view rekent niet zelf).

Live (skip-if-no-DB): grof + fijn maken; de leesregel per plek (fijn verdringt grof, grof blijft
elders); NULL-distinct STRUCTUREEL op DB-niveau (tweede grove dubbel geweigerd door de partiële
index, niet enkel app-side); adres-bestaat (422 ONBEKENDE_PLEK); vervallen-weigering; picker-scope
spiegelt de backend (ondersteunt_werk); fijn weghalen → grof weer leesbaar (niets weggeschreven);
RLS-isolatie; geen engine-state. Live-tests ruimen hun element-rijen structureel op (finally).
"""
import asyncio
import inspect
import pathlib
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
_VUE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "frontend" / "views" / "BedrijfsfunctieLijst.vue"
)


# ── Offline: model + schema ──────────────────────────────────────────────────────

def test_model_partiele_uniciteit_en_cascade_en_kaal():
    from models.models import Functievervulling

    assert Functievervulling.__tablename__ == "functievervulling"
    # Twee PARTIËLE unieke indexen — het NULL-distinct-gat structureel dicht (geen app-check).
    idx = {
        i.name: (i.unique, str(i.dialect_options["postgresql"].get("where")))
        for i in Functievervulling.__table__.indexes
    }
    # ADR-051 — de component-indexen dragen nu `component_id IS NOT NULL` (de geen-systeem-rijen
    # hebben eigen indexen, zie test_rollengrens/test_gapsignaal).
    assert idx["uq_functievervulling_grof"] == (True, "ouder_functie_id IS NULL AND component_id IS NOT NULL")
    assert idx["uq_functievervulling_fijn"] == (True, "ouder_functie_id IS NOT NULL AND component_id IS NOT NULL")
    # Drie composiet-FK's naar element, allemaal CASCADE.
    fks = {
        con.name: con
        for con in Functievervulling.__table__.constraints
        if con.__class__.__name__ == "ForeignKeyConstraint"
    }
    for naam in ("fk_functievervulling_component", "fk_functievervulling_functie", "fk_functievervulling_ouder"):
        assert fks[naam].ondelete == "CASCADE"
    # De as is KAAL — geen applicatiefunctie/werkwoord (ADR-049 besluit 3).
    kolommen = set(Functievervulling.__table__.columns.keys())
    assert "applicatiefunctie" not in kolommen
    assert {"component_id", "functie_id", "ouder_functie_id"} <= kolommen
    assert {"verklaard_door_sub", "verklaard_door"} <= kolommen  # wie/wanneer-stempel


def test_schema_validatie():
    from pydantic import ValidationError
    from schemas.functievervulling import FunctievervullingAanmaken

    grof = FunctievervullingAanmaken(component_id=uuid.uuid4(), functie_id=uuid.uuid4())
    assert grof.ouder_functie_id is None  # leeg adres = grof
    fijn = FunctievervullingAanmaken(
        component_id=uuid.uuid4(), functie_id=uuid.uuid4(), ouder_functie_id=uuid.uuid4()
    )
    assert fijn.ouder_functie_id is not None
    with pytest.raises(ValidationError):  # extra veld verboden (geen werkwoord smokkelen)
        FunctievervullingAanmaken(
            component_id=uuid.uuid4(), functie_id=uuid.uuid4(), applicatiefunctie="registreren"
        )


def test_rbac_en_audit():
    from app.core.audit import AUDIT_TENANT_ENTITEITEN
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    assert "functievervulling" in AUDIT_TENANT_ENTITEITEN
    # Koppelen = medewerker+; verwijderen = beheerder-only (opdracht §4/§6.7).
    assert heeft_permissie(["medewerker"], Entiteit.FUNCTIEVERVULLING, Actie.AANMAKEN)
    assert not heeft_permissie(["viewer"], Entiteit.FUNCTIEVERVULLING, Actie.AANMAKEN)
    assert heeft_permissie(["beheerder"], Entiteit.FUNCTIEVERVULLING, Actie.VERWIJDEREN)
    assert not heeft_permissie(["medewerker"], Entiteit.FUNCTIEVERVULLING, Actie.VERWIJDEREN)
    assert heeft_permissie(["auditor"], Entiteit.FUNCTIEVERVULLING, Actie.LEZEN)


def test_route_verwijder_erft_wijzigen_adr050():
    """ADR-050: een koppeling terugnemen is registratiebeheer (medewerker-werk). De DELETE ERFT
    zijn actie via `verwijder_actie()` (niet per route gekozen), die WIJZIGEN teruggeeft; de
    medewerker mag het, de viewer niet."""
    from app.core.rbac import Actie, Entiteit, heeft_permissie, verwijder_actie
    import routes.functievervulling as r

    src = inspect.getsource(r.verwijder_functievervulling)
    assert "verwijder_actie(Entiteit.FUNCTIEVERVULLING)" in src  # geërfd, niet herhaald
    assert verwijder_actie(Entiteit.FUNCTIEVERVULLING) == Actie.WIJZIGEN
    actie = verwijder_actie(Entiteit.FUNCTIEVERVULLING)
    assert heeft_permissie(["medewerker"], Entiteit.FUNCTIEVERVULLING, actie)
    assert not heeft_permissie(["viewer"], Entiteit.FUNCTIEVERVULLING, actie)


def test_service_raakt_engine_niet():
    """ADR-049-invariant: score blijft de enige lifecycle-driver."""
    import services.functievervulling_service as fvs

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(fvs, naam), f"functievervulling_service mag de engine niet importeren: {naam!r}"


def test_leesregel_leeft_een_keer_en_boom_rekent_niet_zelf():
    """De verdringing 'fijn verdringt grof' bestaat op ÉÉN plek (dekking_overzicht); geen enkele
    andere service-functie bouwt de plek-resolutie, en de boom-view LEEST de gedeelde uitkomst
    (roept `functievervullingen.dekking` aan) i.p.v. grof/fijn zelf te beslissen. Bronscan in de
    geest van test_filterbalk_li040::test_tel_en_lijst_delen_een_filterwaarheid."""
    import services.functievervulling_service as fvs

    # 1. De resolutie zit in dekking_overzicht…
    resolutie = inspect.getsource(fvs.dekking_overzicht)
    assert "fijn_per_plek" in resolutie and "grof_per_functie" in resolutie
    # …en in GEEN enkele andere functie van de service.
    for naam, fn in inspect.getmembers(fvs, inspect.isfunction):
        if naam == "dekking_overzicht":
            continue
        bron = inspect.getsource(fn)
        assert "fijn_per_plek" not in bron, f"tweede plek-resolutie in {naam!r}"

    # 2. De boom-view LEEST de gedeelde afleiding (roept dekking aan, toont 'herkomst', leest de
    #    reikwijdte-telling én de verdringing) en bouwt de resolutie/TELLING NIET zelf na
    #    (bronscan op de kern-datastructuren; "verdring" in comments is toegestaan — het gaat om
    #    de implementatie). LI041: een telling of verdringings-afleiding in de .vue moet FALEN.
    vue = _VUE.read_text(encoding="utf-8")
    assert "functievervullingen.dekking" in vue, "de boom moet de gedeelde dekking-afleiding lezen"
    assert "grof_geldt_op" in vue and ".verdrongen" in vue, (
        "de boom moet de reikwijdte-telling én de verdringing UIT de leeslaag lezen"
    )
    for verboden in ("fijn_per_plek", "grof_per_functie", "totaal_plekken_per_functie", "verfijnd_per_functie"):
        assert verboden not in vue, (
            f"de boom mag de resolutie/telling niet dupliceren ({verboden}) — die leeslaag hoort server-side"
        )


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                res = (await c.execute(text("SELECT to_regclass('functievervulling')"))).scalar()
            return res is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB/functievervulling-tabel niet bereikbaar")


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


async def _maak_component(s, naam, componenttype="applicatie"):
    from models.models import Component, Element, ElementType, HostingModel

    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    s.add(Component(id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam, componenttype=componenttype,
                    hostingmodel=HostingModel.on_premise))
    await s.commit()
    return elem.id


async def _maak_functie(s, naam, vervallen=False):
    from models.models import Bedrijfsfunctie, Element, ElementType

    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.bedrijfsfunctie)
    s.add(elem)
    await s.flush()
    s.add(Bedrijfsfunctie(id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam, vervallen=vervallen))
    await s.commit()
    return elem.id


async def _maak_plek(s, ouder_id, functie_id):
    """Een plaatsing = aggregation-relatie (bron = ouder, doel = functie)."""
    from models.models import Relatie

    s.add(Relatie(tenant_id=uuid.UUID(_TID), bron_id=ouder_id, doel_id=functie_id,
                  relatietype="aggregation", kenmerken={}))
    await s.commit()


async def _ruim(s, ids):
    from sqlalchemy import text as _text

    for eid in reversed(ids):
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    await s.commit()


@integratie
def test_leesregel_fijn_verdringt_grof_per_plek_live():
    """Grof geldt op alle plekken; een fijne verfijning wint op díé plek; het grove blijft
    elders leesbaar; fijn weghalen → grof daar wéér leesbaar (niets weggeschreven)."""
    from services import functievervulling_service as svc

    async def _flow(s):
        ids = []
        try:
            handh = await _maak_component(s, "FV Handhavingssysteem", "applicatie")
            insp = await _maak_component(s, "FV Inspectie-app", "applicatie")
            ids += [handh, insp]
            # Twee ouders (domeinen) + één functie (Toezicht) die onder beide staat.
            milieu = await _maak_functie(s, "FV Milieu")
            bouw = await _maak_functie(s, "FV Bouwen")
            toezicht = await _maak_functie(s, "FV Toezicht")
            ids += [milieu, bouw, toezicht]
            await _maak_plek(s, milieu, toezicht)
            await _maak_plek(s, bouw, toezicht)

            # Grof: handhavingssysteem ondersteunt Toezicht — geldt overal.
            await svc.maak_aan(s, _TID, handh, toezicht, None)
            grof = {(d["functie_id"], d["ouder_functie_id"]): d for d in await svc.dekking_overzicht(s, _TID)}
            # Fijn: onder Milieu de inspectie-app.
            fijn_reg = await svc.maak_aan(s, _TID, insp, toezicht, milieu)
            na_fijn = {(d["functie_id"], d["ouder_functie_id"]): d for d in await svc.dekking_overzicht(s, _TID)}
            # Fijn weghalen → grof daar weer leesbaar.
            await svc.verwijder(s, _TID, fijn_reg["vervulling_id"])
            na_weg = {(d["functie_id"], d["ouder_functie_id"]): d for d in await svc.dekking_overzicht(s, _TID)}
            return grof, na_fijn, na_weg, (toezicht, milieu, bouw, handh, insp)
        finally:
            await _ruim(s, ids)

    grof, na_fijn, na_weg, sleutels = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    toezicht, milieu, bouw, handh, insp = sleutels
    # Grof dekt BEIDE plekken van Toezicht; de reikwijdte-telling (LI041) zegt N=2, M=2.
    assert grof[(toezicht, milieu)]["herkomst"] == "grof"
    assert grof[(toezicht, bouw)]["herkomst"] == "grof"
    assert grof[(toezicht, milieu)]["componenten"][0]["component_id"] == handh
    assert grof[(toezicht, milieu)]["grof_totaal_plekken"] == 2
    assert grof[(toezicht, milieu)]["grof_geldt_op"] == 2
    # Ná verfijnen: Milieu wint fijn (inspectie-app) én BENOEMT het verdrongen grove antwoord;
    # Bouwen blijft grof en telt af (M=1 van N=2).
    assert na_fijn[(toezicht, milieu)]["herkomst"] == "fijn"
    assert na_fijn[(toezicht, milieu)]["componenten"][0]["component_id"] == insp
    assert na_fijn[(toezicht, milieu)]["verdrongen"][0]["component_id"] == handh  # grof is er nog
    assert na_fijn[(toezicht, bouw)]["herkomst"] == "grof"
    assert na_fijn[(toezicht, bouw)]["grof_totaal_plekken"] == 2
    assert na_fijn[(toezicht, bouw)]["grof_geldt_op"] == 1
    # Ná fijn weghalen: Milieu weer grof — het grove is nooit weggeschreven; telling weer M=2,
    # geen verdringing meer.
    assert na_weg[(toezicht, milieu)]["herkomst"] == "grof"
    assert na_weg[(toezicht, milieu)]["componenten"][0]["component_id"] == handh
    assert na_weg[(toezicht, milieu)]["grof_geldt_op"] == 2
    assert na_weg[(toezicht, milieu)]["verdrongen"] == []


@integratie
def test_verdrongen_sluit_bevestigd_uit_live():
    """LI041 correctie 2: een grof systeem dat op déze plek ÓÓK expliciet als verfijning staat
    is bevestigd, niet verdrongen → het valt uit `verdrongen`. Gelijk-only → leeg; gemengd →
    alleen het niet-bevestigde deel. De reikwijdte-telling verandert niet (de plek ís verfijnd)."""
    from services import functievervulling_service as svc

    async def _flow(s):
        ids = []
        try:
            a = await _maak_component(s, "FV-Bev A", "applicatie")  # grof + bevestigd
            b = await _maak_component(s, "FV-Bev B", "applicatie")  # alleen fijn
            c = await _maak_component(s, "FV-Bev C", "applicatie")  # grof, niet bevestigd
            ids += [a, b, c]
            p = await _maak_functie(s, "FV-Bev Ouder P")
            f = await _maak_functie(s, "FV-Bev Functie F")
            q = await _maak_functie(s, "FV-Bev Ouder Q")
            g = await _maak_functie(s, "FV-Bev Functie G")
            ids += [p, f, q, g]
            await _maak_plek(s, p, f)
            await _maak_plek(s, q, g)
            # F: twee grove (A, C); op plek (F,P) verfijnd met A (== grof) + B (nieuw).
            await svc.maak_aan(s, _TID, a, f, None)
            await svc.maak_aan(s, _TID, c, f, None)
            await svc.maak_aan(s, _TID, a, f, p)
            await svc.maak_aan(s, _TID, b, f, p)
            # G: grof A; op plek (G,Q) verfijnd met ALLEEN A (gelijk aan het grove).
            await svc.maak_aan(s, _TID, a, g, None)
            await svc.maak_aan(s, _TID, a, g, q)
            dek = {(d["functie_id"], d["ouder_functie_id"]): d for d in await svc.dekking_overzicht(s, _TID)}
            return dek[(f, p)], dek[(g, q)], (a, b, c)
        finally:
            await _ruim(s, ids)

    plek_f, plek_g, (a, b, c) = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    # Gemengd: A is bevestigd (staat in componenten én was grof) → niet verdrongen; C wél.
    assert {x["component_id"] for x in plek_f["componenten"]} == {a, b}
    assert [x["component_id"] for x in plek_f["verdrongen"]] == [c]
    # Gelijk-only: A verfijnd == A grof → verdrongen is LEEG (de regel verdwijnt).
    assert a in {x["component_id"] for x in plek_g["componenten"]}
    assert plek_g["verdrongen"] == []


@integratie
def test_null_distinct_tweede_grove_dubbel_structureel_geweigerd_live():
    """De partiële unieke index (WHERE ouder IS NULL) weigert een tweede grove dubbel op
    DB-NIVEAU — niet enkel de app-side pre-check. Bewijs: insert rechtstreeks (bypass service),
    verwacht een IntegrityError van uq_functievervulling_grof."""
    from sqlalchemy import text as _text
    from sqlalchemy.exc import IntegrityError

    async def _flow(s):
        ids = []
        try:
            comp = await _maak_component(s, "FV-Null Component", "applicatie")
            functie = await _maak_functie(s, "FV-Null Functie")
            ids += [comp, functie]
            ins = _text(
                "INSERT INTO functievervulling (tenant_id, component_id, functie_id) "
                "VALUES (:t, :c, :f)"
            )
            await s.execute(ins, {"t": _TID, "c": str(comp), "f": str(functie)})
            await s.commit()
            geweigerd = None
            try:
                await s.execute(ins, {"t": _TID, "c": str(comp), "f": str(functie)})
                await s.commit()
            except IntegrityError as e:
                await s.rollback()
                geweigerd = "uq_functievervulling_grof" in str(e.orig)
            return geweigerd
        finally:
            await _ruim(s, ids)

    assert asyncio.run(_run_rls(_TID, "test:bert", _flow)) is True


@integratie
def test_validaties_live():
    """adres-bestaat (fijn op niet-bestaande plek), vervallen-weigering, component-type-scope
    (ondersteunt_werk), verkeerd functie-type, en dubbel (409)."""
    from services import functievervulling_service as svc
    from services.errors import OngeldigeRegistratie, RegistratieConflict

    async def _flow(s):
        ids = []
        try:
            app_comp = await _maak_component(s, "FV-Val App", "applicatie")
            db_comp = await _maak_component(s, "FV-Val DB", "database")  # ondersteunt GEEN werk
            ids += [app_comp, db_comp]
            ouder = await _maak_functie(s, "FV-Val Ouder")
            kind = await _maak_functie(s, "FV-Val Kind")
            los = await _maak_functie(s, "FV-Val Los")  # geen plek onder ouder
            verv = await _maak_functie(s, "FV-Val Vervallen", vervallen=True)
            ids += [ouder, kind, los, verv]
            await _maak_plek(s, ouder, kind)
            fouten = {}
            # database-component ondersteunt geen werk ⇒ 422.
            try:
                await svc.maak_aan(s, _TID, db_comp, kind, None)
            except OngeldigeRegistratie as e:
                fouten["geen_werk"] = e.code
            # Vervallen functie ⇒ 422.
            try:
                await svc.maak_aan(s, _TID, app_comp, verv, None)
            except OngeldigeRegistratie as e:
                fouten["vervallen"] = e.code
            # Fijn op een niet-bestaande plek (kind staat niet onder 'los') ⇒ 422.
            try:
                await svc.maak_aan(s, _TID, app_comp, kind, los)
            except OngeldigeRegistratie as e:
                fouten["plek"] = e.code
            # Functie-kant is een component ⇒ 422.
            try:
                await svc.maak_aan(s, _TID, app_comp, app_comp, None)
            except OngeldigeRegistratie as e:
                fouten["functie_type"] = e.code
            # Dubbel grof ⇒ 409 (pre-check).
            await svc.maak_aan(s, _TID, app_comp, kind, None)
            try:
                await svc.maak_aan(s, _TID, app_comp, kind, None)
            except RegistratieConflict as e:
                fouten["dubbel"] = e.code
            # Fijn op een BESTAANDE plek slaagt (naast het grove).
            fijn = await svc.maak_aan(s, _TID, app_comp, kind, ouder)
            return fouten, fijn["herkomst"]
        finally:
            await _ruim(s, ids)

    fouten, fijn_herkomst = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert fouten == {
        "geen_werk": "COMPONENT_ONDERSTEUNT_GEEN_WERK",
        "vervallen": "VERVALLEN_NIET_KOPPELBAAR",
        "plek": "ONBEKENDE_PLEK",
        "functie_type": "ONGELDIGE_FUNCTIE",
        "dubbel": "KOPPELING_BESTAAT",
    }
    assert fijn_herkomst == "fijn"


@integratie
def test_meerdere_componenten_op_een_plek_en_cascade_rls_audit_live():
    """Meerdere componenten op één plek is normaal; element-cascade (component weg ⇒ koppeling
    weg); audit-capture; RLS-isolatie; geen engine-state."""
    from sqlalchemy import text as _text

    from services import functievervulling_service as svc

    async def _flow(s):
        ids = []
        try:
            c1 = await _maak_component(s, "FV-Multi A", "applicatie")
            c2 = await _maak_component(s, "FV-Multi B", "saas_dienst")
            ids += [c1, c2]
            functie = await _maak_functie(s, "FV-Multi Functie")
            ids.append(functie)
            r1 = await svc.maak_aan(s, _TID, c1, functie, None)
            await svc.maak_aan(s, _TID, c2, functie, None)
            dek = {d["functie_id"]: d for d in await svc.dekking_overzicht(s, _TID)}
            aantal_op_plek = len(dek[functie]["componenten"])  # twee systemen, één plek
            rid = str(r1["vervulling_id"])
            audit = (await s.execute(_text(
                "SELECT count(*) FROM audit_log WHERE entiteit_type='functievervulling' AND entiteit_id=:i"),
                {"i": rid})).scalar()
            profiel = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": rid})).scalar()
            # Element-cascade: component weg ⇒ koppeling weg.
            await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(c1)})
            await s.commit()
            ids.remove(c1)
            rest = (await s.execute(_text(
                "SELECT count(*) FROM functievervulling WHERE id=:i"), {"i": rid})).scalar()
            return aantal_op_plek, audit, profiel, rest, rid
        finally:
            await _ruim(s, ids)

    aantal_op_plek, audit, profiel, rest, rid = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert aantal_op_plek == 2 and audit >= 1 and profiel == 0 and rest == 0

    async def _zicht(s):
        from sqlalchemy import text as _text
        return (await s.execute(_text(
            "SELECT count(*) FROM functievervulling WHERE id=:i"), {"i": rid})).scalar()

    assert asyncio.run(_run_rls(_TID_B, "test:bert", _zicht)) == 0
