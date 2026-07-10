# TST-V037 — Validatierapport

**Build:** V036 (→ V037 bij gen_build)
**Datum:** 2026-07-10
**Sessie:** LI036 — Lagenweergave mét proceslaan volledig geland: "Lagen" als derde kaart-weergave
(preset-baanposities + meet-stap-render-fix), rolbanen met rol-accent (partij in meerdere banen),
"ring uit wint van gaps", organisatiebalk in-beeld (model i), backend proces-projectie in de
subgraaf (roll-up naar hoofdproces, cyclus-veilig), proceslaan + ring "Processen" + proces-vorm,
aantal-badge + herkomst-popup + vervul-toggle met ongedaan-maken-semantiek. Commits `7b4c00c` ·
`0b4a5dd` · `d2b07f3` · `5fa5fe0` · `f9a8a6f` · skill-borging `9914c25` · ADR-onderhoud `a99fe23`.
**Teststatus:** backend 1001 (2 skipped) / frontend 80 files, 1006 groen
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- `py_compile` over de repo (excl. `node_modules`/`__pycache__`): **0 fouten** (één pre-existing
  SyntaxWarning in een overgenomen framework-skill-script buiten de app-code).
- Eraneos/CompliMan-resten (`Eraneos`/`compliman`/`cm_`) in `backend`/`frontend/src`/`modules`:
  **0**.
- Geen hardcoded tenant-IDs, platform-namen of operator-referenties in de gewijzigde code.
- `vite build`: **succesvol** + css-build-check groen (7 kritische interactie-klassen aanwezig,
  alle 41 verwezen `--lk-`-tokens gedefinieerd).

## As 2 — Tests
- Backend (`backend/tests/` + `modules/`, tegen de gemigreerde lk_app-DB op **0059**):
  **1001 passed, 2 skipped, 0 failed** (+4 t.o.v. V036). Nieuw deze sessie:
  `test_landschapskaart_proces.py` (herkomst-veld additief, processen-ring in de subgraaf,
  doorrol naar hoofdproces live, cyclus-veilige `_wortel`-klim live) — met self-contained
  teardown leaf→root incl. kring-breken; de module-brede engine-borging (import-afwezigheid +
  read-only-bronscan in `test_landschapskaart.py`) dekt het proces-projectie-blok automatisch mee.
- Frontend **vitest** (vanuit `frontend/`): **80 files, 1006 passed, 0 failed** (+41 t.o.v.
  V036). Nieuw o.a.: Lagen-weergave-describes (weergave-as, baan-toewijzing, meet-stap),
  rolbanen/instance-projectie (logischId-interactie, rol-tags, dim-deling), ring-uit-wint,
  organisatiebalk-in-beeld (model i, contrafeitelijk), proceslaan (ring, vorm, popup-dispatch),
  stap-3 (aantal-badge, herkomst inklapbaar, vervul-toggle + exact-ongedaan-maken),
  maatwissel-fit; `kaartLayout.test.js` uitgebreid met de preset-baan-invariant op échte
  cytoscape (7-banen-volgorde incl. proces-node, distinct deterministische posities).
- Flakiness: geen — volledige run in één keer groen (de eerder deze sessie waargenomen
  dubbeltap-timer-timeouts onder CPU-verzadiging traden niet op; genoteerd in likara-tests als
  belastinggevoeligheid, geen code-regressie).

## As 3 — DB-integriteit
- **Migratie-head: `0059_adr042_procesvervulling`** — single head, `alembic branches` leeg.
  Deze sessie **geen schema-wijziging** (proces-projectie is een pure leeslaag; `herkomst` is
  een additief response-veld, geen kolom).
- **Restdata-check = 0** — expliciet gecontroleerd na het teardown-residu eerder deze sessie:
  `WT-%`/`TST-%` in proces, component, partij en relatie elk **0**; wees-procesvervullingen
  (zonder bestaand proces of component) **0**.

## As 4 — Multi-tenancy / RLS & conventies
- Proces-projectie draait volledig binnen de bestaande tenant-scoped sessie (`_sc`-scoping op
  `Procesvervulling.component_id`); geen nieuwe queries buiten RLS-context.
- **Engine onaangeroerd geborgd**: de module-brede import-afwezigheid + read-only-bronscan op
  `landschapskaart_service` (2 tests, gericht herdraaid: groen) dekken het nieuwe
  verrijkingsblok — score blijft de enige lifecycle-driver.
- Eén roll-up-definitie: de kaart-projectie gebruikt dezelfde bottom-up-bron als
  `rollup_voor_proces` — geen tweede driftende definitie geïntroduceerd.

## Samenvatting
- **0 kritieke bevindingen.** Backend 1001 (2 skipped), frontend 80/1006, `vite build` +
  css-check ok, migratie-head 0059 (ongewijzigd), restdata 0.
- Zeven commits deze sessie (`7b4c00c` · `0b4a5dd` · `d2b07f3` · `5fa5fe0` · `f9a8a6f` ·
  `9914c25` · `a99fe23`): Lagenweergave + proceslaan volledig, 16 patronen geborgd in vijf
  likara-skills, ADR-034/040 bijgewerkt naar de gebouwde realiteit (open diepte-punt
  "deelprocessen eerste-klas" prominent als tussenstand gemarkeerd).
