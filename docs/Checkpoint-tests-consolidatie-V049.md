# Checkpoint — likara-tests vóór consolidatie (READ-ONLY meting)

**Sessie:** LI049 · **Build:** V049 · **Branch:** master · **HEAD:** `94c5625`
**Werktree:** skills schoon; untracked staan alleen de LI049-checkpointrapporten
**Grond:** `docs/Checkpoint-borgingsregels-algemeen-vs-frontend-V049.md` · verhuizing 1 (het patroon)
**Datum meting:** 2026-07-22 · Niets gewijzigd behalve dit rapport. Scan groen (5 passed).

---

## Blok 1 — koppen, omvang en soort

### 1.1–1.2 Totaal en tabel

**538 regels** (`wc -l`; de laatste regel draagt geen afsluitende newline — een Read telt 539).
Frontmatter + titel: r1–9. **25 `##`-koppen + 1 `###`-kop = 26 totaal.** Som van alle secties +
voorwerk = 538 (sluitend).

| Regel | Kop | Bereik | Regels | Soort |
|---:|---|---|---:|---|
| 10 | conftest.py sys.path-patroon | 10–24 | 15 | onderwerp |
| 25 | Import-conventie | 25–35 | 11 | onderwerp |
| 36 | Model-unit-test-patroon (geen DB nodig) | 36–50 | 15 | onderwerp |
| 51 | Seed-test (asyncio.run — bewust géén pytest-asyncio) | 51–79 | 29 | onderwerp |
| 80 | Backend-tests (app-laag) — env vóór import | 80–88 | 9 | onderwerp |
| 89 | RBAC-matrixtests | 89–106 | 18 | onderwerp |
| 107 | TST-validatiecyclus (4 assen) | 107–121 | 15 | onderwerp |
| 122 | Afsluitprotocol — VOLLEDIG, geen lite-variant | 122–147 | 26 | onderwerp |
| 148 | Frontend-poorten (V003) | 148–207 | 60 | onderwerp (V003 = context, geen bak) |
| 153 | ### Frontend-testpatroon (vitest + @vue/test-utils) | 153–207 | 55 | onderwerp |
| 208 | Offline-grens (bewust) | 208–215 | 8 | onderwerp |
| 216 | V004-patronen (CD003–CD012, geverifieerd) | 216–228 | 13 | **chronologisch** |
| 229 | V007-patronen (CD039–CD056, geverifieerd) | 229–247 | 19 | **chronologisch** |
| 248 | V009/V010-patronen (ADR-023 Fase A–E, geverifieerd) | 248–275 | 28 | **chronologisch** |
| 276 | V010 — Fase F afgerond (F-3): … (geverifieerd) | 276–313 | 38 | **chronologisch** |
| 314 | V012-patronen (dekking: live-DB + end-to-end, geverifieerd) | 314–329 | 16 | **chronologisch** |
| 330 | LI020-patronen (test-hygiëne live-DB) | 330–344 | 15 | **chronologisch** (één onderwerp) |
| 345 | LI021-patronen (reset + live-DB-test-drift) | 345–364 | 20 | **chronologisch** (één onderwerp) |
| 365 | LI022-patronen (strategie A — testmigratie…, geverifieerd) | 365–384 | 20 | **chronologisch** (één onderwerp + 2 aanvullingen) |
| 385 | LI035-patronen (CSS-borging + succes-asserts) | 385–404 | 20 | **chronologisch** (bak, 4 onderwerpen) |
| 405 | LI036-patronen (teardown-aanvulling + suite-flakiness) | 405–422 | 18 | **chronologisch** (bak, 2) |
| 423 | LI039-patronen (test-tenant-grens, UI-pad-dekking, vorm-asserts) | 423–444 | 22 | **chronologisch** (bak, 3) |
| 445 | LI040-patronen (leegte-borging, scan-zelftests, catalogus-asserts) | 445–470 | 26 | **chronologisch** (bak, 5) |
| 471 | LI041-patronen (bronscan-norm + rollengrens-borging) | 471–492 | 22 | **chronologisch** (2, verwant) |
| 493 | LI046 — groen bewijst geen schone bron (bronbestand-hygiëne) | 493–523 | 31 | **chronologisch prefix, één onderwerp** |
| 524 | LI047 — `vi.clearAllMocks()` wist aanroepen… | 524–538 | 15 | **chronologisch prefix, één onderwerp** |

### 1.3 Chronologisch beslag

**15 chronologische `##`-koppen** (5× `V0xx`, 10× `LI0xx`), samen **324 van de 538 regels =
60,2%** — een zwaarder beslag dan het werkprotocol vóór verhuizing 1 had (104/638 = 16%).
Nuance die verhuizing 1 niet had: **5 van de 15** zijn geen grabbelzak maar één-onderwerp-secties
met een sessieprefix (LI020, LI021, LI022, LI046, LI047) — daar is de kop-hernoeming het werk,
niet het uiteenrafelen.

### 1.4 Is `V0xx` een andere soort dan `LI0xx`?

**Nee — beide zijn chronologie en verdienen dezelfde behandeling**, met twee praktische
verschillen die het werk juist beïnvloeden:
1. de V-koppen bundelen CompliMan-tijdperk-sessies en hun bullets dragen bijna allemaal al een
   eigen `[CDxxx]`-marker (V004: 3/3, V007: 4/4) — dáár is het markerwerk klein; de V009/V010-
   en V010-koppen niet (3/4 resp. 3/6 zónder);
2. **zes koppen dragen `(geverifieerd)` als búndel-kwalificatie** (V004, V007, V009/V010,
   V010-F3, V012, LI022) — zie 2.3. Een V-kop markeert geen andersoortige inhoud, alleen een
   andere tijdrekening.

---

## Blok 2 — per chronologische kop: thuiskop, marker, geverifieerd

Bestaande onderwerpskoppen zijn er 11 (10 `##` + het `###`-Frontend-testpatroon). De mapping
laat **vier terugkerende clusters zonder bestaande kop** zien; die staan onderaan als voorstel.

| Sectie · alinea | Thuiskop | Eigen marker? |
|---|---|---|
| **V004** b1 empirische verificatie draaiende stack | §Offline-grens | ✓ [CD007/008/010] |
| V004 b2 regressie-borging als vast onderdeel | geen — voorstel **"Regressie-borging"** | ✓ [CD009/011/004] |
| V004 b3 single-flight/async-tests | §Frontend-testpatroon | ✓ [CD007/CD003] |
| **V007** b1 tweeluik offline structureel + eenmalig live | §Offline-grens | ✓ [CD052/CD056] |
| V007 b2 force-recreate vóór live-check | voorstel **"Live-DB-tests"** — ⚠ dubbelt likara-resilience §P10 | ✓ [CD048-sweep] |
| V007 b3 baseline benoemde tellingen | geen — ⚠ dubbelt CLAUDE.md §Walkthrough-protocol | ✓ [CD054/CD056] |
| V007 b4 allowlist-synctest per sorteerbare lijst | voorstel **"Allowlist-synctests"** — ⚠ dubbelt V012 b3 | ✓ [CD054] |
| **V009/V010** b1 gate-per-schema-slice vs. doorloop | geen tests-kop — ⚠ dubbelt werkprotocol §Gate-discipline vrijwel woordelijk; cross-skill-kandidaat | **–** |
| V009/V010 b2 engine-borging dubbel (import-afwezigheid + live) | voorstel **"Engine-borging"** | **–** |
| V009/V010 b3 live-teardown structureel (element-supertype) | "Live-DB-tests" | ✓ (V009-follow-up a) |
| V009/V010 b4 nieuwe migratie ⇒ dev-DB bijwerken vóór live-run | "Live-DB-tests" | **–** |
| **V010-F3** b1 live signaal-fixture (oriëntatie/scope) | "Live-DB-tests" | **–** |
| V010-F3 b2 pure signaal-matrix offline | §Offline-grens | **–** |
| V010-F3 b3 read-only meting in het gate-rapport | geen tests-kop — cross-skill-kandidaat (werkprotocol §Gate-discipline) | ✓ (F-3: 8×) |
| V010-F3 b4 OPVOLGPUNTEN is tracked bestand | geen tests-kop — cross-skill-kandidaat (werkprotocol §Commit-discipline) | ✓ (DC011) |
| V010-F3 b5 dev-ergonomie (psql via docker exec, find -delete) | geen — kandidaat `docs/LOKAAL-TESTEN.md`/werkprotocol §Browsercheck stap-0-familie | **–** |
| V010-F3 b6 teardown via element-supertype + wees-telling + grep-tip | "Live-DB-tests" | ✓ (V011, 2×) |
| **V012** b1 live-DB-dekkingstest naast seed-test | "Live-DB-tests" | ✓ (V012) |
| V012 b2 service-/SQL-meting ≠ scherm-gedrag, end-to-end | §Frontend-testpatroon | ✓ (V012-bug) |
| V012 b3 sorteer-allowlist-synchroon-test | "Allowlist-synctests" — ⚠ dubbelt V007 b4 | **–** |
| **LI020** b1 self-cleaning via finally | "Live-DB-tests" | ✓ (LI020) |
| LI020 b2 meet de seed-functie, niet de live-staat | "Live-DB-tests" | **–** |
| **LI021** b1 na down -v handmatige dev-seed | "Live-DB-tests" | **–** |
| LI021 b2 seed-drift-diagnose | "Live-DB-tests" | **–** (noemt alleen LI020) |
| LI021 b3 nieuwe live-tests self-contained (WT-fixtures) | "Live-DB-tests" | **–** |
| **LI022** blok (strategie A, 3 samenhangende bullets) | §Frontend-testpatroon; de ast-docstring-strip-bullet (r381–384) → **"Bronscans"** | **–** → 1 blokmarker volstaat (à la LI048) |
| **LI035** b1 class-asserts bewijzen geen rendering (dist-CSS laag C) | "Bronscans" (css-build-tak) | **–** (noemt MeldingBanner-les zonder nr) |
| LI035 b2 Tailwind-candidate-valkuil in de check zelf | "Bronscans" | **–** |
| LI035 b3 succes-toast-asserts | §Frontend-testpatroon | **–** |
| LI035 b4 vitest draait ALTIJD vanuit frontend/ | §Frontend-testpatroon | ✓ (LI035, 3×) |
| **LI036** b1 teardown-kring breken + residu-meting | "Live-DB-tests" | ✓ (LI036) |
| LI036 b2 suite-flakiness onder belasting | §Frontend-testpatroon | ✓ (LI036-meting) |
| **LI039** b1 eigen test-tenant zodra teardown breder veegt | "Live-DB-tests" | ✓ (besluit Bert, LI039) |
| LI039 b2 elk UI-pad minstens één test die hem ÉCHT opent | §Frontend-testpatroon | **–** |
| LI039 b3 vorm-asserts (knopvorm draagt betekenis) | §Frontend-testpatroon | **–** |
| **LI040** b1 assert op zichtbare TEKST | §Frontend-testpatroon | **–** (noemt LI030) |
| LI040 b2 **bewijs dat een test/scan bijt** (r452–455) | **"Bronscans"** (de kern) | **–** |
| LI040 b3 complementariteit gat-filters | "Live-DB-tests" (live-borging) | **–** |
| LI040 b4 assert alleen eigen data, óók catalogi | "Live-DB-tests" | **–** (noemt LI021) |
| LI040 b5 engine-grens dubbel + omgekeerde woord-scan | "Engine-borging" | **–** |
| **LI041** b1 gedeelde leesregel → bronscan-norm + vals-rood | **"Bronscans"** | ✓ (LI038·LI040·LI041) |
| LI041 b2 rollengrens = classificatie-bronscan | **"Bronscans"** | ✓ (ADR-050) |
| **LI046** blok null-bytes/bronbestand-hygiëne | eigen onderwerpskop (titel bestaat al ná het prefix: "groen bewijst geen schone bron") | deels (⚠-deel draagt LI048) → 1 blokmarker |
| **LI047** blok clearAllMocks | eigen onderwerpskop (titel bestaat al ná het prefix) | ✓ (LI047) |

**2.2 — zonder eigen marker: 23 alinea's/blokken** (V009/V010: 3 · V010-F3: 3 · V012: 1 ·
LI020: 1 · LI021: 3 · LI022: 1 blok · LI035: 3 · LI039: 2 · LI040: 5 · LI046: 1 blok) — de
lijst die bij verplaatsing een marker moet krijgen, zoals bij verhuizing 1.

**2.3 — `(geverifieerd)` hangt aan de KOP, niet aan de alinea.** Zes koppen dragen het als
bundel-kwalificatie. Bij verplaatsing per alinea gaat die status verloren tenzij hij in de
marker meereist (bv. `(V007, geverifieerd)`); geen enkele alinea draagt hem nu zelf. Dit is een
extra marker-eis die verhuizing 1 niet had.

**Nieuwe onderwerpskoppen die uit de mapping oprijzen (4):**
1. **"Live-DB-tests"** (fixtures · teardown · drift · eigen test-tenant) — grootste cluster, ~13 alinea's uit 8 secties;
2. **"Bronscans"** (bijten · vals-alarm/vals-rood · bereik · uitzonderingen) — ~6 alinea's; dé landingsplek voor verhuizing 3;
3. **"Engine-borging"** — 2 alinea's (+ verwijzing naar likara-domeinmodel §6);
4. **"Allowlist-synctests"** — 2 alinea's die elkaar nu dubbelen.
Plus **6 cross-skill-kandidaten** (V007 b2/b3, V009/V010 b1, V010-F3 b3/b4/b5) die inhoudelijk
niet in een tests-skill thuishoren — een soort werk dat verhuizing 1 níét had.

---

## Blok 3 — de "bronscans"-kop die verhuizing 3 nodig heeft

1. **Bestaande bronscan-dragende plekken (4 koppen, 7 passages):** §LI040-patronen r452–455
   (bijt-eis) · §LI041-patronen r472–485 (bronscan-norm) + r484–486 (vals-rood-verfijning) +
   r486–491 (rollengrens-classificatiescan) · §LI035-patronen r386–393 (dist-CSS laag C) +
   r394–397 (Tailwind-candidate-valkuil) · §LI022 r381–384 (ast-docstring-strip).
2. **Onder een kop "Bronscans" horen die 7**; er juist NIET onder: leegte-asserts (r446–451),
   complementariteit (r456–458), eigen-data-asserts (r458–463), engine-grens (r464–469 — eigen
   familie "Engine-borging"), en alle Live-DB-/teardown-materie.
3. **De bijt-eis staat onder §LI040-patronen — precies de kop die bij consolidatie in de nieuwe
   "Bronscans"-kop zou opgaan.** Verhuizing 3 wordt dan geen "toevoegen" maar **samenvoegen
   binnen één kop**: de frontend-eisenlijst (1) bijten · (2) geen vals-positieven · (3) geen
   uitzondering komt naast de bestaande bijt-bullet (eis 1, andere formulering) en de
   vals-rood-verfijning (eis 2-familie) te staan. De dubbeling verdwijnt niet door de
   consolidatie; ze wordt er alleen zichtbaar door.

---

## Blok 4 — wat breekt er bij verplaatsen

### 4.1–4.2 Verwijzingen naar tests-koppen, en wat de scan daarvan ziet

**Kop-genoemd → scan-bewaakt (wordt ROOD als de kop verdwijnt):**

| Vindplaats | Verwijst naar | Soort |
|---|---|---|
| modules/…/tests/test_component_open_punten_li047.py:5 | likara-tests §LI039 | **productiecode-comment** |
| modules/…/tests/test_component_bevinding_adr052.py:21 | likara-tests §LI039 | idem |
| modules/…/tests/test_component_norm_adr052.py:25 | likara-tests §LI039 | idem |
| modules/…/tests/test_gebruik_component_breed_adr055.py:8 | likara-tests §LI039 | idem |
| NEXT_SESSION.md:261 (+ spiegels SESSIESTART:343, SESSIE_BRIEFING:301) | tests §LI047 | levende bron + gegenereerd |

De 4 code-verwijzingen wijzen alle naar de **eigen-test-tenant-regel** (LI039 b1 → "Live-DB-
tests"); ze bewegen bewaakt mee. `tests §LI047`: of die rood wordt hangt af van de vormkeuze —
blijft "(LI047)" ergens als vet/kop-tekst staan (zoals "**Bewijs (LI047):**"), dan resolvet het
fragment op dat anker en zwijgt de scan. **Niet vooraf vast te stellen; hangt af van de bouw.**

**Vastleggingen (buiten scanbereik, blijven staan):** Onderzoek-normdrift-V047:91 (§LI039) en
:214 (§LI040) — worden stille geschiedenis; TST-V047:28 (§Offline-grens — kop blijft, breekt niet).

**Skill-zonder-kop → onbewaakt handwerk (beperking 4):** 9 in levende bronnen —
werkprotocol:489 ("likara-tests, LI040" — raakt LI040-kop-opheffing!), ux:338, backend:616,
frontend:472, frontend:1270, domeinmodel:650, domeinmodel:656, OPVOLGPUNTEN:976,
NEXT_SESSION:61 (deel c) — plus **7 code-comments** met "likara-tests" zonder kop
(offline-grens-conventieverwijzingen; kop Offline-grens blijft → geen risico). Netto onbewaakt
te controleren bij consolidatie: vooral **werkprotocol:489** (noemt "LI040" bij naam zonder §).

### 4.3 Bestandsverwijzingen in de skill

**20 unieke bestandsverwijzingen** (`*.py`/`*.js`) in likara-tests — **20 van de 20 bestaan op
disk, 0 ontbrekend** (machinale check). Verplaatsen bínnen dezelfde skill raakt geen enkele
padverwijzing; alleen tekst-knippen zou dat kunnen.

### 4.4 Staat

`git status .claude/skills/likara/likara-tests/` → schoon · branch `master` · HEAD `94c5625` ·
scan **5 passed** op deze tree.

---

## Afwijkingen t.o.v. eerdere rapporten

| Punt | Eerder rapport zei | Nu gemeten |
|---|---|---|
| Checkpoint-borgingsregels: "10 van de **27** `##`-koppen zijn sessiekoppen" | 27 koppen, 10 chronologisch | **25** `##`-koppen; chronologisch **15** (10 LI + 5 V — de V-koppen waren niet meegeteld). Het rapport was dubbel fout; hierbij gecorrigeerd. |
| Checkpoint-skillconsolidatie (blok 3): likara-tests-varianten | r452–455 en r484–486 | bevestigd, regelnummers ongewijzigd |

## Wat je tegenkwam (buiten de vragen)

1. **Consolidatie van likara-tests is een grotere soort beweging dan verhuizing 1**: naast
   verplaatsen-binnen-het-bestand liggen er **6 cross-skill-kandidaten** en minstens **4
   dubbelingen met andere bronnen** (force-recreate ↔ resilience §P10 · baseline-tellingen ↔
   CLAUDE.md §Walkthrough · gate-per-slice ↔ werkprotocol §Gate-discipline · bijt-eis ↔
   frontend-eisenlijst). Ontdubbelen is samenvoegen, en samenvoegen is herformuleren — dat
   vergt per geval een besluit, geen verbatim-knip.
2. **Binnen-bestand-dubbeling:** de allowlist-synctest staat er 2× (V007 b4 en V012 b3, andere
   bewoordingen, zelfde regel).
3. **Dit is de eerste beweging die productiecode raakt**: 4 test-bestanden dragen
   `likara-tests §LI039` in hun docstring/comment. Bewaakt door de scan, maar het betekent een
   commit die buiten `.claude/` en `docs/` komt.
4. **De frontmatter zegt `bijgewerkt: V042`** terwijl de skill LI047-inhoud draagt — zelfde
   metadata-drift als eerder bij werkprotocol/ux/frontend gemeten.
5. **V010-F3 bevat drie alinea's die geen testpatroon zijn** (OPVOLGPUNTEN-tracked-besluit,
   dev-ergonomie, gate-rapport-meting) — chronologie heeft daar materie laten landen die in
   geen tests-kop past, hoe de koppen ook heten.

*Einde meting. Werktree ongewijzigd behalve dit rapport.*
