# TST-V027 — Validatierapport

**Build:** V026 (→ V027 bij gen_build)
**Datum:** 2026-07-01
**Sessie:** LI057 + LI058 (component-focus-herfundering — Slice 1 + Slice 2) + OP-30
**Teststatus:** backend 944 / frontend 745 groen (2 skipped)
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- `py_compile` over `backend/**` + `modules/**` → **OK** (0 fouten).
- localStorage voor tokens: **0**.
- `lk_admin` als app-connectie-string in app-code: **0** (app verbindt als `lk_app`/`lk_platform`).
- Hardcoded `tenant_id = '<uuid>'` in queries (excl. tests/seed/migraties): **0**.

## As 2 — Tests
- Backend (`backend/tests/ modules/`, tegen de pristine geseede lk_app-DB):
  **944 passed, 2 skipped, 0 failed** (≈16s). +3 t.o.v. V026 = de LI058-backfill-tests
  (`test_backfill_beoordeeld_li058`: offline engine-borging + 2 live-integratie).
- Frontend **vitest**: 65 files, **745 passed**.
- OP-30: de env-afhankelijke `test_auth_pkce`-cookie-test is deterministisch gemaakt
  (`cookie_secure` expliciet in de test; `backend/.env` zet `COOKIE_SECURE=false`).

## As 3 — DB-integriteit
- `alembic heads` → **1 head**: `0046_database_beoordeeld`.
- `alembic branches` → **0**.
- Migratie-revisie-ids ≤ 32 tekens (alembic_version varchar(32)): 0045/0046 OK.
- Migraties 0045/0046 up/down reversibel geverifieerd (kolommen + enum-rename + reconcile-vlag).

## As 4 — Veiligheid / conventies
- Vangrail-grep `Eraneos|compliman|cm_` in `backend/ frontend/src/ modules/`: **0**.
- Alle likara-skills gevuld (sluit_acties.py: 4/4 ✅).
- CLAUDE.md-bouwstatus bijgewerkt naar V027 (via gen_build).

## Engine-invariant-borging (LI057 + LI058)
- **Score = enige lifecycle-driver** blijft hard geborgd, dubbel:
  - **Offline:** `test_engine_borging_li057` (lifecycle_service leest de verhuisde
    `migratiepad/complexiteit/prioriteit` **0×**) + `test_backfill_beoordeeld_li058`
    (backfill delegeert aan `herbereken_type`, bevat geen eigen `bepaal_lifecycle`).
  - **Live:** `test_lifecycle*` + de LI058-backfill-integratietests groen (component krijgt
    profiel + afgeleide status; geen mutatie buiten het geactiveerde type).

## Component-focus-stand
- **Slice 1 (LI057):** `migratiepad/complexiteit/prioriteit` component-breed (basis-`component`,
  NOT NULL + defaults); enum `tijdelijk_gedeeld → gedeeld`. Expand: applicatie-subtabel behouden
  (bron = component; subtabel-spiegel via dual-write). Migratie **0045**.
- **Slice 2 (LI058):** scoren per type via `checklist_dragend`; `database` beoordeeld (migratie
  **0046** + seed); startset van 6 database-vragen; **profiel-backfill** bij `checklist_dragend`
  False→True (platform-toggle → per-tenant RLS-scoped worker-sessie, idempotent). True→False =
  profielen inert.
- Pristine reseed: profiel-stand applicatie 16/16 · database 1/1 · fileshare 0/1 · saas 0/1.
