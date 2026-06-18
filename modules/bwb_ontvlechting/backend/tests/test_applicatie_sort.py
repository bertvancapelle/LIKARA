"""Unit-tests — Applicatie server-side sortering (ADR-017).

Offline (complidata-tests): een capture-sessie legt het samengestelde SQLAlchemy-
statement vast; we asserten op de gegenereerde `ORDER BY`/seek (richting) zonder
DB. Inclusief de regressie dat het default-pad (geen sort/order) exact de
pre-ADR-017-ordening en -seek oplevert.
"""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest

from services import applicatie_service as svc
from services.pagination import encode_sort_cursor_nullable

TENANT_A = "11111111-1111-1111-1111-111111111111"


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _CaptureSession:
    """Legt het laatst uitgevoerde statement vast (voor SQL-assertie)."""

    def __init__(self, rows=None):
        self._rows = rows or []
        self.stmt = None

    async def execute(self, stmt):
        self.stmt = stmt
        return _Result(self._rows)


def _sql(sess):
    return str(sess.stmt)


# ── Allowlist-synchroniteit (enum ↔ kolommen ↔ parsers) ─────────────────────

def test_allowlist_enum_en_kolommen_synchroon():
    from schemas.applicatie import ApplicatieSorteerveld

    enum_namen = {e.value for e in ApplicatieSorteerveld}
    assert enum_namen == set(svc._SORTEERBARE_KOLOMMEN)
    assert enum_namen == set(svc._WAARDE_PARSERS)


# ── Regressie: default-pad ongewijzigd ──────────────────────────────────────

def test_default_pad_ordening_en_seek_v2n():
    # UX-B6-b: applicatie-lijst draait nu op de v2n-keyset (NULLS-LAST), consistent met B6-a/B2.
    cursor = encode_sort_cursor_nullable(
        sort="created_at",
        order="asc",
        waarde=datetime(2026, 6, 6, tzinfo=timezone.utc),
        id=uuid.uuid4(),
    )
    sess = _CaptureSession()
    asyncio.run(svc.lijst(sess, TENANT_A, limit=10, after=cursor))
    sql = _sql(sess)
    assert "ORDER BY applicatie.created_at ASC NULLS LAST, applicatie.id ASC" in sql
    assert "IS NULL" in sql  # NULLS-LAST keyset-seek


# ── Richting per order ──────────────────────────────────────────────────────

def test_sort_naam_asc_zonder_cursor():
    sess = _CaptureSession()
    asyncio.run(svc.lijst(sess, TENANT_A, limit=10, sort="naam", order="asc"))
    assert "ORDER BY component.naam ASC NULLS LAST, applicatie.id ASC" in _sql(sess)


def test_sort_naam_desc_seek_v2n():
    cursor = encode_sort_cursor_nullable(sort="naam", order="desc", waarde="Zaaksysteem", id=uuid.uuid4())
    sess = _CaptureSession()
    asyncio.run(svc.lijst(sess, TENANT_A, limit=10, after=cursor, sort="naam", order="desc"))
    sql = _sql(sess)
    assert "ORDER BY component.naam DESC NULLS LAST, applicatie.id DESC" in sql
    assert "IS NULL" in sql  # NULLS-LAST keyset-seek


# ── Cursor↔sort/order-mismatch → ValueError (route ⇒ 400) ───────────────────

def test_cursor_mismatch_geeft_valueerror():
    # Cursor uitgegeven voor created_at/asc, maar gebruikt onder naam/asc.
    cursor = encode_sort_cursor_nullable(
        sort="created_at",
        order="asc",
        waarde=datetime(2026, 6, 6, tzinfo=timezone.utc),
        id=uuid.uuid4(),
    )
    with pytest.raises(ValueError):
        asyncio.run(
            svc.lijst(_CaptureSession(), TENANT_A, after=cursor, sort="naam", order="asc")
        )


def test_onbekend_sortveld_in_service_geeft_valueerror():
    """Defensieve backstop (de route weigert al met 422)."""
    with pytest.raises(ValueError):
        asyncio.run(svc.lijst(_CaptureSession(), TENANT_A, sort="geheim"))
