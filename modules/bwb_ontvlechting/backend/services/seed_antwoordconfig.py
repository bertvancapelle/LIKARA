"""Seed — default-antwoordconfiguratie per checklistvraag (ADR-019, CD025).

Platform-brede referentiedata: zet per vraag het `antwoordtype` en zaait de
optie-catalogus (`checklistvraag_optie`). Idempotent: antwoordtype = UPDATE
(zelfde waarde bij herhaling), opties via `ON CONFLICT DO NOTHING`.

Afgeleide sets (Besluit 12, single source): 2.1 ← `HostingModel` (7), 12.1 ←
`NiveauEnum` (3) — `optie_sleutel` = de enum-waarde (stabiel), label = gehumaniseerd
(aanpasbaar), `afgeleid_bron` gezet. 11.1 blijft vrij. Vragen zonder antwoordtype
hier houden `geen` (server_default) en verschijnen niet in de catalogus.

Draait UITSLUITEND via `platform_init` (init-container, cd_admin) — niet in het
tenant-/app-pad. `bouw_antwoordconfig()` is puur (DB-vrij) en zo testbaar.
"""
import re
import unicodedata

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import (
    AntwoordType,
    ChecklistVraag,
    ChecklistVraagOptie,
    HostingModel,
    NiveauEnum,
)

# Vrije enkelvoudige-keuze-sets (code → geordende labels).
_ENKELVOUDIG: dict[str, list[str]] = {
    "1.2": ["HR", "Financiën", "Zaakgericht", "Archief", "Sociaal domein", "Burgerzaken", "Belastingen", "Overig"],
    "1.3": ["BWB", "Tiel", "Gedeeld"],
    "1.4": ["BWB", "Tiel", "Gedeeld", "Derde partij"],
    "1.5": ["Exclusief Tiel", "Gedeeld met BWB/andere gemeenten"],
    "3.5": ["Geen", "Laag", "Midden", "Hoog"],
    "4.5": ["Laag", "Midden", "Hoog"],
    "4.9": ["Openbaar", "Intern", "Vertrouwelijk", "Geheim"],
    "7.1": ["Active Directory", "Azure AD", "Lokaal", "Federatief"],
    "7.2": ["Gemeente-specifiek", "Gedeeld"],
    "7.5": ["Laag", "Midden", "Hoog"],
    "8.1": ["BWB", "Tiel", "Gedeeld"],
    "8.2": ["Licentie", "SaaS-abonnement", "Maatwerkovereenkomst"],
    "11.1": ["Overdracht Tiel", "Overname BWB", "Tijdelijk gedeeld", "Beëindiging"],
    "11.3": ["Export/import", "Replicatie", "API", "Handmatig"],
    "12.2": ["Laag", "Midden", "Hoog"],
    "12.6": ["Inventariseren", "Escaleren", "Migreren", "Parkeren"],
}

# Meerkeuze-sets (code → geordende labels).
_MEERKEUZE: dict[str, list[str]] = {
    "3.1": ["Tiel", "BWB", "Culemborg", "West-Betuwe"],
    "3.7": ["Burgers", "Ketenpartners", "Andere overheden"],
    "4.1": ["Gestructureerd (DB)", "Documenten/files", "E-mail", "Spatial", "Binair"],
    "4.8": ["Regulier", "Bijzonder"],
    "5.2": ["API", "Bestandsuitwisseling", "Directe DB-koppeling", "Middleware"],
    "5.6": ["BWB", "Tiel", "Derde partij"],
    "6.2": ["API", "Bestandsuitwisseling", "Directe DB-koppeling", "Middleware"],
    "6.6": ["BWB", "Tiel", "Derde partij"],
}

# Afgeleide enkelvoudige-keuze-sets (single source uit een model-enum, Besluit 12).
_AFGELEID: dict[str, tuple[str, type]] = {
    "2.1": ("HostingModel", HostingModel),
    "12.1": ("NiveauEnum", NiveauEnum),
}

# Getal-vragen (geen opties).
_GETAL: list[str] = ["12.4"]


def _slug(label: str) -> str:
    """Stabiel, leesbaar optie-id uit een label (accenten gestript, a-z0-9 + '_')."""
    genormaliseerd = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
    genormaliseerd = genormaliseerd.lower().replace("&", "en")
    return re.sub(r"[^a-z0-9]+", "_", genormaliseerd).strip("_")[:60]


def _humaniseer(waarde: str) -> str:
    """Gehumaniseerd default-label uit een enum-waarde ('on_premise' → 'On premise')."""
    tekst = waarde.replace("_", " ")
    return tekst[:1].upper() + tekst[1:]


def bouw_antwoordconfig() -> tuple[dict[str, AntwoordType], list[dict]]:
    """Puur (DB-vrij): (code → antwoordtype, lijst optie-rijen). Deterministisch."""
    types: dict[str, AntwoordType] = {}
    opties: list[dict] = []

    for code, labels in _ENKELVOUDIG.items():
        types[code] = AntwoordType.enkelvoudige_keuze
        for i, label in enumerate(labels):
            opties.append({
                "vraag_code": code, "optie_sleutel": _slug(label),
                "label": label, "volgorde": i, "afgeleid_bron": None,
            })

    for code, (bron, enum) in _AFGELEID.items():
        types[code] = AntwoordType.enkelvoudige_keuze
        for i, lid in enumerate(enum):
            opties.append({
                "vraag_code": code, "optie_sleutel": lid.value,
                "label": _humaniseer(lid.value), "volgorde": i, "afgeleid_bron": bron,
            })

    for code, labels in _MEERKEUZE.items():
        types[code] = AntwoordType.meerkeuze
        for i, label in enumerate(labels):
            opties.append({
                "vraag_code": code, "optie_sleutel": _slug(label),
                "label": label, "volgorde": i, "afgeleid_bron": None,
            })

    for code in _GETAL:
        types[code] = AntwoordType.getal

    return types, opties


async def seed_antwoordconfig(session) -> tuple[int, int]:
    """Zet antwoordtype per vraag + zaai de optie-catalogus (idempotent).

    Geeft (aantal geconfigureerde vragen, aantal optie-rijen) terug — vaste
    waarden, ook bij een tweede (idempotente) run.
    """
    types, opties = bouw_antwoordconfig()

    for code, antwoordtype in types.items():
        await session.execute(
            update(ChecklistVraag).where(ChecklistVraag.code == code).values(antwoordtype=antwoordtype)
        )

    if opties:
        stmt = pg_insert(ChecklistVraagOptie).values(
            [{**o, "actief": True} for o in opties]
        ).on_conflict_do_nothing(index_elements=["vraag_code", "optie_sleutel"])
        await session.execute(stmt)

    await session.commit()
    return len(types), len(opties)
