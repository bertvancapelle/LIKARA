"""ADR-006 Fase E — keyset-cursor van de auditlog-lees-service (offline)."""
import uuid
from datetime import datetime, timezone

import pytest

from services.auditlog_service import _decode_cursor, _encode_cursor


def test_cursor_round_trip():
    anker = datetime(2026, 6, 14, 10, 0, 0, tzinfo=timezone.utc)
    corr = uuid.uuid4()
    cursor = _encode_cursor(anker, corr)
    terug_anker, terug_corr = _decode_cursor(cursor)
    assert terug_anker == anker
    assert terug_corr == corr


def test_cursor_ongeldig_geeft_valueerror():
    for slecht in ("", "geen-base64!!", "cm9tbWVs"):
        with pytest.raises(ValueError):
            _decode_cursor(slecht)
