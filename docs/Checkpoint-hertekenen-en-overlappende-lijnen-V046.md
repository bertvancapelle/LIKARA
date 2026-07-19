# Checkpoint — wanneer legt de kaart opnieuw, en wanneer verdwijnt een relatie uit beeld?

| | |
|---|---|
| **Sessie** | LI046 · V046 · read-only feitenopname vóór ontwerp |
| **Datum** | 2026-07-19 |
| **Modus** | Niets gewijzigd behalve dit bestand; niets gebouwd; niet gecommit |

**Uitkomst in één zin:** de kaart **wordt** bij elke gevolgde handeling opnieuw gelegd (volledige
deterministische herbouw — géén stille stale-posities), dus waarneming (1) is grotendeels een
gevolg van de **deterministische layout die de knopen op een vaste regel plaatst en dus niet naar
de relaties schikt**; de ergste, waarneming (2), is reëel en **niet afgevangen buiten de flow-ring**:
twee relaties van verschillende ringen tussen hetzelfde knopenpaar worden als twee losse bezier-lijnen
op (nagenoeg) dezelfde plek getekend **zonder enig signaal** dat er meer dan één ligt — al komt dat
geval in de huidige dev-data (nog) **0×** voor.

> Vindplaatsen: `modules/bwb_ontvlechting/frontend/views/LandschapskaartView.vue` (**LKV**),
> `modules/bwb_ontvlechting/backend/services/landschapskaart_service.py` (**svc**).

---

## Blok 1 — Wanneer legt de kaart opnieuw?

**Het mechanisme.** Eén centrale re-layout-watcher (**LKV:2763-2773**) reageert op:
```
[ getekendeNodes.value.map(n => n.id).join('|'),   // node-ID-compositie
  zichtbareEdges, modus, weergave, lezing, groepeerPerOrg,
  verbergLegeLanes, laneVolgorde, toonRegistratiegaps ]
```
→ `_planRedraw` (microtask-**coalesce**, geen tijd-debounce; **LKV:2757-2762**) → `_hertekenNu` →
**`tekenGraaf`** (**LKV:2467-2486**): `cy.elements().remove()` → `cy.add(_elementen())` →
`cy.layout(_layout()).run()`. **Elke trigger is een volledige re-layout** (herpositie), geen
incrementele add/highlight. **Positie-behoud is bewust verwijderd** (`vorigePosities`, comments
LKV:2438-2441/2479-2480). History-herstel tekent synchroon buiten de coalesce (`_herstellen`, LKV:2769).

**Handeling → wordt opnieuw gelegd?** (elke handeling raakt ≥1 watch-key)

| Handeling | Relayout? | Keten |
|---|---|---|
| Component toevoegen aan set | **Ja** | `toggleSet` → `actieveSet` → herfetch-watch (LKV:894) → `herlaadGraaf` → `getekendeNodes` |
| Component verwijderen uit set | **Ja** | idem |
| View openen | **Ja** | zet set/filters/ringen → set-watch + `getekendeNodes`/`zichtbareEdges` |
| Standaardkijk toepassen (`_pasKijkToe`, LKV:529) | **Ja** | zet ringen/filters/diepte/… → watch-keys (raakt bewust niet set/weergave) |
| Filter zetten/wijzigen (type/lev/host/lifecycle/rol/BIV) | **Ja** | filter-refs → `_bepaalZichtbaar` (LKV:740) → `zichtbareNodes` → `getekendeNodes` |
| Ring aan/uit (`toggleRing`) | **Ja** | `ringAan` → `_edgesBinnen` (LKV:767) → `zichtbareEdges` (watch-key) |
| Diepte wijzigen (`zetDiepte`) | **Ja** | `diepte` → `herlaadGraaf` (nieuwe subgraaf-fetch) |
| Organisatie-scope (`toggleScopeOrg`) | **Ja** | `scopeOrgs` → `_inScope` → `zichtbareNodes` |
| Afpel-modus | **Ja (mits filter actief)** | `opbouwModus` → `_bepaalZichtbaar`-tak (LKV:755) |
| Hele landschap tonen | **Ja** | leegt set + `heleLandschap=true` → set-watch → volledige graaf |
| Terugkeer uit detail / deep-link | **Ja** | via `onMounted` + `route.query.center` (geen `props.id`-watcher — zie noot); `herlaadGraaf` |
| F5 / reload | **Ja** | remount → `onMounted` herstelt `lk-state`/standaardkijk → `herlaadGraaf` |

**Noot:** er is **geen `props.id`-watcher**; "terugkeer uit detail" loopt via set/route-state bij
(re)mount, niet via een prop-watch (**niet vastgesteld** zoals in de vraag geformuleerd).

**Reageert het op knopen én op lijnen? — JA, op beide.** De watch keyt níét alleen op de node-ID-
compositie: `zichtbareEdges` staat expliciet als tweede source (**LKV:2766**, comment 2743-2745). Een
wijziging die alléén edges/zichtbaarheid raakt (ring togglen) leidt dus óók tot een volledige relayout.

**Waar zit dan het verschil met de waarneming?** De layouts zijn **deterministisch en regel-gebaseerd**
(grid op volgorde / concentric op ego-afstand / preset-banen — Blok 5): dezelfde node-set geeft
**dezelfde posities**. Re-leggen met een gewijzigde inhoud maar gelijke node-set ziet er dus uit als
"de plattegrond veranderde niet", en de ordening **weerspiegelt nooit de relaties** (dat is de bewuste
ADR-040-keuze tegen force-layout). De hypothese "oude posities blijven stil staan" wordt door de code
**tegengesproken** (geen `vorigePosities`); de indruk komt van de vaste layoutregel, niet van stale state.

---

## Blok 2 — Wat gebeurt er bij filteren?

- **Verwijderen, niet verbergen.** `_bepaalZichtbaar` (LKV:740-762) reduceert `grafNodes` tot een
  kleinere array; `tekenGraaf` doet `remove()` + `add(_elementen())` → weggefilterde nodes/edges zijn
  **fysiek afwezig**, niet gedimd. Dim/opacity (`_pasDim`, LKV:1901-1933) wordt **alleen** door selectie
  (`geselecteerdNodeId`) of de legenda-typefilter gedreven — **niet** door de attribuutfilters.
- **Geen positie-behoud** (zie Blok 1). De overgebleven knopen krijgen nieuwe posities uit de
  deterministische layout op de resterende set.
- **Geen gaten of opeenhopingen:** de layout draait volledig opnieuw op alléén de overgebleven set en
  `_naLayout` fit op het geheel (LKV:2309) → compacte herplaatsing, geen lege plekken waar iets weg is,
  geen stapels "verdwenen" knopen.

---

## Blok 3 — Overlappende lijnen

**Edge-stijl (`CY_STYLE`, LKV:2527-2539):** `'curve-style': 'bezier'` (LKV:2530), vast voor **alle**
edges. **Géén parallel-edge-scheiding geconfigureerd** — geen `control-point-step-size`/`-distances`,
geen `haystack`, geen expliciete boog/offset. (Cytoscape's bezier buigt parallelle edges standaard
íéts uit elkaar, maar dat is render-afhankelijk en niet in de code gezet/geborgd — **niet vastgesteld**
of dat twee overlappende ring-lijnen zichtbaar onderscheidbaar maakt.) Per-ring lijnstijl: `samenstelling`
dashed (LKV:2070), `organisatiestructuur` dotted (LKV:2073), rest solid; kleur uniform default `#94a3b8`.

**Layouts (`_layout`, LKV:2409-2465):** grid (Overzicht) / concentric (Praatplaat) / preset (Lagen);
`avoidOverlap`/`minNodeSpacing`/`nodeDimensionsIncludeLabels` betreffen **node-**overlap, **niet** edge-overlap.

**Kunnen twee verschillende relaties tussen hetzelfde paar op dezelfde plek liggen? JA (in code).**
- Backend groepeert **alleen `flow`** (ring `applicaties`) per gericht paar tot één edge met `aantal`
  (svc:329-380, `aantal=len(groep)` :371-380). `assignment/association/serving/aggregation` gaan
  **één-per-rij, ongegroepeerd** (svc:350-369).
- Frontend maakt per relatietype een **aparte** cytoscape-edge: id = `e{i}-{bron}-{doel}-{relatietype}`
  (LKV:2095). Twee relaties op hetzelfde `(bron,doel)` met verschillend type → twee aparte bezier-lijnen.
- `flow` én `aggregation` verbinden **beide** component→component (svc:348 vs 362) → code-technisch kunnen
  ze op hetzelfde paar samenvallen. **Niet afgevangen.**

**Hoe vaak in de dev-data? (`SELECT`)**
```sql
-- cross-ring overlap: ongeordend paar met >1 distinct relatietype
SELECT count(*) FROM (SELECT least(bron_id::text,doel_id::text) a, greatest(bron_id::text,doel_id::text) b
  FROM relatie GROUP BY 1,2 HAVING count(distinct relatietype) > 1) x;              -- 0
-- component↔component paren met zowel flow als aggregation
… -- 0
-- gericht paar met >1 relatie (alle flow)                                           -- 5
-- ongeordend paar met >1 relatie (incl. A→B + B→A)                                  -- 4
-- totaal per type: aggregation 307 · flow 29 · association 12 · serving 11 · assignment 6
```
→ **Cross-ring overlap komt in de huidige dev-data 0× voor.** Het enige meervoud is **flow** (door de
`aantal`-groepering afgedekt tot één lijn) plus **bidirectionele** flow-paren (A→B én B→A = twee
gerichte edges tussen hetzelfde knopenpaar; de groepering merget tegengestelde richtingen **niet**).

**Lijnen dwars door een knoop / langs elkaar:** **niet vastgesteld** — puur render-afhankelijk. Er is
geen edge-routing/-bundling; of een bezier dwars door een derde, niet-verbonden knoop loopt hangt af
van de door de layout toegewezen posities. Geen code die dit voorkomt.

---

## Blok 4 — Kan de gebruiker merken dat hij iets mist? (DE KERN)

**Nee — buiten de flow-ring is er geen enkel signaal.**

- **Relatie-telling:** er is **geen** edge-/relatie-telling. De enige telling is `zichtbaarAantal =
  getekendeNodes.length` ("… in beeld", LKV:2260/2822) — die telt **knopen**, niet relaties.
- **"N×"-aantal:** verschijnt **alleen** voor flow, **alleen** als tekst ín het edge-label
  (`e.aantal >= 2 ? "N×"`, LKV:2082), en dat label is **default onzichtbaar** (`text-opacity: 0`,
  LKV:2536) — pas zichtbaar bij **hover** (LKV:2713) of op een aangeklikte edge. De andere ringen tonen
  nooit een aantal.
- **Edge-klik-popup (`openEdgePopup`, LKV:1662-1710):** de master-detail die **álle** onderliggende
  relaties van het paar oplijst bestaat **alleen voor de flow-ring** (API-call `paar_bron_id/paar_doel_id,
  relatietype:'flow'`, LKV:1681, "ook bij n=1"). Voor **alle andere ringen** toont de popup **precies één**
  relatie (`_EDGE_TAKKEN`, LKV:1566-1631). Bovendien resolvet de edge-tap op `(bron, doel, ring)`
  (LKV:2702): ligt er een edge van een **ándere** ring onder, dan komt die **niet** in de popup — je opent
  de popup van de aangeklikte ring, de rest blijft onzichtbaar.
- **Verschil "één relatie" vs "twee op elkaar":** *binnen* de flow-ring waarneembaar (N×-hoverlabel +
  master-detail). *Over ringen heen* (flow vs association vs serving vs aggregation op hetzelfde paar):
  **niet waarneembaar** — geen teller, geen badge, de klik-popup toont maar één ring, de node-telling telt
  geen relaties. **Er is geen enkel code-signaal dat meldt dat onder een lijn nog een relatie van een
  andere ring ligt.**

→ **Urgentie-oordeel:** het stille verlies bestaat, maar manifesteert zich in de huidige dev-data (nog)
niet als cross-ring-overlap (0 gevallen). Het risico is structureel-in-de-code, niet acuut-in-de-data.

---

## Blok 5 — Reikwijdte

- **Weergaven:** het **mechanisme** (volledige remove/add/layout via dezelfde watch + `tekenGraaf`) is
  identiek op alle drie. De **layout** verschilt: Overzicht `grid` (centrumloos), Praatplaat `concentric`
  (radiaal + ellips-transform, LKV:2272), Lagen `preset` (baanposities + meet-stap, LKV:2423-2436). De
  overlap-eigenschap (bezier, geen parallel-scheiding) geldt in alle drie.
- **Set-omvang:** cross-ring-overlap hangt niet aan omvang maar aan de data (nu 0). Bidirectionele
  flow-paren en coincidentele kruisingen worden waarschijnlijker naarmate de set groter/dichter is
  (meer edges op dezelfde posities). Indicatie dev-data: 29 flows, 4 ongeordende meervoud-paren; 307
  aggregation-edges (samenstelling, dashed) vormen de dichtste laag.
- **Kolom-verberging (net gebouwd):** het verschijnen/verdwijnen van de linker-`aside` (`v-if="heeftData"`)
  wijzigt de canvasbreedte → opgevangen door de **ResizeObserver** → `_pasCanvasMaat` (LKV:1772-1775):
  **`cy.resize()` + `cy.fit()`, géén re-layout**. Knopen verspringen niet (alleen herpassen/hercentreren);
  de overlay-hersync loopt mee op `pan zoom resize`. → raakt het relayout-/overlap-vraagstuk niet.

---

## Blok 6 — Verrassingen, risico's en open vragen

**Eerdere besluiten (sluit hierop aan, niet los oppakken):**
- **ADR-040** (kaart-herbouw): deterministische teken-cyclus; **Overzicht = grid**, **Praatplaat =
  concentric** (LKV/ADR-040:168-182); `cose`/`fcose` **afgeschaft** wegens de "edges-onzichtbaar"/
  samenval-bug. **Layout-invariant "geen twee nodes op dezelfde positie"** geborgd in
  `frontend/tests/kaartLayout.test.js` — **maar dat is NODE-samenval, niet edge-overlap.**
- **ADR-023a Fase 3/4** (`docs/OPVOLGPUNTEN.md:1365-1372`, DC017): kaart-edge-groepering — meerdere
  **flows** per `(bron,doel)` → één lijn + telling vanaf 2 + universele master-detail. **Flow-only.**
- Geen ADR/opvolgpunt gevonden voor "overlappende lijnen van **verschillende** ringen tussen hetzelfde
  paar" — dat geval valt buiten beide besluiten.

**Verrassingen:**
- De waarneming "kaart legt niet opnieuw" wordt door de code **tegengesproken** (elke handeling relayout);
  de echte oorzaak is de **deterministische, relatie-onbewuste layout** (ADR-040-trade-off).
- De overlap-voorziening (`aantal`) is **flow-only**; het cross-ring-geval is nergens afgevangen — maar
  komt in de dev-data 0× voor.
- Bidirectionele flow (A→B + B→A) is meervoud dat de groepering **niet** merget (twee gerichte edges,
  zelfde knopenpaar).

**Stille keuzes die een oplossing zou moeten maken (niemand heeft ze genomen):**
- Is de "ordening klopt niet"-klacht een reden om de **deterministische layout te vervangen** door een
  structuur-tonende (kruisings-minimaliserende) layout — terwijl ADR-040 force-layout bewust afwees?
- Moet meervoud **over ringen heen** worden geteld/gesignaleerd, of blijft dat flow-only?
- Moet de edge-klik-popup **álle** relaties tussen het paar tonen (over alle ringen), niet alleen de
  aangeklikte ring?

---

## Open ontwerpvragen voor Bert

1. Is de prioriteit de **onderscheidbaarheid van overlappende lijnen** (waarneming 2), of de **ordening/layout** (waarneming 1) — of beide, en in welke volgorde?
2. Moet meervoud **over ringen heen** merkbaar worden (een teller/badge "N relaties tussen dit paar" ongeacht type), of volstaat de bestaande flow-only `aantal`?
3. Moet de **edge-klik-popup** álle onderliggende relaties tussen het paar tonen (alle ringen samen), i.p.v. alleen de aangeklikte ring?
4. Willen we een **relatie-telling** op de kaart ("Y relaties in beeld") naast de bestaande node-telling?
5. Moet **edge-samenval** een geborgde layout-invariant worden (uitbreiding van de node-only `kaartLayout.test.js`), of is dat render-detail?
6. Vraagt "de ordening klopt niet" om een **andere layout** (structuur-tonend / kruisings-arm) — met heropening van de ADR-040-keuze tegen force-layout — of om **expliciete edge-scheiding** (boog/offset/`control-point-step-size`) binnen de bestaande deterministische layout?
7. Telt de **bidirectionele flow** (A→B + B→A) als "twee lijnen die één moeten lijken" (mergen), of juist als twee te tonen richtingen?

*(STOP na dit rapport. Geen vervolgstap gebouwd. Niet gecommit.)*
