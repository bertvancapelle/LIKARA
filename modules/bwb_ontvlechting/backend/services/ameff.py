"""AMEFF-lezer — generieke, veilige parser voor ArchiMate Open Exchange-bestanden (gate 1b).

Motor generiek, aanbod gesloten (ADR-043): dit is een AMEFF-lezer die per aanroep één
elementtype + de aggregation-boom dáártussen extraheert — geen "GEMMA-importer". Welke
bestanden LIKARA aanbiedt is een curatie-keuze (zie `referentiemodellen/HERKOMST.md` +
`referentiemodel_import_service`); deze module kent geen modelnamen.

Veiligheid: parsen via **defusedxml** (XXE-/entity-expansion-/DTD-veilig) — ook een
gecureerd bestand wordt defensief gelezen. Elke parse- of vormfout wordt één leesbare
`AmeffFout`; er lekt nooit een stacktrace naar de aanroeper.

Extractie-regels (verkenning `docs/Verkenning-GEMMA-AMEFF-V040.md`):
- **Filter hard op `xsi:type`** van het element — de GEMMA-eigen type-property is
  onbruikbaar (226/297 leeg) en wordt niet gelezen.
- **Bronsleutel = het `identifier`-attribuut** (dé identiteit — nooit de naam); een
  element zonder identifier of naam, of een dubbele identifier, is een luide fout
  (stil overslaan = stil weggooien).
- **Boom = `Aggregation`-relaties met het doeltype aan BEIDE kanten** (ouder = source,
  kind = target); Groupings en alle overige relatietypen vallen daarmee vanzelf buiten
  scope.
- **Definitie** = de `<documentation>`-tekst van het element; ontbreken is toegestaan
  (10/297 in GEMMA — leeg, geen fout).
- **Overgeslagen elementen worden per type GETELD** — de eerlijke telling voor het
  voorbeeldscherm; nooit stil weggooien. (De "Toelichting"-property blijft in de MVP
  bewust liggen — opvolgpunt, zie OPVOLGPUNTEN.md.)
"""
from dataclasses import dataclass
from pathlib import Path

from defusedxml import DefusedXmlException
from defusedxml import ElementTree as veilige_et

_NS = "{http://www.opengroup.org/xsd/archimate/3.0/}"
_XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_AGGREGATION = "Aggregation"

# Spiegelt de kolomgrenzen van `Bedrijfsfunctie` (bron_sleutel String(120), naam
# String(255)) — een bestand dat daarbuiten valt is een curatie-fout, geen dataverlies.
_MAX_SLEUTEL = 120
_MAX_NAAM = 255


class AmeffFout(ValueError):
    """Eén leesbare fout voor elk parse-/vormprobleem (geen stacktrace naar buiten)."""


@dataclass(frozen=True)
class AmeffFunctie:
    sleutel: str            # het identifier-attribuut — dé identiteit (nooit de naam)
    naam: str
    definitie: str | None


@dataclass(frozen=True)
class AmeffInhoud:
    """Het gelezen model, beperkt tot één elementtype + de boom daartussen."""

    element_type: str
    functies: tuple[AmeffFunctie, ...]
    plaatsingen: frozenset  # {(ouder_sleutel, kind_sleutel), …}
    overgeslagen: dict      # elementtype → aantal (eerlijke telling, nooit stil)

    @property
    def overgeslagen_totaal(self) -> int:
        return sum(self.overgeslagen.values())


def _tekst_kind(element, lokale_naam: str) -> str | None:
    """Tekst van een kind-element; bij meertaligheid wint `xml:lang="nl"`, anders het
    eerste kind. Lege/whitespace-tekst telt als afwezig."""
    kinderen = element.findall(f"{_NS}{lokale_naam}")
    if not kinderen:
        return None
    gekozen = next((k for k in kinderen if k.get(_XML_LANG) == "nl"), kinderen[0])
    tekst = (gekozen.text or "").strip()
    return tekst or None


def lees_ameff(pad: Path | str, *, element_type: str = "BusinessFunction") -> AmeffInhoud:
    """Lees een AMEFF-bestand veilig en extraheer `element_type` + de aggregation-boom.

    Werpt `AmeffFout` bij: onveilige XML (DTD/entities — XXE), niet-parsebare XML, een
    ontbrekende/dubbele identifier, een ontbrekende naam, of waarden buiten de
    kolomgrenzen. De dry-run en de echte uitvoering lezen via ditzelfde pad.
    """
    try:
        boom = veilige_et.parse(str(pad), forbid_dtd=True)
    except DefusedXmlException:
        raise AmeffFout(
            "Het bestand bevat onveilige XML-constructies (DTD/entiteiten) en is geweigerd."
        ) from None
    except OSError:
        raise AmeffFout("Het modelbestand is niet leesbaar.") from None
    except Exception:  # ParseError e.d. — nooit een rauwe parserfout naar buiten
        raise AmeffFout("Het bestand is geen geldig XML-/AMEFF-bestand.") from None

    wortel = boom.getroot()
    if wortel.tag != f"{_NS}model":
        raise AmeffFout("Het bestand is geen ArchiMate Open Exchange-model (AMEFF).")

    functies: list[AmeffFunctie] = []
    sleutels: set[str] = set()
    overgeslagen: dict[str, int] = {}
    for element in wortel.findall(f"{_NS}elements/{_NS}element"):
        soort = element.get(_XSI_TYPE) or "(zonder type)"
        if soort != element_type:
            overgeslagen[soort] = overgeslagen.get(soort, 0) + 1
            continue
        sleutel = (element.get("identifier") or "").strip()
        naam = _tekst_kind(element, "name")
        if not sleutel:
            raise AmeffFout(
                f"Een {element_type}-element heeft geen identifier — zonder bronsleutel "
                "is de inhoud niet herhaalbaar bij te werken."
            )
        if len(sleutel) > _MAX_SLEUTEL:
            raise AmeffFout(f"Identifier langer dan {_MAX_SLEUTEL} tekens: {sleutel[:40]}…")
        if sleutel in sleutels:
            raise AmeffFout(f"Dubbele identifier in het bestand: {sleutel}.")
        if not naam:
            raise AmeffFout(f"Element {sleutel} heeft geen naam.")
        if len(naam) > _MAX_NAAM:
            raise AmeffFout(f"Elementnaam langer dan {_MAX_NAAM} tekens ({sleutel}).")
        sleutels.add(sleutel)
        functies.append(
            AmeffFunctie(sleutel=sleutel, naam=naam, definitie=_tekst_kind(element, "documentation"))
        )

    plaatsingen = frozenset(
        (bron, doel)
        for rel in wortel.findall(f"{_NS}relationships/{_NS}relationship")
        if rel.get(_XSI_TYPE) == _AGGREGATION
        and (bron := rel.get("source")) in sleutels
        and (doel := rel.get("target")) in sleutels
        and bron != doel
    )

    return AmeffInhoud(
        element_type=element_type,
        functies=tuple(functies),
        plaatsingen=plaatsingen,
        overgeslagen=overgeslagen,
    )
