"""Tests — ADR-042 slice 2+3: applicatiefunctie-catalogus + procesvervulling (koppelregel).

Offline: catalogus (model/seed/idempotentie/validatie), koppelregel-model (uniek tripel +
composiet-FK's CASCADE), schema, RBAC (tenant + platform), audit-allowlists (tenant +
platform) + de regressie-borging dat de vervulling-service de engine NIET raakt.
Live (skip-if-no-DB): maak + lezen beide richtingen (naam-verrijking), losse regels
(tweede functie zelfde paar), dubbel tripel 409, ongeldige functie/typen 422,
element-cascade (component weg ⇒ regel weg), RLS-isolatie, audit-capture, geen
engine-state. Live-tests ruimen hun element-rijen structureel op (finally).
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


# ── Offline: applicatiefunctie-catalogus (Deel A) ────────────────────────────────

def test_applicatiefunctie_startset_vorm_en_inhoud():
    """GEMMA-geënte startset (subknoop 4): 5 opties, unieke sleutels, geordend."""
    from services.seed_applicatiefunctie import bouw_applicatiefunctie

    rijen = bouw_applicatiefunctie()
    sleutels = [r["optie_sleutel"] for r in rijen]
    assert sleutels == ["registreren", "raadplegen", "archiveren", "gegevens_leveren", "ondersteunen"]
    assert len(set(sleutels)) == 5
    assert [r["volgorde"] for r in rijen] == list(range(5))
    assert all(r["actief"] for r in rijen)


def test_applicatiefunctie_seed_idempotent():
    from unittest.mock import AsyncMock

    from services.seed_applicatiefunctie import seed_applicatiefunctie

    session = AsyncMock()
    assert asyncio.run(seed_applicatiefunctie(session)) == 5
    assert asyncio.run(seed_applicatiefunctie(session)) == 5  # tweede run: geen fout, vast 5


def test_applicatiefunctie_migratie_byte_gelijk_aan_seed():
    """De 0058-migratie zaait exact dezelfde startset als de seed-functie (norm)."""
    import importlib.util
    import pathlib

    pad = (
        pathlib.Path(__file__).resolve().parents[2]
        / "migrations" / "versions" / "0058_adr042_appfunctie.py"
    )
    spec = importlib.util.spec_from_file_location("m0058", pad)
    m0058 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m0058)
    from services.seed_applicatiefunctie import _FUNCTIES

    assert m0058._FUNCTIES == _FUNCTIES


def test_applicatiefunctie_geen_systeem_sleutel():
    """ADR-042 besluit 3: geen systeem-sleutel — de config-service kent geen
    SYSTEEM_SLEUTEL-bescherming (elke optie is deactiveerbaar)."""
    import inspect

    import services.applicatiefunctieconfig_service as svc

    assert "_SYSTEEM_SLEUTEL" not in inspect.getsource(svc)


def test_applicatiefunctie_platform_rbac_en_audit():
    from app.core.audit import AUDIT_PLATFORM_ENTITEITEN
    from app.core.platform_rbac import PlatformEntiteit, heeft_platform_permissie
    from app.core.rbac import Actie

    assert "applicatiefunctie_optie" in AUDIT_PLATFORM_ENTITEITEN
    assert heeft_platform_permissie(["platformbeheerder"], PlatformEntiteit.APPLICATIEFUNCTIECONFIG, Actie.WIJZIGEN)
    assert not heeft_platform_permissie(["platformbeheerder"], PlatformEntiteit.APPLICATIEFUNCTIECONFIG, Actie.VERWIJDEREN)
    assert heeft_platform_permissie(["platformoperator"], PlatformEntiteit.APPLICATIEFUNCTIECONFIG, Actie.LEZEN)
    assert not heeft_platform_permissie(["platformoperator"], PlatformEntiteit.APPLICATIEFUNCTIECONFIG, Actie.AANMAKEN)


# ── Offline: koppelregel-model + schema (Deel B) ─────────────────────────────────

def test_procesvervulling_model_uniek_tripel_en_cascade():
    from models.models import Procesvervulling

    assert Procesvervulling.__tablename__ == "procesvervulling"
    uqs = {
        con.name: [c.name for c in con.columns]
        for con in Procesvervulling.__table__.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    }
    assert uqs["uq_procesvervulling"] == ["tenant_id", "component_id", "proces_id", "applicatiefunctie"]
    fks = {
        con.name: con
        for con in Procesvervulling.__table__.constraints
        if con.__class__.__name__ == "ForeignKeyConstraint"
    }
    assert fks["fk_procesvervulling_component"].ondelete == "CASCADE"
    assert fks["fk_procesvervulling_proces"].ondelete == "CASCADE"
    assert "toelichting" in Procesvervulling.__table__.columns  # subknoop 2-default


def test_procesvervulling_schema_validatie():
    from pydantic import ValidationError
    from schemas.procesvervulling import ProcesvervullingAanmaken

    ok = ProcesvervullingAanmaken(
        component_id=uuid.uuid4(), proces_id=uuid.uuid4(), applicatiefunctie="registreren"
    )
    assert ok.toelichting is None
    with pytest.raises(ValidationError):  # functie verplicht
        ProcesvervullingAanmaken(component_id=uuid.uuid4(), proces_id=uuid.uuid4(), applicatiefunctie=" ")
    with pytest.raises(ValidationError):  # extra veld verboden
        ProcesvervullingAanmaken(
            component_id=uuid.uuid4(), proces_id=uuid.uuid4(),
            applicatiefunctie="registreren", onbekend="x",
        )


def test_procesvervulling_in_rbac_en_audit():
    from app.core.audit import AUDIT_TENANT_ENTITEITEN
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    assert "procesvervulling" in AUDIT_TENANT_ENTITEITEN
    assert heeft_permissie(["medewerker"], Entiteit.PROCESVERVULLING, Actie.AANMAKEN)
    assert heeft_permissie(["medewerker"], Entiteit.PROCESVERVULLING, Actie.WIJZIGEN)  # verbreken
    assert not heeft_permissie(["viewer"], Entiteit.PROCESVERVULLING, Actie.AANMAKEN)
    assert heeft_permissie(["auditor"], Entiteit.PROCESVERVULLING, Actie.LEZEN)


def test_procesvervulling_service_raakt_engine_niet():
    """ADR-042-invariant: score blijft de enige lifecycle-driver."""
    import services.procesvervulling_service as pvs

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(pvs, naam), f"procesvervulling_service mag de engine niet importeren: {naam!r}"


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                res = (await c.execute(text("SELECT to_regclass('procesvervulling')"))).scalar()
            return res is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB/procesvervulling-tabel niet bereikbaar")


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


async def _maak_component(s, naam):
    """Kale component (database-type, géén applicatie) direct via ORM — geen
    engine-trigger; bewijst meteen het component-brede koppelen (ADR-042 besluit 3)."""
    from models.models import Component, Element, ElementType, HostingModel

    elem = Element(tenant_id=uuid.UUID(_TID), element_type=ElementType.component)
    s.add(elem)
    await s.flush()
    s.add(Component(id=elem.id, tenant_id=uuid.UUID(_TID), naam=naam, componenttype="database",
                    hostingmodel=HostingModel.on_premise))
    await s.commit()
    return elem.id


async def _maak_proces(s, naam, ouder_id=None):
    from schemas.proces import ProcesCreate
    from services import proces_service

    return (await proces_service.maak_aan(s, _TID, ProcesCreate(naam=naam, ouder_id=ouder_id)))["id"]


async def _ruim(s, ids):
    from sqlalchemy import text as _text

    for eid in reversed(ids):
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    await s.commit()


@integratie
def test_vervulling_maak_lees_beide_richtingen_en_losse_regels_live():
    from services import procesvervulling_service as svc

    async def _flow(s):
        ids = []
        try:
            comp = await _maak_component(s, "PV-Test DB-component")
            ids.append(comp)
            pr_top = await _maak_proces(s, "PV-Test Vergunningverlening")
            ids.append(pr_top)
            pr = await _maak_proces(s, "PV-Test Aanvraag behandelen", ouder_id=pr_top)
            ids.append(pr)
            # Twee functies op hetzelfde (component, proces)-paar = losse regels.
            r1 = await svc.maak_aan(s, _TID, comp, pr, "registreren", "eerste regel")
            r2 = await svc.maak_aan(s, _TID, comp, pr, "raadplegen")
            per_proces = await svc.lijst_voor_proces(s, _TID, pr)
            per_component = await svc.lijst_voor_component(s, _TID, comp)
            # Eén regel apart verwijderbaar — de andere blijft.
            await svc.verwijder(s, _TID, r2["vervulling_id"])
            na_verwijder = await svc.lijst_voor_proces(s, _TID, pr)
            return r1, per_proces, per_component, na_verwijder
        finally:
            await _ruim(s, ids)

    r1, per_proces, per_component, na_verwijder = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    # Naam-verrijking beide richtingen + functie-label uit de catalogus.
    assert r1["applicatiefunctie_label"] == "Registreren"
    assert len(per_proces) == 2 and per_proces[0]["component_naam"] == "PV-Test DB-component"
    assert per_proces[0]["componenttype"] == "database"  # component-breed bewezen
    assert len(per_component) == 2 and per_component[0]["proces_naam"] == "PV-Test Aanvraag behandelen"
    assert per_component[0]["proces_ouder_naam"] == "PV-Test Vergunningverlening"  # procescontext
    assert len(na_verwijder) == 1 and na_verwijder[0]["applicatiefunctie"] == "registreren"


@integratie
def test_vervulling_validaties_live():
    from services import procesvervulling_service as svc
    from services.errors import OngeldigeRegistratie, RegistratieConflict

    async def _flow(s):
        ids = []
        try:
            comp = await _maak_component(s, "PV-Val Component")
            ids.append(comp)
            pr = await _maak_proces(s, "PV-Val Proces")
            ids.append(pr)
            fouten = {}
            await svc.maak_aan(s, _TID, comp, pr, "registreren")
            # Dubbel tripel ⇒ 409.
            try:
                await svc.maak_aan(s, _TID, comp, pr, "registreren")
            except RegistratieConflict as e:
                fouten["dubbel"] = e.code
            # Onbekende functie ⇒ 422.
            try:
                await svc.maak_aan(s, _TID, comp, pr, "bestaat_niet")
            except OngeldigeRegistratie as e:
                fouten["functie"] = e.code
            # Verkeerde typen: proces als component-kant / component als proces-kant ⇒ 422.
            try:
                await svc.maak_aan(s, _TID, pr, pr, "raadplegen")
            except OngeldigeRegistratie as e:
                fouten["component_kant"] = e.code
            try:
                await svc.maak_aan(s, _TID, comp, comp, "raadplegen")
            except OngeldigeRegistratie as e:
                fouten["proces_kant"] = e.code
            return fouten
        finally:
            await _ruim(s, ids)

    fouten = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert fouten == {
        "dubbel": "VERVULLING_BESTAAT",
        "functie": "ONGELDIGE_APPLICATIEFUNCTIE",
        "component_kant": "ONGELDIG_COMPONENT",
        "proces_kant": "ONGELDIG_PROCES",
    }


@integratie
def test_vervulling_cascade_rls_audit_en_geen_engine_live():
    from sqlalchemy import text as _text

    from services import procesvervulling_service as svc

    async def _flow(s):
        ids = []
        try:
            comp = await _maak_component(s, "PV-Cas Component")
            ids.append(comp)
            pr = await _maak_proces(s, "PV-Cas Proces")
            ids.append(pr)
            regel = await svc.maak_aan(s, _TID, comp, pr, "ondersteunen")
            rid = str(regel["vervulling_id"])
            audit = (await s.execute(_text(
                "SELECT count(*) FROM audit_log WHERE entiteit_type='procesvervulling' AND entiteit_id=:i"),
                {"i": rid})).scalar()
            profiel = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": rid})).scalar()
            # Element-cascade: component weg ⇒ regel weg (FK CASCADE).
            await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(comp)})
            await s.commit()
            ids.remove(comp)
            rest = (await s.execute(_text(
                "SELECT count(*) FROM procesvervulling WHERE id=:i"), {"i": rid})).scalar()
            return audit, profiel, rest, rid
        finally:
            await _ruim(s, ids)

    audit, profiel, rest, rid = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert audit >= 1 and profiel == 0 and rest == 0

    # RLS-isolatie: tenant B ziet géén vervullingen van tenant A (steekproef op de tabel).
    async def _zicht(s):
        from sqlalchemy import text as _text
        return (await s.execute(_text(
            "SELECT count(*) FROM procesvervulling WHERE id=:i"), {"i": rid})).scalar()

    assert asyncio.run(_run_rls(_TID_B, "test:bert", _zicht)) == 0
