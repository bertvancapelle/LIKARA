# TST-V032 — Validatierapport

**Build:** V031 (→ V032 bij gen_build)
**Datum:** 2026-07-04
**Sessie:** LI031 — ADR-038 (gebruikersgroep-consolidatie + intern/extern-kenmerk) volledig geland:
Slice 1a (`partij.scope`, additief, migratie 0052) · Slice 1b (groep altijd bij organisatie,
`gebruik_id` NOT NULL + `burger`-aard verwijderd, migratie 0053) · Slice 2a (groep-dialoog organisatie
verplicht) · Slice 2b (intern/extern kiesbaar + zichtbaar) · Slice 2c (dood burger-kaartsymbool weg).
**Teststatus:** backend 851 (module) + 80 (platform) / frontend 780 groen (2 skipped)
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- `py_compile` over alle projectcode (`backend/**` + `modules/**`, 323 bestanden) → **OK** (0 syntaxfouten).
- localStorage voor tokens (`frontend/src` + `modules/*/frontend`): **0**.
- `lk_admin` als app-connectie-string in app-code (`backend/app` + `modules/*/backend`): **0** (app verbindt als `lk_app`).
- Eraneos/CompliMan-resten (`Eraneos`/`compliman`/`cm_`) in `backend`/`modules`/`docs/adr`: **0**.

## As 2 — Tests
- Backend module (`modules/bwb_ontvlechting/backend/tests`, tegen de gemigreerde lk_app-DB op 0053):
  **851 passed, 2 skipped, 0 failed** (≈32s). Netto t.o.v. V031: +10 (Slice 1a `partij.scope`:
  `_effectieve_scope`/`_valideer_scope`-matrix, schema-consistentie, CHECK-backstops, audit-capture,
  default/forced/derive) en de Slice 1b-consolidatie (org-verplicht schema+DB-backstop, werk_bij-null-
  weigering, RESTRICT-gedrag, burger-aard-verwijderd); herziene org-loos-/signaal-/kaart-tests.
- Backend platform (`backend/tests`): **80 passed, 0 failed**.
- Frontend **vitest**: 66 files, **780 passed** (+8 t.o.v. V031 = intern/extern-veld per aard,
  default Extern, payload/voorvullen, PartijDetail-leesregel; groep-dialoog org-required; herschreven
  stale burger-tests; opgeruimd kaart-burger-symbool).
- De **2 skips** zijn pre-existing, seed-omgevingsafhankelijk — geen ADR-038-relatie.
- **Geaccepteerde afwijking:** ~31 unhandled-rejection-consoleruis in `LandschapskaartView.test.js` /
  theme-CSS-fetch-abort — **geen falende test** (780/780 groen); geagendeerd voor de Impact-verkenner
  render-herbouw.
- Smoke test: **4 geslaagd, 0 mislukt**. API-health: `{"status":"ok","db":"ok"}`.

## As 3 — DB-integriteit
- `alembic heads` → **1 head**: `0053_adr038_consolidatie`.
- `alembic branches` → **0** (geen split).
- Migratie-revisie-id's ≤ 32 tekens (`alembic_version` varchar(32)): `0052_adr038_scope` (17) en
  `0053_adr038_consolidatie` (24) OK.
- ADR-038 (0052): `partij.scope` (`partij_scope_enum` intern/extern), nullable + twee CHECKs
  (gezet iff organisatie/externe_partij; externe_partij vast extern). ADR-038 (0053):
  `gebruikersgroep.gebruik_id` NOT NULL + FK → RESTRICT; `partij_aard_enum` zonder `burger`
  (type-recreate met drop/herbouw van de aard-CHECKs). Down/up-reversibiliteit van beide geverifieerd;
  0053 draagt een dev-only defensieve opruiming (no-op op een verse DB).

## As 4 — Multi-tenancy / RLS & conventies
- Geen tenant-scoped tabel-wijzigingen die RLS raken: `partij.scope` erft de bestaande FORCE-RLS-policy
  van `partij`; `gebruikersgroep.gebruik_id`/FK erven die van `gebruikersgroep`. `scope`-CHECKs en de
  `gebruik_id`-FK zijn tenant-consistent (composiet-FK's; RESTRICT/CHECK op de eigen rij).
- Geen hardcoded tenant-IDs/platform-namen/operator-referenties in de gewijzigde code.

## As 5 — Engine-invariant (score = enige lifecycle-driver)
- Dubbele borging groen: (1) afwezigheidstest — `partij_service` (incl. het nieuwe scope-pad) en de
  consolidatie-paden importeren geen `herbereken_*`/`bepaal_lifecycle`/`Checklistscore`/`Blokkade`/
  `ComponentProfiel` buiten de engine; (2) live-test — geen trigger op `partij`; een scope-/organisatie-
  mutatie laat `component_profiel`/`lifecycle_status`/`score`/`blokkade` ongemoeid. ADR-038 is puur
  registratie/structuur/read.

---

## Conclusie
**0 kritieke bevindingen.** ADR-038 volledig geland en geborgd (Slice 1a → 2c). Alle assen groen;
klaar voor build-bump naar V032.
