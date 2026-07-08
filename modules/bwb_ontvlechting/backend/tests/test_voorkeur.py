"""Tests — persoonlijke gebruikersvoorkeuren (ADR-041 slice 1).

Offline: schema-guard (extra='forbid' + grootte), engine-import-afwezigheid, RBAC (eigen-scope: elke
tenant-rol beheert zijn eigen voorkeuren).
Live (skip-if-no-DB): upsert + teruglezen (eigen); upsert vervangt de vorige waarde; `sub`-isolatie
(een andere gebruiker ziet/raakt mijn voorkeur niet); tenant-isolatie; en bewijs dat een voorkeur-write
de lifecycle/`component_profiel` ONgewijzigd laat.
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
_SLEUTEL = "gebruikte_componenttypen"


# ── Offline: schema-guard ────────────────────────────────────────────────────────
def test_upsert_schema_extra_forbid_en_grootte():
    from schemas.voorkeur import MAX_WAARDE_BYTES, VoorkeurUpsert

    # Kleine, geldige waarde.
    ok = VoorkeurUpsert(waarde={"typen": ["applicatie", "database"]})
    assert ok.waarde["typen"] == ["applicatie", "database"]
    # extra='forbid' — geen andere velden (bv. een gesmokkelde `sub`).
    with pytest.raises(ValidationError):
        VoorkeurUpsert(waarde=1, sub="hack")
    # Grootte-guard: een te groot blob wordt geweigerd.
    with pytest.raises(ValidationError):
        VoorkeurUpsert(waarde={"x": "a" * (MAX_WAARDE_BYTES + 100)})


# ── Offline: engine onaangeroerd ─────────────────────────────────────────────────
def test_voorkeur_service_raakt_engine_niet():
    import services.voorkeur_service as s

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(s, naam), f"voorkeur_service mag de engine niet importeren: {naam!r}"


# ── Offline: RBAC — eigen-scope, elke tenant-rol beheert zijn eigen voorkeuren ────
def test_voorkeur_rbac_alle_rollen_eigen_beheer():
    from app.core.rbac import Actie, Entiteit, Rol, heeft_permissie

    assert Entiteit.GEBRUIKER_VOORKEUR.value == "gebruiker_voorkeur"
    # Élke tenant-rol mag zijn eigen voorkeuren lezen, zetten (aanmaken) en herroepen (verwijderen).
    for rol in (Rol.VIEWER, Rol.MEDEWERKER, Rol.BEHEERDER, Rol.AUDITOR):
        for actie in (Actie.LEZEN, Actie.AANMAKEN, Actie.WIJZIGEN, Actie.VERWIJDEREN):
            assert heeft_permissie([rol.value], Entiteit.GEBRUIKER_VOORKEUR, actie), f"{rol}/{actie}"


# ── Live-infra (skip-if-no-DB) ───────────────────────────────────────────────────
def _db_bereikbaar() -> bool:
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _probe():
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


async def _run_rls(fn, tid=_TID, actor_sub="pref:userA"):
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


async def _wis(sub, tid=_TID):
    from sqlalchemy import text as _text

    async def _op(s):
        await s.execute(
            _text("DELETE FROM gebruiker_voorkeur WHERE sub=:s"), {"s": sub}
        )
        await s.commit()
    await _run_rls(_op, tid=tid, actor_sub=sub)


@integratie
def test_voorkeur_upsert_teruglezen_en_vervangt_live():
    from sqlalchemy import text as _text

    from services import voorkeur_service as svc

    async def _flow(s):
        # Upsert #1.
        await svc.upsert(s, _TID, _SLEUTEL, {"typen": ["applicatie"]})
        eigen = await svc.lijst_eigen(s, _TID)
        assert any(v.voorkeur_sleutel == _SLEUTEL and v.waarde == {"typen": ["applicatie"]} for v in eigen)
        # Upsert #2 vervangt de waarde — precies één rij voor (sub, sleutel).
        await svc.upsert(s, _TID, _SLEUTEL, {"typen": ["applicatie", "database"]})
        eigen2 = [v for v in await svc.lijst_eigen(s, _TID) if v.voorkeur_sleutel == _SLEUTEL]
        assert len(eigen2) == 1 and eigen2[0].waarde == {"typen": ["applicatie", "database"]}
        # Engine onaangeroerd: een voorkeur-write raakt geen component_profiel-rijen.
        aantal = (await s.execute(_text("SELECT count(*) FROM component_profiel"))).scalar_one()
        await svc.upsert(s, _TID, _SLEUTEL, {"typen": ["applicatie"]})
        aantal2 = (await s.execute(_text("SELECT count(*) FROM component_profiel"))).scalar_one()
        assert aantal == aantal2

    try:
        asyncio.run(_run_rls(_flow, actor_sub="pref:userA"))
    finally:
        asyncio.run(_wis("pref:userA"))


@integratie
def test_voorkeur_sub_isolatie_live():
    from services import voorkeur_service as svc

    async def _als_a(s):
        await svc.upsert(s, _TID, _SLEUTEL, {"typen": ["applicatie"]})
        return [v.voorkeur_sleutel for v in await svc.lijst_eigen(s, _TID)]

    async def _als_b(s):
        # B ziet A's voorkeur niet.
        vroeg = await svc.lijst_eigen(s, _TID)
        b_ziet_a = any(v.sub == "pref:userA" for v in vroeg)
        # B zet zijn eigen (zelfde sleutel) → aparte rij; A blijft ongemoeid.
        await svc.upsert(s, _TID, _SLEUTEL, {"typen": ["koppelvlak"]})
        eigen_b = [v for v in await svc.lijst_eigen(s, _TID)]
        return b_ziet_a, [(v.sub, v.voorkeur_sleutel) for v in eigen_b]

    try:
        a_sleutels = asyncio.run(_run_rls(_als_a, actor_sub="pref:userA"))
        assert _SLEUTEL in a_sleutels
        b_ziet_a, b_eigen = asyncio.run(_run_rls(_als_b, actor_sub="pref:userB"))
        assert b_ziet_a is False
        assert b_eigen == [("pref:userB", _SLEUTEL)]  # B ziet uitsluitend zijn eigen rij
        # A ziet nog steeds alleen zijn eigen rij (niet die van B).
        a_na = asyncio.run(_run_rls(
            lambda s: svc.lijst_eigen(s, _TID), actor_sub="pref:userA"))
        assert [(v.sub, v.voorkeur_sleutel) for v in a_na] == [("pref:userA", _SLEUTEL)]
    finally:
        asyncio.run(_wis("pref:userA"))
        asyncio.run(_wis("pref:userB"))


@integratie
def test_voorkeur_tenant_isolatie_live():
    from services import voorkeur_service as svc

    async def _schrijf(s):
        await svc.upsert(s, _TID, _SLEUTEL, {"typen": ["applicatie"]})

    async def _lees_ander(s):
        return await svc.lijst_eigen(s, _ANDER_TID)

    try:
        asyncio.run(_run_rls(_schrijf, tid=_TID, actor_sub="pref:userA"))
        # Zelfde sub, andere tenant → RLS + tenant-filter: geen kruislekkage.
        ander = asyncio.run(_run_rls(_lees_ander, tid=_ANDER_TID, actor_sub="pref:userA"))
        assert ander == []
    finally:
        asyncio.run(_wis("pref:userA", tid=_TID))
