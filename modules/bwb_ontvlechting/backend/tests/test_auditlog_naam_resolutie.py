"""Tests — auditlog naam-verrijking + naam/actie-filter (ADR-029 Fase 3a).

Live (skip-if-no-DB): echte audit-rows ontstaan via de capture-hook bij een mutatie onder een
gezette audit-context (actor_sub/email). De read verrijkt met `actor_naam` (sub → persoon.naam,
e-mail-fallback) en filtert op naam-fragment (→ sub) + handeling. RBAC is al gedekt in
test_auditlog_routes.py. Uniek per run (uuid) → geen kruis-run-interferentie in het append-only spoor.
"""
import asyncio
import uuid

import pytest
from sqlalchemy import text as _text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import tenant_context as tc

_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"
_TID = "11111111-1111-1111-1111-111111111111"


def _db_bereikbaar() -> bool:
    async def _probe():
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


@integratie
def test_auditlog_naam_verrijking_en_filters():
    from app.core.database import _markeer_rls
    from models.models import GebruikerPersoon, PartijAard
    from schemas.applicatie import ApplicatieCreate
    from schemas.partij import PartijCreate
    from services import actor_resolutie, applicatie_service, partij_service
    from services import auditlog_service as svc

    tid = uuid.UUID(_TID)
    merk = uuid.uuid4().hex[:8]
    naam = f"Jan Audit {merk}"
    sub_gek = f"audit:jan:{merk}"
    sub_ong = f"audit:onbekend:{merk}"

    async def _flow():
        eng = create_async_engine(_CD_APP_URL)
        smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        t_tok = tc.zet_tenant_context(_TID)
        ids = []
        try:
            async with smf() as s:
                _markeer_rls(s)

                async def _muteer(sub, email, fn):
                    a = tc.zet_audit_context(sub, email)
                    try:
                        return await fn(s)
                    finally:
                        tc.reset_audit_context(a)

                # Persoon + koppeling (sub_gek → Jan); audit-context van deze setup is niet relevant.
                a0 = tc.zet_audit_context("test:setup", "setup@test")
                try:
                    org = await partij_service.maak_aan(s, tid, PartijCreate(aard=PartijAard.organisatie, naam=f"AudOrg-{merk}"))
                    persoon = await partij_service.maak_aan(s, tid, PartijCreate(
                        aard=PartijAard.persoon, naam=naam, email=f"jan.{merk}@org.test", organisatie_id=org.id))
                    s.add(GebruikerPersoon(tenant_id=tid, keycloak_sub=sub_gek, persoon_id=persoon.id))
                    await s.flush()
                finally:
                    tc.reset_audit_context(a0)
                ids += [org.id, persoon.id]

                # Mutatie als gekoppelde actor (→ audit-rows met sub_gek).
                app_gek = await _muteer(sub_gek, "jan.kc@org.test", lambda s2: applicatie_service.maak_aan(
                    s2, tid, ApplicatieCreate(naam=f"AudApp-gek-{merk}", hostingmodel="saas",
                                              migratiepad="onbekend", complexiteit="midden", prioriteit="midden")))
                # Mutatie als ongekoppelde actor (beheerder zonder persoon → e-mail-fallback).
                app_ong = await _muteer(sub_ong, "beheerder@audit", lambda s2: applicatie_service.maak_aan(
                    s2, tid, ApplicatieCreate(naam=f"AudApp-ong-{merk}", hostingmodel="saas",
                                              migratiepad="onbekend", complexiteit="midden", prioriteit="midden")))
                ids += [app_gek.id, app_ong.id]

                # (1+2) Verrijking: gekoppeld → persoon.naam; ongekoppeld → e-mail-fallback.
                gek, _ = await svc.lijst(s, tid, actor_naam=naam)
                assert gek and all(g["actor_naam"] == naam for g in gek)
                assert all(r.actor_naam == naam for g in gek for r in g["records"])

                ong, _ = await svc.lijst(s, tid, actor="" + sub_ong)
                assert ong and all(g["actor_naam"] == "beheerder@audit" for g in ong)  # geen koppeling → e-mail

                # (3) Naam-filter beperkt tot de gekoppelde actor; (4) geen match → leeg.
                assert all(r.actor_sub == sub_gek for g in gek for r in g["records"] if r.actor_sub)
                leeg, _ = await svc.lijst(s, tid, actor_naam=f"ZZZ-{merk}")
                assert leeg == []

                # (5) Actie-filter: 'create' levert deze aanmaak; 'delete' (nog niets verwijderd) niet.
                cre, _ = await svc.lijst(s, tid, actor_naam=naam, actie="create")
                assert cre
                dele, _ = await svc.lijst(s, tid, actor_naam=naam, actie="delete")
                assert dele == []

                # (6) N+1-vrij: één resolutie-query per lijst-aanroep, ongeacht #records.
                telling = {"n": 0}
                echt = actor_resolutie.resolveer_namen

                async def _tel(*a, **k):
                    telling["n"] += 1
                    return await echt(*a, **k)

                actor_resolutie.resolveer_namen = _tel
                try:
                    await svc.lijst(s, tid, actor_naam=naam)
                finally:
                    actor_resolutie.resolveer_namen = echt
                assert telling["n"] == 1
            return ids
        finally:
            # Domein opruimen (audit-rows zijn append-only en blijven; uniek merk → geen interferentie).
            async with smf() as s:
                _markeer_rls(s)
                a = tc.zet_audit_context("test:teardown", "teardown@test")
                try:
                    for eid in reversed(ids):
                        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
                    await s.commit()
                finally:
                    tc.reset_audit_context(a)
            tc.reset_tenant_context(t_tok)
            await eng.dispose()

    asyncio.run(_flow())
