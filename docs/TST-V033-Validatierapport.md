# TST-V033 — Validatierapport

**Build:** V032 (→ V033 bij gen_build)
**Datum:** 2026-07-05
**Sessie:** LI032 — gebruiker-cluster volledig geland: contactpersoon uit register (ADR-039,
migratie 0054) · centrale verlopen-sessie-vangrail + zoek-fout-norm · ter-plekke-aanmaken afdeling
(gedeelde `AfdelingSelect`, 4 plekken) · gebruiker aanmaken (org intern-only + gescoopte afdeling) ·
gebruiker bewerken org/afdeling + picker-voorvul-fix + accountsysteem-fix (conditionele
Keycloak-aanroep, PUT zonder username) + 2e interne testorganisatie + stale-label-`:key` +
param-filterende picker-integratie-testhelper · 18 LI032-skillpatronen.
**Teststatus:** backend 866 (module) + 80 (platform) / frontend 825 groen (2 skipped)
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- localStorage voor tokens (`frontend/src` + `modules/*/frontend`): **0**.
- `lk_admin` als app-connectie-string in app-code (`backend/app` + `modules/*/backend`): **0**
  (app verbindt als `lk_app`; migratie/seed als `lk_admin` via de init-container).
- Eraneos/CompliMan-resten (`Eraneos`/`compliman`/`cm_`) in `backend`/`modules`/`docs/adr`: **0**.
- Geen hardcoded tenant-IDs, platform-namen of operator-referenties in de gewijzigde code.

## As 2 — Tests
- Backend module (`modules/bwb_ontvlechting/backend/tests`, tegen de gemigreerde lk_app-DB op 0054):
  **866 passed, 2 skipped, 0 failed** (≈25s). Netto t.o.v. V032: o.a. ADR-039 contactpersoon-ref
  (aard-restrictie, persoon-binnen-partij, read-verrijking), gebruiker-corrigeer afdeling/organisatie
  + aanspreekpunt-blokkade, en de LI032-account-regressies: afdeling-only → géén Keycloak-aanroep
  (`assert_not_awaited`), naam/e-mail → PUT-payload **zonder** `username`, en een afdeling-only edit
  die een account-storing overleeft (interne wijziging blijft behouden).
- Backend platform (`backend/tests`): **80 passed, 0 failed**.
- Frontend **vitest** (`--no-file-parallelism`): 69 files, **825 passed**. Nieuw o.a. de
  picker-integratietests (param-filterende `partijMock.js`): org-picker → alleen interne organisaties;
  na org-wissel → afdelingen van de nieuwe organisatie; geen stale organisatie-label; plus de
  ZoekSelect voorgevuld-openen-regressies.
- De **2 skips** (backend) zijn pre-existing, seed-omgevingsafhankelijk — geen LI032-relatie.
- **Geaccepteerde afwijking:** cytoscape-teardown-flake in `LandschapskaartView.test.js` /
  `LandschapskaartPopups` (unhandled-rejections; run-to-run ~22–24) — **geen falende test**
  (825/825 groen); geagendeerd voor de Impact-verkenner render-herbouw.
- `vite build`: **OK** (228 modules, ✓ built).

## As 3 — DB-integriteit
- `alembic heads` → **1 head**: `0054_contactpersoon_ref`.
- `alembic branches` → **0** (geen split).
- ADR-039 (0054): `partij.contactpersoon_id` optionele composiet-FK `(tenant_id, contactpersoon_id)
  → element`, **ON DELETE SET NULL** kolom-specifiek (PostgreSQL 15+); vervangt het vrije-tekstveld
  `partij.contactpersoon` (String(255)); index `ix_partij_tenant_contactpersoon`. Geen nieuwe
  migratie deze sessie boven 0054 (gebruiker-bewerken is puur service/route/frontend; seed-uitbreiding
  is data, geen schema).

## As 4 — Multi-tenancy / RLS & conventies
- Geen tenant-scoped tabel-wijzigingen die RLS raken: `partij.contactpersoon_id` erft de bestaande
  FORCE-RLS-policy van `partij`; de composiet-FK is tenant-consistent. Gebruiker-corrigeer loopt via
  `get_tenant_session` (RLS-context per request); geen cross-tenant pad.
- Provisioning (`likara-user-provisioning`) blijft least-privilege (manage-users + view-users).

## As 5 — Engine-invariant (score = enige lifecycle-driver)
- Dubbele borging groen: (1) afwezigheidstest — `gebruiker_service`/`partij_service` importeren geen
  `herbereken_*`/`bepaal_lifecycle`/`Checklistscore`/`Blokkade`/`ComponentProfiel` buiten de engine;
  (2) een persoon-/contactpersoon-/afdeling-mutatie raakt de score-/lifecycle-/blokkade-tabellen niet.
  LI032 is puur registratie/structuur/read + provisioning.

## As 6 — Auth/provisioning (LI032-specifiek)
- Accountsysteem (Keycloak) wordt in `corrigeer_gegevens` **alleen** aangeroepen bij een echte
  naam/e-mailwijziging; een afdeling-/organisatie-only wissel raakt het account niet (geen 503, geen
  verlies van de interne wijziging).
- De update-PUT stuurt **geen** `username` meer (alleen email/firstName/lastName). Live geverifieerd:
  realm `loginWithEmailAllowed=True`, identiteit op `sub` → username-divergentie is login-neutraal.

---

## Conclusie
**0 kritieke bevindingen.** LI032 gebruiker-cluster volledig geland en geborgd. Alle assen groen;
klaar voor build-bump naar V033.
