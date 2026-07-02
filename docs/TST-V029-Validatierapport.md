# TST-V029 — Validatierapport

**Build:** V028 (→ V029 bij gen_build)
**Datum:** 2026-07-02
**Sessie:** LI060 (componenttype-catalogus 8 typen + 3 beoordeelbaar) + ADR-028 slices 1–4 (componentclassificatie rol + BIV, end-to-end) + ADR-036 (mini-ADR organisatiegebruik, functioneel besloten)
**Teststatus:** backend 898 / frontend 742 groen (2 skipped)
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- `py_compile` over alle projectcode (`backend/**` + `modules/**`) → **OK** (0 syntaxfouten). (Eén
  `SyntaxWarning` op `\S` in een overgenomen framework-skill-script buiten de projectcode — geen fout.)
- localStorage voor tokens: **0**.
- `lk_admin` als app-connectie-string in app-code: **0** (app verbindt als `lk_app`/`lk_platform`).
- Hardcoded `tenant_id = '<uuid>'` in queries (excl. tests/seed/migraties): **0**.

## As 2 — Tests
- Backend (`backend/tests/ modules/`, tegen de verse geseede lk_app-DB):
  **898 passed, 2 skipped, 0 failed** (≈20s). +33 t.o.v. V028 = nieuwe ADR-028/LI060-tests
  (`test_adr028_classificatie` 30, componenttype/laag-grouping, registratiegaten BIV, opties-endpoint,
  platform-RBAC 2 entiteiten, platform_init-volgorde).
- Frontend **vitest**: 65 files, **742 passed** (+25 t.o.v. V028 = `RolConfigBeheer`/`BivConfigBeheer`
  + rol/BIV in formulier/detail/lijst/kaart + signalering-BIV + api-filterconventie). `vite build`:
  **0 fouten** (alleen de bekende >500 kB-waarschuwing).
- De **2 skips** zijn pre-existing, seed-omgevingsafhankelijk (`client_software` / `Oracle FIN-DB`
  niet in deze DB) — geen ADR-028/LI060-relatie.
- **Geaccepteerde afwijking:** ~32 unhandled-rejection-consoleruis in `LandschapskaartView.test.js`
  (Cytoscape-mock async teardown) — **geen falende test** (742/742 groen); geagendeerd voor de
  Impact-verkenner render-herbouw.

## As 3 — DB-integriteit
- `alembic heads` → **1 head**: `0048_adr028_classificatie`.
- `alembic branches` → **0** (geen split).
- Migratie-revisie-id ≤ 32 tekens (`alembic_version` varchar(32)): `0048_adr028_classificatie` (25) OK.
- Migratie 0048 additief + reversibel: `create_table componentrol_optie/biv_schaal_optie` (GEEN RLS,
  grants als `componentconfig_optie`) + 4 `component`-kolommen (`componentrol` NOT NULL server_default
  `interne_applicatie`; 3× BIV nullable). Downgrade dropt kolommen + tabellen. Verse deploy 0001→0048
  schoon geverifieerd; RLS onaangeroerd op tenant-scoped tabellen.

## As 4 — Veiligheid / conventies
- Vangrail-grep `Eraneos|compliman|cm_` in `backend/ frontend/src/ modules/ docs/adr/`: **0**.
- Alle likara-skills gevuld (>200 bytes; sluit_acties.py: skills ✅) — deze sessie bijgewerkt:
  `likara-domeinmodel` (componenttype-set 8, catalogus-families +2, classificatievelden, signalering 11,
  LandschapsNode rol/BIV), `likara-frontend` (V028-patronen), `likara-backend` (ordinale drempel + guard-les),
  `likara-db` (additieve catalogi + kolommen).
- Generiek platform: geen hardcoded "gemeente"/operator/tenant-begrip in ADR-028/036-code of -UI.

## Engine-invariant-borging (LI060 + ADR-028)
- **Classificatie voedt de engine niet** — dubbel geborgd: (1) offline import-afwezigheid op de nieuwe
  catalogus-/seed-modules (`componentrol_catalog`/`bivschaal_catalog`/`*config_service`/`seed_*`) + een
  function-bronscan (ast, docstring-gestript) op `component_service._valideer_classificatie`; (2) live —
  rol/BIV zetten op een niet-beoordeeld type geeft geen `component_profiel`/`lifecycle_status`.
- **Signalering** (`registratiegaten_service`) blijft read-only: geen `session.add/commit/flush/delete`,
  geen engine-symbolen; het nieuwe BIV-signaal gebruikt alleen `or_` + bestaande `Component`-kolommen.
- **Kaartprojectie** (`landschapskaart_service`) read-only-bronscan groen (rol/BIV additief).
- Score blijft de enige lifecycle-driver.

## Conclusie
Alle vier assen **geslaagd**; **0 kritieke bevindingen**. V029 is releasebaar.
