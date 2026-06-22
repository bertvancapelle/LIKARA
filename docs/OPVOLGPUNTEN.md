# CompliData — Opvolgpunten (backlog)

Bijgehouden met de hand. Niet door `gen_build.py` gegenereerd.
Bron: sessie 2–3 (P1–P5, OP-9 t/m OP-12). Status per punt expliciet vermeld.

---

## OPEN

### Stand V017 (sessie-afsluiting DC016, 2026-06-22)

Build **V017**, migratie head **`0040`**. Tests: **859** backend + **534** frontend groen +
`test:css-build` groen. Deze sessie: UI-standaardisatie (knop/tab/interactie-borging),
api-client-filterconventie, Landschapskaart popups/fullscreen, ADR-023a meervoudige
flow-koppelingen Fase 1+2.

**Nieuwe/geactualiseerde opvolgpunten (DC016)**:
- **ADR-023a Fase 3** (read/contract, geen migratie) — kaart-edge-groepering: meerdere flows per
  `(bron,doel)` → één lijn + **telling vanaf 2**; popup-fetch op het **ongeordende paar**, gegroepeerd
  naar richting (uitgaand bij bron / inkomend bij doel).
- **ADR-023a Fase 4** (frontend) — naam-veld (verplicht) + overrulebare **KOPPELING_DUBBEL**-
  waarschuwingsdialoog; `KoppelingSectie` naam-kolom (sorteerbaar); kaart-telling vanaf 2; en de
  popup ombouwen naar **universeel master-detail** (links sorteerbare interface-lijst op naam/richting,
  pijl-buiten-groen=uitgaand / pijl-binnen-rood=inkomend met **pijlrichting als hoofdsignaal**; rechts
  detail; eerste regel geselecteerd; ook bij n=1). Vervangt de enkelvoudige popup uit `8de3451`.
- **NIEUW SEED-TRAJECT (groot)** — volledige testdataset opnieuw opzetten zodat hij het **hele
  LIKARA-landschap** representeert en alle functionaliteit raakt (besloten DC016). Moet **flow-namen**
  + **meervoudige benoemde koppelingen** bevatten. Volgt ná de ADR-023a-koppeling-keten.
- **Reseed gebroken op flow-namen** — `dev_seed_testdata._seed_koppelingen` maakt flows **zonder naam**
  → faalt onder de naam-eis (ADR-023a Fase 2). Wordt opgelost in het nieuwe seed-traject; tot dan is
  een reseed van de koppelingen gebroken (testdata-kwestie, géén migratievraagstuk).
- **`test:css-build` nog niet in CI** — los script; een CI-stap of pre-push-hook is de logische
  vervolgstap (aparte slice).
- **ADR-030 contract-dekking per contract↔component-band** (voorstel, `3e28481`) — dekking als
  per-band-kenmerk op de association i.p.v. uitsluitend contract-breed. Centrale open subknoop:
  contract-brede dekking **behouden NAAST** per-band of **vervangen**. Op te pakken ná de
  koppeling-keten (n≥2: de koppeling-uitbreiding als blauwdruk). Read-only verkenning is gedaan.

### Stand V016 (sessie-afsluiting DC015, 2026-06-20)

Build **V016**, migratie head **`0038`**. Tests: **856** backend + **500** frontend groen
(1 pre-existing env-auth-test, OP-30). Deze sessie: ADR-029 (gebruikersbeheer als primaire ingang)
grotendeels gerealiseerd + objecthistorie ('i'-knop).

**AF deze sessie (DC015)**:
- Drie kleine opvolgpunten (DC014): dode `<dl>`-rijen op ApplicatieDetail + ComponentDetail
  opgeruimd; `MigratiegereedheidSectie` ook op ComponentDetail; CLAUDE.md interactie-secties
  geconsolideerd.
- **ADR-029 herschreven** (gebruikersbeheer als primaire ingang; LIKARA als bron van waarheid).
- **ADR-029 Fase 2** — backend gebruikersaanmaak: `gebruiker_persoon`-koppeltabel (migratie 0037),
  Keycloak Admin API-provisioning via dedicated service-account `kilara-user-provisioning`
  (least-privilege manage-users/view-users), server-gegenereerd eenmalig wachtwoord,
  orphan-cleanup. Live-geverifieerd na realm-herimport.
- **ADR-029 Fase 4** — gebruikersbeheer-scherm (beheerder-only nav + lijst + aanmaak-dialog +
  eenmalig-wachtwoord-weergave).
- **ADR-029 Fase 3b** — sub-stempeling: `verklaard_door_sub` (klaarverklaring, migratie 0038) +
  plateau `bevestigd_door` {sub,email}; gedeelde `actor_resolutie`-helper (sub→naam, e-mail-fallback);
  read-side `verklaard_door_naam`/`bevestigd_door_naam`. ADR-027 wijzigingshistorie bijgewerkt.
- **ADR-029 Fase 3a** — audit-view + `actor_naam`-batchverrijking + actie-filter + naam-filter
  (naam→sub).
- **Objecthistorie** — `GET /objecthistorie/{type}/{id}` (toegang-volgt-object, geen AUDITLOG-gate)
  + herbruikbaar `ObjectHistoriePaneel` ('i'-knop) op 8 detailschermen, per-record diff met
  NL-veldlabels, "Meer laden".
- **Dev-seed-fix**: `dev_seed_testdata.py` crashte bij reseed op de met migratie 0034 verwijderde
  `eigenaar_naam`/`leverancier`-kwargs (pre-existing DC015-vondst).

**Volgende prioriteiten (DC015 → DC016)**:
1. **ADR-029 Fase 5** — `gereedmeld_recht` (per-type persoon × componenttype) + per-type check in
   de klaarverklaring-service. **Laatste open ADR-029-fase.**
2. **ADR-023 Fase F-rest** — checklist-consistentiecheck technische plaatsing (E-8) + resterende
   RBAC/audit nieuwe entiteiten.
3. **Landschapskaart server-side ego-subgraaf** (`?center=<id>&diepte=1|2`).
4. **LIKARA codebase-rename** (geparkeerd, DC013).

**Nieuwe opvolgpunten (DC015)**:
- **Dode backend-proxy-properties** `Applicatie.eigenaar_naam` / `.leverancier` (`models.py:382/386`)
  lezen een sinds migratie 0034 niet-bestaande kolom — inert (niet in Read-schema's), opruimbaar in
  een aparte backend-taak.
- **Naam-filter audit-view** eventueel als ZoekSelect-op-personen (nu vrije-tekst; bewuste
  search-semantiek — alleen als de praktijk een pick verkiest).
- **id→naam-resolutie in objecthistorie-diff** (`*_id`-velden tonen nu de gelogde id-waarde;
  per-veld id→naam zou een lookup per type vergen).

### Stand V014 (sessie-afsluiting DC013, 2026-06-19)

Build **V014**, migratie head **`0034`**.
Tests: **810** backend + **440** frontend groen (52 files).

**AF deze sessie (DC013)**:
- complidata-domeinmodel skill aangemaakt (CC + claude.ai)
- ADR-024 volledig geland: contract-leverancier verbreed
  (organisatie/afdeling/externe_partij; persoon geblokkeerd);
  roltoewijzing toevoegbaar vanuit partij-detail;
  ADR-024-document bijgewerkt naar werkelijke stand;
  functietitel (persoon-only, migratie 0033);
  eigenaar_naam/leverancier vrije tekst verwijderd (migratie 0034);
  9 beheerrollen (Account Manager + Service Delivery Manager)
- ADR-025 volledig geland (Landschapskaart v4, Cytoscape.js):
  Ego/Impact/Geheel model; zoeken + 4 filters; actieve set;
  node-detail + "Open applicatie →"; blokkade-icoon;
  lifecycle-kleuren; koppelingsdetails (protocol/richting) op edges;
  migratieplaatsing (plateau/dispositie) in detail-paneel;
  diepte-toggle; Koppelingenkaart vervangen; ADR-025-document bijgewerkt
- ZoekSelect-standaard vastgelegd in complidata-frontend skill
- PartijFormulier organisatie-/afdelingskiezer naar ZoekSelect
- LIKARA productnaam besloten (Logische ICT Kaart Afhankelijkheden Relaties Analyse)
- ADR-028 voorstel geland (componentrol + BIV-classificatie, geparkeerd na ADR-027)
- complidata-domeinmodel/-frontend/-ux skills bijgewerkt (DC013-patronen)

**Volgende prioriteiten (DC013 → DC014)**:

1. **ADR-027 — Component-klaarverklaring. ✅ COMPLEET** (DC014): slice 1 model
   (`component_klaarverklaring`, migratie 0036, niet-scorend, herroepbaar, engine-gescheiden) →
   slice 2 UI (Migratiegereedheid-blok + klaar verklaren/heropenen met reden op ApplicatieDetail,
   commit 979a646) → slice 3 dashboard (tellingen `klaar_verklaard` + `klaar_met_afwijking` +
   lijstfilter `klaarverklaring=klaar`/`afwijking=1`, commit 6ffd7e6). Per-categorie + werkverdeling
   bewust vervallen. **Restpunten (nieuw, zie hieronder):** klaarverklaring-blok ook op ComponentDetail.

2. **ADR-029 — Gebruiker-partij-koppeling + per-type gereedmeld-autorisatie** (geparkeerd voorstel,
   fundament voor eerste implementatie). Brug Keycloak-login ↔ persoon-partij (ADR-024) + per-type
   gereedmeld-recht aan de persoon + apart beheerder-autorisatierecht (gescheiden van PARTIJ) +
   gescheiden verantwoordingsketen. Verfijnt het grove ADR-027-recht (per-persoon/per-type,
   preventief); ADR-027 hangt er niet op. Zie docs/adr/ADR-029_Gebruiker_partij_autorisatie_voorstel.md.

3. **ADR-023 Fase F**: checklist-consistentiecheck technische plaatsing (E-8, deferred),
   platform-beheer relatie-kenmerk-catalogus, RBAC/audit nieuwe entiteiten.

4. **Landschapskaart server-side ego-subgraaf** (aparte slice): `?center=<id>&diepte=1|2`
   voor een gereduceerde graaf i.p.v. de volledige tenant-graaf. Vereist nieuw endpoint-contract.

5. **ADR-025 overige roadmap**: vervangingsrelatie, export PNG/PDF, pad-inzicht (kortste route
   A→B), clustering op domein.

**Nieuwe opvolgpunten (DC014)**:
- **Klaarverklaring-blok ook op ComponentDetail** (niet-applicatie checklist-dragende
  componenten). Het model is component-generiek; alleen ApplicatieDetail heeft nu de
  Migratiegereedheid-UI. Triviale follow-up: het herbruikbare `MigratiegereedheidSectie`-blok
  + de knop op ComponentDetail plaatsen.
- **Dode `<dl>`-rijen op ApplicatieDetail Overzicht** opruimen: "Eigenaar (naam)" + "Leverancier"
  tonen sinds migratie 0034 (velden uit schema/form verwijderd) altijd "—".
- **CLAUDE.md interactie-secties consolideren**: deels overlappende blokken (Werkprotocol +
  "Werkwijze CC + claude.ai"); samenvoegen tot één gezaghebbende bron.

**Nog open uit eerdere sessies (doorgeschoven, ongewijzigd geldig)**:
- **Signalerings-ADR / registratiegaten ("bolletjes")** — (1) object zonder toegewezen rol;
  (2) lege eigenaar-organisatie/gebruikersgroep-organisatie (geparkeerd); (3) contract zonder
  leverancier (indicator + statusfilter + dashboard-ratio); (4) lege 'Eigenaar'-kolom blokkadelijst.
  Generalisatie-discipline n≥2; read-only, geen engine-poort.
- **Architectuuroverzicht-sortering volgt codewaarde, niet NL-label** — geaccepteerd randgeval (B2/B6-a).
- Tenant-eigen partijsoort (geparkeerd); per-tenant zichtbaarheid catalogus-opties; OP-29 label-rename;
  `SUBTYPE_HEEFT_DATA` 422↔409-heroverweging.

---

### Stand V013 (sessie-afsluiting DC012, 2026-06-18) — ADR-024-vervolg + UX-doorlichting

Build **V013**, migratie head **`0032`**. Tests: **799** backend + **429** frontend groen
(1 pre-existing env-auth-test, OP-30). Deze sessie: rol-toewijzing (eigen tabel), volledige
UX-doorlichting gedicht, migratielaag-CRUD compleet, organisatie overal als verwijzing naar
het partijenregister.

**AF deze sessie (DC012)**: UX-doorlichting **volledig gedicht** (A1–A4, B1–B6); **rol-toewijzing**
(`roltoewijzing`, slice 2b — eigen tabel bij tegengestelde uniciteit); **migratielaag-CRUD compleet**
(plateau/werkpakket/deliverable/gap beheerbaar in de UI); **`complidata-ux`-skill geland**;
architectuuroverzicht server-side sorteerbaar; B6 organisatie-uit-partijenregister (gebruikersgroep +
applicatie/component).

*(De DC012→DC013-prioriteiten zijn afgehandeld of doorgeschoven naar het V014-blok hierboven —
ADR-024-document is bijgewerkt; signalerings-ADR + sorteer-randgeval staan nu onder "Nog open uit
eerdere sessies" bij V014; ADR-025 is geland.)*

### Stand V008 (sessie-afsluiting 2026-06-13) — ADR-022 volledig afgerond

Build **V008**, migratie head **`0009`** (3 ADR-022-migraties: `0007` profiel, `0008` tenant-vragenset,
`0009` `checklist_dragend`-vlag). Tests: **567** module + **72** platform (1 pre-existing env-auth-test,
zie OP-30) + **255** frontend groen. ADR-022 (Fase A–F + W1) compleet: een componenttype kan een
eigen, **tenant-eigen** checklist dragen — profiel, scoring, lifecycle, toestand-gebaseerde type-lock,
per-type readiness — losgekoppeld van `applicatie`.

**Volgende prioriteiten**:
1. **ADR-006 — hash-chained audit-trail (#17)**: volgende grote prioriteit. ADR-022 ging er bewust
   vóór, zodat de audit-trail het definitieve besturingsmodel logt (append-only, nooit verwijderen).
2. **Tenant-onboarding (#16)**: automatische **baseline-kopie** van de vragenset bij `POST /tenants`
   (de #16-knip uit W1) — vandaag seedt alléén `dev_seed` per tenant; de platform-onboarding-hook
   ontbreekt. De seed schrijft tenant-scoped data → `cd_app` met de nieuwe tenant-RLS-context.

**Bewust vastgelegde foutcode-keuzes (ADR-022)**: `SUBTYPE_HEEFT_DATA` = HTTP **422** (Fase C
type-lock, via `OngeldigeRegistratie`; heroverweging naar 409 is open); checklistvraag type-mismatch
= HTTP **404** (`NietGevonden`, Fase B/E; OP-6-stijl, geen nieuwe code).

**Afgehandeld deze sessie**: lokale CC-settings (`settings.local.json`) nu **durable in-repo**
genegeerd via `.claude/.gitignore` (`*.org.json`, `.DS_Store`) — voorheen enkel via de globale
`~/.config/git/ignore`; het stray-bestand `settings.local.json.org.json` is opgeruimd.

### OP-29 — Impact-/graaf-lens veldlabel `aantal_applicaties` (naamsmell sinds Fase E) — OPEN (nice-to-have)

`component_service.impact_analyse` / `schemas.component.ImpactSamenvatting.aantal_applicaties` telt
sinds ADR-022 Fase E **alle** profiel-dragende geraakte componenten, niet alleen `applicatie`. De
lens is functioneel correct (profiel-generiek sinds Fase A); alleen het veldlabel is misleidend.
Verheldering = rename (bv. `aantal_beoordeeld`) — bewust buiten Fase E/F gehouden.

### OP-30 — `test_auth_pkce` Secure-cookie env-test faalt omgevingsgebonden — OPEN

`test_auth_pkce.py::test_callback_succes_zet_cd_session_cookie` faalt op de Secure-cookievlag in
test/dev; faalt identiek op een schone `HEAD` (los van ADR-022). Te onderzoeken: de Secure-cookie-
assertie omgevings-onafhankelijk maken (bv. `cookie_secure` expliciet in de testconfig forceren).

### OP-3 — Refresh-token-subsysteem (uit P2) — OPEN

P2 zet bewust geen refresh-token; sessie verloopt na 15 min en vereist
opnieuw inloggen. Bouwen: `/auth/refresh`, veilige server-side opslag van de
refresh-token gekoppeld aan een sessie-id, rotatie/intrekking, koppeling aan
de 8-uurs refresh-grens (CLAUDE.md). Geen token client-leesbaar.

### OP-4 — RP-initiated logout via Keycloak (uit P2) — AFGEROND (geverifieerd CD038)

Al geïmplementeerd (CD008/CD010): `POST /auth/logout` trekt het Redis-refresh-handle in
(haalt `id_token_hint`), wist `cd_session`+`cd_refresh`, en geeft de Keycloak
end-session-URL terug; de store (`auth.logout()`) navigeert ernaartoe zodat ook de
SSO-sessie eindigt. Werkt identiek voor tenant- én platform-accounts (gedeelde
login-/logout-infra). Gedekt door `logout.test.js` (redirect naar end-session-URL +
`/login`-fallback). In CD038 is de stale `AppLayout.vue`-comment (die nog "buiten scope"
beweerde) rechtgezet.

### OP-6 — Resource-ownership binnen tenant (P5/ADR-010) — AFGEDEKT (fase 1, P5)

Afgedekt voor fase 1 — tenant-scoped record-resolutie (kruis-tenant → 404) +
rol + RLS volstaan; per-gebruiker-eigenaarschap niet nodig in fase 1
(collaboratief register, ADR-009).

Geïmplementeerd in P5 (Applicatie-CRUD, referentie voor de overige entiteiten):
record-resolutie strikt binnen de tenant-sessie (RLS + expliciete
`tenant_id`-filter); een id buiten de tenant is niet vindbaar ⇒ HTTP 404
`NIET_GEVONDEN` (geen 403, geen onderscheid "bestaat niet" vs "andere tenant",
dus geen lek). Binnen de tenant geldt rol-gebaseerde autorisatie via
`vereist_permissie`; elke Medewerker/Beheerder mag elk record in de eigen tenant
bewerken. Fijnmazig per-gebruiker-eigenaarschap is bewust uitgesteld en pas te
heroverwegen als een toekomstige eis daarom vraagt.

### OP-7 — 401 en 403 in hetzelfde foutformaat (uit P3) — AFGEROND (geverifieerd CD037)

401 is al canoniek `{"fout":{...}}` (CD005): `NietGeauthenticeerd` +
`niet_geauthenticeerd_handler`, en `auth.py`-`_fout` levert hetzelfde envelope.
Live bevestigd op tenant-endpoint, `/auth/me`, `/auth/platform/me` en bij decode-fout;
de frontend (`api.js`) keyt op de **statuscode** en leest `body.fout.code`. 422 blijft
bewust native (ADR-014). In CD037 zijn nog twee stale route-docstrings
(`applicatie.py`/`dashboard.py`) rechtgezet en is een test toegevoegd die het
canonieke 401-envelope op een guarded tenant-route vastlegt.

### OP-13 — Platform-tabel-grants Platforminstellingen/Platformmetadata — OPEN

Het platform-permissiedomein (ADR-012) kent `Platforminstellingen` en
`Platformmetadata`, maar alleen de `tenant`-tabel bestaat. Bij het bouwen van
die endpoints: tabellen + migratie + `GRANT … TO cd_platform` /
`REVOKE … FROM cd_app` (zelfde patroon als `tenant`).

### OP-14 — Dev-credentials vervangen vóór productie — OPEN

`changeme_dev` staat als dev-default in realm (client-secret + testgebruikers)
en DB-rollen (cd_app/cd_platform/cd_admin via `POSTGRES_PASSWORD`). Vóór
productie vervangen door secrets; testgebruikers verwijderen of scheiden van
productie-realm.

### OP-16 — `tenantSlug`-getter leest verkeerd veld — AFGEROND (geverifieerd CD036)

De getter is al gecorrigeerd: `frontend/src/store/auth.js` kent **geen** `tenantSlug`
meer — de getter heet `tenantId` en leest `user.tenant_id` (de werkelijke `/auth/me`-
payload). `useTheme` gebruikt `auth.tenantId`; gedekt door `tenantId.test.js`
(`OP-16: tenantId-getter leest tenant_id`). De oorspronkelijke "leest verkeerd veld"-
bug bestaat niet meer (gefixt in een eerdere sessie, hier tegen de code bevestigd).

**Resterende testrand (CD019, minor)**: na het afhandelen van de `useTheme`-promise (`.catch` in
`tenantId.test.js`) resteert nog één pre-existing happy-dom `DOMException` (interne
resource-`fetch` van de thema-stylesheet, afgebroken bij window-teardown) op stderr —
telt niet als test-fout. Op te ruimen zodra `useTheme` echte call-sites + een
default-thema-fallback krijgt en de test wordt herontworpen met een expliciete
`onerror`-trigger i.p.v. happy-dom's toevallige `fetch`.

### OP-18 — Stale V001-docs (IMPLEMENTATIEPLAN / SESSIE_BRIEFING) — AFGEROND (CD018)

`IMPLEMENTATIEPLAN.md` is voorzien van een *HISTORISCH — V001-snapshot*-banner die naar
de live bronnen verwijst (CD013). De stale `SESSIE_BRIEFING.md`-bouwstatus is opgelost
in **CD018**: `update_claude_bouwstatus` draait nu vóór de generators (i.p.v. ná de
briefing-generatie), zodat `gen_sessie_briefing.py` het nieuwe `BOUWSTATUS`-blok leest.
Geborgd met `backend/tests/test_gen_build_volgorde.py` (functionele write-then-read +
statische volgorde-guard via `inspect.getsource`).

### OP-19 — Frontend bundle >500 kB — AFGEROND/gemitigeerd (geverifieerd CD038-sweep)

`vite build`: géén ">500 kB"-waarschuwing meer; de grootste chunk is `column-*.js`
(PrimeVue DataTable) op **384 kB** (<500 kB), geïsoleerd in een eigen chunk die alleen met
`ApplicatieDetail` laadt. **6 route-level lazy-imports** (CD012) verkleinen de initiële bundle
(`index` ≈ 164 kB). Het oorspronkelijke symptoom doet zich niet meer voor; verdere reductie is
optioneel (geen verplichting).

### OP-21 — Eigenaar-filter als distinct-dropdown (UX, optioneel) — AFGEROND (B6-b, DC012)

Ingehaald door **UX-B6-b**: `eigenaar_organisatie` is geen vrije tekst meer maar een
**verwijzing naar een organisatie-partij**. Het lijstfilter is daarmee een **zoekbare
organisatie-keuze** (`ZoekSelect` op `eigenaar_organisatie_id`, server-side), en sortering loopt
op de gejoinde organisatie-naam (v2n-keyset). De vrije-tekst-`ilike` bestaat niet meer.

### OP-20 — Live-DB-verificatie NULLS-LAST-paginering blokkadesoverzicht (#23) — OPEN

De NULLS-LAST-keyset van het tenant-brede blokkadesoverzicht (CD016, ADR-017 B5:
`encode/decode_sort_cursor_nullable` + `keyset_seek_nulls_last`) is offline
**structureel** getest (cursor-roundtrip met null-vlag, `.nulls_last()` in de
ORDER BY, IS NULL-takken in de seek), maar nog niet **empirisch** tegen Postgres.
Bevestig tijdens de **live-DB-run (#23 / Laag 5)** dat het over de NULL-grens
correct pagineert op de nullable kolommen (`toelichting`, `eigenaar`, `opgelost_op`),
in zowel `asc` als `desc`, zonder duplicaten of overgeslagen rijen.

### OP-23 — Cyclus-padbewaking bij invoer van structuurrelaties (B3) — OPEN

`component_structuur` staat cycli toe (B3): `ZELFVERWIJZING` (self) wordt geweigerd, maar een
indirecte cyclus (A→B, B→A, …) niet. De **leeskant is al cyclus-veilig** (visited-set in elke
traversal, o.a. de impactanalyse CD056). Open vraag: willen we cycli **bij invoer** detecteren/
waarschuwen (pad-bewaking in `component_structuur_service.maak_aan`), of blijft de data-laag
cycli toestaan en bewaakt alleen het leeswerk? Geen verplichting; oppakken als de praktijk
verwarrende cycli oplevert.

### OP-24 — C-drempel: catalogus-keuzevelden zoekbaar boven ~10 opties — OPEN

Catalogus-gedreven keuzevelden (componenttype, relatietype, contract-rol) zijn nu native
`<select>`. Zodra een dimensie structureel **>~10 actieve opties** krijgt, heroverwegen naar een
`ZoekSelect` (zelfde regel als entiteit-referenties, zie complidata-frontend). Geen verplichting;
drempel-gedreven. [CD049]

### OP-25 — Uvicorn-accesslog zonder timestamps — OPEN

De Uvicorn-accesslog mist timestamps, wat live-debugging bemoeilijkt. Logformat configureren
(timestamp + niveau) bij een logging-/observability-pass. Klein, nice-to-have. [CD048]

### OP-26 — `component.eigenaar_organisatie` NOT NULL vs. optionele eigenaar — AFGEROND (B6-b, DC012)

Ingehaald door **UX-B6-b** (migratie 0032): de NOT NULL-vrije-tekstkolom `eigenaar_organisatie` is
vervangen door een **optionele** composiet-FK `eigenaar_organisatie_id → element` (partij,
aard=organisatie). De `""`-workaround is verdwenen; schema's/API dragen nu `None` (echt optioneel).

### OP-27 — Dev-seed in een dev-guarded init-stap — OPEN (nice-to-have)

De dev-testdata (`dev_seed_testdata.py`) is een **handmatige** fixture (niet in de init-container,
bewust dev-only/prod-veilig). Na een reset (`down -v && up -d`) moet hij apart gedraaid worden.
Optioneel: een **dev-guarded** init-stap (bv. env-flag `SEED_DEV=true`) die de dev-seed
automatisch draait in lokale/dev-omgevingen, zodat `down -v && up -d` direct de volledige baseline
geeft — zonder risico op prod-seeding. Raakt de seed-pipeline → eigen besluit. [CD055]

### OP-28 — VPS-deployment — OPEN (roadmap-kandidaat, t.z.t.)

Besluit Bert: in een volgende sessie oppakken. Doel nog te bepalen (demo/test vs. productie).
Raakt: **OP-14** (secrets-hardening — overal `changeme_dev` vervangen door echte secrets); een
**productie-compose-variant** + reverse proxy/HTTPS (alleen 80/443 open); **Keycloak
production-mode** (`KC_HOSTNAME`, redirect-URI's/CORS op het echte domein i.p.v. localhost);
**offsite backups** (de pg_dump-keten bestaat al en is sinds CD055 Keycloak-vrij). Bij een
**productie**-doel zijn **ADR-006** (audit-trail) en **#16** (user-/tenantmanagement)
voorwaarden. EU-jurisdictie-VPS conform de platform-uitgangspunten.

### OP-22 — Backup-scope / secops: Keycloak-secrets in de DB-dump — AFGEROND (geverifieerd CD055)

Opgelost via de tweede optie: **Keycloak draait op een eigen database** `keycloak` (rol
`kc_user`, `init-db/02_keycloak.sql`), losgekoppeld van de app-DB `complidata`. De backup
(`gen_build.py` → `pg_dump complidata`) bevat daardoor **geen** Keycloak-auth-schema meer
(`credential`/`client`/…); geverifieerd in CD055: `pg_dump --schema-only` van `complidata` levert
**0** Keycloak-tabellen. Loste tegelijk de `COMPONENT`-naamruimte-collision op (onze ADR-021-tabel
schaduwde Keycloak's interne `COMPONENT` in het gedeelde `public`-schema → Keycloak startte niet).
Zie complidata-db "V007-patronen" en `docs/LOKAAL-TESTEN.md` (named volume + reset).

---

### ADR-028 — Componentclassificatie (geparkeerd, na ADR-027)

Voorstel geland (DC013). Twee uitbreidingen op het componentmodel:
(1) **Componentrol** (platform-breed): interne_applicatie /
interne_dataprovider / externe_dataprovider / koppelvlak —
bepaalt of koppelingen zelfstandig omgehangen kunnen worden of
afhankelijk zijn van externe ketenafspraken; zichtbaar in
Landschapskaart als visueel onderscheid.
(2) **BIV-classificatie** (tenant-scoped schaal): Beschikbaarheid,
Integriteit, Vertrouwelijkheid — drie velden op component met
tenant-eigen 3- of 5-punts schaal; filterbaar in Landschapskaart,
basis voor migratieset-risicobeoordeling.
Zie docs/adr/ADR-028_componentclassificatie_voorstel.md.

---

### LIKARA — naamswijziging codebase (geparkeerd, DC013)

Besloten productnaam: LIKARA (Kaart ICT Landschap Afhankelijkheden
Relaties Analyse). Vervangt CompliData/CompliMan overal in de
codebase: bestandsnamen, variabelen, README, CLAUDE.md,
seed-namen, Keycloak-realm, Docker-images. Uitvoeren als
gecontroleerde zoek-vervang-slice in een aparte sessie.

---

## AFGEROND (sessie 2–3)

- **O2** — 7.5 BIO2-classificatie → BBN (CD035): de default-optieset van vraag 7.5 is
  **BBN1/BBN2/BBN3** i.p.v. Laag/Midden/Hoog. Expand/contract: `seed_antwoordconfig`
  levert fresh deploys direct BBN; migratie **0004_bio2_bbn** soft-deactiveert de legacy
  `laag/midden/hoog`-opties op bestaande deploys (incl. dev-DB). Bestaande
  `antwoord_waarde` blijft resolvebaar (inactieve sleutels mét `actief`-vlag). Idempotent;
  engine-tellingen (1·4·3·4 / 7·1·2) ongewijzigd. O3/O4 blijven open observaties.
- **OP-15** — CLAUDE.md test-mode-comment (CD013): de comment was al rechtgezet in
  V004 — `COMPLIDATA_TEST_MODE` versoepelt alleen de Origin-check + rate-limit, geen
  auth-stub, seedt niets, inloggen vereist Keycloak. Punt afgesloten.
- **OP-17** — ADR-009 enum-voetnoten ↔ code (CD013): ADR-009 bijgewerkt naar de
  werkelijke code-waarden (`models.py` als single source, == migratie): hostingmodel 7,
  migratiepad 6 (incl. `tijdelijk_gedeeld`), datatype 6 (incl. `combinatie`),
  protocol = vaste enum, `eigenaar_organisatie`/`organisatie` = vrije tekst,
  `checklist_compleet` transient (ADR-013 B4).
- **OP-1** — platform_init-seed als deploystap → vervangen door de
  init-container (ADR-011): `cd-migrate` migreert (cd_admin) → `platform_init`
  → sluit af, met gating vóór de app. CLAUDE.md Commands bijgewerkt.
- **OP-2** — plantekst + skills bijgewerkt → §Architectuurcorrectie in
  `IMPLEMENTATIEPLAN.md` gecorrigeerd; `platform_init`/deploypatroon in
  complidata-db/-security/-tests vastgelegd.
- **OP-5** — cookie-attributen settings-driven (`cookie_secure`/`samesite`/
  `domain`) bevestigd; `COOKIE_SECURE=false` voor lokaal http (P4).
- **OP-8** — CONTRIBUTING §6 As 2 gecorrigeerd naar
  `python3 -m pytest backend/tests/ modules/` (groen geverifieerd).
- **OP-9** — deploy-/migratiestrategie vastgelegd in **ADR-011** (init-container).
- **OP-10** — OIDC `redirect_uri` gelijkgetrokken (realm ↔ backend) +
  realm-import (`--import-realm`); login-round-trip werkt.
- **OP-11** — `cd_admin` volledig uit de app-laag; `cd_platform` (non-superuser)
  voor platform-endpoints (ADR-012).
- **OP-12** — rol-mapping/tweelaags rollenmodel → opgegaan in **ADR-012**
  (realm-rollen → `realm_access.roles`, platform- + tenant-domein).
