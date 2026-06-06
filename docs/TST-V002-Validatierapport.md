# TST-V002 Validatierapport — CompliData

**Build**: V002
**Datum**: 2026-06-06
**Uitgevoerd door**: CC
**Platform**: CompliData — een product van G. van Capelle Beheer B.V.

## Resultaten per as

| As | Beschrijving | Uitkomst | Details |
|---|---|---|---|
| As 1 | py_compile | ✅ | 0 syntaxfouten op alle Python-bestanden; 1 niet-blokkerende `SyntaxWarning` (zie geaccepteerde afwijkingen) |
| As 2 | pytest | ✅ | 45 passed, 0 failed (`backend/tests/` + `modules/bwb_ontvlechting/backend/tests/`) |
| As 3 | Alembic-integriteit | ✅ | heads: 1 (`0002_platform_tenant`); branches: leeg; RLS-count in upgrade-SQL: 6 |
| As 4 | Veiligheid en conventies | ✅ | referentie-scan: 0 hits; alle 6 complidata-skills > 3000 bytes |

## Detail per as

### As 1 — Code-kwaliteit (py_compile)
Alle Python-bestanden gecompileerd zonder syntaxfouten. Eén `SyntaxWarning`
(invalid escape `\S`) in een overgenomen framework-skill-script
(`.claude/skills/engineering-team/ms365-tenant-manager/scripts/powershell_generator.py:242`).
Waarschuwing, geen fout; `py_compile` slaagt (exit 0). Geen `cd_admin`,
`localStorage` of hardcoded tenant/platform/operator in de app-code.

### As 2 — Tests (pytest)
```
45 passed in 0.65s
```
Gedraaid vanaf repo-root (`python3 -m pytest backend/tests/ modules/`, conform
de gecorrigeerde CONTRIBUTING §6). Dekking: model/enum/seed (7), PKCE
login/callback (15), tenant-RBAC-matrix 160 + guard (10), platform-RBAC-matrix
24 + kruis-scheiding + tenant-onboarding-validatie (13).

### As 3 — Database-integriteit (Alembic)
- `alembic heads` → `0002_platform_tenant (head)` — exact 1 head (platform-
  migratie gechaind aan `0001_bwb_initial`).
- `alembic branches` → leeg — geen split.
- `alembic upgrade head --sql` → 6× `ENABLE ROW LEVEL SECURITY` (de 6
  tenant-scoped tabellen; `checklistvraag` en het platform-register `tenant`
  hebben bewust geen RLS).

### As 4 — Veiligheid en conventies
- Referentie-scan (`Eraneos|compliman|cm_`) over
  `backend/ frontend/src/ modules/ docs/adr/` → **0 hits**.
- Alle 6 `complidata`-skills gevuld (3024–7221 bytes).
- Live geverifieerd deze sessie: cd_admin uit de app-laag (alleen
  init-container); cd_platform non-superuser zonder tenant-toegang;
  RLS cross-tenant = 0; platform/tenant-kruistoegang = 403.

## Kritieke bevindingen

Geen.

## Geaccepteerde afwijkingen

| ID | Bevinding | Reden | Geaccepteerd door | Datum |
|---|---|---|---|---|
| TST-V002-K1 | `SyntaxWarning` (`\S` escape) in `.claude/skills/engineering-team/ms365-tenant-manager/scripts/powershell_generator.py:242` | Overgenomen framework-skill (geen CompliData-code); enkel een waarschuwing, `py_compile` slaagt. `.claude/` valt buiten de As-4-scope. | Bert van Capelle | 2026-06-06 |

## Conclusie

**Geslaagd** — alle 4 validatie-assen groen, 0 kritieke bevindingen,
1 gedocumenteerde geaccepteerde afwijking in een overgenomen framework-skill.
