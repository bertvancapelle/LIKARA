# TST-V038 — Validatierapport

**Build:** V037 (→ V038 bij gen_build)
**Datum:** 2026-07-11
**Sessie:** LI037 — Deelprocessen eerste-klas + tree-view-procesbeheer volledig geland:
subboom-verrijkte proces-projectie (deelprocessen als knopen, hiërarchie-edges, vervult op het
geregistreerde proces), proceszone als boom + gap-cue (subboom-semantiek), twee proces-ingangen
via één handoff (herkomst = oranje selectie), dubbelklik-inzoom met history-terugweg,
seed-idempotentie verantwoordelijken, processen-lijst als tree-view met verbindingslijnen +
beheer (verwijderen/verhangen met kring-preventie), gating-/vorm-consistentie op 6 plekken.
Feature-commits `ba6f688` · `8904b2a` · `4a29f2a` · `932f607` · `a970fac` · `ef2421f` ·
`ca6501a` · `ed0799b` · `d4b7266` · skill-borging `d87aad7` (+ 7 checkpoint-/plan-commits).
**Teststatus:** backend 1001 (2 skipped) / frontend 81 files, 1046 groen
**Kritieke bevindingen:** 0

---

## As 1 — Code-kwaliteit
- `py_compile` over de repo (excl. `node_modules`/`__pycache__`): **0 fouten** (dezelfde ene
  pre-existing SyntaxWarning in een overgenomen framework-skill-script buiten de app-code).
- Eraneos/CompliMan-resten (`Eraneos`/`compliman`/`cm_`) in `backend`/`frontend/src`/`modules`/
  `docs/adr`: **0**.
- Geen hardcoded tenant-IDs, platform-namen of operator-referenties in de gewijzigde code;
  geen `localStorage`-tokengebruik (scan frontend + modules: **0**).
- `vite build` + css-build-check: **groen** (7 kritische interactie-klassen aanwezig in de
  dist-CSS, alle 41 verwezen `--lk-`-tokens gedefinieerd).

## As 2 — Tests
- Backend (`backend/tests/` + `modules/`, vanaf de repo-root): **1001 passed, 2 skipped,
  0 failed** (gelijk aan V037 — de subboom-projectie is binnen de bestaande
  `test_landschapskaart_proces.py`-suite herschreven naar de nieuwe semantiek: subboom-nodes,
  hiërarchie-edges, vervult-op-geregistreerd-proces, selectie-schaal; de module-brede
  engine-borging dekt het blok automatisch mee).
- Frontend **vitest** (vanuit `frontend/`): **81 files, 1046 passed, 0 failed** (+1 file,
  +40 t.o.v. V037). Nieuw o.a.: procesBoom-structuur/-layout (gedeelde boom-opbouw),
  proceszone-boom + gap-cue, proces-ingangen (handoff, oranje-selectie-focus, dim-opheffen),
  dubbelklik-inzoom (set-inperking + history), ProcesLijst tree-view (lijnen 3 niveaus diep,
  └-afsluiting, doorloop bij broers, zoeken+lijnen), gate-2-beheer (verwijderen incl. 409,
  verhangen incl. kring-preventie/promoveren/N-kinderen-zin), rol-gating (viewer/medewerker/
  beheerder per actie) + vorm-asserts (severity), en per componentdetail-sectie een
  medewerker-vs-beheerder-gating-test (5×).
- Flakiness: geen — beide suites in één keer groen (frontend deze afsluiting twee keer
  gedraaid, beide runs identiek groen).

## As 3 — DB-integriteit
- **Migratie-head: `0059_adr042_procesvervulling`** — single head, `alembic branches` leeg;
  RLS-statements in de volledige migratieketen (`upgrade head --sql` dry-run): **36×
  ENABLE ROW LEVEL SECURITY**. Deze sessie **geen schema-wijziging** (subboom-projectie is een
  pure leeslaag; de seed-fix raakt uitsluitend dev-seed-data).
- Restdata: deze sessie is **geen** walkthrough-/WT-testdata aangemaakt (browserchecks liepen
  op de reguliere dev-seed); de seed-idempotentie is juist expliciet bewezen met een
  twee-runs-vergelijking (3 gevuld / 264 leeg, stabiel).

## As 4 — Multi-tenancy / RLS & conventies
- De subboom-projectie draait volledig binnen de bestaande tenant-scoped sessie (zelfde
  leespaden als V037; omlaag-batching op `Proces.ouder_id` binnen dezelfde sessie) — geen
  queries buiten RLS-context.
- **Engine onaangeroerd geborgd**: de module-brede import-afwezigheid + read-only-bronscan op
  `landschapskaart_service` dekken het herschreven projectie-blok — score blijft de enige
  lifecycle-driver; één roll-up-bron (omlaag-subboom = spiegel van `rollup_voor_proces`).
- RBAC-consistentie hersteld op de affordance-laag: destructieve acties gaten nu vooraf op het
  VERWIJDEREN-recht (beheerder) op alle 6 plekken; de matrix zelf is **niet** gewijzigd;
  procesvervulling/roltoewijzing bewust op WIJZIGEN gelaten (backend-guard klopt daar).
- Alle likara-skills gevuld (>200 bytes); CLAUDE.md-bouwstatus wordt door `gen_build.py`
  bijgewerkt in deze afsluiting.

## Samenvatting
- **0 kritieke bevindingen.** Backend 1001 (2 skipped), frontend 81/1046, `vite build` +
  css-check ok, migratie-head 0059 (ongewijzigd, single head, 36× RLS), geen restdata.
- Zeventien commits deze sessie (10 feature/borging + 7 checkpoint/plan): deelprocessen
  eerste-klas op de kaart (fase 0–4), seed-idempotentie, tree-view-procesbeheer, gating-/
  vorm-consistentie, 12 patronen geborgd in vier likara-skills + zes nieuwe opvolgpunten.
