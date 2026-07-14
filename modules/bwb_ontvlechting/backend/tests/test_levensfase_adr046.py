"""ADR-046 besluit 1+2 (stuk 1) — levensfase op het component; bedoeling opgeschoond.

Offline: vormkeuzes A+B structureel geborgd (vaste enum-set; nullable ZONDER default —
geen backfill, geen verzonnen fase), onbekende waarde faalt luid, expliciet-null wist
(registratie is corrigeerbaar), route-filter is enum-getypeerd (native 422), en de
ENGINE-GRENS: de lifecycle-engine leest noch schrijft de levensfase, en LIKARA leidt de
fase nooit zelf af (geen schrijf-primitief op `component.levensfase` buiten de facade).

Live (skip-if-no-DB): nullable/geen-default op de echte DB, alle drie de waarden zetbaar,
expliciet wissen, het servergestuurde lijst-filter, en de engine-onaangeroerd-borging
(een levensfase-edit muteert `lifecycle_status` niet en maakt geen score/blokkade).
Live-tests ruimen hun element-rijen structureel op (V009-follow-up a).
"""
import asyncio
import inspect
import uuid

import pytest

import app.core.database  # noqa: F401 — registreert de RLS after_begin-hook (app.tenant_id)
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"


# ── Offline: vormkeuzes A + B ────────────────────────────────────────────────────

def test_levensfase_vaste_set_en_kolom_zonder_default():
    """Vormkeuze A: vaste set van drie (geen catalogus). Vormkeuze B: nullable kolom
    ZONDER server_default — ontbrekend = "nog niet vastgelegd", nooit een verzonnen fase."""
    from models.models import Component, Levensfase

    assert [e.value for e in Levensfase] == ["in_ontwikkeling", "in_productie", "uitfaseren"]
    kolom = Component.__table__.columns["levensfase"]
    assert kolom.nullable is True
    assert kolom.server_default is None and kolom.default is None


def test_levensfase_schema_optioneel_zonder_default():
    from schemas.component import ComponentCreate

    c = ComponentCreate(naam="X", componenttype="database")
    assert c.levensfase is None  # weggelaten = "nog niet vastgelegd" — geen stille default


def test_levensfase_onbekende_waarde_faalt_luid():
    from pydantic import ValidationError

    from schemas.component import ComponentCreate, ComponentUpdate

    with pytest.raises(ValidationError):
        ComponentCreate(naam="X", componenttype="database", levensfase="productie")
    with pytest.raises(ValidationError):
        ComponentUpdate(levensfase="uitgefaseerd")


def test_levensfase_expliciet_null_wist_weggelaten_laat_staan():
    """PATCH-semantiek: exclude_unset onderscheidt 'niet meegegeven' (ongewijzigd) van
    'expliciet null' (terug naar "nog niet vastgelegd" — registratie is corrigeerbaar)."""
    from schemas.component import ComponentUpdate

    assert "levensfase" not in ComponentUpdate(naam="Y").model_dump(exclude_unset=True)
    dump = ComponentUpdate(levensfase=None).model_dump(exclude_unset=True)
    assert "levensfase" in dump and dump["levensfase"] is None


def test_route_filter_is_enum_getypeerd():
    """Het lijst-filter is een `Levensfase`-Query-param → onbekende waarde = native 422
    aan de API-rand (enum-allowlist, ADR-017-lijn)."""
    from models.models import Levensfase
    from routes.component import lijst_componenten

    param = inspect.signature(lijst_componenten).parameters["levensfase"]
    assert param.annotation == (Levensfase | None)


def test_sorteerveld_allowlist_bevat_levensfase():
    from schemas.component import ComponentSorteerveld
    from services import component_service as svc

    assert "levensfase" in {e.value for e in ComponentSorteerveld}
    assert "levensfase" in svc._SORTEERBARE_KOLOMMEN and "levensfase" in svc._WAARDE_PARSERS


# ── Offline: engine-grens + geen automatische afleiding ─────────────────────────

def test_engine_leest_noch_schrijft_levensfase():
    """De engine-invariant: score blijft de ENIGE lifecycle-driver — de engine kent de
    levensfase niet (lezen noch schrijven), en de checklist-/blokkade-paden evenmin."""
    from services import blokkade_service, checklistscore_service, lifecycle_service

    for module in (lifecycle_service, checklistscore_service, blokkade_service):
        src = inspect.getsource(module)
        assert "levensfase" not in src and "Levensfase" not in src, (
            f"{module.__name__} refereert aan de levensfase — de engine mag dit "
            f"registratieve feit niet kennen (ADR-046 engine-invariant)."
        )


def test_geen_automatische_afleiding_van_de_levensfase():
    """LIKARA zet de levensfase NOOIT zelf (ook niet bij nul gebruikers): buiten de
    invoer-facade (`component_service`) en de dev-seed schrijft geen enkele module-service
    aan `levensfase`. Signalerings-/kaart-services mogen 'm uitsluitend LEZEN."""
    import pathlib

    services_dir = pathlib.Path(inspect.getfile(inspect.currentframe())).parents[1] / "services"
    toegestaan = {"component_service.py"}  # de menselijke invoerroute (Create/Update)
    overtreders = []
    for pad in sorted(services_dir.glob("*.py")):
        if pad.name in toegestaan:
            continue
        bron = pad.read_text(encoding="utf-8")
        # Schrijf-signaturen (lezen mag wél — bv. de kaart-projectie `levensfase=_val(…)`
        # op een read-only schema): attribuut-toewijzing of een Component-constructor.
        schrijft = (".levensfase =" in bron) or ("Component(" in bron and "levensfase=" in bron)
        if schrijft:
            overtreders.append(pad.name)
    assert not overtreders, f"services schrijven aan levensfase buiten de facade: {overtreders}"


# ── Live-integratie ──────────────────────────────────────────────────────────────

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
def test_levensfase_nullable_zetbaar_en_wisbaar_live():
    """Nul default op de echte DB; alle drie de waarden zetbaar; expliciet null wist."""
    from sqlalchemy import text as _text

    from models.models import Levensfase
    from schemas.component import ComponentCreate, ComponentUpdate
    from services import component_service as svc

    async def _flow(s):
        ids = []
        try:
            # Zonder levensfase → None (geen default, geen backfill).
            kaal = await svc.maak_aan(s, _TID, ComponentCreate(
                naam="WT-LF-kaal", componenttype="database"))
            ids.append(kaal["id"])
            assert kaal["levensfase"] is None

            # Alle drie de waarden zetbaar (via update — de registratieroute).
            standen = []
            for fase in Levensfase:
                bij = await svc.werk_bij(s, _TID, kaal["id"], ComponentUpdate(levensfase=fase))
                standen.append(bij["levensfase"])
            assert [getattr(v, "value", v) for v in standen] == [
                "in_ontwikkeling", "in_productie", "uitfaseren"]

            # Expliciet null → terug naar "nog niet vastgelegd".
            gewist = await svc.werk_bij(s, _TID, kaal["id"], ComponentUpdate(levensfase=None))
            assert gewist["levensfase"] is None

            # Create mét fase draagt 'm direct.
            met = await svc.maak_aan(s, _TID, ComponentCreate(
                naam="WT-LF-met", componenttype="database", levensfase="uitfaseren"))
            ids.append(met["id"])
            assert getattr(met["levensfase"], "value", met["levensfase"]) == "uitfaseren"
            return True
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    assert asyncio.run(_sessie_run(_flow)) is True


@integratie
def test_levensfase_lijstfilter_live():
    """Het server-side filter: `levensfase=uitfaseren` levert exact die componenten
    (binnen de WT-scope via `zoek`); zonder filter komen ze allemaal."""
    from sqlalchemy import text as _text

    from schemas.component import ComponentCreate
    from services import component_service as svc

    async def _flow(s):
        ids = []
        try:
            plan = [("WT-LFF-uit", "uitfaseren"), ("WT-LFF-prod", "in_productie"), ("WT-LFF-leeg", None)]
            for naam, fase in plan:
                c = await svc.maak_aan(s, _TID, ComponentCreate(
                    naam=naam, componenttype="database", levensfase=fase))
                ids.append(c["id"])

            alles, _ = await svc.lijst(s, _TID, zoek="WT-LFF-", limit=50)
            uit, _ = await svc.lijst(s, _TID, zoek="WT-LFF-", levensfase="uitfaseren", limit=50)
            return {a["naam"] for a in alles}, {u["naam"] for u in uit}
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    alles, uit = asyncio.run(_sessie_run(_flow))
    assert alles == {"WT-LFF-uit", "WT-LFF-prod", "WT-LFF-leeg"}
    assert uit == {"WT-LFF-uit"}  # exact de uitfaserende — leeg/prod vallen weg


@integratie
def test_levensfase_edit_muteert_engine_niet_live():
    """Engine-onaangeroerd (live borging): een levensfase-edit op een applicatie laat
    `lifecycle_status` (profiel) op `concept` en maakt geen checklistscore/blokkade."""
    from sqlalchemy import text as _text

    from schemas.component import ComponentCreate, ComponentUpdate
    from services import component_service as svc

    async def _flow(s):
        ids = []
        try:
            app = await svc.maak_aan(s, _TID, ComponentCreate(
                naam="WT-LF-engine", componenttype="applicatie"))
            ids.append(app["id"])

            async def _stand():
                lc = (await s.execute(_text(
                    "SELECT lifecycle_status FROM component_profiel WHERE id=:i"),
                    {"i": str(app["id"])})).scalar()
                scores = (await s.execute(_text(
                    "SELECT count(*) FROM checklistscore WHERE component_id=:i"),
                    {"i": str(app["id"])})).scalar()
                blokkades = (await s.execute(_text(
                    "SELECT count(*) FROM blokkade WHERE component_id=:i"),
                    {"i": str(app["id"])})).scalar()
                return lc, scores, blokkades

            voor = await _stand()
            await svc.werk_bij(s, _TID, app["id"], ComponentUpdate(levensfase="uitfaseren"))
            na = await _stand()
            return voor, na
        finally:
            for eid in ids:
                await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
            await s.commit()

    voor, na = asyncio.run(_sessie_run(_flow))
    assert voor == ("concept", 0, 0)
    assert na == ("concept", 0, 0)  # score blijft de enige lifecycle-driver
