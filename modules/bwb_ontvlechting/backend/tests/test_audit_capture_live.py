"""ADR-006 — audit-capture end-to-end (live lk_app/lk_platform-DB, skip indien onbereikbaar).

Vereist migratie `0010` (audit_log/platform_audit_log). Valideert wat de offline-grens
niet dekt: de capture-hook schrijft bij een echte flush, actor/correlatie/hash worden
gevuld, driver + afgeleide gevolgen delen één correlatie_id, de blokkade-classificatie
splitst (derive bij score-driver, update bij handmatige wissel), RLS-isolatie +
append-only (grant/trigger) gelden, en platform-mutaties landen in `platform_audit_log`
met een string-`entiteit_id`. Eigen engines (echte lk_app/lk_platform-URL), net als de
CD048-tests — de app-engines draaien in tests op dummy-settings. Append-only: testresidu
in de audit-tabellen is per ontwerp niet opruimbaar (de inhoud-entiteiten worden wél
opgeruimd).
"""
import asyncio
import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import tenant_context as tc
from app.core.audit import verifieer_keten
from app.core.database import _markeer_rls

_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_LK_PLATFORM_URL = "postgresql+asyncpg://lk_platform:changeme_dev@localhost:5432/likara"
DEV_TENANT = "11111111-1111-1111-1111-111111111111"
TENANT_B = "22222222-2222-2222-2222-222222222222"


def _audit_log_bestaat() -> bool:
    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                # to_regclass = catalogus-lookup (geen rij-toegang) → omzeilt FORCE RLS;
                # een directe SELECT op audit_log zou zonder tenant-context op de
                # RLS-policy stuklopen en de tests ten onrechte skippen.
                res = (await c.execute(text("SELECT to_regclass('audit_log')"))).scalar()
            return res is not None
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


live = pytest.mark.skipif(
    not _audit_log_bestaat(),
    reason="audit_log niet bereikbaar (offline of migratie 0010 niet toegepast)",
)


@asynccontextmanager
async def _worker(tenant, actor="system:dev_seed"):
    """Tenant-RLS-sessie op de echte lk_app-DB + tenant/audit-context (zoals
    get_worker_session, maar op een eigen engine)."""
    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    t_tok = tc.zet_tenant_context(tenant)
    a_tok = tc.zet_audit_context(actor)
    try:
        async with smf() as s:
            _markeer_rls(s)
            try:
                yield s
            except Exception:
                await s.rollback()
                raise
    finally:
        tc.reset_audit_context(a_tok)
        tc.reset_tenant_context(t_tok)
        await eng.dispose()


@asynccontextmanager
async def _platform(actor="system:platform_init"):
    """Platform-sessie (lk_platform, GEEN RLS-marker) + audit-context → de hook
    routeert naar platform_audit_log."""
    eng = create_async_engine(_LK_PLATFORM_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    a_tok = tc.zet_audit_context(actor)
    try:
        async with smf() as s:
            yield s
    finally:
        tc.reset_audit_context(a_tok)
        await eng.dispose()


@live
def test_capture_create_actor_hash_en_correlatie():
    # ADR-024 slice 1: sample tenant-entiteit is nu een element-backed partij.
    from models.models import AuditLog, Element, ElementType, Partij, PartijAard, PartijScope

    naam = f"AUDIT-LEV-{uuid.uuid4().hex[:8]}"

    async def _run():
        async with _worker(DEV_TENANT) as s:
            corr = tc.huidige_correlatie_id()
            elem = Element(tenant_id=uuid.UUID(DEV_TENANT), element_type=ElementType.partij)
            s.add(elem)
            await s.flush()
            s.add(Partij(id=elem.id, tenant_id=uuid.UUID(DEV_TENANT),
                         aard=PartijAard.externe_partij, naam=naam, scope=PartijScope.extern))
            await s.commit()
            rows = (await s.execute(
                select(AuditLog).where(AuditLog.correlatie_id == uuid.UUID(corr))
            )).scalars().all()
            await s.execute(
                text("DELETE FROM element WHERE id IN (SELECT id FROM partij WHERE naam = :n)"),
                {"n": naam},
            )
            await s.commit()
            return rows

    rows = asyncio.run(_run())
    lev_rows = [r for r in rows if r.entiteit_type == "partij"]
    assert len(lev_rows) == 1
    r = lev_rows[0]
    assert r.actie == "create"
    assert r.actor_sub == "system:dev_seed"
    assert r.record_hash and len(r.record_hash) == 64
    assert r.wijziging and r.wijziging["naam"]["nieuw"] == naam


@live
def test_score_write_driver_plus_afgeleide_delen_correlatie():
    """Besluit 1/3: een blokkerende score-write die de vragenset compleet maakt ⇒ driver
    (checklistscore=create) + afgeleide gevolgen (blokkade + component_profiel = derive),
    één gedeeld correlatie_id en dezelfde actor.

    Self-contained op het `applicatie`-type (89 tenant-vragen, geseed): 88×ja in een aparte
    setup-transactie + de 89e score `nee` in de gemeten transactie maakt de set compleet mét
    één open blokkade ⇒ lifecycle → geblokkeerd, dus die laatste score-write raakt
    score(create) + blokkade(derive) + component_profiel(derive) in één transactie.
    (LI022 — herijkt op de verrijkte seed: `client_software` is daar niet langer
    checklist-dragend; `applicatie` is het enige dragende type. Elke `_worker` krijgt een
    verse correlatie-id, dus de 88-ja-setup lekt niet in de gemeten correlatie.)"""
    from models.models import AuditLog, ChecklistVraag
    from schemas.component import ComponentCreate
    from schemas.checklistscore import ChecklistscoreCreate
    from services import component_service, checklistscore_service

    naam = f"AUDIT-SRV-{uuid.uuid4().hex[:8]}"

    async def _run():
        app_id = None
        try:
            async with _worker(DEV_TENANT) as s:
                app = await component_service.maak_aan(
                    s, DEV_TENANT,
                    ComponentCreate(componenttype="applicatie", naam=naam, hostingmodel="saas",
                                     migratiepad=None, complexiteit="midden", prioriteit="midden"),
                )
                app_id = app["id"]
                await component_service.start_beoordeling(s, DEV_TENANT, app_id)
                vraag_ids = [
                    r for (r,) in (await s.execute(
                        select(ChecklistVraag.id)
                        .where(ChecklistVraag.componenttype == "applicatie")
                        .order_by(ChecklistVraag.code)
                    )).all()
                ]
            # 88×ja in een eigen transactie (eigen correlatie); de laatste vraag blijft
            # ongescoord tot de gemeten transactie hieronder.
            async with _worker(DEV_TENANT) as s:
                for vid in vraag_ids[:-1]:
                    await checklistscore_service.maak_aan(
                        s, DEV_TENANT,
                        ChecklistscoreCreate(component_id=app_id, checklistvraag_id=vid, score="ja"),
                    )
            # Gemeten transactie: de 89e score (nee) maakt de set compleet mét één open
            # blokkade ⇒ score(create) + blokkade(derive) + component_profiel(derive).
            async with _worker(DEV_TENANT) as s:
                corr = tc.huidige_correlatie_id()
                await checklistscore_service.maak_aan(
                    s, DEV_TENANT,
                    ChecklistscoreCreate(component_id=app_id, checklistvraag_id=vraag_ids[-1], score="nee"),
                )
                rows = (await s.execute(
                    select(AuditLog).where(AuditLog.correlatie_id == uuid.UUID(corr))
                    .order_by(AuditLog.tijdstip)
                )).scalars().all()
            return rows
        finally:
            # Opruimen draait ALTIJD (ook bij een exception vóór dit punt): element-delete
            # cascadeert naar applicatie + score/blokkade/profiel, zodat een gefaalde run geen
            # wees-element achterlaat.
            if app_id is not None:
                async with _worker(DEV_TENANT) as s:
                    await s.execute(text("DELETE FROM element WHERE id = :i"), {"i": str(app_id)})
                    await s.commit()

    rows = asyncio.run(_run())
    per_type: dict = {}
    for r in rows:
        per_type.setdefault(r.entiteit_type, set()).add(r.actie)
    assert "create" in per_type["checklistscore"]
    assert per_type["blokkade"] == {"derive"}
    assert per_type["component_profiel"] == {"derive"}
    assert len({r.correlatie_id for r in rows}) == 1
    assert {r.actor_sub for r in rows} == {"system:dev_seed"}


@live
def test_handmatige_blokkade_wissel_is_update_zonder_score_driver():
    """v3-splitsing: een zelfstandige handmatige blokkade-wissel (open→in_behandeling)
    zónder score-driver in dezelfde transactie ⇒ actie=`update` (geen `derive`)."""
    from models.models import AuditLog, Blokkade, BlokkadeStatus, ChecklistVraag
    from schemas.component import ComponentCreate
    from schemas.blokkade import BlokkadeUpdate
    from schemas.checklistscore import ChecklistscoreCreate
    from services import component_service, blokkade_service, checklistscore_service

    naam = f"AUDIT-BLK-{uuid.uuid4().hex[:8]}"

    async def _run():
        async with _worker(DEV_TENANT) as s:
            app = await component_service.maak_aan(
                s, DEV_TENANT,
                ComponentCreate(componenttype="applicatie", naam=naam, hostingmodel="saas",
                                 migratiepad=None, complexiteit="midden", prioriteit="midden"),
            )
            app_id = app["id"]
            await component_service.start_beoordeling(s, DEV_TENANT, app_id)
            vraag_id = (await s.execute(
                select(ChecklistVraag.id).where(ChecklistVraag.componenttype == "applicatie").limit(1)
            )).scalar_one()
        async with _worker(DEV_TENANT) as s:
            await checklistscore_service.maak_aan(
                s, DEV_TENANT,
                ChecklistscoreCreate(component_id=app_id, checklistvraag_id=vraag_id, score="nee"),
            )
            blok_id = (await s.execute(
                select(Blokkade.id).where(Blokkade.component_id == app_id)
            )).scalar_one()
        async with _worker(DEV_TENANT) as s:
            corr = tc.huidige_correlatie_id()
            await blokkade_service.werk_bij(
                s, DEV_TENANT, blok_id, BlokkadeUpdate(status=BlokkadeStatus.in_behandeling)
            )
            rows = (await s.execute(
                select(AuditLog).where(AuditLog.correlatie_id == uuid.UUID(corr),
                                       AuditLog.entiteit_type == "blokkade")
            )).scalars().all()
        async with _worker(DEV_TENANT) as s:
            await s.execute(text("DELETE FROM element WHERE id = :i"), {"i": str(app_id)})
            await s.commit()
        return rows

    rows = asyncio.run(_run())
    assert len(rows) == 1
    assert rows[0].actie == "update"  # handmatig, geen derive
    assert rows[0].wijziging and "status" in rows[0].wijziging


@live
def test_rls_isolatie_auditlog():
    """Tenant B ziet de audit-rijen van tenant A niet."""
    from models.models import AuditLog, Element, ElementType, Partij, PartijAard, PartijScope

    naam = f"AUDIT-RLS-{uuid.uuid4().hex[:8]}"

    async def _run():
        async with _worker(DEV_TENANT) as s:
            elem = Element(tenant_id=uuid.UUID(DEV_TENANT), element_type=ElementType.partij)
            s.add(elem)
            await s.flush()
            s.add(Partij(id=elem.id, tenant_id=uuid.UUID(DEV_TENANT),
                         aard=PartijAard.externe_partij, naam=naam, scope=PartijScope.extern))
            await s.commit()
        async with _worker(TENANT_B) as s:
            n_b = (await s.execute(
                select(AuditLog).where(AuditLog.entiteit_type == "partij",
                                       AuditLog.wijziging["naam"]["nieuw"].astext == naam)
            )).scalars().all()
        async with _worker(DEV_TENANT) as s:
            n_a = (await s.execute(
                select(AuditLog).where(AuditLog.entiteit_type == "partij",
                                       AuditLog.wijziging["naam"]["nieuw"].astext == naam)
            )).scalars().all()
            await s.execute(
                text("DELETE FROM element WHERE id IN (SELECT id FROM partij WHERE naam = :n)"),
                {"n": naam},
            )
            await s.commit()
        return len(n_b), len(n_a)

    n_b, n_a = asyncio.run(_run())
    assert n_b == 0 and n_a >= 1


@live
def test_append_only_grant_en_trigger_weigeren_mutatie():
    """lk_app mag audit_log niet UPDATE/DELETE/TRUNCATE (grant) en de trigger blokkeert
    UPDATE/DELETE bovendien — alle werpen een fout."""
    async def _probeer(sql):
        async with _worker(DEV_TENANT) as s:
            await s.execute(text(sql))
            await s.commit()

    for sql in ("UPDATE audit_log SET actor_sub = 'x'",
                "DELETE FROM audit_log",
                "TRUNCATE audit_log"):
        with pytest.raises(Exception):
            asyncio.run(_probeer(sql))


@live
def test_keten_verifieert_over_echte_rijen():
    """De per-tenant keten (op tijdstip-volgorde) verifieert intact via verifieer_keten."""
    from models.models import AuditLog

    async def _run():
        async with _worker(DEV_TENANT) as s:
            rows = (await s.execute(
                select(AuditLog).order_by(AuditLog.tijdstip, AuditLog.id)
            )).scalars().all()
            return [
                {
                    "tijdstip": r.tijdstip, "actor_sub": r.actor_sub,
                    "actor_email": r.actor_email, "entiteit_type": r.entiteit_type,
                    "entiteit_id": r.entiteit_id, "actie": r.actie,
                    "wijziging": r.wijziging, "correlatie_id": r.correlatie_id,
                    "tenant_id": r.tenant_id, "record_hash": r.record_hash,
                    "vorige_hash": r.vorige_hash,
                }
                for r in rows
            ]

    records = asyncio.run(_run())
    if not records:
        pytest.skip("geen audit-rijen aanwezig")
    ok, idx = verifieer_keten(records)
    assert ok is True, f"ketenbreuk bij index {idx}"


@live
def test_gelijktijdige_appends_blijven_lineair_geen_fork():
    """v4: meerdere gelijktijdige audit-appends binnen één tenant serialiseren via de
    per-tenant advisory lock tot een LINEAIRE keten — geen twee records ankeren op
    dezelfde voorganger (geen fork); de keten blijft groen verifiëren."""
    from models.models import AuditLog, Element, ElementType, Partij, PartijAard, PartijScope

    prefix = f"AUDIT-CONC-{uuid.uuid4().hex[:8]}"
    K = 5

    async def _een(i):
        async with _worker(DEV_TENANT) as s:
            elem = Element(tenant_id=uuid.UUID(DEV_TENANT), element_type=ElementType.partij)
            s.add(elem)
            await s.flush()
            s.add(Partij(id=elem.id, tenant_id=uuid.UUID(DEV_TENANT),
                         aard=PartijAard.externe_partij, naam=f"{prefix}-{i}", scope=PartijScope.extern))
            await s.commit()

    async def _run():
        await asyncio.gather(*[_een(i) for i in range(K)])
        async with _worker(DEV_TENANT) as s:
            batch = (await s.execute(
                select(AuditLog).where(
                    AuditLog.entiteit_type == "partij",
                    AuditLog.wijziging["naam"]["nieuw"].astext.like(prefix + "%"),
                )
            )).scalars().all()
            keten = (await s.execute(
                select(AuditLog).order_by(AuditLog.tijdstip, AuditLog.id)
            )).scalars().all()
            await s.execute(
                text("DELETE FROM element WHERE id IN (SELECT id FROM partij WHERE naam LIKE :p)"),
                {"p": prefix + "%"},
            )
            await s.commit()
            return batch, keten

    batch, keten = asyncio.run(_run())
    assert len(batch) == K
    # Geen fork: alle voorganger-verwijzingen zijn uniek (geen twee records op dezelfde
    # `vorige_hash`).
    vorige = [r.vorige_hash for r in batch]
    assert len(set(vorige)) == K, f"fork gedetecteerd: dubbele vorige_hash in {vorige}"
    # ADR-024: de element-backed dubbel-write schrijft per insert twee auditrecords
    # (element + partij), dus de partij-records zijn niet meer aaneengesloten. De
    # echte garantie is fork-vrijheid over de HELE keten: geen twee records ankeren op
    # dezelfde voorganger (lineair, niet vertakt) — strenger dan de batch-only check,
    # want dit dekt óók de element-records. Genesis (NULL vorige_hash) telt niet mee.
    keten_vorige = [r.vorige_hash for r in keten if r.vorige_hash is not None]
    assert len(set(keten_vorige)) == len(keten_vorige), "fork in de keten: dubbele vorige_hash"
    # Volledige tenant-keten blijft intact.
    records = [
        {
            "tijdstip": r.tijdstip, "actor_sub": r.actor_sub, "actor_email": r.actor_email,
            "entiteit_type": r.entiteit_type, "entiteit_id": r.entiteit_id, "actie": r.actie,
            "wijziging": r.wijziging, "correlatie_id": r.correlatie_id, "tenant_id": r.tenant_id,
            "record_hash": r.record_hash, "vorige_hash": r.vorige_hash,
        }
        for r in keten
    ]
    ok, idx = verifieer_keten(records)
    assert ok is True, f"ketenbreuk bij index {idx}"


@live
def test_platform_mutatie_naar_platform_audit_log_met_string_id():
    """Een ORM-mutatie op de platform-catalogus (int-PK) → platform_audit_log met
    `entiteit_id` als string."""
    from app.models.platform import PlatformAuditLog
    from models.models import ComponentConfigOptie

    async def _run():
        async with _platform("system:platform_init") as s:
            optie = (await s.execute(select(ComponentConfigOptie).limit(1))).scalar_one()
            optie_id = optie.id
            oud_label = optie.label
            optie.label = oud_label + " (audit-test)"
            await s.commit()
            optie.label = oud_label  # terugzetten (tweede audit-rij)
            await s.commit()
            rows = (await s.execute(
                select(PlatformAuditLog).where(
                    PlatformAuditLog.entiteit_type == "componentconfig_optie",
                    PlatformAuditLog.entiteit_id == str(optie_id),
                )
            )).scalars().all()
            return rows, optie_id

    rows, optie_id = asyncio.run(_run())
    assert len(rows) >= 1
    assert rows[0].entiteit_id == str(optie_id)  # text, niet uuid
    assert rows[0].actor_sub == "system:platform_init"
