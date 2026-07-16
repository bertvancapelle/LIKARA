# Feitenrapport — gate 4 slice 3: sloop-grens, schema-vraag, seed-/organisatie-feiten

**Build:** V042 · **Commit:** `254f905` (slice 1 gecommit; slice 2 + OPVOLGPUNTEN ongecommit) · **Datum:** 2026-07-15 · **Modus:** READ-ONLY checkpoint
**Meetbron:** codebase (canoniek) + het GEMMA-bronbestand + de dev-seed. Geen wijziging, geen migratie, geen commit.

> Elke uitspraak draagt een **vindplaats** (`bestand:regel`) of een **telling uit de code**. Waar de code
> afwijkt van een aanname (PNA-sessie, ADR, opdracht): gemeld in **§5**, code wint.

---

## §0 — Samenvatting in gebruikerstaal

**Wat weg kan:** het hele procesregister-scherm (lijst, detail, secties), zijn menu-item, routes en
api-methodes, plus de backend-proces-routes en -services — die zijn na slice 2 door **niemand** meer
gebruikt. **Wat blijft (erfstuk):** het proces-**model** (de tabellen), `ProcesDiagram.vue` en
`procesBoom.js` — die worden door de **bedrijfsfunctie-as** hergebruikt; en het proces-model wordt nog
door de generieke architectuur/AMEFF-lijst gelezen. **"Verbergen ≠ slopen" geldt dus voor het model,
niet voor de route.**

**Migratie nodig? — NEE.** De functie-as erft niets van proces en heeft geen proces-tabel/-kolom nodig;
onder de ADR-043-lijn blijft het model staan → geen schema-stap, alembic head blijft **0070**. De reseed
is **puur data** (de seed maakt gewoon geen proces-rijen meer). Een migratie zou alleen nodig zijn als je
de tabellen bewust dropt — dat ontraadt "verbergen ≠ slopen", en de enum-waarde `'proces'` is bovendien
niet te droppen.

**Hoeveel organisaties echt? — 8, niet 4.** Intern: BvoWB, RID Rivierenland. Externe gemeenten: Tiel,
Culemborg, West Betuwe. Burger-organisaties: Burgers Tiel, Burgers Culemborg, Burgers West Betuwe.

**Gat-per-organisatie een feit? — NEE.** Een functievervulling draagt **geen organisatie**; de functie-as
is tenant-breed. "Systeem X dekt Toezicht **voor West Betuwe**" is vandaag niet registreerbaar — hooguit
een afleiding (organisatiegebruik × functievervulling), en dat vergt een nieuw feit, niet deze slice.

---

## §1 — De sloop-grens (weg / erfstuk / twijfel)

### 1a. Frontend

| Item | Vindplaats | Status |
|---|---|---|
| `ProcesLijst.vue` (register-scherm) | `views/ProcesLijst.vue` | **weg** |
| `ProcesDetail.vue` (+ "Bekijk op kaart") | `views/ProcesDetail.vue:116-129,172` | **weg** |
| `ProcesComponentenSectie.vue` | `views/…` (alleen door ProcesDetail) | **weg** |
| `OnderliggendeProcessenSectie.vue` | `views/…` (alleen door ProcesDetail) | **weg** |
| `PartijProcessenSectie.vue` (op organisatiedetail) | `PartijDetail.vue:21,362` | **weg** (raakt PartijDetail 2 regels; PartijDetail blijft) |
| `ComponentProcessenSectie.vue` | nergens meer geïmporteerd (al wees na slice 1) | **weg** |
| Nav-item "Processen" | `AppLayout.vue:129-136` | **weg** |
| Routes `proces-lijst`/`proces-detail` + lazy-imports | `router/index.js:34-35,140-141`; labels `useTerugNavigatie.js:22-23` | **weg** |
| Api-methodes `processen`/`procesvervullingen`/`partijen.processen` | `frontend/src/api.js:403-422,222-223` | **weg** |
| `procesZoek.js` (`maakProcesZoeker`) | alleen door ComponentProcessenSectie | **weg** |
| `procesKaartIngang.js` (`bouwProcesKaartHandoff`) | ProcesDetail/ProcesLijst + dode kaart-hook | **weg** |
| **`ProcesDiagram.vue`** | door `BedrijfsfunctieLijst.vue:41,912-932` (functie-diagram) | **BLIJFT (erfstuk)** |
| **`procesBoom.js`** (hele module) | `meervoudBoomStructuur` = functieboom (`BedrijfsfunctieLijst:40`); `procesBoomLayout`/`procesFocusSet`/… via ProcesDiagram | **BLIJFT (erfstuk)** |
| Stale comments | `ComponentFormulier.vue:8`, `ComponentDetail.vue:39` | **weg (opruim, geen runtime)** |

**De 18 dode proces-hooks in `LandschapskaartView.vue` — twee groepen:**
- **Groep A — echt nooit-vurend (veilig weg):** `import procesBoomLayout` (`:22`) + `_procesBoomLayout`
  (`:2135-2142`); `import bouwProcesKaartHandoff` (`:23`); `zoomInOpProces` (`:955-983`, roept `api.processen.rollup`
  + `api.procesvervullingen.lijst`); `openViaProces` (`:987-999`) + `_pasProcesIngangToe` (`:1001-1010`);
  `_inzoomProcesIds` (`:925-950`) + `procesInzoom` (`:921`, ook in history `:1373,1386,1432`); de proces-knoop-popup/
  -styling (`_PROCES_PIJL`, `procesGap`-attr, `node[?procesGap]`-selector); contextmenu-tak `case 'proces'`
  (`:1492` → `proces-detail`).
- **Groep B — nog aan een LEVEND pad (samen met ProcesDetail/ProcesLijst slopen):** `procesIngang` (`:865`) +
  herkomst-chip (`:2966-2974`) + mount-handoff-tak (`:2789-2794`, gevoed door `zetKaartHandoff` in
  ProcesDetail/ProcesLijst) + `_zetProcesFocus` (`:881-888`) + `wisProcesIngang` + `toonHeleBoom` +
  `popupToonLandschap`. **Deze vuren tot slice 3 de "Bekijk op kaart"-handoff van ProcesDetail/ProcesLijst
  weghaalt** — dus samen ontknopen, niet los. `_centreerNaLayoutId`/`_selectieZonderDim` zijn algemene
  centrering-/dim-mechanieken → **laten staan**, alleen de proces-callsites eruit.

**Resterende `proces-detail`/`proces-lijst`-links (breekt er iets bij route-verwijdering?):** alle live-links
zitten in de te-slopen proces-schermen zelf; buiten de proces-cluster alleen (a) de dode kaart-contextmenu-tak
(`:1492`, vuurt nooit — mee-weg met de route) en (b) `ProcesDiagram.vue:62` prop-default `detailRoute:'proces-detail'`
(alleen ProcesLijst leunt erop; `BedrijfsfunctieLijst` geeft `:detail-route="null"` → cosmetisch naar `null`).
`GebruikteApplicatiesSectie.vue:72` schrijft óók een kaart-handoff maar **zonder** `procesIngang` → onafhankelijk.
**Niets breekt** bij het verwijderen van de routes.

### 1b. Backend

| Item | Vindplaats | Status |
|---|---|---|
| `routes/proces.py` (7 endpoints) + `routes/procesvervulling.py` (6) | prefix `/processen`, `/procesvervullingen` | **weg** (geen consument na slice 2) |
| `services/proces_service.py`, `procesvervulling_service.py`, `applicatiefunctie_catalog.py` | — | **weg** (puur proces; geen functie-as-/kaart-hergebruik) |
| `/partijen/{id}/processen` + `processen_voor_organisatie` | `routes/partij.py:27,30,106`; `procesvervulling_service` | **twijfel** — proces-afhankelijk, maar zit fysiek in de partij-route; hoort bij de proces-sloop |
| **`Proces`/`Procesvervulling`/`ApplicatiefunctieOptie`-modellen** | `models.py:667-703,706-744,1264-1282` | **BLIJFT (erfstuk)** — verbergen ≠ slopen; `Proces` wordt nog gelezen door `architectuur_service.py:38,193,222,237` (de generieke ArchiMate/AMEFF-lijst) |
| `proces.ouder_id` (self-FK, RESTRICT) | `models.py:694-703` | **erfstuk van het proces-model** (dood voor de functie-as, levend voor de tabel) — blijft als het model blijft |
| RBAC `Entiteit.PROCES`/`PROCESVERVULLING` + matrix + categorie-sets | `rbac.py:52,55,164,166,237,251` | **beslispunt** — bij verbergen: laten staan; bij slopen: entiteit + matrix + `REGISTRATIE_FEIT_ENTITEITEN` + `LANDSCHAPSOBJECT_ENTITEITEN` **samen** weg, anders faalt de bron-scan-test `test_rollengrens_adr050` |
| Audit-allowlist `"proces"`,`"procesvervulling"` | `audit.py:71-72` | **beslispunt** (idem — samen met RBAC) |
| `platform_init.py` / 89 checklistvragen | `platform_init.py:52-54,77-78` | **blijft** — raakt proces niet; alleen de losse `seed_applicatiefunctie`-catalogus (geen proces-rijen) |

**Backend-consumptie na slice 2 (bevestigd):** `landschapskaart_service.py` importeert **geen** `Proces`/
`proces_service`/`procesvervulling_service` meer (alleen de comment `:494` "proceslaan HIERMEE VERVANGEN, G1").
`functievervulling_service.py` + `bedrijfsfunctie_service.py` raken proces **nergens** aan (de functieboom leeft in
`_aggregatie_paren` op aggregation-relaties; de leeslaag in `dekking_overzicht`/`plek_standen`). De as is **kaal** —
géén applicatiefunctie → `applicatiefunctie_catalog` is puur proces.

---

## §2 — De schema-vraag (vastgesteld, niet gekozen)

**Feiten:**
1. Het zijn **drie eigen tabellen**, geen kolommen op gedeelde tabellen: `proces` (`models.py:682`),
   `procesvervulling` (`:724`), `applicatiefunctie_optie` (`:1273`, platform-tabel).
2. `proces.ouder_id` is een kolom **op de `proces`-tabel zelf** (`:703`, self-FK RESTRICT + CHECK) — géén
   orphan op `element` of een andere gedeelde tabel. Integraal deel van het proces-model.
3. Op `element` kwam alléén de enum-waarde `'proces'` (`0056_adr042_elemtype_proces.py:23-27`). **PostgreSQL kan
   een enum-waarde niet droppen** (`0056:29-32`) → bij een echte sloop blijft `'proces'` sowieso staan (of vergt
   type-hercreatie). Dit versterkt "verbergen ≠ slopen" op DB-niveau.
4. Head = `0070_adr051_gapsignaal`; de proces-tabellen komen uit `0056`–`0059`; sinds 0059 is er niets aan het
   proces-schema veranderd.

**Vaststelling (geen keuze):**
- **Onder "verbergen ≠ slopen" (ADR-043 G10; model/tabellen blijven, alleen UI/routes weg):** **GÉÉN migratie
  nodig.** Geen tabel/kolom/constraint gedropt of gewijzigd; head blijft **0070**. Bijkomend: `Proces` wordt nog
  door `architectuur_service.py` gelezen → het model kán niet zonder meer weg. **Reseed = puur data** (§3.3): de
  dev-seed maakt geen proces-/procesvervulling-rijen meer (sectie 15 vervalt); de tabellen bestaan leeg voort.
- **Alléén als slice 3 de tabellen bewust dropt:** een **drop-migratie (0071)** met bijkomende kosten: de
  niet-droppbare enum-waarde `'proces'`, en `architectuur_service` + RBAC/audit-entries moeten in dezelfde slag mee
  (anders faalt `test_rollengrens_adr050`).

**Harde conclusie:** de modeldefinities dwingen **niets** af — er is geen schema-verplichting die uit de functie-as
voortkomt. Migratie ja/nee hangt **volledig** af van de sloop-vs-verberg-keuze (§4), niet van technische noodzaak.

---

## §3 — Organisatie- + seed-feiten (de echte lijst)

### 3.1 Organisatie-inventarisatie (canonieke seed = `_seed_bvowb_scenario`, `dev_seed_testdata.py:891-1712`)

**8 organisaties** (`aard=organisatie`) — de PNA-lijst was onvolledig:

| Organisatie | Scope | Vindplaats |
|---|---|---|
| **BvoWB** (eigen organisatie / dienstenprovider) | intern | `:945` |
| **RID Rivierenland** (tweede interne org — echte keuze op het gebruikerscherm) | intern | `:948` |
| **Gemeente Tiel** | extern | `:949` |
| **Gemeente Culemborg** | extern | `:950` |
| **Gemeente West Betuwe** | extern | `:951` |
| **Burgers Tiel** | extern | `:1415` |
| **Burgers Culemborg** | extern | `:1415` |
| **Burgers West Betuwe** | extern | `:1415` |

Eén **tenant** (`DEV_TENANT = 11111111-…`, `:95`); organisaties leven als partijen daarbinnen. *(Niet meegeteld:
ketenpartners + leveranciers = `aard=externe_partij`; afdelingen = `aard=organisatie_eenheid`. En:
`_seed_aanvulling_d`/`_seed_technische_laag`/`seed_landschapskaart_demo` worden door `main()` **niet** aangeroepen —
"Gemeente Veldendam"/"Gemeente BWB" zijn géén canonieke seed-data.)*

### 3.2 Draagt een functievervulling een organisatie? — **NEE**

`Functievervulling` (`models.py:754-845`) kolommen: `component_id` (nullable), `functie_id`, `ouder_functie_id`
(nullable), `geen_systeem`, `oordeel`, `toelichting`, `verklaard_door_*` + tenant/timestamps. **Geen
`organisatie_id`.** De as is bewust kaal (`:757-762`).

→ **"Systeem X dekt functie Y voor organisatie Z" is vandaag geen registreerbaar feit.** De organisatie-dimensie
loopt via **`Organisatiegebruik`** (`models.py:458`, `UNIQUE(tenant, organisatie, applicatie)` `:478`) — "wie
gebruikt welke **applicatie**", op componentniveau, **niet** op functieniveau. Een "gat bij West Betuwe op functie
Y" is dus hooguit een **afleiding** (organisatiegebruik × functievervulling, beide op componenten), geen op te slaan
expliciet feit.

### 3.3 Huidige seed-stand op functie-vlak

- **Bedrijfsfuncties (blok 16, `:1610-1712`):** echte GEMMA-import (`referentiemodel_import_service.voer_uit`, `:1666`)
  — **297 functies + 302 plaatsingen, 8 wortels, 1 referentiemodel** (geverifieerd tegen
  `GEMMA_release_2026-07-01.xml` + `test_referentiemodel_import_gate1b.py:62-64`). Plus 2 demo-functies: een
  **vervallen** "Regionale samenwerking" (`:1653-1662`, onder "Sturing") en een **eigen** "Datagedreven werken"
  (`:1701-1710`, onder "Ondersteuning"). Seed-telling: **299 functies, 304 plaatsingen**.
- **Functievervullingen: NUL** (grep leeg; `telling`-dict `:910-914` kent de sleutel niet). **Geen enkele** van de vijf
  MVP-standen komt in de seed voor: niet grof, niet fijn-verdrongen, niet gat, niet via_boven, niet
  systeem-zonder-functie. De functie-as staat er (boom), maar heeft **nul component↔functie-koppelingen** → op een
  verse database is gate 2/3/4 op de functie-as onzichtbaar.
- **Proces (blok 15, `:1544-1608`):** **6 processen + 8 procesvervullingen** (Vergunningverlening→Aanvraag
  behandelen→Besluit vastleggen; Bezwaar behandelen bewust ondersteuningsloos; Burgerzaken→Verhuizing verwerken).

### 3.4 Meervoudige voorouder in de GEMMA-seed — **de path-expansie-casus komt NIET voor**

**7 functies met meerdere ouders** (geverifieerd tegen de XML + `test_referentiemodel_import_gate1b.py:73-76`):
Handhaving (4), Toezicht (4), Autorisatievaststelling (3), Identiteitvaststelling (3), Afrekening (2),
Burgerinitiatieven facilitering (2), Burgerlijke stand diensten (2). **Maar alle 7 zijn bladeren (0 kinderen).**
→ Er staat in de geïmporteerde GEMMA-boom **niets ónder** een meervoudig-geplaatste functie. De slice-2-casus
(herhaalde cue onder een meervoudige voorouder) **komt in GEMMA niet voor**. Om die casus in de seed te tonen is een
**eigen** functie nodig, geplaatst ónder een meervoudig-geplaatste functie (of een eigen functie op twee plekken mét
een kind). Deterministisch vastgesteld, geen aanname.

### 3.5 Test-rimpel bij een seed-herschrijving

- **Frontend: geen rimpel** — de 94 `*.test.js` gebruiken eigen mocks (`tests/helpers/partijMock.js`); namen als
  "Zaaksysteem" zijn lokale fixtures, onafhankelijk van de dev-seed.
- **Backend: ~13 testbestanden raken de seed; ordegrootte ~40-60 seed-afhankelijke asserties.**
  - **Harde kern (lezen het seed-bestand direct → bewegen gegarandeerd mee):** `test_dev_seed_aanvulling_d.py`,
    `test_seed_email_test_domein.py`, `test_adr045_ondersteunt_werk.py` (`test_seed_stand_vijf_true_drie_false`,
    `test_dode_seed_functie_opgeruimd`), `test_checklist_dragend_fix_f6.py` (dev-reseed-duurzaamheid live).
  - **Naam-/aantal-gekoppeld (string-matches, niet per test bewezen als runtime-koppeling):** o.a.
    `test_procesvervulling_adr042.py`, `test_proces_adr042.py`, `test_rollup_adr042.py`, `test_registratiegaten.py`,
    `test_dashboard_service.py`, `test_functievervulling_component_gate4.py`. *Let op:* de proces-tests
    (`test_proces_adr042`, `test_procesvervulling_adr042`, `test_rollup_adr042`) bewegen sowieso mee met de
    **sloop** van de proces-services (§1b), los van de seed.

---

## §4 — Open ontwerpvragen voor het seed-verhaal (genummerd, gebruikerstaal — geen advies, geen voorkeur)

1. **Verbergen of slopen — hoe ver gaat slice 3?** Onder "verbergen ≠ slopen" blijven de proces-**tabellen** staan
   (geen migratie); alleen scherm/routes/services weg. Of wil je de tabellen bewust droppen (dan een migratie, mét de
   niet-droppbare enum-waarde `'proces'` en RBAC/audit/architectuur als bijkomende kosten)? *(Bepaalt migratie ja/nee.)*
2. **Blijft de RBAC-/audit-classificatie van proces staan?** Bij verbergen: laten staan (harmloos, model bestaat nog).
   Bij slopen: entiteit + matrix + de twee categorie-sets + de audit-allowlist moeten samen weg, anders faalt de
   rollengrens-bron-scan.
3. **Wat gebeurt met de afgeleide "Processen"-sectie op het organisatiedetail** en de partij-ingang
   `/partijen/{id}/processen`? Mee-weg met de proces-as, of los beoordeeld (ze hangt fysiek aan de partij-route)?
4. **Wil het seed-verhaal een gat/dekking per organisatie tonen?** Dat kán vandaag niet als feit (functievervulling
   draagt geen organisatie). Óf het verhaal is **tenant-breed** ("het landschap van de BvoWB-samenwerking, niet per
   gemeente"), óf een per-organisatie-dekking is een **nieuw feit** (nieuwe dimensie op de koppeling) — buiten deze
   slice. Welke kant op?
5. **Wil het seed-verhaal de slice-2 path-expansie/herhaalde-cue tonen?** GEMMA levert die casus niet (de 7
   meervoudige functies zijn bladeren). Om 'm te tonen moet de seed een **eigen** functie onder een meervoudig-
   geplaatste functie zetten. Wel of niet demonstreren?
6. **Welke van de vijf standen zet de seed neer, en op welke functies/systemen?** Grof ("geldt overal"),
   fijn-verdrongen (een ander systeem op één plek), gat ("nog geen"), via_boven (koppeling hoog in de boom → cue
   eronder), systeem-zonder-functie (het werkvoorraad-gat). Op welke GEMMA-functies + welke seed-componenten
   (Zaaksysteem/DMS/…) hangt elk?
7. **Blijft het proces-seedblok (sectie 15) staan of vervalt het?** De proceslaan is van de kaart; het register gaat
   uit de UI. Proces-rijen in een verborgen register seeden heeft geen zichtbaar effect meer — vervalt het blok, of
   blijft het voor eventuele latere terugkeer van het procesregister (ADR-043 "de verdieping die terugkomt")?

---

## §5 — Discrepanties tussen skills/ADR's en de code

1. **"18 dode proces-hooks" (slice-2-rapport) ↔ de code:** niet alle 18 zijn nooit-vurend. **Groep B**
   (`procesIngang`/herkomst-chip/mount-handoff) wordt **nog gevoed** door de "Bekijk op kaart"-handoff van
   ProcesDetail/ProcesLijst en vuurt dus tot slice 3 die schermen sloopt. Ze moeten **samen** sneuvelen, niet los.
2. **PNA-organisatielijst (4-5 namen) ↔ de seed:** het zijn er **8**. RID Rivierenland (tweede interne org) en Burgers
   West Betuwe ontbraken in de mondelinge lijst; "Gemeente Veldendam"/"Gemeente BWB" uit niet-aangeroepen
   seed-functies zijn géén canonieke data.
3. **Aanname "gat-per-organisatie" ↔ het model:** `functievervulling` draagt **geen** organisatie — de aanname dat
   dekking per gemeente een feit is, klopt niet; het is een afleiding via organisatiegebruik (componentniveau).
4. **Opdracht "backend proces-endpoints opruimen (G10)" ↔ "verbergen ≠ slopen":** de **routes + services** kunnen weg
   (geen consument), maar het **model** blijft (erfstuk; `architectuur_service` leest `Proces`). "Opruimen" = de
   ingang, niet de tabel. Geen conflict, wel een scherpe grens (per ongeluk het model meeslopen = de architectuur-
   lijst breken).
5. **Ontwerpcheckpoint "meervoud lokt de path-expansie uit" ↔ GEMMA:** klopt conceptueel, maar de **huidige**
   GEMMA-bron heeft geen kind onder een meervoudige functie → de casus is er alleen met een eigen seed-functie.

---

**Read-only checkpoint klaar — niets gewijzigd.**
