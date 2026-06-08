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

### OP-4 — RP-initiated logout via Keycloak (uit P2) — OPEN

`auth/logout` wist nu alleen de lokale `cd_session`-cookie; de Keycloak-SSO-
sessie blijft staan, waardoor een volgende `/login` stil kan herinloggen.
Aanvulling: Keycloak end-session-endpoint aanroepen bij logout.

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

### OP-7 — 401 en 403 in hetzelfde foutformaat (uit P3) — OPEN

403 gebruikt het canonieke `{"fout":{...}}`-formaat; 401 volgt nog het
bestaande `{"detail":{"code":...}}`-patroon van de auth-laag. Op termijn beide
gelijktrekken naar `{"fout":{...}}`.

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

### OP-16 — `tenantSlug`-getter leest verkeerd veld — OPEN

`frontend/src/store/auth.js` `tenantSlug` leest `user.tenant_slug`, maar `/auth/me`
geeft `tenant_id` → altijd `null`. Raakt `useTheme`/per-tenant-thema's zodra die
gebouwd worden.

### OP-18 — Stale V001-docs (IMPLEMENTATIEPLAN / SESSIE_BRIEFING) — DEELS AFGEROND

`IMPLEMENTATIEPLAN.md` is voorzien van een *HISTORISCH — V001-snapshot*-banner die naar
de live bronnen verwijst (CD013). **Resteert:** `SESSIE_BRIEFING.md` toont een stale
bouwstatus (titel = nieuwe build, body = vorige build). Oorzaak is een volgorde-bug in
`gen_build.py`: `gen_sessie_briefing.py` (stap 4) leest het `BOUWSTATUS`-blok uit
CLAUDE.md vóór `update_claude_bouwstatus` (stap 7) het bijwerkt. Het bestand is
gegenereerd — niet met de hand bewerken; de generator-fix is een aparte beslissing.

### OP-19 — Frontend bundle >500 kB — OPEN

De productie-bundle overschrijdt 500 kB (PrimeVue DataTable). Route-level
lazy-loading / code-splitting als optimalisatie.

### OP-20 — Live-DB-verificatie NULLS-LAST-paginering blokkadesoverzicht (#23) — OPEN

De NULLS-LAST-keyset van het tenant-brede blokkadesoverzicht (CD016, ADR-017 B5:
`encode/decode_sort_cursor_nullable` + `keyset_seek_nulls_last`) is offline
**structureel** getest (cursor-roundtrip met null-vlag, `.nulls_last()` in de
ORDER BY, IS NULL-takken in de seek), maar nog niet **empirisch** tegen Postgres.
Bevestig tijdens de **live-DB-run (#23 / Laag 5)** dat het over de NULL-grens
correct pagineert op de nullable kolommen (`toelichting`, `eigenaar`, `opgelost_op`),
in zowel `asc` als `desc`, zonder duplicaten of overgeslagen rijen.

---

## AFGEROND (sessie 2–3)

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
