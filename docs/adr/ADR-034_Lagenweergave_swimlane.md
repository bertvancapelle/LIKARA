# ADR-034 — Lagenweergave (swimlane) als architectuur-lens

**Status:** **Geland (LI036, V037-werk)** — met herzieningen t.o.v. het oorspronkelijke
voorstel (zie "Gebouwde realiteit — LI036" onderaan; besluit 1 is herzien, besluit 4 is
buiten scope gebleven)
**Datum:** 2026-06-25 (voorstel) · 2026-07-10 (geland, LI036)
**Relatie:** Derde weergave op de Landschapskaart, náást Overzicht en Praatplaat
(ADR-040 — de Impact-verkenner/ADR-033 waar dit voorstel oorspronkelijk náást zou komen,
is door ADR-040 afgeschaft). Leunt op het getypeerde elementmodel (ADR-023, ArchiMate-laag
per element), dezelfde relatie-data die de Landschapskaart projecteert, en het
procesregister (ADR-042) voor de proceslaan.
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt
niet geraakt. Puur read-only weergave.

---

## Context / aanleiding

De Landschapskaart heeft nu één visuele vorm: de graph (ego-view, geheel-model,
Impact-verkenner — ADR-033), getekend met Cytoscape. De graph beantwoordt de
**migratie-/impactvraag**: "wat hangt samen, wat raakt wat, welke afhankelijkheden
zijn gedeeld". Dat is z'n kracht.

Een graph beantwoordt echter niet goed de **plek-/structuurvraag**: "waar zit dit in
de architectuur — welke laag (gebruikers / rollen & beheer / applicatie /
infrastructuur)". Daarvoor is een **lagenweergave (swimlane)** passender: vaste banen
per laag, objecten in hun baan, relaties als lijnen ertussen. Dit ADR voert die
tweede lens in.

**Onderscheid (belangrijk).** De swimlane is een **aparte lens náást** de
Impact-verkenner, geen vervanger en geen vereenvoudiging ervan. Graph =
migratie-/impactlens; swimlane = architectuur-/plek-lens. De **data-onderlaag is
gedeeld** (de getypeerde relaties + de ArchiMate-laag per element liggen klaar); de
**rendering is bewust niet gedeeld** (zie besluit).

---

## Besluit (kern)

> **LI036-update (2026-07-10):** besluit 1 is bij de bouw **herzien** (Cytoscape
> preset-baanposities i.p.v. HTML/CSS+SVG — dit voorstel dateerde van vóór de
> ADR-040-Cytoscape-herbouw) en besluit 4 is **buiten scope** gebleven. Zie
> "Gebouwde realiteit — LI036" onderaan voor de geldende staat.

1. **~~Eigen weergave in HTML/CSS, niet via Cytoscape~~ — HERZIEN (LI036).** Gebouwd:
   **Cytoscape preset-baanposities** (zelf-berekende x/y per knoop in zijn baan;
   `_swimlanePositions` + de preset-tak in `_layout()`), met een **HTML-band-overlay**
   voor baan-achtergronden en -koppen óver het canvas. Knopen én lijnen blijven puur
   Cytoscape — dus dezelfde render-eigenaar, stijlbron en interactie als de andere
   weergaven. Wél overeind uit het oorspronkelijke besluit: **bewust GEEN Cytoscape
   compound-nodes** (die faalden eerder op edge-rendering tussen lanen +
   pointer-events); de losse SVG-lijnlaag is daarmee overbodig geworden.
2. **Lagen als banen, in vaste startvolgorde** — *volgorde herzien bij de bouw (LI036)*:
   **Processen → Rollen & beheer → Gebruikers → Componenten → Infrastructuur →
   Contracten → Overig** (proceslaan bovenaan als "waarvoor"-laag; Overig onderaan).
3. **Banen herschikbaar.** De baan-headers zijn versleepbaar om de volgorde aan te
   passen; de gekozen volgorde wordt onthouden (sessionStorage). Een baan en de
   objecten erin verhuizen als één geheel mee; de relatielijnen hertekenen naar de
   nieuwe baanposities.
4. **~~Versleep-interactie uit een bestaande library~~ — BUITEN SCOPE gebleven (LI036).**
   De bestaande hand-rolled baan-kop-drag (pointer-events, LI019) staat en volstaat;
   er is géén drag-library toegevoegd. Het relatielijnen-tekenen is met de herziening
   van besluit 1 gewoon Cytoscape (geen eigen SVG-laag nodig).
5. **Identieke look en feel met de graph.** Een knoop ziet er in de swimlane hetzelfde
   uit als in de graph: zelfde lifecycle-statuskleur, blokkade-indicatie (⚠),
   type-aanduiding, vorm, hoekradius en lettertype — alles uit de bestaande
   `--cd-`-tokens. **Voorwaarde:** de knoop-styling (statuskleur, rand, ⚠,
   type-label) wordt als **één gedeelde bron** vastgelegd die zowel de graph als de
   swimlane lezen, zodat de twee weergaven niet uit elkaar kunnen lopen. Dit patroon
   hoort in de CC-skills.
6. **Toggles:** "Verberg lege banen" en "Toon registratiegaps" (losse objecten zonder
   relaties zichtbaar maken). Relaties tussen banen zichtbaar; objecten aanklikbaar →
   detail-paneel (zoals in de graph).

---

## Model / aanpak

- **Banen** = ArchiMate-laag per element (bestaand, ADR-023). Elk element valt in z'n
  laag-baan; "Overig" vangt wat geen herkenbare laag heeft.
- **Objecten** = de elementen, als HTML-knoop-componenten die de gedeelde knoop-styling
  (besluit 5) gebruiken.
- **Relatielijnen** = dezelfde getypeerde relaties die de Landschapskaart al
  projecteert (flow / draait-op / serving / aggregation / roltoewijzing / contract),
  met leesbare labels; getekend op een SVG-overlay tussen de baanposities.
- **Herschikken** = baan-volgorde (drag op de headers, library-gestuurd) +
  hertekenen lijnen; volgorde in sessionStorage.

---

## Invarianten

- **Read-only / engine onaangeroerd.** Puur een afgeleide weergave-lens bovenop
  bestaande relaties; voedt de engine niet. Dubbele engine-borging zoals gebruikelijk
  als er onverhoopt service-code bij komt (verwacht: frontend-only, hooguit een
  read-projectie).
- **Geen afgeleide relaties** (ADR-023 besluit 7): toont alleen expliciet
  geregistreerde relaties.
- **Gedeelde knoop-styling als één bron** (besluit 5) — geen tweede, los driftende
  stijldefinitie.

---

## Gevolgen

- **Tweede lens, gedeelde data.** De swimlane hergebruikt de relatie- en
  laag-data; alleen de weergave is nieuw. Geen EA-tool — het blijft de begrijpelijke
  kant van LIKARA (vgl. ADR-025).
- **Knoop-styling moet eerst als gedeelde bron landen** vóór (of als eerste stap van)
  de swimlane-bouw, anders ontstaat stijl-drift met de graph.
- **RBAC/audit:** read-only; waarschijnlijk hergebruik van de architectuur-
  leespermissie.

---

## Open subknopen (te beslissen vóór de bouw — met voorlopige default)

1. **Binnen-baan-ordening.** Krijgen objecten binnen een baan een betekenisvolle
   volgorde of zijn ze ook zelf versleepbaar? *Default: v1 alleen banen herschikbaar;
   objecten binnen een baan automatisch geordend (bv. op naam/status). Binnen-baan-
   sleep is een latere uitbreiding.*
2. **Welke drag-library** voor de baan-headers. *Default: een volwassen Vue-compatibele
   drag-and-drop-component; keuze bij de bouw, geen zelfbouw.*
3. **Plek van de gedeelde knoop-styling-bron** (gedeelde component/module + token-set
   die graph én swimlane lezen). *Default: één gedeelde knoop-stijlbron; exacte vorm
   bij de bouw, vastgelegd in de skills.*
4. **Verhouding tot de bestaande view-modi.** Wordt de swimlane een aparte weergave-
   keuze náást de adaptieve graph, en hoe verhoudt zich dat tot "weergave volgt je
   selectie" (ADR-033)? *Default: swimlane is een expliciet kiesbare lens voor het
   geheel-model/een selectie, los van de automatische graph-modus; precieze
   ingang bij de bouw.*
5. **RBAC.** *Default: hergebruik de architectuur-leespermissie.*

---

## Bouw-fasering (indicatief, ná besluitvorming)

1. **Gedeelde knoop-styling als één bron** (graph + toekomstige swimlane lezen
   dezelfde definitie) — borgt besluit 5 vóór de swimlane bestaat.
2. **Swimlane-weergave** — HTML/CSS-banen in de vaste startvolgorde, objecten in hun
   laag, detail-paneel, lege-banen-/registratiegaps-toggles.
3. **Relatielijnen** — SVG-overlay tussen de banen met leesbare labels.
4. **Herschikbare banen** — drag op de headers (library), volgorde in sessionStorage,
   lijnen hertekenen.

Elke slice read-only, met engine-onaangeroerd-borging en de gangbare gate-discipline.

---

## Gebouwde realiteit — LI036 (2026-07-10)

Wat daadwerkelijk is gebouwd (commits `7b4c00c` t/m `f9a8a6f`), met de afwijkingen t.o.v.
het voorstel en de reden:

- **Lagen = derde weergave op de éne weergave-as** (`weergave: 'overzicht' | 'praatplaat'
  | 'lagen'`, ADR-040-schakelaar in de topbar). De vroegere geparkeerde `layoutModus`-as
  ('radiaal'|'swimlane') is geconvergeerd en bestaat niet meer. Zelfde set + filters in
  alle drie de weergaven ("één selectie, drie lenzen").
- **Rendering (herziening besluit 1):** Cytoscape **preset-baanposities** + HTML-band-
  overlay; geen compound-nodes, geen SVG-lijnlaag. Kritieke bouwles: de preset-layout
  meet — anders dan grid/concentric — geen knoopdimensies, waardoor de eerste frame bij
  `width/height:'label'`-knopen geen edge-geometrie had (lijnen tekenden pas na een
  klik). Fix: een **meet-stap vóór de eerste frame** (`updateStyle` + `layoutDimensions`)
  binnen de ADR-040-render-eigenaar — geen timing-nudge.
- **Rolbanen vs. identiteitsbanen (nieuw t.o.v. het voorstel):** de banen "Rollen &
  beheer" en "Gebruikers" zijn **rolbanen** — ze delen partijen in op **de rol in de
  relatie** (gebruikt → Gebruikers; beheerrollen/eigenaar/leverancier-"geleverd door" →
  Rollen & beheer). Eén partij met meerdere petten staat in meerdere rolbanen, via een
  **Lagen-only instance-projectie** (visuele instances `id@baan` met gedeelde
  `logischId`; klik licht álle instances op, één detailkaart). Identiteitsbanen
  (Componenten/Infrastructuur/Contracten) delen in op het type — strikt één keer. Elke
  rol-plek draagt een **rol-tag** (kleur + kort woord: gebruikt/levert/beheert/eigenaar;
  partij zonder rol → Rollen & beheer zónder tag); de tag deelt de dim-staat van zijn
  knoop en keert in dezelfde kleur terug in de popup.
- **"Ring uit wint van gaps"-zichtbaarheidsregel (nieuw):** een ring uitzetten haalt de
  relaties én de knopen weg die alléén via die ring in beeld waren — óók met "Toon
  registratiegaps" aan; een échte gap (geen enkele relatie) volgt de ring van zijn
  categorie; 'Overig' (categorieloos) blijft altijd zichtbaar onder de toggle. Eén
  gedeelde term in `getekendeNodes`, identiek op alle weergaven — de oorspronkelijke
  "toon registratiegaps"-toggle (besluit 6) is hiermee ring-bewust geworden.
- **Besluit 5 (gedeelde knoop-styling) is vervuld** zoals voorzien: één stijlbron
  (`_nodeData`/`_vormVoorType`) voor alle weergaven; identiek uiterlijk per constructie.
  Besluit 6-toggles ("Verberg lege banen", registratiegaps) zijn gebouwd; besluit 3
  (herschikbare banen, sessionStorage) werkt via de bestaande hand-rolled drag.

### Proceslaan (LI036 slice 2 — verankering; relatie ADR-042)

- **Ring 'processen'** (default aan, zichtbaar in álle weergaven, ook in de
  praatplaat-kernset) + **proceslaan bovenaan**. Proces-knoop: `element_type='proces'`,
  business-laag, vorm = **afgeronde rechthoek met verloop-pijl-marker**.
- **Data = read-only subgraaf-projectie** (geen schema, engine onaangeroerd): een
  verrijkingsblok in `landschapskaart_service.haal_grafdata_op` klimt **bottom-up**
  (cyclus-veilig) van de vervul-regels (`procesvervulling`, ADR-042) naar de
  hoofdproces-wortel — **één roll-up-definitie** (zelfde bron als `rollup_voor_proces`,
  andersom bewandeld). Per (component, hoofdproces) één samengetrokken **vervult-edge**
  met `aantal` (badge bij ≥2, flow-precedent) en `herkomst[]` (deelproces +
  applicatiefunctie).
- **Interactie:** dubbelklik = hercentreren (praatplaat rond het proces) — *herzien voor
  proces-knopen, zie "Proces-diepte — besloten (LI037)" hieronder (besluit 5)*; popup toont
  "Vervuld door: N componenten" met de herkomst **inklapbaar per component**
  (detail-op-aanvraag) en de **vervullers-toggle**: "+ Voeg vervullende componenten toe
  (N)" ⇄ "− Verwijder vervullende componenten" — de verwijder-kant maakt uitsluitend de
  eigen toevoeging ongedaan (vóór-bestaand set-werk blijft staan); set-acties wijzigen
  nooit de weergave (zie de ADR-040-herziening).

### Proces-diepte — besloten (LI037): deelprocessen eerste-klas

**Status: Besloten, nog te bouwen** (LI037; vervangt het vroegere "⚠ bewust openstaande"
diepte-punt — de tussenstand "alleen hoofdprocessen" is geen eindstaat meer maar de
vertrekbasis van de bouw; fasering: `docs/Bouwplan-deelprocessen-op-kaart-V037.md`).

1. **Hele keten, niet weggerold.** Raakt een component-in-beeld een (deel)proces, dan komt
   de **volledige subboom onder het bijbehorende hoofdproces** in beeld — inclusief
   deelprocessen zonder ondersteunend systeem. De omvang schaalt mee met de **selectie**
   van de gebruiker (de ketens die de componenten-in-beeld raken), niet met de hele tenant.
2. **De proceszone leest als een boom.** Hoofdproces boven, deelprocessen (en dieper) op
   rijen eronder, het ondersteunende systeem onderaan; **hoogte codeert de hiërarchie**
   (geen niveau-label — spiegel van het ADR-042-principe "de plek in de boom ís het
   niveau"). Deelprocessen zijn **visueel gegroepeerd onder hun eigen hoofdproces**, zodat
   naburige bomen niet in elkaar overlopen; variabele diepte volgt vanzelf uit
   "dieper = rij lager".
3. **Leeft in Lagen, onder de bestaande ring `'processen'`.** De hele keten — proces-knopen
   én de deelproces→hoofdproces-lijnen — valt onder die ene ring: ring uit ⇒ de hele keten
   weg, consistent met "ring uit wint van gaps".
4. **Twee gelijkwaardige ingangen, één breed landschap.** (a) "Bekijk op kaart" op het
   proces-detail en (b) een "Via proces"-zoekingang op het kaart-beginscherm openen
   **beide** hetzelfde: de volledige boom onder het hoofdproces, **neutraal** (niet
   gedimd), in **Lagen**, met het **deelproces-van-herkomst benoemd** (waar de gebruiker
   instapte). Eén gedeeld handoff-mechanisme (uitbreiding van het bestaande
   consume-once-`kaartHandoff`), één weergave.
5. **Klik-gebaren.** Enkelklik op een proces-knoop = **inspecteren** (detailkaart +
   incidente lijnen oplichten, rest dimt) — als elke andere knoop. Dubbelklik = **bewust
   inzoomen** op alléén dat deelproces + zijn directe subboom + de vervullende
   componenten, met het **hoofdproces als klikbare terugweg** naar het brede landschap
   (dit herziet, voor proces-knopen, de dubbelklik-regel "hercentreren op de praatplaat"
   hierboven). Onderscheid: de *ingang* (besluit 4) toont het brede landschap; de
   *dubbelklik* is de inzoom. Detail-op-aanvraag (applicatiefunctie / aantal vervul-regels
   / herkomst) blijft in **badge → inklap → popup** op de vervult-koppelingen — niet in
   het klik-gebaar op de proces-knoop.
6. **Deelproces-zonder-systeem = eigen rustige cue.** Een (deel)proces zonder enige
   procesvervulling eronder draagt een rustige **"geen ondersteunend systeem"-markering**,
   **altijd zichtbaar zolang de proces-ring aan staat** en **los van de "Toon
   registratiegaps"-toggle** (die blijft voor relatie-loze knopen; een keten-deelproces
   heeft immers een hiërarchie-lijn en is dus niet relatie-loos). Eerlijk-gaten-tonen-lijn:
   tonen, rustig, niet blokkeren.

**Testdata-verankering (LI037 fase 0):** het canonieke scenario draagt sinds fase 0 een
boom van **drie niveaus** (Vergunningverlening → Aanvraag behandelen → Besluit vastleggen)
mét een vervulling op het derde niveau, plus het bewust ondersteuningsloze deelproces
"Bezwaar behandelen" — zodat besluit 2 en 6 browserverifieerbaar zijn (reseed, geen
migratie).

**Invariant (ongewijzigd):** read-only projectie, engine onaangeroerd, **één
roll-up-bron** (dezelfde `procesvervulling` + `ouder_id`-boom-semantiek als
`rollup_voor_proces`/`subboom` — nooit een tweede bron).
