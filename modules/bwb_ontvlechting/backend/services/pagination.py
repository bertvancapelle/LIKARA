"""Cursor-paginering (keyset) — referentie-implementatie (P5 + ADR-017).

Stabiele, deterministische paginering op `(created_at, id)`. De cursor is een
ondoorzichtige, URL-veilige base64-string die het laatste geziene
`(created_at, id)`-paar bevat. Een ongeldige cursor levert `ValueError`
(de route vertaalt dat naar een canoniek HTTP 400).

Hergebruikbaar door de overige module-entiteiten zodra die CRUD krijgen.

Twee lagen:
- **Legacy** (`encode_cursor`/`decode_cursor`): vast `created_at|id`-paar — in
  gebruik door de nog niet geretrofitte lijsten (datatype, gebruikersgroep,
  koppeling, checklistscore, blokkade). Byte-voor-byte ongewijzigd.
- **Sorteerbaar** (`encode_sort_cursor`/`decode_sort_cursor`, ADR-017): een
  zelfbeschrijvende v2-cursor die naast de sleutelwaarde ook `sort` en `order`
  draagt, zodat een cursor die niet bij de actieve sortering past, herkend wordt.
"""
import base64
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import and_, or_

_SEP = "|"


class Sorteerrichting(str, Enum):
    """Sorteerrichting (ADR-017). Generiek — per-entiteit herbruikbaar."""

    asc = "asc"
    desc = "desc"


# ── Sorteerbare (zelfbeschrijvende) cursor — ADR-017 ────────────────────────────

_CURSOR_VERSIE = "v2"


def _serialiseer_waarde(waarde) -> str:
    """Serialiseer een sorteerwaarde naar tekst voor de cursor.

    `datetime` → ISO-8601; een enum → zijn `.value`; anders `str()`. De route/
    service parst bij het decoderen terug naar het juiste kolomtype (allowlist).
    """
    if isinstance(waarde, datetime):
        return waarde.isoformat()
    if isinstance(waarde, Enum):
        return str(waarde.value)
    return str(waarde)


def encode_sort_cursor(*, sort: str, order: str, waarde, id) -> str:
    """Codeer een zelfbeschrijvende cursor `v2|sort|order|waarde|id`.

    `id` is de stabiele tiebreaker (totale ordening, ook bij niet-unieke
    sorteerkolommen). `sort`/`order` zijn gecontroleerde tokens (geen `|`); alleen
    `waarde` kan een `|` bevatten — daar houdt `decode_sort_cursor` rekening mee.
    """
    rauw = _SEP.join([_CURSOR_VERSIE, sort, order, _serialiseer_waarde(waarde), str(id)])
    return base64.urlsafe_b64encode(rauw.encode("utf-8")).decode("ascii")


def decode_sort_cursor(cursor: str) -> tuple[str, str, str, uuid.UUID]:
    """Decodeer een v2-cursor naar `(sort, order, waarde_str, id)`.

    `waarde_str` blijft tekst; de aanroeper parst hem naar het kolomtype via zijn
    allowlist. Robuust tegen een `|` in de waarde (rsplit op het laatste scheidings-
    teken voor de id).

    Raises:
        ValueError: bij een ontbrekende, misvormde of verkeerd-geversioneerde cursor.
    """
    if not cursor:
        raise ValueError("lege cursor")
    try:
        rauw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        versie, sort, order, rest = rauw.split(_SEP, 3)
        if versie != _CURSOR_VERSIE:
            raise ValueError("onbekende cursorversie")
        waarde_str, id_str = rest.rsplit(_SEP, 1)
        return sort, order, waarde_str, uuid.UUID(id_str)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError("ongeldige cursor") from exc


# ── NULLS-LAST-variant — ADR-017 B5 (eerste implementatie: CD016) ───────────────
#
# Voor lijsten met een **nullable** sorteerkolom. NULL-waarden staan altijd
# achteraan, ongeacht de richting (`asc` én `desc`). De cursor draagt een extra
# **null-vlag** zodat de keyset-seek de NULL-grens deterministisch oversteekt; de
# seek splitst in twee gevallen (niet-null-regio vs. null-staart). Generaliseert
# over tekst- én timestamp-kolommen (geen type-specifieke sentinel). Apart van de
# v2-cursor zodat bestaande v2-cursors ongewijzigd blijven decoderen.

_CURSOR_VERSIE_NULLABLE = "v2n"


def encode_sort_cursor_nullable(*, sort: str, order: str, waarde, id) -> str:
    """Codeer een NULLS-LAST-bewuste cursor `v2n|sort|order|isnull|waarde|id`."""
    is_null = "1" if waarde is None else "0"
    waarde_str = "" if waarde is None else _serialiseer_waarde(waarde)
    rauw = _SEP.join([_CURSOR_VERSIE_NULLABLE, sort, order, is_null, waarde_str, str(id)])
    return base64.urlsafe_b64encode(rauw.encode("utf-8")).decode("ascii")


def decode_sort_cursor_nullable(cursor: str) -> tuple[str, str, bool, str | None, uuid.UUID]:
    """Decodeer een v2n-cursor naar `(sort, order, is_null, waarde_str, id)`.

    `waarde_str` is None wanneer de sleutelwaarde NULL was (anders tekst; de
    aanroeper parst naar het kolomtype). Robuust tegen een `|` in de waarde.

    Raises:
        ValueError: bij een ontbrekende, misvormde of verkeerd-geversioneerde cursor.
    """
    if not cursor:
        raise ValueError("lege cursor")
    try:
        rauw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        versie, sort, order, is_null_str, rest = rauw.split(_SEP, 4)
        if versie != _CURSOR_VERSIE_NULLABLE:
            raise ValueError("onbekende cursorversie")
        waarde_str, id_str = rest.rsplit(_SEP, 1)
        is_null = is_null_str == "1"
        return sort, order, is_null, (None if is_null else waarde_str), uuid.UUID(id_str)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError("ongeldige cursor") from exc


def keyset_order_by_nulls_last(kolom, id_kolom, order: str) -> list:
    """ORDER BY `(kolom DIR NULLS LAST, id DIR)` — NULLs altijd achteraan."""
    if order == "asc":
        return [kolom.asc().nulls_last(), id_kolom.asc()]
    return [kolom.desc().nulls_last(), id_kolom.desc()]


def keyset_seek_nulls_last(kolom, id_kolom, *, order: str, is_null: bool, waarde, cursor_id):
    """WHERE-predicaat voor de keyset-seek ná de cursor, met NULLS-LAST-semantiek.

    Twee gevallen, symmetrisch voor `asc`/`desc` (NULLs altijd laatst):
    - **niet-null-regio** (cursorwaarde niet-null): rijen met `kolom <op> waarde`,
      of gelijke waarde met `id <op> cursor_id`, **plus de volledige null-staart**
      (`kolom IS NULL`);
    - **null-staart** (cursorwaarde null): uitsluitend `kolom IS NULL` met
      `id <op> cursor_id`.

    `<op>` = `>` voor `asc`, `<` voor `desc`. Voor NOT NULL-kolommen is de
    `kolom IS NULL`-tak altijd onwaar (onschadelijk) — dezelfde helper werkt dus
    uniform.
    """
    oplopend = order == "asc"
    if is_null:
        id_cmp = id_kolom > cursor_id if oplopend else id_kolom < cursor_id
        return and_(kolom.is_(None), id_cmp)
    if oplopend:
        kol_cmp = kolom > waarde
        id_cmp = id_kolom > cursor_id
    else:
        kol_cmp = kolom < waarde
        id_cmp = id_kolom < cursor_id
    return or_(kol_cmp, and_(kolom == waarde, id_cmp), kolom.is_(None))


def encode_cursor(item) -> str:
    """Codeer het `(created_at, id)`-paar van `item` tot een opaque cursor."""
    rauw = f"{item.created_at.isoformat()}{_SEP}{item.id}"
    return base64.urlsafe_b64encode(rauw.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decodeer een cursor naar `(created_at, id)`.

    Raises:
        ValueError: bij een ontbrekende of misvormde cursor.
    """
    if not cursor:
        raise ValueError("lege cursor")
    try:
        rauw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        ts_str, id_str = rauw.split(_SEP, 1)
        return datetime.fromisoformat(ts_str), uuid.UUID(id_str)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError("ongeldige cursor") from exc
