# SESSIESTART — CompliData V002

**Datum**: 2026-06-06
**Platform**: CompliData — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/complidata/ bestaat
   - Zo ja: normale modus — lees alle complidata-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — CompliData V002 — [N] skills geladen"
5. Wacht op START: [naam] van Bert

---

## Interactieregel (VERPLICHT — niet-onderhandelbaar)

Geldt voor zowel CC als claude.ai, in elke sessie:

- Stel vragen ALTIJD één voor één. Stel nooit meerdere vragen tegelijk.
  Wacht op het antwoord van Bert voordat je een volgende vraag stelt.
- Geef adviezen ALTIJD één voor één. Geef nooit meerdere adviezen tegelijk.
  Wacht op de reactie van Bert voordat je een volgend advies geeft.

Deze regel is niet-onderhandelbaar en overschrijft elke neiging om
meerdere vragen of adviezen te bundelen.

---

## Opdrachtformaat CC-opdrachten (VERPLICHT — standaardwerkwijze)

claude.ai levert elke CC-opdracht ALTIJD aan als een .md-bestand
(downloadbaar), nooit als een los codeblok in de chat. Bert gebruikt dat
.md-bestand in CC. Deze afspraak geldt in elke sessie.

---

# SESSIE_BRIEFING.md — CompliData V002

**Gegenereerd**: 2026-06-06

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V001 |
| Datum | June 2026 |
| Commit | 3bf70b5 |
| Tests | 5 passed · 4 TST-assen groen |
| TST-rapport | TST-V001-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
f6b2fc5 docs(tst): TST-V002-validatierapport + NEXT_SESSION top-5 sessie 3
3f70077 docs: sessiepatronen verankerd in skills/CLAUDE.md/CONTRIBUTING; backlog + plantekst bijgewerkt
3bf0c70 feat(auth): tweelaags rollenmodel platform+tenant (ADR-012) — cd_platform, realm-opschoning, platform-RBAC-guard, tenant-onboarding-endpoints
b0a67d4 feat(deploy): init-container voor migratie+seed als cd_admin (ADR-011); realm redirect_uri-fix + --import-realm; psycopg2-binary (OP-9/OP-10)
9e5b7fb docs: opvolgpunten P1-P3 geborgd in docs/OPVOLGPUNTEN.md
```

---

## Prioriteiten volgende sessie

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


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — CompliData V002"
4. Wacht op START: [naam] van Bert

