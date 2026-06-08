"""Unit-tests — NULLS-LAST-sorteercursor + keyset-helpers (ADR-017 B5, CD016).

Pure helper-tests (geen DB). De NULL-ordening is offline **structureel** te testen
(cursor-roundtrip met null-vlag, `.nulls_last()` in de order-by, IS NULL-takken in
de seek); de empirische verificatie tegen Postgres staat als OPVOLGPUNT (#23).

Bewijst óók dat de v2-cursor (Applicatie-lijst) ongemoeid blijft: dit is een
aparte `v2n`-variant.
"""
import base64
import uuid
from datetime import datetime, timezone

import pytest

from models.models import Blokkade
from services.pagination import (
    decode_sort_cursor,
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)


# ── v2n-cursor roundtrip ─────────────────────────────────────────────────────

def test_nullable_cursor_roundtrip_nietnull():
    ident = uuid.uuid4()
    cursor = encode_sort_cursor_nullable(sort="eigenaar", order="asc", waarde="Jan", id=ident)
    sort, order, is_null, waarde_str, got_id = decode_sort_cursor_nullable(cursor)
    assert (sort, order, is_null) == ("eigenaar", "asc", False)
    assert waarde_str == "Jan"
    assert got_id == ident


def test_nullable_cursor_roundtrip_null():
    ident = uuid.uuid4()
    cursor = encode_sort_cursor_nullable(sort="opgelost_op", order="desc", waarde=None, id=ident)
    sort, order, is_null, waarde_str, got_id = decode_sort_cursor_nullable(cursor)
    assert (sort, order, is_null) == ("opgelost_op", "desc", True)
    assert waarde_str is None
    assert got_id == ident


def test_nullable_cursor_robuust_bij_pipe():
    ident = uuid.uuid4()
    cursor = encode_sort_cursor_nullable(sort="toelichting", order="asc", waarde="a|b", id=ident)
    _, _, is_null, waarde_str, _ = decode_sort_cursor_nullable(cursor)
    assert is_null is False
    assert waarde_str == "a|b"


def test_nullable_cursor_misvormd_en_versie():
    with pytest.raises(ValueError):
        decode_sort_cursor_nullable("!!!")
    with pytest.raises(ValueError):
        decode_sort_cursor_nullable("")
    # v2 (zonder null-vlag) is geen geldige v2n-cursor
    v2 = base64.urlsafe_b64encode(f"v2|eigenaar|asc|Jan|{uuid.uuid4()}".encode()).decode("ascii")
    with pytest.raises(ValueError):
        decode_sort_cursor_nullable(v2)


def test_v2_decode_blijft_werken_naast_v2n():
    """Regressie: een echte v2-cursor decodeert nog met de v2-functie."""
    from services.pagination import encode_sort_cursor

    ident = uuid.uuid4()
    v2 = encode_sort_cursor(sort="naam", order="asc", waarde="X", id=ident)
    sort, order, waarde_str, got_id = decode_sort_cursor(v2)
    assert (sort, order, waarde_str) == ("naam", "asc", "X")
    assert got_id == ident
    # en een v2n-cursor is géén geldige v2-cursor
    v2n = encode_sort_cursor_nullable(sort="naam", order="asc", waarde="X", id=ident)
    with pytest.raises(ValueError):
        decode_sort_cursor(v2n)


# ── keyset-helpers: SQL-vorm ─────────────────────────────────────────────────

def test_order_by_nulls_last_beide_richtingen():
    asc = keyset_order_by_nulls_last(Blokkade.eigenaar, Blokkade.id, "asc")
    desc = keyset_order_by_nulls_last(Blokkade.eigenaar, Blokkade.id, "desc")
    assert "NULLS LAST" in str(asc[0]) and "ASC" in str(asc[0])
    assert "NULLS LAST" in str(desc[0]) and "DESC" in str(desc[0])


def test_seek_nietnull_asc_bevat_isnull_tak_en_groter_dan():
    clause = keyset_seek_nulls_last(
        Blokkade.eigenaar, Blokkade.id, order="asc", is_null=False, waarde="Jan", cursor_id=uuid.uuid4()
    )
    sql = str(clause)
    assert "IS NULL" in sql  # de hele null-staart hoort er nog bij
    assert ">" in sql


def test_seek_nietnull_desc_gebruikt_kleiner_dan():
    clause = keyset_seek_nulls_last(
        Blokkade.eigenaar, Blokkade.id, order="desc", is_null=False, waarde="Jan", cursor_id=uuid.uuid4()
    )
    sql = str(clause)
    assert "IS NULL" in sql
    assert "<" in sql


def test_seek_nullstaart_alleen_nulls_met_id():
    clause = keyset_seek_nulls_last(
        Blokkade.opgelost_op, Blokkade.id, order="asc", is_null=True, waarde=None, cursor_id=uuid.uuid4()
    )
    sql = str(clause)
    assert "IS NULL" in sql
    assert ">" in sql  # id-tiebreaker in de null-staart
    # geen waardevergelijking op de kolom zelf in de null-staart
    assert "opgelost_op >" not in sql
