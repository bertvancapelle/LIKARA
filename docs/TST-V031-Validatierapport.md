# TST-V031 — Validatierapport

**Build:** V030 (→ V031 bij gen_build)
**Datum:** 2026-07-03
**Sessie:** LI030 — ADR-037 (verantwoordelijke per checklistantwoord) volledig geland: Pass 1 (schema-gate, migratie 0051) + Pass 2 (picker + aandacht-signaal + velduitleg + leesbaarheid + organisatie-ontdubbeling + veld=identiteit)
**Teststatus:** backend 841 (module) + 80 (platform) / frontend 772 groen (2 skipped)
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- `py_compile` over alle projectcode (`backend/**` + `modules/**`, 320 bestanden) → **OK** (0 syntaxfouten).
- localStorage voor tokens (`frontend/src` + `modules/*/frontend`): **0**.
- `lk_admin` als app-connectie-string in app-code (`backend/app` + `modules/*/backend`): **0** (app verbindt als `lk_app`).
- Hardcoded `tenant_id = '<uuid>'` in queries (excl. tests/seed/migraties): **0**.

## As 2 — Tests
- Backend module (`modules/bwb_ontvlechting/backend/tests`, tegen de verse geseede lk_app-DB):
  **841 passed, 2 skipped, 0 failed** (≈19s). +27 t.o.v. V030 = nieuwe ADR-037-tests:
  aard-validatie `ONGELDIGE_VERANTWOORDELIJKE` (422); engine-borging (`test_engine_borging_adr037`:
  offline bronscan van de verantwoordelijke-leeslaag + het signaal-pad; live-test "verantwoordelijke
  zetten/wijzigen/leegmaken muteert geen lifecycle/score/blokkade" + signaal-correctheid op de seed);
  read-verrijking (verantwoordelijke_naam/afdeling/organisatie) op checklistscore- en blokkade-reads.
- Backend platform (`backend/tests`): **80 passed, 0 failed**.
- Frontend **vitest**: 66 files, **772 passed** (+8 t.o.v. V030 = verantwoordelijke-picker
  kiezen/voorvullen/wissen, aandacht-signaal-hint, Opslaan-knop-leesbaarheidsgrendel, identiteit
  "afdeling — organisatie" / "persoon — afdeling — organisatie" in lijst/veld, veld==lijst).
- De **2 skips** zijn pre-existing, seed-omgevingsafhankelijk (`client_software` / `Oracle FIN-DB`) —
  geen ADR-037-relatie.
- **Geaccepteerde afwijking:** ~29–32 unhandled-rejection-consoleruis in `LandschapskaartPopups.test.js`
  / `LandschapskaartView.test.js` (Cytoscape-mock `cy.nodes` async teardown + theme-CSS-fetch abort) —
  **geen falende test** (772/772 groen); geagendeerd voor de Impact-verkenner render-herbouw.
- Smoke test: **4 geslaagd, 0 mislukt**. API-health: `{"status":"ok","db":"ok"}`.

## As 3 — DB-integriteit
- `alembic heads` → **1 head**: `0051_adr037_verantw`.
- `alembic branches` → **0** (geen split).
- Migratie-revisie-id ≤ 32 tekens (`alembic_version` varchar(32)): `0051_adr037_verantw` (19) OK.
- ADR-037 (migratie 0051): `checklistscore.verantwoordelijke_id` (composiet-FK → `element`,
  ON DELETE SET NULL, kolom-specifiek) vervangt het vrije-tekstveld `checklistscore.eigenaar`;
  `blokkade.eigenaar` gedropt (afgeleid in de leeslaag). Down/up-reversibiliteit geverifieerd;
  init-container migreerde een verse DB schoon tot 0051.

## As 4 — Multi-tenancy / RLS
- `checklistscore.verantwoordelijke_id` is een composiet-FK `(tenant_id, verantwoordelijke_id)` →
  cross-tenant uitgesloten op DB-niveau. De read-verrijking (`resolve_verantwoordelijken`,
  `_verrijk_context`) filtert expliciet op `tenant_id` bovenop RLS.
- Het aandacht-signaal leest `checklistscore` via een `table()/column()`-handle (géén ORM), tenant-
  gescoopt — consistent met de bestaande registratiegaten-engine-invariant.

## As 5 — Engine-invariant (score = enige lifecycle-driver)
- Dubbele borging groen: (1) afwezigheidstest — de verantwoordelijke read-/validatie-laag + de
  signaal-query refereren geen `herbereken_*`/`bepaal_lifecycle` en importeren geen
  `Checklistscore`/`Blokkade`/`ComponentProfiel`-ORM buiten de engine; (2) live-test — een
  verantwoordelijke zetten/wijzigen/leegmaken laat `component_profiel`/`lifecycle_status`/
  `checklistscore.score`/`blokkade` ongemoeid.

---

## Conclusie
**0 kritieke bevindingen.** ADR-037 volledig geland en geborgd. Alle assen groen; klaar voor build-bump
naar V031.
