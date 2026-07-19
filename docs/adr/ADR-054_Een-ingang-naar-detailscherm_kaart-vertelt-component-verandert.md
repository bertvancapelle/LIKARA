# ADR-054 — Eén ingang naar een detailscherm: de kaart vertelt, het component verandert

| | |
|---|---|
| **Status** | Aanvaard — **gebouwd (LI046)**: `80d0038` slice 1 (gedeelde detail-ingang + dekkingsscan) · `4dd1387` slice 2 (veld-anker) · `466eb7b` slice 3 + herstel (per-ring popup-takken + "de bezoeker wint") · `61665a4` startscherm · `9ee6fcb` terugkeer + verdwenen-selectie · `3b7941f` skills. Deze ADR legt het gebouwde vast. |
| **Datum** | 2026-07-19 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-025/040 (Landschapskaart) · ADR-035 (registratiegat-signalen — de open punten die de kaart doorverwijst) · ADR-052 (tenant-norm — de "open punten per component" die dit toegankelijk maakt) · CD022 (deep-link `?tab=/?cat=`) · LI034 (`lk-state`-werkbehoud) · LI023/LI021 (kaart opent leeg) · LI038 (KERNLES: een regel houdt pas als een bouwsteen/scan hem afdwingt) |
| **Grond** | `docs/Checkpoint-detailpaneel-per-relatiesoort-V046.md` · `docs/Checkpoint-open-punten-per-component-V046.md` · `docs/Checkpoint-routes-naar-component-V046.md` · `docs/Checkpoint-terugweg-naar-de-kaart-V046.md` (alle read-only) |
| **Invariant (onschendbaar)** | **De kaart vertelt, het component verandert.** Er is geen mutatie-ingang vanaf de kaart; de kaart brengt je naar het feit, het wijzigen gebeurt op het detailscherm. En: elke navigatie naar een detailscherm loopt door **één** ingang — de aanleiding leeft in de URL, er wordt nooit een route beloofd waar niets te landen valt. |

---

## Context / de gebruikersvraag

De consultant beweegt heen en weer tussen de **kaart** (het overzicht: wat hangt waar samen, wat
mist er) en het **component** (waar hij een feit vastlegt). Drie dingen bleken kapot of onbeslist:

1. **De doorklik verloor zijn aanleiding.** Er waren 21 navigaties naar het componentdetail
   verspreid over 16 bestanden; **precies één** gaf context mee (de blokkade-doorklik met
   `?tab=&cat=&markeer=`). Klikte je op de kaart op de "gebruikt"-lijn, dan landde je op een kale
   `/componenten/<id>` — niet op de plek waar dat feit leeft. Vier plekken besloten bovendien
   zelfstandig "welk objecttype heeft welk detailscherm" — vier kopieën van dezelfde afweging.
2. **Sommige feiten hadden geen eerlijke landingsplek.** Veld-niveau-feiten buiten de checklist
   (eigenaar, BIV, levensfase, bedoeling, beschrijving) kenden geen anker; alleen de checklist
   kende markering. En bedrijfsfunctie/proces hebben helemaal geen detailscherm.
3. **De terugweg verloor je beeld.** Terugkeren naar de kaart mét bewaard werk tekende de kaart
   wél, maar achter de opake beginscherm-overlay — de herstel-tak was de enige binnenkomst-tak die
   het beginscherm niet sloot. En als de bewaarde selectie inmiddels weg was, zweeg het scherm.

Deze ADR legt de gebouwde antwoorden vast — als **invarianten**, niet als afspraken. Waarom dat
onderscheid ertoe doet: zie §Waarom invariant, geen afspraak.

---

## Besluit

### 1. Eén ingang naar een detailscherm (routes-checkpoint Q1/Q3/Q5/Q6)
Alle navigatie naar een detailscherm bouwt zijn route via **`frontend/src/detailIngang.js`
→ `detailRoute(objectType, id, aanleiding)`**. De type→route-beslissing leeft op één plek
(`ROUTE_PER_TYPE`); de vier eerdere kopieën (kaart `_detailLink`, ArchitectuurView,
ArchitectuurLagenView, PartijRollenSectie) zijn hierin opgegaan. Ook een kale rij-klik loopt door
de ingang (zonder aanleiding). Geborgd met een **dekkingsscan** in dezelfde slice:
`tests/detailIngang.scan.test.js` faalt op elk bestand dat zelf een
`name: '<component|contract|partij>-detail'`-literal bouwt (recept: `tests/api.filter.test.js`).
De regel leeft dus in een scan, niet in tekst.

### 2. De aanleiding leeft in de URL (routes-checkpoint Q1: promotie, geen nieuw anker)
De aanleiding is een **promotie** van het bestaande query-mechanisme (CD022), niet een nieuw
generiek feit-anker. `AANLEIDING_SLEUTELS = {tab, cat, markeer, bewerk, veld}`. Zo is de doorklik
**deelbaar, herstelbaar en overleeft F5**. Een onbekende sleutel is een **luide fout**
(`detailRoute` throwt) — een aanleiding kan niet stil wegvallen of stil een niet-bestaande landing
beloven.

### 3. Geen route beloofd waar niets te landen valt (routes-checkpoint Q2: weigeren; Q4)
Een objecttype **zonder** detailscherm geeft `detailRoute` → `null` terug; de aanroeper toont dan
**geen link** (niet: kaal landen, niet: de dichtstbijzijnde tab openen — beide liegen). Concreet:
`bedrijfsfunctie` heeft geen detailscherm → de route opent de bedrijfsfunctielijst met `?focus=<id>`;
`proces` is MVP-verborgen (ADR-043) → geen route. Een onbekend **veld-anker** is eveneens een luide
fout (`VELD_ANKERS`-check).

### 4. Het veld-anker landt gemarkeerd, niet in bewerk-modus (slice 2, optie B)
`?veld=<anker>` landt op het **Overzicht**, markeert het veld (accent-achtergrond) en zet de
**Bewerken-knop ernaast** — géén ongevraagde bewerk-overlay. `VELD_ANKERS = {eigenaar, biv,
levensfase, bedoeling, beschrijving}`. **Waarom:** een gegokte eigenaar is erger dan een lege
eigenaar. LIKARA brengt de mens naar de plek en laat hem beslissen; het verzint geen invoer en
opent geen mutatie ongevraagd (spiegel van "de kaart vertelt, het component verandert").

### 5. Volgorde-invariant: de bezoeker wint van het scherm (slice 3 herstel)
Het **terugschrijven van de tabstand naar de URL** (`router.replace`) begint pas wanneer de
binnenkomst/aanleiding is verwerkt (`_binnenkomstVerwerkt`, `ComponentDetail.vue:273-322`). Zonder
deze poort liet de async categorie-watch (checklistvragen arriveren middenin `laad()`) de
terugschrijf op de **beginstand** vuren en zo de aanleiding uit de URL wissen vóór ze gelezen werd —
op **elk** component mét checklistvragen. Het scherm mag de aanleiding van zijn eigen bezoeker niet
overschrijven.

### 6. Binnenkomst-regel voor het beginscherm — één eenmalige regel, niet reactief (terugweg-checkpoint)
Ná de binnenkomst-beslisboom geldt **één** gedeelde regel voor álle takken (handoff · deep-link ·
herstelde `lk-state` · verse start · elke toekomstige tak): `beginschermOpen = actieveSet.size === 0`
(`LandschapskaartView.vue:2665`). Gevulde kaart → beginscherm dicht; verse start → open. Bewust een
**eenmalige beslissing bij binnenkomst**, géén reactieve koppeling aan de set (de LI023-spooksluiting-
les blijft staan; geen `v-if="actieveSet.size===0"`). Dit **herziet** de oude LI023-regel "sluiten
alleen via expliciete gebruikersactie" voor de herstelde terugkeer: **terugkeren of herladen mét
bewaard werk ís de expliciete gebruikersactie** ("je komt terug waar je was — ook op de kaart").

### 7. Verdwenen selectie: LIKARA zwijgt niet (slice terugkeer, `lk-leeg-verdwenen`)
Kom je terug met een selectie die **volledig verdwenen** is (de componenten bestaan niet meer;
spook-ids worden door de LI052-prune weggeschoond), dan benoemt LIKARA **dát er iets weg is** —
"De eerder gekozen componenten bestaan niet meer" (gedempt, vervallen-taal; geen fout van de
gebruiker) — met de bestaande **"Begin opnieuw"**-actie ter plekke, i.p.v. de zwijgzame kale lege
staat. De teller `setOpgeschoond` (aantal weggeschoonde ids) is het bewijs dat er zojuist iets wég
was; hij verandert het prune-gedrag niet. Dit is de **eerlijke rand** van "je komt terug waar je
was": ook als daar niets meer is, zegt LIKARA het.

### 8. De kaart vertelt, het component verandert
Er is **geen mutatie-ingang vanaf de kaart**. De kaart brengt je naar het feit (besluit 1–4); het
wijzigen gebeurt op het detailscherm. De kaart is een lees-/verwijs-oppervlak.

---

## Waarom invariant, geen afspraak

Elk van deze regels stond deze sessie al **tekstueel** vast — en ging tóch mis. Twee bewijzen uit
deze sessie zelf:

- **De vergeten `gebruikt`-tak.** De edge-popup bouwt per ring een eigen verhaal. Eén ring zonder
  tak viel **stil door naar het koppeling-pad** — de "gebruikt"-doorklik landde op de verkeerde
  plek zonder dat iets faalde. Reparatie: `_EDGE_TAKKEN` + **dekkingstest `RINGEN ⊆ _EDGE_TAKKEN`**
  (`LandschapskaartPopups.test.js:452-454`) + een runtime-fallback (neutraal verhaal bij een
  onbekende ring). Een ring zonder tak faalt nu zichtbaar in de suite.
- **De vergeten per-tak-vlag.** Twee binnenkomst-takken zetten `beginschermOpen = false`, de derde
  (herstel) niet — de terugkeer tekende werk dat niemand zag, achter de overlay. Reparatie:
  besluit 6 — één eenmalige regel ná de beslisboom; **per-tak-vlaggen bestaan niet meer**.

Beide waren "afgedekt" in proza en beide faalden. Daarom: de regel hoort in een **gedeelde
bouwsteen of een scan** (KERNLES LI038 #2/#4), niet in tekst. `detailIngang.js` + de dekkingsscan,
`_EDGE_TAKKEN` + de RINGEN-scan, en de éne binnenkomst-regel zijn die borging.

---

## Gevolgen

- **Positief:** één plek voor route-constructie (nieuwe consument erft de aanleiding gratis); de
  doorklik landt bij het feit; geen dode route-belofte; de terugkeer toont het bewaarde beeld; een
  verdwenen selectie liegt niet meer. Drie scans/tests borgen de invarianten machinaal.
- **Grens:** een aanleiding kan alleen landen waar een landingsplek bestaat. Veld-niveau-feiten op
  niet-applicatie-componenten en flow/groep-feiten daar hebben (nog) geen tab — het gat is
  zichtbaar (geen link), niet verzwegen.
- **Open (naar OPVOLGPUNTEN):** wat er stil kan verschuiven tussen weggaan en terugkomen — de
  organisatie-scope en de rol-/BIV-filters zitten **niet** in `lk-state`, en een **gedeeltelijk**
  verdwenen selectie wordt zonder aanwijzing kleiner getekend + de set stil opgeschoond. Een dichte
  deur zie je; een verschoven filter of een ontbrekend lid niet. Open ontwerpbesluit Bert.

---

## Alternatieven overwogen

- **Een generiek feit-anker** (feit-soort + feit-id in de query) i.p.v. promotie van het bestaande
  `tab/cat/markeer/bewerk/veld`-mechanisme. **Verworpen:** de bestaande query-taal dekt de
  landingsplekken al; een tweede ankertaal ernaast is een tweede waarheid.
- **Kaal landen of de dichtstbijzijnde tab openen** bij een feit zonder landingsplek. **Verworpen:**
  beide liegen (je belooft een landing die er niet is). Geen link tonen is eerlijk.
- **`?veld=` opent direct de bewerk-overlay.** **Verworpen:** een gegokte/ongevraagde bewerk-modus
  duwt de mens naar invoer; markeren + knop ernaast laat de beslissing bij de mens.
- **Terugkeer toont het beginscherm mét een "verder waar je was"-knop.** **Verworpen:** terugkeren
  mét bewaard werk ís de expliciete ingang; een extra klik om je eigen beeld terug te zien is ruis.
- **De per-tak-vlag behouden (elke tak zet `beginschermOpen` zelf).** **Verworpen:** hij wordt
  vergeten (bewijs hierboven). Eén eenmalige regel ná de beslisboom kan niet half-gezet raken.
