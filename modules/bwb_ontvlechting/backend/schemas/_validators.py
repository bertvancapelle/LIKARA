"""Gedeelde, domein-neutrale Pydantic-tekstvalidators (LI059 — volledige facade-purge).

Verhuisd uit `schemas/applicatie.py` (die met de facade-opruiming verdwijnt) naar een neutrale
plek: deze helpers zijn tenant-/entiteit-onafhankelijk en worden hergebruikt door vrijwel elk
invoer-schema. Signaturen zijn ONGEWIJZIGD:

- `_verplichte_tekst(waarde, veld, maxlen)` — 3 args (verplicht veld).
- `_optionele_tekst(waarde, maxlen)` — 2 args (optioneel veld).
"""


def _verplichte_tekst(waarde: str | None, veld: str, maxlen: int) -> str:
    """Niet-lege, gestripte tekst met max-lengte (verplicht veld)."""
    if waarde is None:
        raise ValueError(f"{veld} is verplicht")
    waarde = waarde.strip()
    if not waarde:
        raise ValueError(f"{veld} mag niet leeg zijn")
    if len(waarde) > maxlen:
        raise ValueError(f"{veld} mag maximaal {maxlen} tekens bevatten")
    return waarde


def _optionele_tekst(waarde: str | None, maxlen: int) -> str | None:
    """Gestripte optionele tekst; leeg ⇒ None; max-lengte afgedwongen."""
    if waarde is None:
        return None
    waarde = waarde.strip()
    if not waarde:
        return None
    if len(waarde) > maxlen:
        raise ValueError(f"mag maximaal {maxlen} tekens bevatten")
    return waarde
