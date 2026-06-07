"""Unit-tests — zelfbeschrijvende sorteer-cursor (ADR-017).

Pure helper-tests (geen DB). De legacy `encode_cursor`/`decode_cursor` blijven
elders getest (`test_applicatie_service.test_cursor_roundtrip`) en ongewijzigd.
"""
import base64
import uuid
from datetime import datetime, timezone

import pytest

from services.pagination import decode_sort_cursor, encode_sort_cursor


def test_sort_cursor_roundtrip_datetime():
    ts = datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc)
    ident = uuid.uuid4()
    cursor = encode_sort_cursor(sort="created_at", order="asc", waarde=ts, id=ident)

    sort, order, waarde_str, got_id = decode_sort_cursor(cursor)
    assert (sort, order) == ("created_at", "asc")
    assert datetime.fromisoformat(waarde_str) == ts
    assert got_id == ident


def test_sort_cursor_roundtrip_enumwaarde():
    from models.models import HostingModel

    ident = uuid.uuid4()
    cursor = encode_sort_cursor(
        sort="hostingmodel", order="desc", waarde=HostingModel.saas, id=ident
    )
    sort, order, waarde_str, got_id = decode_sort_cursor(cursor)
    assert (sort, order) == ("hostingmodel", "desc")
    assert waarde_str == "saas"  # enum → .value
    assert got_id == ident


def test_sort_cursor_robuust_bij_pipe_in_waarde():
    """Een sorteerwaarde met '|' moet exact terugkomen (rsplit op de id-grens)."""
    ident = uuid.uuid4()
    cursor = encode_sort_cursor(sort="naam", order="asc", waarde="a|b systeem", id=ident)
    sort, order, waarde_str, got_id = decode_sort_cursor(cursor)
    assert (sort, order) == ("naam", "asc")
    assert waarde_str == "a|b systeem"
    assert got_id == ident


def test_sort_cursor_misvormd_geeft_valueerror():
    with pytest.raises(ValueError):
        decode_sort_cursor("!!!geen-geldige-cursor!!!")


def test_sort_cursor_leeg_geeft_valueerror():
    with pytest.raises(ValueError):
        decode_sort_cursor("")


def test_sort_cursor_verkeerde_versie_geeft_valueerror():
    rauw = base64.urlsafe_b64encode(
        f"v1|created_at|asc|x|{uuid.uuid4()}".encode("utf-8")
    ).decode("ascii")
    with pytest.raises(ValueError):
        decode_sort_cursor(rauw)
