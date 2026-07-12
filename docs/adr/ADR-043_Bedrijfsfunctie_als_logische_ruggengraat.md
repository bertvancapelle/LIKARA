# ADR-043 — Bedrijfsfunctie als logische ruggengraat (herijking ADR-042)

**Status:** Besloten (LI038)
**Datum:** 2026-07-12
**Herijkt:** ADR-042 (procesregister als "waarvoor"-as; bedrijfsfunctie-as bewust geparkeerd)
**Grond:** `docs/Feitenrapport-referentiemodel-bedrijfsfuncties-V038.md` (read-only, geverifieerd) +
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

## Open subknopen (te beslissen vóór de bouw — met voorlopige default)

1. **Element-subtype `bedrijfsfunctie`:** eigen subtype via het bestaande recept (shared-PK,
   FORCE RLS, partitietest). *Default: ja, eigen subtype; `business_function` toevoegen aan de
   ArchiMate-typering.*
2. **Bronsleutel + herkomst: waar?** Op het element-subtype (`bron_model_id` + `bron_sleutel`) of een
   aparte herkomst-tabel? *Default: op het subtype — het is een eigenschap van de rij, niet van een
   relatie.*
3. **Referentiemodel-entiteit:** naam, herkomst, versie, ingelezen-op. Platform-scoped of tenant-scoped?
   *Default: het aanbod is platform-scoped (LIKARA cureert), de ingelezen inhoud is tenant-scoped.*
4. **De koppelregel functie ↔ component:** hergebruikt hij de `procesvervulling`-vorm (met
   applicatiefunctie), of is het een lichtere "ondersteunt"-relatie? *Default: dezelfde vorm — één
   patroon, geen tweede mechanisme; applicatiefunctie optioneel.*
5. **Topgroeperingen** (Besturend / Primair / Ondersteunend): eigen wortelknopen in de boom, of een
   kenmerk? *Default: wortelknopen (de boom kan het dragen).*
6. **Soft-vervallen op elementen:** hergebruik het bestaande `actief`-/soft-deactivate-patroon.
   *Default: ja.*
7. **Import-route:** AMEFF-parser (Open Exchange) — bestaande dependency of nieuw? *Te bepalen bij de
   bouw-validatie; raakt de ooit geparkeerde ADR-023 Open-Exchange-lijn, maar dan aan de **import**-kant.*
8. **Verhouding tot het registratie-feiten-spoor** (toelichting/verwijzingen/verantwoordelijke op
   objecten, besloten LI038): de "eigen laag bij de functie" (besluit 5) is daar een instantie van.
   *Default: samen ontwerpen, zodat de eigen-laag één patroon is en niet functie-specifiek.*

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
