"""LI059 (Slice 3) — engine-regressieborging na het opheffen van de applicatie-subtabel.

De service-laag is een dunne facade over `component` geworden en de dual-write naar de subtabel
is weg. De invariant blijft: score is de ENIGE lifecycle-driver. Deze borging bewijst dat de
transitie-attribuut-**schrijfpaden** (facade `werk_bij`/aanmaak) de engine NIET aandrijven.

- **Offline**: function-bronscan (ast-docstring-strip, zoals LI022) — de schrijfpaden roepen geen
  `herbereken*`/`bepaal_lifecycle` aan.
- **Live** (geseede lk_app-DB, skip indien offline): een `migratiepad/complexiteit/prioriteit`-edit
  via de facade laat `lifecycle_status` (profiel) ongemoeid en maakt geen checklistscore/blokkade;
  teardown via `DELETE FROM element` (residu-wees = 0).

Aanvullend op `test_engine_borging_li057` (die borgt dat de engine de velden niet léést).
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


# ── Offline: de facade-schrijfpaden drijven de engine niet aan ───────────────
def _src_zonder_docstring(fn) -> str:
    """Broncode van `fn` met de docstring gestript (ast) — zodat een uitleg-docstring die
    een verboden symbool noemt geen vals-positief geeft (LI022-patroon)."""
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


def test_facade_schrijfpaden_drijven_de_engine_niet_aan():
    from services import component_service as asv
    from services import component_service as csv

    schrijfpaden = [
        asv.werk_bij,
        asv.maak_aan,
        # LI059 facade-purge: de creatie-kern woont nu in component_service.
        csv.maak_applicatie_component,
        csv.werk_bij,
    ]
    for fn in schrijfpaden:
        src = _src_zonder_docstring(fn)
        for sym in _VERBODEN:
            assert sym not in src, (
                f"{fn.__module__}.{fn.__qualname__} refereert aan '{sym}' — een transitie-"
                f"attribuut-schrijfpad mag de lifecycle NIET (her)afleiden (score blijft de driver)."
            )


def test_facade_raakt_de_opgeheven_subtabel_niet():
    """De facade-service refereert nergens meer aan een `applicatie`-subtabel-CRUD."""
    from services import component_service as asv

    src = inspect.getsource(asv)
    for verboden in ("select(Applicatie)", "update(Applicatie)", "delete(Applicatie)", "Applicatie("):
        assert verboden not in src


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
def test_transitie_attribuut_edit_muteert_engine_niet():
    from sqlalchemy import text as _text

    from models.models import Migratiepad, NiveauEnum
    from schemas.component import ComponentCreate, ComponentUpdate
    from services import component_service as svc

    naam = f"LI059-fs-{uuid.uuid4().hex[:8]}"

    async def _tel(s, tabel, cid):
        return (
            await s.execute(_text(f"SELECT count(*) FROM {tabel} WHERE component_id=:c"), {"c": str(cid)})
        ).scalar_one()

    async def _lifecycle(s, cid):
        return (
            await s.execute(
                _text("SELECT lifecycle_status::text FROM component_profiel WHERE id=:c"), {"c": str(cid)}
            )
        ).scalar_one_or_none()

    async def _flow(s):
        comp = await svc.maak_aan(
            s, _TID,
            ComponentCreate(componenttype="applicatie", 
                naam=naam, hostingmodel="on_premise",
                migratiepad=None, complexiteit="midden", prioriteit="midden",
            ),
        )
        cid = comp["id"]
        try:
            # Verse applicatie: profiel-status concept; geen scores/blokkades.
            assert await _lifecycle(s, cid) == "concept"
            assert await _tel(s, "checklistscore", cid) == 0
            assert await _tel(s, "blokkade", cid) == 0

            # Transitie-attributen wijzigen via de facade — mag de engine NIET raken.
            await svc.werk_bij(
                s, _TID, cid,
                ComponentUpdate(
                    # ADR-046: `uitfaseren` bestaat niet meer als bedoeling — `vervangen`
                    # dekt hetzelfde testdoel (transitie-edit raakt de engine niet).
                    migratiepad=Migratiepad.vervangen,
                    complexiteit=NiveauEnum.hoog,
                    prioriteit=NiveauEnum.laag,
                ),
            )
            # Component draagt de nieuwe waarden…
            gewijzigd = await svc.haal_op(s, _TID, cid)
            assert gewijzigd.migratiepad == Migratiepad.vervangen
            assert gewijzigd.complexiteit == NiveauEnum.hoog
            assert gewijzigd.prioriteit == NiveauEnum.laag
            # …maar de engine-state is onaangeroerd (score blijft de enige driver).
            assert await _lifecycle(s, cid) == "concept"
            assert await _tel(s, "checklistscore", cid) == 0
            assert await _tel(s, "blokkade", cid) == 0
        finally:
            await svc.verwijder(s, _TID, cid)
            await s.commit()

    asyncio.run(_sessie_run(_flow))


@integratie
def test_geen_wees_element_na_facade_delete():
    """Na de facade-delete blijft geen wees-element achter (delete via het element-supertype)."""
    from sqlalchemy import text as _text

    from schemas.component import ComponentCreate
    from services import component_service as svc

    naam = f"LI059-wees-{uuid.uuid4().hex[:8]}"

    async def _flow(s):
        comp = await svc.maak_aan(
            s, _TID,
            ComponentCreate(componenttype="applicatie", 
                naam=naam, hostingmodel="on_premise",
                migratiepad=None, complexiteit="midden", prioriteit="midden",
            ),
        )
        cid = comp["id"]
        await svc.verwijder(s, _TID, cid)
        await s.commit()
        # element-rij weg (cascade), geen wees.
        rest = (
            await s.execute(_text("SELECT count(*) FROM element WHERE id=:c"), {"c": str(cid)})
        ).scalar_one()
        assert rest == 0

    asyncio.run(_sessie_run(_flow))
