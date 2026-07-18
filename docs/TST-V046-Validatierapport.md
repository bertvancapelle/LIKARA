# TST-V046 — Validatierapport

**Build**: V046
**Datum**: 2026-07-18
**Sessie**: LI045 — ADR-052 slices 4a/4b/4c (verschoven lat, norm-beheerscherm, lat-tijdens-invullen) + ADR-053 (Archiefwet) + integrale testronde (S1/C1/C2) + patroon-borging
**Kritieken**: 0

---

## Aard van de sessie

Afronding van de tenant-norm (ADR-052): de gemeente kan nu haar eigen lat voor "migratieklaar" zelf
zien en verzetten, en het systeem onderscheidt streng een bewuste afwijking van een verschoven lat.
Daarnaast ADR-053 (Archiefwet als hard componentfeit, besloten — nog niet gebouwd), een integrale
testronde over het hele normverhaal, en de gevalideerde patronen naar de skills. Alle bouw is per
opdracht apart gecommit + gepusht; deze afsluiting is administratie/borging.

- **Code (gecommit + gepusht):**
  - `aaeeb15` slice 4a — verschoven lat (neutraal) onderscheiden van bewuste afwijking (amber); één
    afleiding `splits_afwijking` (snapshot × live), geen nieuwe opslag.
  - `d748fcf` slice 4b — norm-beheerscherm: de beheerder ziet en verzet de lat; impact-voorspelling
    vóór opslaan; "wanneer/door wie" uit het audit-spoor.
  - `f8a9142` slice 4c — de lat zichtbaar tijdens het invullen (norm-"i" per feit, één aanduiding op
    het kleinste omvattende element); VeldUitleg adopteert `popoverPositie.js`.
  - `6a0931a` S1 — dev-seed schoon geval (HR-systeem, volledig norm-compleet → géén signaal) + borgtest.
  - `3e74a47` C1 — feitnaam "Bedrijfsfunctie" als ondertitel onder "Waarvoor gebruiken we het".
- **Docs/skills (gecommit + gepusht):** `d661846` ADR-052-uitbreiding (besluiten 8-14) + grond;
  `9c0a002` ADR-053 Archiefwet + zaaktype-horizon; `0c7860d` LI045-patronen in vier skills.
- **Schema geraakt** — geen nieuwe migraties deze sessie boven op LI044; head blijft `0073`. Slice 4
  is sleutelgestuurd (nieuw feit = nieuwe sleutel in `component_norm`, geen schemawijziging).

---

## Resultaat per as

| As | Onderwerp | Resultaat |
|----|-----------|-----------|
| **1** | Code-kwaliteit (py_compile, verboden patronen) | ✅ Geslaagd |
| **2** | Tests (backend + modules + frontend + build + css) | ✅ Geslaagd (0 failures) |
| **3** | Database-integriteit (heads/branches) | ✅ Geslaagd |
| **4** | Veiligheid en conventies | ✅ Geslaagd |

### As 1 — Code-kwaliteit
- `py_compile` over alle backend/module-Python: **0 syntaxfouten**.
- Geen hardcoded tenant-IDs / platform-namen (`powered_by`) in code: **0 treffers**.

### As 2 — Tests
```
backend (platform + modules bwb):   1159 passed, 2 skipped
frontend (vitest):                  93 files / 1202 passed
vite build:                         ✅ built (alleen de bestaande >500kB chunk-warning)
test:css-build:                     ✅ 0 afwijkingen / 76 views, detailkop 7, zelftests bijten (5/5)
```
- De **2 skips** zijn seed-afhankelijke tests (bewust overgeslagen op deze DB-stand), geen falen.
- **Nieuwe borging deze sessie:** `test_seed_schoon_geval_s1` (het schone geval blijft signaalloos ná
  een latverschuiving; valt om zodra de seed het vervuilt) + de tellende norm-aanduiding-tests
  (`#[data-norm-lat]` == aantal genormeerde feiten; BIV één keer) + de C1-zichtbare-tekst-test.
- **Engine-borging groen:** import-afwezigheid + read-only bronscan op de norm-/beheer-services — de
  tenant-norm raakt score/lifecycle/blokkade niet.

### As 3 — Database-integriteit
- `alembic heads` → **`0073_adr052_klaarverkl_snapshot` (één head)**.
- `alembic branches` → **leeg** (0 branches). Slice 4 was sleutelgestuurd — geen nieuwe migratie.

### As 4 — Veiligheid en conventies
- Verboden referenties (`Eraneos` / `compliman` / `cm_`) in code: **0**.
- localStorage: **3 treffers, alle UI-voorkeuren** (sidebar-inklap, architectuurweergave) — **geen
  tokens** (de token-in-localStorage-verbod is niet geschonden).
- Alle likara-skills gevuld; LI045-patronen vastgelegd (verschoven lat, sterretje-conventie, één
  aanduiding per feit, feit-brug, gevolgen-vóór-opslaan, referentiemodel-dekking, norm-default).

---

## Integrale testronde — bevindingen en afhandeling

De integrale testronde over het hele normverhaal (`docs/TST-Normverhaal-V045.md`) leverde 0 blokkerend,
1 storend, 2 cosmetisch. Afhandeling:

| Bevinding | Aard | Afhandeling |
|---|---|---|
| **S1** — de demostaat toonde nergens een "in orde"-geval (elk klaar-verklaard component droeg een signaal) | Storend | **Gerepareerd** (`6a0931a`): HR-systeem als schoon geval in de dev-seed (volledig norm-compleet, "bewust geen koppelingen"), signaalloos ook na een latverschuiving; geborgd met `test_seed_schoon_geval_s1`. |
| **C1** — de consultant vond "Bedrijfsfunctie" uit zijn werkvoorraad niet terug (sectie heet "Waarvoor gebruiken we het") | Cosmetisch | **Gerepareerd** (`3e74a47`): feitnaam als ondertitel onder de kop, uit `NORM_FEIT_LABEL`; geborgd met een zichtbare-tekst-test. |
| **C2** — "Bedoeling (migratiepad)" (normscherm) vs. "Bedoeling" (formulier); Contract↔Contracten; Verantwoordelijke↔Verantwoordelijkheden | Cosmetisch | **Bewust gelaten met reden**: enkelvoud/meervoud is geen afwijking, en "(migratiepad)" is een verhelderende toevoeging op de plek waar de beheerder kiest — gelijktrekken zou de koppen ongemakkelijker maken. Vastgelegd als patroon in likara-ux (§LI045, "hetzelfde feit heet overal hetzelfde of de brug wordt zichtbaar"). |

---

## Geaccepteerde afwijkingen

1. **Werktree schoon** — alle LI045-bouw is per opdracht apart geland (één opdracht per commit, telkens
   gepusht vóór de volgende `START`).
2. **ADR-053 (Archiefwet) besloten, niet gebouwd** — een eigen component-enum `{ja, bewust_geen}` met
   `null` = "nog niet gekeken"; ingepland ná de norm-slices (OPVOLGPUNTEN / NEXT_SESSION). Geen defect.
3. **GEMMA-dekking functie↔proces** — 4% relatie-dekking gemeten → geen automatische brug gebouwd; open
   verificatie of de publieke GEMMA-repo méér relaties draagt dan ons AMEFF-bestand (OPVOLGPUNTEN).

**Conclusie: 0 kritieken. Build V046 vrij te geven.**
