"""Tests — consistentie-signalering technische plaatsing (ADR-023 Fase F / F-3 stap 2).

Offline: de pure signaal-afleiding (positief/niet-positief/ongescoord × draait_op aan/uit),
`lijst` over gemockte rijen (filtert alleen gesignaleerde componenten; generiek over
componenttypen — niet-applicatie mét markering wordt meegenomen), engine-import-afwezigheid
+ read-only, en RBAC (`ARCHITECTUUR.LEZEN`). Live (skip-if-no-DB): de oriëntatie
`draait_op = assignment doel==component`, scope-via-markering (componenttype zonder
technische_plaatsing-vraag → géén signaal), met structurele opruim.
"""
import asyncio
import uuid
from types import SimpleNamespace

import pytest

import app.core.audit  # noqa: F401 — registreert de audit-capture-hook
import app.core.database  # noqa: F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context

_TID = "11111111-1111-1111-1111-111111111111"
_CD_APP_URL = "postgresql+asyncpg://cd_app:changeme_dev@localhost:5432/complidata"


# ── Offline: pure signaal-afleiding ──────────────────────────────────────────────

def test_signaal_matrix():
    from services.plaatsingsignaal_service import _signaal

    # Positief (ja/deels) + GEEN draait_op → beoordeeld_niet_vastgelegd.
    assert _signaal("ja", False) == "beoordeeld_niet_vastgelegd"
    assert _signaal("deels", False) == "beoordeeld_niet_vastgelegd"
    # draait_op + niet-positief/ongescoord → vastgelegd_niet_beoordeeld.
    assert _signaal("nee", True) == "vastgelegd_niet_beoordeeld"
    assert _signaal("nvt", True) == "vastgelegd_niet_beoordeeld"
    assert _signaal(None, True) == "vastgelegd_niet_beoordeeld"
    # Consistent → geen signaal.
    assert _signaal("ja", True) is None       # beoordeeld én vastgelegd
    assert _signaal("deels", True) is None
    assert _signaal("nee", False) is None      # niet beoordeeld én niet vastgelegd
    assert _signaal("nvt", False) is None
    assert _signaal(None, False) is None       # ongescoord én niet vastgelegd


def _rij(naam, componenttype, score, draait_op):
    from models.models import ChecklistScore
    return SimpleNamespace(
        id=uuid.uuid4(), naam=naam, componenttype=componenttype,
        score=ChecklistScore(score) if score else None, draait_op=draait_op,
    )


def test_lijst_filtert_en_is_generiek_over_typen():
    """`lijst` geeft alleen gesignaleerde componenten terug, met reden; en doet dat
    generiek — een niet-applicatietype (mét markering, hier als rij aangeleverd) telt mee."""
    from unittest.mock import AsyncMock, MagicMock

    from services import plaatsingsignaal_service as svc

    rijen = [
        _rij("App-A", "applicatie", "ja", False),          # signaal 1
        _rij("App-B", "applicatie", None, True),           # signaal 2 (ongescoord + draait_op)
        _rij("App-C", "applicatie", "ja", True),           # consistent → weg
        _rij("DB-X", "client_software", "deels", False),   # niet-applicatie → tóch meegenomen (signaal 1)
    ]
    result = MagicMock()
    result.all.return_value = rijen
    session = AsyncMock()
    session.execute.return_value = result

    items = asyncio.run(svc.lijst(session, _TID))
    per_naam = {i["naam"]: i for i in items}
    assert set(per_naam) == {"App-A", "App-B", "DB-X"}  # App-C (consistent) weg
    assert per_naam["App-A"]["signaal"] == "beoordeeld_niet_vastgelegd"
    assert per_naam["App-B"]["signaal"] == "vastgelegd_niet_beoordeeld"
    assert per_naam["DB-X"]["signaal"] == "beoordeeld_niet_vastgelegd"  # generiek
    assert per_naam["DB-X"]["componenttype"] == "client_software"
    assert per_naam["App-A"]["reden"]  # leesbare reden aanwezig
    # session is uitsluitend gelezen — geen mutatie.
    session.commit.assert_not_called()
    session.add.assert_not_called()


def test_service_raakt_engine_niet():
    """Engine onaangeroerd: geen lifecycle/profiel/blokkade-import; geen mutatie van score
    (alleen SELECT). `Checklistscore` mag als model worden gelézen — geen mutatiepad."""
    import pathlib

    import services.plaatsingsignaal_service as p

    for naam in ("lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
                 "ComponentProfiel", "Blokkade"):
        assert not hasattr(p, naam), f"signaal-service mag de engine niet importeren: {naam!r}"
    bron = pathlib.Path(p.__file__).read_text(encoding="utf-8")
    for verboden in ("session.add", "session.commit", "session.flush", "session.delete"):
        assert verboden not in bron, f"signaal-service is read-only — {verboden!r} verboden"


def test_rbac_hergebruikt_architectuur_lezen():
    from app.core.rbac import Actie, Entiteit, heeft_permissie

    for rol in ("viewer", "medewerker", "beheerder", "auditor"):
        assert heeft_permissie([rol], Entiteit.ARCHITECTUUR, Actie.LEZEN)
        for actie in (Actie.AANMAKEN, Actie.WIJZIGEN, Actie.VERWIJDEREN):
            assert not heeft_permissie([rol], Entiteit.ARCHITECTUUR, actie)


# ── Live (skip-if-no-DB) ─────────────────────────────────────────────────────────

def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_CD_APP_URL)
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


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="cd_app-DB niet bereikbaar (offline)")


async def _run_rls(fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_CD_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tok = zet_tenant_context(_TID)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_tenant_context(tok)
        await eng.dispose()


async def _maak_component(s, tid, naam, componenttype):
    from models.models import Component, Element, ElementType, HostingModel
    elem = Element(tenant_id=tid, element_type=ElementType.component)
    s.add(elem); await s.flush()
    s.add(Component(id=elem.id, tenant_id=tid, naam=naam, componenttype=componenttype,
                    hostingmodel=HostingModel.on_premise))
    await s.flush()
    return elem.id


async def _maak_assignment(s, tid, bron, doel):
    from models.models import Relatie
    r = Relatie(tenant_id=tid, bron_id=bron, doel_id=doel, relatietype="assignment")
    s.add(r); await s.flush()
    return r.id


async def _ruim(s, ids):
    from sqlalchemy import text as _text
    for eid in ids:
        await s.execute(_text("DELETE FROM element WHERE id=:i"), {"i": str(eid)})
    await s.commit()


@integratie
def test_orientatie_en_scope_live():
    """Borging #2 + #3: `draait_op = assignment doel==component` (host→gehoste); en de
    scope volgt uit de markering (applicatie hééft de technische_plaatsing-vraag;
    applicatieserver niet → valt buiten beschouwing)."""
    from services import plaatsingsignaal_service as svc

    tid = uuid.UUID(_TID)

    async def _flow(s):
        ids = []
        try:
            host = await _maak_component(s, tid, "WT-F3S-host", "database")
            host2 = await _maak_component(s, tid, "WT-F3S-host2", "database")
            host3 = await _maak_component(s, tid, "WT-F3S-host3", "database")
            app1 = await _maak_component(s, tid, "WT-F3S-app1", "applicatie")   # doel → draait_op
            app2 = await _maak_component(s, tid, "WT-F3S-app2", "applicatie")   # bron → géén draait_op
            srv = await _maak_component(s, tid, "WT-F3S-srv", "applicatieserver")  # buiten scope
            ids += [host, host2, host3, app1, app2, srv]
            await _maak_assignment(s, tid, host, app1)    # bron=host, doel=app1  → app1 draait_op
            await _maak_assignment(s, tid, app2, host2)   # bron=app2, doel=host2 → app2 NIET draait_op
            await _maak_assignment(s, tid, host3, srv)    # srv draait_op, maar buiten scope
            await s.commit()

            items = await svc.lijst(s, _TID)
            return {i["naam"]: i for i in items}, (app1, app2, srv)
        finally:
            await _ruim(s, ids)

    per_naam, _ = asyncio.run(_run_rls(_flow))
    # app1: draait_op (doel==component) + ongescoord → vastgelegd_niet_beoordeeld.
    assert "WT-F3S-app1" in per_naam, sorted(per_naam)
    assert per_naam["WT-F3S-app1"]["signaal"] == "vastgelegd_niet_beoordeeld"
    assert per_naam["WT-F3S-app1"]["draait_op"] is True
    # app2: enkel als BRON betrokken → géén draait_op → ongescoord+geen relatie = consistent.
    assert "WT-F3S-app2" not in per_naam
    # srv (applicatieserver): géén technische_plaatsing-vraag → buiten scope, ondanks draait_op.
    assert "WT-F3S-srv" not in per_naam


@integratie
def test_read_only_meting_live():
    """Borging #4: de signalenlijst is opvraagbaar; elk item is een geldig signaaltype met
    reden. (De feitelijke dev-stand staat in het gate-rapport.)"""
    from services import plaatsingsignaal_service as svc

    items = asyncio.run(_run_rls(lambda s: svc.lijst(s, _TID)))
    assert isinstance(items, list)
    for i in items:
        assert i["signaal"] in ("beoordeeld_niet_vastgelegd", "vastgelegd_niet_beoordeeld")
        assert i["reden"]
        assert "naam" in i and "componenttype" in i
