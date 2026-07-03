"""Tests — registratiegaten_service (ADR-035 Slice 1 + 2). Offline (gemockte session).

Borgt de engine-invariant (geen engine-symbolen) + de badge-signaalmatrix + de mapping van de
signaalfuncties. De WHERE-correctheid (NOT EXISTS-subqueries) is de offline-grens → live-DB.
Geen DB nodig (asyncio.run + AsyncMock)."""
import asyncio
import uuid
from unittest.mock import AsyncMock, Mock

from services import registratiegaten_service as svc

TID = str(uuid.uuid4())


def _res_first(val):
    r = Mock()
    r.first = Mock(return_value=val)
    return r


def _res_all(rows):
    r = Mock()
    r.all = Mock(return_value=rows)
    return r


def _row(naam="X", lc=None, _id=None):
    return Mock(id=_id or uuid.uuid4(), naam=naam, lifecycle_status=lc)


def test_registratiegaten_engine_afwezigheid():
    """Engine-invariant: geen schrijf-/engine-symbolen in de servicemodule (alle functies)."""
    for naam in ["lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
                 "ComponentProfiel", "Blokkade", "Checklistscore"]:
        assert not hasattr(svc, naam), f"verboden engine-symbool aanwezig: {naam}"


# ── badge_voor_component — execute-volgorde: bestaat, geen-eigenaar, rol, serving(gg), flow ──
# Badge-execute-volgorde: bestaat, geen_eigenaar, geen_rol, geen_gg(serving), geisoleerd(flow),
# biv_onvolledig (ADR-028 slice 4 — de 6e query).
def test_badge_component_geen_gaten():
    """MET eigenaar/rol/gebruikersgroep/koppeling + complete BIV → geen signalen."""
    s = AsyncMock()
    s.execute = AsyncMock(side_effect=[
        _res_first(("c",)), _res_first(None), _res_first(("rol",)), _res_first(("serv",)), _res_first(("flow",)),
        _res_first(None),  # BIV compleet → geen signaal
    ])
    out = asyncio.run(svc.badge_voor_component(s, TID, uuid.uuid4()))
    assert out == {"signalen": [], "kritiek": 0, "aandacht": 0}


def test_badge_component_alle_gaten():
    """ZONDER eigenaar/rol/gebruikersgroep/koppeling + onvolledige BIV → 3 kritiek + 3 aandacht."""
    s = AsyncMock()
    s.execute = AsyncMock(side_effect=[
        _res_first(("c",)), _res_first(("c",)), _res_first(None), _res_first(None), _res_first(None),
        _res_first(("c",)),  # BIV onvolledig
    ])
    out = asyncio.run(svc.badge_voor_component(s, TID, uuid.uuid4()))
    assert out["kritiek"] == 3 and out["aandacht"] == 3
    assert set(out["signalen"]) == {
        "component_zonder_eigenaar", "component_zonder_verantwoordelijke", "biv_classificatie_onvolledig",
        "component_zonder_gebruikersgroep", "component_geisoleerd", "object_zonder_roltoewijzing",
    }


def test_badge_component_alleen_eigenaar_ontbreekt():
    """ZONDER eigenaar, verder compleet (incl. BIV) → één kritiek signaal, geen aandacht."""
    s = AsyncMock()
    s.execute = AsyncMock(side_effect=[
        _res_first(("c",)), _res_first(("c",)), _res_first(("rol",)), _res_first(("serv",)), _res_first(("flow",)),
        _res_first(None),  # BIV compleet
    ])
    out = asyncio.run(svc.badge_voor_component(s, TID, uuid.uuid4()))
    assert out["signalen"] == ["component_zonder_eigenaar"] and out["kritiek"] == 1 and out["aandacht"] == 0


def test_badge_component_alleen_biv_onvolledig():
    """Compleet behalve BIV → één kritiek signaal `biv_classificatie_onvolledig`."""
    s = AsyncMock()
    s.execute = AsyncMock(side_effect=[
        _res_first(("c",)), _res_first(None), _res_first(("rol",)), _res_first(("serv",)), _res_first(("flow",)),
        _res_first(("c",)),  # BIV onvolledig
    ])
    out = asyncio.run(svc.badge_voor_component(s, TID, uuid.uuid4()))
    assert out["signalen"] == ["biv_classificatie_onvolledig"] and out["kritiek"] == 1 and out["aandacht"] == 0


def test_badge_component_onbestaand_leeg():
    """Onbestaand/kruis-tenant component → lege badge (geen lek), één execute."""
    s = AsyncMock()
    s.execute = AsyncMock(side_effect=[_res_first(None)])
    out = asyncio.run(svc.badge_voor_component(s, TID, uuid.uuid4()))
    assert out == {"signalen": [], "kritiek": 0, "aandacht": 0}


# ── Slice 1 lijst-mapping ──
def test_component_zonder_eigenaar_mapping():
    s = AsyncMock()
    s.execute = AsyncMock(return_value=_res_all([_row("Zaaksysteem", "concept"), _row("BRP", None)]))
    out = asyncio.run(svc.component_zonder_eigenaar(s, TID))
    assert len(out) == 2 and out[0]["naam"] == "Zaaksysteem" and out[0]["lifecycle_status"] == "concept"
    assert out[0]["signaal"] == "component_zonder_eigenaar" and out[0]["niveau"] == "kritiek"


def test_component_zonder_verantwoordelijke_mapping():
    s = AsyncMock()
    s.execute = AsyncMock(return_value=_res_all([_row("DMS", "in_inventarisatie")]))
    out = asyncio.run(svc.component_zonder_verantwoordelijke(s, TID))
    assert out[0]["signaal"] == "component_zonder_verantwoordelijke" and out[0]["niveau"] == "kritiek"


# ── ADR-028 slice 4 — BIV-classificatie onvolledig (kritiek) ──
def test_component_biv_onvolledig_mapping_is_kritiek():
    s = AsyncMock()
    s.execute = AsyncMock(return_value=_res_all([_row("Zaaksysteem", "concept"), _row("BRP", None)]))
    out = asyncio.run(svc.component_biv_onvolledig(s, TID))
    assert len(out) == 2
    assert out[0]["signaal"] == "biv_classificatie_onvolledig" and out[0]["niveau"] == "kritiek"
    assert out[0]["lifecycle_status"] == "concept"


def test_biv_predikaat_een_of_meer_leeg():
    """Predikaat-matrix (0/1/2/3 aspecten gevuld): alleen alle-drie-gevuld is compleet.
    Gecontroleerd op de gecompileerde SQL van `_biv_onvolledig()` (OR van drie IS NULL)."""
    clause = str(svc._biv_onvolledig().compile(compile_kwargs={"literal_binds": True}))
    for kolom in ("biv_beschikbaarheid", "biv_integriteit", "biv_vertrouwelijkheid"):
        assert f"{kolom} IS NULL" in clause
    assert clause.count(" OR ") == 2  # drie IS NULL-takken → twee OR-verbindingen


# ── Slice 2 aandacht-signalen — mapping (signaal + niveau='aandacht') ──
def test_component_zonder_gebruikersgroep_mapping():
    s = AsyncMock()
    s.execute = AsyncMock(return_value=_res_all([_row("Zaaksysteem")]))
    out = asyncio.run(svc.component_zonder_gebruikersgroep(s, TID))
    assert out[0]["signaal"] == "component_zonder_gebruikersgroep" and out[0]["niveau"] == "aandacht"


def test_component_geisoleerd_mapping():
    s = AsyncMock()
    s.execute = AsyncMock(return_value=_res_all([_row("Solo")]))
    out = asyncio.run(svc.component_geisoleerd(s, TID))
    assert out[0]["signaal"] == "component_geisoleerd" and out[0]["niveau"] == "aandacht"


def test_contract_zonder_component_mapping():
    s = AsyncMock()
    s.execute = AsyncMock(return_value=_res_all([_row("Contract X")]))
    out = asyncio.run(svc.contract_zonder_component(s, TID))
    assert out[0]["signaal"] == "contract_zonder_component" and out[0]["niveau"] == "aandacht"


def test_gebruikersgroep_zonder_organisatie_mapping():
    s = AsyncMock()
    s.execute = AsyncMock(return_value=_res_all([_row("Burgerzaken")]))  # naam = afdeling-label
    out = asyncio.run(svc.gebruikersgroep_zonder_organisatie(s, TID))
    assert out[0]["signaal"] == "gebruikersgroep_zonder_organisatie" and out[0]["niveau"] == "aandacht"
    assert out[0]["naam"] == "Burgerzaken"


def test_object_zonder_roltoewijzing_combineert_drie_subtypes():
    """Combineert component + contract + gebruikersgroep, elk met entiteit_type."""
    s = AsyncMock()
    s.execute = AsyncMock(side_effect=[
        _res_all([_row("Comp")]), _res_all([_row("Contr")]), _res_all([_row("GG")]),
    ])
    out = asyncio.run(svc.object_zonder_roltoewijzing(s, TID))
    assert [o["entiteit_type"] for o in out] == ["component", "contract", "gebruikersgroep"]
    assert all(o["signaal"] == "object_zonder_roltoewijzing" and o["niveau"] == "aandacht" for o in out)


def test_registratiegaten_groepeert_per_ernst():
    """De orchestrator levert de twee ernst-groepen met alle signaaltype-sleutels."""
    s = AsyncMock()
    s.execute = AsyncMock(return_value=_res_all([]))  # alle queries leeg
    out = asyncio.run(svc.registratiegaten(s, TID))
    assert set(out) == {"kritiek", "aandacht"}
    assert set(out["kritiek"]) == {
        "component_zonder_eigenaar", "component_zonder_verantwoordelijke", "biv_classificatie_onvolledig",
    }
    assert set(out["aandacht"]) == {
        "component_zonder_gebruikersgroep", "component_geisoleerd", "contract_zonder_component",
        "gebruikersgroep_zonder_organisatie", "gebruiksfeit_zonder_verfijning",
        "object_zonder_roltoewijzing",
    }
