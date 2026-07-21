"""Bron-scan — een verwijzing naar een skill-kop wijst naar een kop die bestaat (LI049).

**Waarom deze scan bestaat.** De skills verwijzen naar elkaar ("zie likara-frontend
§Signaal-kanalen"): 84 keer tussen de skills onderling, 128 keer vanuit de documentatie
(gemeten in docs/Checkpoint-skillconsolidatie-V049.md). Niets bewaakte of die verwijzingen
ergens heen wijzen; er stonden er op het moment van bouwen al twee in de boom die naar een
niet-bestaande kop wezen, waarvan één in productiecode. Zodra koppen bewegen (de
LI049-consolidatie) ontstaan er stil meer. Een verwijzing die naar niets wijst laat de lezer
concluderen dat de regel niet meer geldt.

**Wat "kop" hier betekent (bewuste keuze).** De verwijscultuur in deze repo gebruikt `§` voor
échte koppen (##/###/####) én voor vetgedrukte lead-ins van alinea's/bullets (bv.
`likara-frontend §"Destructieve gating volgt de rollengrens"` wijst naar een vet-lead-in,
niet naar een kop). Beide tellen daarom als anker. Alleen-koppen zou tientallen bestaande,
werkende verwijzingen vals rood maken — en een scan die vals alarm slaat wordt genegeerd.

**Wat deze scan uitdrukkelijk NIET vangt (vier beperkingen — lees dit vóór je erop leunt):**
  1. een regel die in de VERKEERDE skill staat (de verwijzing klopt, de plek niet);
  2. een kop die een andere kop DUBBELT (twee waarheden — hier onzichtbaar);
  3. een tekst die uit de pas loopt met de CODE (inhoudelijke drift);
  4. een verwijzing die GEEN skill noemt (`§LI041` bestaat in vier skills tegelijk — die is
     niet op te lossen en blijft onbewaakt; hetzelfde geldt voor `zie §4 Lege staten` binnen
     een bestand);
  5. een dode verwijzing met een LEVEND VOORVOEGSEL (bv. `§Gate-discipline-oud`) — het
     fragment wordt van achteren ingekort zodat proza dat aan een verwijzing vastplakt geen
     vals alarm geeft (zie `_matcht`), en de prijs daarvan is dat het levende voorvoegsel
     dan alsnog matcht.
Zonder deze notitie lijkt "verwijzingen zijn bewaakt" waar, terwijl alleen de ondubbelzinnige
dat zijn — dat is schijnzekerheid, en die is duurder dan een gat dat je kent.

**Buiten bereik, met reden:**
  - TST-rapporten, changelogs, checkpoints, feitenrapporten, metingen, verkenningen,
    draaiboeken en onderzoeken (alles onder docs/ behalve OPVOLGPUNTEN.md en adr/): die
    leggen een MOMENT vast en horen niet herschreven te worden om een scan groen te krijgen.
  - SESSIESTART.md en SESSIE_BRIEFING.md: door gen_build gegenereerd uit NEXT_SESSION.md;
    meenemen geeft dubbele meldingen op één fout — de bron volstaat.
  - dit bestand zelf: de zelftest draagt een nagebootste dode verwijzing.

**UITSCHAKELVOORWAARDE (afgesproken bij de bouw, LI049):** geeft deze scan in de twee
volgende sessies vals alarm (rood op een verwijzing waarvan het doel wél bestaat), dan gaat
hij eruit. Een scan die getolereerd wordt in plaats van vertrouwd kost meer dan hij oplevert.

Bijtregel (A3): rood ALLEEN als (1) de verwijzing een skill bij naam noemt — `likara-ux §…`
of de korte vorm direct vóór het §-teken (`werkprotocol §…`, `frontend §…`) — én (2) het
fragment na § in die skill op geen enkel anker past. Alle twijfel (geen skillnaam, vrije
formulering, ADR-/documentverwijzing) → zwijgen. Vergelijking is ongevoelig voor
hoofdletters, accenten, aanhalingstekens, het §-teken en koppelteken-/schuine-streep-opmaak.
"""
import pathlib
import re
import unicodedata

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SKILLS_DIR = _ROOT / ".claude" / "skills" / "likara"
_SKIP_DELEN = {"node_modules", "__pycache__", ".git", ".venv", "alembic", "dist"}

# Levende documenten: niet af te leiden, dus benoemd (zie docstring voor wat er bewust
# buiten valt en waarom).
_LEVENDE_DOCS = ("NEXT_SESSION.md", "CLAUDE.md", "README.md", "docs/OPVOLGPUNTEN.md")

_KOP_RE = re.compile(r"^#{2,4}\s+(.+?)\s*$", re.MULTILINE)
# Vet-lead-in aan regelbegin (evt. na lijstteken/citaat/waarschuwing) — de tweede ankersoort.
_VET_RE = re.compile(r"^\s*(?:[-*>]\s+|\d+\.\s+)?(?:⚠\s*)?\*\*(.+?)\*\*", re.MULTILINE)

_STRIP_TEKENS = "-–—/·_.`'\"“”‘’«»§*!?…"
_FRAGMENT_GRENZEN = set('\n·;:()«»"”“—,*.`')
_OPEN_QUOTES = '"“„«'
_SLUIT_QUOTES = '"”«»'


def _norm(tekst: str) -> str:
    """Casefold + accentstrip + opmaaktekens → spatie, zodat 'P8a', '§P8A' en 'p8a' gelijk zijn."""
    t = unicodedata.normalize("NFKD", tekst)
    t = "".join(c for c in t if not unicodedata.combining(c)).casefold()
    t = "".join(" " if c in _STRIP_TEKENS else c for c in t)
    return " ".join(t.split())


def _skill_ankers() -> dict[str, list[str]]:
    """{skillnaam: genormaliseerde ankers} — afgeleid uit de skill-map, nooit een lijst van
    negen. Een tiende skill doet vanzelf mee (het patroon uit likara-frontend §LI048-bereik,
    deze sessie verhuisd naar likara-tests)."""
    uit: dict[str, list[str]] = {}
    for pad in sorted(_SKILLS_DIR.glob("*/SKILL.md")):
        tekst = pad.read_text(encoding="utf-8")
        ankers = [_norm(m) for m in _KOP_RE.findall(tekst)]
        ankers += [_norm(m) for m in _VET_RE.findall(tekst)]
        uit[pad.parent.name] = [a for a in ankers if a]
    return uit


def _naam_patroon(skills: dict[str, list[str]]) -> re.Pattern:
    """De skillnaam moet DIRECT vóór § staan (alleen sluit-leestekens/witruimte ertussen) —
    anders is 'de frontend. Zie §4' ten onrechte een skill-verwijzing."""
    kort = "|".join(sorted((n.removeprefix("likara-") for n in skills), key=len, reverse=True))
    return re.compile(
        r"(?<![A-Za-z0-9-])((?:likara-)?(?:" + kort + r"))[`'\")\]]*\s*$"
    )


def _fragment_na(tekst: str, idx: int) -> str:
    """Het kop-fragment ná een §: tot een harde grens; een geciteerd fragment tot de
    sluit-quote. Inkorten kan een verwijzing alleen makkelijker laten matchen — nooit rood
    door truncatie."""
    i = idx + 1
    while i < len(tekst) and tekst[i] in " \t":
        i += 1
    if i < len(tekst) and tekst[i] in _OPEN_QUOTES:
        j = i + 1
        while j < len(tekst) and tekst[j] not in _SLUIT_QUOTES and tekst[j] != "\n":
            j += 1
        return tekst[i + 1:j]
    j = i
    while j < len(tekst) and (j - i) < 90 and tekst[j] not in _FRAGMENT_GRENZEN:
        j += 1
    return tekst[i:j].strip().rstrip(".!?")


def _matcht(fragment_norm: str, ankers: list[str]) -> bool:
    """Match = fragment past op één anker (substring in één van beide richtingen, of alle
    fragment-tokens komen in één anker voor). Past het volle fragment nergens, dan wordt het
    VAN ACHTEREN token voor token ingekort en opnieuw geprobeerd — proza dat aan een
    verwijzing vastplakt ("§P8b. Wijzigt deze keten…", "§LI046 voor het hoe") mag geen vals
    alarm geven. De prijs, bewust betaald (bijtregel A3: liever missen dan vals alarm): een
    dode verwijzing waarvan een VOORVOEGSEL wél bestaat wordt gemist."""
    tokens = fragment_norm.split()
    for n in range(len(tokens), 0, -1):
        deel = " ".join(tokens[:n])
        for anker in ankers:
            if deel in anker or anker in deel:
                return True
            if all(t in anker.split() for t in tokens[:n]):
                return True
    return False


def vind_overtredingen(tekst: str, label: str, skills: dict[str, list[str]],
                       naam_re: re.Pattern, teller: list | None = None) -> list[str]:
    """Alle `<skill> §<kop>`-verwijzingen in `tekst` waarvan de kop in die skill op geen
    enkel anker past. `teller` (optioneel) telt hoeveel verwijzingen er beoordeeld zijn —
    de nul-doelen-guard leest hem."""
    overtredingen: list[str] = []
    for m in re.finditer("§", tekst):
        venster = tekst[max(0, m.start() - 50):m.start()]
        naam_m = naam_re.search(venster)
        if not naam_m:
            continue  # geen skillnaam direct vóór § → twijfel → zwijgen (bijtregel 1)
        naam = naam_m.group(1)
        skill = naam if naam.startswith("likara-") else f"likara-{naam}"
        ankers = skills.get(skill)
        if ankers is None:
            continue
        fragment = _fragment_na(tekst, m.start())
        fragment_norm = _norm(fragment)
        if not fragment_norm:
            continue
        if teller is not None:
            teller.append(1)
        if not _matcht(fragment_norm, ankers):
            regel = tekst.count("\n", 0, m.start()) + 1
            overtredingen.append(
                f"{label}:{regel} → {skill} §{fragment!r} — geen kop of vet-anker gevonden"
            )
    return overtredingen


def _scan_bestanden():
    """Het bereik: skills (afgeleid) + benoemde levende documenten + ADR's + Python-/JS-code
    inclusief commentaar en tests. Vastleggingen en gegenereerde bestanden bewust niet
    (zie docstring)."""
    eigen = pathlib.Path(__file__).resolve()
    for pad in sorted(_SKILLS_DIR.glob("*/SKILL.md")):
        yield pad
    for rel in _LEVENDE_DOCS:
        p = _ROOT / rel
        if p.is_file():
            yield p
    yield from sorted((_ROOT / "docs" / "adr").glob("*.md"))
    for wortel in ("backend", "modules", "docs/_generators"):
        for pad in sorted((_ROOT / wortel).rglob("*.py")):
            if _SKIP_DELEN & set(pad.parts) or pad.resolve() == eigen:
                continue
            yield pad
    for wortel in ("frontend/src", "frontend/tests", "frontend/scripts", "modules"):
        basis = _ROOT / wortel
        for patroon in ("*.js", "*.mjs", "*.vue"):
            for pad in sorted(basis.rglob(patroon)):
                if _SKIP_DELEN & set(pad.parts):
                    continue
                yield pad


# ── Zelftests: de scan bijt, en zwijgt waar hij moet zwijgen ─────────────────────────────

def test_scan_bijt_op_nagebootste_dode_verwijzing():
    """Een nagebootste verwijzing naar een niet-bestaande kop wordt rood; een geldige en een
    skill-loze niet. Nagebootst — niet de echte dode verwijzing uit de boom (die wordt in
    blok B gerepareerd en dan zou dit bewijs verdwijnen)."""
    skills = {"likara-ux": [_norm("P8a — Een opgeborgen filter blijft zichtbaar (LI048)")]}
    naam_re = _naam_patroon(skills)
    dood = "zie likara-ux §" + "KopDie" + "NietBestaat" + " voor de regel"
    geldig = "zie likara-ux §P8a voor de regel"
    zonder_naam = "zoals §" + "KopDie" + "NietBestaat" + " al zei"

    assert len(vind_overtredingen(dood, "t", skills, naam_re)) == 1, \
        "de scan vangt een dode verwijzing niet — hij bijt niet"
    assert vind_overtredingen(geldig, "t", skills, naam_re) == [], \
        "geldige verwijzing gaf vals alarm"
    assert vind_overtredingen(zonder_naam, "t", skills, naam_re) == [], \
        "verwijzing zonder skillnaam hoort buiten de bijtregel te vallen"


def test_scan_normaliseert_opmaak():
    """Hoofdletters, accenten, aanhalingstekens en koppelteken-opmaak maken geen verschil."""
    skills = {"likara-werkprotocol": [_norm("Adversariële checkvraag vóór de bouw (LI041)")]}
    naam_re = _naam_patroon(skills)
    vormen = [
        'zie werkprotocol §ADVERSARIELE CHECKVRAAG',
        'zie likara-werkprotocol §"Adversariële checkvraag"',
        "zie werkprotocol §Adversariële checkvraag · UI-toepassing",  # grens kapt bij ·
    ]
    for vorm in vormen:
        assert vind_overtredingen(vorm, "t", skills, naam_re) == [], vorm


def test_ankers_worden_gevonden():
    """Nul doelen = stil groen; dat mag niet. Elke skill levert ankers, en het geheel is
    substantieel."""
    skills = _skill_ankers()
    assert len(skills) >= 9, f"te weinig skills gevonden ({len(skills)}) — pad-aanname stuk"
    for naam, ankers in skills.items():
        assert len(ankers) >= 5, f"{naam}: {len(ankers)} ankers — extractie stuk?"
    assert sum(len(a) for a in skills.values()) >= 150


def test_scan_beoordeelt_echte_verwijzingen():
    """De regex vindt de bestaande verwijscultuur — vindt hij er bijna geen, dan is de scan
    stil smaller geworden dan hij lijkt (de les van het lijstkop-bereik, LI048)."""
    skills = _skill_ankers()
    naam_re = _naam_patroon(skills)
    teller: list = []
    for pad in _scan_bestanden():
        vind_overtredingen(pad.read_text(encoding="utf-8", errors="replace"),
                           str(pad.relative_to(_ROOT)), skills, naam_re, teller)
    assert len(teller) >= 25, f"slechts {len(teller)} beoordeelde verwijzingen — bereik stuk?"


# ── DE scan ──────────────────────────────────────────────────────────────────────────────

def test_elke_kopverwijzing_wijst_naar_bestaand_anker():
    skills = _skill_ankers()
    naam_re = _naam_patroon(skills)
    bestanden = list(_scan_bestanden())
    assert len(bestanden) > 200, f"scan vond te weinig bestanden ({len(bestanden)})"
    overtredingen: list[str] = []
    for pad in bestanden:
        overtredingen += vind_overtredingen(
            pad.read_text(encoding="utf-8", errors="replace"),
            str(pad.relative_to(_ROOT)), skills, naam_re,
        )
    if overtredingen:
        pytest.fail(
            f"{len(overtredingen)} verwijzing(en) naar een niet-bestaande kop:\n  "
            + "\n  ".join(overtredingen)
        )
