---
name: complidata-frontend
description: Frontend-patronen voor CompliData (Vue 3, PrimeVue Unstyled, Tailwind v4). Beschrijft de werkelijke V003-staat (login + app-shell + module-views).
stack: Vue 3, Vite, PrimeVue Unstyled, Tailwind CSS v4, Pinia, vue-router, vitest
bijgewerkt: V016
---

# CompliData Frontend Skill

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

- Altijd de **`--cd-`-prefix** (uit `src/themes/base.css`). Geen `<style>`-blokken;
  uitsluitend Tailwind-utilities + `--cd-`-tokens. `assets/main.css` importeert
  Tailwind v4 + `base.css` + globale resets/utilities (o.a. `.card`).
- Tailwind arbitrary aria-variant voor de actieve nav-link:
  `aria-[current=page]:bg-[var(--cd-color-accent)]`.

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
- Uitloggen: `auth.logout()` (wist `cd_session`, redirect `/login`). **OP-4**:
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

## Knopstandaard KILARA (niet-onderhandelbaar)

De knop is **één herbruikbaar standaardobject met één vaste hoogte** (`h-10`), volledig
gestuurd door `frontend/src/presets/Button.js`. Er is **GEEN** size-variatie — `size="small"`
bestaat niet meer (preset-tak verwijderd; een `size`-prop heeft geen hoogte-effect). De enige
toegestane variatie is:

- **(a) kleur per rol** — `primary` (donkerblauw, hoofdactie; default zonder severity),
  `secondary` (lichtblauw, nevenactie), `danger` (rood, destructief), `text` (ghost/tertiair,
  transparant + primary-tekst). Per scherm geldt: **maximaal één primary** (de hoofdactie).
- **(b) breedte** — past zich aan de tekst aan (`px-4`, geen vaste breedte).

**Geen per-call-site hoogte/padding-overrides** (`class`/`:pt`/`style`) — alleen positionering
(`ml-auto`/`mt-*`) is toegestaan. Alle knoppen lopen via het ene preset; zo kan een
hoogteafwijking structureel niet meer ontstaan.

**Tabbladen** (`AppTabs.vue`) volgen dezelfde kleurtaal én hoogte (`h-10`, `--cd-radius-btn`):
omlijnd = beschikbaar, lichtblauw (`--cd-color-primary-50/700`) = hover, donkerblauw
(`--cd-color-primary`, wit, semibold) = gekozen.

## UI-interactiestates + borging (niet-onderhandelbaar)

**Interactiestates.** Hover/focus/selected lopen uitsluitend via `--cd-`-tokens en de centrale
componenten (`presets/Button.js`, `AppTabs.vue`). Geen losse kleuren of state-klassen op
call-sites.

**Tailwind-scanning (vereist, geen optie).** Tailwind v4 scant **glob-gebaseerd** (niet via de
Vite module-graph). Elke module-frontend buiten `frontend/` (onder `modules/`) MOET via een
`@source`-directive in `src/assets/main.css` worden meegescand — anders ontbreken module-unieke
klassen **stil** in de productie-CSS (bewezen: zonder `@source` vallen de tab-hover- en
`border-[0.5px]`-klassen uit de build; ADR-/incidentlijn tab-hover). Een nieuwe module ⇒ een
`@source`-regel toevoegen.

**Borging — drie lagen (`frontend/tests/` + `npm run test:css-build`):**
1. **Token-contracttest** (`tokens.contract.test.js`) — afgesproken `--cd-`-tokens bestaan en zijn
   niet-leeg.
2. **Component-render-state-test** (`interactiestates.test.js`) — Button-preset (elke variant zet
   de juiste token-klasse + vaste `h-10`) en AppTabs (states op de juiste — klikbare — `role="tab"`,
   juiste token-klassen).
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

### 3. Initialisatie: nextTick×2 + offsetHeight-check + delayed resize/fit
```javascript
async function tekenGraaf() {
  await nextTick(); await nextTick()  // tweede tick voor Vite HMR edge-cases
  const el = containerRef.value
  if (!el) return
  if (el.offsetHeight === 0) { el.style.minHeight = '500px'; await nextTick() }
  cy.elements().remove(); cy.add(elementen); cy.layout(layout).run()
  setTimeout(() => { cy?.resize(); cy?.fit(undefined, 50) }, 100)  // browser layout-flush
}
```

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

## Rol-gating = affordance (backend handhaaft)

```javascript
// src/store/auth.js — hasRole IS functioneel post-ADR-010 (rollen uit /auth/me)
const auth = useAuthStore()
auth.hasRole('medewerker', 'beheerder')   // toont/verbergt knoppen
```

De UI verbergt alleen knoppen; de **backend** handhaaft via `vereist_permissie`.
Vang een toch-403 netjes af (Toast). Nooit tokens in `localStorage` (httpOnly).

## Login-patroon (LoginView)

- Launch-page met één knop → **volledige** browser-redirect:
  `window.location.assign('/api/v1/auth/login')` (geen `fetch`, geen in-app
  wachtwoordveld). `next` alleen meesturen bij een same-origin relatief pad
  (backend hervalideert). `?sessie_verlopen=1` → inline `role="alert"`.
- Na login zet de backend `cd_session` en redirect naar `next` (default `/`); de
  router-guard zet de gebruiker door.

## Testopzet (vitest)

- Poorten: `vite build` + `vitest` (geen eslint/type-check).
- Module-view-tests staan onder **`frontend/tests/`** (binnen de vitest-root;
  vitest scant niet buiten `frontend/`) en importeren de view via `@modules`.
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
  `tabs`/`modelValue`/`ariaLabel`/`orientation`/`idPrefix`; `--cd-`-tokens, geen `<style>`. [CD022]
- **2-laags tabs + deep-link** (ApplicatieDetail, CD022): top- én sub-niveau zijn elk een echte
  `AppTabs`; de actieve tab(s) in de URL via query-params (`?tab=`/`&cat=`), `router.replace`
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
  met `:to="{ name: 'component-lijst', query: { … } }"`, `--cd-`-tokens, `data-testid="telling-…"`.
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
