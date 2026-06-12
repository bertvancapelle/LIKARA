"""Unit-tests — blokkade_service.lijst_overzicht (CD016, ADR-017).

Offline (complidata-tests): een capture-sessie legt het samengestelde statement
vast; we asserten op join, statusfilter, sorteer-ORDER BY (incl. NULLS LAST) en de
cursor↔sort/order-mismatch. NULL-ordening is hier structureel (query-vorm), niet
empirisch — empirische bevestiging staat als OPVOLGPUNT (#23).
"""
import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from services import blokkade_service as svc
from services.pagination import encode_sort_cursor_nullable

TENANT_A = "11111111-1111-1111-1111-111111111111"


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _CaptureSession:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.stmt = None

    async def execute(self, stmt):
        self.stmt = stmt
        return _Result(self._rows)


def _sql(sess):
    return str(sess.stmt)


def _run(**kw):
    sess = _CaptureSession(kw.pop("rows", []))
    items, cursor = asyncio.run(svc.lijst_overzicht(sess, TENANT_A, **kw))
    return sess, items, cursor


# ── Allowlist-synchroniteit ─────────────────────────────────────────────────

def test_allowlist_enum_kolommen_parsers_synchroon():
    from schemas.blokkade import BlokkadeSorteerveld

    enum_namen = {e.value for e in BlokkadeSorteerveld}
    assert enum_namen == set(svc._OVERZICHT_KOLOMMEN)
    assert enum_namen == set(svc._OVERZICHT_PARSERS)


# ── Join + default sortering ────────────────────────────────────────────────

def test_join_en_default_sortering():
    sess, _, _ = _run()
    sql = _sql(sess)
    assert "JOIN component" in sql  # naam verhuisde naar component (ADR-021)
    assert "JOIN checklistscore" in sql
    # default = applicatie_naam asc, NULLS LAST, met blokkade.id-tiebreaker
    assert "ORDER BY component.naam ASC NULLS LAST" in sql
    assert "blokkade.id ASC" in sql


def test_nullable_kolom_desc_nulls_last():
    sess, _, _ = _run(sort="eigenaar", order="desc")
    sql = _sql(sess)
    assert "ORDER BY blokkade.eigenaar DESC NULLS LAST" in sql
    assert "blokkade.id DESC" in sql


# ── Statusfilter ────────────────────────────────────────────────────────────

def test_status_actief_filtert_op_constante_set():
    sess, _, _ = _run(status_filter="actief")
    assert "status IN" in _sql(sess)


def test_status_opgelost_filtert_op_enkele_waarde():
    sess, _, _ = _run(status_filter="opgelost")
    assert "blokkade.status =" in _sql(sess)


def test_status_alle_zonder_statusfilter():
    sess, _, _ = _run(status_filter="alle")
    sql = _sql(sess)
    assert "status IN" not in sql
    assert "blokkade.status =" not in sql


# ── Keyset-seek met NULL-cursor ─────────────────────────────────────────────

def test_seek_met_null_cursor_bouwt_isnull_tak():
    cursor = encode_sort_cursor_nullable(
        sort="opgelost_op", order="asc", waarde=None, id=uuid.uuid4()
    )
    sess, _, _ = _run(after=cursor, sort="opgelost_op", order="asc")
    assert "IS NULL" in _sql(sess)


# ── Cursor↔sort/order-mismatch ──────────────────────────────────────────────

def test_cursor_mismatch_geeft_valueerror():
    cursor = encode_sort_cursor_nullable(
        sort="applicatie_naam", order="asc", waarde="Zaaksysteem", id=uuid.uuid4()
    )
    with pytest.raises(ValueError):
        _run(after=cursor, sort="status", order="asc")


def test_onbekend_sortveld_geeft_valueerror():
    with pytest.raises(ValueError):
        _run(sort="geheim")


# ── Respons-vorm + vervolgcursor ────────────────────────────────────────────

def _rij(naam, eigenaar):
    return SimpleNamespace(
        id=uuid.uuid4(),
        applicatie_id=uuid.uuid4(),
        applicatie_naam=naam,
        vraag_code="A1",
        status="open",
        toelichting=None,
        eigenaar=eigenaar,
        opgelost_op=None,
        gewijzigd_op=datetime(2026, 6, 7, tzinfo=timezone.utc),
    )


def test_vorm_en_vervolgcursor():
    rows = [_rij(f"App {i}", None) for i in range(26)]  # limit 25 → 26 ⇒ meer
    sess, items, cursor = _run(rows=rows, limit=25)
    assert len(items) == 25
    assert set(items[0]) == {
        "id", "applicatie_id", "applicatie_naam", "vraag_code",
        "status", "toelichting", "eigenaar", "opgelost_op", "gewijzigd_op",
    }
    assert cursor is not None  # vervolgcursor want er was meer
