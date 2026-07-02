"""Tests — UX-B6-b: eigenaar-organisatie (applicatie/component) als verwijzing naar een organisatie-partij.

Live (skip-if-no-DB): eigenaar zetten levert de naam in read (component én applicatie); aard ≠
organisatie ⇒ 422; applicatie-lijst filtert op eigenaar_organisatie_id; ON DELETE SET NULL bij
verwijderen van de organisatie-partij zet alléén de verwijzing op null (tenant_id intact, geen 409).
De aard-validatie zelf is offline geborgd in `test_gebruikersgroep_b6a` (gedeelde helper).
"""
import asyncio
import uuid

import pytest

import app.core.audit  # noqa: F401
import app.core.database  # noqa: F401
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


def _db_bereikbaar() -> bool:
    import asyncio as _a

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
        return _a.run(_probe())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar (offline)")


async def _run_rls(fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tok = zet_tenant_context(_TID)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_tenant_context(tok)
        await eng.dispose()


async def _maak_partij(s, tid, naam, aard):
    from models.models import Element, ElementType, Partij

    elem = Element(tenant_id=tid, element_type=ElementType.partij)
    s.add(elem); await s.flush()
    s.add(Partij(id=elem.id, tenant_id=tid, aard=aard, naam=naam))
    await s.flush()
    return elem.id


@integratie
def test_eigenaar_organisatie_component_en_applicatie_live():
    from sqlalchemy import text as _text

    from models.models import PartijAard
    from schemas.component import ComponentCreate
    from schemas.component import ComponentCreate
    from services import component_service
    from services.errors import OngeldigeRegistratie

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            org_id = await _maak_partij(s, tid, "WT-B6b-Org", PartijAard.organisatie)
            ext_id = await _maak_partij(s, tid, "WT-B6b-Extern", PartijAard.externe_partij)
            await s.commit(); ids += [org_id, ext_id]

            # Applicatie: eigenaar-organisatie zetten → read levert de naam (transient attribuut).
            app = await component_service.maak_aan(
                s, tid, ComponentCreate(componenttype="applicatie", naam="WT-B6b-App", hostingmodel="saas",
                                         eigenaar_organisatie_id=org_id, migratiepad="onbekend",
                                         complexiteit="midden", prioriteit="midden"),
            )
            ids.append(app["id"])
            assert app["eigenaar_organisatie_id"] == org_id
            assert app["eigenaar_organisatie_naam"] == "WT-B6b-Org"

            # Component (niet-applicatie): idem via _lees.
            comp = await component_service.maak_aan(
                s, tid, ComponentCreate(naam="WT-B6b-Comp", componenttype="database",
                                        eigenaar_organisatie_id=org_id),
            )
            ids.append(comp["id"])
            assert comp["eigenaar_organisatie_id"] == org_id
            assert comp["eigenaar_organisatie_naam"] == "WT-B6b-Org"

            # aard ≠ organisatie ⇒ 422 (zowel component- als applicatie-pad).
            for maak in (
                lambda: component_service.maak_aan(
                    s, tid, ComponentCreate(naam="x", componenttype="database", eigenaar_organisatie_id=ext_id)),
                lambda: component_service.maak_aan(
                    s, tid, ComponentCreate(componenttype="applicatie", naam="x", hostingmodel="saas", eigenaar_organisatie_id=ext_id,
                                             migratiepad="onbekend", complexiteit="midden", prioriteit="midden")),
            ):
                try:
                    await maak()
                    raise AssertionError("verwachtte OngeldigeRegistratie")
                except OngeldigeRegistratie as e:
                    assert e.code == "ONGELDIGE_ORGANISATIE"
                await s.rollback()

            # Applicatie-lijst filtert op eigenaar_organisatie_id.
            gefilterd, _ = await component_service.lijst(s, _TID, eigenaar_organisatie_id=org_id, limit=100)
            assert any(a["id"] == app["id"] for a in gefilterd)

            # ON DELETE SET NULL: verwijder de organisatie → verwijzingen worden null, tenant_id intact.
            app_id = app["id"]
            await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(org_id)})
            await s.commit()
            # Beide componenten (kaal component én applicatie-component) → FK null, tenant_id intact.
            for cid in (comp["id"], app_id):
                rij = (await s.execute(_text(
                    "SELECT eigenaar_organisatie_id, tenant_id FROM component WHERE id=:i"), {"i": str(cid)})).first()
                assert rij[0] is None and str(rij[1]) == _TID
            return True
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_run_rls(_flow)) is True
