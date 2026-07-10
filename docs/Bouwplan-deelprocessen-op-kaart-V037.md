# Bouwplan — Deelprocessen eerste-klas op de kaart (V037)

**Opdracht:** LI037_bouwplan_deelprocessen_op_kaart · **Datum:** 2026-07-10 ·
**Basis:** commit a99fe23 / V037 + `docs/Feitenrapport-deelprocessen-op-kaart-V037.md` (alle
vindplaatsen daaruit opnieuw geverifieerd; regelnummers = stand V037). Read-only planfase —
niets gebouwd; de ADR-file is **niet** bewerkt (concepttekst staat in Deel 1).

**Besloten ontwerp (kader, punt 1–6):** hele keten niet weggerold (subboom onder het hoofdproces,
schaalt met de selectie, gap-deelprocessen vallen op) · proceszone leest als boom (hoogte codeert
hiërarchie, groepering per hoofdproces) · leeft in Lagen onder ring `'processen'` ("ring uit wint") ·
twee gelijkwaardige ingangen (ProcesDetail-knop + "Via proces"-beginschermingang) via één gedeeld
handoff-mechanisme, neutraal, in Lagen, herkomst benoemd · enkelklik = inspecteren / dubbelklik =
inzoom op deelproces + directe subboom + vervullers met hoofdproces als terugweg; detail-op-aanvraag
blijft badge → inklap → popup op de vervult-koppelingen · testdata naar 3 niveaus.

### Interpretatiepunten (gemarkeerd — bevestiging gevraagd bij de fase-gates, niet door CC beslist)

- **A1 — vervult-edge landt op het geregistreerde (deel)proces.** Uit punt 1+2 ("component →
  (deel)proces zichtbaar als koppeling"; "ondersteunend systeem onderaan") volgt dat de huidige
  samengetrokken component→**hoofdproces**-bundel wordt **vervangen** door edges per
  (component, **geregistreerd proces**), gebundeld per paar (meerdere functies → `aantal`-badge +
  herkomst = de functies). Het kader spreekt de wortel-bundel niet expliciet af; beide lijnen naast
  elkaar zou dubbel tellen. → bevestigen bij gate fase 1.
- **A2 — boom-layout is Lagen-specifiek; zichtbaarheid volgt de ring in álle weergaven.**
  Vandaag is de proces-knoop bewust zichtbaar in Overzicht én Lagen (geen weergave-conditie —
  `frontend/tests/LandschapskaartView.test.js:978`). Punt 3 ("leeft in Lagen") lees ik als: de
  bóóm-presentatie (hoogte = hiërarchie) is Lagen-only; op Overzicht/Praatplaat zijn deelprocessen
  gewone knopen zolang de ring aan staat. → bevestigen bij gate fase 1.
- **A3 — "opvallen als registratiegap" is presentatie, niet de gaps-toggle.** Een deelproces
  zonder systeem hééft in de keten een hiërarchie-lijn en is dus per definitie niet relatie-loos;
  de bestaande gaps-toggle (relatie-loze nodes) blijft ongemoeid. Het "opvallen" wordt een rustige
  visuele markering op de proces-knoop zonder vervult-edge (eerlijk-gaten-tonen-lijn, likara-ux).
  → invulling (stijl) bij fase 2-browsercheck.

---

## Deel 1 — ADR-034-amendement (concepttekst; landt pas in fase 0 ná akkoord)

**Doelbestand:** `docs/adr/ADR-034_Lagenweergave_swimlane.md`. De sectie
"### ⚠ Bewust openstaand ontwerppunt — proces-diepte (top-1 volgende sessie, NIET afgesloten)"
(r. 205–212) wordt **vervangen** door onderstaande tekst; de rest van het ADR blijft staan.
Daarnaast wordt in de proceslaan-sectie (r. 186–203) één zin geraakt: de interactie-regel
"dubbelklik = hercentreren (praatplaat rond het proces)" (r. 198–199) krijgt de verwijzing
"— herzien voor proces-knopen, zie 'Proces-diepte — besloten (LI037)' hieronder".

> ### Proces-diepte — besloten (LI037): deelprocessen eerste-klas
>
> **Status: Besloten, nog te bouwen** (vervangt het vroegere "⚠ bewust openstaande"
> diepte-punt; de tussenstand "alleen hoofdprocessen" is daarmee geen eindstaat meer maar
> de vertrekbasis van de bouw).
>
> 1. **Hele keten, niet weggerold.** Raakt een component-in-beeld een (deel)proces, dan komt
>    de **volledige subboom onder het bijbehorende hoofdproces** in beeld — inclusief
>    deelprocessen zonder ondersteunend systeem; die vallen op als **registratiegap**
>    (proces zonder systeem — rustige markering, geen blokkade). De omvang schaalt mee met
>    de **selectie** (de ketens die de componenten-in-beeld raken), niet met de hele tenant.
> 2. **De proceszone leest als een boom.** Hoofdproces boven, deelprocessen (en dieper) op
>    rijen eronder, het ondersteunende systeem onderaan; **hoogte codeert de hiërarchie**
>    (geen niveau-label — spiegel van het ADR-042-principe "de plek in de boom ís het
>    niveau"). Deelprocessen zijn **visueel gegroepeerd onder hun eigen hoofdproces**,
>    zodat naburige bomen niet in elkaar overlopen; variabele diepte volgt vanzelf uit
>    "dieper = rij lager".
> 3. **Leeft in Lagen, onder de bestaande ring `'processen'`.** De hele keten —
>    proces-knopen én de deelproces→hoofdproces-lijnen — valt onder die ene ring: ring uit
>    ⇒ de hele keten weg, consistent met "ring uit wint van gaps".
> 4. **Twee gelijkwaardige ingangen, één breed landschap.** (a) "Bekijk op kaart" op het
>    proces-detail en (b) een "Via proces"-zoekingang op het kaart-beginscherm openen
>    **beide** hetzelfde: de volledige boom onder het hoofdproces, **neutraal** (niet
>    gedimd), in **Lagen**, met het **deelproces-van-herkomst benoemd** (waar de gebruiker
>    instapte). Eén gedeeld handoff-mechanisme (uitbreiding van het bestaande
>    consume-once-`kaartHandoff`), één weergave.
> 5. **Klik-gebaren.** Enkelklik op een proces-knoop = **inspecteren** (detailkaart +
>    incidente lijnen oplichten, rest dimt) — als elke andere knoop. Dubbelklik = **bewust
>    inzoomen** op alléén dat deelproces + zijn directe subboom + de vervullende
>    componenten, met het **hoofdproces als klikbare terugweg** naar het brede landschap
>    (dit herziet, voor proces-knopen, de eerdere dubbelklik-regel "hercentreren op de
>    praatplaat"). Onderscheid: de *ingang* toont het brede landschap; de *dubbelklik* is
>    de inzoom. Detail-op-aanvraag (applicatiefunctie / aantal vervul-regels / herkomst)
>    blijft in **badge → inklap → popup** op de vervult-koppelingen — niet in het
>    klik-gebaar op de proces-knoop.
> 6. **Testdata naar 3 niveaus.** Het canonieke scenario (`_seed_bvowb_scenario`) krijgt op
>    minstens één boom een derde procesniveau (processtap onder deelproces) mét vervulling
>    op dat niveau, plus een deelproces zónder systeem (gap-demonstratie), zodat de
>    "diepte = rijhoogte"-belofte browserverifieerbaar is. Puur testdata (reseed), geen
>    migratie.
>
> **Invariant (ongewijzigd):** read-only projectie, engine onaangeroerd, één
> roll-up-bron (dezelfde `procesvervulling` + `ouder_id`-boom-semantiek als
> `rollup_voor_proces`/`subboom` — nooit een tweede bron).

**Verwijzingen elders (benoemd, niets bewerkt):**

- **ADR-042** (`docs/adr/ADR-042_Procesregister_component_in_proces.md:133–134`): de passage
  "Bewust nog niet in deze fase: het proces op de landschapskaart (raakt het
  kaart-component-breed-ADR-spoor)" is sinds LI036 (proceslaan) feitelijk achterhaald en
  verdient in fase 0 een één-regelige statusverwijzing naar ADR-034 §Proceslaan +
  §Proces-diepte-besloten. Geen inhoudelijke wijziging verder nodig.
- **Skill `likara-domeinmodel`** (sectie "LI036 — proceslaan op de kaart … ⚠ BEWUST
  OPENSTAAND diepte-punt"): draagt hetzelfde tussenstand-punt; wordt bij de gebruikelijke
  skill-review (sessie-afsluiting, ná de bouw) bijgewerkt naar de gebouwde realiteit —
  niet nu.
- **Skill `likara-frontend`** (LI036-patronen, "alleen hoofdprocessen"-formuleringen in de
  Lagen-/proces-secties) en **`likara-backend`** (LI036-sectie idem): zelfde afsluit-moment.

---

## Deel 2 — Impact-inventaris (feitelijk; wat beweegt mee)

### 2.1 "Alleen-hoofdproces"-asserties (back- én frontend — beide suites draaien)

- **Backend** — `modules/bwb_ontvlechting/backend/tests/test_landschapskaart_proces.py`:
  docstring r. 5–6 ("…geen proces-nodes zonder vervulling…"), offline test r. 36
  (`test_landschapskaart_serveert_processen_ring`) en live test r. 105–196
  (`test_proces_projectie_rolt_door_naar_hoofdproces_live`: "(a) … ALLEEN het hoofdproces als
  node (deel/subdeel niet)"; "(b) één samengetrokken edge component→hoofdproces: aantal=2 …").
  Deze verwoorden exact het te vervangen gedrag → herschrijven in fase 1 naar: subboom-nodes,
  hiërarchie-edges, fijnmazige vervult-edges (A1), en "wortels zonder geraakte keten blijven
  buiten beeld" (schaalt met selectie). De cyclus-test r. 200
  (`test_proces_projectie_cyclus_veilig_live`) blijft gelden en breidt uit naar de
  neerwaartse traversal. `test_landschapskaart.py` zelf (engine-borging r. 21 + bronscan
  r. 143, schema-velden-tests) blijft ongemoeid geldig.
- **Frontend** — `frontend/tests/LandschapskaartView.test.js:932–996` (describe "LI036 slice 2 —
  proceslaan + ring Processen"): fixture r. 938–942 = één hoofdproces-node + één gebundelde
  edge-met-herkomst. Beweegt mee in fase 2 (fixture wordt een boompje); de asserties
  (a) proceslaan, (c) ring-toggle, (d) tagloos, (e) alle weergaven blijven inhoudelijk geldig.
  `frontend/tests/kaartLayout.test.js:78–90` (echte-cytoscape-layouttest, met proces-node in de
  fixture) breidt uit met boom-rijen (§3, fase 2).
- **Herinnering geborgd in het plan:** elke fase die dit gedeelde gedrag raakt draait **beide**
  suites (ADR-040-les, likara-tests).

### 2.2 `_BAAN_RING` / "ring uit wint van gaps"

Vindplaats: `LandschapskaartView.vue` — `metZichtbareEdge` (edges ná ring-filter, r. 2068–2069),
`heeftRelatie` (álle `grafEdges`, ring-ongeacht, r. 2071–2072), de gap-term r. 2098–2100,
`_BAAN_RING.processen = 'processen'` (r. 2053).

- **Deelproces-knopen en hiërarchie-lijnen onder de proces-ring:** de hiërarchie-edge krijgt
  `ring='processen'` (besluit 3). Een deelproces-knoop heeft dan altijd ≥1 processen-ring-edge →
  ring aan = zichtbaar via `metZichtbareEdge`; ring uit = alle keten-edges weg én (mits geen
  andere ring de knoop draagt — proces-knopen dragen geen andere ringen) de knoop weg. Werkt
  **zonder wijziging** aan de regel zelf; de bestaande ring-toggle-test (r. 964–977) beweegt mee.
- **Gap-deelprocessen (geen systeem):** hebben een hiërarchie-edge → `heeftRelatie` is waar →
  ze vallen NIET onder de gaps-toggle en zijn gewoon zichtbaar via de keten (gewenst per
  besluit 1). Het "opvallen" is een presentatie-markering (interpretatie A3), géén wijziging
  van `gapZichtbaar`.

### 2.3 Component-centrisch set-/ingang-model

Vindplaatsen: `_isApp` (r. 379), `appNodes` (r. 418 — alleen applicaties + organisaties
zoekbaar/selecteerbaar), `componentBuren` (filtert `_isApp`), `SubgraafRequest.component_ids`
(`schemas/landschapskaart.py:82–89`), set-acties (`toggleSet`/`voegComponentenToeAanSet`),
1-set-lid-watch → praatplaat-centrum (r. 931–941).

Wat proces-knopen wél/niet worden (binnen het besloten kader):
- **Geen set-lid** — de set blijft component-ids; de subgraaf-request wijzigt niet. Processen
  komen als **verrijking** mee (zoals nu), alleen breder (subboom i.p.v. wortel).
- **Niet zoekbaar in de gewone component-zoek** (`appNodes` ongemoeid); de "Via proces"-ingang
  volgt het leverancier-/contract-ingang-patroon (`KaartBeginscherm.vue:94–140`): kies proces →
  **emit de vervullende componenten** van de boom naar de set + geef de proces-context via het
  handoff-/openingsmechanisme door. De picker-bron bestaat al: `frontend/../procesZoek.js`
  (`maakProcesZoeker` — treffer altijd mét oudercontext) en `api.processen.subboom/rollup`
  (`frontend/src/api.js:398–400`).
- **Wél eerste-klas knopen op de kaart** (nodes + eigen klik-gebaren, §2.6/fase 4);
  `componentBuren`/`voegBurenToe` blijven component-gericht — de proces-tegenhanger is de
  bestaande vervul-toggle (`popupVervulActie`, r. 1390–1434), die in fase 4 per-(deel)proces-
  knoop gaat werken (huidige aangrijping = hoofdproces-id via `_vervulEdgesVan`, r. 1361).

### 2.4 Instance-projectie / rolbanen + preset-meet-stap

- **Instance-projectie**: processen zijn tagloos en 1-op-1 (geen rol-expansie; geborgd
  `LandschapskaartView.test.js:958–959`; code `instanceProjectie` r. 2158–2164). Deelprocessen
  volgen dat automatisch (zelfde `element_type`); geen botsing.
- **Baanposities**: `laneLayout` (r. 1965–1980) berekent per baan een **plat, alfabetisch grid**
  (`rows = ceil(n/LANE_COLS)`, hoogte = rijen × `NODE_H`) en `_swimlanePositions`
  (r. 2268–2284) plaatst wrap-gewijs. De boom-layout (besluit 2: rij per niveau, groepering per
  wortel) **botst met dit platte grid binnen de proceslaan** → fase 2 geeft de baan `'processen'`
  een eigen positie-tak in beide functies (hoogte = max-diepte × `NODE_H` i.p.v. wrap-rijen;
  x-groepering per wortel). Andere banen ongemoeid. De HTML-band-overlay (`updateBands`,
  r. 2286+) leest hoogte uit `laneLayout` en beweegt vanzelf mee.
- **Meet-stap preset-tak** (r. 2362–2373: `cy.nodes().updateStyle()` + `layoutDimensions` vóór
  het plaatsen): dekt **alle** nodes, dus ook nieuwe deelproces-knopen (zelfde vorm
  `round-rectangle` + pijl-marker, `_vormVoorType` r. 1755). Bestaand mechanisme volstaat; de
  "geen twee nodes op dezelfde positie"-norm (`kaartLayout.test.js`) moet de nieuwe rijen dekken.

### 2.5 kaartHandoff + `?center=`-deeplink

Bestaand (Feitenrapport §C6, opnieuw geverifieerd): `kaartHandoff.js` consume-once-payload
`{ componentIds, grofOnlyIds?, naam? }` — **geen weergave-veld**; `?center=` opent **hard
praatplaat** (`onMounted` r. 2566–2581, voorrang handoff > center > `lk-state` > standaardkijk).
Er is géén mechanisme dat in **Lagen** opent en géén proces-context.

Wat erbij moet (fase 3): additieve handoff-velden, bv.
`{ componentIds, weergave: 'lagen', procesContext: { herkomstProcesId, herkomstNaam, wortelId, wortelNaam } }` —
de kaart zet bij consumptie `weergave='lagen'`, laadt de set (vervullers van de boom), toont de
herkomst benoemd (chip/regel boven de kaart), **neutraal** (geen dim). Beide ingangen
(ProcesDetail-knop; "Via proces") voeden **hetzelfde** payload-pad — één mechanisme (besluit 4).
`?center=`-gedrag blijft ongewijzigd (component-ingang). ProcesDetail heeft de benodigde data al
grotendeels in huis: de voorouder-keten wordt voor de broodkruimel al cyclus-veilig geladen
(`ProcesDetail.vue:34–47`), de wortel is `voorouders[0] ?? proces`; de vervullers komen uit
`api.processen.rollup(wortelId)` + `api.procesvervullingen.lijst({proces_id: wortelId})`
(eigen regels van de wortel — zie §2.6-nuance).

### 2.6 Leespaden — hergebruik, één roll-up-bron

Bestaand: `lijst_voor_component` (r. 240) / `lijst_voor_proces` (r. 198) /
`proces_service.subboom` (r. 231, BFS + visited-set) / `rollup_voor_proces` (r. 282, subboom +
één join-query, eigen wortel-regels bewust exclusief) — een gecombineerde "subboom + vervullers
in één respons" bestaat niet.

Plan-keuze (voorstel): **hergebruiken, niet combineren.**
- **Frontend-ingangen (fase 3)** halen de boom + vervullers met de twee bestaande calls
  (`subboom` + `rollup`, plus `procesvervullingen?proces_id=` voor de wortel-eigen regels) —
  geen nieuw endpoint; drie kleine calls per ingang-klik is geen N+1-patroon.
- **Kaart-projectie (fase 1)** blijft één blok in `landschapskaart_service.haal_grafdata_op` en
  bewandelt **dezelfde bron** (`Procesvervulling` + de `ouder_id`-boom): het bestaande
  batch-iteratieve **omhoog**-laden (r. 514–528) krijgt er een spiegelbeeldige batch-iteratieve
  **omlaag**-stap bij (kinderen van geraakte wortels, per niveau, visited-set — exact de
  `subboom`-semantiek, maar set-breed gebatcht i.p.v. per wortel N× BFS). Dit is dezelfde
  roll-up-definitie andersom gebatcht; het blok-comment (r. 497–499) wordt daarop bijgewerkt.
  Er ontstaat **geen** tweede bron en **geen** opgeslagen roll-up-feit.

### 2.7 Engine-invariant per slice

- Fase 1 (backend-projectie): automatisch gedekt — de import-afwezigheid + read-only-bronscan
  zijn **module-breed** op `landschapskaart_service`
  (`test_landschapskaart.py:21` `test_landschapskaart_service_raakt_engine_niet`, r. 143
  `test_landschapskaart_geen_schrijfpad_in_bron`); de live-lifecycle-assert
  (`test_landschapskaart_proces.py:193–196`) beweegt mee in de herschreven test.
- Fase 0 (seed): `procesvervulling_service.maak_aan` maakt aantoonbaar geen profiel
  (bestaande ADR-042-borging in `test_procesvervulling_adr042.py`); geen nieuwe borging nodig.
- Fasen 2–4 (frontend-only): geen engine-oppervlak; de bestaande borging blijft de vangrail.

### 2.8 Overige feitelijke raakvlakken

- **Edge-popup-tak** `edge.ring === 'processen'` (r. 1629–1637) veronderstelt een vervult-edge
  (Component/Hoofdproces/herkomst). Een hiërarchie-edge met dezelfde ring zou daar verkeerd
  landen → fase 1 splitst de tak op `relatietype` (vervult vs. hiërarchie), anders oogt de
  browsercheck kapot.
- **Popup-helpers per hoofdproces**: `_vervulEdgesVan`/`popupVervuldDoor`/`_herkomstVelden`
  (r. 1347–1383) en de `<details>`-uitsplitsing (template r. 3188–3196) veronderstellen de
  wortel-bundel met `herkomst[]` = deelprocessen. Onder A1 wordt herkomst per edge = functies
  van dat éne paar; de "Vervuld door"-sectie op een proces-popup blijft, maar leest per knoop
  zijn eigen directe vervullers (fase 2/4).
- **Dubbelklik-gedrag**: `onNodeTap` (r. 1673–1692) doet nu voor élke knoop
  `actieveSet = {id}` + `toonPraatplaat(id)` — voor een proces-id betekent dat vandaag al een
  praatplaat rond het proces (ADR-034 r. 198). Fase 4 vervangt dit **alleen voor
  proces-knopen** door de inzoom (besluit 5); dubbeltap-tests zijn timer-gebaseerd en
  belastinggevoelig (LI036-flakiness-notitie in likara-tests) — meewegen bij de testrun.
- **Live-test-/seed-drift**: nieuwe seed-processen (fase 0) mogen bestaande live-tests niet
  raken; de proces-live-tests zijn self-contained (eigen `WT-*`-fixtures + `finally`-teardown,
  incl. de kring-braak-les), maar de fase-0-gate rapporteert de volledige suite-uitslag als
  bewijs.
- **`lk-state`/standaardkijk**: `weergave` is momentkeuze en zit in `lk-state` (in-sessie),
  níet in de standaardkijk (r. 1142–1156-patroon, likara-frontend LI034). De handoff-opening in
  Lagen respecteert de bestaande voorrang (handoff wint al van `lk-state`, r. 2566+).

---

## Deel 3 — Gefaseerd bouwplan (voorstel)

**Volgorde-motivatie.** Eerst het besluit + de data vastleggen (fase 0: ADR + seed — zonder
3-niveaus-data is niets browserverifieerbaar), dan de databron (fase 1: backend-projectie — de
frontend kan pas een boom tekenen als de subboom + hiërarchie-edges geleverd worden), dan de
presentatie (fase 2: boom-layout), dan de toegangswegen (fase 3: ingangen/handoff) en als
laatste het verfijnde gebaar (fase 4: dubbelklik-inzoom, dat op de gelande boom + ingangen
bouwt). Elke fase is los in de browser te beoordelen; kleiner splitsen (bv. hiërarchie-edges
los van deelproces-nodes) zou tussenstanden geven die visueel als kapot lezen (dangling
lijnen / knopen zonder lijn) — daarom niet verder gesplitst.

### Fase 0 — ADR-amendement + testdata naar 3 niveaus  *(gate: seed-INHOUD)*

**Functioneel:** nog niets nieuws op de kaart; het besluit staat in ADR-034 en het canonieke
scenario kan de belofte straks bewijzen (3 niveaus + een gap-deelproces).

- ADR-034: sectie r. 205–212 vervangen door de Deel-1-tekst + de dubbelklik-zinverwijzing
  (r. 198–199); ADR-042 r. 133–134 krijgt de één-regelige statusverwijzing.
- `backend/dev_seed_testdata.py` sectie 15 (r. 1592–1645): + processtap onder "Aanvraag
  behandelen" (bv. "Besluit vastleggen") mét vervulling (bv. DMS · archiveren op dat niveau);
  + één deelproces zónder vervulling (bv. "Bezwaar behandelen" onder Vergunningverlening) als
  gap-demonstratie. Idempotent skip-op-naam/tripel blijft; reseed volgens
  `docs/LOKAAL-TESTEN.md`.
- **Gate-status:** seed-INHOUD = stop-en-rapporteer-categorie → volledig gate-rapport vóór
  commit (incl. beide suite-uitslagen + seed-tellingen vóór/ná, benoemd per categorie).
- **Browsercheck-draaiboek:** (1) reseed → ProcesDetail "Vergunningverlening" → ✅ broodkruimel
  en OnderliggendeProcessenSectie tonen twee lagen eronder incl. "Besluit vastleggen" met zijn
  doorgerolde regel; (2) ProcesDetail "Bezwaar behandelen" → ✅ bestaat, 0 componentregels;
  (3) Landschapskaart (huidig gedrag) → ✅ ongewijzigd: alleen hoofdprocessen als knoop —
  bewijst dat fase 0 niets aan de kaart deed.
- **Tests mee:** geen productcode geraakt; volledige suites draaien als regressiebewijs
  (seed-drift-check §2.8).

### Fase 1 — Backend: subboom-verrijkte proces-projectie  *(gate: gedrags-/contractwijziging)*

**Functioneel:** wie componenten op de kaart zet, ziet in de proceslaan voortaan de héle
geraakte procesketen — deelprocessen (ook die zonder systeem) als echte knopen, met lijnen
deelproces→hoofdproces en vervult-lijnen op het geregistreerde niveau (A1). Nog als plat grid
(de boom-vorm komt in fase 2).

- `landschapskaart_service.haal_grafdata_op` proces-blok (r. 492–588): + batch-iteratieve
  omlaag-stap (subboom van geraakte wortels, visited-set, §2.6); nodes voor alle
  subboom-leden; hiërarchie-edges (voorstel: `relatietype='proces_hierarchie'`, label
  "onderdeel van", `ring='processen'`); vervult-edges per (component, geregistreerd proces),
  bundel per paar met `aantal` + `herkomst` (= functie-uitsplitsing). Comment r. 497–499
  bijwerken (zelfde bron, nu twee richtingen gebatcht).
- Minimale frontend-correctheid in dezelfde slice (anders leest de browsercheck als kapot):
  edge-popup-tak splitsen op `relatietype` (§2.8) zodat een klik op een hiërarchie-lijn een
  kloppende "Onderdeel van"-popup geeft.
- **Tests mee:** `test_landschapskaart_proces.py` herschreven (subboom-nodes; hiërarchie-edges;
  fijnmazige bundels; gap-deelproces krijgt node zonder vervult-edge; wortels zonder geraakte
  keten blijven buiten beeld; cyclus-veilig omhoog én omlaag; engine/lifecycle onaangeroerd);
  schema-additiviteitstest als `LandschapsEdge`/`LandschapsNode` een veld bij krijgen;
  frontend-suite draait mee (gedeeld gedrag).
- **Browsercheck-draaiboek:** (1) kaart → zoek "Zaaksysteem" + toon → Lagen → ✅ proceslaan
  toont Vergunningverlening, Aanvraag behandelen, Besluit vastleggen én Bezwaar behandelen als
  knopen (plat grid is verwacht); ✅ lijnen deelproces→hoofdproces zichtbaar; ✅ vervult-lijn
  Zaaksysteem→Aanvraag behandelen (niet meer naar Vergunningverlening), badge "2×";
  (2) klik vervult-lijn → ✅ popup "Vervult" met functie-uitsplitsing; klik hiërarchie-lijn →
  ✅ "Onderdeel van"-popup; (3) ring Processen uit → ✅ hele keten weg; aan → terug;
  (4) Overzicht → ✅ zelfde knopen/lijnen zichtbaar (A2-gedrag ter bevestiging).

### Fase 2 — Frontend: de proceszone leest als een boom  *(doorloop + browsercheck-stop)*

**Functioneel:** in Lagen staat elk hoofdproces bovenaan zijn eigen boompje; deelprocessen
hangen op rijen eronder (dieper = lager), gegroepeerd per hoofdproces; een proces zonder
systeem draagt een rustige gap-markering (A3).

- `laneLayout` (r. 1965–1980) + `_swimlanePositions` (r. 2268–2284): eigen positie-tak voor de
  baan `'processen'` — x-groepering per wortel, y = niveau (afgeleid uit de
  hiërarchie-edges), baanhoogte = maximale boomdiepte; overige banen exact ongewijzigd
  (default-pad byte-identiek-les V028: de tak alleen achter `baan === 'processen'`).
- Gap-markering op proces-knopen zonder vervult-edge (stijl bij de browsercheck af te stemmen,
  A3); popup-helpers (r. 1347–1383) lezen per knoop de eigen directe vervullers.
- **Tests mee:** `kaartLayout.test.js` breidt uit tegen de échte cytoscape — geen samenval,
  determinisme, én "dieper proces heeft grotere y dan zijn ouder; wortels van verschillende
  bomen overlappen niet"; `LandschapskaartView.test.js` LI036-blok herschreven op de
  boom-fixture; volledige beide suites.
- **Browsercheck-draaiboek:** (1) zelfde instap als fase 1 → ✅ Vergunningverlening boven,
  Aanvraag behandelen rij eronder, Besluit vastleggen nóg een rij lager; ✅ Burgerzaken-boompje
  staat er los naast (geen overloop); (2) ✅ "Bezwaar behandelen" toont de gap-markering;
  (3) banen verslepen/"verberg lege banen"/fullscreen → ✅ banden en posities blijven kloppen
  (geen verspringen; `_pasCanvasMaat`-pad); (4) ring uit/aan → ✅ boom weg/terug.

### Fase 3 — Ingangen: "Bekijk op kaart" + "Via proces", één handoff  *(doorloop + browsercheck-stop)*

**Functioneel:** vanaf een (deel)proces opent de gebruiker het brede proceslandschap: de
volledige boom onder het hoofdproces, neutraal, in Lagen, met de herkomst benoemd.

- `kaartHandoff.js`: additieve payload-velden (§2.5); `LandschapskaartView.vue` `onMounted`
  (r. 2566–2571): bij `weergave:'lagen'`-handoff → Lagen openen + herkomst-vermelding
  (chip/regel; wisbaar) — bestaande voorrang blijft.
- `ProcesDetail.vue`: knop "Bekijk op kaart" (plaatsing conform het
  `ComponentDetail`-precedent r. 405–410; rol-gating `magKaartZien`-spiegel): wortel uit de al
  geladen voorouder-keten → vervullers via `rollup` + `procesvervullingen?proces_id=wortel` →
  `zetKaartHandoff` → navigeren.
- `KaartBeginscherm.vue`: vierde context-sectie "Via proces" (ZoekSelect op
  `maakProcesZoeker` — treffers mét oudercontext) → zelfde pad als de ProcesDetail-knop
  (één mechanisme, besluit 4).
- **Tests mee:** `ProcesDetail.test.js` (knop → handoff-payload + navigatie),
  KaartBeginscherm-test (proces-ingang → emit + handoff), `LandschapskaartView.test.js`
  (handoff met `weergave:'lagen'` → Lagen + herkomst-chip; consume-once blijft);
  `api.filter.test.js` n.v.t. (geen nieuwe filters) — anders meebewegen.
- **Browsercheck-draaiboek:** (1) ProcesDetail "Besluit vastleggen" → "Bekijk op kaart" →
  ✅ kaart opent in Lagen met de volledige Vergunningverlening-boom + alle vervullers,
  niets gedimd, herkomst "geopend vanuit: Besluit vastleggen" zichtbaar; (2) beginscherm →
  "Via proces" → zoek "besluit" → treffer toont "Besluit vastleggen — Aanvraag behandelen" →
  kies → ✅ exact hetzelfde beeld als (1); (3) F5 → ✅ geen spook-herhaling van de handoff
  (consume-once); (4) "Begin opnieuw" → ✅ herkomst-vermelding weg.

### Fase 4 — Dubbelklik-inzoom op een (deel)proces  *(doorloop + browsercheck-stop)*

**Functioneel:** dubbelklik op een deelproces zoomt bewust in: alleen dat deelproces + zijn
directe subboom + de vervullende componenten; het hoofdproces staat erbij als klikbare
terugweg naar het brede landschap. Enkelklik blijft inspecteren.

- `onNodeTap` (r. 1673–1692): proces-tak in het dubbelklik-pad (i.p.v. `toonPraatplaat`);
  inzoom-staat + terugweg-affordance (hoofdproces-knop/kruimel); vervul-toggle
  (`popupVervulActie`, r. 1390–1434) grijpt aan op de knoop-eigen (deel)proces-scope.
- **Tests mee:** dubbeltap-test voor de proces-tak (timer-gevoeligheid: geïsoleerd draaien bij
  flakiness, LI036-notitie); regressie: dubbelklik op component blijft praatplaat; terugweg
  herstelt het brede landschap; "set-acties wijzigen nooit de weergave" blijft geborgd
  (inzoom is een dubbelklik-gebaar, geen set-actie).
- **Browsercheck-draaiboek:** (1) breed landschap (fase 3-instap) → dubbelklik "Aanvraag
  behandelen" → ✅ alleen die knoop + "Besluit vastleggen" + hun vervullers in beeld,
  hoofdproces "Vergunningverlening" zichtbaar als terugweg; (2) klik terugweg → ✅ het brede
  landschap exact terug; (3) enkelklik op een proces → ✅ alleen inspecteren
  (popup + highlight, geen inzoom); (4) dubbelklik op een component → ✅ ongewijzigd
  praatplaat-gedrag.

### Ná fase 4 (regulier afsluitprotocol, geen aparte fase)

Skill-review (likara-domeinmodel ⚠-punt, likara-frontend/-backend LI036-secties, likara-ux
kaartpatronen) + TST + `gen_build.py` volgens het vaste sessie-afsluitingspatroon.

---

*Einde bouwplan. Read-only; geen code/tests/migraties/seeds/ADR-files gewijzigd. Fasering en
interpretatiepunten A1–A3 wachten op Berts akkoord.*
