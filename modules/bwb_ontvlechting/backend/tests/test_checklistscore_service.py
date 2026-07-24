"""Unit-tests — Checklistscore service-laag (ADR-013, Model A).

Focus: ouder-/checklistvraag_id-validatie, uniciteit, de auto-blokkade-invariant
(`_synchroniseer_blokkade`) en dat een schrijf de lifecycle-herberekening
aanroept. DB gemockt.
"""
import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

_APP = uuid.uuid4()
_VRAAG = uuid.uuid4()


def _create(score="nee", vraag=_VRAAG):
    from schemas.checklistscore import ChecklistscoreCreate

    return ChecklistscoreCreate(component_id=_APP, checklistvraag_id=vraag, score=score)


def _result(waarde):
    r = MagicMock()
    r.scalar_one_or_none.return_value = waarde
    return r


# ── maak_aan: validatie-paden ───────────────────────────────────────────────

def test_maak_aan_ouder_ontbreekt():
    # ADR-022 Fase E: geen component_profiel binnen de tenant ⇒ niet scoorbaar (404).
    from services import checklistscore_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    session.execute.side_effect = [_result(None)]  # _componenttype_van_profiel → geen profiel
    with pytest.raises(NietGevonden):
        asyncio.run(svc.maak_aan(session, uuid.uuid4(), _create()))


def test_maak_aan_onbekende_checklistvraag_id():
    from services import checklistscore_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    # 1) componenttype van profiel (scoorbaar), 2) checklist_dragend?, 3) checklistvraag_id niet gevonden.
    session.execute.side_effect = [_result("applicatie"), _result(True), _result(None)]
    with pytest.raises(NietGevonden):
        asyncio.run(svc.maak_aan(session, uuid.uuid4(), _create()))


def test_maak_aan_dubbele_score():
    from services import checklistscore_service as svc
    from services.errors import ChecklistscoreConflict

    session = AsyncMock()
    session.execute.side_effect = [
        _result("applicatie"),   # componenttype van profiel (scoorbaar)
        _result(True),           # checklist_dragend? (ADR-027 invoer-invariant)
        _result(_VRAAG),         # checklistvraag_id bestaat (juiste type)
        _result(uuid.uuid4()),   # bestaande score gevonden → conflict
    ]
    with pytest.raises(ChecklistscoreConflict):
        asyncio.run(svc.maak_aan(session, uuid.uuid4(), _create()))


def test_maak_aan_roept_herbereken(monkeypatch):
    from services import checklistscore_service as svc, lifecycle_service

    aangeroepen = {}

    async def _herb(session, tenant_id, app_id):
        aangeroepen["yes"] = True

    monkeypatch.setattr(lifecycle_service, "herbereken_lifecycle", _herb)

    session = AsyncMock()
    session.add = lambda o: None
    # componenttype van profiel, checklist_dragend?, vraag bestaat (→ vraagtekst), geen dup,
    # geen bestaande blokkade (nvt), huidige vraagtekst (ADR-056-leesverrijking in _verrijk).
    session.execute.side_effect = [
        _result("applicatie"), _result(True), _result("Vraagtekst?"), _result(None),
        _result(None), _result("Vraagtekst?"),
    ]
    asyncio.run(svc.maak_aan(session, uuid.uuid4(), _create(score="nvt")))
    assert aangeroepen.get("yes") is True


def test_maak_aan_geweigerd_als_type_niet_checklist_dragend(monkeypatch):
    """ADR-027 read-only-invariant: score-invoer op een niet-dragend componenttype ⇒ 422
    CHECKLIST_GESLOTEN, ZONDER engine-mutatie (geen add, geen herbereken)."""
    from services import checklistscore_service as svc, lifecycle_service
    from services.errors import OngeldigeRegistratie

    herb = {}

    async def _herb(*a, **k):
        herb["x"] = True

    monkeypatch.setattr(lifecycle_service, "herbereken_lifecycle", _herb)

    session = AsyncMock()
    toegevoegd = []
    session.add = lambda o: toegevoegd.append(o)
    # 1) componenttype van profiel ('middleware'), 2) checklist_dragend? → None = niet dragend.
    session.execute.side_effect = [_result("middleware"), _result(None)]
    with pytest.raises(OngeldigeRegistratie) as exc:
        asyncio.run(svc.maak_aan(session, uuid.uuid4(), _create()))
    assert exc.value.code == "CHECKLIST_GESLOTEN"
    assert not toegevoegd and not herb  # engine onaangeroerd (geen add/herbereken)


# ── invariant score↔blokkade (_synchroniseer_blokkade) ──────────────────────

def test_aanmaken_score_nee_maakt_blokkade_open():
    # oude_score=None ⇒ aanmaken met blokkerende score
    from models.models import BlokkadeStatus, ChecklistScore
    from services.checklistscore_service import _synchroniseer_blokkade

    score_obj = SimpleNamespace(id=uuid.uuid4(), component_id=_APP, score=ChecklistScore.nee)
    session = AsyncMock()
    session.execute.return_value = _result(None)  # nog geen blokkade
    toegevoegd = []
    session.add = lambda o: toegevoegd.append(o)

    asyncio.run(_synchroniseer_blokkade(session, uuid.uuid4(), score_obj, oude_score=None))

    assert len(toegevoegd) == 1
    assert toegevoegd[0].status == BlokkadeStatus.open


def test_transitie_nee_naar_ja_lost_actieve_blokkade_op():
    from models.models import BlokkadeStatus, ChecklistScore
    from services.checklistscore_service import _synchroniseer_blokkade

    blok = SimpleNamespace(status=BlokkadeStatus.open, opgelost_op=None)
    score_obj = SimpleNamespace(id=uuid.uuid4(), component_id=_APP, score=ChecklistScore.ja)
    session = AsyncMock()
    session.execute.return_value = _result(blok)

    asyncio.run(_synchroniseer_blokkade(session, uuid.uuid4(), score_obj, ChecklistScore.nee))

    assert blok.status == BlokkadeStatus.opgelost
    assert blok.opgelost_op is not None


def test_transitie_ja_naar_nee_heropent_opgeloste_blokkade():
    # Echte regressie: ja → nee (de uitgangsscore was NIET blokkerend)
    from models.models import BlokkadeStatus, ChecklistScore
    from services.checklistscore_service import _synchroniseer_blokkade

    blok = SimpleNamespace(status=BlokkadeStatus.opgelost, opgelost_op="2026-01-01")
    score_obj = SimpleNamespace(id=uuid.uuid4(), component_id=_APP, score=ChecklistScore.nee)
    session = AsyncMock()
    session.execute.return_value = _result(blok)

    asyncio.run(_synchroniseer_blokkade(session, uuid.uuid4(), score_obj, ChecklistScore.ja))

    assert blok.status == BlokkadeStatus.open
    assert blok.opgelost_op is None


def test_ongewijzigde_nee_score_laat_opgeloste_blokkade_met_rust():
    # Kern van de correctie: nee → nee (bv. alleen bevinding gewijzigd) mag een
    # geremedieerde (opgeloste) blokkade NIET heropenen → migratieklaar blijft.
    from models.models import BlokkadeStatus, ChecklistScore
    from services.checklistscore_service import _synchroniseer_blokkade

    blok = SimpleNamespace(status=BlokkadeStatus.opgelost, opgelost_op="2026-01-01")
    score_obj = SimpleNamespace(id=uuid.uuid4(), component_id=_APP, score=ChecklistScore.nee)
    session = AsyncMock()
    session.execute.return_value = _result(blok)

    asyncio.run(_synchroniseer_blokkade(session, uuid.uuid4(), score_obj, ChecklistScore.nee))

    assert blok.status == BlokkadeStatus.opgelost  # niet heropend
    assert blok.opgelost_op == "2026-01-01"


def test_binnen_blokkerend_nee_naar_deels_laat_blokkade_met_rust():
    from models.models import BlokkadeStatus, ChecklistScore
    from services.checklistscore_service import _synchroniseer_blokkade

    blok = SimpleNamespace(status=BlokkadeStatus.in_behandeling, opgelost_op=None)
    score_obj = SimpleNamespace(id=uuid.uuid4(), component_id=_APP, score=ChecklistScore.deels)
    session = AsyncMock()
    session.execute.return_value = _result(blok)

    asyncio.run(_synchroniseer_blokkade(session, uuid.uuid4(), score_obj, ChecklistScore.nee))

    assert blok.status == BlokkadeStatus.in_behandeling  # ongemoeid


def test_haal_op_niet_gevonden():
    from services import checklistscore_service as svc
    from services.errors import NietGevonden

    session = AsyncMock()
    session.execute.return_value = _result(None)
    with pytest.raises(NietGevonden):
        asyncio.run(svc.haal_op(session, uuid.uuid4(), uuid.uuid4()))


# ── FASE-1-invariant: velden-update zonder score raakt lifecycle/blokkade niet ──

def test_werk_bij_zonder_score_raakt_blokkade_en_lifecycle_niet(monkeypatch):
    """Een `ChecklistscoreUpdate` met enkel bevinding/actie (géén `score`)
    mag de score-afgeleide blokkade en lifecycle NIET wijzigen.

    Mechanisme (vastgelegd): omdat `score` niet in de update zit, blijft
    `obj.score` gelijk aan `oude_score`; `_synchroniseer_blokkade` kruist dan geen
    blokkerende grens en keert vroeg terug — vóór enige blokkade-query. De
    sentinel op `session.execute` bewijst dat er geen blokkade-mutatie plaatsvindt.
    """
    from models.models import ChecklistScore
    from schemas.checklistscore import ChecklistscoreUpdate
    from services import checklistscore_service as svc, lifecycle_service

    score_obj = SimpleNamespace(
        id=uuid.uuid4(), component_id=_APP, checklistvraag_id=_VRAAG,
        score=ChecklistScore.nee, bevinding=None, verantwoordelijke_id=None, actie=None,
    )

    async def _haal(*a, **k):
        return score_obj

    monkeypatch.setattr(svc, "haal_op", _haal)
    # ADR-027 invoer-invariant is orthogonaal aan dit blokkade/lifecycle-no-op-bewijs → no-op
    # (de invariant heeft een eigen test). Voorkomt dat de dragend-query de sentinel raakt.
    async def _kv_open(*a, **k):
        return None

    monkeypatch.setattr(svc, "_verzeker_checklist_open_voor", _kv_open)
    # ADR-056-leesverrijking (vraag_gewijzigd) is een READ-query, geen engine-mutatie —
    # buiten deze sentinel houden (de sentinel bewaakt blokkade-queries).
    async def _tekst(*a, **k):
        return None

    monkeypatch.setattr(svc, "_huidige_vraagtekst", _tekst)

    herb = {}

    async def _herb(session, tenant_id, app_id):
        herb["called"] = True  # loopt, maar op ONGEWIJZIGDE feiten (score gelijk)

    monkeypatch.setattr(lifecycle_service, "herbereken_lifecycle", _herb)

    session = AsyncMock()
    # _synchroniseer_blokkade hoort vroeg terug te keren ⇒ géén execute (geen
    # blokkade-query/mutatie). Komt er tóch een execute, dan faalt de test.
    session.execute.side_effect = AssertionError(
        "geen blokkade-query verwacht bij een update zonder score (no-op)"
    )

    asyncio.run(
        svc.werk_bij(
            session, uuid.uuid4(), score_obj.id,
            ChecklistscoreUpdate(bevinding="Onderbouwing.", actie="Herstelplan"),
        )
    )

    assert score_obj.bevinding == "Onderbouwing."   # veld toegepast
    assert score_obj.actie == "Herstelplan"
    assert score_obj.score == ChecklistScore.nee     # score ongewijzigd
    assert herb.get("called") is True                # herbereken aangeroepen (no-op qua feiten)


# ── ADR-019: semantische validatie van antwoord_waarde (los van het score-pad) ──

def _vraag_ns(antwoordtype):
    return SimpleNamespace(antwoordtype=antwoordtype)


def _opties_result(sleutels):
    r = MagicMock()
    r.all.return_value = [(s,) for s in sleutels]
    return r


def test_antwoord_none_doet_geen_query():
    from services.checklistscore_service import _valideer_antwoord_waarde

    session = AsyncMock()
    asyncio.run(_valideer_antwoord_waarde(session, "1.1", None))
    session.execute.assert_not_awaited()


def test_antwoord_op_type_geen_weigert():
    from models.models import AntwoordType
    from services.checklistscore_service import _valideer_antwoord_waarde
    from services.errors import OngeldigAntwoord

    session = AsyncMock()
    session.execute.return_value = _result(_vraag_ns(AntwoordType.geen))
    with pytest.raises(OngeldigAntwoord):
        asyncio.run(_valideer_antwoord_waarde(session, "1.1", {"optie": "x"}))


def test_antwoord_enkelvoudig_actieve_optie_ok():
    from models.models import AntwoordType
    from services.checklistscore_service import _valideer_antwoord_waarde

    session = AsyncMock()
    session.execute.side_effect = [
        _result(_vraag_ns(AntwoordType.enkelvoudige_keuze)),
        _opties_result(["saas", "on_premise"]),
    ]
    asyncio.run(_valideer_antwoord_waarde(session, "2.1", {"optie": "saas"}))  # geen raise


def test_antwoord_enkelvoudig_onbekende_optie_weigert():
    from models.models import AntwoordType
    from services.checklistscore_service import _valideer_antwoord_waarde
    from services.errors import OngeldigAntwoord

    session = AsyncMock()
    session.execute.side_effect = [
        _result(_vraag_ns(AntwoordType.enkelvoudige_keuze)),
        _opties_result(["saas"]),
    ]
    with pytest.raises(OngeldigAntwoord):
        asyncio.run(_valideer_antwoord_waarde(session, "2.1", {"optie": "xxx"}))


def test_antwoord_meerkeuze_subset_ok_buiten_set_weigert():
    from models.models import AntwoordType
    from services.checklistscore_service import _valideer_antwoord_waarde
    from services.errors import OngeldigAntwoord

    ok = AsyncMock()
    ok.execute.side_effect = [
        _result(_vraag_ns(AntwoordType.meerkeuze)),
        _opties_result(["a", "b", "c"]),
    ]
    asyncio.run(_valideer_antwoord_waarde(ok, "4.1", {"opties": ["a", "c"]}))

    fout = AsyncMock()
    fout.execute.side_effect = [
        _result(_vraag_ns(AntwoordType.meerkeuze)),
        _opties_result(["a", "b"]),
    ]
    with pytest.raises(OngeldigAntwoord):
        asyncio.run(_valideer_antwoord_waarde(fout, "4.1", {"opties": ["a", "z"]}))


def test_antwoord_getal_doet_geen_optie_query():
    from models.models import AntwoordType
    from services.checklistscore_service import _valideer_antwoord_waarde

    session = AsyncMock()
    session.execute.return_value = _result(_vraag_ns(AntwoordType.getal))
    asyncio.run(_valideer_antwoord_waarde(session, "12.4", {"getal": 3}))  # geen raise
    session.execute.assert_awaited_once()  # alleen de vraag-query, geen optie-query


def test_werk_bij_met_antwoord_zonder_score_raakt_engine_niet(monkeypatch):
    """Update mét antwoord_waarde maar ZONDER score wijzigt lifecycle/blokkade niet.

    Validatie geïsoleerd (gemockt); de engine-no-op blijkt uit de execute-sentinel
    (`_synchroniseer_blokkade` keert vroeg terug — geen blokkade-query)."""
    from models.models import ChecklistScore
    from schemas.checklistscore import ChecklistscoreUpdate
    from services import checklistscore_service as svc, lifecycle_service

    score_obj = SimpleNamespace(
        id=uuid.uuid4(), component_id=_APP, checklistvraag_id=_VRAAG,
        score=ChecklistScore.ja, antwoord_waarde=None, verantwoordelijke_id=None,
    )

    async def _haal(*a, **k):
        return score_obj

    monkeypatch.setattr(svc, "haal_op", _haal)

    async def _kv_open(*a, **k):
        return None

    monkeypatch.setattr(svc, "_verzeker_checklist_open_voor", _kv_open)  # ADR-027 invariant: eigen test

    async def _valid(*a, **k):
        return None

    monkeypatch.setattr(svc, "_valideer_antwoord_waarde", _valid)
    # ADR-056-leesverrijking = READ-query, geen engine-mutatie — buiten de sentinel.
    async def _tekst(*a, **k):
        return None

    monkeypatch.setattr(svc, "_huidige_vraagtekst", _tekst)

    herb = {}

    async def _herb(session, tenant_id, app_id):
        herb["x"] = True

    monkeypatch.setattr(lifecycle_service, "herbereken_lifecycle", _herb)

    session = AsyncMock()
    session.execute.side_effect = AssertionError("geen blokkade-query verwacht (engine no-op)")

    asyncio.run(
        svc.werk_bij(
            session, uuid.uuid4(), score_obj.id,
            ChecklistscoreUpdate(antwoord_waarde={"optie": "saas"}),
        )
    )

    assert score_obj.antwoord_waarde == {"optie": "saas"}
    assert score_obj.score == ChecklistScore.ja  # score ongewijzigd
    assert herb.get("x") is True
