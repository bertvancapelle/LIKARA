"""Tests — ADR-023 Fase E (E3): Deliverable + realisatieketen.

Offline: model (element-subtype), schema, RBAC, audit-allowlist + de regressie-borging
dat de deliverable-laag de engine NIET raakt. Live (skip-if-no-DB): CRUD, ketenkoppeling
(work_package → deliverable → plateau via realization), type-validatie (422), dubbel (409),
optionaliteit, read-traversals, RLS-isolatie, audit-capture. Live-tests ruimen hun
element-rijen + realization-relaties structureel op.
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
_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"


# ── Offline: model + schema ──────────────────────────────────────────────────────

def test_deliverable_is_element_subtype():
    from models.models import Deliverable

    assert Deliverable.__tablename__ == "deliverable"
    fks = [
        sorted(c.name for c in con.columns)
        for con in Deliverable.__table__.constraints
        if con.__class__.__name__ == "ForeignKeyConstraint"
    ]
    assert ["id", "tenant_id"] in fks  # shared-PK → element(tenant_id,id)
    kols = Deliverable.__table__.columns
    assert "naam" in kols and "toelichting" in kols


def test_deliverable_schema_validatie():
    from pydantic import ValidationError
    from schemas.deliverable import DeliverableCreate, KoppelWerkpakket

    DeliverableCreate(naam="Overgezette Oracle-DB")
    with pytest.raises(ValidationError):
        DeliverableCreate(naam="  ")
    with pytest.raises(ValidationError):
        KoppelWerkpakket(work_package_id="geen-uuid")


# ── Offline: RBAC + audit + regressie ────────────────────────────────────────────

def test_deliverable_in_audit_allowlist():
    from app.core.audit import AUDIT_TENANT_ENTITEITEN

    assert "deliverable" in AUDIT_TENANT_ENTITEITEN


def test_deliverable_in_rbac_inhoud_patroon():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    assert heeft_permissie(["medewerker"], Entiteit.DELIVERABLE, Actie.AANMAKEN)
    assert heeft_permissie(["beheerder"], Entiteit.DELIVERABLE, Actie.VERWIJDEREN)
    assert not heeft_permissie(["viewer"], Entiteit.DELIVERABLE, Actie.AANMAKEN)
    assert heeft_permissie(["auditor"], Entiteit.DELIVERABLE, Actie.LEZEN)


def test_deliverable_service_raakt_engine_niet():
    import services.deliverable_service as ds

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(ds, naam), f"deliverable_service mag de engine niet importeren: {naam!r}"


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_CD_APP_URL)
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


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="cd_app-DB niet bereikbaar (offline)")


async def _run_rls(tenant, actor, fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_CD_APP_URL)
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


async def _ruim(s, ids):
    from sqlalchemy import text as _text

    for eid in ids:
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    await s.commit()


@integratie
def test_deliverable_keten_en_traversal_live():
    from schemas.deliverable import DeliverableCreate, KoppelPlateau, KoppelWerkpakket
    from schemas.plateau import PlateauCreate
    from schemas.work_package import WorkPackageCreate
    from services import deliverable_service as dsvc
    from services import plateau_service as psvc
    from services import work_package_service as wsvc

    async def _flow(s):
        ids = []
        try:
            wp = await wsvc.maak_aan(s, _TID, WorkPackageCreate(naam="WP-Del E3"))
            pl = await psvc.maak_aan(s, _TID, PlateauCreate(naam="PL-Del E3 Doel"))
            d = await dsvc.maak_aan(s, _TID, DeliverableCreate(naam="DEL-E3 Overgezette DB"))
            ids += [wp["id"], pl["id"], d["id"]]
            k_wp = await dsvc.koppel_werkpakket(s, _TID, d["id"], KoppelWerkpakket(work_package_id=wp["id"]).work_package_id)
            k_pl = await dsvc.koppel_plateau(s, _TID, d["id"], KoppelPlateau(plateau_id=pl["id"]).plateau_id)
            keten = await dsvc.keten_van_deliverable(s, _TID, d["id"])
            wp_keten = await dsvc.realisatieketen_van_werkpakket(s, _TID, wp["id"])
            return wp, pl, d, k_wp, k_pl, keten, wp_keten
        finally:
            await _ruim(s, ids)

    wp, pl, d, k_wp, k_pl, keten, wp_keten = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    # Deliverable-centrische keten.
    assert [x["element_id"] for x in keten["werkpakketten"]] == [wp["id"]]
    assert [x["element_id"] for x in keten["plateaus"]] == [pl["id"]]
    # Werkpakket-centrische traversal: wp → deliverable → plateau.
    assert wp_keten["work_package_id"] == wp["id"]
    assert len(wp_keten["deliverables"]) == 1
    dlv = wp_keten["deliverables"][0]
    assert dlv["deliverable_id"] == d["id"]
    assert [p["plateau_id"] for p in dlv["plateaus"]] == [pl["id"]]


@integratie
def test_deliverable_type_validatie_en_dubbel_live():
    from schemas.deliverable import DeliverableCreate
    from schemas.plateau import PlateauCreate
    from schemas.work_package import WorkPackageCreate
    from services import deliverable_service as dsvc
    from services import plateau_service as psvc
    from services import work_package_service as wsvc
    from services.errors import OngeldigeRegistratie, RegistratieConflict

    async def _flow(s):
        ids = []
        try:
            wp = await wsvc.maak_aan(s, _TID, WorkPackageCreate(naam="WP-Val E3"))
            pl = await psvc.maak_aan(s, _TID, PlateauCreate(naam="PL-Val E3"))
            d = await dsvc.maak_aan(s, _TID, DeliverableCreate(naam="DEL-Val E3"))
            ids += [wp["id"], pl["id"], d["id"]]
            fouten = {}
            # Een plateau als "werkpakket"-realiseerder → 422.
            try:
                await dsvc.koppel_werkpakket(s, _TID, d["id"], pl["id"])
            except OngeldigeRegistratie as e:
                fouten["wp_type"] = e.code
            # Een werkpakket als "plateau" → 422.
            try:
                await dsvc.koppel_plateau(s, _TID, d["id"], wp["id"])
            except OngeldigeRegistratie as e:
                fouten["pl_type"] = e.code
            # Geldige koppeling, daarna dubbel → 409.
            await dsvc.koppel_werkpakket(s, _TID, d["id"], wp["id"])
            try:
                await dsvc.koppel_werkpakket(s, _TID, d["id"], wp["id"])
            except RegistratieConflict as e:
                fouten["dubbel"] = e.code
            return fouten
        finally:
            await _ruim(s, ids)

    fouten = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert fouten == {
        "wp_type": "ONGELDIGE_REALISATIE",
        "pl_type": "ONGELDIGE_REALISATIE",
        "dubbel": "REALISATIE_BESTAAT",
    }


@integratie
def test_deliverable_optioneel_en_geen_engine_live():
    """Een deliverable zonder werkpakket/plateau is toegestaan (geen verplichte keten);
    en hij krijgt geen engine-state (component_profiel)."""
    from sqlalchemy import text as _text
    from schemas.deliverable import DeliverableCreate
    from services import deliverable_service as dsvc

    async def _flow(s):
        ids = []
        try:
            d = await dsvc.maak_aan(s, _TID, DeliverableCreate(naam="DEL-Solo E3"))
            ids.append(d["id"])
            keten = await dsvc.keten_van_deliverable(s, _TID, d["id"])
            audit = (await s.execute(_text(
                "SELECT count(*) FROM audit_log WHERE entiteit_type='deliverable' AND entiteit_id=:i"),
                {"i": str(d["id"])})).scalar()
            profiel = (await s.execute(_text(
                "SELECT count(*) FROM component_profiel WHERE id=:i"), {"i": str(d["id"])})).scalar()
            return keten, audit, profiel
        finally:
            await _ruim(s, ids)

    keten, audit, profiel = asyncio.run(_run_rls(_TID, "test:bert", _flow))
    assert keten == {"werkpakketten": [], "plateaus": []}  # losse deliverable mag
    assert audit >= 1 and profiel == 0


@integratie
def test_deliverable_rls_isolatie_live():
    from sqlalchemy import text as _text
    from schemas.deliverable import DeliverableCreate
    from services import deliverable_service as dsvc

    async def _maak(s):
        return (await dsvc.maak_aan(s, _TID, DeliverableCreate(naam="DEL-RLS")))["id"]

    async def _zicht(s, did):
        return (await s.execute(_text("SELECT count(*) FROM deliverable WHERE id=:i"), {"i": str(did)})).scalar()

    did = asyncio.run(_run_rls(_TID, "test:bert", _maak))
    try:
        zicht_b = asyncio.run(_run_rls(_TID_B, "test:bert", lambda s: _zicht(s, did)))
        zicht_a = asyncio.run(_run_rls(_TID, "test:bert", lambda s: _zicht(s, did)))
    finally:
        asyncio.run(_run_rls(_TID, "test:bert", lambda s: _ruim(s, [did])))
    assert zicht_b == 0 and zicht_a == 1
