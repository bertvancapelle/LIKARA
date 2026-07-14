# Feitenrapport — Koppelen component aan bedrijfsfunctie (gate 2)

**Build:** V041 · **Commit:** `6cc7db0` · **Datum:** 2026-07-14 · **Modus:** READ-ONLY checkpoint
**Meetbron:** dev-DB (`lk_admin`, read-only) + codebase (canoniek).
**Reikwijdte:** vaststellen wat vandaag bestaat, waar gate 2 aanhaakt, welke knopen open zijn.
Geen wijziging, geen migratie, geen commit.

> Elke uitspraak draagt een **vindplaats** (`bestand:regel`) of een **telling** uit de dev-DB.
> Waar de code afwijkt van een aanname in de opdracht/ADR/skill: gemeld in **§9**, code wint.

---

## 2. Wat de gebruiker vandaag kan (schermen eerst)

### 2.1 Bedrijfsfunctieboom — één scherm, twee weergaven (Boom | Diagram)

View: `modules/bwb_ontvlechting/frontend/views/BedrijfsfunctieLijst.vue`
(route `bedrijfsfunctie-lijst`, `frontend/src/router/index.js:143`). De Diagram-weergave hergebruikt
`ProcesDiagram.vue`; er is **geen** detail-route per functie.

**Handelingen per rij** (blok `RijActies`, `BedrijfsfunctieLijst.vue:864-918`):

| Handeling | Betekenis | Vindplaats |
|---|---|---|
| Toon in functiebeeld → | naar Diagram | `:867-873` |
| + Deelfunctie | nieuwe onderfunctie (niet bij vervallen) | `:874-881` |
| Bewerken | alleen eigen functies | `:882-889` |
| Plaats ook onder… | extra plaatsing (ADR-044) | `:894-901` |
| Haal hier weg | déze plaatsing weghalen (danger, alleen mét ouder) | `:902-909` |
| Verwijderen | danger, eigen + VERWIJDEREN-recht | `:910-917` |
| "staat ook onder" → | doorklik naar andere plek van dezelfde functie | `:841-857` |

Buiten de rij: "Nieuwe functie" `:661`, "Model inlezen" `:660`.

**Koppelt vandaag iets een component aan een functie of plaatsing? → NEE.** Bewezen:
- `BedrijfsfunctieLijst.vue`: de enige `component`-treffers zijn drie generieke imports
  (`BevestigVerwijderDialog`, `MeldingBanner`, `RijActies`) op `:37-39` — geen koppeling.
- De functie-API kent alleen `lijst/haal/maak/werkBij/verwijder/subboom/plaats/verwijderPlaatsing`
  — `frontend/src/api.js:426-437`. **Geen** component-endpoint.
- Geen functie-detailscherm en geen componentsubroute — `frontend/src/router/index.js:143`.
- Comment die de leegte zelf benoemt: `BedrijfsfunctieLijst.vue:821` ("de gate-2-telling past er
  later in de tekst bij").

→ De MVP-belofte stopt vandaag inderdaad na stap 1: de boom is leesbaar, er hangt geen systeem aan.

### 2.2 Componentdetail — waar een "Bedrijfsfuncties"-sectie zou landen

View: `ComponentDetail.vue` (route `component-detail`, `router/index.js:123`), tabs op `:194-214`.
Bestaande secties: Overzicht (`:349`), Checklist (`:528`), Datatypes (`:543`),
Gebruikersgroepen (`:546`), Koppelingen (`:549`), Gebruik (`:554`), Opbouw (`:558`),
Impact (`:561`), Contracten (`:564`), Verantwoordelijkheden (`:567`), Blokkades (`:578`).
Binnen Overzicht zit al de procesinzet-sectie "Waarvoor gebruiken we het" →
`ComponentProcessenSectie` (`ComponentDetail.vue:457`, import `:39`).

**Spiegel voor een nieuwe "Bedrijfsfuncties"-sectie:** `ComponentProcessenSectie.vue` — de
component-zijde van procesvervulling (component ↔ proces). Dat is het directe as-analoog voor
component ↔ bedrijfsfunctie, bekeken vanaf het component.

### 2.3 Het "PROCES"-veld in het componentformulier — raakt gate 2 dat? → NEE

Label "Proces" + `ZoekSelect`: `ComponentFormulier.vue:436-445` (naastliggend "Applicatiefunctie" `:448-452`).
Dit veld is de **procesvervulling-as** (component→proces, ADR-042), een andere as dan de
bedrijfsfunctie. Gate 2 voegt een nieuwe as toe en **wijzigt dit veld niet**; het herbenoemen van
"PROCES" is expliciet gate 4's onderwerp. **Niet gewijzigd.**

---

## 3. De plaatsing als anker (ADR-044) — bestaat dit zoals aangenomen?

### 3.1 De boom leeft in aggregation-relaties, geen `ouder_id` meer — BEVESTIGD

- Docstring: `bedrijfsfunctie_service.py:3-8` ("de boom leeft in PLAATSINGEN — aggregation-relaties
  (bron = ouder/geheel, doel = kind/deel)"). Constante `_AGGREGATION` op `:52`.
- Paren-leesquery uit `relatie`: `_plaatsings_paren`, `bedrijfsfunctie_service.py:116-130`.
- Plaatsing aanmaken = `Relatie`-rij bouwen: `:254-257`, `:369-372`.
- `ouder_id` **gedropt**: migratie `0063_adr044_plaatsing.py:40` (`drop_column`), self-FK/CHECK/index
  weg op `:37-39`. Test-borging: `test_bedrijfsfunctie_adr043.py:43` (`"ouder_id" not in kols`).
- Let op: `proces.ouder_id` bestaat nog wél (`0057_adr042_proces.py:37`) — proces heeft de
  ADR-044-omzetting (nog) niet gehad; alleen bedrijfsfunctie.

### 3.2 Kan een fijn feit veilig aan een plaatsing hangen? — HIER ZIT DE SCHEMAKNOOP

Een plaatsing is een rij in `relatie` (`relatie.id` = het anker, ADR-044 besluit 1, `:69-71`).

**Constraints/indexen op `relatie` vandaag** (dev-DB, gemeten):
- `PRIMARY KEY (id)` — `relatie_pkey`.
- Partiële unieke index `uq_relatie` op `(tenant_id, bron_id, doel_id, relatietype) WHERE relatietype <> 'flow'`
  (aangemaakt in `0012_adr023_relatiemodel.py`, partieel gemaakt in `0039`).
- **GEEN `UNIQUE(tenant_id, id)`.**

→ **Een composiet-FK `(tenant_id, plaatsing_id) → relatie(tenant_id, id)` is vandaag NIET mogelijk.**
Het huisrecept (composiet-FK met tenant in de sleutel, zoals overal in de codebase) vereist eerst
een `UNIQUE(tenant_id, id)` op `relatie`. Een simpele FK naar `relatie(id)` zou wél kunnen, maar
wijkt af van het patroon. **Dit is een schemastap vóór gate 2 kan landen — zie open knoop 1.**

**Bestaand precedent van een tabel die naar `relatie.id` verwijst? → NEE.**
Grep over models + alle migraties: **niets** verwijst vandaag naar `relatie.id` of `relatie(tenant_id,id)`.
Gate 2 zou de **eerste** zijn. LI038/ADR-043 spreekt van "twee ankers: elementen én koppelingen via
`relatie.id`" — dat is **intentie**, geen gebouwd precedent (**discrepantie, §9**).

**Wél een precedent voor exact dezelfde schemazet, op een andere tabel:** `organisatiegebruik` kreeg
juist een `UNIQUE(tenant_id, id)` (`models.py:480`) speciaal als composiet-FK-doel voor zijn
verfijning `gebruikersgroep` (`fk_gebruikersgroep_gebruik (tenant_id, gebruik_id) → organisatiegebruik(tenant_id, id)`,
`models.py:515-518`). Wat `relatie` mist, deed `organisatiegebruik` al — dat is het te spiegelen recept.

**Huidige FK-/cascade-praktijk op `relatie`:** `relatie` verwijst zélf naar `element` via twee
composiet-FK's, **beide `ON DELETE CASCADE`** (`0012_adr023_relatiemodel.py:40-47`, `models.py:321-328`).
Verdwijnt een functie-element, dan verdwijnt de plaatsing-relatie mee (CASCADE). Een fijn feit dat aan
`relatie.id` hangt zou dus ook een verdwijn-regel nodig hebben — **zie open knoop 2**.

### 3.3 Tellingen op de dev-DB

| Meting | Aantal |
|---|---|
| Bedrijfsfuncties (`bedrijfsfunctie` = `element` type `bedrijfsfunctie`) | **299** |
| Waarvan `vervallen` | **1** |
| Plaatsingen (aggregation-relaties tussen bedrijfsfuncties) | **304** |
| Distinct kinderen (functies met ≥1 plaatsing) | **291** |
| **Functies met méér dan één plaatsing** | **7** ✅ (bevestigt de verwachting) |

---

## 4. Het precedent procesvervulling (ADR-042) — wat is 1-op-1 herbruikbaar?

De koppeling component→proces (ADR-042) is de dichtstbijzijnde spiegel. Per onderdeel:

| Onderdeel | Vindplaats | 1-op-1 herbruikbaar voor component→functie? |
|---|---|---|
| Tabel/model | model `models.py:706-745`; migratie `0059_adr042_procesvervulling.py:27-42` | Recept ja; **UNIQUE nee** (zie ⚠) |
| UNIQUE | `(tenant_id, component_id, proces_id, applicatiefunctie)` — `0059:38-41`, `models.py:726-729` | **Nee** — bevat het werkwoord |
| FK's | 2× composiet → `element`, `ON DELETE CASCADE` — `0059:46-53` | Ja (component-zijde); functie-zijde = plaatsing (§3.2) |
| RLS/grants | ENABLE+FORCE+`tenant_isolation`+grants `lk_app` — `0059:54-61` | Ja, 1-op-1 |
| Service | `maak_aan` `:65`, `werk_bij` `:120`, `verwijder` `:156`, leespaden `:198/:240`, roll-up `:282/:348` | Ja, structuur; werkwoord-logica eruit |
| Routes | `routes/procesvervulling.py:37-96`; eigen `Entiteit.PROCESVERVULLING` (`rbac.py:55`) | Ja als vorm |
| Audit-allowlist | `"procesvervulling"` in `app/core/audit.py:72` | Ja |
| Frontend | `ComponentProcessenSectie.vue` (component-zijde) = **het model voor gate 2** | Ja |

⚠ **Kritisch verschil (getoetst): de functie-as is KAAL, procesvervulling is een TRIPEL.**
Procesvervulling draagt een verplicht werkwoord `applicatiefunctie` (`NOT NULL`, `models.py:743`;
`0059:34`), dat in de UNIQUE zit (`:38-41`), in het schema verplicht is (`schemas/procesvervulling.py:21`)
en in de service hard wordt gevalideerd (`maak_aan` via `af_catalog.valideer_functie`, `:80`). ADR-044
besluit 2 (`:98-101`) houdt de functie-as **kaal** — géén applicatiefunctie. **Oordeel:** het *recept*
(eigen tenant-tabel, composiet-FK's naar `element`+CASCADE, FORCE RLS, eigen RBAC-entiteit,
audit-allowlist, twee-zijdige leespaden, regel-acties-frontend) is 1-op-1 herbruikbaar; het *TRIPEL-deel*
(de `applicatiefunctie`-kolom, NOT NULL, plek in UNIQUE, validatie) **vervalt** — de uniciteit wordt
`(tenant, component, functie/plaatsing)`.

---

## 5. "Ondersteunt werk" (ADR-045) — is de vangrail voor de picker er?

### 5.1 Kolom + CHECK + waarden — BEVESTIGD
- Kolom `ondersteunt_werk` (Boolean, NOT NULL, `server_default false`): `models.py:1620`;
  migratie `0065_adr045_ondersteunt_werk.py:42-45`.
- CHECK `ck_componentconfig_ondersteunt_werk_dim`: `dimensie='componenttype' OR ondersteunt_werk=false`
  (`0065:32-33`) — gemeten aanwezig in de DB.
- **Typen op `true` (dev-DB gemeten):** `applicatie` · `saas_dienst` · `landelijke_voorziening` ·
  `fileshare` · `client_software`. Op `false`: `database` · `integratievoorziening` · `server_compute`.
  ✅ (exact de verwachting).

### 5.2 Kan de tenant-frontend de vlag lezen? — JA
- Catalog-select levert de vlag: `componentconfig_catalog.py:120` + projectie `:144`
  (`actieve_opties_per_dimensie`, `:107`).
- Schema draagt het veld: `schemas/component.py:244` (`ondersteunt_werk: bool = False`,
  comment `:242-243` noemt "gate 2").

### 5.3 Server-side filter op `GET /componenten` — BESTAAT AL (géén bouwvereiste)
- Query-parameter **`ondersteunt_werk: bool | None`**: `routes/component.py:79` (comment `:78` → "ADR-045
  besluit 5"), doorgegeven aan de service `:99`.
- Service-filter (IN-subquery op de catalogus-eigenschap, niet op een hardcoded typelijst):
  `component_service.py:395-403` (param `:330` in `lijst`, ook in `tel` `:497/:539`).

→ **Correctie op de opdracht-aanname (§5.3):** het filter is niet afwezig. De picker kan zijn scope
vandaag al spiegelen via `?ondersteunt_werk=true`. Zie §9.

### 5.4 Koppelbare componenten in de dev-DB (gemeten)

| Type | Aantal | Koppelbaar (`ondersteunt_werk`) |
|---|---|---|
| applicatie | 16 | ✅ true |
| fileshare | 1 | ✅ true |
| saas_dienst | 1 | ✅ true |
| database | 1 | ❌ false |
| **Totaal** | **19** | **18 koppelbaar / 1 niet** |

---

## 6. Grof→fijn-precedent organisatiegebruik (ADR-036/046) — en het échte verschil

**Grof feit:** `organisatiegebruik` (org gebruikt applicatie), model `models.py:458-493`,
`UNIQUE(tenant, org, app)` `:478`, migratie `0049_adr036_organisatiegebruik.py:36-66`.
**Fijne verfijning:** `gebruikersgroep` (`models.py:496-533`), verwijst omhoog via `gebruik_id`
→ `organisatiegebruik(tenant_id, id)` (`:515-518`).

**"Verdwijnt nooit stil":** app-laag 409 + DB-RESTRICT.
- 409-check bij verwijderen grof feit met verfijning: `organisatiegebruik_service.py:120-152`
  (`RegistratieConflict("GEBRUIK_HEEFT_VERFIJNING", ...)` `:137-142`).
- DB `ON DELETE RESTRICT` als backstop: `0053_adr038_consolidatie.py:68-73` (was eerder SET NULL in 0049).

**Signaal "detaillering ontbreekt"** (`gebruiksfeit_zonder_verfijning`): **read-only afgeleid, niets
opgeslagen** — `registratiegaten_service.py:305-330` (constante `:56`, aanroep `:384`); query
`~exists(gebruikersgroep met dit gebruik_id)`.

### ⚠ Het échte verschil met ADR-044 besluit 2 — scherp benoemd

**Bij organisatiegebruik verdringt fijn het grove NIET; grof en fijn bestaan náást elkaar.**
De leeslagen tonen het grove feit **altijd** en zetten er een `heeft_verfijning`/`verfijnd`-vlag naast:
`organisatiegebruik_service.py:207-245` (`lijst_voor_applicatie`, vlag `:215-219`), `:248-283`
(`lijst_voor_organisatie`, docstring "Inclusief grof-only feiten" `:252-253`), `_lees_een` `:155-178`.
Consumenten idem (`landschapskaart_service.py:333-343`, frontend `GebruikteApplicatiesSectie.vue:74-75`).

**"Fijn verdringt grof" bestaat nergens in de codebase** (brede grep op verdring/overschrijf/verberg/vervang:
geen leesregel; procesregister doet roll-up/aggregatie, geen verdringing). ADR-044 zélf noemt
organisatiegebruik "de spiegel" en spreekt van "de leesregel (fijn verdringt grof op die plek)"
(`ADR-044:103-107`) — maar de **feitelijke** organisatiegebruik-implementatie doet dat juist níét.

→ **Gevolg:** gate 2 (ADR-044 besluit 2, kernregel `:84-86`: verfijnen **vervangt** de grove koppeling op
die plek) zou de **eerste** plek zijn waar "fijn verdringt grof" daadwerkelijk gebouwd wordt. Dit bepaalt
of het een **leeslaag** wordt (ADR-044 `:106-107`: "geen tweede opgeslagen waarheid") of een schrijfregel.
**Zie open knoop 3.**

---

## 7. Stempel, gaten en rechten (aanhaking, niet bouwen)

### 7.1 Actor-stempel (wie/wanneer + optionele toelichting) — BESTAAT AL
Module `services/actor_resolutie.py` (`resolveer_naam` `:52`, `resolveer_namen` `:36`, `pak_sub_email` `:24`).
Toegepast op o.a. component-klaarverklaring (`verklaard_door_sub` + `_naam`,
`component_klaarverklaring_service.py:44-45,70,110`; kolom `models.py:1336`), plateau-bevestiging
(`plateau_service.py:220,232`), impact-view (`impact_view_service.py:88,139`), auditlog-leeszijde
(`auditlog_service.py:104,158`). Het `verklaard_door_sub` + `resolveer_naam`-patroon is direct te spiegelen
voor de koppeling; het bestaat nog niet op een koppel-entiteit.

### 7.2 Gap-signaal (gate 3 — NIET bouwen, alleen aanhaking)
- Aggregator heet **`registratiegaten()`** (niet `overzicht()`): `registratiegaten_service.py:372`. Levert
  vandaag o.a. component-zonder-eigenaar `:114`, BIV-onvolledig `:144`, geïsoleerd `:245`,
  `gebruiksfeit_zonder_verfijning` `:305`; per-component badge `:155`. Alles read-only per tenant.
- **Signaal op bedrijfsfuncties vandaag? → GEEN** (geen treffer in `registratiegaten_service.py` of
  `plaatsingsignaal_service.py`).
- `plaatsingsignaal_service.py` bestaat (ADR-023 Fase F) maar betekent iets anders: consistentie tussen het
  checklist-antwoord `technische_plaatsing` en een `draait_op`-relatie (`assignment`, `:72`); route
  `GET /plaatsing` `routes/plaatsingsignaal.py:22`. Het hangt aan relatie-rijen maar níét aan
  bedrijfsfunctie-plaatsingen. Een gate-3-plaatsingsignaal zou hier een nieuw signaaltype toevoegen.

### 7.3 RBAC + audit
- `Entiteit.BEDRIJFSFUNCTIE = "bedrijfsfunctie"`: `backend/app/core/rbac.py:59`, matrix `:164`,
  gebruikt in `routes/bedrijfsfunctie.py:48`.
- `AUDIT_TENANT_ENTITEITEN` (`app/core/audit.py:54`) bevat `"bedrijfsfunctie"` `:74` én `"relatie"` `:58`.
  De plaatsingen (relatie-rijen) vallen dus onder het `relatie`-auditspoor (test-bevestigd
  `test_bedrijfsfunctie_adr043.py:151`).
- **Onder welke entiteit valt een component→functie-koppeling?** Sterkste parallel: een **eigen** entiteit
  zoals `Entiteit.PROCESVERVULLING` (`rbac.py:55`; ADR-042 gaf de koppelregel een eigen entiteit omdat een
  koppeling "geen eenduidige bron-kant heeft om op mee te liften", comment `:53-54`). Alternatief: onder
  `Entiteit.RELATIE`/audit `"relatie"` als de koppeling als relatie-rij wordt gemodelleerd. **Open knoop 4.**

---

## 8. Frontend-bouwstenen die gate 2 erft

| Bouwsteen | Vindplaats | Zonder aanpassing herbruikbaar? |
|---|---|---|
| `ZoekSelect` | `.../views/ZoekSelect.vue` | **Ja** — picker-regel bevestigd: openen toont altijd de volledige startlijst, ook voorgevuld (comment `:14-15`, `openen()`/`zoek('')` `:98-104`, klik-op-gefocust `:138-143`) |
| `RijActies` | `frontend/src/components/RijActies.vue` | Ja — al in de functieboom (`BedrijfsfunctieLijst.vue:864`) |
| `BevestigVerwijderDialog` | `frontend/src/components/BevestigVerwijderDialog.vue` | Ja |
| `MeldingBanner` | `frontend/src/components/MeldingBanner.vue` | Ja |
| `toastSucces` | `frontend/src/meldingen.js:15` | Ja |
| `useToonNieuweRij` / `useAanstip` | `frontend/src/composables/useToonNieuweRij.js` (`scrolNaarRij` `:34`, `useAanstip` `:43`, `useToonInBoom` `:69`) | **Ja, incl. plek-paden** — `useToonInBoom({…, padVan})` voor meervoud-bomen, in de functieboom aangeroepen met plek-paden (`BedrijfsfunctieLijst.vue:261-277`, `padVan` `:269`) |
| `FilterResultaatRegel` | `frontend/src/components/FilterResultaatRegel.vue` | Bestaat; nog niet in de functieboom gebruikt (geen bevestigd meervoud-boom-gedrag) |
| `DetailKop` | `frontend/src/components/DetailKop.vue` | Ja — al in `ComponentDetail.vue:42` |
| `.lk-veld` | `frontend/src/assets/main.css:47-72`; token `themes/base.css:68` | Ja — globale utility |
| `IdentiteitLabel` | `.../views/IdentiteitLabel.vue:18` | Bestaat; semantisch afdeling/persoon-gericht — geen 1-op-1 fit voor component↔functie |

**Ontbreekt er iets dat gate 2 nodig heeft? → NEE** uit deze lijst; alle elf bestaan. Aandachtspunten:
`IdentiteitLabel` past semantisch niet, en `FilterResultaatRegel` mist bevestigd meervoud-boom-gedrag.

---

## 9. Discrepanties, open knopen en risico's

### 9a. Discrepanties (code wint)
1. **§3.2 "bestaand precedent van een tabel die naar `relatie.id` verwijst":** de opdracht (via LI038/ADR-043
   "twee ankers") veronderstelt dat dit bestaat. **Code:** niets verwijst vandaag naar `relatie.id`; gate 2
   zou de eerste zijn. "Twee ankers" is intentie, geen gebouwd precedent.
2. **§5.3 server-side filter "ontbreekt mogelijk":** **Code:** het filter bestaat al
   (`routes/component.py:79`, `component_service.py:395-403`). Geen bouwvereiste; wél nog frontend-bedrading.
3. **§6 "de verfijningslogica is de spiegel van organisatiegebruik":** **Code:** organisatiegebruik laat grof
   en fijn *coëxisteren* (geen verdringing). ADR-044 `:103-107` framet het als spiegel, maar "fijn verdringt
   grof" is nergens gebouwd. Dit is een **echt verschil**, geen detail (bepaalt leeslaag vs. schrijfregel).
4. **ADR-044 besluit 1 claimt `UNIQUE(tenant, bron, doel, relatietype)`:** **Code:** bestaat, maar als
   **partiële** unieke index `uq_relatie … WHERE relatietype <> 'flow'` (flow-relaties zijn dus niet uniek).
   Nuance, geen conflict.

### 9b. Tests die gate 2 raakt & huidige staat
Raakvlak-tests (backend): `test_bedrijfsfunctie_adr043.py`, `test_procesvervulling_adr042.py`,
`test_organisatiegebruik_adr036.py`, `test_adr045_ondersteunt_werk.py`, `test_registratiegaten.py`,
`test_relatie_bcore.py`, `test_plaatsingsignaal_f3.py`. Frontend: `ZoekSelect.test.js`,
`BedrijfsfunctieLijst.test.js`, `OrganisatiegebruikSectie.test.js`.

**Suites nu (gedraaid vanaf repo-root):**
- Backend `pytest backend/tests/ modules/`: **1095 passed, 2 skipped** ✅
- Frontend `npm test` (vitest run): **92 files, 1199 passed** ✅

### 9c. Open knopen — genummerde vragen in gebruikerstaal (NIET door CC beantwoord)

**Knoop 1 — Waaraan hangt het fijne feit precies vast?**
Het fijne antwoord ("in Milieu doen we het met de inspectie-app") hoort bij één plek in de boom, maar die
plek (`relatie`) heeft vandaag geen veilige tenant-sleutel om aan vast te maken.
- **A.** `UNIQUE(tenant_id, id)` toevoegen op `relatie` + composiet-FK — precies zoals bij organisatiegebruik
  al gedaan (huisrecept, strengst).
- **B.** Simpele FK naar `relatie(id)` zonder tenant-composiet — minder werk, wijkt af van het patroon.
- **C.** Geen FK naar de plaatsing; het fijne feit onthoudt (component, functie, ouder-functie) los.
*Voor de consultant:* A/B laten de verfijning netjes meebewegen met de plaatsing; C maakt het fragiel bij een
herinlees. **Dit is een schemastap die vóór gate 2 moet vallen.**

**Knoop 2 — Wat gebeurt er met een fijn feit als de plaatsing verdwijnt (functie verhangen / herinlees)?**
- **A.** Mee verwijderen (CASCADE) — botst met ADR-044 addendum LI040 ("import verwijdert nooit stil een
  plaatsing mét registratie").
- **B.** Weigeren met melding (RESTRICT/409) — spiegel van organisatiegebruik ("verdwijnt nooit stil").
- **C.** Markeren + melden ("deze plek is verhuisd; hier hangt veldwerk aan") — spiegel van *vervallen ≠ verwijderen*.
*Voor de consultant:* bepaalt of hij vastgelegd veldwerk ooit ongemerkt kan kwijtraken.

**Knoop 3 — Is "fijn vervangt grof op die plek" een leeslaag of een schrijfregel?**
Nergens in LIKARA bestaat deze regel; organisatiegebruik (de genoemde spiegel) laat grof + fijn juist naast
elkaar staan.
- **A.** Leeslaag: bij het lezen van een plek toont LIKARA het fijne antwoord als dat er is, anders het grove —
  niets extra opgeslagen (dit is wat ADR-044 `:106-107` letterlijk zegt).
- **B.** Schrijfregel: bij het vastleggen van een fijn antwoord wordt de grove koppeling actief onderdrukt/gemarkeerd.
*Voor de consultant:* A houdt het simpel en altijd-waar; B is expliciet maar introduceert een tweede waarheid.

**Knoop 4 — Krijgt de koppeling eigen rechten en een eigen auditspoor, of lift ze mee?**
- **A.** Eigen entiteit (zoals `PROCESVERVULLING`) — eigen rechten, eigen auditregel.
- **B.** Onder `relatie` — meeliften op het bestaande relatie-auditspoor.
*Voor de consultant:* A maakt "wie mag koppelen" apart regelbaar; B is minder werk maar minder fijnmazig.

**Knoop 5 — Grof en fijn: één tabel of twee?**
Het grove feit hangt aan (component, functie), het fijne aan (component, plaatsing) — beide kaal (geen werkwoord).
- **A.** Eén koppeltabel met een nullable plaatsing-verwijzing (leeg = grof, gevuld = fijn) — spiegel
  procesvervulling zonder het werkwoord.
- **B.** Twee aparte tabellen (grof / fijn).
*Voor de consultant:* onzichtbaar in het scherm; bepaalt hoe eenvoudig "fijn vervangt grof" (knoop 3) te lezen is.

---

## 10. Slaagcriteria van dit checkpoint

- ✅ Dit bestand bestaat en beantwoordt §2 t/m §9, elke uitspraak met vindplaats of telling.
- ✅ Geen wijziging buiten dit ene bestand (zie git-status in het terugkoppelrapport).
- ✅ Geen migratie, geen schema, geen commit.
- ✅ Alle open knopen staan als genummerde vragen in gebruikerstaal (§9c), klaar om één voor één te beslissen.

**STOP — wacht op Bert.**
