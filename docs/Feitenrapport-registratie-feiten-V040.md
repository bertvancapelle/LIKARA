# Feitenrapport — registratie-feiten op objecten, met de plaatsing als eerste consument

| | |
|---|---|
| **Opdracht** | LI040-checkpoint-registratie-feiten (read-only feitencheck) |
| **Datum** | 2026-07-13 |
| **Commit** | `0e678a7` (V040) — werktree bevat de vier ongecommitte ADR-045-docs (ongemoeid gelaten); dit rapport is het enige nieuwe bestand |
| **Alembic head** | `0064_gate1b_inlees_voltooid` (1 head) |
| **Modus** | Read-only. DB-metingen als `lk_admin` (SELECT-only). |

---

## 1. Uitkomst in één zin

De code ondersteunt de werkhypothese — **"wie/wanneer" leeft in élk bestaand precedent als
eigenschap op het feit zelf** (klaarverklaring-kolommen, plateau-jsonb, impact_view-maker), de
audit is overal het vangnet eronder en nergens de leeslaag op de plek van het feit — **maar** de
harde B2-vraag heeft een tweeledig antwoord: `relatie.id` van een plaatsing **overleeft een
herinlees zolang de plaatsing in de bron blijft** (delta-import, rij wordt niet aangeraakt) en
**gaat verloren bij een verhangen plaatsing** (harde ORM-delete; terugkeer = nieuwe rij, nieuwe
id) — én er hangt vandaag nog géén enkele tabel aan `relatie.id`, dus dit spoor zou de eerste
zijn.

---

## 2. De knoop, beslecht met bewijs

**Vraag:** hoort "wie legde dit vast, en wanneer" bij het **feit** (kolom op de registratie) of
bij het **gedeelde spoor** (aparte tabel)?

**Wat de code laat zien — drie precedenten, alle drie kolom-op-feit:**

1. **`component_klaarverklaring`** (`models.py:1299-1309`): `verklaard_door_sub` (String 255,
   nullable — stabiele Keycloak-sub), `verklaard_door` (e-mail-fallback), `verklaard_op`
   (DateTime NOT NULL) én een **verplichte `reden`** (Text NOT NULL, `:1304`). Docstring
   (`:1279-1280`): elke statushandeling herstempelt door/op **server-side**. Dit is het
   volledigste precedent: wie + wanneer + waarom, op de rij zelf.
2. **Plateau-bevestiging** (`plateau_service.py:189-200`): `bevestigd_door = {"sub": …,
   "email": …}` + `bevestigd_op` (ISO-timestamp), server-side gestempeld, in het
   **jsonb-`kenmerken`-veld van de aggregation-relatie** — dus wie/wanneer op het feit, maar in
   jsonb i.p.v. echte kolommen. Historische kale strings blijven leesbaar via
   `pak_sub_email` (`actor_resolutie.py:24-33`).
3. **`impact_view`** (`models.py:1334-1337`): `maker_sub` + `maker_email`, server-side
   gestempeld, "nooit client-aanleverbaar" (docstring `:1320-1321`).

**Een apart-tabel-precedent voor wie/wanneer bestaat niet.** Het enige gedeelde spoor is de
audit-trail — en die is bewust iets anders:

- **Technisch dekt de audit "wie/wanneer" volledig**: `audit_log.actor_sub` (Text NOT NULL,
  `models.py:1609`), gezet via de request-ContextVar (`zet_audit_context`/`huidige_actor`,
  `app/core/tenant_context.py:49-77`), met `correlatie_id` per handeling; append-only,
  hash-keten. Bekend gat: ORM-only vangnet (core-writes onzichtbaar — LI035-skillfeit).
- **Maar hij is niet leesbaar op de plek van het feit, voor de mensen om wie het gaat:**
  - het centrale auditscherm is **beheerder/auditor-only** (`Entiteit.AUDITLOG`:
    viewer/medewerker = géén rechten, `rbac.py:193-198`) — de consultant (medewerker) mag er
    niet in;
  - de bredere ingang (objecthistorie, toegang-volgt-object) kent exact **zeven typen**
    (`routes/objecthistorie.py:40-48`): component, contract, partij, plateau, work_package,
    deliverable, gap. **`bedrijfsfunctie`, `relatie` (dus de plaatsing) en `proces` hebben géén
    ingang** — de route-comment (`:37-39`) sluit `relatie` expliciet uit ("geen eigen
    detailscherm / geen eigenstandige object-read");
  - de audit toont **technische per-veld-diffs**, geen verplichte reden ("waarom") en geen
    actueel oordeel — wie het huidige oordeel draagt moet je uit een handelingenreeks
    reconstrueren.

**Oordeel (met dit bewijs):** de codebase kent één consequent patroon — *het actuele feit draagt
zelf wie/wanneer (en waar dat besloten is: een verplichte reden); de audit is het onveranderlijke
verloop eronder.* De klaarverklaring-docstring formuleert die taakverdeling letterlijk: "het
klaar→open→klaar-verloop blijft terug te lezen via de append-only audit-trail (geen aparte
historie-tabel)" (`models.py:1280-1282`). "Wie/wanneer alleen in de audit" zou voor de plaatsing
bovendien vandaag **onbereikbaar** zijn voor een consultant (geen objecthistorie-ingang, geen
auditscherm-recht). Een tweede waarheid ontstaat er niet van: het feit draagt het **actuele**
antwoord, de audit het **verloop** — verschillende vragen. De werkhypothese ("wie/wanneer bij het
feit; toelichting + verwijzingen als gedeeld spoor") wordt door de eerste helft dus gedragen;
voor de tweede helft (het gedeelde spoor) bestaat **geen precedent** — dat zou de eerste
generieke registratie-tabel op een anker zijn (zie B2/B3).

---

## 3. A — Wie/wanneer (en vrije tekst) vandaag

### A1 — Inventaris van "wie deed dit"-vormen

| Plek | Vorm | Wat bewaard wordt | Vindplaats |
|---|---|---|---|
| `component_klaarverklaring` | **Echte kolommen op het feit** | `verklaard_door_sub` + `verklaard_door` (e-mail-fallback) + `verklaard_op` + **verplichte `reden`** | `models.py:1299-1309` |
| Plateau-bevestiging | **jsonb-kenmerk op de aggregation-relatie** | `bevestigd_door: {sub, email}` + `bevestigd_op` (ISO-string); historisch: kale e-mailstring | `plateau_service.py:189-200`, uitlezing `:222-236` |
| `impact_view` | Echte kolommen | `maker_sub` + `maker_email` (eigenaarschap, servicelaag-guard) | `models.py:1334-1337` |
| `gebruiker_voorkeur` | Echte kolom | `sub` als eigen-scope-sleutel (geen "wie legde vast" maar "van wie is dit") | `models.py` (ADR-041, migratie 0055) |
| Audit-trail | **Aparte append-only tabel** | `actor_sub` (NOT NULL) + `actor_email` + `correlatie_id` per handeling; per-veld-diff van mapped columns | `models.py:1600-1615`, `app/core/audit.py:146-157`, `tenant_context.py:49-77` |
| `actor_resolutie.py` | Gedeelde leeshulp | `pak_sub_email` (normaliseert dict/string), `resolveer_naam`/`resolveer_namen` (sub → persoonsnaam via `gebruiker_persoon`→`Partij`, e-mail-fallback, batch/N+1-vrij) | `services/actor_resolutie.py:24-50` |
| **`roltoewijzing`** | — | ⚠ **Scherp onderscheid:** draagt uitsluitend **wie de rol vervúlt** (`partij_id`/`object_id`/`rol`) — **niet wie de toewijzing vastlegde**. Alleen `created_at`/`updated_at` (TimestampMixin); geen actor-kolom. Wie het vastlegde staat alléén in de audit. | `models.py:1178-1210` |
| `procesvervulling` | — | Idem: het tripel + optionele `toelichting`; **geen actor-kolommen** | `models.py` (Procesvervulling: component_id/proces_id/applicatiefunctie/toelichting) |

### A2 — beantwoord in §2 (de knoop). Kern: kolom-op-feit-precedent = ja (klaarverklaring, bewezen); apart-tabel-precedent = nee; audit dekt technisch maar is voor de plaatsing onleesbaar op de plek van het feit en draagt geen reden.

### A3 — Waar leeft vrije tekst vandaag

| Veld | Vorm | Vindplaats |
|---|---|---|
| `proces.toelichting` | Text nullable; schema-grens **≤10.000** (`_optionele_tekst(v, 10_000)`) — lees/schrijf via het gewone proces-CRUD (tenant-rollen, `_INHOUD`) | model: `models.py` (Proces `:36` binnen de klasse); schema: `schemas/proces.py:36-39` |
| `checklistscore.bevinding` (+ `actie`) | Text nullable, ≤10.000 | `models.py` (Checklistscore), `schemas/checklistscore.py:86,113` |
| `relatie.omschrijving` | Text nullable — vrije tekst op élke relatie (dus ook op een plaatsing beschikbaar) | `models.py:320` |
| `bedrijfsfunctie.definitie` | Text nullable, ≤10.000 — maar **modelinhoud is read-only**: op bron-dragende functies 422 `MODELINHOUD_BESCHERMD`, en de herinlees **overschrijft** naam+definitie naar de bron (`voer_uit:378-381`) | `models.py:757+`, `schemas/bedrijfsfunctie.py:49,70` |
| **Eigen toelichting naast de bron-definitie op `bedrijfsfunctie`** | **Bestaat niet.** Er is geen tweede vrij-tekstveld en geen ander mechanisme; de ADR-043-besluit-5-laag ("afwijken doe je bíj het object, niet erin") is vandaag nergens gebouwd. | — |

---

## 4. B — De twee ankers

### B1 — Anker 1: element

- **Identiteit**: `element` met `UNIQUE(tenant_id, id)` — één gedeelde identiteitsruimte, FORCE
  RLS (ADR-023).
- **Het feitelijke FK-recept uit de laatste subtype-migratie** (`0062_adr043_bedrijfsfunctie.py`,
  het "proces-recept 0057 1-op-1"): kolommen incl. `tenant_id`; `UNIQUE(tenant_id, id)` als
  composiet-FK-target; composiet-FK `(tenant_id, id) → element(tenant_id, id)` **ON DELETE
  CASCADE**; `ENABLE` + `FORCE ROW LEVEL SECURITY` + policy `tenant_isolation` op
  `current_setting('app.tenant_id')::uuid`; `REVOKE ALL FROM lk_app` + `GRANT
  SELECT,INSERT,UPDATE,DELETE TO lk_app` (`0062:84-92`). Voor een **kind-tabel op een element**
  (geen subtype) is het spiegel-recept `component_klaarverklaring`/`roltoewijzing`: eigen
  UUID-PK + composiet-FK `(tenant_id, <object>_id) → element` CASCADE (`models.py:1293-1297`,
  `:1197-1206`).
- **Consumenten — allemaal element-subtypes, geverifieerd**: component
  (`fk_component_element`, `models.py:338`), contract (`fk_contract_element`, `:1386`), partij
  (`fk_partij_element`, `:1004`), proces (`fk_proces_element`, `:663`), bedrijfsfunctie
  (`fk_bedrijfsfunctie_element`, `:798`). Eén element-anker dekt ze dus alle vijf (plus
  datatype/gebruikersgroep/plateau/gap/work_package/deliverable).

### B2 — Anker 2: koppeling (`relatie.id`) — en de harde vraag

- **Surrogaat-PK bevestigd**: `relatie.id` UUID-PK (`models.py:312`); de uniciteit is de
  **partiële** index `uq_relatie (tenant, bron, doel, relatietype) WHERE relatietype <> 'flow'`
  (`:298-301`, ADR-023a/migratie 0039). De plaatsing is een `aggregation`-rij tussen twee
  bedrijfsfunctie-elementen (ADR-044/migratie 0063), dus uniek per (ouder, functie)-paar.

- **Overleeft `relatie.id` een herinlees? — Onomwonden: ja én nee, per geval.** De import
  (`referentiemodel_import_service.voer_uit:311-420`) is **delta-gebaseerd, niet herbouwend**:
  1. **Functies** worden op bronsleutel gematcht en **in-place** bijgewerkt
     (`:362-381`) — geen delete/recreate, element-id's blijven; vervallen = markeren
     (`:397-401`), terugkeer = herleven (`:380`).
  2. **Plaatsingen die in de bron blijven** komen in geen enkele schrijfstap voor
     (alleen `bron − bestaand` wordt aangemaakt, `:385-388`) → **de rij wordt niet
     aangeraakt, `relatie.id` blijft**.
  3. **Verhangen plaatsingen** (paar verdwenen uit de bron terwijl béide functies er nog in
     staan) worden **hard verwijderd**: `verwijder_plaatsing(via_import=True)` (`:389-395`) →
     `session.delete(rij)` (`bedrijfsfunctie_service.verwijder_plaatsing`, ORM-delete) — **rij
     weg, id weg**. Komt hetzelfde paar in een latere release terug, dan ontstaat een **nieuwe
     rij met een nieuwe id** (plaatsingen kennen géén herleef-mechanisme zoals functies).
  4. **Plaatsingen van een vertrekkende (vervallen) functie** worden bewust **bevroren** — niet
     verwijderd (`:390-392`, comment) → id blijft.

  **Consequentie voor dit spoor**: een registratie-feit dat via FK aan `relatie.id` hangt is
  veilig voor het gewone geval (blijvende plaatsing, vervallen functie) maar wordt bij een
  **verhangen** plaatsing door de import geraakt — afhankelijk van de FK-keuze verdwijnt het
  mee (CASCADE), blokkeert het de import (RESTRICT — `verwijder_plaatsing` zou dan falen) of
  raakt het los. Dit is een echte ontwerpknoop (zie §6, knoop 2), geen theoretische: de import
  verwijdert vandaag aantoonbaar rijen. (Hoe váák GEMMA verhangt is niet gemeten — zie §7.)

- **Precedent voor een tabel aan `relatie.id`**: **bestaat niet.** Grep over modellen en
  migraties: geen enkele `ForeignKey` verwijst naar `relatie` (het enige near-match,
  `correlatie_id`, is een audit-kolom zonder FK). Dit spoor zou de **eerste** consument van dat
  anker zijn. NB: `relatie` heeft ook geen `UNIQUE(tenant_id, id)` — voor een tenant-consistente
  **composiet**-FK `(tenant_id, relatie_id)` (het vaste recept) zou die target-constraint erbij
  moeten, zoals `uq_impact_view_tenant_id` en `uq_bedrijfsfunctie_tenant_id` dat voor hun
  junctie/self-FK deden (`models.py:1330`, `:786`).

### B3 — De teleenheid

Bevestigd: elke plaatsing is een eigen `relatie`-rij (partiële UNIQUE per (ouder, functie)-paar)
— een registratie via `relatie.id` verschilt dus **per plek**, exact ADR-044 besluit 4.
**Nuancering op de aanname "er is geen bestaand mechanisme dat dit al doet"** (correctie op de
opdrachttekst): het **jsonb-`kenmerken`-veld op `relatie` ís een bestaand
per-relatie-registratiemechanisme** — de plateau-bevestiging legt er vandaag wie/wanneer/aantal
in vast (`plateau_service.py:189-200`). Er is dus geen aparte *tabel*, maar wel een gevestigde
per-plek-drager. Kanttekening uit de eigen geschiedenis (DC016, likara-backend): voor
**audit-naspeurbaarheid per veld** werd jsonb eerder bewust afgewezen ten gunste van een echte
kolom (de diff-capture toont jsonb alleen als geheel oud→nieuw).

---

## 5. C — Verwijzingen, en wat het niet is

- **Bestaat er een "benoemde verwijzing" (label + adres) als gestructureerd veld?** In de
  **tenant-modellen: nee** — geen enkel `url`/`adres`/`link`-veld (grep over `models.py`: 0
  mapped kolommen). Het dichtstbijzijnde bestaande is **platform-niveau**:
  `referentiemodel_optie.herkomst` (String 255, `models.py:1172`) — een vrije bronaanduiding
  die feitelijk repo-URL + bestand + licentie in één string draagt (live: "VNG-Realisatie/
  GEMMA-Archi-repository (github.com/…, export/GEMMA release.xml) — licentie EUPL"), naast een
  apart `versie`-veld. Géén gestructureerd (label, adres)-paar; het concept moet dus nieuw
  gemodelleerd worden.
- **Bestandsupload**: MinIO staat in de stack en in de settings (`app/core/config.py` is de
  enige code-treffer op minio/s3); **geen enkel domeinpad importeert een S3-client** — "geen
  upload" is daarmee een **gegeven** (er is niets om op aan te sluiten), niet een breuk met
  bestaand gedrag. Het verboden patroon (directe blob-toegang buiten de applicatielaag) blijft
  onverkort staan.
- **Meervoud — welke vormen kiest de code elders?** Twee precedenten bestaan naast elkaar:
  1. **rij-per-feit** (eigen tabel, eigen levenscyclus per regel): `roltoewijzing` (meerdere
     rollen = losse rijen, `models.py:1178-1210`), `procesvervulling` (meerdere functies =
     losse regels), `impact_view_component` (junctie);
  2. **array-in-kolom**: `contract_band_dekking.dekking_sleutels TEXT[]` (ADR-030) — voor een
     waardenlijstje zónder eigen identiteit/levenscyclus.
  Een verwijzing met label + adres die individueel toegevoegd/verwijderd wordt lijkt qua vorm op
  categorie 1; welke het wordt is een ontwerpkeuze (knoop 4).

---

## 6. D — Reikwijdte en volgorde

- **Schermen die het spoor zouden tonen zodra het bestaat** (inventaris, geen ontwerp):
  ComponentDetail/ApplicatieDetail · ContractDetail · PartijDetail · de functieboom
  (`BedrijfsfunctieLijst` — rij/popup, en de diagram-popup) · de koppeling-popup op de
  Landschapskaart (master-detail) · ProcesLijst/proces-detailblokken · de migratie-detailviews
  (Plateau/Gap/WorkPackage/Deliverable). Voor de eerste consument (plaatsing): de
  functieboom-rij/-popup is de plek waar de plaatsing vandaag zichtbaar is.
- **Gedeelde bouwsteen die erop lijkt**: `ObjectHistoriePaneel.vue`
  (`modules/…/views/ObjectHistoriePaneel.vue:14-17`, props `entiteitType`/`entiteitId`; lazy
  dialog, keyset). Het **vorm-patroon** (klein paneel per object, props type+id) past; het
  **doel botst niet maar verschilt**: dat paneel is een read-only lezer op de audit-API, een
  registratie-paneel zou schrijven en zou (voor anker 2) een `relatie_id` i.p.v.
  `entiteitType/Id` dragen. NB: het historie-paneel zelf ontbreekt vandaag óók op
  bedrijfsfunctie/plaatsing (geen objecthistorie-ingang, §2).
- **RBAC/audit bij twee nieuwe tenant-tabellen**: per tabel een `Entiteit.<NAAM>` +
  `_INHOUD`-regel in `PERMISSIES` (viewer L · medewerker LAW · beheerder LAWV · auditor L —
  de matrixtest telt mee), opname in `AUDIT_TENANT_ENTITEITEN` + NL-labels; het 0062-recept
  levert RLS/grants. (Alleen benoemd, zoals gevraagd.)
- **Schaal (dev-DB, live)**: elementen — bedrijfsfunctie 299 · partij 72 · component 19 ·
  contract 15 · gebruikersgroep 8 · proces 6 (totaal 419; overige subtypes 0 rijen).
  Relaties — aggregation 307 (waarvan 304 bedrijfsfunctie↔bedrijfsfunctie-plaatsingen, meting
  vorig checkpoint) · flow 29 · association 12 · serving 8 · assignment 6 (totaal 362).

---

## 7. Open knopen voor Bert

1. **Waar landt "wie/wanneer" voor het nieuwe spoor?** Opties die de code toelaat:
   (a) echte kolommen op het feit (`*_door_sub` + `*_door` e-mail-fallback + `*_op` — het
   klaarverklaring-recept, incl. `actor_resolutie` voor de naamweergave); (b) het
   jsonb-`{sub,email}`-recept (plateau-vorm — maar per-veld-audit-diff is dan grover, DC016-les);
   (c) alleen de audit (feitelijk dekkend maar vandaag onleesbaar voor de consultant op deze
   objecten — zie §2). De precedenten wijzen allemaal naar het feit zelf; de keuze blijft aan
   Bert.
2. **Wat gebeurt er met een registratie op een plaatsing die de import verhangt?** De import
   verwijdert zo'n relatie-rij vandaag hard (`voer_uit:389-395`). Opties: (a) FK CASCADE — de
   registratie verdwijnt mee (stil verlies van een bevinding); (b) FK RESTRICT — de import
   faalt op een geregistreerde plaatsing (botst met het idempotente import-ontwerp);
   (c) de import aanpassen: een verhangen plaatsing niet verwijderen maar markeren
   ("vervallen plaatsing", spiegel van de functie-vervallen-vorm) — een semantiekwijziging van
   `voer_uit`/`_bepaal_plan`; (d) de registratie niet aan `relatie.id` maar in
   `relatie.kenmerken` (jsonb) dragen — verdwijnt dan óók mee, zonder tweede tabel. Elke optie
   heeft een aantoonbaar gevolg; hier hoort het besluit vóór de bouw.
3. **Verplichte reden per feit-soort?** De klaarverklaring eist een reden (Text NOT NULL); de
   plateau-bevestiging niet. Voor "hier gebruiken we geen systeem" (de eerste consument) is
   het de vraag of de toelichting verplicht is (het oordeel draagt) of optioneel.
4. **Meervoud-vorm voor verwijzingen**: rij-per-verwijzing (roltoewijzing-vorm, eigen
   levenscyclus per regel) · array-in-kolom (band-dekking-vorm) · één enkel veld. Het
   gestructureerde (label, adres)-paar bestaat nog nergens — de vorm is vrij.
5. **Leesbaarheid van het "wie/wanneer"-verloop**: bedrijfsfunctie, plaatsing (relatie) en
   proces hebben géén objecthistorie-ingang (`_TYPES`, `routes/objecthistorie.py:40-48`).
   Opties: een ingang toevoegen (toegang-volgt-object; voor relatie ontbreekt een eigen
   object-read — de reden dat hij is uitgesloten), of het nieuwe spoor draagt zelf de actuele
   wie/wanneer-weergave en het verloop blijft beheerder/auditor-terrein.
6. **Composiet-anker of kale FK voor anker 2**: het vaste recept (tenant-consistente
   composiet-FK) vergt een nieuwe `UNIQUE(tenant_id, id)` op `relatie` (bestaat nu niet); een
   kale FK op alleen `relatie.id` zou van het recept afwijken. Feit: beide kunnen; het
   composiet-recept is de gevestigde vorm (`uq_impact_view_tenant_id`-precedent).
7. **Volgorde van de twee ankers**: het besluit zegt "structureel, plaatsing eerst, aansluiting
   zonder herbouw". Opties: beide dunne tabellen in één slice (de "twee ankers"-vorm meteen
   compleet) of alleen anker 2 nu met anker 1 als tweede slice (n≥2-discipline: de tweede
   instantie naast de eerste bouwen vóór abstractie — hier is de leest al besloten, dus dit is
   puur volgorde/scope-keuze).

---

## 8. Wat ik NIET heb kunnen vaststellen

- **Hoe vaak GEMMA-releases plaatsingen verhangen.** De Verkenning-V040 mat dat 296/296
  functie-identifiers 9 maanden stabiel bleven; de stabiliteit van de *plaatsings-paren* over
  releases is **niet** apart gemeten. Knoop 2 weegt dus op een onbekende frequentie — kan
  desgewenst gemeten worden met de twee release-bestanden uit de verkenning.
- **De exacte stempel-route van de klaarverklaring** (dat `verklaard_door*` via
  `huidige_actor()` loopt): de model-docstring zegt "server-side herstempeld" en de
  DC015-patronen bevestigen het; de servicecode zelf heb ik niet regel-voor-regel gelezen.
- **Frontend-gedrag bij een plaatsing-popup**: welke popup/rij in `BedrijfsfunctieLijst` de
  natuurlijke drager van het spoor is heb ik geïnventariseerd (§6) maar niet UX-matig
  beoordeeld — dat is ontwerp, geen feit.
- **Live-gedrag van een import mét toekomstige registratie eraan**: hypothetisch (de tabel
  bestaat nog niet); het delete-pad zelf is uit de code vastgesteld, niet live gereproduceerd
  met een afhankelijke rij.
