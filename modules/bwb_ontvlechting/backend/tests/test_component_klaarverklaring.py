"""Tests — component-klaarverklaring (ADR-027, componentniveau).

Offline: schema-validatie (verplichte reden, status-allowlist), engine-import-afwezigheid, RBAC.
Live (skip-if-no-DB): maak_aan (happy/404/409), symmetrische statuswissel, RLS-isolatie,
audit-record bij aanmaken én bij statuswissel, en bewijs dat lifecycle/profiel ONgewijzigd blijft.
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
_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"


# ── Offline: schema-validatie ────────────────────────────────────────────────────
def test_create_reden_verplicht():
    from schemas.component_klaarverklaring import KlaarverklaringCreate

    cid = uuid.uuid4()
    KlaarverklaringCreate(component_id=cid, reden="beoordeeld, akkoord")
    for leeg in ("", "   "):
        with pytest.raises(ValidationError):
            KlaarverklaringCreate(component_id=cid, reden=leeg)


def test_create_geen_categorie_meer():
    """ADR-027 ompak: de categorie-dimensie is vervallen (component-niveau)."""
    from schemas.component_klaarverklaring import KlaarverklaringCreate

    assert "categorie_nr" not in KlaarverklaringCreate.model_fields
    with pytest.raises(ValidationError):  # extra='forbid' weigert het oude veld
        KlaarverklaringCreate(component_id=uuid.uuid4(), categorie_nr=1, reden="x")


def test_statuswijzig_validatie():
    from schemas.component_klaarverklaring import KlaarverklaringStatusWijzig

    KlaarverklaringStatusWijzig(status="open", reden="heropend wegens nieuwe info")
    with pytest.raises(ValidationError):
        KlaarverklaringStatusWijzig(status="afgehandeld", reden="x")
    with pytest.raises(ValidationError):
        KlaarverklaringStatusWijzig(status="klaar", reden="  ")


def test_create_geen_serverbeheerde_velden():
    from schemas.component_klaarverklaring import KlaarverklaringCreate

    for veld in ("id", "tenant_id", "status", "verklaard_door", "verklaard_op", "created_at"):
        assert veld not in KlaarverklaringCreate.model_fields


# ── Offline: engine onaangeroerd ─────────────────────────────────────────────────
def test_klaarverklaring_service_raakt_engine_niet():
    import services.component_klaarverklaring_service as s

    for naam in (
        "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
        "ComponentProfiel", "Blokkade", "Checklistscore",
    ):
        assert not hasattr(s, naam), f"klaarverklaring-service mag de engine niet importeren: {naam!r}"


# ── Offline: RBAC (inhoud-patroon) ───────────────────────────────────────────────
def test_klaarverklaring_rbac_inhoud_patroon():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    assert heeft_permissie(["viewer"], Entiteit.KLAARVERKLARING, Actie.LEZEN)
    assert heeft_permissie(["medewerker"], Entiteit.KLAARVERKLARING, Actie.AANMAKEN)
    assert heeft_permissie(["medewerker"], Entiteit.KLAARVERKLARING, Actie.WIJZIGEN)
    assert not heeft_permissie(["medewerker"], Entiteit.KLAARVERKLARING, Actie.VERWIJDEREN)
    assert heeft_permissie(["beheerder"], Entiteit.KLAARVERKLARING, Actie.VERWIJDEREN)
    assert not heeft_permissie(["viewer"], Entiteit.KLAARVERKLARING, Actie.AANMAKEN)


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────
def _db_bereikbaar() -> bool:
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
        return asyncio.run(_probe())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="cd_app-DB niet bereikbaar (offline)")


async def _run_rls(fn, tid=_TID):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_CD_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tok = zet_tenant_context(tid)
    audit_tok = zet_audit_context(actor_sub="test:adr027", actor_email="adr027@test", correlatie_id=None)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_audit_context(audit_tok)
        reset_tenant_context(tok)
        await eng.dispose()


async def _maak_app(s, tid):
    from schemas.applicatie import ApplicatieCreate
    from services import applicatie_service

    app = await applicatie_service.maak_aan(
        s, tid, ApplicatieCreate(naam="WT-KV-App", hostingmodel="saas", migratiepad="onbekend",
                                 complexiteit="midden", prioriteit="midden"))
    return app.id


@integratie
def test_klaarverklaring_happy_statuswissel_audit_engine_live():
    """Happy aanmaak + symmetrische statuswissel + audit-historie + engine onaangeroerd."""
    from sqlalchemy import text as _text

    from services import component_klaarverklaring_service as svc
    from schemas.component_klaarverklaring import KlaarverklaringCreate, KlaarverklaringStatusWijzig

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            app_id = await _maak_app(s, tid)
            ids.append(app_id)
            lc_voor = (await s.execute(
                _text("SELECT lifecycle_status FROM component_profiel WHERE id=:i"), {"i": str(app_id)}
            )).scalar_one()

            obj = await svc.maak_aan(s, tid, KlaarverklaringCreate(
                component_id=app_id, reden="gecoördineerd en akkoord"))
            assert obj.status.value == "klaar"
            assert obj.verklaard_door and obj.verklaard_op is not None

            n_na_create = (await s.execute(_text(
                "SELECT count(*) FROM audit_log WHERE entiteit_type='component_klaarverklaring' "
                "AND entiteit_id=:i"), {"i": str(obj.id)})).scalar_one()
            assert n_na_create >= 1

            o2 = await svc.wijzig_status(s, tid, obj.id, KlaarverklaringStatusWijzig(
                status="open", reden="heropend: scope gewijzigd"))
            assert o2.status.value == "open" and o2.reden == "heropend: scope gewijzigd"
            o3 = await svc.wijzig_status(s, tid, obj.id, KlaarverklaringStatusWijzig(
                status="klaar", reden="opnieuw afgehandeld"))
            assert o3.status.value == "klaar"

            n_na_wissel = (await s.execute(_text(
                "SELECT count(*) FROM audit_log WHERE entiteit_type='component_klaarverklaring' "
                "AND entiteit_id=:i"), {"i": str(obj.id)})).scalar_one()
            assert n_na_wissel > n_na_create
            laatste = (await s.execute(_text(
                "SELECT wijziging::text FROM audit_log WHERE entiteit_type='component_klaarverklaring' "
                "AND entiteit_id=:i ORDER BY tijdstip DESC LIMIT 1"), {"i": str(obj.id)})).scalar_one()
            assert "reden" in laatste and "status" in laatste

            lc_na = (await s.execute(
                _text("SELECT lifecycle_status FROM component_profiel WHERE id=:i"), {"i": str(app_id)}
            )).scalar_one()
            assert lc_na == lc_voor
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_klaarverklaring_404_onbekende_component_live():
    from services import component_klaarverklaring_service as svc
    from services.errors import NietGevonden
    from schemas.component_klaarverklaring import KlaarverklaringCreate

    tid = uuid.UUID(_TID)

    async def _flow(s):
        with pytest.raises(NietGevonden):
            await svc.maak_aan(s, tid, KlaarverklaringCreate(component_id=uuid.uuid4(), reden="x"))

    asyncio.run(_run_rls(_flow))


@integratie
def test_klaarverklaring_409_dubbel_live():
    from sqlalchemy import text as _text

    from services import component_klaarverklaring_service as svc
    from services.errors import RegistratieConflict
    from schemas.component_klaarverklaring import KlaarverklaringCreate

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            app_id = await _maak_app(s, tid)
            ids.append(app_id)
            await svc.maak_aan(s, tid, KlaarverklaringCreate(component_id=app_id, reden="afgehandeld"))
            with pytest.raises(RegistratieConflict) as exc:
                await svc.maak_aan(s, tid, KlaarverklaringCreate(component_id=app_id, reden="nogmaals"))
            assert exc.value.code == "KLAARVERKLARING_BESTAAT_AL"
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_klaarverklaring_rls_isolatie_live():
    """Een andere tenant ziet de klaarverklaring niet (RLS + expliciet tenant-filter)."""
    from sqlalchemy import text as _text

    from services import component_klaarverklaring_service as svc
    from schemas.component_klaarverklaring import KlaarverklaringCreate

    tid = uuid.UUID(_TID)

    async def _maak(s):
        app_id = await _maak_app(s, tid)
        await svc.maak_aan(s, tid, KlaarverklaringCreate(component_id=app_id, reden="afgehandeld"))
        return app_id

    app_id = asyncio.run(_run_rls(_maak, tid=_TID))

    async def _ander(s):
        return len(await svc.lijst(s, uuid.UUID(_ANDER_TID), component_id=app_id))

    try:
        assert asyncio.run(_run_rls(_ander, tid=_ANDER_TID)) == 0
    finally:
        async def _op(s):
            await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(app_id)})
            await s.commit()
        asyncio.run(_run_rls(_op, tid=_TID))


@integratie
def test_slice3_dashboard_en_lijstfilter_live():
    """ADR-027 slice 3 — dashboard-tellingen + lijstfilter. Bewijst dat `klaar_verklaard`
    elke klaar-verklaring telt, terwijl `klaar_met_afwijking`/`afwijking=1` puur de
    lifecycle-join is (concept = afwijking; migratieklaar = géén afwijking). Engine ongemoeid:
    de lifecycle wordt test-only direct gezet om de READ-filter te toetsen (geen scoring)."""
    from sqlalchemy import text as _text

    from services import component_klaarverklaring_service as svc
    from services import component_service, dashboard_service
    from schemas.component_klaarverklaring import KlaarverklaringCreate

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            base = await dashboard_service.haal_dashboard(s, tid)
            app_id = await _maak_app(s, tid)  # start = concept (∉ {migratieklaar, geblokkeerd})
            ids.append(app_id)
            await svc.maak_aan(s, tid, KlaarverklaringCreate(component_id=app_id, reden="afgehandeld"))

            # Concept + klaar → telt in BEIDE (klaar_verklaard én afwijking).
            na = await dashboard_service.haal_dashboard(s, tid)
            assert na["klaar_verklaard"] == base["klaar_verklaard"] + 1
            assert na["klaar_met_afwijking"] == base["klaar_met_afwijking"] + 1

            async def _ids(**filters):
                items, _ = await component_service.lijst(s, tid, limit=100, **filters)
                return {str(i["id"]) for i in items}

            assert str(app_id) in await _ids(klaarverklaring="klaar")
            assert str(app_id) in await _ids(afwijking=True)

            # Lifecycle test-only op 'migratieklaar' (checklist compleet) → valt uit de afwijking,
            # blijft wél klaar verklaard.
            await s.execute(
                _text("UPDATE component_profiel SET lifecycle_status='migratieklaar' WHERE id=:i"),
                {"i": str(app_id)},
            )
            na2 = await dashboard_service.haal_dashboard(s, tid)
            assert na2["klaar_verklaard"] == base["klaar_verklaard"] + 1   # nog steeds klaar verklaard
            assert na2["klaar_met_afwijking"] == base["klaar_met_afwijking"]  # niet langer afwijking
            assert str(app_id) in await _ids(klaarverklaring="klaar")
            assert str(app_id) not in await _ids(afwijking=True)
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))


@integratie
def test_klaarverklaring_naam_resolutie_live():
    """ADR-029 Fase 3b: klaar verklaren stempelt sub+email; read resolveert sub→persoon.naam.
    Plus ongekoppelde (beheerder→email) en historische (sub=None→email) fallback. Engine ongemoeid."""
    from sqlalchemy import text as _text

    from models.models import GebruikerPersoon, PartijAard
    from schemas.partij import PartijCreate
    from schemas.component_klaarverklaring import KlaarverklaringCreate
    from services import actor_resolutie, partij_service
    from services import component_klaarverklaring_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            org = await partij_service.maak_aan(s, tid, PartijCreate(aard=PartijAard.organisatie, naam="ADR029-Org"))
            afd = await partij_service.maak_aan(s, tid, PartijCreate(
                aard=PartijAard.organisatie_eenheid, naam="ADR029-Afd", organisatie_id=org.id))
            persoon = await partij_service.maak_aan(s, tid, PartijCreate(
                aard=PartijAard.persoon, naam="Jan Resolutie", email="jan.res@org.test",
                organisatie_id=org.id, afdeling_id=afd.id))
            ids += [org.id, afd.id, persoon.id]
            # Koppel de harness-actor ("test:adr027") aan deze persoon.
            s.add(GebruikerPersoon(tenant_id=tid, keycloak_sub="test:adr027", persoon_id=persoon.id))
            await s.flush()

            app_id = await _maak_app(s, tid)
            ids.append(app_id)
            lc_voor = (await s.execute(
                _text("SELECT lifecycle_status FROM component_profiel WHERE id=:i"), {"i": str(app_id)})).scalar_one()

            kv = await svc.maak_aan(s, tid, KlaarverklaringCreate(component_id=app_id, reden="afgehandeld"))
            assert kv.verklaard_door_sub == "test:adr027"
            assert kv.verklaard_door == "adr027@test"            # e-mail-fallback bewaard
            assert kv.verklaard_door_naam == "Jan Resolutie"     # sub → persoon.naam

            # Ongekoppelde actor (beheerder) → e-mail; historische rij (geen sub) → e-mail.
            assert await actor_resolutie.resolveer_naam(s, tid, sub="kc-onbekend", email="beheerder@x") == "beheerder@x"
            assert await actor_resolutie.resolveer_naam(s, tid, sub=None, email="hist@x") == "hist@x"

            lc_na = (await s.execute(
                _text("SELECT lifecycle_status FROM component_profiel WHERE id=:i"), {"i": str(app_id)})).scalar_one()
            assert lc_na == lc_voor  # engine onaangeroerd
        finally:
            for eid in reversed(ids):  # leaf-first: app → persoon → afd → org (RESTRICT-FK's)
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    asyncio.run(_run_rls(_flow))
