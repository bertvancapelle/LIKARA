"""ADR-023 Fase A — element-identiteit + ArchiMate-typing-catalogus.

Offline: element-supertype-model + shared-PK-grens, catalogus-dimensie + dekkingstest
(elk actief componenttype heeft een ArchiMate-mapping), relatietype-kenmerk-definities.
Live (skip-if-no-DB): element-RLS-isolatie tussen tenants.
"""
import asyncio
import uuid

import pytest
from sqlalchemy import text


# ── Element-supertype (model) ────────────────────────────────────────────────────

def test_element_type_enum_waarden():
    from models.models import ElementType

    assert [e.value for e in ElementType] == [
        "component", "datatype", "gebruikersgroep", "contract",
        "plateau", "gap", "work_package", "deliverable",
        # ADR-024 slice 1 — partij-supertype (business actor).
        "partij",
        # ADR-042 slice 1 — procesregister (business process).
        "proces",
        # ADR-043 gate 1a — bedrijfsfunctie-as (business function).
        "bedrijfsfunctie",
    ]


def test_element_model_tenant_scoped_en_unique_target():
    from models.models import Element

    assert Element.__tablename__ == "element"
    kols = Element.__table__.columns
    assert "tenant_id" in kols and "element_type" in kols
    # UNIQUE(tenant_id, id) = composiet-FK-target (Besluit 12).
    uniques = [
        sorted(c.name for c in con.columns)
        for con in Element.__table__.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    ]
    assert ["id", "tenant_id"] in uniques


def test_component_is_subtype_van_element_composiet_fk():
    from models.models import Component

    fks = [
        sorted(c.name for c in con.columns)
        for con in Component.__table__.constraints
        if con.__class__.__name__ == "ForeignKeyConstraint"
    ]
    # Component verwijst via (tenant_id, id) naar element → shared-PK + tenant-consistent.
    assert ["id", "tenant_id"] in fks


# ── Typing-catalogus + dekkingstest ──────────────────────────────────────────────

def test_archimate_relatie_dimensie_acht_typen_met_kenmerken():
    from services.seed_componentconfig import bouw_componentconfig

    rels = {
        r["optie_sleutel"]: r
        for r in bouw_componentconfig()
        if r["dimensie"].value == "archimate_relatie"
    }
    assert set(rels) == {
        "composition", "aggregation", "serving", "assignment", "flow", "realization",
        "association", "access",
    }
    # OK-2: kenmerk-definities per relatietype (flow draagt protocol/impact; association rol).
    assert "protocol" in rels["flow"]["kenmerk_definitie"]
    assert "impact_bij_verbreking" in rels["flow"]["kenmerk_definitie"]
    assert "relatie_rol" in rels["association"]["kenmerk_definitie"]
    assert rels["composition"]["kenmerk_definitie"] == {}


def test_dekkingstest_elk_componenttype_heeft_mapping():
    """Besluit 4: elk actief componenttype draagt een volledige ArchiMate-mapping.

    ADR-026 Besluit 2: de toegestane sets komen uit de gedeelde bron (`archimate_typing`),
    niet uit een inline kopie."""
    from services.archimate_typing import (
        TOEGESTANE_ASPECTEN,
        TOEGESTANE_ELEMENTEN,
        TOEGESTANE_LAGEN,
    )
    from services.seed_componentconfig import bouw_componentconfig

    for r in bouw_componentconfig():
        if r["dimensie"].value == "componenttype" and r["actief"]:
            assert r["archimate_element"] in TOEGESTANE_ELEMENTEN, r["optie_sleutel"]
            assert r["laag"] in TOEGESTANE_LAGEN, r["optie_sleutel"]
            assert r["aspect"] in TOEGESTANE_ASPECTEN, r["optie_sleutel"]


def test_ok3_resterende_type_mappings():
    from services.seed_componentconfig import bouw_componentconfig

    mapping = {
        r["optie_sleutel"]: r["archimate_element"]
        for r in bouw_componentconfig() if r["dimensie"].value == "componenttype"
    }
    assert mapping["client_software"] == "system_software"
    # LI060 — middleware → integratievoorziening (system_software, technology-band: eigen ESB/broker);
    # applicatieserver → server_compute (node).
    assert mapping["integratievoorziening"] == "system_software"
    assert mapping["applicatie"] == "application_component"
    assert mapping["server_compute"] == "node"
    assert mapping["database"] == "system_software"
    assert mapping["fileshare"] == "node"
    assert mapping["landelijke_voorziening"] == "application_service"  # LI060 — nieuw type
    assert mapping["saas_dienst"] == "application_component"


# ── Live: element-RLS-isolatie ───────────────────────────────────────────────────

_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


def _element_tabel_bestaat() -> bool:
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                res = (await c.execute(text("SELECT to_regclass('element')"))).scalar()
            return res is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


live = pytest.mark.skipif(
    not _element_tabel_bestaat(), reason="element-tabel niet bereikbaar (migratie 0011 niet toegepast)"
)

_TENANT_A = "11111111-1111-1111-1111-111111111111"
_TENANT_B = "22222222-2222-2222-2222-222222222222"


@live
def test_element_rls_isolatie():
    from app.core import tenant_context as tc
    from app.core.database import _markeer_rls
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from models.models import Element, ElementType

    naam_id = uuid.uuid4()

    async def _run():
        eng = create_async_engine(_LK_APP_URL)
        smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        try:
            tok = tc.zet_tenant_context(_TENANT_A)
            atok = tc.zet_audit_context("system:dev_seed")
            try:
                async with smf() as s:
                    _markeer_rls(s)
                    s.add(Element(id=naam_id, tenant_id=uuid.UUID(_TENANT_A),
                                  element_type=ElementType.component))
                    await s.commit()
            finally:
                tc.reset_audit_context(atok); tc.reset_tenant_context(tok)

            tok = tc.zet_tenant_context(_TENANT_B)
            try:
                async with smf() as s:
                    _markeer_rls(s)
                    zicht_b = (await s.execute(
                        text("SELECT count(*) FROM element WHERE id = :i"), {"i": str(naam_id)}
                    )).scalar()
            finally:
                tc.reset_tenant_context(tok)

            tok = tc.zet_tenant_context(_TENANT_A)
            try:
                async with smf() as s:
                    _markeer_rls(s)
                    zicht_a = (await s.execute(
                        text("SELECT count(*) FROM element WHERE id = :i"), {"i": str(naam_id)}
                    )).scalar()
                    await s.execute(text("DELETE FROM element WHERE id = :i"), {"i": str(naam_id)})
                    await s.commit()
            finally:
                tc.reset_tenant_context(tok)
            return zicht_b, zicht_a
        finally:
            await eng.dispose()

    zicht_b, zicht_a = asyncio.run(_run())
    assert zicht_b == 0 and zicht_a == 1
