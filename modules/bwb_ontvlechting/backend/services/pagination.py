"""Cursor-paginering (keyset) — referentie-implementatie (P5).

Stabiele, deterministische paginering op `(created_at, id)`. De cursor is een
ondoorzichtige, URL-veilige base64-string die het laatste geziene
`(created_at, id)`-paar bevat. Een ongeldige cursor levert `ValueError`
(de route vertaalt dat naar een canoniek HTTP 400).

Hergebruikbaar door de overige module-entiteiten zodra die CRUD krijgen.
"""
import base64
import uuid
from datetime import datetime

_SEP = "|"


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
