"""Tests — ADR-043 gate 1a: Bedrijfsfunctie-element + referentiemodel-lagen.

Offline: model (element-subtype + composiet self-FK RESTRICT + CHECK's, herkomst-paar,
vervallen-vlag), referentiemodel (tenant + platform-aanbod), schema, ArchiMate-typing
(business_function in de whitelist; DERDE gemarkeerde behavior-afwijking),
sorteer-allowlist-sync, RBAC (tenant + platform), audit-allowlists + de regressie-
borging dat de functie-laag de engine NIET raakt.
Live (skip-if-no-DB): CRUD + subboom, modelinhoud-bescherming (422), vervallen-guard
(422), verwijdergedrag (409 + model-functie 422), cycluspreventie, RLS-isolatie,
audit-capture + geen-engine-mutatie. Live-tests ruimen hun element-rijen structureel op
(element-supertype, leaf→root, in finally); de referentiemodel-rij via een directe
DELETE (geen element).
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

def test_bedrijfsfunctie_is_element_subtype_met_fks():
    from models.models import Bedrijfsfunctie

    assert Bedrijfsfunctie.__tablename__ == "bedrijfsfunctie"
    fks = {
        con.name: con
        for con in Bedrijfsfunctie.__table__.constraints
        if con.__class__.__name__ == "ForeignKeyConstraint"
    }
    # shared-PK → element(tenant_id,id), cascade.
    assert fks["fk_bedrijfsfunctie_element"].ondelete == "CASCADE"
    # composiet self-FK met RESTRICT (subboom niet stilzwijgend wegvagen).
    assert fks["fk_bedrijfsfunctie_ouder"].ondelete == "RESTRICT"
    # herkomst-FK naar de INGELEZEN instantie (tenant-zijde), RESTRICT — een model met
    # functies verdwijnt niet stil (besluit LI039-5/6).
    assert fks["fk_bedrijfsfunctie_bron_model"].ondelete == "RESTRICT"
    kols = Bedrijfsfunctie.__table__.columns
    for k in ("naam", "definitie", "ouder_id", "bron_model_id", "bron_sleutel", "vervallen"):
        assert k in kols


def test_bedrijfsfunctie_checks_en_bron_uniciteit():
    from models.models import Bedrijfsfunctie

    checks = [
        con.name for con in Bedrijfsfunctie.__table__.constraints
        if con.__class__.__name__ == "CheckConstraint"
    ]
    assert "ck_bedrijfsfunctie_geen_self_parent" in checks
    # Herkomst is een paar: model + sleutel samen gezet of samen leeg (eigen functie).
    assert "ck_bedrijfsfunctie_bron_paar" in checks
    uniques = [
        sorted(c.name for c in con.columns)
        for con in Bedrijfsfunctie.__table__.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    ]
    # Bronsleutel = identiteit binnen één ingelezen model (NULL distinct → eigen
    # functies onbeperkt, betekenis-precedent).
    assert ["bron_model_id", "bron_sleutel", "tenant_id"] in uniques
    assert ["id", "tenant_id"] in uniques  # composiet-FK-target self-FK


def test_referentiemodel_twee_lagen():
    """Besluit LI039-5: aanbod = platform (`referentiemodel_optie`, geen tenant_id),
    ingelezen inhoud = tenant (`referentiemodel`, tenant-scoped, herinlees = bijwerken)."""
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
    assert ["id", "tenant_id"] in uniques            # composiet-FK-target
    assert ["model_sleutel", "tenant_id"] in uniques  # één instantie per model


def test_bedrijfsfunctie_schema_validatie():
    from pydantic import ValidationError
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate

    ok = BedrijfsfunctieCreate(naam="Dienstverlening")
    assert ok.ouder_id is None
    BedrijfsfunctieCreate(naam="Klantcontact", ouder_id=uuid.uuid4())
    with pytest.raises(ValidationError):  # naam verplicht
        BedrijfsfunctieCreate(naam="  ")
    with pytest.raises(ValidationError):  # extra veld verboden
        BedrijfsfunctieCreate(naam="X", onbekend="y")
    with pytest.raises(ValidationError):  # herkomst NOOIT via het gebruikers-pad
        BedrijfsfunctieCreate(naam="X", bron_sleutel="s")
    with pytest.raises(ValidationError):  # vervallen NOOIT via het gebruikers-pad
        BedrijfsfunctieCreate(naam="X", vervallen=True)


# ── Offline: ArchiMate-typing (ADR-043) ──────────────────────────────────────────

def test_bedrijfsfunctie_typing_business_function_behavior():
    """Bedrijfsfunctie = business_function / business / behavior — de DERDE gemarkeerde
    behavior-afwijking op OK-3 (naast work_package en proces). ADR-043 heropent de door
    ADR-042 geparkeerde as."""
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
    from app.core.audit import AUDIT_PLATFORM_ENTITEITEN, AUDIT_TENANT_ENTITEITEN

    assert "bedrijfsfunctie" in AUDIT_TENANT_ENTITEITEN
    assert "referentiemodel" in AUDIT_TENANT_ENTITEITEN
    assert "referentiemodel_optie" in AUDIT_PLATFORM_ENTITEITEN


def test_bedrijfsfunctie_in_rbac_inhoud_patroon():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    for ent in (Entiteit.BEDRIJFSFUNCTIE, Entiteit.REFERENTIEMODEL):
        assert heeft_permissie(["medewerker"], ent, Actie.AANMAKEN)
        assert heeft_permissie(["beheerder"], ent, Actie.VERWIJDEREN)
        assert not heeft_permissie(["viewer"], ent, Actie.AANMAKEN)
        assert heeft_permissie(["auditor"], ent, Actie.LEZEN)


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
    """ADR-043-invariant: score blijft de enige lifecycle-driver — de functie-service
    importeert géén engine-onderdeel."""
    import services.bedrijfsfunctie_service as bs

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(bs, naam), f"bedrijfsfunctie_service mag de engine niet importeren: {naam!r}"


def test_seed_referentiemodel_puur_en_idempotent_vormgegeven():
    from services.seed_referentiemodel import bouw_referentiemodel

    rijen = bouw_referentiemodel()
    assert any(r["optie_sleutel"] == "gemma_bedrijfsfuncties" for r in rijen)
    assert all(r["actief"] for r in rijen)


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                # De bedrijfsfunctie-tabel moet bestaan (migratie 0062), anders skippen.
                res = (await c.execute(text("SELECT to_regclass('bedrijfsfunctie')"))).scalar()
            return res is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


integratie = pytest.mark.skipif(
    not _db_bereikbaar(), reason="lk_app-DB/bedrijfsfunctie-tabel niet bereikbaar"
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
    """Element-rijen leaf→root (RESTRICT-veilig) via het supertype; daarna de
    referentiemodel-rij(en) (geen element — directe DELETE, ná de functies i.v.m. de
    bron-FK RESTRICT)."""
    from sqlalchemy import text as _text

    for eid in reversed(ids):  # aanmaakvolgorde root→leaf → omgekeerd opruimen
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    for mid in model_ids:
        await s.execute(_text("DELETE FROM referentiemodel WHERE id=:i"), {"i": str(mid)})
    await s.commit()


async def _maak_model(s, sleutel="wt_bf_model"):
    """Testfixture: één ingelezen-referentiemodel-rij (ORM → audit-gedekt)."""
    from models.models import Referentiemodel

    rij = Referentiemodel(
        tenant_id=uuid.UUID(_TID), model_sleutel=sleutel,
        naam="WT-BF Testmodel", versie="t1",
    )
    s.add(rij)
    await s.commit()
    await s.refresh(rij)
    return rij.id


async def _maak_modelfunctie(s, svc, naam, sleutel, model_id, ouder_id=None):
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate

    return await svc.maak_aan(
        s, _TID, BedrijfsfunctieCreate(naam=naam, ouder_id=ouder_id),
        bron_model_id=model_id, bron_sleutel=sleutel,
    )


@integratie
def test_bedrijfsfunctie_crud_boom_subboom_en_herkomst_live():
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate
    from services import bedrijfsfunctie_service as svc

    async def _flow(s):
        ids, mids = [], []
        try:
            mid = await _maak_model(s)
            mids.append(mid)
            a = await _maak_modelfunctie(s, svc, "WT-BF Primair", "wt_primair", mid)
            ids.append(a["id"])
            b = await _maak_modelfunctie(s, svc, "WT-BF Dienstverlening", "wt_dienst", mid, a["id"])
            ids.append(b["id"])
            eigen = await svc.maak_aan(
                s, _TID, BedrijfsfunctieCreate(naam="WT-BF Eigen functie", ouder_id=b["id"])
            )
            ids.append(eigen["id"])
            subboom = await svc.subboom(s, _TID, a["id"])
            detail = await svc.lees_detail(s, _TID, a["id"])
            return a, b, eigen, subboom, detail
        finally:
            await _ruim(s, ids, mids)

    a, b, eigen, subboom, detail = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    # Herkomst-resolutie: model-functie draagt sleutel + modelnaam/-versie; eigen niet.
    assert a["bron_sleutel"] == "wt_primair" and a["bron_model_naam"] == "WT-BF Testmodel"
    assert detail["bron_model_versie"] == "t1"
    assert eigen["bron_sleutel"] is None and eigen["bron_model_naam"] is None
    per_id = {x["id"]: x for x in subboom}
    assert per_id[b["id"]]["niveau"] == 1 and per_id[eigen["id"]]["niveau"] == 2
    assert per_id[eigen["id"]]["pad"][-1] == "WT-BF Eigen functie"


@integratie
def test_bedrijfsfunctie_modelinhoud_beschermd_live():
    """ADR-043 kern: modelinhoud lees je — je wijzigt hem niet (naam/definitie/plek),
    en je verwijdert hem nooit. Eigen functies zijn wél volledig bewerkbaar."""
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate, BedrijfsfunctieUpdate
    from services import bedrijfsfunctie_service as svc
    from services.errors import OngeldigeRegistratie

    async def _flow(s):
        ids, mids = [], []
        try:
            mid = await _maak_model(s)
            mids.append(mid)
            mf = await _maak_modelfunctie(s, svc, "WT-BF Model", "wt_model", mid)
            ids.append(mf["id"])
            eigen = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-BF Eigen"))
            ids.append(eigen["id"])
            fouten = {}
            for veld, upd in (
                ("naam", BedrijfsfunctieUpdate(naam="Hernoemd")),
                ("definitie", BedrijfsfunctieUpdate(definitie="Eigen tekst")),
                ("ouder", BedrijfsfunctieUpdate(ouder_id=eigen["id"])),
            ):
                try:
                    await svc.werk_bij(s, _TID, mf["id"], upd)
                except OngeldigeRegistratie as e:
                    fouten[veld] = e.code
            try:
                await svc.verwijder(s, _TID, mf["id"])
            except OngeldigeRegistratie as e:
                fouten["verwijder"] = e.code
            # Eigen functie: bewerken slaagt gewoon.
            bewerkt = await svc.werk_bij(
                s, _TID, eigen["id"], BedrijfsfunctieUpdate(naam="WT-BF Eigen v2")
            )
            return fouten, bewerkt
        finally:
            await _ruim(s, ids, mids)

    fouten, bewerkt = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert fouten == {
        "naam": "MODELINHOUD_BESCHERMD", "definitie": "MODELINHOUD_BESCHERMD",
        "ouder": "MODELINHOUD_BESCHERMD", "verwijder": "MODELINHOUD_BESCHERMD",
    }
    assert bewerkt["naam"] == "WT-BF Eigen v2"


@integratie
def test_bedrijfsfunctie_vervallen_niet_koppelbaar_live():
    """Besluit LI039-6: vervallen = zichtbaar mét markering, NIET meer koppelbaar —
    geen nieuwe functies eronder (aanmaken én verplaatsen geweigerd); bestaande
    kinderen blijven staan."""
    from sqlalchemy import text as _text
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate, BedrijfsfunctieUpdate
    from services import bedrijfsfunctie_service as svc
    from services.errors import OngeldigeRegistratie

    async def _flow(s):
        ids, mids = [], []
        try:
            mid = await _maak_model(s)
            mids.append(mid)
            verv = await _maak_modelfunctie(s, svc, "WT-BF Vervallen", "wt_vervallen", mid)
            ids.append(verv["id"])
            kind = await _maak_modelfunctie(s, svc, "WT-BF Kind", "wt_kind", mid, verv["id"])
            ids.append(kind["id"])
            # Markeer vervallen (het gate-1b-herinlees-pad; hier direct, ORM → audit).
            obj = await svc.haal_op(s, _TID, verv["id"])
            obj.vervallen = True
            await s.commit()
            fouten = {}
            try:
                await svc.maak_aan(
                    s, _TID, BedrijfsfunctieCreate(naam="WT-BF Nieuw", ouder_id=verv["id"])
                )
            except OngeldigeRegistratie as e:
                fouten["aanmaken"] = e.code
            eigen = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-BF Los"))
            ids.append(eigen["id"])
            try:
                await svc.werk_bij(s, _TID, eigen["id"], BedrijfsfunctieUpdate(ouder_id=verv["id"]))
            except OngeldigeRegistratie as e:
                fouten["verplaatsen"] = e.code
            # Zichtbaar + bestaand kind intact (het signaal is de werklijst, geen opruimactie).
            kind_ouder = (await s.execute(_text(
                "SELECT ouder_id FROM bedrijfsfunctie WHERE id=:i"), {"i": str(kind["id"])})).scalar()
            zichtbaar = await svc.lees_detail(s, _TID, verv["id"])
            return fouten, str(kind_ouder), zichtbaar
        finally:
            await _ruim(s, ids, mids)

    fouten, kind_ouder, zichtbaar = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert fouten == {
        "aanmaken": "VERVALLEN_NIET_KOPPELBAAR", "verplaatsen": "VERVALLEN_NIET_KOPPELBAAR",
    }
    assert zichtbaar["vervallen"] is True and kind_ouder == str(zichtbaar["id"])


@integratie
def test_bedrijfsfunctie_cyclus_en_verwijdergedrag_live():
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate, BedrijfsfunctieUpdate
    from services import bedrijfsfunctie_service as svc
    from services.errors import OngeldigeRegistratie, RegistratieConflict

    async def _flow(s):
        ids = []
        try:
            a = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-BF Cyc A"))
            ids.append(a["id"])
            b = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-BF Cyc B", ouder_id=a["id"]))
            ids.append(b["id"])
            fouten = {}
            try:
                await svc.werk_bij(s, _TID, a["id"], BedrijfsfunctieUpdate(ouder_id=a["id"]))
            except OngeldigeRegistratie as e:
                fouten["self"] = e.code
            try:
                await svc.werk_bij(s, _TID, a["id"], BedrijfsfunctieUpdate(ouder_id=b["id"]))
            except OngeldigeRegistratie as e:
                fouten["kring"] = e.code
            try:
                await svc.verwijder(s, _TID, a["id"])
            except RegistratieConflict as e:
                fouten["ouder_delete"] = e.code
            # Kind eerst weg, dan ouder → mag (eigen functies).
            await svc.verwijder(s, _TID, b["id"])
            ids.remove(b["id"])
            await svc.verwijder(s, _TID, a["id"])
            ids.remove(a["id"])
            return fouten
        finally:
            await _ruim(s, ids)

    fouten = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert fouten == {
        "self": "CYCLISCHE_HIERARCHIE", "kring": "CYCLISCHE_HIERARCHIE",
        "ouder_delete": "HEEFT_DEELFUNCTIES",
    }


@integratie
def test_bedrijfsfunctie_rls_isolatie_live():
    from sqlalchemy import text as _text
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate
    from services import bedrijfsfunctie_service as svc

    async def _maak(s):
        return (await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-BF RLS")))["id"]

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
    """Dubbele engine-borging (live helft): aanmaken/wijzigen muteert geen
    component_profiel/lifecycle — een bedrijfsfunctie krijgt geen profiel en de
    profiel-telling blijft byte-gelijk. Audit-capture dekt de nieuwe entiteit."""
    from sqlalchemy import text as _text
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate, BedrijfsfunctieUpdate
    from services import bedrijfsfunctie_service as svc

    async def _flow(s):
        ids = []
        try:
            profielen_voor = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel"))).scalar()
            f = await svc.maak_aan(s, _TID, BedrijfsfunctieCreate(naam="WT-BF Audit"))
            ids.append(f["id"])
            await svc.werk_bij(s, _TID, f["id"], BedrijfsfunctieUpdate(definitie="tekst"))
            audit = (await s.execute(_text(
                "SELECT count(*) FROM audit_log "
                "WHERE entiteit_type='bedrijfsfunctie' AND entiteit_id=:i"),
                {"i": str(f["id"])})).scalar()
            eigen_profiel = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": str(f["id"])})).scalar()
            profielen_na = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel"))).scalar()
            return audit, eigen_profiel, profielen_voor, profielen_na
        finally:
            await _ruim(s, ids)

    audit, eigen_profiel, voor, na = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert audit >= 2          # create + update in de trail
    assert eigen_profiel == 0  # geen engine-state op de functie
    assert voor == na          # de totale profiel-stand is onaangeroerd
