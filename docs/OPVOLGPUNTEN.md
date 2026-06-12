# CompliData — Opvolgpunten (backlog)

Bijgehouden met de hand. Niet door `gen_build.py` gegenereerd.
Bron: sessie 2–3 (P1–P5, OP-9 t/m OP-12). Status per punt expliciet vermeld.

---

## OPEN

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

### OP-21 — Eigenaar-filter als distinct-dropdown (UX, optioneel) — OPEN

CD017 filtert `eigenaar_organisatie` met een vrije-tekst `ilike`-contains (robuust
bij ongecontroleerde vrije tekst). Als de organisatie-waardenset per tenant klein
en stabiel blijkt, is een tenant-scoped distinct-waarden-dropdown
(`GET .../eigenaar-organisaties`) een nettere UX. Geen verplichting; pas oppakken
als de praktijk erom vraagt.

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

### OP-26 — `component.eigenaar_organisatie` NOT NULL vs. optionele eigenaar — OPEN

De kolom `component.eigenaar_organisatie` is in de DB **NOT NULL**, terwijl een kaal component
(database/fileshare) en de convergente aanmaak een **lege** eigenaar toestaan (service defaultt
`None`→`""`). De `""`-default is een workaround; bij een volgende migratie-gelegenheid de kolom
**nullable** maken en de API/schema's `None` laten dragen i.p.v. lege string. Geen functionele
bug; opruimpunt. [CD054]

### OP-27 — Dev-seed in een dev-guarded init-stap — OPEN (nice-to-have)

De dev-testdata (`dev_seed_testdata.py`) is een **handmatige** fixture (niet in de init-container,
bewust dev-only/prod-veilig). Na een reset (`down -v && up -d`) moet hij apart gedraaid worden.
Optioneel: een **dev-guarded** init-stap (bv. env-flag `SEED_DEV=true`) die de dev-seed
automatisch draait in lokale/dev-omgevingen, zodat `down -v && up -d` direct de volledige baseline
geeft — zonder risico op prod-seeding. Raakt de seed-pipeline → eigen besluit. [CD055]

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
