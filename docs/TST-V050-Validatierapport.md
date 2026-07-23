# TST-V050 — Validatierapport

**Build:** V050 · **Datum:** 2026-07-23 · **Sessie:** LI049 (afsluiting) · **Basis:** werktree op `d90629e` + afsluitwerk

## Resultaat per as

| As | Toets | Resultaat |
|---|---|---|
| 1 — Code-kwaliteit | `py_compile` over alle Python-bestanden | **OK — 0 syntaxfouten** (1 `SyntaxWarning` in een overgenomen framework-skill-script buiten de LIKARA-code: `engineering-team/ms365-tenant-manager/scripts/powershell_generator.py`; geen fout, geen LIKARA-bestand) |
| 2 — Tests | `python3 -m pytest backend/tests/ modules/` vanaf de repo-root | **1221 passed / 2 skipped** (incl. de nieuwe kopverwijzingen-scan: hoofdscan + 4 zelftests groen) |
| 3 — Database-integriteit | `alembic heads` / `branches` / RLS-telling | **1 head** (`0073_adr052_klaarverkl_snapshot`) · **0 branches** · **38× ENABLE ROW LEVEL SECURITY** in de offline upgrade-SQL |
| 4 — Veiligheid en conventies | grep `Eraneos\|compliman\|cm_` over backend/ frontend/src/ modules/ docs/adr/ | **0 hits** · alle 9 likara-skills gevuld (>200 bytes, `sluit_acties` ✅) · CLAUDE.md-bouwstatus wordt door `gen_build` op V050 gezet |

## Frontend-poorten

- `vitest run`: **102 files / 1374 passed**
- `vite build`: **OK** (666 ms; chunk-waarschuwing is geen fout)
- `check-css-build`: **14× OK** — alle bron-scans mét zelftests (veld, detailkop, lijstkop, icoon, kop-rij, kopstijl; elk bijt-bewijs groen)

## Kritieke bevindingen

**0.**

## Geaccepteerde afwijkingen

- `sluit_acties.py` gaf bij aanvang van de afsluitrun ❌ op git-status: de werktree droeg op dat
  moment per definitie het afsluitwerk zelf (blok A + protocolstappen); lost op bij de
  afsluitcommit (stap 7).
- De 9 skill-frontmatters en dit rapport dragen **V050 vooruitgeschreven** — het nummer wordt
  door `gen_build.py` in dezelfde afsluiting gezet (counter 49 → 50); zelfde conventie als de
  V049-afsluiting.

## Bijzonderheden van deze build

LI049 was een skill-consolidatiesessie: de suites zijn ongewijzigd gebleven op de
kopverwijzingen-scan na (+5 tests, `backend/tests/test_kopverwijzingen_scan.py`), die repo-breed
54–56 `skill §kop`-verwijzingen bewaakt en zich drie keer op nieuw werk bewees
(domeinmodel-verwijzing bij verhuizing 1; 4 code-docstrings bij de tests-consolidatie; de
mjs-comment-verwijzing).
