"""Tests — ADR-021 Fase E impactanalyse (CD056).

Offline-invariant (kruis-tenant 404) + live-integratie tegen de geseede cd_app-DB
(skip indien onbereikbaar): directe + transitieve afhankelijkheid met niveau/pad,
cyclus-terminatie (A↔B), lege impact, en de contracten-van-bron-context.
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

_TID = "11111111-1111-1111-1111-111111111111"
_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"


# ── Offline ─────────────────────────────────────────────────────────────────────

def test_impact_kruis_tenant_geeft_404():
    from services import component_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    res = MagicMock()
    res.scalar_one_or_none.return_value = None  # bron niet vindbaar binnen tenant
    session.execute.return_value = res

    with pytest.raises(NietGevonden):
        asyncio.run(svc.impact_analyse(session, _TID, uuid.uuid4()))


# ── Live-integratie (cd_app) ─────────────────────────────────────────────────────

import app.core.database  # noqa: E402,F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context  # noqa: E402


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


async def _sessie_run(fn):
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
def test_impact_directe_afhankelijkheid_seed():
    from sqlalchemy import text
    from services import component_service as svc

    async def _flow(s):
        row = (await s.execute(text("select id from component where naam='Oracle FIN-DB'"))).first()
        out = await svc.impact_analyse(s, _TID, row[0])
        namen = {g["naam"]: g for g in out["geraakt"]}
        # Belastingsysteem én Financieel draaien direct op de DB (niveau 1).
        assert {"Belastingsysteem", "Financieel"} <= set(namen)
        bs = namen["Belastingsysteem"]
        assert bs["niveau"] == 1
        assert bs["pad"] == ["Oracle FIN-DB", "Belastingsysteem"]
        assert bs["relatietype_label"]  # draait_op-label gevuld
        assert bs["lifecycle_status"] is not None  # applicatie-subtype → verrijkt
        assert bs["open_blokkades"] is not None and bs["open_blokkades"] >= 0
        assert out["samenvatting"]["aantal_geraakt"] >= 2
        assert out["samenvatting"]["aantal_applicaties"] >= 2
        assert isinstance(out["contracten"], list)  # contracten-van-bron context aanwezig

    asyncio.run(_sessie_run(_flow))


@integratie
def test_impact_transitief_en_cyclus_termineren():
    from sqlalchemy import text
    from schemas.component import ComponentCreate
    from schemas.component_structuur import ComponentStructuurCreate
    from services import component_service as svc
    from services import component_structuur_service as struct_svc

    sfx = uuid.uuid4().hex[:8]

    async def _flow(s):
        a = await svc.maak_aan(s, _TID, ComponentCreate(naam=f"CD056-A-{sfx}", componenttype="database"))
        b = await svc.maak_aan(s, _TID, ComponentCreate(naam=f"CD056-B-{sfx}", componenttype="database"))
        c = await svc.maak_aan(s, _TID, ComponentCreate(naam=f"CD056-C-{sfx}", componenttype="database"))
        ids = [a["id"], b["id"], c["id"]]
        try:
            # A draait_op B, B draait_op A (cyclus), C draait_op A.
            await struct_svc.maak_aan(s, _TID, ComponentStructuurCreate(component_id=a["id"], op_component_id=b["id"], relatietype="draait_op"))
            await struct_svc.maak_aan(s, _TID, ComponentStructuurCreate(component_id=b["id"], op_component_id=a["id"], relatietype="draait_op"))
            await struct_svc.maak_aan(s, _TID, ComponentStructuurCreate(component_id=c["id"], op_component_id=a["id"], relatietype="draait_op"))

            # impact(B): A direct (niveau 1), C transitief via A (niveau 2). Termineert
            # ondanks de A↔B-cyclus (B is de bron en wordt nooit opnieuw bezocht).
            out = await svc.impact_analyse(s, _TID, b["id"])
            namen = {g["naam"]: g for g in out["geraakt"]}
            assert set(namen) == {f"CD056-A-{sfx}", f"CD056-C-{sfx}"}  # B (bron) niet in de set
            assert namen[f"CD056-A-{sfx}"]["niveau"] == 1
            assert namen[f"CD056-C-{sfx}"]["niveau"] == 2
            assert namen[f"CD056-C-{sfx}"]["pad"] == [f"CD056-B-{sfx}", f"CD056-A-{sfx}", f"CD056-C-{sfx}"]
            # kale infra → geen applicatie-verrijking
            assert namen[f"CD056-A-{sfx}"]["lifecycle_status"] is None
            assert out["samenvatting"]["aantal_applicaties"] == 0

            # impact(C): niemand draait op C → lege impact.
            leeg = await svc.impact_analyse(s, _TID, c["id"])
            assert leeg["geraakt"] == []
            assert leeg["samenvatting"]["aantal_geraakt"] == 0
        finally:
            # Opruimen: eerst de structuurrelaties, dan de componenten (anders IN_GEBRUIK).
            await s.execute(text(
                "delete from component_structuur where component_id = any(:ids) or op_component_id = any(:ids)"
            ), {"ids": ids})
            await s.execute(text("delete from component where id = any(:ids)"), {"ids": ids})
            await s.commit()

    asyncio.run(_sessie_run(_flow))
