# TST-V028 — Validatierapport

**Build:** V027 (→ V028 bij gen_build)
**Datum:** 2026-07-02
**Sessie:** LI059 (component-focus-herfundering) — Slice 3 (subtabel-drop) + Slice 4 (frontend-cutover) + FacadeOpruiming (volledige purge) + Slice 5 (ADR-021/022-afronding)
**Teststatus:** backend 865 / frontend 717 groen (2 skipped)
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- `py_compile` over alle projectcode (`backend/**` + `modules/**`, excl. `.claude/`) → **OK** (0 fouten).
- localStorage voor tokens: **0**.
- `lk_admin` als app-connectie-string in app-code: **0** (app verbindt als `lk_app`/`lk_platform`).
- Hardcoded `tenant_id = '<uuid>'` in queries (excl. tests/seed/migraties): **0**.

## As 2 — Tests
- Backend (`backend/tests/ modules/`, tegen de verse geseede lk_app-DB):
  **865 passed, 2 skipped, 0 failed** (≈16s). −83 t.o.v. V027 = de verwijderde `/applicaties`-facade-
  endpoints + 6 verwijderde facade-testbestanden (`test_applicatie_{sort,filter,service,schemas,routes,opties}`);
  fixture-tests gemigreerd naar `component_service`/`ComponentCreate`.
- Frontend **vitest**: 63 files, **717 passed** (−2 files t.o.v. V027 = geretireerde `ApplicatieDetail`/
  `ApplicatieFormulier`-tests). `vite build`: **0 fouten** (alleen de bekende >500 kB-waarschuwing).
- De **2 skips** zijn pre-existing, seed-omgevingsafhankelijk (`client_software` / `Oracle FIN-DB`
  niet in deze DB) — geen LI059-relatie.

## As 3 — DB-integriteit
- `alembic heads` → **1 head**: `0047_li059_drop_applicatie`.
- `alembic branches` → **0**.
- Migratie-revisie-id ≤ 32 tekens (`alembic_version` varchar(32)): `0047_li059_drop_applicatie` (26) OK.
- Migratie 0047 up/down reversibel: `DROP TABLE applicatie` (upgrade) / schema-reversibele terugbouw
  (downgrade, geen databehoud-backfill — DC016 testdata-regel). Verse deploy 0001→0047 schoon geverifieerd.

## As 4 — Veiligheid / conventies
- Vangrail-grep `Eraneos|compliman|cm_` in `backend/ frontend/src/ modules/ docs/adr/`: **0**.
- Alle likara-skills gevuld (sluit_acties.py: skills ✅).
- Facade-purge: **0** echte code-referenties naar `applicatie_service`/`schemas.applicatie`/
  `Entiteit.APPLICATIE`/`vereist_permissie(APPLICATIE`.

## Engine-invariant-borging (LI057–LI059)
- **Score = enige lifecycle-driver** blijft hard geborgd, dubbel:
  - **Offline:** `test_engine_borging_li057` (lifecycle_service leest `migratiepad/complexiteit/prioriteit`
    **0×**) + `test_engine_borging_li059` (facade-schrijfpaden roepen geen `herbereken*`/`bepaal_lifecycle`
    aan; function-bronscan met ast-docstring-strip).
  - **Live:** `test_engine_borging_li059` (transitie-attribuut-edit muteert `lifecycle_status`/score/
    blokkade niet; facade-delete laat 0 wees-element achter).

## RBAC / audit / objecthistorie (FacadeOpruiming)
- RBAC-matrixtest (`set(VERWACHT)==set(Entiteit)`): **22 entiteiten × 4 × 4 = 352** combinaties (was 23/368;
  `Entiteit.APPLICATIE` verwijderd, dashboard-guard → `COMPONENT.LEZEN`). Groen.
- Audit: `applicatie` uit `AUDIT_TENANT_ENTITEITEN` (dood sinds 0047). **0** audit-records met
  `entiteit_type='applicatie'` — historie van een applicatie-component loopt via type `component`.

## Verse-reseed-proef (Fase 5)
- `down -v && up -d` → init (0001→0047 + platform_init) → handmatige dev-seed (nieuw create-pad):
  **16 applicatie-componenten** · 267 scores · volledige baseline. Wees-elementen **0**; residu `LI059-%`/
  `WT-%` **0**.

## Conclusie
**0 kritieke bevindingen.** De component-focus-herfundering is compleet en formeel afgerond (ADR-021/022
slotsecties "Eindstaat"): `component` is de enige bron in data/API/RBAC/audit.
