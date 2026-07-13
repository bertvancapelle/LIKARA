# Verkenning — het GEMMA-bedrijfsfunctiebestand (AMEFF)

| | |
|---|---|
| **Opdracht** | LI039-verkenning-gemma-ameff (ophalen + lezen + rapporteren; niets gebouwd) |
| **Datum** | 2026-07-12 |
| **Werkplek bestand** | Sessie-scratchpad, búíten de repo (`GEMMA_release.xml` + de okt-2025-versie ter vergelijking) — committen pas ná bekrachtiging |
| **Basis** | ADR-043 (besluiten LI039) · `docs/Feitenrapport-inlezen-referentiemodel-V040.md` |

---

## 1. Herkomst — dit is wat Bert bekrachtigt

- **Bron:** officiële VNG Realisatie GitHub-repository **`VNG-Realisatie/GEMMA-Archi-repository`** ("Samenwerken aan het GEMMA ArchiMate-model"), default branch `master`.
  https://github.com/VNG-Realisatie/GEMMA-Archi-repository
- **Bestand:** `export/GEMMA release.xml` — het **enige** bestand in de export-map; het is de AMEFF-export van het **volledige GEMMA-model** (niet alleen bedrijfsfuncties). Raw-URL:
  `https://raw.githubusercontent.com/VNG-Realisatie/GEMMA-Archi-repository/master/export/GEMMA%20release.xml`
- **Grootte:** 13.411.843 bytes (13,4 MB). **Formaat:** ArchiMate Open Exchange, namespace `http://www.opengroup.org/xsd/archimate/3.0/`, schemaLocation 3.1 (incl. Diagram-schema — het bestand bevat ook views).
- **Versie-aanduiding:** de repo kent **géén tags/releases**; versies = release-commits op het bestand. Recente historie: **2026-07-01 "Release: Actief openbaarmaken"** (de opgehaalde stand), 2026-06-30 "diverse kleine fixes", 2025-10-11 "Release". Repo laatst bijgewerkt 2026-07-08.
- **Licentie:** **EUPL — bevestigd** in de repo-Readme (§Licentie: gebruik/aanpassen/delen toegestaan, mét bronvermelding en share-alike). NB: GitHub's licentie-metadataveld is leeg; de Readme is de bron.
- **Meerdere versies beschikbaar:** ja, uitsluitend via de git-historie van hetzelfde bestand (per release-commit). Er is geen apart "bedrijfsfuncties-only"-bestand.
- **Te bekrachtigen door Bert:** (a) dít bestand als het gecureerde aanbod; (b) wélke commit als versie geldt (voorstelbaar: de release-commit-datum als versielabel — merk op: onze seed-tekst "GEMMA 2 (2025)" komt **niet** uit het bestand; het model heet daarin simpelweg "GEMMA" en draagt geen versienummer).

---

## 2. De drie kritieke vragen

### B1. De boom → **Aggregation-relaties; organizations is presentatie; de topgroeperingen bestaan niet**

- **De hiërarchie zit in `Aggregation`-relaties tussen BusinessFunctions** (ouder = `source`, kind = `target`): **302** stuks. `Composition` tussen functies: **0**. Fragment:
  ```xml
  <relationship identifier="id-6b1df466fbd34b018e21aea7a76e0735"
      source="id-f428d5d5785a46fbb7ffdbda4a431e8b"
      target="id-bdfb9971-8db0-11e3-67ab-0050568a6153" xsi:type="Aggregation">
  ```
- **`<organizations>` is een platte presentatie-indeling**, geen boom: onder Business › Bedrijfsfuncties liggen twee mappen — "(Hoofd)bedrijfsfuncties" (69 refs) en "Sub(sub)bedrijfsfuncties" (228 refs):
  ```xml
  <item><label xml:lang="nl">(Hoofd)bedrijfsfuncties</label>
    <item identifierRef="id-03c32c37-e435-47be-8b71-d143452ea4f9" /> …
  ```
- **Topgroeperingen Besturend / Primair / Ondersteunend bestaan NIET als knopen.** De echte wortels (functies zonder aggregation-ouder) zijn **8**: *Sturing, Ondersteuning, Uitvoering, Klant- en keteninteractie, Ontwikkeling, Regievoering, Bewaking* en *Belastingoplegging* (die laatste een losse knoop: geen ouder én geen kinderen). Er bestaat wél een functie "Besturing" — maar als kínd onder "Sturing".
- **Omvang/diepte:** 297 functies, boom tot **niveau 4** (vijf lagen). Verdeling per niveau (0=wortel, mét dubbeltellingen door meervoudige ouders): 0:8 · 1:46 · 2:140 · 3:113 · 4:3.
- **Meervoudige ouders: JA — 7 functies hebben 2 tot 4 ouders.** Voorbeelden: *"Toezicht"* en *"Handhaving"* hangen elk onder de vier domein-varianten "Toezicht en handhaving …"; *"Afrekening"*, *"Autorisatievaststelling"* en *"Identiteitvaststelling"* onder Verstrekking/Ontvangst(/Vertrouwelijke informering); *"Burgerlijke stand diensten"* en *"Burgerinitiatieven facilitering"* elk onder twee ouders. → **Wrijving met ons één-ouder-model, zie §4.**
- **Tweede as:** 7 `Grouping`-elementen (domeinen: Sociaal domein, Publieksdiensten, Fysieke leefomgeving, Openbare orde en veiligheid, Bestuur, Ondersteuning, Niet domeingebonden) aggregeren 20 functies — een domein-indeling náást de functieboom. Een BF→BF-filter laat deze vanzelf buiten beschouwing.

### B2. De bronsleutel → **het `identifier`-attribuut; stabiliteit empirisch aangetoond over 9 maanden**

- Élk element draagt een `identifier`-attribuut (`id-<uuid>`), **0 functies zonder**. Fragment:
  ```xml
  <element identifier="id-c227565e-0152-4a71-9623-d8e98a8bef0e" xsi:type="BusinessFunction">
    <name xml:lang="nl">Subsidieverlening Publieksdiensten</name>
  ```
- Daarnaast draagt élke functie (297/297) de property **"Object ID"** — dezelfde uuid zónder `id-`-prefix. Een "GEMMA URL"-property bestaat in het bestand maar **niet op de functies** (props op BF: Object ID 297 · Toelichting 169 · GEMMA type 71 · Grondslag 1).
- **Stabiliteitstoets (empirisch, twee releases 9 maanden uiteen):** okt-2025-versie (296 functies) vs. jul-2026 (297): **296/296 identifiers ongewijzigd aanwezig, 0 verdwenen, 0 hernoemd-met-nieuwe-id, 1 nieuwe functie** ("Actieve openbaarmaking van informatie", onder "Openbare informering" — exact de release-titel van 2026-07-01). De identifier overleeft dus releases, inclusief inhoudelijke wijzigingen.
- **Eerlijke kanttekening:** dit bewijst stabiliteit over de gemeten periode/werkwijze (VNG ontwikkelt hetzelfde Archi-model door; Archi bewaart element-id's), **geen formele garantie** — er is geen VNG-document dat id-stabiliteit belooft. Dat restrisico weegt Bert; het alternatief (naam) is aantoonbaar slechter (ADR-043 besluit: nooit op naam).

### B3. De definitie → **`<documentation>` op het element; 10 functies zonder; doorgaans kort**

- De definitie leeft in het `<documentation>`-kind van het element (287/297 gevuld; **10 zonder definitie**). Voorbeeld: *"Het subsidiëren van diverse soorten binnengemeentelijke activiteiten."*
- **Lengte:** min 24 · mediaan 90 · max 3370 tekens. Slechts **17 definities > 200 tekens** en **5 > 400** → de twee-regel-lees-laag past vrijwel altijd; een handvol lange gevallen wordt geknipt en moet zijn volledige tekst ergens kwijt kunnen (de diagram-popup toont nu de volledige tekst — bij 3370 tekens is ook dát fors; weergave-feit voor de bouw-gate).
- Daarnaast draagt **169/297** functies een property **"Toelichting"** — aanvullende vrije tekst náást de definitie (voorbeelden, uitleg). Wat daarmee gebeurt (negeren of meenemen) is een klein ontwerpvraagje voor de bouw-gate.

---

## 3. Wat er nog meer in zit (B4) + het filter

**Totaal 2752 elementen, 5800 relaties, plus views/diagrams.** Elementen per type (top): 522 Constraint · 507 BusinessObject · 426 ApplicationService · **297 BusinessFunction** · 256 ApplicationComponent · 176 BusinessProcess · 142 Grouping · 81 BusinessService · 57 SystemSoftware · 48 BusinessRole · 48 TechnologyService · 43 ApplicationInterface · 31 BusinessActor · en verder Capability/Principle/Goal/DataObject/Driver/Product/… Relaties: 2145 Aggregation · 1388 Realization · 800 Association · 521 Serving · 493 Specialization · 181 Flow · 79 Assignment · **68 Composition** · 62 Triggering · 40 Influence · 23 Access.

**Filteren zonder iets stils weg te gooien:**
- Elementen: `xsi:type="BusinessFunction"` op `<elements>/<element>` — hard en eenduidig. De property "GEMMA type" is **geen** bruikbaar filter (226/297 leeg).
- Boom: uitsluitend `Aggregation`-relaties waarvan **bron én doel** BusinessFunction zijn (302); de domein-Groupings en alle overige relatietypen vallen daarmee vanzelf buiten scope.
- **Niet stil:** het voorbeeld-/importrapport hoort de genegeerde aantallen per elementtype te benoemen ("2455 elementen van 25 andere typen genegeerd") — de eerlijke telling, geen stille weggooi.

---

## 4. Wrijving met ons model (gate 1a)

| # | Bevinding | Aard |
|---|---|---|
| 1 | **7 functies met meervoudige ouders (2–4)** — ons model is één-ouder (composiet self-FK `fk_bedrijfsfunctie_ouder`). Het bestand past dus **niet 1-op-1** op onze boom. | **Ontwerpvraag voor Bert** — geen workaround verzonnen. De 7 gevallen staan in §B1; het gaat om ~2,4% van de functies, systematisch van vorm (gedeelde subfuncties onder domein-varianten). |
| 2 | **De topgroeperingen uit onze seed (Besturend/Primair/Ondersteunend) bestaan niet in het echte model** — de echte wortels zijn de 8 uit §B1. Onze geseede sleutels (`besturend`, `primair`, `ondersteunend`, `dienstverlening`, …) komen **niet** voor in het bestand: een echte import zou ze allemaal **vervallen** markeren en er 297 nieuwe naast zetten. | **Ontwerpvraag/feit** — de GEMMA-achtige demo-seed en het echte model zijn verschillende werelden; hoe de overgang loopt (seed vervangen vóór de import-gate, of de import het laten opruimen) is een bouwkeuze. |
| 3 | Tweede as: domein-`Groupings` aggregeren 20 functies. Ons model kent geen domein-groepering op functies. | Feit; het BF→BF-filter laat ze buiten — maar wel benoemen in het importrapport (niet stil). |
| 4 | Definities: passen in ons `definitie`-veld (Text, onbegrensd); 10 functies zonder definitie (veld nullable — past); max 3370 tekens raakt alleen de wéérgave (twee-regel-clamp + popup). | Geen model-wrijving. |
| 5 | Losse wortel zonder kinderen ("Belastingoplegging") en een boom van 5 lagen: past probleemloos (self-FK, geen dieptegrens). | Geen wrijving. |

---

## 5. Open feiten

1. **Identifier-stabiliteit** is empirisch over 9 maanden/2 releases aangetoond, maar niet formeel gegarandeerd door VNG (§B2) — restrisico ter weging.
2. **Cyclus-vrijheid** van de aggregation-graaf is niet uitputtend bewezen (de traversal bereikte alle niveaus zonder problemen; een geïsoleerde kring buiten de wortels is niet expliciet uitgesloten). De bouw houdt sowieso de bestaande visited-set-discipline aan.
3. **"Toelichting"-property** (169/297): meenemen of negeren — klein ontwerpvraagje.
4. **Versie-aanduiding**: het bestand draagt geen versienummer; het label wordt een curatie-keuze (bv. release-commit-datum). Onze seed-tekst "GEMMA 2 (2025)" heeft geen tegenhanger in het bestand.
5. **Meervoudige-ouders-besluit** (§4.1) — het enige punt waarop het bestand ons model niet past; bepaalt mede het parser-ontwerp.

**Bronnen:** [VNG-Realisatie/GEMMA-Archi-repository](https://github.com/VNG-Realisatie/GEMMA-Archi-repository) (bestand `export/GEMMA release.xml`, master, release-commit 2026-07-01; Readme §Licentie/EUPL) · [VNG Realisatie op GitHub](https://github.com/VNG-Realisatie).
