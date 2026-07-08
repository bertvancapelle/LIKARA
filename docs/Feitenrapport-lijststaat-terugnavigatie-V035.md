# Feitenrapport — lijststaat behouden bij terugnavigeren (READONLY, V035)

> Read-only feitenonderzoek n.a.v. `START: READONLY_lijststaat_behoud_terugnavigatie`.
> Niets gewijzigd, niets gebouwd. Alle bevindingen zijn tegen de code geverifieerd op
> commit `73d1aaa` (V035). Regelnummers verwijzen naar de huidige werktree.

## Samenvatting (TL;DR)

- **De waarneming op Partijen klopt.** `PartijLijst.vue` houdt aard-filter, zoekterm,
  sortering en cursor uitsluitend in **component-lokale `ref`s**; bij navigatie naar het
  detail unmount de route-component en bij terugkeer mount hij vers met kale defaults
  (`onMounted(() => laad({ reset: true }))`). Er is géén `<keep-alive>`, géén
  URL-sync, géén storage. Alles is weg.
- Dit geldt voor **alle** lijstschermen, met één gedeeltelijke uitzondering:
  **ComponentLijst** en **BlokkadeOverzicht** lezen bij mount éénmalig een paar
  route-query-params (doorklik-prefill: `?type=`, `?status=`, `?afwijking=`,
  `?klaarverklaring=`) — maar schrijven wijzigingen **nooit terug** naar de URL. Alleen
  díé query-gedragen prefills herleven bij een echte browser-/terugknop-back; alles wat
  de gebruiker daarna handmatig instelde is verloren.
- Er is **geen gedeelde lijst-bouwsteen**: elk scherm implementeert het
  laad/sort/filter/cursor-patroon zelf (wel byte-voor-byte hetzelfde idioom, wat een
  mechanische retrofit haalbaar maakt). Een generieke fix landt dus óf op router-niveau
  (één plek), óf als composable die N schermen adopteren.
- Er zijn **drie bruikbare precedenten**: het `lk-state`-sessionStorage-patroon van de
  Landschapskaart (LI022/LI034, incl. `beforeunload` + herstel-precedentie), de
  module-singleton `useTerugNavigatie` (weet al óf de gebruiker "van een detail terugkomt"),
  en de consume-once in-memory `kaartHandoff`. Nergens `<keep-alive>`, nergens
  `scrollBehavior` — scrollpositie gaat overal verloren.

---

## 1. Inventaris van lijstschermen

Criterium: (a) filter/zoek/sortering én (b) doorklik naar detail waar de gebruiker van
terugkeert.

### 1a. Volledig in scope (filter/zoek/sort + doorklik-terug-flow)

| # | Scherm (route) | Bestand | Lijststaat-elementen | Doorklik → terug |
|---|---|---|---|---|
| 1 | **Partijen** (`/partijen`) | `modules/bwb_ontvlechting/frontend/views/PartijLijst.vue` | aard-filter (select), zoekveld (debounced), server-sort op 3 kolommen (naam/aard/plaats), keyset-cursor "Meer laden" | ja — `partij-detail` (rij-link + aanspreekpunt-link) |
| 2 | **Componenten** (`/componenten`) | `modules/.../ComponentLijst.vue` | grootste set: status (multi), type, ArchiMate-laag, hosting, eigenaar (ZoekSelect), zoekveld, rol (multi), BIV-drempel ×3, klaarverklaring/afwijking-chip; server-sort; keyset-cursor | ja — `component-detail` |
| 3 | **Contracten** (`/contracten`) | `modules/.../ContractLijst.vue` | leverancier-, type-, dekking-, kostenmodel-filter, zoekveld, server-sort, keyset-cursor | ja — `contract-detail` |
| 4 | **Blokkades** (`/blokkades`) | `frontend/src/views/BlokkadeOverzichtView.vue` | statusfilter (init uit `?status=`), server-sort (default `applicatie_naam asc`), keyset-cursor | ja — `component-detail` (met markeer-/tab-query) |

### 1b. Gedeeltelijk in scope (wel momentstaat + doorklik, geen filter/zoek/sort)

| # | Scherm | Bestand | Staat die verloren gaat | Doorklik |
|---|---|---|---|---|
| 5 | **Signalering** (`/signalering`) | `frontend/src/views/SignaleringView.vue` | actieve **tab** (registratiegaten/plaatsing, lokale `ref`) | ja — links naar entiteit-details (`SignaleringView.vue:122`) |
| 6 | **Migratie-lijsten** ×4 (`/migratie/plateaus`, `gaps`, `werkpakketten`, `deliverables`) | `frontend/src/views/migratie/*LijstView.vue` | alléén keyset-cursor ("Meer laden"-voortgang) + scroll — **geen filter/zoek/sort aanwezig** (de sorteer-sweep uit OPVOLGPUNTEN is hier nog open) | ja — `router.push` naar detail |

### 1c. Buiten scope — met reden (discrepanties t.o.v. de verwachte kandidaten)

| Verwachte kandidaat | Bevinding |
|---|---|
| **Gebruikersgroepen** | **Bestaat niet als lijstscherm.** Gebruikersgroepen leven uitsluitend als sectie op ComponentDetail (`GebruikersgroepSectie.vue`); er is geen eigen lijstroute, dus geen doorklik-terug-flow. |
| **Leveranciers** | **Bestaat niet meer als eigen lijst** — opgegaan in Partijen (PartijLijst "vervangt LeverancierLijst", header-comment). |
| **Auditlog** (`/auditlog`, `AuditTrailView.vue`) | Heeft wél filters (actor-naam, component-ZoekSelect, actie, van/tot) + cursor, maar het "detail" is een **inline uitklaprij** (`uitgeklapt`-map) — er staat **geen enkele router-link** in de template. Geen doorklik-weg, dus geen terugkeer-verlies binnen de flow. (Weg-navigeren via de sidebar wist uiteraard wél alles.) |
| **Checklistvragen** (`/checklistvragen`) + alle `/beheer/*`-configlijsten | Hebben filters (bv. client-side `categorieFilter`), maar bewerken gebeurt **inline/in dialogs** — geen detail-route, geen terug-flow. |
| **Gebruikersbeheer** (`/gebruikers`) | Platte lijst zonder cursor/zoekveld op de lijst; beheer in dialogs. Geen terug-flow. |
| **Dashboard** | Geen lijst; bron van doorklik-filters náár ComponentLijst. |
| **Landschapskaart** | Heeft de flow wél, maar is al opgelost (het `lk-state`-precedent, zie §4). |

---

## 2. Bewaart het niets, of het verkeerde — en waaróm

### Feitelijk gedrag per scherm

**Partijen (waarneming bevestigd).** Alle staat is component-lokaal:
`filterAard`/`filterZoek`/`sortVeld`/`sortRichting`/`cursor`/`items` zijn `ref`s in
`<script setup>` (`PartijLijst.vue:27-40`). De route-component unmount bij navigatie naar
`partij-detail`; bij terugkeer (terugknop óf sidebar) mount een verse instantie en draait
`onMounted(() => laad({ reset: true }))` (`:88`) met alle defaults. Het aard-filter
"Organisatie" is dus weg — exact zoals waargenomen. Er staat niets in de URL, dus ook
`router.back()` (de "← Terug naar Partijen"-knop) herstelt niets.

**Componenten en Blokkades: "het verkeerde" — half via de URL, eenrichting.**
- `ComponentLijst.vue:183-195` leest bij mount éénmalig `route.query.type`, `status`,
  `afwijking`, `klaarverklaring` (doorklik-prefill vanaf dashboard/`/applicaties`-redirect).
- `BlokkadeOverzichtView.vue:29-31` leest `route.query.status`.
- **Geen van beide schrijft filterwijzigingen terug** naar de URL (geen
  `router.replace` met query in deze views).

Gevolg — het gedrag splitst per terugpad:
- **Echte back** (browser-terug of de `useTerugNavigatie`-knop, die `router.back()` doet):
  de vorige history-entry incl. query komt terug → alléén de query-gedragen prefill
  herleeft (bv. `?status=geblokkeerd` van een dashboard-doorklik). Alles wat de gebruiker
  daarná handmatig bijstelde (extra filters, zoekterm, sortering, "Meer laden"-voortgang)
  is weg. Dit is de "verkeerd bewaard"-variant: deels hersteld, deels gereset.
- **Sidebar-navigatie terug naar de lijst**: verse route zonder query → volledig kaal.

**Contracten, Signalering (tab), migratie-lijsten:** puur "niets bewaard" — zelfde
lokale-`ref`s-plus-`onMounted`-patroon, zonder enige query-lezing.

### Oorzaken (waar de staat leeft en wat ermee gebeurt)

1. **Lijststaat = component-lokale reactive state.** In élk lijstscherm. Geen Pinia-store
   (de enige store is `auth.js`), geen composable, geen storage.
2. **Route-component unmount bij detail-navigatie.** De `<router-view>` in
   `AppLayout.vue` is **niet** in `<keep-alive>` gewikkeld (0 hits op
   keep-alive/KeepAlive in de hele frontend) → Vue vernietigt de lijst-instantie.
3. **Keyset-paginering (ADR-017) is client-gedragen.** De cursor
   (`v2n|sort|order|…`-string) leeft in de lokale `cursor`-ref; de server is stateless.
   Verdwijnt de component, dan verdwijnt óók de "Meer laden"-voortgang. Conform de
   vastgelegde cursor-discipline (likara-db) reset de frontend de cursor bij elke
   filter-/sortwissel — filters zitten bewust níét in de cursor.
4. **URL-query is inconsistent gebruikt**: 2 van de 4 hoofdlijsten lezen een subset van
   hun filters éénmalig uit de query (als doorklik-ingang), geen enkel scherm
   synchroniseert de actieve staat ernaartoe. Elders in de app bestaat twee-weg-achtig
   URL-gebruik wél al: ComponentDetail schrijft zijn actieve tabs naar de URL met
   `router.replace` (`?tab=`/`&cat=`, CD022-patroon).
5. **Scroll**: `createRouter` heeft **geen `scrollBehavior`** (`router/index.js:179-182`)
   en nergens wordt scroll hersteld → scrollpositie gaat overal verloren, ook bij back.

---

## 3. Eén gedeelde bouwsteen of N bespoke lijsten?

**N bespoke lijsten — maar met één sterk geüniformeerd idioom.**

- Er is **geen** gedeelde lijst-/tabel-/filterbalk-component en **geen** lijst-composable
  (0 hits op `useLijst`/`lijstStaat`/`useList`). Elk scherm bouwt zijn eigen filterbalk
  (`data-testid="filterbalk"`) en implementeert zelf: `items/cursor/laden/fout/
  eersteGeladen`-refs, `laad({reset})`, `onSort`, `herfilter`, `herfilterDebounced`
  (300 ms), `wisFilters`, `heeftFilters`. De namen en structuur zijn in PartijLijst,
  ComponentLijst, ContractLijst en BlokkadeOverzicht vrijwel identiek (copy-paste-idioom).
- Wat wél gedeeld is: de **filter-widgets** (`ZoekSelect.vue`, `ZoekMultiSelect.vue`,
  `frontend/src/components/MultiSelectDropdown.vue`) en het DataTable-preset. Die dragen
  geen lijststaat over navigatie heen.
- **Waar een generieke fix structureel één keer kan landen:**
  - *Router-/shell-niveau*: de `<router-view>` in `AppLayout.vue` (voor `<keep-alive>`)
    of `router/index.js` (voor `scrollBehavior` / een centrale query-sync-guard) — echt
    één plek.
  - *Composable-niveau*: een `useLijstStaat(sleutel, velden)`-achtige composable naast
    `useTerugNavigatie.js` — één implementatie, maar **N adoptiepunten** (4 hoofdlijsten
    + evt. Signalering-tab + 4 migratie-lijsten). Door het uniforme idioom is die
    retrofit mechanisch (zelfde refs, zelfde mount-hook overal).

---

## 4. Bestaande precedenten (niet opnieuw uitvinden)

| Precedent | Vindplaats | Mechanisme | Herbruikbaar voor lijststaat? |
|---|---|---|---|
| **Kaart-state (LI022/LI034, commit `c8ae3c7`)** | `LandschapskaartView.vue:2120-2167` | sessionStorage-key `lk-state`; **bewaard** op `onBeforeRouteLeave` én `beforeunload` (F5-fix LI034); **hersteld** bij mount met expliciete precedentie: handoff > deep-link `?center=` > bewaarde state > standaardkijk; herstel valideert elke waarde (geldige permutatie/allowlist); `wisSet` ("Begin opnieuw") **verwijdert** de key expliciet (`:814`) | **Ja — dit is het meest directe precedent.** Zelfde vraag (momentstaat behouden over een detailbezoek + reload), zelfde in-sessie-scope, bewezen incl. de F5-rand en de wis-actie. |
| **useTerugNavigatie (LI018)** | `frontend/src/composables/useTerugNavigatie.js` + `router/index.js:186` | module-niveau singleton-`ref` `vorigeRoute`, centraal gevuld via `router.afterEach` | Ja als **detectie-bouwsteen**: het systeem wéét al waar de gebruiker vandaan komt — daarmee is "herstel alleen bij terugkeer-van-detail, open kaal bij verse navigatie" te onderscheiden. |
| **kaartHandoff (LI033)** | `frontend/src/composables/kaartHandoff.js` | module-niveau **consume-once** in-memory payload (bewust géén route-query: te lang voor URL; géén store) | Ja als precedent voor een lichte **in-memory nav-cache** (optie D in §5), incl. de gedocumenteerde afweging query-vs-memory. |
| **Twee-weg tab-in-URL (CD022)** | ComponentDetail (`?tab=`/`&cat=`, `router.replace`, geen history-spam, default = schone URL) | query-sync van UI-staat | Ja als precedent voor optie A (staat-in-URL): het `router.replace`-patroon bestaat al in de codebase. |
| **Eenrichtings-query-prefill** | `ComponentLijst.vue:183-195`, `BlokkadeOverzichtView.vue:29-31`, `/applicaties`-redirect (`router/index.js:102`) | mount-time `route.query`-lezing | De halve versie van optie A; elke gekozen route moet hiermee composeren (doorklik-filters mogen niet breken). |
| **sessionStorage elders** | `lk-legenda` (`LandschapskaartView.vue:1587-1593`), lane-volgorde (`:1963`) | kleine UI-voorkeuren in-sessie | Bevestigt sessionStorage als het gangbare "momentstaat"-kanaal. |
| **localStorage elders** | `arch-weergave` (`ArchitectuurView.vue:35-103`), `lk-sidebar-ingeklapt` (`AppLayout.vue:34-45`) | duurzame, niet-gevoelige weergavevoorkeuren | Contrast: localStorage wordt gebruikt voor "vaste bril"-voorkeuren, níét voor momentstaat — consistent met de LI034-sortering (vaste bril vs. momentkeuze). |
| **`<keep-alive>`** | — | **nergens gebruikt** (0 hits) | Zou een nieuw mechanisme in de codebase zijn. |
| **`scrollBehavior` / scroll-herstel** | — | **afwezig** in `createRouter` | Scroll is vandaag in géén enkel scherm gedekt; elke optie moet dit apart benoemen. |
| **Pinia** | alleen `store/auth.js` | — | Een lijststaat-store zou de eerste niet-auth-store zijn; `kaartHandoff` koos bewust een module-ref i.p.v. een store. |

---

## 5. Kandidaat-routes voor de generieke oplossing (opsomming — géén keuze)

| Optie | Waar het landt | Generiek of per-scherm | Aanhaking op precedenten | UX-consequenties |
|---|---|---|---|---|
| **A. Lijststaat twee-weg in de URL-query** (`router.replace` bij elke filter-/sortwijziging; mount leest query) | per lijstview (of via een klein query-sync-composable) | één helper, **N adoptiepunten**; de bestaande eenrichtings-prefill (ComponentLijst/Blokkades) wordt het fundament i.p.v. een conflict | CD022-tab-patroon (`router.replace`, schone default-URL); bestaande `?type=`/`?status=`-doorkliks blijven vanzelf werken | + URL is deelbaar/bookmarkbaar; + overleeft reload én back; + terugknop (`router.back()`) herstelt automatisch. − Sidebar-klik naar de lijst is een verse URL → alsnog kaal (tenzij de nav-link de laatste fullPath onthoudt); − lange query's bij veel filters (BIV×3 + rol-multi…); − "Meer laden"-voortgang en scroll passen niet zinvol in een URL. |
| **B. `<keep-alive>` om de `<router-view>` in AppLayout** (met `include`-lijst van lijstviews) | **één plek**: `AppLayout.vue` | volledig generiek; lijstviews zelf vrijwel ongemoeid (wel `onActivated`-vers-check per scherm gewenst tegen stale data) | geen precedent — nieuw mechanisme in deze codebase | + Behoudt **alles**: filters, sortering, geladen items incl. "Meer laden"-pagina's, en (binnen de gescrollde container) de scrollpositie; + geen serialisatie. − Alleen in-sessie, overleeft **geen** reload; − stale-data-risico (na bewerken in het detail toont de teruggekeerde lijst oude rijen → verversing in `onActivated` nodig); − interactie met de bestaande `props.id`-watch-discipline en geheugengebruik bewaken; − herstelt óók bij sidebar-navigatie (kan gewenst of ongewenst zijn — geen onderscheid back vs. vers zonder extra logica). |
| **C. sessionStorage-composable à la `lk-state`** (bv. `useLijstStaat('partij-lijst', {filterAard, filterZoek, sortVeld, …})`: bewaar op `onBeforeRouteLeave` + `beforeunload`, herstel gevalideerd bij mount, "Filters wissen" wist de key) | nieuw composable naast `useTerugNavigatie.js`; **N adoptiepunten** (mechanisch — uniform idioom, zie §3) | **directe voortzetting van het LI034-precedent** (`lk-state`, incl. F5-gedrag, herstel-precedentie query > storage, en expliciete wis-actie) | + Overleeft reload (F5) én werkt bij álle terugpaden (back én sidebar); + in-sessie-scope past bij "momentkeuze" (sessionStorage sluit per tab, geen voorkeur-laag). − URL niet deelbaar; − herstelt ook bij verse navigatie binnen de sessie (tenzij gecombineerd met `vorigeRoute`-detectie); − lijst wordt her-fetcht vanaf pagina 1 (filters/sort terug, "Meer laden"-voortgang en exacte scroll niet — cursor her-opbouwen zou meerdere fetches vergen). |
| **D. In-memory nav-cache** (module-singleton per route-naam, à la `kaartHandoff`/`useTerugNavigatie`; optioneel keyed op "kwam terug van detail" via `vorigeRoute`) | nieuw composable; N adoptiepunten óf centraal via een `router.afterEach` | `kaartHandoff` (module-ref, bewust geen query/store) + `useTerugNavigatie` (herkomst-detectie bestaat al) | + Kan méér cachen dan serialiseerbare staat (desgewenst óók `items`+`cursor`+scrolloffset → volledige terugkeer incl. "Meer laden"-voortgang, zonder keep-alive); + kan precies het gewenste onderscheid maken: herstel **alleen** bij terugkeer-van-detail, kaal bij verse navigatie. − Overleeft geen reload (F5 → kaal; juist de rand die LI034 op de kaart dichtte); − URL niet deelbaar; − items cachen introduceert hetzelfde stale-data-punt als B. |

**Dwarsverbanden die bij de keuze meewegen (feitelijk, geen advies):**
- De opties zijn combineerbaar (bv. C voor filter/sort/zoek + een aparte, kleine
  scroll-afspraak; of A voor de deelbare kernfilters + D voor paginering/scroll).
- Elke route moet composeren met de **bestaande doorklik-query's** (dashboard →
  `?status=`, `/applicaties`-redirect → `?type=`): een expliciete query bij binnenkomst
  hoort voorrang te houden op herstelde staat — exact de precedentie-volgorde die de
  kaart al hanteert (handoff > deep-link > bewaarde state > standaard).
- **Scroll** is in géén van de opties gratis behalve B; A/C/D vergen daarvoor een
  aanvullende `scrollBehavior`- of offset-afspraak.
- De 4 migratie-lijsten hebben vandaag niets te herstellen behalve cursor/scroll; zodra
  de openstaande sorteer-sweep (OPVOLGPUNTEN) daar filters/sortering toevoegt, horen ze
  bij dezelfde oplossing aan te sluiten.

---

## Discrepantie-log (aannames uit de opdracht vs. code)

1. **"Partijen: aard-filter weg na terug"** — ✅ bevestigd (component-lokale refs, geen
   enkel behoud; §2).
2. **"Gebruikersgroepen" als kandidaat-lijstscherm** — ❌ bestaat niet als lijstroute
   (sectie op ComponentDetail).
3. **"Leveranciers" als kandidaat** — ❌ bestaat niet meer; opgegaan in Partijen.
4. **"Blokkades, Signalering, checklist-/beheerlijsten"** — deels: Blokkades volledig in
   scope; Signalering alleen tab-staat; checklist-/beheerlijsten en Auditlog hebben
   filters maar **geen detail-doorklik-flow** (inline dialogs/uitklaprijen) → geen
   terugkeer-verlies binnen de flow.
5. **"Beeld verschilt per scherm"** — ✅ ja, maar beperkt: het enige verschil is de
   eenrichtings-query-prefill op ComponentLijst/Blokkades (herleeft alléén bij echte
   back). De rest is uniform "alles kwijt".

---

*Einde rapport — STOP conform opdracht. Geen fix, geen ontwerpkeuze, geen commit;
route-keuze ligt bij PNA + Bert.*
