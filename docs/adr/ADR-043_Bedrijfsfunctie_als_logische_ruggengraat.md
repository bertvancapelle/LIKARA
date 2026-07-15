# ADR-043 — Bedrijfsfunctie als logische ruggengraat (herijking ADR-042)

**Status:** Besloten (LI038; subknopen beslist LI039) — **deels herijkt door ADR-044**
(plaatsing als eerste-klas feit: de boom = aggregation-plaatsingen met mogelijk meerdere
ouders; de koppeling wordt *(component, plaatsing)*; het grof-signaal en het gap-signaal
hangen aan de plaatsing. Onaangeroerd: bronsleutel, vervallen ≠ verwijderen,
modelinhoud-read-only, aanbod gesloten, procesregister verborgen, engine-invariant.)
**Datum:** 2026-07-12
**Herijkt:** ADR-042 (procesregister als "waarvoor"-as; bedrijfsfunctie-as bewust geparkeerd)
**Grond:** `docs/Feitenrapport-referentiemodel-bedrijfsfuncties-V038.md` +
`docs/Feitenrapport-bedrijfsfunctie-as-V039.md` (beide read-only, geverifieerd) +
GEMMA-bron (gemmaonline.nl/wiki/Bedrijfsfuncties, VNG Realisatie)
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt niet geraakt.
Dit is registratie + leeslaag.

---

## Context / aanleiding

LIKARA levert een **Logische ICT Kaart**. Een *logische* kaart beschrijft **wat** er moet gebeuren,
los van **hoe** het toevallig is ingericht. Vandaag rust de "waarvoor"-as op het **procesregister** —
de "hoe"-laag. Dat wringt met de belofte:

- Een **proces** is organisatie-eigen en veranderlijk: het verschuift met elke herinrichting. Een kaart
  die erop rust, tekent zichzelf elke reorganisatie opnieuw.
- Een **bedrijfsfunctie** is stabiel en gedeeld: activiteiten gegroepeerd omdat daarvoor vergelijkbare
  bedrijfsmiddelen, kennis of competenties nodig zijn — **onafhankelijk van hoe de processen zijn
  ingericht**. VNG rekent het bedrijfsfunctiemodel tot de **GEMMA Basisarchitectuur**: expliciet een
  *stabiel* architectuurproduct.
- **Stabiliteit is gevalideerd, niet aangenomen:** de bewerkdata van het GEMMA-functiemodel liggen jaren
  uit elkaar (bedrijfsfuncties-overzicht okt-2025, BA01-view aug-2025, losse elementen dec-2024; het
  model stamt uit de GEMMA 2-vernieuwing). Wat in GEMMA wél snel beweegt (standaarden, ZGW-API) leeft
  in een andere laag.

**Bijkomend, zwaarwegend:** vandaag is een verse tenant pas waardevol nadat de gemeente haar processen
heeft uitgeschreven — een drempel van maanden. Met een ingelezen referentiemodel is de volgorde
omgekeerd: **model inlezen → applicaties aanhangen → kaart**. Direct waarde, dag één.

---

## Besluit (kern)

1. **De bedrijfsfunctie wordt de ruggengraat van de logische kaart.** Componenten hangen **direct aan
   bedrijfsfuncties** ("Zaaksysteem ondersteunt Uitvoering Publieksdiensten"). Dit is de
   kern-registratie; zonder haar is een ingelezen functieboom een dood plaatje.
2. **Bedrijfsfunctie = eigen element-as** (ArchiMate **BusinessFunction**, ≠ BusinessProcess), genest,
   met **naam**, **definitie** en **stabiele bronsleutel**. Dit heropent de door ADR-042 geparkeerde
   functie-as.
3. **"Referentiemodel" wordt een eerste-klas begrip** (naam, herkomst, versie). LIKARA leest
   ArchiMate-referentiemodellen in (Open Exchange / AMEFF). **GEMMA-bedrijfsfuncties = instantie 1.**
   Meerdere modellen naast elkaar = meer rijen, geen herbouw.
4. **Motor generiek, aanbod gesloten.** De beheerder kiest uitsluitend uit **door LIKARA gevalideerde,
   aangeboden modellen**. De "eigen bestand"-route bestaat als capaciteit maar staat **niet open** —
   later een schakelaar, geen herbouw. *(Leveranciersoverweging: gecureerde referentiemodellen zijn
   potentieel verdienmodel; de generieke motor houdt dat goedkoop schaalbaar.)*
5. **Modelinhoud lees je, je wijzigt hem niet.** Naam, definitie en plek in de boom komen van de bron en
   worden bij een herinlees bijgewerkt. **De gemeente wijzigt modelinhoud niet.**
   - **Eigen functies toevoegen mag** (dragen geen bronsleutel; import raakt ze nooit aan).
   - **Afwijken doe je *bij* de functie, niet *in* de functie**: een eigen laag ernaast ("VNG zegt dit —
     wij zeggen dit"), als eigen registratie-feit. **Uitdrukkelijk verworpen:** "een wijziging maakt er
     automatisch een eigen functie van" — dat splitst ongemerkt een knooppunt mét registratie af
     (welke applicaties gaan mee? welke kinderen?), veroorzaakt dubbelen bij de volgende herinlees, en
     koppelt de gemeente stil los van de referentie.
6. **Vervallen ≠ verwijderen.** Een functie die uit een nieuwe modelversie verdwijnt wordt **gemarkeerd**,
   nooit hard verwijderd — hard verwijderen zou via CASCADE de **eigen registratie meesleuren**
   (feitelijk bevestigd). Signaal: *"deze functie bestaat niet meer in het model, maar N applicaties
   hangen er nog aan."*
7. **De bronsleutel is de identiteit.** Herhaalbaar bijwerken matcht op bronsleutel, **nooit op naam**
   (naam is niet uniek; hernoemd/verhangen zou onherkenbaar zijn).
8. **Geen synchronisatiemachine.** Het model verandert in jaren, niet maanden (zie context). Een
   herinlees is een **zeldzame, bewuste handeling**: gevalideerd bestand → **voorbeeldscherm** (zoveel
   nieuw / bijgewerkt / vervallen, en welke vervallen functies nog in gebruik zijn) → bevestigen. Geen
   live koppeling, geen achtergrond-sync, geen permanente conflictafhandeling.

### MVP-scope (eerste release)

- **Eén verhaal, één plek.** Een component hangt in de MVP **uitsluitend aan een bedrijfsfunctie**.
  Eén koppelregel, geen keuze — twee plekken die dezelfde vraag lijken te beantwoorden zou de gemeente
  laten vastlopen op "hang ik dit aan een functie of aan een proces?".
- **Het procesregister wordt VERBORGEN, niet verwijderd.** Geen menu-item, geen ingang, geen proceskolom
  op de kaart; `procesvervulling` blijft in het model bestaan maar wordt niet gevuld en verwart dus
  niemand.
- **Dit is geen technische schuld, maar een verdieping zonder trap.** De bouw blijft intact en wordt
  **hergebruikt** door de functie-as: de boom-afleiding, het diagram (zoeken/focus/inzoom/history), de
  vervulling-koppelregel en de gap-cue zijn **structuur-generiek**, niet proces-specifiek. Weggooien zou
  betekenen dat we het binnen weken opnieuw bouwen (n≥2: dit wordt de tweede instantie van "genestelde
  structuur met vervulling" → juist moment om te abstraheren).
- **Gaten zichtbaar vanaf dag één.** Een functie zonder ondersteunende applicatie is een eerlijk signaal
  — en meteen de sterkste demo: model inlezen, applicaties aanhangen, zien waar het landschap gaten heeft.

### Terugkeer van het procesregister (later, niet in MVP)

De functie blijft het **anker**; het proces wordt de **detaillering eronder** ("zo doen wij dat
concreet"), nooit ernaast. Daarmee is de vraag "waar hang ik het aan?" nooit dubbelzinnig — de volgorde
ligt vast. Wat het procesregister dan toevoegt: het operationele impact-inzicht ("wat gaat er *vandaag*
stuk"), de concrete taal van de proceseigenaar, en het applicatiefunctie-detail
(registreren/raadplegen/archiveren) dat op procesniveau leeft.

---

## Waarom niet "het procesregister hernoemen tot bedrijfsfuncties"

Overwogen en **verworpen**. Niet om semantische redenen, maar om één praktische:

**VNG-inhoud en eigen inhoud kunnen niet in dezelfde bak zitten als je de ene wilt kunnen verversen
zonder de andere te raken.** Bij een herinlees moet LIKARA weten welke rijen van de bron zijn (mag ik
bijwerken/vervallen verklaren) en welke van de gemeente (blijf eraf). Eén bak → de import overschrijft
eigen werk, óf durft niets bij te werken. Beide onbruikbaar. Daarnaast verliest de gemeente het vermogen
te zeggen *"wij doen dit anders dan de referentie"* — er is dan geen referentie meer om tegen af te
zetten.

Wat wél klopt aan het hernoem-gevoel: **de bouw is grotendeels herbruikbaar.** Daarom: tweede as die de
bouwstenen erft — niet dezelfde bak met een ander etiket.

---

## Feitelijke uitgangspositie (uit het checkpoint — geverifieerd, niet aangenomen)

**Aanwezig:**
- Proces draagt al een **vrije toelichting** (Text ≤10.000) → een **definitie heeft een landingsplek**.
- Boom (`ouder_id`, self-FK RESTRICT), koppelregel `procesvervulling` (component/proces/
  applicatiefunctie + toelichting), applicatiefunctie-catalogus (uitbreidbaar zonder redeploy),
  RBAC (`_INHOUD`-patroon) en audit-dekking compleet.
- Diagram, boom-afleiding, focus/inzoom/history, gap-cue: **gebouwd en getest** (LI038).

**Leeg — de zes kritieke slots:**
1. `business_function` bestaat niet (niet in `TOEGESTANE_ELEMENTEN`, geen element-type). Het
   subtype-recept + partitietests maken toevoegen een **bekende, geborgde route**.
2. **Geen bronsleutel-veld** op enig element (precedenten elders: `keycloak_sub`, `optie_sleutel`).
3. **Geen model-/versie-identiteit**, nergens.
4. **Geen import-route** — alleen losse POST's, ouder-vóór-kind.
5. **Geen idempotentie** — tweede run dubbelt alles; hernoemd/verhangen onherkenbaar; "vervallen" kan nu
   alleen hard verwijderen (**CASCADE sleept eigen registratie mee** — direct raakvlak met besluit 6).
6. **Scheiding modelinhoud ↔ eigen registratie** bestaat als **patroon** elders (stabiele sleutel +
   soft-deactivate + herkomst-marker + seed-op-sleutel) maar **niet op elementen**.

**Discrepanties om te bewaken:** de relatie-facade valideert **geen** bron/doel-elementtype; de
GEMMA-topgroeperingen (Besturend/Primair/Ondersteunend) hebben nog **geen dragend begrip**.

---

## Invarianten

- **Engine onaangeroerd**; score blijft de enige lifecycle-driver. Registratie + read-only leeslaag.
- **Geen polymorfe FK / exclusieve arc** — structureel boven conventioneel.
- **Eén bron per feit.** Geen tweede pad naar dezelfde uitspraak (zie MVP: component hangt uitsluitend
  aan een functie).
- **Bronvermelding** respecteren (GEMMA ArchiMate-repository, EUPL).
- **Multi-tenant generiek** — nooit ontwerpen alsof één model of één gemeente de werkelijkheid is.

---

## Besloten (LI039) — de acht subknopen

Grond: het feitenrapport bedrijfsfunctie-as (V039). De besluiten in functionele taal:

1. **De koppeling applicatie ↔ functie is kaal.** Het paar *(component, bedrijfsfunctie)*, **één regel
   per paar**. **Géén applicatiefunctie/werkwoord** op de functie-as. Reden: op functieniveau is het
   werkwoord niet scherp te geven ("een zaaksysteem doet alles een beetje binnen een brede functie");
   een veld dat willekeurig wordt ingevuld maakt de kaart onbetrouwbaar in plaats van rijker. Het
   werkwoord blijft bij het **proces**, waar het wél onderscheidend is — dat wordt straks het
   bestaansrecht van het procesregister als verdieping. *Dit is een expliciete afwijking van de eerdere
   default bij deze subknoop (hergebruik van de `procesvervulling`-vorm mét applicatiefunctie).*
2. **Koppelen mag op elk niveau van de boom** — ook heel grof. Reden: het koppelen gebeurt in een
   **begeleide (consultancy) sessie**; dwing je naar het diepste niveau, dan gokt de gemeente in de
   workshop en zit die gok mét consultancy-gezag voorgoed in de kaart. Een grof feit is eerlijk en
   later verfijnbaar.
3. **"Grof gekoppeld — verfijning ontbreekt" is een AFGELEID SIGNAAL, geen status.** Een koppeling op
   een functie **die kinderen heeft**, terwijl er onder die functie geen enkele verfijning staat, geeft
   een rustige cue. Geen tweede waarheid om bij te houden, geen afvinkactie: de registratie lost het
   signaal op. Dit is het bestaande *"begin grof → detaillering ontbreekt"*-patroon (ADR-036), tweede
   toepassing. **Randgeval bewust niet opgelost:** soms ís grof de waarheid (een generiek systeem
   ondersteunt een functie breed) — dan blijft het signaal rustig staan. Pas als de praktijk uitwijst
   dat het gaat zeuren, is de klaarverklaring (ADR-027) het bestaande antwoord. Nu géén
   ontsnappingsluik bouwen.
4. **Topgroeperingen** (Besturend / Primair / Ondersteunend) = **gewone wortelknopen** in dezelfde
   boom. Geen apart begrip, geen tweede mechanisme.
5. **Aanbod is platform-gecureerd; het inlezen doet de tenant-beheerder** (in de praktijk de
   consultant, werkend in de omgeving van de gemeente). Functioneel: de ingelezen functies **zijn** het
   landschap van de gemeente. Structureel: een platform-account heeft principieel geen tenant-context
   (ADR-012) en kán niet in tenant-tabellen schrijven — dit is een harde grens, geen voorkeur.
6. **Vervallen functie: zichtbaar met markering, NIET meer koppelbaar.** Bestaande koppelingen blijven
   staan en zichtbaar (signaal: *"bestaat niet meer in het model — N applicaties hangen er nog aan"* =
   de werklijst om te verhangen). Nieuwe koppelingen kunnen er niet meer bij: verder bouwen op een
   verdwenen fundament mag niet stil gebeuren. Nooit hard verwijderen (CASCADE sleept eigen registratie
   mee — bevestigd op de FK's). Dit is soft-deactivate, voor het eerst op een **element** in plaats van
   een catalogus.
7. **Eigen functies toevoegen mag** (dragen geen bronsleutel → een herinlees raakt ze nooit aan).
   **"Afwijken bij de bron"** (eigen naam/definitie naast de referentie) gaat **niet** functie-specifiek
   in de MVP: het is een instantie van het bredere **registratie-feiten-spoor** (toelichting/
   verwijzingen/verantwoordelijke op elk object) — daar één keer bouwen, niet twee keer
   (n≥2-discipline).
8. **Procesregister volledig uit beeld in de MVP** — menu, ingangen **én de proceslaan op de kaart**.
   Reden: één verhaal, één plek; een proceslaan náást een functielaan roept meteen "waar hoort dit nou
   bij?" op, en de proces-ingangen op de kaart zouden doodlopen. **Model en code blijven intact**
   (`procesvervulling`, procesboom, diagram) — het is de verdieping die terugkomt zodra de functie het
   anker is.
   > **Aangescherpt LI042 (zie §"Gate 4 — de bedrijfsfunctie-laan op de kaart"):** de proceslaan gáát
   > van de kaart (conform dit besluit), maar **niet met een leeg gat** — een **bedrijfsfunctie-laan
   > vervangt hem in dezelfde gate**. Oude lezing: "de proceslaan verdwijnt (de kaart heeft even geen
   > waarvoor-laan)"; nieuwe lezing: "de proceslaan wordt vervangen door de functie-laan, zonder
   > tussenperiode". De frontend-routes gaan nu wél weg (niet slechts verbergen); model/leeslaag/
   > bouwstenen blijven (gate-4 besluit G6).

**Vangrail-knopen — volgen het bestaande recept (vastgelegd, geen keuze):**
- Bedrijfsfunctie = **eigen element-subtype** via het bestaande recept (shared-PK, FORCE RLS,
  partitietest), zoals `proces`.
- **Bronsleutel + herkomst op het subtype** (`bron_model_id` + `bron_sleutel`) — een eigenschap van de
  rij, niet van een relatie.
- De **inlees-motor is modelonafhankelijk** (ArchiMate Open Exchange / AMEFF) — nooit een
  "GEMMA-importer"; welke modellen worden aangeboden is een productkeuze.

---

## Bouw-fasering (indicatief, ná besluitvorming)

1. **Read-only bouw-validatie** — AMEFF-parse-route, subtype-recept-kosten, soft-deactivate op elementen.
2. **Bedrijfsfunctie-as** (element-subtype + bronsleutel/herkomst + soft-vervallen) — gate, mét migratie.
3. **Referentiemodel + gevalideerde import** — incl. **voorbeeldscherm vóór landing** en idempotente
   match op bronsleutel.
4. **Koppelregel component ↔ functie** + gap-signalering.
5. **Kaart op functies** — hergebruik van boom/diagram/inzoom/gap-cue uit LI038 (n≥2: abstraheren).
6. **Procesregister verbergen** (menu/route/ingangen uit; model blijft intact).

Elke slice met engine-onaangeroerd-borging, browserverificatie vóór commit, en de gangbare
gate-discipline.

> **Fasering-actualisatie (LI042):** stap 5 ("kaart op functies") en stap 6 ("procesregister
> verbergen") zijn in LI042 uitgewerkt tot de tien gate-4-besluiten hieronder. Stap 6 wordt
> **verwijderen** (frontend-routes weg, niet slechts verbergen; backend slapend tot de laatste
> slice) — zie §"Gate 4".

---

## Gate 4 — de bedrijfsfunctie-laan op de kaart (besloten LI042; bouw volgt)

**Status:** Besloten (LI042) — **bouw nog niet gestart.** Status blijft *besloten / bouw volgt*;
geen enkel besluit is "geïmplementeerd".
**Datum:** 2026-07-15
**Grond:** `docs/Feitenrapport-gate4-kaart-op-functies-V043.md` (feitencheckpoint, read-only) +
`docs/Ontwerpcheckpoint-bedrijfsfunctie-laan-V043.md` (ontwerpcheckpoint, read-only) + besluiten Bert LI042.
**Gerelateerd:** ADR-044 (meervoudige plaatsing — de teleenheid is de plek → besluit G7) ·
ADR-049 (component-functie-koppeling: adres- en leesregel → de invariant + besluit G9) ·
ADR-051 (gap-signaal per plek → besluit G8) · ADR-042 (procesregister — het herbruikte recept, gaat uit beeld).
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver. Dit is registratie + read-only leeslaag;
de engine wordt niet geraakt.

Gate 4 sluit blok A af: de **logische kaart komt op bedrijfsfuncties te rusten** en het
**procesregister verlaat de MVP-UI**. De besluiten staan hier als coherent geheel; de mechanismen
waarop ze leunen leven in ADR-044/049/051 (kruisverwijzingen per besluit).

### Ontwerpbesluiten

- **G1 — De proceslaan verdwijnt van de kaart; een bedrijfsfunctie-laan vervangt hem, in dezelfde
  gate.** Geen tussenperiode waarin de kaart de waarvoor-vraag niet beantwoordt. *Scherpt ADR-043
  besluit 8 (LI039) aan* — zie de aanscherping-noot bij besluit 8 hierboven. De kaart-projectie
  blijft een **read-only verrijking onder `ARCHITECTUUR.LEZEN`** (dezelfde entiteit, geen
  scope-verbreding; feitencheckpoint §2.1) — de functie-laan erft die discipline 1-op-1.
- **G2 — Koppelen kan vanuit het component.** Een registrerende sectie op componentdetail, op de kop
  *"waarvoor gebruiken we het"* — de plek die vandaag door de proces-sectie (`ComponentProcessenSectie`)
  bezet is; die maakt plaats. De consultant denkt vanuit het systeem én vanuit de functieboom; dezelfde
  koppeling, meerdere ingangen (zie de invariant).
- **G3 — Het formulier-subveld "Proces" wordt "Bedrijfsfunctie".** Koppelen kan al bij het aanmaken van
  een systeem.
- **G4 — Het veld is optioneel.** Een systeem zonder bedrijfsfunctie is geen fout, maar een **zichtbaar,
  filterbaar registratiegat** (de werkvoorraad van de consultant). Dit is vandaag nergens zichtbaar
  (geen registratiegaten-signaal, geen lijstfilter, geen badge — ontwerpcheckpoint §3.4); het volgt de
  bestaande `*_ontbreekt`/`component_zonder_*`-patronen. *Consistent met* de "leeg ≠ fout, LIKARA verzint
  niets"-lijn (LI040) en met de openstaande vraag over "één taal voor afwezigheid".
- **G5 — Bestaande proces-registraties verdwijnen via reseed** (ontwikkelmodus, alléén testdata — géén
  datamigratievraagstuk). De dev-seed vertelt voortaan het **functie-verhaal**, inclusief het
  gate-3-verhaal (grof / fijn / geen-systeem / noodoplossing / het gat; OPVOLGPUNT L4). De seed vult de
  functievervulling-as vandaag nog **niet** (ontwerpcheckpoint §5).
- **G6 — De procesregister-UI en frontend-routes gaan geheel weg** (geen gebruikers, geen bookmarks,
  geen redirect nodig). **Model, leeslaag en bouwstenen blijven staan** — de functie-as erft ze
  (`Proces`/`Procesvervulling`-model, RLS, roll-up-service, `procesBoom.js`, `ProcesDiagram`, RBAC- en
  audit-entiteiten). *"Verbergen is niet slopen" geldt voor het model, niet voor de route.*

### Verdiepingsbesluiten (uit het ontwerpcheckpoint)

- **G7 — De kaart-laan is een laan van PLEKKEN, niet van functies.** Een functie die op meerdere plekken
  staat (GEMMA: 7 functies met 2-4 ouders), verschijnt **per plek**. *Reden:* de teleenheid van de kaart
  moet gelijk zijn aan die van de werkvoorraad en de gap-cue — de **plaatsing** (ADR-044 besluit 4,
  ADR-051) — zodat het overal één verhaal is. **Verworpen: laan van functies** (één knoop, alle lijnen
  omhoog — de bestaande `ProcesDiagram`-aanpak, `ProcesDiagram.vue:112-118`): dan collapst een functie
  die op de ene plek een systeem draagt en op de andere een gat tot één kleur — de per-plek-werkvoorraad
  wordt oneerlijk. *Gevolg (bouwwerk, geen ontwerpkeuze meer):* er is een **nieuwe per-plek-layout** nodig;
  `procesBoomLayout` is single-parent, `meervoudBoomStructuur` (DAG) bestaat al maar er is nog geen
  meervoud-layout die één functie onder meerdere ouders positioneert (ontwerpcheckpoint §2.1).
- **G8 — De kaart-plek toont de OMHOOG-gap (`plek_standen`, ADR-051), niet de omlaag/subboom-cue.** Een
  plek is een gat als er **op die plek zelf** niets hangt (met de derde stand "ondersteund via een
  bovenliggende functie"); dezelfde cue als de werkvoorraad — één afleiding, twee vensters (ADR-051
  besluit 5). De **omlaag/roll-up-blik** (gat érgens in de subboom eronder — de proces-cue `_procesZonderSysteem`)
  is een mógelijke latere overzichtslaag, **niet** de cue op de plek. *Legt vast in ADR-051-termen; daar
  een addendum, van hieruit verwezen.*
- **G9 — Vanuit het component koppelt de gebruiker één of meer functies, en per koppeling grof of fijn.**
  Meerdere koppelingen per systeem is normaal. **Grof** = de hele functie (alle plekken tegelijk, "geldt
  overal"); **fijn** = één plek. **Grof is het vertrekpunt/default** — óók vanuit het component, waar
  boomcontext ontbreekt. **Fijn verdringt grof bij het lezen** (ADR-049 besluit 1; verdringing is een
  verschijning, geen verwijdering). *Legt de component-ingang vast bovenop ADR-049; daar een addendum.*
- **G10 — De proces-backend-endpoints blijven slapend** tot de functie-laan aantoonbaar geen proces-route
  meer nodig heeft; opruimen gebeurt als **laatste slice**. De **frontend** gaat nu weg (G6). Reden: de
  kaart-interacties `zoomInOpProces` en "Via proces" hangen vandaag aan `/processen` + `/procesvervullingen`
  (feitencheckpoint §2.3); pas als hun functie-equivalent staat, is de proces-route dood.

### Invariant — één feit, meerdere ingangen (niet-onderhandelbaar)

De componentdetail-sectie (G2), het formulier-veld (G3) én de kaart-laan-edges (G1/G7) lezen **altijd de
gedeelde leeslaag** — `dekking_overzicht` / `plek_standen`, **mét verdringing** — en **nooit** een verse
rauwe `where component_id`-query. Eén gedeelde bouwsteen, geen `if` per scherm, geen consument die zelf
rekent. Dit **generaliseert ADR-049 besluit 5** naar de nieuwe consumenten en sluit de tweede waarheid uit
die het ontwerpcheckpoint blootlegde: een naïeve `lijst_voor_component` (zoals de proces-tegenhanger, die
géén verdringing kent) zou *"geldt overal"* tonen terwijl op een plek een ánder systeem het grove antwoord
verdringt. De richting *component → plekken* is een **her-indexering** van `dekking_overzicht` (dat draagt
per plek al `componenten[]` + `verdrongen[]`), geen tweede afleiding. *(Vastgelegd in ADR-049-termen; daar
het addendum, van hieruit verwezen.)*

### Bouwvolgorde (slice-knip, indicatief)

1. **Component-ingangen + werkvoorraad-gat** (G2/G3/G4) — omkeerbaar, raakt de kaart niet; browser per slice.
2. **Kaart-swap** — proceslaan eruit, bedrijfsfunctie-laan (van plekken, G7/G8) erin — **atomair** (G1: geen
   tussenperiode; de proceslaan zit op ~8 frontend-plekken vastgedraaid — verwijderen en terugplaatsen samen).
3. **Proces-frontend-sloop + reseed + backend-opruim** (G5/G6/G10) — **laatste** (de onomkeerbare sloop komt
   ná het bewijs dat de vervanger werkt).

Elke slice met engine-onaangeroerd-borging, browserverificatie vóór commit, en de gangbare gate-discipline.
