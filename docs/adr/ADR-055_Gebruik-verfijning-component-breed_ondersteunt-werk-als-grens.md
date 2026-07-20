# ADR-055 — De gebruik-verfijning is component-breed: `ondersteunt_werk` is de grens

| | |
|---|---|
| **Status** | Besloten (LI047) — bouw volgt in een eigen slice |
| **Datum** | 2026-07-20 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-036 (grof organisatiegebruik) · ADR-036a (afdeling structureel) · ADR-038 (groep hoort altijd bij een organisatie) · **ADR-041 (het precedent: de grove laag werd component-breed, het type-slot verdween)** · **ADR-045 (`ondersteunt_werk` als catalogus-eigenschap van het componenttype)** · ADR-043 (bedrijfsfunctie — de verwante vraag die dezelfde grens al hanteert) · ADR-035 (registratiegat-signalen) · ADR-052 (tenant-norm — het feit `gebruikersgroep`) · LI057–LI059 (opheffing van de `applicatie`-subtabel — de herkomst van het overblijfsel) |
| **Grond** | `docs/Checkpoint-gebruik-component-breed-V047.md` (read-only, LI047) |
| **Herziet** | De impliciete applicatie-binding van de gebruik-verfijning. Er is geen ADR die deze binding vastlegde; ze bestond uitsluitend als applicatie-zijdige controle. |
| **Invariant (onschendbaar)** | **De vraag "wie gebruikt dit" wordt gesteld waar mensen ermee werken — niet waar het toevallig ooit is gebouwd.** De grens is één bestaande catalogus-eigenschap, nooit een typelijst in code. |

---

## Context / de gebruikersvraag

LIKARA registreert het gebruik van een component op twee niveaus. **Grof:** welke organisatie gebruikt
dit. **Fijn:** welke afdeling of team binnen die organisatie. De grove laag werkt sinds ADR-041 voor elk
componenttype; de verfijning was gebonden aan componenten van het type `applicatie`.

Bij een ontvlechting houdt die grens geen stand. De gedeelde G-schijf waarop Burgerzaken werkt heeft net
zo goed een gebruikende afdeling als het zaaksysteem — en juist bij een gedeelde fileshare is "wie werkt
hierop" de vraag waar de hele ontvlechting op vastloopt. Wie moet er mee, wie blijft achter, wie moet
worden geïnformeerd.

De aanleiding was concreet. Bij het ontwerp van het overzicht "open punten per component" bleek dat op
een fileshare, een SaaS-dienst en een databaseserver het punt *"nog geen gebruikersgroep vastgelegd"*
verschijnt — terwijl de consultant het daar **niet kan wegwerken**. Het overzicht toont dan een taak die
niet bestaat. Drie voorgestelde uitwegen bleken alle drie compromissen: laat twee schermen verschillend
antwoorden op dezelfde vraag, verzwak de vraag voor iedereen om hem voor sommigen beantwoordbaar te
maken, of laat het overzicht een punt tonen dat de gebruiker net heeft beantwoord.

Dit ADR pakt in plaats daarvan de oorzaak.

---

## Het besluit

1. **De verfijning "welke afdeling of team gebruikt dit component" komt beschikbaar voor elk
   componenttype dat werk ondersteunt** — niet langer alleen voor applicaties.

2. **De grens is de bestaande catalogus-eigenschap `ondersteunt_werk` (ADR-045).** Draagt een
   componenttype die vlag niet, dan wordt de vraag daar niet gesteld: het feit telt er niet mee en het
   signaal wijst er niet naar. De grens is dus **beheerbaar en afgeleid**, nooit een typelijst in code.

3. **De grove laag blijft ongewijzigd.** "Deze organisatie gebruikt dit component" werkt al
   component-breed en blijft naast de verfijning bestaan — inclusief de bestaande regel dat een
   verfijning de grove koppeling op díé plek vervangt, en dat een groep altijd bij een organisatie hoort
   (ADR-038).

---

## Redenering

### Er was nooit een domeinregel

De beperking bestond als **één typevergelijking in de applicatielaag**, bij het aanmaken van een
gebruikersgroep. Wijzigen, verwijderen en lezen kenden hem niet. Het commentaar erboven verraadt de
herkomst: toen `applicatie` nog een eigen subtabel was, wás de ouder per definitie een applicatie. De
LI059-herfundering hief die subtabel op en verving de structuur door een typevergelijking — de beperking
bleef staan als controle, zonder dat er ooit een reden voor is opgeschreven.

Twaalf ADR's noemen gebruikersgroepen. **Geen enkele grondt de grens.** Wat er wél staat wijst de andere
kant op: ADR-036 beschrijft de groep als *de fijne verfijning ván het grove feit*, en dat grove feit is
component-breed.

Een beperking die niemand heeft besloten en die niemand kan verantwoorden, is geen ontwerp maar een
overblijfsel.

### Het precedent staat al in de repo

ADR-041 deed **exact deze herziening één laag hoger**, met dezelfde vaststelling: bij analyse bleek de
onderliggende structuur al component-breed, en het type-slot verdween. Dit is dezelfde beweging, één laag
dieper — geen nieuw principe, maar het afmaken van een herziening die halverwege is blijven steken.

Dat de fijne laag toen niet is meegenomen, is verklaarbaar: ADR-041 ging over de grove laag en had geen
aanleiding om verder te kijken.

### Er verandert geen enkele bepaling

Dit is de kern van waarom deze weg de drie alternatieven verslaat. Het signaal blijft dezelfde relatie
meten. De norm geeft dezelfde uitkomst. De klaarverklaring bevriest hetzelfde. De contracttoets die
vastlegt dat feit en signaal één bron delen, blijft ongewijzigd slagen.

**Wat verandert is uitsluitend wie de vraag kán beantwoorden.** Er wordt niets ontkoppeld, niets
verzwakt en niets van betekenis veranderd. Daarmee is dit de goedkoopste ingreep die tegelijk de meest
volledige is.

### Waarom `ondersteunt_werk` de juiste grens is

De vraag "welke afdeling gebruikt dit" veronderstelt dat er mensen mee werken. Bij een applicatie, een
fileshare, client-software, een SaaS-dienst of een landelijke voorziening is dat zo. Bij een
databaseserver, een rekenserver of een integratievoorziening niet: die worden door **andere componenten**
gebruikt, en dat is een koppeling, geen gebruik.

Stel je de vraag daar toch, dan zet je de consultant aan het werk voor een antwoord dat niet bestaat. Hij
kan het punt niet afvinken, het blijft op zijn overzicht staan, en hij leert het overzicht te negeren.
Dat is duurder dan de ontbrekende registratie ooit was.

LIKARA kent dit onderscheid al en gebruikt het al voor **dezelfde soort vraag**: het bedrijfsfunctie-feit
("waarvoor gebruiken we dit", ADR-043) is al op deze vlag gescoopt, aan zowel de signaal- als de
registratiekant. Twee verwante vragen die dezelfde grens hanteren is geen toeval maar consistentie. We
introduceren hier geen nieuw begrip — we passen een bestaand begrip toe waar het al hoorde te gelden.

Dat de vlag **beheerbaar** is (ADR-045: een catalogus-eigenschap, geen hardcoded lijst) betekent
bovendien dat een organisatie die er anders over denkt de grens zelf verlegt, en dat een nieuw
componenttype de regel automatisch erft.

---

## Gevolgen

### Wat er zichtbaar verandert, per componenttype

| Componenttype | `ondersteunt_werk` | Vandaag | Na dit besluit |
|---|:-:|---|---|
| applicatie | ja | verfijning beschikbaar | **ongewijzigd** |
| fileshare | ja | geen ingang; het punt staat er en is onbeantwoordbaar | **ingang verschijnt**, het punt wordt wegwerkbaar |
| saas_dienst | ja | idem | **ingang verschijnt** |
| client_software | ja | idem | **ingang verschijnt** |
| landelijke_voorziening | ja | idem | **ingang verschijnt** |
| database | **nee** | het punt staat er en is onbeantwoordbaar | **het punt verdwijnt** — de vraag geldt hier niet |
| server_compute | **nee** | idem | **het punt verdwijnt** |
| integratievoorziening | **nee** | idem | **het punt verdwijnt** |

### Het tenant-brede signaal wordt kleiner

Het signaal "component zonder gebruikersgroep" wijst in het demolandschap vandaag **twaalf van de
negentien** componenten aan; na de scoping zijn dat er **elf**.

> **Correctie (bij de bouw gemeten, LI047).** Het checkpoint noemde "twaalf naar negen". Dat was een
> rekenfout: daar werden alle drie de niet-applicatiecomponenten afgetrokken, terwijl in dezelfde zin
> stond dat de fileshare en de SaaS-dienst blijven — die dragen `ondersteunt_werk` immers wél. Er valt
> precies **één** component af: de Shared DB-server (type `database`). Het effect van deze scoping op
> het demolandschap is dus kleiner dan gedacht; de *reden* ervoor verandert er niet door.

Dat is **correctie, geen verlies.** Dat component stond als openstaand geregistreerd terwijl er niets
te doen viel. Een signaallijst die taken bevat die niemand kan uitvoeren, verliest zijn gezag — en dan
worden de terechte punten óók genegeerd.

### Zonder de scoping zou de norm onhoudbaar worden

De tenant-norm kent geen componenttype: een organisatie zet een feit verplicht voor **álle** typen
tegelijk of voor geen. Zou de verfijning overal mogelijk worden zónder de scoping, dan zou
"gebruikersgroep verplicht" ook gelden op een databaseserver, waar niemand het ooit kan afvinken.

De scoping lost dat op **bij de bron** in plaats van in de norm — precies zoals het bedrijfsfunctie-feit
het al doet. Besluit 2 is daarmee geen verfijning van besluit 1 maar een **voorwaarde** ervoor.

### Geen schemawijziging, geen migratie

De vreemde sleutels van de gebruikersgroep wijzen alle naar generieke doelen: het element, het grove
gebruiksfeit (zelf al component-breed) en de afdeling-partij. De band met het component is een
`serving`-relatie, en de relatie-facade valideert geen elementtype.

**De structuur is dus al component-breed.** De beperking leefde volledig in de applicatielaag. Dat is
tegelijk het sterkste bewijs dat het een overblijfsel was en geen ontwerp: een echte domeingrens had zich
in het schema vastgelegd.

### Wat níét verandert

- **Bestaande bevroren klaarverklaringen wijzigen niet.** Hun momentopname is opgeslagen tekst en wordt
  nooit herrekend.
- **De betekenis van het feit `gebruikersgroep`** in de tenant-norm blijft gelijk.
- **Het rechtenmodel** blijft ongemoeid: de permissies zijn entiteit-gebonden, nooit type-gebonden.
- **De grove laag** en de verdringingsregel (fijn vervangt grof op die plek) blijven zoals ze zijn.

---

## Open punten — dit ADR beslecht ze niet

1. **De historische veldnaam.** Het API-veld heet `applicatie_id` maar draagt een component-id. Dezelfde
   situatie bestaat al bij de grove laag, waar de naam bewust historisch is gelaten. Laten staan of
   meenemen in de opruimsnede die al loopt voor `heeft_applicatie_subtype` — **niet beslist**.

2. **Het antwoord bij weigering.** De huidige weigering geeft "bestaat niet" in plaats van "mag hier
   niet". Als er na dit besluit nog een weigering overblijft, moet die dan een eerlijker antwoord geven —
   **niet beslist**.

3. **Zes docstrings en drie naamgevingen** zeggen "applicatie" waar "component" bedoeld wordt. Ze zijn
   geen gedrag, maar liegen na de verbreding wel. Eigen opruimsnede — **volgorde niet beslist**.

4. **De demodata.** De drie niet-applicatiecomponenten hebben nog géén gebruik geregistreerd, grof noch
   fijn. Of de seed er een voorbeeld bij krijgt zodat de verbreding zichtbaar wordt in plaats van een
   leeg tabblad — **niet beslist**.

5. **Geen scan bewaakt misleidende contractnamen.** Dit punt staat al breder open en wordt hier alleen
   genoemd, niet opgelost.

---

## Borging (bij de bouw, niet in dit ADR)

De regel moet niet als tekst blijven bestaan. Bij de bouw hoort minimaal:

- een toets die **over de catalogus itereert** in plaats van typen op te sommen, zodat een nieuw
  componenttype de regel erft zonder codewijziging;
- een toets die de weigering-regressie vangt (de verfijning op een fileshare mag niet worden geweigerd);
- het **ongewijzigd** laten slagen van de bestaande contracttoets die vastlegt dat feit en signaal één
  bron delen — dat is het bewijs dat deze herziening de norm niet heeft aangeraakt.
