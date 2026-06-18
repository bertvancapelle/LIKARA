# CompliData — Opvolgpunten (backlog)

Bijgehouden met de hand. Niet door `gen_build.py` gegenereerd.
Bron: sessie 2–3 (P1–P5, OP-9 t/m OP-12). Status per punt expliciet vermeld.

---

## OPEN

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

**Volgende prioriteiten (DC012 → DC013)**:

1. **ADR-024-document bijwerken — EERSTE PRIORITEIT.** Het ADR-024-document staat nog op
   "slice 1 (externe partij)", terwijl deze sessie **rol-toewijzing**, **partij-lidmaatschap-beheer**
   (persoon/afdeling → organisatie) en **organisatie-koppeling** (gebruikersgroep-organisatie +
   eigenaar-organisatie als partij-verwijzing) zijn gebouwd. Het document **loopt achter op de bouw**
   → bijwerken zodat het de werkelijke stand weerspiegelt.

2. **Signalerings-ADR / registratiegaten ("bolletjes")** — verzameld, **geen actie tot opgepakt**.
   Verzamelde gevallen:
   - (1) **object zonder toegewezen rol** (applicatie/component/contract zonder verantwoordelijke);
   - (2) **lege eigenaar-organisatie** op applicatie/component én **lege organisatie** op gebruikersgroep
     (B6 DC012: het veld is nu een optionele keuze uit het partijenregister; signaleren-als-gat geparkeerd);
   - (3) **contract zonder leverancier** (groen/amber-indicator + statusfilter + dashboard-ratio met
     drill-down — apart contract-spoor, pas ná leverancier-optioneel-maken);
   - (4) **lege 'Eigenaar'-kolom op de blokkadelijst.**
   **Patroon (generalisatie-discipline n≥2)**: bouw de tweede concrete instance naast de eerste vóór je
   abstraheert. **Score blijft de enige lifecycle-driver**; signalering is puur **read-only**, geen
   engine-poort.

3. **Architectuuroverzicht-sortering volgt codewaarde, niet het NL-label** — geaccepteerd randgeval
   (B2/B6-a): Laag/Aspect/Soort sorteren server-breed op de opgeslagen **snake_case-codewaarde**; de UI
   toont het NL-label. Sorteren-op-label zou een verbouwing vergen voor klein effect → pas oppakken bij
   een concrete wens.

**Blijvend open (ongewijzigd geldig)**: tenant-eigen partijsoort (geparkeerd); per-tenant zichtbaarheid
van catalogus-opties; **ADR-025** (praatplaat) en **ADR-027** (categorie-klaarverklaring) als geplande
ADR's na het ADR-024-vervolg; eventuele resterende ADR-022-follow-ups (o.a. OP-29 label-rename,
`SUBTYPE_HEEFT_DATA` 422↔409-heroverweging).

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
