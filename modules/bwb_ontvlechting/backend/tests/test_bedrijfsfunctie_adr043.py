"""Tests — ADR-043 gate 1a + ADR-044 gate 1a-bis: Bedrijfsfunctie + plaatsingen.

Offline: model (element-subtype; ADR-044: GÉÉN ouder-kolom/self-FK meer — de boom leeft
in aggregation-plaatsingen), referentiemodel (tenant + platform-aanbod), schema's
(Update zonder plaatsing-velden), ArchiMate-typing (business_function; DERDE gemarkeerde
behavior-afwijking), sorteer-allowlist-sync, RBAC (tenant + platform), audit-allowlists
(plaatsingen liften mee op het relatie-spoor) + engine-borging.
Live (skip-if-no-DB): CRUD + subboom over plaatsingen, MEERVOUDIGE ouders (het
"Toezicht"-geval), endpoint-typeborging (422), modelinhoud-bescherming (422),
vervallen-guard (422), dubbele plaatsing (409), cyclus over de meervoudige-ouders-graaf
(422), verwijdergedrag (409), RLS-isolatie, audit + geen-engine-mutatie. Live-tests
ruimen hun element-rijen structureel op (element-supertype, leaf→root, in finally);
plaatsings-relaties cascaden mee met hun endpoints.
"""
import asyncio
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


# ── Offline: model + schema ──────────────────────────────────────────────────────

def test_bedrijfsfunctie_is_element_subtype_zonder_ouderkolom():
    """ADR-044: de boom is geen kolom — geen ouder_id, geen self-FK, geen
    self-parent-CHECK; wél de shared-PK-cascade en de herkomst-FK (RESTRICT)."""
    from models.models import Bedrijfsfunctie

    assert Bedrijfsfunctie.__tablename__ == "bedrijfsfunctie"
    kols = Bedrijfsfunctie.__table__.columns
    assert "ouder_id" not in kols  # ADR-044 — plaatsing is een relatie, geen veld
    for k in ("naam", "definitie", "bron_model_id", "bron_sleutel", "vervallen"):
        assert k in kols
    fks = {
        con.name: con
        for con in Bedrijfsfunctie.__table__.constraints
        if con.__class__.__name__ == "ForeignKeyConstraint"
    }
    assert fks["fk_bedrijfsfunctie_element"].ondelete == "CASCADE"
    assert fks["fk_bedrijfsfunctie_bron_model"].ondelete == "RESTRICT"
    assert "fk_bedrijfsfunctie_ouder" not in fks
    checks = [
        con.name for con in Bedrijfsfunctie.__table__.constraints
        if con.__class__.__name__ == "CheckConstraint"
    ]
    assert "ck_bedrijfsfunctie_bron_paar" in checks
    assert "ck_bedrijfsfunctie_geen_self_parent" not in checks


def test_bedrijfsfunctie_bron_uniciteit():
    from models.models import Bedrijfsfunctie

    uniques = [
        sorted(c.name for c in con.columns)
        for con in Bedrijfsfunctie.__table__.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    ]
    assert ["bron_model_id", "bron_sleutel", "tenant_id"] in uniques
    assert ["id", "tenant_id"] in uniques


def test_referentiemodel_twee_lagen():
    """Besluit LI039-5: aanbod = platform (`referentiemodel_optie`, geen tenant_id),
    ingelezen inhoud = tenant (`referentiemodel`, herinlees = bijwerken)."""
    from models.models import Referentiemodel, ReferentiemodelOptie

    assert "tenant_id" not in ReferentiemodelOptie.__table__.columns
    for k in ("optie_sleutel", "label", "herkomst", "versie", "actief"):
        assert k in ReferentiemodelOptie.__table__.columns

    assert "tenant_id" in Referentiemodel.__table__.columns
    uniques = [
        sorted(c.name for c in con.columns)
        for con in Referentiemodel.__table__.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    ]
    assert ["id", "tenant_id"] in uniques
    assert ["model_sleutel", "tenant_id"] in uniques


def test_bedrijfsfunctie_schema_validatie():
    from pydantic import ValidationError
    from schemas.bedrijfsfunctie import (
        BedrijfsfunctieCreate,
        BedrijfsfunctieUpdate,
        PlaatsingCreate,
    )

    ok = BedrijfsfunctieCreate(naam="Toezicht")
    assert ok.ouder_id is None
    BedrijfsfunctieCreate(naam="Handhaving", ouder_id=uuid.uuid4())  # gemak: mét 1e plaatsing
    with pytest.raises(ValidationError):  # naam verplicht
        BedrijfsfunctieCreate(naam="  ")
    with pytest.raises(ValidationError):  # extra veld verboden
        BedrijfsfunctieCreate(naam="X", onbekend="y")
    with pytest.raises(ValidationError):  # herkomst NOOIT via het gebruikers-pad
        BedrijfsfunctieCreate(naam="X", bron_sleutel="s")
    # ADR-044: Update kent GEEN plaatsing-velden — plaatsingen via de eigen endpoints.
    with pytest.raises(ValidationError):
        BedrijfsfunctieUpdate(ouder_id=uuid.uuid4())
    PlaatsingCreate(ouder_id=uuid.uuid4())
    with pytest.raises(ValidationError):
        PlaatsingCreate()


# ── Offline: ArchiMate-typing (ADR-043) ──────────────────────────────────────────

def test_bedrijfsfunctie_typing_business_function_behavior():
    """Bedrijfsfunctie = business_function / business / behavior — de DERDE gemarkeerde
    behavior-afwijking op OK-3 (naast work_package en proces)."""
    from models.models import ElementType
    from services.archimate_typing import TOEGESTANE_ELEMENTEN, typing_voor

    assert "business_function" in TOEGESTANE_ELEMENTEN
    assert typing_voor(ElementType.bedrijfsfunctie) == {
        "archimate_element": "business_function", "laag": "business", "aspect": "behavior",
    }


def test_bedrijfsfunctie_sorteer_allowlist_synchroon():
    """ADR-017 — schema-enum ⟺ service-allowlist ⟺ parsers blijven 1-op-1."""
    from schemas.bedrijfsfunctie import BedrijfsfunctieSorteerveld
    from services import bedrijfsfunctie_service as svc

    assert {e.value for e in BedrijfsfunctieSorteerveld} == set(svc._SORTEERBARE_KOLOMMEN)
    assert set(svc._SORTEERBARE_KOLOMMEN) == set(svc._WAARDE_PARSERS)


# ── Offline: RBAC + audit + regressie ────────────────────────────────────────────

def test_bedrijfsfunctie_in_audit_allowlists():
    """ADR-044 1.2 — geverifieerd: plaatsingen zijn `relatie`-rijen en liften mee op het
    bestaande relatie-audit-spoor; de functie zelf + het referentiemodel zijn eigen
    allowlist-entries."""
    from app.core.audit import AUDIT_PLATFORM_ENTITEITEN, AUDIT_TENANT_ENTITEITEN

    assert "bedrijfsfunctie" in AUDIT_TENANT_ENTITEITEN
    assert "referentiemodel" in AUDIT_TENANT_ENTITEITEN
    assert "relatie" in AUDIT_TENANT_ENTITEITEN  # ← draagt de plaatsingen
    assert "referentiemodel_optie" in AUDIT_PLATFORM_ENTITEITEN


def test_bedrijfsfunctie_in_rbac_inhoud_patroon():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    assert heeft_permissie(["medewerker"], Entiteit.BEDRIJFSFUNCTIE, Actie.AANMAKEN)
    assert heeft_permissie(["beheerder"], Entiteit.BEDRIJFSFUNCTIE, Actie.VERWIJDEREN)
    assert not heeft_permissie(["viewer"], Entiteit.BEDRIJFSFUNCTIE, Actie.AANMAKEN)
    assert heeft_permissie(["auditor"], Entiteit.BEDRIJFSFUNCTIE, Actie.LEZEN)


def test_referentiemodel_inlezen_is_beheerder():
    """Gate 1b (besloten kader): inlezen = beheerder — het inhoud-patroon is
    gecorrigeerd (een medewerker mocht aanmaken; te ruim voor een import die het
    functie-landschap herschrijft). Lezen mag iedereen (precedent GEBRUIKERSBEHEER
    voor de mutatie-kant)."""
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    for rol in ("viewer", "medewerker", "beheerder", "auditor"):
        assert heeft_permissie([rol], Entiteit.REFERENTIEMODEL, Actie.LEZEN)
    for actie in (Actie.AANMAKEN, Actie.WIJZIGEN, Actie.VERWIJDEREN):
        assert heeft_permissie(["beheerder"], Entiteit.REFERENTIEMODEL, actie)
        for rol in ("viewer", "medewerker", "auditor"):
            assert not heeft_permissie([rol], Entiteit.REFERENTIEMODEL, actie)


def test_referentiemodelconfig_platform_law_zonder_v():
    from app.core.platform_rbac import PlatformEntiteit, heeft_platform_permissie
    from app.core.rbac import Actie

    assert heeft_platform_permissie(
        ["platformbeheerder"], PlatformEntiteit.REFERENTIEMODELCONFIG, Actie.WIJZIGEN
    )
    assert not heeft_platform_permissie(
        ["platformbeheerder"], PlatformEntiteit.REFERENTIEMODELCONFIG, Actie.VERWIJDEREN
    )
    assert heeft_platform_permissie(
        ["platformoperator"], PlatformEntiteit.REFERENTIEMODELCONFIG, Actie.LEZEN
    )
    assert not heeft_platform_permissie(
        ["platformoperator"], PlatformEntiteit.REFERENTIEMODELCONFIG, Actie.WIJZIGEN
    )


def test_bedrijfsfunctie_service_raakt_engine_niet():
    """ADR-043/044-invariant: score blijft de enige lifecycle-driver — de functie-service
    importeert géén engine-onderdeel (Relatie is registratie, geen engine)."""
    import services.bedrijfsfunctie_service as bs

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(bs, naam), f"bedrijfsfunctie_service mag de engine niet importeren: {naam!r}"


def test_seed_referentiemodel_bekrachtigde_herkomst():
    """LI039 — het aanbod draagt de navolgbare, bekrachtigde herkomst (bron-repository +
    licentie + release-versie), niet meer het verzonnen 'GEMMA 2 (2025)'."""
    from services.seed_referentiemodel import bouw_referentiemodel

    rijen = bouw_referentiemodel()
    gemma = next(r for r in rijen if r["optie_sleutel"] == "gemma_bedrijfsfuncties")
    assert gemma["versie"] == "release 1 juli 2026"
    assert "GEMMA-Archi-repository" in gemma["herkomst"]
    assert "EUPL" in gemma["herkomst"]


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                # ADR-044 toegepast? De ouder-kolom moet wég zijn (migratie 0063).
                res = (await c.execute(text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_name='bedrijfsfunctie' AND column_name='ouder_id'"
                ))).scalar()
            return res == 0
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


integratie = pytest.mark.skipif(
    not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar of migratie 0063 niet toegepast"
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


async def _ruim(s, ids, model_ids=()):
    """Element-rijen opruimen via het supertype (plaatsings-relaties cascaden mee met
    hun endpoints); daarna de referentiemodel-rij(en) — ná de functies i.v.m. de
    bron-FK RESTRICT."""
    from sqlalchemy import text as _text

    for eid in reversed(ids):
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    for mid in model_ids:
        await s.execute(_text("DELETE FROM referentiemodel WHERE id=:i"), {"i": str(mid)})
    await s.commit()


async def _maak_model(s, sleutel="wt_bf_model"):
    from models.models import Referentiemodel

    rij = Referentiemodel(
        tenant_id=uuid.UUID(_TID), model_sleutel=sleutel,
        naam="WT-BF Testmodel", versie="t1",
    )
    s.add(rij)
    await s.commit()
    await s.refresh(rij)
    return rij.id


async def _maak_modelfunctie(s, svc, naam, sleutel, model_id):
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate

    return await svc.maak_aan(
        s, _TID, BedrijfsfunctieCreate(naam=naam),
        bron_model_id=model_id, bron_sleutel=sleutel,
    )


@integratie
def test_bedrijfsfunctie_meervoudige_ouders_en_subboom_live():
    """ADR-044-kern: één functie op TWEE plekken (het Toezicht-geval) — één identiteit,
    twee plaatsingen; de read levert beide ouders; de subboom bereikt haar éénmaal."""
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate
    from services import bedrijfsfunctie_service as svc

    async def _flow(s):
        ids = []
        try:
            wortel = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-P Uitvoering"))
            ids.append(wortel["id"])
            d1 = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-P Domein A", ouder_id=wortel["id"]))
            ids.append(d1["id"])
            d2 = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-P Domein B", ouder_id=wortel["id"]))
            ids.append(d2["id"])
            toezicht = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-P Toezicht", ouder_id=d1["id"]))
            ids.append(toezicht["id"])
            # De tweede plaatsing: zelfde functie, tweede ouder.
            na = await svc.plaats(s, _TID, toezicht["id"], d2["id"])
            subboom = await svc.subboom(s, _TID, wortel["id"])
            detail = await svc.lees_detail(s, _TID, toezicht["id"])
            return d1, d2, toezicht, na, subboom, detail
        finally:
            await _ruim(s, ids)

    d1, d2, toezicht, na, subboom, detail = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert sorted(map(str, na["ouder_ids"])) == sorted([str(d1["id"]), str(d2["id"])])
    assert sorted(map(str, detail["ouder_ids"])) == sorted([str(d1["id"]), str(d2["id"])])
    # Subboom: Toezicht komt éénmaal voor (één identiteit), op zijn kortste afstand.
    per_id = [x for x in subboom if str(x["id"]) == str(toezicht["id"])]
    assert len(per_id) == 1 and per_id[0]["niveau"] == 2


@integratie
def test_plaatsing_typeborging_en_regels_live():
    """Endpoint-typeborging (422 op een niet-functie), modelinhoud-slot (422),
    vervallen-guard (422), dubbele plaatsing (409), zelf/kring (422)."""
    from sqlalchemy import text as _text
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate
    from services import bedrijfsfunctie_service as svc
    from services.errors import OngeldigeRegistratie, RegistratieConflict

    async def _flow(s):
        ids, mids = [], []
        fouten = {}
        try:
            mid = await _maak_model(s)
            mids.append(mid)
            a = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-P A"))
            ids.append(a["id"])
            b = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-P B", ouder_id=a["id"]))
            ids.append(b["id"])
            # Typeborging: een bestaand NIET-functie-element als ouder ⇒ 422.
            comp_id = (await s.execute(_text(
                "SELECT id FROM component LIMIT 1"))).scalar()
            if comp_id is not None:
                try:
                    await svc.plaats(s, _TID, b["id"], comp_id)
                except OngeldigeRegistratie as e:
                    fouten["type"] = e.code
            # Modelinhoud: plaatsing muteren op een model-functie ⇒ 422 (gebruikers-pad)…
            mf = await _maak_modelfunctie(s, svc, "WT-P Model", "wt_p_model", mid)
            ids.append(mf["id"])
            try:
                await svc.plaats(s, _TID, mf["id"], a["id"])
            except OngeldigeRegistratie as e:
                fouten["model"] = e.code
            # …maar het import-pad passeert legitiem.
            via_import = await svc.plaats(s, _TID, mf["id"], a["id"], via_import=True)
            fouten["import_ok"] = len(via_import["ouder_ids"]) == 1
            # Vervallen ouder ⇒ 422.
            verv = await _maak_modelfunctie(s, svc, "WT-P Vervallen", "wt_p_verv", mid)
            ids.append(verv["id"])
            rij = await svc.haal_op(s, _TID, verv["id"])
            rij.vervallen = True
            await s.commit()
            try:
                await svc.plaats(s, _TID, b["id"], verv["id"])
            except OngeldigeRegistratie as e:
                fouten["vervallen"] = e.code
            # Dubbel ⇒ 409.
            try:
                await svc.plaats(s, _TID, b["id"], a["id"])
            except RegistratieConflict as e:
                fouten["dubbel"] = e.code
            # Zelf + kring (via de meervoudige-ouders-graaf) ⇒ 422.
            try:
                await svc.plaats(s, _TID, a["id"], a["id"])
            except OngeldigeRegistratie as e:
                fouten["zelf"] = e.code
            try:
                await svc.plaats(s, _TID, a["id"], b["id"])  # a onder zijn eigen kind
            except OngeldigeRegistratie as e:
                fouten["kring"] = e.code
            return fouten
        finally:
            await _ruim(s, ids, mids)

    fouten = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert fouten.get("type") == "ONGELDIGE_PLAATSING"
    assert fouten["model"] == "MODELINHOUD_BESCHERMD"
    assert fouten["import_ok"] is True
    assert fouten["vervallen"] == "VERVALLEN_NIET_KOPPELBAAR"
    assert fouten["dubbel"] == "PLAATSING_BESTAAT"
    assert fouten["zelf"] == "CYCLISCHE_HIERARCHIE"
    assert fouten["kring"] == "CYCLISCHE_HIERARCHIE"


@integratie
def test_bedrijfsfunctie_modelinhoud_en_verwijdergedrag_live():
    """Modelinhoud niet bewerkbaar/verwijderbaar (422); eigen functie mét kind ⇒ 409;
    plaatsing weghalen maakt het kind een wortel (legitiem), daarna kan verwijderen."""
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate, BedrijfsfunctieUpdate
    from services import bedrijfsfunctie_service as svc
    from services.errors import OngeldigeRegistratie, RegistratieConflict

    async def _flow(s):
        ids, mids = [], []
        fouten = {}
        try:
            mid = await _maak_model(s)
            mids.append(mid)
            mf = await _maak_modelfunctie(s, svc, "WT-D Model", "wt_d_model", mid)
            ids.append(mf["id"])
            try:
                await svc.werk_bij(s, _TID, mf["id"], BedrijfsfunctieUpdate(naam="Hernoemd"))
            except OngeldigeRegistratie as e:
                fouten["bewerk"] = e.code
            try:
                await svc.verwijder(s, _TID, mf["id"])
            except OngeldigeRegistratie as e:
                fouten["verwijder_model"] = e.code
            a = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-D Eigen"))
            ids.append(a["id"])
            k = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-D Kind", ouder_id=a["id"]))
            ids.append(k["id"])
            try:
                await svc.verwijder(s, _TID, a["id"])
            except RegistratieConflict as e:
                fouten["heeft_kind"] = e.code
            # Plaatsing weghalen → kind wordt wortel → ouder is kinderloos → mag weg.
            los = await svc.verwijder_plaatsing(s, _TID, k["id"], a["id"])
            fouten["wortel_geworden"] = los["ouder_ids"] == []
            await svc.verwijder(s, _TID, a["id"])
            ids.remove(a["id"])
            await svc.verwijder(s, _TID, k["id"])
            ids.remove(k["id"])
            return fouten
        finally:
            await _ruim(s, ids, mids)

    fouten = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert fouten["bewerk"] == "MODELINHOUD_BESCHERMD"
    assert fouten["verwijder_model"] == "MODELINHOUD_BESCHERMD"
    assert fouten["heeft_kind"] == "HEEFT_DEELFUNCTIES"
    assert fouten["wortel_geworden"] is True


@integratie
def test_bedrijfsfunctie_rls_isolatie_live():
    from sqlalchemy import text as _text
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate
    from services import bedrijfsfunctie_service as svc

    async def _maak(s):
        return (await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-P RLS")))["id"]

    async def _zicht(s, fid):
        return (await s.execute(_text(
            "SELECT count(*) FROM bedrijfsfunctie WHERE id=:i"), {"i": str(fid)})).scalar()

    fid = asyncio.run(_run_rls(_TID, "test:bert", _maak))
    try:
        zicht_b = asyncio.run(_run_rls(_TID_B, "test:bert", lambda s: _zicht(s, fid)))
        zicht_a = asyncio.run(_run_rls(_TID, "test:bert", lambda s: _zicht(s, fid)))
    finally:
        asyncio.run(_run_rls(_TID, "test:bert", lambda s: _ruim(s, [fid])))
    assert zicht_b == 0 and zicht_a == 1


@integratie
def test_bedrijfsfunctie_audit_en_geen_engine_live():
    """Dubbele engine-borging (live helft) + ADR-044 1.2: de PLAATSING wordt als
    relatie-rij geaudit (het relatie-spoor); functie-mutaties in de eigen trail; en
    niets muteert component_profiel/lifecycle."""
    from sqlalchemy import text as _text
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate
    from services import bedrijfsfunctie_service as svc

    async def _flow(s):
        ids = []
        try:
            profielen_voor = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel"))).scalar()
            a = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-P Audit A"))
            ids.append(a["id"])
            b = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-P Audit B"))
            ids.append(b["id"])
            na = await svc.plaats(s, _TID, b["id"], a["id"])
            # De plaatsing = relatie-rij → geaudit via het relatie-spoor.
            rel_audit = (await s.execute(_text(
                "SELECT count(*) FROM audit_log WHERE entiteit_type='relatie' "
                "AND actie='create' AND wijziging::text LIKE :d"),
                {"d": f'%{b["id"]}%'})).scalar()
            f_audit = (await s.execute(_text(
                "SELECT count(*) FROM audit_log WHERE entiteit_type='bedrijfsfunctie' "
                "AND entiteit_id=:i"), {"i": str(a["id"])})).scalar()
            profielen_na = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel"))).scalar()
            return na, rel_audit, f_audit, profielen_voor, profielen_na
        finally:
            await _ruim(s, ids)

    na, rel_audit, f_audit, voor, na_p = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert [str(x) for x in na["ouder_ids"]] != []
    assert rel_audit >= 1   # plaatsing naspeurbaar in de trail (relatie-spoor)
    assert f_audit >= 1     # functie-create in de eigen trail
    assert voor == na_p     # engine onaangeroerd
