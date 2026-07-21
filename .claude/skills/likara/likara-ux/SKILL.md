---
name: likara-ux
description: Interaction-design-denkmethode voor LIKARA. Verplicht te raadplegen bij ELKE frontend-rakende slice (nieuw scherm, nieuwe sectie, nieuwe actie) — door zowel CC als claude.ai. Borgt dat een functie de UI logisch en compleet houdt voor de gebruiker: geen lege lijsten zonder route naar de actie, actie op de plek waar de gebruiker hem verwacht, terminologie vanuit de gebruiker. Dit is GEEN stijl-/visuele skill (dat is likara-frontend); dit gaat over of het scherm doet wat de gebruiker verwacht.
bijgewerkt: V043
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
- **Een tenant-wens versmalt nooit de platform-default (W4, LI044).** Een tenant die een feit niet
  hanteert, zet het in zijn eigen norm/configuratie **uit** — dat is tenant-configuratie. Het is nóóit
  een reden een feit uit de **meegeleverde platform-default** te verwijderen: de default geldt voor
  elke tenant en versmalt niet mee met één gebruiker. (LI044: BvoWB hanteert geen BIV → BIV blijft in
  `DEFAULT_VERPLICHT`; de tenant zet 'm uit, de default blijft compleet.)

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

**Nul is een uitkomst, geen storing — ook bij BLOKKEN en TELLERS (LI047, herzien LI048).** Een blok
met nul punten **blijft bestaan**, toont "0" in zijn naam en zegt geopend wát er niets open is ("Er
staat niets meer open dat uw organisatie verplicht heeft gesteld."); verbergen laat de lezer
twijfelen of het blok bestaat of stuk is.

**De knip loopt niet tussen lijst en teller, maar tussen een teller die ERGENS BIJ hangt en een
teller die een PLEK benoemt (LI048 besluit 3).**
- Een **badge op een knop of object** (een aantal dat een bestaand ding aankleedt) **zwijgt bij
  nul**: de "0" vraagt aandacht voor niets — de rust ís het signaal dat het schoon is.
- Een **plek-label** (tabnaam, sectiekop, filterchip) draagt het getal **altijd, ook bij nul**. In
  een rij van twaalf tabbladen leest "geen getal" niet als *nul* maar als *"dit tabblad telt
  niets"* — dat verschil is onzichtbaar, dus klikt de gebruiker alsnog. Precies het klikken dat de
  teller moest besparen.

⚠ De oude vuistregel *"een lijst legt uit, een teller zwijgt"* was te grof: hij liet één scherm twee
tegengestelde dingen doen. Vóór LI048 stond `Open punten` (kop-knop, zwijgend bij nul) recht boven
`Dit moet nog (0)` (tabblad, sprekend bij nul) — dezelfde vorm, tegengesteld gedrag, één blik.
(Referentie nu: `ComponentDetail` — tabblad `Open punten (0)`; `OpenPuntenSectie` — drie blokken met
hun aantal in de tabnaam. Beide plek-labels, dus beide sprekend.)

**Een weigering zegt WÁT er aan de hand is (LI047).** "Er is niets" en "die vraag geldt hier niet"
zijn **verschillende antwoorden**; ze door elkaar halen kost vertrouwen. Een 404 op een bestaand
object stuurt de gebruiker een verdwenen ding zoeken — hij vernieuwt de pagina en twijfelt aan zijn
eigen ogen. Kies de foutsoort dus op **betekenis**, niet op gemak: 404 = het bestaat niet; 422 = het
bestaat, maar hier geldt deze regel niet, mét de reden erbij.
(LI047: een gebruikersgroep op een databaseserver gaf `NietGevonden("applicatie")` → *"dit component
bestaat niet"* over een component dat er wél was. Nu: 422 `COMPONENT_ONDERSTEUNT_GEEN_WERK` — *"Met
dit type component wordt niet door mensen gewerkt, dus een gebruikersgroep vastleggen heeft hier geen
betekenis."*)

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

**Toets elke zin tegen het RANDGEVAL, niet het typische geval (LI041).** Taal is een
ontwerpbesluit, geen laklaag. Een woord dat klopt voor het gemiddelde antwoord kan liegen voor het
randgeval — en juist het randgeval is waar de consultant twijfelt. Concrete toets: **"klopt deze
zin ook als het antwoord een fileshare is? En als het antwoord papier is?"** Instanties LI041:
*"systeem"* bij een G-schijf (→ *"waarmee wordt dit werk gedaan"*) · *"component"* in de bevinding
(te technisch → *"hiervoor wordt niets gebruikt"*) · *"vervangen"* bij een grove koppeling die juist
**bevestigd** blijft (verdringing is een verschijning, geen verwijdering — ADR-049). De browsercheck
is het sluitpunt: een verkeerd woord vangt geen test.

### 6. Consistentie met bestaande schermen
Een nieuwe sectie hoort qua interactie te lijken op vergelijkbare bestaande secties
(zelfde knop-plaatsing, zelfde lege-staat-stijl, zelfde manier van toevoegen/verwijderen),
zodat de gebruiker niet per scherm opnieuw moet leren.

**Identiteit "afdeling — organisatie" / "persoon — afdeling — organisatie" (ADR-036a/037, LI030;
geconvergeerd LI040).** In ELKE niet-org-gescoopte lijst/picker waar afdelingen of personen
verschijnen, toon de organisatie-context — dit ontdubbelt gelijknamige afdelingen/groepen van
verschillende organisaties ("Studenten — Culemborg" is een ándere groep dan "Studenten — Tiel").
Regels: afdeling → "afdeling — organisatie"; persoon → "persoon — afdeling — organisatie" (persoon
zonder afdeling → "persoon — organisatie"). Het **geselecteerde** item in het veld toont dezelfde
identiteit als de lijst (niet uiteen laten lopen).
- **Identiteit wordt nooit afgekapt en nooit ingekort** — óók niet als er een organisatie-kolom
  naast staat: de organisatie is geen ruis maar het onderscheidende deel. Naam = **scanlaag**
  (zwart), de rest = **gedempte leeslaag**; in platte picker-inputs kan demping niet — daar staat
  wél de volledige tekst.
- **Bouwsteen (LI040):** `IdentiteitLabel.vue` (6 consumenten) + `partijIdentiteit`/
  `gebruikersgroepIdentiteit` in `labels.js:19-35` — geen losse identiteits-opmaak per scherm.

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
- **Verbergen mag, stiekem verbergen niet — twee LI041-instanties.** (1) De **verdrongen grove
  koppeling**: op een plek met een fijn antwoord wint het fijne bij het tonen, maar het grove
  verdwijnt alleen uit *beeld*, niet uit de database (ADR-049) — het scherm zegt dát er een grof
  antwoord onder zit, verzwijgt het niet. (2) De **ongetelde reikwijdte**: een *"geldt overal"*-label
  zonder telling verzwijgt hoe breed het geldt; het label draagt daarom de telling
  (`grof_totaal_plekken`/`grof_geldt_op`). **De zin is de aankondiging; de gedeelde afleiding is de
  vangrail** — teller en getoonde lijst uit één bron (`dekking_overzicht`), nooit twee die uit de pas
  lopen (de kernregel-derde-gezicht, likara-domeinmodel §LI041).

### P8a — Een opgeborgen filter blijft zichtbaar (LI048, niet-onderhandelbaar)

Derde instantie van dezelfde lijn, en de scherpste: niet een filter dat verbergt, maar een filter
dat **zelf** verborgen is.

> **Een filter dat werkt maar niet zichtbaar is wanneer zijn besturingselement gesloten is, bestaat
> voor de gebruiker niet.**

Berg je filters op achter een knop, paneel of venster, dan moet **zonder openen** zichtbaar zijn:
1. **dát** er gefilterd wordt (een teller op de knop — bij nul geen getal, zie §"een lijst legt uit,
   een teller zwijgt");
2. **welke** filters aanstaan (uitgeschreven, label + waarde);
3. **hoeveel** er overblijft ("7 van 20 componenten");
4. en elk actief filter is **los weg te klikken** zonder het venster te openen.

**Waarom dit geen vormvoorkeur is.** Een consultant die naar een stiekem gefilterde lijst kijkt,
trekt verkeerde conclusies over zijn eigen landschap: hij ziet zeven componenten en denkt dat het er
zeven zíjn. In LIKARA is dat geen ongemak maar een **fout antwoord op de vraag waarvoor het product
bestaat**. De vraag *"waarom zie ik er maar zeven?"* moet altijd beantwoord zijn zonder iets te
openen.

**Vangrail:** de teller en de opsomming lezen **één bron** (in de componentenlijst: `filterChips`).
Zo kan een filter niet wél tellen en géén chip krijgen — dat is precies het defect dat onzichtbaar
filtert, en het is niet met het blote oog te zien.

⚠ **Een toets die het geval niet oefent, geeft valse zekerheid (LI048).** Bij een regel als deze is
de toets de enige bewaking — het defect is per definitie onzichtbaar. Maar een toets die de
*omstandigheid* niet nabootst waarin het defect optreedt, blijft groen terwijl het defect erin zit.
Tweemaal aangetoond in LI048:
- De **Annuleren**-toets bewees dat een keuze niet lekt naar de toegepaste filters — maar zette de
  debounce-timer niet vooruit, dus de live-teller had nooit gedraaid en juist dáár zat het lek. Met
  het defect ingebouwd bleef hij groen.
- De **dist-CSS-check** bleef groen toen de wit-op-wit-regressie werd teruggezet, omdat de check de
  regel die het defect droeg niet toetste (alleen het bestaan van de klasse).

**Vuistregel: een bijt-bewijs is pas af als de toets rood wordt op de assertie die het defect
draagt** — niet ergens anders in de suite, en niet "er valt iets om". Breek het defect opzettelijk,
kijk wélke regel rood wordt, en draai terug. Wordt niets rood, dan is de toets het probleem, niet
het defect. (Zusje van "assert op zichtbare tekst" en de zelftest-eis bij bronscans, likara-tests.)

**Herkomst:** `ComponentLijst` (LI048) — dertien filtervelden verhuisden naar een venster; de knop
draagt `Filter (N)`, de chips staan eronder met het aantal ernaast.

⚠ **Deze schermen raakt de regel zodra ze hun filters achter een knop bergen** (nu nog een open
filterbalk, dus nog niet van toepassing): `PartijLijst` · `ContractLijst` · `BedrijfsfunctieLijst` ·
`BlokkadeOverzichtView`. Genoteerd zodat een volgende sessie de regel tegenkomt **vóór** de bouw in
plaats van erna.

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

### beginschermOpen-vlag (aangescherpt LI046)

Zichtbaarheid = aparte `beginschermOpen = ref(true)`.
NIET **reactief** gekoppeld aan `actieveSet.size === 0` — die koppeling veroorzaakte
spooksluitingen. Wél geldt bij **binnenkomst** één EENMALIGE gedeelde regel over álle
binnenkomst-takken (handoff · deep-link · herstelde lk-state · verse start · elke toekomstige
tak): **gevulde kaart → beginscherm dicht** (`beginschermOpen = actieveSet.size === 0`, ná de
beslisboom). **Terugkeren of herladen mét bewaard werk telt als de expliciete gebruikersactie**
(besluit Bert LI046: "je komt terug waar je was — ook op de kaart"); het beginscherm hoort bij
een VERSE start, niet bij een terugkeer. Sluiten tijdens de sessie = expliciete actie;
heropenen = wisSet() + harde reset. Een nieuwe binnenkomst-tak hoeft alleen de set te vullen
en erft dit — borging: LandschapskaartView.test.js.

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

### Plek-stand-kleurtaal (LI043) — een aparte as

De **plek-standen** (bedrijfsfunctie-plek, gate 4) dragen een eigen vaste kleurtaal, uit één bron
(`standCodering`), consistent over **lijst-pill + kaart + legenda**:

- **amber** (`--lk-color-warning`) = er ligt **werk** — `gat` én `werkvoorraad` (onderscheiden door tekst, niet kleur)
- **groen** (`--lk-color-success`) = **hier draait** een systeem
- **blauw** (`--lk-color-primary-700`) = **gedekt via** een bovenliggende functie
- **grijs** (`--lk-color-text-muted`) = **bewust niets** (een afgerond besluit)

⚠ **Niet verwarren met andere kleur-assen.** Dit is een ándere as dan (a) de Signalering-ernst hierboven
(🔴 kritiek / 🟡 aandacht) en (b) de **Beoordelingsstatus/lifecycle**-tinten op de kaart (`LC_STYLE`:
groen = migratieklaar, blauw = in_inventarisatie). Die bestaande conventies blijven eigenstandig; de
plek-stand-kleurtaal overschrijft ze niet. "Consistent over vensters" geldt alleen bínnen de plek-stand-context.

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

> ⚠ **Procesregister-UI geparkeerd (LI044, gate-4 sloop `c82ad80`).** De proces-UX-patronen hierna
> (§LI035 "Proces-detail = twee blokken", de registratiegap-cue "op de processen-lijst", §LI036/LI037
> "kaartpatronen: proces-ingang/-inzoom", §LI038 "processen-scherm Boom | Diagram") beschrijven schermen
> die **uit de MVP-UI zijn verwijderd**: nav, routes, `ProcesLijst`/`ProcesDetail`, `PartijProcessenSectie`,
> de kaart proces-ingang en de "Bekijk op kaart"-doorklik zijn gesloopt. Ze blijven staan als
> **historische ontwerpgrond** — de bouwstenen (`procesBoom`/`ProcesDiagram`) en het datamodel leven
> nog, het concept is geparkeerd (niet verwijderd). Zie likara-domeinmodel §LI038/ADR-043. Lees deze
> patronen dus niet als "een levend scherm dat de gebruiker nu bezoekt".

- **Regel-acties zijn een recht van elke regel.** Wat een gebruiker registreert moet hij
  ter plekke kunnen corrigeren (Bewerken: kenmerk-velden wijzigbaar, de identiteit van
  het feit read-only zichtbaar) en verwijderen — verwijderen áltijd met bevestiging
  waarin de regel léésbaar staat ("*registreren* in Vergunningverlening — Zaaksysteem
  verwijderen?"). Nooit een kaal ×-kruisje op een registratie-feit.
- **Aandacht schaalt met gewicht — bevestiging = auditeerbaar wilsbesluit (LI043).** Niet elke
  handeling verdient dezelfde drempel: overal bevestigen traint weg-klikken én vervuilt het audit-spoor
  met betekenisloze bevestigingen. Een **ijkpunt** hoort bij handelingen die **werk terugzetten of iets
  vernietigen** en **benoemt het gevolg** ("deze plek komt hierdoor terug op je werklijst") — het is een
  verantwoordingsmoment (wie · wanneer · welk getoond gevolg · bewust akkoord). Lichte, triviaal-
  omkeerbare, additieve handelingen (koppelen, gebruikersgroep tóevoegen) krijgen géén drempel. Het uit
  te voeren werk staat in **OPVOLGPUNTEN L1a** (niet hier dupliceren).
  - **De drempel hangt aan de AFWIJKING, niet aan de handeling (U1, LI044 — expliciete uitzondering op
    L1a).** Dezelfde handeling is licht óf zwaar afhankelijk van de afwijking: een component klaar
    verklaren is normaal een lichte vooruit-handeling (L1a: "vooruit-handelingen blijven licht"), maar
    klaar verklaren **terwijl de tenant-norm afwijkt** (verplichte feiten nog niet vastgesteld) is het
    bewust overrulen van de gemeente-norm en verdient dáárom het rijke, auditeerbare akkoord met de
    open feiten benoemd (of "eerst aanvullen" — geen doodlopend pad). De drempel zit in de afwijking,
    niet in het verklaren; leg deze uitzondering expliciet vast zodat een latere sessie L1a niet leest
    als "klaar verklaren is altijd licht". Referentie: ADR-052 besluit 5 + §L1a-uitzondering,
    `MigratiegereedheidSectie` (`toontNormAfwijking` → `bevestigLabel`).
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
  **Context die alleen bij een afwijking telt, hoort achter de waarschuwing, niet permanent bij de
  status (U3, LI044):** een reden bij een klaarverklaring staat niet vast in beeld — de waarschuwing
  die de vraag "waarom toch?" oproept ís de ingang naar de reden + stand-bij-het-besluit; de verdieping
  herhaalt niet wat er al boven staat.

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

## LI038 — proces-only structuurbeeld

- **Een componentloos beeld hoort NIET in de kaart.** De kaart is component-/applicatie-
  centrisch. Een **componentloos** beeld (alleen processen, alleen functies, …) hoort als
  **weergave binnen het eigen registerscherm** — LI038: **Boom | Diagram** in het
  processen-scherm. Twee representaties van dezelfde structuur: **Boom = beheren**,
  **Diagram = begrijpen/navigeren**. Een componentloos beeld tussen Overzicht/Praatplaat/Lagen
  breekt het mentale model ("waar zijn ineens de componenten?").
- **Het derde gebaar: enkele klik = kijken.** Aanvulling op *"ingang dimt, inzoom snijdt"*
  (LI037) — die regel **geldt ook buiten de kaart**. Volledig:
  - **Enkele klik = kijken** — highlight van de knoop **inclusief zijn verbindingen** + popup.
    **Géén set-inperking, géén weergave-wissel.** De gebruiker oriënteert zich alleen.
  - **Dubbelklik = snijden** — knoop + subboom worden de scope, **zónder ouderketen/zusjes**;
    nieuwe history-staat; "← Terug" via de bestaande history-laag (snapshot + cursor,
    veld-agnostisch).
  - **Ingang = neutraal openen** — centraal + oranje selectie, **géén inperking**.

  **Weging bij dubbelklik-onderscheiding:** de enkele klik moet **direct** aanvoelen (popup
  zonder uitstel). LI038 koos daarom bewust "popup-direct" boven "geen flikker" — bij een
  dubbelklik flitst de popup heel kort. Browserverificatie besliste dit, niet de test.
- **"Verbreden binnen het beeld" ≠ "overstappen naar een andere wereld".** Twee **visueel en
  functioneel gescheiden** uitgangen; nooit op één knop:
  - *"Toon hele processenlandschap"* — heft de focus op, **blijft in hetzelfde (proces-only)
    beeld**.
  - *"Bekijk op de kaart →"* — **bewuste overstap** naar de component-wereld (via de bestaande
    handoff-bouwer + consume-once store, **niet** de `?center=`-component-deeplink).

  Samen op één knop zou "meer processen zien" laten lezen als "componenten erbij halen".

## LI039 — gevalideerde UX-patronen (fase A: `docs/Validatie-patronen-LI039.md`)

- **"Informatie die overal hetzelfde is, is geen informatie."** Herkomst/context die voor
  élke rij gelijk is staat ÉÉN keer boven de lijst (data-gedreven, bv. `modelHerkomst` in de
  functieboom); op de rij staat alléén wat afwijkt ("eigen", "vervallen"). Reden: herhaling
  per rij maakt de échte afwijking onzichtbaar. ⚠ Tekst-regel — geen bouwsteen; converge bij
  het tweede scherm (n≥2).
- **Kern-inhoud staat nooit in een tooltip.** Een tooltip is onvindbaar, bedient één persoon
  tegelijk en breekt op touch/toetsenbord/schermlezer. De definitie in de functieboom is
  daarom een zichtbare lees-laag (max twee regels) + volledig in de popup — "zichtbaar zonder
  muisbeweging" (main.css-comment bij `.lk-rij-definitie`). ⚠ Tekst-regel — geen bouwsteen.
- **Geen doodlopend pad.** Wat om actie of aandacht vraagt, biedt minstens één uitgang:
  een vervallen rij houdt "Toon in functiebeeld" (alleen de mutaties zijn geweerd); een
  onvoltooide inlees is afrondbaar óók als er niets meer bij hoeft (anders is de melding
  nooit weg te werken); een popup bestaat op inhoud, óók zonder uitgangen. ⚠ Tekst-regel —
  per-scherm-ontwerp, geen bouwsteen.
- **Lege uitkomst ≠ fout (aanvulling op P8).** "Aanroep slaagde, niets gevonden" is een
  TOESTAND (rustige lege staat mét route naar de actie); "aanroep faalde" is een FOUT (rood).
  Nooit beide tegelijk — dwing dat structureel af met één toestandsvariabele (de
  aanbodStaat-vorm, zie likara-frontend). Reden: een gebruiker die alarmrood ziet gaat
  bellen terwijl er niets kapot is; twee tegenstrijdige meldingen maken het scherm
  ongeloofwaardig (browsercheck-bevinding LI039).
- **Picker-regel 1-aanvulling (LI039): weren vooraf ÉN uitleggen waarom.** Weren vooraf is
  gebouwd (de plaats-picker spiegelt PLAATSING_BESTAAT/kring/vervallen; `plaatsZin` zegt wat
  er gáát gebeuren). **BESLOTEN, NOG TE BOUWEN:** de picker legt óók uit waaróm een optie
  ontbreekt — zonder die uitleg is een ontbrekende optie in de ogen van de gebruiker een BUG.
  Eerst nodig bij de componenttype-filtering in gate 2 (de consultant zoekt zijn database,
  vindt hem niet, en denkt dat er iets stuk is — terwijl het een regel is: een database
  ondersteunt geen werk). Zie OPVOLGPUNTEN.
- **Koppel-UX bij meervoudige plaatsingen — BESLOTEN, NOG NIET GEBOUWD (gate 2, ADR-044
  besluit 2):** één zoekresultaat per functie (niet vier), *"geldt overal"* voorop, verfijnen
  mag meerdere plekken tegelijk, het scherm benoemt wat het doet, en pas als ÁLLE plekken
  verfijnd zijn is de functie volledig verfijnd.


## LI040 — leegte, oordelen, filters en de detailkop (gevalideerd)

- **Leeg ≠ fout, én leeg ≠ een ingevulde waarde/oordeel (LI043).** Een default die als oordeel oogt
  ("Onbekend", "Midden") is erger dan leegte: niet te onderscheiden van een echt oordeel — en
  precies op de kolommen waarop een bestuurder sorteert. **Dat geldt óók voor een afgeleide/proxy-
  waarde en een placeholder-sentinel**: presenteer die nooit alsof het een echt ingevuld antwoord is.
  Bewijs LI043: de domein-lezing toonde het componenttype-label ("Applicatie") als wás het een domein
  (proxy → schijnwaarde); BIV "niet geclassificeerd" mag niet als "in orde" lezen. Velden waar
  afwezigheid betekenis heeft zijn **nullable zonder default**; afwezigheid toont **gedempt** als
  **"nog niet vastgelegd"**, nooit rood. LIKARA doet nooit zelf de uitspraak (ook de seed niet).
  *(Migraties 0067/0068; ADR-046 addendum A, vormkeuze B.)*
- **Eén taal voor afwezigheid** in de hele applicatie. ⚠ OPENSTAAND (OPVOLGPUNTEN 0a): er zijn
  nu nog vijf woorden — "nog niet vastgelegd" · "Niet geclassificeerd" (BIV) · "nog niet
  geregistreerd" (eigenaar/rollen) · "n.v.t." · "—". Keuze is aan Bert; niet zelf gladstrijken.
- **Leeg moet vindbaar zijn.** Elk veld waar afwezigheid betekenis heeft krijgt een filteroptie
  "nog niet vastgelegd". **Het registratiegat is de werkvoorraad van de consultant** — "waar moet
  ik nog langs?" is de vraag die hij stelt. *(`*_ontbreekt`-filters op levensfase/bedoeling/
  complexiteit/prioriteit + BIV; routes/component.py.)*
- **De filterbalk vertelt wat hij doet:** altijd het **aantal** ("3 van 19 componenten"), elk
  actief filter **uitgeschreven als chip** (label + waarde), **los wisbaar**. Een lege uitkomst
  staat zo **naast zijn eigen reden** — anders is leeg een raadsel van elf dropdowns. *(Bouwsteen:
  `src/components/FilterResultaatRegel.vue`; uitrol naar de overige lijsten = OPVOLGPUNTEN 0.)*
- **De acties horen bij het object, niet bij het einde van de pagina.** Detailkop naast de naam:
  **Bewerken** primair · **statusovergangen alleen wanneer ze kunnen** (geen grijze knop die
  meereist) · navigatie (kaart/geschiedenis) lichter · **destructief in een eigen, gescheiden
  zone** (een misklik wist niets). **Sectie-acties blijven in hun sectie** ("+ Lid koppelen" is
  geen object-actie). Nooit op twee plekken. *(Bouwsteen: `src/components/DetailKop.vue`, 8
  consumenten; bron-scan dwingt af.)*
- **Eén veldhoogte** (`--lk-veld-h` = de knophoogte): élke formulierbesturing via `.lk-veld`; het
  tekstvlak (`.lk-veld-tekstvlak`) is de ENIGE uitzondering — hoger, zelfde breedte/rand/radius/
  focus. *(main.css:40-77; bron-scan dwingt af.)*
- **Tabel zodra een rij meer dan één gegeven draagt of gesorteerd moet worden.** Bouw de vorm die
  het **eindbeeld** draagt, niet wat vandaag nét past — de Gebruik-tabel draagt de kolommen
  Stand/Tranche van stuk 3 zonder herbouw. *(`OrganisatiegebruikSectie.vue`, sorteerbare DataTable.)*
- **Bewust aanvinken.** Bij een bulk-actie staat **niets voorgevinkt**: een vinkje is een
  **uitspraak**, geen selectie — zeker waar het andermans veldwerk overschrijft. "Selecteer alles"
  mag als expliciete klik; een stille default niet. *(LI040-besluit Bert; ontwerpregel — er is nog
  geen gebouwde bulk-vinkinstantie om naar te wijzen.)*
- **Neutrale taal bij afgeleide uitkomsten.** "geen gebruikers meer", niet "valt om". **Amber,
  nooit rood** — er is niets kapot, en vaak is de uitkomst juist de bedoeling. LIKARA toont het
  feit; de mens trekt de conclusie. *(ADR-046 besluit 5 — bouw volgt in stuk 3/5.)*
- **Geen uitleg die moet gokken.** Verklaar afwezigheid niet als de reden niet zeker is (in een
  onvolledig landschap is "niet gevonden" meestal "niet geregistreerd", niet "geweerd"). Een
  **scope-regel** die benoemt wát je ziet ("met componenten van dit type wordt werk gedaan") is
  **altijd waar**; een verklaring van afwezigheid niet. Verfijnt de LI039-regel "weren vooraf én
  uitleggen waarom": de uitleg krijgt de vorm van een zékere scope-regel. *(velduitleg.js:286.)*

## LI044 — Eén norm-definitie, twee peildata (ADR-052)

**Eén norm-definitie, twee peildata (U2).** Een afgeleid signaal en zijn vastlegging lezen uit
**dezelfde** definitie, maar tegen **verschillende peildata** — en dat onderscheid mag niet vervlakken:
- **Het signaal leeft** — een **live** her-afleiding (de badge "klaar verklaard, maar N verplichte
  feiten open") die vanzelf **dooft** zodra het feit alsnog is vastgesteld.
- **De vastlegging bevriest** — een **snapshot** op het moment van het besluit (de open feiten bij het
  klaar-verklaren + wie + wanneer) die **blijft staan**, ook nadat de feiten zijn aangevuld.
- **Beide uit één definitie, nooit twee parallelle afleidingen** die uiteen kunnen lopen (dezelfde lijn
  als "één bron, meerdere ingangen" — likara-domeinmodel §LI041-kernregel).

**Nuance — de bevroren snapshot mág worden opgeslagen (schijnbaar in strijd met ADR-046 besluit 5).**
De regel "afgeleide uitkomsten worden nooit opgeslagen" (LI040/ADR-046 besluit 5) geldt voor afgeleide
**waarden** (readiness, zwaarte) — die tel je live, je bewaart ze niet, want een opgeslagen afleiding is
een tweede waarheid. De klaarverklaring-snapshot is een **andere soort**: geen afgeleide waarde maar de
**audit van een wilsbesluit** ("consultant X kreeg déze open feiten voorgelegd en verklaarde toch
klaar"). Die bewaar je juist wél — de auditwaarde zit in de bevriezing. Benoem dit onderscheid expliciet
zodat een latere sessie de snapshot niet als schending van ADR-046 besluit 5 leest. Referentie: ADR-052
besluit 6, `component_klaarverklaring.open_feiten` (snapshot) vs. `norm_status` (live badge).

## LI045/ADR-052 — de verschoven lat, de aanduiding en de brug

*(Bouwt voort op LI044 "één norm-definitie, twee peildata". De patronen zijn gevalideerd in
`docs/TST-Normverhaal-V045.md`; slices 4a–4c + C1.)*

- **Nooit een besluit toeschrijven dat een mens niet nam (U-norm).** Verschuift een organisatienorm in
  de tijd, dan mag een signaal dat daaruit volgt niet lezen als een **keuze van de gebruiker**. Onderscheid
  streng: **de organisatie verzette de lat** (neutraal, gedempt — géén waarschuwingskleur) vs. **deze
  persoon week bewust af** (amber). De scheidslijn is de **bevroren snapshot**: een feit dat er wél in stond
  is bewust afgewogen (amber); een feit dat er níét in stond is nooit een besluit geweest (neutraal —
  "sindsdien verplicht gesteld; daar is hier nog niet naar gekeken"). Dragen beide tegelijk: **beide tonen,
  elk in eigen toon** — er wint er geen. **Het verschil snapshot × live ís het signaal — geen extra opslag**
  (geen derde bron; het audit-log voedt alléén de "wanneer/door wie"-metadata, niet de classificatie).

  ⚠ **Één afleiding is niet één presentatie — de les van LI048.** Deze regel stond hier, `splits_afwijking`
  was al de enige bron, en het onderscheid was gebouwd — maar alléén in `MigratiegereedheidSectie`. Het
  open-punten-kader (`OpenPuntenSectie`, in LI047 apart gebouwd) toonde beide soorten in **dezelfde toon**
  met alleen andere woorden. Twee vensters, één afleiding, twee presentaties: precies de misleiding die
  deze regel verbiedt, ín het scherm waar de consultant zijn werk aftekent. En **niets werd rood** — de
  tests dekten wél *dát* de groepen gescheiden waren, niets over toon.
  **Vuistregel:** noemt een regel een KLEUR of een TOON, dan is de borging pas compleet als de presentatie
  óók één bron heeft (LI043) én een toets de twee tonen tegen elkaar legt. Een gedeelde data-afleiding
  garandeert niets over wat de gebruiker ziet.
  Borging (nu): pure `splits_afwijking(live, snapshot)` + `test_component_norm_adr052` voor de DATA;
  `afwijkingCodering.js` + `.lk-afwijking-bewust`/`-verschoven` voor de PRESENTATIE, met
  `afwijkingCodering.test.js` (de twee tonen verschillen in klasse, icoon én kleur; de neutrale zin draagt
  geen verwijt-taal; beide vensters lezen de bron en zetten er geen tweede toon naast).
  Referentie: `component_norm_service`, `MigratiegereedheidSectie`, `OpenPuntenSectie`, `SignaleringView`.

- **Het sterretje is gereserveerd voor opslaan-blokkerend.** Een **genormeerd** veld is géén **verplicht**
  veld: opslaan mag, de norm geldt op het **beoordelingsmoment** (het klaar-verklaren), niet op het invullen.
  Overlaad de sterretje-/verplicht-conventie daarom niet met de norm — anders verliest hij zijn betekenis
  waar hij wél blokkeert. De norm-aanduiding zegt het met zoveel woorden: *"telt mee om klaar te kunnen
  verklaren; opslaan kan wel zonder."* Borging: `VeldUitleg` `LAT_PASSAGE` (geen sterretje op het veld).

- **Eén aanduiding per feit, op het kleinste omvattende element.** Niet per veld. Eén veld → veldlabel;
  groep velden → groepkop (BIV op de `<legend>`, niet 3× op de schaalvelden); sectie → sectiekop. Vallen de
  velden van één feit over meerdere secties uiteen: **melden, niet oplossen** — dat is een modelleerfout.
  **Borging (structureel, niet in tekst):** de view geeft het **feit** door (`norm-feit="…"`), géén
  plaatsings-boolean — de bouwsteen `VeldUitleg` beslist zélf uit de ge-provide norm of hij de aanduiding
  toont, zodat een view er niet stiekem een tweede voor hetzelfde feit bijzet — plús een **tellende test per
  scherm** (`#[data-norm-lat]` == aantal genormeerde feiten; BIV precies één keer). Referentie:
  `ComponentFormulier.test.js` / `ComponentDetail.test.js`.

- **Hetzelfde feit heet overal hetzelfde — of de brug wordt zichtbaar gemaakt.** De feitnaam is gelijk op
  het normscherm, in de werkvoorraad en op het component-badge (alle uit `NORM_FEIT_LABEL`). Wijkt een
  **sectiekop** bewust af omdat die beter is voor de consultant ("Waarvoor gebruiken we het" i.p.v.
  "Bedrijfsfunctie"), dan draagt die sectie het feitwoord als **ondertitel, per constructie uit dezelfde
  labelbron** — zo herkent de consultant de plek die zijn werkvoorraad bedoelt zónder de bewust gekozen kop
  op te geven. **Enkelvoud/meervoud is geen afwijking** (Contract↔Contracten, Verantwoordelijke↔
  Verantwoordelijkheden blijven). Borging: `ComponentBedrijfsfunctieSectie` (ondertitel uit
  `NORM_FEIT_LABEL.bedrijfsfunctie`) + een test op de **zichtbare tekst** (C1). Aanvulling op §5
  Terminologie.

- **Toon gevolgen vóór het opslaan, niet erna.** Raakt één handeling veel objecten (een feit verplicht
  stellen raakt elk component), dan leest de gebruiker **vooraf** wat het doet: *"raakt 12 systemen die er
  nu niet aan voldoen — waarvan 1 eerder klaar is verklaard."* **Geen blokkade, geen waarschuwingskleur —
  een rustige voorspelling**, zodat hij het met open ogen doet. De voorspelling en de latere werkvoorraad
  komen uit **dezelfde afleiding** (`feit_vastgesteld`), zodat het voorspelde aantal klopt met wat de
  consultant daarna ziet (geen tweede telling). Onderscheiden van de bevestiging-die-het-gevolg-benoemt
  (LI043, §LI035): dát is een auditeerbaar akkoord bij een terugzet-/vernietig-handeling; dit is een
  vrijblijvende vooruitblik. Referentie: `component_norm_beheer_service.impact_voor_feit`, `NormBeheer.vue`.

- **Taal volgt de gebruiker, niet het model (LI045-instantie van §5).** Gebruik het begrip waarop de
  gebruiker zoekt en dat een verantwoordelijke kent — **"Archiefwet"**, niet "houdt gegevens vast"
  (ADR-053). Analyse-/modeltaal hoort niet op het scherm; toets tegen het randgeval (§5).

## LI046 — de kaart vertelt, het component verandert (ADR-054)

Drie regels over de beweging kaart ↔ component. Alle drie vanuit de gebruiker; alle drie geborgd
in code (zie likara-frontend §LI046 voor het hoe), niet in tekst.

- **De kaart vertelt, het component verandert.** Er is **geen mutatie-ingang vanaf de kaart**. De
  kaart is een lees-/verwijs-oppervlak: hij brengt je naar het feit; het wijzigen gebeurt op het
  detailscherm. Bouw op de kaart nooit een "wijzig hier"-affordance.
- **Je landt bij het feit waar je vandaan kwam.** Klik je op de kaart op een relatie/feit, dan land
  je op de plek waar dát feit leeft (de juiste tab, of het gemarkeerde veld) — niet op een kale
  detailpagina. De aanleiding leeft in de URL, dus de landing is **deelbaar en herstelbaar**.
  - **Wat niets kan doen, staat er niet — geen route beloofd waar niets te landen valt.** Eén regel,
    twee verschijningsvormen: (a) bestaat er geen eerlijke landingsplek (een type zónder detailscherm;
    een feit zónder anker), dan toont LIKARA **geen link** — nooit kaal landen of "de dichtstbijzijnde
    tab", want beide liegen; (b) een **besturing die op dit moment geen werk kan verrichten** wordt
    níét getoond (niet uitgegrijsd, niet leeg) — de kijkinstellingen-kolom verschijnt alléén bij een
    getekende kaart (`heeftData`), want een filter zonder verzameling belooft iets wat hij niet kan
    nakomen. Het gat is zichtbaar (geen affordance), niet verzwegen. (Code: likara-frontend §LI046.)
  - **Een veld-anker markeert, het opent geen bewerk-modus.** `?veld=` markeert het veld op het
    Overzicht met de Bewerken-knop ernaast; het duwt je niet ongevraagd in een invoerscherm. Reden:
    **een gegokte eigenaar is erger dan een lege eigenaar** — LIKARA verzint geen antwoord, het brengt
    je naar de plek en laat jou beslissen (spiegel van de kernregel §LI041 "verzint nooit een antwoord").
- **En je komt terug waar je was.** Terugkeren of herladen **mét bewaard werk ís de expliciete
  gebruikersactie** — de kaart tekent direct het bewaarde beeld; het beginscherm hoort bij een **verse
  start** (herziet de oude LI023-vlag-regel voor de herstelde terugkeer; zie §LI023 + likara-frontend).
  - **Is er niets meer om naar terug te keren, dan zegt LIKARA dát.** Een volledig verdwenen selectie
    (de componenten bestaan niet meer) krijgt een **eerlijke, gedempte melding** ("De eerder gekozen
    componenten bestaan niet meer", vervallen-taal — geen fout van de gebruiker) met de "Begin
    opnieuw"-uitweg ter plekke, niet een zwijgzaam leeg canvas. Instantie van de eerlijk-gaten-tonen-
    lijn (§LI034 "eerlijk gaten tonen"): een belofte ("je komt terug waar je was") draagt haar eigen
    uitzondering.

## LI046 — de kaart leesbaar houden (linkerkolom + relaties zien)

Alle regels vanuit de gebruiker; het hoe staat in likara-frontend §LI046 (linkerkolom + hoedanigheid).
Gebouwd `3a72b35` (kolom) + `6651f1f` (banen).

- **Vertrekpunt vs. kijkinstelling — twee bakken.** Een **vertrekpunt** beantwoordt "waar begin ik?" en
  werkt zónder inhoud (opgeslagen views, zoeken, hele landschap). Een **kijkinstelling** versmalt een
  beeld dat er al is (filters, ringen, drempels) en werkt alleen mét een getekende kaart. Ze horen niet
  in dezelfde bak: staan ze bij elkaar, dan gaan de vertrekpunten zwerven en ontstaat dubbeling.
  (Toegepast: vertrekpunten op het startpaneel `KaartBeginscherm`, kijkinstellingen in de
  `heeftData`-gegate kolom.)
- **Eén plek per functie.** De opgeslagen views hadden één bron en **drie** renderplekken met
  verschillend gedrag — dat waren geen drie weergaven maar drie halve versies (bron van de dubbeling).
  Beheer (openen/bewerken/verwijderen) hoort op **één** plek te leven (nu het startpaneel). Zusje van de
  KERNLES-LI038-convergentieregel.
- **Een verborgen instelling die wél versmalt, laat dat zien.** Een ingeklapte filter (Rol & BIV achter
  een `<details>`) draagt een zichtbaar merk op de kop zodra hij iets wegneemt (`lk-rolbiv-actief`-badge,
  spiegel van "+ Filters actief"). Anders versmalt er iets wat de gebruiker niet kan waarnemen — dat is
  "stiekem verbergen" (§P8), nu voorkomen.
- **Zichtbaar gaat boven aanklikbaar (KERN).** Wat je niet ziet, klik je niet aan — je klikt niet op
  iets waarvan je niet weet dat het bestaat. Op de kaart: **meervoud moet zichtbaar zijn, niet
  ontdekbaar.** Lopen er meerdere relaties tussen twee knopen, dan krijgt **elke hoedanigheid een eigen
  baan** (een aparte lijn), niet één lijn die je moet aanklikken om de rest te vinden. Een teller telt
  alléén **binnen** dezelfde soort ("N×"); ongelijksoortige feiten (koppeling · contract · beheer) worden
  **nooit** opgeteld — dat zou wissen wat de consultant moet weten. Aanvullend: de klik levert altijd
  **alles onder het paar** ("Tussen deze twee:"), zodat niets verstopt blijft.
- **Richting is betekenis.** Heen (A→B) en terug (B→A) zijn **twee feiten**, geen dubbeling —
  samenvoegen wist informatie. Ze krijgen twee gescheiden banen.
- **De laan is de betekenis — niet "oplossen" als dubbeling.** In een **lanen**weergave (Lagen) mag
  dezelfde entiteit in meerdere lanen voorkomen — geen dubbeling maar precies het antwoord ("Culemborg
  als gebruiker" naast "Culemborg als beheerder"; instance-projectie, LI036). **Grens:** in een weergave
  **zonder** lanen (Overzicht/Praatplaat) hoort de entiteit **één keer** te staan, met de relaties als
  **gescheiden lijnen** (baan-per-hoedanigheid), niet als meerdere knopen. Een volgende sessie mag de
  lanen-meervoud niet "oplossen".
