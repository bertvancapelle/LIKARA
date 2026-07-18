# Read-only meting — legt GEMMA zelf de brug tussen bedrijfsfunctie en bedrijfsproces?

**Sessie:** LI045 · **Build:** V045 · **Aard:** feitenopname, geen bouw · **Bestand gemeten:**
`modules/bwb_ontvlechting/backend/referentiemodellen/GEMMA_release_2026-07-01.xml`
(commit `de0984717e69`, SHA-256 `b844f184…d0d4cf1`, 13.411.843 bytes — exact het gecureerde aanbod
uit `HERKOMST.md`, niets bijgedownload).

> De vraag: de bewaartermijnen uit de selectielijst hangen aan **procestypen**, niet aan
> bedrijfsfuncties. Levert GEMMA zélf de brug functie↔proces mee (dan is het ooit een inleesbaar
> kado), of moet een gemeente die brug zelf leggen (dan is het een implementatieproject vóór er
> waarde ontstaat, en bouwen we het niet)?

---

## Kernuitkomst in één zin

**GEMMA levert de brug niet bruikbaar mee: van de 297 bedrijfsfuncties raakt slechts 4% een
bedrijfsproces, uitsluitend via de zwakste relatie (`Serving`) en alleen in de bedrijfsvoerings-hoek —
en géén enkel proces draagt een selectielijst-, zaaktype- of bewaartermijn-verwijzing.**

---

## Blok 1 — Wat zit er behalve functies in het bestand

Het bestand telt **2.752 elementen** in **26 ArchiMate-typen**. De grootste:

| Aantal | Type | | Aantal | Type |
|---:|---|---|---:|---|
| 522 | Constraint | | 81 | BusinessService |
| 507 | BusinessObject | | 57 | SystemSoftware |
| 426 | ApplicationService | | 48 | BusinessRole |
| **297** | **BusinessFunction** | | 48 | TechnologyService |
| 256 | ApplicationComponent | | 43 | ApplicationInterface |
| **176** | **BusinessProcess** | | 31 | BusinessActor |
| 142 | Grouping | | 26 | Capability |

…plus 19 kleinere typen (Principle, Goal, DataObject, Driver, Product, en enkele singletons als
BusinessEvent, Contract, Artifact).

**Procesachtige elementen:** **176 BusinessProcess**, plus 2 BusinessInteraction en 1 BusinessEvent.
De 142 Grouping zijn ordeningsmappen en de 26 Capability zijn strategisch — geen van beide is een
proces.

**Bevestiging zelfde bestand:** **297 BusinessFunction** — exact het aantal dat de import kent
(`HERKOMST.md`: 297 functies / 302 plaatsingen). We meten hetzelfde bestand als bij de import.

---

## Blok 2 — Bestaat de relatie functie ↔ proces

**Dit is de kern, en het antwoord is hard: nauwelijks.**

Het bestand telt 5.800 relaties. Tussen een bedrijfsfunctie en een bedrijfsproces bestaan er
**precies 12** — allemaal van het type **`Serving`** (7 functie→proces, 5 proces→functie). Geen enkele
`Composition`, `Aggregation` of `Realization` verbindt de twee werelden.

**Dekking (de eigenlijke vraag):**

| | Aantal | Aandeel |
|---|---:|---:|
| Bedrijfsfuncties met ≥1 procesrelatie | **12 van 297** | **4,0 %** |
| Bedrijfsfuncties zónder enige procesrelatie | 285 van 297 | 96,0 % |
| Bedrijfsprocessen met ≥1 functierelatie | 12 van 176 | 6,8 % |
| Bedrijfsprocessen zónder enige functierelatie | 164 van 176 | 93,2 % |
| Processen gekoppeld aan meer dan één functie | **0** | — |

Een dekking van 4% is geen grondslag; het is ruis. En de 12 uitzonderingen maken het beeld eerder
slechter dan beter: het zijn stuk voor stuk **bedrijfsvoerings**-paren waar functie en proces bijna
hetzelfde woord zijn —

> *"Uitvoeren juridische ondersteuning" ↔ "Juridische ondersteuning"* · *"Uitvoeren inkoop en
> contractmanagement" ↔ "Inkoop- en contractmanagement"* · *communicatie · projectmanagement ·
> financieel · archiefbeheer · veiligheid · personeel · automatisering · huisvesting · informatisering
> · administratief.*

Dit zijn 1-op-1 naamspiegels in de overhead-hoek, gelegd met `Serving` ("dient"), niet met een
decompositie. Juist de **primaire, burgergerichte** processen — waar archiefwettelijke bewaring speelt
— dragen **geen** functiekoppeling. Meervoudigheid (ADR-044) speelt hier niet: geen enkel gekoppeld
proces hangt aan meer dan één functie; elk van de 12 is strikt 1:1.

**Indirecte brug (via een tussen-element)?** Nee. Ik heb gezocht naar elementen die zowel een functie
als een proces aanraken — een Grouping, BusinessService of BusinessRole die de twee bomen zou
verbinden. De enige elementen die beide raken zijn **de 12 functies en 12 processen zelf** (plus één
toevallig BusinessObject). Geen groepering bevat zowel de functieboom als de procesboom; geen gedeelde
dienst of rol overbrugt ze. De functieboom (302 `Aggregation` functie→functie) en de proceswereld
staan als **twee losse eilanden** in het model.

**Views/groeperingen zonder expliciete relatie?** Er is een `<views>`-sectie, maar dat zijn
diagram-layouts (visuele plaatjes), geen machineleesbare getypeerde relaties. Ze leggen geen
brug die de import zou kunnen volgen.

---

## Blok 3 — Hoe diep gaat de procesindeling

**De proceswereld heeft wél echte diepte** — alleen niet gekoppeld aan de functies. Van de 176
processen:

- 43 zijn "ouder" (dragen deelprocessen), 133 zijn "kind"; 43 zijn wortel.
- Via `Composition` + `Aggregation` proces→proces loopt de boom **4 lagen** diep (bedrijfsproces →
  deelproces → …).
- Daarnaast 57 `Triggering` proces→proces (volgorde/flow) en 45 `Assignment` rol→proces (wie voert
  uit). Het is dus een volwaardige, meerlaagse procesarchitectuur — op zichzelf.

**Verwijst enig element naar een selectielijst-procestype, zaaktype of bewaartermijn?**

**Nee — nergens machineleesbaar, en op géén enkel proces.** Vastgesteld, niet aangenomen:

- Er is **geen property-definitie** voor selectielijst, zaaktype of bewaartermijn (76 property-typen
  in het bestand; geen enkele hierover). Er is dus geen gestructureerd veld waar zo'n verwijzing in
  zou kunnen staan.
- **0 van de 176 BusinessProcess-elementen** bevat een van de termen (selectielijst / zaaktype /
  bewaartermijn / vernietiging / waardering) in naam, documentatie of property.
- Waar de woorden wél vallen, is het **losse prozatekst in de applicatielaag**: "zaaktype" in de
  documentatie van ~16 elementen (vooral Constraint/ApplicationService/DataObject), "selectielijst" in
  6 (Constraint/ApplicationInterface), "bewaartermijn" in 1 (ApplicationService). Dat is toelichtende
  tekst bij eisen en diensten, geen typed archiefmetadata — niet te volgen door een machine.

De archiefwettelijke kapstok (selectielijst-procestype → bewaartermijn) zit dus **niet** in dit model,
in geen enkele vorm die je zou kunnen inlezen.

---

## Blok 4 — Wat LIKARA er vandaag van zou opnemen

De import (`services/ameff.py` → `lees_ameff(pad, element_type="BusinessFunction")`) leest bewust
**één elementtype + de `Aggregation`-boom dáártussen** (ouder = source, kind = target, beide van het
gekozen type). Al het andere wordt **per type geteld als "overgeslagen"** — eerlijk, nooit stil.

Vandaag betekent dat:

- **Wél ingelezen:** de 297 bedrijfsfuncties + de 302 `Aggregation`-relaties functie→functie
  (de functieboom).
- **Stil overgeslagen (geteld):** alle 176 bedrijfsprocessen, de overige ~2.279 elementen van 24
  andere typen, én **álle** relaties behalve de functie-aggregaties — inclusief juist de 12
  `Serving`-bruggen functie↔proces en de 102 `Aggregation`-relaties proces→proces.

Belangrijk: de import is **geparametreerd op elementtype**. Je zou 'm op `BusinessProcess` kunnen
richten en dan zou hij de procesboom (via de proces→proces-aggregaties) net zo netjes inlezen. Maar de
brug functie↔proces kan hij **structureel nooit** vangen: die is een `Serving`-relatie tússen twee
elementtypen, en `lees_ameff` extraheert alleen de aggregatie-boom bínnen één type. De brug valt dus
per ontwerp buiten wat dit importmechanisme kan zien — los van de vraag of hij er is.

**Het geparkeerde proces-datamodel (gate 4, niet verwijderd):** de `proces`-tabel is een
element-subtype met een self-FK `ouder_id` (hiërarchie) — dat zou de meerlaagse procesboom
**structureel kunnen dragen**. Maar er is in LIKARA's schema **geen functie↔proces-relatie**
gemodelleerd, en geen veld voor bewaartermijn/selectielijst/zaaktype. Het datamodel is dus niet de
blokkade; de blokkade is dat de **bron** de brug (en de archiefmetadata) niet levert.

---

## Blok 5 — Oordeel

**Nee. GEMMA levert deze brug niet bruikbaar mee.** De keten die we zouden willen tonen — *systeem →
bedrijfsfunctie → bedrijfsproces → selectielijst-procestype → bewaartermijn* — heeft in dit bestand
**twee gebroken schakels**. De eerste schakel, functie↔proces, bestaat op papier (12 relaties) maar
dekt maar 4% van de functies, ligt uitsluitend in de bedrijfsvoerings-hoek waar functie en proces
synoniem zijn, en is gelegd met de zwakste relatie (`Serving`) — niet met een decompositie. De tweede
schakel, proces↔selectielijst/bewaartermijn, ontbreekt volledig: geen property, geen relatie, geen
proces dat de term draagt. "Gedeeltelijk aanwezig" met 4% dekking is hier een hard nee.

Een gemeente die deze keten wil, zou dus **beide** bruggen zelf moeten leggen — de functie→proces-
koppeling voor 285 functies, én de proces→bewaartermijn-koppeling vanaf nul. Dat is precies het
implementatieproject-vóór-waarde, de wijkende horizon die LIKARA bestaat om te vermijden. **Niet
bouwen.**

**Wat ik uit dit bestand alléén niet kon vaststellen:** of VNG/GEMMA de brug functie↔proces↔
selectielijst in een **ándere, aparte bron** publiceert (bv. een losse GEMMA-processenarchitectuur,
een zaaktypecatalogus/ZTC, of de VNG-selectielijst als eigen dataset). Dit bestand is het
**bedrijfsfunctie-model**; een separate procesbron zou de koppeling in principe kunnen dragen. Maar dat
is dan geen kado dat in dít inleesbare bestand meekomt — het zou een nieuwe bron, een nieuwe meting en
een eigen koppelvraag zijn. Binnen dit bestand: de brug is er niet.

---

## Afsluiting

1. **Read-only — niets gewijzigd, niets gebouwd, niets gecommit.** Uitsluitend het GEMMA-bestand en de
   code gelezen; alle metingen via read-only Python-parsing (geen DB, geen schrijfquery).
2. `git status` van deze worktree: alleen dit nieuwe document is nieuw; verder schoon.
3. **Slice-4a-worktree onaangeraakt:** er is geen aparte slice-4a-bouwworktree (slice 4a stopte bij het
   pre-build-checkpoint, niets gebouwd). De enige worktree is de hoofd-worktree op de schone commit
   `d661846`; deze meting las dus tegen schone, gecommitte grond — geen tussenstand meegelezen.
