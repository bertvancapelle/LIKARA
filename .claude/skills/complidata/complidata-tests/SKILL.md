---
name: complidata-tests
description: Test-patronen voor CompliData (pytest unit-tests + TST-validatiecyclus). Beschrijft de werkelijke V001-staat.
stack: pytest, asyncio, unittest.mock, SQLAlchemy models, vitest, @vue/test-utils
bijgewerkt: V007
---

# CompliData Tests Skill

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
  verificatie** tegen de geseede `cd_app`-DB (skip-if-onbereikbaar via een verbindings-probe).
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
