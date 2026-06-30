---
name: likara-security
description: Security-patronen voor LIKARA (Zero Trust, httpOnly cookies, NCSC, RLS). Beschrijft de werkelijke V001-staat.
stack: Keycloak 24.x, FastAPI middleware, Redis, PostgreSQL RLS
bijgewerkt: V016
---

# LIKARA Security Skill

## Kernregel: httpOnly cookies — geen localStorage

```javascript
// VERBODEN
localStorage.setItem('token', ...)
```

Sessie loopt via de `lk_session` httpOnly cookie (`HttpOnly`, `Secure`,
`SameSite=Strict`). De backend leest de cookie en valideert de Keycloak-JWT
via JWKS.

## SecurityHeadersMiddleware — exact 6 headers

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

## OriginCheckMiddleware

- Controleert de Origin-header op muterende methodes (POST/PUT/PATCH/DELETE).
- Uitzondering: `likara_test_mode` accepteert requests zonder Origin.
- Bij mismatch/ontbreken: HTTP 403, foutcode `ORIGIN_GEWEIGERD`.

## Auth endpoint-patroon

```python
# /api/v1/auth/me — 401 NIET_GEAUTHENTICEERD (canoniek envelope) zonder sessie (CD005)
@router.get("/auth/me")
async def me(request: Request, user: AuthenticatedUser = Depends(get_current_user)):
    return asdict(user)

# /api/v1/auth/logout — RP-initiated (CD008/CD010): lokaal intrekken (lk_session +
# lk_refresh + Redis-refresh-handle) + Keycloak end-session-URL teruggeven met
# id_token_hint (naadloze redirect). Zie de V004-sectie hieronder.
```

`get_current_user` zonder cookie → 401 `NIET_GEAUTHENTICEERD`; bij decode-fout → 401
+ Redis auth-fail-counter (IP gepseudonimiseerd). Token zonder `tenant_id` → 403
`TENANT_MISMATCH` (auth-grens). Alle drie canoniek `{"fout":{…}}` (ADR-014).

## DB-rollen — driedeling (ADR-011/012)

```python
# lk_app       — non-superuser, tenant-werk onder RLS (get_session / get_tenant_session)
# lk_platform  — non-superuser, platform-endpoints (get_platform_session)
# lk_admin     — superuser, UITSLUITEND init-container (migratie + platform_init); NOOIT in de app
```

`lk_admin` is volledig uit de app-laag (OP-11): geen `admin_database_url`, geen
`get_admin_session`. Platform-werk loopt via `lk_platform`. Details + grants:
zie likara-db (DB-rollen / migratie-deploypatroon).

## Tweelaags rollenmodel + twee permissiedomeinen (ADR-012)

Een account is **óf platform óf tenant — nooit beide** (strikt gescheiden):

| Domein | Rollen | Permissietabel | Guard | Sessie |
|---|---|---|---|---|
| Tenant | viewer · medewerker · beheerder · auditor | `core/rbac.py` `PERMISSIES` | `vereist_permissie` | `get_session` (RLS) |
| Platform | platformbeheerder · platformoperator | `core/platform_rbac.py` `PLATFORM_PERMISSIES` | `vereist_platform_permissie` | `get_platform_session` (lk_platform) |

- Twee **onafhankelijke** barrières: een tenant-rol op een platform-endpoint ⇒
  **403**, en een platform-rol op een tenant-endpoint ⇒ **403** (kruis-scheiding).
- `platformoperator` = read-only op platform-metadata (Tenant=L, Metadata=L,
  Platforminstellingen=—); nooit tenantinhoud, nooit mutatie.
- `platformbeheerder` = CRUD op Tenant + Platforminstellingen, Metadata=L.

## Twee auth-paden

```python
# Tenant-endpoints — vereist tenant_id, leest TENANT-rollen
get_current_user(request) -> AuthenticatedUser     # 403 TENANT_MISMATCH zonder tenant_id

# Platform-endpoints — GEEN tenant_id, leest alleen PLATFORM-rollen
get_current_platform_user(request) -> PlatformUser  # platform-accounts hebben geen tenant-context
```

Een platform-account heeft principieel géén `tenant_id` ⇒ het kan een
tenant-endpoint niet passeren; een tenant-account levert geen platform-rollen
⇒ het wordt door de platform-guard geweigerd.

## PKCE login/callback (P2, geïmplementeerd — ADR-002)

Authorization Code + PKCE, **volledig server-side** (`api/v1/auth.py`):

- `/auth/login`: genereer `code_verifier`/`code_challenge`(S256)/`state`/`nonce`;
  bewaar `{verifier, nonce, next}` server-side in **Redis** op sleutel
  `auth_login:{state}` (TTL `auth_state_ttl`); redirect naar Keycloak. Verifier/
  nonce staan NOOIT in de browser-zichtbare URL.
- `/auth/callback`: `state` **eenmalig** via Redis `GETDEL` (CSRF + replay);
  code-exchange met `code_verifier` server-side (client_secret nooit naar
  client); `id_token`-validatie incl. **nonce** (`decode_id_token`); zet
  `lk_session` (`HttpOnly`/`Secure`/`SameSite=Strict`, max-age = access 15 min).
- Open-redirect-bescherming op `next` (`_valideer_next`: alleen same-origin
  relatief pad, anders app-root).
- Fouten in canoniek `{"fout":{...}}`; auth-fail hergebruikt de
  IP-gepseudonimiseerde Redis-counter.

## Realm-conventies (Keycloak)

- Rollen-mapper schrijft naar **`realm_access.roles`** (precies wat
  `extract_rollen`/`extract_platform_rollen` lezen). Mapper-`claim.name` ≠
  `roles` maar `realm_access.roles`.
- Tenant-users dragen een `tenant_id`-attribuut (mapper → `tenant_id`-claim);
  platform-users **niet** (strikte scheiding).
- **VALKUIL — audience-mapper verplicht.** Zonder `oidc-audience-mapper` zet
  Keycloak `aud: null` in het access-token (alleen `azp`), waardoor
  `decode_token` (`audience=keycloak_client_id`) faalt met
  `InvalidAudienceError` → `/auth/me` geeft 401 `NIET_GEAUTHENTICEERD`. De realm MOET
  een audience-mapper hebben die `complidata-api` aan het access-token toevoegt.

## RBAC-handhaving (fail-secure)

- Declaratieve permissietabel is de **enige bron** (`PERMISSIES` /
  `PLATFORM_PERMISSIES`); endpoints checken via `heeft_permissie` /
  `heeft_platform_permissie`, nooit ad-hoc rolvergelijking.
- **Fail-secure**: lege, onbekende of verkeerd-gecapitaliseerde rol ⇒ geen
  rechten. Onbekende entiteit ⇒ False.
- **401 vs 403**: geen/ongeldige sessie ⇒ 401 `NIET_GEAUTHENTICEERD` in canoniek
  `{"fout":{...}}` (`NietGeauthenticeerd` + handler, CD005); geldige sessie,
  onvoldoende rechten ⇒ 403 `ONVOLDOENDE_RECHTEN`; token zonder tenant ⇒ 403
  `TENANT_MISMATCH` (CD009). Alle canoniek (ADR-014).

## Dubbele tenant-bescherming

1. **RLS** via `set_config('app.tenant_id', :tid, false)` — databaseniveau.
2. **Expliciete `tenant_id`-filter** in elke query — applicatieniveau (te
   hanteren zodra module-queries worden geschreven).

## NCSC-richtlijnen (niet NIST)

LIKARA volgt **NCSC** (Nederlandse overheid) als beveiligingskader.
Gebruik nooit NIST als primaire referentie.

## IP-pseudonimisering

Auth-fail-counters in Redis gebruiken een SHA-256 hash van het IP-adres
(`hash_waarde`) — nooit het ruwe IP opslaan (AVG, privacy by design).

## Stubs en openstaande ADRs (V001)

| Onderdeel | Status |
|---|---|
| RBAC tenant + platform | Geïmplementeerd — `_load_roles` mapt `realm_access.roles`; twee domeinen (ADR-010/012) |
| Login/callback PKCE-flow | Geïmplementeerd — server-side PKCE + `lk_session` (ADR-002) |
| Audit trail / hash-chaining | Niet geïmplementeerd — ADR-006 open |
| MFA-config Keycloak | Realm aanwezig; MFA-policy nog in te stellen |
| Refresh-token / RP-initiated logout | Geïmplementeerd — ADR-015 (refresh + Redis) + RP-logout met `id_token_hint` (CD007/CD008/CD010). Voorwaarde: `revoke-refresh-token` aan (OP-14) |

## OP-6 — record-resolutie binnen tenant (AFGEDEKT, fase 1)

Tenant-scoped record-resolutie volstaat (geen per-gebruiker-eigenaarschap in fase 1,
collaboratief register, ADR-009): RLS + expliciete `tenant_id`-filter; een id buiten
de tenant is **niet vindbaar** ⇒ **404 `NIET_GEVONDEN`** — nooit 403, nooit het
bestaan van een ander-tenant-record lekken. Kind-entiteiten valideren de ouder via
`parent_service.haal_op(...)` (zelfde 404-no-leak).

## Rol-gating: affordance vs. handhaving

De frontend toont/verbergt knoppen met `hasRole(...)` (affordance); de **backend is
de enige handhaver** via `vereist_permissie` (fail-secure). Een frontend-gating-bug
mag nooit tot een autorisatie-omzeiling leiden. `hasRole` is post-ADR-010
functioneel (rollen uit `/auth/me`). Een toch-403 in de UI netjes afvangen (Toast).

## Cookie — dev vs. productie

`lk_session` is `HttpOnly`/`SameSite=Strict`; `cookie_secure` is **settings-driven**.
Lokaal-dev (http://localhost) zet `COOKIE_SECURE=false` (in `docker-compose.yml` op
de api-service, dev-only; `.env.example`), anders dropt o.a. Safari de Secure-cookie
over HTTP. **Productie houdt `secure=True`** — de dev-waarde nooit meenemen.

## Test-mode is GEEN auth-stub

`LIKARA_TEST_MODE` versoepelt **alleen** de Origin-check (`origin_check.py`) en de
rate-limit-sleutel (`rate_limit.py`). Het stubt **geen** auth en seedt niets. Inloggen
vereist altijd Keycloak (volledige stack). (De CLAUDE.md-comment "auth stub/auto-seed"
is onjuist — openstaand vervolgpunt.)

## V004-patronen (CD003–CD012, geverifieerd)

- **Keycloak-gedelegeerde refresh + Redis (ADR-015)**: het `refresh_token` (+ `id_token`)
  als JSON in Redis `auth_refresh:{sessie_id}`, gekoppeld via een opake httpOnly
  `lk_refresh`-cookie (nooit client-leesbaar). `POST /auth/refresh`:
  `grant_type=refresh_token` server-side (`client_secret` nooit naar client) → nieuw
  `lk_session` + **geroteerd** token; faal → 401 canoniek + handle opruimen. Bij
  refresh het `id_token` **meeverversen** (anders verouderde logout-hint). [CD007/CD010]
- **RP-initiated logout (OP-4)**: lokaal intrekken (`lk_session` + `lk_refresh` +
  Redis-handle, idempotent) **én** Keycloak end-session; `id_token_hint` (uit het
  handle) → naadloze redirect naar `post_logout_redirect_uri` (server-config, geen
  open redirect). Zonder hint toont Keycloak een bevestigingsscherm (empirisch
  bevestigd). [CD008/CD010]
- **401 canoniek** (`NIET_GEAUTHENTICEERD`) + **403 `TENANT_MISMATCH`** (auth-grens,
  geen ADR-003-404) via `HTTPException`-subclass-excepties + handlers. 429 al canoniek
  (`RATE_LIMIT_OVERSCHREDEN`). 422 bewust native (ADR-014). [CD005/CD009]
- **VOORWAARDE-noot**: `revoke-refresh-token` moet **aan** in de realm, anders is de
  reuse-detectie uit ADR-015 B3 niet actief (oude refresh-tokens blijven geldig tot
  SSO-einde). Opvolgpunt OP-3-realm-hardening / OP-14. [CD007]

## V006-patronen (CD025–CD038, ADR-012 Addendum A / ADR-019, geverifieerd)

- **`PlatformEntiteit.CHECKLISTCONFIG`** (ADR-012 Addendum A): platformbeheerder `{L,A,W}`,
  platformoperator `{L}`, **geen `V`** — een optie wordt soft-gedeactiveerd (W), nooit hard
  verwijderd. De config-endpoints zijn geguard met `vereist_platform_permissie(CHECKLISTCONFIG, …)`
  op `get_platform_session` (lk_platform). [CD031]
- **Domeingrens als veiligheidsgrens, niet alleen scheiding**: `lk_platform` mag de tenant-tabel
  `checklistscore` **niet lezen** → een cross-domain "is deze optie/dit type in gebruik?"-check is
  onmogelijk. Conservatief blokkeren (antwoordtype alleen vanuit `geen`) is hier de veilige keuze;
  `geen→type` is bewijsbaar antwoord-vrij. Soft-deactivate verweest niets (read levert inactieve
  sleutels mét `actief`-vlag). [CD031]
- **Platform-identiteit in de SPA**: `GET /auth/platform/me` (`get_current_platform_user`, géén
  `tenant_id`); een sessie zónder platform-rol ⇒ 403 (`OnvoldoendeRechten`). De frontend detecteert
  het sessietype via `/auth/me` (403 → platform) + `/auth/platform/me`; dezelfde PKCE-login/cookies/
  RP-logout gelden voor beide domeinen. Platform-testusers staan in de realm (`platformbeheerder-test`/
  `platformoperator-test`, géén `tenant_id`, wachtwoord `changeme_dev`). [CD032/CD033]
- **401 al canoniek (OP-7, CD005)**: alle 401 → `{"fout":{"code":"NIET_GEAUTHENTICEERD",…}}` (handler +
  `_fout`); de frontend keyt op de **statuscode** en leest `body.fout.code`. 422 blijft native. [CD037]

## V016-patronen (DC015 — ADR-029 gebruikersbeheer + identiteit)

- **Keycloak Admin API-provisioning via dedicated service-account (least-privilege).**
  Gebruikersaanmaak loopt via een eigen Keycloak-client `likara-user-provisioning`
  (`serviceAccountsEnabled`, client-credentials-grant), met **uitsluitend** de
  `realm-management`-rollen `manage-users` + `view-users` — niet de brede master-admin-creds.
  Structureel consistent met de lk_app/lk_platform/lk_admin-least-privilege-driedeling.
  Realm-export-patroon (Keycloak 24): client + synthetische `users`-entry
  `{username:"service-account-<client>", serviceAccountClientId, clientRoles:{"realm-management":
  ["manage-users","view-users"]}}`. **Verplichte live-verificatie** na `down -v && up -d`:
  client-credentials-token ophalen + `GET /admin/realms/<realm>/users` → 200 (niet 403) bewijst
  dat de rolmapping correct is geïmporteerd (een stille mismatch geeft pas bij provisioning een
  403). `get_provisioning_token()` in `app/core/keycloak.py`; secret is dev-default `changeme_dev`
  (productie-hardening + MFA hoort bij realm-hardening/OP-28).
- **Server-gegenereerd tijdelijk wachtwoord.** Bij gebruikersaanmaak genereert de backend een
  sterk wachtwoord (`secrets`, ≥16, mix), zet `UPDATE_PASSWORD` als Keycloak required action, en
  geeft het **eenmalig** terug in de 201-respons. Nooit loggen, nergens persisteren; geen
  wachtwoordveld in de request- of read-schema's.
- **Niet-transactionele Keycloak-orphan-cleanup.** Bij de flow persoon-flush → KC-create →
  koppelrij → commit: faalt KC-create → DB-rollback (geen orphan). Faalt de commit ná KC-create →
  best-effort `deactiveer_keycloak_gebruiker(sub)` in de `except`, fout terug als 503
  (`KEYCLOAK_NIET_BESCHIKBAAR`). KC en DB zijn niet transactioneel; deactiveer is de compensatie.
- **Toegang-volgt-object (RBAC-patroon, naast de centrale entiteit-gate).** De objecthistorie
  (`GET /objecthistorie/{type}/{id}`) is géén `AUDITLOG`-gegate scherm (dat blijft beheerder/
  auditor-only). In plaats daarvan: de toegang volgt het object — resolveer het object eerst via
  `<type>_service.haal_op` (404 no-leak buiten tenant), check dán de **leespermissie van dát
  objecttype** (`COMPONENT.LEZEN`, `CONTRACT.LEZEN`, …). Mag je het object zien, dan zie je z'n
  geschiedenis. Sub-/schermloze entiteiten krijgen geen eigen ingang (verschijnen via hun ouder);
  nooit een type opnemen met een gegokte permissie — bij twijfel STOP.

## Keycloak 24 custom login-theme (DC017)

Structuur: `keycloak/themes/likara/login/` (parent=keycloak).
- `theme.properties`: `parent=keycloak`, `styles=css/likara.css`
- `login.ftl`: volledige override met `<#import "template.ftl">` + `<@layout.registrationLayout>`.
  Voeg LIKARA-branding toe bovenaan de "form"-sectie.
- `likara.css`: CSS-overrides voor KC 24.0.5 (PatternFly 4-stijl, NIET PF5).
  KC 24 gebruikt `.login-pf-*` classes (`.pf-v5-*` bestaat niet op login-pagina).
  Kritieke selectors: `html, body, .login-pf-page` voor achtergrond;
  `.card-pf, #kc-content, #kc-content-wrapper` voor kaart (height:auto, transparent);
  `#kc-form-wrapper` voor witte kaart; `#kc-page-title` display:none.
  VALKUIL: `#kc-content` NIET `min-height:100vh` geven — zit ín de kaart!
- Volume mount in docker-compose: `./keycloak/themes:/opt/keycloak/themes` (was al aanwezig).
- Realm JSON: `"loginTheme": "likara"`, `"displayName": "LIKARA"`.
- Tab-titel = realm displayName.

## Dev-gebruiker aanmaken met persoon-koppeling (DC017, ADR-029)

Aanpak: vaste UUID's in realm JSON (`"id": "<uuid>"`) + hardcoded in seed als keycloak_sub.
- Voordeel: deterministisch over re-imports heen, geen runtime-KC-afhankelijkheid in seed.
- Live toepassen: `kcadm partialImport` (honoreert vaste id's; `kcadm create users` kan dat niet).
- Seed-functie `_seed_dev_gebruikers`: zoek persoon op naam → maak GebruikerPersoon aan.
- KC-client voor gebruikersbeheer: `likara-user-provisioning` (hernoemd van kilara, DC017).
