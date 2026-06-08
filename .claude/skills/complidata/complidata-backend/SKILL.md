---
name: complidata-backend
description: Backend-patronen voor CompliData (FastAPI + SQLAlchemy + Alembic). Beschrijft de werkelijke V001-staat.
stack: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy asyncio, Alembic, PostgreSQL 16
bijgewerkt: V005
---

# CompliData Backend Skill

## App-factory en lifespan

```python
# backend/app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup_config()  # faalt leesbaar bij ontbrekende env-vars
    yield

app = FastAPI(
    title="CompliData API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
```

## Middleware-volgorde (buitenste eerst)

```python
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(OriginCheckMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
```

## Router-registratie

```python
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
# Module-routers hier toevoegen, bijv.:
# app.include_router(bwb_router, prefix="/api/v1")
```

## Database-sessies

| Functie | Gebruik |
|---|---|
| `get_session(tenant_id)` | Tenant-scoped (RLS-context gezet) |
| `get_worker_session(tenant_id)` | Achtergrond-workers (verse sessie per event) |
| `get_platform_db_session()` | Platform-brede queries (geen RLS-context) |

RLS-context — ALTIJD via `set_config`, NOOIT via `SET`:

```python
await session.execute(
    text("SELECT set_config('app.tenant_id', :tid, false)"),
    {"tid": str(tenant_id)},
)
```

## Config-regels

- Pydantic-settings met `extra="ignore"`.
- Verplichte velden zonder default: `database_url`, `database_url_sync`,
  `admin_database_url`, `keycloak_url/realm/client_id/client_secret`,
  `rabbitmq_url` — de app start niet zonder deze (`validate_startup_config`).
- Cookie-naam: `cd_session`.
- Test-mode: `COMPLIDATA_TEST_MODE=true` versoepelt Origin-check en
  rate-limit-key.

## Enum-sync-patroon (Python ↔ PostgreSQL)

LET OP: de generieke `sa.Enum` accepteert **geen** `create_type`-parameter
(dat geeft een TypeError bij import). De enum-DDL wordt volledig door de
Alembic-migratie beheerd; het model verwijst alleen naar de type-naam.

```python
# Python enum
class HostingModel(str, Enum):
    saas = "saas"
    on_premise = "on_premise"

# Model-kolomtype — generieke sa.Enum, GEEN create_type, naam eindigt op _enum
hostingmodel_enum = sa.Enum(HostingModel, name="hostingmodel_enum")

# Gedeeld type-object voor hergebruik over meerdere kolommen
niveau_enum = sa.Enum(NiveauEnum, name="niveau_enum")  # complexiteit + prioriteit
```

In de **migratie** (niet in het model) wordt `postgresql.ENUM(..., create_type=False)`
gebruikt en expliciet `.create(bind, checkfirst=True)` aangeroepen — zie de
complidata-db skill.

## Model-patroon

```python
class Applicatie(Base, TenantMixin, TimestampMixin):
    __tablename__ = "applicatie"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    naam: Mapped[str] = mapped_column(String(255), nullable=False)
    hostingmodel: Mapped[HostingModel] = mapped_column(hostingmodel_enum, nullable=False)
    # Configureerbaar per tenant — bewust vrije tekst, geen hardcoded enum
    eigenaar_organisatie: Mapped[str] = mapped_column(String(120), nullable=False)
```

`Base`, `TenantMixin`, `TimestampMixin` komen uit `app.models.base`.

## Seed-patroon (idempotent)

```python
async def seed_checklist_vragen(session) -> int:
    rows = [{**v, "prioriteit": ChecklistPrioriteit(v["prioriteit"])}
            for v in CHECKLIST_VRAGEN]
    stmt = pg_insert(ChecklistVraag).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["code"])
    await session.execute(stmt)
    await session.commit()
    return len(CHECKLIST_VRAGEN)   # vast 89, ook bij idempotente herhaling
```

Gebruik `len(...)` als returnwaarde — `result.rowcount` zou bij een tweede
(idempotente) run 0 teruggeven.

## Stubs en openstaande ADRs (V001)

| Onderdeel | Status |
|---|---|
| `_load_roles()` | Stub — geeft `[]` — RBAC volgt uit ADR-010 |
| `AuthenticatedUser.roles` | Altijd leeg tot ADR-010 |
| Rate-limit-decorators op endpoints | Nog niet toegepast (limiter wel geregistreerd) |
| Audit/hash-chaining | Niet geïmplementeerd — ADR-006 open |

## Module-entiteit-CRUD — referentie (V003, bewezen over 6 entiteiten)

Applicatie, Datatype, Gebruikersgroep, Koppeling, Checklistscore, Blokkade volgen
één patroon (`modules/bwb_ontvlechting/backend/{schemas,services,routes}/`):

- **Schemas** `Create`/`Update`/`Read`/`Pagina` met `model_config={"extra":"forbid"}`
  op invoer + field validators op elk veld. Server-velden (`id`, `tenant_id`,
  timestamps, `lifecycle_status`) nooit in Create/Update. `Update` = partieel
  (alles optioneel); een `model_validator` verbiedt expliciet `null` op verplichte
  velden. Validatie-helpers hergebruiken uit `schemas/applicatie.py`
  (`_verplichte_tekst`/`_optionele_tekst`).
- **Service** `lijst` (keyset-cursor + optionele filters), `haal_op` (tenant-scoped
  → `NietGevonden`), `maak_aan`, `werk_bij` (`model_dump(exclude_unset=True)`),
  `verwijder` (DB-cascade). Dubbele tenant-bescherming: RLS + expliciete
  `tenant_id`-filter. Pure beslisregels apart houden (DB-vrij testbaar), bv.
  `volgende_status_na_start`, `bepaal_lifecycle`.
- **Routes** dun, onder `vereist_permissie(Entiteit.X, Actie.<L/A/W/V>)`;
  `get_tenant_session`; `{id}` als `uuid.UUID` (ongeldig → 422). Router + handlers
  registreren in `backend/app/main.py` (module-backend op `sys.path`, `parents[2]`;
  in de container `./modules` op `/modules` gemount).

### Ouder-validatie kind-entiteiten (OP-6-uitbreiding)
Bij `maak_aan` van een kind: `await applicatie_service.haal_op(session, tenant_id,
parent_id)` → ouder buiten de tenant ⇒ **404 `NIET_GEVONDEN`** (geen lek, geen 403).
Ouder-FK's zijn immutabel (niet in Update).

### Domeinexceptie + handler-patroon
`modules/.../services/errors.py` definieert exceptie **én** handler (analoog aan
`OnvoldoendeRechten`); registreren in `main.py`. Canoniek
`{"fout":{"code","http_status","bericht"}}`:

| Exceptie | HTTP | Code |
|---|---|---|
| `NietGevonden` | 404 | `NIET_GEVONDEN` |
| `OngeldigeStatusovergang` | 409 | `ONGELDIGE_STATUSOVERGANG` |
| `KoppelingConflict` | 409 | `KOPPELING_CONFLICT` (DB-CHECK-backstop) |
| `ChecklistscoreConflict` | 409 | `CHECKLISTSCORE_BESTAAT_AL` (unieke-index-backstop) |

### Foutformaat-conventie
404/403/409 canoniek; **422 = standaard FastAPI** (`{"detail":[…]}`) — géén
canonieke wrapper (gelijktrekken = OP-7). 401 volgt nog `{"detail":{...}}` (OP-7).
DB-`IntegrityError` in `maak_aan` afvangen → rollback → canonieke domeinfout (nooit
rauwe DB-melding lekken).

### Route-volgorde
Statische subpaden vóór de dynamische `/{id}` (bv. `GET /applicaties/opties`,
`/applicaties/nieuw`) — anders parseert FastAPI "opties" als UUID → 422.

### Opties-endpoint (read-only enum-metadata)
`GET /applicaties/opties`, `vereist_permissie(APPLICATIE, LEZEN)`, pure DB-vrije
helper `enum_opties()` die de waarden uit de single-source-enums teruggeeft
(NL-labels zijn frontend). Vóór `/{id}` declareren.

### Afwijkende CRUD (systeem-afgeleide entiteit)
Blokkade is systeem-afgeleid: **alleen** `GET` (lijst + id) en `PATCH` — geen
`POST`/`DELETE` voor gebruikers (auto-creatie via Checklistscore + DB-cascade);
ongedefinieerde methodes → 405.

## V004-patronen (CD003–CD012, geverifieerd)

- **Per-entiteit opties-endpoints** generaliseren: DB-vrije `enum_opties()`, `/opties`
  **vóór** `/{id}`, alleen voor entiteiten **met** enum-velden (Gebruikersgroep =
  vrije tekst → géén opties). [CD003/CD004]
- **Platform-breed read-only referentie-endpoint zonder tenant-RLS**
  (`GET /checklistvragen`): expliciete code-comment waaróm geen scoping +
  **cross-tenant-test** die de identieke set bevestigt; **één respons** voor vaste
  kleine seeds (geen keyset). [CD004]
- **Canoniek foutcontract (eindstaat, ADR-014)**: 401/403/404/409/429 → `{"fout":{…}}`;
  422 **bewust native** FastAPI `{"detail":[…]}`. Nieuwe domein-/auth-fouten via het
  envelope; nieuwe validatie blijft 422. Auth-excepties (`NietGeauthenticeerd`,
  `TenantMismatch`) als **`HTTPException`-subclass** → offline test-apps zonder handler
  geven 401/403 i.p.v. 500; de echte app levert het envelope via de geregistreerde
  handler. 403 `TENANT_MISMATCH` = auth-grens (token zonder tenant-claim), géén
  ADR-003-404. [CD005/CD009]
- **Systeem-afgeleide status volledig afgeleid (ADR-016)**: de auto-resolutie
  (`checklistscore_service._synchroniseer_blokkade`) buiten de handmatige PATCH-route
  houden; guard op het **handmatige** pad (`blokkade_service.werk_bij`: handmatig
  `opgelost` → 409) zonder het auto-pad te raken. [CD011]

## V005-patronen (CD016/CD020/CD023, geverifieerd)

- **Nieuw endpoint vs. bestaand contract oprekken**: een **bevroren** contract (CD016
  tenant-breed blokkadesoverzicht) krijgt een **apart** endpoint (`GET /blokkades/overzicht`),
  niet het bestaande `GET /blokkades` opgerekt. Statische subpaden (`/overzicht`, `/opties`)
  vóór de dynamische `/{id}`. Een additieve uitbreiding van een bestaand contract (sort/order op
  de per-app lijst, CD020) mag wél: puur **optionele** params, default = exact het oude gedrag
  (geen gedragsbreuk). [CD016/CD020]
- **Gedeelde domein-constante = single source bij de enum in `models.py`**: een constante met
  meerdere consumenten (bv. `ACTIEVE_BLOKKADE_STATUSSEN` = `{open, in_behandeling}`, gebruikt
  door de lifecycle-herberekening, het dashboard én het overzicht-statusfilter) leeft **bij de
  enum**, niet gedupliceerd per service — losse kopieën lopen stil uit elkaar. [CD014/CD016]
- **Sorteer-retrofit per lijst-service (ADR-017/CD020)**: `sort`/`order` als optionele params,
  een `*Sorteerveld`-enum op de route (onbekend veld → 422), een allowlist-kolommen-map + parsers
  in de service, v2n-keyset (zie complidata-db). Levert de service **dicts** (join, bv. koppeling-
  `tegenpartij_naam`) → een apart `*LijstItem`/`*LijstPagina`-schema náást de enkel-item `*Read`.
  White-box cursor-/route-tests bewegen mee met het cursorformaat; een default-pad-assertie is het
  bewijs dat het gedrag niet wijzigde. [CD020]
