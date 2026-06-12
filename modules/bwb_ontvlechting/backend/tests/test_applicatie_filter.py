"""Unit-tests — Applicatie-registerfilters (CD017).

Offline: een capture-sessie legt het samengestelde statement vast; we asserten op
de WHERE-clauses (status `IN`, hostingmodel `=`, ge-escapete `ILIKE`-contains) en
op de **regressie** dat het default-pad (geen filters) byte-identiek het
CD015-gedrag oplevert.
"""
import asyncio
import uuid

import pytest

from services import applicatie_service as svc

TENANT_A = "11111111-1111-1111-1111-111111111111"


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _CaptureSession:
    def __init__(self, rows=None):
        self._rows = rows or []
        self.stmt = None

    async def execute(self, stmt):
        self.stmt = stmt
        return _Result(self._rows)


def _sql(**kw):
    sess = _CaptureSession()
    asyncio.run(svc.lijst(sess, TENANT_A, **kw))
    return str(sess.stmt)


# ── LIKE-escaping (unit) ────────────────────────────────────────────────────

def test_escape_like_escapet_wildcards_en_escapeteken():
    # eerst de backslash, daarna % en _
    assert svc._escape_like("50%_x") == r"50\%\_x"
    assert svc._escape_like("a\\b") == "a\\\\b"
    assert svc._escape_like("schoon") == "schoon"


# ── Regressie: default-pad ongewijzigd ──────────────────────────────────────

def test_default_pad_zonder_filters_ongewijzigd():
    sql = _sql(limit=25)
    assert "ORDER BY applicatie.created_at ASC, applicatie.id ASC" in sql
    assert " IN " not in sql  # geen statusfilter
    assert "LIKE" not in sql  # geen ilike-contains
    # alleen de tenant-filter in de WHERE
    assert "applicatie.tenant_id =" in sql


def test_lege_statuslijst_is_geen_filter():
    sql = _sql(status=[])
    assert "lifecycle_status IN" not in sql


# ── Filters afzonderlijk ────────────────────────────────────────────────────

def test_status_multi_geeft_in_clause():
    sql = _sql(status=["concept", "geblokkeerd"])
    assert "applicatie.lifecycle_status IN" in sql


def test_hostingmodel_geeft_gelijkheid():
    sql = _sql(hostingmodel="saas")
    assert "component.hostingmodel =" in sql


def test_eigenaar_geeft_geescapte_ilike():
    sql = _sql(eigenaar="tiel")
    assert "lower(component.eigenaar_organisatie) LIKE" in sql
    assert "ESCAPE" in sql


def test_zoek_geeft_geescapte_ilike_op_naam():
    sql = _sql(zoek="zaak")
    assert "lower(component.naam) LIKE" in sql
    assert "ESCAPE" in sql


# ── AND-combinatie ──────────────────────────────────────────────────────────

def test_alle_filters_and_gecombineerd():
    sql = _sql(status=["concept"], hostingmodel="saas", eigenaar="tiel", zoek="zaak")
    assert "lifecycle_status IN" in sql
    assert "component.hostingmodel =" in sql
    assert "lower(component.eigenaar_organisatie) LIKE" in sql
    assert "lower(component.naam) LIKE" in sql


# ── Filters combineren met sortering (CD015 blijft werken) ──────────────────

def test_filter_met_sortering_behoudt_order_by():
    sql = _sql(zoek="zaak", sort="naam", order="desc")
    assert "lower(component.naam) LIKE" in sql
    assert "ORDER BY component.naam DESC, applicatie.id DESC" in sql


# ── Escaping is echt actief: een wildcard wordt letterlijk gebonden ─────────

def test_wildcard_in_zoekterm_wordt_letterlijk_gebonden():
    sess = _CaptureSession()
    asyncio.run(svc.lijst(sess, TENANT_A, zoek="50%"))
    compiled = sess.stmt.compile()
    # de gebonden waarde bevat de ge-escapete term, niet het rauwe wildcard
    waarden = [str(v) for v in compiled.params.values()]
    assert any(r"%50\%%" == w or r"50\%" in w for w in waarden)
