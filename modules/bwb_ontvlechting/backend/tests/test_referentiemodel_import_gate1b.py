"""Tests — gate 1b: het referentiemodel inlezen (AMEFF-parser + dry-run + uitvoering).

Offline: de parser tegen het ÉCHTE GEMMA-bestand (de verkenning-cijfers 297/302/2455
zijn de spec), het harde xsi:type-filter, XXE-/vormfout-weigering, het pure
vergelijkingsplan (`_bepaal_plan` — nieuw/bijgewerkt/vervallen/herleefd/verhangen/
bevroren), de read-only-borging van de dry-run (bronscan), engine-import-afwezigheid
en het aanbod-bestand zelf (aanwezig + byte-exact).
Live (skip-if-no-DB): dry-run schrijft niets; uitvoering = exact het plan; herinlees
idempotent (0 wijzigingen); vervallen = vlag (rij blijft, plaatsing bevroren); eigen
functies ongemoeid; meervoudige plaatsingen komen door; onbekend model geweigerd; en
één run op het echte bestand (297 nieuw · 302 plaatsingen) mét duurmeting. Live-tests
ruimen hun element-rijen + modelrij structureel op (in finally; residu 0).
"""
import asyncio
import time
import uuid
from pathlib import Path

import pytest

import app.core.audit  # noqa: F401 — registreert de audit-capture-hook
import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import (
    reset_audit_context,
    reset_tenant_context,
    zet_audit_context,
    zet_tenant_context,
)

# EIGEN test-tenant — bewust NIET de dev-tenant (1111…): de import-teardown ruimt álle
# functies van het geteste model in zijn tenant op; in de dev-tenant zou dat de geseede
# GEMMA-boom opeten (self-contained-regel, likara-tests). RLS isoleert per tenant.
_TID = "99999999-9999-4999-9999-999999999999"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"

_ECHT_BESTAND = (
    Path(__file__).resolve().parents[1] / "referentiemodellen" / "GEMMA_release_2026-07-01.xml"
)

_AMEFF_KOP = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<model xmlns="http://www.opengroup.org/xsd/archimate/3.0/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" identifier="m1">\n'
    '<name xml:lang="nl">Testmodel</name>\n'
)


def _schrijf(tmp_path, inhoud: str) -> Path:
    p = tmp_path / "model.xml"
    p.write_text(inhoud, encoding="utf-8")
    return p


# ── Offline: parser tegen het echte bestand (de verkenning is de spec) ────────────

def test_parser_leest_echte_gemma_bestand():
    """Verkenning-V040-cijfers als spec: 297 functies · 302 plaatsingen · 2455
    overgeslagen (25 typen) · 10 zonder definitie · 7 meervoudige kinderen · 8 wortels."""
    from services.ameff import lees_ameff

    inhoud = lees_ameff(_ECHT_BESTAND)
    assert len(inhoud.functies) == 297
    assert len(inhoud.plaatsingen) == 302
    assert inhoud.overgeslagen_totaal == 2455
    assert len(inhoud.overgeslagen) == 25
    assert sum(1 for f in inhoud.functies if f.definitie is None) == 10

    ouders_per_kind: dict = {}
    for ouder, kind in inhoud.plaatsingen:
        ouders_per_kind.setdefault(kind, set()).add(ouder)
    namen = {f.sleutel: f.naam for f in inhoud.functies}
    meervoudig = sorted(namen[k] for k, o in ouders_per_kind.items() if len(o) > 1)
    assert meervoudig == [
        "Afrekening", "Autorisatievaststelling", "Burgerinitiatieven facilitering",
        "Burgerlijke stand diensten", "Handhaving", "Identiteitvaststelling", "Toezicht",
    ]
    wortels = sorted(namen[s] for s in namen if s not in ouders_per_kind)
    assert wortels == [
        "Belastingoplegging", "Bewaking", "Klant- en keteninteractie", "Ondersteuning",
        "Ontwikkeling", "Regievoering", "Sturing", "Uitvoering",
    ]


def test_aanbod_bestand_aanwezig_en_byte_exact():
    """Repo-route (besloten LI039): het gecureerde bestand reist mee in de release —
    aanwezig én byte-exact (grootte uit HERKOMST.md)."""
    from services.referentiemodel_import_service import _AANBOD_BESTANDEN

    pad = _AANBOD_BESTANDEN["gemma_bedrijfsfuncties"]
    assert pad == _ECHT_BESTAND
    assert pad.is_file()
    assert pad.stat().st_size == 13_411_843


# ── Offline: filter + veiligheid + vormfouten ─────────────────────────────────────

def test_parser_filtert_hard_op_xsi_type(tmp_path):
    """Alleen BusinessFunction + aggregation met BF aan BEIDE kanten; al het andere
    wordt GETELD overgeslagen (nooit stil weggegooid)."""
    from services.ameff import lees_ameff

    pad = _schrijf(tmp_path, _AMEFF_KOP + """
<elements>
  <element identifier="id-a" xsi:type="BusinessFunction">
    <name xml:lang="nl">Alpha</name>
    <documentation xml:lang="nl">Definitie A</documentation>
  </element>
  <element identifier="id-b" xsi:type="BusinessFunction"><name>Beta</name></element>
  <element identifier="id-p" xsi:type="BusinessProcess"><name>Proces</name></element>
  <element identifier="id-o" xsi:type="BusinessObject"><name>Object</name></element>
</elements>
<relationships>
  <relationship identifier="r1" source="id-a" target="id-b" xsi:type="Aggregation"/>
  <relationship identifier="r2" source="id-a" target="id-p" xsi:type="Aggregation"/>
  <relationship identifier="r3" source="id-p" target="id-b" xsi:type="Aggregation"/>
  <relationship identifier="r4" source="id-a" target="id-b" xsi:type="Composition"/>
</relationships>
</model>""")
    inhoud = lees_ameff(pad)
    assert {f.sleutel for f in inhoud.functies} == {"id-a", "id-b"}
    assert inhoud.plaatsingen == frozenset({("id-a", "id-b")})
    assert inhoud.overgeslagen == {"BusinessProcess": 1, "BusinessObject": 1}
    per = {f.sleutel: f for f in inhoud.functies}
    assert per["id-a"].definitie == "Definitie A"
    assert per["id-b"].definitie is None  # geen documentation = leeg, geen fout


def test_parser_schoont_bron_op_met_de_gedeelde_regel(tmp_path):
    """LI051 weg 1 — de parser schoont naam én definitie op bij de uitvoer, met de gedeelde regel
    (`schemas/tekstschoning`): een vaste spatie wordt een gewone (woordgrens blijft), een zero-width
    teken verdwijnt, dubbele spaties vouwen samen. Omdat aanmaken (via het schema), bijwerken (directe
    toewijzing) én de her-inlees-vergelijking allemaal deze ene opgeschoonde brontekst gebruiken,
    dragen ze vanzelf identieke tekst — geen twee definities die uiteen groeien."""
    from services.ameff import lees_ameff

    nbsp = chr(0x00A0)
    zwsp = chr(0x200B)
    pad = _schrijf(tmp_path, _AMEFF_KOP + f"""
<elements>
  <element identifier="id-a" xsi:type="BusinessFunction">
    <name xml:lang="nl">Zaak{nbsp}systeem  beheer</name>
    <documentation xml:lang="nl">Regel  met{zwsp}   ruis.</documentation>
  </element>
</elements>
</model>""")
    f = lees_ameff(pad).functies[0]
    assert f.naam == "Zaak systeem beheer"   # NBSP -> spatie, dubbele spatie samengevouwen
    assert f.definitie == "Regel met ruis."  # zero-width weg, spaties samengevouwen


def test_parser_weigert_onveilige_xml(tmp_path):
    """XXE-borging: een bestand met DTD/entiteiten (external entity of
    entity-expansion) wordt geweigerd met één leesbare fout."""
    from services.ameff import AmeffFout, lees_ameff

    xxe = (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE model [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>\n'
        '<model xmlns="http://www.opengroup.org/xsd/archimate/3.0/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<elements><element identifier=\"id-a\" xsi:type=\"BusinessFunction\">"
        "<name>&xxe;</name></element></elements></model>"
    )
    with pytest.raises(AmeffFout, match="geweigerd"):
        lees_ameff(_schrijf(tmp_path, xxe))

    lol = (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE model [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">'
        '<!ENTITY c "&b;&b;&b;&b;">]>\n'
        '<model xmlns="http://www.opengroup.org/xsd/archimate/3.0/">'
        "<elements/></model>"
    )
    with pytest.raises(AmeffFout, match="geweigerd"):
        lees_ameff(_schrijf(tmp_path, lol))


def test_parser_vormfouten_zijn_luid(tmp_path):
    """Stil overslaan = stil weggooien: geen identifier, dubbele identifier, geen naam,
    geen XML en een niet-AMEFF-wortel zijn elk één leesbare fout."""
    from services.ameff import AmeffFout, lees_ameff

    with pytest.raises(AmeffFout, match="geen identifier"):
        lees_ameff(_schrijf(tmp_path, _AMEFF_KOP + (
            '<elements><element xsi:type="BusinessFunction"><name>X</name></element>'
            "</elements></model>")))
    with pytest.raises(AmeffFout, match="Dubbele identifier"):
        lees_ameff(_schrijf(tmp_path, _AMEFF_KOP + (
            '<elements>'
            '<element identifier="id-a" xsi:type="BusinessFunction"><name>X</name></element>'
            '<element identifier="id-a" xsi:type="BusinessFunction"><name>Y</name></element>'
            "</elements></model>")))
    with pytest.raises(AmeffFout, match="geen naam"):
        lees_ameff(_schrijf(tmp_path, _AMEFF_KOP + (
            '<elements><element identifier="id-a" xsi:type="BusinessFunction"/>'
            "</elements></model>")))
    with pytest.raises(AmeffFout, match="geldig XML"):
        lees_ameff(_schrijf(tmp_path, "dit is geen xml < >"))
    with pytest.raises(AmeffFout, match="geen ArchiMate"):
        lees_ameff(_schrijf(tmp_path, '<?xml version="1.0"?><iets/>'))


def test_parser_meertalige_naam_nl_wint(tmp_path):
    from services.ameff import lees_ameff

    pad = _schrijf(tmp_path, _AMEFF_KOP + (
        '<elements><element identifier="id-a" xsi:type="BusinessFunction">'
        '<name xml:lang="en">English</name><name xml:lang="nl">Nederlands</name>'
        "</element></elements></model>"))
    assert lees_ameff(pad).functies[0].naam == "Nederlands"


# ── Offline: het pure vergelijkingsplan (dry-run = uitvoering) ───────────────────

def _inhoud(functies, plaatsingen=(), overgeslagen=None):
    from services.ameff import AmeffFunctie, AmeffInhoud

    return AmeffInhoud(
        element_type="BusinessFunction",
        functies=tuple(AmeffFunctie(sleutel=s, naam=n, definitie=d) for s, n, d in functies),
        plaatsingen=frozenset(plaatsingen),
        overgeslagen=dict(overgeslagen or {}),
    )


def _stand(*rijen):
    from services.referentiemodel_import_service import FunctieStand

    return [
        FunctieStand(sleutel=s, naam=n, definitie=d, vervallen=v) for s, n, d, v in rijen
    ]


def test_plan_eerste_inlees_alles_nieuw():
    from services.referentiemodel_import_service import _bepaal_plan

    bron = _inhoud(
        [("a", "Alpha", None), ("b", "Beta", "def"), ("c", "Gamma", None)],
        plaatsingen={("a", "b"), ("a", "c")},
        overgeslagen={"BusinessProcess": 4},
    )
    plan = _bepaal_plan(bron, [], set(), set())
    assert plan.nieuw == ["Alpha", "Beta", "Gamma"]
    assert plan.bijgewerkt == [] and plan.vervallen == [] and plan.ongewijzigd == 0
    assert plan.plaatsingen_totaal == 2 and plan.plaatsingen_nieuw == 2
    assert plan.overgeslagen_totaal == 4


def test_plan_idempotent_geen_wijzigingen():
    from services.referentiemodel_import_service import _bepaal_plan

    bron = _inhoud([("a", "Alpha", None), ("b", "Beta", "def")], plaatsingen={("a", "b")})
    stand = _stand(("a", "Alpha", None, False), ("b", "Beta", "def", False))
    plan = _bepaal_plan(bron, stand, {("a", "b")}, set())
    assert plan.nieuw == [] and plan.bijgewerkt == [] and plan.vervallen == []
    assert plan.ongewijzigd == 2
    assert plan.plaatsingen_nieuw == 0 and plan.plaatsingen_vervallen == 0


def test_plan_herinlees_nieuw_bijgewerkt_vervallen_herleefd():
    from services.referentiemodel_import_service import _bepaal_plan

    bron = _inhoud([
        ("a", "Alpha hernoemd", None),   # naam gewijzigd → bijgewerkt
        ("b", "Beta", "nieuwe def"),     # definitie gewijzigd → bijgewerkt
        ("d", "Delta", None),            # nieuw
        ("h", "Herrezen", None),         # was vervallen → herleefd = bijgewerkt
    ])
    stand = _stand(
        ("a", "Alpha", None, False),
        ("b", "Beta", "def", False),
        ("c", "Gamma", None, False),     # niet meer in bron → vervallen
        ("h", "Herrezen", None, True),
        ("z", "Al weg", None, True),     # al vervallen + nog steeds weg → GEEN wijziging
    )
    plan = _bepaal_plan(bron, stand, set(), set())
    assert plan.nieuw == ["Delta"]
    assert plan.bijgewerkt == ["Alpha hernoemd", "Beta", "Herrezen"]
    assert plan.vervallen == [{"naam": "Gamma", "in_gebruik": False}]
    assert plan.ongewijzigd == 0


def test_plan_verhangen_raakt_het_kind():
    """Verhangen (plaatsing gewijzigd) telt als bijgewerkt op het KIND; het weghalen
    gebeurt alléén als beide endpoints nog in de bron staan."""
    from services.referentiemodel_import_service import _bepaal_plan

    bron = _inhoud(
        [("a", "Alpha", None), ("b", "Beta", None), ("k", "Kind", None)],
        plaatsingen={("b", "k")},        # kind verhuist van a naar b
    )
    plan = _bepaal_plan(bron, _stand(
        ("a", "Alpha", None, False), ("b", "Beta", None, False), ("k", "Kind", None, False),
    ), {("a", "k")}, set())
    assert plan.bijgewerkt == ["Kind"]
    assert plan.plaatsingen_nieuw == 1 and plan.plaatsingen_vervallen == 1
    assert plan.ongewijzigd == 2       # Alpha en Beta zelf ongewijzigd


def test_plan_plaatsing_van_vertrekkende_functie_bevroren():
    """Een functie die uit het model verdwijnt houdt haar historische plek: het
    (ouder, kind)-paar met een vertrekkend endpoint wordt NIET weggehaald."""
    from services.referentiemodel_import_service import _bepaal_plan

    bron = _inhoud([("a", "Alpha", None)])
    plan = _bepaal_plan(bron, _stand(
        ("a", "Alpha", None, False), ("weg", "Vertrekt", None, False),
    ), {("a", "weg")}, set())
    assert plan.vervallen == [{"naam": "Vertrekt", "in_gebruik": False}]
    assert plan.plaatsingen_vervallen == 0  # bevroren, geen verwijdering
    assert plan.bijgewerkt == []


def test_plan_vervallen_in_gebruik_vlag():
    """De in-gebruik-vlag komt uit de meegegeven set (gate 2 vult de echte telling;
    nu per definitie leeg — er wordt geen getal verzonnen)."""
    from services.referentiemodel_import_service import _bepaal_plan

    bron = _inhoud([])
    plan = _bepaal_plan(bron, _stand(
        ("x", "In gebruik", None, False), ("y", "Vrij", None, False),
    ), set(), {"x"})
    assert plan.vervallen == [
        {"naam": "In gebruik", "in_gebruik": True},
        {"naam": "Vrij", "in_gebruik": False},
    ]


# ── Offline: read-only-borging + engine-afwezigheid ─────────────────────────────

def _functie_bron_zonder_docstrings(fn) -> str:
    import ast
    import inspect
    import textwrap

    boom = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    for knoop in ast.walk(boom):
        if isinstance(knoop, (ast.AsyncFunctionDef, ast.FunctionDef)) and ast.get_docstring(knoop):
            knoop.body = knoop.body[1:] or [ast.Pass()]
    return ast.unparse(boom)


def test_dry_run_pad_is_read_only():
    """De dry-run schrijft NIETS: function-bronscan (ast-docstring-strip) op het hele
    droge pad — geen add/commit/flush/delete/voer_uit."""
    from services import referentiemodel_import_service as m

    for fn in (
        m.dry_run, m._bepaal_plan, m._bestaande_stand, m._aanbod_rij,
        m._in_gebruik_sleutels, m.overzicht,
    ):
        bron = _functie_bron_zonder_docstrings(fn)
        for verboden in (".add(", ".commit(", ".flush(", ".delete(", "voer_uit"):
            assert verboden not in bron, f"{fn.__name__} bevat schrijf-primitief {verboden!r}"


def test_import_raakt_engine_niet_offline():
    """ADR-043/044-invariant: score blijft de enige lifecycle-driver — parser noch
    import-service importeert een engine-symbool."""
    import services.ameff as ameff_mod
    import services.referentiemodel_import_service as import_mod

    for mod in (ameff_mod, import_mod):
        for naam in (
            "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
            "ComponentProfiel", "Blokkade", "Checklistscore",
        ):
            assert not hasattr(mod, naam), f"{mod.__name__} mag de engine niet importeren: {naam!r}"


def test_dry_run_en_voer_uit_delen_het_plan():
    """Geen tweede vergelijking die uit de pas kan lopen: beide paden roepen exact
    `_bepaal_plan` + `_lees_bron`/`bron`-injectie aan (bronscan)."""
    from services import referentiemodel_import_service as m

    for fn in (m.dry_run, m.voer_uit):
        bron = _functie_bron_zonder_docstrings(fn)
        assert "_bepaal_plan(" in bron
        assert "_lees_bron(" in bron


# ── Offline: platform-aanbod-beheer (gesloten aanbod) ────────────────────────────

def test_referentiemodelconfig_update_schema_gesloten_aanbod():
    """§2.1 — het aanbod is gesloten: het Update-schema kent alléén label/volgorde/
    actief; sleutel/herkomst/versie zijn gecureerde identiteit (extra='forbid' weert
    ze) en er bestaat geen Create-schema (nieuw aanbod = release-curatie)."""
    import pydantic

    import schemas.referentiemodelconfig as sch

    upd = sch.ReferentiemodelOptieUpdate(label="Nieuw label", actief=False)
    assert upd.model_dump(exclude_unset=True) == {"label": "Nieuw label", "actief": False}
    with pytest.raises(pydantic.ValidationError):
        sch.ReferentiemodelOptieUpdate(herkomst="x")
    with pytest.raises(pydantic.ValidationError):
        sch.ReferentiemodelOptieUpdate(optie_sleutel="x")
    assert not hasattr(sch, "ReferentiemodelOptieCreate")


# ── Offline: route-guards (inlezen = beheerder; lezen = iedereen) ────────────────

def _maak_route_test_app(monkeypatch):
    """De ÉCHTE router in een test-app: auth via gemonkeypatchte decode_token, sessie-
    dependency gestubd (de guard beslist vóór de service; de services zijn gemockt)."""
    from unittest.mock import AsyncMock

    from fastapi import FastAPI

    from app.middleware.auth import NietGeauthenticeerd, niet_geauthenticeerd_handler
    from app.middleware.authz import OnvoldoendeRechten, onvoldoende_rechten_handler
    from app.middleware.tenant import get_tenant_session
    from routes.referentiemodel import router
    from services import referentiemodel_import_service as svc

    plan = {
        "nieuw": ["Alpha"], "bijgewerkt": [], "vervallen": [], "ongewijzigd": 0,
        "plaatsingen_totaal": 0, "plaatsingen_nieuw": 0, "plaatsingen_vervallen": 0,
        "overgeslagen": {}, "overgeslagen_totaal": 0,
    }
    monkeypatch.setattr(svc, "overzicht", AsyncMock(return_value=[]))
    monkeypatch.setattr(svc, "dry_run", AsyncMock(return_value=dict(plan)))
    monkeypatch.setattr(svc, "voer_uit", AsyncMock(return_value={
        **plan, "model": {"model_sleutel": "x", "naam": "X", "versie": "1"},
    }))

    app = FastAPI()
    app.add_exception_handler(OnvoldoendeRechten, onvoldoende_rechten_handler)
    app.add_exception_handler(NietGeauthenticeerd, niet_geauthenticeerd_handler)
    app.include_router(router)
    app.dependency_overrides[get_tenant_session] = lambda: None
    return app


def _rol_payload(rollen):
    return {"sub": "u", "tenant_id": _TID, "realm_access": {"roles": rollen}}


def test_route_inlezen_is_beheerder_only(monkeypatch):
    """Besloten kader gate 1b: een medewerker mag niet inlezen (403, óók niet het
    voorbeeld — dat is stap één van dezelfde handeling); een beheerder wél; het
    overzicht mag élke rol lezen. Geen affordance-gat: de backend is de handhaver."""
    from fastapi.testclient import TestClient

    from app.core.config import settings

    app = _maak_route_test_app(monkeypatch)

    for rol in ("viewer", "medewerker", "auditor"):
        monkeypatch.setattr(
            "app.middleware.auth.decode_token", lambda t, _r=rol: _rol_payload([_r])
        )
        c = TestClient(app)
        c.cookies.set(settings.cookie_name, "tok")
        assert c.get("/referentiemodellen").status_code == 200
        for pad in ("voorbeeld", "inlezen"):
            r = c.post(f"/referentiemodellen/gemma_bedrijfsfuncties/{pad}")
            assert r.status_code == 403, (rol, pad)
            assert r.json()["fout"]["code"] == "ONVOLDOENDE_RECHTEN"

    monkeypatch.setattr("app.middleware.auth.decode_token", lambda t: _rol_payload(["beheerder"]))
    c = TestClient(app)
    c.cookies.set(settings.cookie_name, "tok")
    assert c.post("/referentiemodellen/gemma_bedrijfsfuncties/voorbeeld").status_code == 200
    assert c.post("/referentiemodellen/gemma_bedrijfsfuncties/inlezen").status_code == 200
    # Sleutel-vorm op de API-rand: ongeldige vorm ⇒ 422 native.
    assert c.post("/referentiemodellen/Foute%20Sleutel/voorbeeld").status_code == 422


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                res = (await c.execute(text(
                    "SELECT count(*) FROM referentiemodel_optie "
                    "WHERE optie_sleutel='gemma_bedrijfsfuncties' AND actief"
                ))).scalar()
            return res == 1
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


integratie = pytest.mark.skipif(
    not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar of aanbod niet geseed"
)


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


async def _ruim_model_op(s, model_sleutel):
    """Structurele teardown: álle functies van het model (element-supertype; de
    plaatsings-relaties cascaden mee) + de modelrij (ná de functies — bron-FK RESTRICT)."""
    from sqlalchemy import text as _text

    await s.execute(_text(
        "DELETE FROM element WHERE tenant_id=:t AND id IN "
        "(SELECT bf.id FROM bedrijfsfunctie bf JOIN referentiemodel rm "
        " ON rm.id = bf.bron_model_id WHERE rm.model_sleutel=:m AND bf.tenant_id=:t)"
    ), {"t": _TID, "m": model_sleutel})
    await s.execute(_text(
        "DELETE FROM referentiemodel WHERE tenant_id=:t AND model_sleutel=:m"
    ), {"t": _TID, "m": model_sleutel})
    await s.commit()


async def _tellingen(s):
    from sqlalchemy import text as _text

    bf = (await s.execute(_text(
        "SELECT count(*) FROM bedrijfsfunctie WHERE tenant_id=:t"), {"t": _TID})).scalar()
    profielen = (await s.execute(_text("SELECT count(*) FROM component_profiel"))).scalar()
    return bf, profielen


@integratie
def test_import_synthetisch_dry_run_uitvoering_herinlees_live():
    """De hele levensloop op een klein synthetisch model (bron-injectie): dry-run
    schrijft niets → uitvoering = het plan (incl. meervoudige plaatsing) → idempotente
    herinlees → herinlees v2 (hernoemd/verhangen/vervallen/nieuw) → eigen functie
    ongemoeid → engine onaangeroerd. Teardown in finally; residu 0."""
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate
    from services import bedrijfsfunctie_service as bf_svc
    from services import referentiemodel_import_service as m

    _SLEUTEL = "gemma_bedrijfsfuncties"  # bestaand aanbod; bron wordt geïnjecteerd

    bron_v1 = _inhoud(
        [("id-wt-a", "WT-IMP Alpha", "Def A"), ("id-wt-b", "WT-IMP Beta", None),
         ("id-wt-c", "WT-IMP Gamma", None)],
        plaatsingen={("id-wt-a", "id-wt-c"), ("id-wt-b", "id-wt-c")},  # meervoudig kind
        overgeslagen={"BusinessProcess": 2},
    )
    bron_v2 = _inhoud(
        [("id-wt-a", "WT-IMP Alpha hernoemd", "Def A"), ("id-wt-b", "WT-IMP Beta", None),
         ("id-wt-d", "WT-IMP Delta", None)],                      # c weg, d nieuw
        plaatsingen={("id-wt-b", "id-wt-d")},
    )

    async def _flow(s):
        eigen_id = None
        try:
            bf_voor, prof_voor = await _tellingen(s)

            # Overzicht vóór het inlezen: aanbod zichtbaar, nog niets ingelezen.
            voor = await m.overzicht(s, _TID)
            gemma_voor = next(o for o in voor if o["model_sleutel"] == _SLEUTEL)
            assert gemma_voor["beschikbaar"] is True
            assert gemma_voor["ingelezen"] is None and gemma_voor["aantal_functies"] == 0

            # Dry-run schrijft niets.
            plan = await m.dry_run(s, _TID, _SLEUTEL, bron=bron_v1)
            assert plan["nieuw"] == ["WT-IMP Alpha", "WT-IMP Beta", "WT-IMP Gamma"]
            assert plan["plaatsingen_nieuw"] == 2
            assert plan["overgeslagen"] == {"BusinessProcess": 2}
            assert (await _tellingen(s)) == (bf_voor, prof_voor)

            # Eigen functie vóór de import — een herinlees raakt haar nooit aan.
            eigen = await bf_svc.maak_aan(s, _TID, BedrijfsfunctieCreate(
                naam="WT-IMP Eigen functie"))
            eigen_id = eigen["id"]

            # Uitvoering = het plan.
            resultaat = await m.voer_uit(s, _TID, _SLEUTEL, bron=bron_v1)
            assert resultaat["nieuw"] == plan["nieuw"]
            detail_c = await bf_svc.lees_detail(
                s, _TID, await _id_op_sleutel(s, "id-wt-c"))
            assert len(detail_c["ouder_ids"]) == 2  # het meervoud-geval komt door

            # Overzicht ná het inlezen: snapshot + tellingen zichtbaar.
            na = await m.overzicht(s, _TID)
            gemma_na = next(o for o in na if o["model_sleutel"] == _SLEUTEL)
            assert gemma_na["ingelezen"] is not None
            assert gemma_na["aantal_functies"] == 3 and gemma_na["aantal_vervallen"] == 0

            # Idempotente herinlees: 0 wijzigingen.
            plan2 = await m.dry_run(s, _TID, _SLEUTEL, bron=bron_v1)
            assert (plan2["nieuw"], plan2["bijgewerkt"], plan2["vervallen"]) == ([], [], [])
            assert plan2["ongewijzigd"] == 3
            resultaat2 = await m.voer_uit(s, _TID, _SLEUTEL, bron=bron_v1)
            assert (resultaat2["nieuw"], resultaat2["bijgewerkt"], resultaat2["vervallen"]) == ([], [], [])

            # Herinlees v2: hernoemd + nieuw + vervallen (mét naam) + verhangen.
            plan3 = await m.dry_run(s, _TID, _SLEUTEL, bron=bron_v2)
            assert plan3["nieuw"] == ["WT-IMP Delta"]
            assert plan3["bijgewerkt"] == ["WT-IMP Alpha hernoemd"]
            assert plan3["vervallen"] == [{"naam": "WT-IMP Gamma", "in_gebruik": False}]
            resultaat3 = await m.voer_uit(s, _TID, _SLEUTEL, bron=bron_v2)
            assert resultaat3["vervallen"] == plan3["vervallen"]

            # Vervallen = vlag; de rij bestaat nog en houdt haar (bevroren) plaatsingen.
            gamma = await bf_svc.lees_detail(s, _TID, await _id_op_sleutel(s, "id-wt-c"))
            assert gamma["vervallen"] is True
            assert len(gamma["ouder_ids"]) == 2  # historische plekken bevroren
            # Hernoemd op de BRONSLEUTEL (niet op naam).
            alpha = await bf_svc.lees_detail(s, _TID, await _id_op_sleutel(s, "id-wt-a"))
            assert alpha["naam"] == "WT-IMP Alpha hernoemd"

            # Eigen functie ongemoeid.
            eigen_na = await bf_svc.lees_detail(s, _TID, eigen_id)
            assert eigen_na["naam"] == "WT-IMP Eigen functie"
            assert eigen_na["vervallen"] is False

            # Engine onaangeroerd: geen component_profiel ontstaan of verdwenen.
            assert (await _tellingen(s))[1] == prof_voor
        finally:
            if eigen_id is not None:
                from sqlalchemy import text as _text
                await s.execute(_text("DELETE FROM element WHERE tenant_id=:t AND id=:i"),
                                {"t": _TID, "i": str(eigen_id)})
                await s.commit()
            await _ruim_model_op(s, _SLEUTEL)
            # Residu-check: 0 WT-IMP-functies over.
            from sqlalchemy import text as _text
            rest = (await s.execute(_text(
                "SELECT count(*) FROM bedrijfsfunctie WHERE tenant_id=:t AND naam LIKE 'WT-IMP%'"
            ), {"t": _TID})).scalar()
            assert rest == 0

    async def _id_op_sleutel(s, sleutel):
        from sqlalchemy import text as _text

        return (await s.execute(_text(
            "SELECT id FROM bedrijfsfunctie WHERE tenant_id=:t AND bron_sleutel=:k"
        ), {"t": _TID, "k": sleutel})).scalar_one()

    asyncio.run(_run_rls(_TID, "wt-gate1b", _flow))


@integratie
def test_import_echte_bestand_live_297_functies():
    """De echte GEMMA-import door het echte pad (parser → plan → schrijven): 297 nieuw ·
    302 plaatsingen · 2455 overgeslagen; tweede dry-run = 0 wijzigingen. Meet de duur
    (import-prestatie, gate-rapport). Teardown in finally; residu 0."""
    from services import referentiemodel_import_service as m

    _SLEUTEL = "gemma_bedrijfsfuncties"

    async def _flow(s):
        try:
            plan = await m.dry_run(s, _TID, _SLEUTEL)
            assert len(plan["nieuw"]) == 297
            assert plan["plaatsingen_totaal"] == 302
            assert plan["overgeslagen_totaal"] == 2455

            start = time.monotonic()
            resultaat = await m.voer_uit(s, _TID, _SLEUTEL)
            duur = time.monotonic() - start
            print(f"\n[meting] echte GEMMA-import: {duur:.1f}s "
                  f"(297 functies + 302 plaatsingen)")
            assert len(resultaat["nieuw"]) == 297
            assert resultaat["plaatsingen_nieuw"] == 302

            plan2 = await m.dry_run(s, _TID, _SLEUTEL)
            assert (plan2["nieuw"], plan2["bijgewerkt"], plan2["vervallen"]) == ([], [], [])
            assert plan2["ongewijzigd"] == 297
        finally:
            await _ruim_model_op(s, _SLEUTEL)
            from sqlalchemy import text as _text
            rest = (await s.execute(_text(
                "SELECT count(*) FROM bedrijfsfunctie bf WHERE bf.tenant_id=:t "
                "AND bf.bron_model_id IS NOT NULL"
            ), {"t": _TID})).scalar()
            assert rest == 0

    asyncio.run(_run_rls(_TID, "wt-gate1b", _flow))


@integratie
def test_onbekend_model_geweigerd_live():
    from services import referentiemodel_import_service as m
    from services.errors import OngeldigeRegistratie

    async def _flow(s):
        with pytest.raises(OngeldigeRegistratie) as fout:
            await m.dry_run(s, _TID, "bestaat_niet")
        assert fout.value.code == "ONBEKEND_MODEL"

    asyncio.run(_run_rls(_TID, "wt-gate1b", _flow))


# ── Gate 1b-afronding — onvoltooide inlees: nooit stil ───────────────────────────

def test_referentiemodel_heeft_inlees_markering():
    """De inlees heeft een begin en een eind: `inlees_voltooid` is een echte kolom
    (audit-naspeurbaar, DC016-precedent), NOT NULL met server_default true (bestaande
    rijen zijn per definitie niet-halverwege). Migratie 0064."""
    from models.models import Referentiemodel

    kol = Referentiemodel.__table__.columns["inlees_voltooid"]
    assert kol.nullable is False
    assert kol.server_default is not None
    assert "true" in str(kol.server_default.arg).lower()


@integratie
def test_afgebroken_inlees_herkend_en_hervat_live(monkeypatch):
    """Gedragstest + kritisch randgeval: een import die crasht VÓÓR de vervallen-
    markering laat `inlees_voltooid=False` achter (het scherm meldt 'niet afgerond')
    terwijl de vertrekkende functie nog als geldig in de data staat — precies de
    stille onwaarheid die de vlag zichtbaar maakt. Een hervatte inlees maakt hem
    idempotent af (vervallen alsnog gezet, vlag True, signaal weg); een voltooide
    inlees geeft geen vals signaal."""
    from services import bedrijfsfunctie_service as bf_svc
    from services import referentiemodel_import_service as m

    _SLEUTEL = "gemma_bedrijfsfuncties"

    bron_v1 = _inhoud(
        [("id-wt-a", "WT-IMP Alpha", None), ("id-wt-b", "WT-IMP Beta", None),
         ("id-wt-c", "WT-IMP Gamma", None)],
        plaatsingen={("id-wt-a", "id-wt-b")},
    )
    # v2: Gamma verdwijnt (→ vervallen verwacht), Delta nieuw mét plaatsing — de
    # plaatsings-stap (stap 2) ligt vóór de vervallen-markering (stap 3).
    bron_v2 = _inhoud(
        [("id-wt-a", "WT-IMP Alpha", None), ("id-wt-b", "WT-IMP Beta", None),
         ("id-wt-d", "WT-IMP Delta", None)],
        plaatsingen={("id-wt-a", "id-wt-b"), ("id-wt-b", "id-wt-d")},
    )

    echte_plaats = bf_svc.plaats

    async def _crasht(*a, **kw):
        raise RuntimeError("WT: gesimuleerde afbraak midden in de import")

    async def _flow(s):
        try:
            # Voltooide inlees → vlag True, geen vals signaal.
            await m.voer_uit(s, _TID, _SLEUTEL, bron=bron_v1)
            gemma = next(o for o in await m.overzicht(s, _TID) if o["model_sleutel"] == _SLEUTEL)
            assert gemma["ingelezen"].inlees_voltooid is True

            # Afgebroken herinlees: crash in de plaatsings-stap (vóór vervallen).
            monkeypatch.setattr(bf_svc, "plaats", _crasht)
            with pytest.raises(RuntimeError, match="gesimuleerde afbraak"):
                await m.voer_uit(s, _TID, _SLEUTEL, bron=bron_v2)
            monkeypatch.setattr(bf_svc, "plaats", echte_plaats)

            gemma = next(o for o in await m.overzicht(s, _TID) if o["model_sleutel"] == _SLEUTEL)
            assert gemma["ingelezen"].inlees_voltooid is False  # herkend: niet afgerond
            # HET randgeval: Gamma is uit het model maar nog NIET vervallen gemarkeerd —
            # zonder de vlag zou de kaart haar als geldig tonen.
            from sqlalchemy import text as _text
            gamma_vervallen = (await s.execute(_text(
                "SELECT vervallen FROM bedrijfsfunctie WHERE tenant_id=:t AND bron_sleutel='id-wt-c'"
            ), {"t": _TID})).scalar_one()
            assert gamma_vervallen is False

            # Hervatten (bewuste handeling; zelfde pad) → idempotent afgemaakt.
            await m.voer_uit(s, _TID, _SLEUTEL, bron=bron_v2)
            gemma = next(o for o in await m.overzicht(s, _TID) if o["model_sleutel"] == _SLEUTEL)
            assert gemma["ingelezen"].inlees_voltooid is True   # signaal weg
            gamma_vervallen = (await s.execute(_text(
                "SELECT vervallen FROM bedrijfsfunctie WHERE tenant_id=:t AND bron_sleutel='id-wt-c'"
            ), {"t": _TID})).scalar_one()
            assert gamma_vervallen is True                       # vervallen alsnog gezet
            plan = await m.dry_run(s, _TID, _SLEUTEL, bron=bron_v2)
            assert (plan["nieuw"], plan["bijgewerkt"], plan["vervallen"]) == ([], [], [])
        finally:
            monkeypatch.setattr(bf_svc, "plaats", echte_plaats)
            await _ruim_model_op(s, _SLEUTEL)

    asyncio.run(_run_rls(_TID, "wt-gate1b", _flow))
