# TST-V035 — Validatierapport

**Build:** V034 (→ V035 bij gen_build)
**Datum:** 2026-07-08
**Sessie:** LI034 — ADR-041 persoonlijke voorkeuren: voorkeur-laag (`gebruiker_voorkeur`, migratie 0055,
RBAC eigen-scope) · component-breed organisatiegebruik-schrijf-slot (`valideer_component`) · terugrol
sectie-voorkeur · kaart-kijkfilter als persoonlijke standaardkijk + reload-fix (herladen behoudt werk) ·
kaart-bug B (doorklik popup↔zijpaneel gelijkgetrokken via `_heeftComponentDetail`) · kaart-bug A
(relatie-loos set-lid tekenen op Overzicht) · 7 skillpatronen vastgelegd in de negen likara-skills.
**Teststatus:** backend 960 (2 skipped) — 880 module + 80 platform / frontend 71 files, 869 groen
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- `py_compile` over `backend/` + `modules/` (excl. `__pycache__`): **0 fouten**.
- localStorage voor tokens / `lk_admin` als app-connectie-string in app-code: **0** (ongewijzigd).
- Eraneos/CompliMan-resten (`Eraneos`/`compliman`/`cm_`) in `backend`/`frontend/src`/`modules`/`docs/adr`: **0**.
- Geen hardcoded tenant-IDs, platform-namen of operator-referenties in de gewijzigde code.
- `vite build`: **succesvol** (chunk-grootte-waarschuwing op `LandschapskaartView` is pre-existing).

## As 2 — Tests
- Backend (`backend/tests/` + `modules/`, tegen de gemigreerde lk_app-DB op **0055**):
  **960 passed, 2 skipped, 0 failed** — 880 module + 80 platform. Nieuw deze sessie o.a.: voorkeur-laag
  (`test_voorkeur.py`: schema-guard, engine-import-afwezigheid, RBAC eigen-scope; live: upsert/vervangt,
  `sub`-isolatie, tenant-isolatie), component-breed schrijf-slot (`valideer_component` accepteert elk
  componenttype, niet-component → `ONGELDIG_COMPONENT`; live: schrijf negeert de voorkeur), RBAC-spec
  uitgebreid (`GEBRUIKER_VOORKEUR`, 24×4×4).
- Frontend **vitest**: **71 files, 869 passed, 0 failed**. Nieuw/bijgewerkt in `LandschapskaartView.test.js`:
  standaardkijk (opslaan zet `kaart_kijkfilter` zonder `actieveSet`; toepassen bij mount/`wisSet`;
  precedentie), reload (`_bewaarKaartState`/`beforeunload`/`wisSet` wist `lk-state`; in-sessie wint van
  standaardkijk), bug B (doorklik gelijkgetrokken), bug A (relatie-loos set-lid getekend + cue).
  `GebruikteApplicatiesSectie.test.js` teruggebracht naar de component-brede lijst (sectie-voorkeur weg).

## As 3 — DB-integriteit
- **Migratie-head: `0055_adr041_gebruiker_voorkeur`** (lineair op 0054; single head, geen branch).
  Nieuwe tabel `gebruiker_voorkeur` (FORCE RLS + policy `tenant_isolation` + REVOKE/GRANT geverifieerd
  tegen de DB: `relforcerowsecurity=t`, policy aanwezig; uniek `(tenant_id, sub, voorkeur_sleutel)`).
- Geen andere schema-wijziging; het component-brede schrijf-slot is puur validatie-code (geen migratie).
- Live-testdata opgeruimd (0 `pref:%`/`WT-*`-restrijen na de runs; expliciet geverifieerd).

## As 4 — Multi-tenancy / RLS & conventies
- Voorkeur-laag: **tenant-isolatie + `sub`-isolatie** live geborgd (gebruiker B ziet/raakt A's voorkeur
  niet; zelfde `sub` in andere tenant → leeg). `sub` altijd server-side uit `huidige_actor()`, nooit uit
  de payload (`extra='forbid'`).
- RBAC eigen-scope (`_EIGEN_VOORKEUR`): elke tenant-rol beheert alleen zijn eigen voorkeuren; ownership in
  de service. Niet geaudit (bewust — geen compliance-record).
- Engine onaangeroerd: import-afwezigheid + geen lifecycle-mutatie na voorkeur-/organisatiegebruik-writes.

## Samenvatting
- **0 kritieke bevindingen.** Backend 960 (2 skipped), frontend 869, `vite build` ok, migratie-head 0055.
- Zes app-commits deze sessie (9498983 · b05cc53 · f5e7afe · c8ae3c7 · 33fa485 · 3d889ab) + de skill-/
  afsluit-commit. ADR-041 afgerond; beide geparkeerde kaart-bugs (A, B) opgelost.
