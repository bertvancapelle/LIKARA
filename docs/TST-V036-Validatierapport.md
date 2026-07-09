# TST-V036 — Validatierapport

**Build:** V035 (→ V036 bij gen_build)
**Datum:** 2026-07-09
**Sessie:** LI035 — lijststaat-patroon (`useLijstStaat`, 4 lijstschermen) · ADR-042 volledig
(procesregister + koppelregel + schermen + roll-up, slices 1 t/m 5: `cc43418` · `ddb7b7a` ·
`3a65c3b` · `0c4fe60` · `8a76f55`, docs `2ff8fa9`, lijststaat `9128a24`/`233cc0c`) · zes
browsercheck-bevindingen omgezet in systeembrede patronen (Dialog-primitive/scroll-schaduw,
breedte-override, MeldingBanner, samengevoegd blok, succes-toast-standaard, regel-acties) ·
LI035-patronen + correcties vastgelegd in de acht likara-skills.
**Teststatus:** backend 997 (2 skipped) / frontend 80 files, 965 groen
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- `py_compile` over de repo (excl. `node_modules`/`__pycache__`): **0 fouten** (één pre-existing
  SyntaxWarning in een overgenomen framework-skill-script buiten de app-code).
- localStorage voor tokens: **0** (bestaande treffers zijn UI-voorkeuren — sidebar/weergave — nooit
  tokens). `lk_admin` in app-code: **0** (treffers zijn uitleg-comments + init-container-seeds).
- Eraneos/CompliMan-resten (`Eraneos`/`compliman`/`cm_`) in `backend`/`frontend/src`/`modules`/
  `docs/adr`: **0**.
- Geen hardcoded tenant-IDs, platform-namen of operator-referenties in de gewijzigde code.
- `vite build`: **succesvol** + css-build-check groen (7 kritische klassen, 41 verwezen
  `--lk-`-tokens gedefinieerd; nieuw: `.lk-scroll-schaduw` + de token-verwijzings-check zelf).

## As 2 — Tests
- Backend (`backend/tests/` + `modules/`, tegen de gemigreerde lk_app-DB op **0059**):
  **997 passed, 2 skipped, 0 failed**. Nieuw deze sessie o.a.: `test_proces_adr042.py` (15 —
  boom/cyclus/verwijdergedrag/RLS), `test_procesvervulling_adr042.py` (18 — catalogus, tripel,
  regel-acties-PATCH, band-dekking-audit, engine-borging), `test_rollup_adr042.py` (7 — subboom-
  rollup met herkomst/pad/tak_id, organisatie-afleiding eigendom+gebruik+dedupe, RLS no-leak,
  read-only-bronscan + live geen-mutatie).
- Frontend **vitest**: **80 files, 965 passed, 0 failed**. Nieuw o.a.: `useLijstStaat.test.js`,
  `ProcesLijst`/`ProcesDetail` (boom, koppelregels, regel-acties, succes-toasts),
  `OnderliggendeProcessenSectie.test.js` (groepering per tak, pad-bijschrift, open-tenzij-groot,
  lijststaat), `PartijProcessenSectie.test.js` (afgeleid beeld), `dialogPreset.test.js`
  (scroll-structuur + schaduw-mechanisme), `meldingen.test.js` (succes-toast-vorm),
  ComponentFormulier/ComponentDetail herbouwd voor de overlay + vier-blokken-Overzicht.

## As 3 — DB-integriteit
- **Migratie-head: `0059_adr042_procesvervulling`** — single head, `alembic branches` leeg,
  lineair 0056→0059 (proces-subtype + boom-FK, applicatiefunctie-catalogus, procesvervulling).
- RLS in de volledige migratieketen: **36× ENABLE + 36× FORCE ROW LEVEL SECURITY** (alle
  tenant-scoped tabellen incl. `proces` en `procesvervulling`).
- Live-testdata opgeruimd (element-rijen via `finally`-teardown in alle live-tests; RU-*/PV-*-
  residu 0 na de runs).

## As 4 — Multi-tenancy / RLS & conventies
- Proces + procesvervulling: tenant-isolatie live geborgd (404 no-leak kruis-tenant op proces,
  vervulling, rollup én organisatie-proceskijk).
- Roll-up/organisatiekijk = pure leeslaag: per-functie read-only-bronscan + live geen-mutatie-
  bewijs (tellingen element/procesvervulling/audit_log vóór/na identiek); dubbele engine-borging
  (import-afwezigheid + geen lifecycle-mutatie) op alle nieuwe paden.
- Audit: band-dekking omgebouwd naar ORM-mutatiepaden (flush-hook-dekking); het systemische
  element-core-delete-gat expliciet als bekend risico gedocumenteerd (opvolgpunt, pre-existing).

## Samenvatting
- **0 kritieke bevindingen.** Backend 997 (2 skipped), frontend 80/965, `vite build` + css-check
  ok, migratie-head 0059.
- Acht app-commits deze sessie (233cc0c · 9128a24 · 2ff8fa9 · cc43418 · ddb7b7a · 3a65c3b ·
  0c4fe60 · 8a76f55) + de skill-/afsluit-commit. ADR-042 volledig gerealiseerd (5 slices);
  lijststaat-patroon platformbreed gevestigd; zes browsercheck-bevindingen → zes systeembrede
  patronen.
