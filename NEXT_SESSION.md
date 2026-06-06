# NEXT_SESSION.md — CompliData V002

**Gegenereerd**: 2026-06-06
**Vorige build**: V002

---

## Top-5 prioriteiten volgende sessie

1. **P5 — Module-CRUD-laag, te beginnen met Applicatie.**
   Endpoints onder `vereist_permissie` (tenant-domein), lifecycle-handhaving in
   de service-laag, cursor-paginering, input-validatie (Pydantic `extra='forbid'`).
   Neem **OP-6** (resource-ownership binnen tenant — mag deze gebruiker DIT
   record) hierin mee.

2. **OP-3 — Refresh-token-subsysteem.**
   `/auth/refresh`, veilige server-side opslag van de refresh-token gekoppeld
   aan een sessie-id, rotatie/intrekking, koppeling aan de 8-uurs grens. Sessie
   verloopt nu na 15 min → opnieuw inloggen.

3. **Frontend login-view (begin laag 4).**
   SPA-login-knop op de werkende backend-login + realm, zodat end-to-end
   inloggen in de UI werkt (contract uit P2: `/api/v1/auth/login` →
   Keycloak → callback → `cd_session` → `/auth/me`).

4. **OP-7 — 401 en 403 in hetzelfde canonieke `{"fout":{...}}`-formaat.**
   401 volgt nu nog `{"detail":{"code":…}}`; gelijktrekken met de 403-handler.

5. **OP-4 — RP-initiated logout** via het Keycloak end-session-endpoint
   (lokale `cd_session` wissen + Keycloak-SSO-sessie beëindigen).

---

## Openstaande beslissingen

- OAuth-callback-eigenaarschap definitief: de backend bezit nu de callback
  (`/api/v1/auth/callback`); de frontend-route volgt bij de login-view.
- Branding-tokens (huisstijl) en productie-domeinnaam nog niet bepaald.

---

## Bekende risico's en aandachtspunten

- **OP-13** — platform-tabel-grants voor `Platforminstellingen`/`Platformmetadata`
  bij uitbouw van die endpoints (zelfde GRANT/REVOKE-patroon als `tenant`).
- **OP-14** — dev-credentials `changeme_dev` (realm-secret, testgebruikers,
  DB-rollen) vervangen vóór productie; testgebruikers uit de productie-realm houden.
- Platform-users hebben geen `tenant_id` → tenant-endpoints geven 403 (bewust).
- Audit trail (ADR-006) nog niet gebouwd — mutaties worden nog niet gelogd.

---

## Technische schuld

- `get_platform_session` gebruikt een module-engine op `cd_platform`; bij
  uitbreiding van platform-endpoints connection-gebruik bewaken.
- SyntaxWarning in overgenomen framework-skill (ms365-tenant-manager) —
  geaccepteerd als TST-V00x-K1, buiten CompliData-scope.

---

## Geleerde patronen deze sessie

Verankerd in de skills/CLAUDE.md/CONTRIBUTING (commit `3f70077`): DB-driedeling
(cd_admin/cd_platform/cd_app), tweelaags rollenmodel + twee permissiedomeinen,
twee auth-paden, init-container-deploy (ADR-011), PKCE-flow, realm-conventies +
audience-mapper-valkuil, RBAC-handhaving + testdiscipline, gate-werkwijze,
CONTRIBUTING §6-fix. Zie ADR-011 en ADR-012.
