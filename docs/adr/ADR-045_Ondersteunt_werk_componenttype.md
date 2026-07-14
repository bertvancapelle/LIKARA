# ADR-045 — "Ondersteunt werk" als eigenschap van het componenttype

| | |
|---|---|
| **Status** | Besloten (LI040) |
| **Datum** | 2026-07-13 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-043 (bedrijfsfunctie als logische ruggengraat) · ADR-044 (plaatsing als eerste-klas feit — de koppeling landt op de plaatsing) · ADR-026 (precedent: beheerbare eigenschap op het componenttype; dit ADR repareert bovendien een gat dat ADR-026's belofte breekt) · ADR-036 (grof→fijn + "detaillering ontbreekt"-signaal) · ADR-028 (`componentrol`: verplichte eigenschap met vaste beginstand) |
| **Grond** | `docs/Feitenrapport-ondersteunt-werk-V040.md` (checkpoint LI040) · besluiten Bert LI040 (zeven knopen gesloten) |
| **Invariant (ongewijzigd)** | Score blijft de enige lifecycle-driver. Dit ADR is registratie + leeslaag; de engine wordt niet geraakt. |

---

## Context — de vraag die de consultant stelt

De consultant koppelt in de workshop componenten aan bedrijfsfuncties: *"dít werk doen wij
met dát."* Niet elk component kan dat antwoord zijn. Een zaaksysteem ondersteunt werk; een
database ondersteunt een systeem, geen mens. Zonder regel wordt de koppel-picker een
technische inventaris en verwordt de logische kaart tot een infrastructuurplaat.

De regel mag **geen lijst in code** zijn: welke soorten componenten werk ondersteunen is
een inrichtingskeuze van het platform, geen wet. Ze hoort dus thuis waar de andere
eigenschappen van een componenttype al leven — de componenttype-catalogus, beheerd door de
platformbeheerder (precedent: `checklist_dragend`, ADR-026/LI058).

Het checkpoint (feitenrapport LI040) bevestigde dat er vandaag géén bestaande waarheid is
die dit al zegt: `checklist_dragend` ("wordt beoordeeld") dekt óók database/server/
integratievoorziening, en de ArchiMate-laag (`laag === 'application'`) is een afgeleide van
de typering met een andere betekenis. "Ondersteunt werk" is een echte derde as — en juist
daarom een eigen, beheerbare eigenschap.

---

## Besluit 1 — "Ondersteunt werk" is een eigenschap van het componenttype

Een nieuwe, beheerbare eigenschap op de componenttype-catalogus (`componentconfig_optie`,
dimensie `componenttype`). Kolomnaam: **`ondersteunt_werk`** (boolean).

- **Verplicht, geen derde stand.** Een componenttype ondersteunt werk of niet; "nog niet
  ingevuld" bestaat niet — zo'n type zou stil uit elke picker vallen. Vorm: **NOT NULL +
  `server_default false`** (spiegel van `componentrol`, ADR-028/migratie 0048, en van
  `checklist_dragend` zelf, migratie 0009); de migratie zet de vijf werkondersteunende
  typen (besluit 2) expliciet op `true`.
- **Alleen op componenttypen — schema-afgedwongen.** De catalogus-tabel draagt naast de
  8 componenttypen ook 10 rijen van andere dimensies (2 structuurrelatie-typen, 8
  ArchiMate-relatietypen); die mogen de eigenschap niet dragen. De passende vorm is het
  ADR-026-precedent (migratie 0025, `ck_componentconfig_typering_volledig`): een
  **conditionele CHECK per dimensie**, hier concreet
  `dimensie = 'componenttype' OR ondersteunt_werk = false` — buiten de dimensie blijft de
  kolom structureel op zijn default. NB: `checklist_dragend` heeft zo'n CHECK **niet**
  (daar is de dimensie-binding louter conventie + dimensie-gefilterde leespaden); dit ADR
  kiest bewust de strakkere 0025-borging — *structureel boven conventioneel*.
- **Beheerbaar door de platformbeheerder** onder de bestaande
  `PlatformEntiteit.COMPONENTCONFIG` (beheerder LAW, operator L) — geen nieuwe permissie.
  De audit beweegt gratis mee: de capture is mapped-column-gebaseerd
  (`app/core/audit.py`, `bouw_wijziging`), dus elke flip verschijnt per-veld in het
  platform-auditspoor.

---

## Besluit 2 — Welke typen ondersteunen werk (ruim)

| Ondersteunt werk | Ondersteunt géén werk |
|---|---|
| `applicatie` · `saas_dienst` · `landelijke_voorziening` · `fileshare` · `client_software` | `database` · `server_compute` · `integratievoorziening` |

**Motivering — deze draagt besluit 6.** De keuze is bewust **ruim**. In de praktijk hoort
de consultant: *"vergunningdossiers? Die staan op de G-schijf, in Word."* Dat is geen ruis
maar de waardevolste bevinding van de dag. Sluit je fileshare en client software uit, dan
kan hij die werkelijkheid niet vastleggen en toont LIKARA daar "nog geen ondersteunend
systeem" — terwijl er wél iets is, alleen iets zorgwekkends. Een echt gat en een noodgreep
moeten verschillend zichtbaar zijn, en dat kan alleen als de noodgreep registreerbaar is.

⚠ **Erkende keerzijde — harde ontwerpeis voor gate 3, geen losse wens:** een
bedrijfsfunctie die door een fileshare of client software gedragen wordt, mag op de kaart
**niet als volwaardig ondersteund** ogen. Dat is een vraag van het gap-signaal (ADR-044
besluit 4, per plaatsing), niet van de picker. Gate 3 ontwerpt het gap-signaal dus met
minstens drie standen in gedachten: niet onderzocht · gedragen door een volwaardig systeem
· gedragen door een noodgreep (of vastgesteld "geen systeem", ADR-044 besluit 3).

---

## Besluit 3 — De picker toont alleen wat werk ondersteunt, en benoemt zijn scope

De koppel-picker (component → bedrijfsfunctie/plaatsing, gate 2) **weert vooraf**: alleen
componenten van typen met de eigenschap verschijnen. Dat volgt de niet-onderhandelbare
picker-regel (*toon nooit een optie die de backend zou weigeren*).

Eronder staat één vaste regel die **de scope benoemt, niet de afwezigheid verklaart**:

> *"Componenten waarmee werk gedaan wordt."*

**Uitdrukkelijk verworpen: een uitleg-bouwsteen die vertelt waaróm iets ontbreekt.**
Doorslaggevende reden: in een verse tenant is het landschap onvolledig, dus het **vaakst
voorkomende** geval van "niet gevonden" is *niet geregistreerd*, niet *geweerd*. Een
uitleg zou moeten raden en zou in het meest voorkomende geval een onwaarheid tonen
("databases mogen hier niet") terwijl de waarheid is "dat component ken ik niet". Een
scope-regel is **altijd waar**; een verklaring van afwezigheid niet. Bovendien: de
consultant is geen kleuter — hij weet dat een database geen werk doet.

Dit herziet het eerdere LI039-voornemen ("picker legt uit waarom een optie ontbreekt",
fase-A-patroon 11 / OPVOLGPUNTEN gate-1b punt 3): dat voornemen is bij de LI040-weging
**niet gebouwd maar vervangen** door de scope-regel.

*Geparkeerd (opvolgpunt, geen schuld): "geweerd tonen mét reden" als evaluatiepunt in echt
gebruik. De scope-regel is de plek waar dat later kan groeien, zonder herbouw.*

---

## Besluit 4 — Een componenttype is in één handeling volledig in te richten (+ bugfix)

De platformbeheerder zet **alle** eigenschappen van een componenttype bij het aanmaken:
naam, ArchiMate-typering, `checklist_dragend`, `ondersteunt_werk`. Het Create-schema
draagt dus beide vlaggen; het beheerscherm biedt ze in de aanmaak-dialoog aan.

Dit repareert een **bestaand kapot pad** (checkpoint-bevinding): het beheerscherm stuurt
`checklist_dragend` al mee bij aanmaken (`ComponentConfigBeheer.vue:157`), terwijl het
Create-schema (`extra='forbid'`, `schemas/componentconfig.py:49-96`) dat veld niet kent →
422 `extra_forbidden`. Er is vandaag dus **geen werkende route via het beheerscherm om een
componenttype toe te voegen** — precies de functie waarvoor ADR-026 geschreven is. (Via de
kale API, zonder de vlag, kan het wel; dat maakt het scherm-pad niet minder kapot.) De fix
landt in deze slice, want het is dezelfde regel op dezelfde plek; hem apart parkeren zou
dezelfde bestanden een tweede keer openen.

⚠ De 422 is offline op schema-niveau vastgesteld (Pydantic weigert exact de payload die
het scherm bouwt), **niet in de browser** gereproduceerd. Het bouwdraaiboek krijgt hiervoor
een verplichte browsercheck-stap (vóór én ná de fix).

---

## Besluit 5 — Filteren gebeurt op de eigenschap, nooit op een lijstje typen

Eén server-side filter op de eigenschap zelf, met **twee gebruikers**:

1. **de koppel-picker** (gate 2): welke componenten mag ik kiezen;
2. **de componentenlijst**: *"welke componenten in mijn landschap ondersteunen geen
   werk?"* — de vraag die de beheerder stelt vóór en na een flip (besluit 7 leunt hierop).

Zet de beheerder morgen een negende type aan, dan bewegen picker én lijst vanzelf mee.
**Geen typen-opsomming in de frontend, geen tweede waarheid.** (Het checkpoint vond de
bestaande hardcoded inperkingen — o.a. de flow-picker op `'applicatie'` en de
kaart-predicaten; die betekenen iets anders en blijven staan, zie Invarianten.)

⚠ **Vereiste — de kern van de bouw: de tenant-frontend moet de eigenschap kunnen lezen en
erop kunnen filteren.** De feitelijke stand (checkpoint B2, gecorrigeerd t.o.v. de eerdere
formulering in de opdracht):

- Het **read-pad voor catalogus-vlaggen naar de tenant bestaat al**: `GET
  /componenten/opties` levert per componenttype o.a. `checklist_dragend`
  (`componentconfig_catalog.actieve_opties_per_dimensie` → `ComponentKeuze`). Een
  **nieuwe** vlag reist daar echter niet automatisch in mee — hij moet expliciet aan de
  catalog-select, het resultaat-dict en het `ComponentKeuze`-schema worden toegevoegd.
- Wat **écht ontbreekt** is een server-side filter op de *componentenlijst* zelf: het
  `componenttype`-filter op `GET /componenten` is enkelvoudig, en er bestaat geen filter
  dat tegen een catalogus-vlag joint. (Precedent voor een herhaalbare multi-param bestaat
  op hetzelfde endpoint: `componentrol`.)

Het ADR legt de eis vast (server-side, op de eigenschap, met deze twee gebruikers); de
**vorm** van het filter (vlag-param met catalogus-join, of anders) kiest de bouwopdracht.

---

## Besluit 6 — Een flip verandert zichtbaarheid, nooit veldwerk

Zet de beheerder de eigenschap uit voor een type (bv. `fileshare`), dan:

- **verdwijnt het type uit de picker** — vanaf nu niet meer koppelbaar;
- **blijven bestaande koppelingen staan.** Ze worden nooit stil verwijderd. Een beheerder
  maakt met een vinkje een beleidskeuze over **toekomstige registratie**; hij spreekt geen
  oordeel uit over wat consultants in het veld hebben vastgesteld. Zou LIKARA die
  koppelingen wissen, dan verdwijnt veldwerk door één vinkje en liegt de kaart over gaten
  die er niet zijn — hetzelfde CASCADE-gevaar dat bij vervallen bedrijfsfuncties al is
  verworpen (*vervallen ≠ verwijderen*, ADR-043);
- **wordt niets herberekend.** Geen backfill, geen fan-out. Anders dan bij
  `checklist_dragend`, waar aanzetten een naloop had (`_activeer_type_backfill`: per
  tenant profielen bijmaken + herberekenen) omdat er engine-state moest **ontstaan** —
  hier hoeft niets te ontstaan of te verdwijnen. De **geest** is gelijk (een config-flip
  vernietigt nooit registratie; True→False laat bij checklist de profielen ook inert
  staan), de machinerie niet;
- **de engine wordt niet geraakt.**

---

## Besluit 7 — Een flip levert werkvoorraad, geen speurtocht *(vorm vastgelegd; gebouwd in gate 2/3)*

De consultant hoeft niets op te sporen; het werk komt naar hem toe.

| Wanneer | Wat | Waarom |
|---|---|---|
| **Vóór de flip** | *"Dit raakt 12 plekken waar nu een fileshare het werk draagt — doorvoeren?"* | Voorbeeld-vóór-bevestigen (het patroon van het referentiemodel-inlezen, gate 1b). Geen drempel maar een **spiegel**: bij 40 plekken is niet-doen vaak het juiste antwoord. |
| **Ná de flip** | Een **gedeelde, afgeleide teller** (*"12 plekken vragen aandacht"*) met een lijst van uitsluitend de geraakte plekken | Een teller die aantoonbaar naar **nul** kan. Gedeeld, niet persoonlijk: met meerdere consultants op één landschap is een privé-inbox een tweede waarheid. Read-only afgeleid — **niets opgeslagen**. |
| **In de lijst** | Gebundeld **per component** (*"G-schijf Vergunningen — draagt 5 plekken"*) | Drie besluiten in plaats van twaalf regels. |

**Drie uitgangen per bundel** (nooit een doodlopend pad):

1. **Vervangen** door een component dat wél werk ondersteunt — met de bestaande "meerdere
   plekken tegelijk"-handeling (ADR-044 besluit 2);
2. **"Hier gebruiken we geen systeem"** vaststellen → een **bevinding** (ADR-044
   besluit 3), niet een ontbrekende registratie. Dit is vaak de wáre uitkomst: dit werk
   draait op een netwerkschijf. De flip vernietigt die waarheid niet — hij dwingt haar uit
   te spreken;
3. **De regel terugleggen** bij de beheerder — vuurt het op twaalf plekken, dan klopte de
   regel wellicht niet. Ook dat is een geldige uitkomst; de teller gaat dan aan de bron
   naar nul.

**Bewust aanvinken — niet-onderhandelbaar.** Bij een bundel-actie staat **niets
voorgevinkt**. Elk vinkje is een **uitspraak** ("ik weet dat dit hier het antwoord is"),
geen selectie; voorvinken zou van *"ik heb dit vastgesteld"* een *"ik heb dit niet
tegengehouden"* maken — exact het onderscheid dat ADR-044 besluit 3 scherp houdt.
Bovendien muteert de consultant hier **veldwerk van een collega**. Een expliciete
*"selecteer alle N"* mag; een stille default niet. De knop telt mee (*"Vervang op 3
plekken"*) en de zin eronder benoemt wat er gebeurt **én wat niet** (*"de 2 niet-gekozen
plekken blijven ongewijzigd en blijven op de lijst"*).

**Elke plek telt voor zichzelf** — de teleenheid is de plaatsing, niet de functie en niet
het component (ADR-044 besluit 4).

---

## Besluit 8 — Het signaal is afgeleid, nooit een opgeslagen status

Een koppeling op een component van een type dat geen werk (meer) ondersteunt krijgt
**geen status-veld** (actief/inactief). Het feit is **af te lezen** uit het componenttype
— altijd actueel, ook na een tweede flip of een nieuw type. Een opgeslagen status zou een
tweede waarheid zijn die bij één gemiste bijwerking gaat liegen.

Weergave: **alleen de afwijking krijgt een merkteken** — amber ⚠ + tekst, de vorm van de
vervallen bedrijfsfunctie (gate 1b). **Geen rood** (er is niets kapot; de regel is
veranderd — de "lege uitkomst ≠ fout"-lijn). **Geen groen** (wat overal hetzelfde is, is
geen informatie en maakt de échte afwijking onzichtbaar).

---

## Scope — wat deze slice bouwt, en wat niet

**In deze slice (gate: schema-rakend):**

1. de eigenschap op de componenttype-catalogus (schema + service + beheerscherm + seed +
   reconcile-migratie in het 0023/0046-patroon);
2. de 422-bugfix: componenttype toevoegen via het beheerscherm werkt weer (besluit 4);
3. het read-pad naar de tenant-frontend (de eigenschap meeleveren op
   `/componenten/opties`) + het server-side filter op de eigenschap;
4. de componentenlijst-filter ("ondersteunt werk: ja/nee").

**Niet in deze slice — vastgelegd, gebouwd in gate 2/3** (besluiten 6–8 bestaan juist
zodat gate 2 er niet omheen ontwerpt):

- de koppel-picker zelf (gate 2);
- werkvoorraad, telling-vóór-bevestigen, bundel-actie met bewust aanvinken (gate 2);
- het afgeleide signaal + "fileshare als drager = gat, niet groen" (gate 3).

---

## Invarianten

- **Engine onaangeroerd** — score blijft de enige lifecycle-driver. Dubbele borging bij de
  bouw (import-afwezigheidstest + live geen-lifecycle-mutatie).
- **Geen regressie op bestaande pickers.** "Ondersteunt werk" geldt **uitsluitend** voor
  de bedrijfsfunctie-as. Een database blijft koppelbaar aan een server, een fileshare aan
  een contract, een koppelvlak in een flow. Koppeling · structuur (`draait_op`) · contract
  · procesvervulling: **alle vier ongemoeid** — expliciete browsercheck bij de bouw. (De
  procesvervulling is per ADR-042 bewust component-breed en blijft dat; de bestaande
  hardcoded inperkingen — flow-picker `'applicatie'`, kaart-predicaten — zijn eigen, losse
  waarheden en blijven staan.)
- **Ontwikkelmodus** — uitsluitend testdata; "migratie" = alembic-schemastap + reseed waar
  nodig, nooit een databehoudvraagstuk. De seed draagt de eigenschap expliciet per type
  (single source, F-6-les); een data-reconcile zet bestaande DB's op dezelfde stand.
- **Structureel boven conventioneel** — de regel leeft in de catalogus + het schema
  (incl. de dimensie-CHECK), nooit als lijst in code.

---

## Alternatieven overwogen

1. **Strikte set** (alleen `applicatie`/`saas_dienst`/`landelijke_voorziening`) —
   verworpen: de G-schijf-werkelijkheid wordt dan onvastlegbaar, en een echt gat en een
   noodgreep krijgen hetzelfde signaal.
2. **Een lijst met koppelbare typen in code** — verworpen: de regel is een
   inrichtingskeuze, geen wet; en het zou een tweede waarheid worden naast de catalogus.
3. **Uitleg-bouwsteen "waarom ontbreekt deze optie"** — verworpen voor de MVP: kan
   afwezigheid niet betrouwbaar verklaren in een onvolledig landschap (besluit 3).
   Geparkeerd als evaluatiepunt.
4. **Geweerde componenten tonen, gedempt, met reden** — verworpen: betuttelend voor een
   consultant die de regel kent, en het maakt "niet gevonden" dubbelzinnig.
5. **Voorgevinkte bundel-actie** — verworpen: maakt van een bevinding een
   niet-tegengehouden aanname, op andermans veldwerk (besluit 7).
6. **Opgeslagen status (actief/inactief) op de koppeling** — verworpen: tweede waarheid
   die kan gaan liegen (besluit 8).
7. **Flip blokkeren zolang er koppelingen bestaan** — verworpen: gijzelt de beheerder met
   veldwerk. LIKARA signaleert, de mens beslist.
8. **Koppelingen wissen bij een flip** — verworpen: vernietigt veldwerk met één vinkje.

---

## Opvolgpunten (ook opgenomen in `docs/OPVOLGPUNTEN.md`)

1. **"Geweerd tonen mét reden"** — evaluatiepunt in echt gebruik; groeit op de scope-regel
   (besluit 3), geen herbouw.
2. **Registratie-feiten: teruggeknipt (besloten LI040).** Het brede
   registratie-feiten-spoor (verantwoordelijkheid, benoemde verwijzingen, twee ankers,
   verplichte reden) blijft **blok D — ná de MVP**. Wat gate 2 wél meeneemt, omdat het
   bij de registratie zelf hoort en niet apart in te schuiven valt:
   - **wie legde dit vast, en wanneer** — server-gestempeld op het feit (nooit uit de
     payload), zichtbaar op de plek zelf. Zonder dit is "bewust aanvinken" (besluit 7)
     leeg: wie andermans veldwerk overschrijft, moet zien wiens werk het is. De
     audit-trail blijft het **vangnet** eronder (*"is dit later gewijzigd?"* —
     beheerdersvraag, eigen scherm), nooit de leeslaag op de plek van het feit.
   - **een optionele vrije toelichting** bij de bevinding *"hier gebruiken we geen
     systeem"*.

   **Verplichte reden is verworpen voor de MVP:** verplichten waar de uitspraak zichzelf
   verklaart (een koppeling) leert de gebruiker ruis typen, en die ruis besmet dan ook
   het geval waar de reden er wél toe doet. Verplichten kan later alsnog; een
   aangeleerde ruisgewoonte niet meer afleren.
3. **Gelijktijdig vastleggen door twee consultants** op dezelfde plaatsing — geen
   taakvraag maar een registratievraag (weigeren of eerlijk melden, nooit stil de laatste
   laten winnen). Ontwerppunt **gate 2**.
4. **Dode functie `_seed_tweede_type`** in de dev-seed met stale docstring
   (checkpoint-bevinding) — opruimen bij de bouw of expliciet parkeren.
