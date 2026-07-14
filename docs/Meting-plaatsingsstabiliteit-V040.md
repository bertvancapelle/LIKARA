# Meting — plaatsingsstabiliteit tussen twee GEMMA-releases

| | |
|---|---|
| **Opdracht** | LI040-meting-plaatsingsstabiliteit-v2 |
| **Datum** | 2026-07-13 |
| **Modus** | Read-only bestandsvergelijking + één geautoriseerde ophaalactie (twee HTTP-calls: commit-hash-lookup via de GitHub-API + raw-download op die hash). Geen import tegen de DB, geen code, geen commit. Meetscript in het sessie-scratchpad (buiten de repo). |
| **Methode** | **De bestaande LIKARA-parser** (`services/ameff.py`, `lees_ameff`) voor béide bestanden — de meting ziet exact wat een echte inlees zou zien (zelfde identifier-, naam- en aggregation-extractie, zelfde XXE-/vormguards). Geen eigen XML-interpretatie. |

**De twee bestanden:**

| | Release A (oud) | Release B (nieuw, gecureerd) |
|---|---|---|
| Bestand | `export/GEMMA release.xml` op commit **`7bcba2ad3888`** (2025-10-11, "Release") — opgehaald naar het sessie-scratchpad, **niet** in de repo geplaatst | `modules/bwb_ontvlechting/backend/referentiemodellen/GEMMA_release_2026-07-01.xml` (commit-gepind `de0984717e69`, 2026-07-01, "Release: Actief openbaarmaken") |
| Grootte | 13.307.499 bytes | 13.411.843 bytes |
| SHA-256 | `682ac4d6df463ac42a521f3af6ee4104a10fbb9258fcfca92df12646b819834c` | `b844f184cd960293a1e6ce690b159353130e81798ee851a8ce97ff3edf0d4cf1` (conform `HERKOMST.md`) |
| Bedrijfsfuncties | **296** | **297** |
| Aggregation-plaatsingen (BF↔BF) | **301** | **302** |

Beide vingerafdrukken zijn vastgelegd in de nieuwe releasegeschiedenis in
`modules/bwb_ontvlechting/backend/referentiemodellen/HERKOMST.md` (§6 van de opdracht) —
daarmee is deze meting, en elke volgende driftmeting, exact reproduceerbaar zonder de
bestanden zelf te bewaren.

---

## 1. Uitkomst in één zin

**Tussen de twee releases (9 maanden uiteen) is het aantal verhangen plaatsingen exact 0**
— alle 301 plaatsingen uit oktober 2025 bestaan ongewijzigd in juli 2026 (100%), de enige
wijziging is één nieuwe plaatsing voor de éne nieuwe functie, en er is niets vervallen en
niets in meervoud verschoven; de plaatsing was over dit interval dus een volkomen stabiel
anker.

---

## 2. Contra-check — identifier-stabiliteit gereproduceerd: **JA, exact**

| Verkenning (LI039) | Deze meting |
|---|---|
| 296/296 identifiers ongewijzigd aanwezig | **296/296** ✓ |
| 0 verdwenen · 0 hernoemd-met-nieuwe-id | **0 verdwenen** ✓ |
| 1 nieuwe functie: "Actieve openbaarmaking van informatie", onder "Openbare informering" | **1 nieuw: `id-f157a282d0d14d19bbc7a9483b619bfb` — "Actieve openbaarmaking van informatie", geplaatst onder "Openbare informering" (diepte 3)** ✓ |

Dit zijn aantoonbaar dezelfde releases als in de verkenning; de plaatsingsmeting hieronder
vergelijkt dus het juiste paar.

---

## 3. De tabel

Plaatsing = (ouder-functie, kind-functie) op **bronsleutel** (identifier), conform de
parser/het import-plan.

| # | Categorie | Aantal | Toelichting |
|---|---|---|---|
| 1 | **Ongewijzigd** (paar in A én B) | **301** | 100% van release A |
| 2 | **Verhangen** (kind blijft, andere ouder) | **0** | — |
| 2a | — binnen dezelfde tak | 0 | |
| 2b | — naar een andere tak/domein | 0 | |
| 2c | — van één naar meerdere ouders of omgekeerd | 0 | |
| 3 | **Nieuw** (paar alleen in B, kind nieuw) | **1** | de plaatsing van de nieuwe functie |
| 4 | **Vervallen** (kind verdwijnt uit B) | **0** | geen enkele functie verdween (contra-check) |
| 5 | **Meervoud-verschuiving** (≥1 plaatsing behouden, één erbij/eraf) | **0** | de 13 meervoud-paren (7 functies met 2–4 ouders) zijn in beide releases **identiek** |

Sluitende rekensom: A = 301 paren → 301 ongewijzigd + 0 weg; B = 302 paren → 301
ongewijzigd + 1 nieuw. Er is geen enkel paar verdwenen, dus categorie 2/4/5 zijn alle
leeg per constructie én per meting.

---

## 4. De lijst verhangen plaatsingen

**Leeg — er zijn er nul.** (De meetmethode voor de 2a/2b/2c-uitsplitsing — tak-bepaling
via wortel-voorouders, diepte via kortste pad omhoog, cyclus-veilig — is gebouwd en
gedraaid; hij trof een lege verzameling. Bij een volgende release-vergelijking is dezelfde
uitsplitsing direct herbruikbaar.)

Ter volledigheid de éne structurele wijziging (categorie 3, onschadelijk):

| Bronsleutel | Naam | Plaatsing | Diepte |
|---|---|---|---|
| `id-f157a282d0d14d19bbc7a9483b619bfb` | Actieve openbaarmaking van informatie | nieuw onder "Openbare informering" | 3 |

---

## 5. De weging

Bij 0 verhangen plaatsingen is er niets te wegen; ter context de boomvorm waarin een
registratie zou leven (release B, gemeten):

- **8 wortels** (domeinen) · **297 functies** · **231 bladeren** (78%).
- Diepteverdeling: diepte 0: 8 · diepte 1: 46 · diepte 2: 136 · diepte 3: 105 · diepte 4: 2.
- De meervoudsstructuur (7 functies met 2–4 ouders, 13 extra paren boven één-ouder) is
  tussen de releases **onveranderd** — óók het beweeglijkst denkbare deel van de boom
  (gedeelde subfuncties onder domein-varianten) bleef stil liggen.

Wat ik **niet** hard kon maken (en ook niet hoefde bij een lege categorie 2): welke
functies "realistisch koppelbaar" zijn — er bestaat nog geen koppeling in LIKARA (gate 2
ongebouwd), dus elke koppelbaarheidsaanname zou een gok zijn. De ruwe cijfers hierboven
(231 bladeren, 78%) zijn de feitelijke bovengrens van waar geregistreerd zou worden.

---

## 6. Wat dit betekent voor knoop 2 (feitelijk doorgerekend, geen aanbeveling)

- **Bij dít release-paar: 0 geraakte registraties, ongeacht de vullingsgraad.** Zelfs in
  het maximale scenario — een registratie op élk van de 301 plaatsingen — zou de
  herinlees van juli 2026 er **nul** hebben verwijderd: het import-delta bestond uit
  uitsluitend 1 toevoeging (en het `verwijder_plaatsing`-pad, `voer_uit:389-395`, zou 0×
  vuren).
- **De frequentiekant van knoop 2 is daarmee gemeten op n=1 interval: 0 verhangingen per
  9 maanden.** De risico-kant blijft wat het feitenrapport beschreef: *áls* VNG ooit
  verhangt, verdwijnt de rij hard en de registratie ermee (afhankelijk van de FK-keuze).
  De meting zegt dat dit gebeurtenis-type in het gemeten interval niet voorkwam; ze zegt
  niet dat het niet kán (zie §8).
- Ter kalibratie van de andere categorieën: het enige dat wél gebeurde (1 nieuwe functie
  + 1 nieuwe plaatsing) is precies de categorie waar geen registratie aan kan hangen.

---

## 7. Contra-check-verklaring bij de aantallen

De verkenning/HERKOMST noteert voor release B "302 aggregation-relaties BF↔BF"; deze
meting via de parser komt op exact hetzelfde getal uit (302), en op 301 voor release A —
consistent met 296 functies + dezelfde meervoudsstructuur. Geen discrepanties tussen
parser-uitkomst en eerdere handmatige tellingen.

---

## 8. Wat ik NIET heb kunnen vaststellen

- **Dit is één release-paar (n=1).** De meting bewijst stabiliteit over dít interval van
  ~9 maanden; ze is geen garantie voor toekomstige releases. VNG geeft geen formele
  id- of structuur-stabiliteitsbelofte (verkenning §B2); een grote GEMMA-herstructurering
  blijft mogelijk en zou door deze meting niet voorspeld worden. De releasegeschiedenis in
  `HERKOMST.md` maakt een herhaalmeting bij elke volgende release goedkoop.
- **Tussenliggende niet-release-commits** (bv. 2026-06-30 "diverse kleine fixes") zijn
  niet gemeten — bewust: LIKARA leest per gecureerde release in, dus release→release is
  de relevante vergelijking.
- **Koppelbaarheid per functie** (welke bladeren in een echt landschap daadwerkelijk een
  component dragen): niet vaststelbaar zonder gebouwde gate 2; alleen de bovengrens (231
  bladeren) is een feit.
