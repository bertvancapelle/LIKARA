"""Tests — vraagevolutie snede 1 (ADR-056, aangescherpt LI051).

De regel: een beheerder mag de vraagstelling wijzigen; wat er dan gebeurt hangt aan
zíjn keuze (verduidelijking | wijziging), nooit aan een tekst-heuristiek. Een echte
wijziging laat bestaande antwoorden als verouderd lezen (vergelijking bevroren ↔
huidig, besluit 4) zónder ook maar íéts aan de beoordeling te veranderen (besluit
11 + invariant); opnieuw antwoorden ís de bevestiging (besluit 8, LI051).

Borging in twee lagen:
1. **Offline:** schema + service-randen (aard verplicht bij tekstwijziging; aard
   zonder wijziging geweigerd) + de pure vergelijking (`_zet_vraag_gewijzigd`).
2. **Live flow (skip-if-offline) — de bijt-test:** echte wijziging ⇒ antwoord leest
   als verouderd én de lifecycle-status verandert NIET; opnieuw antwoorden dooft het
   sein en de toelichting blijft; verduidelijking ⇒ géén sein maar wél de stille
   notitie, die dooft bij aanraken; het tabbladgetal telt beide soorten werk.
"""
import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_LK_ADMIN_URL = "postgresql+asyncpg://lk_admin:changeme_dev@localhost:5432/likara"
_TYPE = "client_software"  # wegwerp-type (default niet checklist-dragend)


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


async def _admin_exec(sql: str, params: dict | None = None):
    eng = create_async_engine(_LK_ADMIN_URL)
    try:
        async with eng.begin() as c:
            await c.execute(text(sql), params or {})
    finally:
        await eng.dispose()


# ── 1. Offline: schema + service-randen ─────────────────────────────────────────


def test_vraagupdate_kent_wijzigingsaard():
    from schemas.checklistconfig import VraagUpdate, WijzigingsAard

    upd = VraagUpdate(vraag="Nieuwe tekst?", wijzigingsaard="wijziging")
    assert upd.wijzigingsaard is WijzigingsAard.wijziging
    with pytest.raises(Exception):
        VraagUpdate(vraag="x", wijzigingsaard="iets_anders")  # gesloten lijst


def _result(waarde):
    r = MagicMock()
    r.scalar_one_or_none.return_value = waarde
    return r


def _vraag_ns(tekst="Oude tekst?"):
    return SimpleNamespace(
        id=uuid.uuid4(), tenant_id=uuid.UUID(_TID), componenttype=_TYPE,
        vraag=tekst, categorie_id=uuid.uuid4(), laatste_wijzigingsaard=None,
    )


def test_tekstwijziging_zonder_aard_geweigerd():
    """Besluit 2 — LIKARA leidt de aard nooit af; zonder keuze geen tekstwijziging."""
    from schemas.checklistconfig import VraagUpdate
    from services import checklistconfig_service as cc
    from services.errors import OngeldigeRegistratie

    session = AsyncMock()
    session.execute.return_value = _result(_vraag_ns())
    with pytest.raises(OngeldigeRegistratie) as exc:
        asyncio.run(cc.werk_vraag_bij(session, uuid.uuid4(), VraagUpdate(vraag="Nieuwe tekst?")))
    assert exc.value.code == "WIJZIGINGSAARD_VEREIST"


def test_aard_zonder_tekstwijziging_geweigerd():
    """Een aard zonder wijziging is een uitspraak over niets — luid weigeren, niet stil slikken."""
    from schemas.checklistconfig import VraagUpdate
    from services import checklistconfig_service as cc
    from services.errors import OngeldigeRegistratie

    vraag = _vraag_ns("Zelfde tekst?")
    session = AsyncMock()
    session.execute.return_value = _result(vraag)
    with pytest.raises(OngeldigeRegistratie) as exc:
        asyncio.run(
            cc.werk_vraag_bij(
                session, uuid.uuid4(),
                VraagUpdate(vraag="Zelfde tekst?", wijzigingsaard="verduidelijking"),
            )
        )
    assert exc.value.code == "GEEN_TEKSTWIJZIGING"


def test_vergelijking_is_het_sein():
    """Besluit 4 — 'verouderd' is een vergelijking, geen opgeslagen markering."""
    from services.checklistscore_service import _zet_vraag_gewijzigd

    obj = SimpleNamespace(vraag_bevroren="Wat was de vraag?")
    _zet_vraag_gewijzigd(obj, "Wat was de vraag?")
    assert obj.vraag_gewijzigd is False  # gelijk ⇒ geen sein
    _zet_vraag_gewijzigd(obj, "Wat is de vraag nu?")
    assert obj.vraag_gewijzigd is True  # afwijkend ⇒ sein
    _zet_vraag_gewijzigd(obj, None)
    assert obj.vraag_gewijzigd is False  # onbekende vraag ⇒ nooit een vals sein


# ── 2. Live flow — de bijt-test (skip-if-offline) ───────────────────────────────


async def _lc(s, component_id) -> str:
    return (
        await s.execute(
            text("select lifecycle_status from component_profiel where id = :i"), {"i": component_id}
        )
    ).scalar_one()


@integratie
def test_vraagevolutie_end_to_end():
    from schemas.checklistconfig import CategorieCreate, VraagCreate, VraagUpdate
    from schemas.checklistscore import ChecklistscoreCreate, ChecklistscoreUpdate
    from schemas.component import ComponentCreate
    from services import checklistconfig_service as cc
    from services import checklistscore_service as score_svc
    from services import component_open_punten_service as open_punten_svc
    from services import component_service as comp

    sfx = uuid.uuid4().hex[:6]

    async def _flow(s):
        comp_ids = []
        try:
            c = await comp.maak_aan(s, _TID, ComponentCreate(naam=f"VE-{sfx}", componenttype=_TYPE))
            comp_ids.append(c["id"])
            await comp.start_beoordeling(s, _TID, c["id"])

            cat = await cc.maak_categorie(
                s, _TID, CategorieCreate(componenttype=_TYPE, naam=f"VE-cat-{sfx}", volgorde=1)
            )
            v1 = await cc.maak_vraag(
                s, _TID, VraagCreate(componenttype=_TYPE, vraag="Is de koppeling gedocumenteerd?", categorie_id=cat["id"])
            )
            v2 = await cc.maak_vraag(
                s, _TID, VraagCreate(componenttype=_TYPE, vraag="Is de licentie overdraagbaar?", categorie_id=cat["id"])
            )

            # Beide beantwoord (mét toelichting op s1) → migratieklaar; bevroren = de tekst van nu.
            s1 = await score_svc.maak_aan(
                s, _TID, ChecklistscoreCreate(
                    component_id=c["id"], checklistvraag_id=v1["id"], score="ja",
                    bevinding="Zelf geschreven toelichting.",
                )
            )
            s2 = await score_svc.maak_aan(
                s, _TID, ChecklistscoreCreate(component_id=c["id"], checklistvraag_id=v2["id"], score="ja")
            )
            assert await _lc(s, c["id"]) == "migratieklaar"
            assert s1.vraag_bevroren == "Is de koppeling gedocumenteerd?"
            assert s1.vraag_gewijzigd is False

            # ── DE BIJT-TEST (besluit 7 + 11): een ECHTE wijziging laat het antwoord als
            # verouderd lezen én verandert het component NIET van status. ──
            await cc.werk_vraag_bij(
                s, v1["id"],
                VraagUpdate(vraag="Is de koppeling actueel gedocumenteerd?", wijzigingsaard="wijziging"),
            )
            r1 = await score_svc.lees_detail(s, _TID, s1.id)
            assert r1.vraag_gewijzigd is True, (
                "na een echte wijziging hoort het antwoord als verouderd te lezen"
            )
            assert r1.vraag_bevroren == "Is de koppeling gedocumenteerd?"  # bevroren blijft staan
            assert r1.score.value == "ja"  # de score is niet geleegd (invariant)
            assert await _lc(s, c["id"]) == "migratieklaar", (
                "één herformulering mag geen enkel component van status laten veranderen"
            )
            # De keuze is als kolom op de vraag geland (audit-drager, besluit 2).
            aard = (
                await s.execute(
                    text("select laatste_wijzigingsaard from checklistvraag where id = :i"),
                    {"i": v1["id"]},
                )
            ).scalar_one()
            assert aard == "wijziging"

            # Open punten: het sein telt in blok 3 én in het tabbladgetal (besluit 10) —
            # beide soorten werk, maar nooit in "dit moet nog" (invariant).
            uit = await open_punten_svc.open_punten(s, _TID, c["id"])
            punt = next(
                p for p in uit["valt_op"]["punten"]
                if p["soort"] == open_punten_svc.PUNT_VRAAG_GEWIJZIGD
            )
            assert punt["aantal"] == 1
            assert uit["tabblad_aantal"] == uit["moet_nog"]["aantal"] + 1
            assert not any(
                p.get("soort") == open_punten_svc.PUNT_VRAAG_GEWIJZIGD
                for p in uit["moet_nog"]["punten"]
            )

            # Alleen een velden-bewerking (toelichting) is AANRAKEN, geen opnieuw antwoorden:
            # het sein blijft staan (besluit 8 — alleen een nieuw antwoord dooft het).
            r1 = await score_svc.werk_bij(
                s, _TID, s1.id, ChecklistscoreUpdate(actie="Nog eens nakijken.")
            )
            assert r1.vraag_gewijzigd is True

            # Opnieuw antwoorden (zelfde keuze mag) ⇒ het sein dooft; de toelichting staat er nog.
            r1 = await score_svc.werk_bij(s, _TID, s1.id, ChecklistscoreUpdate(score="ja"))
            assert r1.vraag_gewijzigd is False
            assert r1.vraag_bevroren == "Is de koppeling actueel gedocumenteerd?"
            assert r1.bevinding == "Zelf geschreven toelichting."  # toelichting bewaard
            uit = await open_punten_svc.open_punten(s, _TID, c["id"])
            assert uit["tabblad_aantal"] == uit["moet_nog"]["aantal"]  # werk is weg

            # ── Verduidelijking (besluit 6): géén sein, wél de stille notitie; de bevroren
            # tekst schuift mee. Aanraken (élke bewerking) dooft de notitie. ──
            await cc.werk_vraag_bij(
                s, v2["id"],
                VraagUpdate(vraag="Is de licentie overdraagbaar bij ontvlechting?", wijzigingsaard="verduidelijking"),
            )
            r2 = await score_svc.lees_detail(s, _TID, s2.id)
            assert r2.vraag_gewijzigd is False, "een verduidelijking is geen sein"
            assert r2.vraag_bevroren == "Is de licentie overdraagbaar bij ontvlechting?"
            assert r2.vraag_verduidelijkt_op is not None  # de stille notitie
            assert await _lc(s, c["id"]) == "migratieklaar"

            r2 = await score_svc.werk_bij(
                s, _TID, s2.id, ChecklistscoreUpdate(bevinding="Gezien.")
            )
            assert r2.vraag_verduidelijkt_op is None  # aanraken dooft de notitie
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
