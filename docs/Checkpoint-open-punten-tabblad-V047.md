# Checkpoint — het tabblad "Open punten" per component

**Sessie:** LI047 · **Build:** V047 · **Commit:** 5e00bab · **Type:** READ-ONLY feitenopname vóór de bouw
**Datum:** 2026-07-19 · **Aard:** design-heavy → checkpoint-eerst (werkprotocol §Gate-discipline)

> Dit rapport **wijzigt niets** aan code/schema/seed. Het enige geschreven bestand is dit rapport zelf.
> Alle DB-metingen zijn `SELECT` als `lk_admin` (ziet alle tenants). Feiten met vindplaats (bestand:regel).
> Waar iets niet vast te stellen was: **"niet vastgesteld"**.
>
> **Vertrekpunt:** `docs/Checkpoint-open-punten-per-component-V046.md` (LI046) — dát rapport stelde vast
> dát de grond bestaat (bronnen, routes, dubbeltellingen). Dit rapport herhaalt dat niet en beperkt zich
> tot wat de **tien LI047-besluiten** aan de code vragen.

---

## Kernbevindingen vooraf (leest u dit eerst)

Zes dingen, waarvan **twee stop-en-rapporteer-punten**.

1. **⚠ CORRECTIE OP LI046 — de seed zet ZES feiten verplicht, niet vijf.** `DEFAULT_VERPLICHT` is
   {eigenaar, verantwoordelijke, biv, contract, koppelingen} (component_norm_service.py:58-60), **maar de
   dev-seed verzet daarna de lat**: ná de klaarverklaringen wordt `bedoeling` op `verplicht=true` gezet
   (dev_seed_testdata.py:1794-1800). De LI046-tabel "moet nog (default)" rekende met vijf feiten en is
   daarmee **structureel één te laag** voor bijna elk component. Alle tellingen in Blok 5 hieronder zijn
   opnieuw berekend met de zes.

2. **⚠ STOP-EN-RAPPORTEER (besluit 10 × besluit 9) — voor het feit `gebruikersgroep` is "de plek geven"
   géén frontend-slice maar een DOMEINBESLUIT.** De backend **weigert** een gebruikersgroep op een
   niet-`applicatie`-component met 404 (`gebruikersgroep_service.py:383`). Hetzelfde geldt voor Datatypes
   (`datatype_service.py:148`). Het signaal dat het punt oplevert kent die restrictie echter **niet**
   (`badge_voor_component` filtert niet op componenttype, registratiegaten_service.py:200-206). Zet een
   tenant `gebruikersgroep` verplicht, dan ontstaat op een fileshare/database/saas_dienst een punt dat
   **nergens beantwoord kan worden** — niet omdat een tab ontbreekt, maar omdat de registratie voor dat
   type niet bestaat. Ik heb dit **niet** beslist (zie open vraag 1).

3. **Besluit 8 ("bewust geen" hangt aan het feit) erft NU NIET.** De uitsluiting zit **niet** in de pure
   functie maar in twee aanroepers, elk met een **hardcoded paar-literal**
   (`norm_status` :131 `verplicht & {FEIT_KOPPELINGEN, FEIT_CONTRACT}` en `feit_vastgesteld` :192
   `if feit in (FEIT_KOPPELINGEN, FEIT_CONTRACT)`). Een nieuw feit met dezelfde drieslag erft de regel dus
   **niet** zonder codewijziging — en het ADR-053-Archiefwetfeit erft hem zelfs met codewijziging niet,
   want dat is een **andere vorm** (eigen kolom-enum, geen `component_bevinding`-rij). Zie Blok 1.2.

4. **⚠ STOP-EN-RAPPORTEER (besluit 8 × besluit 2) — het schone geval draagt een punt in "Dit valt op".**
   HR-systeem heeft "bewust geen koppelingen" → het feit `koppelingen` telt als vastgesteld → **0 in "Dit
   moet nog"** ✓. Maar "staat los in het landschap" (`component_geisoleerd`, registratiegaten_service.py:283)
   **honoreert die bevinding niet** en vuurt gewoon. Het ijkbeeld van "in orde" toont daarmee een punt.
   Besluit 8 spreekt over *feiten*; "staat los" is per besluit 2 **geen** ontbrekend feit, dus de regel
   dekt dit geval tekstueel niet. Zie open vraag 2.

5. **Besluit 6 is goedkoper dan het lijkt: de `SignaleringBadge` heeft precies ÉÉN consument.**
   `ComponentDetail.vue:344` — nergens anders in de codebase (lijstscherm noch kaart) wordt de component
   gemount, en `api.signalering.badgeComponent` (api.js:362) heeft één aanroeper (ComponentDetail.vue:131).
   De knop vervangt dus geen gedeelde bouwsteen; er gaat **geen ander scherm** iets verliezen. Wat wél
   verdwijnt: de **tooltip met signaalnamen** (SignaleringBadge.vue:18-26) en de drie signalen die géén
   norm-feit zijn (zie Blok 3.2).

6. **⚠ De dev-DB is nog steeds stale — en breder dan LI046 meldde.** `component_norm` = **0 rijen**
   (bevestigd), én **alle 267 checklistscores staan op `ja`** terwijl de seed voor Zaaksysteem één `nee`
   voorschrijft (dev_seed_testdata.py:1132). Gevolg: **blok 3 "Dit valt op" heeft in de huidige data géén
   enkele checklistregel** om te tonen. Niet gediagnosticeerd, niet hersteld (zie Blok 5.1).

---

## Blok 1 — Kan één afleiding alle drie de blokken voeden?

### 1.1 Bestaat er één functie die alle open punten levert? — **Nee. Drie bronnen, drie endpoints.**

Er is geen per-component "alle open punten"-functie. Per blok, exact:

| Blok | Inhoud | Functie | Endpoint | Vindplaats |
|---|---|---|---|---|
| **Dit moet nog** | verplichte feiten met status `niet_vastgesteld` | `component_norm_service.norm_status` | `GET /component-normen/status/{id}` | component_norm_service.py:101-152 · routes/component_norm.py:25-33 |
| **Dit zou netjes zijn** | open feiten die **niet** verplicht zijn | ⚠ **bestaat niet** — `norm_status` levert **alleen verplichte** feiten (`:120`, `:152`) | — | zie hieronder |
| **Dit valt op** — checklist | scores op nee/deels | `checklistscore_service.lijst(component_id=…)` | `GET /checklistscores?component_id=` | routes/checklistscore.py:42-73 |
| **Dit valt op** — los in landschap | `component_geisoleerd` | `registratiegaten_service.badge_voor_component` | `GET /signalering/badges/component/{id}` | registratiegaten_service.py:172-261 |

**Het gat zit in blok 2.** `norm_status` filtert op `verplicht` (`:120`) en retourneert uitsluitend die
feiten (`:152`). De niet-verplichte `HARDE_FEITEN` — precies het "netjes"-domein — worden **niet
geëvalueerd**. De determinatie zelf kán het wel: `_beslis_vastgesteld` (`:155-170`) is feit-agnostisch. Voor
blok 2 is dus **geen nieuwe afleiding nodig, wel een tweede aanroep-vorm** van dezelfde pure functie (of een
parameter die de verplicht-filter opheft). Dat is de goedkoopste vorm die geen tweede waarheid maakt.

**Twee bronnen leveren hetzelfde feit met andere semantiek** (bevestigd, LI046 Blok 4.2 blijft staan): voor
`koppelingen`/`contract` honoreert `norm_status` de bewust-geen-bevinding (`:131-143`) en de badge **niet**
(`component_geisoleerd` :283, `contract_zonder_component` :300). Blok 1 en blok 3 moeten dus **verschillende**
bronnen gebruiken voor wat oppervlakkig hetzelfde lijkt — anders spreekt het scherm zichzelf tegen op één rij.

### 1.2 Besluit 8 aan het feit hangen — waar leeft "dit feit is vastgesteld"?

**De determinatie is één pure functie:** `_beslis_vastgesteld(feit, *, hostingmodel, levensfase,
migratiepad, signalen, rel_vast)` (component_norm_service.py:155-170). Twee aanroepers delen hem
(`norm_status` :146-149 en `feit_vastgesteld` :197-200) — dat deel is gezond.

**Maar de bewust-geen-uitsluiting zit er NIET in.** De functie leest alleen het al-uitgerekende
`rel_vast`-dict (`:161-162`); het **uitrekenen** gebeurt in de aanroepers, elk met een eigen literal:

```python
# norm_status                              (:131)
rel_feiten = verplicht & {FEIT_KOPPELINGEN, FEIT_CONTRACT}
# feit_vastgesteld                         (:192)
if feit in (FEIT_KOPPELINGEN, FEIT_CONTRACT):
```

Dat is **dezelfde verzameling op twee plekken uitgeschreven**, terwijl er een derde, wél afgeleide
formulering naast staat: `norm_definitie` :208 gebruikt `{s.value for s in ComponentBevindingSoort}`.

**Kan een nieuw feit de regel erven zonder codewijziging? — Nee, en er zijn twee verschillende gevallen:**

- **(a) Een nieuw RELATIONEEL feit met bewust-geen** (nieuwe `ComponentBevindingSoort`-waarde): erft
  vandaag **niet** — de twee literals moeten mee. Zouden beide `{s.value for s in ComponentBevindingSoort}`
  gebruiken (zoals `norm_definitie` al doet), dan erfde het **wel** automatisch. Dat is een kleine,
  gerichte convergentie — geen nieuwe bouwsteen.
- **(b) ADR-053 Archiefwet — erft principieel niet, ook niet ná (a).** Dat feit is per ADR-053 een **eigen
  component-kolom** met enum `{ja, bewust_geen}` en `null` = "nog niet gekeken" (likara-domeinmodel §LI045:
  *"gedeelde wóórden zijn geen gedeelde bouwsteen"*). Het loopt dus **niet** via `component_bevinding` en
  krijgt een eigen tak in `_beslis_vastgesteld` — zoals `FEIT_LEVENSFASE` (`:166-167`) er een heeft.
  **Feitelijke stand:** het feit is **niet gebouwd** — geen kolom in `models.py`, niet in `HARDE_FEITEN`
  (`:49-53`), geen migratie (laatste = `0073_adr052_klaarverklaring_snapshot.py`). ADR-053 bestaat als
  document, niet als code.

**Wat nodig zou zijn om het te laten erven** (niet gebouwd, ter besluitvorming): één helper per feit die
"vastgesteld" beantwoordt uit de bron die dát feit draagt, met `_beslis_vastgesteld` als de ene
dispatch-plek — dan is een nieuw feit één tak op één plek in plaats van drie plekken. De literal-duplicatie
onder (a) is de eerste, goedkoopste stap.

### 1.3 Teller en lijst uit één bron — **ja, mogelijk; niets staat het in de weg.**

Het getal op de kopknop = `len(feiten met status niet_vastgesteld)` uit exact dezelfde `norm_status`-respons
die blok 1 vult. Er is **geen tweede telling nodig** en er bestaat er ook geen die eerst opgeruimd moet
worden: `MigratiegereedheidSectie` leest `norm_status` al rechtstreeks (MigratiegereedheidSectie.vue:108) en
telt niet zelf.

⚠ Eén randvoorwaarde: de knop staat in de **DetailKop** en de lijst in een **tabpanel**. Als beide hun eigen
`api.componentNormen.status()`-call doen, zijn dat twee *aanroepen* van één bron — geen tweede waarheid,
maar wel twee laadmomenten die kunnen divergeren bij een mutatie in het tabblad. De norm van LI041
(*"teller en lijst delen één filterwaarheid"*, likara-tests §LI041-bronscan-norm) vraagt hier om **één
laadpunt in `ComponentDetail`** dat beide voedt — zoals `signaleringBadge` nu al werkt (ComponentDetail.vue:71,
:131). Een bronscan-test in de LI041-vorm hoort erbij.

### 1.4 Dubbeltellingen en tegenspraak buiten LI046 Blok 4 — **drie nieuwe gevonden.**

| # | Bevinding | Waarom het stil verkeerd telt | Vindplaats |
|---|---|---|---|
| 1 | **`koppelingen` (blok 1) vs. "staat los in het landschap" (blok 3)** | Zelfde onderliggende feit (geen flow-relatie), **twee blokken**, en blok 3 honoreert bewust-geen niet. Een component met bewust-geen-koppelingen: 0 in blok 1, 1 in blok 3 (kernbevinding 4). Zonder ingreep leest de gebruiker een tegenspraak op één scherm. | component_norm_service.py:131-143 vs. registratiegaten_service.py:283-291 |
| 2 | **`contract` (blok 1) vs. `contract_zonder_component`** | Identiek mechanisme als #1. **Bijt nu niet**: dat signaal zit **niet** in `badge_voor_component` (alleen tenant-breed) — maar het is een latente val zodra iemand de badge uitbreidt. | registratiegaten_service.py:300-307 |
| 3 | **`bedrijfsfunctie` is voor 3 van de 8 typen structureel "vastgesteld"** | `_SIG_GEEN_BF` vuurt alleen bij `ondersteunt_werk`-typen (registratiegaten_service.py:227-243). Voor database/server_compute/integratievoorziening is het feit dus **altijd** vastgesteld — het verschijnt nooit als punt. Correct gedrag (het feit is daar betekenisloos), maar het is een **stille** neutralisatie: het scherm zegt niet dat de vraag daar niet geldt. | zie Blok 2.5 |

De LI046-dubbeltelling (`verantwoordelijke` × `object_zonder_roltoewijzing`, registratiegaten_service.py:249
+ :257-258) is door **besluit 7** al opgelost: het overzicht telt één keer als feit `verantwoordelijke`.
Bevestigd dat de conditie letterlijk dezelfde is (beide op `geen_rol`).

---

## Blok 2 — Wat kost "elk punt een plek" per componenttype?

### 2.1 De tabbladen per componenttype (volledige matrix)

`isSubtype` ≡ `componenttype == 'applicatie'` (component_service.py:268, :591 — de vlag
`heeft_applicatie_subtype` is sinds LI059 een pure type-vergelijking, geen subtabel meer).
`isChecklistDragend` = `checklist_dragend === true || lifecycle_status` (ComponentDetail.vue:106-108).
Alle condities: ComponentDetail.vue:202-226.

Catalogus-stand (`componentconfig_optie`, gemeten):

```sql
SELECT optie_sleutel, checklist_dragend, ondersteunt_werk FROM componentconfig_optie
WHERE dimensie='componenttype' ORDER BY volgorde;
```
| type | checklist_dragend | ondersteunt_werk |
|---|---|---|
| applicatie | t | t |
| database | t | f |
| server_compute | t | f |
| client_software | f | t |
| saas_dienst | f | t |
| integratievoorziening | t | f |
| fileshare | f | t |
| landelijke_voorziening | t | t |

**Tabblad-matrix** (✓ = getoond · ✗ = niet getoond):

| Tabblad | conditie (vindplaats) | applicatie | database | server_compute | client_software | saas_dienst | integratie&shy;voorziening | fileshare | landelijke_&shy;voorziening |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Overzicht | altijd (:203) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Bedrijfsfunctie | altijd (:207) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Checklist | `isChecklistDragend` (:208) | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ |
| Datatypes | `isSubtype` (:211) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Gebruikersgroepen | `isSubtype` (:212) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Koppelingen | `isSubtype` (:213) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Gebruik | altijd (:218) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Opbouw | altijd (:219) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Impact | altijd (:220) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Contracten | altijd (:221) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Verantwoordelijkheden | altijd (:222) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Blokkades | `isChecklistDragend` (:224) | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ |

⚠ **Noot bij `isChecklistDragend`:** de tweede tak (`|| lifecycle_status`) betekent dat een component dat
**ooit** beoordeeld is de Checklist/Blokkades-tabs **houdt**, ook nadat de platformbeheerder
`checklist_dragend` uitzet. Bewust (LI058: "profielen inert"), maar het maakt de matrix per **instantie**
variabel, niet alleen per type.

### 2.2 Feit × plek — waar legt de gebruiker het antwoord vast?

| Norm-feit | Plek waar het antwoord landt | Bestaat voor élk type? |
|---|---|---|
| `eigenaar` | Overzicht → veld-anker `eigenaar` + Bewerken-overlay (ComponentDetail.vue:463-473) | **ja** |
| `verantwoordelijke` | Verantwoordelijkheden-tab (:222); `roltoewijzing` accepteert component (roltoewijzing_service.py:33) | **ja** |
| `biv` | Overzicht → veld-anker `biv` + Bewerken (:415-426) | **ja** |
| `gebruikersgroep` | Gebruikersgroepen-tab (:212) | **NEE — alleen applicatie** |
| `bedrijfsfunctie` | Bedrijfsfunctie-tab (:207) | tab ja; **registratie alleen bij `ondersteunt_werk`** |
| `levensfase` | Overzicht → veld-anker `levensfase` + Bewerken (:430-435) | **ja** |
| `bedoeling` | Overzicht → veld-anker `bedoeling` + Bewerken (:436-442) | **ja** |
| `hosting` | Overzicht toont "Hostingmodel" (:410-411); **géén veld-anker** → alleen Bewerken-overlay | **ja** (maar zie 2.4) |
| `koppelingen` | Koppelingen-tab (:213) | **NEE — alleen applicatie** |
| `contract` | Contracten-tab (:221) | **ja** |

**De (componenttype × feit)-combinaties waar het punt wél kan ontstaan maar de plek ontbreekt:**

| Feit | Componenttypen zonder plek | Kan het punt daar ontstaan? |
|---|---|---|
| `gebruikersgroep` | database · server_compute · client_software · saas_dienst · integratievoorziening · fileshare · landelijke_voorziening (**7 van 8**) | **Ja** — `_SIG_GG` kent geen type-guard (registratiegaten_service.py:200-206) |
| `koppelingen` | dezelfde **7 van 8** | **Ja** — `heeft_echte_registratie` kent geen type-guard (component_bevinding_service.py:62-88) |

Dat zijn **14 combinaties**. Voor `bedrijfsfunctie` ontstaat het punt níét bij de drie
niet-`ondersteunt_werk`-typen (zie 2.5), dus dat is geen dood punt.

### 2.3 De aard van de conditie — frontend, backend of schema? (**hier scheiden de wegen**)

| Feit | Aard van de blokkade | Vindplaats | Gevolg |
|---|---|---|---|
| `koppelingen` | **FRONTEND-conditie.** De tab staat achter `isSubtype` (:213), maar de registratie loopt via de **generieke relatie-facade** (`api.relaties.maak`, KoppelingSectie.vue:257) en `relatie_service.maak_aan` **valideert geen `element_type`** (bevestigd; ook likara-domeinmodel §"Type-validatie bron/doel leeft NIET in de relatie-facade"). Een flow op een fileshare is backend-zijdig gewoon toegestaan. | relatie_service.py:149-152 | **Frontend-slice.** De tab tonen voor elk type volstaat. |
| `gebruikersgroep` | **BACKEND-weigering.** `gebruikersgroep_service.maak_aan` haalt de ouder op en gooit `NietGevonden` (404) als het componenttype ≠ `applicatie`. | gebruikersgroep_service.py:381-384 | **DOMEINBESLUIT — ik stop hier.** |
| `bedrijfsfunctie` | **BACKEND-weigering**, maar met een **passende** signaal-scope (het punt ontstaat daar niet). | functievervulling_service.py:107-111 (`422 COMPONENT_ONDERSTEUNT_GEEN_WERK`) | geen dood punt; wel een UX-gat (2.5) |
| Datatypes (geen norm-feit) | **BACKEND-weigering**, idem | datatype_service.py:147-149 | buiten scope van dit overzicht |

**Stop-en-rapporteer (werkprotocol §Gate-discipline: "bij twijfel stoppen").** Besluit 10 zegt: *"Ontbreekt
die plek voor een componenttype, dan wordt de plek gegeven."* Voor `koppelingen` is dat een frontend-slice.
Voor **`gebruikersgroep` is het een domeinbesluit**: het vraagt óf (a) de gebruikersgroep component-breed
maken (zoals `organisatiegebruik` al is — likara-domeinmodel §LI034: *"het schrijf-slot is component-breed"*),
óf (b) het signaal type-scopen zoals `bedrijfsfunctie` dat doet, óf (c) het punt aanvaarden als niet-dekbaar.
Ik heb **geen** van die drie gekozen. Zie open vraag 1.

### 2.4 Veld-ankers — dekking tegen de feiten uit 2.2

`VELD_ANKERS = ['eigenaar', 'biv', 'levensfase', 'bedoeling', 'beschrijving']` (detailIngang.js:34).
Een onbekend anker is een **luide fout** (`detailRoute` throwt, :51-53) — een producent merkt het direct.

| Feit | Veld-anker? | Landing |
|---|---|---|
| `eigenaar` | ✓ `eigenaar` | gemarkeerd op Overzicht + Bewerken-knop ernaast |
| `biv` | ✓ `biv` | idem |
| `levensfase` | ✓ `levensfase` | idem |
| `bedoeling` | ✓ `bedoeling` | idem |
| **`hosting`** | **✗ ontbreekt** | Hostingmodel staat wél op het Overzicht (:410-411) maar zónder `id="veld-hosting"` en zonder markering → alleen "open het hele Bewerken-formulier" |
| `verantwoordelijke` · `gebruikersgroep` · `bedrijfsfunctie` · `koppelingen` · `contract` | n.v.t. (tab-feiten) | via `tab`-aanleiding |

⚠ **`hosting` is het enige norm-feit met een Overzicht-veld maar zónder anker.** Het is geen
default-verplicht feit, dus het valt vandaag in blok 2 ("netjes") — maar de tenant kán het verplicht zetten
(NormBeheer.vue), en dan levert besluit 10 een punt zonder gerichte landing. `beschrijving` is het spiegelbeeld:
een anker **zonder** norm-feit (geen `HARDE_FEIT`).

### 2.5 Feiten die voor een type betekenisloos zijn

**Eén feit: `bedrijfsfunctie`, voor de drie niet-`ondersteunt_werk`-typen** (database, server_compute,
integratievoorziening).

**Waaraan je dat in de code ziet:** het signaal `_SIG_GEEN_BF` wordt in `badge_voor_component` alleen gezet
als het componenttype in `_ondersteunt_werk_typen()` zit (registratiegaten_service.py:227-243). Omdat
`_beslis_vastgesteld` voor dit feit "vastgesteld ⟺ signaal afwezig" hanteert (`:159-160`), telt het feit voor
die typen **altijd** als vastgesteld. De registratiekant sluit hetzelfde af
(`functievervulling_service.py:107-111`). De twee kanten zijn dus **consistent** — dit is het enige feit dat
netjes type-gescoped is, en het is precies het model dat `gebruikersgroep` mist (2.3).

⚠ **Bestaand UX-gat, niet veroorzaakt door dit ontwerp:** de **Bedrijfsfunctie-tab wordt onvoorwaardelijk
getoond** (:207) en `ComponentBedrijfsfunctieSectie` gate't de koppel-actie **alleen op rol**, niet op
`ondersteunt_werk` (ComponentBedrijfsfunctieSectie.vue:34, :273). Op een database ziet de gebruiker dus een
toevoegregel die bij opslaan 422 geeft — een schending van picker-regel 1 (likara-frontend §ZoekSelect-patronen:
*"toon nooit een optie die bij opslaan een 422 oplevert"*). Gemeld, niet gerepareerd.

---

## Blok 3 — De kopknop (besluit 6)

### 3.1 De knopgroep vandaag

Bouwsteen `DetailKop.vue` levert drie zones (`#badges`, `#acties`, `#destructief`, DetailKop.vue:40-53); de
consument levert de knoppen. In `ComponentDetail.vue:346-376`, in deze volgorde:

| # | Knop | Vorm | Conditie | Vindplaats |
|---|---|---|---|---|
| 1 | **Bewerken** | primary (default) | `magBewerken` | :347 |
| 2 | Start beoordeling | secondary | `magStarten` (checklist-dragend + concept) | :349-356 |
| 3 | Klaar verklaren / Heropenen | secondary | `magKlaarverklaren && isChecklistDragend` | :357-363 |
| 4 | **Bekijk op kaart** | secondary | `magKaartZien` | :365-371 |
| 5 | Geschiedenis (`ObjectHistoriePaneel`) | eigen 'i'-knop | altijd | :372 |
| — | Verwijderen | danger, **eigen zone** | `magVerwijderen` | :374-376 |

Besluit 6 plaatst "Open punten" **vóór** #4 — dus tussen de statusovergangen en de navigatie. Dat strookt met
de zone-documentatie van de bouwsteen (`#acties` = object-actie → statusovergangen → navigatie,
DetailKop.vue:13-17). ⚠ **Vormkeuze niet vastgesteld:** besluit 6 zegt "in de lichte knopgroep"; de
knopstandaard (likara-frontend §Knopstandaard) kent `secondary` (nevenactie) en `text` (navigatie/doorklik,
mét pijl). Alle bestaande lichte knoppen hier zijn `secondary`. Zie open vraag 4.

### 3.2 Het rode signaleringsbolletje — reikwijdte van het verwijderen

**Consumenten: precies één.** `SignaleringBadge` wordt geïmporteerd op ComponentDetail.vue:44 en gemount op
:344 — **nergens anders** in `frontend/src` of `modules/` (grep over `*.vue`/`*.js`). Ook de databron
`api.signalering.badgeComponent` (api.js:362) heeft **één** aanroeper (ComponentDetail.vue:131). Het bolletje
wordt **niet** hergebruikt op het lijstscherm of de kaart.

**Wat er verloren gaat als het van het componentdetailscherm verdwijnt:**

1. **De tooltip met signaalnamen.** De badge toont bij hover de concrete namen via `SIGNAAL_LABEL`
   (SignaleringBadge.vue:18-26). Een teller op een knop draagt dat niet.
2. **Het onderscheid kritiek (🔴) / aandacht (🟡).** De knop-teller telt per besluit 6 alleen "Dit moet nog";
   de ernst-as van ADR-035 verdwijnt van dit scherm.
3. **Drie signalen die géén norm-feit zijn en dus in géén blok landen.** De badge dekt 7 signalen
   (registratiegaten_service.py:245-261); besluit 7 laat `object_zonder_roltoewijzing` bewust vallen; blijven
   over: **`component_geisoleerd`** (landt in blok 3 per besluit 2) en — bij de vijf feit-signalen — geen
   verlies. Netto verdwijnt er dus **geen** signaal uit beeld, mits blok 3 `component_geisoleerd` draagt.
4. **De component `SignaleringBadge.vue` zelf wordt daarmee ongebruikt** — geen enkele andere consument.
   Verwijderen of laten staan is een aparte opruimkeuze; **ik heb niets verwijderd.**

**Tenant-breed blijft alles bestaan:** `SignaleringView.vue` leest `api.signalering.registratiegaten()`
(api.js:361) — een andere, ongewijzigde bron. Besluit 7 raakt die niet.

### 3.3 Draagt elke detailscherm de gedeelde kop?

**Ja, en het is met een scan afgedwongen.** `DetailKop.vue` documenteert dat een eigen actiebalk verboden is
(DetailKop.vue:9-10) en `frontend/scripts/check-css-build.mjs` bevat de detailkop-bron-scan (likara-frontend
§LI040: *"elk `*Detail*`-scherm gebruikt `<DetailKop>`; de object-acties mogen uitsluitend binnen dat blok"*;
8 consumenten). **Geen consument met eigen kopknoppen aangetroffen.**

⚠ **Consequentie voor besluit 6:** de knop is een **component-specifieke** actie en hoort dus in
`ComponentDetail`'s `#acties`-slot — níét in `DetailKop.vue` zelf (dat zou hem aan alle 8 detailschermen
opdringen, terwijl alleen componenten een norm kennen). De scan verzet zich daar niet tegen (hij eist dat de
acties *binnen* het blok staan, niet dat ze in de bouwsteen leven).

---

## Blok 4 — Het tabblad zelf (besluiten 2, 3, 4, 5)

### 4.1 Tabrij-opbouw en de tweede plek

`topTabs` is een `computed` die een array opbouwt (ComponentDetail.vue:202-226) en aan de gedeelde `AppTabs`
wordt gevoerd (:384-390). Een tabblad op de **tweede** plek, voor **elk** componenttype, vereist één regel
**tussen** :203 en :207:

```js
const t = [{ key: 'overzicht', label: 'Overzicht' }]
// ← hier: { key: 'open-punten', label: `Open punten (${n})` }   — onvoorwaardelijk (besluit 9)
t.push({ key: 'bedrijfsfunctie', label: 'Bedrijfsfunctie' })
```

`AppTabs` accepteert vrije `{key, label}`-paren (AppTabs.vue:15) — een teller **in het label** vraagt geen
wijziging aan de bouwsteen. ⚠ Wel: het label wordt dan **reactief** (het getal beweegt mee met een mutatie in
een ander tabblad), waar alle bestaande labels statisch zijn. Dat is nieuw gedrag voor `AppTabs`, maar geen
breuk.

⚠ **De `watch(topTabs)`-valgrens** (:231-233) zet `activeTop` terug op `'overzicht'` zodra de actieve tab uit
de set verdwijnt. Omdat het nieuwe tabblad onvoorwaardelijk is, kan het nooit verdwijnen — geen interactie.

### 4.2 Leeft de actieve tab in het adres? — **ja, en het werkt voor dit tabblad zonder uitbreiding**

- **Lezen:** `_initVanafQuery` (:246-264) zet `activeTop` uit `route.query.tab` als de key in `topTabs` zit
  (:247-248).
- **Schrijven:** de watch op `[activeTop, activeCat]` (:276-285) schrijft `?tab=` terug met `router.replace`
  (geen history-spam); Overzicht = schone URL (:279).
- **Aanleiding-taal:** `AANLEIDING_SLEUTELS = {tab, cat, markeer, bewerk, veld}` (detailIngang.js:29) — `tab`
  zit er al in. **`detailRoute('component', id, { tab: 'open-punten' })` werkt dus vandaag al**, mits de key
  in `topTabs` bestaat. Geen wijziging aan `detailIngang.js` nodig voor besluit 5.

**Deelbaar en herstelbaar: ja.** Terugkeren op dit tabblad (besluit 5) volgt automatisch uit de bestaande
terugschrijf — de URL draagt `?tab=open-punten`, en `_initVanafQuery` leest hem terug.

### 4.3 "Dit moet nog" altijd open bij binnenkomst (besluit 4)

**De poort bestaat**: `_binnenkomstVerwerkt` (:273) houdt de URL-terugschrijf dicht tot de aanleiding gelezen
is (:277), gezet in de `props.id`-watch (:316, :322). Dit is de LI046-"de bezoeker wint"-poort.

**Moet het nieuwe tabblad erop aanhaken? — Nee, en juist dát is de crux.** Besluit 4 zegt dat het
**sub**-tabblad ("Dit moet nog") **geen** momentkeuze onthoudt. De veilige vorm is dus dat de sub-blok-state
**niet in de URL en niet in sessionStorage** landt:

- de watch op :276 mag **niet** worden uitgebreid met de sub-blok-state (anders keert de gebruiker terug op
  het laatst geopende blok — precies wat besluit 4 verbiedt);
- er is geen `useLijstStaat` op `ComponentDetail` (grep: geen treffer), dus geen bestaand
  momentstaat-mechanisme dat het per ongeluk oppikt;
- de sub-blok-`ref` moet **resetten op elke binnenkomst**, dus in de `props.id`-watch (:315-323) — anders
  houdt een component→component-hop de vorige blok-keuze vast (de instance wordt hergebruikt, likara-frontend
  §Detail-navigatie watch-patroon).

⚠ Als het sub-blok als **tweede `AppTabs`** wordt gebouwd (zoals de checklist-categorieën, :533-540), erft het
**niet** automatisch de `activeCat`-URL-koppeling — die is expliciet aan `cat` gekoppeld (:280). Goed: er is
niets om uit te zetten, maar het moet **bewust** zo blijven.

### 4.4 Norm-aanduiding — wat moet het scherm mounten?

**Het mechanisme:** `useNormLat()` laadt `GET /component-normen` en levert `verplichtPerFeit`
(useNormLat.js:13-26); `ComponentDetail` roept `laadNorm()` (:128) en doet `provide('normVerplicht', …)`
(:63); `VeldUitleg` **injecteert** dat en beslist zélf op zijn `norm-feit`-prop of de "telt mee"-passage
verschijnt (VeldUitleg.vue:33, :45).

**Voor het nieuwe tabblad:** het leeft **binnen** `ComponentDetail`, dus de `provide` op :63 dekt het al —
**er hoeft niets extra ge-provide't te worden**, mits het tabblad een child-component van `ComponentDetail`
is. Wat het scherm zélf moet doen: elke feitregel die een `VeldUitleg` draagt de **juiste `norm-feit`-sleutel**
meegeven (er is geen globale scan die dat afdwingt — OPVOLGPUNTEN LI045-2/3).

⚠ **Maar de aanduiding is hier waarschijnlijk misplaatst.** De passage luidt *"Dit feit telt mee om dit
systeem klaar te kunnen verklaren. Opslaan kan wel zonder."* (VeldUitleg.vue:R-constante). Op een scherm dat
**per definitie** alleen genormeerde feiten in blok 1 toont, herhaalt die zin zich op elke rij — precies het
LI039-anti-patroon *"informatie die overal hetzelfde is, is geen informatie"* (likara-ux §LI039). De
LI045-regel is bovendien **één aanduiding per feit, op het kleinste omvattende element** (likara-ux §LI045) —
dat pleit voor **één** aanduiding op de blok-kop, niet per rij. Zie open vraag 5.

**De tellende test die erbij hoort** (bestaande vorm): `expect(w.findAll('[data-norm-lat]').length).toBe(N)`
— nu 2 op `ComponentDetail` (ComponentDetail.test.js:574) en 2 op `ComponentFormulier`
(ComponentFormulier.test.js:379). Een nieuw tabblad **verhoogt die bestaande telling** en breekt dus de
huidige assert; die moet meebewegen (en de nieuwe test telt het aantal genormeerde feiten dát het tabblad toont).

### 4.5 Feitnamen — komen ze uit de gedeelde labelbron?

`NORM_FEIT_LABEL` (labels.js:326-337) is de bron, met vier bestaande consumenten: `SignaleringView.vue:143`,
`MigratiegereedheidSectie.vue:53-55, :74`, `NormBeheer.vue:50, :125`, `ComponentBedrijfsfunctieSectie.vue:225`
(de LI045-brug-ondertitel). **Een nieuw overzicht moet daar uit putten** (LI045-brugregel).

**Plekken waar hetzelfde feit onder een andere naam zou verschijnen** (bevestigt en verfijnt LI046 Blok 7.4):

| Feit | `NORM_FEIT_LABEL` | Andere naam in beeld | Vindplaats |
|---|---|---|---|
| `bedoeling` | "Bedoeling (migratiepad)" | **"Bedoeling"** op het Overzicht · uitleg-sleutel `migratiepad` | ComponentDetail.vue:436 · ComponentFormulier.vue:42 |
| `verantwoordelijke` | "Verantwoordelijke" | tabkop **"Verantwoordelijkheden"** | ComponentDetail.vue:222 |
| `bedrijfsfunctie` | "Bedrijfsfunctie" | sectiekop **"Waarvoor gebruiken we het"** (bewust — mét feit-ondertitel, LI045-brug) | ComponentBedrijfsfunctieSectie.vue:216-225 |
| `gebruikersgroep` | "Gebruikersgroep" | tabkop **"Gebruikersgroepen"** (meervoud — geen afwijking per LI045) · ⚠ **"Gebruik"-tab dekt dit feit NIET** (dat is `organisatiegebruik`) | ComponentDetail.vue:212, :218 |
| `hosting` | "Hostingmodel" | "Hostingmodel" op Overzicht — **gelijk** ✓ | ComponentDetail.vue:410 |
| `koppelingen` | "Koppelingen" | tabkop "Koppelingen" — **gelijk** ✓ | ComponentDetail.vue:213 |
| `contract` | "Contract" | tabkop **"Contracten"** (meervoud) | ComponentDetail.vue:221 |

Enkelvoud/meervoud geldt per LI045 **niet** als afwijking. Het echte risico is **`bedoeling`** (drie namen,
één feit) en de **verwarring Gebruik ↔ Gebruikersgroep**.

---

## Blok 5 — Meting op de dev-database

**Tenant:** één, `11111111-1111-1111-1111-111111111111` · **19 componenten** (16 applicatie, 1 database,
1 fileshare, 1 saas_dienst).

### 5.1 Is `component_norm` nog steeds leeg? — **ja, bevestigd.**

```sql
SELECT 'component',count(*) FROM component
UNION ALL SELECT 'component_norm',count(*) FROM component_norm
UNION ALL SELECT 'component_klaarverklaring',count(*) FROM component_klaarverklaring
UNION ALL SELECT 'component_bevinding',count(*) FROM component_bevinding
UNION ALL SELECT 'tenant',count(*) FROM tenant
UNION ALL SELECT 'checklistscore',count(*) FROM checklistscore;
```
| tabel | rijen |
|---|---:|
| component | 19 |
| **component_norm** | **0** |
| component_klaarverklaring | 5 |
| component_bevinding | 3 |
| tenant | 0 |
| checklistscore | 267 |

**Tweede, nieuwe stale-bevinding:** alle 267 checklistscores staan op `ja`
(`SELECT score::text,count(*) FROM checklistscore GROUP BY 1;` → `ja|267`), en de enige blokkade is
`opgelost` op Zaaksysteem. De seed schrijft voor Zaaksysteem echter `blokkeer=1` voor
(dev_seed_testdata.py:1132: `score = "nee" if i < blokkerend else "ja"`), **zonder** een resolutie-stap in
`_seed_bvowb_scenario`. **Oorzaak niet vastgesteld** (read-only; niet gediagnosticeerd, niet hersteld).
Gevolg voor dit ontwerp: **blok 3 "Dit valt op" heeft nu géén checklistregel om te tonen** op enig component.

**Wat een reseed zou herstellen** (niet uitgevoerd): `seed_component_norm` schrijft 10 rijen — de vijf
`DEFAULT_VERPLICHT` op `true` (seed.py:179-199) — en `_seed_bvowb_scenario` zet daarna **`bedoeling` óók op
true** (dev_seed_testdata.py:1794-1800), plus de Zaaksysteem-`nee`. Netto na reseed: **zes verplichte feiten**
+ minstens één checklistpunt.

### 5.2 De drie tellingen per component — twee scenario's

Berekend volgens de besluiten: **mét** bewust-geen-uitsluiting op `koppelingen`/`contract` (besluit 8) en
**zonder** de dubbeltelling van de verantwoordelijke (besluit 7). "Dit valt op" = (checklist nee/deels > 0
→ 1 gebundelde regel) + (staat los in het landschap → 1).

- **Scenario A = huidige DB-stand** (`component_norm` leeg → niets verplicht → `norm_status.feiten = {}`).
- **Scenario B = de norm die de seed hoort te zetten** (zes verplicht: eigenaar · verantwoordelijke · biv ·
  contract · koppelingen · **bedoeling**).

<details>
<summary>Gedraaide query (volledig)</summary>

```sql
WITH f AS (
SELECT c.id, c.naam, c.componenttype,
 (c.eigenaar_organisatie_id IS NOT NULL) AS eigenaar,
 EXISTS(SELECT 1 FROM roltoewijzing r WHERE r.tenant_id=c.tenant_id AND r.object_id=c.id) AS verantwoordelijke,
 (c.biv_beschikbaarheid IS NOT NULL AND c.biv_integriteit IS NOT NULL AND c.biv_vertrouwelijkheid IS NOT NULL) AS biv,
 EXISTS(SELECT 1 FROM relatie s WHERE s.tenant_id=c.tenant_id AND s.relatietype='serving' AND s.bron_id=c.id) AS gebruikersgroep,
 (NOT (cc.ondersteunt_werk) OR EXISTS(SELECT 1 FROM functievervulling fv WHERE fv.tenant_id=c.tenant_id AND fv.component_id=c.id)) AS bedrijfsfunctie,
 (c.levensfase IS NOT NULL) AS levensfase, (c.migratiepad IS NOT NULL) AS bedoeling,
 (c.hostingmodel::text <> 'onbekend') AS hosting,
 (EXISTS(SELECT 1 FROM relatie fl WHERE fl.tenant_id=c.tenant_id AND fl.relatietype='flow' AND (fl.bron_id=c.id OR fl.doel_id=c.id))
   OR EXISTS(SELECT 1 FROM component_bevinding b WHERE b.tenant_id=c.tenant_id AND b.component_id=c.id AND b.soort::text='koppelingen')) AS koppelingen,
 (EXISTS(SELECT 1 FROM relatie a JOIN contract ct ON ct.id=a.doel_id AND ct.tenant_id=c.tenant_id
         WHERE a.tenant_id=c.tenant_id AND a.relatietype='association' AND a.bron_id=c.id)
   OR EXISTS(SELECT 1 FROM component_bevinding b WHERE b.tenant_id=c.tenant_id AND b.component_id=c.id AND b.soort::text='contract')) AS contract,
 (SELECT count(*) FROM checklistscore s WHERE s.tenant_id=c.tenant_id AND s.component_id=c.id AND s.score::text IN ('nee','deels')) AS nee_deels,
 NOT EXISTS(SELECT 1 FROM relatie fl2 WHERE fl2.tenant_id=c.tenant_id AND fl2.relatietype='flow' AND (fl2.bron_id=c.id OR fl2.doel_id=c.id)) AS geisoleerd
FROM component c JOIN componentconfig_optie cc ON cc.optie_sleutel=c.componenttype AND cc.dimensie='componenttype')
SELECT naam, componenttype, /* B_moet, B_netjes, A_netjes, valt_op, open feiten */ … FROM f;
```
</details>

| Component | type | **A** moet | **A** netjes | **B** moet | **B** netjes | valt op | B: welke feiten open |
|---|---|:-:|:-:|:-:|:-:|:-:|---|
| Extern SaaS-platform | saas_dienst | 0 | 9 | **6** | 3 | 1 | eigenaar, verantw, biv, contract, koppel, bedoeling |
| Shared fileshare | fileshare | 0 | 9 | **6** | 3 | 1 | eigenaar, verantw, biv, contract, koppel, bedoeling |
| Aangiften | applicatie | 0 | 8 | 5 | 3 | 1 | verantw, biv, contract, koppel, bedoeling |
| Reisdocumenten | applicatie | 0 | 6 | 5 | 1 | 1 | verantw, biv, contract, koppel, bedoeling |
| Shared DB-server | database | 0 | 7 | 5 | 2 | 1 | verantw, biv, contract, koppel, bedoeling |
| Verkiezingen | applicatie | 0 | 8 | 5 | 3 | 1 | verantw, biv, contract, koppel, bedoeling |
| **Archiefbeheer** | applicatie | 0 | 7 | 4 | 3 | 1 | eigenaar, verantw, biv, bedoeling |
| Omgevingsloket | applicatie | 0 | 4 | 3 | 1 | 1 | biv, koppel, bedoeling |
| Vergunningensysteem | applicatie | 0 | 6 | 3 | 3 | 1 | biv, koppel, bedoeling |
| BRP | applicatie | 0 | 3 | 2 | 1 | 0 | biv, bedoeling |
| Burgerzaken-suite | applicatie | 0 | 3 | 2 | 1 | 0 | biv, bedoeling |
| DMS | applicatie | 0 | 2 | 2 | 0 | 0 | biv, bedoeling |
| Financieel systeem | applicatie | 0 | 4 | 2 | 2 | 0 | biv, bedoeling |
| Gegevensmakelaar | applicatie | 0 | 5 | 2 | 3 | 0 | biv, bedoeling |
| Sociaal domein suite | applicatie | 0 | 3 | 2 | 1 | 0 | biv, bedoeling |
| Zaakafhandelcomponent | applicatie | 0 | 4 | 2 | 2 | 0 | biv, bedoeling |
| Zaaksysteem | applicatie | 0 | 2 | 2 | 0 | 0 | biv, bedoeling |
| Klantportaal | applicatie | 0 | 1 | 1 | 0 | 0 | bedoeling |
| **HR-systeem** | applicatie | 0 | 3 | **0** | 3 | **1** | — |

**Het verschil tussen A en B is het hele ontwerp:** in de huidige stand is **"Dit moet nog" op élk van de 19
componenten leeg** en valt alles in blok 2. Een browsercheck vóór reseed toont dus 19× een leeg eerste
tabblad — een vals beeld dat als "werkt niet" leest.

⚠ **`valt op` is in beide scenario's identiek en komt volledig uit "staat los in het landschap"** (10
componenten); de checklistcomponent is 0 (zie 5.1).

### 5.3 De drie browsercheck-gevallen

| Rol | Component | Waarom |
|---|---|---|
| **Schoon geval** | **HR-systeem** | B: 0 in "moet nog" — het ijkbeeld dat het eerste blok rustig leeg is. ⚠ **Maar het draagt 1 punt in "Dit valt op"** (staat los, ondanks bewust-geen-koppelingen) — zie kernbevinding 4. Als dat blijft staan, is dit **geen** schoon geval meer voor het scherm als geheel. |
| **Rijkste geval** | **Extern SaaS-platform** en **Shared fileshare** (elk 6) | ⚠ Beide zijn **niet-checklist-dragend én niet-applicatie** — precies de typen waar besluit 9 en besluit 10 samen bijten: 6 punten, waarvan `koppelingen` géén plek heeft (frontend-conditie) en `gebruikersgroep` in blok 2 zit zonder plek (backend-weigering). Het rijkste geval is dus tegelijk het **moeilijkste**. Als een checklist-dragend geval nodig is: **Archiefbeheer** (4 moet, klaar verklaard, mét bevindingen). |
| **Bewust-geen** | **Archiefbeheer** (koppelingen + contract) en **HR-systeem** (koppelingen) | Archiefbeheer toont beide soorten tegelijk én is klaar verklaard mét afwijking-snapshot `{biv,eigenaar,verantwoordelijke}` — het rijkste bewijs dat de uitsluiting werkt. |

Klaarverklaring-snapshots (ongewijzigd t.o.v. LI046):
`Archiefbeheer {biv,eigenaar,verantwoordelijke}` · `DMS {biv}` · `Zaaksysteem {biv}` · `HR-systeem {}` ·
`Klantportaal {}`.

### 5.4 Draagt de dev-data een component waarvoor besluit 10 bijt? — **ja, drie.**

| Component | type | Punt zonder plek | Aard |
|---|---|---|---|
| **Shared fileshare** | fileshare | `koppelingen` (B: open) | frontend-conditie → frontend-slice |
| **Extern SaaS-platform** | saas_dienst | `koppelingen` (B: open) | frontend-conditie → frontend-slice |
| **Shared DB-server** | database | `koppelingen` (B: open) | frontend-conditie → frontend-slice |

Voor `gebruikersgroep` bijt het **in de huidige norm niet** (het feit is niet verplicht en valt in blok 2),
maar het staat wél als open punt in blok 2 op alle drie — met dezelfde ontbrekende plek, en dáár is de
blokkade een **backend-weigering** (Blok 2.3). Zet de tenant `gebruikersgroep` verplicht, dan verhuist het
naar blok 1 en is het onbeantwoordbaar.

---

## Blok 6 — Verrassingen en risico's

Wat een naïeve bouw op de tien besluiten stukmaakt:

1. **Stille dubbeltelling / zichtbare tegenspraak: `koppelingen` staat in twee blokken tegelijk.**
   Blok 1 zegt "vastgesteld (bewust geen)", blok 3 zegt "staat los in het landschap" — over hetzelfde feit,
   op hetzelfde scherm. Bevestigd op HR-systeem. **Dit is geen randgeval maar het schone geval.**

2. **Twee waarheden dreigen bij de teller.** De knop staat in de kop, de lijst in een tabpanel. Twee losse
   `status()`-aanroepen leveren na een mutatie in het tabblad verschillende getallen. De LI041-norm
   (*teller en lijst delen één filterwaarheid*) vraagt één laadpunt + een bronscan-test; zonder dat is dit
   exact de fout die LI040/LI041 driemaal moesten repareren.

3. **Besluit 8 is vandaag een tekst-regel, geen invariant.** De bewust-geen-uitsluiting leeft in twee
   hardcoded literals (`:131`, `:192`) náást een wél-afgeleide derde formulering (`:208`). Volgens
   werkprotocol §KERNLES LI038 vierde geval — *"staat een regel 'in elke tak moet je X doen', dan is X
   vergeten wachten te gebeuren"* — hoort dit **één** afgeleide bron te worden (`ComponentBevindingSoort`),
   niet nóg een tak. Ongewijzigd erft een nieuw feit de regel niet.

4. **Besluit 10 botst op een domeingrens die het besluit niet noemt.** "De plek wordt gegeven" is voor
   `koppelingen` een frontend-slice, maar voor `gebruikersgroep` een **backend-weigering**
   (gebruikersgroep_service.py:383). Bouwen zonder dat besluit levert óf een tab die 404 geeft, óf een stil
   verzwegen punt — beide in strijd met besluit 10 zelf.

5. **De code spreekt de opdracht op één punt tegen — besluit 3 ("een blok met nul punten blijft bestaan").**
   Voor blok 2 ("Dit zou netjes zijn") **bestaat de bron niet**: `norm_status` levert uitsluitend verplichte
   feiten (`:120`, `:152`). Een blok dat altijd bestaat, moet gevuld kunnen worden — dat vraagt een
   uitbreiding van de leeslaag, niet alleen een frontend-blok. Dit is geen tegenspraak in het besluit maar
   een ontbrekende grond die de opdracht als aanwezig veronderstelt.

6. **De demostaat kan de besluiten niet aantonen.** `component_norm` = 0 → blok 1 is 19× leeg (scenario A);
   alle scores `ja` → blok 3 draagt geen checklistregel. Per werkprotocol §Browsercheck (LI044: *"seed de
   demostaat zó dat de browsercheck iets te zien geeft"*) is een reseed een **voorwaarde** voor de
   browsercheck, niet een nette-bijkomstigheid.

7. **De bestaande tellende norm-lat-tests breken.** `ComponentDetail.test.js:574` assert exact 2
   `[data-norm-lat]`-elementen. Een tabblad dat norm-feiten toont verhoogt dat getal — de assert moet
   bewust meebewegen, anders leest een terechte rode test als "de bouw is stuk".

8. **Regels die alleen in tekst bestaan en dus niet erven** (geen bouwsteen, geen scan): de norm-aanduiding
   per scherm (OPVOLGPUNTEN LI045-2/3), "max één primary per scherm", en — nieuw — de blok-indeling zelf. Wie
   later een vierde blok toevoegt, erft geen enkele regel over welke bron welk blok voedt.

---

## Open ontwerpvragen voor Bert

1. **`gebruikersgroep` op een niet-applicatie-component is backend-zijdig geweigerd** (404,
   gebruikersgroep_service.py:383), terwijl het signaal dat het punt oplevert géén type-restrictie kent.
   Besluit 10 eist een plek. Welke kant op: de gebruikersgroep component-breed maken (zoals
   `organisatiegebruik` al is), het signaal type-scopen zoals `bedrijfsfunctie` dat doet, of het punt
   aanvaarden als niet-dekbaar voor die zeven typen?

2. **Het schone geval draagt een punt in "Dit valt op".** HR-systeem heeft "bewust geen koppelingen" → 0 in
   "Dit moet nog", maar "staat los in het landschap" vuurt wél (dat signaal honoreert de bevinding niet).
   Moet een bewuste vaststelling óók blok 3 dempen, of is "staat los" een observatie die losstaat van de
   vraag of iemand er al naar gekeken heeft?

3. **Blok 2 ("Dit zou netjes zijn") heeft vandaag geen bron:** `norm_status` levert uitsluitend de
   **verplichte** feiten. Wil je dat de bestaande afleiding wordt uitgebreid zodat ze óók de niet-verplichte
   feiten evalueert (één bron, twee filters), of wordt blok 2 een aparte lezing?

4. **Vorm van de kopknop:** de lichte knoppen in de kop zijn nu alle `secondary`; de knopstandaard reserveert
   `text` (mét pijl) voor navigatie/doorklik. "Open punten" navigeert naar een tabblad op hetzelfde scherm —
   `secondary` (nevenactie) of `text` (doorklik)?

5. **Norm-aanduiding op het nieuwe tabblad:** de "telt mee om klaar te kunnen verklaren"-passage per feitregel
   herhaalt zich op elke rij van blok 1 (elk feit is er per definitie een norm-feit) — het LI039-anti-patroon
   *"informatie die overal hetzelfde is, is geen informatie"*. Eén aanduiding op de blok-kop, of per rij?

6. **Een component zónder klaarverklaring heeft geen bevroren snapshot**, dus geen bewust/verschoven-onderscheid
   (`afwijking_voor_component` geeft dan beide leeg, component_norm_service.py:264-266). Voor 14 van de 19
   dev-componenten is dat de stand. Is "Dit moet nog" daar simpelweg één neutrale lijst, of wil je ook dáár
   iets van het onderscheid tonen?

7. **`hosting` is het enige norm-feit met een Overzicht-veld maar zónder veld-anker**
   (VELD_ANKERS, detailIngang.js:34). Krijgt het er een — of blijft het bij "open het hele Bewerken-formulier"
   zolang het niet default-verplicht is?

8. **De reseed** (component_norm = 0 én alle scores op `ja`, waardoor blok 1 én blok 3 leeg tonen): uitvoeren
   vóór de bouw, of vóór de browsercheck? En wil je dat ik de oorzaak van de drift eerst read-only uitzoek?

*(STOP na dit rapport. Geen vervolgstap gebouwd, niets gewijzigd, niet gecommit.)*
