# TST-V044 — Validatierapport

**Build**: V044
**Datum**: 2026-07-17
**Sessie**: LI043 — gate 4 kaart-lezing (slice 2 → A → B1 → B2) + serving-fix + brok 3 seed + naam-fix + patroon-borging
**Kritieken**: 0

---

## Aard van de sessie

Gate-4 kaart-lezing volledig geland + omliggende borging. Alle bouw is gecommit + gepusht; deze
afsluiting is administratie/borging (geen nieuwe code).

- **Code (gecommit + gepusht):**
  - `095491b` gate 4 slice 2 — proceslaan → bedrijfsfunctie-plek-laan (ADR-043)
  - `bae58b2` serving-richting-fix — "zonder gebruikersgroep" leest bron=component + richtingtest
  - `ac9db21` gate 4 brok 2 slice A — kaart-lezing werk/status/domein + neutraliseer-model + meebewegende legenda
  - `bd60085` gate 4 brok 3 — dev-seed vertelt het functie-verhaal (5 standen), proces-seed verwijderd
  - `972df21` slice B1 — gedeelde `standCodering` + ernst-pills in de bedrijfsfunctielijst
  - `6d41dbf` slice B2 — stand-codering op de kaart + meebewegende standen-legenda (gedeelde bron, optie A)
  - `9b322b6` naam-fix — beoordelings-veldlabel → "Beoordelingsstatus", structureel uit de VELD_LABELS-registry
- **Skills/docs (gecommit + gepusht):** `d76e06a` gg-signaalrichting · `38b02eb` domeinmodel-terminologie
  (component/type/applicatie) · `5c4e479` zes sessiepatronen (frontend/ux + LOKAAL-TESTEN) · zes
  opvolgpunt-commits (`813a338` `2a1eba0` `0a46db6` `d33c850` `5d9b04f` `8937e95`).
- **Geen schema, geen migratie** — head blijft `0070`.

---

## Resultaat per as

| As | Onderwerp | Resultaat |
|----|-----------|-----------|
| **1** | Code-kwaliteit (py_compile, verboden patronen) | ✅ Geslaagd |
| **2** | Tests (backend + modules + frontend + build) | ✅ Geslaagd (0 failures) |
| **3** | Database-integriteit (heads/branches) | ✅ Geslaagd |
| **4** | Veiligheid en conventies | ✅ Geslaagd |

### As 1 — Code-kwaliteit
- `py_compile` over alle backend/module-Python: **0 syntaxfouten**.
- Geen hardcoded tenant-IDs / platform-namen / operator-referenties; geen localStorage-tokens.

### As 2 — Tests
```
backend (platform):            80 passed
backend (modules bwb):       1053 passed, 2 skipped
frontend (vitest):    95 files / 1222 passed
vite build:                  ✅ built (~0.5s)
```
Totaal backend: **1133 passed / 2 skipped / 0 failed**.
- De **2 skips** zijn seed-afhankelijke tests (`test_checklist_dragend_fix_f6`, `test_component_impact_cd056`)
  die een specifiek dev-seed-component vereisen — bewust overgeslagen op deze DB, geen falen.
- **De 2 audit-keten-tests uit V043** (`test_audit_capture_live.py`) **SLAGEN nu** (8 passed): de
  data-conditie in de dev-`audit_log` (ketenbreuk op een oude rij) is opgelost — waarschijnlijk via een
  reseed deze sessie. **Geen pre-existing failure meer; geen regressie.**

### As 3 — Database-integriteit
- `alembic heads` → **`0070_adr051_gapsignaal` (één head)**. Geen schema-wijziging deze sessie.
- `alembic branches` → **leeg** (geen split branches).

### As 4 — Veiligheid en conventies
- Verboden referenties (`Eraneos` / `compliman` / `cm_`) in **code** (`backend/ frontend/src/ modules/`): **0**.
- 3 treffers in `docs/adr/ADR-012` — **legitieme historische prose** (documenteert het verwíjderen van de
  17 CompliMan-rollen bij de migratie naar LIKARA); geen code, niet geraakt deze sessie.
- Alle likara-skills gevuld; frontend/ux/domeinmodel op **V043**-frontmatter (patroon-borging).

---

## Geaccepteerde afwijkingen

1. **Werktree schoon** — anders dan V043 is er deze afsluiting **geen** bewust-verstrengelde slice; alle bouw
   is per opdracht apart geland (één opdracht per commit, telkens gepusht vóór de volgende `START`).
2. **Skill-frontmatter "V043" vs. build V044** — de skills zijn tijdens de sessie op V043 gezet (de toen
   lopende build); gen_build bumpt de bouw naar V044. Inhoudelijk correct; de versielabel is een
   sessiestempel, geen breuk.

**Conclusie: 0 kritieken. Build V044 vrij te geven.**
