# Feitenrapport — gate 1b: het inlezen van een referentiemodel

| | |
|---|---|
| **Opdracht** | LI039-checkpoint-gate-1b-inlezen (read-only feitencheck) |
| **Datum** | 2026-07-12 |
| **Basis** | Commit `605299a` (gate 1a geland), werktree schoon, alembic head `0062_adr043_bedrijfsfunctie` |
| **Modus** | Uitsluitend gelezen; niets gewijzigd, geen dependency, geen download, geen commit |

---

## A. Het modellenaanbod — wat staat er, wat ontbreekt

### A.1 De twee lagen zoals ze nu zijn

**Platform-aanbod `referentiemodel_optie`** (model `ReferentiemodelOptie`, `models.py:1062` e.v.; migratie `0061:47-66`):
- Velden: `id` (int, autoincrement), `optie_sleutel` String(60) UNIQUE (`uq_referentiemodel_optie`), `label` String(150), `herkomst` String(255), `versie` String(60), `volgorde`, `actief` (soft-deactivate). **Geen tenant_id, geen RLS.**
- Grants (0061:57-60): `REVOKE ALL … FROM lk_app` → `GRANT SELECT … lk_app` → `GRANT SELECT, INSERT, UPDATE … lk_platform` + sequence — **geen DELETE** (catalogus-recept).
- RBAC: `PlatformEntiteit.REFERENTIEMODELCONFIG` (`platform_rbac.py:42`; matrix :114-117 — beheerder **LAW**, operator **L**). Audit: `referentiemodel_optie` op `AUDIT_PLATFORM_ENTITEITEN` (`audit.py:91`).
- **Geen route, geen service, geen beheerscherm** — bewust gate-1b-scope (gate-1a-rapport).

**Tenant-instantie `referentiemodel`** (model `Referentiemodel`, `models.py:715` e.v.; migratie `0061:70-99`):
- Velden: `id` UUID, `tenant_id`, `model_sleutel` String(60) (app-side verwijzing naar `optie_sleutel`, géén harde FK — catalogus-conventie), `naam` String(150) + `versie` String(60) (ingelezen **snapshot**), `ingelezen_op` DateTime server_default now(), timestamps.
- `UNIQUE(tenant_id, id)` (composiet-FK-target voor `bedrijfsfunctie.bron_model_id`) + `UNIQUE(tenant_id, model_sleutel)` — **een herinlees werkt de bestaande rij bij, geen tweede rij per model**.
- FORCE RLS + `tenant_isolation` + lk_app S/I/U/D (0061:92-99). RBAC: `Entiteit.REFERENTIEMODEL` = `_INHOUD` (`rbac.py:62, :165`). Audit: op `AUDIT_TENANT_ENTITEITEN` (`audit.py:74`).
- **Geen route/service** — de rij ontstaat nu alleen via de dev-seed.

### A.2 Wat de seed zaait
- Platform-aanbod: `services/seed_referentiemodel.py` `_MODELLEN` = één rij `("gemma_bedrijfsfuncties", "GEMMA Bedrijfsfuncties", "VNG Realisatie — GEMMA Basisarchitectuur (gemmaonline.nl)", "GEMMA 2 (2025)")`; idempotent `ON CONFLICT (optie_sleutel) DO NOTHING`; byte-gelijk in migratie 0061 en via de `platform_init`-keten (`platform_init.py:32, :79-80`).
- Tenant-instantie: `dev_seed_testdata.py` sectie 16 — get-or-create op `model_sleutel='gemma_bedrijfsfuncties'`, naam/versie-snapshot; daarna 15 model-functies (bronsleutels als `besturend`, `dienstverlening`, …) + 1 eigen functie.

### A.3 Beheerscherm-patroon om te spiegelen
Jongste, volledigste spiegel: het **applicatiefunctieconfig**-beheer (ADR-042). Footprint uit de git-historie:
- Backend (commit `ddb7b7a`): `routes/applicatiefunctieconfig.py` (54 r) + `schemas/…` (61 r) + `services/…_service.py` (78 r) + `main.py`-registratie.
- Frontend (commit `3a65c3b`): `frontend/src/views/ApplicatiefunctieConfigBeheer.vue` (297 r) + `api.js`-client (+9) + `router/index.js` (+9, platform-child) + `BeheerLayout.vue`-nav (+8; huidige nav-rij: `BeheerLayout.vue:62-113`).
- **Kosten voor een Referentiemodel-aanbod-beheerscherm: ± 8 bestanden** (4 backend + 4 frontend + tests) — tabel, grants, RBAC-entiteit, audit én seed bestaan al (gate 1a); alleen route/schema/service/scherm ontbreken.

### A.4 Bestand-verwijzing — **bevestigd: alleen metadata**
De aanbod-rij draagt sleutel/label/herkomst/versie/volgorde/actief — **geen pad, geen URL, geen blob-verwijzing** (models.py-kolommenlijst hierboven; migratie 0061 idem). Waar het AMEFF-bestand leeft is volledig open (→ B).

---

## B. Waar komt het bestand vandaan? — de drie routes (feiten, geen keuze)

### B.1 Bestandsupload — bestaat niet
Geen `UploadFile`/multipart-route in `backend/app` of de module (grep leeg; ook al vastgesteld in het V039-rapport §E.1). `python-multipart` staat in requirements (:9) maar wordt door geen route gebruikt.

### B.2 MinIO — **dood in de stack**
- Infra bestaat: compose-service `lk-minio` (`docker-compose.yml:89-102`), api-env `MINIO_ENDPOINT_URL` (:165), settings (`config.py:66-69`), `boto3>=1.34.0` in `requirements.txt:16`.
- **Nul applicatielaag-gebruik**: geen enkel `boto3`-import, geen client-module, geen bucket-aanmaak, geen put/get in `backend/app` of de module (grep leeg buiten config.py). De "bucket-per-tenant"-conventie uit CLAUDE.md bestaat alléén als tekst; er is geen code die er ooit een bucket door heeft gezien.

### B.3 Meegeleverd bestand in de repo
- Er staat **geen enkel** `*.xml`-bestand in de repo (find leeg).
- **Precedent voor een meegeleverd, gevalideerd databestand bestaat wél**: `keycloak/realms/likara-realm.json` — in de repo, via volume-mount geïmporteerd bij stack-start. Alle overige referentiedata leeft als **code-seeds** (hardcoded lijsten in `services/seed_*.py`; checklist-baseline in `services/seed.py`).

### B.4 Kosten per route (feiten; het besluit is aan Bert)

| Route | Wat er al ligt | Wat er nieuw moet | Spanning met besluiten |
|---|---|---|---|
| **(i) Repo-bestand** (bv. `modules/bwb_ontvlechting/backend/data/gemma_bedrijfsfuncties.xml`, conventie sleutel→bestandsnaam of pad-kolom op het aanbod) | Realm-JSON-precedent; het aanbod ís al release-gecureerd (ADR-043 besluit 4: "aangeboden modellen zijn een productkeuze") | Alleen het bestand + een leespad in de parser (±1-2 raakpunten) | Nieuw model/versie = nieuwe release — dat is bij een gecureerd aanbod eerder een feature dan een beperking |
| **(ii) MinIO/blob** | Container + settings + boto3 (ongebruikt) | De **volledige applicatielaag**: client-module, bucket-conventie, put/get, upload-beheer voor de platformbeheerder, en de (CLAUDE.md-optionele) ClamAV-vraag komt in beeld (±8-12 raakpunten) | Vereist alsnog een upload-route (→ iii) of handmatig vullen buiten de app om |
| **(iii) Upload-endpoint** | Niets (python-multipart als slapende dependency) | Multipart-route + validatie + opslagkeuze (belandt daarna alsnog bij i of ii) | ADR-043 besluit 4: de "eigen bestand"-route bestaat als capaciteit maar **staat niet open** — een tenant-upload zou dat besluit doorbreken; een platform-upload is een kleiner conflict maar blijft nieuw oppervlak |

---

## C. XML-parse: dependency + veiligheid

1. **Aanwezig: niets.** `requirements.txt` bevat geen `lxml`/`defusedxml`; nergens in de backend wordt `xml.*` geïmporteerd (grep leeg; `git log -S "defusedxml"` matcht alleen het V039-feitenrapport-document). Alleen stdlib `xml.etree` is beschikbaar-en-ongebruikt.
2. **Kleinste veilige toevoeging: `defusedxml`** — pure-Python wrapper om de stdlib-parsers die entity-expansion/XXE/DTD-truuks blokkeert; geen C-build, minimale voetafdruk. Kale stdlib `xml.etree` weert niet alle entity-constructies defensief; ook een gecureerd bestand hoort defensief geparseerd (opdracht-uitgangspunt). `lxml` is zwaarder (C-dependency) en alleen nodig als er XSD-schema-validatie van het AMEFF-bestand gewenst is — dat is een afweging, geen noodzaak voor het lezen zelf.
3. **Precedent dependency-toevoeging**: `requirements.txt` is de enige registratieplek; de git-historie kent er maar één na de scaffold (`psycopg2-binary`, geland ín de ADR-011-gate-commit `b0a67d4`). Werkwijze dus: dependency in requirements + mee in de gate-commit; de `likara-api:local`-image moet daarna opnieuw gebouwd worden (`docker compose build`).

---

## D. Het formaat — wat de repo wél en niet weet

1. **ADR-023** noemt Open Exchange uitsluitend als **geparkeerde export-fase** ("latere additieve fase, buiten scope" — `ADR-023_archimate-uitlijning.md:4, :67, :141`). Er is **geen code en geen formaatkennis** aan de exportkant blijven hangen die de importkant kan hergebruiken. Het V038-feitenrapport (grond van ADR-043) bevat evenmin formaat-structuur (grep op formaat/organizations/identifier leeg).
2. **Wat de repo zegt** is dus beperkt tot: de motor leest "ArchiMate Open Exchange / AMEFF" (ADR-043:46, :200) en matcht op bronsleutel. Als algemene, **niet-repo-gefundeerde** schets (bij de bouw te verifiëren): een AMEFF-bestand is XML met een `<model>`-wortel, elementen onder `<elements>` met een `identifier`-attribuut + `xsi:type` (bv. BusinessFunction) + `<name>`/`<documentation>`-kinderen; de **boomstructuur zit niet op het element** maar in een aparte `<organizations>`-mappenstructuur (items met identifier-verwijzingen) en/of in composition-relaties onder `<relationships>`.
3. **Open feit (expliciet):** zie "Open feiten" onderaan — niets over de concrete GEMMA-export is uit de repo vast te stellen.

---

## E. Idempotent bijwerken op bronsleutel

1. **Upsert-patroon:** de codebase kent uitsluitend `pg_insert(...).on_conflict_do_nothing` (alle `seed_*.py`, bv. `seed_referentiemodel.py:36-38`) — dat is invoegen, **geen bijwerken**; `on_conflict_do_update` komt nergens voor (grep leeg). **Bepalend feit voor de bouw:** de audit-trail hangt op ORM-flush-hooks en ziet core-statements níét (LI035-les, `app/core/audit.py`) — een SQL-upsert zou de import **audit-onzichtbaar** maken. Een echte upsert op `(tenant_id, bron_model_id, bron_sleutel)` moet dus **ORM-matig** (select op de sleutel → setattr/aanmaken → commit), met de bestaande `uq_bedrijfsfunctie_bron` (models.py) als DB-backstop. Precedent voor exact die vorm: de bedrijfsfuncties-dev-seed (get-or-create op bronsleutel, `dev_seed_testdata.py` sectie 16) en de vul-als-leeg-verantwoordelijkenseed (:1559-1592, "vaste identiteit"-les LI037).
2. **Vervallen zetten:** set-verschil per model — rijen met `bron_model_id = <dit model>` waarvan de `bron_sleutel` niet in het bestand voorkomt → `vervallen = true`. Betrouwbaar: de sleutel is UNIQUE binnen het model en **eigen functies (bron NULL) vallen structureel buiten elke vergelijking** (CHECK `ck_bedrijfsfunctie_bron_paar`). Randgeval om bij de bouw te beslissen: een sleutel die in een latere versie **terugkeert** → `vervallen` weer false (symmetrie) of niet.
3. **Langs het slot, zonder het te verzwakken:** `MODELINHOUD_BESCHERMD` zit in `bedrijfsfunctie_service.werk_bij` (:196-206) en `.verwijder` (:218-227) — het **gebruikers-pad** (de route biedt alléén die functies aan). Het precedent voor een legitiem import-pad bestaat al in dezelfde service: `maak_aan` heeft keyword-only `bron_model_id`/`bron_sleutel`-parameters, in de docstring expliciet gemarkeerd als "het seed-/import-pad (gate 1b)" (:161-176). Het import-pad wordt dus een eigen service-functie náást `werk_bij` — de route-laag blijft onveranderd en het slot onverzwakt.
4. **Verhangen:** een `ouder_id`-UPDATE raakt de self-FK **niet** (`RESTRICT` geldt alleen bij DELETE van de ouder); de cyclus-preventie bestaat (`_zou_kring_maken` :117-137). **Aandachtspunt:** `_valideer_ouder` weigert een **vervallen** ouder (`VERVALLEN_NIET_KOPPELBAAR`, :139-160) — een import die eerst vervallen markeert en daarna verhangt (of andersom) moet zijn volgorde bewust kiezen of het import-pad die gebruikers-guard bewust niet laten gelden (bouwkeuze). De eigen registratie blijft ongemoeid: verhangen wijzigt alleen `ouder_id`; kinderen (ook eigen functies onder een model-functie) verhuizen mee; functie↔component-koppelingen bestaan pas in gate 2.

---

## F. Het voorbeeldscherm

1. **Bevestigd:** een "toon eerst wat er gaat gebeuren, bevestig dan"-patroon bestaat nergens (V039-rapport §E.4; gate 1a voegde niets toe).
2. **Dichtstbijzijnde spiegels:** de `KOPPELING_DUBBEL`-flow (server berekent → bevestigingsdialoog → hersubmit met vlag — een twee-staps-handeling over een server-uitkomst), `BevestigVerwijderDialog` (gedeelde bevestigingsvorm met de handeling leesbaar in de vraag), het overlay-formulier-patroon (Dialog-preset + footer-slot) en `MeldingBanner`. Alle vier herbruikbaar als bouwstenen; het voorbeeld-**inhoudsdeel** (tellingen + lijstjes) is nieuw.
3. **Dry-run-precedent: nee.** Dichtstbij qua vorm: de seed-tweedeling (pure, DB-vrije `bouw_*()`-functies naast idempotente `seed_*()`-appliers) en de read-only afleidingen (rollup). De vorm die het minst afwijkt: **één pure diff-functie** (geparste elementen + huidige model-rijen → `{nieuw, bijgewerkt, vervallen, ongewijzigd}`) die twee consumenten heeft — het voorbeeldscherm (tonen) en de apply-functie (uitvoeren). Eén berekening, twee gebruikers; nooit twee definities van "wat gaat er gebeuren" (de één-roll-up-bron-lijn).
4. **Wat is nu eerlijk telbaar:** nieuw / bijgewerkt / vervallen volledig; per vervallen functie bovendien **"heeft N onderliggende functies"** (subboom-leeswerk bestaat: `bedrijfsfunctie_service.subboom`), inclusief eigen functies eronder. **"N applicaties hangen er nog aan" is per definitie 0 tot gate 2** — het voorbeeldscherm kan dat onderdeel eerlijk weglaten of als "nog geen koppelingen" tonen; er is niets om te tellen.

---

## G. Rechten en stand

1. **Discrepantie om te beslissen:** `Entiteit.REFERENTIEMODEL` volgt het `_INHOUD`-patroon (`rbac.py:165`) — dus ook de **medewerker** heeft AANMAKEN/WIJZIGEN, terwijl ADR-043 besluit 5 zegt: *"het inlezen doet de tenant-**beheerder**"*. De matrix en het besluit sporen nu niet. Bestaand precedent voor beheerder-only tenant-rechten: `GEBRUIKERSBEHEER`/`TENANT_INSTELLINGEN` (`rbac.py:180-191`). Of het inlezen op de entiteit-matrix wordt aangescherpt dan wel op de route strenger geguard, is een gate-1b-ontwerpknoop. Platform-zijde klopt: `REFERENTIEMODELCONFIG` beheerder LAW / operator L (`platform_rbac.py:114-117`) — dat is het beheer van het **aanbod**, niet het inlezen.
2. **Stand:** werktree schoon; commit `605299a`; `alembic heads` = 1 (`0062_adr043_bedrijfsfunctie`). ✓

---

## De drie bestandsroutes (samenvatting B — géén keuze)

1. **Repo-bestand**: goedkoopst (±1-2 raakpunten bovenop de parser), realm-JSON-precedent, past bij het release-gecureerde aanbod; nieuw model = release.
2. **MinIO**: infra + boto3 liggen klaar maar de héle applicatielaag ontbreekt (±8-12 raakpunten) én er is alsnog een vul-route nodig; ClamAV-vraag komt in beeld.
3. **Upload-endpoint**: volledig nieuw oppervlak en spant met ADR-043 besluit 4 (de eigen-bestand-route staat bewust niet open); eindigt bovendien alsnog in opslagvraag (i) of (ii).

## Wat is nieuw terrein (grove kosten)

| Onderdeel | Nieuw/hergebruik | Grove omvang |
|---|---|---|
| **AMEFF-parser** | Volledig nieuw + `defusedxml`-dependency (rebuild image) | ±3-4 bestanden (parser-service, tests, requirements, evt. data-bestand) |
| **Diff/dry-run** | Nieuw, maar naar bestaand vorm-precedent (puur bouw_* naast applier) | ±2-3 bestanden (pure diff + tests) |
| **Import-apply (upsert op bronsleutel)** | Nieuw pad in de bestaande service (ORM-matig i.v.m. audit; `maak_aan`-bronparams bestaan al) | ±2-3 bestanden (service-uitbreiding + route + tests) |
| **Voorbeeldscherm + bevestigen** | Nieuw scherm-deel; dialoog-/banner-bouwstenen herbruikbaar | ±5-7 bestanden (backend route/schema, frontend view/dialoog, api.js, tests) |
| **Aanbod-beheerscherm (platform)** | Recept bestaat volledig (applicatiefunctieconfig-spiegel); tabel/RBAC/audit/seed al geland | ±8 bestanden |
| **Rechten-knoop inlezen** | Beslissing + 1-2 raakpunten (matrix of route-guard + teltest) | klein |

Totaal indicatief: **±20-27 raakpunten over ±15-20 bestanden**, exclusief de bestandsroute-keuze.

## Open feiten

1. **Het AMEFF-formaat zelf** — niets in de repo: de concrete GEMMA-exportvorm (zit de boom in `<organizations>` of in composition-relaties; welke identifier is stabiel genoeg als bronsleutel; draagt `<documentation>` de definitie; AMEFF-versie/namespaces/encoding; reizen de topgroeperingen als elementen of als mappen). **Empirisch verifiëren bij de bouw, tegen het echte bestand.**
2. **Terugkeer-semantiek**: of een vervallen sleutel die in een latere modelversie terugkomt de vlag weer verliest (symmetrie) — ontwerpkeuze.
3. **Rechten-knoop** (G.1): matrix vs. besluit 5 — te beslissen vóór de inlees-route er komt.
4. **Bestandsroute** (B) — het ontwerpbesluit voor Bert.
5. **MinIO-doodheid** is een code-feit van nu; of er elders (deploy-scripts, VPS) tóch iets naar MinIO schrijft is buiten de repo niet vast te stellen (niets in de repo wijst erop).
