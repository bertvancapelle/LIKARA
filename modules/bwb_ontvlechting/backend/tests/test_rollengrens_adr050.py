"""Tests — ADR-050: de rollengrens knipt op het ONDERWERP (registratie-feit vs landschapsobject).

Offline (de regel wordt structureel geërfd, en bijt):
- de classificatie is disjunct en `verwijder_actie` volgt haar;
- GEEN registratie-feit-DELETE staat op VERWIJDEREN (de kern);
- elke primaire content-DELETE strookt met `verwijder_actie(entiteit)` — een niet-geclassificeerde
  entiteit of een feit-op-VERWIJDEREN faalt hier (zo kan een nieuw feit de regel niet vergeten);
- lidmaatschap-sub-resources (leden/plaatsingen/band-dekking) zijn membership-uitspraken → WIJZIGEN;
- medewerker neemt een feit terug (viewer niet); de medewerker vernietigt géén landschapsobject.

Live (skip-if-no-DB): de grond beschermt zichzelf — een GEMMA-plaatsing (aggregation, kind =
modelinhoud) is via het generieke relatie-pad NIET wisbaar/wijzigbaar, door NIEMAND (ADR-050
besluit 4); het import-pad (`via_import`) kan het wél.
"""
import asyncio
import pathlib
import re
import uuid

import pytest

import app.core.database  # noqa: F401
from app.core.rbac import (
    Actie,
    Entiteit,
    LANDSCHAPSOBJECT_ENTITEITEN,
    REGISTRATIE_FEIT_ENTITEITEN,
    heeft_permissie,
    verwijder_actie,
)
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_ROUTES = pathlib.Path(__file__).resolve().parents[1] / "routes"

# Feit-op-een-host: de DELETE guardt bewust op de WIJZIGEN van een HOST-object-entiteit i.p.v.
# een eigen entiteit (de koppelregel heeft geen eigen entiteit; roltoewijzing lift op PARTIJ).
_FEIT_OP_HOST = {("roltoewijzing.py", Entiteit.PARTIJ)}
# Eigen-beheer-records: buiten de object/feit-grens (je eigen view/voorkeur weggooien mag elke rol).
_EIGEN_SCOPE = {Entiteit.IMPACT_VIEW, Entiteit.GEBRUIKER_VOORKEUR}


def _delete_routes():
    """(bestand, pad, entiteit, actie, is_subresource) voor elke @router.delete in de routes."""
    uit = []
    for f in sorted(_ROUTES.glob("*.py")):
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, regel in enumerate(lines):
            m = re.search(r'@router\.delete\("([^"]*)"', regel)
            if not m:
                continue
            pad = m.group(1)
            blok = "\n".join(lines[i:i + 18])
            g = re.search(
                r"vereist_permissie\(\s*Entiteit\.([A-Z_]+)\s*,\s*"
                r"(?:Actie\.([A-Z]+)|verwijder_actie\(Entiteit\.([A-Z_]+)\))",
                blok,
            )
            if not g:
                continue
            ent = Entiteit[g.group(1)]
            actie = Actie[g.group(2)] if g.group(2) else verwijder_actie(Entiteit[g.group(3)])
            is_sub = pad.count("/") > 1  # "/{id}" = 1 slash; "/{id}/leden/{x}" = meer
            uit.append((f.name, pad, ent, actie, is_sub))
    return uit


def test_classificatie_disjunct_en_verwijder_actie():
    assert REGISTRATIE_FEIT_ENTITEITEN.isdisjoint(LANDSCHAPSOBJECT_ENTITEITEN)
    for e in REGISTRATIE_FEIT_ENTITEITEN:
        assert verwijder_actie(e) == Actie.WIJZIGEN
    for e in LANDSCHAPSOBJECT_ENTITEITEN:
        assert verwijder_actie(e) == Actie.VERWIJDEREN


def test_geen_registratie_feit_op_verwijderen():
    """De kern van ADR-050: geen enkel registratie-feit wordt met VERWIJDEREN (beheerder-only) gegate."""
    for fn, pad, ent, actie, _sub in _delete_routes():
        if ent in REGISTRATIE_FEIT_ENTITEITEN:
            assert actie == Actie.WIJZIGEN, f"{fn}{pad}: registratie-feit {ent.value} mag niet op VERWIJDEREN"


def test_primaire_delete_erft_categorie_en_bijt():
    """Elke PRIMAIRE content-DELETE strookt met `verwijder_actie(entiteit)`. Een nieuw feit dat op
    VERWIJDEREN gaat, of een entiteit die niemand classificeerde, faalt hier — zo kan de regel niet
    (opnieuw) vergeten worden. Bijt-borging in de geest van test_filterbalk_li040."""
    gezien = 0
    for fn, pad, ent, actie, is_sub in _delete_routes():
        if is_sub:
            continue
        if (fn, ent) in _FEIT_OP_HOST:
            assert actie == Actie.WIJZIGEN
            continue
        if ent in _EIGEN_SCOPE:
            continue
        assert ent in (REGISTRATIE_FEIT_ENTITEITEN | LANDSCHAPSOBJECT_ENTITEITEN), (
            f"{fn}{pad}: entiteit {ent.value} is niet geclassificeerd (ADR-050 — voeg toe aan "
            f"REGISTRATIE_FEIT_ENTITEITEN of LANDSCHAPSOBJECT_ENTITEITEN)"
        )
        assert actie == verwijder_actie(ent), (
            f"{fn}{pad}: de DELETE van {ent.value} strookt niet met haar categorie "
            f"(verwacht {verwijder_actie(ent).value})"
        )
        gezien += 1
    assert gezien >= 8  # de sweep raakt aantoonbaar meerdere content-entiteiten


def test_lidmaatschap_deletes_zijn_wijzigen():
    """Sub-resource lidmaatschap-deletes (leden/plaatsingen/band-dekking/werkpakketten) zijn
    membership-uitspraken → WIJZIGEN (medewerker), nooit VERWIJDEREN."""
    subs = [(fn, pad, actie) for fn, pad, _e, actie, is_sub in _delete_routes() if is_sub]
    assert len(subs) >= 5
    for fn, pad, actie in subs:
        assert actie == Actie.WIJZIGEN, f"{fn}{pad}: lidmaatschap-delete moet op WIJZIGEN staan"


def test_medewerker_neemt_feit_terug_viewer_niet():
    for e in REGISTRATIE_FEIT_ENTITEITEN:
        a = verwijder_actie(e)
        assert heeft_permissie(["medewerker"], e, a), e
        assert not heeft_permissie(["viewer"], e, a), e


def test_landschapsobject_blijft_beheerder():
    """De grens houdt: een medewerker vernietigt geen landschapsobject."""
    for e in LANDSCHAPSOBJECT_ENTITEITEN:
        a = verwijder_actie(e)  # VERWIJDEREN
        assert heeft_permissie(["beheerder"], e, a), e
        assert not heeft_permissie(["medewerker"], e, a), e


# ── Live: de grond beschermt zichzelf ────────────────────────────────────────────

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


async def _maak_modelfunctie(s, naam, sleutel, model_id):
    # Modelinhoud vereist het paar (bron_model_id, bron_sleutel) — CHECK ck_bedrijfsfunctie_bron_paar.
    from models.models import Bedrijfsfunctie, Element, ElementType

    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.bedrijfsfunctie)
    s.add(elem)
    await s.flush()
    s.add(Bedrijfsfunctie(id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam,
                          bron_model_id=model_id, bron_sleutel=sleutel))
    await s.commit()
    return elem.id


@integratie
def test_grond_niet_wisbaar_via_generieke_relatie_live():
    from schemas.relatie import RelatieUpdate
    from services import bedrijfsfunctie_service as bf
    from services import relatie_service
    from services.errors import OngeldigeRegistratie

    async def _flow(s):
        from models.models import Relatie
        from sqlalchemy import select, text as _text
        from models.models import Referentiemodel
        ids = []
        try:
            model_id = (await s.execute(
                select(Referentiemodel.id).where(Referentiemodel.tenant_id == uuid.UUID(_TID)).limit(1)
            )).scalar_one_or_none()
            if model_id is None:
                pytest.skip("geen referentiemodel in de dev-DB om modelinhoud aan te haken")
            ouder = await _maak_modelfunctie(s, "RG-Grond Ouder", "rg_ouder", model_id)
            kind = await _maak_modelfunctie(s, "RG-Grond Kind", "rg_kind", model_id)
            ids += [ouder, kind]
            # De GEMMA-plaatsing: aggregation, kind = modelinhoud (bronsleutel).
            await bf.plaats(s, _TID, kind, ouder, via_import=True)
            plaatsing = (await s.execute(
                select(Relatie).where(Relatie.tenant_id == uuid.UUID(_TID),
                                      Relatie.bron_id == ouder, Relatie.doel_id == kind,
                                      Relatie.relatietype == "aggregation")
            )).scalar_one()
            fouten = {}
            # Generiek verwijderen: geweigerd (door NIEMAND — de rol doet er niet toe).
            try:
                await relatie_service.verwijder(s, _TID, plaatsing.id)
            except OngeldigeRegistratie as e:
                fouten["verwijder"] = e.code
            # Generiek wijzigen: idem geweigerd.
            try:
                await relatie_service.werk_bij(s, _TID, plaatsing.id, RelatieUpdate(omschrijving="x"))
            except OngeldigeRegistratie as e:
                fouten["werk_bij"] = e.code
            # Nog aanwezig?
            rest = (await s.execute(_text(
                "SELECT count(*) FROM relatie WHERE id=:i"), {"i": str(plaatsing.id)})).scalar()
            # Het IMPORT-pad kan de plaatsing wél opruimen (via_import).
            await bf.verwijder_plaatsing(s, _TID, kind, ouder, via_import=True)
            na_import = (await s.execute(_text(
                "SELECT count(*) FROM relatie WHERE id=:i"), {"i": str(plaatsing.id)})).scalar()
            return fouten, rest, na_import
        finally:
            from sqlalchemy import text as _text
            for eid in reversed(ids):
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    fouten, rest, na_import = asyncio.run(_run_rls(_flow))
    assert fouten == {"verwijder": "MODELINHOUD_BESCHERMD", "werk_bij": "MODELINHOUD_BESCHERMD"}
    assert rest == 1  # generiek pad heeft niets gewist
    assert na_import == 0  # het import-pad wél
