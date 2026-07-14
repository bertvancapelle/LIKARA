# Feitenrapport — levensfase van een component (en wat "migratiepad" vandaag betekent)

| | |
|---|---|
| **Opdracht** | LI040-checkpoint-levensfase-component (read-only feitencheck) |
| **Datum** | 2026-07-14 |
| **Commit** | `7148672` (veldbouwsteen-gate — correctie op de opdracht-kop die `87dc120` noemde) — werktree schoon; dit rapport is het enige nieuwe bestand |
| **Modus** | Read-only; code + één DB-meting (`lk_admin`, SELECT-only) |

---

## 1. Uitkomst in één zin

`migratiepad` is een **bestemmings**-veld ("wat gaat er met dit component gebeuren", niet
"waar staat het nu") dat bovendien vrijwel **dood** is — nooit gevuld (19/19 componenten op
`onbekend`) en op slechts twee weergaveplekken gelezen — terwijl de levensfase-vraag alleen
indirect en onbetrouwbaar beantwoordbaar is via de plateau-dispositie; en er bestaan
vandaag al **twee** "uitfaseren"-waarheden (migratiepad-waarde + dispositie-kenmerk), dus
een blind toegevoegd fase-veld zou inderdaad de **derde** zijn — precies het risico dat de
opdracht benoemt.

---

## 2. A — Migratiepad en zijn buren

### A1 — Het veld, volledig

- **Waarden** (enum `Migratiepad`, `models.py:58-64` — single source; geen catalogus, geen
  vrije tekst), met de labels zoals de gebruiker ze ziet (`labels.js:149-156`):
  `lift_and_shift` "Lift-and-shift" · `herbouw` "Herbouw" · `vervangen` "Vervangen" ·
  `uitfaseren` "Uitfaseren" · `gedeeld` "Gedeeld" · `onbekend` "Onbekend".
- **Verplicht mét beginstand**: kolom NOT NULL, `server_default 'onbekend'`
  (`models.py:362-364`, LI057/migratie 0045 — component-breed); het Create-schema default
  op `onbekend` (`schemas/component.py:58`) en het formulier zet dat voor
  (`ComponentFormulier.vue:61,156`). Er is dus altijd een waarde — maar "Onbekend" ís de
  facto de lege staat.
- **Wie zet het**: tenant-rollen medewerker/beheerder (COMPONENT.AANMAKEN/WIJZIGEN), in de
  aanmaak-/bewerk-overlay (`ComponentFormulier.vue:77` — dropdown onder de groep
  "Plaatsing en migratie"). Nergens anders (geen bulk, geen import, geen afleiding).
- **Waar gelezen — precies twee plekken, beide passieve weergave**:
  `ComponentDetail.vue:345` (regel in de `<dl>`) en `LandschapskaartView.vue:1670` (veld
  in de klik-popup). **Niet**: geen kolom of filter in de componentenlijst, geen
  sorteerveld (`ComponentSorteerveld`, `schemas/component.py:21-33` — hosting/complexiteit/
  prioriteit wél, migratiepad niet), geen signalering (`registratiegaten_service` kent
  9 signaaltypen — geen migratiepad), geen dashboard-telling, geen kaartfilter of -kleur,
  geen export.
- **Dood veld: ja, dubbel.** Live-meting dev-DB: **alle 19 componenten staan op
  `onbekend`** — het veld is nooit gevuld, óók niet door de dev-seed-scenario's. Nooit
  gevuld + bijna nergens gelezen = een veld dat vandaag geen enkele vraag beantwoordt.
- **ADR**: ADR-009 (het oorspronkelijke BWB-datamodel; de code is leidend — 6 waarden,
  likara-db-vastlegging) en het LI057-besluit (component-breed, was applicatie-only).
  Geen eigen ADR met een bedoeling-definitie; de bedoeling staat wél in
  `velduitleg.js:94-98` (zie A2).

### A2 — Het oordeel: **bestemming — niet fase** (met één weggelekt woord)

`migratiepad` zegt **waar het heen gaat**, niet **waar het staat**. Bewijs:

1. **De waarden zelf**: lift-and-shift, herbouw, vervangen, gedeeld zijn transitie-
   *aanpakken/bestemmingen* — geen van alle beantwoordt "draait dit nu?" of "is dit al in
   gebruik?". Er is géén waarde voor "in ontwikkeling" en géén waarde voor "in productie,
   blijft gewoon" (het dichtstbijzijnde is impliciet: geen enkel pad).
2. **De eigen uitlegtekst** (`velduitleg.js:94-98`) zegt het letterlijk: *"Wat er met dit
   component in de transitie gaat gebeuren — … **Legt de bedoeling vast, los van of het
   al gebeurd is.**"* — een expliciete bestemmings-/intentie-definitie.
3. **Het ene dubbelzinnige woord**: `uitfaseren` kan als bestemming ("gaat eruit") én als
   fase ("is aan het uitgaan") gelezen worden — dat is het halve antwoord waar de
   aanleiding op wijst. De andere vijf waarden zijn eenduidig bestemming.

De twee vragen zijn bovendien **orthogonaal in het normale geval**: een systeem dat volop
in productie draait én bestemming "vervangen" heeft is geen randgeval maar de kern van een
migratieportfolio. Eén veld kan die twee waarheden alleen dragen via combinatiewaarden —
de waarden-explosie die de opdracht terecht wil vermijden.

### A3 — De buren (onder "Plaatsing en migratie")

| Veld | Betekent feitelijk | Waar gelezen |
|---|---|---|
| `hostingmodel` (enum, 7, NOT NULL) | technische plaatsing — wáár draait het | lijstkolom + filter + sortering, kaart-node + kaartfilter |
| `complexiteit` (NiveauEnum, NOT NULL `midden`) | hoe zwaar is de aanpak (planningsoordeel, `velduitleg.js:99-103`) | lijstkolom + sortering (`ComponentLijst.vue:535-537`) |
| `prioriteit` (NiveauEnum, NOT NULL `midden`) | hoe urgent (planningsoordeel) | lijstkolom + sortering (`:538-540`) |
| `migratiepad` | bestemming (A2) | alleen detail + popup (A1) |

**Samen zijn ze inderdaad een half migratiedossier** — waar draait het · wat gaat ermee
gebeuren · hoe zwaar · hoe urgent — waarin "waar staat het nu in zijn leven" het
ontbrekende eerste hoofdstuk is. Kanttekening: drie van de vier worden werkend gelezen
(lijst/filter/sort); alleen migratiepad ligt braak.

---

## 3. B — Bestaat er al ergens een levensfase-notie?

| Kandidaat | Wat het wél zegt | Wat het níét zegt |
|---|---|---|
| **`lifecycle_status`** (concept / in_inventarisatie / geblokkeerd / migratieklaar) | hoe ver de **registratie** is; gevoed door uitsluitend de score-engine | niets over de werkelijkheid buiten LIKARA. **Engine-inputs, exact** (`lifecycle_service.py:48-52`): `bepaal_lifecycle(huidige, aantal_gescoord, aantal_vragen, aantal_open_blokkades)` — vier parameters, verder niets; `herbereken_lifecycle` telt vragen/scores/open blokkades. Een nieuw registratiefeit blijft daar structureel buiten zolang niemand het in deze twee functies opneemt. |
| **Plateau-dispositie** (behouden / migreren / vervangen / **uitfaseren** — relatiekenmerk op het plateau-lidmaatschap, catalogus-dimensie `dispositie`) | de **enige bestaande uitfaseer-notie**: gelezen door `plateau_service.py:219-232` (lid-read + label) en de kaart-node (`landschapskaart_service.py:192-205` → `plateau_dispositie` op `LandschapsNode`) | het is een **plan-uitspraak per plateau-lidmaatschap**, geen eigenschap van het component: bestaat alleen als het component in een plateau is geplaatst, kan per plateau verschillen, en zegt "in dít doelbeeld gaat het eruit" — niet "het ís aan het uitgaan" |
| **Contract-datums** | `begindatum`/`einddatum`/`vernieuwingsdatum` bestaan (nullable, `models.py` Contract-blok) | er is **geen enkele afleiding** component ↔ contract-einddatum: geen signaal (de 9 ADR-035-signalen kennen geen einddatum), geen kaart-notie, geen telling. Het impliciete uitfaseer-signaal ligt er ongebruikt bij. |
| **Datumvelden op component** (ingebruikname/einddatum) | — | **bestaan niet** (Component: naam/type/hosting/beschrijving/eigenaar/rol/BIV/migratiepad/complexiteit/prioriteit + timestamps) |
| **`actief`-vlag / soft-delete op component** | — | **bestaat niet** (verwijderen = hard, via het element-supertype) |

**Oordeel B**: ja — maar alleen **indirect en onbetrouwbaar**. Een gebruiker kan "wordt
uitgefaseerd" vandaag uitsluitend zien via (a) de plateau-dispositie `uitfaseren`, mits
iemand het component in een plateau plaatste én de dispositie zette (contextgebonden,
optioneel), of (b) het migratiepad-veld op het detail, dat in de praktijk overal
"Onbekend" toont. "In ontwikkeling" is **nergens** uitdrukbaar; "in productie" is overal
een stilzwijgende aanname.

---

## 4. C — Waar zou het landen (twee opties, feitelijk)

### Optie 1 — een nieuw registratiefeit op het component

Twee bestaande recepten passen, beide op dezelfde plek (kolom op `component`):

- **Catalogus-recept** (`componentrol`, ADR-028/migratie 0048): `String(60)` kolom +
  single-purpose platform-catalogus (`componentrol_optie`-vorm: id/optie_sleutel/label/
  volgorde/actief; lk_app SELECT, lk_platform S/I/U zonder DELETE; soft-deactivate) —
  waarden beheerbaar door de platformbeheerder. Sub-varianten die de code kent:
  NOT NULL + `server_default` (rol-recept — altijd een waarde) of nullable (BIV-recept —
  leeg = registratiegat, voedt signalering).
- **Enum-recept** (`migratiepad` zelf): Python-enum + PostgreSQL-enum — waarden in code,
  wijzigen = migratie.

**Raakpunten-telling** (gemodelleerd op de feitelijke ADR-028-rol-implementatie):
migratie (1) · model (1) · schemas Create/Update/Read/LijstItem (4) · service
maak/werk-bij/read-verrijking/lijst-filter (4) · opties-endpoint + `ComponentOpties` (2) ·
route-filterparam (1) · `api.js`-allowlist (1) · formulier (1) · detail (1) · lijst
kolom+filter (1) · kaart `LandschapsNode` + popup (2) · labels + velduitleg (2) ·
seed/dev-testdata (1) · tests (≥4) — **~22 raakpunten over ~15 bestanden**, vrijwel
identiek aan wat ADR-028 destijds raakte.

**Engine-grens — bewezen sluitend**: de engine leest uitsluitend de vier
`bepaal_lifecycle`-inputs (score/vragen/blokkades); een component-kolom komt daar alleen
in als iemand hem expliciet in `lifecycle_service` opneemt. Het enige denkbare
inlek-punt is verleiding, geen mechaniek: "fase = uitfaseren, dus zet de lifecycle op X"
— dat zou een tweede engine-poort zijn en is exact wat het bestaande dubbele
borgingspatroon (import-afwezigheidstest + live geen-mutatie-test) per slice afvangt.

### Optie 2 — verrijking van `migratiepad`

Waarden toevoegen/hernoemen zodat het veld óók de fase draagt. Feitelijke kosten:
technisch goedkoop (`ALTER TYPE … ADD VALUE`; 19×`onbekend` dus geen datakost; 2
leesplekken + labels + formulier), **maar semantisch draagt één veld dan twee orthogonale
vragen** (A2): "in productie + wordt vervangen" — het normale geval — vergt
combinatiewaarden (explosie) óf laat één van de twee vragen onbeantwoord. Elke lezer
(lijst, kaart, gap-signaal) moet voortaan twee vragen uit één waarde destilleren. Dit is
beschrijving, geen keuze.

### De drie-waarheden-kaart (het risico uit de opdracht, gemeten)

Er zijn er vandaag al **twee**: `migratiepad = uitfaseren` (bestemming, component-breed)
en `dispositie = uitfaseren` (plan, per plateau-lidmaatschap). Een fase-veld met een
uitfaseer-waarde wordt de **derde**. Wat de code toelaat: de drie assen zijn verenigbaar
mits afgebakend (fase = werkelijkheid nú, component-breed · migratiepad = bestemming ·
dispositie = plan-per-doelbeeld) — maar die afbakening bestaat nergens op schrift en de
woorden overlappen letterlijk. Zonder vastgelegde afbakening krijgt "welke systemen
verdwijnen komend jaar?" drie antwoorden.

---

## 5. D — De kaartvraag

- **De kaart kleurt vandaag op de registratiestatus** (vulkleur = `lifecycle_status`,
  de `_nodeData`-stijlbron) — dus op "hoe ver is de vastlegging", niet op "wat is er
  buiten waar". De node draagt wel al `plateau_naam`/`plateau_dispositie` (en sinds
  ADR-028 rol/BIV) — het patroon "registratief kenmerk op de node + filter + legenda"
  bestaat en is drie keer herhaald.
- **Als het fase-feit bestond**, zouden deze plekken het kunnen lezen (inventaris, geen
  ontwerp): `LandschapsNode` + `_nodeData`/popup/legenda + kaartfilter (het
  rol/BIV-precedent incl. filter-exemptie voor context-nodes) · het **gap-signaal van
  gate 3** — ADR-044 besluit 4 (per plaatsing) + de ADR-045-besluit-2-keerzijde is
  letterlijk dezelfde familie: *"gedragen door een noodgreep"* en *"gedragen door iets
  dat verdwijnt"* zijn twee smaken van "niet volwaardig ondersteund" · de
  componentenlijst (kolom + filter, het `ondersteunt_werk`-precedent van gisteren) ·
  de signalering (ADR-035-patroon: "functie gedragen door uitsluitend
  uitfaserende/nog-niet-draaiende componenten") · het dashboard (telling + doorklik).
- De bedrijfsfunctie-koppeling zelf bestaat nog niet (gate 2) — het "gat met een tijdbom"
  is dus pas toonbaar zodra gate 2 én het fase-feit er beide zijn; de leespaden hierboven
  zijn er klaar voor.

---

## 6. Open knopen voor Bert

1. **Nieuw feit of verrijking?** Beide feitelijk beschreven (C). De orthogonaliteit
   (A2: "in productie + wordt vervangen" is het normale geval) is het feit waarop dit
   scharniert.
2. **Vorm bij een nieuw feit**: platform-catalogus (componentrol-recept — beheerbaar,
   soft-deactivate) of code-enum (migratiepad-recept — vast). De fase-waardenlijst uit de
   aanleiding (in ontwikkeling / in productie / uitfaseren) is gesloten en klein; beide
   recepten bestaan.
3. **Verplicht-met-default of nullable**: NOT NULL + `server_default` (rol-recept — maar
   wélke default: "in productie" maakt de stilzwijgende aanname expliciet; "onbekend"
   herhaalt het migratiepad-lot) versus nullable (BIV-recept — leeg = registratiegat,
   signaleerbaar).
4. **De afbakening van de drie uitfaseer-waarheden** (fase · migratiepad-bestemming ·
   plateau-dispositie): vastleggen hoe ze zich verhouden, en of `migratiepad.uitfaseren`
   en/of de waardenset van migratiepad zelf herzien wordt zodra de fase bestaat. Dit is
   de kern van het ADR dat hierop volgt.
5. **Wat te doen met het dode veld nu**: migratiepad alsnog leesbaar/filterbaar maken
   (lijst/kaart — het is 3 van de 4 buren al), laten liggen tot het fase-besluit, of
   meenemen in dezelfde slice.
6. **Consumptie-volgorde**: het fase-feit alleen registreerbaar maken (formulier/detail/
   lijst) en de kaart-/gap-consumptie in gate 3 laten landen, of direct de kaart-node +
   filter meenemen (rol/BIV-precedent deed dat in één ADR, in slices).

---

## 7. Wat ik NIET kon vaststellen

- **Of "gedeeld" als bestemming nog een levende betekenis heeft** (LI057 hernoemde
  `tijdelijk_gedeeld` → `gedeeld`): met 0 gevulde waarden is er geen gebruiksfeit om op
  te toetsen; de betekenis leeft alleen in ADR-009-context.
- **Hoeveel componenten in de praktijk een plateau-dispositie dragen**: de dev-DB heeft
  plateaus met leden, maar dev-data zegt niets over echt gebruik; het structurele punt
  (dispositie bestaat alleen bínnen een plateau) staat los daarvan vast.
- **Berts precieze fase-indeling** (zijn de drie fasen uit de aanleiding compleet — of
  horen er meer bij, zoals "gepland/besteld" vóór ontwikkeling of "uitgefaseerd" als
  eindstand): dat is een domeinkeuze voor het ADR, geen codefeit.
