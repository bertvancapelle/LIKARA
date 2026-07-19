# TST-V047 — Validatierapport

| | |
|---|---|
| **Build** | V047 |
| **Sessie** | LI046 |
| **Datum** | 2026-07-19 |
| **Basis-commit** | `aca7cb1` (werktree schoon vóór afsluiting) |
| **Kritieke bevindingen** | **0** |

## Resultaat per as (CONTRIBUTING.md sectie 6)

| As | Controle | Resultaat |
|---|---|---|
| **1 — Code-kwaliteit** | `py_compile` op alle `*.py` (excl. node_modules/.git/__pycache__) | ✅ **0 syntaxfouten** (één `SyntaxWarning` in `.claude/skills/engineering-team/…/powershell_generator.py` — overgenomen framework-skill, geen LIKARA-productcode; py_compile slaagt) |
| **2 — Tests (backend)** | `python3 -m pytest backend/tests/ modules/ -q` | ✅ **1159 passed / 2 skipped** (46,7 s) |
| **2 — Tests (frontend)** | `npx vitest run` | ✅ **97 files / 1248 passed** |
| **2 — Build (frontend)** | `npx vite build` | ✅ built OK (chunk >500 kB is een waarschuwing, geen fout) |
| **2 — CSS-borging** | `npm run test:css-build` | ✅ 13 kritische klassen · 44 tokens · veld-scan 0/76 afwijkingen · detailkop-scan 7 · zelftests bijten (5/5, 7/7) |
| **3 — Database-integriteit** | `alembic heads` / `alembic branches` | ✅ **1 head** (`0073_adr052_klaarverkl_snapshot`), **0 branches** |
| **4 — Veiligheid & conventies** | grep `Eraneos\|compliman\|cm_` op `backend/ frontend/src/ modules/ docs/adr/` | ✅ **0 hits** |

## Geaccepteerde afwijkingen

- **`SyntaxWarning` (As 1):** in een overgenomen engineering-team-framework-skill (PowerShell-generator),
  buiten de LIKARA-productcode en bewust uitgesloten van de conventiescope (CONTRIBUTING §As 1/As 4).
- **2 skipped backend-tests:** de bekende live-DB-tests met een `skipif`-verbindingsprobe (offline-grens,
  likara-tests §Offline-grens).

## Conclusie

Alle vier de assen geslaagd; frontend- en backend-suites, build en alle scans groen. **0 kritieke
bevindingen.** Build V047 kan worden gegenereerd.
