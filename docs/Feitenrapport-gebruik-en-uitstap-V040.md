# Feitenrapport — wie gebruikt een component, en kan LIKARA dat betrouwbaar tellen?

| | |
|---|---|
| **Opdracht** | LI040-checkpoint-gebruik-en-uitstap (read-only feitencheck) |
| **Datum** | 2026-07-14 |
| **Commit** | `7148672` — werktree schoon; dit rapport is het enige nieuwe bestand |
| **Modus** | Read-only; code + DB-metingen (`lk_admin`, SELECT-only) |

---

## 1. Uitkomst in één zin

"Wie gebruikt dit component" is als organisatielijst een **hard af te leiden feit** — er is
één canonieke bron (`organisatiegebruik`, uniek per organisatie×component, al gelezen door
de kaart én door een bestaand endpoint), structureel consistent met de groepen-laag (0
divergentie gemeten) — maar de twee tellingen wijken in de praktijk **fors** af (via
groepen: 4 componenten/max 3 organisaties; via het grove feit: 8 componenten/tot 5) omdat
**25 van de 32 gebruiksfeiten grof-only zijn**: wie op de gebruikersgroepen telt, telt een
ondergrens — en een voornemen dat op de groep zou landen is voor die 25 relaties zelfs
**onregistreerbaar**.

---

## 2. A — De twee lagen

### A1 — Exact

**Gebruikersgroep** (`models.py:467-507`) — element-subtype (shared-PK → `element`), met:
- `gebruik_id` **NOT NULL** → composiet-FK naar `organisatiegebruik` (ON DELETE RESTRICT,
  `:486-489`) — de organisatie leeft dáár, niet op de groep (ADR-036/038, single source);
- `afdeling_id` optioneel → organisatie-eenheid-partij (RESTRICT, `:494-497`);
- `aantal_gebruikers` optioneel;
- **de band met de applicatie is een `serving`-relatie** (applicatie → groep), aangemaakt
  in dezelfde transactie als de groep (`gebruikersgroep_service.py:362-363`).
De groep hangt dus aan een **combinatie**: applicatie (via serving) + organisatie (via het
grove feit) + optioneel afdeling.

**Organisatiegebruik** (`models.py:431-464`) — eigen tenant-tabel (géén element-subtype;
roltoewijzing-vorm): `organisatie_id` + `applicatie_id` (beide composiet-FK → element,
**ON DELETE CASCADE**), **`UNIQUE(tenant_id, organisatie_id, applicatie_id)`** — één feit
per (organisatie, component); "onvolledig = geldig" (grof-only mag). ⚠ **Docstring-correctie**:
`:442-443` beweert dat `applicatie_id` app-side op `componenttype='applicatie'` wordt
geborgd — dat is **stale**: sinds ADR-041-herziening is het slot **component-breed**
(`organisatiegebruik_service.valideer_component:33-49` eist alleen "bestaand component,
élk type"). De kolomnaam `applicatie_id` is dus historisch.

**De verhouding**: organisatiegebruik is een **eigen, zelfstandig feit** dat óók de rol
van ouder speelt: de groep is een *verfijning ván* het grove feit (`gebruik_id`). Beide
bestaan: 25 van de 32 feiten staan er vandaag zónder verfijning onder (grof-only), 7 mét.

### A2 — Ontstaat het grove feit automatisch? **Ja — en het blijft ook staan.**

- **Aanmaak**: `gebruikersgroep_service.maak_aan:353` roept
  `organisatiegebruik_service.ensure` (get-or-create, silent reuse, `:66-80`) — wie een
  groep bij afdeling X van gemeente C aanmaakt, borgt automatisch het feit (C, applicatie).
  Zelfde bij een org-wissel in `werk_bij:377-391` (ensure op de nieuwe organisatie).
- **Verwijderen van de groep** (`:405-409`, delete via het element-supertype): het grove
  feit **blijft staan** — er is geen FK van gebruik→groep en geen opruim-logica. Idem bij
  een org-wissel: het **oude** grove feit blijft achter (ensure maakt/vindt het nieuwe,
  ruimt het oude nooit op). Bewust ontwerp (grof-only is geldig), maar het betekent: het
  grove feit representeert *"ooit geregistreerd gebruik"* totdat iemand het expliciet
  verwijdert.
- **Invoerroute los grof feit — bevestigd zoals verwacht, met een nuance**: de backend is
  compleet (`routes/organisatiegebruik.py`: GET `:37` met `applicatie_id`- óf
  `organisatie_id`-filter, **POST `:63`**, **DELETE `:74`**), maar de **api-client kent
  alleen `lijstVoorOrganisatie`** (`api.js:198-200`) — geen `maak`, geen `verwijder`,
  geen applicatie-kant. Er is dus geen UI-formulier én geen UI-opruimroute; ook het
  achtergebleven "spook-gebruik" (hierboven) is alleen via de kale API te verwijderen.

### A3 — De meting die het beslecht: **de tellingen wijken af — fors**

Dev-DB: **8 gebruikersgroepen** (alle 8 met organisatie — NOT NULL) · **32
organisatiegebruik-rijen** · 0 groepen zonder serving-relatie · **0 groepen waar de
serving-applicatie ≠ de grove-feit-applicatie** (consistentie structureel én feitelijk).

| Component | (a) organisaties via groepen | (b) organisaties via het grove feit |
|---|---|---|
| BRP | **0** | 4 |
| Burgerzaken-suite | 1 | **5** |
| DMS | 1 | 4 |
| Gegevensmakelaar | **0** | 4 |
| Klantportaal | 2 | 2 |
| Sociaal domein suite | **0** | 4 |
| Zaakafhandelcomponent | **0** | 4 |
| Zaaksysteem | 3 | **5** |

**Ja, ze wijken af** — op 7 van de 8 componenten. De verklaring is volledig herleidbaar:
**25/32 feiten zijn grof-only** (geen verfijnende groep). Er bestaan dus vandaag al twee
antwoorden op "wie gebruikt dit" — maar anders dan gevreesd is de eerste ontwerpvraag
beantwoordbaar uit het ontwerp zelf: (a) is per constructie een **deelverzameling** van
(b) (elke groep wijst via `gebruik_id` naar een grof feit met dezelfde applicatie — 0
divergentie gemeten), dus **het grove feit is de volledige telling en de groepen-telling
een ondergrens**. ADR-036 bedoelde het precies zo (single source of truth).

---

## 3. B — Kan "wie gebruikt dit" als organisatielijst worden afgeleid?

**Ja — de leespaden bestaan al gedeeltelijk:**

1. **Endpoint**: `GET /organisatiegebruik?applicatie_id=…` levert exact "welke
   organisaties gebruiken dit component" (`routes/organisatiegebruik.py:37-49`,
   `OrganisatiegebruikRead`). ⚠ **Ontbrekende schakel: de api-client** — `applicatie_id`
   staat niet in de `_filterQuery`-allowlist (`api.js:200` kent alleen `organisatie_id`)
   en geen enkel scherm roept de applicatie-kant aan; ComponentDetail toont wél de
   gebruikersgroepen-sectie (de ondergrens) maar geen organisatielijst.
2. **De kaart leest het grove feit al op drie plekken**
   (`landschapskaart_service.py:108-109` subgraaf-scope; `:298-303` gg-aggregatie via
   `gebruik_id`; `:331-339` "gebruikt door organisatie(s)" per component uit
   `Organisatiegebruik`).
3. **Per organisatie** bestaat de spiegel al in de UI: `GebruikteApplicatiesSectie.vue`
   (PartijDetail) op `lijstVoorOrganisatie` — incl. `verfijnd`-vlag.

**Betrouwbaarheid**:
- **Dubbeltellen kan niet**: `UNIQUE(tenant, organisatie, applicatie)` — twee afdelingen/
  groepen van dezelfde gemeente convergeren via `ensure` op dezelfde rij.
- **Onzichtbaar als organisatie**: sinds ADR-038 structureel onmogelijk voor
  geregistreerd gebruik (groep zonder organisatie bestaat niet; het grove feit ontstaat
  altijd mee). Wat overblijft is niet-geregistreerd gebruik — per definitie onzichtbaar,
  en dát hoort de signalering te dragen. ⚠ Daar zit een **bestaande inconsistentie**: het
  signaal `component_zonder_gebruikersgroep` telt uitsluitend **serving-relaties**
  (`registratiegaten_service.py:229-242`) — de vier componenten met 4 grove gebruikers
  maar 0 groepen (BRP, Gegevensmakelaar, …) vuren dit signaal vandaag **onterecht**: er
  ís gebruik geregistreerd, alleen grof.
- **Vervuiling naar boven**: het achterblijvende spook-gebruik uit A2 (org-wissel/
  groep-delete) telt mee als gebruiker; opruimen kan alleen via de kale DELETE-API.

**Oordeel: hard af te leiden feit** — mits geteld op het grove feit. Eén canonieke bron,
uniciteit per (organisatie, component), structurele consistentie met de verfijning, en
bestaande leespaden (kaart + endpoint). *"3 van de 4 gebruikers blijven"* is exact
telbaar; de kanttekening is niet de telling maar het **bijhouden** (spook-gebruik heeft
geen UI-opruimroute, en het gaten-signaal kijkt naar de verkeerde laag).

---

## 4. C — Waar zou het voornemen landen? (beide opties, feitelijk)

### Optie 1 — op de gebruikersgroep (afdelingsniveau)

- Kolom op `gebruikersgroep` + Create/Update/Read + `GebruikersgroepSectie`-formulier +
  read-verrijking: **~10 raakpunten** (migratie · model · 3 schemas · service ·
  formulier · sectie-weergave · labels · tests).
- ⚠ **Het "drie keer zeggen"-risico bestaat feitelijk**: meerdere groepen per
  (organisatie, component) is precies het model (per afdeling een groep — Zaaksysteem
  heeft er vandaag 3 van 3 organisaties). Consistentie tussen die groepen zou app-side
  bewaakt moeten worden of het "halve vertrek" ontstaat zoals de opdracht schetst.
- ⚠ **Zwaarder**: voor de **25 grof-only feiten is er geen groep** — het voornemen zou
  daar pas registreerbaar zijn ná het aanmaken van een verfijning die er inhoudelijk
  niet is. Het voornemen op de groep kan het dev-scenario ("gemeente C stapt uit alle 12")
  vandaag dus grotendeels niet eens dragen.

### Optie 2 — op het organisatiegebruik (organisatieniveau)

- Kolom op `organisatiegebruik` (het niveau waarop het besluit valt; de `ensure` en de
  UNIQUE bestaan al) + Create/Update-pad + leespaden. **Raakpunten (~15)**: migratie (1) ·
  model (1) · schemas (2) · service maak/werk-bij/lees (2) · route PATCH ontbreekt nog
  (GET/POST/DELETE bestaan — 1) · **api-client: `maak`/`verwijder`/`lijstVoorApplicatie`/
  werk-bij ontbreken alle vier** (1 blok) · **het losse-invoer-formulier — het
  ADR-036-restpunt hoort dan inderdaad bij de slice** (1) · `GebruikteApplicatiesSectie`
  toont het voornemen per organisatie (1) · een component→organisaties-weergave op het
  detail (1) · kaart-popup/edge (1) · signalering (1) · labels/velduitleg (1) · tests (≥2).
- Alle 32 bestaande feiten kunnen het voornemen direct dragen; de groepen erven het via
  hun `gebruik_id`-verwijzing (leesbaar zonder tweede registratie).

---

## 5. D — Afgeleide zwaarte, functie-doorwerking, engine-grens

- **Tellen kan**: "N organisaties gebruiken dit, waarvan M met voornemen 'stapt eruit'"
  is één `GROUP BY` op het grove feit zodra het voornemen-veld bestaat — geen andere
  schakel ontbreekt dan dat veld + de leespaden (C-optie 2). "Valt om" = N−M = 0 blijvers;
  "minder draagvlak" = M > 0 én blijvers > 0 — beide afgeleid, niets opgeslagen.
- **Functie-doorwerking** (zodra gate 2 bestaat): "functie gedragen door uitsluitend
  omvallende componenten" is een join plaatsing→component→(fase/voornemen-telling) —
  dezelfde leesfamilie als het gate-3-gap-signaal (ADR-044 besluit 4) en de
  ADR-045-keerzijde ("gedragen door een noodgreep"); leesplekken: gap-signaal ·
  functieboom/diagram-cue · kaart · signalering · dashboard.
- **Engine-grens — bewezen**: `organisatiegebruik_service` draagt de engine-invariant
  expliciet (docstring `:11-13`, machine-geborgd via de bestaande
  import-afwezigheidstest); de engine-inputs zijn gesloten
  (`bepaal_lifecycle(huidige, gescoord, vragen, open_blokkades)`,
  `lifecycle_service.py:48-52`). Een voornemen-kolom op het gebruik kan alleen inlekken
  als iemand hem expliciet in `lifecycle_service` opneemt — het bestaande dubbele
  borgingspatroon (import-afwezigheid + live geen-mutatie) dekt dat per slice af.

---

## 6. Open knopen voor Bert

1. **Bevestiging van de telbron**: het grove feit als canonieke gebruikstelling (de
   groepen als ondergrens/verfijning) — de code wijst er eenduidig heen, maar het staat
   nergens als regel op schrift; het uitstapscherm gaat erop leunen.
2. **Voornemen op groep of op gebruik**: beide beschreven (C). Het 25/32-grof-only-feit
   en het "drie keer zeggen"-risico zijn de meetbare feiten waarop dit scharniert.
3. **Het spook-gebruik**: org-wissel en groep-delete laten het oude grove feit staan, en
   er is geen UI-route om het op te ruimen (DELETE bestaat alleen als endpoint). Opties:
   de losse-invoer-slice krijgt óók de verwijder-route in de UI · een signaal
   "gebruiksfeit zonder enige verfijning én zonder recente bevestiging" · laten (grof-only
   is immers geldig — maar dan telt spook mee in het uitstapscherm).
4. **Het inconsistente signaal**: `component_zonder_gebruikersgroep` telt serving-relaties
   en vuurt onterecht op grof-only geregistreerd gebruik (4 componenten vandaag). Opties:
   hertellen op het grove feit · hernoemen/splitsen (zonder-gebruik vs. zonder-verfijning
   — het tweede signaal bestaat al) · laten.
5. **De ontbrekende client-/UI-schakels** (applicatie-kant van het GET-endpoint,
   maak/verwijder in de client, het losse-invoer-formulier): bij de voornemen-slice
   trekken of als eigen reparatie ervoor.
6. **De stale kolomnaam/docstring** (`applicatie_id` op een component-breed feit,
   `models.py:442-443`): hernoemen (migratie) of alleen de docstring corrigeren.

---

## 7. Wat ik NIET kon vaststellen

- **Of grof-only de bedoelde eindtoestand is of achterstallige verfijning**: de dev-seed
  registreert de 4-gemeenten-matrix bewust grof (BvoWB-scenario); hoe echte consultants
  de verhouding grof/fijn gaan gebruiken is geen codefeit.
- **De volledige voornemen-waardenset** ("blijft · stapt eruit · komt erbij" — plus
  eventueel een datum/horizon bij "stapt eruit"): domeinkeuze voor het ADR.
- **Hoe het voornemen zich verhoudt tot de levensfase-knopen** (vorig rapport): de twee
  sporen delen de kaart-/gap-leespaden; de afbakening (fase op component · voornemen op
  gebruik · dispositie per plateau · migratiepad-bestemming) is ontwerp, geen feit — al
  wijst het besluit van Bert (kop van deze opdracht) de richting.
