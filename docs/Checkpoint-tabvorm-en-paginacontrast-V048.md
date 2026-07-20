# Checkpoint — de tabrij als tabrij, en de pagina als ondergrond

| | |
|---|---|
| **Sessie** | LI048 |
| **Build** | V048 |
| **Gemeten tegen commit** | `3497d56` (`master`, schone werktree — `git status` leeg bij aanvang) |
| **Aard** | READ-ONLY feitenopname · niets gewijzigd behalve dit bestand |
| **Meetwijze contrast** | WCAG 2.x relatieve-luminantieformule, berekend op de tokenwaarden uit `base.css` |

---

## Kernbevindingen vooraf

**1. STOP — `ApplicatieDetail` bestaat niet meer.** De opdracht noemt het als "bekend precedent"
voor 2-laags tabs. Er is geen enkel bestand met die naam in de repo. De 2-laags opzet is met LI059
**opgegaan in `ComponentDetail.vue`** (`ComponentDetail.vue:5`, `:209` — *"geport uit
ApplicatieDetail"*). Gevolg voor de reikwijdte: er is precies **één** scherm met twee tabniveaus,
niet twee. De skill `likara-frontend:519` noemt `ApplicatieDetail` nog wél — dat is een onware
passage (zie 5.2).

**2. STOP — de klacht is geen bijverschijnsel maar een bewust ontworpen uitzondering.** Er is één
variabele (`activeTop`) voor zowel tabbladen als Open punten. `PLEKKEN_ZONDER_TAB = ['open-punten']`
(`ComponentDetail.vue:218`) bestaat expliciet om een waarde toe te laten die bij géén tabblad hoort,
mét een watch-uitzondering (`:255-260`) die voorkomt dat het scherm terugvalt op Overzicht. De
LI047-motivering staat er letterlijk bij (`:212-217`): *"Open punten toont geen onderdeel van het
component maar wat eraan mankeert"* + *"de tabrij was bovendien al elf breed"*. De voorgestelde
richting **herroept een beredeneerd LI047-besluit** — dat is legitiem, maar het is geen bugfix.

**3. STOP — de huidige toestand is een echte toegankelijkheidsfout, niet alleen een visuele.**
`AppTabs.vue:69` zet `:tabindex="t.key === modelValue ? 0 : -1"`. Staat `activeTop` op
`'open-punten'`, dan matcht **geen enkele** tab → **alle** tabs krijgen `tabindex="-1"` → de hele
tabrij valt uit de tab-volgorde en is met het toetsenbord **onbereikbaar**. De gebruiker kan dan
alleen nog met de muis terug naar een tabblad. Dit is een zelfstandige reden om de plek een tabblad
te maken, los van de vorm.

**4. De paginakleur heeft een gemeten plafond — dieper gaan kost WCAG-AA op gedempte tekst.**
Huidig verschil pagina↔wit is **1,05:1** (praktisch onzichtbaar). Maar gedempte tekst op die
pagina-ondergrond zit nu al op **4,64:1**, met 4,5:1 als AA-ondergrens. Eén tint dieper is
mogelijk, twee niet: bij `#eef2f7` is het **4,51:1** (de facto de laatste toegestane stap), bij
`#e9eef5` **4,42:1** — gezakt. Zie 4.4 voor de volledige tabel. Dit is een harde randvoorwaarde
voor de ontwerpkeuze, geen smaakkwestie.

**5. De reikwijdte is klein en de canvas-naad bestaat niet.** `AppTabs` heeft **drie**
aanroepplekken in **twee** bestanden. Het Cytoscape-canvas staat op `--lk-color-surface` (wit), niet
op de paginakleur (`LandschapskaartView.vue:3125`) — het risico uit vraag 4.3 doet zich dus niet
voor. Er is wél één **tweede, met de hand gebouwde tabrij** (`SignaleringView.vue:94-113`) die de
wijziging niet erft.

**6. De regel "bij nul geen getal" en de regel "een lijst legt uit" botsen zodra Open punten een
tabblad wordt.** Nu draagt de kopknop géén getal bij nul (`ComponentDetail.vue:404`), terwijl de
sub-tabbladen binnen Open punten juist wél "(0)" tonen (`OpenPuntenSectie.vue:41-43`). Twee
tegengestelde regels op straks dezelfde visuele vorm — een tablabel met een aantal. Dit moet Bert
beslissen (open vraag 3).

---

## Blok 1 — De tabbouwsteen zelf

### 1.1 `AppTabs.vue`

**Pad:** `modules/bwb_ontvlechting/frontend/views/AppTabs.vue` — **84 regels**.

**Props** (`:14-20`):

| Prop | Type | Vereist | Betekenis |
|---|---|---|---|
| `tabs` | Array `[{key, label}]` | ja | de tabbladen |
| `modelValue` | String\|Number, default `null` | nee | het gekozen tabblad |
| `ariaLabel` | String | ja | label op de `tablist` |
| `orientation` | String, default `'horizontal'` | nee | `horizontal` \| `vertical` |
| `idPrefix` | String | ja | id-conventie `${idPrefix}-tab-${key}` / `-panel-` |

De bouwsteen rendert **alleen de tablist**; de ouder rendert de panelen (`:5-7`).

**Hoe "gekozen" wordt gezet** (`:23-25`): `selecteer(key)` emit `update:modelValue` — de bouwsteen
houdt **geen eigen staat**; de ouder is eigenaar. Er is dus geen intern vangnet.

**De drie staten** (`:71-77`), alle op de `<button role="tab">` zelf:

| Staat | Klassen |
|---|---|
| gemeenschappelijk | `inline-flex items-center h-10 rounded-[var(--lk-radius-btn)] px-[var(--lk-space-md)] text-[length:var(--lk-text-sm)] text-left` + focus-outline |
| **gekozen** | `border-[0.5px] border-[var(--lk-color-primary)] bg-[var(--lk-color-primary)] font-semibold text-white` |
| **beschikbaar** | `border-[0.5px] border-[var(--lk-color-border)] bg-white text-[var(--lk-color-text)]` |
| **hover** | `hover:bg-[var(--lk-color-primary-50)] hover:text-[var(--lk-color-primary-700)]` |

De tabrij zelf (`:56-59`) is `flex gap-[var(--lk-space-xs)]`, met `flex-wrap` horizontaal —
er is dus **geen** doorlopende onderrand en **geen** verband met het inhoudsvlak eronder. Elk
tabblad is een op zichzelf staand, volledig omrand blokje. Dat is precies de "knoppenrij"-vorm.

### 1.2 Kán er een tabrij zonder gekozen tabblad bestaan? — **Ja, en dat gebeurt hier bewust**

De bouwsteen dwingt **niets** af. `modelValue` heeft default `null` (`:16`), er is geen validator,
geen fallback en geen watch die corrigeert. Alles wat van "gekozen" afhangt is een directe
vergelijking `t.key === modelValue` (`:67`, `:69`, `:74`). Bestaat die sleutel niet in `tabs`, dan
is de uitkomst voor **elk** tabblad `false`.

De ouder maakt daar gebruik van (`ComponentDetail.vue:218-219`):

```js
const PLEKKEN_ZONDER_TAB = ['open-punten']
const isGeldigePlek = (k) => topTabs.value.some((x) => x.key === k) || PLEKKEN_ZONDER_TAB.includes(k)
```

en beschermt die toestand actief tegen de terugval-watch (`:255-260`):

```js
watch(topTabs, (tabs) => {
  if (PLEKKEN_ZONDER_TAB.includes(activeTop.value)) return
  if (!tabs.some((t) => t.key === activeTop.value)) activeTop.value = 'overzicht'
})
```

**Drie gevolgen, alle drie feitelijk:**

- `aria-selected` is `false` op álle tabbladen (`:67`) — hulptechnologie meldt een tablist zonder
  selectie.
- `tabindex` is `-1` op álle tabbladen (`:69`) — **de tabrij is niet bereikbaar met Tab**
  (kernbevinding 3). De pijltjesnavigatie in `opToets` (`:27-48`) kan niet starten, want die vereist
  focus binnen de rij.
- Visueel draagt geen tabblad de gekozen-vulling → de rij leest als een knoppenrij. Dit is exact de
  klacht.

### 1.3 Toegankelijkheidsattributen — en wat er bij een vormwijziging verandert

De bouwsteen zet nu: `role="tablist"` + `aria-label` + `aria-orientation` (`:52-55`); per tabblad
`role="tab"`, `aria-selected`, `aria-controls`, roving `tabindex`, `id` (`:63-70`). Toetsenbord
(`:27-48`): ←/→ (↑/↓ verticaal), Home/End met **automatische activatie**, Enter/Space activeren.

**Wat verandert bij de voorgestelde vormwijziging: niets aan de ARIA-laag.** De semantiek is
volledig losgekoppeld van de opmaak — alle attributen hangen aan `role`/`modelValue`, niet aan
klassen. Een tabvorm-wijziging raakt uitsluitend de `:class`-expressie (`:71-77`) en eventueel de
container-klassen (`:56-59`).

**Eén uitzondering, en die is juist de winst:** zodra Open punten een écht tabblad wordt, is er
altijd precies één match → `aria-selected="true"` klopt weer en de roving `tabindex` levert weer
één bereikbaar element. De a11y-fout uit 1.2 verdwijnt als **gevolg** van de ontwerpkeuze, niet als
aparte reparatie.

⚠ **Aandachtspunt bij het bouwen:** `role="tabpanel"` + `aria-labelledby="detailtabs-tab-…"` hoort
dan óók op het open-punten-paneel. Dat draagt nu bewust `role="region"` +
`aria-labelledby="open-punten-titel"` (`ComponentDetail.vue:573-574`) — correct voor een plek
zónder tabblad, onjuist zodra het er wél een heeft.

---

## Blok 2 — Reikwijdte: wie erft deze wijziging?

### 2.1 Alle consumenten van `AppTabs`, repo-breed

Gezocht over de héle repo (`frontend/`, `modules/`, `backend/`, `docs/`), niet per module.

| Bestand | Scherm | Aanroep | Tabbladen | Niveau |
|---|---|---|---|---|
| `modules/…/views/ComponentDetail.vue:445` | Componentdetail | `id-prefix="detailtabs"` | 6–11 (conditioneel per type, `:221-250`) | **1** |
| `modules/…/views/ComponentDetail.vue:605` | Componentdetail → Checklist | `id-prefix="checklisttabs"`, `orientation="vertical"` | = aantal categorieën (12 in de baseline), afgeleid uit de geladen vragen (`:263-265`) | **2** |
| `modules/…/views/OpenPuntenSectie.vue:118` | Open punten (binnen Componentdetail) | `id-prefix="open-punten"` | 3, vast (`:33-37`) | **2** |

Plus één niet-productieve consument: `frontend/tests/interactiestates.test.js` (mount in de
render-state-test).

**Totaal: 3 aanroepen in 2 bestanden, beide in de bwb-module.** Geen enkele consument in
`frontend/src/`. Dat maakt de reikwijdte van een `AppTabs`-vormwijziging klein — maar zie 2.3.

### 2.2 Waar staan twee tabniveaus onder elkaar?

**Precies één scherm: `ComponentDetail.vue`.** Twee verschillende nestingen, en dat onderscheid is
belangrijk voor de "niveau 2 wordt ondergeschikt"-keuze:

| Geval | Buitenste rij | Binnenste rij | Verhouding |
|---|---|---|---|
| **Checklist** (`:596-618`) | horizontale toptabs | **verticale** rij, links náást het paneel (`md:w-[16rem]`) | naast elkaar — niveau 2 staat niet ónder niveau 1 |
| **Open punten** (`:570-578` → `OpenPuntenSectie.vue:118`) | horizontale toptabs (nu: géén gekozen) | **horizontale** rij, direct eronder | **onder elkaar, zelfde richting, zelfde maat** |

De klacht "twee tabrijen in dezelfde maat en vorm" slaat dus **uitsluitend op het tweede geval**.
Het checklist-geval is door zijn verticale oriëntatie al onderscheiden. Een generieke
"niveau 2 = kleiner en gedempt"-regel op de bouwsteen zou het checklist-geval mee veranderen zonder
dat daar een klacht ligt — dat is een keuze, geen automatisme (open vraag 2).

`ApplicatieDetail` bestaat niet meer — zie kernbevinding 1.

### 2.3 Tabrijen die niet via `AppTabs` lopen — **ja, één**

`frontend/src/views/SignaleringView.vue:94-113` bouwt een tablist met de hand: drie
`<button role="tab">` met `:aria-selected`, in een `<div role="tablist">`.

Feiten:

- **Deelt de tokens deels, niet de vorm.** Wel `h-10` en `--lk-color-primary`; maar
  `rounded-t-[var(--lk-radius-btn)]` (alleen bovenhoeken) en een **`border-b` op de container** —
  dus dit scherm heeft nu al een aanzet tot de "vast aan het vlak eronder"-vorm die de opdracht
  voorstelt. De hover is `--lk-color-accent`, niet `--lk-color-primary-50` zoals `AppTabs`.
- **Mist de a11y-laag volledig:** geen `aria-controls`, geen roving `tabindex`, geen
  pijltjesnavigatie, geen `id`-koppeling met de panelen (`:117`, `:196`, `:201` dragen `role="tabpanel"`
  zónder `aria-labelledby`).
- **Erft de wijziging niet.** Verandert de tabvorm in `AppTabs`, dan lopen deze drie tabbladen
  stilzwijgend uit de pas — precies de faalmodus uit werkprotocol §KERNLES LI038 ("een tweede
  implementatie is de plek waar de wijziging niet landt").

Geen andere handgebouwde tabrijen gevonden. De overige `aria-selected`-treffers
(`ZoekSelect.vue:272`/`:296`, `LandschapskaartView.vue:3394`) zijn listbox-/lijstselectie, geen tabs.

---

## Blok 3 — De huidige ingang naar "Open punten"

### 3.1 Hoe kopknop en tabrij samenhangen

**Eén variabele, niet twee.** `activeTop` (`ComponentDetail.vue:251`) bestuurt élk paneel via
`v-show`; de kopknop zet diezelfde variabele (`:400`):

```html
<Button severity="secondary" data-testid="open-punten-knop" @click="activeTop = 'open-punten'">
```

en het paneel leest hem (`:571`): `v-show="activeTop === 'open-punten'"`.

**Kan er een staat bestaan waarin zowel een tabblad als het open-punten-paneel actief is? Nee.**
Alle panelen hangen aan een gelijkheidsvergelijking op dezelfde `ref`; die kan maar één waarde
dragen. De architectuur is dus al één-plek-tegelijk — er is **geen tweede vlag om op te ruimen**.
De wijziging is daarmee kleiner dan hij oogt: `'open-punten'` moet als sleutel in `topTabs` komen
en uit `PLEKKEN_ZONDER_TAB` verdwijnen.

### 3.2 Het aantal — één laadpunt, en dat blijft zo

**Bevestigd.** `ComponentDetail.vue:141`:

```js
openPunten.value = await api.componentNormen.openPunten(props.id)
```

Dat is de **enige** aanroep in de repo (geverifieerd repo-breed). Daaruit komen beide:

- de teller: `moetNog = computed(() => openPunten.value?.moet_nog?.aantal ?? 0)` (`:76`), gebruikt
  op de knop (`:404`, `:407`);
- de lijst: als prop doorgegeven (`:577`), en `OpenPuntenSectie` laadt bewust niet zelf
  (`OpenPuntenSectie.vue:19-22`, met de LI047-motivering er letterlijk bij).

**Wat gebeurt er als de teller in een tablabel moet?** `topTabs` is een `computed` in **hetzelfde
bestand** (`:221-250`) en heeft dus rechtstreeks toegang tot `moetNog`. Een label
`` `Open punten (${moetNog.value})` `` leest **dezelfde ref**; er ontstaat **geen tweede aanroep**.
Het `computed` wordt reactief op `openPunten` — dat is winst, geen risico.

⚠ Wel een gevolg om te kennen: `topTabs` wordt daarmee afhankelijk van `openPunten`, dus de
`watch(topTabs, …)` (`:255`) vuurt voortaan óók wanneer alleen het aantal wijzigt. Die watch is
idempotent (hij zet alleen terug bij een ongeldige `activeTop`), dus onschadelijk — maar het hoort
in de bouwslice bewust nagelopen te worden, niet aangenomen.

### 3.3 De regel "bij nul geen getal"

**Vindplaats:** `ComponentDetail.vue:403-407` — een `v-if="moetNog"` op de badge-`<span>`, met de
motivering in de comment op `:393-396` (*"Nul draagt geen getal — rust is het signaal dat het schoon
is"*). De regel staat óók in `likara-ux:108-114`.

**Erft een tablabel hem automatisch? Nee.** De regel zit vast aan de **knopvorm**: hij is
uitgedrukt als een `v-if` op een apart DOM-element binnen de `<Button>`-slot. Een tablabel is een
platte string in het `topTabs`-`computed` (`{ key, label }`), gerenderd als `{{ t.label }}`
(`AppTabs.vue:81`). De nul-onderdrukking moet dus **opnieuw uitgedrukt** worden, in de
labelsamenstelling.

Er is **geen gedeelde bouwsteen** voor deze regel — het is een tekstregel in de skill plus één
`v-if` in één bestand. Dat is precies de KERNLES-LI038-situatie: bij een tweede drager loopt hij uit
de pas. En dat gebeurt hier al: **`OpenPuntenSectie.vue:41-43` doet het omgekeerde** en toont wél
"(0)" in zijn tablabels:

```js
BLOKKEN.map((b) => ({ key: b.key, label: `${b.label} (${props.data?.[b.key]?.aantal ?? 0})` }))
```

met eigen motivering (`:8-13`, `:40`). Twee regels, straks één vorm → open vraag 3.

### 3.4 Diep linken

**Ja, `?tab=open-punten` werkt vandaag al** — in beide richtingen:

- **lezen:** `_initVanafQuery` (`:273-275`) accepteert `open-punten` via `isGeldigePlek`, dat
  `PLEKKEN_ZONDER_TAB` expliciet meeneemt;
- **schrijven:** de terugschrijf-watch (`:322-329`) zet `query.tab = activeTop.value` voor elke
  waarde ≠ `'overzicht'` — dus zodra de gebruiker op de knop klikt, verschijnt `?tab=open-punten` in
  de URL. De landing is nu al deelbaar en overleeft F5.

**De aanleidingen die naar dit scherm kunnen sturen** (`frontend/src/detailIngang.js:30`):

```js
const AANLEIDING_SLEUTELS = new Set(['tab', 'cat', 'markeer', 'bewerk', 'veld'])
```

met `VELD_ANKERS = ['eigenaar', 'biv', 'levensfase', 'bedoeling', 'beschrijving']` (`:35`). Een
onbekende sleutel of een onbekend veld-anker is een **luide fout** (`:47`, `:52`).

**Wat er blijft werken als Open punten een tabblad wordt:** `?tab=open-punten` verandert van
"geldige plek zónder tabblad" naar "gewoon tabblad" — dezelfde URL, hetzelfde gedrag, maar dan via
het normale pad. `PLEKKEN_ZONDER_TAB` en de watch-uitzondering worden daarmee **dode code**.

**Wat aandacht vraagt:** de binnenkomstpoort `_binnenkomstVerwerkt` (`:319`, `:323`) — de
LI046-invariant "de bezoeker wint van het scherm". Die blijft nodig en ongewijzigd, maar de
bouwslice moet hem aantoonbaar niet breken (bestaande borging: `tests/detailIngang.flow.test.js`).

**Niet vastgesteld:** of er buiten `ComponentDetail` een producent is die actief
`{ tab: 'open-punten' }` aan `detailRoute` meegeeft. Repo-breed komt de literal `'open-punten'`
alleen in de twee genoemde views voor; het open-punten-overzicht zélf levert routes van soort `tab`
of `veld` vanaf de **backend** (`gaNaarPunt`, `:298-310`), en welke `tab`-waarden de backend
teruggeeft is in deze read-only ronde niet uitgeput.

### 3.5 Dwingt `DetailKop.vue` af welke knoppen in de kop horen?

**Ja, maar Open punten valt er niet onder.** De detailkop-bron-scan
(`frontend/scripts/check-css-build.mjs:234-276`) bewaakt exact drie naalden (`:262`):

```js
const OBJECT_ACTIES = ['<ObjectHistoriePaneel', 'label="Bewerken"', 'label="Verwijderen"']
```

De Open punten-knop gebruikt géén `label`-attribuut maar een slot met `<span>`-inhoud
(`ComponentDetail.vue:397-408`) — hij matcht dus geen enkele naald.

**Wat zegt de scan als de knop verdwijnt? Niets.** Hij blijft groen; er is geen regel die eist dat
Open punten in de kop staat, en geen regel die het verbiedt. `DetailKop.vue` zelf (58 regels) is een
pure slot-bouwsteen zonder kennis van individuele knoppen.

⚠ De scan eist wél dat `<DetailKop>` bestaat en dat de drie object-acties **binnen** het blok staan
(`:248-252`). Dat blijft na het verwijderen van de Open punten-knop ongewijzigd waar.

---

## Blok 4 — De paginakleur en het inhoudsvlak

### 4.1 De twee tokens

`frontend/src/themes/base.css:43-45`:

```css
--lk-color-surface: #ffffff;
--lk-color-bg:      #f7fafc;
--lk-color-border:  #e2e8f0;
```

**Paginaondergrond** — `--lk-color-bg`, toegepast op `body` (`main.css:13`) en op de twee
layout-wortels: `AppLayout.vue:59` en `BeheerLayout.vue:24` (`min-h-screen … bg-[var(--lk-color-bg)]`).

**Het witte vlak** — `--lk-color-surface`, gedragen door `.card` (`main.css:35-41`):

```css
.card { background: var(--lk-color-surface); border-radius: var(--lk-border-radius);
        padding: 1.5rem; margin-bottom: 1rem; box-shadow: var(--lk-shadow-sm); }
```

⚠ **`.card` heeft nu géén `border`** — alleen `--lk-shadow-sm` (`0 1px 2px rgba(0,0,0,0.05)`). De
voorgestelde "haarlijn op het inhoudsvlak" is dus een **toevoeging** aan de gedeelde bouwsteen, geen
aanpassing van een bestaande waarde. Dat is één plek, en alle kaarten erven hem — goed nieuws voor
de reikwijdte.

⚠ **Losse bevinding (buiten scope, niet gerepareerd):** de zebra-striping in `main.css:31-32` zet
even rijen op `var(--lk-color-surface, #f9fafb)` en oneven op `white`. Sinds `--lk-color-surface`
`#ffffff` is, zijn beide wit — de striping is stilzwijgend dood. Genoteerd als bevinding.

### 4.2 Leeft de paginakleur op één plek?

**Vier plekken zetten `--lk-color-bg`, en alle vier lezen het token** — geen enkele hardcodeert de
waarde:

| Vindplaats | Rol |
|---|---|
| `main.css:13` (`body`) | de basis |
| `AppLayout.vue:59` | tenant-shell |
| `BeheerLayout.vue:24` | platform-shell |
| `LoginView.vue:47` | inlogscherm |
| `KaartBeginscherm.vue:180` | actiebalk van het startpaneel (bewust "pagina-achtig") |
| `LandschapskaartView.vue:2827` | fullscreen-kaart |
| `LandschapskaartView.vue:3428` | opake beginscherm-overlay op het canvas |

**Conclusie: het is één token, netjes geërfd.** Er is geen scherm gevonden dat zijn eigen
paginakleur hardcodeert. Een tintwijziging in `base.css` beweegt alles mee — inclusief de drie
kaartplekken, wat gewenst is (ze zijn juist bedoeld als "pagina").

Ter contrast: `bg-white` komt **32×** voor in views. Dat zijn vlakken, geen ondergronden; ze
beweegen bewust niet mee. Of ze alle 32 terecht `bg-white` zijn in plaats van
`bg-[var(--lk-color-surface)]` is **niet vastgesteld** — het is dezelfde waarde, dus vandaag
onzichtbaar, maar het is wel een tweede uitdrukking van hetzelfde feit.

### 4.3 Wat tekent op een eigen ondergrond? — het canvas-risico bestaat niet

**Het Cytoscape-canvas staat op wit, niet op de paginakleur.** De canvaskolom
(`LandschapskaartView.vue:3125`):

```html
<div class="relative min-h-0 min-w-0 flex-1 bg-[var(--lk-color-surface)]">
```

en de container zelf (`:3140`) draagt géén achtergrond — hij is transparant en erft dat wit. Er is
in de hele `CY_STYLE` geen `background-color` op canvasniveau (alleen op nodes/edges, `:2527`,
`:2576`).

**Gevolg:** een diepere paginakleur geeft **geen naad** bij de kaart; het canvas blijft een wit
werkvlak op een dan duidelijker afgetekende ondergrond. Dat is precies het beoogde effect.

**Tokenresolutie op tekenmoment** gebeurt op één plek, en volgens het LI043-patroon:
`modules/…/frontend/standCodering.js:110`:

```js
v = getComputedStyle(document.documentElement).getPropertyValue(c.token).trim()
```

Dat betreft de plek-stand-kleuren, niet de achtergrond — dus er is niets dat een verouderde
pagina-hex meedraagt.

**Overlays:** `:3428` (beginscherm-overlay, opaak `--lk-color-bg`) en `:2827` (fullscreen) lezen het
token en bewegen dus mee. De laag-banden (`:3135`) gebruiken `b.bg` met `opacity: 0.5` — die
mengen met het **witte** canvas, niet met de pagina, dus ongewijzigd.

### 4.4 Contrastmeting — met een hard plafond

Berekend op de tokenwaarden uit `base.css` (WCAG relatieve luminantie). `--lk-color-text-muted` is
`rgba(45, 55, 72, 0.7)` — een **alpha**-kleur, dus samengesteld tegen de achterliggende ondergrond
vóór meting.

**Huidige stand:**

| Paar | Ratio | Oordeel |
|---|---|---|
| wit vlak vs. pagina (`#ffffff` ↔ `#f7fafc`) | **1,048:1** | praktisch onzichtbaar — bevestigt de klacht |
| gedempte tekst op de **pagina** | **4,637:1** | AA gehaald, marge **0,14** |
| gedempte tekst op het **witte vlak** | 4,777:1 | AA gehaald |
| gewone tekst (`#1A1A2E`) op de pagina | 16,27:1 | ruim |
| rand (`#e2e8f0`) op wit | 1,233:1 | zichtbaar genoeg voor een haarlijn |

**Wat gebeurt er bij een diepere pagina:**

| Kandidaat | wit vs. pagina | **gedempte tekst op pagina** | AA (≥4,5) |
|---|---|---|---|
| `#f7fafc` (huidig) | 1,048 | 4,637 | ✅ |
| `#f1f5f9` | 1,096 | 4,561 | ✅ marge 0,06 |
| `#eef2f7` | 1,124 | **4,510** | ✅ **op de rand** |
| `#e9eef5` | 1,166 | 4,421 | ❌ **gezakt** |
| `#e2e8f0` (= randtoken) | 1,233 | 4,305 | ❌ |

**De harde conclusie: `#eef2f7` is de laatste stap die AA haalt op gedempte tekst.** "Eén tint
dieper" kan; twee kan niet zonder óók `--lk-color-text-muted` te verdiepen. Alles boven `#e9eef5`
zakt door de ondergrens.

**Zit er dan gedempte tekst op de pagina-ondergrond?** Ja — op `ComponentDetail` alleen al twee
gevallen buiten elke `.card`:

- `:374` — de terugknop (`terug-knop`, `text-[var(--lk-color-text-muted)]`);
- `:440` — de voortgangsregel (`detail-voortgang`).

Repo-breed staat `--lk-color-text-muted` **388× in 62 bestanden**. Hoeveel daarvan op de
paginaondergrond staat in plaats van in een kaart is **niet vastgesteld** — dat vergt een
per-geval-analyse die buiten deze read-only ronde valt. Voor de besluitvorming volstaat dat het
**aantoonbaar voorkomt**, dus de ondergrens telt.

⚠ **Belangrijk voor de weging:** de twee doelen trekken tegen elkaar in. Het gewenste effect
(werkgebied uit de ondergrond) schaalt met de diepte; de leesbaarheid van gedempte tekst schaalt
er omgekeerd mee. De **haarlijn op `.card`** (4.1) levert scheiding **zonder** die kosten — 1,23:1
rand op wit is scherper dan welke van deze tintstappen dan ook. Dat maakt de haarlijn mogelijk de
zwaardere helft van de oplossing en de tintstap de lichtere. Beslissing bij Bert (open vraag 4).

### 4.5 Welke borgingen raken dit?

**`frontend/scripts/check-css-build.mjs` — vier scans plus een klassenlijst:**

| Onderdeel | Wat het toetst | Valt het om? |
|---|---|---|
| `VEREIST`-lijst (`:33-58`, 15 klassen) | kritische klassen in de **gebouwde** CSS | **ja, drie stuks** — zie hieronder |
| token-verwijzingscheck (`:99-117`) | élke fallback-loze `var(--lk-…)` bestaat in `base.css`/`main.css` | nee, mits nieuwe tokens gedefinieerd worden |
| veld-bron-scan (`:119-232`) + zelftest | elk `<input/select/textarea>` op `.lk-veld` | nee — tabbladen zijn `<button>` |
| detailkop-bron-scan (`:234-343`) + zelftest | `<DetailKop>` aanwezig; object-acties binnen de kop | nee — zie 3.5 |
| kopstijl-bron-scan (`:345-…`) | geen eigen maat/gewicht op `h1`/`h2` | nee |

**De drie die omvallen** — en dat is de bedoeling, want het zijn precies de vormklassen:

| Naam | Match (`:34-36`) | Enige drager |
|---|---|---|
| `tab-hover-bg` | `hover:bg-[var(--lk-color-primary-50)]:hover` | `AppTabs.vue:76` |
| `tab-hover-text` | `hover:text-[var(--lk-color-primary-700)]:hover` | `AppTabs.vue:76` |
| `tab-omlijning` | `border-[0.5px]` | `AppTabs.vue:75`, `:76` |

Geverifieerd: **`AppTabs.vue` is de enige plek in de repo** waar deze drie klassen voorkomen.
Verandert de tabvorm (geen omlijning meer, andere hover), dan verdwijnen ze uit de build-CSS en
**faalt `npm run test:css-build` luid**. Dat is correct gedrag; de lijst moet in dezelfde slice
meebewegen naar de nieuwe vormklassen — anders verliezen we de borging in plaats van hem te
verplaatsen.

**`frontend/tests/interactiestates.test.js` (laag B)** — de test *"niet-gekozen tab: omlijning +
hover-klassen op de tab-button zelf"* asserteert letterlijk `border-[0.5px]`,
`border-[var(--lk-color-border)]`, `hover:bg-[var(--lk-color-primary-50)]` en
`hover:text-[var(--lk-color-primary-700)]`. **Valt om.** De test *"gekozen tab: donkerblauwe
token-vulling + witte tekst"* blijft staan zolang de gekozen tab die vulling houdt.

⚠ **De-vervuilingsregel geldt onverkort** (`interactiestates.test.js:19-26` en
`check-css-build.mjs:28-32`): nieuwe module-unieke klassetokens moeten in beide bestanden uit
**fragmenten** worden opgebouwd (`j('border-[0.5px', ']')`), anders seedt Tailwind ze zelf en wordt
de build-check vals-groen.

**`frontend/tests/tokens.contract.test.js` (laag A)** — toetst 11 tokens (`:17-31`). **Valt niet
om**, maar draagt een **gat**: `--lk-color-bg`, `--lk-color-surface` en `--lk-color-accent` staan er
**niet** in. Juist de twee tokens die deze sessie de kern van de wijziging vormen, zijn niet
gecontracteerd. Voorstel: in de bouwslice toevoegen (goedkoop, één regel per token).

**`frontend/tests/ComponentDetail.test.js`** — 10 treffers op `open-punten-knop` /
`open-punten-teller` / `panel-open-punten`. Dit is het enige testbestand dat de kopknop kent en het
enige dat `detailtabs-tab`/`checklisttabs-tab` gebruikt. Het beweegt dus volledig mee met snede 1.

**Suite-omvang ter oriëntatie:** 91 testbestanden onder `frontend/tests/`.

---

## Blok 5 — Wat de skills hierover al beweren

### 5.1 De passage die herzien wordt

`likara-frontend/SKILL.md:177-179`:

> **Tabbladen** (`AppTabs.vue`) volgen dezelfde kleurtaal én hoogte (`h-10`, `--lk-radius-btn`):
> omlijnd = beschikbaar, lichtblauw (`--lk-color-primary-50/700`) = hover, donkerblauw
> (`--lk-color-primary`, wit, semibold) = gekozen.

En `:184-185` (§UI-interactiestates, "niet-onderhandelbaar"):

> Hover/focus/selected lopen uitsluitend via `--lk-`-tokens en de centrale componenten
> (`presets/Button.js`, `AppTabs.vue`). Geen losse kleuren of state-klassen op call-sites.

**Wordt de regel nageleefd?** In `AppTabs.vue`: **volledig** — `h-10`, `--lk-radius-btn`, en de drie
staten exact zoals beschreven (`:72-77`). Eén drager, één plek, precies nageleefd.

**Wordt hij ergens geschonden? Ja, op één plek:** `SignaleringView.vue:98` (en `:104`, `:111`) —
zelfde `h-10`, maar `rounded-t-[var(--lk-radius-btn)]` in plaats van de volle radius, hover op
`--lk-color-accent` in plaats van `--lk-color-primary-50/700`, en géén omlijning. Dat is drie van de
vier beschreven eigenschappen anders.

**Duiding (KERNLES LI038):** de regel houdt in de bouwsteen en houdt níét op de plek die de
bouwsteen omzeilt — het klassieke "een regel in tekst is een claim, geen borging". Pikant detail:
de afwijkende plek doet toevallig al ongeveer wat de nieuwe richting voorstelt (bovenhoeken +
onderrand op de container). Dat is **geen bewijs dat de vorm klopt**, maar het is wel het enige
levende voorbeeld ervan in de codebase.

**Waarom de scan dit niet ving:** `VEREIST` toetst of de klassen **ergens** in de build-CSS staan,
niet of élke tabrij ze draagt. Eén nalevende drager houdt de check groen. Een dekkingsscan
("elke `role="tab"` loopt via `AppTabs`") bestaat niet — dat is de structurele borging die hier
ontbreekt (voorstel: snede 4).

### 5.2 Andere passages die onwaar (zouden) worden

| Vindplaats | Passage | Status |
|---|---|---|
| `likara-frontend:519` | *"**2-laags tabs + deep-link** (ApplicatieDetail, CD022)"* | **nu al onwaar** — `ApplicatieDetail.vue` bestaat niet; de opzet leeft in `ComponentDetail.vue` (kernbevinding 1) |
| `likara-frontend:177-179` | de tabvorm-passage | wordt onwaar bij snede 2 |
| `likara-frontend:198` | *"AppTabs (states op de juiste — klikbare — `role="tab"`, juiste token-klassen)"* | blijft waar; alleen de klassenamen wijzigen |
| `likara-frontend:511-518` | de `AppTabs`-props/a11y-beschrijving | blijft waar (1.3) |
| `likara-ux:108-114` | *"een lijst legt uit, een teller zwijgt"* met `ComponentDetail`-knop als referentie | de **referentie** wordt onwaar zodra de knop verdwijnt; de regel zelf blijft (zie open vraag 3) |
| `likara-frontend:1529` | veld-anker markeert met `--lk-color-accent` | blijft waar — **en bevestigt de premisse**: `veldKlas` (`ComponentDetail.vue:346-347`) gebruikt `bg-[var(--lk-color-accent)]`, dus een getinte tabpaneel-achtergrond zou met dát kanaal botsen |

Geen enkele skillpassage claimt iets over de **paginakleur** — `--lk-color-bg` komt in geen enkele
likara-skill voor. Dat is een ongeschreven feit; de bouwslice kan het vastleggen.

**Niets bijgewerkt** — conform opdracht alleen benoemd.

---

## Openstaande vragen voor Bert

**1. Wordt het LI047-besluit herroepen, of verplaatst?**
De keuze "Open punten is géén tabblad" is beredeneerd vastgelegd (`ComponentDetail.vue:212-217`):
het toont geen ónderdeel van het component maar een werkvoorraad, én de tabrij was al elf breed en
liep over twee regels.
- *Herroepen* (Open punten wordt tabblad 2): lost de klacht in de kern op — geen tabrij zonder
  selectie meer, a11y-fout weg, één ingang. Kosten: de rij wordt **twaalf** breed en loopt zeker
  over twee regels; en de semantische scheiding "onderdeel vs. werkvoorraad" verdwijnt.
- *Vasthouden aan de scheiding* en alleen de knop een actieve staat geven: raakt de tabrij niet,
  maar laat de "inhoud die bij niets hoort"-klacht **en de a11y-fout** bestaan.
- *Derde weg (niet in de opdracht, wel mogelijk):* de rij smaller maken door tabbladen te bundelen,
  zodat de twaalfde past. Dat is een eigen ontwerpvraag.

**2. Wordt "niveau 2 ondergeschikt" een eigenschap van de bouwsteen of van de aanroepplek?**
Er zijn twee niveau-2-rijen met verschillende geometrie (2.2).
- *In de bouwsteen* (bv. een `niveau`-prop): één plek, elke toekomstige sub-rij erft het. Maar het
  raakt óók de **verticale** checklist-rij, waar geen klacht ligt en waar "kleiner en gedempt" een
  ongevraagde wijziging is.
- *Op de aanroepplek*: alleen `OpenPuntenSectie` verandert. Maar dan leeft de niveau-2-vorm in een
  call-site — precies wat `likara-frontend:184-185` verbiedt, en de volgende sub-rij erft niets.

**3. Bij nul: zwijgt de teller, of niet?**
De twee bestaande regels spreken elkaar tegen zodra beide dezelfde vorm dragen (3.3): de kopknop
onderdrukt "0", de sub-tabbladen tonen het.
- *Zwijgen (`Open punten`)*: consistent met `likara-ux:112` (*"de rust ís het signaal"*), maar dan
  verschilt het van de sub-tabbladen er direct onder — dezelfde vorm, ander gedrag, één scherm.
- *Altijd tonen (`Open punten (0)`)*: consistent binnen het scherm, maar breekt de ux-regel en zet
  een aandachttrekker neer voor niets.
- *Onderscheid vastleggen* ("niveau 1 zwijgt, niveau 2 telt altijd"): verdedigbaar, maar dat is een
  **nieuwe regel** die dan expliciet in `likara-ux` hoort — niet stilzwijgend.

**4. Hoe diep gaat de pagina, en draagt de haarlijn of de tint het gewicht?**
De meting geeft een hard plafond: `#eef2f7` = 4,51:1 op gedempte tekst, `#e9eef5` = gezakt (4.4).
- *`#f1f5f9`* (marge 0,06): merkbaar dieper, veilig binnen AA.
- *`#eef2f7`* (marge 0,01): het maximum. Elke latere verdieping van `--lk-color-text-muted` of van
  de pagina zakt er doorheen — een randstand die een volgende sessie kan breken zonder het te merken.
- *Alleen de haarlijn, tint ongewijzigd*: 1,23:1 rand op wit is scherper dan elke tintstap en kost
  **niets** aan leesbaarheid. Mogelijk voldoende op zichzelf.
- *Beide, maar `--lk-color-text-muted` mee verdiepen*: geeft ruimte, maar raakt **388 vindplaatsen
  in 62 bestanden** in één klap — dat is een eigen slice met een eigen browsercheck, geen bijvangst.

**5. Wordt de tweede tabrij (`SignaleringView`) meegenomen?**
- *Meenemen (converge naar `AppTabs`)*: één vorm, en het scherm krijgt de ontbrekende a11y-laag
  (`aria-controls`, roving `tabindex`, pijltjesnavigatie) gratis. Kosten: een extra scherm in de
  browsercheck.
- *Laten staan*: kleinere slice, maar het scherm blijft achter met de oude vorm én zonder
  toetsenbordnavigatie — en de volgende sessie treft twee tabvormen aan.

---

## Voorgestelde sneden

Alleen een voorstel; volgorde en knip zijn aan Bert.

| # | Snede | Wat de gebruiker erna ziet | Suites | Gate? |
|---|---|---|---|---|
| **1** | **Open punten wordt tabblad 2**; kopknop weg; `PLEKKEN_ZONDER_TAB` + watch-uitzondering verwijderd; paneel krijgt `role="tabpanel"` + `aria-labelledby="detailtabs-tab-open-punten"` | Klikken op het tabblad licht het tabblad op; de tabrij is weer met het toetsenbord bereikbaar; `?tab=open-punten` blijft werken | `ComponentDetail.test.js`, `detailIngang.flow.test.js` | **Ja** — herroept een LI047-besluit en raakt de a11y-semantiek |
| **2** | **Tabvorm niveau 1**: geen omkadering per tabblad, tab vastgeklonken aan het vlak eronder; `VEREIST`-lijst en `interactiestates.test.js` meeverhuisd naar de nieuwe vormklassen | De tabrij leest als tabrij, niet als knoppenrij | `interactiestates.test.js`, `test:css-build`, `vite build` | **Ja** — vormbesluit + herziening van `likara-frontend:177` |
| **3** | **Tabniveau 2 ondergeschikt** (afhankelijk van open vraag 2: bouwsteen-prop óf call-site) | Binnen Open punten zijn de drie blokken zichtbaar een laag lager | `interactiestates.test.js`, `ComponentDetail.test.js` | Nee, mits vraag 2 beslist |
| **4** | **`SignaleringView` converge naar `AppTabs`** (afhankelijk van open vraag 5) + een **dekkingsscan** "elke `role="tab"` loopt via `AppTabs`", met zelftest | Signalering-tabbladen zien er hetzelfde uit en werken met het toetsenbord | `test:css-build` (nieuwe scan + zelftest), `SignaleringView`-tests | Nee |
| **5** | **Paginakleur + haarlijn**: `--lk-color-bg` één stap dieper en/of `border` op `.card`; `--lk-color-bg`/`--lk-color-surface` toevoegen aan `tokens.contract.test.js` | Het werkgebied komt zichtbaar uit de ondergrond, platform-breed | `tokens.contract.test.js`, `test:css-build`, `vite build` | **Ja** — raakt élk scherm; contrastplafond uit 4.4 is de randvoorwaarde |

**Browsercheck is bij snede 1, 2, 3 en 5 het sluitpunt, niet de suite** (werkprotocol §Browsercheck
vóór commit): dit is uitsluitend UI-/vormwerk, en de suite bewijst geen rendering. Snede 5 vraagt
expliciet om verificatie van gedempte tekst op de nieuwe ondergrond op minstens één scherm mét
`text-muted` buiten een kaart (`ComponentDetail`, terugknop + voortgangsregel).

Snede 1 en 2 raken **hetzelfde bestand** (`ComponentDetail.vue` resp. `AppTabs.vue` — feitelijk
disjunct, maar `ComponentDetail.test.js` beweegt bij beide). Bij samen bouwen geldt de
werkprotocol-regel over stapelen in één werktree; los committen heeft de voorkeur.

⚠ **Sneden 1 en 3 ontsluiten samen één beeld** (werkprotocol §LI047: *"sneden die dezelfde functie
ontsluiten, beoordeel je op één beeld"*) — precies de val die in LI047 toesloeg met dit exacte
scherm. Plan één gezamenlijk beoordelingsmoment waarop tabblad én sub-blokken tegelijk in beeld staan.

---

## Reikwijdte in één regel

**Code:** 2 views met `AppTabs` (3 aanroepen) · 1 handgebouwde tabrij · 1 bouwsteen · 2 CSS-bronnen
(`base.css`, `main.css`) — **circa 6 bestanden** voor sneden 1-3+5, plus 2 bij snede 4.
**Schermen:** 1 (Componentdetail) voor sneden 1-3; 1 extra (Signalering) bij snede 4; **alle
schermen** bij snede 5.
**Suites:** `ComponentDetail.test.js`, `interactiestates.test.js`, `tokens.contract.test.js`,
`detailIngang.flow.test.js`, `npm run test:css-build`, `vite build` — geen backend-suite geraakt
(geen schema, geen endpoint, geen seed).

---

*Read-only vastgesteld op commit `3497d56`. Tellingen in dit rapport zijn momentopnamen van die
commit (werkprotocol §"een rapport is geen meting").*
