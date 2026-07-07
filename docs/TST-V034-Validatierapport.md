# TST-V034 — Validatierapport

**Build:** V033 (→ V034 bij gen_build)
**Datum:** 2026-07-07
**Sessie:** LI033 — ADR-040 kaart-herbouw: deterministische render-eigenaar (fcose weg) ·
tweedeling Overzicht/Praatplaat + expliciete weergave-state + schakelaar (2a) · Impact-verkenner
afgeschaft · voorspelbare organisatie-scope (eenmalige seed, balk alleen op Overzicht, 2b) ·
afgeleide read-only gebruikt-lijn (org → applicatie, spiegel van eigenaar) + gebruikt-ring +
dode afdeling-sub-picker weg (3-1) · layout-herziening: samenval-fix (animate:false),
Overzicht=grid (centrumloos), Praatplaat=concentric + vensterverhouding-ellips, grotere knopen ·
12 skillpatronen.
**Teststatus:** backend 951 passed (2 skipped) / frontend 71 files, 840 groen
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- `py_compile` over `backend/` + `modules/` (excl. `__pycache__`): **0 fouten**.
- localStorage voor tokens / `lk_admin` als app-connectie-string in app-code: **0** (ongewijzigd).
- Eraneos/CompliMan-resten (`Eraneos`/`compliman`/`cm_`) in `backend`/`frontend/src`/`modules`/`docs/adr`: **0**.
- Geen hardcoded tenant-IDs, platform-namen of operator-referenties in de gewijzigde code.

## As 2 — Tests
- Backend (`backend/tests/` + `modules/`, tegen de gemigreerde lk_app-DB op 0054):
  **951 passed, 2 skipped, 0 failed** (≈35s). Nieuw deze sessie o.a.: de afgeleide gebruikt-edge
  (source-inspectie + 2 live integratietests: gebruikt-edge org→app, bezit+gebruik = twee lijnen,
  gebruiker-org via scope-add niet-dangling) en de bijgewerkte `test_eigenaar_edge_is_context_geen_impact`
  (afschaffing `IMPACT_RINGEN`).
- Frontend **vitest**: **71 files, 840 passed, 0 failed**. Nieuw `frontend/tests/kaartLayout.test.js`
  (echte cytoscape): geen samenvallende posities (grid-Overzicht deterministisch; concentric-Praatplaat),
  praatplaat-ellips breder-dan-hoog zonder overlap. Plus de omgezette weergave-state-/schakelaar-/scope-/
  gebruikt-ring-tests.
- De **2 skips** (backend) zijn pre-existing, seed-omgevingsafhankelijk — geen LI033-relatie.
- `vite build`: **OK** (✓ built, ~0.6s; de >500 kB-waarschuwing op de kaart-chunk is geen fout).

## As 3 — DB-integriteit
- `alembic heads` → **1 head**: `0054_contactpersoon_ref` (**ongewijzigd** — geen nieuwe migratie).
- `alembic branches` → **0** (geen split).
- **Geen schema-wijziging deze sessie.** Het enige backend-raakvlak is de afgeleide, read-only
  gebruikt-edge in `landschapskaart_service` (projectie van het bestaande grove feit `organisatiegebruik`;
  geen nieuwe tabel/kolom/relatie). Engine (score/lifecycle/blokkade) onaangeroerd.

## As 4 — Multi-tenancy / RLS & conventies
- De gebruikt-edge en scope-add draaien binnen de bestaande `_sc()`-scopefilter (tenant-gescoped);
  geen nieuwe query buiten het RLS-pad.
- Geen `SET` i.p.v. `set_config`, geen `lk_admin` in app-code, geen hardcoded tenant/operator.
- Frontend-only voor 2a/2b/layout; read-side + frontend voor 3-1.

---

## Samenvatting
Alle vier de assen groen; 0 kritieke bevindingen. De ADR-040-kaart-herbouw (render-eigenaar,
tweedeling, scope-opschoning, gebruikt-lijn, layout-herziening) is geland zonder schema-/engine-raakvlak.
Openstaande punten in OPVOLGPUNTEN.md (terug/vooruit-navigatie, interactie-basis, 4 ringen volledig,
overige centreerbare objecttypes, scope-B, LI033b-stash-beslissing).
