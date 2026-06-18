"""Tests — Landschapskaart (ADR-025, read-only grafprojectie).

Offline: engine-import-afwezigheid + RBAC (ARCHITECTUUR.LEZEN, alleen-lezen).
Live (skip-if-no-DB): de volledige graaf met de vier ring-edge-types + lifecycle op een
applicatie-node, met structurele opruim.
"""
import asyncio
import uuid

import pytest

import app.core.audit  # noqa: F401
import app.core.database  # noqa: F401
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"


# ── Offline: engine onaangeroerd ─────────────────────────────────────────────────
def test_landschapskaart_service_raakt_engine_niet():
    import services.landschapskaart_service as s

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(s, naam), f"landschapskaart_service mag de engine niet importeren: {naam!r}"


def test_landschapskaart_geen_schrijfpad_in_bron():
    """Read-only: de servicebron bevat geen schrijf-operaties op de sessie."""
    import inspect

    import services.landschapskaart_service as s

    bron = inspect.getsource(s)
    for verboden in ("session.add(", "session.commit(", "session.flush(", "session.delete("):
        assert verboden not in bron, f"read-only service mag geen {verboden!r} bevatten"


# ── Offline: RBAC (ARCHITECTUUR.LEZEN, alleen-lezen) ─────────────────────────────
def test_landschapskaart_rbac_alleen_lezen():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    for rol in ("viewer", "medewerker", "beheerder", "auditor"):
        assert heeft_permissie([rol], Entiteit.ARCHITECTUUR, Actie.LEZEN)
    # Een rol zonder enige tenant-rol heeft geen leesrecht → route zou 403 geven.
    assert not heeft_permissie([], Entiteit.ARCHITECTUUR, Actie.LEZEN)


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────
def _db_bereikbaar() -> bool:
    import asyncio as _a

    async def _probe():
        from sqlalchemy.ext.asyncio import create_async_engine

        eng = create_async_engine(_CD_APP_URL)
        try:
            async with eng.connect():
                return True
        except Exception:
            return False
        finally:
            await eng.dispose()

    try:
        return _a.run(_probe())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="cd_app-DB niet bereikbaar (offline)")


async def _run_rls(fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_CD_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tok = zet_tenant_context(_TID)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_tenant_context(tok)
        await eng.dispose()


@integratie
def test_landschapskaart_graf_vier_ringen_en_lifecycle_live():
    from sqlalchemy import text as _text

    from models.models import (
        Contract, ContractType, Element, ElementType, HostingModel, Migratiepad,
        NiveauEnum, Partij, PartijAard, Relatie, RelatieKenmerkDimensie, Roltoewijzing,
    )
    from schemas.applicatie import ApplicatieCreate
    from schemas.component import ComponentCreate
    from services import applicatie_service, component_service, landschapskaart_service as svc
    from services import relatiekenmerk_catalog as rk

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            # Applicatie (krijgt een profiel → lifecycle_status) + een database-component.
            app = await applicatie_service.maak_aan(
                s, tid, ApplicatieCreate(
                    naam="WT-LK-App", hostingmodel="saas", migratiepad="onbekend",
                    complexiteit="midden", prioriteit="midden"))
            comp = await component_service.maak_aan(s, tid, ComponentCreate(naam="WT-LK-DB", componenttype="database"))
            app_id, comp_id = app.id, comp["id"]
            ids += [app_id, comp_id]

            # Organisatie-partij + contract (leverancier = de organisatie).
            oe = Element(tenant_id=tid, element_type=ElementType.partij); s.add(oe); await s.flush()
            s.add(Partij(id=oe.id, tenant_id=tid, aard=PartijAard.organisatie, naam="WT-LK-Org")); await s.flush()
            ce = Element(tenant_id=tid, element_type=ElementType.contract); s.add(ce); await s.flush()
            s.add(Contract(id=ce.id, tenant_id=tid, leverancier_id=oe.id,
                           contracttype=ContractType.los_contract, contractnaam="WT-LK-Contract"))
            await s.flush()

            # Vier ringen: flow (app→db), assignment (db host→app), association (app→contract),
            # roltoewijzing (org→app).
            s.add(Relatie(tenant_id=tid, bron_id=app_id, doel_id=comp_id, relatietype="flow"))
            s.add(Relatie(tenant_id=tid, bron_id=comp_id, doel_id=app_id, relatietype="assignment"))
            s.add(Relatie(tenant_id=tid, bron_id=app_id, doel_id=ce.id, relatietype="association"))
            rol = sorted(await rk.actieve_sleutels(s, RelatieKenmerkDimensie.beheerrol))[0]
            s.add(Roltoewijzing(tenant_id=tid, partij_id=oe.id, object_id=app_id, rol=rol))
            await s.commit()
            ids += [ce.id, oe.id]

            graf = await svc.haal_grafdata_op(s, _TID)
            return graf, app_id, comp_id, oe.id, ce.id
        finally:
            # Contract eerst (leverancier-RESTRICT), dan de rest.
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    graf, app_id, comp_id, org_id, contract_id = asyncio.run(_run_rls(_flow))

    node_per_id = {n.id: n for n in graf.nodes}
    # Nodes: applicatie met lifecycle, partij met soort, contract.
    assert node_per_id[app_id].element_type == "applicatie"
    assert node_per_id[app_id].lifecycle_status == "concept"   # uit component_profiel (read-only)
    assert node_per_id[org_id].element_type == "partij" and node_per_id[org_id].soort == "organisatie"
    assert node_per_id[org_id].laag == "business"
    assert node_per_id[contract_id].element_type == "contract"

    # Alle vier de ringen aanwezig in de edges (beperkt tot onze testrelaties).
    mijn_ids = {app_id, comp_id, org_id, contract_id}
    ringen = {e.ring for e in graf.edges if e.bron_id in mijn_ids and e.doel_id in mijn_ids}
    assert {"applicaties", "infrastructuur", "contracten", "beheerorganisatie"} <= ringen
    # De beheerorganisatie-edge draagt de rol-naam als label.
    beheer = [e for e in graf.edges if e.ring == "beheerorganisatie" and e.bron_id == org_id]
    assert beheer and beheer[0].label
