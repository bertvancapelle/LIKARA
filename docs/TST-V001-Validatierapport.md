# TST-V001 Validatierapport — CompliData

**Build**: V001
**Datum**: 2026-06-05
**Uitgevoerd door**: CC
**Platform**: CompliData — een product van G. van Capelle Beheer B.V.

## Resultaten per as

| As | Beschrijving | Uitkomst | Details |
|---|---|---|---|
| As 1 | py_compile | ✅ | 0 syntaxfouten op alle Python-bestanden; 1 niet-blokkerende `SyntaxWarning` (zie geaccepteerde afwijkingen) |
| As 2 | pytest | ✅ | 5 passed, 0 failed (`modules/bwb_ontvlechting/backend/tests/`) |
| As 3 | Alembic-integriteit | ✅ | heads: 1 (`0001_bwb_initial`); branches: leeg; RLS-count in upgrade-SQL: 6 |
| As 4 | Veiligheid en conventies | ✅ | referentie-scan: 0 hits; alle 6 complidata-skills > 3000 bytes |

## Detail per as

### As 1 — Code-kwaliteit (py_compile)
Alle Python-bestanden gecompileerd zonder syntaxfouten. Eén `SyntaxWarning`
(invalid escape `\S`) in een overgenomen framework-skill-script
(`.claude/skills/engineering-team/ms365-tenant-manager/scripts/powershell_generator.py:242`).
Dit is een waarschuwing, geen fout; `py_compile` slaagt (exit 0).

### As 2 — Tests (pytest)
```
5 passed in 0.19s
```
Tests: modellen importeerbaar, enum-waarden, 89 unieke checklist-codes,
seed geeft 89 terug, seed idempotent.

### As 3 — Database-integriteit (Alembic)
- `alembic heads` → `0001_bwb_initial (head)` — exact 1 head.
- `alembic branches` → leeg — geen split.
- `alembic upgrade head --sql` → 6× `ENABLE ROW LEVEL SECURITY` (de 6
  tenant-scoped tabellen; `checklistvraag` heeft bewust geen RLS).

### As 4 — Veiligheid en conventies
- Referentie-scan (`Eraneos|compliman|CompliMan|cm_|cm-`) over
  `backend/ frontend/src/ modules/ docs/adr/` → **0 hits**.
- Alle 6 `complidata`-skills gevuld (3024–4398 bytes).

## Kritieke bevindingen

Geen.

## Geaccepteerde afwijkingen

| ID | Bevinding | Reden | Geaccepteerd door | Datum |
|---|---|---|---|---|
| TST-V001-K1 | `SyntaxWarning` (`\S` escape) in `.claude/skills/engineering-team/ms365-tenant-manager/scripts/powershell_generator.py:242` | Overgenomen framework-skill (geen CompliData-code); enkel een waarschuwing, `py_compile` slaagt. Buiten de scope van de As-4-referentiescan (`.claude/` bewust uitgesloten). | Bert van Capelle | 2026-06-05 |

## Conclusie

**Geslaagd** — alle 4 validatie-assen groen, 0 kritieke bevindingen,
1 gedocumenteerde geaccepteerde afwijking in een overgenomen framework-skill.
