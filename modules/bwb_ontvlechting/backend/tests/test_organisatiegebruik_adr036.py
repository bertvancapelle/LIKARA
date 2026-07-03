"""Tests — ADR-036 stap A: grof gebruiksfeit `organisatiegebruik` + gebruikersgroep-verfijning.

Offline:
- engine-onaangeroerd (import-afwezigheid): de service importeert geen engine-symbolen;
- `valideer_applicatie` accepteert een applicatie, weigert een niet-applicatie (422).

Live (skip-if-no-DB):
- los grof feit vastleggen (onvolledig = geldig) + duplicaat ⇒ 409 (uniciteit, geen dubbel feit);
- afdeling-mét-organisatie borgt automatisch het grove feit (get-or-create, geen dubbele invoer,
  geen dubbel opgeslagen organisatie) + verfijning-link + `heeft_verfijning`;
- organisatie-loze groep (`gebruik_id` NULL) blijft geldig;
- type-validaties: organisatie ≠ aard=organisatie ⇒ 422; doel ≠ applicatie ⇒ 422;
- engine niet geraakt: een grof feit / afdeling muteert geen `lifecycle_status`, maakt geen blokkade.
"""
import asyncio
import pathlib
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.core.audit  # noqa: F401
import app.core.database  # noqa: F401
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline: engine-onaangeroerd (import-afwezigheid) ────────────────────────────
def test_engine_niet_geimporteerd_in_organisatiegebruik_service():
    base = pathlib.Path(__file__).resolve().parents[1] / "services"
    verboden = ("lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
                "ComponentProfiel", "Blokkade", "Checklistscore")
    importregels = [
        r for r in (base / "organisatiegebruik_service.py").read_text(encoding="utf-8").splitlines()
        if r.lstrip().startswith(("import ", "from "))
    ]
    blob = "\n".join(importregels)
    for term in verboden:
        assert term not in blob, f"organisatiegebruik_service importeert onverwacht {term}"


# ── Offline: applicatie-typevalidatie ────────────────────────────────────────────
def _mock_session_met_componenttype(ct):
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncMock(spec=AsyncSession)
    res = MagicMock()
    res.scalar_one_or_none.return_value = ct
    session.execute.return_value = res
    return session


def test_valideer_applicatie_accepteert_applicatie():
    from services import organisatiegebruik_service as svc

    session = _mock_session_met_componenttype("applicatie")
    asyncio.run(svc.valideer_applicatie(session, uuid.uuid4(), uuid.uuid4()))  # geen exception


def test_valideer_applicatie_weigert_niet_applicatie():
    from services import organisatiegebruik_service as svc
    from services.errors import OngeldigeRegistratie

    session = _mock_session_met_componenttype("integratievoorziening")
    with pytest.raises(OngeldigeRegistratie) as ei:
        asyncio.run(svc.valideer_applicatie(session, uuid.uuid4(), uuid.uuid4()))
    assert ei.value.code == "ONGELDIGE_APPLICATIE"


def test_gebruikersgroep_heeft_geen_eigen_organisatie_kolom():
    """ADR-036 single source of truth: de organisatie leeft op het grove feit, niet op de groep."""
    from models.models import Gebruikersgroep

    assert not hasattr(Gebruikersgroep, "organisatie_id")
    assert hasattr(Gebruikersgroep, "gebruik_id")


def test_identiteit_afdeling_organisatie():
    """ADR-036 stap D — "afdeling — organisatie" met de drie terugvallen (pure helper)."""
    from services.gebruikersgroep_service import identiteit

    assert identiteit("Burgerzaken", "Tiel") == "Burgerzaken — Tiel"
    assert identiteit("Burgerzaken", None) == "Burgerzaken"       # org-loos → alleen afdeling
    assert identiteit(None, "Tiel") == "Tiel"                     # afdeling ontbreekt → organisatie
    assert identiteit("  ", "  ") == "Gebruikersgroep"            # geen van beide → generiek
    assert identiteit(None, None) == "Gebruikersgroep"


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


async def _maak_org(s, tid, naam, aard=None):
    from models.models import Element, ElementType, Partij, PartijAard

    elem = Element(tenant_id=tid, element_type=ElementType.partij)
    s.add(elem); await s.flush()
    s.add(Partij(id=elem.id, tenant_id=tid, aard=aard or PartijAard.organisatie, naam=naam))
    await s.flush()
    return elem.id


async def _maak_app(s, tid, naam="WT-OG-App"):
    from models.models import HostingModel, Migratiepad, NiveauEnum
    from services import component_service

    comp = await component_service.maak_applicatie_component(
        s, tid, naam=naam, beschrijving=None, hostingmodel=HostingModel.on_premise,
        eigenaar_organisatie_id=None,
        migratiepad=Migratiepad.onbekend, complexiteit=NiveauEnum.midden, prioriteit=NiveauEnum.midden,
    )
    return comp.id


async def _maak_niet_app(s, tid, naam="WT-OG-NietApp"):
    from models.models import Component, Element, ElementType

    elem = Element(tenant_id=tid, element_type=ElementType.component); s.add(elem); await s.flush()
    s.add(Component(id=elem.id, tenant_id=tid, naam=naam, componenttype="integratievoorziening",
                    hostingmodel="on_premise")); await s.flush()
    return elem.id


@integratie
def test_grof_feit_los_uniciteit_en_read_live():
    from sqlalchemy import text as _text

    from schemas.organisatiegebruik import OrganisatiegebruikCreate
    from services import organisatiegebruik_service as svc
    from services.errors import RegistratieConflict

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            org_id = await _maak_org(s, tid, "WT-OG-Org")
            app_id = await _maak_app(s, tid)
            await s.commit(); ids += [org_id, app_id]

            # Onvolledig = geldig: alleen organisatie + applicatie.
            feit = await svc.maak_aan(s, tid, OrganisatiegebruikCreate(organisatie_id=org_id, applicatie_id=app_id))
            assert feit["organisatie_id"] == org_id and feit["applicatie_id"] == app_id
            assert feit["organisatie_naam"] == "WT-OG-Org"
            assert feit["heeft_verfijning"] is False

            # Duplicaat (zelfde org, app) ⇒ 409, geen tweede rij.
            try:
                await svc.maak_aan(s, tid, OrganisatiegebruikCreate(organisatie_id=org_id, applicatie_id=app_id))
                raise AssertionError("verwachtte RegistratieConflict")
            except RegistratieConflict as e:
                assert e.code == "GEBRUIK_BESTAAT"
            await s.rollback()

            # Read per applicatie: precies één feit, org-naam gevuld, nog geen verfijning.
            lijst = await svc.lijst_voor_applicatie(s, tid, app_id)
            assert len(lijst) == 1 and lijst[0]["organisatie_naam"] == "WT-OG-Org"
            assert lijst[0]["heeft_verfijning"] is False
            return True
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_run_rls(_flow)) is True


@integratie
def test_afdeling_borgt_grof_feit_automatisch_live():
    """Een afdeling-mét-organisatie borgt het grove feit (get-or-create): geen dubbele org-invoer,
    geen dubbel feit, verfijning-link gelegd. Een tweede afdeling van dezelfde org hergebruikt het
    feit (één rij)."""
    from sqlalchemy import func, select
    from sqlalchemy import text as _text

    from models.models import Gebruikersgroep, Organisatiegebruik
    from schemas.gebruikersgroep import GebruikersgroepCreate
    from services import gebruikersgroep_service as gg
    from services import organisatiegebruik_service as og

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            org_id = await _maak_org(s, tid, "WT-OG-Org2")
            app_id = await _maak_app(s, tid, "WT-OG-App2")
            await s.commit(); ids += [org_id, app_id]

            # Afdeling + organisatie → grove feit ontstaat automatisch.
            g1 = await gg.maak_aan(s, tid, GebruikersgroepCreate(
                applicatie_id=app_id, organisatie_id=org_id, afdeling="Burgerzaken", aantal_gebruikers=40))
            ids.append(g1["id"])
            assert g1["organisatie_id"] == org_id and g1["organisatie_naam"] == "WT-OG-Org2"

            # Verfijning-link: de groep verwijst structureel naar het grove feit.
            gg_obj = await gg.haal_op(s, tid, g1["id"])
            assert gg_obj.gebruik_id is not None
            feiten = await og.lijst_voor_applicatie(s, tid, app_id)
            assert len(feiten) == 1 and feiten[0]["heeft_verfijning"] is True

            # Tweede afdeling van dezelfde organisatie → hergebruikt hetzelfde grove feit (geen duplicaat).
            g2 = await gg.maak_aan(s, tid, GebruikersgroepCreate(
                applicatie_id=app_id, organisatie_id=org_id, afdeling="Publiekszaken", aantal_gebruikers=25))
            ids.append(g2["id"])
            aantal = (await s.execute(
                select(func.count()).select_from(Organisatiegebruik).where(
                    Organisatiegebruik.tenant_id == tid,
                    Organisatiegebruik.organisatie_id == org_id,
                    Organisatiegebruik.applicatie_id == app_id))).scalar()
            assert aantal == 1, "afdeling-mét-organisatie mag het grove feit niet dupliceren"
            g2_obj = await gg.haal_op(s, tid, g2["id"])
            assert g2_obj.gebruik_id == gg_obj.gebruik_id  # beide verfijnen hetzelfde feit
            return True
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_run_rls(_flow)) is True


@integratie
def test_organisatie_loze_groep_blijft_geldig_live():
    from sqlalchemy import text as _text

    from schemas.gebruikersgroep import GebruikersgroepCreate
    from services import gebruikersgroep_service as gg

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            app_id = await _maak_app(s, tid, "WT-OG-App3")
            await s.commit(); ids.append(app_id)
            groep = await gg.maak_aan(s, tid, GebruikersgroepCreate(
                applicatie_id=app_id, organisatie_id=None, afdeling="Burgers", aantal_gebruikers=35000))
            ids.append(groep["id"])
            assert groep["organisatie_id"] is None and groep["organisatie_naam"] is None
            obj = await gg.haal_op(s, tid, groep["id"])
            assert obj.gebruik_id is None  # hangt onder géén grof feit
            return True
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_run_rls(_flow)) is True


@integratie
def test_type_validaties_live():
    from sqlalchemy import text as _text

    from models.models import PartijAard
    from schemas.organisatiegebruik import OrganisatiegebruikCreate
    from services import organisatiegebruik_service as svc
    from services.errors import OngeldigeRegistratie

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            org_id = await _maak_org(s, tid, "WT-OG-OrgT")
            ext_id = await _maak_org(s, tid, "WT-OG-Extern", aard=PartijAard.externe_partij)
            app_id = await _maak_app(s, tid, "WT-OG-AppT")
            niet_app = await _maak_niet_app(s, tid, "WT-OG-NietAppT")
            await s.commit(); ids += [org_id, ext_id, app_id, niet_app]

            # Organisatie ≠ aard=organisatie ⇒ 422 ONGELDIGE_ORGANISATIE.
            try:
                await svc.maak_aan(s, tid, OrganisatiegebruikCreate(organisatie_id=ext_id, applicatie_id=app_id))
                raise AssertionError("verwachtte ONGELDIGE_ORGANISATIE")
            except OngeldigeRegistratie as e:
                assert e.code == "ONGELDIGE_ORGANISATIE"
            await s.rollback()

            # Doel ≠ applicatie ⇒ 422 ONGELDIGE_APPLICATIE.
            try:
                await svc.maak_aan(s, tid, OrganisatiegebruikCreate(organisatie_id=org_id, applicatie_id=niet_app))
                raise AssertionError("verwachtte ONGELDIGE_APPLICATIE")
            except OngeldigeRegistratie as e:
                assert e.code == "ONGELDIGE_APPLICATIE"
            await s.rollback()
            return True
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_run_rls(_flow)) is True


@integratie
def test_grof_feit_en_afdeling_raken_engine_niet_live():
    """Live engine-borging: een grof feit + een afdeling muteren `lifecycle_status` niet en maken
    geen blokkade voor de applicatie."""
    from sqlalchemy import text as _text

    from schemas.gebruikersgroep import GebruikersgroepCreate
    from schemas.organisatiegebruik import OrganisatiegebruikCreate
    from services import gebruikersgroep_service as gg
    from services import organisatiegebruik_service as og

    tid = uuid.UUID(_TID)

    async def _status(s, app_id):
        return (await s.execute(
            _text("SELECT lifecycle_status FROM component_profiel WHERE id=:i"), {"i": str(app_id)}
        )).scalar_one_or_none()

    async def _blokkades(s, app_id):
        return (await s.execute(
            _text("SELECT count(*) FROM blokkade WHERE component_id=:i"), {"i": str(app_id)}
        )).scalar()

    async def _flow(s):
        ids = []
        try:
            org_id = await _maak_org(s, tid, "WT-OG-OrgE")
            app_id = await _maak_app(s, tid, "WT-OG-AppE")
            await s.commit(); ids += [org_id, app_id]
            voor_status = await _status(s, app_id)
            voor_blok = await _blokkades(s, app_id)

            await og.maak_aan(s, tid, OrganisatiegebruikCreate(organisatie_id=org_id, applicatie_id=app_id))
            g = await gg.maak_aan(s, tid, GebruikersgroepCreate(
                applicatie_id=app_id, organisatie_id=org_id, afdeling="Burgerzaken", aantal_gebruikers=10))
            ids.append(g["id"])

            assert await _status(s, app_id) == voor_status, "lifecycle_status mag niet muteren"
            assert await _blokkades(s, app_id) == voor_blok, "geen blokkade door registratief feit"
            return True
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_run_rls(_flow)) is True


@integratie
def test_kaart_gebruikt_door_grove_feiten_live():
    """ADR-036 stap B — "gebruikt door organisatie(s)" komt uit de grove feiten: grof-only verschijnt;
    een organisatie die zowel grof als via een afdeling bekend is telt één keer; een org-loze groep
    telt niet mee maar zet wél de organisatieloos-flag."""
    from sqlalchemy import text as _text

    from schemas.gebruikersgroep import GebruikersgroepCreate
    from services import gebruikersgroep_service as gg
    from services import landschapskaart_service as lk
    from services import organisatiegebruik_service as og

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            org1 = await _maak_org(s, tid, "WT-B-Org1")
            org2 = await _maak_org(s, tid, "WT-B-Org2")
            app_id = await _maak_app(s, tid, "WT-B-App")
            await s.commit(); ids += [org1, org2, app_id]

            # org1: zowel grof als via een afdeling; org2: grof-only; plus een org-loze groep.
            await og.ensure(s, tid, org1, app_id); await s.commit()
            g1 = await gg.maak_aan(s, tid, GebruikersgroepCreate(
                applicatie_id=app_id, organisatie_id=org1, afdeling="Burgerzaken", aantal_gebruikers=10))
            ids.append(g1["id"])
            await og.ensure(s, tid, org2, app_id); await s.commit()
            g_loos = await gg.maak_aan(s, tid, GebruikersgroepCreate(
                applicatie_id=app_id, organisatie_id=None, afdeling="Burgers", aantal_gebruikers=999))
            ids.append(g_loos["id"])

            graf = await lk.haal_grafdata_op(s, _TID)
            node = next((n for n in graf.nodes if n.id == app_id), None)
            assert node is not None
            # Elke organisatie precies één keer (org1 niet dubbel ondanks grof + afdeling).
            assert sorted(node.gebruikt_door_organisaties, key=str) == sorted([org1, org2], key=str)
            assert node.gebruikt_door_organisatieloos is True
            return True
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_run_rls(_flow)) is True


@integratie
def test_signaal_detaillering_ontbreekt_live():
    """ADR-036 stap C — het signaal vuurt op een grof feit zonder afdeling en dooft zodra een
    afdeling-mét-die-organisatie eronder hangt; aantal-onbekend triggert het NIET."""
    from sqlalchemy import text as _text

    from schemas.gebruikersgroep import GebruikersgroepCreate
    from services import gebruikersgroep_service as gg
    from services import organisatiegebruik_service as og
    from services import registratiegaten_service as rg

    tid = uuid.UUID(_TID)

    async def _mijn(s, app_id):
        rijen = await rg.gebruiksfeit_zonder_verfijning(s, tid)
        return [r for r in rijen if r["applicatie_id"] == app_id]

    async def _flow(s):
        ids = []
        try:
            org1 = await _maak_org(s, tid, "WT-C-Org1")
            org2 = await _maak_org(s, tid, "WT-C-Org2")
            app_id = await _maak_app(s, tid, "WT-C-App")
            await s.commit(); ids += [org1, org2, app_id]

            # Grof-only feit → vuurt (aandacht), label "app — org".
            await og.ensure(s, tid, org1, app_id); await s.commit()
            mijn = await _mijn(s, app_id)
            assert len(mijn) == 1 and mijn[0]["niveau"] == "aandacht"
            assert mijn[0]["naam"] == "WT-C-App — WT-C-Org1"

            # Afdeling-mét-organisatie ZONDER aantal → verfijning bestaat → signaal dooft; aantal-
            # onbekend triggert dus niet.
            g1 = await gg.maak_aan(s, tid, GebruikersgroepCreate(
                applicatie_id=app_id, organisatie_id=org1, afdeling="Burgerzaken", aantal_gebruikers=None))
            ids.append(g1["id"])
            assert await _mijn(s, app_id) == []

            # Tweede grof-only feit (org2) → vuurt weer, alleen voor org2.
            await og.ensure(s, tid, org2, app_id); await s.commit()
            mijn2 = await _mijn(s, app_id)
            assert len(mijn2) == 1 and mijn2[0]["naam"] == "WT-C-App — WT-C-Org2"
            return True
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_run_rls(_flow)) is True


# ── Invariant "afdeling-met-org ⟹ grof feit" (borgt de no-dubbeltelling van stap B) ──
@integratie
def test_afdeling_met_org_impliceert_grof_feit_live():
    """ADR-036 kern-invariant — elke gebruikersgroep MÉT organisatie (per ADR-036: `gebruik_id`
    gezet) én afdeling, die een applicatie bedient, heeft een grof gebruiksfeit voor (tenant,
    organisatie, bediende applicatie). Dat is exact wat `unie(grove feiten, groepen) ⊆ grove feiten`
    borgt: geen org-ful afdeling-groep valt buiten de grove feiten. Read-only scan over de geseede
    tenant; niet vacuously true (≥1 groep onderzocht)."""
    from sqlalchemy import and_, exists, func, select
    from sqlalchemy import text as _text  # noqa: F401 — consistent met de andere live-tests
    from sqlalchemy.orm import aliased

    from models.models import Gebruikersgroep, Organisatiegebruik, Relatie

    tid = uuid.UUID(_TID)
    og_ref = aliased(Organisatiegebruik)    # het feit waar de groep naar verwijst (via gebruik_id)
    og_serve = aliased(Organisatiegebruik)  # het feit voor (org, bediende applicatie)

    async def _flow(s):
        # Afdeling-met-org groepen (afdeling + gebruik_id gezet) die een applicatie bedienen; hun
        # organisatie = die van het feit; hun applicatie = de serving-bron.
        base = (
            select(
                Gebruikersgroep.id.label("gg_id"),
                og_ref.organisatie_id.label("org"),
                Relatie.bron_id.label("app"),
            )
            .join(og_ref, and_(og_ref.id == Gebruikersgroep.gebruik_id, og_ref.tenant_id == tid))
            .join(Relatie, and_(
                Relatie.doel_id == Gebruikersgroep.id, Relatie.relatietype == "serving",
                Relatie.tenant_id == tid,
            ))
            .where(
                Gebruikersgroep.tenant_id == tid,
                Gebruikersgroep.afdeling.isnot(None),
                Gebruikersgroep.gebruik_id.isnot(None),
            )
        ).subquery()

        onderzocht = (await s.execute(select(func.count()).select_from(base))).scalar()
        overtredingen = (
            await s.execute(
                select(func.count()).select_from(base).where(
                    ~exists(
                        select(og_serve.id).where(
                            og_serve.tenant_id == tid,
                            og_serve.organisatie_id == base.c.org,
                            og_serve.applicatie_id == base.c.app,
                        )
                    )
                )
            )
        ).scalar()
        return onderzocht, overtredingen

    onderzocht, overtredingen = asyncio.run(_run_rls(_flow))
    assert onderzocht >= 1, "scan is vacuously true — geen afdeling-met-org groepen in de seed"
    assert overtredingen == 0, f"{overtredingen} afdeling-met-org groep(en) zonder grof feit"


@integratie
def test_creatie_afdeling_met_org_borgt_grof_feit_live():
    """Gedragsborging (A): een afdeling-mét-organisatie aanmaken via het Pass 1-creatiepad borgt het
    grove feit voor (tenant, organisatie, DE bediende applicatie) — A==A'. Locks dat een refactor van
    `maak_aan`/`ensure` het feit niet naar een andere applicatie laat wijzen."""
    from sqlalchemy import and_, exists, select
    from sqlalchemy import text as _text

    from models.models import Organisatiegebruik
    from schemas.gebruikersgroep import GebruikersgroepCreate
    from services import gebruikersgroep_service as gg

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            org_id = await _maak_org(s, tid, "WT-INV-Org")
            app_id = await _maak_app(s, tid, "WT-INV-App")
            await s.commit(); ids += [org_id, app_id]

            g = await gg.maak_aan(s, tid, GebruikersgroepCreate(
                applicatie_id=app_id, organisatie_id=org_id, afdeling="Burgerzaken", aantal_gebruikers=12))
            ids.append(g["id"])

            # Een grof feit voor (tenant, organisatie, DE bediende applicatie) bestaat.
            feit_er = (await s.execute(
                select(exists(select(Organisatiegebruik.id).where(
                    Organisatiegebruik.tenant_id == tid,
                    Organisatiegebruik.organisatie_id == org_id,
                    Organisatiegebruik.applicatie_id == app_id,
                ))))).scalar()
            assert feit_er is True
            return True
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_run_rls(_flow)) is True
