# Feitenrapport — Proces-only structuurbeeld (LI038, checkpoint)

**Build:** V038 · **Commit-basis:** 24dc755 · **Type:** read-only feitenonderzoek — niets gewijzigd.
**Doel:** vaststellen wat het proces-only structuurbeeld kan hergebruiken en wat ontbreekt,
per checkpoint-punt A1–E10 met vindplaats + feitelijke conclusie.

---

## A. Proces-boomafleiding — bestaat een proces-only bron?

### A1 — Proces-only afleiding zónder componenten: JA, die bestaat (backend)

| Bron | Vindplaats | Wat het levert |
|---|---|---|
| `proces_service.subboom` | `modules/bwb_ontvlechting/backend/services/proces_service.py:231-267` | Puur processen: alle deelprocessen (alle niveaus) onder één proces, per rij `id/naam/ouder_id/niveau/pad`. Iteratieve BFS per niveau, visited-set (cyclus-veilig). Geen component, geen vervulling. |
| Endpoint `GET /processen/{id}/subboom` | `modules/bwb_ontvlechting/backend/routes/proces.py:79-86` | Ontsluit bovenstaande 1-op-1, guard `PROCES.LEZEN`. |
| `proces_service.lijst` | `proces_service.py:185-228` | Volledige tenant-processet (gepagineerd, v2n-keyset), incl. `ouder_id` per rij + optioneel filter `ouder_id=` (directe kinderen). |

De **kaart-projectie** (`landschapskaart_service.haal_grafdata_op`, proces-blok
`modules/bwb_ontvlechting/backend/services/landschapskaart_service.py:492-625`) is daarentegen
**component-scope-gedreven**: het vertrekpunt is de `procesvervulling`-query gefilterd op de
gescopede componenten (`:506-518`, incl. dangling-guard `r.component_id in comp_node`). Alleen
bomen waarvan een tak door een vervul-regel op een in-beeld-component geraakt wordt komen mee.
**Consequentie (feit):** een procesboom zonder énige vervulling is op de kaart onzichtbaar; de
kaart-projectie is dus GEEN bruikbare bron voor een proces-only beeld dat "leeg opent → proces
zoeken". De proces-only bron bestaat wél: `lijst` (hele register) + `subboom` (één boom omlaag).

**Conclusie:** proces-only bron bestaat backend-side (`lijst` + `subboom`); de kaart-projectie is
component-gedreven en ongeschikt als bron voor dit beeld.

### A2 — Tree-view-boomstructuur: client-side afgeleid uit de volledige set

- `ProcesLijst.vue` haalt de **volledige** processet op via een pagineer-lus over
  `api.processen.lijst({limit: 100, after})` (`ProcesLijst.vue:59-71`; ref `alle` op `:34` —
  "platte set (alle pagina's); de boom is een client-side afgeleide").
- De boom-structuur komt uit de **gedeelde pure module** `procesBoomStructuur`
  (`modules/bwb_ontvlechting/frontend/procesBoom.js:21-37`), aangeroepen in het `boom`-computed
  (`ProcesLijst.vue:83`). Zelfde module levert ook `procesBoomLayout` (kaart-posities,
  `procesBoom.js:43-84`). Comment in beide bestanden: "géén derde boom-opbouw ernaast".
- Het levert **alle bomen van de tenant** (wortels = knopen zonder ouder in de set), niet één
  subboom. Dezelfde volledige-set-aanpak zit ook in de gedeelde proces-zoeker
  (`procesZoek.js:14-28`, client-side cache met `ouder_naam`-resolutie).

**Conclusie:** client-side afgeleid van het generieke lijst-endpoint; volledige bomen. Direct
herbruikbaar als databron + structuurmodule voor het proces-only beeld.

### A3 — Ouderketen omhoog + zusjes: geen eigen backend-afleiding; client-side triviaal

- **Ouderketen omhoog:** er is **geen** apart backend-endpoint. Twee bestaande klimmen:
  1. client-side in `procesKaartIngang.js:20-25` (`bouwProcesKaartHandoff`): loop
     `api.processen.haal(ouder_id)` met visited-set — N+1 per niveau, maar begrensd (boomdiepte);
  2. server-side **binnen** de kaart-projectie (`landschapskaart_service.py:520-562`,
     batch-iteratief bijladen + memoized `_wortel`) — niet los ontsloten.
  Met de volledige set (A2) is de keten ook client-side uit `ouderVan` afleidbaar zonder extra call.
- **Zusjes:** `proces_service.lijst(ouder_id=X)` levert de directe kinderen van X
  (`proces_service.py:205-206`; route-param `routes/proces.py:47`). Zusjes van P =
  `lijst(ouder_id=P.ouder_id)`. **Randgeval (feit):** het filter is
  `if ouder_id is not None` — "zusjes van een top-level proces" (`ouder_id IS NULL`) is via de
  API **niet** als filter opvraagbaar; met de volledige set is het client-side wel triviaal
  (`boom.wortels`).

**Conclusie:** bestaat niet als eigen backend-afleiding; met de volledige-set-aanpak van de
tree-view zijn ouderketen én zusjes client-side gratis (geen nieuw endpoint nodig voor V1).

---

## B. Inzoom / doorwandel / history

### B4 — Dubbelklik-inzoom + "← Terug": deels gekoppeld aan het component-set-pad

Vindplaatsen (alle in `modules/bwb_ontvlechting/frontend/views/LandschapskaartView.vue`):
- **Dubbelklik-detectie:** `onNodeTap` (`:1894-1919`, `_DBLTAP_MS = 280`); op een proces-knoop →
  `zoomInOpProces(id)` (`:1901-1903`), op andere knopen → praatplaat-hercentrering.
- **Inzoom = set-inperking:** `zoomInOpProces` (`:954-982`) haalt vervullers op (rollup + eigen
  regels), zet `procesInzoom`, **`actieveSet = vervuller-ids`** (`:973`) en `weergave = 'lagen'`.
  De actieve-set-wijziging triggert de bestaande subgraaf-herfetch
  (`POST /landschapskaart/subgraaf`, component-ids). Zichtbare proces-knopen tijdens inzoom =
  subboom + voorouder-keten, client-side afgeleid uit de getekende `proces_hierarchie`-edges
  (`_inzoomProcesIds`, `:924-949`); toegepast als filter in `_bepaalZichtbaar` (`:739-743`).
  De inzoom weigert bovendien bij 0 vervullers ("er is niets om op in te zoomen", `:964-967`) —
  het gebaar is dus wezenlijk **component-set-gedreven**.
- **History:** generiek en NIET component-specifiek. Snapshot `_maakToestand` (`:1360-1374`)
  bevat set/selectie/weergave/ego/ringen/filters/scope + `inzoom` (procesInzoom) + `selZD`;
  signatuur-watch `:1387-1397` (browser-model, `_HIST_MAX = 50`), herstel `_herstelToestand`
  (`:1403-1442`, alleen-toewijzen-wat-verandert), `terugInHistorie`/`vooruitInHistorie`
  (`:1443-1452`).

**Conclusie:** de **history-laag is losweekbaar** (toestand-snapshot + cursor, veld-agnostisch —
een proces-only toestand zou er net zo in passen). Het **inzoom-gebaar zelf** is in de huidige
vorm gekoppeld aan het component-set-pad (`actieveSet` → subgraaf-fetch → vervullers). Voor een
proces-only beeld is het patroon (dubbeltap → nieuwe scope → history-staat → "← Terug")
herbruikbaar, de implementatie niet 1-op-1 (er is geen component-set om in te perken; de scope
zou een proces-id/subboom zijn — vgl. `_inzoomProcesIds`, dat al puur op proces-edges werkt).

### B5 — Lagen-schakelaar + proceszone-boom: layout-bouwstenen herbruikbaar, zone zit in de meerlaags-opzet

- **Weergave-as:** `weergave = ref('overzicht')` — `'overzicht' | 'praatplaat' | 'lagen'`
  (`:156`); schakelfuncties `toonOverzicht`/`toonPraatplaat`/`toonLagen` (`:188-206`),
  schakelaar-knoppen in de template (`:3002-3004` e.v.).
- **Proceszone-als-boom:** `_laneVan` mapt `element_type === 'proces'` → baan `'processen'`
  (`:2172`); `_procesBoom` (`:2199-2205`) voedt zich met de proces-instances + de
  `proces_hierarchie`-edges en roept de gedeelde `procesBoomLayout` aan; `laneLayout` geeft de
  proceszone rij-per-diepte-hoogte (`:2217-2219`); `_swimlanePositions` plaatst de proces-knopen
  op boom-posities, andere banen als wrap-grid (`:2527-2554`).
- **Meet-stap vóór de eerste frame:** in de preset-tak van `_layout()`
  (`:2617-2644`): `cy.nodes().updateStyle()` + per node
  `layoutDimensions({nodeDimensionsIncludeLabels: true})` (`:2642-2643`) — zonder deze stap
  tekent de eerste frame geen lijnen (LI036-les).
- **Verbindingslijnen = echte ouder→kind:** de kaart tekent uitsluitend de door de backend
  geleverde `proces_hierarchie`-edges (`landschapskaart_service.py:592-601`; de wortel draagt er
  zelf geen). **Gap-cue:** `procesGap` op de node-data (`_nodeData`, `:2256-2259`), afgeleid met
  subboom-semantiek (`_procesZonderSysteem`), altijd zichtbaar zolang de proces-ring aan staat.

**Conclusie:** de layout-kern is **niet** aan de meerlaags-baanopzet vastgeklonken: de
boom-berekening leeft in de gedeelde pure module (`procesBoom.js`) en de proceszone-tak is een
key-specifieke tak (`lane.key === 'processen'`) bovenop de generieke lane-stapeling. Een
proces-only beeld kan `procesBoomStructuur`/`procesBoomLayout` + het preset-layout-recept (incl.
meet-stap) 1-op-1 hergebruiken; wat NIET los te pakken is, is de zone zelf — die rendert alleen
binnen de Lagen-weergave met alle banen eromheen (lege banen zijn wel verbergbaar via
`verbergLegeLanes`, maar dat is een gebruikers-toggle, geen proces-only modus).

---

## C. Selectie-aanwijzen + proces→kaart-ingang

### C6 — "Oranje selectie + centrering": direct herbruikbare functies

- **Kleurbron:** `SELECTIE_RAND = '#f59e0b'` (`LandschapskaartView.vue:116`); cy-stijlen
  `node.hl-node`/`edge.hl-edge`/`node:selected` (`:2755-2765`).
- **Mechaniek:** `geselecteerdNodeId` → watch (`:1330`) → `_pasSelectieHighlight` (`:1311-…`) +
  `_pasDim`; na elke (her)tekening opnieuw aangebracht (`:2521`). Enkelklik-pad:
  `inspecteerNode(id)` (`:1334-1342`).
- **"Proces centraal, oranje" bestaat al als functie:** `_zetProcesFocus(ingang)` (`:880-887`)
  zet `geselecteerdNodeId` + `_selectieZonderDim` (hoofdproces: oranje zónder dim) +
  `_centreerNaLayoutId` (one-shot centrering, geconsumeerd in `_naLayout` — werkt óók in Lagen,
  `:865-867`). Aanvullend: `toonHeleBoom` (dim opheffen, `:891-894`), `wisProcesIngang`
  (chip-×, `:897-904`).

**Conclusie:** volledig herbruikbaar; precies het gevraagde gedrag (vertrekhouding 2, "dát proces
centraal, oranje") is al geïmplementeerd voor de proces-ingang van LI037.

### C7 — Bestaande proces→kaart-handoff (exact beschreven)

- **Eén bouwer:** `bouwProcesKaartHandoff(api, procesId)`
  (`modules/bwb_ontvlechting/frontend/procesKaartIngang.js:17-47`): klimt naar het hoofdproces
  (visited-set), verzamelt vervullers van de héle boom (rollup + eigen wortel-regels), retour
  `{ componentIds, weergave: 'lagen', procesIngang: { wortelId, wortelNaam, herkomstId,
  herkomstNaam } }` (herkomst* = null bij instap op het hoofdproces zelf).
- **Ingang a — ProcesDetail "Bekijk op kaart"** (`ProcesDetail.vue:110-126`): bouwt de payload,
  legt hem in de **consume-once handoff-store** `zetKaartHandoff(payload)`
  (`frontend/src/composables/kaartHandoff.js:17`; géén route-query) en doet
  `router.push({ name: 'landschapskaart' })` (`ProcesDetail.vue:124`). De kaart leest hem bij
  mount: `neemKaartHandoff()` (`LandschapskaartView.vue:2843-2853`) → set + `weergave='lagen'` +
  `procesIngang` + `_zetProcesFocus`.
- **Ingang b — KaartBeginscherm "Via proces"** (`KaartBeginscherm.vue:110-117, 324` — gedeelde
  proces-zoeker `maakProcesZoeker`, `procesZoek.js`): emit → `openViaProces(proces)`
  (`LandschapskaartView.vue:986-998`) → zelfde bouwer, direct toegepast via
  `_pasProcesIngangToe` (`:1000-1009`; geen navigatie, kaart is al open).
- **NB:** de `?center=`-query bestaat óók, maar is de **component**-deep-link
  (`ComponentDetail.vue:158`); de proces-ingang loopt bewust via de handoff-store, niet via query.

**Conclusie:** de handoff bestaat, is één gedeelde bouwer + consume-once-store, en is de
natuurlijke kandidaat voor zowel "Toon in procesbeeld" (zelfde patroon: payload → store →
router.push) als de bewuste doorschakeling proces-only → volle kaart (de bestaande payload ís
al "open de volle kaart op deze boom"). Kanttekening: de huidige bouwer weigert bij
`componentIds.length === 0` ("niets te tonen") — voor een proces-only beeld is die weigering
juist níét van toepassing (het beeld heeft geen componenten nodig).

---

## D. Plek, route, rechten

### D8 — Woonplaats-opties (alleen inventaris, geen besluit)

Huidige stand:
- **Kaart-route:** één route `path: 'landschapskaart'`, `name: 'landschapskaart'`, gegate op
  `MIGRATIE_ROLLEN` (`frontend/src/router/index.js:95`; `MIGRATIE_ROLLEN =
  ['viewer','medewerker','beheerder','auditor']`, `:70`). Weergave-state is **geen route-state**:
  de as `weergave = 'overzicht'|'praatplaat'|'lagen'` leeft in de view
  (`LandschapskaartView.vue:156`), wissel via `toonOverzicht/toonPraatplaat/toonLagen`
  (`:188-206`); momentkeuze, bewust niet in de standaardkijk (LI034-sortering).
- **Procesregister-routes:** `processen` (`proces-lijst`) + `processen/:id` (`proces-detail`),
  children onder AppLayout, zonder extra `meta.roles` (`router/index.js:136-137`); nav-link
  `nav-processen` in `AppLayout.vue:121-124`.

Opties met aanhaakpunt (feitelijk, niet gewogen):
1. **Vierde waarde op de bestaande weergave-as** (`weergave === 'procesboom'` o.i.d.) binnen
   `LandschapskaartView` — haakt aan op `:156` + `_layout()` (`:2617`); erft schakelaar, history,
   selectie, popup en cytoscape-plumbing, maar de hele view is component-set-gedreven
   (beginscherm, subgraaf-watch, actieveSet) — het proces-only beeld zou daar dwars op staan.
2. **Eigen view/route** (bv. `procesbeeld`), die de gedeelde bouwstenen importeert
   (`procesBoom.js`, cytoscape-composable, preset-layout-recept, selectie-/centreer-patroon) —
   haakt aan op `router/index.js` naast `:136`; databron = `api.processen.lijst`/`subboom`
   (A1/A2), los van `landschapskaart_service`.
3. **Modus binnen ProcesLijst** (tree-view en beeld als twee weergaven van hetzelfde scherm) —
   haakt aan op `ProcesLijst.vue` (boom-computed `:83` bestaat daar al); vergt cytoscape-opname
   in dat scherm.

### D9 — Rechten

- **Proces-lezen:** `Entiteit.PROCES` volgt het `_INHOUD`-patroon
  (`backend/app/core/rbac.py:52, :153`) — alle vier tenant-rollen hebben LEZEN;
  `PROCESVERVULLING` idem (`:55, :155`) — relevant zodra het beeld rollup/vervul-data leest
  (de rollup-route guard't op `PROCESVERVULLING.LEZEN`, `routes/proces.py:92`).
- **Kaart-lezen:** `Entiteit.ARCHITECTUUR` = `_ALLEEN_LEZEN` (`rbac.py:57, :158`); beide
  landschapskaart-endpoints guarden `ARCHITECTUUR.LEZEN`
  (`modules/.../backend/routes/landschapskaart.py:27, :37`).
- **Feit:** een proces-only beeld dat uitsluitend `/processen*` leest heeft aan `PROCES.LEZEN`
  (+ `PROCESVERVULLING.LEZEN` voor de gap-cue/doorschakel-payload) genoeg; `ARCHITECTUUR.LEZEN`
  is alleen nodig als het de landschapskaart-endpoints aanroept. Alle genoemde rechten dekken
  dezelfde vier tenant-rollen als de frontend-gating `MIGRATIE_ROLLEN` — er is geen
  rechten-verschil dat de plek-keuze (D8) forceert.

---

## E. Spoor-2-vooruitblik (proces→proces-flow)

### E10 — Bevestigd: `ouder_id` is de enige proces→proces-band; flow is geparkeerd

- **Model:** `Proces` (`modules/bwb_ontvlechting/backend/models/models.py:634-663`) draagt als
  enige verband de composiet self-FK `(tenant_id, ouder_id) → proces(tenant_id, id)` met
  `ON DELETE RESTRICT` (`fk_proces_ouder`, `:662-663`). Er bestaat geen andere
  proces→proces-registratie: `procesvervulling` is het tripel component↔proces (eigen tabel),
  en er is geen code die `Relatie`-rijen tussen proces-elementen aanmaakt.
- **ADR-042 parkeert het expliciet:** "Flow/volgorde tussen processtappen blijft buiten scope"
  (`docs/adr/ADR-042_Procesregister_component_in_proces.md:135`); de bedrijfsfunctie-as idem
  (`:36, :62-63`).
- **Waar een latere flow-laag zou aanhaken (alleen inventaris):**
  - *Relatie-facade:* proces is een element-subtype, dus de generieke `relatie`-tabel kán
    proces→proces dragen. Feit daarbij (geverifieerd): `relatie_service.maak_aan`
    (`modules/.../backend/services/relatie_service.py:149-176`) valideert **geen**
    `element_type` van bron/doel — alleen bron≠doel (`:152`), tenant-bestaan, relatietype-
    catalogus (`:157`), kenmerken (`:158`) en de flow-dubbel-signalering (`:163`). Een
    proces→proces-`flow` zou technisch nú al door de facade heen kunnen; endpoint-type-borging
    zou expliciet toegevoegd moeten worden (domeinbesluit, ADR-spoor).
  - *Kaart-/beeld-kant:* het proces-only beeld tekent hiërarchie als `proces_hierarchie`-edges
    (boom); een flow-laag zou een tweede edge-soort naast de boom zijn. De tree-view-regel
    ("netwerk-relaties horen op de kaart, nooit in een tree-view" — likara-ux LI037) en de
    edge-ring-mechaniek (`ringAan`, `zichtbareEdges` `:762-768`) zijn de bestaande haakpunten.
- **Borging voor nu:** zolang het beeld knopen + boom-edges scheidt van eventuele latere
  netwerk-edges (aparte `relatietype`/ring, zoals de kaart al doet met
  `proces_hierarchie` vs. `procesvervulling`), draagt het de flow-laag later zonder herbouw.

---

## Hergebruik-kansen vs. te-bouwen-nieuw

**1-op-1 herbruikbaar:**
- **Databron:** `api.processen.lijst` (volledige set, `frontend/src/api.js:392-400`) +
  `GET /processen/{id}/subboom`; de volledige-set-cache-aanpak van `procesZoek.js`/`ProcesLijst`.
- **Boomstructuur + layout:** `procesBoomStructuur`/`procesBoomLayout` (gedeelde pure module,
  procesBoom.js) — expliciet bedoeld als de ene boom-definitie.
- **Cytoscape-recept:** preset-layout + meet-stap vóór de eerste frame + render-eigenaar/
  `stop`-callback (`_layout` preset-tak, `_naLayout`).
- **Selectie/centrering:** het `_zetProcesFocus`-patroon (`geselecteerdNodeId` + `hl-node`
  oranje + `_centreerNaLayoutId`).
- **Proces-zoeker:** `maakProcesZoeker` (leeg openen → proces zoeken, mét oudercontext).
- **Handoff naar de volle kaart:** `bouwProcesKaartHandoff` + `zetKaartHandoff`/`router.push`
  (de bewuste doorschakeling bestaat feitelijk al als ProcesDetail-knop).
- **History-patroon:** het snapshot+cursor-model (browser-model) is veld-agnostisch en
  kopieerbaar; de gap-cue-afleiding (rollup-subboom-semantiek) bestaat in twee vormen
  (kaart `_procesZonderSysteem`, lijst `laadGapCue`).

**Te bouwen (bestaat niet):**
- Een **proces-only weergave/route** zelf: er is geen modus waarin alléén processen getekend
  worden — de kaart tekent processen uitsluitend als verrijking op een component-set, en de
  proceszone leeft alleen binnen de meerlaags Lagen-plaat.
- **"Toon in procesbeeld" vanuit de tree-view:** die knop/ingang bestaat niet (ProcesLijst heeft
  geen kaart-ingang; ProcesDetail heeft "Bekijk op kaart" = volle kaart).
- **Ouderketen + zusjes rond een gekozen centrum** als beeld-opbouw (boven/onder/opzij): de
  ingrediënten bestaan (A3), de compositie niet.
- **Inzoom/doorwandel op proces-scope zonder component-set:** het bestaande dubbelklik-gebaar
  perkt een component-set in; een proces-only variant moet de scope op proces-ids voeren
  (patroon `_inzoomProcesIds` is de voorzet, maar de fetch-/set-koppeling is component-gebonden).

---

## Discrepanties t.o.v. de aannames in de opdracht

1. **"Hergebruikt de bestaande Lagen-inzoom/doorwandel-mechaniek" — deels.** De history en het
   dubbeltap-patroon zijn herbruikbaar als patroon, maar de inzoom-implementatie is een
   **component-set-inperking** (vervullers → `actieveSet` → subgraaf-fetch) en weigert zelfs bij
   0 vervullers. Een proces-only beeld kan die code niet aanroepen zoals hij is; het moet een
   proces-scope-variant zijn (B4).
2. **De kaart-proceszone is geen zelfstandig herbruikbare "zone".** De boom-layout wel
   (gedeelde module), maar de zone rendert alleen binnen de Lagen-plaat met component-gedreven
   data; "proceszone + proces-only filter binnen de kaart" botst met het feit dat de
   kaart-graafdata een component-set vereist en vervulling-loze bomen daar überhaupt niet in
   voorkomen (A1). De lichtste route loopt via de proces-endpoints, niet via
   `landschapskaart_service` (D8-optie 2/3 vs. 1).
3. **Zusjes van een top-level proces** zijn via het `ouder_id`-filter van de API niet opvraagbaar
   (filter negeert `None`); alleen relevant als het beeld per-niveau zou willen bijladen — met de
   volledige-set-aanpak (de bestaande norm in tree-view én zoeker) is dit een non-issue (A3).
4. **De bestaande proces→kaart-handoff reist via een consume-once store, niet via route-query**
   (`kaartHandoff.js`) — de checkpoint-aanname "route + query, bv. `?center=`/proces-param" klopt
   alleen voor de component-deep-link; voor "Toon in procesbeeld" is de store-vorm het bestaande
   precedent (C7).
5. **Spoor-2-borging:** de relatie-facade valideert geen bron/doel-`element_type` — een latere
   proces→proces-flow "kan" er technisch nu al doorheen; het ADR-spoor moet dus niet alleen het
   registreerbaar-maken ontwerpen maar ook de type-borging expliciet regelen (E10; consistent met
   de eerdere V030-correctie in likara-domeinmodel).

---

*Einde feitenrapport — read-only; geen code, schema of testdata gewijzigd.*
