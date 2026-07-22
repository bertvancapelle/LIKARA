# Checkpoint — de gedrifte comment in check-css-build.mjs (READ-ONLY meting)

**Sessie:** LI049 · **Build:** V049 · **Branch:** master · **HEAD:** `049c4c9` · werktree schoon
**Grond:** gate-rapport verhuizing 3 (§Bronscans canoniek) · **Datum meting:** 2026-07-22
Niets gewijzigd behalve dit rapport. Scan groen (5 passed).

---

## Blok 1 — wat er staat, en hoe ver gedrift

### 1.1 De comment (frontend/scripts/check-css-build.mjs, **r509–513**, 5 regels)

> "GEEN UITZONDERINGENLIJST. Er stond er even één in (BedrijfsfunctieLijst, dat de schakelaar en
> een tweede actie in de kop droeg). Hij deed geen schade en werd elke run afgedrukt — maar hij
> legitimeerde een VORM: de volgende sessie die één scherm niet kan omzetten heeft dan een
> voorbeeld. Zo ontstaan achterdeuren: niet met een besluit, maar met een precedent. Het scherm
> is omgezet, de lijst is weg."

Hij staat als slot van het kop-commentaar (r486–513) boven `scanLijstkopOvertredingen` (r515).

### 1.2 De canonieke regel (likara-tests §Bronscans, bullet vanaf **r374**)

> "**Geen benoemde uitzondering — een uitzondering is een achterdeur (LI047).** Vraagt een geval
> om een uitzondering in de scan, dan is meestal **het GEVAL fout, niet de regel**; en wie er één
> opneemt, verbreedt de volgende. Moet er tóch iets buiten vallen, laat het dan **afleiden**
> i.p.v. opsommen — … **Een zichtbare uitzondering is óók een achterdeur (LI048):** hij doet geen
> schade, hij legitimeert een VORM — het volgende geval dat niet past heeft dan een voorbeeld; zo
> ontstaan achterdeuren, niet met een besluit maar met een precedent. **Toets bij een uitzondering
> niet 'richt hij schade aan?' maar 'welke vorm maak ik navolgbaar?'** — en kijk eerst of het
> geval zelf op te lossen valt. (Frontend-casussen …: likara-frontend §LI040-patronen.)"

### 1.3 Verschilanalyse

| Categorie | Inhoud |
|---|---|
| **Gedeeld** (comment = korter §Bronscans) | geen schade + elke run afgedrukt · "legitimeerde een VORM" · het volgende-geval-heeft-een-voorbeeld · "achterdeuren ontstaan met een precedent" (interpunctie wijkt af: ":" vs "—") |
| **§Bronscans heeft, comment mist** (de drift) | de "**het GEVAL is fout, niet de regel**"-uitweg · de toets "welke vorm maak ik navolgbaar?" · "kijk eerst of het geval zelf op te lossen valt" · de LI047-eerste-vorm + afleiden-i.p.v.-opsommen-context · de LI048-marker |
| **Uniek in de comment** (codespecifiek, §Bronscans heeft het níét) | de harde instructie "**GEEN UITZONDERINGENLIJST**" voor déze functie · de casus-áfloop "**Het scherm is omgezet, de lijst is weg**" — het feit dat `LIJSTKOP_OPENSTAAND` hier verwijderd ís en een terugkeer dus een regressie zou zijn |

**Conclusie 1.3:** de comment is **niet volledig vervangbaar** door een kale verwijzing — het
codespecifieke deel (de geen-lijst-instructie + de afloop) hoort bij deze functie; alleen de
algemene moraal-zinnen zijn de driftkopie.

---

## Blok 2 — wat de comment functioneel doet

1. **De code eronder** (r515 e.v.): `scanLijstkopOvertredingen(bron, label)` — de lijstkop-scan
   die bewust **geen skip-/uitzonderingenlijst** heeft. De comment is een
   **ontwerpbesluit-verklaring**: waaróm deze functie geen `LIJSTKOP_OPENSTAAND`-lijst (meer)
   draagt en waarom die er niet terug mag komen.
2. **Begrijpelijkheid bij een verwijzing:** de code blijft volledig te onderhouden als het
   codespecifieke deel blijft staan ("GEEN UITZONDERINGENLIJST. Er stond er even één in
   (BedrijfsfunctieLijst) … het scherm is omgezet, de lijst is weg") met de moraal als
   verwijzing — de onderhouder hoeft de volledige les niet ter plekke; hij moet alleen weten
   dát er geen lijst mag komen en wáár de regel staat.
3. **Een mjs-comment-verwijzing ís scan-bewaakt — empirisch bevestigd:**
   `check-css-build.mjs` zit in het scanbereik (gemeten: aanwezig in `_scan_bestanden()`), en
   een gesimuleerde comment-verwijzing gedroeg zich correct: `likara-tests §KopDieNietBestaat`
   → **ROOD**, `likara-tests §Bronscans` → stil. Anders dan de LOKAAL-TESTEN- en
   CLAUDE.md-gevallen zou een verwijzing hier dus wél bewaakt zijn tegen een latere
   kop-hernoeming.

---

## Blok 3 — de opties (gemeten, geen keuze)

| Optie | Gevolg | Raakt verwijzingen? | Suite/css-build |
|---|---|---|---|
| **(a)** moraal-zinnen → bewaakte verwijzing "…waaróm: likara-tests §Bronscans", codespecifiek deel blijft | drift weg; één canonieke bron; verwijzing scan-bewaakt (Blok 2.3) | 0 bestaande verwijzingen naar deze comment (gemeten: geen treffers buiten vastleggingen) | comment-only: de mjs-zelftests toetsen scan-gédrag, niet commentaar; de nieuwe tekst bevat geen class-literals (Tailwind-candidate-regel geldt hier — geen aaneengesloten te-detecteren klassen in de verwijzing opnemen) |
| **(b)** alleen codespecifiek deel behouden, moraal weg zónder verwijzing | drift weg, iets minder tekst; maar de onderhouder verliest de vindplaats van het waaróm (moet zelf weten dat §Bronscans bestaat) | idem 0 | idem |
| **(c)** laten staan | de derde regel-drager blijft, incompleet (mist de uitweg én de toets); drift groeit bij elke aanscherping van de canonieke regel | n.v.t. | n.v.t. |

---

## Blok 4 — bewaking

1. `git status` schoon · branch `master` · HEAD `049c4c9` · scan **5 passed**.
2. **De mjs-zelftests en een comment-wijziging:** `check-css-build.mjs` draait eigen zelftests
   (o.a. `LIJSTKOP_ZELFTEST`, r575/623–634: 7/7 "de scan bijt") die de **functies** voeden met
   nagebootste bronnen — ze lezen het eigen commentaar niet. Een comment-only wijziging raakt ze
   niet; laatste run groen ("kop-rij-scan-zelftest 7/7", "kopstijl-scan 41 schermen"). Eén
   voorbehoud staat al in de eigen regels: geen aaneengesloten class-literal in de nieuwe
   comment-tekst zetten (Tailwind-candidate-valkuil, §Bronscans/LI035).

---

## Wat je tegenkwam (buiten de vragen)

1. **De les-familie heeft nu vier vindplaatsen**: canoniek (tests §Bronscans r374-blok) ·
   toepassing (frontend §LI040-patronen, de uitzondering-les-bullet) · deze mjs-comment · de
   OPVOLGPUNTEN-verwijzing (r1905, wijst sinds verhuizing 3 naar §Bronscans). De mjs is de enige
   die géén verhouding tot de canonieke bron uitspreekt.
2. **De comment-versie is ouder dan de skill-versie ooit was**: hij mist elementen die de
   skill-tekst al vóór verhuizing 3 droeg (de GEVAL-uitweg stond in de frontend-versie) — de
   drift ontstond dus al bij het schrijven, niet door de verhuizing.
3. Het kop-commentaar erbóven (r486–507, de (a)–(e)-regels) is **geen** driftkopie: dat is de
   codespecifieke documentatie van wat déze scan afdwingt en heeft geen canonieke tweeling —
   buiten dit besluit.

*Einde meting. Werktree ongewijzigd behalve dit rapport.*
