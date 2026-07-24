"""Gedeelde, domein-neutrale Pydantic-tekstvalidators (LI059 — volledige facade-purge).

Verhuisd uit `schemas/applicatie.py` (die met de facade-opruiming verdwijnt) naar een neutrale
plek: deze helpers zijn tenant-/entiteit-onafhankelijk en worden hergebruikt door vrijwel elk
invoer-schema. **Dit is DE gedeelde plek die elke tekstwaarde passeert** — de invoer-weerbaarheid
(LI051) leeft daarom hier, één keer, niet per veld:

- **Blok B — één schrijfwijze:** elke tekst wordt NFC-genormaliseerd, zodat twee manieren om
  dezelfde letter te schrijven ("José" met los accent vs. samengestelde letter) dezelfde tekst
  opleveren. Onzichtbaar voor de gebruiker (hij typt José en ziet José); emoji/andere schriften
  blijven gewoon toegestaan — dit gaat over vorm, niet over toelaatbaarheid.
- **Blok A — weigeren wat geen tekst is:** nultekens en overige stuurtekens hebben in een naam of
  toelichting geen betekenis (plakfout, gereedschap-residu) en worden bij de deur geweigerd. Het
  onderscheid enkel-/meerregelig is een ontwerpkeuze (`meerregelig`): een **naam/code/aanduiding**
  (één regel) mag geen regelovergang of tab bevatten (plakfout); een **toelichting/bevinding/
  omschrijving** (`meerregelig=True`) mag dat wél (alinea). Een nulteken is nooit toegestaan.

De lijn (besluit Bert, LI051): **niet filteren op wat gevaarlijk lijkt, maar zorgen dat inhoud
nooit opdracht wordt.** Deze validators BLOKKEREN dus geen `<adres>` of `Select & Go` — dat is
legitieme inhoud; de scheiding inhoud↔opdracht leeft in de opslag (geparametriseerde queries) en op
het scherm (Vue-interpolatie), geborgd door aparte wachters.

Signaturen — `veld`/`maxlen` ONGEWIJZIGD; `meerregelig` is optioneel met default False:

- `_verplichte_tekst(waarde, veld, maxlen, *, meerregelig=False)` — verplicht veld.
- `_optionele_tekst(waarde, maxlen, *, meerregelig=False)` — optioneel veld.
"""
import unicodedata

# C0/C1-stuurtekens die nooit betekenisdragende tekst zijn. NUL (\x00) staat er expliciet in en
# wordt in GEEN enkel veld toegestaan. In een meerregelig veld zijn regelovergang/tab/CR wél
# betekenis (alinea) — die worden dan uit deze set gehaald (zie `_stuurtekens`).
_MEERREGELIG_TOEGESTAAN = frozenset("\n\r\t")


def _stuurtekens(waarde: str, *, meerregelig: bool) -> set[str]:
    """De aangetroffen stuurtekens (C0 < 0x20, plus DEL/C1 0x7f–0x9f). In een meerregelig veld
    tellen \\n/\\r/\\t niet mee; een nulteken telt ALTIJD mee (nooit toegestaan)."""
    gevonden = set()
    for ch in waarde:
        o = ord(ch)
        if o == 0 or o < 0x20 or 0x7F <= o <= 0x9F:
            if meerregelig and ch in _MEERREGELIG_TOEGESTAAN:
                continue
            gevonden.add(ch)
    return gevonden


def _weiger_niet_tekst(waarde: str, *, veld: str | None, meerregelig: bool) -> None:
    """Blok A — weiger wat geen tekst is, met een begrijpelijke NL-melding (blok C). `veld` is de
    naam voor in de melding; None ⇒ neutrale aanhef ("Dit veld")."""
    onderwerp = f"De {veld}" if veld else "Dit veld"
    ongeldig = _stuurtekens(waarde, meerregelig=meerregelig)
    # Een regelovergang/tab in een enkelregelig veld is een aparte, begrijpelijker melding dan
    # "onzichtbare tekens" — het is bijna altijd een plakfout uit een lijst of tabel.
    if not meerregelig and ongeldig & _MEERREGELIG_TOEGESTAAN:
        raise ValueError(
            f"{onderwerp} mag niet uit meerdere regels bestaan. Dit gebeurt vaak bij kopiëren "
            "uit een lijst of tabel — plak de tekst opnieuw of typ hem op één regel over."
        )
    if ongeldig:
        raise ValueError(
            f"{onderwerp} bevat tekens die niet kunnen worden opgeslagen. Dit gebeurt vaak bij "
            "kopiëren uit een ander programma — plak de tekst opnieuw of typ hem over."
        )


def _normaliseer(waarde: str) -> str:
    """Blok B — NFC: gelijk-uitziende tekst wordt gelijke tekst. Onzichtbaar voor de gebruiker."""
    return unicodedata.normalize("NFC", waarde)


def _verplichte_tekst(waarde: str | None, veld: str, maxlen: int, *, meerregelig: bool = False) -> str:
    """Niet-lege, genormaliseerde, gestripte tekst met max-lengte (verplicht veld).
    Weigert nul-/stuurtekens (blok A) met een NL-melding (blok C)."""
    if waarde is None:
        raise ValueError(f"{veld} is verplicht")
    waarde = _normaliseer(waarde).strip()
    if not waarde:
        raise ValueError(f"{veld} mag niet leeg zijn")
    _weiger_niet_tekst(waarde, veld=veld, meerregelig=meerregelig)
    if len(waarde) > maxlen:
        raise ValueError(f"{veld} mag maximaal {maxlen} tekens bevatten")
    return waarde


def _optionele_tekst(waarde: str | None, maxlen: int, *, meerregelig: bool = False) -> str | None:
    """Genormaliseerde, gestripte optionele tekst; leeg ⇒ None; max-lengte afgedwongen.
    Weigert nul-/stuurtekens (blok A) met een NL-melding (blok C)."""
    if waarde is None:
        return None
    waarde = _normaliseer(waarde).strip()
    if not waarde:
        return None
    _weiger_niet_tekst(waarde, veld=None, meerregelig=meerregelig)
    if len(waarde) > maxlen:
        raise ValueError(f"mag maximaal {maxlen} tekens bevatten")
    return waarde
