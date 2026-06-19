---
name: complidata-frontend
description: Frontend-patronen voor CompliData (Vue 3, PrimeVue Unstyled, Tailwind v4). Beschrijft de werkelijke V003-staat (login + app-shell + module-views).
stack: Vue 3, Vite, PrimeVue Unstyled, Tailwind CSS v4, Pinia, vue-router, vitest
bijgewerkt: V007
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
