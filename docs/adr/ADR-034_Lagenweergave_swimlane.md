# ADR-034 — Lagenweergave (swimlane) als architectuur-lens

**Status:** Voorstel (open subknopen nog te beslissen)
**Datum:** 2026-06-25
**Relatie:** Tweede weergave-lens op de Landschapskaart, náást de Impact-verkenner
(ADR-033). Leunt op het getypeerde elementmodel (ADR-023, ArchiMate-laag per element)
en op dezelfde relatie-data die de Landschapskaart al projecteert.
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

1. **Eigen weergave in HTML/CSS, niet via Cytoscape.** De banen zijn gewone HTML/CSS-
   kolommen; de objecten zijn HTML-elementen in hun baan; een losse SVG-laag tekent de
   relatielijnen tussen de banen. Bewust GEEN Cytoscape compound-nodes — Cytoscape is
   gebouwd voor vrij-zwevende knopen met auto-layout en vecht tegen een strakke,
   bestuurbare kolommenindeling.
2. **Lagen als banen, in vaste startvolgorde:** Rollen & beheer → Gebruikers →
   Componenten → Infrastructuur → Overig → Contracten.
3. **Banen herschikbaar.** De baan-headers zijn versleepbaar om de volgorde aan te
   passen; de gekozen volgorde wordt onthouden (sessionStorage). Een baan en de
   objecten erin verhuizen als één geheel mee; de relatielijnen hertekenen naar de
   nieuwe baanposities.
4. **Versleep-interactie uit een bestaande library**, niet zelf geschreven. Alleen het
   relatielijnen-tekenen (op basis van de getypeerde relaties + leesbare labels) is
   eigen, omdat dat LIKARA-specifiek is en in geen externe module zit.
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
