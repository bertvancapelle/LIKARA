# Feitenrapport — bedrijfsfunctie-as (ADR-043, bouw-fasering stap 1)

| | |
|---|---|
| **Opdracht** | LI039-checkpoint-bedrijfsfunctie-as (read-only feitencheck) |
| **Datum** | 2026-07-12 |
| **Basis** | Build V039, commit `b46f4b0`, werktree schoon, alembic head `0059_adr042_procesvervulling` |
| **Modus** | Uitsluitend gelezen; niets gewijzigd, niets gebouwd, geen commit |

Elke bewering hieronder is tegen de code geverifieerd. Waar ADR-043 of een skill iets beweert, staat de uitkomst (bevestigd/discrepantie) expliciet.

---

## A. Wat kost een tweede genest element-subtype? (subknoop 1)

Sjabloon: het `proces`-subtype (ADR-042, migraties 0056–0059). Alles hieronder moest destijds meebewegen en moet voor `bedrijfsfunctie` opnieuw meebewegen — tenzij bewust weggelaten (bv. geen eigen koppelregel, geen kaartprojectie in de MVP).

### A.1 Enum + migratie
- `ElementType.proces = "proces"` — `modules/bwb_ontvlechting/backend/models/models.py:194`.
- Migratie `0056_adr042_elemtype_proces` — **aparte, voorafgaande** migratie (`ALTER TYPE element_type_enum ADD VALUE IF NOT EXISTS`, autocommit_block; PostgreSQL staat ADD VALUE niet toe in dezelfde transactie als eerste gebruik). Downgrade = no-op (enum-waarde is niet te droppen). `migrations/versions/0056_adr042_elemtype_proces.py:23-32`.

### A.2 ArchiMate-typing — `business_function` ontbreekt (ADR-043-claim BEVESTIGD)
- `TOEGESTANE_ELEMENTEN` (`services/archimate_typing.py:29-41`) bevat `business_process` (:38) maar **niet** `business_function`. Het comment op :66-67 zegt letterlijk: *"`business_function` is bewust NIET opgenomen: de bedrijfsfunctie-as is een geparkeerd, eigen ADR-spoor (ADR-042 besluit 1)."*
- Typing-entry proces: `archimate_typing.py:68` — `{business_process, business, behavior}`. Een bedrijfsfunctie zou de **derde** gemarkeerde behavior-afwijking op OK-3 worden (na work_package en proces; comment :18-20).
- Een functie-as vergt dus: `business_function` toevoegen aan `TOEGESTANE_ELEMENTEN` **én** een entry in `ELEMENT_ARCHIMATE_TYPING` (:45-69).

### A.3 Partitietests — wat faalt precies bij een nieuwe enum-waarde
- `test_archimate_fase_a.py:16-26` (`test_element_type_enum_waarden`): asserteert de **exacte, volledige lijst** enum-waarden. Een nieuwe waarde ⇒ deze test faalt letterlijk op de lijst.
- `test_archimate_fase_d.py:13-27` (partitietest): `getypeerd | geparkeerd | via_componenttype == set(ElementType)`. Een nieuwe waarde zónder typing-entry (of parkering in `ELEMENT_TYPEN_NOG_NIET_GEREALISEERD`) ⇒ set-vergelijking faalt. Ook `:83` asserteert dat de geparkeerde set **leeg** is — parkeren is dus óók een testwijziging.

### A.4 Subtabel + migratie (het 0057-recept)
`migrations/versions/0057_adr042_proces.py:29-66` — het volledige recept:
- Kolommen: `id` (gen_random_uuid), `tenant_id`, `naam` String(255) NOT NULL, `toelichting` Text nullable, `ouder_id` nullable, timestamps (:32-39).
- `UNIQUE(tenant_id, id)` als composiet-FK-target (:41); `CHECK ouder_id IS NULL OR ouder_id <> id` (:42-45).
- Indexen `ix_proces_tenant`, `ix_proces_tenant_ouder` (:47-48).
- Shared-PK composiet-FK `(tenant_id,id) → element` **ON DELETE CASCADE** (:50-53); self-FK `(tenant_id,ouder_id) → proces` **ON DELETE RESTRICT** (:55-58).
- `ENABLE`+`FORCE ROW LEVEL SECURITY` + policy `tenant_isolation` + `REVOKE ALL`/`GRANT S,I,U,D … lk_app` (:59-66).
- Model: klasse `Proces` — `models.py:632-671` (o.a. `uq_proces_tenant_id` :652, `ck_proces_geen_self_parent` :655, `fk_proces_element` :659, `fk_proces_ouder` :662-663).

### A.5 RBAC
- `Entiteit.PROCES` — `backend/app/core/rbac.py:52`; `Entiteit.PROCESVERVULLING` — :55.
- `PERMISSIES`: `Entiteit.PROCES: dict(_INHOUD)` — :153; `Entiteit.PROCESVERVULLING: dict(_INHOUD)` — :155.
- Teltest: `backend/tests/test_rbac.py:85` — docstring en telling **"26×4×4 = 416 combinaties"**. Elke nieuwe tenant-entiteit verhoogt de 26 (functie-as met eigen koppelregel-entiteit: 26→28 = 448; alleen het element: 26→27 = 432).

### A.6 Audit
- `AUDIT_TENANT_ENTITEITEN` bevat `"proces", "procesvervulling"` — `backend/app/core/audit.py:71-72`. Nieuwe tabelnamen moeten hier bij (+ de allowlist-test beweegt mee).

### A.7 Service / schemas / routes / registratie
- Services: `proces_service.py` (267 r; cycluspreventie `_zou_kring_maken` :88, `verwijder` met HEEFT_DEELPROCESSEN-precheck :163-183, keyset-`lijst` :185, `subboom` BFS :231), `procesvervulling_service.py` (425 r), `applicatiefunctie_catalog.py`, `applicatiefunctieconfig_service.py`, `seed_applicatiefunctie.py` (alle in `modules/bwb_ontvlechting/backend/services/`).
- Schemas: `schemas/proces.py` (`ProcesSorteerveld` :16, `ProcesCreate` :24, `ProcesUpdate` :42, `ProcesRead` :63, `ProcesPagina` :72, `ProcesBoomItem` :77), `schemas/procesvervulling.py` (Aanmaken :16, Wijzigen :40, Uit :68), `schemas/applicatiefunctieconfig.py`.
- Routes: `routes/proces.py`, `routes/procesvervulling.py`, `routes/applicatiefunctieconfig.py`, plus het afgeleide beeld `GET /partijen/{id}/processen` in `routes/partij.py:97-106`.
- Registratie: `backend/app/main.py:77-79` (imports) en `:174-175` + `:184` (include_router).
- Platform-seed-keten: `backend/app/platform_init.py:31` + `:76-77` (`seed_applicatiefunctie`).
- Kaartprojectie: `services/landschapskaart_service.py:492-625` (het volledige proces-blok — zie B.4).

### A.8 Frontend (platform-bedrading)
- `frontend/src/api.js`: `processen`-client :392-401, `procesvervullingen` :404-410, `partijen.processen` :214-215, platform `applicatiefunctieconfig` :572-577.
- Router `frontend/src/router/index.js`: :33 (lazy import), :135-137 (`proces-lijst`, `proces-detail`), :56 + :180 (`beheer-applicatiefunctieconfig`).
- Nav: `frontend/src/layouts/AppLayout.vue:121-127` (`data-testid="nav-processen"`).
- Testrouters: `AppLayout.test.js:26` én `AppLayout.gating.test.js:18` (naam `proces-lijst` in beide — de bekende dubbele-registratie-gotcha).
- Labels: `modules/bwb_ontvlechting/frontend/labels.js:61-63` (`proces`, `procesvervulling`).
- Pure modules: `procesBoom.js` (169 r), `procesZoek.js` (41 r), `procesKaartIngang.js` (47 r).
- Module-views (7): `ProcesLijst.vue` (666 r), `ProcesDetail.vue`, `ProcesDiagram.vue` (490 r), `ProcesComponentenSectie.vue`, `ComponentProcessenSectie.vue`, `OnderliggendeProcessenSectie.vue`, `PartijProcessenSectie.vue`.
- Consumenten: `ComponentDetail.vue:38` + `:398` (processectie), `PartijDetail.vue:20` + `:358`, `ComponentFormulier.vue:28-34` + `:99-123` (verzamel-procesregels bij aanmaken), `KaartBeginscherm.vue:22` + `:113` ("Via proces"), `LandschapskaartView.vue` (zie F), plus platform-view `frontend/src/views/ApplicatiefunctieConfigBeheer.vue`.

### A.9 Seed
- `backend/dev_seed_testdata.py:1595-1657`: twee procesbomen (Vergunningverlening → Aanvraag behandelen → Besluit vastleggen; + Bezwaar behandelen bewust ondersteuningsloos; Burgerzaken → Verhuizing verwerken), idempotent skip-op-naam resp. skip-op-tripel; telling-keys `"processen", "procesvervullingen"` op :1001.

### A.10 Tests (bestanden die het proces-subtype dragen)
Backend: `test_archimate_fase_a.py`, `test_archimate_fase_d.py`, `test_proces_adr042.py`, `test_procesvervulling_adr042.py`, `test_rollup_adr042.py`, `test_landschapskaart_proces.py`, `test_rbac.py` (teltal).
Frontend: `ProcesLijst.test.js`, `ProcesDetail.test.js`, `ProcesDiagram.test.js`, `procesFocusSet.test.js`, `procesKaartIngang.test.js`, `OnderliggendeProcessenSectie.test.js`, `PartijProcessenSectie.test.js`, plus proces-raakvlakken in `LandschapskaartView.test.js`, `LandschapskaartPopups.test.js`, `ComponentDetail.test.js`, `ComponentFormulier.test.js`, `kaartLayout.test.js`, `api.filter.test.js`, `AppLayout.test.js`/`AppLayout.gating.test.js`.

### A.11 Geteld overzicht

| Cluster | Raakpunten | Bestanden |
|---|---|---|
| Schema/model/migratie (enum, subtabel, typing) | 7 | models.py, archimate_typing.py, 0056, 0057, (+catalogus: 0058, models.py:1029, koppelregel: 0059, models.py:674) |
| RBAC + audit + teltest | 4 | rbac.py, audit.py, test_rbac.py |
| Backend services/schemas/routes/registratie | 12 | 5 services, 3 schemas, 3+1 routes, main.py, platform_init.py, landschapskaart_service.py |
| Seed | 1 | dev_seed_testdata.py |
| Backend-tests | 7 | zie A.10 |
| Frontend-bedrading (api/router/nav/labels/testrouters) | 6 | api.js, router/index.js, AppLayout.vue, labels.js, 2 testrouters |
| Frontend pure modules + views + consumenten | 15 | 3 modules, 7 views, 5 consumenten (incl. kaart + platform-beheer) |
| Frontend-tests | 14 | zie A.10 |

**Totaal: ± 66 raakpunten verdeeld over ± 45 bestanden** voor de volledige proces-as (element + catalogus + koppelregel + kaartprojectie + schermen). De kale kern "genest element-subtype zonder koppelregel/kaart" is het kleinere deel: ± 20 raakpunten over ± 14 bestanden (enum-migratie, subtabel-migratie, model, typing, partitietests, RBAC+audit+teltests, service, schema, route, main.py, api.js, router, nav, labels, lijst-view, seed).

---

## B. Hoe generiek is de LI038-bouw werkelijk?

### B.1 `procesBoom.js` — **generiek**
Alle vier exports werken op kale `(ids: Set, hierEdges: [{bron,doel}], naamVan: fn)` — geen enkele proces-specifieke data-toegang, geen api-import, geen veldnaam buiten `bron/doel` (`procesBoom.js:26, 48, 117, 137`). De module is bewust puur (geen Vue/cytoscape-import, :18-20). Het enige proces-gebonden is de **naamgeving** (functienamen, comments). Werkt vandaag al op elke genestelde structuur.

### B.2 `ProcesDiagram.vue` — **structuur generiek, huid proces-gebonden**
- Props zijn vorm-generiek: `processen` = platte rijen `{id, naam, ouder_id, ouder_naam}` (:27-35), `gapIds` = Set, `initieelCentrumId`. De component is api-vrij (:6-8, de LI038-borging).
- Proces-specifiek (hard): benaming van props/emits (`processen`, `centrumGewijzigd`, `bekijk-op-kaart` :38-44), alle UI-teksten ("Zoek een proces" :379, "Toon hele processenlandschap" :64-65), client-side zoek + identiteit "naam — ouder" (:86-95), silhouet `round-rectangle` = "zelfde proces-silhouet als de kaart" (:257), gap-selector `node[?procesGap]` (:266, :293-295), popup-velden (naam/toelichting/ouder, :112-134), en de kaart-uitgang (emit naar de proces-handoff).
- De kern (focus/inzoom/history/layout) leunt volledig op de generieke `procesBoom`-functies (:24, :78-79, :317).

### B.3 `ProcesLijst.vue` — **patroon herbruikbaar, bestand proces-gebonden**
Harde koppelingen: `api.processen.lijst/maak/werkBij/verwijder` (:78, :235-236, :281, :358), gap-cue via `api.processen.rollup` + `api.procesvervullingen.lijst` (:183-184), `useLijstStaat`-sleutel (:57), router-link `proces-detail` (:533-537), kaart-handoff `zetKaartHandoff`/`bouwProcesKaartHandoff` (:21, :375-395), alle teksten. De tree-view-rendering zelf loopt via de gedeelde `procesBoomStructuur` (:95) en de Boom|Diagram-schakelaar is een lokaal UI-patroon (:415). Niets hiervan is als bouwsteen geparametriseerd op een tweede entiteit.

### B.4 Backend
- **`procesvervulling_service.py`** — de VORM is een herhaalbaar recept (tripel-uniciteit + pre-check 409, element-type-validatie beide kanten, catalogus-validatie, naam-verrijkte leespaden, rollup via subboom, organisatie-afleiding), maar élke functie noemt letterlijk `Proces`, `Procesvervulling`, `ElementType.proces`, `proces_id`, `ONGELDIG_PROCES`, `VERVULLING_BESTAAT` (:29-42, :65-104, :120-153, :282-345, :348-424). Geen parametrisering aanwezig.
- **`proces_service.py`** — idem: het genest-subtype-recept (kringpreventie :88-109, ouder-validatie :111, HEEFT_DEELPROCESSEN :163-183, subboom-BFS :231-259) is generiek van vorm maar overal `Proces`-gebonden. NB: `verwijder` doet een **core-delete op het element-supertype** (:181) — zie D.2-nuance (audit).
- **Kaartprojectie** (`landschapskaart_service.py:492-625`) — het algoritme (vervullingen in scope → batch-klim naar de wortel met cyclus-memoisatie :540-562 → subboom-BFS omlaag :564-580 → eerste-klas knopen :583-591 → hiërarchie-edges :593-601 → gebundelde vervult-edges met `herkomst[]` :603-622) is vorm-generiek, maar hard verweven met `Proces`/`Procesvervulling`-modellen, `element_type="proces"` (:590), `relatietype="proces_hierarchie"` (:598), `relatietype="procesvervulling"` (:618), `ring="processen"` (:600, :621) en de applicatiefunctie-catalogus (:603).

### B.5 Conclusie per onderdeel (feit-oordeel, geen bouwadvies)

| Onderdeel | Oordeel |
|---|---|
| `procesBoom.js` (structuur/layout/focus/subboom) | **Hergebruikbaar zonder wijziging** (alleen naamgeving is proces-gekleurd) |
| `procesZoek.js` (picker-helper) | Generaliseerbaar met beperkte ingreep (api-object + teksten zijn de enige binding) |
| `ProcesDiagram.vue` | **Generaliseerbaar met beperkte ingreep** (props al vorm-generiek; teksten/emits/gap-selector/silhouet hernoemen of parametriseren) |
| `ProcesLijst.vue` | **Feitelijk herbouw of forse parametrisering** (api-calls, routes, handoff, lijststaat-sleutel, teksten door het hele bestand) |
| `proces_service.py` | Herbouw naar het recept (generiek van vorm, `Proces`-gebonden in code) |
| `procesvervulling_service.py` | Herbouw naar het recept (idem; zie ook C.4) |
| Kaartprojectie (landschapskaart_service) | Proces-gebonden; het algoritme is kopieerbaar, niet aanroepbaar-met-ander-type. **MVP-noot:** ADR-043 verbergt het procesregister — of de functie-as überhaupt een kaartprojectie krijgt is een open ontwerpknoop, geen gegeven |

---

## C. Koppelregel functie ↔ component (subknoop 4)

### C.1 Exacte vorm `procesvervulling`
- **Tabel** (migratie `0059:27-61`; model `models.py:674-712`): `id`, `tenant_id`, `component_id`, `proces_id`, `applicatiefunctie` String(60) **NOT NULL** (models.py:710), `toelichting` Text nullable, timestamps.
- **Uniciteit**: `UNIQUE(tenant_id, component_id, proces_id, applicatiefunctie)` = het tripel (`uq_procesvervulling`, models.py:694-695; 0059:38-41). Meerdere functies per (component, proces) = losse regels; dubbel tripel = 409 `VERVULLING_BESTAAT` (pre-check service :82-96, UNIQUE als backstop).
- **FK's**: beide zijden composiet-FK → `element(tenant_id, id)` **ON DELETE CASCADE** (`fk_procesvervulling_component` :699, `fk_procesvervulling_proces` :703; 0059:46-53). Dat het écht een component resp. proces is dwingt de **service** af (422 `ONGELDIG_COMPONENT`/`ONGELDIG_PROCES`, service :71-79) — niet het schema.
- **RLS**: FORCE + `tenant_isolation` + REVOKE/GRANT lk_app (0059:54-61).
- **RBAC**: `Entiteit.PROCESVERVULLING`, `_INHOUD`-patroon (rbac.py:55, :155). **Audit**: op de allowlist (audit.py:72).
- **Validaties**: element-type beide kanten, actieve catalogus-optie (`ONGELDIGE_APPLICATIEFUNCTIE`, service :80), tripel-pre-check; `werk_bij` wijzigt alléén kenmerk-velden (ankers niet in het Wijzigen-schema; service :120-153).

### C.2 Is `applicatiefunctie` onlosmakelijk?
**Feitelijk: ja, in de huidige vorm.** De kolom is NOT NULL (models.py:710; 0059:34) én onderdeel van de uniciteits-definitie (het tripel). Optioneel maken raakt twee dingen tegelijk: (1) een migratie `nullable=True`; (2) de uniciteits-semantiek — PostgreSQL behandelt NULL als distinct in een UNIQUE, dus `(component, proces, NULL)` zou **onbeperkt vaak** mogen bestaan; "één functieloze regel per paar" zou een partiële index of andere constraint vergen (er is geen partial-index-precedent in de codebase — likara-db V010-notitie). Daarnaast: service-validatie (:80), schema's, de kaart-bundeling (label uit de functie, landschapskaart :617-618) en de UI-dropdowns lezen het veld als verplicht.

### C.3 CASCADE bij hard verwijderen — ADR-043-claim BEVESTIGD, met twee nuances
- **Bevestigd**: een delete van het proces-**element** cascadeert `element → proces`-subtype (`fk_proces_element`, 0057:50-53) én veegt alle `procesvervulling`-rijen weg (`fk_procesvervulling_proces` CASCADE, 0059:50-53). De eigen registratie wordt dus feitelijk meegesleurd — exact de ADR-043-claim.
- **Nuance 1 (gebruikerspad)**: `proces_service.verwijder` pre-checkt deelprocessen (409 `HEEFT_DEELPROCESSEN`, :168-180) en de self-FK RESTRICT is de backstop — via de API kan alleen een **blad** verdwijnen; diens vervullingen cascaden wél geruisloos mee.
- **Nuance 2 (audit)**: de delete loopt via een **core-delete** op `Element` (:181) — het bekende systemische audit-gat (LI035): de subtype-/vervulling-rijen verdwijnen buiten de audit-capture om. Relevant feit voor "vervallen ≠ verwijderen".

### C.4 Tweede tabel (`functievervulling`) vs. bestaande generiek maken — raakpunten
- **Tweede tabel** = het 0059-recept kopiëren: 1 migratie, 1 model-klasse, 1 RBAC-entiteit + PERMISSIES + teltal (416→+16 per entiteit), 1 audit-allowlist-regel, 1 service + schema + route + main.py-registratie, api.js-client, testbestand(en), seed-scenario. Bestaande code, contracten en historie blijven onaangeraakt. (Dit is de n≥2-situatie waarvoor harde regel 8 — pas abstraheren bij twee instanties — is geschreven; het bestaan van twee instanties is dan het feit dat abstractie legitimeert.)
- **Bestaande generiek maken** (bv. `proces_id` → generiek doel-anker) raakt feitelijk: het API-contract (`proces_id` in schemas/routes/api.js), de UNIQUE-naam en kolomnamen (migratie op bestaande tabel), de audit-historie (veldnamen in gelogde diffs), de seed, alle 7 frontend-views + de kaartprojectie, en de bestaande testbestanden. Het is een breaking wijziging van een werkend contract; de tweede tabel is dat niet.

---

## D. Bronsleutel, herkomst en soft-vervallen op elementen (subknopen 2 en 6)

### D.1 Draagt enig element een bronsleutel/herkomst-marker? — **Nee.**
- `Element` heeft alleen `id`, `tenant_id`, `element_type` + timestamps (models.py:262-275). Geen enkel element-subtype (component/proces/partij/contract/…) draagt een bron- of herkomst-kolom.
- Bestaande precedenten (elders, niet op elementen):
  - `optie_sleutel` — stabiele sleutel op álle catalogi (models.py:797, :984, :1004, :1023, applicatiefunctie :1029 e.v.);
  - `checklistvraag.betekenis` — nullable marker-kolom met stabiele catalogus-sleutel, app-side gevalideerd, geen harde FK (models.py:763-769);
  - `checklistvraag_optie.afgeleid_bron` — herkomst-marker "deze set is afgeleid uit een model-enum" (models.py:803);
  - `gebruiker_persoon.keycloak_sub` — stabiele externe identiteit, UNIQUE per tenant (models.py:1096, :1105).

### D.2 Soft-deactivate op elementen? — **Bestaat niet.**
- `actief`-vlaggen bestaan uitsluitend op catalogi (models.py:760, :800, :987, :1007, :1026, :1047, :1368, :1394, :1417, :1441). Dichtstbijzijnde vormen bij "vervallen ≠ verwijderen":
  1. **`checklistvraag.actief`** (models.py:760) — het enige **tenant-scoped** record met een actief-vlag ("verwijderen" = deactiveren, historie blijft resolvebaar); qua vorm het dichtst bij een vervallen-vlag op een tenant-rij.
  2. **`betekenis`-marker** (D.1) — nullable status-/classificatiekolom op een tenant-entiteit.
  3. **`component_klaarverklaring`** (models.py:1145, tabel :1162) — status als **eigen registratie-tabel** naast de entiteit (herroepbaar, audit-gedragen) i.p.v. een kolom erop.
- Nuance uit C.3 geldt hier: het huidige element-verwijderpad (core-delete) is deels audit-blind — een gedocumenteerd risico dat een vervallen-vlag zou omzeilen door überhaupt niet te verwijderen.

### D.3 Leespaden die een `vervallen`-vlag op een (proces-achtig) element zouden moeten respecteren — vindplaatsen
1. `proces_service.lijst` (keyset, :185) en `subboom` (:231) — lijstscherm + rollup-basis.
2. `procesvervulling_service`: `lijst_voor_proces` (:198), `lijst_voor_component` (:240), `rollup_voor_proces` (:282), `processen_voor_organisatie` (:348).
3. Kaartprojectie `landschapskaart_service.py:492-625` (knopen :583-591, hiërarchie-edges :593-601, vervult-edges :603-622).
4. Pickers: `procesZoek.js` (gedeelde zoeker; consumenten `ComponentProcessenSectie.vue:42`, `KaartBeginscherm.vue:113`, `ComponentFormulier.vue:34`) — plus de ouder-picker in de ProcesLijst-dialoog.
5. Gap-cue: `ProcesLijst.vue:172-205` (rollup + vervullingen per wortel) en de kaart-gap-tegenhanger.
6. Afgeleid beeld: `routes/partij.py:97-106`.
7. **Niet** nodig: signalering en dashboard — `registratiegaten_service.py` en `dashboard_service.py` bevatten géén proces-verwijzing (grep leeg).

---

## E. Referentiemodel-entiteit + import-route (subknopen 3 en 7)

### E.1 Import-/parse-route — **bestaat niet.**
Geen `UploadFile`, geen file-/multipart-route, geen bulk-endpoint in `backend/app` of de module-routes (grep leeg). Alle registratie loopt via losse JSON-POST's. (`python-multipart` staat wél in `backend/requirements.txt:9`, maar geen enkele route gebruikt Form/File — het is een ongebruikte capaciteit van de dependency-set.)

### E.2 XML-parse-dependency — **geen aanwezig.**
`requirements.txt` bevat geen `lxml` en geen `defusedxml`; nergens in de backend-code wordt `xml.etree`/`lxml`/`defusedxml` geïmporteerd (grep leeg). Alleen stdlib `xml.etree` is beschikbaar-maar-ongebruikt. Een AMEFF/ArchiMate-inlezer introduceert dus een **nieuwe** dependency-keuze (securityrelevant: XML uit externe bron).

### E.3 Platform- vs. tenant-tabel — de twee bestaande recepten
- **Platform-recept** (applicatiefunctie-catalogus, `0058:36-48`): tabel zónder RLS/tenant_id (`id` int PK, `optie_sleutel` UNIQUE, `label`, `volgorde`, `actief`); `REVOKE ALL … FROM lk_app` → `GRANT SELECT … TO lk_app` → `GRANT SELECT, INSERT, UPDATE … TO lk_platform` + sequence-grant — **geen DELETE** (soft-deactivate). Beheer-endpoint onder `vereist_platform_permissie`, view `ApplicatiefunctieConfigBeheer.vue`.
- **Tenant-recept** (proces/procesvervulling, `0057:59-66` / `0059:54-61`): `ENABLE`+`FORCE ROW LEVEL SECURITY`, policy `tenant_isolation` op `app.tenant_id`, `REVOKE ALL`/`GRANT S,I,U,D … TO lk_app`.
- Beide recepten liggen dus klaar voor de knoop "aanbod = platform, ingelezen inhoud = tenant"; er bestaat **geen** gemengd precedent (platform-gevoede tenant-inhoud) behalve de checklistvraag-onboarding-kopie (hardcoded baseline in `services/seed.py`, per tenant gekopieerd — geen bestand-import).

### E.4 Voorbeeldscherm-vóór-landing — **bestaat niet.**
Er is geen preview-en-bevestig-patroon voor te landen data. Dichtstbijzijnde verwanten zijn bevestigings-dialogen (KOPPELING_DUBBEL-hersubmit; `BevestigVerwijderDialog.vue`) — die bevestigen een actie, ze tonen geen diff/voorbeeld van in te lezen inhoud. Het ADR-043-voorbeeldscherm (nieuw/bijgewerkt/vervallen + nog-in-gebruik) is volledig nieuw terrein.

---

## F. Procesregister verbergen (MVP-scope) — alle ingangen

Kaart van wat er is; **niets verwijderd**.

| # | Ingang | Vindplaats |
|---|---|---|
| 1 | Menu-item "Processen" | `frontend/src/layouts/AppLayout.vue:121-127` (`nav-processen`) |
| 2 | Routes `proces-lijst` / `proces-detail` | `frontend/src/router/index.js:33, 135-137` |
| 3 | Platform-beheer-route + view applicatiefunctie-catalogus | `router/index.js:56, 180`; `frontend/src/views/ApplicatiefunctieConfigBeheer.vue` |
| 4 | Componentdetail — processectie ("waarvoor gebruiken we het") | `ComponentDetail.vue:38, 398` (`ComponentProcessenSectie`) |
| 5 | Componentformulier — verzamel-procesregels bij aanmaken | `ComponentFormulier.vue:28-34, 99-123` |
| 6 | Partijdetail — afgeleid procesbeeld | `PartijDetail.vue:20, 358` (`PartijProcessenSectie`); backend `routes/partij.py:97-106` |
| 7 | Kaart: ring `processen` (default aan, óók praatplaat-kern) + proceslaan | `LandschapskaartView.vue:54` (RINGEN), :67 (`RING_PRAATPLAAT_KERN`), :70 (label), :85 + :93 (proceslaan/`DEFAULT_LANE_VOLGORDE`) |
| 8 | Kaart: subboom-projectie (proces-knopen + vervult-edges) | backend `landschapskaart_service.py:492-625` |
| 9 | Kaart: proces-popup ("Vervuld door", herkomst-uitsplitsing, vervul-toggle) | `LandschapskaartView.vue:1526-1648` |
| 10 | Kaart: proces-ingang (dim-focus) + dubbelklik-inzoom | `LandschapskaartView.vue:862-979` (o.a. `procesIngang` :865, `zoomInOpProces` :955); inzoom-filter :741-744 |
| 11 | Kaart-beginscherm: "Via proces"-ingang | `KaartBeginscherm.vue:22, 113`; `LandschapskaartView.vue:984` |
| 12 | Handoff/deep-link proces→kaart (consume-once) | `modules/.../frontend/procesKaartIngang.js` (bouwer), `frontend/src/composables/kaartHandoff.js`; aanroepers `ProcesDetail.vue:110-164`, `ProcesLijst.vue:375-395` |
| 13 | Boom|Diagram-schakelaar + ProcesDiagram | `ProcesLijst.vue:415-448`; `ProcesDiagram.vue` |
| 14 | api-clients | `api.js:214-215, 392-410, 572-577` |
| 15 | Backend-routes | `routes/proces.py`, `routes/procesvervulling.py`, `routes/applicatiefunctieconfig.py`, `main.py:174-175, 184` |
| 16 | Seed-scenario (proces-data) | `dev_seed_testdata.py:1595-1657` |

**Dashboard/signalering:** géén proces-verwijzingen (`dashboard_service.py`, `registratiegaten_service.py` — grep leeg). Daar hoeft niets verborgen.

**Wat raakt er in de tests bij verbergen (afhankelijk van de gekozen verberg-laag):**
- Nav/route weg → `AppLayout.test.js:26` en `AppLayout.gating.test.js:18` (testrouters + gating-asserts).
- Proces-schermen onbereikbaar/weg → `ProcesLijst.test.js`, `ProcesDetail.test.js`, `ProcesDiagram.test.js`, `procesFocusSet.test.js`, `procesKaartIngang.test.js`, `OnderliggendeProcessenSectie.test.js`, `PartijProcessenSectie.test.js`.
- Kaart-ring/laan/popup/ingang uit → `LandschapskaartView.test.js` (o.a. :41-45 proces-mocks, :597-610 laneVolgorde-assert mét `processen`), `LandschapskaartPopups.test.js`, `kaartLayout.test.js` (procesBoomLayout).
- Detail-secties uit → `ComponentDetail.test.js`, `ComponentFormulier.test.js`, `PartijDetail.test.js`.
- api-client-wijzigingen → `api.filter.test.js` (processen-allowlist).
- Backend blijft (alleen UI-verbergen raakt geen backend-suite); wordt óók de projectie/route uitgezet, dan raken `test_landschapskaart_proces.py` en de route-tests in `test_proces_adr042.py`/`test_procesvervulling_adr042.py`/`test_rollup_adr042.py`.

---

## G. Stand van de werktree

1. **`git status`: schoon**; branch `master`, up-to-date met origin. Huidige commit `b46f4b0` ("LI038: sessie-afsluiting (V039)"). **`alembic heads`: exact 1 head — `0059_adr042_procesvervulling`** (verwachting klopt).
2. **LI037 seed-idempotentie-fix: GELAND.** Commit `ef2421f` ("LI037: verantwoordelijken-seed idempotent — vaste identiteit (Zaaksysteem 1.1/1.2/1.3), vul-als-leeg — ADR-037"); code in `dev_seed_testdata.py:1559-1592` (doelrijen op vaste identiteit component+vraagcode; `rij.verantwoordelijke_id is not None → overslaan` :1586).
   **Term-discrepantie:** het woord "stakeholder" komt nergens in de repo voor — de opdracht-term "stakeholder-toewijzing" verwijst feitelijk naar deze **verantwoordelijken**-toewijzing (ADR-037).

---

## Kostprijs functie-as (samenvatting A)

**± 66 raakpunten over ± 45 bestanden** was de volledige proces-as (element + catalogus + koppelregel + kaartprojectie + 7 views + tests). De **kale kern** "tweede genest element-subtype" (zonder eigen koppelregel, zonder kaartprojectie): **± 20 raakpunten over ± 14 bestanden** — 2 migraties (enum + subtabel), model, typing (2 constanten), 2 partitietests, RBAC (entiteit + PERMISSIES + teltal 416→432), audit-allowlist, service, schema, route, main.py, api.js, router, nav (+2 testrouters), labels, lijst-view, seed. Elke optionele laag (koppelregel-tabel: +16 RBAC-combinaties + service/route/schema/api/tests; kaartprojectie; detail-secties) telt daar bovenop conform het A.11-overzicht.

## Hergebruik-oordeel (samenvatting B)

| LI038-onderdeel | Oordeel |
|---|---|
| `procesBoom.js` (structuur, layout, focus, subboom) | **Hergebruikbaar zonder wijziging** |
| `procesZoek.js` | Generaliseerbaar met beperkte ingreep |
| `ProcesDiagram.vue` | **Generaliseerbaar met beperkte ingreep** (props al generiek; teksten/emits/selectors proces-gebonden) |
| `ProcesLijst.vue` | **Feitelijk herbouw** of forse parametrisering (api/routes/handoff/teksten door het hele bestand) |
| `proces_service.py` | Herbouw naar het bewezen recept (vorm generiek, code proces-gebonden) |
| `procesvervulling_service.py` (koppelregel + rollup) | Herbouw naar het bewezen recept; zie C.4 voor tweede-tabel-vs-generiek |
| Kaartprojectie (`landschapskaart_service`) | Proces-gebonden; algoritme kopieerbaar, niet parametriseerbaar-in-huidige-vorm |

Netto: het **zuiver structurele** deel (boom-opbouw/layout/focus/inzoom, en de vorm van de recepten) is generiek of bijna-generiek; alles wat **api, routes, teksten, ringen en modellen** raakt is proces-gebonden. De functie-as is dus deels hergebruik (frontend-boomkern), deels herbouw-naar-recept (backend + lijstscherm) — géén gratis hergebruik, maar ook géén blinde herbouw: de recepten zijn beproefd en 1-op-1 kopieerbaar.

## Open feiten

1. **RBAC-teltal na de functie-as** hangt af van het aantal nieuwe entiteiten (element alleen: 27×4×4=432; + koppelregel: 28×4×4=448) — een ontwerpknoop, geen vaststaand feit.
2. **`python-multipart`**: aanwezig in requirements maar door geen route gebruikt; of iets in de FastAPI-stack er impliciet op leunt is niet verder onderzocht (niet relevant voor de import-conclusie: er is géén upload-route).
3. **Live-DB-stand** is niet bevraagd (geen psql nodig gebleken): alle feiten zijn schema-/code-feiten. De CASCADE-claim is op FK-definities bevestigd, niet opnieuw live gedemonstreerd (ADR-043 meldde de eerdere live-bevestiging).
4. **ProcesLijst-dialoog ouder-picker**: als vindplaats geteld (D.3-punt 4) maar niet regel-voor-regel geciteerd; het bestand gebruikt de gedeelde proces-zoeker, verdere detaillering was voor dit rapport niet nodig.
5. **Verberg-mechanisme MVP** (feature-vlag vs. routes/nav weghalen vs. rol-gating) is bewust niet uitgewerkt — F levert alleen de kaart van de ingangen; het mechanisme is een ontwerpknoop.
