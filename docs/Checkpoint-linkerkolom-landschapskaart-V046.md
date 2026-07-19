# Checkpoint — de linkerkolom van de Landschapskaart: wat staat er, en wat kan het doen?

| | |
|---|---|
| **Sessie** | LI046 · V046 · read-only feitenopname vóór ontwerp |
| **Datum** | 2026-07-19 |
| **Herkomst** | opvolgpunt 2× doorgeschoven (LI034 punt 3 · LI035 punt 5) |
| **Modus** | Niets gewijzigd behalve dit bestand; niets gebouwd; niet gecommit |

**Uitkomst in één zin:** de linkerkolom (`<aside data-testid="lk-links">`, `LandschapskaartView.vue:2853`,
**zonder `v-if`**) staat **altijd** — óók op de lege kaart — en mengt daar twee soorten dingen die niet
door elkaar horen: een handvol **vertrekpunten** (opgeslagen views) náást een reeks **kijkinstellingen**
(6 filters + drempels + ringen) die op een lege kaart **niets kunnen doen** omdat er nog geen getekende
verzameling is; het startpaneel rechts maakt die vertrekpunt/kijk-scheiding al wél (het draagt een eigen
"+ Filters" met Laag/Hosting/Eigenaar die de server-side set opbouwen), waardoor de linkerkolom deels
dubbelt en deels een lege belofte toont.

> Alle vindplaatsen: `modules/bwb_ontvlechting/frontend/views/LandschapskaartView.vue` (**LKV**),
> `.../KaartBeginscherm.vue` (**KB**), `frontend/src/api.js`.

---

## Blok 1 — De volledige inventaris van de linkerkolom

De kolom is een flex-`<aside class="w-60 flex-shrink-0 …">` (LKV:2853) naast het `flex-1`-canvas
(LKV:3081) en de rechter-`w-56`-aside (LKV:3398). **Geen `v-if` op de aside** → altijd meegerenderd zodra
de kaartlayout toont. De beginscherm-overlay (`KaartBeginscherm`) staat `absolute inset-0 z-20` **binnen
het canvas** (LKV:3361-3373), niet over de kolom — dus de kolom staat zichtbaar **naast** het open
beginscherm.

| # | Element (testid) | Wat het is (gebruikerstaal) | Waarop het werkt (bron) | Zichtbaar op de LEGE kaart? | Oordeel |
|---|---|---|---|---|---|
| A | Standaardkijk-blok (`lk-standaardkijk`, 2856-2876) | "★ Sla op als mijn standaardkijk" + status + "Herroep" | slaat de **kijk-config** op (`_huidigeKijk` 506-511: ringen/filters/diepte/groepeer), **niet** de momentkeuze | **ja** (geen `v-if`) | **kijkinstelling (meta)** |
| B | Opgeslagen views (`lk-views`, 2880-2892) | lijst met open + (eigenaar) bewerken/verwijderen | `opgeslagenViews` (958) → `openView` zet een bewaarde `actieveSet` | alleen `v-if="opgeslagenViews.length"` | **vertrekpunt** |
| C | Vrij zoekveld (`lk-zoek`, 2894) | "🔍 Zoek naam/domein/leverancier…" | `zoekterm` (141) → `_matcht` (636) → `gefilterdeNodes` (641); **niet** het graafpad (`filterActief` sluit zoekterm uit, 584-600) | **ja** | **allebei/onduidelijk** |
| D | Kaart-zoekresultaten (`lk-kaartzoek`, 2898-2936) | teller + tweede zoekveld + resultatenlijst + "Voeg alle toe" | `gefilterdeNodes`; toevoeg-ingang (`kiesComponent`/`toggleSet`/`voegAlleGefilterdeToe`) | **nee** — `v-if="!beginschermOpen && (zoekterm||filterActief)"` (2899) | **vertrekpunt (na openen)** |
| E | Type-filter (2938-2949) | multi-select componenttype | `filterTypes` (142) → `_nodeVoldoet` (613) → graafpad | **ja** | **kijkinstelling** |
| F | Leverancier-filter (2950-2961) | doorzoekbare leverancier-pick | `filterLeveranciers` (143); **server-side** `api.partijen.lijst({aard:'externe_partij'})` (447) | **ja** | **kijkinstelling** |
| G | Hosting-filter (2962-2974) | multi-select hostingmodel | `filterHosting` (144), client-side lijst | **ja** | **kijkinstelling** |
| H | Beoordelingsstatus-filter (2975-2987) | multi-select lifecycle | `filterLifecycle` (145), vaste `LIFECYCLE_OPTIES` (44) | **ja** | **kijkinstelling** |
| I | Rol-filter (2988-2999) | multi-select componentrol | `filterRollen` (471); alleen op nodes mét `componentrol` (620-621) | **ja** | **kijkinstelling** |
| J | BIV-drempels ×3 (3000-3015) | Beschikbaarheid/Integriteit/Vertrouwelijkheid ≥ | `filterBivB/I/V` (472-474), ordinale drempel (zie Blok 5) | **ja** | **kijkinstelling** |
| K | Afpel-modus (`lk-afpel-toggle`, 3017-3019) | insluiten↔afpellen | `opbouwModus` (214) | **nee** — `v-if="modus==='geheel'"` | **kijkinstelling** |
| L | Diepte-toggle (`lk-diepte`, 3021-3028) | 1 stap / 2 stappen | `diepte` (219); **roept `herlaadGraaf`** (381) → dataload | **nee** — `v-if="modus==='ego'||'geheel'"` | **kijkinstelling (met dataload)** |
| M | Ringen-checkboxes (3032-3041) + "Groepeer per organisatie" (3038) | tien ring-toggles | `ringAan` (147); `groepeerPerOrg` (242-281) | **ja** | **kijkinstelling** |
| N | Toon registratiegaps (`lk-registratiegaps`, 3046-3048) | losse nodes meenemen | `toonRegistratiegaps` | **ja** | **kijkinstelling** |
| O | Verberg lege banen (`lk-verberg-lege`, 3051-3053) | lege lanen verbergen | `verbergLegeLanes` | **nee** — `v-if="weergave==='lagen'"` | **kijkinstelling** |

**Niet in de linkerkolom** (ter afbakening): de **organisatie-scope** ("Organisaties in beeld") zit in de
**middenkolom** boven het canvas (`v-if="organisatieNodes.length && weergave!=='praatplaat'"`, LKV:3064-3065),
niet links. Er is **geen apart "domein"- of "laag"-filter** als eigen control in de kolom (domein bestaat
alleen als zoekterm-match + kleuring; laag alleen in het startpaneel — zie Blok 3/5).

**Zichtbaar op de LEGE kaart** (`modus='leeg'`, `beginschermOpen=true`): A · C · E-J · M · N.
**Verborgen op de lege kaart:** B (tenzij views bestaan) · D · K · L · O.

**Kernobservatie:** van de **altijd-zichtbare** elementen is precies één een vertrekpunt (B, en dan alleen
als er views zijn); de rest (A, C, E-J, M, N) zijn kijkinstellingen die zonder getekende kaart geen doel
hebben.

---

## Blok 2 — Wat doet een kijkinstelling op een lege kaart?

**Datastaat op de lege kaart:** `herlaadGraaf` (LKV:320-331) doet bij `beginscherm.value` (computed 299:
`actieveSet.size===0 && !heleLandschap`) → `nodes.value=[]; edges.value=[]; return`. De hele computed-keten
(`grafNodes` 242 → `appNodes` 429 → `gefilterdeNodes` 641 → `zichtbareNodes` 763 → `getekendeNodes` 2155)
leest dan een **lege node-set**.

- **Een filter/drempel zetten:** de ref muteert, `filterActief` (588) wordt `true`, maar de keten leest een
  lege set → **er verandert niets zichtbaars**. De resultatenlijst (D) blijft bovendien verborgen
  (`v-if="!beginschermOpen…"`, 2899).
- **Eén uitzondering — wél een server-call:** typen/focussen in "Zoek leverancier…" roept via `ZoekSelect`
  (`ZoekSelect.vue:75/104`) `api.partijen.lijst(...)` (LKV:447) aan om de **dropdown-opties** te vullen —
  een call voor de picker, **niet** om de kaart te filteren. De andere filters (Type/Hosting/Lifecycle/Rol/
  BIV) gebruiken client-side lijsten → geen call. *Dus het veld is niet volledig "dood" (het toont
  leveranciers), maar de filter-actie erachter heeft geen doel.*
- **Blijft de invoer bewaard?** **Ja.** Niets reset een gezette filter op de lege kaart; zelfs "Begin
  opnieuw"/`wisSet` reset de kijk-variabelen **niet** (expliciet, LKV:871). Zodra er dán een set wordt
  opgebouwd of "hele landschap" laadt, grijpt dezelfde filter alsnog via `_nodeVoldoet` (613)/`_bepaalZichtbaar`
  (740-761). De invoer verdwijnt dus niet; hij werkt zichtbaar zodra er data is.
- **Stille verwachting "eerst links instellen, dán zoeken"?** Die zit impliciet in het feit dat de filters
  persistent zijn en later grijpen — maar het scherm geeft op de lege kaart **geen enkele terugkoppeling**
  dat de instelling "geladen staat te wachten". Dat is de schijnbelofte: de belofte (filter) is zichtbaar,
  het doel (een verzameling) niet.

**Betekenis voor het ontwerp:** "afwezig maken" van de kijkinstellingen op de lege kaart neemt **geen
functie** weg (er is niets te filteren) — het ruimt een schijnbelofte op. De enige nuance: het leverancier-
veld toont wél opties, dus het lijkt "iets te doen".

---

## Blok 3 — De dubbeling

**Opgeslagen views — ÉÉN databron, DRIE renderplekken, ONGELIJKE acties.**
- Bron: `opgeslagenViews` (LKV:958) ← `laadViews()` (961-967) ← `api.impactViews.lijst()` → `GET /impact-views`
  (api.js:337-338). Eén `openView` (1040-1046).
- Plek 1 — **linkerkolom** `lk-views` (2880-2892): openen **+ bewerken (`openBewerk`) + verwijderen
  (`verwijderView`)** — de **enige** plek met bewerk/verwijder-affordances. Geen `beginschermOpen`-guard.
- Plek 2 — **beginscherm-overlay** `kb-views` (KB:321-336, prop op LKV:3365; emit `openView` → LKV:3370):
  **alleen openen**.
- Plek 3 — **startscherm-modal** `lk-startscherm` (LKV:3539-3567, bij `toonStartscherm` 2668-2670): **alleen
  openen**.
- **Gedrag niet identiek**: bewerken/verwijderen bestaat uitsluitend links. Omdat `lk-views` geen
  `beginschermOpen`-guard heeft, verschijnen de views **tegelijk** links én in de beginscherm-overlay — de
  gemelde dubbeling.

**Standaardkijk — ÉÉN implementatie, alleen links.** Voorkeur-sleutel `kaart_kijkfilter` (`_KIJK_SLEUTEL`
LKV:494); laden/opslaan/herroepen via `api.voorkeuren.*` (api.js:348-350); affordance uitsluitend
`lk-standaardkijk` (2856-2876). **Niet gedubbeld.** Kijk = ringen/filters/diepte/groepeer (506-511);
momentkeuze (set/centrum/weergave/zoekterm/scope) bewust uitgesloten (527-528).

**Overige dubbeling:**
- **Zoeken — twee verschillende implementaties** (geen dubbele bron): startpaneel = server-side
  `/componenten` om de set **op te bouwen** (KB:7, `_zoekParams` KB:53-59); linkerkolom = client-side filter
  op de **al getekende** nodes (LKV:2894/2898). Complementair, comment LKV:2896-2897.
- **"Hele landschap tonen" — twee plekken**, beide → `toonHeleLandschap()` (876-883): beginscherm-link
  (KB:345-352) + startscherm-knop (LKV:3565).
- **"Begin opnieuw" — twee plekken**, beide → `wisSet()` (852-873): werkbalkknop `lk-begin-opnieuw` (2821)
  + verdwenen-selectie-knop `lk-leeg-verdwenen-opnieuw` (3383).

---

## Blok 4 — Wat is er nodig om de kolom bij een getekende kaart te laten verschijnen?

**Betrouwbaar "kaart getekend"-signaal:** **`heeftData`** (computed LKV:284 = `nodes.value.length > 0`).
`!beginschermOpen` is **niet** gelijk aan "kaart getekend": de overlay kan dicht zijn terwijl de kaart nog
laadt (`lk-laden`), leeg-geprund is (`lk-leeg-verdwenen`) of "Geen componenten" toont — de overlay-vlag zegt
alleen iets over de overlay, niet over nodes.

**Drie ontkoppelde grootheden:**
- `beginschermOpen` — ref (294), overlay-zichtbaarheid, **imperatief** gezet (`wisSet`→true 860 ·
  `toonHeleLandschap`→false 882 · `openView`→false 1045 · `@sluit`→false 3372). **Niet reactief afgeleid.**
- `beginscherm` — computed (299) = `actieveSet.size===0 && !heleLandschap`; stuurt alleen het "niets laden"-
  pad. **Ander ding** dan de ref.
- `heleLandschap` — ref (290), "toon bewust de volledige plaat, los van set-grootte".

**ADR-054 besluit 6 (binnenkomst-regel):** `beginschermOpen = actieveSet.size === 0` (LKV:2665), **eenmalig**
ná de beslisboom (handoff 2641 · deep-link 2646 · herstel 2654), **bewust géén reactieve koppeling**
(comment 2658-2664). Bij mount vallen `beginschermOpen`, `actieveSet.size` en `heleLandschap` samen; daarna
kan de gebruiker het beginscherm sluiten terwijl hij nog opbouwt → ze lopen uiteen.

**Bij verdwijnen van de selectie:** `wisSet` (852-873) → `beginschermOpen=true` + `lk-state` gewist (869) +
standaardkijk toegepast (872). De **prune** (`_schoonSetOp` 910-918) zet `beginschermOpen` **niet** (conform
"geen reactieve koppeling"); de aside blijft staan (geen `v-if`).

**Raakt dit `lk-state`, de views, of de layout?**
- **`lk-state`** (`_bewaarKaartState` 2560-2580) bewaart: `actieveSet`, `ringAan`, `laneVolgorde`,
  `verbergLegeLanes`, `toonRegistratiegaps`, `egoStartId`, `groepeerPerOrg`, `lezing`. **NIET** de
  attribuutfilters (Type/Leverancier/Hosting/Lifecycle/Rol/BIV) en **NIET** de scope. → een verschijnen/
  verdwijnen van de kolom raakt geen bewaarde filterstaat, want die wordt **nu al niet bewaard** (los
  opvolgpunt LI046).
- **Views/standaardkijk**: eigen bronnen (server), losstaand van de kolom-zichtbaarheid.
- **Layout**: de aside is **flex** (`w-60 flex-shrink-0`), sibling van het `flex-1`-canvas → **de aside
  verbergen laat het canvas de vrijgekomen breedte overnemen** (reflow). Nu wordt alleen ínhoud geguard
  (`lk-kaartzoek` op `!beginschermOpen`; K/L/O op `modus`/`weergave`), de aside zelf niet.

**Samengevat:** het benodigde signaal bestaat (`heeftData`, en/of `actieveSet.size>0`/`!beginscherm`
computed); de keuze wélk signaal de kolom gate't is een ontwerpbeslissing (ze verschillen in de laad-/
verdwenen-randgevallen). Het verbergen van de aside reflowt het canvas (waarschijnlijk gewenst — meer canvas
op de lege start).

---

## Blok 5 — Verrassingen, risico's en open vragen

**BIV-drempels en Rol — in de huidige demodata vrijwel inert (DB-meting, read-only):**
```sql
SELECT count(*) totaal,
  count(*) FILTER (WHERE biv_beschikbaarheid IS NOT NULL AND biv_integriteit IS NOT NULL
                   AND biv_vertrouwelijkheid IS NOT NULL) AS biv_volledig
FROM component;                       -- 19 | 2   (alleen HR-systeem + Klantportaal)
SELECT componentrol, count(*) FROM component GROUP BY 1;  -- interne_applicatie | 19
```
- **BIV-drempel**: `_bivVoldoet` (LKV:481-487) is ordinaal (`bivRangMap` 470) en **fail-open** bij een
  onbekende drempel, maar een gezette drempel **laat een node zónder waarde wegvallen** (485-486). Op deze
  data: BIV is volledig ingevuld op **2 van 19** → een BIV-drempel zou ~17 componenten wegfilteren. Praktisch
  bruikbaar op een handjevol.
- **Rol-filter** (620-621): **alle 19 componenten dragen `interne_applicatie`** → een rol-filter onderscheidt
  in de huidige data **niets**.
- **Filter-exemptie**: rol/BIV gelden alléén voor nodes mét `componentrol`; context-nodes (partij/contract/
  gebruikersgroep, incl. org-partijen) zijn exempt (617-626).
- → Een **inklap** ("Geavanceerd/BIV & Rol", dicht by default) zou in de huidige stand zelden iets raken; de
  vraag is of dat aan de data ligt (demodata onvolledig) of structureel.

**Startfilters Laag / Hosting / Eigenaar — die staan al in het startpaneel achter "+ Filters":**
`KaartBeginscherm` draagt een weggevouwen filterblok `toonFilters` (KB:47) met **`filterLaag`** (LAAG_OPTIES,
KB:35/48), **`filterHosting`** (HOSTING_OPTIES, KB:36/49) en **`eigenaarId`** (KB:50) — **server-side**,
onderdeel van `_zoekParams` → `/componenten` (`componenttype/zoek/laag/hostingmodel/eigenaar`, KB:53-59). Dit
zijn dus **vertrekpunt-criteria** die de set **opbouwen**. Tegelijk bestaat **Hosting** óók als
**kijkinstelling** in de linkerkolom (G), en **Type** in beide (startpaneel `gekozenType` + kolom E). **Laag**
en **Eigenaar** bestaan **alleen** in het startpaneel, niet als kolom-filter. → de vertrekpunt/kijk-scheiding
is in het startpaneel al deels gemaakt; de linkerkolom overlapt erop (Hosting, Type) en mist tegelijk de
symmetrie (geen Laag/Eigenaar als kijkinstelling).

**Stille keuzes die niemand expliciet heeft genomen** (benoemd, niet gekozen):
- Wélk signaal gate't de kolom — `heeftData`, `actieveSet.size>0`, of `!beginschermOpen`? Ze lopen uiteen bij
  laden/verdwenen/hele-landschap.
- Verdwijnt de **hele aside** (canvas reflowt) of alleen het kijkinstelling-blok (vertrekpunten blijven)?
- De **vertrekpunt-elementen in de kolom** (opgeslagen views; en het "toevoeg"-zoeken C/D) — verhuizen die
  naar het beginscherm (einde dubbeling), of blijven ze links als tweede ingang?
- **Standaardkijk** is een kijkinstelling die je pas zinvol zet mét een getekende kaart, maar staat nu altijd
  — hoort die bij de kijkinstellingen (mee verbergen) of is het een aparte laag?
- **Bewerken/verwijderen van views** leeft nu alléén links — als de kolom verdwijnt op de lege kaart, waar
  beheert de gebruiker dan zijn views (het beginscherm biedt alleen openen)?
- Horen **Laag/Eigenaar** óók als kijkinstelling in de kolom (symmetrie met Hosting/Type), of blijven ze
  puur vertrekpunt in het startpaneel?
- **BIV/Rol inklappen** by default — op databruikbaarheid, of pas als een tenant ze echt gebruikt?

---

## Open ontwerpvragen voor Bert

1. Welk signaal bepaalt of de kijkinstellingen-kolom verschijnt — "er staan nodes" (`heeftData`), "er is een selectie" (`actieveSet.size>0`), of "het beginscherm is dicht" (`!beginschermOpen`)?
2. Verdwijnt op de lege kaart de **hele** linkerkolom (canvas krijgt de ruimte), of alleen het kijkinstellingen-deel terwijl de vertrekpunten blijven?
3. Waar horen de **vertrekpunten** die nu links staan — opgeslagen views (incl. bewerken/verwijderen) en het toevoeg-zoeken — thuis: in het beginscherm (dubbeling opheffen) of links als tweede ingang?
4. Waar beheert de gebruiker zijn **opgeslagen views** (bewerken/verwijderen) als de kolom op de lege kaart weg is — verhuist dat beheer mee naar het beginscherm/startscherm?
5. Is **standaardkijk** onderdeel van de (verbergbare) kijkinstellingen, of een aparte, altijd-bereikbare laag?
6. Horen **Laag** en **Eigenaar** óók als kijkinstelling in de kolom (symmetrie met Hosting/Type), of blijven ze uitsluitend vertrekpunt-filter in het startpaneel "+ Filters"?
7. Moeten **BIV-drempels en Rol** standaard ingeklapt — en is hun geringe bruikbaarheid een datakwestie (demodata) of structureel?
8. Moeten de **attribuutfilters en de organisatie-scope** in `lk-state` (nu niet bewaard, los LI046-opvolgpunt) — en verandert het antwoord als de kolom verschijnt/verdwijnt?

*(STOP na dit rapport. Geen vervolgstap gebouwd. Niet gecommit.)*
