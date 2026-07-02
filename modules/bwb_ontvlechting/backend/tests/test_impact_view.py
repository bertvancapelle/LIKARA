"""Tests — opgeslagen & deelbare Impact-verkenner-views (ADR-033 slice 2).

Offline: schema-validatie (naam/selectie/serverbeheerde velden), engine-import-afwezigheid,
read-only bronscan-vrije guard, RBAC (eigen-beheer-patroon).
Live (skip-if-no-DB): aanmaken + selectie; lijst toont eigen + gedeelde, niet andermans privé;
ophalen/bewerken/verwijderen andermans (privé/niet-eigen) = 404 no-leak; dubbele naam per maker =
409; component verwijderen valt uit de selectie (cascade); view verwijderen ruimt de junctie op;
RLS-isolatie; audit op beide tabellen; en bewijs dat lifecycle/profiel ONgewijzigd blijft.
"""
import asyncio
import uuid

import pytest
from pydantic import ValidationError

import app.core.audit  # noqa: F401  (activeert de capture-hook)
import app.core.database  # noqa: F401
from app.core.tenant_context import (
    reset_audit_context,
    reset_tenant_context,
    zet_audit_context,
    zet_tenant_context,
)

_TID = "11111111-1111-1111-1111-111111111111"
_ANDER_TID = "22222222-2222-2222-2222-222222222222"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline: schema-validatie ────────────────────────────────────────────────────
def test_create_naam_en_selectie_verplicht():
    from schemas.impact_view import ImpactViewCreate

    cid = uuid.uuid4()
    ok = ImpactViewCreate(naam="Mijn view", component_ids=[cid])
    assert ok.gedeeld is False and ok.component_ids == [cid]
    for leeg in ("", "   "):
        with pytest.raises(ValidationError):
            ImpactViewCreate(naam=leeg, component_ids=[cid])
    with pytest.raises(ValidationError):  # lege selectie
        ImpactViewCreate(naam="X", component_ids=[])
    with pytest.raises(ValidationError):  # naam te lang
        ImpactViewCreate(naam="x" * 151, component_ids=[cid])


def test_create_dedupliceert_selectie_behoud_volgorde():
    from schemas.impact_view import ImpactViewCreate

    a, b = uuid.uuid4(), uuid.uuid4()
    assert ImpactViewCreate(naam="X", component_ids=[a, b, a]).component_ids == [a, b]


def test_create_geen_serverbeheerde_velden():
    from schemas.impact_view import ImpactViewCreate

    for veld in ("id", "tenant_id", "maker_sub", "maker_email", "created_at", "updated_at"):
        assert veld not in ImpactViewCreate.model_fields
    with pytest.raises(ValidationError):  # extra='forbid'
        ImpactViewCreate(naam="X", component_ids=[uuid.uuid4()], maker_sub="hack")


def test_update_partieel_en_lege_selectie_verboden():
    from schemas.impact_view import ImpactViewUpdate

    # Alle velden optioneel.
    ImpactViewUpdate()
    ImpactViewUpdate(naam="Nieuw")
    ImpactViewUpdate(gedeeld=True)
    with pytest.raises(ValidationError):  # meegestuurde, maar lege selectie
        ImpactViewUpdate(component_ids=[])


# ── Offline: engine onaangeroerd ─────────────────────────────────────────────────
def test_impact_view_service_raakt_engine_niet():
    import services.impact_view_service as s

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(s, naam), f"impact_view-service mag de engine niet importeren: {naam!r}"


# ── Offline: RBAC (eigen-beheer-patroon) ─────────────────────────────────────────
def test_impact_view_rbac_eigen_beheer():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    for rol in ("viewer", "medewerker", "beheerder", "auditor"):
        assert heeft_permissie([rol], Entiteit.IMPACT_VIEW, Actie.LEZEN)
    assert not heeft_permissie(["viewer"], Entiteit.IMPACT_VIEW, Actie.AANMAKEN)
    assert not heeft_permissie(["auditor"], Entiteit.IMPACT_VIEW, Actie.AANMAKEN)
    # Medewerker mag aanmaken én eigen view verwijderen (afwijking van het inhoud-sjabloon).
    assert heeft_permissie(["medewerker"], Entiteit.IMPACT_VIEW, Actie.AANMAKEN)
    assert heeft_permissie(["medewerker"], Entiteit.IMPACT_VIEW, Actie.WIJZIGEN)
    assert heeft_permissie(["medewerker"], Entiteit.IMPACT_VIEW, Actie.VERWIJDEREN)
    assert heeft_permissie(["beheerder"], Entiteit.IMPACT_VIEW, Actie.VERWIJDEREN)


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────
def _db_bereikbaar() -> bool:
    async def _probe():
        from sqlalchemy.ext.asyncio import create_async_engine

        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect():
                return True
        except Exception:
            return False
        finally:
            await eng.dispose()

    try:
        return asyncio.run(_probe())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar (offline)")


async def _run_rls(fn, tid=_TID, actor_sub="view:makerA"):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tok = zet_tenant_context(tid)
    audit_tok = zet_audit_context(actor_sub=actor_sub, actor_email=f"{actor_sub}@test", correlatie_id=None)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_audit_context(audit_tok)
        reset_tenant_context(tok)
        await eng.dispose()


async def _maak_app(s, tid, naam):
    from schemas.component import ComponentCreate
    from services import component_service

    app = await component_service.maak_aan(
        s, tid, ComponentCreate(componenttype="applicatie", naam=naam, hostingmodel="saas", migratiepad="onbekend",
                                 complexiteit="midden", prioriteit="midden"))
    return app["id"]


async def _wis(tid, view_ids, app_ids):
    from sqlalchemy import text as _text

    async def _op(s):
        for vid in view_ids:
            await s.execute(_text("DELETE FROM impact_view WHERE id=:i"), {"i": str(vid)})
        for aid in app_ids:
            await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(aid)})
        await s.commit()
    await _run_rls(_op, tid=tid)


@integratie
def test_view_aanmaken_selectie_audit_engine_live():
    """Aanmaken met selectie; audit op header + junctie; lifecycle ONgewijzigd."""
    from sqlalchemy import text as _text

    from schemas.impact_view import ImpactViewCreate
    from services import impact_view_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        app1 = await _maak_app(s, tid, "WT-IV-A1")
        app2 = await _maak_app(s, tid, "WT-IV-A2")
        lc_voor = (await s.execute(
            _text("SELECT lifecycle_status FROM component_profiel WHERE id=:i"), {"i": str(app1)})).scalar_one()

        v = await svc.maak_aan(s, tid, ImpactViewCreate(naam="Migratie Q3", component_ids=[app1, app2]))
        assert v.maker_sub == "view:makerA" and v.maker_email == "view:makerA@test"
        assert v.is_eigenaar is True and v.gedeeld is False
        assert set(v.component_ids) == {app1, app2}

        n_header = (await s.execute(_text(
            "SELECT count(*) FROM audit_log WHERE entiteit_type='impact_view' AND entiteit_id=:i"),
            {"i": str(v.id)})).scalar_one()
        n_junctie = (await s.execute(_text(
            "SELECT count(*) FROM audit_log WHERE entiteit_type='impact_view_component'"))).scalar_one()
        assert n_header >= 1 and n_junctie >= 2  # twee componenten toegevoegd

        lc_na = (await s.execute(
            _text("SELECT lifecycle_status FROM component_profiel WHERE id=:i"), {"i": str(app1)})).scalar_one()
        assert lc_na == lc_voor
        return v.id, [app1, app2]

    vid, apps = asyncio.run(_run_rls(_flow))
    asyncio.run(_wis(tid, [vid], apps))


@integratie
def test_view_lijst_eigen_en_gedeeld_niet_andermans_prive_live():
    """Maker B ziet z'n eigen privé-view + de gedeelde view van A, NIET A's privé-view."""
    from schemas.impact_view import ImpactViewCreate
    from services import impact_view_service as svc

    tid = uuid.UUID(_TID)

    async def _als_A(s):
        app = await _maak_app(s, tid, "WT-IV-shared")
        prive = await svc.maak_aan(s, tid, ImpactViewCreate(naam="A-prive", component_ids=[app]))
        gedeeld = await svc.maak_aan(s, tid, ImpactViewCreate(naam="A-gedeeld", component_ids=[app], gedeeld=True))
        return app, prive.id, gedeeld.id

    app, a_prive, a_gedeeld = asyncio.run(_run_rls(_als_A, actor_sub="view:makerA"))

    async def _als_B(s):
        app_b = await _maak_app(s, tid, "WT-IV-B")
        b_prive = await svc.maak_aan(s, tid, ImpactViewCreate(naam="B-prive", component_ids=[app_b]))
        namen = {v.naam for v in await svc.lijst(s, tid)}
        # is_eigenaar correct gezet op de gedeelde view van A (B is geen eigenaar).
        gedeeld_obj = next(v for v in await svc.lijst(s, tid) if v.naam == "A-gedeeld")
        return app_b, b_prive.id, namen, gedeeld_obj.is_eigenaar

    app_b, b_prive, namen, b_is_eigenaar_van_gedeeld = asyncio.run(_run_rls(_als_B, actor_sub="view:makerB"))
    try:
        assert "B-prive" in namen          # eigen privé
        assert "A-gedeeld" in namen        # gedeeld door A
        assert "A-prive" not in namen      # andermans privé → niet zichtbaar
        assert b_is_eigenaar_van_gedeeld is False
    finally:
        asyncio.run(_wis(tid, [a_prive, a_gedeeld, b_prive], [app, app_b]))


@integratie
def test_view_no_leak_404_op_andermans_prive_en_mutatie_live():
    """Ophalen/bewerken/verwijderen van andermans privé-view = 404 (no-leak)."""
    from schemas.impact_view import ImpactViewCreate, ImpactViewUpdate
    from services import impact_view_service as svc
    from services.errors import NietGevonden

    tid = uuid.UUID(_TID)

    async def _als_A(s):
        app = await _maak_app(s, tid, "WT-IV-noleak")
        v = await svc.maak_aan(s, tid, ImpactViewCreate(naam="A-geheim", component_ids=[app]))
        return app, v.id

    app, vid = asyncio.run(_run_rls(_als_A, actor_sub="view:makerA"))

    async def _als_B(s):
        with pytest.raises(NietGevonden):
            await svc.haal_op(s, tid, vid)
        with pytest.raises(NietGevonden):
            await svc.werk_bij(s, tid, vid, ImpactViewUpdate(naam="gekaapt"))
        with pytest.raises(NietGevonden):
            await svc.verwijder(s, tid, vid)

    try:
        asyncio.run(_run_rls(_als_B, actor_sub="view:makerB"))
    finally:
        asyncio.run(_wis(tid, [vid], [app]))


@integratie
def test_view_409_dubbele_naam_per_maker_live():
    from schemas.impact_view import ImpactViewCreate
    from services import impact_view_service as svc
    from services.errors import RegistratieConflict

    tid = uuid.UUID(_TID)

    async def _flow(s):
        app = await _maak_app(s, tid, "WT-IV-dup")
        v1 = await svc.maak_aan(s, tid, ImpactViewCreate(naam="Zelfde", component_ids=[app]))
        vid = v1.id  # vastleggen vóór de conflicterende create (de rollback expired het object anders)
        with pytest.raises(RegistratieConflict) as exc:
            await svc.maak_aan(s, tid, ImpactViewCreate(naam="Zelfde", component_ids=[app]))
        assert exc.value.code == "VIEW_NAAM_BESTAAT_AL"
        return app, vid

    app, vid = asyncio.run(_run_rls(_flow))
    asyncio.run(_wis(tid, [vid], [app]))


@integratie
def test_view_cascades_component_en_view_delete_live():
    """Component verwijderd ⇒ valt uit de selectie; view verwijderd ⇒ junctie opgeruimd."""
    from sqlalchemy import text as _text

    from schemas.impact_view import ImpactViewCreate
    from services import impact_view_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        app1 = await _maak_app(s, tid, "WT-IV-cas1")
        app2 = await _maak_app(s, tid, "WT-IV-cas2")
        v = await svc.maak_aan(s, tid, ImpactViewCreate(naam="Cascade", component_ids=[app1, app2]))

        # Component app1 verwijderen → junctie-rij cascadeert; view houdt alleen app2.
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(app1)})
        await s.commit()
        herladen = await svc.haal_op(s, tid, v.id)
        assert herladen.component_ids == [app2]

        # View verwijderen → junctie volledig opgeruimd.
        await svc.verwijder(s, tid, v.id)
        rest = (await s.execute(_text(
            "SELECT count(*) FROM impact_view_component WHERE view_id=:i"), {"i": str(v.id)})).scalar_one()
        assert rest == 0
        return [app2]  # app1 al weg

    apps = asyncio.run(_run_rls(_flow))
    asyncio.run(_wis(tid, [], apps))


@integratie
def test_view_rls_isolatie_live():
    """Een andere tenant ziet de view niet (RLS + expliciet tenant-filter)."""
    from schemas.impact_view import ImpactViewCreate
    from services import impact_view_service as svc

    tid = uuid.UUID(_TID)

    async def _maak(s):
        app = await _maak_app(s, tid, "WT-IV-rls")
        v = await svc.maak_aan(s, tid, ImpactViewCreate(naam="RLS", component_ids=[app], gedeeld=True))
        return app, v.id

    app, vid = asyncio.run(_run_rls(_maak, tid=_TID, actor_sub="view:makerA"))

    async def _ander(s):
        return len(await svc.lijst(s, uuid.UUID(_ANDER_TID)))

    try:
        # Gedeeld binnen tenant A, maar onzichtbaar voor tenant B (RLS-grens).
        assert asyncio.run(_run_rls(_ander, tid=_ANDER_TID, actor_sub="view:makerB")) == 0
    finally:
        asyncio.run(_wis(tid, [vid], [app]))
