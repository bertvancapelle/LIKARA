# Checkpoint productie-gereedheid — V050 (read-only)

**Opdracht:** `START: checkpoint-productie-gereedheid-V050` · **Datum:** 2026-07-23
**Aard:** read-only meting; niets gebouwd, niets gemigreerd, niets geseed, niets gecommit.

---

## 1. Stand

| Veld | Waarde |
|---|---|
| Branch | `master` |
| HEAD | `788d451` — "[docs] LI049 afsluiting — V050 …" |
| Werktree | schoon (0 gewijzigde bestanden vóór dit rapport) |
| Alembic heads | 1 — `0073_adr052_klaarverkl_snapshot` |
| Stack | draaiend (lk-api, lk-postgres, lk-keycloak, lk-redis, lk-rabbitmq, lk-minio) |
| Gemeten tenant | `11111111-1111-1111-1111-111111111111` (dev-seed-tenant; **geen naam — de `tenant`-registry telt 0 rijen**, zie §G2-3) |
| Componenten in tenant | **24** (20 applicatie · 1 database · 1 fileshare · 1 client_software · 1 saas_dienst) |
| Overige tellingen | 428 elementen · 98 checklistvragen (alle actief) · 267 scores · 373 relaties · 1 open blokkade · 1 nee/deels-score |

Alle tenant-metingen zijn gedaan als **`lk_app`** met `set_config('app.tenant_id', …)` op bovenstaande tenant.

---

## 2A — Checklistvraag deactiveren: de poort en het gevolg (P50-1)

### A1 — De poort: TENANT-bevoegdheid, medewerker kan erbij

- Menu-item "Checklistvragen" staat **zonder enige rol-gating** in de nav (`frontend/src/layouts/AppLayout.vue:191-196`, geen `v-if`) en route `checklistvragen` → `ChecklistConfigBeheer.vue` in de **tenant-shell** (`frontend/src/router/index.js:151`). De view zelf bevat **0** `hasRole`/`mag`-checks — elke tenant-rol ziet scherm én knoppen.
- Backend: alle vraagbeheer-routes guarden op **`Entiteit.CHECKLISTVRAAG`** (tenant-matrix, `backend/app/core/rbac.py:218` → `_INHOUD`, `rbac.py:106-111`): Viewer **L** · Medewerker **LAW** · Beheerder **LAWV** · Auditor **L**. Deactiveren = `POST /vragen/{id}/actief` onder **WIJZIGEN** (`modules/bwb_ontvlechting/backend/routes/checklistconfig.py:118-127` + `:41`).
- **Feitelijk kunnen deactiveren: medewerker én beheerder.** Viewer/auditor zien de knop en krijgen pas bij klikken een 403.
- **Tegenspraak beslecht (meetregel 5):** `docs/OPVOLGPUNTEN.md` P50-1 verwachtte *platformbeheer*; de code zegt **tenant** — en dat is een gedocumenteerd besluit (comment `rbac.py:214-217`: "ADR-022 W1: de vragenset is tenant-eigendom"). De likara-db-skill klopt; de verwachting in het opvolgpunt niet. Of *medewerker* (naast beheerder) deze tenant-brede knop hoort te hebben is een **besluit van Bert** — de `_INHOUD`-matrix geeft hem WIJZIGEN, en deactiveren ís WIJZIGEN.

### A2 — Het gevolg: antwoorden worden verborgen (niet verwijderd), en de engine telt scheef

Gemeten aan vraag 1.1 (type applicatie) in de tenant: deactivering raakt **20** componenten (`impact_telling` telt componenten per type, `checklistconfig_service.py:203-211`; de "17" uit de waarneming is een oudere datastand). **5** componenten dragen een antwoord op 1.1, waarvan **1** een `nee` (de voeding van de enige open blokkade).

1. **Antwoorden blijven in de database** — `zet_actief` togglet alleen `vraag.actief` (`checklistconfig_service.py:262-272`), scores worden nergens aangeraakt.
2. **Maar ze worden onzichtbaar**: de scoring-read levert alleen `actief=true` (`checklistvraag_service.py:31`), en de frontend joint scores op de geladen vragenlijst en **laat scores op verdwenen vragen stil vallen** (`ChecklistscoreSectie.vue:163-168`, `_codeVoorVraagId` → alleen bij match). Antwoord op A2: **verborgen**, niet verwijderd.
3. **De engine telt scheef (nieuw gat, §G2-1):** `herbereken_lifecycle` telt `aantal_vragen` alleen over **actieve** vragen (`lifecycle_service.py:111-120`) maar `aantal_gescoord` over **álle** scores van het component — zonder join op de vraag (`lifecycle_service.py:121-128`). Scores op gedeactiveerde vragen blijven meetellen. Scenario: deactiveer gescoorde vragen → `gescoord ≥ vragen` → component wordt **migratieklaar terwijl de zichtbare checklist onbeantwoord is** (UI-teller toont dan bv. 0/4, status groen). `test_vraagbeheer_w1_fanout.py` dekt de symmetrische case (vraag erbij/eraf zonder scores), niet deze asymmetrie.
4. **Blokkade-doodlopend pad:** de `nee`-score op 1.1 voedt een open blokkade. Na deactivering blijft die open (handmatig `opgelost` ⇒ 409, `blokkade_service.py:414-418`); auto-oplossen vergt een score-overgang, maar de score-rij is uit de UI verdwenen → **de blokkade is via de UI niet meer te dichten** en het component blijft `geblokkeerd`. (Alleen via de kale API kan de score nog gemuteerd worden — `_valideer_checklistvraag_id` checkt bestaan + type, **niet** `actief`, `checklistscore_service.py:140-158`.)

### A3 — Het stille gat: niet in "Dit moet nog", wél in "Dit valt op"

- **De premisse van de opdracht klopt niet met de code** (meetregel 5): de organisatienorm stelt **feiten** verplicht, geen checklistvragen — `HARDE_FEITEN` = 10 feiten (eigenaar/verantwoordelijke/biv/gebruikersgroep/bedrijfsfunctie/levensfase/bedoeling/hosting/koppelingen/contract, `component_norm_service.py:38-47`). "Dit moet nog" kan dus nooit een losse vraag bevatten.
- **Het echte stille gat zit in "Dit valt op":** `_checklist_nee_deels` telt nee/deels-scores **zonder actief-filter** (`component_open_punten_service.py:94-108`) en geeft als route `tab: checklist` (`:174`). Een `nee` op een gedeactiveerde vraag blijft dus als open signaal staan, met een doorklik naar een tabblad **waar de rij niet meer bestaat** — een punt dat niemand kan dichten. In de gemeten tenant zou dat na deactivering van 1.1 direct spelen (de enige nee-score zit op 1.1).
- **Testdekking: 0.** `test_component_open_punten_li047.py` bevat 0 verwijzingen naar `actief`/deactivering; geen enkele test oefent open-punten × inactieve vraag.

### A4 — De omkering

**Ja, volledig omkeerbaar:** dezelfde knop toont "Activeren" op een gedeactiveerde vraag (`ChecklistConfigBeheer.vue:347`); `zet_actief(true)` togglet terug en herberekent; omdat scores nooit gemuteerd zijn verschijnen de antwoorden **exact zoals ze waren** (client-join op vraag-id herstelt vanzelf), inclusief `antwoord_waarde`.

### De drie vragen (A)

- **(a)** Ja — met echte gebruikers kan élke medewerker met twee klikken de vragenlijst van de hele organisatie wijzigen, waarbij antwoorden onzichtbaar worden, de status-berekening scheef gaat tellen en er onafsluitbare signalen/blokkades kunnen ontstaan die de gebruiker niet kan verklaren.
- **(b)** Deels — de rechtenkeuze (A1) en de telfouten (A2.3/A3) zijn codefixes die nu en later even duur zijn; maar zodra er ná livegang ooit gedeactiveerd is mét scores, vergt herstel ook een herbereken-pass over echte data.
- **(c)** De rechtenkeuze kan strikt genomen ná livegang; de engine-asymmetrie en het onafsluitbare "Dit valt op"-punt kunnen alleen wachten zolang **niemand** de Deactiveren-knop gebruikt — en die staat voor elke medewerker klaar.

---

## 2B — De naam van de tegenpartij (P50-2)

### B1 — Repo-brede inventaris: 1 echte treffer, 2 verwante gevallen

| # | Vindplaats | Limiet | Wat er buiten de limiet gebeurt |
|---|---|---|---|
| 1 (treffer) | `KoppelingSectie.vue:73-82` `_zorgCompNamen` — `api.componenten.lijst({limit: 100})` → id→naam-map; lookup `?? ''` (`:72`) | 100 (backend capt op `le=100`, `routes/component.py:46`; default-sortering `created_at asc`, `:48-49` → de **100 oudste**) | tegenpartij-cel rendert **leeg** (`:393`, `:422`) — geen "—", geen fout |
| 2 (verwant) | `ContractLijst.vue:85` `laadBronnen` — `api.leveranciers.lijst({limit: 100})` voedt het leverancier-**filter**-dropdown (`:198-200`); de rij-naam zelf komt server-side (`leverancier_naam`) | 100 | leverancier 101+ ontbreekt als **filteroptie** (statische select, niet zoekend) — er valt niet op te filteren |
| 3 (verwant) | `GebruikersbeheerView.vue:66` — `api.gebruikers.lijst({limit: 100})`, platte lijst zonder cursor (comment `:65`) | 100 | gebruiker 101+ wordt in het beheerscherm **nooit getoond** |

**Expliciet niet geraakt** (gemeten en vrijgesproken): `WerkvoorraadPlekView.vue:26-51`, `BedrijfsfunctieLijst.vue:103-115`, `ArchitectuurLagenView.vue:38-57` (pagineren álle pagina's door met een `after`-lus); `ComponentBedrijfsfunctieSectie.vue:97-108` (per-id `haal`, geen limiet); alle `ZoekSelect`-pickers (server-side zoek + "verfijn"-regel, `ZoekSelect.vue:74`). **Conclusie: geen patroon maar één echte naam-resolutie-plek + twee losse limiet-100-lijsten.**

### B2 — Schermen en breekpunt

- **ComponentDetail → tabblad Koppelingen** (route `component-detail`, `router/index.js:122`; sectie gemount `ComponentDetail.vue:800`): breekt vanaf **>100 componenten in de tenant**, zodra een tegenpartij buiten de 100 oudste valt. De gebruiker ziet een koppeling-rij met een **lege tegenpartij-kolom** — de rij bestaat, het doel is naamloos.
- ContractLijst-filter: breekt vanaf >100 leveranciers (ontbrekende filteroptie). Gebruikersbeheer: breekt vanaf >100 gebruikers (onzichtbare accounts).
- De kaart is **niet** via dit pad geraakt (eigen subgraaf-endpoint levert nodes mét namen).

### B3 — Huidige tenant

**24 componenten** — ruim onder 100; daarom ziet vandaag niemand iets.

### B4 — Bestaat de weg om namen mee te leveren?

Ja, tweevoudig, zonder nieuwe machinerie (alleen vastgesteld, niet gebouwd): (1) het **naam-in-read-patroon** (gejoinde alias) bestaat al in ≥7 read-schemas (`component_contract.py:79` `applicatie_naam`, `functievervulling.py:88,106`, `organisatiegebruik.py:45`, `procesvervulling.py:100`, `blokkade.py:148`, `contract.py:152,178,228`, `roltoewijzing.py:39,43`); (2) de generieke batch-resolver `services/entiteit_resolutie.py` (N+1-vrij, tenant-scoped) kent `Component` en `Relatie` al. `RelatieRead` draagt nu **geen** endpoint-namen (`schemas/relatie.py:47-59`) — de frontend-comment bevestigt dat (`KoppelingSectie.vue:9-10`).

### De drie vragen (B)

- **(a)** Ja — wat nu onzichtbaar is wordt met een echt landschap (>100 componenten) een **stil fout antwoord**: een koppeling naar een naamloos component, zonder enige melding.
- **(b)** Er is geen datakant — het is een contract-/frontendfix die nu en later even duur is; "gratis" speelt hier niet.
- **(c)** Formeel kan het ná livegang, maar alleen zolang de tenant onder de 100 componenten blijft — een echte gemeente zit daar snel overheen, dus praktisch: vóór.

---

## 2C — Kolom `organisatiegebruik.applicatie_id` (P50-3)

### C1 — Vindplaatsen (alleen de organisatiegebruik-`applicatie_id`; andere uitgesplitst)

| Laag | Aantal | Kern-vindplaatsen |
|---|---|---|
| Model | 5 (+ FK-naam `fk_organisatiegebruik_applicatie`) | `models.py:465,471,480,488,495` (:471 documenteert zelf: "component, élk componenttype … de kolomnaam is historisch") |
| Migraties | 4 (+ FK-naam) | `0049_adr036_organisatiegebruik.py:42,45,49,57` |
| Services | ±32 | `organisatiegebruik_service.py` (19×) · `landschapskaart_service.py` (8×) · `registratiegaten_service.py` (4×) · `procesvervulling_service.py:364` |
| Schemas | 2 | `organisatiegebruik.py:17` (Create) · `:26` (Read) — **API-contract-veld** |
| Routes | 7 | `routes/organisatiegebruik.py:3,39,46,54-57` |
| Seed | 2 | `dev_seed_testdata.py:1368,1370` |
| Tests | ±37 | backend ±27 · frontend 10 |
| Frontend/api-client | 5 | `api.js:206` (whitelist) · `OrganisatiegebruikSectie.vue:57,92` · `LandschapskaartView.vue:1649` · `SignaleringView.vue:57` |

**Voor de gebruiker zichtbaar: ja, 2×.** (1) Letterlijk in een foutmelding: 400 `ONGELDIGE_FILTER` met bericht *"Geef precies één van applicatie_id of organisatie_id op."* (`routes/organisatiegebruik.py:55`). (2) Als wire-contract: request-/responsveld én URL-queryparam `?applicatie_id=` die drie schermen lezen/schrijven. Niet als kolomkop op een scherm.

### C2 — Kosten vandaag versus ná livegang

- **Vandaag:** één kolom-rename-migratie (`ALTER TABLE … RENAME COLUMN`, geen datatransformatie — er is alleen testdata) + hernoemen in ±37 niet-test-vindplaatsen (model/service/schema/route/api-client/3 views) + ±37 test-vindplaatsen + reseed. **Precedent bestaat**: gebruikersgroep deed exact deze rename (`applicatie_id` → `component_id`, ADR-055) — de blauwdruk ligt er.
- **Ná livegang:** de kolom-rename zelf blijft een lichte metadata-migratie, maar het **API-veld is dan een extern contract** met echte afnemers: hernoemen vergt een gecoördineerde deploy of een overgangsperiode met beide veldnamen, en elke afwijking raakt draaiende schermen van echte gebruikers.

### C3 — Meer namen die "applicatie" zeggen waar élk component geldt (7 gevallen)

1. `organisatiegebruik.applicatie_id` (het C1-onderwerp) — bewijs `models.py:471`.
2. Foutcode **`GROEP_ZONDER_APPLICATIE`** (`gebruikersgroep_service.py:442`) — berichttekst is al "component", de machine-leesbare CODE niet (comment `:437-441` benoemt dit als opvolgpunt).
3. API-veld **`heeft_applicatie_subtype`** (`schemas/component.py:169,206`; gezet in `component_service.py:268,594`) — waarde is eerlijk ("type == applicatie") maar de naam zegt "subtype" terwijl de subtabel niet meer bestaat; frontend leest hem nog (`ComponentDetail.vue:95`, `ComponentLijst.vue:890`).
4. Functie-/endpointnaam **`lijst_voor_applicatie`/`lijstVoorApplicatie`** + queryparam `applicatie_id` (`organisatiegebruik_service.py:207`, `routes/organisatiegebruik.py:57`, `api.js:206`) — component-breed gebruikt (`OrganisatiegebruikSectie.vue:57` geeft `props.componentId` door).
5. FK-constraintnaam **`fk_organisatiegebruik_applicatie`** (`models.py:489`, migratie 0049:56) — wijst naar `element`, niet naar een applicatie-tabel.
6. Respons-/sorteerveld **`applicatie_naam`** in het blokkadesoverzicht (`schemas/blokkade.py:48,148`; `BlokkadeOverzichtView.vue:36,41,174`) — kolomkop is al "Component", de veld-/sorteersleutel in de API niet.
7. Contract-read-zijde **`ApplicatieContractRead`/`applicatie_id`/`applicatie_naam` + route `/{contract}/applicaties`** (`schemas/applicatie_contract.py:46,78-79`, `contract_service.py:511-540`, `ContractDetail.vue:227`) — deels: het id is een component-id, maar de read filtert op profiel-dragende componenten; de create-zijde is al hernoemd (`ComponentContractCreate.component_id`).

**Geen geval** (echt applicatie-only): `datatype.applicatie_id` — harde type-gate (`datatype_service.py:148`).

### De drie vragen (C)

- **(a)** Nauwelijks — de gebruiker ziet de naam alleen in één foutmelding en in de URL; het risico is verwarring voor beheerders/afnemers, geen fout antwoord op het scherm.
- **(b)** Ja — dit is het klassieke "nu nog gratis"-geval: vandaag een rename zonder datamigratie of contractzorg, ná livegang een externe contractwijziging met gecoördineerde deploy.
- **(c)** Technisch kan het ná livegang, maar tegen structureel hogere kosten; als het ooit moet, is vóór livegang het goedkoopste moment — besluit Bert (schema-rakend, eigen gate).

---

## 2D — Keuzelijsten: beheerbaar of vast? (P50-4)

### D1 — De tabel (31 keuzelijsten; actieve-optie-aantallen live gemeten)

**Catalogus-gedreven — beheerbaar zonder deploy (12):**

| Keuzelijst | Waar | Bron | Beheerscherm | # actief (DB) |
|---|---|---|---|---|
| Componenttype | ComponentFormulier:376 + lijstfilter | `componentconfig_optie` dim componenttype | ComponentConfigBeheer | 8 |
| Componentrol | ComponentFormulier:484 | `componentrol_optie` | RolConfigBeheer | 4 |
| BIV-schaal (B/I/V) | ComponentFormulier:510 + filter | `biv_schaal_optie` | BivConfigBeheer | 3 |
| Contract-dekking | ContractFormulier:300 + filter | `contractconfig_optie` dim dekking | ContractConfigBeheer | 3 |
| Contract-kostenmodel | ContractFormulier:308 + filter | `contractconfig_optie` dim kostenmodel | ContractConfigBeheer | 3 |
| Contract-relatierol | ContractSectie:145 | `relatiekenmerk_optie` dim relatie_rol | RelatieKenmerkConfigBeheer | 3 |
| Beheerrol (roltoewijzing) | PartijRollenSectie:172 | `relatiekenmerk_optie` dim beheerrol | RelatieKenmerkConfigBeheer | 9 |
| Partijsoort | PartijFormulier:343 | `partijsoort_optie` | PartijsoortConfigBeheer | 3 |
| Checklist-antwoordopties | ChecklistscoreSectie:480,488 | `checklistvraag_optie` (tenant-RLS) | ChecklistConfigBeheer | per vraag |
| Vraagbetekenis | ChecklistConfigBeheer | `vraagbetekenis_optie` | VraagBetekenisConfigBeheer | 1 |
| Applicatiefunctie | organisatiegebruik-secties | `applicatiefunctie_optie` | ApplicatiefunctieConfigBeheer | 5 |
| Dispositie (historisch) | geen formulier meer (ADR-046) | `relatiekenmerk_optie` dim dispositie | RelatieKenmerkConfigBeheer | **0** |

**Code-/seedvast — alleen wijzigbaar met codewijziging + deploy (±14):**

| Keuzelijst | Waar | Bron | # opties |
|---|---|---|---|
| Hostingmodel | ComponentFormulier + filter | enum `HostingModel` (models.py:34) | 7 |
| Levensfase | ComponentFormulier + filter | enum `Levensfase` (models.py:71) | 3 |
| Bedoeling (migratiepad) | ComponentFormulier + filter | enum `Migratiepad` (models.py:58) | 4 |
| Complexiteit / Prioriteit | ComponentFormulier + filter | enum `NiveauEnum` (models.py:52) | 3 |
| Beoordelingsstatus | lijstfilter (engine-gezet) | enum `LifecycleStatus` (models.py:44) | 4 zichtbaar / 5 |
| **Koppeling: protocol** | KoppelingSectie:483 | enum `Koppelprotocol` (models.py:99) | 5 |
| **Koppeling: richting** | KoppelingSectie:483 | enum `Koppelrichting` (models.py:94) | 2 |
| **Koppeling: impact bij verbreking** | KoppelingSectie:483 | enum `ImpactVerbreking` (models.py:107) | 4 |
| Datatype-categorie | DatatypeSectie:255 | enum `DatatypeCategorie` (models.py:85) | 6 |
| Contracttype | ContractFormulier:260 + filter | enum `ContractType` (models.py:151) | 3 |
| Partij-aard | PartijFormulier:255 + filter | enum `PartijAard` (models.py:219) | 4 |
| Partij-scope | PartijFormulier:270 | enum `PartijScope` (models.py:232) | 2 |
| Checklist-score | ChecklistscoreSectie:431 | enum `ChecklistScore` (models.py:114) | 4 |
| Gebruikersrol · Gap-lid-type · Functie-oordeel | Gebruikersbeheer · GapDetail:346 · ComponentFormulier:456 | frontend-constanten/enum | 4 · 2 · 2 |

(ArchiMate-laag-filter: afgeleid uit de componentconfig-typering — de typering per type is beheerbaar, de labelmap niet.)

### D2 — De protocol-lijst: code-vast, drievoudig

Een koppeling ís een `flow`-relatie; protocol/richting/impact leven als jsonb-kenmerk. De catalogus-declaratie verwijst expliciet naar **code-enums** (`seed_componentconfig.py:63-68`: `"enum": "koppelprotocol"` enz.), en het formulier haalt de opties **niet uit een endpoint** maar uit de frontend-labelmaps (`KoppelingSectie.vue:162-171`, comment: "vaste enums … geen apart opties-endpoint meer"). **Een waarde toevoegen zonder codewijziging + deploy kan niet** — het vergt de Python-enum (models.py), een DB-enum-migratie én de labelmap (labels.js). Zelfde antwoord voor richting en impact_bij_verbreking.

### D3 — Beheerbare bron zonder beheerscherm: **0**

Alle 10 catalogus-tabellen hebben een beheerscherm (componentconfig/contractconfig/relatiekenmerk/partijsoort/vraagbetekenis/componentrol/biv_schaal/applicatiefunctie/referentiemodel + tenant-checklistvraag_optie). Het DC014-gat is dicht. Nuance (spiegelbeeld): de **dispositie**-dimensie heeft wél een scherm maar geen enkel formulier meer dat hem gebruikt (0 actieve opties — consistent met de ADR-046-afbouw).

### D4 — ADR-026: hetzelfde patroon, met één bewuste afwijking

De typering per componenttype (element/laag/aspect) is **beheerbaar via ComponentConfigBeheer** (dialoogvelden `ComponentConfigBeheer.vue:141-158`, opties uit `/platform/componentconfig/typering-opties`) — zelfde catalogus+scherm-patroon. Afwijking: de **waardenset** (TOEGESTANE_ELEMENTEN/LAGEN/ASPECTEN, `services/archimate_typing.py`) is bewust code-vast (ADR-026 besluit 1). Een type ánders typeren = data; een nieuwe ArchiMate-code = deploy. Dat is dezelfde soort knip als bij protocol — met dit verschil dat hij bij ADR-026 als besluit gedocumenteerd is en bij de koppeling-enums niet.

### De drie vragen (D)

- **(a)** Beperkt — een ontbrekende protocol-waarde geeft geen fout antwoord, maar dwingt een echte gemeente haar koppelingen in "overig" te proppen (5 vaste waarden), wat de registratie verarmt zonder dat iemand het merkt.
- **(b)** Een enum → catalogus-verbouwing is nu goedkoper (geen bestaande kenmerk-waarden om te converteren), maar niet "gratis versus datamigratie" op de schaal van C.
- **(c)** Ja — dit kan ná livegang (een catalogus-verbouwing per lijst); de functionele vraag *welke lijsten open horen* is een besluit van Bert en staat los van het moment.

---

## 2E — Dev-instellingen die niet mee mogen naar productie

| Punt | Waar + dev-waarde | Productiewaarde | Houdt iets het tegen? |
|---|---|---|---|
| `changeme_dev`-secrets | **31 vindplaatsen**: `.env.example`, `docker-compose.yml`, `init-db/01+02` (DB-rollen), realm-JSON (client-secrets), `backend/.env`, `alembic.ini` — én als **code-default**: `config.py:20` (`keycloak_admin_password`), `:22` (`likara_provisioning_secret`), `:69` (`minio_root_password="changeme_dev_only"`) | echte secrets | **Stopt niet — leunt op een handeling.** `validate_startup_config` (`config.py:84-107`) checkt alleen *aanwezigheid* van 8 velden, geen waarde; de drie code-defaults vullen in productie stil `changeme_dev` in als de env ontbreekt. (= OP-14) |
| `COOKIE_SECURE` | code-default **True** (`config.py:37`); dev-override `false` in `docker-compose.yml:170` én `backend/.env:14` | `true` | **Stopt half vanzelf** — de code-default is veilig, maar niets weigert een expliciete `false` in een productie-env; hergebruik van de dev-compose/.env reist stil mee. |
| `LIKARA_TEST_MODE` | code-default **False** (`config.py:62`); staat níét in docker-compose en níét in backend/.env | uit | **Stopt vanzelf** — moet expliciet aangezet worden. |
| Testgebruikers in de realm | **9 accounts** in `likara-realm.json`: viewer/medewerker/beheerder/auditor-test, j.devries, p.vandijk, m.bakker, platformbeheerder/platformoperator-test (+ provisioning-service-account), wachtwoorden `changeme_dev` | niet aanwezig / eigen productie-realm | **Stopt niet — leunt op een handeling** (realm-import is juist het deploy-pad; niets scheidt dev- van productie-realm). |
| MFA-policy | realm: `otpPolicyType` niet gezet, `CONFIGURE_TOTP` enabled maar `defaultAction=false`, standaard `browser`-flow → TOTP **optioneel** | MFA verplicht (platform-uitgangspunt, NCSC) | **Stopt niet — leunt op realm-hardening** (OP-28). |
| `revoke-refresh-token` | **niet gezet** in realm-JSON → Keycloak-default uit → refresh-token-reuse-detectie (ADR-015 B3) inactief | aan | **Stopt niet — leunt op een handeling** (bekend als voorwaarde-noot CD007/OP-14). |
| Dev-seed op productie-DB | `dev_seed_testdata.py` verbindt via de app-config (`get_worker_session`, `:44`, `main():1899-1940`); **geen omgevingsguard, geen bevestigingsvraag** | onmogelijk op productie | **Stopt niet — leunt op een handeling.** OPVOLGPUNTEN noemt hem "bewust dev-only/prod-veilig" — dat klopt alleen in de zin dat hij niet automatisch draait; wie hem met een productie-`DATABASE_URL` start, seedt productie. |

---

## 2F — Wat verandert er als "alleen testdata" vervalt?

| Afspraak | Vindplaats | Blijft waar naast productie? |
|---|---|---|
| "Een schemawijziging vergt nooit een databehoud-migratie" | `.claude/skills/likara/likara-db/SKILL.md` §Testdata-regel (DC016) | **Nee.** Naast een productieomgeving vergen schemawijzigingen expand/contract-datamigraties; de regel moet vóór livegang worden herschreven tot een dev-only-regel, anders stuurt hij een sessie fout. |
| Reset = volume weg + reseed | `docs/LOKAAL-TESTEN.md:43-48,183-184` (volume-rm-route; `down -v` op Deny) | **Blijft waar voor lokaal/dev**, maar "reseed lost het op" is geen herstelpad meer zodra er productie is — daar geldt de backup/restore-keten (pg_dump bestaat al, OP-28 noemt offsite backups). |
| Live-DB-tests schrijven/wissen in de dev-tenant | **60** testbestanden met skipif-probe; **81** verwijzingen naar tenant `11111111-…` in module-tests; teardown o.a. `DELETE FROM element` | **Alleen houdbaar met harde omgevingsscheiding.** De tests schrijven in de DB waar `DATABASE_URL` naar wijst; er is geen "dit is geen productie"-guard. Vóór livegang borgen dat een testrun nooit productie-credentials kan zien. |
| Dode seed-paden met echt lijkende namen | `_seed_technische_laag`: **bestaat nog** (`dev_seed_testdata.py:650`, **0 aanroepen**). `_seed_tweede_type`: **bestaat niet meer** — verwijderd, met borgingstest (`test_adr045_ondersteunt_werk.py:217-221`) | `_seed_tweede_type` is al opgeruimd (afwijking t.o.v. de opdrachttekst — melden, zie §5). `_seed_technische_laag` is dood maar heeft **geen** absentie-borging; zolang hij niet wordt aangeroepen zaait hij niets — opruimen is hygiëne, geen productieblokker. |

---

## 2G — De rest van de vóór-productie-lijst

### G1 — OPVOLGPUNTEN.md getoetst tegen de code

| Punt | Stand in de code |
|---|---|
| §"VÓÓR PRODUCTIE oplossen" (r2178): kolom `applicatie_id` | **Bestaat nog** (gemeten in C) — open. |
| §"VÓÓR PRODUCTIE": namenkaart KoppelingSectie limit 100 | **Bestaat nog** (gemeten in B) — open. |
| P50-1 (r16) | Gemeten (A). **De verwachting "platformbeheer" in het punt klopt niet** — tenant-bevoegdheid, bewust (ADR-022 W1). |
| P50-2 (r32) | Gemeten (B) — bevestigd, 1 treffer + 2 verwante. |
| P50-3 (r40) | Gemeten (C) — bevestigd. |
| P50-4 (r46) | Gemeten (D) — protocol inderdaad code-vast; "catalogus = beheerbaar via beheerscherm" klopt volledig (10/10). |
| Kleine punten LI047: `GROEP_ZONDER_APPLICATIE` · `heeft_applicatie_subtype` · "door onbekend" | Alle drie **bestaan nog** (`gebruikersgroep_service.py:442` · `schemas/component.py:169,206` · `MigratiegereedheidSectie.vue:218`) — kloppen als open. |
| OP-14 dev-credentials (r1756) | **Open en klopt** (31 changeme-vindplaatsen + 9 testaccounts, zie E). |
| OP-28 VPS-deployment (r1846) | Open (compose-variant/HTTPS/KC-production-mode/offsite backups). **Maar de voorwaarden-zin is verouderd**: "ADR-006 (audit-trail) en #16 (user-/tenantmanagement)" staan als voorwaarden terwijl beide **gebouwd** zijn (`backend/app/core/audit.py` bestaat; `GebruikersbeheerView.vue` bestaat) — het punt leest zwaarder dan het is. |

### G2 — Nieuw: vóór-livegang-kandidaten die nergens op de lijst staan

1. **Engine telt scores op gedeactiveerde vragen mee** (`lifecycle_service.py:111-128`, zie A2.3): een component kan migratieklaar tonen terwijl de zichtbare checklist onbeantwoord is. (a) Ja — fout statusantwoord op het scherm; (b) codefix, nu en later even duur, maar na echt gebruik van Deactiveren is ook een herbereken-pass op echte data nodig; (c) alleen uitstelbaar zolang niemand deactiveert.
2. **"Dit valt op" telt nee/deels op gedeactiveerde vragen met een dode route** (`component_open_punten_service.py:94-108`, zie A3): een onafsluitbaar open punt. Zelfde a/b/c als hierboven; testdekking 0.
3. **De `tenant`-registry is leeg terwijl er tenant-data bestaat** (registry: 0 rijen; element-data: 1 tenant): de dev-seed registreert zijn tenant niet, en platform-brede operaties die de registry enumereren — de checklist_dragend-backfill (`componentconfig_service.py:110-113`) — raken dan **0 tenants** en slaan bestaande data stil over. (a) In productie alleen een risico als een tenant buiten de registry om data krijgt — precies wat de dev-inrichting nu demonstreert; (b) provisioning-afspraak, geen migratie; (c) moet als inrichtingsregel helder zijn vóór de eerste echte tenant.
4. **ChecklistscoreSectie laadt scores met `limit: 100`** (`ChecklistscoreSectie.vue:173,185`): bij >100 vragen van één type tonen bestaande antwoorden zich stil als "niet gescoord". Vandaag max 89 per type, maar het vraagbeheer laat vragen toevoegen. (a) Ja, zelfde stilte-familie als B; (b) geen datakant; (c) kan na livegang zolang geen type boven de 100 vragen komt — begrensd risico, wel noteren.
5. **Gebruikersbeheer toont maximaal 100 accounts** en **ContractLijst-filter maximaal 100 leveranciers** (B1 #2/#3). (a) Ja bij echte aantallen; (b) geen datakant; (c) kan na livegang bij een kleine organisatie — zelfde familie, zelfde afweging.

---

## 3. Overzichtstabel (gesorteerd op wat de gebruiker het hardst raakt)

| Punt | Wat de gebruiker merkt | Karakter veranderd? | Nu nog gratis? | Kan na livegang? |
|---|---|---|---|---|
| B — naamloze tegenpartij (limit 100) | Koppeling wijst naar een component **zonder naam**; geen fout, dus niemand meldt het | Ja — van onzichtbaar naar stil fout antwoord bij >100 componenten | n.v.t. (geen datakant) | Alleen zolang <100 componenten — praktisch: nee |
| A — Deactiveren: poort + gevolg | Elke **medewerker** kan de tenant-vragenlijst wijzigen; antwoorden verdwijnen uit beeld, status kan vals groen worden, blokkade/"Dit valt op"-punt onafsluitbaar | Ja — van ontwerpvraag naar rechten- én waarheidsrisico | Deels (codefixes; na echt gebruik ook herbereken-pass) | Alleen zolang niemand de knop gebruikt — feitelijk: nee |
| G2-1/2 — engine- en open-punten-telling × inactieve vragen | Status/opsomming klopt niet met wat hij op de checklist ziet | Ja (volgt uit A) | Ja (codefix + test) | Zie A |
| E — secrets/testusers/MFA/revoke | Buitenstaander kan met `changeme_dev`/testaccount binnen; sessies zwakker dan beloofd | Ja — van dev-gemak naar beveiligingsgat | n.v.t. | **Nee** — hard vóór livegang (OP-14/OP-28) |
| E — dev-seed zonder guard | Eén verkeerde env en de productie-DB krijgt BvoWB-demodata | Ja | Ja (guard is triviaal klein, maar bouwen = besluit) | Nee — leunt anders op alleen discipline |
| C — `applicatie_id`-kolom + 6 verwante namen | Vrijwel niets (één foutmelding, URL-veld); vooral toekomstige verwarring | Beperkt | **Ja — laatste goedkope moment** | Ja, maar structureel duurder (contractwijziging) |
| G2-3 — lege tenant-registry | Niets — tot een platform-brede actie zijn tenant stil overslaat | Ja (provisioning wordt echt) | Ja (afspraak/inrichting) | Moet helder zijn vóór de eerste echte tenant |
| D — protocol/richting/impact code-vast | Kan zijn eigen koppelprotocol niet kwijt → "overig" | Nee (was al zo; weegt zwaarder) | Deels (enum→catalogus nu iets goedkoper) | **Ja** — besluit Bert wélke lijsten open horen |
| F — testdata-regel + testomgeving-scheiding | Niets direct; raakt de werkwijze | Ja — de aanname zelf vervalt | Ja (documentatie/afspraak) | Regel herschrijven + env-scheiding: vóór; rest: na |
| G2-4/5 — overige limit-100-lijsten | >100 vragen/gebruikers/leveranciers: stil onvolledig | Ja, zelfde stilte-familie als B | n.v.t. | Ja, zolang de aantallen klein blijven — wel noteren |

---

## 4. Niet vastgesteld

- **Geen browserverificatie** — dit checkpoint is read-only code + database; al het beschreven schermgedrag (lege naam, verdwenen rij, teller-gedrag) is uit de code afgeleid, niet visueel nagespeeld. De skills-norm (browsercheck als sluitpunt) geldt onverkort voor de reparatie-slices.
- **De naam van de gemeten tenant** — niet vaststelbaar: de `tenant`-registry is leeg (§G2-3); alleen het id is bekend.
- **Het geplande productie-deploypad** (eigen realm? eigen compose? beheerd secret-store?) — OP-28 is nog niet uitgewerkt; de E-antwoorden meten de huidige repo-stand, niet een toekomstige deploy-inrichting.
- **Gedrag van `docker exec`-loze omgevingen** — alle DB-metingen liepen via de draaiende dev-stack; er is geen tweede omgeving gemeten.

## 5. Tegenspraken (code wint — meetregel 5)

1. **OPVOLGPUNTEN P50-1** verwacht platformbeheer op vraagbeheer; de code maakt het een **tenant**-bevoegdheid (medewerker+beheerder), bewust en gedocumenteerd (`rbac.py:214-218`, ADR-022 W1; likara-db-skill klopt). Het opvolgpunt corrigeren.
2. **De opdrachttekst A3** veronderstelt dat de organisatienorm een *vraag* verplicht kan stellen; de norm kent alleen **feiten** (`HARDE_FEITEN`, 10 stuks). Het gat bestaat wél, maar in "Dit valt op" (nee/deels-telling zonder actief-filter), niet in "Dit moet nog".
3. **De opdrachttekst F** noemt `_seed_tweede_type` als dood seed-pad; die is al **verwijderd** en de afwezigheid is getest (`test_adr045_ondersteunt_werk.py:217-221`). Alleen `_seed_technische_laag` bestaat nog (dood, 0 aanroepen).
4. **OP-28** noemt ADR-006 (audit) en #16 (gebruikersbeheer) als openstaande productie-voorwaarden; **beide zijn gebouwd** (`backend/app/core/audit.py`; `modules/.../views/GebruikersbeheerView.vue`). De voorwaarden-zin is verouderd.
5. **OPVOLGPUNTEN r1840** noemt de dev-seed "bewust dev-only/prod-veilig"; feitelijk is hij alleen *niet-automatisch* — er is geen enkele guard tegen draaien op een productie-URL.
6. **De waarneming "raakt 17 componenten"** (P50-1/opdracht A): de huidige seed telt **20** applicatie-componenten; de 17 was een oudere datastand — de tellogica zelf (`impact_telling`) klopt.
7. **LI058-skilltekst** ("de backfill enumereert de Tenant-registry") beschrijft het mechanisme correct, maar de dev-inrichting wijkt af: de dev-tenant stáát niet in die registry, dus de beschreven backfill raakt in dev 0 tenants (de dev-seed roept hem daarom zelf per tenant aan).
