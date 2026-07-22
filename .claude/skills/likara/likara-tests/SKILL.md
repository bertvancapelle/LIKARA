---
name: likara-tests
description: Test-patronen voor LIKARA (pytest unit-tests + TST-validatiecyclus). Beschrijft de werkelijke V001-staat.
stack: pytest, asyncio, unittest.mock, SQLAlchemy models, vitest, @vue/test-utils
bijgewerkt: V042
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
`LIKARA_TEST_MODE=true`) en voegt `backend/` aan `sys.path` toe — vóór enig
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
3. Skill-review — relevante likara-skills bijwerken (inhoudelijk stap 1: bepaal welke
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
  **Uitzondering [LI035]:** de AppLayout-tests staan colocated in `frontend/src/layouts/`
  (`AppLayout.test.js` + `AppLayout.gating.test.js`); een nieuwe named route hoort in
  beide testrouters dáár.
- Mock `@/api` met `vi.mock`; mount met `[pinia, [PrimeVue,{unstyled:true}],
  ToastService, router]`. Zet de auth-store-`user` (rollen) voor rol-gating-tests.
- PrimeVue `Dialog` teleporteert naar body → `global.stubs: { teleport: true }`.
- `window.location` via `vi.stubGlobal('location', { assign: vi.fn() })`.
- Cursor-/paginering-assertions via gemockte `lijst`-resoluties (`volgende_cursor`).
- **Toets ook de visuele/interactie-staat, niet alleen de payload (LI030).** Een groene payload-assert
  dekte tweemaal een kapotte UX niet: een onleesbare Opslaan-knop (wit-op-bijna-wit `--lk-color-accent`)
  en een geselecteerd-item-label dat afweek van de lijst-identiteit. Assert daarom óók de knop-stijl-class
  (primaire token, **niet** `accent`) én het geselecteerde-item-label (`veld == lijst`); en bekijk
  UX-rakende schermen vóór commit in de **echte browser** (mocks tonen de styling/selectie-staat niet).
  **Geldt óók voor render/layout (ADR-040):** leeg canvas, samenvallende nodes, stervorm-layout en
  dim-bij-schakelen bleven állemaal groen in de suite en waren alleen in de browser zichtbaar. Elke
  UI-/render-/layout-wijziging wordt **browserverifieerd vóór commit** — tests dekken logica/payload,
  niet het visuele resultaat.
- **Draai de VOLLEDIGE suite (front + back) bij het wijzigen/afschaffen van een gedeeld symbool (ADR-040).**
  Raakt een wijziging een symbool dat backend én frontend delen (bv. een backend-test die de frontend-bron
  op een constante scant), draai **beide** suites — anders blijft een latente rode test onopgemerkt. (Deze
  sessie: een pre-existing rode backend-test op een in de frontend afgeschaft symbool bleef zitten omdat
  bij frontend-stappen alleen de frontend-suite draaide.)
- **Picker-integratietests: param-filterende mock + open-picker-assert (LI032, niet-onderhandelbaar).**
  Een `api.*.lijst`-mock die een **vaste set** teruggeeft en de `aard`/`scope`/`organisatie_id`/`zoek`-params
  **negeert**, laat een picker die de **verkeerde bron** aanroept (afdelingen i.p.v. organisaties, extern
  i.p.v. intern, ongescoopt) nooit falen — de fout komt dan pas in de browser boven (drie keer gebeurd op het
  gebruiker-scherm). Gebruik daarom de gedeelde **`tests/helpers/partijMock.js`** (`partijLijstFake()`): die
  filtert net als de backend. Toets vervolgens door de picker **echt te openen** en te asserten welke
  **entiteitsoort/scope** verschijnt: organisatie-picker → alleen `organisatie`+`intern`; afdeling-picker →
  alleen `organisatie_eenheid` van de gekozen organisatie; na org-wissel verschuift de afdelinglijst mee; en
  bij een remount-gevoelige picker: open twee entiteiten na elkaar en assert dat het label niet **stale**
  blijft (het geval dat de ontbrekende `:key` verraadt). Referentie: `GebruikersbeheerView.test.js`
  (org-picker-bron, org-wissel→afdeling, geen-stale-label).
- **Layout-testnorm: "geen twee nodes op dezelfde positie" (ADR-040).** Borg per layout een test die
  uitsluit dat nodes **samenvallen** — overlappende endpoints betekent dat lijnen niet tekenbaar zijn en
  het canvas leeg oogt. De gemockte cytoscape kent geen posities; test daarom tegen de **echte cytoscape**
  (import het pakket direct in een apart testbestand, draai de laytout-config, assert dat alle posities
  distinct zijn + deterministisch bij herhaling). Referentie: `frontend/tests/kaartLayout.test.js`. De
  fijn-afstemming van leesbaarheid (labelbreedte, ratio) is een **browsercheck-criterium** — headless
  meet geen tekst.
- **Pure-functie-patroon: is de DOM/layout niet unit-testbaar, test dan de BESLISSING (LI044).** jsdom/
  happy-dom doen **geen layout** (`getBoundingClientRect` = 0, geen `innerHeight`-effect), dus is een
  positioneer-/flip-beslissing niet zinvol te asserten via de gerenderde DOM. **Extraheer de beslissing
  als pure functie** en test díé (in-/uitvoer); verifieer de DOM-bedrading in de **browser**. Generieke
  tegenhanger van de "assert op zichtbare tekst"-regel (LI040): waar het beeld niet renderbaar toetsbaar
  is, toets je de logica die het beeld bepaalt. Referentie: `berekenPopoverPositie` (puur, 4 tests) +
  `usePopoverPositie` (bedrading, browsercheck); `frontend/tests/popoverPositie.test.js`.
- **`wrapper.isVisible()`-gotcha (LI044): onbetrouwbaar zonder `attachTo: document.body`.** Zonder
  `attachTo` gaf `isVisible()` een vals-positief op een `v-show`-verborgen paneel; assert dan op het
  style-attribuut (`v-show` schrijft `display: none`) — `expect(el.attributes('style') || '').toContain('display: none')` —
  óf mount met `attachTo: document.body` (zoals de VeldUitleg-tests, die daarom `isVisible()` wél mogen gebruiken).
- **Frontend single-flight/async-tests**: `vi.stubGlobal('fetch', …)` met per-URL-state
  (401-dan-200) om refresh-on-401 + retry te bewijzen; `attachTo: document.body` +
  macrotask-defer voor focus-asserts; `:closable="false"` Dialog focust het eerste veld. [CD007/CD003] (V004, geverifieerd)
- **Een service-/SQL-meting bewijst het SCHERM-gedrag NIET — verifieer end-to-end.** De Fase-2-"leden-
  filter"-meting was een directe SQL-query en bleef daardoor blind voor de **api-client** die de filter
  stil dropte (V012-bug). Toets een filter/sortering die het scherm aanstuurt **via de keten** (api-
  client → endpoint), niet alleen op service-niveau. In de frontend-test: assert dat
  `api.<resource>.lijst` mét de filter/sort wordt aangeroepen **én** dat de client die in de query zet. (V012, geverifieerd)
- **Succes-toast-asserts**: mock de helper-module (`vi.mock('@/meldingen', () => ({
  toastSucces: vi.fn() }))`) en assert `toHaveBeenCalledWith(expect.anything(),
  '<werkwoord>')` in de succes-flow; de vorm zelf (severity/life) borgt
  `tests/meldingen.test.js` één keer centraal. (LI035)
- **vitest draait ALTIJD vanuit `frontend/`** (cwd-valkuil trad in LI035 drie keer op:
  vanaf de repo-root falen de alias-resolves met "Cannot find package '@/store/auth'").
- **Suite-flakiness onder belasting (bekend broos punt, geen code-regressie).** Tests met
  échte `setTimeout`-waits (m.n. de dubbeltap-tests, `_DBLTAP_MS`) kunnen bij rug-aan-rug
  volledige-suite-runs/CPU-verzadiging massaal timeouten (LI036-meting: 1 van ~7 runs
  faalde met 16 timeouts à 12s+; geïsoleerd en in 4 opeenvolgende runs daarna groen).
  Duiding: belastinggevoeligheid van de timer-tests, niet de gewijzigde code. Keert het in
  een rustige omgeving terug → dan wél de gerichte `git stash`-vergelijking (ADR-028-
  diagnose-recept in likara-backend) draaien vóór er iets "gefixt" wordt.
- **Elk UI-pad dat de gebruiker opent (popup/dialoog/overlay) heeft minstens één test die
  hem ÉCHT opent.** Payload-groen zegt niets over een pad dat nooit gemount wordt.
  Referenties: de diagram-popup-tests ("popup bestaat op inhoud, óók zonder uitgang") en de
  inleesdialoog-tests (openen → voorbeeld → bevestigen). ⚠ Tekst-regel — geen bouwsteen;
  discipline per slice. (LI039)
- **Vorm-asserts (aanscherping op de LI030-regel "toets de interactie-staat"):** assert ook
  de KNOPVORM waar die betekenis draagt — doorklik vs. mutatie:
  `expect(w.findComponent('[data-testid=…]').props('outlined')).toBe(true)` (referentie:
  BedrijfsfunctieLijst.test.js:325-329). Een payload-assert ziet niet dat een mutatie-knop
  per ongeluk als doorklik oogt. ⚠ Tekst-regel — per test een keuze. (LI039)
- **Assert op zichtbare TEKST, niet op "rendert"** (aanscherping van de LI030-regel): een test
  die alleen controleert dát een component rendert, vangt een leeg scherm niet — een ontbrekende
  component-`import` rendert in Vue STIL als leeg element en de suite blijft groen. Assert dus de
  letterlijke gebruikerstekst (`expect(...text()).toBe('nog niet vastgelegd')`,
  `not.toContain('Onbekend')`), en bij UI-wijzigingen blijft de browsercheck het sluitpunt. (LI040)


## Offline-grens (bewust)

De testsuite draait zonder echte Postgres. Daardoor wordt **DB-afhankelijk gedrag
structureel** geassert i.p.v. live: de `ON DELETE CASCADE` op kind-FK's (assert op
`fk.ondelete=='CASCADE'`) en de lifecycle-keten (pure `bepaal_lifecycle` +
spy op `herbereken_lifecycle`-aanroep). De live keten is in V003 wél éénmalig
empirisch geverifieerd tegen de draaiende stack (zie `docs/LOKAAL-TESTEN.md`).
- **Empirische verificatie tegen de draaiende stack** voor risicovolle aannames die de
  offline-grens niet dekt: `refresh_token` aanwezig? (handmatige PKCE-flow), logout-
  confirm-scherm vs. 302 mét `id_token_hint`, end-session-config. Aanvullend op de
  offline-tests, niet vervangend. [CD007/CD008/CD010] (V004, geverifieerd)
- **Tweeluik herbevestigd**: offline **structureel** (mocks/AsyncMock; FK-`ondelete`, schema-
  invarianten, allowlist-synctests, pure beslisregels) + een **eenmalige empirische live-
  verificatie** tegen de geseede `lk_app`-DB (skip-if-onbereikbaar via een verbindings-probe).
  Live-tests **ruimen hun eigen testdata op** (structuurrelaties vóór componenten — anders
  `IN_GEBRUIK`) zodat de baseline ongemoeid blijft. Cyclus-/graaftests bewijzen **terminatie**
  (maak A↔B en assert dat de traversal eindigt + correct telt). [CD052/CD056] (V007, geverifieerd)
- **Pure signaal-matrix offline**: test de afleidings-helper (bv. `_signaal(score, draait_op)`) DB-vrij
  over alle combinaties (positief/niet-positief/ongescoord × draait_op aan/uit), en `lijst` met een
  gemockte `session.execute().all()` die rijen van **meerdere** componenttypen levert (bewijst genericiteit
  + dat alleen gesignaleerde rijen + `reden` terugkomen, en dat de session **niet** muteert). (V010 Fase F, geverifieerd)

## Live-DB-tests — fixtures, teardown, drift en eigen test-tenant

- **Force-recreate-les (niet onderhandelbaar)**: bind-mounts laden **geen** nieuwe code in een
  draaiend proces — herstart de api-container (`docker compose up -d --force-recreate api`) vóór
  élke live-check ná een codewijziging, anders test je de oude code. [CD048-sweep] (V007, geverifieerd)
- **Live-test-teardown structureel** (V009-follow-up a): live element-subtype-tests ruimen hun
  `element`-rijen op via `DELETE FROM element` (cascade subtype + relaties); bij een self-FK (RESTRICT)
  **leaf→root**. Residu-check ná de run = **0**. Harness: `zet_tenant_context` + `zet_audit_context` +
  `session.info['rls']=True` op een verse async-sessie; `skipif` als de lk_app-DB onbereikbaar is
  (offline blijft alles groen via de offline-tests). Importeer `app.core.audit` zodat de capture-hook
  actief is bij een live audit-test. (V009/V010, geverifieerd)
- **Nieuwe migratie ⇒ dev-DB bijwerken vóór de live-run**: pas de migratie als `lk_admin` toe
  (`DATABASE_URL_SYNC=postgresql://lk_admin:changeme_dev@localhost:5432/likara python3 -m alembic
  upgrade head`) zodat de skip-if-DB-tests de nieuwe tabellen/kolommen zien; ID ≤32 tekens. Een
  ORM-`SELECT` die een **nog niet gemigreerde** kolom noemt → "column does not exist" + aborted
  transaction in **alle** live-tests van dat bestand (signaal: migratie nog niet toegepast). (V009/V010, geverifieerd)
- **Live signaal-fixture (oriëntatie + scope-via-markering)**: maak componenten **direct via ORM**
  (`Element`→`flush`→subtype) — dit triggert **géén** lifecycle/profiel, dus de plaatsingsvraag is van
  nature **ongescoord** (handig om `vastgelegd_niet_beoordeeld` te bewijzen). Leg een `assignment`
  (`bron=host, doel=app`) → de app telt als `draait_op` (oriëntatie `doel==component`); een app die enkel
  als **bron** in een assignment zit telt **niet** (bewijst de oriëntatie). Een componenttype **zonder**
  de betekenis-markering (bv. `applicatieserver`) valt buiten scope ondanks `draait_op` (bewijst scope-
  via-markering). Teardown: `DELETE FROM element` cascadeert subtypes **én** relaties → residu 0. (V010 Fase F, geverifieerd)
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
  tests wordt anders gemist. (V010 Fase F, geverifieerd)
- **Live-DB-dekkingstest NAAST de seed-test.** Borg een invariant niet alleen tegen de seed-functie
  maar óók tegen de **draaiende database** (een `@live`/`skipif`-test die de live DB controleert), zodat
  wat via het **beheer** ontstaat ook gedekt is. Voorbeelden (V012, partij-lidmaatschap): live
  CHECK-backstop (een directe insert van persoon/afdeling zónder organisatie ⇒ DB weigert met de
  benoemde constraint), wees-element-telling = 0 per subtype, geen trigger op `partij`. (V012, geverifieerd)
- **Live-DB-tests moeten zelf-opruimend zijn via `finally`/teardown, NIET inline.** Een test die de
  rijen pas aan het eind van de happy-flow opruimt, lekt bij een fout (een falende assert vóór dat
  punt) zijn rijen naar de dev-DB. Bewezen mechanisme (LI020): `CD052-db-*`
  (test_component_fase_b_cd052) + `AUDIT-SRV-*` (test_audit_capture_live) ruimden inline op, faalden,
  en stapelden **32 wees-componenten** op → die vervuilden de lijst-/sort-asserts van *ándere* tests →
  die faalden → hun opruiming werd overgeslagen → **vicieuze cirkel** (verklaart "8 pre-existing falers
  + reseed lost het op"). Regel: cleanup van live-DB-fixtures in `finally`/teardown, zodat falen niet
  vervuilt. Patroon-anker: de bestaande `try/finally`-DELETE-blokken in de landschapskaart-/gebruiker-
  livetests (`for eid in ids: DELETE FROM element ...` in `finally`) zijn de juiste vorm.
- **Bij twijfel over vreemde data in de dev-DB: meet de SEED-functie, niet de live-DB-staat.** De
  live-DB kan test-residu bevatten; tel/inspecteer `_seed_bvowb_scenario` (of query mét de
  artefact-prefixen — `CD052-*`/`AUDIT-SRV-*` — uitgesloten) om de échte dekking te beoordelen. (LI020)
- **Na elke `docker compose down -v` moet de dev-seed HANDMATIG.** De init-container draait
  `alembic upgrade head` + `platform_init` (referentiedata), maar **niet** de dev-seed
  (`_seed_bvowb_scenario`). Na een reset dus expliciet:
  `docker compose exec <api-service> python dev_seed_testdata.py` (of lokaal
  `cd backend && python3 dev_seed_testdata.py`). Vergeten = lege scenario-data → veel live-DB-
  tests falen. (Of de seed automatisch mee zou moeten draaien is een open vraag; voor nu:
  handmatige stap.) (LI021)
- **Live-DB-tests kunnen "drift" vertonen t.o.v. de seed.** Symptoom: een test asserteert op
  rijen die de huidige `_seed_bvowb_scenario` níét (meer) maakt (bv. namen uit dode seed-paden
  als `_seed_technische_laag`). De `finally`-hygiëne (LI020) lost het *lekken* op, maar niet de
  *drift*: een falende test die zijn fixtures netjes opruimt blijft falen tot óf de seed de
  verwachte rijen levert óf de test herijkt is op de canonieke seed. Diagnose: vergelijk de
  test-verwachting met wat `main()`/`_seed_bvowb_scenario` daadwerkelijk aanmaakt. (LI021)
- **Nieuwe live-DB-tests altijd self-contained:** maak je eigen `WT-*`-fixtures aan + ruim ze
  in `finally` op, en asserteer alléén op je eigen data — dan ben je immuun voor seed-drift en
  residu. (Let op: `applicatie_service.maak_aan` geeft een **object** terug (`.id`),
  `component_service.maak_aan` een **dict** (`["id"]`).) (LI021)
- **Teardown bij een self-FK-RESTRICT — aanvulling op de bestaande leaf→root-regel.**
  (1) Een via core-SQL geconstrueerde **kring** (bv. de proces-cyclus-test: `UPDATE proces
  SET ouder_id=…` buiten de service-validatie om) is met leaf→root alléén niet te wissen —
  **breek eerst de kring** (`UPDATE … SET ouder_id=NULL`) en wis dán leaf→root. (2) Een
  teardown die halverwege crasht (bv. op de RESTRICT) slaat de resterende deletes over en
  **stapelt residu over runs heen** (LI036: 16 WT-PL-rijen uit 2 gefaalde runs, pas zichtbaar
  in een latere sanity-meting). Borging is niet sluitend zonder meting: check restdata = 0
  ná de run (`SELECT count(*) … WHERE naam LIKE 'WT-%'`), zeker na een gefaalde run.
- **Eigen test-tenant zodra de teardown breder veegt dan de eigen fixtures (besluit Bert,
  LI039).** De bestaande norm blijft: live-tests self-contained (WT-fixtures, opruimen in
  `finally`) — in de dev-tenant is dat prima. Maar zodra een teardown NIET tot eigen rijen
  te beperken is (bv. de import-tests: "ruim álle functies van het model op"), is een
  **eigen test-tenant verplicht** (referentie: `test_referentiemodel_import_gate1b.py:30-33`,
  tenant `9999…`). Reden (les LI039): de import-teardown draaide eerst in de dev-tenant en
  at de geseede GEMMA-boom op. Bewust NIET als absolute "nooit dev-tenant"-regel vastgelegd —
  die zou de gezonde bestaande praktijk tot overtreding verklaren en daarmee genegeerd worden.
- **Complementariteit bij gat-filters**: *gat-set ∪ waarde-sets = totaal* — geen enkel object
  valt buiten beide, en een gezette waarde verlaat het gat. Referenties:
  `test_leeg_vindbaar_li040.py` / `test_geen_oordeel_li040.py` (live). (LI040)
- **Assert alleen op eigen data — óók bij catalogi** (aanscherping van de LI021-regel):
  set-GELIJKHEID over een hele beheerbare catalogus breekt zodra een beheerder legitiem een
  optie toevoegt (dat is een feature, geen regressie) — gebruik een **subset-assert**
  (`{verwachte} <= {gevonden}`) of assert op de eigen WT-fixtures. Exacte gelijkheid alleen op
  code-eigen enums. (LI040)

## Bronscans — bijten, vals alarm en bereik

- **Bewijs dat een test/scan bijt.** Elke bron-scan draagt een ZELFTEST die bij élke run
  opzettelijk foute voorbeelden invoert en verifieert dat ze gevangen worden (referenties:
  veld-scan + detailkop-scan in `check-css-build.mjs`, elk 5/5). Zonder bijt-bewijs is een
  vangnet een aanname. (LI040)
- **Geen vals-positieven.** Een scan die vals alarm slaat wordt genegeerd en is erger dan geen
  scan: scan precies de laag die je bedoelt en strip wat de regel niet draagt (commentaar,
  strings; de frontend-invulling — template-only scannen, comments strippen, quote-bewust
  multi-line tags lezen — staat als toepassing in likara-frontend §LI040-patronen). (LI040)
- **Geen benoemde uitzondering — een uitzondering is een achterdeur (LI047).** Vraagt een geval om
  een uitzondering in de scan, dan is meestal het GEVAL fout, niet de regel; en wie er één opneemt,
  verbreedt de volgende. Moet er tóch iets buiten vallen, laat het dan **afleiden** i.p.v.
  opsommen — tegenvoorbeeld waar dat wél mag: `test_schema_aanroepen_scan.py` slaat aanroepen
  binnen `pytest.raises` over; die geven bewust een ongeldig veld door om te bewijzen dát
  `extra="forbid"` bijt, en dat is een structurele eigenschap, geen lijst. **Een zichtbare
  uitzondering is óók een achterdeur (LI048):** hij doet geen schade, hij legitimeert een VORM —
  het volgende geval dat niet past heeft dan een voorbeeld; zo ontstaan achterdeuren, niet met een
  besluit maar met een precedent. Toets bij een uitzondering niet "richt hij schade aan?" maar
  "welke vorm maak ik navolgbaar?" — en kijk eerst of het geval zelf op te lossen valt.
  (Frontend-casussen — de `GapDetailView`-tegels en `LIJSTKOP_OPENSTAAND`: likara-frontend
  §LI040-patronen.)
- **Het BEREIK van een scan is even belangrijk als zijn regels, en versmalt stiller (LI048).**
  Leid het bereik af uit wat de scan hoort te dekken (de gezaghebbende bron), nooit uit
  bestandsnamen — een naamconventie is geen criterium maar een toevalligheid. Drie eisen naast
  het afleiden zelf: (1) een niet-resolvebaar pad faalt LUID, nooit `continue` — een borging die
  stilletjes smaller wordt dan hij lijkt is gevaarlijker dan geen borging: hij wekt vertrouwen
  dat hij niet waarmaakt; (2) het criterium mag het bestaande bereik niet uitsluiten — bouw een
  ratel, zodat een gedekt geval er nooit ongezien vanaf valt; (3) toets het GETAL in een suite —
  zakt het, dan is dat een bevinding, geen getal dat je bijwerkt. (Toepassing + de drie hard
  geleerde bewijzen: de lijstkop-scan, likara-frontend §LI040-patronen.)
- **Elke gedeelde leesregel/afleiding krijgt een bronscan-test die een tweede implementatie laat
  falen.** Drie sessies raak — LI038 (twee ankers, één model) · LI040 (de "3 van 19"-teller/lijst-
  splitsing) · LI041 (`dekking_overzicht` / `plek_standen`) — dus geen zin meer maar een **norm**:
  de consument **leest** de gedeelde uitkomst en **rekent nooit zelf**; teller en lijst delen één
  filterwaarheid. Vorm: een backend-bronscan die de verboden implementatie-interne symbolen in de
  consumentbron uitsluit (de Vue-view mag `dekking_overzicht`/`plek_standen` niet nabouwen), plus
  een frontend-test die bewijst dat teller en getoonde lijst uit dezelfde bron komen. Precedenten:
  `test_leesregel_leeft_een_keer_en_boom_rekent_niet_zelf` (functievervulling_adr049) ·
  `test_standen_afleiding_niet_gedupliceerd_in_de_vue` (gapsignaal_adr051) · de frontend-`it()`
  *"teller en lijst delen één filterwaarheid"* (WerkvoorraadPlekView.test.js). ⚠ Verfijn de scan
  zoals in LI041: verbied alléén de implementatie-interne symbolen (`_dichtstbijzijnde_dragers`,
  `fijn_per_plek`, …), niet begrippen die legitiem in een comment/label mogen staan (`plek_standen`
  als woord) — anders wordt de scan vals-rood.
- **Rollengrens-borging is een classificatie-bronscan, geen per-route-assert** (ADR-050). Test dat
  élke content-entiteit in precies één categorie valt (registratie-feit **xor** landschapsobject)
  en dat haar primaire DELETE guardt op de actie die `verwijder_actie()` teruggeeft — faalt zodra
  een nieuw feit niet geclassificeerd is of op de verkeerde actie guardt. Precedenten:
  `test_classificatie_disjunct_en_verwijder_actie` · `test_primaire_delete_erft_categorie_en_bijt`
  (test_rollengrens_adr050). Zo kan "zeven feiten vergaten de regel" niet opnieuw ontstaan.
- **Function-bronscan met `ast`-docstring-strip** voor engine-/read-only-borging van een nieuwe
  service-functie in een module die de engine elders wél raakt: een platte tekstscan struikelt over een
  docstring die een verboden symbool ter uitleg noemt → strip de docstring via `ast` vóór de scan. (LI022, geverifieerd)
- **Class-asserts bewijzen geen rendering.** vitest assert klasse-STRINGS; of een klasse
  daadwerkelijk stijl oplevert bewijst alléén de dist-CSS. Laag C
  (`frontend/scripts/check-css-build.mjs`) checkt daarom (1) kritische klassen in de
  gebouwde CSS en (2) élke fallback-loze `var(--lk-…)`-verwijzing tegen de
  token-definities (de MeldingBanner-les: token `--lk-color-warn` bestond niet — heette
  `-warning` — en de banner rendeerde stil zonder tint). (LI035)
- **Tailwind-candidate-valkuil in de check zelf.** Alles onder `frontend/` (ook
  testbestanden en het check-script) wordt door Tailwind gescand; een aaneengesloten
  class-literal in een comment seedt de klasse en maakt de check vals-groen. Bouw te
  matchen tokens uit fragmenten (gesplitste `]`), behalve voor handgeschreven
  main.css-klassen (die kan Tailwind nooit zelf genereren). (LI035)

## Engine-borging — import-afwezigheid en de omgekeerde woord-scan

- **Engine-onaangeroerd = dubbele regressie-borging** (machine-geborgd, niet beweerd): (a) **offline
  import-afwezigheidstest** — `import <service> as m; assert not hasattr(m, naam)` voor
  `lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/
  `Checklistscore` (een tekstscan struikelt over docstrings — gebruik import-afwezigheid); (b) **live
  test** — de nieuwe entiteit/koppeling doet géén `component_profiel`/lifecycle-state ontstaan of
  muteren. Readiness wordt altijd puur read-only afgeleid; consistentiechecks zijn signalering. (V009/V010, geverifieerd)
- **Engine-grens dubbel borgen — nu óók de omgekeerde richting**: naast de bestaande
  import-afwezigheid ("de nieuwe service importeert de engine niet") de **woord-scan op de
  engine-bronnen zelf** — `lifecycle_service`/`checklistscore_service`/`blokkade_service`
  bevatten het nieuwe registratieve veld als wóórd niet (`levensfase`, `migratiepad`,
  `complexiteit`, `prioriteit`) — plus live: een edit muteert lifecycle niet, 0 scores,
  0 blokkades. Referenties: `test_levensfase_adr046.py`, `test_geen_oordeel_li040.py`. (LI040)

## Allowlist-synctests

- **Allowlist-synctest per sorteerbare lijst**: borg in één test
  `set(_SORTEERBARE_KOLOMMEN) == {e.value for e in *Sorteerveld} == set(_WAARDE_PARSERS)`
  (enum ⟺ kolommen ⟺ parsers) — zo blijven de schema-enum en de service-allowlist 1-op-1
  (geen rauwe kolomnaam in `ORDER BY`; de tweedelige vorm `{e.value for e in <Sorteerveld>}
  == set(svc._SORTEERBARE_KOLOMMEN)` was daar de grond van), en een half toegevoegde kolom
  faalt zodra er een sorteerveld bij komt (bv. `aard`). [CD054] (V007 + V012, geverifieerd)

## Regressie-borging

- **Regressie-borging als vast onderdeel**: 422-native bij foutformaat-werk; auto-pad
  ongemoeid bij guard-werk; cross-tenant-identiek voor platform-data; bestaande
  auth-tests groen na auth-wijzigingen. [CD009/CD011/CD004] (V004, geverifieerd)

## Testmigratie bij een laadpad-omslag — strategie A (LI022, geverifieerd)

- **Wijzigt een view zijn laadgedrag fundamenteel** (bv. van "laad altijd alles" naar set-gestuurd via
  een nieuw endpoint), **herschrijf de bestaande gedragstests dan niet** — richt ze op de **modus waar
  dat gedrag aantoonbaar nog leeft**. Recept (Landschapskaart Fase B slice 0+1):
  - een gedeelde `mountView`-helper die ná mount de **"volledige" modus** laadt, zodat de bestaande
    full-graph-asserties (filters/scope/ego/impact/swimlane/history/ringen) geldig blijven;
  - **één setter voedt beide laadpaden**: de oude full-load én de nieuwe subgraaf-mock leveren
    **dezelfde data**, zodat een set opbouwen de graaf niet leegt onder de bestaande tests;
  - **nieuwe bedrading-tests apart** (eigen `describe`): dekken alléén het nieuwe laad-/reset-/
    teller-gedrag (lege set = geen fetch + placeholder; set → subgraaf; mutatie → herfetch hele set;
    hele-landschap → full-graph + set geleegd; begin-opnieuw → reset).
- **Nagel onbesliste semantiek niet vast in tests.** Wat nog niet ontworpen is (bv. wat
  filter/scope/impact/swimlane betekenen op een opgebouwde subgraaf) hoort **niet** in een assertie —
  dek alleen de bedrading; de inhoudelijke semantiek volgt in een eigen ontwerpslice. Een test die een
  nog-open ontwerpkeuze fixeert, blokkeert dat ontwerp later.

## Groen bewijst geen schone bron — bronbestand-hygiëne (LI046)

Een tekstbronbestand (.js/.py/.vue/.md) moet **schone UTF-8** zijn. Groene tests bewijzen dat **niet**:
Node/vitest parseren een `.js` mét **null-bytes** (`\0`) probleemloos, dus de suite bleef groen —
maar git zag `kaartBanen.js` als **binair** (geen diffs, fragiel) en `file` meldde "data". Oorzaak deze
sessie: Map-key-separators werden per ongeluk `\0` i.p.v. een spatie. **Controleer vóór commit** met
`file <bestand>` (moet "… text", niet "data") en/of `git diff --cached --stat` (een tekstbestand dat als
`Bin 0 -> N bytes` verschijnt is verdacht); lokaliseer met `python3 -c "print(open(f,'rb').read().count(b'\\x00'))"`.
Een unieke sleutel mag elke ASCII-separator gebruiken die niet in de waarden voorkomt (UUIDs bevatten
geen spatie) — kies bewust, geen onzichtbare control-byte.

⚠ **Deze regel faalde op zijn eigen bestand (ontdekt LI048).** Bij het opschrijven van bovenstaande
les in LI047 zijn de twee null-bytes **letterlijk als voorbeeld in de tekst gezet** — waardoor
`likara-tests/SKILL.md` zélf besmet raakte en `file` er "data" van maakte. Twee dingen om te onthouden:

1. **Schrijf een control-byte nooit als zichzelf, maar als escape** (`\0`, `\x00`). Een voorbeeld van
   iets onzichtbaars mag het bestand niet onzichtbaar besmetten.
2. **De schade is subtieler dan "git ziet het als binair".** Git keek hier weg omdat de bytes voorbij
   de eerste 8 kB stonden, dus de diffs bleven werken en niets viel op. Maar **`grep` slaat het
   bestand stil over** — geen foutmelding, gewoon nul treffers. Zo werd de skill onvindbaar voor de
   sessiestart-zoekopdrachten waar hij juist voor bestaat: in LI048 gaven vier greps op rij niets
   terug terwijl de gezochte tekst er wél stond, en pas `grep -a` bracht hem boven water.
   **Vuistregel:** krijg je nul treffers op een bestand waarvan je wéét dat de tekst er staat, toets
   dan `file <bestand>` vóór je je zoekterm gaat betwijfelen.

**De algemene regel: een regel die een valkuil beschrijft is zelf niet immuun voor die valkuil.** De null-byte-les werd besmet door zijn eigen voorbeeld; hij is niet het enige geval waarin
dat kán — elke instructie over een gevaarlijk teken, een breed matchend patroon of een fragiel
bestandsformaat loopt hetzelfde risico zodra hij een voorbeeld toont. **Pas een controle-instructie
daarom meteen toe op het bestand waarin je hem opschrijft**, vóór je verdergaat. Dat kost één
commando en vangt precies de fout die je zojuist beschreef.

## Mock-reset wist aanroepen, niet implementaties (LI047)

`vi.clearAllMocks()` in een `beforeEach` reset `mock.calls`, maar **laat een via `mockResolvedValue`
gezette implementatie staan**. Een respons die één toets instelt, lekt daardoor door naar élke
volgende toets in dat bestand — en faalt dáár, op een assertie die niets met de oorzaak te maken
heeft.

**Bewijs (LI047):** een nieuwe toets zette `openPunten` op drie punten; een bestaande toets die
`[data-norm-lat]`-elementen telt sloeg om van 2 naar 3. De rode test wees de verkeerde kant op — hij
leek een bouwfout te melden, en was testvervuiling.

**Regel:** zet in `beforeEach` élke mock die een toets kán herconfigureren **expliciet terug** op zijn
standaardrespons (naast `clearAllMocks`), of gebruik `mockResolvedValueOnce` waar het om één aanroep
gaat. Referentie: `ComponentDetail.test.js` — de `componentNormen.openPunten`-mock wordt per toets
teruggezet, met de reden erbij in een comment.

## Cross-skill-kandidaten (LI049 — horen inhoudelijk elders; hier geparkeerd tot eigen besluit)

- **Baseline-rapportage bij een walkthrough:** voluit in CLAUDE.md §Walkthrough-protocol
  (benoemde tellingen vóór én ná, vaste volgorde — een kale "register=N" verbergt drift;
  restdata-check o.a. `WT-Test%`, tijdelijke catalogus-sleutels). [CD054/CD056] (V007, geverifieerd)
- **Gate-per-schema-slice vs. doorloop:** de werkwijze staat voluit in likara-werkprotocol
  §Gate-discipline; stoppen bij een onvoorziene model-/RLS-/semantiekkeuze: likara-werkprotocol
  §CC-autonomiescope. (V009/V010, geverifieerd)
- **Read-only meting in het gate-rapport (borging)**: bij een afgeleide read-API meet je de **feitelijke
  dev-stand** (welke componenten welk signaal, met waarom) via een klein script onder `_run_rls`, en zet
  je die in het gate-rapport zodat Bert de regel op echte data toetst (F-3: 8× `beoordeeld_niet_vastgelegd`). (V010 Fase F, geverifieerd)
- **OPVOLGPUNTEN.md is een NORMAAL TRACKED projectbestand** (besluit DC011 — geverifieerd `git ls-files`,
  niet in `.gitignore`). Behandel het als elk ander tracked bestand. De achterhaalde aanname
  "OPVOLGPUNTEN is untracked tijdens de sessie en landt pas bij close" geldt **niet** meer — niet
  herintroduceren. Bij een feature-commit hoort een OPVOLGPUNTEN-wijziging er niet stil in mee te liften:
  gebruik **gerichte staging** (`git add <expliciete feature-paden>` + `git diff --cached --stat` als
  bewijs); de afsluit-/parkeer-updates van OPVOLGPUNTEN landen in de **sessie-afsluit-commit**. (V010 Fase F, geverifieerd)
- **Dev-ergonomie**: `psql` staat **niet** op de host → `docker exec lk-postgres psql -U lk_admin -d
  likara -At -F'|' -c "…"` voor read-only metingen als lk_admin (ziet álle tenants). `rm` is in de
  sandbox geweigerd → ruim een per ongeluk aangemaakt stray-bestand op met `find <pad> -type f -delete`. (V010 Fase F, geverifieerd)
