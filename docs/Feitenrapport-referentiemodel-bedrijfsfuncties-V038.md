# Feitenrapport — Draagvlak procesmodel + inlezen referentiemodel (GEMMA-bedrijfsfuncties)

**Build:** V038 · **Commit-basis:** f1d3270 · **Type:** read-only feitenonderzoek — niets gewijzigd.
**Doel:** feitelijk vastleggen wat LIKARA vandaag draagt (deel 1) en waar het inlezen van een
referentiemodel vandaag op stukloopt (deel 2), als grond voor het ADR-spoor
"referentiemodel + bedrijfsfunctie-as". Geen ontwerp, geen oordeel.

---

## Deel 1 — Wat draagt het LIKARA-procesmodel vandaag?

### 1. Alle velden op het `proces`-subtype

**Vindplaats:** `modules/bwb_ontvlechting/backend/models/models.py:634-671` (class `Proces`) +
migratie `modules/bwb_ontvlechting/migrations/versions/0057_adr042_proces.py` +
schemas `modules/bwb_ontvlechting/backend/schemas/proces.py`.

| Kolom | Type | Null | Default / constraint |
|---|---|---|---|
| `id` | UUID, PK | nee | `gen_random_uuid()`; shared-PK: composiet-FK `(tenant_id,id)` → `element` ON DELETE CASCADE (`fk_proces_element`) |
| `tenant_id` | UUID | nee | TenantMixin; FORCE RLS + `tenant_isolation`-policy (migratie 0057) |
| `naam` | String(255) | nee | app-side `_verplichte_tekst(…, 255)` (`schemas/proces.py`); **géén UNIQUE** — dubbele namen zijn toegestaan |
| `toelichting` | Text | ja | app-side `_optionele_tekst(…, 10_000)` |
| `ouder_id` | UUID | ja | composiet self-FK `(tenant_id, ouder_id)` → `proces(tenant_id,id)` **ON DELETE RESTRICT** (`fk_proces_ouder`); CHECK `ouder_id IS NULL OR ouder_id <> id` |
| `created_at`/`updated_at` | timestamptz | nee | `now()` (TimestampMixin) |

Overige constraints/indexen: `uq_proces_tenant_id (tenant_id,id)` (self-FK-target),
`ix_proces_tenant`, `ix_proces_tenant_ouder`. Grants: `lk_app` SELECT/INSERT/UPDATE/DELETE.

**Conclusie (aanname getoetst):** de aanname *"alleen een naam en zijn plek in de boom"* is
**bijna juist maar gefalsifieerd op één veld**: er is óók een vrije **`toelichting`**
(beschrijving, Text, max 10.000 — een definitie/beschrijving kán daar dus in). Verder is er
**niets**: geen code/externe sleutel, geen status, geen geldigheid, geen volgorde-veld.

### 2. De boom

**Vindplaats:** model-docstring `models.py:634-646`; cycluspreventie `proces_service.py:88-124`
(`_zou_kring_maken`/`_valideer_ouder`, 422 `CYCLISCHE_HIERARCHIE`); verwijdergedrag
`proces_service.py:163-182` (409 `HEEFT_DEELPROCESSEN`, RESTRICT = DB-backstop).

- **Diepte onbeperkt** — geen niveau-constraint; de docstring bevestigt de ADR-042-lijn:
  "de plek in de boom ís het niveau — geen niveau-label". Geen type-/niveau-kolom.
- **Volgorde tussen zusjes bestaat niet als data.** De ordening is overal **afgeleid op naam**:
  backend `subboom` sorteert `ORDER BY naam, id` (`proces_service.py:252`), de gedeelde
  frontend-boom sorteert deterministisch naam→id (`procesBoom.js:31-32`), de lijst default
  `created_at` (ADR-017). Een modelvolgorde (zoals GEMMA-`volgorde`) kan nergens landen.

### 3. Proces → component: `procesvervulling`

**Vindplaats:** `models.py:673-711` (class `Procesvervulling`) + migratie `0059_adr042_procesvervulling.py`.

Velden: `id`, `tenant_id`, `component_id` (composiet-FK → element, **ON DELETE CASCADE**),
`proces_id` (idem, **CASCADE**), `applicatiefunctie` (String(60), tekst-sleutel naar de
catalogus — geen harde FK, app-side gevalideerd op actief), `toelichting` (Text, nullable),
timestamps. Uniciteit: **exact het tripel** `UNIQUE(tenant_id, component_id, proces_id,
applicatiefunctie)`. Bewust een eigen tabel (niet de relatie-facade): meerdere functies per
(component, proces) als losse regels.

**Conclusie:** de regel draagt naast het tripel alléén een vrije `toelichting` — niets anders
(geen periode, geen status, geen bron). NB voor deel 2: door de **CASCADE op `proces_id`**
verdwijnen de eigen koppelregels van de organisatie mee wanneer een proces(-knoop) verwijderd
wordt — relevant voor "vervallen modelinhoud nooit stil laten verdwijnen".

### 4. Proces → proces: `ouder_id` is de enige band

**Vindplaats:** model (`models.py:634-671` — geen andere proces-verwijzing);
ADR `docs/adr/ADR-042_Procesregister_component_in_proces.md:135` ("Flow/volgorde tussen
processtappen blijft buiten scope"); relatie-facade `relatie_service.py:149-176`;
relatietype-catalogus `seed_componentconfig.py:44-72`.

- **Bevestigd:** er bestaat geen flow-, triggering- of volgorde-relatie tussen processen.
  De gecureerde relatietype-set telt exact **acht** ArchiMate-typen (composition, aggregation,
  serving, assignment, flow, realization, association, access) — **`triggering` bestaat niet**
  in de catalogus.
- **Bevestigd:** de generieke facade `relatie_service.maak_aan` valideert **géén**
  bron/doel-elementtype — alleen bron≠doel (`:152`), tenant-bestaan, relatietype-catalogus
  (`:157`), kenmerken (`:158`) en de flow-dubbel-signalering (`:163`). Technisch kan er dus nú
  al via `POST /relaties` een relatie mét een proces als endpoint ontstaan; niets in de UI of
  services doet dat, en een latere flow-/samenhang-laag vergt **expliciete type-borging**
  (consistent met de eerdere V030-correctie in likara-domeinmodel).

### 5. Proces → partij/rol: geweigerd

**Vindplaats:** `roltoewijzing_service.py:33` —
`_OBJECT_TYPES = frozenset({ElementType.component.value, ElementType.contract.value})`;
handhaving in `maak_aan` (`:60-62`): een object buiten die set ⇒ **422 `ONGELDIG_DOEL`**,
bericht "Een rol kan alleen aan een component of contract worden toegewezen."

**Conclusie:** een proces kan vandaag **geen** verantwoordelijke/rol dragen — een
roltoewijzing op een proces wordt expliciet geweigerd. (GEMMA-onafhankelijk feit: ook een
proceseigenaar-rol uit de bestaande beheerrol-startset kan dus niet óp een proces landen —
alleen op component/contract.)

### 6. `applicatiefunctie_optie` — startset en beheerbaarheid

**Vindplaats:** `seed_applicatiefunctie.py:13-19` (startset) +
`applicatiefunctieconfig_service.py` (beheer) + `routes/applicatiefunctieconfig.py:24-26` (guards).

- **Startset (5, GEMMA-geënt):** `registreren`, `raadplegen`, `archiveren`, `gegevens_leveren`,
  `ondersteunen`.
- **Beheerbaarheid:** platform-brede catalogus (geen RLS); platformbeheerder kan **zonder
  redeploy** opties toevoegen/labelen/herordenen/soft-deactiveren (`actief`); er is **géén
  DELETE** (catalogus-familie-norm) en — expliciet gedocumenteerd — **géén systeem-sleutel**:
  élke optie is deactiveerbaar. Guards: `vereist_platform_permissie(APPLICATIEFUNCTIECONFIG,
  LEZEN/AANMAKEN/WIJZIGEN)`.

### 7. RBAC + audit rond proces en procesvervulling

**Vindplaats:** `backend/app/core/rbac.py:52,55` (`Entiteit.PROCES`, `Entiteit.PROCESVERVULLING`)
en `:153,155` (beide `_INHOUD`-patroon); `backend/app/core/audit.py:71-72`.

- **Rechten (`_INHOUD`):** viewer L · medewerker LAW · beheerder LAWV · auditor L — voor
  zowel proces als procesvervulling. Frontend-gating spiegelt dit (ProcesLijst: verwijderen
  beheerder-only, LI037).
- **Audit:** `"proces"` én `"procesvervulling"` staan op `AUDIT_TENANT_ENTITEITEN`
  (`audit.py:72`) — mutaties landen in de hash-chained audit-trail.

---

## Deel 2 — Waar loopt het inlezen van een referentiemodel vandaag op stuk?

### 8. Elementtype-ruimte: `business_function` bestaat niet

**Vindplaats:** `modules/bwb_ontvlechting/backend/services/archimate_typing.py:29-41`
(`TOEGESTANE_ELEMENTEN`), `:63-68` (expliciet comment), `:75` (`ELEMENT_TYPEN_NOG_NIET_GEREALISEERD
= frozenset()`).

- **`business_function` staat NIET in `TOEGESTANE_ELEMENTEN`** (business-laag kent alleen
  business_actor/business_role/business_service/contract/business_object + het door ADR-042
  toegevoegde business_process). Een componenttype of element mét die typing is vandaag een
  **422** (de lijst is de enige bron voor de Pydantic-validators).
- Er is **geen `ElementType`** dat 'm kan dragen; het comment op `:66-67` legt vast dat de
  bedrijfsfunctie-as **bewust geparkeerd** is (ADR-042 besluit 1).
- **Wat een nieuw element-subtype feitelijk vergt** (het bestaande, herhaalde recept — geen
  ontwerp): (a) enum-uitbreiding `element_type_enum` via een ADD VALUE-migratie (precedent
  `0056_adr042_elemtype_proces.py`); (b) subtype-tabel via het element-subtype-bouwrecept
  (shared-PK composiet-FK, FORCE RLS, grants — precedent `0057_adr042_proces.py`, likara-db
  V009/V010); (c) `business_function` toevoegen aan `TOEGESTANE_ELEMENTEN` + een entry in
  `ELEMENT_ARCHIMATE_TYPING`; (d) de **partitietests** (`test_archimate_fase_a`/`fase_d`)
  bewegen mee — een vergeten indeling faalt zichtbaar; (e) RBAC-`Entiteit` + `PERMISSIES` +
  audit-allowlist bewegen mee (matrixtests + allowlist-test).

### 9. Bronsleutel/herkomst: nergens op een element

**Vindplaats (afwezigheid + bestaande patronen):** grep op extern/bron/import/herkomst-velden in
`models.py` levert op element-niveau **niets**. De drie bestaande externe-sleutel-achtige
patronen elders:
- `gebruiker_persoon.keycloak_sub` (`models.py:1086-1105`) — een **stabiele externe sleutel**
  (Keycloak-`sub`) met `UNIQUE(tenant_id, keycloak_sub)`: het enige echte
  extern-systeem-identiteitspatroon in het domein.
- `optie_sleutel` op alle platform-catalogi — een **stabiele, nooit-hergebruikte modelsleutel**
  (soft-deactivate i.p.v. delete; historisch resolvebaar).
- `checklistvraag_optie.afgeleid_bron` (`models.py:803`) — een **herkomst-marker** ("deze set
  is afgeleid uit model-enum X" → read-only in de beheer-UI).

**Conclusie:** er is vandaag **geen enkele plek** op `element`/`proces` (of enig ander
element-subtype) waar een GEMMA-`id-<uuid>` stabiel kan landen. Een tweede inlees zou moeten
matchen op **naam** — en zelfs dát is onbetrouwbaar: `naam` draagt geen UNIQUE (dubbele namen
toegestaan, punt 1), dus naam-matching kan zowel missen (hernoemd) als verkeerd matchen
(gelijknamig).

### 10. Versie-/model-identiteit: volledig afwezig

**Vindplaats (afwezigheid):** grep op `versie` in het domein-datamodel levert niets; er bestaat
geen tabel of veld dat "deze set komt uit bron X, versie Y" vastlegt. De seeds (platform_init,
`seed.py`-checklistbaseline) zijn **code-versies** (mee-gedeployed, idempotent
`ON CONFLICT DO NOTHING`) zonder geregistreerde versie-identiteit in de data; `plateau` is een
situatiebeschrijving van het landschap, geen modelversie.

**Conclusie:** "referentiemodel als eerste-klas begrip (naam, herkomst, versie)" bestaat vandaag
nergens — ook niet in embryonale vorm.

### 11. Import-route: alleen losse create-endpoints

**Vindplaats:** `routes/proces.py:61-67` (POST `/processen`, één per aanroep) — er is **geen**
bulk-/CSV-/import-endpoint in het hele routes-oppervlak (grep op bulk: geen treffers). De enige
niet-endpoint-schrijfpaden zijn `platform_init` (platform-catalogi, idempotent op
`optie_sleutel`) en `dev_seed_testdata.py` (handmatige dev-fixture, geen productie-pad).

**Wat een geautomatiseerde inlees vandaag zou kunnen zetten:** per POST één proces met
`naam` (verplicht, ≤255), `toelichting` (≤10.000) en `ouder_id` — de boom moet dus
**ouder-vóór-kind** aangeleverd worden (de ouder moet bestaan: 404-validatie in
`_valideer_ouder`). **Waar hij stukloopt:** geen veld voor de GEMMA-sleutel (punt 9), geen
versie-registratie (punt 10), één-voor-één zonder transactionele bundel (een half gelukte
inlees laat een halve boom achter), en verwijderen van een vervallen tak vergt leaf→root
(RESTRICT) waarbij de **CASCADE op `procesvervulling` de eigen registratie meeneemt** (punt 3).

### 12. Idempotentie: een tweede run dubbelt

**Vindplaats:** `proces_service.maak_aan` (`proces_service.py:127-142`) maakt **altijd** een
nieuw `Element` + `Proces`; er is geen upsert, geen natural key, geen `ON CONFLICT`-pad;
`naam` is niet uniek (punt 1).

**Conclusie:** twee keer dezelfde inlees draaien = **elke rij dubbel**. Er is geen identiteit
om op te matchen. Bij een **tweede, gewijzigde** modelversie: een **hernoemde** functie is
onherkenbaar (naam-match faalt → dubbel), een **verhangen** functie idem (er is geen sleutel
om de bestaande rij te vinden en `ouder_id` bij te werken), een **vervallen** functie kan
alleen **hard verwijderd** worden (409 zolang er kinderen zijn; verwijdering cascadeert de
eigen `procesvervulling`-regels weg) — er bestaat geen soft-vervallen-status op een proces
(geen `actief`-veld, punt 1).

### 13. Scheiding "geleverde inhoud" ↔ "eigen registratie": drie bestaande patronen

Er is **geen** patroon op element-niveau, wél drie verwante patronen elders:

| Patroon | Vindplaats | Werking |
|---|---|---|
| **Platform-catalogus met stabiele sleutel + soft-deactivate** | catalogus-familie (o.a. `componentconfig_optie`, `applicatiefunctie_optie`); `SYSTEEM_SLEUTEL_BESCHERMD` op componentconfig/componentrol | Geleverde én beheerder-toegevoegde opties leven in één tabel; identiteit = `optie_sleutel`; verwijderen bestaat niet (deactiveren wel); systeem-sleutels zijn extra beschermd. Seeds zijn idempotent op de sleutel (`ON CONFLICT DO NOTHING`) — een her-seed overschrijft beheerder-wijzigingen dus óók niet. |
| **Baseline-kopie per tenant** | `checklistvraag` (ADR-022 W1; `seed.py`-baseline per tenant gekopieerd) | Geleverde inhoud wordt bij onboarding **eigendom van de tenant**; daarna is er geen band meer met de bron (geen her-inlees-begrip). Soft-deactivate via `actief`. |
| **Herkomst-marker op een optieset** | `checklistvraag_optie.afgeleid_bron` (`models.py:803`) | Markeert "deze inhoud is afgeleid uit bron X" → de beheer-UI maakt 'm read-only (alleen label editbaar). Het dichtstbijzijnde "dit is modelinhoud, blijf eraf"-mechanisme. |

**Conclusie:** de bouwstenen (stabiele sleutel, soft-deactivate/nooit-hard-verwijderen,
herkomst-marker, idempotente seed-op-sleutel) bestaan als **patronen**, maar geen ervan leeft
op elementen/processen, en geen ervan onderscheidt binnen één boom "model-knopen" van
"eigen knopen".

### 14. Applicatieservice-kant: drie naburige begrippen

- **Componenttype `landelijke_voorziening`** — het enige begrip dat vandaag als
  `application_service` getypeerd is (`seed_componentconfig.py:37`:
  `("landelijke_voorziening", …, "application_service", "application", "active", True)`);
  semantiek: "extern afgenomen voorziening". `application_service` staat als geldige waarde
  in `TOEGESTANE_ELEMENTEN` (`archimate_typing.py:31`), dus de platformbeheerder kan óók een
  **nieuw componenttype** met die typing aanmaken zonder code-wijziging (ADR-026).
- **`applicatiefunctie_optie`** — een plat vocabulaire ("wat een systeem dóét in een proces":
  registreren/raadplegen/…), géén hiërarchie, géén element; leeft alleen als sleutel op de
  koppelregel.
- **`procesvervulling`** — de bestaande koppelregel component↔proces (punt 3): het huidige
  mechanisme dat "systeem ondersteunt gedrag" vastlegt; GEMMA's "functie ↔ applicatieservice"
  heeft hier zijn dichtstbijzijnde bestaande spiegel, maar dan met een **component** (elk type)
  als drager en een **proces** (niet een functie) als doel.

---

## WAT LIKARA VANDAAG DRAAGT (compleet, feitelijk)

Op een **proces**: `naam` (≤255, niet uniek) · `toelichting` (vrije tekst ≤10.000) · plek in
een onbeperkt diepe boom (`ouder_id`, RESTRICT, cycluspreventie) · timestamps · tenant-isolatie
(FORCE RLS) · volledige audit-dekking · `_INHOUD`-RBAC. Eromheen: koppelregels naar
**componenten** (tripel + vrije toelichting; elk componenttype; uniciteit op het tripel),
een beheerbare **applicatiefunctie-catalogus** (5 startopties, vrij uitbreidbaar, geen
redeploy), de **kaart-/boom-/diagram-leeslagen** (subboom, rollup, gap-cue, proces-only
diagram) en de proces→kaart-handoff.

## LEGE SLOTS voor een referentiemodel

1. **Bedrijfsfunctie-as ontbreekt volledig** — geen `business_function` in
   `TOEGESTANE_ELEMENTEN`, geen element-type/subtype, bewust geparkeerd (ADR-042).
2. **Bronsleutel/externe identiteit op een element** — nergens; een GEMMA-`id-<uuid>` kan niet
   landen (dichtstbijzijnde precedenten: `keycloak_sub`, `optie_sleutel`).
3. **Model-/versie-identiteit** — "welk referentiemodel, welke versie, wanneer ingelezen"
   bestaat nergens.
4. **Import-route** — geen bulk-/import-pad; alleen losse POST's, ouder-vóór-kind, zonder
   transactionele bundel.
5. **Idempotente her-inlees** — geen match-identiteit; tweede run dubbelt; hernoemd/verhangen
   onherkenbaar.
6. **Vervallen-status** — geen `actief`/geldigheid op een proces(-achtig element); "vervallen"
   kan alleen hard verwijderen, wat via CASCADE eigen `procesvervulling`-registratie meeneemt.
7. **Scheiding modelinhoud ↔ eigen inhoud binnen één boom** — de patronen bestaan elders
   (sleutel + soft-deactivate + herkomst-marker) maar niet op elementen.
8. **Volgorde tussen zusjes** — geen volgorde-veld; ordening is overal afgeleid (naam).
9. **Rol/verantwoordelijke op een proces-achtig element** — roltoewijzing accepteert alleen
   component/contract (422 `ONGELDIG_DOEL`).
10. **Groeperingen bovenin het model** (Besturend/Primair/Ondersteunend) — geen begrip dat een
    "visuele groep die zelf geen functie is" kan dragen (alles in de boom is een volwaardig
    element).
11. **Functie ↔ applicatieservice-relatie** — het bestaande koppelmechanisme
    (`procesvervulling`) is component↔proces; er is geen regel-vorm met een functie als anker.

## DISCREPANTIES t.o.v. de aannames in de opdracht

1. **"Een proces draagt alleen een naam en zijn plek in de boom" — net niet:** er is óók een
   vrije `toelichting` (Text, ≤10.000). Een GEMMA-definitie/beschrijving heeft dus wél een
   landingsplek; al het andere uit de aanname klopt (geen sleutel, geen status, geen volgorde).
2. **De relatie-facade is opener dan de scheiding suggereert:** technisch kan er nú al een
   relatie met een proces-endpoint via `POST /relaties` ontstaan (geen elementtype-borging) —
   het "ouder_id is de enige band"-feit geldt voor wat er ontworpen/gebruikt wordt, niet voor
   wat de facade tegenhoudt (punt 4).
3. **`applicatiefunctie_optie` kent géén systeem-sleutels** (expliciet gedocumenteerd) — wie het
   catalogus-patroon als basis neemt voor "geleverde modelinhoud beschermen" moet weten dat déze
   catalogus die bescherming bewust niet heeft (punt 6/13).
4. **Idempotentie-val in de seeds als spiegel:** de bestaande seed-idempotentie werkt op een
   **stabiele sleutel** (`ON CONFLICT (optie_sleutel)`); precies het ingrediënt dat op
   proces-/elementniveau ontbreekt (punt 12).

---

*Einde feitenrapport — read-only; geen code, schema of testdata gewijzigd.*
