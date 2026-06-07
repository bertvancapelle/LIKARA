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
