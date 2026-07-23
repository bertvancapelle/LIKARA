"""Tests — een uitgezette vraag bestaat voor de beoordeling niet (LI050, besluit Bert).

Regel: het antwoord van een uitgezette vraag telt niet mee, en het knelpunt dat eruit
voortkwam telt niet mee — zolang de vraag uit staat. Er wordt NIETS gewist of opgelost;
weer aanzetten draait alles vanzelf terug.

Borging in twee lagen:
1. **Bronscan (offline):** de afleiding leeft op ÉÉN plek (`services/actieve_vraag.py`);
   elke tellende/tonende consument gebruikt de helper en bouwt geen eigen actief-filter.
2. **Live flow (skip-if-offline):** de bijt-test — zichtbare vragen onbeantwoord + antwoord
   op een uitgezette vraag ⇒ NIET klaar; knelpunt van een uitgezette vraag blokkeert niet en
   verdwijnt uit lijst + open-punten; omkeerbaar; niets gewist.
"""
import asyncio
import pathlib
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_LK_ADMIN_URL = "postgresql+asyncpg://lk_admin:changeme_dev@localhost:5432/likara"
_TYPE = "client_software"  # wegwerp-type (default niet checklist-dragend)

_SERVICES = pathlib.Path(__file__).resolve().parents[1] / "services"


def _db_bereikbaar() -> bool:
    async def _check():
        eng = create_async_engine(_LK_APP_URL)
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


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar (offline)")


async def _app_sessie_run(fn):
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


async def _admin_exec(sql: str, params: dict | None = None, *, fetch: bool = False):
    eng = create_async_engine(_LK_ADMIN_URL)
    try:
        async with eng.begin() as c:
            res = await c.execute(text(sql), params or {})
            return res.first() if fetch else None
    finally:
        await eng.dispose()


# ── 1. Bronscan: één afleiding, geen tweede actief-filter per consument ──────────

_CONSUMENTEN = {
    "lifecycle_service.py": ("score_telt_mee", "blokkade_telt_mee"),
    "component_open_punten_service.py": ("score_telt_mee",),
    "dashboard_service.py": ("blokkade_telt_mee",),
    "landschapskaart_service.py": ("blokkade_telt_mee",),
    "blokkade_service.py": ("blokkade_telt_mee",),
}


def test_elke_consument_gebruikt_de_gedeelde_afleiding():
    """Tellen én tonen komen uit `actieve_vraag.py` — een consument die de helper mist
    is precies de stille tegenspraak tussen twee schermen die de regel verbiedt."""
    for bestand, helpers in _CONSUMENTEN.items():
        bron = (_SERVICES / bestand).read_text()
        assert "from services import actieve_vraag" in bron, f"{bestand}: helper-import ontbreekt"
        for h in helpers:
            assert f"actieve_vraag.{h}" in bron, f"{bestand}: {h} niet gebruikt"


def test_helper_is_puur_en_orm_vrij():
    """De bron is core-only (table/column) en puur lezend — zo kan óók de engine-naburige
    kaart-service hem dragen zonder zijn import-afwezigheidsborging te breken."""
    bron = (_SERVICES / "actieve_vraag.py").read_text()
    for verboden in ("session.", "commit", "flush", ".add(", ".delete(", "from models"):
        assert verboden not in bron, f"actieve_vraag.py bevat {verboden!r} — hoort puur te zijn"


def test_bijt_zelftest_consument_zonder_helper_faalt():
    """Zelftest van de bronscan: een nagebootste consument zónder helper wordt gevangen."""
    nep = "from sqlalchemy import select\n# telt scores zonder filter\n"
    assert "from services import actieve_vraag" not in nep  # de scan-conditie bijt


# ── 2. Live flow: de regel end-to-end, omkeerbaar, niets gewist ─────────────────


async def _lc(s, component_id) -> str:
    return (
        await s.execute(
            text("select lifecycle_status from component_profiel where id = :i"), {"i": component_id}
        )
    ).scalar_one()


@integratie
def test_uitgezette_vraag_telt_niet_mee_end_to_end():
    from schemas.checklistconfig import CategorieCreate, VraagCreate
    from schemas.checklistscore import ChecklistscoreCreate, ChecklistscoreUpdate
    from schemas.component import ComponentCreate
    from services import blokkade_service
    from services import checklistconfig_service as cc
    from services import checklistscore_service as score_svc
    from services import component_open_punten_service as open_punten_svc
    from services import component_service as comp

    sfx = uuid.uuid4().hex[:6]

    async def _flow(s):
        comp_ids = []
        try:
            c = await comp.maak_aan(s, _TID, ComponentCreate(naam=f"UV-{sfx}", componenttype=_TYPE))
            comp_ids.append(c["id"])
            await comp.start_beoordeling(s, _TID, c["id"])

            cat = await cc.maak_categorie(
                s, _TID, CategorieCreate(componenttype=_TYPE, naam=f"UV-cat-{sfx}", volgorde=1)
            )
            v1 = await cc.maak_vraag(
                s, _TID, VraagCreate(componenttype=_TYPE, vraag="zichtbare vraag", categorie_id=cat["id"])
            )
            v2 = await cc.maak_vraag(
                s, _TID, VraagCreate(componenttype=_TYPE, vraag="straks uitgezette vraag", categorie_id=cat["id"])
            )

            # Alleen V2 beantwoord: 1/2 → in_inventarisatie.
            s2 = await score_svc.maak_aan(
                s, _TID, ChecklistscoreCreate(component_id=c["id"], checklistvraag_id=v2["id"], score="ja")
            )
            assert await _lc(s, c["id"]) == "in_inventarisatie"

            # DE BIJT-TEST — V2 uitzetten: zichtbaar 1 vraag (V1) ONBEANTWOORD, maar er ligt
            # een antwoord op de uitgezette vraag. Oude telling: 1 antwoord ≥ 1 vraag ⇒
            # (vals) migratieklaar. De regel: het antwoord telt niet ⇒ in_inventarisatie.
            await cc.zet_actief(s, _TID, v2["id"], False)
            assert await _lc(s, c["id"]) == "in_inventarisatie", (
                "een antwoord op een uitgezette vraag telde mee — het systeem toont 'klaar' "
                "terwijl de zichtbare checklist onbeantwoord is"
            )
            # Niets gewist: het antwoord bestaat nog.
            n_scores = (
                await s.execute(
                    text("select count(*) from checklistscore where component_id = :i"), {"i": c["id"]}
                )
            ).scalar_one()
            assert n_scores == 1

            # Omkeerbaar: V2 weer aan + V1 beantwoorden → 2/2 → migratieklaar.
            await cc.zet_actief(s, _TID, v2["id"], True)
            await score_svc.maak_aan(
                s, _TID, ChecklistscoreCreate(component_id=c["id"], checklistvraag_id=v1["id"], score="ja")
            )
            assert await _lc(s, c["id"]) == "migratieklaar"

            # Knelpunt: V2 → nee ⇒ blokkade ⇒ geblokkeerd; lijst + open-punten tonen hem.
            await score_svc.werk_bij(s, _TID, s2.id, ChecklistscoreUpdate(score="nee"))
            assert await _lc(s, c["id"]) == "geblokkeerd"
            items, _ = await blokkade_service.lijst(s, _TID, component_id=c["id"])
            assert len(items) == 1
            uit = await open_punten_svc.open_punten(s, _TID, c["id"])
            assert any(p["soort"] == open_punten_svc.PUNT_CHECKLIST for p in uit["valt_op"]["punten"])

            # V2 uitzetten: het knelpunt telt niet mee (status), staat niet in de lijst en
            # niet in de open punten — maar bestaat nog als registratie (niet opgelost).
            await cc.zet_actief(s, _TID, v2["id"], False)
            assert await _lc(s, c["id"]) == "migratieklaar", (
                "een knelpunt van een uitgezette vraag hield het systeem geblokkeerd"
            )
            items, _ = await blokkade_service.lijst(s, _TID, component_id=c["id"])
            assert items == []
            uit = await open_punten_svc.open_punten(s, _TID, c["id"])
            assert not any(p["soort"] == open_punten_svc.PUNT_CHECKLIST for p in uit["valt_op"]["punten"])
            rij = (
                await s.execute(
                    text("select status from blokkade where component_id = :i"), {"i": c["id"]}
                )
            ).first()
            assert rij is not None and rij.status == "open"  # niet gewist, niet opgelost

            # Omkeerbaar: V2 weer aan → het knelpunt telt en toont weer.
            await cc.zet_actief(s, _TID, v2["id"], True)
            assert await _lc(s, c["id"]) == "geblokkeerd"
            items, _ = await blokkade_service.lijst(s, _TID, component_id=c["id"])
            assert len(items) == 1
        finally:
            for cid in comp_ids:
                # Via het element-supertype (cascade: profiel + scores + blokkades).
                await s.execute(text("delete from element where id = :i"), {"i": cid})
            await s.commit()

    async def _run():
        await _admin_exec(
            "UPDATE componentconfig_optie SET checklist_dragend = true "
            "WHERE dimensie = 'componenttype' AND optie_sleutel = :t",
            {"t": _TYPE},
        )
        try:
            await _app_sessie_run(_flow)
        finally:
            await _admin_exec("DELETE FROM checklistvraag WHERE componenttype = :t", {"t": _TYPE})
            await _admin_exec("DELETE FROM checklist_categorie WHERE componenttype = :t", {"t": _TYPE})
            await _admin_exec(
                "UPDATE componentconfig_optie SET checklist_dragend = false "
                "WHERE dimensie = 'componenttype' AND optie_sleutel = :t",
                {"t": _TYPE},
            )

    asyncio.run(_run())
