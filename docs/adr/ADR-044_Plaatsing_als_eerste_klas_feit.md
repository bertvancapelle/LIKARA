# ADR-044 — Plaatsing als eerste-klas feit (herijking van ADR-043)

| | |
|---|---|
| **Status** | Besloten (LI039) |
| **Datum** | 2026-07-12 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-043 (bedrijfsfunctie als ruggengraat — herijkt door dit ADR), ADR-023 (relatiemodel), ADR-036 (grof→fijn-verfijning), ADR-042 (procesregister) |
| **Grond** | `docs/Verkenning-GEMMA-AMEFF-V040.md` · `docs/Feitenrapport-inlezen-referentiemodel-V040.md` · gate 1a (`605299a`) |

---

## Context — een aanname die geen besluit was

De GEMMA-verkenning (LI039) legde bloot dat **7 van de 297 bedrijfsfuncties meerdere ouders
hebben** — "Toezicht" en "Handhaving" hangen elk onder víér domein-varianten tegelijk. Ons
gate-1a-model kent één ouder per functie (`ouder_id` als kolom op het subtype). Die
één-ouder-vorm was een **impliciete aanname**, geen genomen besluit: nergens is gewogen of
een functie op meer plekken kan staan.

De eerste reflex — de functie stil onder de eerste ouder plaatsen — is **verworpen**, en
terecht: dat wist het interessantste feit uit dat er ligt. *Toezicht wordt in vier domeinen
uitgeoefend* is geen ruis maar een uitspraak over de werkelijkheid, met directe gevolgen:
een systeem dat Toezicht ondersteunt raakt vier domeinen, dus een vervanging vergt vier
gesprekken. Dát is precies het impact-inzicht waarvoor de logische kaart bestaat.

**GEMMA bevestigt dit structureel.** De boom leeft in de bron in **302 aggregation-relaties**
tussen functies — niet in een ouder-veld (composition tussen functies: 0; `<organizations>`
is louter presentatie). De bron modelleert de plaatsing dus zelf als eerste-klas feit; wij
hadden hem platgeslagen tot een kolom. Vandaar de wrijving — en dit besluit gaat vóór de
import-bouw uit, want bouwen op ongeschreven grond doen we niet.

---

## Besluit 1 — De plaatsing is een eigen registratie, geen veld

De functieboom wordt gedragen door **plaatsingen** ("functie hoort onder functie"), niet
door een ouder-kolom.

- Een functie kan **meerdere plaatsingen** hebben (7 gevallen in GEMMA vandaag).
- Een herinlees mapt daarmee **één-op-één** op wat de bron levert (aggregation-relatie in
  het bestand = plaatsing bij ons).
- **Geen thuisplek, geen rangorde.** De vier plekken van "Toezicht" zijn **gelijkwaardig** —
  GEMMA kent geen hoofd-ouder, en er één benoemen zou een hiërarchie verzinnen die niet
  bestaat. De consultant leert: *toezicht speelt overal — dat ís het verhaal.*
- De functie **bestaat één keer** (één identiteit, één bronsleutel, één definitie) en
  **verschijnt** op elk van haar plaatsingen. Verschijnen ≠ dupliceren.

**Vorm: facade-over-Relatie met het bestaande relatietype `aggregation`** — géén eigen
tabel. Motivering langs de vaste beslisregel (ADR-023 / harde regels 2–3):

1. *Is het een ArchiMate-relatie?* **Ja, letterlijk** — het ís de aggregation-relatie die
   GEMMA levert; de import leest haar 1-op-1 in. Een eigen tabel zou het relatiemodel
   dupliceren voor iets dat er al een naam in heeft.
2. *Botst de uniciteit?* **Nee — ze past exact.** `UNIQUE(tenant, bron, doel, relatietype)`
   op de `relatie`-tabel dwingt precies af wat we willen: één plaatsing per
   (ouder, functie)-paar; meerdere ouders = meerdere rijen. (Vergelijk roltoewijzing en
   procesvervulling, die juist een eigen tabel kregen ómdat hun uniciteit met deze botste —
   hier is het omgekeerde het geval.)
3. *Is het een registratie-feit in plaats van een architectuurverband?* Nee — de plaatsing
   is structuur. (De **verfijning** op de plaatsing, besluit 2, is wél een registratie-feit
   — en die krijgt zijn eigen vorm.)
4. Het plateau-lidmaatschap gebruikt `aggregation` al via een dunne facade
   (`plateau_service`) — dit wordt de tweede facade op hetzelfde relatietype, met eigen
   endpoint-borging (bron én doel = bedrijfsfunctie; de generieke relatie-facade valideert
   elementtypen bewust niet, de dunne facade wél — het gevestigde patroon).

Geen polymorfe FK, geen exclusieve arc. **Cyclus-preventie blijft servicelaag** (visited-set,
zoals overal). De plaatsing heeft via `relatie.id` een eigen, stabiele identiteit — het anker
waar besluiten 2–4 aan hangen; dat spoort met het al-besloten registratie-feiten-spoor
(LI038/ADR-043: "één model, twee ankers — elementen én koppelingen via `relatie.id`").

---

## Besluit 2 — Koppelen: grof en fijn, één antwoord per plek

De gemeente moet twee dingen kunnen zeggen, en het tweede vervangt het eerste:

- **Grof:** *"ons handhavingssysteem ondersteunt Toezicht."* Eén handeling, vastgelegd op de
  **functie**; geldt (leesbaar) op elke plek waar Toezicht staat.
- **Fijn:** *"maar in Milieu doen we het met de inspectie-app."* Een verbijzondering op
  **die ene plaatsing**.

**KERNREGEL (niet-onderhandelbaar): verfijnen VERVANGT de grove koppeling op die plek.**
Zodra een plaatsing een eigen antwoord draagt, verdwijnt de grove koppeling dáár uit beeld.
Nooit twee antwoorden naast elkaar op één plaatsing.

*Reden (doorslaggevend):* het is verwarrend — en onwaar — als er een component gekoppeld
staat op een plek waar hij niet gebruikt wordt. **"Grof" betekent onvoltooid, niet
universeel:** het is de ruwe pennenstreek van iemand die de details nog niet weet, bedoeld
om vervangen te worden zodra de consultant doorvraagt. Dit sluit ook de dubbelzinnigheid
*"vervangt het, of komt het erbij?"* voorgoed uit: verfijnen is **altijd** in plaats van.

- **"Erbij" bestaat wél** — twee systemen die sámen één functie op één plek ondersteunen.
  Dat regel je op de plaatsing zelf: **meerdere componenten per plaatsing is normaal**, geen
  uitzondering.
- **Een applicatie kan meerdere functies ondersteunen** — dat kon al en verandert niet.
- **De koppeling blijft kaal** (ADR-043 besluit 1, aangepast anker): het paar wordt
  *(component, plaatsing)* voor het fijne feit, met de grove vorm *(component, functie)* als
  onvoltooide voorloper. **Nog steeds géén applicatiefunctie/werkwoord** op de functie-as —
  het werkwoord blijft bij het proces (daar is het onderscheidend).

Dit is een **verfijningsrelatie in de bestaande LIKARA-vorm** — de spiegel van
organisatiegebruik (ADR-036: grof feit "organisatie gebruikt applicatie" → fijne verfijning
per afdeling, en het "nog niet verfijnd"-signaal erbij). Zelfde discipline: het fijne feit
hangt onder het grove; **één bron per feit** blijft overeind — de leesregel (fijn verdringt
grof op die plek) is een kijk op twee registraties, geen tweede opgeslagen waarheid.

---

## Besluit 3 — "Geen ondersteunend systeem" is een vastgestelde uitkomst

Een verfijning kan ook luiden: **"hier gebruiken we niets."** Dat is geen ontbrekende
registratie maar **een bevinding** — en het interessantste feit van de workshop: werk dat de
gemeente doet zonder enige systeemondersteuning.

*Reden:* zonder deze uitkomst kan de consultant "niets" niet vastleggen, blijft de grove
koppeling op die plek staan, en **liegt de kaart precies over het gat dat ertoe doet**.

Onderscheid strikt, en voorgoed:
- *nooit naar gekeken* = een **openstaande vraag** (afwezigheid van registratie);
- *vastgesteld dat er niets draait* = een **bevinding** (aanwezige registratie met uitkomst
  "geen"; klaar — niet opnieuw navragen).

---

## Besluit 4 — Het gap-signaal hangt aan de plaatsing, niet aan de functie

De vraag *"is Toezicht ondersteund?"* is **niet beantwoordbaar** — het antwoord verschilt
per domein. Eén oordeel over de functie zou het ene gat achter het andere verstoppen.

Per **plaatsing** drie leesbare werksoorten voor de consultant:

| Signaal | Betekenis | Handeling |
|---|---|---|
| **"Nog geen ondersteunend systeem"** | openstaande vraag | *ga navragen* |
| **"Grof gekoppeld — verfijning ontbreekt"** | half antwoord | *ga doorvragen* (het ADR-043-besluit-3-signaal, nu scherp: aan de plek, niet aan de functie) |
| **"Geen ondersteunend systeem — vastgesteld"** | **bevinding** | geen taak meer; dit is het eindresultaat dat de gemeente wil zien |

De **teleenheid is de plaatsing**, niet de functie: er zijn geen "Toezicht-gaten", er zijn
**plekken** met of zonder ondersteuning. Toezicht telt dus niet één keer en niet vier keer —
elke plek telt voor zichzelf.

---

## Wat dit ADR herijkt in ADR-043

| ADR-043 | Herijking | Reden |
|---|---|---|
| Besluit 1: kale koppeling *(component, bedrijfsfunctie)* | Wordt *(component, **plaatsing**)*, met de grove vorm op de functie als onvoltooide voorloper. Kaal blijft kaal: géén applicatiefunctie/werkwoord. | Eén functie op meerdere plekken → één koppeling per functie kan de plek-waarheid niet dragen (besluit 2). |
| Impliciete één-ouder-aanname (gate 1a: `ouder_id`-kolom) | **Vervalt.** De boom = plaatsingen (besluit 1). | GEMMA-feit: 7 functies met 2–4 ouders; de bron modelleert plaatsing zelf als relatie. |
| Besluit 3: "grof gekoppeld — verfijning ontbreekt"-signaal | **Blijft**, maar hangt aan de **plaatsing**. | De functie is niet de teleenheid; de plek wel (besluit 4). |

**Onaangeroerd blijven:** bronsleutel = identiteit · vervallen ≠ verwijderen (zichtbaar,
niet koppelbaar) · modelinhoud lees je, je wijzigt hem niet · aanbod gesloten, motor
generiek · procesregister verborgen in de MVP · **engine-invariant** (score blijft de enige
lifecycle-driver; dit alles is registratie + leeslaag).

---

## Gevolgen (benoemd, niet gebouwd)

1. **Schemastap:** `bedrijfsfunctie.ouder_id` verdwijnt als kolom (met self-FK + CHECK); de
   boom verhuist naar `aggregation`-relaties tussen functie-elementen. Ontwikkelmodus:
   alembic + reseed — **geen databehoudvraagstuk** (er is uitsluitend testdata).
2. **Raakvlakken in het gebouwde** (te leren dat één functie op meerdere plekken staat):
   de boom-afleiding (`procesBoomStructuur` — kent een dubbele-ouder-guard die nu júíst
   meervoud moet tonen i.p.v. wegfilteren), `BedrijfsfunctieLijst` (boom-rendering: één
   functie, meerdere rijen), `ProcesDiagram` (focus-/inzoom-sets), de subboom-leestraversal
   in de service, de verplaats-/deelfunctie-acties (worden plaatsings-acties), en het
   gap-signaal (telt per plaatsing — besluit 4). Het processen-scherm blijft één-ouder en
   ongemoeid.
3. **De import (gate 1b) wordt eenvoudiger:** de aggregation-relaties uit het bestand worden
   **rechtstreeks** plaatsingen — de meervoudige-ouders-wrijving uit de verkenning verdwijnt
   als vertaalprobleem.
4. De verfijnings-registratie (besluiten 2–3) en het plaatsings-signaal (besluit 4) horen
   bij de kóppel-gate (gate 2); dit ADR legt het fundament vast zodat gate 1b (import) er
   niet omheen hoeft te bouwen.

---

## Alternatieven overwogen

1. **Stil de eerste ouder kiezen** (functie onder één ouder platslaan) — **verworpen door
   Bert**: wist het meervoud-feit uit dat juist het impact-inzicht draagt; verzint bovendien
   een rangorde die de bron niet kent.
2. **Hoofd-ouder + neven-plaatsingen** (één thuisplek, rest secundair) — verworpen: GEMMA
   kent geen hoofd-ouder; elke rangorde is verzonnen hiërarchie (besluit 1).
3. **Eigen plaatsings-tabel** i.p.v. de relatie-facade — verworpen langs de beslisregel: de
   uniciteit botst niet en het is een echt ArchiMate-verband; een eigen tabel dupliceert het
   relatiemodel (besluit 1, motivering).
4. **Grof en fijn naast elkaar tonen op één plaatsing** — verworpen: twee antwoorden op één
   plek is verwarrend en onwaar; grof = onvoltooid, niet universeel (besluit 2, kernregel).
5. **Gap-signaal op de functie** — verworpen: niet beantwoordbaar bij meerdere plekken;
   verstopt het ene gat achter het andere (besluit 4).

---

## Addendum LI040 — de plaatsing is een houdbaar anker (gemeten, niet aangenomen)

*Toegevoegd 2026-07-13 (Bert, LI040), naar aanleiding van registratie-feiten-knoop 2
(`docs/Feitenrapport-registratie-feiten-V040.md`) en de meting
`docs/Meting-plaatsingsstabiliteit-V040.md`.*

Tussen de GEMMA-releases van okt-2025 en juli-2026 is **geen enkele plaatsing
verhangen** (301/301 paren identiek, inclusief alle 13 meervoud-paren; de enige
wijziging is één nieuwe plaatsing voor de éne nieuwe functie). Registraties die aan een
plaatsing (`relatie.id`) hangen zijn over dit interval dus volkomen veilig geweest.

**Besluit: er komt géén overleef-machinerie** (hermatching van registraties over
plaatsings-identiteiten heen, herstelroutes): dat zou overdimensionering zijn voor een
gebeurtenis die nul keer voorkwam. Het is n=1 interval en VNG geeft geen formele
garantie — dus wél deze twee vangrails:

1. **Het inleesvoorbeeld moet een verhuizing benoemen.** Het scherm kent nu drie
   woorden (nieuw / bijgewerkt / vervallen); een verhangen plaatsing is geen van drieën
   en zou **onzichtbaar** verdwijnen — mét de registratie eraan. Vierde categorie:
   *"X verhuist van A naar B — hier hangen N componenten en M bevindingen aan."*
   **Ontwerpeis voor gate 2 / het import-pad.**
2. **De import verwijdert nooit stilzwijgend een plaatsing mét registratie** — dezelfde
   lijn als *vervallen ≠ verwijderen*: markeren en melden, nooit CASCADE-en over
   veldwerk. (Vandaag verwijdert `voer_uit` een verhangen plaatsing hard; dat is
   houdbaar zolang er niets aan hangt — zodra gate 2 registraties aan plaatsingen
   hangt, gaat deze vangrail gelden.)

De herhaalmeting is dankzij de releasegeschiedenis in
`modules/bwb_ontvlechting/backend/referentiemodellen/HERKOMST.md` voortaan goedkoop;
ze hoort bij elke curatie van een nieuwe release.
