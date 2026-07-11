---
name: likara-ux
description: Interaction-design-denkmethode voor LIKARA. Verplicht te raadplegen bij ELKE frontend-rakende slice (nieuw scherm, nieuwe sectie, nieuwe actie) — door zowel CC als claude.ai. Borgt dat een functie de UI logisch en compleet houdt voor de gebruiker: geen lege lijsten zonder route naar de actie, actie op de plek waar de gebruiker hem verwacht, terminologie vanuit de gebruiker. Dit is GEEN stijl-/visuele skill (dat is likara-frontend); dit gaat over of het scherm doet wat de gebruiker verwacht.
bijgewerkt: V024
---

# LIKARA UX / Interaction-Design Skill

## Kernprincipe (niet-onderhandelbaar)

**Gebruikerservaring is altijd het startpunt.**
Elke ontwerpbeslissing, elke afweging en elk advies vertrekt vanuit de vraag:
*wat is het beste voor de gebruiker van LIKARA?*
Schema, migraties, RBAC en technische borging zijn vangrails die de UX-keuze
ondersteunen — ze sturen hem niet.

Dit principe overschrijft technische voorkeur als de twee conflicteren.

### Functioneel beschrijven is de NORM, niet de uitzondering (DC014, niet-onderhandelbaar)

Elke vraag, elk advies, elke afweging en elke analyse — door CC én claude.ai — vertrekt
vanuit de gebruiker van LIKARA: *wat betekent dit voor de gebruiker, wat ziet/doet hij?*
Techniek (schema, endpoints, RLS, RBAC, migraties) komt **alleen** ter sprake als (a) de
gebruiker er expliciet om vraagt, of (b) als vangrail bij een gate/borging — **nooit als
opening of toon** van een antwoord. Een advies dat begint bij de tabel of het schema is
fout, óók als het technisch klopt: herformuleer het vanuit wat de gebruiker wil bereiken.

## Waarom deze skill bestaat

LIKARA wordt gebouwd vanuit één vast uitgangspunt: **continu optimaliseren van de
gebruikerservaring.** Techniek, schema en proces zijn vangrail, nooit het vertrekpunt.
Deze skill maakt dat uitgangspunt operationeel voor het scherm: bij elke functie die de
UI raakt, eerst denken vanuit wat de gebruiker ziet, verwacht en wil doen — pas daarna bouwen.

## Vast uitgangspunt — GENERIEK multi-tenant platform (niet-onderhandelbaar)

LIKARA/CompliMan is een **generiek multi-tenant platform**. **BWB** is slechts een
voorbeeld van een organisatie die het gebruikt; **Tiel** een voorbeeld van een
ontvlechtingscontext. Ontwerp platform, datamodel, schermen, terminologie en features
**nooit** alsof ze BWB/Tiel-specifiek zijn — alles is **tenant-agnostisch en herbruikbaar**
voor elke tenant. BWB/Tiel dienen uitsluitend als concreet voorbeeld om scenario's te
toetsen, niet als ontwerpdoel. Concreet: geen hardcoded organisatie-/operatornamen,
geen aannames over één specifieke ontvlechting, labels en velden algemeen genoeg voor
elke overheidsorganisatie. Dit geldt platform-breed (ook backend/db/frontend), maar staat
hier omdat het ontwerp-denken ermee begint.

### Eén tenant nu — géén tenant-onderscheid in deze fase (DC014, niet-onderhandelbaar)

"Tenant-agnostisch" (hierboven: niet BWB/Tiel hardcoden) is **niet** hetzelfde als
"ontwerp voor meerdere gelijktijdige tenants met per-tenant-verschillen". LIKARA draait nu
als **één implementatie met één gebruikerswereld**; er is **geen functioneel
tenant-onderscheid**. Dus:

- **Niet vooruit ontwerpen op meerdere tenants** en niet de **"per-tenant"-reflex** inzetten
  bij vragen over rechten, catalogi of zichtbaarheid. Voorbeeld: RBAC is één platform-brede
  matrix (geen per-tenant-rechtenvariatie); catalogi zijn gedeeld, niet per-tenant
  gedifferentieerd, tenzij de gebruikerslogica dat écht vraagt.
- **RLS / tenant-isolatie blijft technisch bestaan als fundament** (`tenant_id` + policies) —
  maar het is **geen ontwerp- of gespreksonderwerp** tot er echt meerdere tenants zijn.
  Verschijnt "per tenant" in een advies/analyse zonder dat de gebruiker erom vroeg, dan is
  dat bijna altijd de verkeerde abstractie voor deze fase: herformuleer vanuit de ene
  gebruikerswereld.
- Verenigbaar met het bovenstaande: bouw **generiek** (geen hardcoding), maar voeg **geen
  per-tenant-differentiatielogica** toe zolang er één tenant is.

Twee concrete missers die deze skill voorkomt (DC012):
1. **Partij-detailscherm met drie leeslijsten en geen enkele toevoeg-knop.** De gebruiker
   verwachtte afdelingen/personen te kunnen toevoegen op de plek waar ze getoond worden,
   maar moest naar een ander scherm en daar de relatie handmatig terugleggen.
2. **Rollen (catalogus) wel beheerbaar in de backend, maar geen beheerscherm.** De functie
   bestond technisch, maar was voor de gebruiker onvindbaar/onbruikbaar.

In beide gevallen waren de tests groen en het datamodel correct — en tóch was de functie
voor de gebruiker niet af. Daar is deze skill voor.

---

## De denkmethode (loop dit af vóór je een frontend-slice ontwerpt of bouwt)

### 1. Gebruikersdoel
Wat wil de gebruiker hier bereiken? Formuleer het als een zin in gebruikerstaal,
niet in datamodel-/schema-taal. ("Ik wil zien wie verantwoordelijk is voor deze
applicatie" — niet "ik wil de roltoewijzing-relaties van dit element ophalen".)

### 2. Wat moet de gebruiker hier kunnen
Som de handelingen op die de gebruiker logischerwijs op dit scherm verwacht: zien,
toevoegen, wijzigen, verwijderen, doorklikken. **Een lijst die iets toont, roept bijna
altijd de verwachting op dat je er ook iets aan kunt toevoegen** — tenzij expliciet en
zichtbaar gemaakt is dat dat ergens anders gebeurt.

### 3. Acties op de juiste plek
De gebruiker verwacht een actie op de plek waar het onderwerp leeft. Een afdeling
toevoegen aan een organisatie hoort op de organisatie-pagina, niet op een generiek
aanmaakscherm waar je de organisatie terug moet kiezen. Voorinvulling van context
(de organisatie staat al ingevuld) is een teken van goede plaatsing.

### 4. Lege staten
Elke lege lijst krijgt een lege-staat die óf een route naar de actie biedt ("+ Toevoegen"),
óf uitlegt waarom hij leeg is en waar de actie dan wél zit ("Rollen wijs je toe vanaf de
applicatie of het contract."). **Een lege lijst zonder knop en zonder uitleg is een bug,
geen neutrale toestand.**

> **Picker-patronen (keuzelijsten).** Vier beproefde regels voor `ZoekSelect`-pickers staan in
> `likara-frontend` §ZoekSelect-patronen (V030): (1) **picker-scope spiegelt de backend-regel** —
> toon nooit een optie die bij opslaan een 422 geeft; (2) **bewerken leest uit de actuele bron** +
> `initieel-weergave` zodat een voorgevuld id ook zijn naam toont; (3) **search-first
> create-in-lege-zoekstaat** — aanmaken pas in de lege zoekuitkomst, met vergevingsgezinde zoek
> tegen duplicaten; (4) **voorgevuld openen toont de volledige (scope-)lijst** — de voorgevulde
> waarde is een label, nooit een zoekfilter, zodat de gebruiker niet vastzit aan zijn bestaande
> keuze; de eerste toetsaanslag vervangt de voorgevulde tekst (LI032).

### 5. Terminologie
Labels en koppen volgen hoe de gebruiker denkt, niet de tabelnamen. "Verantwoordelijkheden",
niet "assignment-relaties". "Wie hoort hierbij", niet "lidmaatschap-FK".

### 6. Consistentie met bestaande schermen
Een nieuwe sectie hoort qua interactie te lijken op vergelijkbare bestaande secties
(zelfde knop-plaatsing, zelfde lege-staat-stijl, zelfde manier van toevoegen/verwijderen),
zodat de gebruiker niet per scherm opnieuw moet leren.

**Identiteit "afdeling — organisatie" / "persoon — afdeling — organisatie" (ADR-036a/037, LI030).**
In ELKE niet-org-gescoopte lijst/picker waar afdelingen of personen verschijnen, toon de
organisatie-context via de gedeelde helper `gebruikersgroepIdentiteit` (`labels.js`) — dit ontdubbelt
gelijknamige afdelingen van verschillende organisaties ("Beheer & Exploitatie — Tiel" vs. "— Culemborg").
Regels: afdeling → "afdeling — organisatie"; persoon → "persoon — afdeling — organisatie" (persoon
zonder afdeling → "persoon — organisatie"). Het **geselecteerde** item in het veld toont dezelfde
identiteit als de lijst (niet uiteen laten lopen). Toegepast op de verantwoordelijke-picker (ADR-037);
nog toe te passen op de ContractFormulier-leverancier-picker + PartijLijst (opvolgpunt).

---

## Toepassing in de praktijk

- **Elke frontend-rakende bouwopdracht** opent met een korte "Wat de gebruiker straks kan"-
  beschrijving (gebruikerstaal, niet schema). Dit is de uitkomst van stap 1–2 hierboven.
- **Bij elke nieuwe lijst/sectie**: expliciet benoemen wat de lege staat toont en of er een
  toevoeg-actie hoort.
- **Bij read-only secties** (zoals "Rollen op objecten" op de partij): de lege-staat-tekst
  wijst de gebruiker naar waar de actie wél plaatsvindt.
- **Bij een nieuwe beheerbare catalogus**: controleer of er een beheerscherm bij hoort —
  een lijst configureerbaar maken in de backend zonder UI laat de functie onvindbaar.

## UX-doorlichting bij een afgeronde feature-reeks (beproefd, DC012)

Na een afgeronde reeks slices loont een **read-only UX-doorlichting** over álle geraakte
schermen, langs de denkmethode hierboven. Bevindingen geprioriteerd:
- **A — storend gat**: de gebruiker kan iets niet wat het scherm wél suggereert (lijst zonder
  toevoeg-route; beheerbare catalogus zonder beheerscherm).
- **B — inconsistentie**: jargon i.p.v. gebruikerstaal, afwijkende kolomkop/term, ontbrekende
  doorklik/sortering t.o.v. vergelijkbare schermen.
- **C — nette to-have**: kleine politoer, geen functioneel gat.
Uit de doorlichting volgen **landbare reparatie-slices** (één bevinding of een kleine bundel
per gate-slice). De doorlichting zelf muteert niets — alleen rapporteren + prioriteren.

**Toets "lijst-zonder-CRUD-op-de-plek-waar-het-leeft = gat"** (DC012 meermaals raak): toont een
scherm een lijst van X'en die daar thuishoren, dan hoort de gebruiker X daar ook te kunnen
toevoegen/wijzigen — tenzij zichtbaar gemaakt is dat het elders gebeurt (dan de lege-staat-route,
stap 4). Een leeslijst zonder die route is bijna altijd een A-gat.

## Landschapskaart UX-patronen (ADR-025, DC013)

### Drie-modus graaf
> **Herzien in ADR-040** (kaart-herbouw): de set-grootte-afgeleide drie-modus is vervangen door een
> **tweedeling met expliciete weergave-state** (Overzicht = centrumloos landschap / Praatplaat =
> radiaal, één centrum + kring) met een zichtbare schakelaar; de **impact-modus is afgeschaft**. De
> concrete weergaven staan in ADR-040; het herbruikbare patroon in P6a (likara-frontend). Onderstaande
> beschrijving is de historische (pre-ADR-040) opzet.

Één view, drie perspectieven via toggle:
- Ego-view: één centrum, directe buren, klik=hercentreren
- Impact-view: migratieset multi-select, raakvlak-detectie
- Geheel model: full-graph, opbouw (leeg→vol) of afpel (vol→leeg)

### Actieve set
De migratieset is een `Set<uuid>` in Vue-state. Toevoegen via zoekresultaten,
verwijderen via rechterpaneel ×-knop. "Voeg alle gefilterde toe" vult de set met het
gefilterde resultaat.

### Resultatenlijst: alleen applicaties (bewuste applicatie-centrische keuze)
De zoeklijst/filters tonen ALLEEN applicaties (+ organisaties); partijen/contracten/infra verschijnen
automatisch als ring-nodes rond de geselecteerde applicaties — nooit als kiesbare entiteiten. Dit is een
**bewuste** keuze (de kaart is applicatie-centrisch), **geen bug**: de kaart component-breed maken is een
eigen ADR-spoor. Zie de applicatie-centrisch-vindplaatsen (`appNodes`/`_isApp`) in likara-frontend/
likara-domeinmodel.

### Selectie highlight
Klik actieve-set-item → `selecteerNode(id)`: `cy.elements().unselect()` →
`cy.getElementById(id).select()` → `cy.animate({ center:{eles:node}, zoom:max(zoom,1.2), 400ms })`.

### Node-detail start leeg
Het detail-paneel toont "Klik een node voor detail" bij mount; vult pas na node-klik of
set-item-klik. Toont o.a. plateau/dispositie (migratieplaatsing) indien gevuld.

### "Open component →" doorklik (gecorrigeerd LI034)
`router.push({ name: 'component-detail', params: { id } })` — knop in de popup én het detail-paneel.
Doorklik-conditie = **één gedeeld predicaat** `_heeftComponentDetail(n) = element_type==='applicatie' ||
laag==='application'` (applicatielaag-componenten, niet alleen strikt `element_type==='applicatie'`); zo
geven popup (`_detailLink`) en zijpaneel **dezelfde** doorklik. Label is **"Open component →"**. (Route
`applicatie-detail` bestaat nog als **redirect** naar `component-detail`, `router/index.js`.)

### Deep-link vanuit component-detail
`<router-link :to="{ name: 'landschapskaart', query: { center: id } }">` "🗺 Open in Landschapskaart →".
LandschapskaartView leest `?center` bij onMounted → praatplaat centraal op dat component. **`?modus` is
vervallen** (de weergave volgt de handeling/set, niet een URL-param).

### Diepte-toggle
"1 stap (direct)" / "2 stappen" (ego + geheel). Diepte 2 voegt de indirecte applicatie-buren
toe (partijen/contracten/infra blijven op diepte 1); client-side op de geladen graaf.

## Vertrekpunt bij schaal — leeg openen, geen betutteling (LI021, niet-onderhandelbaar)

- **Geen scenario-afhankelijke beschermregels.** De gebruiker is geen kleuter: geef de vrijheid
  om alles aan te zetten en desnoods een gigantisch model op te roepen — hij komt zélf tot het
  inzicht weer dingen uit te zetten. Bied een schone **"begin opnieuw"** (set leegmaken → terug
  naar de lege zoek-staat, cache weggooien, vers zoeken) i.p.v. preventieve regels die "in
  scenario X wel, in Y niet" werken. Vrijheid + een goede reset > betuttelende vangrails.
- **Bij schaal opent de kaart leeg, niet op "alles".** De "val terug op alles"-defaults
  (scopebalk niets-aan→alles; startscherm geen-views→hele model) schalen niet — bij 300+
  componenten is het hele model geen rustige beginstand maar de drukte zélf. Vertrekpunt = de
  gebruiker kiest (zoeken/opgeslagen views), niet "hier is alles, filter maar weg".
- **Zoeken op betekenis, niet scrollen.** De set bouw je op via betekenis-zoek
  (naam/type/domein/leverancier/eigenaar-organisatie), zodat "alle zaaksystemen" / "alles van
  Tiel" / "alles van leverancier X" één zoekactie is — niet honderden namen scrollen. (De
  selectie bevat componenten; organisatie/leverancier zijn criteria — zie likara-frontend.)

## Filters, controls en verbergen (ADR-040)

### P6b — Een control die in een weergave niets zinvols doet, hoort verborgen

Toon geen inerte/ruis-controls; erger nog: **nooit een control die stil iets kan wegfilteren dat bij de
weergave hoort**. (Deze sessie: de organisatie-scope-balk is **verborgen op de praatplaat** — daar
bepaalt het centrum + de kring wat je ziet; een organisatiefilter zou daar een kring-organisatie stil
kunnen wegfilteren.)

### P8 — Filter = niet-destructieve lens; set-acties breiden uit; nooit stiekem verbergen

- Een filter **verbergt** (aan) en **toont** (uit) — het gooit **nooit weg**; **uitbreiden** doe je met
  **set-acties**. Consistent in álle weergaven.
- Een filter mag verbergen, maar **nooit stiekem**: elke verberging is het gevolg van een control die op
  dat moment **zichtbaar** is. Daarom: bij een set-wijziging **reset naar "alles aan"** — geen
  nawerkende, onzichtbare uitvink die stil objecten blijft verbergen.

## Verhouding tot andere skills

- `likara-frontend` = hoe je bouwt (Vue/PrimeVue/Tailwind, tokens, presets). Stijl en techniek.
- `likara-ux` (deze) = of het scherm klopt voor de gebruiker. Interaction design.
- Beide raadplegen bij frontend-werk; deze skill gaat over het ontwerp-denken vooraf,
  de frontend-skill over de uitvoering.

## LI023 — Landschapskaart Fase B beginscherm (V024)

### Vier ingangen — structuur

De kaart opent altijd leeg (beginscherm). De gebruiker kiest een startpunt:

1. **Zoeken op component** — naam/type/laag/hosting/eigenaar/leverancier →
   aanvinkbare multi-select dropdown → componenten verschijnen als "In beeld"-chips.
2. **Via leverancier** — doorzoekbare pick → alle componenten van die leverancier in de set.
3. **Via contract** — doorzoekbare pick → alle gekoppelde componenten in de set.
4. **Via gebruikersgroep/context** — pick van (organisatie, afdeling) → componenten in de set.
5. **Opgeslagen views** — eerdere sets direct openen (gelijkwaardige ingang).
6. **Toon het hele landschap** — bewuste, bescheiden actie onderaan.

### Chips = "In beeld" (de set)

- Aangevinkte componenten verschijnen als chips boven de kaart.
- Uitvinken of `×` = component uit de set (niet uit het systeem).
- Chips en graaf-knopen zijn hetzelfde object — één bron van waarheid.
- Actiebalk ("Toon N componenten") staat **bovenaan** het beginscherm (niet sticky-bottom):
  gebruiker kijkt omhoog na aanvinken → actie zit waar de blik al is.

### Set-gestuurd laadmodel

- Niet-lege set → POST `/landschapskaart/subgraaf` → set + 1-hop buren.
- Bij elke set-mutatie wordt de hele set opnieuw opgehaald (idempotent).
- "Begin opnieuw" = harde reset: set leeg + kaart leeg + beginscherm heropend.
- Organisatie/leverancier zijn **filtercriteria**, geen set-leden.
- De kaart laadt NOOIT automatisch het hele landschap (schaalt niet).

### beginschermOpen-vlag

Zichtbaarheid = aparte `beginschermOpen = ref(true)`.
NIET gekoppeld aan `actieveSet.size === 0` — die koppeling veroorzaakte spooksluitingen.
Sluiten = alleen via expliciete gebruikersactie; heropenen = wisSet() + harde reset.

## LI023 — Signalering registratiegaten (ADR-035, V024)

### Doel

De gebruiker ziet direct waar registraties onvolledig zijn. LIKARA stimuleert
volledigheid actief — zonder iets te blokkeren of automatisch aan te passen.

### Twee presentatielagen

- **Badges op entiteiten** — kleine indicator direct op de component/contract/
  gebruikersgroep in lijst of kaart. Gat zichtbaar op de plek waar het hoort.
- **Centraal Signalering-scherm** — overzicht alle openstaande gaten, gesorteerd
  op ernst, met doorkliklink naar de entiteit.

### Tien signaaltypen in twee niveaus

🔴 **Kritiek** (governance direct geraakt):
- Component zonder eigenaar (organisatie)
- Component zonder verantwoordelijke persoon (rol)
- Registratie onvolledig (score onder drempelwaarde — default 80%, configureerbaar)
- Contract zonder leverancier
- Blokkade zonder eigenaar

🟡 **Aandacht** (volledigheid geraakt, niet blokkerend):
- Component zonder gebruikersgroep
- Component zonder koppeling (geïsoleerd)
- Contract zonder gekoppeld component
- Gebruikersgroep zonder organisatie
- Object zonder enige roltoewijzing

### Interactie-invariant

Signalering is puur read-only en informatief — geen engine-poort, geen
score-mutatie, geen lifecycle-driver. De gebruiker beslist; LIKARA signaleert.
Elk signaal heeft een directe doorkliklink; geen in-line bewerking in het
signaleringsscherm.

## LI024 — Aanvullende UX-patronen

### Draggable overlays
Legenda én detail-popup zijn versleepbaar via mousedown/mousemove/mouseup op document.
Initialiseer positie vanuit getBoundingClientRect() bij eerste drag (niet ?? 0).
Reset bij wisSet(). Patroon: detailPos/legendaPos ref({x,y}), null = CSS-standaardpositie.

### Incrementele graaf-uitbreiding (positie-stabiel)
Component toevoegen aan set → bestaande nodes houden hun positie (vorigePosities
vastgelegd vóór cy.elements().remove()); nieuwe nodes worden gepositioneerd via
fcose fixedNodeConstraint. cy blijft een pure afgeleide van de state (LI032).

### Ring-filter (legenda)
Klik op type in legenda → dat type blijft scherp (opacity 1.0), alle anderen dimmen
(opacity 0.35, lk-dim class). Geen relayout. Reset bij dubbelklik op node of wisSet().
Buiten history (_toestandSig).

### Zoekresultaten in kaart-modus
In kaart-modus (beginscherm dicht): zoekresultaten verschijnen inline onder de
zoekbalk bij zoekterm.trim() || filterActief. Per rij een +-knop (toggleSet) en
✓ als al in beeld. Beginscherm heeft een eigen server-side zoek (los pad).

## Zoekveld-norm (platform-breed, niet-onderhandelbaar — LI032)

Waar de gebruiker ook zoekt (persoon, leverancier, applicatie, contract, plateau, …), het gedrag is
gelijk. Elk zoekveld:
1. **Zoekt soepel** — partieel, hoofdletter- én spatie-ongevoelig (client trimt; backend `ILIKE %frag%`
   ge-escapet). Nooit exact/case-sensitive.
2. **Toont een nette lege staat** — "Geen resultaten." (of een contextuele actie, bv. ter-plekke
   aanmaken), nooit een leeg-ogend of doods veld.
3. **Toont NOOIT een rauwe foutcode.** Een technische fout → een generieke, leesbare melding
   ("Zoeken mislukt."); nooit `e.message`/`NIET_GEAUTHENTICEERD` blind in beeld.
4. **Verlopen sessie → opnieuw inloggen.** Is de sessie onherstelbaar verlopen, dan leidt de centrale
   vangrail (zie likara-frontend) de gebruiker naar de inlogpagina met "je sessie is verlopen" + behoud
   van waar hij was — geen rauwe code, geen dood veld. Dit geldt óók voor lijsten, formulieren en
   detail-schermen: nergens verschijnt een rauwe 401-code.

Deze norm is grotendeels **structureel geërfd** (gedeelde `ZoekSelect`-component + `ILIKE`-backend-
conventie); een nieuw zoekveld op een bestaand zoek-endpoint krijgt 1–3 gratis. Nieuw endpoint = het
`ILIKE`-patroon meenemen (likara-frontend/likara-db).

## Nooit een doodlopend keuzeveld (LI032, norm)

**Een keuzeveld dat verwijst naar iets wat de gebruiker redelijkerwijs ter plekke kan aanmaken, loopt
nooit dood.** Typ je iets dat nog niet bestaat, dan biedt het veld **search-first** het aanmaken aan —
**zonder de flow te verlaten** — met **soepel zoeken vooraf** (geen dubbelen) en **landing in de juiste
context** (bv. de afdeling landt binnen déze partij, `organisatie_id` = deze partij). De nieuwe waarde
wordt meteen gekozen.

- **Toepassing is een bewuste keuze per veld**, niet automatisch overal aan. **Wél** zinvol voor
  open-ended, licht-gewicht doelen (afdeling, persoon). **Bewust niet** voor entiteiten die een eigen
  formele opvoer horen te hebben (contract, component, leverancier) of context-zwaar zijn (organisatie,
  verantwoordelijke) — die blijven "kiezen uit bestaande" tot een expliciet besluit per veld.
- **Visueel — inline aanmaak-zijstap.** Een ter-plekke-aanmaak-blok is een herkenbare **getinte,
  omrande zijstap** met **"Aanmaken en kiezen / Annuleren"** als begin en eind, zodat de gebruiker ziet
  dat hij in een aanmaak-zijstapje zit. Een **genest** aanmaakblok (aanmaken-in-aanmaken) krijgt **één
  stap diepere tint**. **Grens: maximaal twee niveaus** met tint onderscheiden. Kom je dieper uit, dan is
  dát het signaal dat de flow herzien moet worden — niet dieper kleuren.
- **Consistentie:** hetzelfde doel gedraagt zich overal gelijk. Afdeling-ter-plekke-aanmaken leeft in de
  gedeelde `AfdelingSelect`-bouwsteen (spiegel van `ContactpersoonSelect` voor persoon); een nieuw
  afdelingsveld erft het gratis. Historie: vóór LI032 bood alleen `GebruikersgroepSectie` het aan,
  terwijl `PartijFormulier`/`ContactpersoonSelect` doodliepen — inconsistent voor identiek doel.

## Organisatie → afdeling-keuzeopzet (LI032, norm)

Overal waar een gebruiker/lid bij een **organisatie + afdeling** hoort (gebruiker aanmaken én
bewerken; gebruikersgroep), is de opzet **identiek**:
- **Organisatie eerst**, verplicht, **alleen interne organisaties** (de picker spiegelt
  `aard='organisatie', scope='intern'` — een gebruiker is een account van de eigen organisatie).
- **Afdeling daaronder**, **gescoped op de gekozen organisatie** (`organisatie_eenheid` binnen die
  organisatie), en **uitgeschakeld-met-hint** ("Kies eerst een organisatie") zolang er geen
  organisatie is — nooit een actief-maar-leeg afdelingsveld.
- **Org-wissel reset de afdeling** (de oude keuze is niet meer geldig) en remount de afdeling-picker.
- **Aanmaken en bewerken gedragen zich gelijk** — dezelfde volgorde, scoping en reset; een
  bewerk-scherm is geen uitzondering. Bij bewerken zijn org + afdeling **voorgevuld** op de huidige
  waarden (zie de voorgevuld-openen-regel in de picker-patronen).

## LI034 — Persoonlijke standaard-voorkeuren (ADR-041)

### Voorkeur = KIJKFILTER, nooit invoerregel (niet-onderhandelbaar, KERN)
Een persoonlijke voorkeur bepaalt **alleen wat je standaard ziet** — nooit wat je **mag invoeren** of wat
er **is** (gedeelde data). Wie mag registreren wat, is een eigenschap van het landschap (component-breed,
tenant-gelijk), geen persoonsafhankelijke regel. (Deze sessie gecorrigeerd: een voorkeur die het
organisatiegebruik-schrijf-slot stuurde is teruggedraaid; zie likara-domeinmodel.)

### "Onthoud als mijn standaard" — het patroon
Een **bewuste opslaan-actie bij de keuze zelf** (niet een centraal settings-scherm; de voorkeur woont waar
de keuze gemaakt wordt): "★ Sla op als mijn standaard". Met **opgeslagen/gewijzigd-status** (de opslaan-
actie is alleen actief zodra de huidige keuze afwijkt van de opgeslagen standaard) en **herroep** (opnieuw
opslaan met een lege/kale keuze → standaard weg → terug naar de kale default). Bewaar het **geheel** als
één standaard. Server-persistent per gebruiker (voorkeur-laag), dus geldt over sessies/apparaten heen.

### "Vaste bril" vs. "momentkeuze" — sorteerregel
Onderscheid vóór je iets onthoudt:
- **Vaste bril** (onthouden = voorkeur): "hoe ik altijd kijk" — bv. ringen, filters, verkenningsdiepte,
  kleur-op-domein, welke componenttypen je meerekent.
- **Momentkeuze** (vers per keer, nooit onthouden): zoekterm, welk component centraal staat, de actieve
  selectie/set, de weergave (Overzicht/Praatplaat). Een onthouden default zou hier hinderen.
- **Plaatsingsregel:** platformvormend → **centraal beheer**; persoonlijke werkstijl → **voorkeur-laag**;
  momentkeuze → **inline, vers**.

### Eerlijk gaten tonen (aanvulling op P8)
Filters/weergaven **verbergen nooit stilzwijgend** een bestaand feit — ze **benoemen het gat leesbaar**.
Levende instanties: de klik-popup benoemt ontbrekende relaties ("nog geen eigenaar geregistreerd" e.d.,
`popupSamenvatting`); een gekozen relatie-loos component krijgt de cue "geen relaties in beeld"
(`lk-geen-relaties`); en de bestaande "nog niet verfijnd"-markering / `toonRegistratiegaps`. Consistente
eerlijkheidslijn: een gat tonen (rustig), niet verbergen en niet schreeuwen.

**Registratiegap-cue consistent over schermen (LI037).** De "geen ondersteunend systeem"-cue geldt
**identiek op de kaart én de processen-lijst**, met **subboom-semantiek**: een proces is pas een gat
als zijn **héle subboom** geen enkele vervulling draagt (zo toont een hoofdproces met vervulde
deelprocessen zich niet onterecht als gat). De cue is **altijd zichtbaar zolang de proces-ring aan
staat** — los van de `toonRegistratiegaps`-toggle. Afleiding via dezelfde roll-up-leespaden
(rollup + procesvervullingen), nooit een eigen tweede afleiding per scherm.

## LI035 — Regel-acties, meldingen, overlay en de proceswereld (ADR-042)

- **Regel-acties zijn een recht van elke regel.** Wat een gebruiker registreert moet hij
  ter plekke kunnen corrigeren (Bewerken: kenmerk-velden wijzigbaar, de identiteit van
  het feit read-only zichtbaar) en verwijderen — verwijderen áltijd met bevestiging
  waarin de regel léésbaar staat ("*registreren* in Vergunningverlening — Zaaksysteem
  verwijderen?"). Nooit een kaal ×-kruisje op een registratie-feit.
- **Weigeringen en fouten zijn zichtbaar, nooit alléén kleur.** MeldingBanner: kleur +
  icoon + tekst, bóven de invoervelden (leesvolgorde vóór het te corrigeren veld), met
  scroll-vangnet; de melding verdwijnt zodra de invoer wijzigt. Een 409 "bestaat al" is
  een rustige warn-banner, géén fout-toast (er is niets kapot).
- **Succes is voelbaar**: elke geslaagde opslaan-intentie geeft de korte bevestiging
  (succes-toast, werkwoord). Stilte na "Opslaan" leest als "is er iets gebeurd?" — de
  LI035-browsercheck-bevinding.
- **Overlay-formulier**: aanmaken/bewerken in een overlay boven de lijst/het detail (de
  context blijft zichtbaar); annuleren met onopgeslagen wijzigingen vraagt bevestiging;
  deelregistraties die je al invulde gaan niet verloren bij een deelfout (entiteit staat,
  banner benoemt wat er restte, met "Opnieuw proberen").
- **Vier-vragen-Overzicht (componentdetail)** — het Overzicht beantwoordt vier vragen in
  vaste volgorde: *wat is dit* (blok-wat-is-dit) / *wie is verantwoordelijk*
  (blok-verantwoordelijk: sleutelrollen product_owner + proceseigenaar read-only uit de
  roltoewijzingen; een gat toont rustig "nog niet geregistreerd" — tonen ≠ registreren) /
  *waarvoor gebruiken we het* (processectie, dáár wél direct registrerend) / *hoe staat
  het ervoor* (migratiegereedheid).
- **Proces-detail = twee blokken**: "Componenten in dit proces" (registratie op dít
  niveau) bovenaan; daaronder ÉÉN blok "Onderliggende processen" — kopje per direct
  deelproces (het kopje ís de herkomst: regels daaronder dragen géén bijschrift),
  pad-bijschrift alléén bij diepere lagen ("via › Besluit vastleggen", klikbaar),
  open-tenzij-groot (±10 doorgerolde regels; telling telt componenten/herkomst UNIEK;
  uitklapstand onthouden via het lijststaat-patroon; de kopjes blijven altijd staan —
  navigatie verliest niets). Deelprocessen en hun componentregels zijn één onderwerp —
  geen twee losse blokken (browsercheck-inzicht LI035).
- **Afgeleide-leeslaag eerlijk presenteren**: een roll-up- of afgeleide kijk (organisatie
  → processen via componenten) is read-only, zegt dat expliciet in de (i) ("hier wordt
  niets geregistreerd"), en de acties wonen op de herkomst-plek — de doorklik brengt je
  daar. Afgeleid beeld nooit als registratie vermommen.
- **Lijststaat**: een gebruiker die terugkeert naar een lijst vindt hem zoals hij hem
  verliet (zie het lijststaat-patroon in likara-frontend) — deep-link wint altijd van de
  bewaarde staat.

## LI036 — kaartpatronen: zichtbaarheid, rolbanen, filterbalk, toggle-acties

- **"Ring uit wint van gaps" (zichtbaarheidsregel, alle weergaven).** Wat zichtbaar blijft
  = de ringen die AAN staan. Een ring uitzetten haalt de relaties én de knopen weg die
  alléén via die ring in beeld waren — óók met "Toon registratiegaps" aan. Een knoop met
  nog een geldige aanstaande-ring-relatie blijft; een échte gap (geen enkele relatie)
  volgt de ring van zijn categorie; **'overig' (categorieloos) blijft altijd zichtbaar
  onder de toggle** (er is niets uitgezet — stil verbergen zou een echte gap verstoppen).
  Eén gedeelde term in `getekendeNodes`, identiek op Overzicht/Praatplaat/Lagen
  (techniek: likara-frontend).
- **Rolbanen vs. identiteitsbanen.** Rolbanen ("wie doet wat": Rollen & beheer,
  Gebruikers) delen in op **de rol in de relatie** — een partij verschijnt in élke rolbaan
  waar ze die rol speelt (meerdere petten = meerdere plekken, max. één per baan; techniek:
  instance-projectie). Identiteitsbanen (Componenten/Infrastructuur/Contracten) delen in
  op **wat het object ís** — precies één keer. Leverancier ("geleverd door"), eigenaar en
  beheerrollen → Rollen & beheer (elk met rol-tag); gebruikt → Gebruikers; een partij
  zonder rol in de selectie → Rollen & beheer zónder tag (geen tag = "hier geen rol").
- **Selectie-meebewegende filterbalk ("toont alleen wat in beeld is").** Een balk die
  "X in beeld" heet, leidt zijn lijst af uit de getekende set **met de eigen scope-term
  contrafeitisch weggedacht** — dan (1) bevat hij alleen items die voor déze selectie
  relevant zijn, (2) blijft een uitgezet item zichtbaar-onaangevinkt zolang de selectie
  het relevant maakt (uitzetten om te focussen blijft omkeerbaar via de balk), en
  (3) beweegt de lijst automatisch mee met selectie/ringen/weergave. Lege lijst → korte
  hint ("geen organisatie in beeld"), geen kale ruimte. Referentie: `organisatiesInBeeld`.
- **Een toggle-actie maakt alleen z'n eigen actie ongedaan.** Een groeps-toevoegknop
  ("+ Voeg vervullende componenten toe (N)") onthoudt precies wát ze toevoegde (per bron,
  bv. `_vervulToegevoegd` per proces) en de omgekeerde knop ("− Verwijder …") verwijdert
  **alleen dat** — vóór-bestaand werk (het vertrekpunt van de gebruiker) blijft staan.
  Nooit "wis alles wat hierbij hoort": dat veegt eerder eigen werk weg (afgekeurd).
  Alles-zat-er-al → "(0)" disabled met hint (niets ongedaan te maken). Terugkoppeling bij
  elke klik: toevoegen licht het geraakte web op (bestaand selectie-pad), verwijderen
  geeft een korte succes-toast. Set-acties wijzigen nooit de weergave.
- **Detail-op-aanvraag (expliciete verankering).** Houd de plaat/lijst rustig en laag de
  onderbouwing gelaagd achter één klik: **badge** (aantal op de gebundelde lijn) →
  **inklap** (herkomst per component, standaard dicht) → **popup/detailscherm** (volledige
  uitsplitsing + doorklik). Nooit alle detail front-loaden (de "Vervuld door"-tekstmuur
  was de aanleiding); geldt als leidend principe voor elke roll-up-/bundel-weergave.

## LI037 — kaartpatronen: proces-ingang, inzoom, boom vs. netwerk

- **Herkomst-aanwijzen = de bestaande selectie (oranje), geen eigen accent-kleur.** Bij een
  kaart-ingang vanaf een (deel)proces wordt de herkomst-knoop de **geselecteerde** knoop
  (oranje) + gecentreerd — LIKARA's eigen "kijk hier"-taal. Een tweede markering-kleur (het
  blauwe accent) is **afgekeurd**: viel weg tussen de knopen én dupliceerde betekenis. De
  chip benoemt de herkomst in woorden; oranje = "waar sta ik nu".
- **Ingang dimt, inzoom snijdt (twee onderscheiden gebaren).** Een proces-**ingang** ("Bekijk
  op kaart"/"Via proces") opent het brede landschap: deelproces gedimd-met-focus (hele boom
  geladen; "Toon hele landschap" in de popup heft de dim op), hoofdproces breed/neutraal —
  beide met oranje selectie + centrering, **géén set-inperking**. Een **dubbelklik-inzoom**
  perkt de set écht in (proces + hele subboom + vervullers) = nieuwe history-staat; "← Terug"
  loopt via de bestaande history (waar je vandaan kwam), geen apart terug-mechanisme. Houd de
  twee begripsmatig gescheiden.
- **Hiërarchie = boom, netwerk = kaart.** Een boom-weergave (kaart-proceszone én
  lijst-tree-view) toont **hoogte codeert diepte**, gegroepeerd per boom; verbindingslijnen =
  **uitsluitend echte geregistreerde ouder→kind-relaties** (spiegelt "geen afgeleide relaties",
  ADR-023 b7). **Geen verbindende stam tussen losse wortels** (dat suggereert een ouder die er
  niet is). Netwerk-/afhankelijkheidsrelaties horen op de kaart, nooit in een tree-view
  (één-ouder-per-knoop).
