# TST-V030 — Validatierapport

**Build:** V029 (→ V030 bij gen_build)
**Datum:** 2026-07-03
**Sessie:** ADR-036 (organisatiegebruik end-to-end: grof feit + gebruikersgroep-verfijning + kaart-afleiding/signaal/identiteit) + Velduitleg (alle formulieren) + ADR-036a (afdeling structureel, migratie 0050) + 3 UI-fixes (bewerken-voorvulling gebruikersgroep, contract-leverancier-picker, eigenaar-picker onderzocht)
**Teststatus:** backend 914 / frontend 763 groen (2 skipped)
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- `py_compile` over alle projectcode (`backend/**` + `modules/**`, 318 bestanden) → **OK** (0 syntaxfouten).
- localStorage voor tokens (`frontend/src` + `modules/*/frontend`): **0**.
- `lk_admin` als app-connectie-string in app-code (`backend/app` + `modules/*/backend`): **0** (app verbindt als `lk_app`).
- Hardcoded `tenant_id = '<uuid>'` in queries (excl. tests/seed/migraties): **0**.

## As 2 — Tests
- Backend (`backend/tests/ modules/`, tegen de verse geseede lk_app-DB):
  **914 passed, 2 skipped, 0 failed** (≈18s). +16 t.o.v. V029 = nieuwe ADR-036/036a-tests
  (`test_organisatiegebruik_adr036` grof feit + verfijning + signaal + invariant "afdeling-met-org ⟹
  grof feit"; ADR-036a afdeling-validatie/read/lijst/context; gebruikersgroep-service re-plumb).
- Frontend **vitest**: 66 files, **763 passed** (+21 t.o.v. V029 = `VeldUitleg` + velduitleg-uitrol,
  search-first afdeling-picker, gebruikersgroep bewerken-voorvulling, contract-leverancier picker-scope).
- De **2 skips** zijn pre-existing, seed-omgevingsafhankelijk (`client_software` / `Oracle FIN-DB`) —
  geen ADR-036-relatie.
- **Geaccepteerde afwijking:** ~32 unhandled-rejection-consoleruis in `LandschapskaartView.test.js`
  (Cytoscape-mock async teardown) — **geen falende test** (763/763 groen); geagendeerd voor de
  Impact-verkenner render-herbouw.

## As 3 — DB-integriteit
- `alembic heads` → **1 head**: `0050_adr036a_gg_afdeling`.
- `alembic branches` → **0** (geen split).
- Migratie-revisie-id ≤ 32 tekens (`alembic_version` varchar(32)): `0050_adr036a_gg_afdeling` (24) OK.
- ADR-036 (pass 1): `organisatiegebruik` grof-feit-tabel + `gebruikersgroep.gebruik_id` (verfijning-
  verwijzing). ADR-036a (0050): `gebruikersgroep.afdeling` (vrije tekst) → `afdeling_id` composiet-FK
  `(tenant_id, afdeling_id) → element` ON DELETE RESTRICT (organisatie_eenheid-partij). RLS-patroon +
  FORCE onaangeroerd op tenant-scoped tabellen; verse deploy 0001→0050 schoon.
- Seed geverifieerd (DB): alle contract-leverancier-koppelingen geldig (12 externe_partij + 3 organisatie;
  nul persoon/burger); 4 organisatie-partijen aanwezig (eigenaar-picker-onderzoek).

## As 4 — Veiligheid / conventies
- Vangrail-grep `eraneos|compliman|cm_` (case-insensitive) in `backend/ frontend/src/ modules/ docs/adr/`:
  **3 hits — alle in `ADR-012`** (historische verwijzing naar de weggemigreerde legacy CompliMan-rollen;
  legitiem documentair in een ADR, geen code/output, pre-existent). **Geen regressie** — in code/UI: **0**.
- Alle likara-skills gevuld (sluit_acties.py: skills ✅) — deze sessie bijgewerkt:
  `likara-domeinmodel` (signaaltelling gecorrigeerd naar 9 (3 kritiek / 6 aandacht) + ADR-036-signaal;
  relatie-facade doet GÉÉN bron/doel-typevalidatie — gecorrigeerd; gebruikersgroep organisatie op grof feit
  + afdeling structureel ADR-036a), `likara-frontend` (§ZoekSelect-patronen: picker-scope-spiegelt-backend,
  bewerken-voorvulling+`initieel-weergave`, search-first create-in-lege-zoekstaat), `likara-ux`
  (picker-patronen kruisverwijzing).
- Generiek platform: geen hardcoded gemeente/operator/tenant-begrip in ADR-036/036a-code of -UI.

## Engine-invariant-borging (ADR-036 / ADR-036a)
- **Organisatiegebruik + afdeling voeden de engine niet** — read-afleidingen (`registratiegaten_service`
  "detaillering ontbreekt", `landschapskaart_service` "gebruikt door") blijven read-only: geen
  `session.add/commit/flush/delete`, geen engine-symbolen; alleen SELECT over bestaande kolommen.
- **Invariant-test** "afdeling-met-org ⟹ grof feit" geborgd (`test_organisatiegebruik_adr036`).
- Score blijft de enige lifecycle-driver.

## Conclusie
Alle vier assen **geslaagd**; **0 kritieke bevindingen**. V030 is releasebaar.
