# ADR-049 — De component-functie-koppeling: het adres van de plek, en verdringing als leesregel

| | |
|---|---|
| **Status** | Besloten (LI041) — bouw nog niet gestart (gate 2a, stap 1 = dit ADR) |
| **Datum** | 2026-07-14 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-043 (bedrijfsfunctie als ruggengraat — herijkt) · ADR-044 (plaatsing als eerste-klas feit — herijkt op twee punten) · ADR-045 ("ondersteunt werk" — de picker-vangrail) · ADR-042 (procesregister — het herbruikte recept) · ADR-036 (grof→fijn + "detaillering ontbreekt"-signaal) |
| **Grond** | `docs/Feitenrapport-koppelen-bedrijfsfunctie-V041.md` (checkpoint gate 2, `6cc7db0`) · besluiten Bert LI041 |
| **Invariant (ongewijzigd)** | Score blijft de enige lifecycle-driver. Dit ADR is registratie + leeslaag; de engine wordt niet geraakt. |

---

## Context — de belofte stopt na stap 1

De consultant kan vandaag de bedrijfsfunctieboom lezen, maar er **geen enkel systeem aan
hangen** (feitenrapport §2.1: geen knop, link of API die een component aan een functie of
plek koppelt). De MVP-belofte — *"dít werk doen wij met dát systeem"* — stopt daarmee halverwege.

Twee dingen moet hij kunnen zeggen, en het tweede verfijnt het eerste:

- **Grof:** *"ons handhavingssysteem ondersteunt Toezicht."* Eén handeling, leesbaar op elke
  plek waar Toezicht staat (7 functies staan op meerdere plekken — feitenrapport §3.3).
- **Fijn:** *"maar in Milieu doen we het met de inspectie-app."* Een verbijzondering op díé plek.

Het feitenrapport legde twee dingen bloot die dit ADR beslecht:

1. **De vorm van het anker.** ADR-044 besluit 1 verankerde het fijne feit aan `relatie.id`
   (de plaatsing als eigen identiteit). Maar `relatie` heeft geen `UNIQUE(tenant_id, id)`
   (§3.2) — de veilige composiet-FK kan daar niet zonder schemastap, en `relatie` CASCADE-t
   bovendien mee met zijn eind-element. Het anker moest opnieuw gewogen.
2. **De verdringing.** ADR-044 besluit 2 noemt organisatiegebruik "de spiegel" en spreekt van
   "de leesregel (fijn verdringt grof)". Maar in de code doet organisatiegebruik dat **niet**:
   grof en fijn bestaan er náást elkaar; "fijn verdringt grof" bestaat **nergens** in de
   codebase (§6). Deze gate is de eerste plek waar die regel echt gebouwd wordt — en dat maakt
   het een expliciet te nemen besluit: leeslaag of schrijfregel.

---

## Besluit 1 — Verfijnen voegt toe; verdringen gebeurt bij het lezen

De grove koppeling blijft bestaan als **registratie**. Op een plek die een eigen (fijn)
antwoord draagt, **wint het fijne antwoord bij het tonen** — het grove verdwijnt daar uit
beeld, **niet uit de database**.

*Reden (doorslaggevend):* LIKARA schrijft **nooit** antwoorden weg voor plekken waar niemand
naar heeft gevraagd. Het grove antwoord is een geldige registratie met een eigen betekenis —
*"nog niet nagevraagd wáár precies"*, de ruwe pennenstreek — niet *"overal waar"*. Zou het
verfijnen het grove wegschrijven, dan verliest de consultant informatie die hij bewust heeft
vastgelegd, en verandert *"ik heb dit vastgesteld"* stil in *"dit is overschreven"*.

Dit precatiseert ADR-044 besluit 2 ("verfijnen VERVANGT de grove koppeling op die plek"):
het vervangen is een **verschijning**, geen **verwijdering**. Op de plek zelf ziet de
consultant nooit twee antwoorden naast elkaar (ADR-044's kernregel blijft overeind); maar de
grove registratie overleeft, zodat het verwijderen van de fijne koppeling het grove antwoord
op die plek **weer leesbaar** maakt.

---

## Besluit 2 — De koppeling verwijst naar het adres van de plek, niet naar `relatie.id`

Een plek in de boom is te benoemen als een **adres**: *welke functie, onder welke functie.*
De fijne koppeling verwijst naar dat adres (de functie + haar ouder-functie), **niet** naar de
identiteit van de plaatsings-relatie (`relatie.id`).

*Reden:*
- Het adres is **stabiel en reconstrueerbaar**: het is opgebouwd uit twee functie-identiteiten
  (bronsleutels), die volgens ADR-043 de dragende identiteit zijn. Een herinlees die de
  plaatsing opnieuw legt, herstelt hetzelfde adres — waar een verwijzing naar `relatie.id`
  breekt zodra de relatie-rij vervangen wordt.
- Het **vermijdt de schemaknoop** uit feitenrapport §3.2: er wordt niet naar `relatie.id`
  verwezen, dus `relatie` hoeft geen `UNIQUE(tenant_id, id)` te krijgen en er ontstaat geen
  eerste-tabel-die-naar-relatie-wijst met het bijbehorende CASCADE-risico (relatie CASCADE-t
  mee met haar eind-element — dat zou het fijne veldwerk stil meenemen).

Daarmee **herijkt dit ADR het anker van ADR-044 besluit 1**: de plek wordt geadresseerd via
haar twee functies, niet via de plaatsings-relatie. De schemaknoop §3.2 vervalt en wordt
**niet** alsnog gebouwd.

---

## Besluit 3 — Eén soort registratie, plek optioneel

Er is **één** soort component-functie-registratie. Het adres is optioneel:

- **Leeg adres (geen ouder-functie)** = **grof**: *"nog niet nagevraagd wáár precies."*
- **Gevuld adres (ouder-functie erbij)** = **fijn**: *dít is de plek.*

Eén bron, één filterwaarheid. Twee aparte tabellen (grof/fijn) zouden de registratie én de
leesregel dupliceren — precies de tweede-waarheid die LI038/LI040 als foutbron aanwijzen.

De as blijft **kaal** (ADR-044 besluit 2): géén applicatiefunctie, géén werkwoord op de
functie-as. Het werkwoord blijft bij het proces (ADR-042), waar het onderscheidend is.
Meerdere componenten op één plek is normaal — twee systemen kunnen samen één functie op één
plek dragen.

---

## Besluit 4 — Vastleggen gebeurt in de boom; het componentdetail leest later mee

De handeling — koppelen en verfijnen — leeft in de **functieboom**, waar de consultant de
plek aanwijst. Het componentdetail dat dezelfde registratie **meeleest** (vanaf het systeem
bekeken) is gate 2b en wordt in deze slice niet gebouwd, maar mag niet geblokkeerd worden:
de registratie en de leesregel (besluit 5) zijn bewust vanaf één gedeelde bron leesbaar.

---

## Besluit 5 — De leesregel is één gedeelde bouwsteen, geen `if` per scherm

*"Op deze plek wint het fijne antwoord; waar geen fijn antwoord staat, is het grove antwoord
leesbaar."*

Deze regel bestaat **één keer**, als één gedeelde afleiding ("welke componenten dragen déze
plek"), en wordt door **elke** consument geërfd — boom, straks componentdetail, kaart,
gap-signaal, export. Consumenten **lezen** die afleiding; ze rekenen niet zelf.

*Reden:* een regel die vijf keer als `if` in een scherm staat, loopt stil uit de pas — de
kernles van LI038 (twee ankers, één model) en de "3 van 19"-bug van LI040 (teller en lijst
deelden niet dezelfde filterwaarheid). De verdringing wordt **nooit opgeslagen**: ze is een
leeslaag, geen tweede waarheid in de database (generalisatie van de readiness-regel).

---

## Wat dit ADR herijkt in ADR-043/044

| Bron | Oorspronkelijk | Herijking (dit ADR) | Reden |
|---|---|---|---|
| ADR-044 besluit 1 | Het fijne feit verankert aan **`relatie.id`** (de plaatsing als eigen identiteit; "twee ankers — elementen én koppelingen via `relatie.id`"). | Het fijne feit verwijst naar het **adres van de plek** (functie + ouder-functie), niet naar `relatie.id`. | `relatie` mist `UNIQUE(tenant_id, id)` (§3.2) en CASCADE-t mee met haar eind-element; het adres draagt dezelfde plek-identiteit stabiel en zonder dat schemarisico. |
| ADR-044 besluit 2 | "Verfijnen **vervangt** de grove koppeling op die plek"; de leesregel "fijn verdringt grof" als "kijk op twee registraties". | Vervangen = **verschijnen**, niet verwijderen. De verdringing is expliciet een **leeslaag** (gedeelde bouwsteen, besluit 5); het grove blijft altijd als registratie bestaan (besluit 1). | Feitenrapport §6: "fijn verdringt grof" bestaat nergens; de genoemde spiegel (organisatiegebruik) laat grof + fijn juist coëxisteren. Dit ADR maakt het de eerste plek én legt vast dat het niet-opgeslagen is. |
| ADR-043 besluit 1 (via ADR-044) | Kale koppeling *(component, bedrijfsfunctie)*, later *(component, plaatsing)*. | *(component, functie)* grof · *(component, functie, ouder-functie)* fijn — één registratie, plek optioneel (besluit 3). Kaal blijft kaal. | Eén functie op meerdere plekken → het adres draagt de plek-waarheid; één registratievorm houdt één filterwaarheid. |

**Onaangeroerd blijven:** bronsleutel = identiteit · vervallen ≠ verwijderen (zichtbaar, niet
koppelbaar) · modelinhoud lees je, je wijzigt hem niet · aanbod gesloten, motor generiek ·
procesregister verborgen in de MVP · **engine-invariant** (score blijft de enige
lifecycle-driver; dit is registratie + leeslaag).

---

## Gevolgen (benoemd, niet gebouwd — stap 2 volgt ná Berts akkoord)

1. **Registratie langs het procesvervulling-recept** (feitenrapport §4: 1-op-1 herbruikbaar —
   eigen tenant-tabel, composiet-FK's naar `element` met CASCADE, FORCE RLS, eigen
   RBAC-`_INHOUD`-entiteit, `AUDIT_TENANT_ENTITEITEN`, twee-zijdige leespaden), mét één
   verschil: **geen `applicatiefunctie`** — de as is kaal.
2. **Uniciteit structureel, in twee vormen** (Postgres behandelt NULL als distinct — een
   gewone `UNIQUE(..., adres)` laat onbeperkt grove dubbelen toe): hoogstens één **grove** per
   (component, functie) en één **fijne** per (component, functie, ouder-functie). Vorm:
   partiële unieke indexen (precedent `uq_relatie`, migratie 0039). App-side check is géén
   vervanging.
3. **Het adres moet bestaan bij registreren** (de ouder→functie-plaatsing bestaat, beide zijn
   bedrijfsfuncties) — type-borging in de **specifieke** service (de generieke relatie-facade
   valideert elementtypen bewust niet).
4. **Wie/wanneer + optionele toelichting** server-stamped (`actor_resolutie`-patroon), nooit uit
   de payload.
5. **De picker spiegelt de backend-regel** (ADR-045): alleen componenttypen met
   `ondersteunt_werk = true`; het server-side filter bestaat al (`routes/component.py:79`).
6. **Wortelfuncties** (functie zonder ouder) hebben precies één plek; grof en fijn vallen daar
   feitelijk samen — read-only vast te stellen en te beschrijven, geen kunstgreep.
7. **De vorm draagt het eindbeeld zonder herbouw:** gate 3 registreert *"hier gebruiken we
   geen systeem — vastgesteld"* als bevinding op een plek (ADR-044 besluit 3); gate 2b het
   losgeraakt-gedrag. Ontwikkelmodus: alembic-schemastap + reseed — geen datamigratievraagstuk.

---

## Addendum LI042 — de component-ingang en de kaart-edges lezen de leesregel (gate 4, besloten; bouw volgt)

Gate 4 (ADR-043 §"Gate 4") maakt besluit 5 van dit ADR concreet met **drie nieuwe consumenten** van de
gedeelde afleiding: de **componentdetail-sectie** (koppelen vanuit het systeem, ADR-043 besluit G2), het
**formulier-veld "Bedrijfsfunctie"** (G3) en de **kaart-laan-edges** (G1/G7). Alle drie lezen **altijd**
`dekking_overzicht` / `plek_standen` — **mét verdringing** — en **nooit** een verse rauwe
`where component_id`-query.

**De tweede-waarheid-val, concreet.** De proces-tegenhanger `procesvervulling_service.lijst_voor_component`
is een directe `where component_id`-query — dat kan bij proces, want proces kent **geen** verdringing (grof
en fijn coëxisteren daar niet). Kopieer dat patroon naar de functie-as en je krijgt de ruwe rijen **zonder**
de leesregel: het systeem toont *"ondersteunt Toezicht — geldt overal"* terwijl op plek *Milieu* een ánder
systeem dat grove antwoord verdringt (besluit 1). Twee schermen, twee waarheden, uit de pas — de "3-van-19"-val
(LI040). Dezelfde val geldt voor de **kaart-vervult-edges**: een edge op een verdrongen plek zou niet mogen
verschijnen.

**Vorm (geen tweede afleiding).** De richting *component → plekken* is een **her-indexering** van
`dekking_overzicht`: die draagt per plek al `componenten[]` én `verdrongen[]` met `component_id` in elke entry
— filter de plek-entries waar het component voorkomt. Dit **generaliseert besluit 5** ("de leesregel is één
gedeelde bouwsteen, geen `if` per scherm") naar de nieuwe consumenten en is als **invariant** vastgelegd in
ADR-043 §"Gate 4" (*één feit, meerdere ingangen*). Grof/fijn vanuit het component: **grof is de default**
(ADR-043 besluit G9), fijn verdringt grof bij het lezen — ongewijzigd t.o.v. besluit 1. Status:
**besloten (LI042), bouw nog niet gestart.**

---

## Alternatieven overwogen

1. **Verankeren aan `relatie.id`** (ADR-044's oorspronkelijke lijn) — **verworpen**: `relatie`
   mist `UNIQUE(tenant_id, id)`, dus de veilige composiet-FK vergt eerst een schemastap, en
   `relatie` CASCADE-t mee met haar eind-element — dat zou fijn veldwerk stil meenemen. Het
   adres (functie + ouder-functie) draagt dezelfde plek-identiteit zonder die kwetsbaarheid.
2. **Grof stil vervangen bij verfijnen** (het grove wegschrijven) — **verworpen**: LIKARA
   schrijft nooit antwoorden weg voor plekken waar niemand naar vroeg; het grove is een geldige
   registratie ("nog niet nagevraagd wáár"), niet ruis.
3. **Grof én fijn samen tonen op één plek** — **verworpen** (ADR-044 besluit 2 kernregel): twee
   antwoorden op één plek is verwarrend en onwaar.
4. **Twee aparte tabellen (grof / fijn)** — **verworpen**: één registratie met optioneel adres
   houdt één bron en één filterwaarheid; twee tabellen dupliceren de leesregel (LI038-les).
5. **De verdringing opslaan** (een "verdrongen"-vlag op het grove feit) — **verworpen**: tweede
   waarheid in de database; de verdringing is puur een leeslaag (besluit 5).
6. **Applicatiefunctie/werkwoord op de functie-as** (zoals procesvervulling) — **verworpen**
   (ADR-044 besluit 2): de as is kaal; het werkwoord hoort bij het proces, waar het
   onderscheidend is.
7. **De leesregel per scherm herhalen** (`if` in boom, kaart, detail) — **verworpen**: loopt
   stil uit de pas (LI038 / de "3 van 19"-bug LI040); één gedeelde bouwsteen (besluit 5).
