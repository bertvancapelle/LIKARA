---
name: complidata-tests
description: Test-patronen voor LIKARA (pytest unit-tests + TST-validatiecyclus). Beschrijft de werkelijke V001-staat.
stack: pytest, asyncio, unittest.mock, SQLAlchemy models, vitest, @vue/test-utils
bijgewerkt: V010
---

# LIKARA Tests Skill

## conftest.py sys.path-patroon

```python
# modules/bwb_ontvlechting/backend/tests/conftest.py
import pathlib, sys
# tests/ -> backend/ -> bwb_ontvlechting/ -> modules/ -> repo-root = parents[4]
ROOT = pathlib.Path(__file__).resolve().parents[4]
for _p in (ROOT / "backend", ROOT / "modules" / "bwb_ontvlechting" / "backend"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
```

`backend/` levert `app.models.base`; de module-`backend/` levert de
top-level packages `models` en `services`.

## Import-conventie

```python
# Absolute imports — geen relative imports buiten een top-level package
from models.models import Applicatie, HostingModel
from services.seed import seed_checklist_vragen, CHECKLIST_VRAGEN
```

`models/` en `services/` hebben een `__init__.py`; `tests/` en de module-
`backend/` bewust NIET (voorkomt pytest package-mode-conflicten).

## Model-unit-test-patroon (geen DB nodig)

```python
def test_modellen_importeerbaar():
    from models import models as m
    for naam in ["Applicatie", "Datatype", "Gebruikersgroep", "Koppeling",
                 "ChecklistVraag", "Checklistscore", "Blokkade"]:
        assert hasattr(m, naam)

def test_enum_waarden():
    from models import models as m
    assert [e.value for e in m.HostingModel] == [
        "on_premise", "private_cloud", "saas", "iaas", "paas", "hybride", "onbekend"]
```

## Seed-test (asyncio.run — bewust géén pytest-asyncio)

De seed-functie is async maar wordt zonder DB getest via een `AsyncMock`.
`asyncio.run(...)` vermijdt een pytest-asyncio-afhankelijkheid.

```python
import asyncio
from unittest.mock import AsyncMock

def test_seed_codes_uniek_en_89():
    from services.seed import CHECKLIST_VRAGEN
    codes = [v["code"] for v in CHECKLIST_VRAGEN]
    assert len(codes) == 89 and len(set(codes)) == 89

def test_seed_geeft_89_terug():
    session = AsyncMock()
    assert asyncio.run(seed_checklist_vragen(session)) == 89
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()

def test_seed_idempotent():
    session = AsyncMock()
    assert asyncio.run(seed_checklist_vragen(session)) == 89
    assert asyncio.run(seed_checklist_vragen(session)) == 89  # geen fout
```

De seed retourneert `len(CHECKLIST_VRAGEN)` (vast 89), niet `rowcount` —
daarom blijft de assertie ook bij de tweede (idempotente) run kloppen.

## Backend-tests (app-laag) — env vóór import

`app.core.config` instantieert `Settings()` bij import en faalt zonder de
verplichte env-vars. `backend/tests/conftest.py` zet die daarom met
`os.environ.setdefault(...)` (dummy-waarden: `DATABASE_URL`,
`DATABASE_URL_SYNC`, `PLATFORM_DATABASE_URL`, `KEYCLOAK_*`, `RABBITMQ_URL`,
`COMPLIDATA_TEST_MODE=true`) en voegt `backend/` aan `sys.path` toe — vóór enig
`app.*`-import. Keycloak/Redis/DB worden gemockt; geen echte verbinding.

## RBAC-matrixtests (her-codeer de matrix onafhankelijk)

Test de permissietabel door de matrix in de test **onafhankelijk** te
her-coderen en ALLE combinaties te vergelijken — inclusief negatieven:

- Tenant: 10 entiteiten × 4 rollen × 4 acties = **160** combinaties
  (`heeft_permissie`).
- Platform: 3 entiteiten × 2 rollen × 4 acties = **24** combinaties
  (`heeft_platform_permissie`).
- Plus fail-secure (lege/onbekende/verkeerd-gecapitaliseerde rol → False) en de
  **kruis-scheiding** via test-endpoints: tenant-rol op platform-endpoint ⇒ 403,
  platform-rol op tenant-endpoint ⇒ 403, geen sessie ⇒ 401.

Guard-integratie offline: bouw een kleine `FastAPI()`-test-app met de guard als
`Depends`, registreer `OnvoldoendeRechten`-handler, en monkeypatch
`app.middleware.auth.decode_token` om een payload (met/zonder `tenant_id`,
`realm_access.roles`) te injecteren.

## TST-validatiecyclus (4 assen)

Bij elke sessie-afsluiting conform CONTRIBUTING.md sectie 6:

| As | Commando | Verwacht |
|---|---|---|
| 1 — py_compile | `find . -name "*.py" ... \| xargs python3 -m py_compile` | 0 fouten |
| 2 — pytest | `python3 -m pytest modules/.../tests/ -q` | alle tests groen |
| 3 — Alembic | `alembic heads` / `alembic branches` | 1 head, 0 branches |
| 4 — referentie-grep | grep op `backend/ frontend/src/ modules/ docs/adr/` | 0 hits |

Rapport opslaan als `docs/TST-{build_label}-Validatierapport.md`.
Eerst `python3 docs/_generators/sluit_acties.py` draaien (TST-rapport,
skills gevuld, NEXT_SESSION ingevuld, git clean).

## Afsluitprotocol — VOLLEDIG, geen lite-variant (niet-onderhandelbaar)

Het sessie-afsluitprotocol (CLAUDE.md sectie "Sessie-afsluitingspatroon") wordt ALTIJD
volledig doorlopen, in deze vaste volgorde:

1. `sluit_acties.py` — lost alle ❌ op
2. TST-validatiecyclus (CONTRIBUTING.md sectie 6) → `docs/TST-{build_label}-Validatierapport.md`
3. Skill-review — relevante complidata-skills bijwerken (inhoudelijk stap 1: bepaal welke
   patronen vastgelegd moeten worden)
4. NEXT_SESSION.md invullen — top-5 + openstaande punten
5. `gen_build.py` — verhoogt bouwnummer, genereert alle MD-bestanden, **MAAKT DE ZIP**,
   draait de PostgreSQL-dump + iCloud-backup automatisch
6. git commit + git push
7. (backup loopt automatisch in stap 5)
8. claude.ai memory bijwerken

**VERBOD op een "lite-closeout":** een verkorte afsluiting (alleen OPVOLGPUNTEN + V-bump +
changelog handmatig, ZONDER `sluit_acties.py` / TST / `gen_build.py`) is NIET toegestaan
tenzij Bert daar EXPLICIET om vraagt. De ZIP en iCloud-backup zitten in stap 5
(`gen_build.py`) — die stap overslaan betekent geen ZIP en geen backup, en mag dus nooit
stilzwijgend gebeuren.

**Claude bepaalt nooit zelf dat een afsluiting "licht" mag.** Bij twijfel of capaciteitsdruk:
signaleer het aan Bert (conform de ROLVERDELING-bewaking) en laat Bert beslissen — maar draai
standaard het volledige protocol.

## Frontend-poorten (V003)

Naast de 4 backend-assen: **`vite build`** (0 fouten; >500 kB-waarschuwing is geen
fout) en **`vitest run`** (alles groen). Geen eslint/type-check aanwezig.

### Frontend-testpatroon (vitest + @vue/test-utils, happy-dom)
- Module-view-tests staan onder **`frontend/tests/`** (binnen de vitest-root; vitest
  scant niet buiten `frontend/`) en importeren de view via de `@modules`-alias.
- Mock `@/api` met `vi.mock`; mount met `[pinia, [PrimeVue,{unstyled:true}],
  ToastService, router]`. Zet de auth-store-`user` (rollen) voor rol-gating-tests.
- PrimeVue `Dialog` teleporteert naar body → `global.stubs: { teleport: true }`.
- `window.location` via `vi.stubGlobal('location', { assign: vi.fn() })`.
- Cursor-/paginering-assertions via gemockte `lijst`-resoluties (`volgende_cursor`).

## Offline-grens (bewust)

De testsuite draait zonder echte Postgres. Daardoor wordt **DB-afhankelijk gedrag
structureel** geassert i.p.v. live: de `ON DELETE CASCADE` op kind-FK's (assert op
`fk.ondelete=='CASCADE'`) en de lifecycle-keten (pure `bepaal_lifecycle` +
spy op `herbereken_lifecycle`-aanroep). De live keten is in V003 wél éénmalig
empirisch geverifieerd tegen de draaiende stack (zie `docs/LOKAAL-TESTEN.md`).

## V004-patronen (CD003–CD012, geverifieerd)

- **Empirische verificatie tegen de draaiende stack** voor risicovolle aannames die de
  offline-grens niet dekt: `refresh_token` aanwezig? (handmatige PKCE-flow), logout-
  confirm-scherm vs. 302 mét `id_token_hint`, end-session-config. Aanvullend op de
  offline-tests, niet vervangend. [CD007/CD008/CD010]
- **Regressie-borging als vast onderdeel**: 422-native bij foutformaat-werk; auto-pad
  ongemoeid bij guard-werk; cross-tenant-identiek voor platform-data; bestaande
  auth-tests groen na auth-wijzigingen. [CD009/CD011/CD004]
- **Frontend single-flight/async-tests**: `vi.stubGlobal('fetch', …)` met per-URL-state
  (401-dan-200) om refresh-on-401 + retry te bewijzen; `attachTo: document.body` +
  macrotask-defer voor focus-asserts; `:closable="false"` Dialog focust het eerste veld. [CD007/CD003]

## V007-patronen (CD039–CD056, geverifieerd)

- **Tweeluik herbevestigd**: offline **structureel** (mocks/AsyncMock; FK-`ondelete`, schema-
  invarianten, allowlist-synctests, pure beslisregels) + een **eenmalige empirische live-
  verificatie** tegen de geseede `lk_app`-DB (skip-if-onbereikbaar via een verbindings-probe).
  Live-tests **ruimen hun eigen testdata op** (structuurrelaties vóór componenten — anders
  `IN_GEBRUIK`) zodat de baseline ongemoeid blijft. Cyclus-/graaftests bewijzen **terminatie**
  (maak A↔B en assert dat de traversal eindigt + correct telt). [CD052/CD056]
- **Force-recreate-les (niet onderhandelbaar)**: bind-mounts laden **geen** nieuwe code in een
  draaiend proces — herstart de api-container (`docker compose up -d --force-recreate api`) vóór
  élke live-check ná een codewijziging, anders test je de oude code. [CD048-sweep]
- **Baseline-rapportage met benoemde tellingen**: tel categorieën **apart en benoemd**
  (app-koppelingen **vs.** contract-koppelingen; engine apps/blokkades) in een vaste volgorde —
  een kale "register=N" verbergt drift. Rapporteer de baseline vóór én na een walkthrough; check
  expliciet op walkthrough-restdata (bv. `WT-Test%`, tijdelijke catalogus-sleutels). [CD054/CD056]
- **Allowlist-synctest per sorteerbare lijst**: `{e.value for e in <Sorteerveld>} == set(svc._SORTEERBARE_KOLOMMEN)`
  — borgt dat de schema-enum en de service-allowlist 1-op-1 blijven (geen rauwe kolomnaam in
  `ORDER BY`). [CD054]

## V009/V010-patronen (ADR-023 Fase A–E, geverifieerd)

- **Gate-per-schema-slice vs. doorloop-bij-licht-additief.** Een **schema-rakende** bouwslice (nieuwe
  tabel/RLS/migratie/RBAC/audit, of iets dat werkend domein raakt): bouw volledig uit, draai de tests,
  en **STOP met een gate-rapport VÓÓR de commit** — Bert verifieert en geeft pas dan `AKKOORD: commit`;
  zo wordt elke nieuwe entiteit geverifieerd vóór de volgende erop bouwt. Een **doorloop-tot-eindrapport-
  met-afsluitende-commit** geldt **alléén** voor lichte, volledig additieve fasen zonder open knopen
  (alleen read-side/frontend/constants/docs — géén schema). De bouwopdracht-`.md` markeert expliciet
  gate of doorloop. In beide gevallen: bij iets buiten de vastgelegde beslissingen (onvoorziene
  model-/RLS-/semantiekkeuze) STOP + terugkoppelen.
- **Engine-onaangeroerd = dubbele regressie-borging** (machine-geborgd, niet beweerd): (a) **offline
  import-afwezigheidstest** — `import <service> as m; assert not hasattr(m, naam)` voor
  `lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/
  `Checklistscore` (een tekstscan struikelt over docstrings — gebruik import-afwezigheid); (b) **live
  test** — de nieuwe entiteit/koppeling doet géén `component_profiel`/lifecycle-state ontstaan of
  muteren. Readiness wordt altijd puur read-only afgeleid; consistentiechecks zijn signalering.
- **Live-test-teardown structureel** (V009-follow-up a): live element-subtype-tests ruimen hun
  `element`-rijen op via `DELETE FROM element` (cascade subtype + relaties); bij een self-FK (RESTRICT)
  **leaf→root**. Residu-check ná de run = **0**. Harness: `zet_tenant_context` + `zet_audit_context` +
  `session.info['rls']=True` op een verse async-sessie; `skipif` als de lk_app-DB onbereikbaar is
  (offline blijft alles groen via de offline-tests). Importeer `app.core.audit` zodat de capture-hook
  actief is bij een live audit-test.
- **Nieuwe migratie ⇒ dev-DB bijwerken vóór de live-run**: pas de migratie als `lk_admin` toe
  (`DATABASE_URL_SYNC=postgresql://lk_admin:changeme_dev@localhost:5432/complidata python3 -m alembic
  upgrade head`) zodat de skip-if-DB-tests de nieuwe tabellen/kolommen zien; ID ≤32 tekens. Een
  ORM-`SELECT` die een **nog niet gemigreerde** kolom noemt → "column does not exist" + aborted
  transaction in **alle** live-tests van dat bestand (signaal: migratie nog niet toegepast).

## V010 — Fase F afgerond (F-3): signaal-fixtures + werkwijze (geverifieerd)

- **Live signaal-fixture (oriëntatie + scope-via-markering)**: maak componenten **direct via ORM**
  (`Element`→`flush`→subtype) — dit triggert **géén** lifecycle/profiel, dus de plaatsingsvraag is van
  nature **ongescoord** (handig om `vastgelegd_niet_beoordeeld` te bewijzen). Leg een `assignment`
  (`bron=host, doel=app`) → de app telt als `draait_op` (oriëntatie `doel==component`); een app die enkel
  als **bron** in een assignment zit telt **niet** (bewijst de oriëntatie). Een componenttype **zonder**
  de betekenis-markering (bv. `applicatieserver`) valt buiten scope ondanks `draait_op` (bewijst scope-
  via-markering). Teardown: `DELETE FROM element` cascadeert subtypes **én** relaties → residu 0.
- **Pure signaal-matrix offline**: test de afleidings-helper (bv. `_signaal(score, draait_op)`) DB-vrij
  over alle combinaties (positief/niet-positief/ongescoord × draait_op aan/uit), en `lijst` met een
  gemockte `session.execute().all()` die rijen van **meerdere** componenttypen levert (bewijst genericiteit
  + dat alleen gesignaleerde rijen + `reden` terugkomen, en dat de session **niet** muteert).
- **Read-only meting in het gate-rapport (borging)**: bij een afgeleide read-API meet je de **feitelijke
  dev-stand** (welke componenten welk signaal, met waarom) via een klein script onder `_run_rls`, en zet
  je die in het gate-rapport zodat Bert de regel op echte data toetst (F-3: 8× `beoordeeld_niet_vastgelegd`).
- **OPVOLGPUNTEN.md is een NORMAAL TRACKED projectbestand** (besluit DC011 — geverifieerd `git ls-files`,
  niet in `.gitignore`). Behandel het als elk ander tracked bestand. De achterhaalde aanname
  "OPVOLGPUNTEN is untracked tijdens de sessie en landt pas bij close" geldt **niet** meer — niet
  herintroduceren. Bij een feature-commit hoort een OPVOLGPUNTEN-wijziging er niet stil in mee te liften:
  gebruik **gerichte staging** (`git add <expliciete feature-paden>` + `git diff --cached --stat` als
  bewijs); de afsluit-/parkeer-updates van OPVOLGPUNTEN landen in de **sessie-afsluit-commit**.
- **Dev-ergonomie**: `psql` staat **niet** op de host → `docker exec lk-postgres psql -U lk_admin -d
  complidata -At -F'|' -c "…"` voor read-only metingen als lk_admin (ziet álle tenants). `rm` is in de
  sandbox geweigerd → ruim een per ongeluk aangemaakt stray-bestand op met `find <pad> -type f -delete`.
- **Teardown MOET via het element-supertype (les uit V011 — wees-elementen).** Een live-test-teardown
  ruimt een element-subtype (component/contract/…) **uitsluitend** op met `DELETE FROM element WHERE id=…`
  (cascade omlaag: element → subtype → profiel/scores/blokkades + relatie-endpoints). `DELETE FROM
  component` (of een ander subtype) verwijdert **alleen de subtype-rij** en laat de `element`-ouder als
  **wees** achter — onzichtbaar in de meeste tests, maar zichtbaar in de architectuur-view als
  "component <id8>" (de `_naam`-fallback in `architectuur_service`). Symptoom: élke run laat N wezen
  achter (telt op over dagen). **Borging is niet sluitend zonder meting**: tel ná een volledige suite-run
  de wees-elementen — `SELECT count(*) FROM element e WHERE NOT EXISTS (SELECT 1 FROM <subtype> WHERE
  id=e.id)` per subtype — en eis **0**. Het productie-delete-pad (`*_service.verwijder`) verwijdert al
  correct via `element`; dit was puur een test-teardown-fout (4 bestanden, V011). **Grep
  case-insensitive** (`grep -niE "delete[[:space:]]+from[[:space:]]+component"`) — lowercase SQL in
  tests wordt anders gemist.

## V012-patronen (dekking: live-DB + end-to-end, geverifieerd)

- **Live-DB-dekkingstest NAAST de seed-test.** Borg een invariant niet alleen tegen de seed-functie
  maar óók tegen de **draaiende database** (een `@live`/`skipif`-test die de live DB controleert), zodat
  wat via het **beheer** ontstaat ook gedekt is. Voorbeelden (V012, partij-lidmaatschap): live
  CHECK-backstop (een directe insert van persoon/afdeling zónder organisatie ⇒ DB weigert met de
  benoemde constraint), wees-element-telling = 0 per subtype, geen trigger op `partij`.
- **Een service-/SQL-meting bewijst het SCHERM-gedrag NIET — verifieer end-to-end.** De Fase-2-"leden-
  filter"-meting was een directe SQL-query en bleef daardoor blind voor de **api-client** die de filter
  stil dropte (V012-bug). Toets een filter/sortering die het scherm aanstuurt **via de keten** (api-
  client → endpoint), niet alleen op service-niveau. In de frontend-test: assert dat
  `api.<resource>.lijst` mét de filter/sort wordt aangeroepen **én** dat de client die in de query zet.
- **Sorteer-allowlist-synchroon-test breidt mee uit**: voeg je een sorteerveld toe (bv. `aard`), borg
  dan in één test `set(_SORTEERBARE_KOLOMMEN) == {e.value for e in *Sorteerveld} == set(_WAARDE_PARSERS)`
  (enum ⟺ kolommen ⟺ parsers), zodat een half toegevoegde kolom faalt.
