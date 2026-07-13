# TST-Validatierapport — V040

| | |
|---|---|
| **Build** | V040 |
| **Datum** | 2026-07-13 |
| **Sessie** | LI039 — gate 1a-bis (ADR-044 plaatsing als eerste-klas feit) + gate 1b (referentiemodel inlezen, AMEFF) + browsercheck-fixes (leeg-aanbod, onvoltooide inlees) + patronen-validatie fase A/B |
| **Kritieke bevindingen** | **0** |

## Resultaat per as

| As | Controle | Resultaat |
|---|---|---|
| 1 — Code-kwaliteit | `py_compile` alle Python-bestanden | ✅ 0 syntaxfouten (één pre-existing SyntaxWarning in een overgenomen framework-skill-script, buiten scope per CONTRIBUTING §6) |
| 2 — Tests | `pytest backend/tests/ modules/` (repo-root, live DB) | ✅ **1040 passed, 2 skipped** |
| 3 — Database-integriteit | `alembic heads` / `branches` / RLS-telling | ✅ 1 head (`0064_gate1b_inlees_voltooid`) · 0 branches · 38× ENABLE ROW LEVEL SECURITY |
| 4 — Veiligheid & conventies | grep Eraneos/compliman/cm_ (backend, frontend/src, modules, docs/adr) | ✅ 0 hits · alle likara-skills gevuld · CLAUDE.md-bouwstatus bijgewerkt naar V040 |
| Frontend-poort 1 | `vite build` | ✅ built (610 ms; chunk-waarschuwing >500 kB is geen fout) |
| Frontend-poort 2 | `vitest run` | ✅ **88 bestanden, 1146 tests groen** |
| Frontend-poort 3 | `npm run test:css-build` | ✅ 11 kritische klassen + 43 `--lk-`-tokens in de dist-CSS |
| Smoke test | `bash smoke_test.sh` + health | ✅ 4/4 · `{"status":"ok","db":"ok"}` |

## Aanvullende borging deze sessie

- **Engine-invariant**: dubbel geborgd voor het hele gate-1b-pad (import-afwezigheidstests + live geen-mutatie op `component_profiel`).
- **XXE**: kwaadaardige XML (external entity + entity-expansion) wordt geweigerd (defusedxml, `forbid_dtd`).
- **RBAC**: inlezen = beheerder (403-guard-tests op de echte router); matrix-spec-tests bijgewerkt.
- **Restdata**: 0 (WT-fixtures + eigen test-tenant `9999…` leeg na de runs; dev-tenant intact: 299 functies, `inlees_voltooid = true`).
- **Verse-installatie-bewijs**: schone DB + migraties + platform_init (zonder dev-seed) → aanbod gevuld, inlezen werkt (297 · 302 · 2455).

## Geaccepteerde afwijkingen

- 2 pre-existing skipped backend-tests (V039-baseline, ongewijzigd).
- Import-duur 13–25 s (facade-pad met per-call-commits — bewuste keuze, bezig-indicatie + afbreek-markering aanwezig; batch-optimalisatie is een gewogen niet-nu).
