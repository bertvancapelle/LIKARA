# Feitenrapport — veldhoogtes in formulieren

| | |
|---|---|
| **Opdracht** | LI040-checkpoint-veldhoogtes (read-only inventarisatie) |
| **Datum** | 2026-07-14 |
| **Commit** | `87dc120` — werktree schoon (correctie op de opdracht-header: de "ondersteunt werk"-slice is inmiddels gecommit en gepusht; dit rapport is het enige nieuwe bestand) |
| **Modus** | Read-only; geteld met een multi-line tag-parser over alle `.vue`-bronnen (een regel-grep mist attributen op vervolgregels en telt `<select` in code-comments mee — twee van zulke vals-positieven handmatig weggefilterd) |

---

## 1. Uitkomst in één zin

**Er bestaat géén gedeelde hoogte-afspraak voor formuliervelden** — knoppen hebben er wél
één (`h-10`, preset-afgedwongen), maar de 183 invoervelden van de applicatie verdelen zich
over **vier verschillende hoogte-recepten** (±42 px · 40 px · ±34 px · ±30 px), waarvan er
drie samen in de dialoog *Nieuw component* staan — precies de gemelde rommeligheid.

---

## 2. De oorzaak in de dialoog *Nieuw component* (§2.1)

Er is geen besturingsklasse en geen hoogte-token; elk veld krijgt zijn hoogte uit zijn
eigen combinatie van padding + font-size (+ soms een expliciete `h-10`). In
`ComponentFormulier.vue` staan drie eenregelige recepten naast elkaar:

| Veld | Recept | Berekening (border-box, 1px rand) | Vindplaats |
|---|---|---|---|
| Naam | **PrimeVue `InputText`-preset**: `px-3 py-2` + `text-base` (16px×1.5=24px regel) | 24 + 2×8 + 2 = **±42 px** | `frontend/src/presets/InputText.js:7-9`; gebruik `ComponentFormulier.vue:354` |
| Componenttype / hostingmodel / rol / BIV | **Native-recept**: `px-[--lk-space-sm] py-[--lk-space-xs]` (`--lk-space-xs` = 4px, `base.css:9`) | 24 + 2×4 + 2 = **±34 px** | `ComponentFormulier.vue:368, 471, 490, 512` |
| Proces-regelvelden (functie-select + toelichting-input) | **`h-10`-recept** (het knop-recept) | **40 px** vast | `ComponentFormulier.vue:440, 447` |
| Beschrijving | **`Textarea`-preset**: `py-2` + `min-h-[5rem]` | **≥80 px** (meerregelig — legitiem hoger, zie §6) | `frontend/src/presets/Textarea.js`; gebruik `:380` |

**De ⚠-verdachte (native `<select>` op browserstandaard) is weerlegd**: geen enkel echt
veld draait op de browserstandaard (de drie kandidaten bleken comment-/parser-artefacten).
De selects hébben een recept — alleen een ánder recept dan de InputText ernaast. Het
verschil zit in de **verticale padding** (8px vs 4px) en, in filterbalken, de **font-size**
(labels dragen `text-sm`; Tailwind-preflight laat form-elementen de font erven → ±30 px
daar). Niet in de border (overal 1px) en niet in de browserstandaard.

Kanttekening: Tailwind-preflight geeft form-elementen `font: inherit`, dus de font-size
volgt de context — hetzelfde native-recept is daardoor ±34 px in een dialoog en ±30 px in
een `text-sm`-filterbalk: zelfs binnen één recept varieert de hoogte met de omgeving.

---

## 3. De telling (§2.2)

**183 invoervelden** (checkbox/radio/hidden uitgesloten) in `frontend/src` +
`modules/bwb_ontvlechting/frontend`, over **38 bestanden** (+2 presets +2 bouwstenen):

| Recept | Aantal | Hoogte (indicatief) | Waar |
|---|---|---|---|
| Native-recept (`py-[--lk-space-xs]`, `--lk-radius-input`, meest `bg-white`) | **99** | ±34 px (±30 px in text-sm-context) | vrijwel alle dialogen/secties, incl. `ZoekSelect.vue:218-233` en alle beheerschermen |
| PrimeVue-preset (`py-2`, `text-base`) | **47** (29× `<InputText`, 18× `<Textarea`) | ±42 px / ≥80 px | o.a. ComponentFormulier-naam, contract-/partij-formulieren |
| Filterbalk-recept (`py-1`, `--lk-radius-btn`) | **27** | ±30-34 px | ComponentLijst-, PartijLijst-, KaartBeginscherm-, Architectuur-, Landschapskaart-filters |
| `h-10`-recept (knophoogte, `--lk-radius-btn`) | **10** | 40 px | `ComponentFormulier.vue:440,447` · `ProcesComponentenSectie.vue:289,302,335,348` · `ComponentProcessenSectie.vue:272,285,315,328` |
| Browserstandaard (geen recept) | **0** | — | de drie ruwe treffers waren vals (2× `<select` in een code-comment: `MultiSelectDropdown.vue:5`, `KaartBeginscherm.vue:35`; 1× multi-line-tag: `ZoekSelect.vue:218` heeft zijn class op `:233`) |

**Eigen hoogte vs. geërfd: 136 van de 183 velden (74%) zetten hun recept per call-site**
(de native- + filterbalk- + h-10-recepten zijn losse class-strings per veld); alleen de 47
preset-velden erven van een gedeelde bron — en die bron wijkt zelf af van de rest.

**Uitschieters:** de 10 `h-10`-velden (proces-secties + ComponentFormulier-regelvelden)
— de enige velden op knophoogte, mét knop-radius; en de dialoog *Nieuw component* zelf,
waar drie eenregelige hoogtes (42/40/34) in één scherm staan.

---

## 4. Andere ongelijkheden uit dezelfde oorzaak (§2.3 — benoemd, niet opgelost)

1. **Twee randkleuren**: de presets gebruiken **rauw Tailwind-grijs** (`border-gray-300`,
   `InputText.js:8`) waar alle natives `--lk-color-border` dragen — tegen de
   tokens-only-regel van likara-frontend.
2. **Drie radius-varianten op velden**: `--lk-radius-input` (6px 0 6px 0, natives) ·
   `--lk-radius-btn` (8px 0 8px 0, filterbalk + h-10-velden) · `--lk-border-radius` (6px
   symmetrisch, Textarea-preset — dus het tekstvlak heeft niet eens dezelfde hoekvorm als
   het invoerveld erboven).
3. **Twee achtergronden**: `bg-white` hardcoded (natives) vs `bg-[--lk-color-surface]`
   (presets, filterbalken).
4. **Twee focus-talen**: `focus:ring-2` (presets) vs `focus:outline-2` (natives).
5. **Knop naast veld lijnt niet**: knoppen zijn overal 40 px (`Button.js:35`); een knop in
   één rij met een native veld (±34 px) staat er zichtbaar boven uit — o.a. elke
   toevoegregel met "Opslaan" naast een select.
6. **VeldUitleg-(i)-plaatsing wisselt**: soms in de labelregel
   (`ComponentConfigBeheer.vue:509-512`), soms als los element ónder het veld (`:478`).
7. Klein los feit: beide presets refereren in hun kop-comment "**ADR-047 B6**" — dat
   ADR-nummer bestaat niet (register loopt t/m ADR-045). Stale verwijzing.

---

## 5. Waar de fix zou landen (§2.4 — feitelijk, geen keuze)

**De ene plek.** Twee vormen die de codebase al kent, combineerbaar:
- een **handgeschreven besturingsklasse** (bv. `.lk-veld`) in `frontend/src/assets/main.css`
  — precedent `.lk-rij`/`.lk-rij-acties`; handgeschreven klassen kan Tailwind niet zelf
  genereren, dus de bestaande CSS-toets kan er zonder de-vervuiling op asserteren;
- en/of een **hoogte-token** (bv. `--lk-veld-h`) in `frontend/src/themes/base.css`, dat ook
  de twee presets (`InputText.js`/`Textarea.js`) en de bouwstenen (`ZoekSelect`,
  `MultiSelectDropdown`-trigger) consumeren.

Feit om te wegen: knoppen staan al vast op `h-10` (40 px) — velden die daarnaast in één
rij staan lijnen alleen bij dezelfde hoogte; welke waarde de norm wordt is knoop 1.

**Bereik**: ~**42 bestanden** — 38 views/secties met native velden + 2 presets + 2
gedeelde bouwstenen. Grotendeels mechanische vervanging van de per-veld class-strings
door de gedeelde klasse.

**Kan de bestaande CSS-toets afdwingen dat een view geen eigen hoogte meer zet?**
**Ja, mits uitgebreid.** De huidige `check-css-build.mjs` leest uitsluitend de
**dist-CSS** + de tokendefinities (`:56-62`) — hij kan borgen dat `.lk-veld` bestaat en
zijn token gedefinieerd is, maar ziet niet wát views op hun velden zetten. Een verbod
vergt een **bron-scan-stap** in hetzelfde script (node/fs is er al): alle `.vue`-bronnen
scannen op `py-*`/`h-*`-klassen binnen `<input|select|textarea>`-tags buiten de
bouwsteen-bestanden → overtreding = rode build. Twee lessen uit dit checkpoint voor die
scanner: hij moet **multi-line tags** parsen én **code-comments strippen** (beide gaven
hier vals-positieven). Daarmee wordt de regel structureel (werkprotocol-kernles: een
regel zonder bouwsteen wordt overtreden — dit checkpoint is er het bewijs van: de
knopstandaard hield stand, de veld-afspraak die nooit bestond niet).

---

## 6. Open knopen voor Bert

1. **De normhoogte voor eenregelige velden.** Feitelijke kandidaten: 40 px (= de
   bestaande knopstandaard `h-10` — knoppen en velden lijnen dan overal) · ±42 px (de
   huidige preset-hoogte) · een andere waarde. Raakt ook de filterbalken (nu bewust
   compacter, ±30 px): één hoogte overal, of een aparte — dan wel gedeelde — compacte
   variant voor filterbalken.
2. **De bouwsteen-vorm**: handgeschreven `.lk-veld`-klasse · hoogte-token door presets +
   utilities · beide. (De klasse-vorm dekt ook natives in één woord; de token-vorm laat
   de presets meedoen.)
3. **Scope van de reparatie**: alleen hoogte, of in dezelfde pass ook de
   zelfde-oorzaak-schade uit §4 (randkleur, radius, achtergrond, focus-stijl) — het zijn
   dezelfde ~42 bestanden; apart repareren opent ze twee keer.
4. **De textarea-uitzondering formeel**: *gelijke hoogte geldt voor eenregelige
   besturingen*; een tekstvlak is meerregelig en krijgt een eigen, consistente
   min-hoogte (nu `min-h-[5rem]`) — maar deelt verder het veld-uiterlijk (rand, radius,
   padding, focus). Vast te leggen als onderdeel van de norm.
5. **Handhaving**: de CSS-toets uitbreiden met de bron-scan (§5) — ja/nee.
6. **De filterbalk-`MultiSelectDropdown`-trigger en `ZoekSelect`** meenemen als
   bouwsteen-consumenten (zij zijn de gedeelde velden die het nieuwe recept gratis
   doorgeven aan al hun gebruikers).

---

## 7. Wat ik NIET heb kunnen vaststellen

- **Exacte gerenderde pixelhoogtes**: berekend uit padding/font/line-height (incl.
  Tailwind-preflight `font: inherit`), niet in de browser gemeten — geen
  browser-automatisering opgezet (buiten scope per opdracht). De verhoudingen (drie
  verschillende eenregelige hoogtes in één dialoog) staan vast uit de code; de exacte
  px-waarden kunnen ±1-2 px afwijken per platform/font.
- **Of parent-CSS ergens extra hoogte-invloed heeft** (bv. een `line-height` op een
  omliggende container) — niet uitputtend nagelopen; de vier recepten verklaren de
  waarneming al volledig.
- **De herkomst van de "ADR-047 B6"-verwijzing** in de presets (bestaat niet in het
  register) — mogelijk een nummer uit een oudere planning; alleen gesignaleerd.
