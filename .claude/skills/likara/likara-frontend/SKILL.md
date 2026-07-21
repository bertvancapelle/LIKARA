---
name: likara-frontend
description: Frontend-patronen voor LIKARA (Vue 3, PrimeVue Unstyled, Tailwind v4). Beschrijft de werkelijke V003-staat (login + app-shell + module-views).
stack: Vue 3, Vite, PrimeVue Unstyled, Tailwind CSS v4, Pinia, vue-router, vitest
bijgewerkt: V043
---

# LIKARA Frontend Skill

## PrimeVue Unstyled + PassThrough presets

```javascript
// src/main.js
app.use(createPinia())
app.use(router)
app.use(PrimeVue, { unstyled: true, pt: presets })   // pt = src/presets/index.js
app.use(ToastService)
```

Elke gebruikte PrimeVue-component vereist een preset in `src/presets/` (anders
rendert hij leeg in unstyled-mode). Aanwezig: Button, DataTable, Dialog, Drawer,
InputText, Popover, Tag, Textarea, Toast (+ `index.js`). Column heeft géén eigen
preset nodig (de DataTable-preset stuurt header/body/empty).

## Design-tokens + styling

- Altijd de **`--lk-`-prefix** (uit `src/themes/base.css`). Geen `<style>`-blokken;
  uitsluitend Tailwind-utilities + `--lk-`-tokens. `assets/main.css` importeert
  Tailwind v4 + `base.css` + globale resets/utilities (o.a. `.card`).
- Tailwind arbitrary aria-variant voor de actieve nav-link:
  `aria-[current=page]:bg-[var(--lk-color-accent)]`.

## Frontend-module-loading (Optie A — V003)

Module-frontendcode staat **buiten** de vite-root in
`modules/<module>/frontend/` (views/, labels.js). Geregeld via vite-config:

```javascript
// frontend/vite.config.js
resolve: { alias: {
  '@':        fileURLToPath(new URL('./src', import.meta.url)),
  '@modules': fileURLToPath(new URL('../modules', import.meta.url)),  // generiek
}},
server: { fs: { allow: [frontendDir, modulesDir] } },   // strak gescoopt, niet kale ..
```

- De centrale router importeert een module-view via `@modules/...` en registreert
  hem als **child onder `AppLayout`** (erft `requiresAuth` via de meta-merge → guard
  ongewijzigd). Statische subpaden (`/nieuw`) vóór `/:id`; `props: true` voor
  id-routes.

### Cross-root-barrels (VERPLICHT patroon voor module-views)

`node_modules` woont in `frontend/`; module-views buiten de root kunnen bare deps
(`primevue/*`, `vue-router`) niet resolven. Importeer gedeelde deps daarom via
platform-barrels:

```javascript
import { DataTable, Column, Tag, Button, Dialog, InputText, Textarea, useToast } from '@/primevue'
import { useRouter, useRoute } from '@/composables/router'
import { api } from '@/api'
```

Breid `src/primevue.js` / `src/composables/router.js` uit zodra een view een extra
component/composable nodig heeft. (`vue` zelf resolvet wél cross-root — vite dedupet
het.) Route-params bij voorkeur via `props: true`, niet `useRoute`.

## App-shell (AppLayout) + router-nesting

```
src/layouts/AppLayout.vue   — topbar (app-naam, gebruiker-e-mail, uitlog-knop) +
                              inklapbare sidebar (nav) + hoofd-<router-view> + <Toast/>
```

- Sidebar-toggle: `aria-expanded`/`aria-controls`; voorkeur optioneel in
  `localStorage` (`cd-sidebar-ingeklapt`, niet-gevoelig, try/catch).
- Router: geauthenticeerde routes als children onder `AppLayout`;
  `login`/`auth-callback`/`verboden` standalone (`meta.public`). De guard
  (`store/auth.js` + `router/index.js`) blijft ongewijzigd.
- Uitloggen: `auth.logout()` (wist `lk_session`, redirect `/login`). **OP-4**:
  geen Keycloak-SSO-logout (buiten scope; in code gedocumenteerd).

## api.js fetch-wrapper

```javascript
// src/api.js — BASE='/api/v1', credentials:'include' (httpOnly cookie)
// 401 -> throw 'NIET_GEAUTHENTICEERD'; 204 -> null (DELETE);
// fout verrijkt met { status, code, detail } voor 403/404/409/422-mapping.
api.applicaties.{lijst({limit,after}), haal(id), maak(data), werkBij(id,data),
                 startInventarisatie(id), verwijder(id), opties()}
```

Voeg per entiteit platte methodes toe via de interne `request()`-helper (geen
generieke get/post).

### API-client-filterconventie (niet-onderhandelbaar)

**Eén conventie: filternamen zijn SNAKE_CASE, exact gelijk aan de backend-query-params**
(`bron_id`, `doel_id`, `component_id`, `leverancier_id`, `applicatie_id`, …). Er is **geen**
camel/snake-vertaalgrens in de client — schermen geven de keys door zoals de backend ze kent.

**Elke filter-dragende `lijst`/lees-methode valideert via `_filterQuery(naam, params, allowlist)`**:
een doorgegeven key die NIET in de allowlist staat → **LUIDE fout** (`onbekende filter-parameter
'X' voor <naam>`), nooit stil weglaten. `_query` laat bewust-lege waarden (`undefined`/`null`/`''`)
wél weg — het onderscheid is "bewust niet gezet" (ok) versus "gezet onder een onbekende naam"
(fout). Zo kan een filter **niet** meer geruisloos wegvallen en een scherm ongefilterd "alles"
laten ophalen.

**Achtergrond (waarom dit niet-onderhandelbaar is):** het Koppelingen-tabblad toonde alle 17 flows
van het hele landschap i.p.v. de 5 van Zaaksysteem, doordat `KoppelingSectie` `bron_id/doel_id`
(snake) doorgaf terwijl de client `bronId/doelId` (camel) verwachtte → filter stil weg → ongefilterd.
Dit is exact de eerder vastgelegde V012-les, die zonder structurele borging tóch terugkwam.
Geborgd door `tests/api.filter.test.js` (filter zit in de URL **én** onbekende key = luide fout).

## Data-view-patroon (lijst)

- PrimeVue `DataTable` + `Column`; **keyset-cursor-paginering** met "Meer laden"
  (`volgende_cursor`; `null` = einde). Lifecycle/status als `Tag` (severity-map in
  `labels.js`). Lege-/laad-/foutstatus; fout in `role="alert"`. Detail-navigatie
  via een toetsenbord-toegankelijke `<router-link>` op de naam.

## Formulier-patroon

- Dropdowns uit het backend **opties-endpoint** (`applicaties.opties()`) +
  per-module `labels.js` (NL-labels met **humanize-fallback** — een nieuwe
  backend-waarde verschijnt direct, hooguit generiek gelabeld). Native `<select>`
  (geen Select-preset).
- Clientvalidatie **spiegelt de backend-schemas** (naam verplicht, vrije-tekst-/
  lengtegrenzen, enums verplicht). **422-veldfouten** van de backend
  (`{detail:[{loc:[...,veld],msg}]}`) op het juiste veld zetten.
- Succes/fout via `Toast`; fout-mapping 403→geen rechten, 404→niet gevonden,
  409→conflict, 422→veldfouten, 401→bestaande sessie-flow.
- Toegankelijk: `label/for`, `aria-invalid`, `aria-describedby`, focusbeheer.

## Knopstandaard LIKARA (niet-onderhandelbaar)

De knop is **één herbruikbaar standaardobject met één vaste hoogte** (`h-10`), volledig
gestuurd door `frontend/src/presets/Button.js`. Er is **GEEN** size-variatie — `size="small"`
bestaat niet meer (preset-tak verwijderd; een `size`-prop heeft geen hoogte-effect). De enige
toegestane variatie is:

- **(a) kleur/vorm per rol** — `primary` (donkerblauw, hoofdactie; default zonder severity),
  `secondary` (lichtblauw, nevenactie), `danger` (rood, destructief), `text` (ghost/tertiair,
  transparant + primary-tekst) en `outlined` (LI039, bekrachtigd — lichte omlijning,
  transparante vulling, gedempte tekst; de standaard-PrimeVue boolean-prop, in het preset
  geactiveerd). Per scherm geldt: **maximaal één primary** (de hoofdactie).
- **(b) breedte** — past zich aan de tekst aan (`px-4`, geen vaste breedte).

**Wanneer-je-wat (LI039, drievorm in rij-context):** `text` = **navigatie/doorklik** ("hier
ga je naartoe" — label mét pijl, bv. "Toon in functiebeeld →"); `outlined` = **rustige
mutatie** in lees-context (rij-acties als Bewerken/Verplaatsen/+ Deelfunctie: onmiskenbaar
een knop, zonder kleurdruk); `secondary` = nevenactie in formulier-/dialoogcontext;
`danger` = destructief (ALTIJD, ook tussen rustige rij-acties — LI037 blijft staan);
`primary` = dé hoofdactie. Rij-acties leven in de gedeelde **`RijActies`-bouwsteen**
(`src/components/RijActies.vue` + `.lk-rij`/`.lk-rij-acties` in main.css): onzichtbaar in
rust, zichtbaar op de actieve rij (hover) én via `:focus-within`; op touch permanent
zichtbaar (`@media (hover: none)`).

**Destructief = danger-knop, nooit tekstlink (LI037).** Een destructieve actie draagt **altijd**
de `danger`-vorm en is een Button — geen rustige tekstlink met `hover:underline` (de gevaarlijkste
actie mag er niet het minst gevaarlijk uitzien). Beheeracties op rijen/lijsten spiegelen de
detailscherm-knopconventie: secundair voor nevenacties (Bewerken/Hernoemen/Verplaatsen), danger
voor destructief.

**Geen per-call-site hoogte/padding-overrides** (`class`/`:pt`/`style`) — alleen positionering
(`ml-auto`/`mt-*`) is toegestaan. Alle knoppen lopen via het ene preset; zo kan een
hoogteafwijking structureel niet meer ontstaan.

**Leesbaarheid van een losse knop (LI030, niet-onderhandelbaar).** Een `<button>` buiten het preset
(bv. de inline uitklaprij-Opslaan in `ChecklistscoreSectie`) MOET een rol-kleur met leesbaar contrast
dragen: hoofdactie = `bg-[var(--lk-color-primary)] text-white` (+ `hover:bg-[#2D6DB5]` + focus-outline).
**NOOIT** `bg-[var(--lk-color-accent)] text-white` — `--lk-color-accent` (#E8F0FB) is bijna-wit, dus
witte tekst is onleesbaar en de knop oogt disabled/dood (incident LI030: de groene payload-test dekte
dit niet; pas in de echte browser zichtbaar). Voorkeur: gebruik het Button-preset (dwingt dit af); bij
een losse knop een class-assert op de primaire token in de view-test.

**Tabbladen zijn GEEN knoppen (herzien LI048 — vervangt de oude "zelfde vorm en hoogte als een
knop"-regel).** Tot LI048 droeg een tabblad de knopvorm (`h-10`, `--lk-radius-btn`, omlijning,
donkerblauwe vulling bij gekozen). Bij dertien tabbladen over twee regels las die rij als dertien
losse knoppen: de gebruiker moest per scherm uitzoeken wat hem stuurt en wat een actie is — **de
vorm droeg de betekenis niet.** Een tabrij zónder zichtbare keuze (de LI047-uitzondering) was
daardoor niet eens als tabrij herkenbaar.

De vorm leeft nu in **handgeschreven main.css-klassen**, niet in Tailwind-utilities op de call-site
(Tailwind kan ze niet seeden → de build-check kan niet vals-groen worden):
- `.lk-tabrij` + `.lk-tabrij-h`/`-v` — de **rij** draagt de doorlopende lijn (onder resp. rechts).
- `.lk-tab` — geen omkadering, geen knophoogte (`padding: .5rem`), gedempte tekst, transparante
  randen (zodat er niets verspringt bij het wisselen); hover = `--lk-color-primary-50/700`.
- `.lk-tab[aria-selected='true']` — **de stijl leest ARIA, niet een aparte staat-class**, zodat het
  toegankelijkheidsfeit en het zichtbare feit structureel niet uiteen kunnen lopen. Gekozen = wit
  als het vlak + `--lk-color-primary` als **accentlijn en tekst** (géén nieuwe kleur, en géén
  vulling: een gevulde tab kán niet aan een wit vlak vastzitten) + `border-bottom-color: surface`,
  waarmee hij de rij-lijn doorbreekt.
- `.lk-tabrij-sub` (prop `niveau="2"`) — een rij **binnen** een gekozen groep is zichtbaar
  ondergeschikt: kleiner en dunner (geen 2px-accentbalk — die is de hoofdrij voorbehouden). Het
  gewicht leeft in de **bouwsteen**, niet op de aanroepplek — elke volgende sub-rij erft het.
  *(Dit was snede 3; het landde mee met 2b omdat een tweede rij zonder gewichtsverschil direct
  onleesbaar is. Van snede 3 blijft niets over.)*

  ⚠ **Wit op wit was het defect (2c).** De eerste versie zette de sub-rij **transparant** op het
  witte werkvlak. Een niet-gekozen tabblad had dan geen ondergrond om uit naar voren te komen:
  alleen de gekozen pil was zichtbaar, de rest zweefde als losse tekst, en de rij las niet als een
  rij. **Een tabrij heeft altijd een ondergrond die verschilt van zijn gekozen tabblad** — anders
  is er niets om uit naar voren te komen. De sub-rij draagt daarom een **grijze band** (de
  paginatint, uitbloedend tot de randen van `.lk-tabvlak`); het gekozen tabblad is **wit** en loopt
  over in de witte inhoud. Dezelfde regel als de hoofdrij, één maat kleiner. Borging: `subrij-band`
  + `subrij-band-verticaal` + `subtab-versmelt` in `check-css-build.mjs`.

### Navigatie ziet er anders uit dan een schakelaar (LI048 2c/2d)

Een rij die **een paneel wisselt** is navigatie (tabvorm). Een rij die **één lijst filtert** is een
**schakelaar**: `role="group"` + `aria-pressed`, vorm `.lk-schakelaar` / `.lk-schakelaar-stand`.
De vorm moet zeggen wát het ding is.

Twee vormregels die uit het scherm zelf volgen — beide getoetst in de dist-CSS:
- **De schakelaar loopt NIET door tot de rand** (`display: inline-flex`; het grijs sluit strak om
  de standen). Een volle band over de breedte is inmiddels hét teken voor navigatie
  (`.lk-tabrij-sub` bloedt bewust wél uit tot de vlakranden). Wordt dit `flex`, dan leest de
  schakelaar opnieuw als tabrij en is het hele 2c-onderscheid weg. Borging: `schakelaar-inline`
  toetst `padding:2px;display:inline-flex}` — de vorm-eigenschap zelf, niet het bestaan van de klasse.
- **De actieve stand krijgt een VOLLE accentvulling** — precies omgekeerd aan een tabblad, waar
  *wit* "gekozen" betekent (een tab versmelt met zijn inhoud; een schakelaar staat op zichzelf en
  moet uitspringen). De niet-gekozen standen dragen géén eigen rand: het is één ding, geen N.

- **Geen grijze plaat als vulling** (de eerste 2d-vorm had die; vervallen). Een lichte lijn óp een
  grijze vulling verdwijnt erin — in de browser was er geen zichtbaar verschil, dus de vorm werd
  met een hulplijn overeind gehouden in plaats van dat hij het zelf droeg. En grijs-als-vulling is
  al bezet door de band onder de tabrijen. Het blok draagt nu zijn eigen omlijning met
  scheidingslijntjes tussen de standen.

**De uitkomst krijgt een eigen kader** (`.lk-inhoudskader`, gewoon lijngewicht) in plaats van een
streep eronder: zo wisselt de inhoud zichtbaar *binnen* het kader bij een andere stand, in plaats
van dat de lijst eronder hangt en de gebruiker het verband moet aannemen. De **uitlegregel hoort
binnen dat kader**, bovenaan met een lijn eronder (`.lk-inhoudskader-uitleg`) — hij verandert mee
per stand, en buiten het kader zou hij lijken te gelden voor alle standen. **De vulling blijft
wit:** daar staan de signalen (amber = bewust afgewogen, gedempt = verschoven lat, blauw =
Vastleggen), en signaal hoort niet op een gekleurde vloer — dezelfde reden waarom het gekleurde
tabbladvlak eerder is afgewezen.

⚠ **Dit gedrag bestond al zes keer met evenzoveel eigen vormen** (Landschapskaart weergave/diepte/
lezing, BedrijfsfunctieLijst Boom|Diagram, ArchitectuurView Lagen|Tabel, ArchitectuurLagenView
aspect-filter). De bouwsteen is generiek gehouden zodat ze er alle zes op kunnen; de omzetting is
een eigen snede (OPVOLGPUNTEN LI048-0). **Bouw geen zevende variant** — haak aan de bouwsteen.

⚠ **Toets het gedrag, niet de gelijkenis.** De drie blokken in `OpenPuntenSectie` (*Dit moet nog /
Dit zou netjes zijn / Dit valt op*) waren als `AppTabs` gebouwd — inclusief `role="tab"` en
`aria-controls` naar `open-punten-panel-*`, panelen die **niet bestaan**: er is geen enkele
`role="tabpanel"` in die sectie. Een schermlezer kondigde dus "tabblad 1 van 3" aan en verwees naar
het niets. Ze zijn nu toggle-knoppen in een `role="group"` met `aria-pressed`. **Vuistregel: staat
er geen `role="tabpanel"` tegenover je `role="tab"`, dan is het geen tabrij.** Borging:
`OpenPuntenSectie.test.js` (geen `role="tab"`, geen `aria-controls`, wél `role="group"`).
- `.lk-tabvlak` — het witte, omrande werkvlak waar de rij aan vastzit. **Eén vlak om álle panelen**,
  niet één per paneel; anders loopt het bij het volgende paneel weer uiteen.

### De buitenrand is altijd zwaarder dan de lijnen erbinnen (LI048)

De buitenrand van een werkvlak draagt **`--lk-color-border-sterk`**, niet `--lk-color-border`.
Beide waren aanvankelijk `#e2e8f0` — dus de buitengrens was exact even zwaar als de `th/td`-
scheidingslijntjes in een lijst, en las daardoor niet als buitengrens maar als zoveelste streepje.

**Waarom dit meer is dan opmaak:** het verschil tussen pagina en werkvlak *moet* klein blijven. De
paginatint mag niet dieper zonder gedempte tekst onder de AA-grens te duwen (gemeten plafond
`#eef2f7` = 4,51:1). De lijn doet dus het werk dat de tint niet mag doen — en dan moet die lijn wel
meedoen.

**De regel, niet de waarde:** de buitenrand is de sterkste lijn op het scherm, alles daarbinnen is
lichter. Welke tint dat precies is mag veranderen; de verhouding niet. Bandbreedte: zwaarder dan de
binnenlijn, maar onder ~1,8× het contrast ervan — een rand om élk werkvlak wordt bij twintig
schermen per dag anders een raster (slate-400 ≈ 2,08× overschrijdt dat). Huidige keuze `#cbd5e1`
(slate-300, 1,48:1 op wit = 1,20×) blijft in de bestaande slate-familie: bg=slate-50,
border=slate-200, buitenrand=slate-300.

Borging in **twee** richtingen: `tokens.contract.test.js` vergelijkt de **luminantie** van beide
tokens (valt om als de buitenrand verlicht wórdt én als de binnenlijn verzwaard wordt — die tweede
is de sluipweg die anders niemand opmerkt) plus de bovengrens; `check-css-build.mjs`
(`werkvlak-sterke-rand`) toetst dat de bouwsteen de sterke token daadwerkelijk draagt in de
gebouwde CSS.

⚠ **`.card` draagt géén rand** (alleen `--lk-shadow-sm`) en beweegt dus niet mee — zie
OPVOLGPUNTEN. Lijstschermen en de kaart hebben op dit moment helemaal geen omrand werkvlak.

### Een tabrij telt maximaal vijf tabbladen (LI048 snede 2b)

Dertien tabbladen liepen over naar een tweede regel — en dán hangt het gekozen tabblad los boven
een vlak dat pas onder regel twee begint, dus de tabvorm hierboven valt om precies waar hij nodig
is. Dertien woorden zijn bovendien niet te scannen: alles weegt even zwaar. **Een overloopmenu is
géén oplossing** (dan is een deel gewoon onzichtbaar — dat ís de klacht).

`ComponentDetail` groepeert daarom naar **hoe de consultant denkt**: Overzicht · Beoordeling (N) ·
Wat het doet · Samenhang · Afspraken. Verworpen groepsnamen — niet opnieuw voorstellen: *"Status"*
en *"Inventarisatie"* (beide dragen elders op hetzelfde scherm al een andere betekenis, en geen van
beide is telbaar).

**Sleuteldiscipline (niet-onderhandelbaar):** `?tab=` en `activeTop` spreken de **onderdeel**-taal
(`checklist`, `contracten`, …), nooit de groep. De groep is **afgeleid** (`actieveGroep`). Zo blijft
élke bestaande ingang letterlijk werken — gemeten waren dat er acht: drie kaart-aanleidingen, de
blokkade-doorklik, vier backend-routes uit het open-punten-overzicht, en de gedeelde URL uit snede 1.
Een tweede sleutel in de URL zou een tweede waarheid zijn die stil uit de pas loopt.

Vier gedragsregels, elk met een eigen bijtende toets (`ComponentDetail.test.js`): (1) een groep
zonder beschikbare onderdelen verschijnt niet; (2) een groep met precies één onderdeel toont **geen**
sub-rij — een keuzerij met één keuze is geen keuze, en het paneel labelt dan naar het *groeps*tabblad;
(3) op **beide** rijen is altijd precies één gekozen (de snede-1-invariant geldt onverkort); (4) een
groep openen kiest het **eerste** beschikbare onderdeel.

⚠ **Teltip bij tests:** `findAll('[role="tablist"]')` telt óók verborgen rijen mee — het
open-punten-paneel draagt zijn eigen blokken-rij en is altijd gemount (`v-show`). Tel op de
`data-testid`-prefix van de rij die je bedoelt.
- Radius: `--lk-radius-tab` / `--lk-radius-tab-v` (alleen de hoek áf van het vlak is rond) — niet de
  knopradius.

**De knopvorm blijft gereserveerd voor knoppen.** Borging: `interactiestates.test.js` toetst per
knopvorm-signaal (`h-10`, knopradius, `border-[0.5px]`, gevulde staat) dat een tabblad het níét
draagt, plus dat gekozen en niet-gekozen tab **dezelfde classes** hebben (valt om zodra iemand
terugvalt op class-gebaseerde staat); `check-css-build.mjs` toetst de vijf vormregels in de
**gebouwde** CSS, waaronder apart `border-bottom-color:var(--lk-color-surface)` — sneuvelt juist
díé, dan zweeft de tab weer boven een losse lijn en is de snede visueel ongedaan. Beide aantoonbaar
bijtend.

## UI-interactiestates + borging (niet-onderhandelbaar)

**Interactiestates.** Hover/focus/selected lopen uitsluitend via `--lk-`-tokens en de centrale
componenten (`presets/Button.js`, `AppTabs.vue`). Geen losse kleuren of state-klassen op
call-sites.

**Tailwind-scanning (vereist, geen optie).** Tailwind v4 scant **glob-gebaseerd** (niet via de
Vite module-graph). Elke module-frontend buiten `frontend/` (onder `modules/`) MOET via een
`@source`-directive in `src/assets/main.css` worden meegescand — anders ontbreken module-unieke
klassen **stil** in de productie-CSS (bewezen: zonder `@source` vallen de tab-hover- en
`border-[0.5px]`-klassen uit de build; ADR-/incidentlijn tab-hover). Een nieuwe module ⇒ een
`@source`-regel toevoegen.

**Borging — drie lagen (`frontend/tests/` + `npm run test:css-build`):**
1. **Token-contracttest** (`tokens.contract.test.js`) — afgesproken `--lk-`-tokens bestaan en zijn
   niet-leeg.
2. **Component-render-state-test** (`interactiestates.test.js`) — Button-preset (elke variant zet
   de juiste token-klasse + vaste `h-10`) en AppTabs (de tabvorm: géén knopvorm-signaal op een
   tabblad, de vorm in de gedeelde `.lk-tab*`-klassen, de staat op `aria-selected` — zie
   §Tabbladen zijn GEEN knoppen).
3. **Build-CSS-check** (`scripts/check-css-build.mjs`, script `test:css-build`) — faalt als een
   kritische interactie-klasse niet in de **gebouwde** CSS belandt, óók bij een ontbrekende
   `@source`. Draait een productie-build en greep't de dist-CSS.

**Vals-groen-valkuil (cruciaal).** De build-CSS-check (en render-state-test) staan zélf onder
`frontend/` en worden dus door Tailwind gescand. Een te-matchen class-token dat hier **aaneengesloten**
als literal staat, wordt door Tailwind als candidate opgepikt en zélf gegenereerd → de check maakt
zijn eigen controle waar (vals-groen). Daarom: bouw zulke tokens uit **fragmenten** met de sluit-`]`
afgesplitst (`'border-[0.5px' + ']'`) — een los fragment met ongebalanceerde `[` is geen candidate.
Bij elke nieuwe kritische-klasse-check deze de-vervuiling aanhouden.

## ZoekSelect-standaard (niet-onderhandelbaar)

Elke keuzelijst met meer dan 10 opties OF met een open-ended catalogus gebruikt altijd de
`ZoekSelect`-component. Statische `<select>` alleen voor gesloten lijsten van maximaal 10
vaste opties.

**Altijd ZoekSelect:**
- Partijen (organisatie / persoon / afdeling / externe partij)
- Applicaties en componenten
- Contracten
- Plateaus, gaps, werkpakketten, deliverables
- Componenttypen (kan groeien)

**Mag statische `<select>`:**
- Hostingmodel, migratiepad, complexiteit, prioriteit
- Koppelingrichting, protocol, impact bij verbreking
- Lifecycle-statusfilter, ArchiMate-laag, partij-aard
- Elke andere gesloten lijst met ≤ 10 vaste opties

**Patroon ZoekSelect** (gebruik de bestaande `modules/.../views/ZoekSelect.vue` — niet opnieuw
implementeren; server-side `zoek-functie`, debounce, ~10 resultaten + "verfijn"-regel):

```vue
<ZoekSelect
  v-model="gekozenId"
  :zoek-functie="zoekPartijen"
  :weergave="(p) => p.naam"
  placeholder="Zoek een partij…"
/>
```

Bij twijfel: kies ZoekSelect.

### ZoekSelect-patronen (V030, beproefd)

**1. Picker-scope spiegelt de backend-regel (niet-onderhandelbaar).** Een keuze-picker toont alléén wat
de backend als geldig accepteert — nooit opties die bij opslaan een 422 opleveren. De gebruiker mag geen
keuze kunnen maken die het systeem verwerpt. Referentie: contract-leverancier filtert
`aard_in=[organisatie, organisatie_eenheid, externe_partij]` (spiegelt
`contract_service.TOEGESTANE_LEVERANCIER_AARDEN`); eigenaar-organisatie filtert `aard=organisatie`.
Bestaat er een meervoudige filter-param (`aard_in`), gebruik die; hij loopt al door de hele keten
(route → service → `api.js`-whitelist).

**2. Bewerken-voorvulling leest uit de ACTUELE bron + `initieel-weergave` (niet-onderhandelbaar).** Een
edit-formulier vult elk veld voor uit waar de waarde ná de laatste ADR écht leeft — niet de oude plek.
Referentie: de organisatie van een gebruikersgroep leeft sinds ADR-036 op het grove feit, niet meer op
de groep; de read resolvet `organisatie_naam`, het formulier vult daaruit voor. Een `ZoekSelect` kent
alleen het id, niet de naam: **zonder de `initieel-weergave`-prop blijft het veld leeg terwijl het id
correct gezet is** (verwarrend + risico op stille ontkoppeling). Geef `:initieel-weergave` bij élke
edit-prefill; remount met een `:key` als de dialog-instantie voortleeft (anders blijft een vorig
`gekozenLabel` staan).

**3. Search-first create-in-lege-zoekstaat (voor open-ended catalogi).** Een picker die ter plekke
aanmaken toestaat (bv. afdeling) biedt dat **pas aan in de lege zoekuitkomst** — géén altijd-zichtbare
"+ Nieuw"-knop (die lokt voortijdig aanmaken → duplicaten). De aanmaak-actie is contextueel (toont de
zoekterm + de organisatie), de naam is **vastgeklonken aan de zoekterm**, met een korte **inline**
bevestiging (geen popup-op-popup), en alleen zichtbaar met aanmaakrecht. De kern-maatregel tegen
wildgroei is een **vergevingsgezinde zoek** (ilike / partieel / trim), zodat een bestaande afdeling
gevonden wordt vóór iemand een dubbele aanmaakt. Referentie: generiek `#leeg`-scoped-slot op
`ZoekSelect.vue` (backward-compatible: default = "Geen resultaten.").

**4. Voorgevuld openen toont de VOLLEDIGE (scope-)startlijst — nooit de prefill als zoekfilter
(niet-onderhandelbaar, LI032).** Een `ZoekSelect` met een voorgevulde waarde (bewerken-modus) toont bij
openen de **volledige startlijst binnen zijn scope**, niet alleen de huidige waarde. Anders zit de
gebruiker vast aan de bestaande keuze en lijkt er maar één afdeling/organisatie te bestaan. Concreet:
`openen()` zoekt met een **lege term** (`zoek('')`), niet met de voorgevulde `query`; de voorgevulde
tekst blijft als **label** zichtbaar maar filtert niet; de input-tekst wordt bij openen geselecteerd
(`input.select()`) zodat de eerste toetsaanslag de prefill vervangt. Typen ná openen filtert daarna wél
soepel (debounce). Regressietest: mount met `modelValue` + `initieelWeergave` en een zoek-mock die op
`params.zoek` filtert → bij focus wordt `zoek: undefined` doorgegeven en verschijnt de volledige lijst.
Referentie: `ZoekSelect.vue` `openen()`/`zoek(term)`; tests in `ZoekSelect.test.js` +
`GebruikersbeheerView.test.js` (beheer-afdeling-picker toont alle org-afdelingen).

**5. Een picker in een voortlevende dialog krijgt een `:key`, opgehoogd bij openen (LI032).** Zit een
voorgevulde `ZoekSelect`/`AfdelingSelect` in een beheer-/bewerk-dialog die tussen entiteiten **niet
opnieuw mount** (dialog blijft leven, alleen de inhoud wisselt), geef 'm dan een `:key` die je in de
open-handler ophoogt (bv. `beheerOrgKey`/`beheerAfdKey` in `openBeheer`). Zonder remount blijft het
`gekozenLabel` van de vorige entiteit hangen — de `initieelWeergave`-watch update alleen `if
(!gekozenLabel)`, dus het label wordt **stale**. **Symmetrisch voor org- én afdeling-picker** (de ene
wél en de andere niet keyen is precies hoe de stale-label-bug ontstond). Onzichtbaar zolang alle
entiteiten dezelfde waarde delen (bv. één interne organisatie), fout zodra er meer zijn. Referentie:
`GebruikersbeheerView.vue` (`beheerOrgKey`/`beheerAfdKey`); regressie: open twee gebruikers na elkaar
en assert dat het label meebeweegt (`GebruikersbeheerView.test.js`, geen-stale-label).

## Overlay-positionering (LI044) — een venster valt nooit buiten beeld

Een overlay/popover (verantwoordingsvenster, veld-uitleg, klik-popup) **valt nooit buiten het
zichtbare gebied**: **flip** boven↔onder naar de beschikbare ruimte + **horizontaal klemmen** binnen
beeld, **herberekend bij openen én bij resize/scroll**. Gebouwd als gedeelde bouwsteen
`frontend/src/composables/popoverPositie.js`:
- **Rekenkern puur + unit-getest** — `berekenPopoverPositie({trigger, paneel, viewport})` beslist
  flip/klem zonder layout-engine (jsdom doet geen layout — zie likara-tests, pure-functie-patroon);
- **bedrading browser-geverifieerd** — `usePopoverPositie(paneelRef)` koppelt de kern aan
  `getBoundingClientRect` + resize/scroll (`position: fixed`); de feitelijke plaatsing toets je in de
  browser, niet in de suite.
- **A11y blijft bij de aanroeper** (Escape/klik-buiten/focus-terug/aria) — dit gaat puur over plaatsing.

**Elke overlay-consument hoort deze bouwsteen te dragen** (KERNLES LI038: "elk pad dat de regel kan
omzeilen moet hem dragen, of het pad moet niet bestaan"). **Gedragen door `MigratiegereedheidSectie`
én — sinds LI045 slice 4c — `VeldUitleg`** (adopteerde `usePopoverPositie`; eigen `absolute`-overlay
vervangen door `fixed` + flip/klem, dus het paneel valt niet meer buiten beeld onderaan een scrollende
Dialog). **Alle ~29 VeldUitleg-schermen erven de fix uit die ene bouwsteen** — geen tweede
positioneringslogica per view. Borging: regressietest in `VeldUitleg.test.js` (paneel is `fixed`, niet
`absolute`) + de pure-functie-tests op `berekenPopoverPositie`. Duikt er een nieuwe eigen-overlay op,
dan adopteert die de bouwsteen op dezelfde wijze (repareer in de bouwsteen, niet in de consument —
werkprotocol KERNLES LI038 #3).

## Cytoscape.js Vue 3 integratiepatroon (DC013, niet-onderhandelbaar)

Cytoscape.js in een Vue 3 flex-container vereist vier dingen voor een correcte render.
Mis je één ervan → lege canvas.

### 1. Import via composable-wrapper
Importeer Cytoscape nooit direct in een module-view (module-path-problemen buiten `frontend/`).
Gebruik de wrapper:
```javascript
// frontend/src/composables/cytoscape.js
import cytoscape from 'cytoscape'
export default cytoscape

// In de view:
import cytoscape from '@/composables/cytoscape'
```

### 2. Container-hoogte (KRITIEK: min-h-0 op elk flex-niveau)
```html
<div class="flex flex-col h-screen">              <!-- outer -->
  <div class="flex flex-1 min-h-0">               <!-- rij -->
    <div class="flex-1 min-h-0 min-w-0 relative"> <!-- canvas-kolom -->
      <div id="cy" class="w-full h-full" style="min-height: 500px;"></div> <!-- vangrail -->
    </div>
  </div>
</div>
```
Zonder `min-h-0` negeert een flex-child de `height:100%` van zijn parent → Cytoscape
initialiseert op hoogte 0 → lege canvas. `min-height: 500px` op `#cy` is de harde vangrail.

### 3. Initialisatie: nextTick×2 + offsetHeight-check + fit via de layout-stop-callback
```javascript
async function tekenGraaf() {
  await nextTick(); await nextTick()  // tweede tick voor Vite HMR edge-cases
  const el = containerRef.value
  if (!el) return
  if (el.offsetHeight === 0) { el.style.minHeight = '500px'; await nextTick() }
  cy.elements().remove(); cy.add(elementen)
  cy.layout({ ...layout, stop: _naLayout }).run()  // resize/fit/highlight in de STOP-callback
}
function _naLayout() {           // ADR-040: deterministisch bij het EINDE van de layout, geen setTimeout
  cy.resize(); cy.fit(undefined, 50)
}
```
> **ADR-040 (aangescherpt, vervangt de oude `setTimeout(...,100)`-hack):** de her-meting + fit + het
> opnieuw aanbrengen van highlight/dim horen **deterministisch in de layout-`stop`-callback**, niet in
> een losse `setTimeout` (een timing-hack die op een langzame/dichte render mis kan gaan). Zie P5a hieronder.

### 4. ResizeObserver voor dynamische containers (guarded; disconnect bij unmount)
```javascript
let resizeObserver = null
onMounted(async () => {
  cy = cytoscape({ container: containerRef.value, elements: [], style })
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => { cy?.resize(); cy?.fit(undefined, 50) })
    resizeObserver.observe(containerRef.value)
  }
  await tekenGraaf()
})
onBeforeUnmount(() => { resizeObserver?.disconnect(); cy?.destroy(); cy = null })
```

### 5. Testpatroon (Cytoscape mocken — test de panelen/logica, niet de render)
```javascript
vi.mock('@/composables/cytoscape', () => ({
  default: vi.fn(() => ({
    add: vi.fn(), layout: () => ({ run: vi.fn() }), fit: vi.fn(), resize: vi.fn(),
    destroy: vi.fn(), on: vi.fn(), zoom: () => 1, animate: vi.fn(),
    elements: () => ({ remove: vi.fn(), unselect: vi.fn() }),
    getElementById: () => ({ length: 0, select: vi.fn() }),
  })),
}))
```

### P5a — Deterministische layout + render-eigenaar-discipline (ADR-040)

- **Layouts moeten deterministisch zijn** (built-in `grid`/`concentric`): identieke posities bij
  herhaling, geen naschuiven. **Geen niet-deterministische force-layout** (`cose`/`fcose`) zonder
  browserbewijs van stabiliteit — die familie gaf eerder de "edges-onzichtbaar"/samenval-bugs. Render
  **niet-geanimeerd** bij dichte grafen: een `animate:true` die nodes vanaf (0,0) laat invliegen kan op
  een dichte graaf niet settelen → knopen vallen samen.
- **Render-eigenaar = één opbouw, één layout, fit via de `stop`-callback.** `tekenGraaf` doet
  `remove → add → layout(...).run()`; álle post-layout werk (resize, fit/center, highlight/dim, en een
  post-layout **transform** zoals een ellips-schaling) hoort in de `stop`-callback: die **leest cy-state
  en past posities aan** — géén `setTimeout`-timing-hack, géén re-layout, géén reactieve-state-mutatie
  (anders een render-loop). Uitrek-transforms mogen alleen **spreiden**, nooit comprimeren (geen nieuwe
  overlap).

### P6a — Tweedeling-layout: de weergave volgt de vraag, niet de set-grootte (ADR-040)

Verschillende gebruikersvragen verdienen verschillende layouts, gekozen op de **expliciete weergave-state**
(niet op set-grootte): een **landschap-zonder-centrum** (overzicht) krijgt een **centrumloze** spreiding;
een **één-object-met-omgeving** (praatplaat) krijgt een **radiale** (concentric). Leg **nooit een
centrum-vorm op aan iets zonder centrum** — een concentric op een centrumloos landschap geeft een
stervorm. (De concrete layout-keuzes van deze sessie staan in ADR-040, niet hier.)

## Rol-gating = affordance (backend handhaaft)

```javascript
// src/store/auth.js — hasRole IS functioneel post-ADR-010 (rollen uit /auth/me)
const auth = useAuthStore()
auth.hasRole('medewerker', 'beheerder')   // toont/verbergt knoppen
```

De UI verbergt alleen knoppen; de **backend** handhaaft via `vereist_permissie`.
Vang een toch-403 netjes af (Toast). Nooit tokens in `localStorage` (httpOnly).

**Destructieve gating volgt de rollengrens op het ONDERWERP (ADR-050, herzien LI041 — vervangt de
oude LI037-formulering).** Welk recht een verwijder-/ontkoppel-knop eist, hangt af van **wát**
verwijderd wordt, niet van het werkwoord:

- **Registratie-feit** (een uitspraak óver het landschap — koppelingen, gebruik, rollen, scores,
  vervullingen, álle `relatie`-typen): guardt backend-zijdig op **`WIJZIGEN`**, dus de frontend
  gate't op de **medewerker**-check (`magBewerken`/`mag` = medewerker|beheerder). De medewerker
  neemt zijn eigen uitspraak terug.
- **Landschapsobject** (iets dat bestáát — component · contract · partij · datatype ·
  gebruikersgroep · bedrijfsfunctie · proces · plateau · work_package · deliverable · gap): guardt
  op **`VERWIJDEREN`**, dus `magVerwijderen = computed(() => auth.hasRole('beheerder'))`.

⚠ **Dit is géén "beheerder-only met twee uitzonderingen" meer** (zoals de oude LI037-regel het las —
die duwde een volgend registratie-feit weer richting VERWIJDEREN, precies de fout die ADR-050 bij
zeven feiten verhielp). Het is een **categorie**: de bron van waarheid is `verwijder_actie(entiteit)`
in `rbac.py` (`REGISTRATIE_FEIT_ENTITEITEN`/`LANDSCHAPSOBJECT_ENTITEITEN`); de frontend-gating
**spiegelt** die, nooit strenger of losser. Bij een nieuw feit: kijk wat `verwijder_actie` teruggeeft,
kies dan `magBewerken` of `magVerwijderen`. Vooraf weren (actie niet tonen), nooit een
backend-403-pas-in-de-dialoog op een destructieve knop. (Domeinregel: likara-domeinmodel §7;
backend-borging `test_rollengrens_adr050`.)

## Login-patroon (LoginView)

- Launch-page met één knop → **volledige** browser-redirect:
  `window.location.assign('/api/v1/auth/login')` (geen `fetch`, geen in-app
  wachtwoordveld). `next` alleen meesturen bij een same-origin relatief pad
  (backend hervalideert). `?sessie_verlopen=1` → inline `role="alert"`.
- Na login zet de backend `lk_session` en redirect naar `next` (default `/`); de
  router-guard zet de gebruiker door.

## Testopzet (vitest)

- Poorten: `vite build` + `vitest` (geen eslint/type-check).
- Module-view-tests staan onder **`frontend/tests/`** (binnen de vitest-root;
  vitest scant niet buiten `frontend/`) en importeren de view via `@modules`.
  **Uitzondering [LI035]:** de AppLayout-tests staan colocated in `frontend/src/layouts/`
  (`AppLayout.test.js` + `AppLayout.gating.test.js`) — een nieuwe named route moet in
  BEIDE testrouters daar geregistreerd worden, anders breken ze.
- Mock `@/api` met `vi.mock`; mount met `[pinia, [PrimeVue,{unstyled:true}],
  ToastService, router]`. PrimeVue `Dialog` teleporteert naar body → gebruik
  `global.stubs: { teleport: true }` zodat `find()` de inhoud ziet. `window.location`
  via `vi.stubGlobal('location', { assign: vi.fn() })`.

## Openstaande punten (V003)

| Onderdeel | Status |
|---|---|
| `tenantSlug`-getter | Leest `user.tenant_slug`, maar `/auth/me` geeft `tenant_id` → altijd null. Fix bij theming. |
| Bundle >500 kB | DataTable; route-level lazy-loading als optimalisatie. |
| Per-tenant thema's | `useTheme` aanwezig; nog geen tenant-thema's. |
| Login/SSO-logout | OP-3 (refresh) / OP-4 (RP-logout) open. |

## V004-patronen (CD003–CD012, geverifieerd)

- **Secties-in-detail i.p.v. child-routes**: child-entiteiten als sectie-componenten
  in `ApplicatieDetail` (prop `applicatieId`), `Dialog`-formulieren, géén aparte
  routes (subordinate aan de ouder). Code-comment waaróm dit afwijkt van Applicatie's
  volledige-route-CRUD. [CD003/CD004]
- **Inline scoringslijst** over een vaste referentieset: native `<table>` + `<select>`,
  per-rij opslaan (maak/werkBij), per-rij inline feedback i.p.v. toast-per-actie,
  client-side join op de **sleutel** — let op `vraag_code`, **niet** `vraag_id`. [CD004]
  **Scope-correctie [LI035]:** de "inline i.p.v. toast"-regel geldt ALLÉÉN voor deze
  hoogfrequente per-rij-scoringslijst — relatie-secties en dialogen volgen de
  succes-toast-standaard (`toastSucces`, zie LI035-patronen). LI035 paste CD004 eerst
  te breed toe op de proces-secties; dat is teruggedraaid.
- **Systeem-afgeleide entiteit-view**: géén Toevoegen/Verwijderen-affordance; beperkte
  status-dropdown; auto-afgeleide status (`opgelost`) als **read-only badge** (zichtbaar,
  niet kiesbaar); bij opslaan de read-only status NIET meesturen. [CD004/CD011]
- **Mutatie met neveneffecten → gecoördineerde refetch**: na een score de
  lifecycle-indicator **en** de blokkadelijst herladen; ouder coördineert via
  `defineExpose` (tellers) + `emits('gewijzigd')`. De frontend **toont** backend-
  afgeleide status, berekent die **nooit** zelf (ADR-013). [CD004]
- **Bron-OF-doel-lijst via twee disjuncte calls**: concat zonder dedup (DB-CHECK
  `bron≠doel` ⇒ disjunct), per-richting "Meer laden". [CD003]
- **A11y in Dialog-formulieren**: `:closable="false"` → focustrap focust het eerste
  veld; focus terug naar trigger op sluiten; `aria-labelledby`/`aria-invalid`/
  `aria-describedby`; 422-veldfouten **in-form** op het veld, overige codes als Toast. [CD003/CD004]
- **401 status-gebaseerd + single-flight refresh-on-401** (`api.js`): keyt op HTTP-status
  (niet body/code); één gedeelde refresh-promise bij gelijktijdige 401's; retry-guard
  (`_isRetry`); `/auth/refresh` via raw fetch → triggert geen eigen refresh (geen lus). [CD005/CD007]
- **Route-level lazy-loading** (OP-19): zware route-componenten als `() => import(...)`;
  LoginView + AppLayout eager (first paint). Houdt Optie-A/`@modules`/cross-root-barrels
  + guard intact; alleen het laadmoment verschuift. [CD012]

## V005-patronen (CD022/CD023, geverifieerd)

- **`AppTabs.vue` — herbruikbare toegankelijke tablist** (`modules/.../frontend/views/AppTabs.vue`):
  rendert de tablist (`role="tablist"` + `role="tab"` met `aria-selected`/`aria-controls`/
  roving `tabindex`); de **ouder rendert de panelen** (`role="tabpanel"`, `aria-labelledby`).
  **Automatic activation**: ←/→ (↑/↓ bij `orientation="vertical"`) + Home/End verplaatsen de focus
  **én** selecteren direct (panelen zijn gemount, dus goedkoop); Enter/Space selecteren het
  gefocuste tabblad eveneens (idempotent — het is dan al geselecteerd). Props
  `tabs`/`modelValue`/`ariaLabel`/`orientation`/`idPrefix`; `--lk-`-tokens, geen `<style>`. [CD022]
- **Eén gekozen tabblad is een INVARIANT, geen afspraak (LI048).** `AppTabs` dwingt niets af: een
  `modelValue` die bij géén tab hoort geeft `aria-selected="false"` op álle tabs én — venijniger —
  `tabindex="-1"` op álle tabs, waardoor de hele rij **uit de toetsenbordvolgorde valt**. LI047 had
  hier bewust een uitzondering (`PLEKKEN_ZONDER_TAB`, "Open punten" als plek zónder tabblad); die is
  met LI048 herroepen. Elke plek in het adres is een tabblad. Borging: `ComponentDetail.test.js`
  telt over **élke** `role="tablist"` en elke bereikbare staat (binnenkomst · elk tabblad geklikt ·
  deep-link incl. een onzin-`?tab=`) dat er precies één `aria-selected="true"` én precies één
  `tabindex="0"` is — aantoonbaar bijtend (een heringevoerde uitzondering laat de telling naar 0
  zakken).
- **3-laags tabs + deep-link** (ComponentDetail; herkomst CD022/ApplicatieDetail). Sinds LI048 2b:
  groepsrij → sub-rij (onderdelen) → de verticale checklist-categorierij. Elk niveau is een echte
  `AppTabs`; de sub-rij en de categorierij dragen `niveau="2"` (drie gewichten zou overdreven zijn,
  en de categorierij staat bovendien op een andere as — verticaal, naast het paneel).
  De actieve plek in de URL via query-params (`?tab=`/`&cat=`), `router.replace`
  (geen history-spam), default = schone URL. Alle panelen blijven **gemount** (`v-show`) → geen
  state-verlies bij wisselen, en refs/voortgang-tellers blijven geldig. De 12 categorie-tabs
  voeden **één gedeelde** sectie-instantie met een `categorieNr`-filterprop (één load, gedeelde
  state) i.p.v. N× mounten/laden. [CD022]
- **Visualisatie → toegankelijk tabel-alternatief is de waarheidsbron** (ADR-018, CD023): een
  grafiek (hand-rolled SVG, `role="img"` + samenvattende `aria-label`) is **verrijking**; de
  toetsenbord-/screenreader-toegankelijke tabel ernaast ontsluit dezelfde data en is de primaire
  interface. **Gefocuste ego-graaf** (één entiteit + directe buren, hercentreerbaar) i.p.v. een
  volledige graaf → schaalt naar honderden knopen zonder hairball; **geen** zware graaf-dependency. [CD023]
- **Platform-view consumeert module-data**: tenant-brede views (`DashboardView`,
  `BlokkadeOverzichtView`, `KoppelingenkaartView`) staan in `frontend/src/views/`, als lazy-route
  child onder `AppLayout` + nav-item; labels via `@modules/bwb_ontvlechting/frontend/labels`. [CD016/CD023]

## V006-patronen (CD025–CD038, ADR-019, geverifieerd)

- **Sessietype-bewuste auth in één SPA** (login-aanpak a): `store/auth.js` `fetchSession` probeert
  `/auth/me` (200 → `sessionType='tenant'`); bij 403 valt het terug op `/auth/platform/me` (200 →
  `'platform'`). De **bestaande PKCE-login + httpOnly-cookies worden hergebruikt** — geen aparte
  login. De router-guard delegeert naar een **pure, testbare** `routeBeslissing(to, auth)`: tenant op
  een platform-route → `/`, platform op een tenant-route → `/beheer`. De tenant-flow blijft ongemoeid.
  [CD032/CD033]
- **Aparte lichte beheer-shell** (`BeheerLayout`, `meta.platform`) los van de tenant-`AppLayout`;
  hergebruikt dezelfde `auth.logout()` (RP-logout werkt identiek voor platform). [CD033]
- **Beheer-UI = pure schil op de server-endpoints**: dupliceer **geen** serverregels — de UI biedt
  affordances + nette foutweergave. **409 `CONFIGURATIE_CONFLICT`** (orphan/afgeleid) → inline + toast;
  **422 native** → veldfout; 401/403/404 standaard. Afgeleide sets (2.1/12.1) read-only via
  `afgeleid_bron` (alleen label editbaar; geen toevoegen/deactiveren/volgorde). [CD034]
- **Antwoordcontrole per type in de CD025-uitklaprij**: native `<select>` (enkelvoudige_keuze) /
  checkbox-groep (meerkeuze) / `number` (getal); opties uit `vraag.opties` (alleen `actief` kiesbaar,
  inactieve enkel voor label-resolutie). Opslaan via het bestaande `werkBij`-pad **mét `antwoord_waarde`,
  zónder `score`** (engine-no-op); `disabled-tot-gescoord`. Kolomkop "Score" → **"Afgehandeld"**. [CD029]
- **Categoriefilter zonder categorie-naam**: de platform-config-read kent geen `categorie_naam` (en het
  platform-account mag het tenant-`/checklistvragen` niet) → filter afgeleid uit de **code-prefix**
  (`code.split('.')[0]`). [CD034]

## V007-patronen (CD039–CD056, geverifieerd)

- **ZoekSelect-regel**: elk keuzeveld dat een **entiteit-referentie** is (onbegrensd groeibaar —
  leverancier, contract, applicatie, doel-component) is een **server-side zoekende `ZoekSelect`**
  (`modules/.../views/ZoekSelect.vue`): debounce, ~10 resultaten + "verfijn"-regel, leeg-veld =
  startlijst (gedraagt zich als dropdown bij kleine sets), combobox-a11y (↑/↓/Enter/Escape,
  `aria-activedescendant`), `extraFilters`, `defineExpose({focus})` voor Dialog-autofocus,
  `testid`-prefix per instantie. Vaste **enums** blijven native `<select>`; catalogus-gedreven
  lijsten heroverwegen boven ~10 opties (opvolgpunt C-drempel). [CD049]
- **Verenigde Componenten-lijst (doelbeeld sinds CD054b-v2)**: één werkscherm met een Type-kolom +
  **besturingskolommen** (Eigenaar/Complexiteit/Prioriteit/Status), **"—"** voor niet-beoordeelde
  typen, vaste kolommenset (voorspelbaar scherm), filterbalk incl. status. Subtype-rijen linken
  naar **ApplicatieDetail** (rijk detail, één waarheid per perspectief); aanmaak met type
  `applicatie` redirect naar de checklist (convergentie). **Geen apart Applicaties-menu** — de oude
  lijstroute `/applicaties` is een **redirect** naar de Componenten-lijst met `?type=applicatie`;
  `/applicaties/:id` blijft de subtype-detailview. [CD054]
- **Impact-paneel (ADR-021 Fase E)**: **read-only**, **knop-getriggerd** (geen eager load), de
  toegankelijke **tabel is de waarheidsbron** (geen graaf-visual); samenvatting + geraakte
  componenten (naam·type·niveau·relatie·lifecycle·open blokkades), pad uitgeklapt bij niveau > 1,
  subtype-rij → ApplicatieDetail. Gemount op zowel ComponentDetail (sectie) als ApplicatieDetail
  (tab) — élk type kan onderlegger zijn. Géén acties/schrijf-affordances. [CD056]

## V010-patronen (ADR-023 Fase F — F-1…F-3, geverifieerd)

- **Read-only lees-/inzicht-views in `frontend/src/views/`** (migratielaag-lijsten, `ArchitectuurView`,
  `PlaatsingSignalenView`): lazy import + child-route onder `AppLayout`, gegate op **`MIGRATIE_ROLLEN`**
  (= de `ARCHITECTUUR.LEZEN`-rollen: viewer/medewerker/beheerder/auditor); labels via
  `@modules/bwb_ontvlechting/frontend/labels`. De nav-link in `AppLayout.vue` is de affordance
  (`v-if="magArchitectuurZien"`/`magMigratieZien`); de **backend handhaaft** (`vereist_permissie`).
- **Test-router-gotcha (recurring)**: een gegate `router-link` naar een **nieuwe named route** vereist
  die naam in **beide** AppLayout-testrouters — `AppLayout.test.js` (children-array) **én**
  `AppLayout.gating.test.js` (`NAMEN`-lijst) — anders gooit vue-router bij mount. Voeg de naam in beide
  toe tegelijk met de nav-link.
- **Signaal/afgeleide weergave = leesbare tekst, backend levert de grond**: de view mapt sleutels naar
  leesbare labels (bv. `beoordeeld_niet_vastgelegd` → "Plaatsing beoordeeld maar niet vastgelegd") en
  toont de door de backend geleverde `reden`; de sleutel zelf is **niet** zichtbaar (test asserteert dat).
  Lege staat expliciet ("geen signalen") + foutregel met `role="alert"`. Eenvoudige `<table>` volstaat
  voor een begrensd afgeleid overzicht (geen DataTable/paginering nodig).

## V012-patronen (ADR-024 slice 2a/2a-bis + sorteer-eis, geverifieerd)

- **VASTE UI-EIS — elke rij-tabel is per kolom sorteerbaar.** Iedere lijst-/rij-tabelweergave krijgt
  per kolom sortering. Mechanisme volgt de groei van de dataset:
  - **Lijst kan groeien / is gepagineerd ⇒ SERVER-SIDE sortering** over de **volledige** dataset:
    het ADR-017-keyset-patroon (`lazy` DataTable + `:sort-field`/`:sort-order` + `@sort="onSort"` →
    `sort`/`order` + cursor-reset + refetch), met een sorteer-allowlist op het endpoint. Zo doen
    `ComponentLijst`/`BlokkadeOverzichtView`/`ContractLijst`/`PartijLijst` het, en sinds V012 ook het
    **leden-overzicht op partij-detail** (kolommen Naam/Aard `sortable`, filter + sort/order/after in
    elke fetch). **NOOIT** client-side sorteren op alléén de zichtbare pagina — dat sorteert een
    deelverzameling en is misleidend.
  - **Alleen écht vaste, korte tabellen** (een handvol rijen, groeit niet) mogen client-side: PrimeVue
    `sortable` op een **niet-lazy** DataTable (sorteert in-memory). **Bij twijfel: server-side.**
  - **Niet-tabellen** (grafen/projecties/bomen: `KoppelingenkaartView`, `ArchitectuurView`,
    `ImpactSectie`) vallen buiten de eis.
  - **Openstaande sorteer-sweep** (zie `OPVOLGPUNTEN.md`): PartijLijst Aard/Contactpersoon,
    config-beheer-tabellen, detail-sub-tabellen (client-side) + de vier migratie-lijstviews
    (server-side, allowlist per endpoint) — nog niet sorteerbaar; geen tabel vergeten.
- **api-client geeft élke filter door**: een nieuwe lijst-filter (bv. `organisatie_id`/`afdeling_id`)
  moet in `api.<resource>.lijst` **zowel** in de destructuring **als** in `_query({…})` staan — anders
  dropt de client de filter stil en haalt het scherm ongefilterd álles op (V012-bug: leden-blok toonde
  het hele register). Borg dit end-to-end (een service-/SQL-test bewijst het scherm-gedrag niet — zie de
  tests-skill).
- **Signalering/registratiegat — niet generaliseren vóór n=3**: het patroon "registratiegat zichtbaar
  maken" (status-indicator + filter + dashboard-telling met doorklik) niet abstraheren tot er ≥3
  concrete instanties zijn. Bouw concrete gevallen apart langs bestaande patronen; abstraheer pas bij
  bewezen herhaling.

## V015-patronen (ADR-027 — read-only sluiten + dashboard-doorklik, geverifieerd)

- **Read-only sectie bij een gesloten invoerpad.** Vouw "mag bewerken" in één computed:
  `mag = rolOK && bewerkbaar` (prop `bewerkbaar`, default true). Bij `bewerkbaar=false` zijn
  alle invoercontrols `:disabled` én verschijnt een **banner** ("… gesloten voor bewerking,
  bestaande antwoorden blijven leesbaar") — maar **alleen voor wie de rol heeft** (geen ruis
  voor viewers): `toonMelding = rolOK && !bewerkbaar`. De parent geeft `:bewerkbaar` door en
  toont de sectie ook read-only voor een gesloten-met-data geval (bv.
  `v-if="dragend === true || lifecycle_status"`).
- **Dashboard-tegel + doorklik (bestaand patroon).** Een telling = `<router-link class="card …">`
  met `:to="{ name: 'component-lijst', query: { … } }"`, `--lk-`-tokens, `data-testid="telling-…"`.
  Een afwijkings-/waarschuwingstegel krijgt nadruk via **kleur + icoon + tekstueel label**
  (niet alléén kleur — toegankelijk) en is alléén warn-gekleurd bij `> 0`.
- **Doorklik-filter end-to-end (V012-les, opnieuw).** Een nieuwe filter MOET in de api-client
  zowel in de `lijst`-destructuring ALS in de `_query` staan, anders dropt de client hem stil.
  De lijst-view leest de filter uit `route.query`, zet hem in `params`, en toont een **wisbare
  chip** (zien + wissen) i.p.v. een dropdown wanneer de filter puur van een doorklik komt.
  Bewijs het end-to-end met een component-test (route-query → de filter belandt in de api-call;
  wissen → de filter verdwijnt uit de volgende call) — een SQL-/service-test bewijst dit niet.

## V016-patronen (DC015 — gebruikersbeheer + objecthistorie)

- **Eenmalig-geheim-weergavepatroon.** Na een aanmaak die een eenmalig geheim teruggeeft
  (server-gegenereerd wachtwoord): toon het in een **tweede dialog-staat** met kopieerknop
  (`navigator.clipboard`) + begeleidende tekst ("eenmalig; bij eerste login wijzigen"); leeft
  alleen in component-state, gewist bij sluiten, nooit in store/localStorage. "Klaar" sluit +
  herlaadt de lijst.
- **Herbruikbaar objecthistorie-paneel (`ObjectHistoriePaneel.vue`).** Props
  `entiteitType`/`entiteitId`; 'i'-knop (`aria-label="Toon geschiedenis"`) opent een Dialog,
  lazy-laad bij openen, keyset "Meer laden", per-record diff "veld: oud → nieuw" met NL-veldlabels
  (`VELD_LABELS` in labels.js + humanize-fallback). **Geen rol-gating op de knop** — toegang volgt
  het object (backend handhaaft). Geplaatst op alle detailschermen met een object-read +
  leespermissie (component/applicatie/contract/partij/plateau/work_package/deliverable/gap).
  `*_id`-velden tonen een leesbaar label; de waarde blijft de gelogde id (id→naam-resolutie per
  veld bewust buiten scope).
- **Beheer-scherm gegate op rol-affordance.** Gebruikersbeheer-nav + -knoppen via
  `hasRole('beheerder')`; audit-view-nav via `hasRole('beheerder','auditor')`. Affordance —
  backend blijft de handhaver. Nieuwe gegate named-route → registreer 'm in BEIDE
  AppLayout-testrouters (`AppLayout.test.js` + `AppLayout.gating.test.js`), anders faalt de mount.

## Kaart edge-groepering + master-detail popup (DC017, ADR-023a Fase 3+4)

### Edge-groepering (LandschapskaartService)
- Groepeer flows per gericht paar (bron_id, doel_id) → één LandschapsEdge met `aantal: int = 1`.
- Richting/protocol: van eerste flow; niet-uniform → `"bidirectioneel"` resp. `None`.
- Frontend: badge op edge-label als `aantal >= 2`.

### Ongeordend-paar-fetch
- Edge-klik: fetch via `paar_bron_id` + `paar_doel_id` (niet gericht bron_id/doel_id).
- Backend-filter: `(bron=A AND doel=B) OR (bron=B AND doel=A)`.
- api.js allowlist: `paar_bron_id`, `paar_doel_id`.

### Master-detail popup (universeel, ook n=1)
- Links (~40%): gesorteerde lijst naam + richting-icoon
  (groen → = bron_id===edge.bron_id, rood ← = bron_id===edge.doel_id).
- Rechts (~60%): detail geselecteerde koppeling.
- Client-side sort op naam ASC; eerste rij auto-geselecteerd.
- Geldt voor ALLE edge-klikken (ook n=1) — vervangt enkelvoudige popup.

### KOPPELING_DUBBEL-dialoogpatroon (DC017, ook in likara-backend)
- 409 met code `KOPPELING_DUBBEL` → bevestigingsdialoog (NIET fout-toast).
- "Toch aanmaken" → hersubmit met `negeer_waarschuwing: true`.
- Overige 409 (RELATIE_BESTAAT) → bestaande fout-toast.
- Formulier blijft open bij Annuleren (data behouden).

## Detail-navigatie watch-patroon (DC017)

Detail-views die via router-link naar dezelfde componentnaam navigeren (partij→partij,
component→component) hergebruiken de Vue-instance → onMounted vuurt niet opnieuw.

Fix: vervang onMounted door:
```
watch(() => props.id, () => herlaad(), { immediate: true })
```
- `immediate: true` vervangt onMounted volledig.
- Voeg `:key="props.id"` toe op zelf-ladende child-secties (PartijRollenSectie,
  ObjectHistoriePaneel etc.) zodat die ook remounten.
- Toegepast op: PartijDetail, ComponentDetail, ApplicatieDetail (DC017).
- NB: child-secties in Component/Applicatie-detail die zelf in onMounted laden
  zonder :key kunnen nog stale zijn bij detail→detail-hop — OPVOLGPUNT DC018.

## Context-in-header patroon (DC017)

Parent-context ("hoort bij", "valt onder", "overgang") hoort als klikbare
subtitelregel IN de header-div, direct onder naam + badge — NIET onder contentblokken.

```html
<div class="flex items-center gap-2">
  <h1>{{ naam }}</h1><Tag :label="aard" />
</div>
<p class="text-sm text-secondary mt-1">
  <router-link :to="{ name: 'partij-detail', params: { id: ouderOrgId } }">
    {{ ouderOrgNaam }}
  </router-link>
  <span v-if="ouderAfdelingNaam"> › <router-link ...>{{ ouderAfdelingNaam }}</router-link></span>
</p>
```

Toegepast op DC017: PartijDetail (hoort bij), ContractDetail (valt onder mantelcontract),
GapDetailView (overgang baseline→doel), WorkPackageDetailView (onderdeel van bovenliggend pakket).

## Aard_in-filter ZoekSelect (DC017)

Voor ZoekSelect die alleen bepaalde aarden moet tonen:
- Backend: voeg `aard_in: list[str] | None = Query(None)` toe aan het lijstendpunt.
- Service: filter `WHERE aard = ANY(:aard_in)` indien meegegeven.
- api.js allowlist: `aard_in` toevoegen.
- Voorbeeld: GebruikersgroepSectie organisatie-picker → `aard_in: ['organisatie']` (ADR-038 — de
  `burger`-aard is verwijderd; burger-doelgroepen zijn gewone externe organisaties).

## Detail-view patroon — props.id watch (VERPLICHT, LI018)

Elke detail-view die via een route-param geladen wordt MOET een watch gebruiken
i.p.v. alleen onMounted. Dit voorkomt dat Vue Router de component hergebruikt
zonder opnieuw te laden bij param-wissels (bv. contract → contract navigatie).

```js
// CORRECT — altijd zo in detail-views
watch(() => props.id, (id) => { if (id) laad() }, { immediate: true })

// FOUT — mist herladen bij param-wissel op dezelfde route
onMounted(() => laad())
```

Van toepassing op: ApplicatieDetail, ComponentDetail, PartijDetail, ContractDetail,
GapDetail, WorkPackageDetail, PlateauDetail, en alle toekomstige detail-views.

## useTerugNavigatie composable (LI018)

Contextgebonden terugknop op detail-pagina's.

```js
import { useTerugNavigatie } from '@/composables/useTerugNavigatie'
const { terugLabel, gaTerug } = useTerugNavigatie()
// terugLabel: "← Terug naar Landschapskaart" / "← Terug naar Partijen" / etc.
// gaTerug: router.back()
```

Herkomst wordt globaal bijgehouden via router.afterEach in router/index.js.
Knop verborgen als er geen vorige route is (directe URL-toegang).

## Landschapskaart — state en ringen (LI018)

**Ringen (frontend):** `['applicaties', 'rollen', 'gebruikers', 'contracten', 'infrastructuur']`
**Let op:** backend levert ring='beheerorganisatie' → frontend mapt dit bij laden naar 'rollen'.

**State-preservatie:** sessionStorage key `lk-state`
(modus / egoStartId / ringAan / groepeerPerOrg — bewaard bij onBeforeRouteLeave).

**Layout (herzien ADR-040/LI036):** `cytoscape-dagre` én **fcose** zijn verwijderd (fcose = de
edges-onzichtbaar-bug; de Impact-verkenner is afgeschaft). `_layout()` kiest per WEERGAVE:
`concentric` (Praatplaat/ego, + ellips-transform in de stop-callback), built-in `grid`
(Overzicht — deterministisch, centrumloos), `preset` (Lagen — baanposities, zie de
Lagen-weergave-sectie). Alles `animate:false`; géén dagre-/fcose-aanroep.

**Edge-labels:** standaard verborgen (`text-opacity: 0`); zichtbaar op hover of
bij geselecteerde edge (class `sel-edge`).

**Gebruikersgroep-nodes:** groepeerPerOrg default true (client-side aggregatie per organisatie).

**Actieve set (LI027):** zoekbalk in de resultatenlijst, "Wis alles"-knop, en
"Focus op actieve set"-toggle (graph toont alleen set-nodes + directe buren).

## ArchitectuurLagenView (LI018)

Visuele ArchiMate-lagenweergave naast de bestaande DataTable.
Toggle 'Tabel / Lagen' (default: Lagen), localStorage key `arch-weergave`.

Kleurschema laagbands:
- business: `#185FA5`
- application: `#0F6E56`
- technology: `#5F5E5A`
- implementation_migration: `#993C1D`

Pill-stijl per aspect: active=solid border, passive=dashed border, behavior=ronde pill (border-radius:99px).

---

## ZoekMultiSelect-patroon (LI019)

Doorzoekbare multi-select bovenop ZoekSelect. Gebruik voor alle Landschapskaart-filters
én elke andere multi-select behoefte met server-side zoeken.

**Component:** `modules/.../frontend/views/ZoekMultiSelect.vue`

Kenmerken:
- Chips per geselecteerde waarde, elk verwijderbaar met ×
- "× Wis"-knopje verschijnt alleen bij ≥1 chip (wist alle chips in één klik)
- Blijft open na elke keuze (heropenNaKeuze=true op de onderliggende ZoekSelect)
- Vaste onderste optie mogelijk via `vasteOptie`-prop (bijv. "Zonder leverancier")
- Geen selectie = lege array = alles tonen (nooit een "Alle X"-optie toevoegen)

```vue
<ZoekMultiSelect
  v-model="geselecteerdeIds"
  :zoek-functie="zoekLeveranciers"
  :weergave="(p) => p.naam"
  :id-veld="'id'"
  :vaste-optie="{ label: 'Zonder leverancier', waarde: '__zonder__' }"
  placeholder="Zoek leverancier…"
  testid="lk-filter-leverancier"
/>
```

---

## Landschapskaart filter-patronen (LI019)

### Filter-exemptie regel (niet-onderhandelbaar)
Context-nodes (contracten, partijen, gebruikersgroepen) hebben geen attribuut-kenmerken
(geen leverancier, hosting, lifecycle). Ze worden NOOIT weggefilterd bij een attribuut-filter —
alleen nodes mét het kenmerk én niet in de selectie vallen weg.

```javascript
// CORRECT
if (filterLeveranciers.value.length && n.leverancier_id && !filterLeveranciers.value.includes(n.leverancier_id)) return false
// n.leverancier_id falsy → node heeft geen leverancier → niet wegfilteren

// FOUT
if (filterLeveranciers.value.length && !filterLeveranciers.value.includes(n.leverancier_id)) return false
// filtert ook nodes weg zonder leverancier_id
```

### "Zonder [X]" als expliciete filteroptie
Voeg aan elke attribuut-filter een vaste onderste optie "Zonder [X]" toe.
- Geen filter actief → alles tonen (kenmerkloze nodes zichtbaar)
- Filter actief, "Zonder [X]" niet gekozen → kenmerkloze nodes wegfilteren
- Filter actief, "Zonder [X]" gekozen → kenmerkloze nodes meenemen
- Sentinel-waarde: `'__zonder__'`

### Ego-centrum bevestigingsdialoog
Bij een filterwijziging die het ego-centrum zou verbergen: toon een bevestigingsdialoog
"Het geselecteerde filter verbergt het huidige centrum-component. Wil je doorgaan?"
- Doorgaan → filter toegepast
- Annuleren → filter teruggedraaid (snapshot-revert via guard-flag)
- Alleen in Ego-view (geen centrum-concept in andere modi)

---

## Landschapskaart auto-herpositionering (LI019)

Na elke relevante wijziging (filter, ring, selectie, view) herpositioneert de kaart automatisch.

```javascript
// _naLayout als stop-callback op ELKE layout
function _naLayout() {
  if (modus.value === 'ego' && _recenterPending) {
    _recenterPending = false
    const c = cy.getElementById(String(egoStartId.value))
    if (c?.length) cy.center(c)
  } else {
    cy.fit(undefined, 60)
  }
}
// _recenterPending alleen zetten bij expliciete hercentrering (dubbelklik/selecteerNode)
// Alle andere wijzigingen → cy.fit() via _naLayout
// maxZoom: 1.6 op Cytoscape-init voorkomt extreme inzoom bij kleine node-sets
```

---

## Landschapskaart getekendeNodes-regel — "ring uit wint van gaps" (LI019 → herzien LI036)

Eén gedeelde conditieregel in `getekendeNodes`, identiek voor ALLE weergaven (Overzicht/
Praatplaat/Lagen — de vroegere swimlane-"toont alles"-uitzondering is VERVALLEN):

```javascript
const catRing = _BAAN_RING[_laneVan(n)] // baan→ring; 'overig' heeft geen ring
const gapZichtbaar = toonRegistratiegaps.value && !heeftRelatie.has(n.id) && (!catRing || ringAan.value.has(catRing))
if (gapZichtbaar || egoCentrum || setLid || metZichtbareEdge.has(n.id)) uniek.set(n.id, n)
```

- **Ring uit wint**: een knoop die alléén via uitgezette ringen relaties had verdwijnt —
  óók met "Toon registratiegaps" aan (hij heeft relaties, dus is géén échte gap).
  `metZichtbareEdge` is ring-bewust (uit `zichtbareEdges`, gefilterd op `ringAan`);
  `heeftRelatie` telt over `grafEdges` (alle edges, ring-ongeacht).
- **Échte gap** (geen enkele relatie) toont onder de toggle alleen als de ring van zijn
  CATEGORIE aan staat (`_BAAN_RING`: componenten↔'applicaties'-ring); **'overig'
  (categorieloos) heeft geen ring → altijd zichtbaar onder de toggle** (er is niets
  uitgezet; stil verbergen zou een echte gap onzichtbaar maken).
- `egoCentrum`/`setLid` blijven bewuste altijd-tonen-keuzes.
- Losse knopen zijn dus in ÁLLE weergaven (ook Lagen) alleen via de gaps-toggle zichtbaar.

---

## Auditlog UI-patronen (LI019)

### Actor-weergave fallback-keten
```javascript
// labels.js — actorWeergave(record)
actor_naam → actor_email → actor_sub → "—"
```

Systeem-actor labels (SYSTEEM_ACTOR-map in labels.js):
- `system:dev_seed` → "Systeem (seed)"
- `system:worker` → "Systeem (worker)"
- `system:platform_init` → "Systeem (initialisatie)"
- Overige `system:`-prefixes → "Systeem"

### Entiteit_naam batch-resolver (backend)
Backend levert `entiteit_naam` op AuditRecordRead via een read-only N+1-vrije
batch-resolver (`entiteit_resolutie.py`). Frontend toont:
`"[Entiteit-type] — [entiteit_naam || entiteit_id]"`

### Uitklapbare diff in AuditTrailView
Per rij een chevron-toggle → uitklapbaar detailpaneel met diff:
- update: "veld: oud → nieuw"
- create: "Aangemaakt met: veld = waarde"
- delete: "Verwijderd: veld was waarde"
Hergebruik VELD_LABELS + humanize-fallback uit ObjectHistoriePaneel. Standaard ingeklapt.

---

## Leverancier via contract-keten (LI019)

`leverancier_id` op Landschapskaart-nodes wordt afgeleid via twee paden:
1. Roltoewijzing (externe_partij) — leidend
2. Component → association-relatie → contract → contract.leverancier_id — vult gaten

Roltoewijzing-leverancier wint van contract-leverancier (setdefault-patroon in service).
Dit zorgt dat de leverancier-filter werkt voor alle componenten, ook zonder directe
leverancier-koppeling.

LeverancierDetail (PartijDetail) toont een "Componenten"-sectie voor externe partijen
via endpoint `GET /partijen/{id}/componenten` (keten: contract.leverancier_id == partij
→ association-relatie component→contract → component).

---

## Lagen-weergave (LI036 — gebouwde realiteit; vervangt "Swimlane geparkeerd")

De vroegere geparkeerde swimlane is met LI036 slice 1 tot leven gebracht als **derde
weergave** — en de oude ADR-034-aanname ("HTML/CSS-div-lanes + SVG-overlay is de enige
bewezen architectuur") is daarmee ACHTERHAALD:

- **Eén weergave-as**: `weergave = 'overzicht' | 'praatplaat' | 'lagen'` — de aparte
  `layoutModus`-as ('radiaal'|'swimlane') en `setLayoutModus()` bestaan NIET meer
  (geconvergeerd; een oude `layoutModus`-sleutel in sessionStorage wordt genegeerd).
- **Rendering = Cytoscape preset-baanposities** (`_swimlanePositions` → de preset-tak in
  `_layout()`), **géén compound-nodes** (compound faalde eerder op edge-rendering tussen
  lanen + pointer-events). Knopen én lijnen blijven puur Cytoscape; de baan-koppen +
  scheidslijnen zijn een HTML-band-overlay óver het canvas (twee lagen: banden z-0 onder,
  koppen z-5 boven, `pointer-events-none`; gesynct op pan/zoom/layout-stop).
- Zelfde node-set (`getekendeNodes`), zelfde knoop-stijlbron (`_nodeData`/`_vormVoorType`)
  en zelfde klik-gedrag als de andere weergaven; de ADR-040-render-eigenaar (één opbouw →
  één layout → fit via de `stop`-callback) geldt óók hier — mét de verplichte **meet-stap
  vóór de eerste frame** (zie LI036-patronen hieronder).
- Baan-indeling via `_laneVan` + `LANE_DEF`/`DEFAULT_LANE_VOLGORDE` (Processen bovenaan →
  Rollen & beheer → Gebruikers → Componenten → Infrastructuur → Contracten → Overig);
  baan-koppen zijn versleepbaar (volgorde in sessionStorage), "Verberg lege banen"-toggle.

## LI020-patronen (Landschapskaart — adaptief, highlight, geschiedenis, vorm, scope)

- **Eén adaptieve weergave, één graph-pipeline.** De modus volgt de actieve set (leeg →
  geheel, 1 → ego, ≥2 → Impact-verkenner); ego/geheel/impact gebruiken dezelfde Cytoscape-
  pipeline (`zichtbareNodes → _elementen → _layout`). Geen tweede graph-mechanisme, geen
  view-tabs.
- **Selectie-highlight via runtime cytoscape-klassen, nooit via relayout.** Enkelklik =
  inspecteren (detail + alléén de incidente lijnen in `SELECTIE_RAND`-oranje via
  `hl-node`/`hl-edge`); dubbelklik = dieper (impact-drill / ego-hercentreren). Lijnen
  standaard neutraal; oranje = "verbindingen van dít component" (één gedeelde kleurbron).
- **Toestand-geschiedenis (terug/vooruit) = browser-model, maar herstel mag NOOIT een
  geforceerde geanimeerde relayout triggeren** (de hang-les). Regels: vergelijk inhoud
  vóór reassignment (Set/array-gelijkheid) zodat een gelijk-blijvende toestand nul
  (re)tekeningen geeft; `animate:false` tijdens herstel; centreer via het bestaande
  layout-stop-pad (`_naLayout`), géén losse extra `fit`; begrens de history (~50) en
  ont-reactiveer (`shallowRef` + bevroren snapshots); scherm álle afgeleide watchers
  (incl. de filter-watch) af met de `_herstellen`-guard. Zoom/pan blijven buiten de
  geschiedenis; een scope-/filter-/selectie-wijziging is wél een toestand.
- **Vorm-per-type via één gedeelde knoop-stijlbron.** Vorm = wat het is; kleur toont de
  **actieve kaart-lezing** (default: status) — **niet absoluut status** [herzien LI042], want de
  kaart kan de kleur-lezing wisselen (werk/status/domein, zie §Signaal-kanalen · kaart-kleur-lezing).
  `_vormVoorType` (op element_type + partij-aard + infra-laag) voedt `_nodeData.shape`,
  gelezen door alle weergaven (incl. de Lagen-banen) — geen tweede definitie. **Harde
  contrast-eis:** tekstkleur altijd via luminantie (`_txtColor`) op de werkelijke
  vulkleur; introduceer geen nieuwe donkere vullingen; test elke vorm × elke status.
  Type-label voor álle typen als tweede signaal. Native, labelvriendelijke vormen;
  near-dubbele paren krijgen een echt ander silhouet.
- **Context-ringen blijven buiten de impact-keten.** Een relatie die geen migratie-impact
  is (organisatiestructuur "hoort bij", samenstelling als context) krijgt een eigen ring,
  **standaard uit**, en stond NIET in `IMPACT_RINGEN` (afgeschaft met de Impact-verkenner
  — bestaat niet meer in de code [LI035]). Organisatiestructuur opgebouwd
  vanaf rol-vervullende personen omhoog (geen lege takken); afdeling-NULL → directe
  persoon→organisatie-edge.
- **Scope-balk (organisatie) = scope-keuze, niet zomaar een filter.** De balk bepaalt
  wélke application-componenten in beeld komen (bezit = `eigenaar_organisatie_id` ∈
  selectie; gebruik = `gebruikt_door_organisaties` overlapt); niets aangevinkt → alles
  (nooit leeg). Gewone filters/ringen werken daarbinnen door. Registratiegaten (component
  zonder eigenaar; gebruik via organisatieloze groep) eerlijk tonen, niet wegpoetsen.
- **Uitklapbare legenda** (canvas-overlay): standaard ingeklapt, een "Vorm = type"-sectie +
  een **"Kleur ="-sectie die de ACTIEVE lezing toont** (werk/status/domein), voorkeur in
  sessionStorage (try/catch). Glyphs zijn CSS-benaderingen van de Cytoscape-vormen —
  herkenbaar volstaat.
- **Legenda beweegt mee met het kanaal (P3, LI042).** Verandert een switch/voorkeur de
  betekenis van een kaart-kanaal, dan toont de legenda wat de kleuren in de *actieve lezing*
  betekenen — **kleur zónder meebewegende legenda-uitleg is het anti-patroon.** Bekend gat: het
  `kleurOpDomein`-gat (de rand wisselt naar domein terwijl de legenda "Kleur = status" blijft
  zeggen). De legenda is een KIJK-uitleg, geen invoerregel (likara-ux §Voorkeur = KIJKFILTER).

## Kaart-vertrekpunt = zoeken, niet "alles tonen" (LI021, schaalarchitectuur)

- **De kaart laadt NOOIT de volledige graaf bij schaal.** Bij 300+ componenten is "het hele
  model" onbruikbaar. De kaart laadt **set + 1-hop** via de set-scoped backend (POST
  `/landschapskaart/subgraaf` `{component_ids, diepte}`; zie likara-backend).
- **Accumulerende sub-graaf-cache.** `nodes`/`edges` zijn niet meer de volledige graaf maar de
  **unie van geladen sub-grafen** binnen de sessie. Ego/impact/drill = **incrementeel bijladen**
  (klik → buren van die node ophalen → mergen). De terug/vooruit-geschiedenis werkt **zonder
  her-fetch** want de cache is een superset van bezochte sets. "Begin opnieuw" = set leegmaken →
  terug naar de lege zoek-staat én **cache weggooien** (vers zoeken).
- **Vertrekpunt = zoeken.** De kaart opent **leeg** (zoekveld + opgeslagen views); de gebruiker
  bouwt een set op via het server-side component-zoekendpoint (`/componenten`, gepagineerd:
  naam/type/laag/hosting/eigenaar-organisatie/leverancier). De **selectie bevat altijd
  componenten** (component-ids); organisatie/leverancier zijn **filtercriteria** die de set
  inperken, geen set-leden.
- **"Zoek-erop-dan-toon-het" (algemeen principe).** Zoek je op een dimensie met een
  corresponderende ring/knoop (leverancier, eigenaar-organisatie), dan verschijnt dat ding ook
  als **context-knoop**; zoek je er niet op, dan alleen via de bewuste ring-vink. **Handmatige
  ring-vink wint altijd**: auto-zichtbaarheid verdwijnt bij een leeg zoekcriterium, een handmatig
  aangezette ring blijft staan.
- **Eigenaar-edge "is eigendom van"** is context, destijds **niet** in `IMPACT_RINGEN`
  (die constante is met de Impact-verkenner afgeschaft en bestaat niet meer in de code
  [LI035]). Dit vervangt het oude "scopebalk-tekent-organisaties"-spoor.
- **NB — de oude "val terug op alles"-defaults schalen niet** en worden in fase B/C omgedraaid:
  scopebalk "niets-aan → alles" en startscherm "geen-views → hele model" gaan naar **leeg openen**
  (de gebruiker kiest). Laat dit niet per ongeluk terugkeren.

## LI022 — set-gestuurd kaart-laadpad (Fase B slice 0+1, niet-onderhandelbaar)

- **De Landschapskaart opent LEEG** (beginscherm) en bouwt **set-gestuurd** op: niet-lege set =
  `POST /landschapskaart/subgraaf` (`api.landschapskaart.subgraaf([...set], diepte)` → set + 1-hop).
  **Bij elke set-mutatie de HELE set opnieuw ophalen** (idempotent; geen incrementele merge — eenvoud >
  micro-optimalisatie). Eén centrale herfetch-watch op `(set, heleLandschap)`; een `_mountKlaar`-guard
  voorkomt een dubbele fetch tijdens de mount.
- **`modus` 0 is niet meer 'geheel'.** Lege set + geen hele-landschap = `'leeg'` (beginscherm).
- **"Toon het hele landschap" is een BEWUSTE, aparte actie** (geen default van een lege set): een
  `heleLandschap`-vlag **los van de set-grootte** leegt de set en laadt de volledige graaf
  (`haalGrafdata`). Een set opbouwen (`toggleSet`/`openView`) zet de vlag weer uit.
- **Voortgangsteller "X van N"** bij het laden van het hele landschap: tel op **verwerkte data in
  chunks** (`cy.add` is één synchrone call zonder native batches) — een echt meebewegend getal naar een
  **bekend totaal**, géén tijd-gedreven spinner.
- **"Begin opnieuw" = de enige harde reset** → set leeg + hele-landschap-vlag uit → de herfetch-watch
  leegt de graaf → terug naar het lege beginscherm.
- Een **entry-point** (hele landschap / begin opnieuw) is een **verse history-wortel**: her-zaai de
  toestand-historie ná de laad (via `nextTick`), zodat de scope-default geen losse "terug"-stap wordt.
- **Strategie A voor de tests** bij deze omslag: zie likara-tests (mountView-helper laadt het hele
  landschap; één setter voedt full-load én subgraaf-mock; nieuwe bedrading-tests apart).

## LI023 — Landschapskaart Fase B patronen

### beginschermOpen-vlag (expliciete sluit-actie — aangescherpt LI046)
De zichtbaarheid van KaartBeginscherm is NIET **reactief** gekoppeld aan de set-grootte
(nooit `v-if="actieveSet.size === 0"` — spooksluitingen). Een aparte
`beginschermOpen = ref(true)` bepaalt de zichtbaarheid. Bij **binnenkomst** geldt één
eenmalige gedeelde regel ná de beslisboom: `beginschermOpen = actieveSet.size === 0` —
gevulde kaart (handoff/deep-link/herstelde lk-state/toekomstige tak) → beginscherm dicht;
**terugkeren/herladen mét bewaard werk ís de expliciete actie** (LI046). Per-tak-vlaggen
bestaan niet meer; een nieuwe tak vult alleen de set en erft de regel. Sluiten tijdens de
sessie = expliciete gebruikersactie ("Toon N componenten"-knop, view openen, hele landschap);
heropenen = wisSet() + elke harde reset.

### Actiebalk bovenaan beginscherm
De primaire actieknop staat als vaste actiebalk BOVENAAN het beginscherm (niet
sticky-bottom). Structuur:
- Root: `flex flex-col` (geen overflow op root)
- Actiebalk: `shrink-0 border-b` (v-if="setGrootte > 0", niet disabled)
- Scrollbare content: `flex-1 overflow-y-auto`
Redenering: gebruiker heeft ogen bovenin na aanvinken → actie zit waar gebruiker kijkt.

### z-index management Landschapskaart
Canvas-kolom is een relative stacking-context:
- Cytoscape-canvas #cy: `z-[1]`
- Knoppen (history/legenda/fullscreen): `z-10`
- KaartBeginscherm overlay: `z-20` (opaak, ontvangt pointer-events)
- Modal-dialogen: `z-50` / `z-[60]`
KaartBeginscherm heeft `absolute inset-0 z-20` — altijd boven canvas en knoppen.

### componentBuren() — via grafEdges, NIET cy.neighborhood
Cytoscape node-data draagt ALLEEN visuele velden (label, bg, border, shape).
element_type/naam/laag zijn NIET beschikbaar via `cy.getElementById(id).data()`.
Buren ophalen = via de reactieve `grafEdges` + `nodePerId` computed properties.
Voorbeeld:
```javascript
function componentBuren(id) {
  return grafEdges.value
    .filter(e => e.bron === id || e.doel === id)
    .map(e => e.bron === id ? nodePerId.value[e.doel] : nodePerId.value[e.bron])
    .filter(n => n && _isApp(n))
}
```
Dit is testbaar zonder cy-mock te wijzigen (Strategie A).

### Generieke re-layout watcher
De re-layout watcher keyt op getekendeNodes-ID-compositie (NIET op zichtbareNodes):
```javascript
watch(
  () => getekendeNodes.value.map(n => n.id).join('|'),
  _debounce(() => { if (_mountKlaar && cy) tekenGraaf() }, 250)
)
```
- getekendeNodes vangt ook focusOpSet-wijzigingen (die zichtbareNodes niet raken)
- Debounce coalesceert snelle wijzigingen
- History-uitzondering: tijdens terug/vooruit (_herstellen) direct uitvoeren (niet debounced)
- Initiële layout blijft de directe tekenGraaf() in onMounted/herlaadGraaf

### Scope-filter in subgraaf-modus
In subgraaf-modus (actieveSet.size > 0) filtert scope ANDERS dan in hele-landschap-modus:
- Set-leden: altijd zichtbaar (nooit weggefilterd)
- Geen scope geselecteerd: alles zichtbaar
- Org-nodes: alleen zichtbaar als scopeOrgs.has(n.id)
- Gebruikersgroep-nodes: zichtbaar als scopeOrgs.has(n.organisatie_id); org-loos → altijd
- Contract/infra/persoon/externe partij: altijd zichtbaar
- Application-componenten: NOOIT weggefilterd in subgraaf-modus (de set IS de scope)
"Biedt aan/Gebruikt"-toggle: v-if="actieveSet.size === 0" (alleen hele-landschap)

## V028-patronen (ADR-028 componentclassificatie — rol + BIV, geverifieerd)

- **Rol/BIV in het componentformulier**: rol = native `<select>` (4 opties, catalogus-gedreven —
  OP-24-drempel geldt, géén ZoekSelect nu; default voorgeselecteerd op `interne_applicatie`). BIV =
  gegroepeerd `<fieldset>` met drie native `<select>`s (Beschikbaarheid/Integriteit/Vertrouwelijkheid),
  elk met eerste optie **"— Niet geclassificeerd —"** (leeg → payload `null`). Opties + niveaus komen
  additief uit `GET /componenten/opties` (`componentrol_opties`, `biv_niveaus` — ordinaal).
  Code-gebaseerde 422 (`ONGELDIGE_ROL`/`ONGELDIGE_BIV`) mapt op het juiste veld.
- **Detail**: rol + BIV in het `<dl>`; leeg BIV-aspect toont expliciet **"Niet geclassificeerd"**
  (geen leeg vakje).
- **Twee catalogus-beheerschermen** (`RolConfigBeheer`/`BivConfigBeheer`, platform-shell): gespiegeld
  op `ComponentConfigBeheer`. Rol: `interne_applicatie` beschermd (Systeem-Tag i.p.v. deactiveer-knop;
  422 `SYSTEEM_SLEUTEL_BESCHERMD` afvangen). BIV: `volgorde` zichtbaar/beheerbaar (ordinaal — nieuw
  niveau als "Zeer hoog" krijgt zijn plek via `volgorde`). Named routes in **beide** relevante routers
  registreren (mount-gotcha).
- **Componentlijst server-side filter**: rol (multi → herhaalde `componentrol`-param) + BIV per aspect
  (`biv_*_min`, drempel op de ordinale `volgorde`). **API-client-filterconventie blijft
  niet-onderhandelbaar**: elke param zowel in de `lijst`-aanroep als in de `_filterQuery`-allowlist
  (snake_case, exact = backend); een typo (bv. `biv_vertrouwelijkheid` zonder `_min`) faalt LUID.
- **Landschapskaart-filter**: rol/BIV met de **filter-exemptie-regel** — rol/BIV gelden uitsluitend
  voor nodes mét `componentrol`; context-nodes altijd exempt. Rand + legenda voor `externe_dataprovider`
  (géén nieuwe vulkleur). BIV-drempel client-side op de ordinale positie uit `biv_niveaus`.
- **SignaleringBadge**: optionele `signalen`-prop (sleutels) → sprekende tooltip via de gedeelde
  `SIGNAAL_LABEL`-map (labels.js); zonder `signalen` valt hij terug op de generieke telling.

## Centrale verlopen-sessie-vangrail + zoekveld-fout-staat (LI032, niet-onderhandelbaar)

- **Eén aanhaakpunt: het bewezen-gefaalde-refresh-punt in `api.js`.** `request()` doet bij een 401
  eerst de single-flight `refreshSessie()` (raw fetch → geen lus) + één retry (`_isRetry`-guard). Pas
  als dat bewezen faalt, wordt de 401 doorgezet (`throw`, `.status===401`). **Uitsluitend dáár** roept
  `api.js` de centrale vangrail (`_meldSessieVerlopen`) aan — dus nóóit terwijl een sessie nog te redden
  is. Single-flight (`_sessieVerloopBezig`) → één redirect bij een storm; een geslaagde 2xx reset de vlag.
- **Framework-loze bedrading (verplicht).** `api.js` importeert géén router/store (offline testbaar).
  De app registreert bij init één handler via `registreerSessieVerlopenHandler(fn)`; de handler-fabriek
  `sessieVerlopenHandler(router, auth)` (`src/sessieVangrail.js`) wist de sessie + `router.push` naar
  `login?sessie_verlopen=1&next=<huidig fullPath>` (geen `next` op de wortel; niet op publieke routes).
- **Sessiecheck symmetrisch met data-fetches.** `store/auth.js fetchSession` probeert bij een 401 op
  `/auth/me` **eerst** `refreshSessie()` vóór ze de sessie opgeeft — zodat navigatie een nog-te-redden
  sessie (access verlopen, refresh geldig) niet afbreekt. `routeBeslissing` blijft puur/testbaar.
- **Geen rauwe foutcode in beeld — overal.** `ZoekSelect.zoek()`-catch: op 401 leeg (vangrail redirect),
  overige fouten → generieke "Zoeken mislukt." (**nooit** `e.message`). Load-catches (`fout.value = …`):
  op 401 `null` (geen banner). `_toastFout`/inline toasts: **vroege terugkeer op 401**. De bestaande
  403/404/409/422-mappings (waar `e.message` de nette backend-`bericht` is) blijven ongemoeid — alleen de
  401-tak werd afgevangen. Borging: `api.test.js` (handler één keer / niet bij succes), `sessieVangrail.test.js`
  (redirect + next), `authSession.test.js` (refresh-vóór-opgeven), `ZoekSelect`/`PartijLijst` (geen rauwe code).
- **Backend-zoek-conventie:** elk lijst-endpoint met `zoek` doet `Naam.ilike(f"%{_escape_like(zoek)}%",
  escape=…)` (partieel, case-insensitief, ge-escapet). Observatie: `_escape_like` is per service
  gedupliceerd (6×, identiek) — cosmetisch consolideerbaar tot één helper, geen gedragsfout.

## Ter-plekke-aanmaken bij keuzevelden (LI032, gedeelde bouwstenen)

- **`#leeg`-override op `ZoekSelect` = de dwingende plek** voor search-first aanmaken. Twee gedeelde
  bouwstenen: **`ContactpersoonSelect.vue`** (persoon van deze partij) en **`AfdelingSelect.vue`**
  (organisatie_eenheid van deze partij). Een nieuw afdelingsveld gebruikt `AfdelingSelect` (props
  `partijId`, `modelValue`, `initieelWeergave`, `magAanmaken`, `orgNaam`, `genest`, `disabled`,
  `testid`) en erft het gedrag gratis — **geen** losse her-implementatie per veld. **Vier gebruikers**
  van `AfdelingSelect`: `PartijFormulier`, `ContactpersoonSelect`, `GebruikersbeheerView` (aanmaak- én
  beheer-paneel) en `GebruikersgroepSectie`. Er bestaat **geen** tweede afdeling-inline-aanmaak-
  implementatie; een nieuw afdelingsveld hangt aan deze bouwsteen.
- **Aanmaken via een bestaand endpoint, geen schemawerk.** Afdeling: `api.partijen.maak({aard:
  'organisatie_eenheid', naam:<zoekterm>, organisatie_id:<deze partij>})`. Persoon: idem met
  `aard:'persoon'`. Na aanmaak: `naAanmaakNaam` + remount-`:key` + `emit('update:modelValue', id)` →
  de nieuwe waarde staat meteen geselecteerd + gelabeld (spiegel van het `initieel-weergave`-patroon).
- **Picker-scope spiegelt de backend-regel** (`aard` + `organisatie_id` = deze partij) — nooit een optie
  die bij opslaan 422 geeft. Soepel zoeken (ilike) vindt bestaande vóór iemand dubbel aanmaakt.
- **Visueel — getinte, omrande aanmaak-zijstap.** Blok-klassen met bestaande tokens: niveau 1 =
  `bg-[var(--lk-color-primary-50)]` + `border-[var(--lk-color-primary-100)]`; **genest** (niveau 2) =
  `bg-[var(--lk-color-primary-100)]` (`genest`-prop op `AfdelingSelect`). Begin/eind = "Aanmaken en
  kiezen / Annuleren". **Max twee niveaus** — feitelijk geborgd doordat een afdeling **naam-only** is
  (bladniveau, geen entiteit-keuzeveld → geen laag 3). Tailwind genereert deze arbitrary-utilities uit
  `modules/` mits de `@source`-glob staat (die staat er); geverifieerd in de dist-CSS.
- **Rechten:** aanmaken alleen tonen aan wie personen/afdelingen mag aanmaken (`hasRole('medewerker',
  'beheerder')`); de backend handhaaft. Borging: `AfdelingSelect.test.js` (search-first, endpoint-args,
  soepel-zoeken-vóór-dubbel, voorvulling, genest-tint + geen laag 3) + nesting-test in
  `ContactpersoonSelect.test.js` (blok-in-blok, twee niveaus).
- **Niet elk keuzeveld hoort dit te krijgen** — zie de UX-norm (open-ended vs. formele opvoer).
  `GebruikersbeheerView` heeft inmiddels een **organisatie-picker (intern-only)** die de afdeling
  scoopt (aanmaak én beheer); de afdeling-picker is daar dus **wél** gescoped + ter-plekke-aanmaakbaar
  (het eerdere "ongescoped"-gat is gedicht — zie de organisatie→afdeling-keuzeopzet in likara-ux).

## LI034 — kaart-state: reload behoudt werk + samenloop met de standaardkijk (ADR-041)

Meerdere onthoud-mechanismen op de kaart, met een **vaste precedentie: in-sessie `lk-state` > persoonlijke
standaardkijk > kale default.** Vindplaats: `LandschapskaartView.vue`.
- **`lk-state` (sessionStorage)** = in-sessie werk over navigatie/reload heen. Kritieke les:
  `onBeforeRouteLeave` vuurt **niet** bij F5 → persisteer óók op **`beforeunload` → `_bewaarKaartState`**
  (listener opgeruimd in `onBeforeUnmount`, geen lek). `wisSet` ("Begin opnieuw") **wist `lk-state`** →
  F5 hierna landt op het beginscherm i.p.v. een stale set. Zónder deze twee herstelt F5 de laatste
  route-leave-snapshot (bug: 1 gekozen component → 8 na F5).
- **Standaardkijk** (voorkeur-sleutel `kaart_kijkfilter`, hergebruikt de voorkeur-laag): opgeslagen bij
  **verse start** (mount, alleen als `_herstelKaartState` niets herstelde) en bij **"Begin opnieuw"** (na
  het wissen van `lk-state`). `_herstelKaartState` geeft daarom `true/false` terug (in-sessie hersteld?).
- **Standaardkijk = de KIJK-variabelen** (`ringAan`/filters/`diepte`/`kleurOpDomein`/`groepeerPerOrg`/
  lane-opts), **NOOIT de momentkeuze** (`actieveSet`/`egoStartId`/`weergave`/`zoekterm`/`focusOpSet`/
  `scopeOrgs`). Zie de vaste-bril-vs-momentkeuze-regel in likara-ux.

## LI034 — de landschapskaart is bewust applicatie-centrisch

Leg vast **dát** dit een bewuste ontwerpkeuze is (niet een bug), zodat een volgende sessie het niet per
ongeluk "fixt". Waar het zit (`LandschapskaartView.vue`):
- `appNodes = nodes.filter(_isApp || _isOrg)` → **alleen applicaties + organisaties zijn zoekbaar/
  selecteerbaar**; partijen/contracten/infra verschijnen als ring-nodes. `componentBuren` filtert `_isApp`;
  de set-/buren-acties behandelen niet-app-nodes als **context**; diepte-2-ego breidt alleen via strikte
  `isApplicatie` uit. NB: `_isApp`'s 2e tak (`element_type==='component'`) is **dood** voor backend-nodes
  (`element_type` = het componenttype, nooit letterlijk `'component'`) → `_isApp ≡ isApplicatie` in de
  praktijk.
- **De kaart component-breed maken** (elk componenttype zoekbaar/als buur) = **een eigen ADR-spoor**, geen
  kleine fix.
- **Afgeronde consistentie-fixes** (geen open bug meer): (a) doorklik gelijkgetrokken — één predicaat
  `_heeftComponentDetail(n) = element_type==='applicatie' || laag==='application'`, gebruikt door zowel de
  popup (`_detailLink`) als het zijpaneel; (b) een relatie-loos **set-lid** wordt op Overzicht toch
  getekend (`getekendeNodes`, `setLid`-term) met een rustige "geen relaties in beeld"-cue.

## LI035-patronen (ADR-042 slice 4/5 + sessie-fixes, geverifieerd)

- **Lijststaat-patroon (VERPLICHT voor elk lijstscherm met filter/zoek/sortering)** —
  `useLijstStaat(sleutel, refs, {valideer})` (`src/composables/useLijstStaat.js`):
  sessionStorage-momentstaat per scherm-sleutel, bewaard op route-leave ÉN beforeunload,
  gevalideerd hersteld bij mount; precedentie **deep-link-query > bewaarde staat >
  defaults** (bij een doorklik-query `herstel()` overslaan); cursor/paginering en data
  NOOIT mee (verse fetch, ADR-017). In gebruik op partij-/component-/contract-/proces-
  lijst, BlokkadeOverzicht en de rollup-uitklapstand — nieuwe lijstschermen haken aan.
- **Regel-acties-patroon** — elke registratie-/relatieregel krijgt **Bewerken** (dialoog
  op de kenmerk-velden; de identiteit/ankers zichtbaar maar read-only) en **Verwijderen**
  (áltijd via de gedeelde `src/components/BevestigVerwijderDialog.vue`, met de regel
  leesbaar in de vraag; testids `${testid}-dialog/-omschrijving/-annuleer/-bevestig`).
  Geen losse ×-kruisjes. Voorbeelden: ProcesComponentenSectie, ComponentProcessenSectie,
  ContractSectie-banddekking. (Backend-kant: PATCH-kenmerk-recept in likara-backend.)
- **MeldingBanner** (`src/components/MeldingBanner.vue`) — dé conflict-/weigering-vorm in
  secties en dialogen: `soort` warn=weigering (role=status), danger=fout (role=alert),
  info; altijd kleur+icoon+tekst (nooit alléén kleur); positie **bóven** de invoervelden;
  scrollIntoView-vangnet bij mount; de melding verdwijnt bij invoerwijziging (hij hoort
  bij de geweigerde poging). Geen stille grijze meldingen.
- **Succes-toast-standaard** — elke geslaagde actie met expliciete opslaan-intentie
  (dialog-/formulier-/toevoegregel-submit, bevestigde verwijdering) roept
  `toastSucces(toast, '<werkwoord>')` aan (`src/meldingen.js`: severity success, life
  3000), ná de geslaagde call, vóór sluiten/herladen. Enige uitzondering: de CD004-
  scoringslijst (zie de scope-correctie hierboven). Test-patroon: mock `@/meldingen` en
  assert de aanroep.
- **Dialog-primitive-regels** (`src/presets/Dialog.js` + `.lk-scroll-schaduw` in
  `assets/main.css`) — de dialoog past binnen de viewport (`mt-[10vh]`+`max-h-[80vh]`);
  het preset-content is hét scroll-gebied (`overflow-y-auto` + **`min-h-0`**-krimpgarantie
  + eigen padding zodat veldranden/focus-ringen niet clippen) en draagt de tweezijdige
  toestandsafhankelijke scroll-schaduw (puur CSS, `background-attachment: local`, getint
  op `--lk-color-primary`); vaste knoppenbalken horen in het **#footer-slot** (submit via
  het `form`-attribuut). Views bouwen NOOIT een eigen scroll-wrapper (die clipte de
  omlijning en liet de voetbalk mee-scrollen). Het preset capt élke dialog op `max-w-lg`
  — brede dialogen overschrijven per instantie met `!w-…`/`!max-w-…` (!important wint).
  Borging: `tests/dialogPreset.test.js`.
- **Overlay-formulier-patroon** (ComponentFormulier) — aanmaken/bewerken identiek in één
  Dialog-overlay (twee kolommen, stapelt smal); annuleren met wijzigingen vraagt
  bevestiging (dirty-snapshot); verzamel-subregels bij aanmaken worden ná de entiteit in
  één keer opgeslagen, met een retry-pad dat de entiteit NIET dubbelt (`aangemaaktId`);
  oude aanmaak-/bewerk-routes blijven werken als redirect met query (`?nieuw=1`/
  `?bewerk=1`) naar de overlay. Overlays lazy mounten (`v-if` op de open-vlag — anders
  toast-provider-fouten in tests).
- **CSS-token-borging** — `scripts/check-css-build.mjs` (laag C) checkt naast de kritische
  klassen ook élke **fallback-loze** `var(--lk-…)`-verwijzing in de dist-CSS tegen de
  definities in base.css/main.css (een onbestaand token = dode declaratie = "class staat
  erop maar doet niets"). Lessen: class-naam-asserts in vitest bewijzen GÉÉN rendering
  (borg op dist-CSS); comment-teksten in gescande bestanden zijn Tailwind-candidates
  (noem nooit een aaneengesloten class-literal die je juist wil detecteren).

## LI036-patronen (Lagen-weergave, rolbanen, kaart-interactie — geverifieerd)

- **Meet-stap vóór de eerste frame bij een preset-layout (kritiek).** Nodes met
  `width/height:'label'` hebben pas een maat ná een meting; grid/concentric meten zelf
  (concentric.mjs:76/:81 `nodes.updateStyle()` + `layoutDimensions`), de **preset**-layout
  meet níéts → de eerste frame heeft geen edge-endpointgeometrie en tekent GÉÉN lijnen
  (elke latere klik/style-invalidatie herstelt het — vandaar "werkt na een klik").
  Fix: in de preset-tak vóór het plaatsen `cy.nodes().updateStyle()` + per node
  `layoutDimensions({ nodeDimensionsIncludeLabels: true })` — een synchrone stateberekening
  binnen de ene render-eigenaar, géén setTimeout-nudge (LI019 maskeerde dit met de
  100ms-fit die ADR-040 terecht verving door de stop-callback).
- **Instance-projectie (Lagen-only) — één logische node, meerdere visuele plekken.**
  `instanceProjectie` (naar het gg-aggregatie-precedent) zit tussen de logische laag
  (`getekendeNodes`/`zichtbareEdges`) en de teken-/banenlaag (`_elementen`/`laneLayout`):
  een partij krijgt per rolbaan een instance (`id = <logischId>@<baan>` + `logischId`;
  één pet houdt de logische id), rol-edges remappen naar de instance van hun eigen ring
  (edge-data draagt `bronLog`/`doelLog` voor de resolutie). Interactie matcht op
  **`logischId`**: tap-grens resolvet instance→logisch, highlight/dim (`_pasSelectieHighlight`/
  `_pasDim`) laten álle instances samen oplichten, één detailkaart. Buiten Lagen geeft de
  projectie 1-op-1 door (geen duplicaten op Overzicht/Praatplaat). Instances delen de éne
  stijlbron (`_nodeData`) — identiek uiterlijk per constructie.
- **Rol-tag-accent = eigen laag, gedeelde dim-staat.** De rol-tag (kleur + kort woord:
  gebruikt/levert/beheert/eigenaar) is een HTML-pill-overlay ónder de instance — een
  APARTE laag naast vorm(=type/aard), vulling(=lifecycle) en rand(=selectie/blokkade — op de
  kaart draagt de rand tevens de kaart-kleur-lezing werk/domein, §Signaal-kanalen · kaart-kleur-lezing);
  één kleurbron (`ROL_TAG`) voor node-tag én popup. De tag **deelt de dim-staat van zijn
  knoop**: `updateRolTags` leest `hasClass('lk-dim')` van het cy-element (de ene dim-
  eigenaar `_pasDim` eindigt met de tag-sync; `DIM_NODE_OPACITY` is de ene opacity-bron
  voor knoop én tag). Overlay synct op pan/zoom/layout-stop, `pointer-events-none`.
- **Maatwissel = resize()+fit, nooit re-layout** (verfijning van het ResizeObserver-
  patroon). Vergroten/verkleinen/fullscreen wijzigt alleen de container; het ene pad
  `_pasCanvasMaat` (de observer-callback) doet `cy.resize()` + de `_naLayout`-fit op de
  BESTAANDE posities — geen `_layout()`-herberekening (knopen verspringen niet), geen
  viewport-behoud-vlag of `setTimeout`-nudge (die zijn met LI036 verwijderd). De fit vuurt
  zoom/pan-events → de HTML-overlays (banden + rol-tags) hersyncen vanzelf.
- **Proces-knoop**: `element_type='proces'` → afgeronde rechthoek + **verloop-pijl-marker**
  (SVG-data-URI als node-achtergrond via een `CY_STYLE`-selector — hoort bij de vorm-
  definitie, dimt/schaalt mee), eigen proceslaan + ring 'processen' (default aan, óók in
  `RING_PRAATPLAAT_KERN`), tagloos, popup met "Vervuld door"-sectie (herkomst inklapbaar
  per component, native `<details>`) en de vervul-toggle (zie likara-ux).

## LI037-patronen (procesboom gedeeld, tree-view, cytoscape-kleur)

- **Eén gedeelde boom-opbouw voor kaart én lijst** —
  `modules/bwb_ontvlechting/frontend/procesBoom.js`: `procesBoomStructuur(ids, hierEdges,
  naamVan)` → `{wortels, ouderVan, kinderenVan}` (deterministische naam→id-sortering,
  cyclus-/dubbele-ouder-guard); `procesBoomLayout` is erop gerefactord. De kaart bouwt er
  zijn cytoscape-posities op, het Processen-lijstscherm zijn DOM-tree. **Nooit een derde
  boom-opbouw** — bij ontdekking van een tweede variant: convergeren naar deze module.
  Alleen de rendering is schermspecifiek: cytoscape-preset (kaart) vs. DOM-overlay-
  connectoren (lijst: laatste kind = └, anders ├; guides beslaan de volle rijhoogte;
  wortels dragen geen connector-kolom — de wortel-lus zaait een lege lijnen-prefix).
- **Cytoscape-kleur zonder CSS-var-resolutie.** Cytoscape resolvet geen CSS-custom-properties
  (`var(--…)` = invalide-color-warning) → waar een cy-stijl een UI-kleur moet spiegelen is een
  concrete waarde nodig. **Waar die kleur uit één gedeelde bron moet komen (LI043): resolve het
  `--lk-`-token op tekenmoment** (`getComputedStyle`, bv. `standKaartKleur(stand)` → `standCodering`)
  i.p.v. een tweede hex te kopiëren — dan blijft de bron enkelvoudig en is **token-drift onmogelijk**
  (er is géén dark-mode; elk token heeft één vaste waarde, dus de geresolvede waarde is stabiel). Een
  losse hex mét token-commentaar (bv. `#64748b` = `--lk-color-text-muted`) blijft acceptabel waar géén
  gedeelde bron speelt. Vermijd een losse hex waar het via node-data/klassen kan (`_nodeData`-stijlbron).

## LI038-patronen (useSleepbaar, ZoekSelect-filter-slot, proces-only diagram)

- **`useSleepbaar` — de ENIGE overlay-sleep-bron (geconvergeerd LI038).** Het sleep-*recept*
  stond al in likara-ux; de *bouwsteen* ontbrak. Nu: `frontend/src/composables/useSleepbaar.js`
  is de enige bron. `pos {x:null,y:null}` (null = CSS-standaardplek), positie-init uit
  `getBoundingClientRect()` bij de eerste drag (nooit `?? 0` — anders springt de overlay weg),
  knoppen/links/inputs zijn **geen greep**, mousemove/mouseup op `document` met opruiming bij
  unmount, `reset()`. **Kaart-legenda en kaart-klik-popup draaien er nu ook op** (de twee
  inline-kopieën zijn vervangen; exposed namen via destructuring-aliassen behouden). **Elke
  nieuwe overlay haakt hieraan aan — nooit een nieuwe inline kopie.** **Reset-semantiek:**
  reset bij een verse context (nieuwe keuze / `wisSet()` / popup sluiten); een
  **inspectie-reeks** (achtereenvolgens knopen aanklikken) behoudt bewust de gesleepte plek.
- **ZoekSelect — de faalmodus achter picker-regel 4 (LI038).** De regel (§ZoekSelect-patronen
  regel 4) bestond; dit is **waaróm hij stukging**, zodat hij niet terugkomt: de volledige
  startlijst opende alleen op **`@focus`**. Direct ná een keuze **behoudt de input focus** (de
  optie-klik gebruikt `mousedown.prevent`) → een nieuwe klik vuurt **geen** focus-event → de
  lijst opent niet en typen **plakt aan de voorgevulde naam** = filter-slot. **Fix in de
  bouwsteen:** `@click` opent de volle startlijst **óók bij bestaande focus** (met guard: een
  klik terwijl de lijst al open is — cursor verplaatsen tijdens typen — reset niets), plus een
  **×-wis-gebaar** ("Wis en zoek opnieuw": veld leeg, `update:modelValue(null)`, volledige
  lijst open, focus vastgehouden met `mousedown.prevent`). Het ×-gebaar **erft platform-breed**
  op alle ZoekSelect-consumenten; in formulieren betekent × = keuze leeg (`modelValue null`),
  wat de bestaande verplicht-veld-validatie afvangt.
- **Consument behoudt zijn beeld tot een NIEUWE keuze.** Een view die op **`@keuze`** luistert
  (niet op elke input-mutatie) houdt zijn huidige weergave staan bij focus / typen / wissen —
  het beeld wisselt **pas** bij een écht nieuwe keuze. De gebruiker verliest zijn zicht niet
  halverwege het zoeken. Referentie: `ProcesDiagram` (centrum wijzigt uitsluitend in
  `kiesCentrum`/`zoomInOp`).
- **Proces-only diagram — vindplaatsen (LI038).** `ProcesDiagram.vue` (api-vrij: volledige
  set + gap-cue als props uit ProcesLijst — zie de werkprotocol-kernles), pure afleidingen
  `procesFocusSet` (focus: keten boven / subboom beneden / zusjes opzij) en `procesSubboomSet`
  (inzoom: alleen proces + subboom) in `procesBoom.js`; snapshot+cursor-history op de
  beeld-velden (kaart-patroon); ingang-prop `initieelCentrumId` + emit `centrumGewijzigd`
  (plek behouden over Boom↔Diagram-wissels).

## LI039-patronen (functieboom + inleesflow — gevalideerd fase A, `docs/Validatie-patronen-LI039.md`)

- **Convergentie bij twee waarheden = een TWEEDE EXPORT in dezelfde module (ADR-044).**
  Processen zijn één-ouder, functies meervoud: `procesBoom.js` draagt nu `procesBoomStructuur`
  (:26, ongewijzigd — `ProcesLijst` byte-compatibel) én `meervoudBoomStructuur` (:62, plek-paden
  voor plaatsingen). Nooit een kopie-module; de tweede waarheid woont naast de eerste in
  dezelfde bouwsteen. Reden: een kopie loopt stil uit de pas (LI038-kernles).
- **Tweelaags rij-contract (`.lk-rij-*` in main.css:96-130, gedeeld met het processen-scherm).**
  SCAN-laag (`.lk-rij-kop`: naam + alléén wat afwijkt) boven LEES-laag (`.lk-rij-definitie`:
  de definitie volledig zichtbaar, `line-clamp: 2` op woordgrens met ellipsis — géén tooltip,
  géén uitklap; de volledige tekst leeft op popup/detail). NB: het kappen is op REGELgrens,
  niet zinsgrens (zinsgrens = gewogen opvolgpunt). Reden: de definitie is het product — wie
  moet hoveren om te lezen, leest niet.
- **Vaste actiekolom rechts (`.lk-rij { flex-wrap }` + `.lk-rij-acties { flex:0 0 auto; wrap }`).**
  De actiekolom claimt eigen breedte; knoppen stapelen binnen de kolom — er valt er nooit één
  buiten beeld, óók de rode niet. Bouwsteen: het main.css-rij-contract.
- **`useToonNieuweRij` — "wat je zojuist hebt vastgelegd, zie je altijd" (bouwsteen, 4/5).**
  `useAanstip()` (aanstip + scroll-alleen-als-nodig, mét omgeving via `block:'center'`, zacht;
  `scrolNaarRij` beweegt NIETS als de rij al in beeld is) + `useToonInBoom()` (pad open —
  plek-paden via `padVan` voor meervoud-bomen —, zoekterm wijkt ZICHTBAAR via `wijkMelding`,
  aanstip functie-breed met scroll naar de gevraagde plek). **Consument-grens:** het
  vooraan-invoegen bij gepagineerde secties doet de consument zelf (Datatype-/Gebruikersgroep-/
  KoppelingSectie); de composable levert daar alleen de aanstip. Elke nieuwe lijst haakt aan —
  geen inline kopieën.
- **Signaal-kanalen gescheiden (ProcesDiagram:45-55).** `gapIds` (gestippeld, gedempt) en
  `vervallenIds` (solid warning + ⚠) zijn EIGEN props — nooit twee betekenissen door één
  kanaal; combinatie = gestippeld in warning-kleur. Altijd kleur + icoon + tekst. Reden: beide
  toestanden kunnen tegelijk waar zijn; een gedeeld kanaal kan er maar één vertellen.
- **Kaart-kleur-lezing: één leidende lezing, één render-kanaal (P1, LI042).** De kaart kent drie
  kleur-lezingen; de **ACTIEVE lezing leidt één render-kanaal, de andere kleur-kanalen
  neutraliseren** (neutraal/uit) — nooit twee betekenissen tegelijk op één knoop. Vaste toewijzing:
  **werk → rand-STIJL, status → VULLING, domein → rand-KLEUR.** De **selectie-rand (amber) wint in
  elke lezing** en blijft altijd zichtbaar (selectie is geen lezing maar interactie-staat). Dit is de
  kaart-invulling van de kanaal-scheidingsregel hierboven; de legenda beweegt mee (§Uitklapbare
  legenda). "Welk kanaal bezet ik?" hoort als checkvraag vóór elke vorm-keuze (likara-werkprotocol
  §Adversariële checkvraag · UI-/vorm-toepassing).
- **Lege uitkomst ≠ fout — de aanbodStaat-vorm (BedrijfsfunctieLijst, inleesdialoog).** Eén
  enum-ref (`'laden'|'fout'|'leeg'|'ok'`), op precies één plek per pad gezet; de template
  vertakt er exclusief op. 'Fout' (aanroep faalde → rood) en 'leeg' (aanroep slaagde, niets →
  rustige tekst mét route) kunnen structureel niet samen renderen — de vanochtend-bug (beide
  meldingen tegelijk) is onmogelijk gemaakt, niet alleen verholpen.
  ⚠ **Tekst-regel — geen gedeelde bouwsteen; converge bij het tweede geval (n≥2).** Het
  patroon is per scherm gebouwd; een volgend scherm met lijst + foutpad kan de overlap-bug
  opnieuw maken (OPVOLGPUNT: toestandsbouwsteen).
- **Eén bron voor PRESENTATIE, niet alleen data (LI043).** De KERNLES ("een regel houdt pas als een
  gedeelde bouwsteen hem afdwingt", werkprotocol) geldt net zo hard voor **presentatie**: een
  label/kleur/icoon/legenda-tekst leeft op precies één plek en álle vensters erven ervan — bv.
  `standCodering` (lijst-pill + kaart + legenda) en `VELD_LABELS`/`veldLabel` (het beoordelings-
  veldlabel op 6 plekken). **Een single-source/sentinel-test is verplicht onderdeel**: hij zet de bron
  tijdelijk op een sentinel en bewijst dat elke plek meebeweegt — en **breekt zodra iemand het opnieuw
  hardcodet**. (Zo is het `kleurOpDomein`-gat en het "veldnaam verloopt"-gat structureel dichtgezet.)
- **Boom-diagram links→rechts + haakse lijnen — BESLOTEN, NOG NIET GEBOUWD (vervangt huidige
  gedraging).** De huidige `procesBoomLayout` is top-down en het diagram tekent bij meervoud
  ÁLLE plaatsings-lijnen (ProcesDiagram:112-115). Het besloten ontwerp: links→rechts, haakse
  lijnen, meervoud als VERWIJZING (niet als doorkruisende lijn). Bij bouw vervangt dit de
  huidige weergave — de skill beschrijft tot die tijd bewust niet de code.
- **Knopvormen + rij-acties (LI039):** al vastgelegd in §Knopstandaard hierboven (drievorm +
  `RijActies`-bouwsteen) — daar niets aan toegevoegd; de bestaande formulering is vollediger
  (kent ook `secondary`). ⚠ "Max één primary per scherm" + pijl-op-doorklik blijven
  **tekst-regels zonder bouwsteen** (het preset dwingt vormen af, niet het aantal of het label).


## LI040-patronen — bouwstenen + bron-scan-handhaving (gevalideerd)

- **De actuele gedeelde bouwstenen** (fix in de bouwsteen, niet in de consument — de
  werkprotocol-KERNLES; consumenten bouwen géén eigen variant):
  - **Veld**: `.lk-veld` / `.lk-veld-tekstvlak` + `--lk-veld-h` (main.css:40-77) — één hoogte
    (= knophoogte), één rand/radius/focus-taal; het tekstvlak is de ENIGE uitzondering (hoger,
    zelfde verdere vorm). Élke `<input>/<select>/<textarea>` draagt de klasse.
  - **Identiteit**: `IdentiteitLabel.vue` + `partijIdentiteit`/`gebruikersgroepIdentiteit`
    (labels.js:19-35), 6 consumenten — zie likara-ux voor de weergaveregels.
  - **Resultaatregel**: `src/components/FilterResultaatRegel.vue` — aantal + chips + los wisbaar
    (zie likara-ux); uitrol naar overige lijsten = OPVOLGPUNTEN 0.
  - **Detailkop**: `src/components/DetailKop.vue` — naam (wrapt, nooit afgekapt) + #badges +
    #subtitel + #acties + #destructief (eigen gescheiden zone); 8 detailschermen zijn consument.
- **Een bouwsteen faalt LUID bij een programmeerfout** — nooit een stille lege uitkomst.
  Referentie: `IdentiteitLabel.vue:27-50` — lege naam ⇒ zichtbare ⚠-marker (in élke omgeving) +
  `console.error` die de consúment aanwijst. Een stille lege render is precies de faalmodus die
  de suite niet vangt (zie de niet-geresolvede-component-les in likara-werkprotocol).
- **Handhaving via bron-scan** (`scripts/check-css-build.mjs`): regels die zich lenen voor een
  structurele scan krijgen er een — veld-recept (élk veld op de bouwsteen, geen eigen
  hoogte/padding/rand) en detailkop (elk `*Detail*`-scherm gebruikt `<DetailKop>`; de
  object-acties `label="Bewerken"`/`label="Verwijderen"`/`<ObjectHistoriePaneel` mogen
  uitsluitend binnen dat blok). Eisen aan élke scan: (1) **aantoonbaar bijten** — een zelftest
  met opzettelijk foute voorbeelden draait bij elke run mee; (2) **geen vals-positieven**
  (template-only scannen, comments strippen, quote-bewust multi-line tags lezen) — een scan die
  vals alarm slaat wordt genegeerd en is erger dan geen scan; (3) **geen benoemde uitzondering —
  een uitzondering is een achterdeur (LI047)**. Vraagt een geval om een uitzondering in de scan, dan
  is meestal het GEVAL fout, niet de regel; en wie er één opneemt, verbreedt de volgende. Moet er
  tóch iets buiten vallen, laat het dan **afleiden** i.p.v. opsommen. (LI047: twee tegels in
  `GapDetailView` droegen hun label als `<h2>` en werden door de gedeelde kopstijl even groot als
  hun waarde — niet de scan een uitzondering geven, maar vaststellen dat het geen kóppen waren en er
  een definitiepaar (`dl`/`dt`/`dd`) van maken. Tegenvoorbeeld waar afleiden wél mag:
  `test_schema_aanroepen_scan.py` slaat aanroepen binnen `pytest.raises` over — die geven bewust een
  ongeldig veld door om te bewijzen dát `extra="forbid"` bijt, en dat is een structurele eigenschap,
  geen lijst.)

## LI047 — teller en lijst uit ÉÉN laadpunt (niet alleen één bron)

Een teller in de kop en de lijst in een panel mogen niet elk hun eigen aanroep doen. Twee aanroepen
van dezelfde bron zijn geen tweede *waarheid*, maar wél **twee laadmomenten** — en die kunnen na een
mutatie uiteenlopen: de knop zegt "4" terwijl het tabblad drie regels toont, een leugen die niemand
opmerkt omdat beide getallen op zichzelf kloppen.

**Regel: één laadpunt in het scherm dat beide voedt, doorgegeven als prop.** De kindsectie laadt
niet zelf. Referentie: `ComponentDetail.vue` haalt `api.componentNormen.openPunten()` op en geeft
het als `:data` aan `OpenPuntenSectie`; teller én lijst lezen daarna letterlijk hetzelfde object.
Borging: een test die het getal tegen het **aantal regels** legt (`ComponentDetail.test.js` — "het
getal in het tablabel is exact het aantal regels in Dit moet nog"); die valt om zodra iemand een
tweede laadpunt introduceert. **De regel is vorm-onafhankelijk gebleken:** in LI048 verhuisde de
teller van een kopknop naar het tablabel `Open punten (N)` — zelfde `moetNog`-computed, zelfde
laadpunt, alleen een andere drager. Verhuist een teller, controleer dan dat hij zijn **bron**
meeneemt en er geen tweede aanroep bij ontstaat.

⚠ **Bewijs dat de tekst dit niet dekte:** in LI047 werd snede 1 met een zelfladende sectie gebouwd en
snede 2 met één laadpunt — het verschil stond nergens, terwijl de LI041-norm ("teller en lijst delen
één filterwaarheid") over de *filter* gaat, niet over het *laadmoment*.

## LI046-patronen (één ingang naar een detailscherm — ADR-054, geverifieerd tegen de code)

- **Eén gedeelde detail-ingang, geborgd met een scan.** Élke navigatie naar een detailscherm bouwt
  zijn route via `frontend/src/detailIngang.js` → `detailRoute(objectType, id, aanleiding)`; de
  type→route-map (`ROUTE_PER_TYPE`) leeft op **één** plek (de vier eerdere kopieën —
  kaart `_detailLink`, `ArchitectuurView`, `ArchitectuurLagenView`, `PartijRollenSectie` — zijn
  erin opgegaan). Ook een kale rij-klik loopt door de ingang (zonder aanleiding). Borging:
  `tests/detailIngang.scan.test.js` (patroon `name:\s*['"](component|contract|partij)-detail['"]`,
  recept `tests/api.filter.test.js`) faalt op elk bestand dat er tóch een eigen route-literal op
  nahoudt. **De regel leeft in een scan, niet in tekst** (KERNLES LI038).
- **De aanleiding leeft in de URL — promotie van het bestaande query-mechanisme.**
  `AANLEIDING_SLEUTELS = {tab, cat, markeer, bewerk, veld}` (CD022-query + slice 2's `veld`), dus
  deelbaar/herstelbaar/overleeft F5. Een **onbekende sleutel** is een **luide fout** (`detailRoute`
  throwt, zelfde conventie als `_filterQuery` in `api.js`) — een aanleiding valt niet stil weg.
- **Geen route beloofd waar niets te landen valt.** `detailRoute` geeft `null` voor een type zonder
  detailscherm → de aanroeper toont **geen link** (nooit kaal landen of de dichtstbijzijnde tab
  openen). `bedrijfsfunctie` → `bedrijfsfunctie-lijst` met `?focus=<id>` (geen detailscherm);
  `proces` = MVP-verborgen, geen route. Onbekend **veld-anker** = luide fout (`VELD_ANKERS`).
- **Veld-anker landt gemarkeerd, niet in bewerk-modus (slice 2, optie B).** `?veld=<anker>` markeert
  het veld op het Overzicht (accent-achtergrond via `veldKlas`) en zet de **Bewerken-knop ernaast**
  (`data-testid="veld-bewerk-knop"`) — géén ongevraagde bewerk-overlay. `VELD_ANKERS = {eigenaar,
  biv, levensfase, bedoeling, beschrijving}` (`detailIngang.js`). De mens beslist; LIKARA opent de
  plek, verzint geen invoer.
- **De bezoeker wint van het scherm (volgorde-invariant).** Een detail-view die een deep-link/
  aanleiding uit de URL leest én zijn sub-content **async** bijlaadt, mag zijn eigen URL-terugschrijf
  pas starten **nadat de binnenkomst verwerkt is**. Referentie: `ComponentDetail.vue:273-322`
  (`_binnenkomstVerwerkt`-poort op `schrijfTabNaarUrl`); zonder poort liet de async categorie-watch
  (checklistvragen arriveren middenin `laad()`) de terugschrijf op de beginstand vuren en wiste de
  aanleiding vóór `_initVanafQuery` hem las — op elk component mét checklistvragen. Elke nieuwe
  aanleiding-lezende view met async sub-content erft deze poort-eis.
- **Per-ring edge-popup-takken + dekkingsscan (het "vergeten gebruikt-tak"-bewijs).** De kaart-edge-
  popup vertelt per ring zijn eigen verhaal via `_EDGE_TAKKEN` (`LandschapskaartView.vue:1566`);
  borging `RINGEN ⊆ _EDGE_TAKKEN` (`tests/LandschapskaartPopups.test.js:452-454`) + een
  **runtime-fallback** (neutraal verhaal bij een onbekende ring, `:1701`). Zonder de scan viel een
  ring zonder tak **stil** door naar het koppeling-pad (de gebruikt-doorklik landde verkeerd). Een
  nieuwe ring zonder tak faalt nu zichtbaar in de suite.
- **Beginscherm-binnenkomst = één eenmalige regel (zie §LI023 hierboven, aangescherpt LI046).**
  `beginschermOpen = actieveSet.size === 0` ná de beslisboom (`:2665`), voor álle takken; **per-tak-
  vlaggen bestaan niet meer** (het "vergeten per-tak-vlag"-bewijs). Borging: de gedeelde regel wordt
  getoetst via de herstelde-`lk-state`-tak + verse start + de verdwenen-selectie (`LandschapskaartView.test.js`
  `:1607/:1617/:1632`); handoff/deep-link erven hetzelfde codepad (niet apart per tak uitgeoefend).
- **Verdwenen selectie = eerlijke lege staat (`lk-leeg-verdwenen`).** Kom je terug met een selectie die
  volledig weggeschoond is (spook-ids, LI052-prune), dan telt `setOpgeschoond` de weggeschoonde ids en
  toont de view `data-testid="lk-leeg-verdwenen"` ("De eerder gekozen componenten bestaan niet meer" +
  "Begin opnieuw"→`wisSet`) i.p.v. het zwijgzame `lk-leeg`. `setOpgeschoond` verandert het prune-gedrag
  niet; het is het bewijs dat er zojuist iets wég was.

## LI046-patronen (linkerkolom heeftData-gate + relaties gescheiden op hoedanigheid)

*(De UX-regels staan in likara-ux §LI046 "de kaart leesbaar houden"; hier het hoe, geverifieerd.
Gebouwd `3a72b35`/`6651f1f`.)*

- **Kolom-gate op `heeftData`, niet op `!beginschermOpen`.** De kijkinstellingen-`<aside data-testid="lk-links">`
  draagt `v-if="heeftData"` (`nodes.length > 0`, `LandschapskaartView.vue:284`) — bewust níét
  `!beginschermOpen` (dat staat ook open tijdens laden of bij een verdwenen selectie). De aside is een
  flex-sibling van het `flex-1`-canvas → verbergen reflowt het canvas; de ResizeObserver (`_pasCanvasMaat`:
  `cy.resize()` + `fit()`, **géén re-layout**) vangt dat op zonder knoop-verspringing. Filter-refs blijven
  bewaard en grijpen zodra er weer data is. Borging: `LandschapskaartView.test.js` (leeg → geen kolom ·
  getekend → kolom · `wisSet` → kolom weg).
- **Views + beheer op het startpaneel; standaardkijk blijft bij de kaart.** `KaartBeginscherm` draagt nu de
  views-CRUD (`kb-view-bewerk/-verwijder`, prop `magViewsBeheren` + emits `bewerkView`/`verwijderView`); het
  `lk-views`-kolomblok is weg (één plek). De standaardkijk-opslaan blijft in de kolom — je slaat op wát je
  op de getekende kaart ziet; toepassen-bij-start gebeurt al in `onMounted`. Rol & BIV in een native
  `<details data-testid="lk-rolbiv">` met een `lk-rolbiv-actief`-badge bij een gezet filter.
- **Scheiden op HOEDANIGHEID — zuivere beslissing + soort-agnostische geometrie.** `modules/…/frontend/
  kaartBanen.js`: `hoedanigheidVan(relatietype)` (default = het relatietype; **alléén** `roltoewijzing →
  'beheer'`), `baanVerdeling(edges)` groepeert per `(bron,doel,hoedanigheid)` en verdeelt de groepen **per
  ongeordend knooppaar** over banen met een richting-gecorrigeerde control-point-afstand (`cpd =
  basis·richting`; de spiegeling zet A→B en B→A op eigen banen). De fan rekent puur op het knooppaar →
  **ring-agnostisch**: een nieuwe soort erft een eigen baan **zónder code-tak** (invariant-boven-afspraak,
  werkprotocol §KERNLES LI038 — géén nieuwe les). `CY_STYLE`: `curve-style: 'unbundled-bezier'` +
  `control-point-distances: 'data(cpd)'` (één hoedanigheid → cpd 0 → rechte lijn). Beheerrollen → één
  'beheer'-baan (`baanLabel`: ≤`BEHEER_LABEL_MAX`=2 → namen, ≥3 → teller).
- **Ripple-vrije ingang: groepeer/fan in `_elementen()`, ná de instance-projectie.** Zo blijven de
  Lagen-rolbanen + rol-tags (die `zichtbareEdges`/`_rollenVanPartij` **vóór** de collapse lezen) ongemoeid.
  Raak dit patroon nooit vóór de projectie aan — dan breken de rolbanen.
- **De klik levert alles onder het paar.** `openEdgePopup` bouwt `popupPaarLijst` uit `grafEdges` (de
  VOLLEDIGE graaf — ook een relatie op een uitgezette ring telt mee) via dezelfde `baanVerdeling`; de popup
  toont "Tussen deze twee:" met élke hoedanigheid, aanklikbaar (`lk-popup-paar-<hoed>`). Vervangt de oude
  tap-resolutie op één ring. De flow-master-detail (`api.relaties.lijst`, paar-fetch) blijft ongewijzigd.
- **Borging = de BESLISSING (LI044-pure-functie-patroon).** `frontend/tests/kaartBanen.test.js` bewijst:
  twee hoedanigheden → twee onderscheiden geometrische plekken · een **onbekend** relatietype ("toekomstige_
  soort") erft een eigen baan · beheer-collapse · bidirectioneel gescheiden. De render (unbundled-bezier +
  `BAAN_STAP`-afstand) is **browsercheck**-materie, geen unit-test.
