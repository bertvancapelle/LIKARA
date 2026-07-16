# Horizon na MVP — bron-gedreven opvoeren (denk/ontwikkelrichting)

| | |
|---|---|
| **Status** | **Horizon — géén backlogtaak, géén besluit.** Ligt nadrukkelijk ná blok A / na de MVP-gates en vergt eerst haalbaarheidsonderzoek (zie onderaan). Geen ADR: dit is richting, geen keuze. |
| **Vastgelegd** | LI042 (2026-07-15), opdracht van Bert — docs-only |
| **Verwijzing** | `docs/OPVOLGPUNTEN.md` § "Horizon na MVP — bron-gedreven opvoeren" |

---

## Kernidee (in gebruikerstaal)

Vandaag voert de consultant een applicatie op via een grotendeels leeg formulier — elk veld is
werk. De richting keert dat om: **de consultant bevestigt in plaats van invoert.** Hij zegt "dit
is een Zaakregistratiecomponent", en LIKARA doet op basis van gestandaardiseerde bronnen een
voorzet voor de rest (welke bedrijfsfuncties dit type doorgaans draagt, welke standaarden/
koppelingen, welke afdelingen/gebruikersgroepen). De consultant vinkt aan, stelt bij, verwijdert
wat niet past. Dat raakt LIKARA's kernbelofte recht in het hart: **drempel omlaag, curatie
overeind** — governance-inzicht zonder documentatietraject, nu op het niveau van één applicatie.

Dit is de MVP-belofte doorgetrokken: het formulierveld werd in LI042 al "Bedrijfsfunctie",
koppelen kan al bij het aanmaken. De opvoer-wizard is de rijkere versie van precies dat moment.

---

## Vier samenhangende denklijnen

### 1. AI-ondersteunde vulling (algemeen principe)

AI/sjablonen stellen concept-registratiefeiten voor; **de mens beschikt**. Nooit auto-koppelen.
Een suggestie is zichtbaar een suggestie (niet vermengd met bevestigde feiten). Weet het systeem
het niet, dan blijft het een eerlijk registratiegat in de werkvoorraad — geen gok.

Scope: het **VULLEN** helpen (drempel omlaag). Bewust **buiten scope voorlopig**: een LLM die de
gevulde basis in vrije taal bevraagt — de leeslaag geeft die antwoorden nu al exact en
herleidbaar; een taalmodel eroverheen ruilt betrouwbaarheid in, en betrouwbaarheid is wat een
governance-tool moet leveren.

### 2. Bronnen-import: scheid extractie van deductie

De data ligt vaak al klaar in losse documenten, spreadsheets en ArchiMate-exports. Behandel die
niet als één probleem:

- **ArchiMate** = gestructureerd → extractie, laagste risico, erft de bestaande import-machine;
- **spreadsheets** = half-gestructureerd → AI mapt kolommen → velden, mens bevestigt;
- **losse documenten** = rijkste kennis én hoogste hallucinatie-risico → koppel-voorstellen uit
  proza, altijd met bron én zekerheid.

Harde regel: **elk resultaat draagt zijn bron en zijn zekerheid.** Een geëxtraheerd feit wijst
naar de cel/regel; een gededuceerde koppeling zegt eerlijk "afgeleid, niet letterlijk". Output is
NOOIT een import, altijd een **voorstel-tot-import** (dry-run-preview zoals de AMEFF-import),
regel voor regel bevestigd.

### 3. GEMMA Softwarecatalogus als gestructureerde bron (geen concurrent)

De GEMMA Softwarecatalogus (VNG) bevat per gemeente het feitelijke applicatielandschap: pakket →
GEMMA-referentiecomponent, plus per product de ondersteunde functies en standaarden. Dat is de
applicatielaag — **wát** je hebt. Wat de catalogus NIET doet is de koppeling naar de
bedrijfsfunctie — **waarvóór** het in het werk dient en waar de gaten zitten. **Dat is precies
LIKARA's toegevoegde waarde** (de bedrijfsfunctie-as, de per-plek-gap uit blok A). De catalogus
is dus geen concurrent maar een **bron** — en de gestructureerde bron waarmee je zou moeten
BEGINNEN bij import (laagste risico, extractie i.p.v. deductie). De GEMMA-referentiecomponenten
zelf zijn een tweede referentiemodel naast het bedrijfsfunctiemodel, importeerbaar zoals het
bedrijfsfunctiemodel nu.

### 4. De opvoer-wizard (de concrete, meest LIKARA-eigen invulling — grotendeels ZONDER AI)

Eén doorloop, elke stap een bevestiging i.p.v. een invoer:

- **Stap 1 — wat voor applicatie?** Kies het GEMMA-referentiecomponent (zoek/typeahead).
  Optioneel: het concrete pakket + leverancier. **Onderscheid het referentietype** (stabiel,
  generiek, draagt de functie-voorzetten) **van het concrete pakket** (leverancier/contract/
  versie). LIKARA's kernkoppeling hangt aan het TYPE; het pakket-detail mag optioneel blijven.
- **Stap 2 — waarvoor gebruiken jullie het?** LIKARA toont de bedrijfsfunctie(s) die dit type
  doorgaans draagt, als voorzet uit het referentiecomponent-sjabloon. Aanvinken/bijstellen. Grof
  als vertrekpunt (zoals besloten G9); verfijnen kan later op het detail.
- **Stap 3 — wie is erbij betrokken?** Voorzet voor afdelingen/gebruikersgroepen. Bevestigen/
  bijstellen. (Leunt t.z.t. op het partijenregister, ADR-024.)
- **Stap 4 — klaar.** De applicatie staat met bevestigde koppelingen; niet-bevestigde stappen
  worden registratiegaten in de werkvoorraad. **Geen gedwongen volledigheid — leeg blijft
  eerlijk leeg.**

---

## Niet-onderhandelbare grenzen (dezelfde als de rest van LIKARA)

- **Voorstel-generator, geen invuller.** Voorgesteld ≠ bevestigd, ook visueel (vorm bepaalt
  betekenis).
- **Elke voorgestelde koppeling draagt herkomst** ("voorgesteld vanuit referentiecomponent /
  geëxtraheerd uit bron X, bevestigd door Y") — het model draagt herkomst al; dit wordt een
  herkomst-soort.
- **De leeslaag blijft de enige waarheid**; voorstellen landen als gewone koppelfeiten ná
  bevestiging.
- **Sterke match anders tonen dan zwakke; eerlijk over zekerheid.**

## Open haalbaarheidsvragen (eerst uitzoeken — hier niet beantwoord)

1. Levert de GEMMA-bron de referentiecomponent→bedrijfsfunctie-mapping machine-leesbaar
   (API / ArchiMate-view zoals OS03 / dataset)? Bepaalt of stap 2 échte voorzetten kan doen.
2. Levert de Softwarecatalogus een machine-leesbare export van een tenant-landschap, en hoe komt
   die bij LIKARA (alleen gemeentelijke gebruikers hebben toegang → de tenant levert zelf aan)?
3. Hoe generiek zijn de voorzetten per type (zaak-component = sterk; archief-component = zwak)?

## Fasering (indicatief, ná MVP/blok A)

1. GEMMA-referentiecomponenten als tweede referentiemodel (import zoals bedrijfsfunctiemodel).
2. Opvoer-wizard op de referentiecomponent-sjablonen (grotendeels zonder AI).
3. Softwarecatalogus-export als landschaps-import (extractie, gestructureerd).
4. Pas daarna de rommelige bronnen (spreadsheets, documenten) waar AI-deductie nodig is — begin
   waar verificatie goedkoop is; documenten zijn het kroonjuweel én het grootste
   vertrouwensrisico.
