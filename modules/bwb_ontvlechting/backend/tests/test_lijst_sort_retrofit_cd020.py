"""Unit-tests — sorteer-retrofit van de 5 legacy-lijsten (CD020, ADR-017).

Offline (likara-tests): een capture-sessie legt het samengestelde statement
vast; we asserten op de gegenereerde `ORDER BY` (incl. NULLS LAST) en de seek,
plus de regressie dat het default-pad (geen sort/order) `created_at` oplopend
behoudt. Alle vijf lijsten gebruiken uniform het v2n NULLS-LAST-pad (CD016).

De per-entiteit-configuratie staat in `_CONFIG`; de tests parametriseren erover.
"""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest

from services import (
    blokkade_service,
    checklistscore_service,
    datatype_service,
    gebruikersgroep_service,
)
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


def _enum(module, naam):
    import importlib

    return getattr(importlib.import_module(f"schemas.{naam}"), {
        "datatype": "DatatypeSorteerveld",
        "gebruikersgroep": "GebruikersgroepSorteerveld",
        "checklistscore": "ChecklistscoreSorteerveld",
        "blokkade": "BlokkadeLijstSorteerveld",
    }[naam])


# (svc, schema-naam, kolommen-attr, parsers-attr, default-ORDER-BY-prefix,
#  voorbeeld-sorteerveld, voorbeeld-ORDER-BY-prefix)
_CONFIG = [
    (datatype_service, "datatype", "_SORTEERBARE_KOLOMMEN", "_WAARDE_PARSERS",
     "datatype.created_at", "omschrijving", "datatype.omschrijving"),
    # ADR-036a — `afdeling` sorteert nu op de gejoinde partij-naam; het voorbeeld-veld gebruikt een
    # directe gebruikersgroep-kolom voor de ORDER-BY-prefix-assertie.
    (gebruikersgroep_service, "gebruikersgroep", "_SORTEERBARE_KOLOMMEN", "_WAARDE_PARSERS",
     "gebruikersgroep.created_at", "aantal_gebruikers", "gebruikersgroep.aantal_gebruikers"),
    (checklistscore_service, "checklistscore", "_SORTEERBARE_KOLOMMEN", "_WAARDE_PARSERS",
     "checklistscore.created_at", "score", "checklistscore.score"),
    (blokkade_service, "blokkade", "_LIJST_KOLOMMEN", "_LIJST_PARSERS",
     "blokkade.created_at", "eigenaar", "blokkade.eigenaar"),
]

_IDS = [c[1] for c in _CONFIG]


def _run(svc, **kw):
    sess = _CaptureSession()
    asyncio.run(svc.lijst(sess, TENANT_A, **kw))
    return str(sess.stmt)


# ── Allowlist-synchroniteit (enum ↔ kolommen ↔ parsers) ─────────────────────

@pytest.mark.parametrize("cfg", _CONFIG, ids=_IDS)
def test_allowlist_enum_kolommen_parsers_synchroon(cfg):
    svc, naam, kol_attr, par_attr, *_ = cfg
    enum = _enum(svc, naam)
    enum_namen = {e.value for e in enum}
    assert enum_namen == set(getattr(svc, kol_attr))
    assert enum_namen == set(getattr(svc, par_attr))


# ── Regressie: default-pad = created_at oplopend (NULLS LAST), id-tiebreaker ──

@pytest.mark.parametrize("cfg", _CONFIG, ids=_IDS)
def test_default_pad_created_at_oplopend(cfg):
    svc, _naam, _ka, _pa, default_prefix, *_ = cfg
    sql = _run(svc, limit=10)
    assert f"ORDER BY {default_prefix} ASC NULLS LAST" in sql
    assert "DESC" not in sql  # default is volledig oplopend


# ── Richting per order op een voorbeeld-sorteerveld ─────────────────────────

@pytest.mark.parametrize("cfg", _CONFIG, ids=_IDS)
def test_sorteerveld_asc_en_desc(cfg):
    svc, _naam, _ka, _pa, _dp, veld, veld_prefix = cfg
    asc = _run(svc, limit=10, sort=veld, order="asc")
    assert f"ORDER BY {veld_prefix} ASC NULLS LAST" in asc
    desc = _run(svc, limit=10, sort=veld, order="desc")
    assert f"ORDER BY {veld_prefix} DESC NULLS LAST" in desc


# ── Seek met null-cursor bouwt de IS NULL-tak (NULLS-LAST-staart) ───────────

@pytest.mark.parametrize("cfg", _CONFIG, ids=_IDS)
def test_seek_met_null_cursor_bouwt_isnull_tak(cfg):
    svc, _naam, _ka, _pa, _dp, veld, _vp = cfg
    cursor = encode_sort_cursor_nullable(sort=veld, order="asc", waarde=None, id=uuid.uuid4())
    sql = _run(svc, limit=10, after=cursor, sort=veld, order="asc")
    assert "IS NULL" in sql


# ── Cursor↔sort/order-mismatch → ValueError (route ⇒ 400) ───────────────────

@pytest.mark.parametrize("cfg", _CONFIG, ids=_IDS)
def test_cursor_mismatch_geeft_valueerror(cfg):
    svc = cfg[0]
    # Cursor uitgegeven voor created_at/asc, gebruikt onder created_at/desc.
    cursor = encode_sort_cursor_nullable(
        sort="created_at", order="asc",
        waarde=datetime(2026, 6, 6, tzinfo=timezone.utc), id=uuid.uuid4(),
    )
    with pytest.raises(ValueError):
        asyncio.run(svc.lijst(_CaptureSession(), TENANT_A, after=cursor,
                              sort="created_at", order="desc"))


@pytest.mark.parametrize("cfg", _CONFIG, ids=_IDS)
def test_onbekend_sortveld_geeft_valueerror(cfg):
    """Defensieve backstop (de route weigert al met 422)."""
    svc = cfg[0]
    with pytest.raises(ValueError):
        asyncio.run(svc.lijst(_CaptureSession(), TENANT_A, sort="geheim"))
