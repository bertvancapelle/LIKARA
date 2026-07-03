"""ADR-037 — engine-borging: de verantwoordelijke per checklistantwoord is registratief.

De invariant: score blijft de ENIGE lifecycle-driver. Een `verantwoordelijke_id` op een antwoord
(en de daaruit afgeleide blokkade-verantwoordelijke) is registratie/leeslaag — hij mag de engine
NOOIT voeden, triggeren of een tweede lifecycle-bron worden.

- **Offline**: bronscan (ast-docstring-strip, LI022-patroon) — de verantwoordelijke read-/validatie-
  laag (`checklistscore_service._verrijk`, `partij_service.valideer_verantwoordelijke`/
  `resolve_verantwoordelijken`) refereert aan géén engine-(her)afleidingssymbool.
- **Live** (geseede lk_app-DB, skip indien offline): een verantwoordelijke zetten/wijzigen/leegmaken
  op een blokkerend antwoord laat `lifecycle_status` (profiel), `checklistscore.score` en de blokkade
  (aantal + status) ongemoeid; teardown via de facade-verwijder (residu = 0).
"""
import ast
import asyncio
import inspect
import uuid

import pytest

import app.core.database  # noqa: F401 — registreert de RLS/audit after_begin-hooks (app.tenant_id)
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"

_VERBODEN = ("herbereken_lifecycle", "herbereken_type", "bepaal_lifecycle")


def _src_zonder_docstring(fn) -> str:
    src = inspect.getsource(fn)
    mod = ast.parse(src)
    functie = mod.body[0]
    if (
        functie.body
        and isinstance(functie.body[0], ast.Expr)
        and isinstance(functie.body[0].value, ast.Constant)
        and isinstance(functie.body[0].value.value, str)
    ):
        functie.body = functie.body[1:]
    return ast.unparse(functie)


def test_verantwoordelijke_leeslaag_drijft_de_engine_niet_aan():
    """De read-/validatie-paden van de verantwoordelijke raken geen engine-(her)afleiding."""
    from services import checklistscore_service as css
    from services import partij_service as ps

    for fn in (css._verrijk, css._verrijk_lijst, ps.valideer_verantwoordelijke, ps.resolve_verantwoordelijken):
        src = _src_zonder_docstring(fn)
        for sym in _VERBODEN:
            assert sym not in src, (
                f"{fn.__module__}.{fn.__qualname__} refereert aan '{sym}' — de verantwoordelijke-"
                f"leeslaag mag de lifecycle NIET (her)afleiden (score blijft de enige driver)."
            )


# ── Live-integratie ──────────────────────────────────────────────────────────
def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

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


async def _sessie_run(fn):
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


@integratie
def test_verantwoordelijke_edit_muteert_engine_niet():
    from sqlalchemy import text as _text

    from models.models import ChecklistScore
    from schemas.checklistscore import ChecklistscoreCreate, ChecklistscoreUpdate
    from schemas.component import ComponentCreate
    from services import checklistscore_service as css
    from services import component_service as comp

    naam = f"ADR037-app-{uuid.uuid4().hex[:8]}"

    async def _lifecycle(s, cid):
        return (
            await s.execute(
                _text("SELECT lifecycle_status::text FROM component_profiel WHERE id=:c"), {"c": str(cid)}
            )
        ).scalar_one_or_none()

    async def _blok(s, cid):
        return (
            await s.execute(
                _text("SELECT count(*), max(status::text) FROM blokkade WHERE component_id=:c"), {"c": str(cid)}
            )
        ).first()

    async def _partij_van_aard(s, aard):
        return (
            await s.execute(
                _text("SELECT id FROM partij WHERE aard=:a AND tenant_id=:t LIMIT 1"),
                {"a": aard, "t": _TID},
            )
        ).scalar_one()

    async def _flow(s):
        comp_obj = await comp.maak_aan(
            s, _TID,
            ComponentCreate(componenttype="applicatie", naam=naam, hostingmodel="on_premise",
                            migratiepad="onbekend", complexiteit="midden", prioriteit="midden"),
        )
        cid = comp_obj["id"]
        try:
            await comp.start_beoordeling(s, _TID, cid)
            # Een blokkerend antwoord (nee) → engine maakt een open blokkade + zet lifecycle.
            vraag_id = (
                await s.execute(
                    _text("SELECT id FROM checklistvraag WHERE componenttype='applicatie' "
                          "AND tenant_id=:t ORDER BY code LIMIT 1"),
                    {"t": _TID},
                )
            ).scalar_one()
            score = await css.maak_aan(
                s, _TID,
                ChecklistscoreCreate(component_id=cid, checklistvraag_id=vraag_id, score="nee"),
            )
            # Baseline engine-state vastleggen. Het blokkerende antwoord maakt één open blokkade;
            # de lifecycle (nog niet alles gescoord → geen `geblokkeerd`) leggen we vast zoals hij is.
            lc0 = await _lifecycle(s, cid)
            aantal0, status0 = await _blok(s, cid)
            assert aantal0 == 1 and status0 == "open"

            afd = await _partij_van_aard(s, "organisatie_eenheid")
            pers = await _partij_van_aard(s, "persoon")

            # Zetten → wijzigen → leegmaken; elk mag de engine-state NIET veranderen.
            for verantw in (afd, pers, None):
                bij = await css.werk_bij(
                    s, _TID, score.id, ChecklistscoreUpdate(verantwoordelijke_id=verantw)
                )
                assert bij.verantwoordelijke_id == verantw          # registratie toegepast
                assert bij.score == ChecklistScore.nee              # score ongemoeid
                assert await _lifecycle(s, cid) == lc0              # lifecycle ongemoeid
                aantal, status = await _blok(s, cid)
                assert (aantal, status) == (aantal0, status0)       # blokkade ongemoeid
        finally:
            await comp.verwijder(s, _TID, cid)
            await s.commit()

    asyncio.run(_sessie_run(_flow))


# ── ADR-037 aandacht-signaal: engine-veilig + correct op het seed-scenario ──────

def test_signaal_query_drijft_de_engine_niet_aan():
    """De nieuwe signaal-query leest `checklistscore` via een table()-handle (géén ORM) en
    refereert geen engine-(her)afleiding."""
    from services import registratiegaten_service as reg

    src = _src_zonder_docstring(reg.antwoord_zonder_verantwoordelijke)
    for sym in _VERBODEN:
        assert sym not in src
    # Engine-tabellen worden nooit als ORM-klasse aangesproken vanuit deze service.
    for orm in ("ComponentProfiel", "Blokkade", "Checklistscore"):
        assert not hasattr(reg, orm), f"verboden engine-symbool aanwezig: {orm}"


@integratie
def test_signaal_antwoord_zonder_verantwoordelijke_op_seed():
    """Op het dev-seed-scenario vuurt het signaal op de gescoorde antwoorden ZONDER
    verantwoordelijke, en NIET op de antwoorden met een gezette verantwoordelijke."""
    from sqlalchemy import text as _text

    from services import registratiegaten_service as reg

    async def _flow(s):
        gescoord = (await s.execute(
            _text("SELECT count(*) FROM checklistscore WHERE tenant_id=:t AND score IS NOT NULL"),
            {"t": _TID},
        )).scalar_one()
        met_verantw_ids = {
            r[0] for r in (await s.execute(
                _text("SELECT id FROM checklistscore WHERE tenant_id=:t AND score IS NOT NULL "
                      "AND verantwoordelijke_id IS NOT NULL"),
                {"t": _TID},
            )).all()
        }
        assert len(met_verantw_ids) >= 1  # de seed zet er ≥1 (persoon/afdeling/blokkade)

        items = await reg.antwoord_zonder_verantwoordelijke(s, _TID)
        signaal_ids = {it["id"] for it in items}

        # Telt exact de gescoorde antwoorden zonder verantwoordelijke.
        assert len(items) == gescoord - len(met_verantw_ids)
        # De ingevulde antwoorden vuren NIET.
        assert signaal_ids.isdisjoint(met_verantw_ids)
        # Elk item is een aandacht-signaal met de juiste sleutel + een "component — vraag"-label.
        assert items and all(
            it["signaal"] == "antwoord_zonder_verantwoordelijke"
            and it["niveau"] == "aandacht"
            and " — " in it["naam"]
            for it in items
        )

    asyncio.run(_sessie_run(_flow))
