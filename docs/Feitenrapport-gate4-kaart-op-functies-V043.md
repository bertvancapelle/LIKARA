# Feitenrapport — gate 4: de kaart op functies, het procesregister uit de MVP-UI

**Build:** V042 · **Commit:** `254f905` · **Datum:** 2026-07-14 · **Modus:** READ-ONLY checkpoint
**Meetbron:** codebase (canoniek) + de vastgelegde gate-2/3-checkpoints (`Feitenrapport-koppelen-bedrijfsfunctie-V041.md`, `Feitenrapport-gapsignaal-V041.md`).
**Reikwijdte:** vaststellen wat de gebruiker vandaag aan "proces" ziet en doet, wat de kaart leest, wat er al aan functie-kant ligt, en welke keuzes vóór de gate-4-bouw open zijn. **Geen wijziging, geen migratie, geen commit** — alleen dit ene bestand.

> Elke uitspraak draagt een **vindplaats** (`bestand:regel`). Waar de code afwijkt van een aanname in de opdracht/ADR/skill: gemeld in **§5**, code wint. Paden in de module beginnen met `modules/bwb_ontvlechting/…`.

---

## §0 — Samenvatting in gebruikerstaal

Vandaag heeft "proces" een **eigen ingang in het hoofdmenu** ("Processen"), zichtbaar voor **elke** ingelogde gebruiker — geen rol-slot. Daar leeft een volwaardig register: een procesboom (Boom | Diagram), aanmaken/hernoemen/verplaatsen/verwijderen, deelprocessen, en per proces "Componenten in dit proces". Op het **componentdetail** beantwoordt de sectie *"Waarvoor gebruiken we het"* de waarvoor-vraag vandaag **in processen**, niet in bedrijfsfuncties. Op het **componentformulier** staat bij aanmaken een "Vervult een rol in"-blok met een subveld "Proces". De **kaart** heeft een eigen proceslaan ("Processen") met vervult-lijnen, een "geen ondersteunend systeem"-cue en een "Via proces"-ingang.

Na gate 4 verschuift het anker: de waarvoor-vraag wordt op het component in **bedrijfsfuncties** beantwoord, en het procesregister verdwijnt uit de MVP-UI (menu + schermen) — **verborgen, niet verwijderd**: model, service, kaartlaan en seed blijven intact.

**Het grootste risico** zit niet in het verbergen zelf, maar in één onbesliste spanning: **ADR-043 besluit 8 wil de proceslaan óók van de kaart af** ("menu, ingangen **én de proceslaan op de kaart**"), terwijl de randvoorwaarde in déze opdracht die laan juist wil **behouden** als read-only verrijking. Dat is een echte, nog te nemen keuze (§4.1 / §5.1) — niet iets om stilzwijgend één kant op te bouwen. Het tweede risico: de titel *"Waarvoor gebruiken we het"* is nú al door de proces-sectie bezet; de functie-leesrichting *"op welke functies hangt dit component"* bestaat nog **niet** (§3).

---

## §1 — Wat ziet de gebruiker vandaag aan "proces"? (inventarisatie, deel 1)

Waar "verdwijnt bij verbergen" staat, betekent *verbergen* = nav-item + de routes `proces-lijst`/`proces-detail` weghalen.

| # | Waar de gebruiker het ziet | Wat hij er kan | Vindplaats | Verdwijnt bij verbergen? |
|---|---|---|---|---|
| 1 | **Menu-item "Processen"** (onder kop "BWB-ontvlechting), **zonder rol-slot** | Naar het register | `frontend/src/layouts/AppLayout.vue:129-136` (`data-testid="nav-processen"`, `{name:'proces-lijst'}`) | **Ja** — dit ís de nav-ingang |
| 1 | Routes `proces-lijst` (`processen`) + `proces-detail` (`processen/:id`), **zonder `meta.roles`** | URL/deeplink | `frontend/src/router/index.js:140-141` (lazy imports `:34-35`) | **Ja** — routes weghalen |
| 2 | **Componentformulier (aanmaken):** blok **"Vervult een rol in"** met subvelden **"Proces"** + "Applicatiefunctie" + "Toelichting" | Proces-koppelingen alvast opstellen; ná opslaan in bulk gepost | `ComponentFormulier.vue:413-463` (kop `:415`, "Proces" `:436`, picker `:442`) | **Nee** — woont op het componentformulier; het subveld "Proces" moet apart verwijderd |
| 2 | **Er is GÉÉN los "PROCES"-element-veld** op het formulier | — | Bestaat niet (alleen de collector hierboven) | n.v.t. |
| 3 | **Componentdetail:** sectie **"Waarvoor gebruiken we het"** (de vier-vragen-opbouw, 3e vraag) toont proces-koppelingen | Zien/toevoegen/bewerken/verwijderen; procesnaam-links | `ComponentDetail.vue:456-462` → `ComponentProcessenSectie.vue:215` (kop) | **Nee** — sectie woont op componentdetail; de proces-links (`:234,250`) worden doelloos |
| 4 | **Procesregister-lijst "Processen"** met schakelaar **Boom \| Diagram**, "Nieuw proces", zoek, gap-badge "geen ondersteunend systeem" | Aanmaken/hernoemen/verplaatsen/verwijderen/diagram | `ProcesLijst.vue:439,456,463,465,589,606-634` | **Ja** — scherm onbereikbaar |
| 4 | **Proces-detail** (broodkruimel, toelichting, "Bekijk op kaart") | Detail; deelproces toevoegen; naar kaart | `ProcesDetail.vue:159-164,199` | **Ja** — scherm onbereikbaar |
| 4 | Sectie **"Componenten in dit proces"** (op proces-detail) | Koppelingen zien/toevoegen/bewerken/verwijderen | `ProcesComponentenSectie.vue:224` | **Ja** — deel van proces-detail |
| 4 | Roll-up **"Onderliggende processen"** (open-tenzij-groot) | Deelprocessen + doorgerolde componentregels | `OnderliggendeProcessenSectie.vue:105,108,134-135` | **Ja** — deel van proces-detail |
| 4 | **Organisatie-proceskijk:** sectie **"Processen"** op organisatiedetail (afgeleid, read-only) | Afgeleide processen + brug-componenten | `PartijProcessenSectie.vue:49` via `PartijDetail.vue:359-362` | **Nee** — woont op organisatiedetail; proces-links (`:61`) worden doelloos |
| 5 | **Kaart:** ring/laan **"Processen"**, proces-knopen, **vervult**-edges ("vervult", "N×"), hiërarchie "onderdeel van", **gap-cue** (dashed), popup **"Vervuld door"**, **vervul-toggle**, **"Via proces"**-ingang, "Open proces →", "Bekijk op kaart" | Proceslaag verkennen; via proces inzoomen; dubbelklik-inzoom | `LandschapskaartView.vue:70,85,1492,1583,1607-1650,2244,2695,2990-2994`; `KaartBeginscherm.vue:324-328` | **Nee** (gated `magArchitectuurZien`) — zie §2; "Open proces →"-navigatie wordt doelloos |
| 6 | **Signalering / Dashboard / componentenlijst-typefilter** | — | `SignaleringView.vue`, `DashboardView.vue`, `ComponentLijst.vue` — geen proces-treffer | Proces komt hier **niet** voor (niets te verbergen) |
| 7 | **Deep-links/handoff:** "Bekijk op kaart" = **sessionStorage-handoff** (géén route-query); enige echte route-param = `proces-detail/:id` | — | `procesKaartIngang.js:17` (`bouwProcesKaartHandoff`); `ProcesDetail.vue:116-125`, `ProcesLijst.vue:409-419` | Handoff overleeft verbergen; `:id`-route verdwijnt met de route |
| 7 | **Bewaarde lijststaat:** sleutel `lijst-state:proces-lijst` (sessionStorage): `zoekterm`, `openTakken`, `weergave` | — | `ProcesLijst.vue:60-71`; `useLijstStaat.js` | Onbereikbaar met het scherm; blijft als dode sessie-sleutel |
| 8 | **Terug-navigatie-labels** `proces-lijst → "Processen"`, `proces-detail → "Proces"` | — | `useTerugNavigatie.js:22-23` | Bewegen mee |

**Taal op het scherm (letterlijk, het vertaalpunt voor gate 4).**
Menu/titels: **Processen** (nav, `ProcesLijst` h1, organisatie-sectie h2). Secties: **Waarvoor gebruiken we het** · **Vervult een rol in** · **Componenten in dit proces** · **Onderliggende processen**. Subvelden: **Proces** · **Applicatiefunctie** · **Toelichting**. Acties: **Nieuw proces** · **Boom** · **Diagram** · **Toon in procesbeeld →** · **Bekijk op kaart** · **Deelproces toevoegen** · **Toon hele processenlandschap** · **Open proces →** · **Hoofdproces**. Cues/lege staten: **geen ondersteunend systeem** · **Nog niet vastgelegd in welke processen dit component een rol vervult.** · **Nog geen componenten aan dit proces gekoppeld.** · **Vervuld door** · **Proceslandschap: … · via …**. Kaart: laan **Processen**, edge **vervult**. (i)-uitleg (`velduitleg.js:22-47`): *"Een proces is wat de organisatie doet, van grof naar fijn nestbaar. Voorbeeld: Vergunningverlening → Aanvraag behandelen."*

**Rol-observatie (relevant voor "wie ziet het"):** het nav-item én de routes zijn **ongegate** — elke ingelogde gebruiker ziet "Processen" vandaag (contrast: Signalering staat op `v-if="magArchitectuurZien"`, `AppLayout.vue`). Er is **geen test** die de zichtbaarheid van `nav-processen` asserteert (`AppLayout.test.js:26` registreert alleen de route-stub), dus verbergen breekt geen nav-assertie.

---

## §2 — Wat leest de kaart, en wat raakt het verbergen? (deel 2)

### 2.1 Wat de kaart precies leest — en of het read-only verrijking is

**Bevestigd: verrijking, read-only, géén scope-verbreding.**

- De kaart is één view, `LandschapskaartView.vue` (drie weergaven: overzicht / praatplaat / lagen). De proceslaan tekent de kaart **zelf** als Cytoscape-knopen/edges — **niet** via `ProcesDiagram.vue` (die hoort alleen bij het register en de functieboom; `ProcesLijst.vue:29`, `BedrijfsfunctieLijst.vue:41`).
- Backend: `GET /landschapskaart` + `POST /landschapskaart/subgraaf` → `landschapskaart_service.haal_grafdata_op` (`landschapskaart_service.py:64`). De proces-blok (`:494-625`) leest `Procesvervulling`, `Proces` en `Component` met **alleen `select(...)`** — geen `add/commit/flush/delete`. Module-docstring `:8-13` ("puur read-only, afgeleid … schrijft niets").
- **Geen scope-verbreding:** `scope_ids` wordt alleen uit componenten + hun 1-hop-buren opgebouwd (`:82-139`); processen worden er **nooit** aan toegevoegd. De proces-subboom wordt ná de scope afgeleid en gefilterd met een dangling-guard (`pv_rijen = [r for r in pv_rijen if r.component_id in comp_node]`, `:520`) — een component buiten beeld trekt géén proces-subboom binnen. Code-comment bevestigt letterlijk: "Read-only VERRIJKING … geen scope_ids-verbreding" (`:494-495,507`).

→ De opdracht-aanname ("de kaart leest de proces-projectie als read-only subgraaf-verrijking, geen scope-verbreding") is **bevestigd door de code**.

### 2.2 Waar `ARCHITECTUUR.LEZEN` aan hangt

- Definitie: `Entiteit.ARCHITECTUUR = dict(_ALLEEN_LEZEN)` (`backend/app/core/rbac.py:185`) — LEZEN voor **elke** tenant-rol (viewer/medewerker/beheerder/auditor); er bestaan **geen schrijfacties** op deze entiteit.
- Hangt aan: `routes/landschapskaart.py:27` (GET) en `:37` (POST subgraaf) — **de kaart**; verder `routes/architectuur.py:39`, `routes/signalering.py:25`, `routes/plaatsingsignaal.py:24`.
- De kaart-proces-ring draait dus volledig ónder `ARCHITECTUUR.LEZEN` — **`PROCES.LEZEN` is niet nodig** voor de statische ring (die query't de modellen direct in de service).
- **Wat breekt als iemand `ARCHITECTUUR` zou opruimen?** Dan valt de hele kaart + signalering + architectuur-lees weg — het is een gedeelde leesentiteit, geen proces-specifiek slot. **Niets aangeraakt; alleen vastgesteld.**

### 2.3 Wat valt stil als het procesregister uit de UI gaat

*Verbergen* hier = nav + routes `proces-lijst`/`proces-detail` weg (evt. de "Bekijk op kaart"/"Via proces"-ingangen). De **backend**-routes (`/processen`, `/procesvervullingen`, `/landschapskaart`) blijven bestaan.

| Kaart-/proces-onderdeel | Bron | Uitkomst |
|---|---|---|
| Statische proces-ring op de kaart (knopen, vervult-edges, "onderdeel van", gap-cue, "Vervuld door"-popup) | `/landschapskaart` (ARCHITECTUUR.LEZEN), `landschapskaart_service.py:494-625` | **Blijft draaien** — leest de modellen direct, los van het register |
| Vervul-toggle op een proces-popup | client-side op geladen graafdata (`LandschapskaartView.vue:1607-1650`) | **Blijft draaien** (geen eigen fetch) |
| Dubbelklik-inzoom `zoomInOpProces` | `api.processen.rollup` + `api.procesvervullingen.lijst` (`LandschapskaartView.vue:958-959`) | **Blijft draaien** zolang de backend proces-routes bestaan; breekt (met nette toast, geen crash) als die óók weggaan |
| "Via proces"-ingang op het beginscherm | `procesKaartIngang.js:18-31` (`api.processen.*`), UI `KaartBeginscherm.vue:324-328` | **Blijft draaien** zolang backend proces-routes bestaan — maar dit is een **proces-ingang** die de gebruiker terugbrengt bij het thema dat we verbergen |
| "Bekijk op kaart" vanaf **proces-detail** | `ProcesDetail.vue:159-164` | **Verdwijnt uit beeld** — de host-pagina is weg. De **component**-variant (`ComponentDetail.vue:324`) blijft |
| "Waarvoor gebruiken we het" (componentdetail) → procesnaam-links | `ComponentProcessenSectie.vue:234,250` | **Blijft in beeld, maar de links worden doelloos** (route weg) |
| "Processen"-sectie (organisatiedetail) → proces-links | `PartijProcessenSectie.vue:61` | **Blijft in beeld, links doelloos** |
| Kaart "Open proces →" | `LandschapskaartView.vue:1492` (`router.push({name:'proces-detail'})`) | **Blijft in beeld, navigatie doelloos** |
| Seed (6 processen + 8 koppelingen) | `dev_seed_testdata.py:1544-1607` | **Blijft ongewijzigd** — **geen reseed nodig**; verbergen is UI-only, geen schema/data |
| Alle backend-tests (model/API/RBAC) | `modules/bwb_ontvlechting/backend/tests/test_*proces*` | **Moeten blijven** — geen ervan toetst een frontend-ingang |

### 2.4 Testdekking — wat beweegt mee, wat moet blijven

- **UI-ingang (beweegt mee):** `ProcesLijst.test.js`, `ProcesDetail.test.js`, `ProcesDiagram.test.js`, `OnderliggendeProcessenSectie.test.js`, `procesFocusSet.test.js`, `procesKaartIngang.test.js`, `KaartBeginscherm.test.js` (de "Via proces"-test `:198-209`).
- **Grensgeval (raakt, maar host-scherm blijft):** `PartijProcessenSectie.test.js`, `PartijDetail.test.js:106-108`, `ComponentDetail.test.js:78-81,403`, `ComponentFormulier.test.js:12-13,27-28`, `BedrijfsfunctieLijst.test.js:43,58,415,427` — deze houden route-stubs `proces-lijst`/`proces-detail` nodig zolang die links blijven staan.
- **Model/leeslaag (moeten blijven):** `LandschapskaartView.test.js` (proceslaan-ordening, ring "Processen", vervult-edges), `kaartLayout.test.js:80-92`, `api.filter.test.js:107-110`, `meervoudBoom.test.js`; backend: alle `test_proces_adr042.py` / `test_procesvervulling_adr042.py` / `test_rollup_adr042.py` / `test_landschapskaart_proces.py`.

### 2.5 "Verborgen ≠ verwijderd" — de opties per plek, mét gevolg (geen keuze gemaakt)

| Plek | Opties die de code toelaat | Gevolg (deep-links / bewaarde staat / kaart) |
|---|---|---|
| **Nav-item "Processen"** | (a) `v-if="false"`/verwijderen · (b) achter een rol-slot | (a) helemaal weg; (b) alleen voor bepaalde rollen — maar de MVP-lijn is "één verhaal, één plek", dus rol-gate lost de dubbelzinnigheid niet op |
| **Routes `proces-lijst`/`proces-detail`** | (a) route verwijderen · (b) route behouden zónder nav-ingang · (c) route behouden achter rol-guard | (a) alle 7 inkomende `proces-detail`-links worden doelloos (harde 404/redirect); (b) deep-links + kaart "Open proces →" blijven werken maar zijn onvindbaar in de UI; bewaarde `lijst-state:proces-lijst` wordt onbereikbaar |
| **"Waarvoor gebruiken we het" (componentdetail)** | (a) sectie laten staan (proces) · (b) vervangen door de functie-sectie · (c) beide tonen | Bepaalt of de proces-links hier doelloos worden. Botst met §3-titelkwestie: dezelfde vraag, ander anker |
| **Subveld "Proces" op componentformulier** | (a) veld verwijderen · (b) laten staan | Laten staan = een schrijf-ingang naar een verborgen thema |
| **Organisatie-"Processen"-sectie** | (a) laten (afgeleid, read-only) · (b) verbergen | Laten = proces-links worden doelloos; verbergen = een afgeleid inzicht verdwijnt |
| **Kaart-proceslaan + "Via proces" + "Open proces →"** | (a) laan + ingangen behouden (opdracht-randvoorwaarde) · (b) laan behouden, proces-ingangen (Via proces / Open proces / dubbelklik-inzoom) eraf · (c) laan óók uit (ADR-043 besluit 8) | Dit is dé kernkeuze — zie §4.1 en §5.1. (a) houdt proces zichtbaar op de kaart terwijl het register weg is; (c) volgt de ADR maar sloopt wat de randvoorwaarde wil behouden |

---

## §3 — Functie-kant: aanwezig / ontbrekend / dubbel (deel 3)

### 3.1 De leesregel bestaat per plek — de omgekeerde richting (per component) ontbreekt

**Aanwezig (gate 2/3, geland V042):**
- `dekking_overzicht` (`functievervulling_service.py:351-478`) — de gedeelde afleiding *"welke componenten dragen déze plek"*, met verdringing (fijn wint bij tonen), `grof_totaal_plekken`/`grof_geldt_op`. Route `GET /functievervullingen/dekking` (`routes/functievervulling.py:32-38`).
- `plek_standen` (`:481-554`) — de **vier standen** (`gat` / `via_boven` / `hier` / `niets`) + tellers, **kijkt OMHOOG**. Route `GET /functievervullingen/standen` (`:41-47`). Bevinding "geen systeem": `POST /geen-systeem`; oordeel: `PATCH /{id}/oordeel`.
- API-client: `api.functievervullingen.dekking`/`.standen`/`.maak`/`.geenSysteem`/`.zetOordeel`/`.verwijder` (`api.js:427-436`).

**Ontbreekt — precies wat gate 4 op het component nodig heeft:**
- Er is **geen** `lijst_voor_component` / `functies_voor_component` op `functievervulling_service.py` (proces heeft die wél: `procesvervulling_service.py:240`). De index `ix_functievervulling_tenant_component` (`models.py:801`) is voorbereid; het **leespad niet**.
- Er is **geen** route per component en **geen** frontend-sectie: `ComponentDetail.vue` mount geen functie-sectie.
- → De richting *"op welke bedrijfsfuncties/plekken hangt dít component"* bestaat **nergens**. Dat is het leespad dat gate 4 moet toevoegen om de waarvoor-vraag op het component in functies te beantwoorden.

### 3.2 Waar de consultant vandaag koppelt — en hoe dat afwijkt van het proces-veld

Koppelen aan een functie gebeurt **alleen in de functieboom** (`BedrijfsfunctieLijst.vue:546-613`), niet op het component. Scope: `api.componenten.lijst({ondersteunt_werk:true})`, backend hard afgedwongen (`functievervulling_service.py:106-110`, 422 `COMPONENT_ONDERSTEUNT_GEEN_WERK`). Werkwoord: **kaal** ("ondersteunt").

| Aspect | Proces-koppeling (`procesvervulling`) | Functie-koppeling (`functievervulling`) |
|---|---|---|
| **Betekenis** | tripel `(component, proces, applicatiefunctie)` — mét werkwoord | kaal adres `(component, functie, ouder-functie)` — géén werkwoord |
| **Verplichting** | applicatiefunctie **verplicht** (`models.py:743` NOT NULL) | koppeling optioneel; oordeel optioneel (`models.py:836`) |
| **Meervoud** | n per component; UNIQUE op tripel (`models.py:726-729`) | n per component; partiële UNIQUE grof/fijn (`models.py:781-788`) |
| **Plek van registratie** | op **component** (detail + aanmaakformulier) **én** op **proces-detail** — twee ingangen | **alleen** in de functieboom — géén ingang op het component |
| **Koppelbare typen** | **élk** componenttype (component-breed) | alleen `ondersteunt_werk=true` (ADR-045) |
| **Taal** | "Waarvoor gebruiken we het" / "vervult *applicatiefunctie* in …" | "ondersteunt" / "geldt overal" / "alleen op deze plek" |

**Kernbotsing:** de titel **"Waarvoor gebruiken we het"** is nú door de **proces**-sectie bezet (`ComponentProcessenSectie.vue:215`). Gate 4 stelt exact dezelfde vraag, maar met bedrijfsfuncties als anker — die twee kunnen niet allebei ongemarkeerd dezelfde kop dragen.

### 3.3 Gedeelde bouwstenen — al geconvergeerd vs nog dubbel

**Al hergebruikt door de functie-as (convergentie geslaagd):**
- Diagram: de functieboom gebruikt de **gegeneraliseerde `ProcesDiagram`** (`BedrijfsfunctieLijst.vue:41,912-932`, functie-taal via `DIAGRAM_TEKSTEN`, "Open functie →"). Geen apart functie-diagram.
- Boom-afleiding/focus/inzoom/history: één keer in `procesBoom.js` + `ProcesDiagram.vue` — de functie-as erft ze gratis.
- Rij-acties/dialogen/banner: gedeelde `RijActies`/`BevestigVerwijderDialog`/`MeldingBanner`.

**Nog dubbel (convergentie-kandidaten, n≥2 — niet uitvoeren):**
1. **Twee service-lagen met identieke helpers.** `functievervulling_service.py` en `procesvervulling_service.py` dragen elk hun eigen `_tenant_uuid`, `_element_type`, `_lees_een` (component-naam/typelabel-verrijking). Identiek recept, twee kopieën.
2. **Twee near-duplicate sectie-componenten.** `ComponentProcessenSectie.vue` (component-zijde) en `ProcesComponentenSectie.vue` (proces-zijde): zelfde toevoeg/bewerk/verwijder-structuur, zelfde 409-banner. Een **functie-sectie** voor gate 4 zou een **derde** kopie worden tenzij geabstraheerd.
3. **Het `gapIds`-kanaal.** De functieboom laat het diagram-gap-kanaal **bewust leeg** (`BedrijfsfunctieLijst.vue:908-911`, "vrij voor gate 3"); het functie-gapsignaal (`plek_standen`) toont vandaag alleen in de boomrijen + `WerkvoorraadPlekView`, niet in het diagram. Convergentie-kandidaat: `plek_standen` → `gapIds`-prop van het gedeelde diagram.
4. **Twee tegengestelde gap-semantieken.** Proces-gap kijkt **omlaag** (subboom "geen ondersteunend systeem"); functie-gap kijkt **omhoog** (`plek_standen`, `:485-488`). Beide heten "gap", geen gedeelde afleiding.

### 3.4 Adversariële checkvraag — wat een gate-4-bouw stilzwijgend zou beslissen

De code legt deze onbesliste keuzes bloot (alleen blootleggen — niet beslissen):

1. **Bestaande proces-registraties.** `Procesvervulling` en `Functievervulling` zijn twee losse tabellen zonder brug; de proces-sectie blijft gemount (`ComponentDetail.vue:457`). Verlegt gate 4 "Waarvoor gebruiken we het" naar functies, dan moet stilzwijgend beslist worden of de **proces-sectie blijft staan (twee secties), vervangen wordt, of onbereikbaar wordt**.
2. **Component mét proces maar zónder functie is een geldige toestand.** Niets koppelt de twee; geen constraint dwingt een functie af. Wordt dat een zichtbaar gat op componentdetail? Vandaag is er geen signaal (de gap-afleiding is puur plek-gericht).
3. **Functie-koppeling is optioneel.** Leeg = legitiem "nog niet vastgelegd" — consistent met de bestaande lijn, maar niet expliciet besloten voor de component-ingang.
4. **Meervoud is ongelimiteerd.** Eén component kan grof + meerdere fijne koppelingen dragen; een component-leespad toont dus een **lijst** (n plekken), niet één veld — inclusief hoe grof/fijn/verdrongen daar wordt samengevat (die aggregatie leeft nu alleen plek-gericht in `dekking_overzicht`).
5. **Tweede schrijf-ingang.** De enige koppel-ingang is de functieboom. Koppelen vanaf componentdetail introduceert een **tweede** schrijf-ingang — de backend POST accepteert het al (`functievervulling.py`), maar het raakt de "één plek van registratie"-lijn.
6. **`geen_systeem`-bevindingen hangen aan de plek, niet aan een component** (`component_id IS NULL`, XOR-CHECK `models.py:804-807`). Een component-gericht leespad ziet ze per definitie niet — de asymmetrie is impliciet.

---

## §4 — Open keuzes vóór de bouw (genummerd, in gebruikerstaal — geen advies, geen voorkeur)

1. **Blijft "proces" op de kaart staan, of gaat het er ook af?** ADR-043 besluit 8 zegt: menu, ingangen **én de proceslaan op de kaart** weg. De randvoorwaarde in deze opdracht zegt: de proceslaan blijft als read-only verrijking. Dat kan niet allebei. *(a) Laan + proces-ingangen op de kaart behouden; (b) laan behouden maar de proces-ingangen "Via proces" / "Open proces →" / dubbelklik-inzoom eraf; (c) de laan óók verbergen.* — dit is de zwaarste knoop (zie §5.1).
2. **Waar landt "waarvoor gebruiken we dit systeem?" op het componentdetail — en wat gebeurt met de bestaande proces-sectie die die vraag nu al beantwoordt?** Blijft de proces-sectie staan naast een nieuwe functie-sectie, vervangt de functie-sectie haar, of wordt de proces-sectie onbereikbaar? En wie krijgt de kop "Waarvoor gebruiken we het"?
3. **Wat gebeurt er met het subveld "Proces" op het component-aanmaakformulier?** Verdwijnt het bij het verbergen, of blijft de gebruiker daar processen koppelen aan een thema dat verder verborgen is?
4. **Blijft de afgeleide "Processen"-sectie op het organisatiedetail?** Het is een read-only afgeleid inzicht dat vandaag naar proces-detail linkt; bij verbergen worden die links doelloos.
5. **Mag de consultant vanaf het componentdetail koppelen aan een functie, of blijft koppelen uitsluitend in de functieboom?** (Eén plek van registratie vs. twee ingangen — de proces-as had er twee, de functie-as nu één.)
6. **Behouden we de routes `proces-lijst`/`proces-detail` zonder nav-ingang (zodat deep-links en kaart-"Open proces →" blijven werken), of halen we de routes helemaal weg (zodat alle inkomende links hard doodlopen)?**

---

## §5 — Discrepanties tussen skills/ADR-043 en de code

1. **ADR-043 besluit 8 ↔ de opdracht-randvoorwaarde (de zwaarste).** ADR-043 (`:193-197`) besluit dat het procesregister "volledig uit beeld in de MVP" gaat — **"menu, ingangen én de proceslaan op de kaart"** — met als reden dat "de proces-ingangen op de kaart zouden doodlopen". De randvoorwaarde in déze opdracht (en het projectgeheugen: "ARCHITECTUUR.LEZEN niet slopen") wil de proceslaan juist **behouden** als read-only verrijking. **Code-stand:** de proceslaan draait onder `ARCHITECTUUR.LEZEN` en is een echte read-only verrijking (§2.1), dus technisch kan hij blijven — maar dat is een **koerswijziging t.o.v. ADR-043 besluit 8**, geen uitvoering ervan. Vereist een expliciet besluit (§4.1); niet stilzwijgend één kant op bouwen.
2. **ADR-043 fasering stap 6 ("procesregister verbergen: menu/route/ingangen uit; model blijft intact") ↔ de losse inkomende links.** De code kent **7 plekken buiten het register** die naar `proces-detail`/`proces-lijst` linken (componentdetail, organisatiedetail, kaart, en de proces-secties onderling — §1 rij 7, §2.3). "Menu/route uit" laat die links doelloos achter; de ADR benoemt dit neveneffect niet. Feit, geen conflict — maar het is werk dat de fasering impliciet aanneemt.
3. **Titel-botsing (skill likara-ux ↔ code).** ADR-043/de gate-2-lijn beschrijven het component dat straks "waarvoor gebruiken we dit" in functies beantwoordt; de code heeft die kop (`"Waarvoor gebruiken we het"`) al aan de **proces**-sectie toegewezen (`ComponentProcessenSectie.vue:215`). Geen fout in de bouw — maar de vraag "welke sectie krijgt die kop" is onbeslist (§4.2).
4. **Stale docstring (buiten scope, gemeld).** `routes/functievervulling.py:4-6` beweert dat DELETE op `VERWIJDEREN` guardt; de code (`:91`) guardt op `WIJZIGEN` (registratie-feit, ADR-050, `rbac.py:235-267`). Documentatie-drift, raakt gate 4 niet.
5. **Geen datakwestie.** De seed (6 processen + 8 procesvervullingen, `dev_seed_testdata.py:1544-1607`) en het schema blijven ongewijzigd; verbergen is UI-only. **Reseed nodig: nee.** (Ontwikkelmodus, alleen testdata.)

---

**Read-only checkpoint klaar — niets gewijzigd.**
