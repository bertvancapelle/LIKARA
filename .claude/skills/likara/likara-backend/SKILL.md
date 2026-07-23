---
name: likara-backend
description: Backend-patronen voor LIKARA (FastAPI + SQLAlchemy + Alembic). Beschrijft de werkelijke V001-staat.
stack: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy asyncio, Alembic, PostgreSQL 16
bijgewerkt: V050
---

# LIKARA Backend Skill

## App-factory en lifespan

```python
# backend/app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup_config()  # faalt leesbaar bij ontbrekende env-vars
    yield

app = FastAPI(
    title="LIKARA API",
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

RLS-context — ALTIJD via `set_config`, NOOIT via `SET`, en **transactie-lokaal**
(`true`, niet `false`) via de `after_begin`-hook (norm sinds CD048 — zie likara-db
"V007-patronen"). De eenmalige per-sessie `set_config(..., false)` is **verboden**
(contextloze poolverbinding na `commit`→`refresh`):

```python
# app/core/database.py — per transactie, op sessies met info['rls']=True
await session.execute(
    text("SELECT set_config('app.tenant_id', :tid, true)"),  # true = transactie-lokaal
    {"tid": str(tenant_id)},
)
```

## Config-regels

- Pydantic-settings met `extra="ignore"`.
- Verplichte velden zonder default: `database_url`, `database_url_sync`,
  `admin_database_url`, `keycloak_url/realm/client_id/client_secret`,
  `rabbitmq_url` — de app start niet zonder deze (`validate_startup_config`).
- Cookie-naam: `lk_session`.
- Test-mode: `LIKARA_TEST_MODE=true` versoepelt Origin-check en
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
likara-db skill.

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
| `RegistratieConflict("KOPPELING_BESTAAT")` | 409 | component↔contract = `association` via `component_contract_service` (ADR-023; de oude `Koppeling`-entiteit + `KoppelingConflict` zijn met de cutover vervallen) |
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
  in de service, v2n-keyset (zie likara-db). Levert de service **dicts** (join, bv. koppeling-
  `tegenpartij_naam`) → een apart `*LijstItem`/`*LijstPagina`-schema náást de enkel-item `*Read`.
  White-box cursor-/route-tests bewegen mee met het cursorformaat; een default-pad-assertie is het
  bewijs dat het gedrag niet wijzigde. [CD020]

## V006-patronen (CD025–CD038, ADR-019, geverifieerd)

- **Oordeel ≠ antwoord (drie aparte lagen op `Checklistscore`)**: `score` = gereedheidsoordeel
  ("afgehandeld/voldoet") en **voedt de engine**; `antwoord_waarde` (jsonb, nullable) = het
  configureerbare **feitelijke** antwoord (keuze/getal) en **raakt de engine nooit**; `bevinding`
  blijft vrije toelichting. Een additief nullable veld dat de engine niet leest is byte-identiek
  bewijsbaar (`lifecycle_service` telt rij-bestaan + actieve blokkades; `_synchroniseer_blokkade`
  reageert alleen op `score`). [CD027/CD028]
- **Validatie-tweedeling (ADR-014-lijn)**: *structureel* (envelope-vorm `{optie}`/`{opties}`/
  `{getal≥1}`, geen dubbele) in een Pydantic-validator → **422 native**; *semantisch* (past het type
  bij de vraag, is de optie `actief` en hoort die erbij) in de service tegen de catalogus →
  `OngeldigAntwoord` → **422-envelope**. De envelope-422 is gerechtvaardigd waar Pydantic niet kan
  (DB-lookup nodig); 422 blijft anders native. [CD028]
- **Domeingrens-respecterende validatie op de platform-laag**: `lk_platform` mag tenant-tabellen
  (`checklistscore`) per ADR-012 **niet lezen** → een usage-based "blokkeer als in gebruik"-check
  kan niet cross-domain. Daarom **conservatief blokkeren**: antwoordtype alleen wijzigbaar vanuit
  `geen` (een `geen`-vraag kan per 2B-validatie geen `antwoord_waarde` hebben → bewijsbaar veilig);
  wisselen van een reeds-getypeerde vraag ⇒ `ConfiguratieConflict` (409). [CD031]
- **Platform-config-endpoints**: module-routebestand (`routes/checklistconfig.py`) geguard met
  `vereist_platform_permissie(CHECKLISTCONFIG, …)` op `get_platform_session` (lk_platform) —
  platform-rol-domein, raakt het score-/engine-pad niet (AST-guard in de test). [CD031]
- **Platform-identiteit**: `GET /auth/platform/me` op `get_current_platform_user` (géén `tenant_id`);
  een sessie zonder platform-rol (tenant-account) ⇒ 403 (strikte scheiding). Additief naast
  `/auth/me`. [CD032]

## V007-patronen (CD039–CD056, geverifieerd)

- **Catalogus-familie (gevestigd patroon, 3 instanties)**: checklistconfig / contractconfig /
  componentconfig — één relationele tabel per familie-lid met een **`dimensie`-discriminator**,
  een **stabiele `optie_sleutel`** (lowercase snake_case) + `label`/`volgorde`/`actief`.
  **Soft-deactivate** (`actief=false`), **nooit** hard verwijderen (sleutel blijft resolvebaar
  voor historische waarden); de tenant-leeszijde resolvet óók gedeactiveerde sleutels.
  Dubbele borging tegen muteren: `lk_app` **SELECT-only** + `lk_platform` **zonder DELETE**
  (geen endpoint én geen grant). Eigen `PlatformEntiteit` (beheerder LAW, operator L, geen V).
  **Systeem-sleutels** (bv. `componenttype.applicatie`) zijn niet deactiveerbaar
  (`SYSTEEM_SLEUTEL_BESCHERMD`). Elke nieuwe configureerbare lijst volgt dit patroon. [CD053]
- **Subtype-patroon (ADR-021)**: supertype `component` + subtype `applicatie` als **shared-PK**
  (subtype-PK ís FK naar het supertype, zelfde waarde). Read-only **proxy-properties** op het
  subtype houden bestaande API-responsen byte-compatibel. **Convergente aanmaak**: het
  component-pad met type `applicatie` maakt atomair het subtype met defaults via dezelfde
  service-kern (`maak_applicatie_subtype`) — één implementatie, twee routes. Een **typewijziging**
  van/naar een subtype-dragend type is geweigerd (`SUBTYPE_BESCHERMD`); **delete** van een subtype
  loopt via het subtype-delete-pad (engine-kinderen cascaden; alleen een onderlegger-relatie
  blokkeert). Nieuw checklist-dragend type = nieuw subtype-besluit = eigen ADR. [CD050-CD054]
- **Foutcontract-aanvulling**: `ZELFVERWIJZING` (422), `RELATIE_BESTAAT` (409),
  `SUBTYPE_BESCHERMD` (422), `SYSTEEM_SLEUTEL_BESCHERMD` (422); `GEBRUIK_APPLICATIE_PAD` is
  **vervallen** (convergente aanmaak). Nette app-fout vóór CHECK/UNIQUE blijft de norm.
- **Graaf-leeswerk is altijd cyclus-veilig**: traversals over `component_structuur` gebruiken een
  **visited-set** (B3 staat cycli in de data toe; een traversal mag nooit hangen — de
  belangrijkste eis). **Iteratieve BFS per niveau** is het referentiepatroon: één query per niveau
  op de structuurrelatie, gejoined met `component`; geeft van nature de kortste afstand (`niveau`)
  + het pad. Read-only, geen schrijfpaden, geen engine-koppeling (ADR-021 Fase E). [CD056]

## V009/V010-patronen (ADR-023 Fase A–E + ADR-006, geverifieerd)

- **Facade-over-Relatie-conventie voor een nieuw verband**: een nieuw verband loopt via het **bestaande**
  unified relatiemodel met een **bestaand** relatietype, via een **dunne service-facade** die `Relatie`
  direct bouwt — zoals `component_contract_service` (`association`, rol als kenmerk), `plateau_service`
  (`aggregation`, dispositie + bevestiging als kenmerken) en `deliverable_service` (`realization`-keten
  work_package → deliverable → plateau). De facade valideert het toegestane **`element_type` van bron/
  doel per richting** (realiseerder → gerealiseerde) → **422** bij ongeldig type; dubbel → **409** (de
  `UNIQUE(tenant,bron,doel,relatietype)`). **Geen** nieuw relatietype en **geen** FK-kolommen — TENZIJ
  een **vaste ariteit** dat vereist (gap↔plateau: twee verplichte composiet-FK's op het subtype).
  Relaties worden **expliciet** gelegd (ADR-023 Besluit 8); het systeem leidt nooit relaties af;
  read-traversals zijn afgeleid en **cyclus-veilig** (visited-set).
- **Engine-onaangeroerd (score = de ENIGE lifecycle-driver)**: een nieuwe entiteit/feature die naast de
  engine staat importeert aantoonbaar géén `lifecycle_service`/`herbereken_lifecycle`/`ComponentProfiel`/
  `Blokkade`/`Checklistscore`. Readiness is **puur read-only afgeleid** uit de bestaande lifecycle (geen
  opgeslagen tweede bron); een consistentiecheck is **signalering** (geen tweede engine-poort).
- **Nieuwe tenant-entiteit ⇒ RBAC + audit bewegen mee**: nieuwe `Entiteit`-waarde + `PERMISSIES` in het
  `_INHOUD`-patroon (Viewer L · Medewerker LAW · Beheerder LAWV · Auditor L) — de RBAC-matrix-teltest
  beweegt mee; voeg de tabelnaam toe aan `AUDIT_TENANT_ENTITEITEN` (platform-catalogi →
  `AUDIT_PLATFORM_ENTITEITEN`). Relatie-koppelingen worden al via het `relatie`-spoor geauditeerd.
- **ADR-006 audit-trail**: één centrale `before/after_flush`-capture-hook (ORM-only) → append-only
  `audit_log` (tenant, hash-keten per tenant) resp. `platform_audit_log`; actie `derive` voor
  systeem-afgeleide mutaties (`component_profiel`/`blokkade`). De audit-tabellen zelf staan NIET in de
  capture (via core-INSERT geschreven).

## V010 — Fase F afgerond (F-3 betekenis-marker + signalering, geverifieerd)

- **Consistentie-signalering = read-only afleiding op een markering (F-3 stap 2)**: een afgeleid
  attentie-overzicht (`plaatsingsignaal_service` → `GET /signalen/plaatsing`) leunt op de **betekenis-
  markering**, NIET op een vast vraagnummer/componenttype → **generiek** over componenttypen via een
  INNER join `Component.componenttype == ChecklistVraag.componenttype AND betekenis=<sleutel>` (alleen
  typen mét de markering komen in scope). Score via LEFT JOIN (ongescoord = NULL); `draait_op` =
  **`EXISTS(assignment WHERE doel_id == component)`** (host→gehoste = bron→doel; oriëntatie exact als
  `component_service.structuur_overzicht` — NIET als bron). Twee zachte signalen (positief={ja,deels}):
  *beoordeeld_niet_vastgelegd* (positief & geen draait_op) en *vastgelegd_niet_beoordeeld* (draait_op &
  niet-positief/ongescoord). Blokkeert niets. **Hergebruik `ARCHITECTUUR.LEZEN`** (geen nieuwe entiteit
  voor tenant-breed inzicht). Een begrensd afgeleid rapport mag **bewust niet pagineren** (gemotiveerde
  afwijking van "alle list-endpoints pagineren" — documenteer het in de route).
- **Engine-borging-verfijning bij een afleiding die score leest**: een read-only afleiding **mag**
  `Checklistscore`/`score` **lezen**. De import-afwezigheidstest verbiedt dan alleen
  `lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade` (NIET het
  gelezen `Checklistscore`-model), aangevuld met een **read-only bronscan** (`session.add`/`commit`/
  `flush`/`delete` mogen niet in de service-bron voorkomen). `zet_*`-classificatie (bv. `zet_betekenis`)
  doet **geen** fan-out (`herbereken_*` niet aangeroepen — geborgd via `inspect.getsource`).
- **Platform-catalogus-seed woont in de module-backend**: `seed_*.py` (o.a. `seed_vraagbetekenis`,
  `seed_relatiekenmerk`) staat in `modules/bwb_ontvlechting/backend/services/`, **niet** in
  `backend/services/`. `app/platform_init.py` importeert ze via `_MOD_BACKEND` op `sys.path` en ketent
  ze op één platform-sessie (`bouw_*()` puur/DB-vrij + `seed_*()` idempotent `ON CONFLICT DO NOTHING`).
- **Validator-helpers (signatuur)**: `_optionele_tekst(waarde, maxlen)` neemt **2** args (géén veldnaam);
  `_verplichte_tekst(waarde, veld, maxlen)` neemt **3**. Beide uit `schemas/applicatie.py`.

## V015-patronen (ADR-027 component-klaarverklaring, geverifieerd)

- **Read-only-bij-sluiten (invoer-blokkade ≠ engine-poort).** Een beheerschakel kan een
  invoerpad sluiten zonder de engine te raken. Voorbeeld: `checklist_dragend=false` op een
  componenttype → score-INVOER dicht (422 `CHECKLIST_GESLOTEN` op `maak_aan`/`werk_bij` in
  `checklistscore_service`), maar bestaande scores/lifecycle blijven staan en leesbaar; niets
  wordt gewist of herberekend. Het afdwingpunt zit op het **gebruikers-invoerpad**, NIET op het
  auto-/lifecycle-pad (`_synchroniseer_blokkade`/`herbereken_lifecycle` draaien intern verder).
  Symmetrisch omkeerbaar; geldt voor elk type (geen speciaal geval voor `applicatie`).
  Borg de engine-onaangetastheid met een test die bewijst: geen `add`, geen `herbereken` bij
  de geblokkeerde invoer. Bundel de check in één monkeypatchbare helper zodat offline-mocktests
  hem als no-op kunnen zetten (de invariant krijgt een eigen test).
- **Twee-assen read-only afleiding (geen tweede bron/telling).** Een afgeleid signaal wordt
  berekend uit bestaande bronnen naast elkaar, nooit uit een nieuw opgeslagen veld/telling.
  De `lifecycle_status` encodeert de vragen-volledigheid al: **compleet ⟺ status ∈
  {migratieklaar, geblokkeerd}**. Het afwijkingsgeval ("klaar verklaard terwijl checklist niet
  compleet") is dus een **read-only join** van de klaar-status (`component_klaarverklaring`) met
  `component_profiel.lifecycle_status NOT IN (migratieklaar, geblokkeerd)` — op het dashboard
  (`dashboard_service`, INNER join → kale componenten vallen uit) én als lijstfilter
  (`component_service.lijst`, dezelfde definitie). Spiegelt het per-component-signaal (slice 2,
  `aantalGescoord/aantalVragen`) op landschapsniveau met dezelfde bron.
- **Dashboard = uitbreiding, geen nieuw endpoint.** Tenant-brede tellingen hangen aan
  `dashboard_service.haal_dashboard` + `DashboardRead` (RLS-scoped `func.count()` + join, zoals de
  readiness/blokkade-tellingen). Een nieuwe lijst-filterparam staat in de route-allowlist
  (`Query(..., pattern=...)`) én wordt doorgegeven aan `svc.lijst`; engine ongemoeid.

## V016-patronen (DC015 — actor-identiteit & resolutie)

- **Sub als stabiele actor-sleutel, email als fallback-waarde (beide bewaard).** Waar eerder
  `actor_email or actor_sub` werd gedenormaliseerd: stempel voortaan de stabiele Keycloak-`sub`
  als sleutel **plus** de email als fallback-waarde. Klaarverklaring: aparte kolom
  `verklaard_door_sub` (sleutel) naast `verklaard_door` (= email-fallback, achterwaarts
  compatibel). Plateau-bevestiging (jsonb-kenmerk): `{"sub":…, "email":…}` i.p.v. kale string;
  historische kale strings blijven leesbaar (vorm-detectie). De audit-trail droeg de pure `sub` al.
- **Gedeelde naam-resolutie-helper (`services/actor_resolutie.py`).** `resolveer_naam(session,
  tid, sub, email)` + batch `resolveer_namen(session, tid, {subs})` (N+1-vrij: één query per
  pagina/lijst) + `pak_sub_email(waarde)` (normaliseert dict-vorm vs. historische string). Drie
  gevallen: gekoppelde sub → `persoon.naam` (join `gebruiker_persoon` → Partij); ongekoppelde sub
  (beheerder) → email; historische rij (geen sub) → email. Nooit leeg. Naam wordt read-side als
  **transient attribuut** gezet (`verklaard_door_naam`/`bevestigd_door_naam`/`actor_naam`),
  conform het `eigenaar_organisatie_naam`-patroon. **Engine-import-afwezigheid** geborgd.
- **HET REGISTER-PATROON — elk geval doet een uitspraak, of het bestaat niet (LI048).** De twee
  registers hieronder (`SUB_ENTITEITEN`, `NAAMBRON`) zijn instanties van één regel; die staat hier
  los zodat een derde geval hem niet uit twee voorbeelden hoeft af te leiden.
  Aanleiding: een gat per geval repareren lost het GEVAL op, niet het PATROON — de volgende soort
  komt er weer zonder binnen. Drie eisen, alle drie nodig:
  1. **Elk geval staat erin.** Een toets vergelijkt het register met de gezaghebbende verzameling
     (bijv. `AUDIT_TENANT_ENTITEITEN`) en faalt bij een ontbrekende sleutel.
  2. **Het register verzint niets.** De omgekeerde toets ook — een sleutel die nergens wordt
     aangeroepen suggereert dat er iets geregeld is terwijl niets die tak raakt. Zonder deze
     tweede richting zegt de eerste weinig.
  3. **"Bewust geen" draagt een leesbare reden**, en een toets dwingt dat af. Zonder reden is het
     alsnog een stille terugval, alleen met een vinkje ervoor.
  Bewezen waarde: het register dwingt je per geval een bron aan te wijzen, en dáár sneuvelen
  aannames. In LI048 drie stuks — een veronderstelde `component_id` die er niet was, een
  naamkolom die niet bestond, een labelmap die ontbrak. Zonder register waren ze stil blijven staan.
  ⚠ Neem in het register geen geval op dat **zijn eigen, rijkere weg** heeft (zoals `component` bij
  beide registers hieronder): dan bepalen twee plekken hetzelfde en lopen ze uiteen.

- **`SUB_ENTITEITEN` — de geschiedenis van een ding bevat zijn sub-entiteiten (LI048).** Sta je op
  een partij, dan hoort daarin te staan dat iemand haar een rol gaf of afnam. Dat gebeurde alleen
  als het toevallig in dezelfde handeling zat: 154 van de 229 roltoewijzingen waren onvindbaar —
  hier niet, en nergens anders. De code légde bovendien uit dat het wél gebeurde
  (`routes/objecthistorie.py`: "verschijnt in de historie van de ouder"); dat is waargemaakt in
  plaats van bijgesteld. Vorm gelijk aan `NAAMBRON`: `[(sub_type, veld), …]` of `("geen", reden)`,
  met toetsen in **beide** richtingen plus een reden-eis.
  ⚠ Twee dingen die makkelijk misgaan:
  (1) het object-deel en de sub-takken horen als **één OR** bij elkaar — blijft het object-deel een
  losse AND, dan sluit het de sub-takken juist uit;
  (2) **`oud` én `nieuw` allebei — DE REGEL: een verwijzing zit bij een verwijdering alléén in de
  oude waarde.** Een ingetrokken rol draagt zijn `partij_id` in `oud`, een verbroken koppeling haar
  `bron_id`/`doel_id` idem. Kijk je alleen naar `nieuw`, dan mis je precies de ontkoppelingen en
  intrekkingen — en dat is waar de consultant naar zoekt ("sinds wanneer niet meer"). Geldt voor
  élk `wijziging`-veld waarop gefilterd wordt, niet alleen voor deze twee registers.
  `component` staat er bewust NIET in: dat heeft zijn eigen, rijkere modus (component_id + koppelingen).
  Eén waarheid, twee ingangen — het componentdetail en het auditlog-filter roepen dezelfde tak aan.
- **Het component-filter beantwoordt "wat is er met dit ding gebeurd" (LI048).** Drie takken in
  `_record_filters`: (1) de entiteit ÍS het component — dekt ook de rijen die hun PK met het
  component delen (`element`, `component_profiel`); (2) het component staat als `component_id` in
  de diff (score, blokkade, functievervulling, klaarverklaring, bevinding); (3) **het component is
  BRON of DOEL van een koppeling** (`bron_id`/`doel_id`, elk in `oud` én `nieuw`). Die derde
  ontbrak en dat was een fout, geen afbakening: een `relatie` draagt nooit een `component_id` (0
  van 9.291 regels), dus een ontkoppeling was onvindbaar terwijl de lijst compleet oogde.
  ⚠ `oud` én `nieuw` allebei — zie de regel bij `SUB_ENTITEITEN` hierboven. (Stond hier eerst in
  eigen bewoordingen; twee formuleringen van dezelfde regel lopen uiteen, zoals LI048 met het
  amber-onderscheid liet zien.)
- **`NAAMBRON` — élke geauditeerde soort spreekt uit waar zijn naam vandaan komt (LI048 snede 3).**
  Twee soorten toonden een kale code (`Checklistvraag — e123f280…`, `Componentprofiel — d7f127c0…`).
  Die twee los repareren lost het GEVAL op, niet het PATROON: de volgende soort komt er weer
  naamloos bij. Vandaar een register in `auditlog_service` met vier vormen —
  `("veld", <naam>)` · `("leen_veld", <idveld>)` · `("leen_identiteit",)` · `("geen", <reden>)` —
  en **twee toetsen die beide richtingen afdwingen**: elke soort uit `AUDIT_TENANT_ENTITEITEN`
  staat erin, én het register verzint geen soorten die niet geauditeerd worden. Ook `"geen"` moet
  een leesbare reden dragen; anders is het alsnog een stille terugval, alleen met een vinkje ervoor.
  ⚠ **Meet de bron, neem hem niet aan.** Drie aannames sneuvelden tijdens het bouwen:
  `component_profiel` heeft géén `component_id` in zijn wijziging (0 van 2.085 — het deelt zijn
  PK met `component`, dus de gedeelde sleutel is de route); `gebruikersgroep` heeft helemaal geen
  naamkolom; en `relatietype` heeft geen labelmap. Elk daarvan zou als "werkt niet" zijn geland
  als het register niet dwong om per soort een bron aan te wijzen.
- **De auditregel benoemt zichzelf — de UI leidt niets af (LI048).** Twee regels, beide in
  `auditlog_service`, beide met een eigen helper zodat ze los toetsbaar zijn:
  1. **`_kies_driver`** — de gebeurtenis wordt benoemd door de eerste record die iets INHOUDELIJKS
     zegt, niet door de chronologisch eerste. Bij een element-subtype ontstaat eerst de supertype-rij
     (tabel `element`) die alleen het discriminator-veld draagt; die werd stelselmatig de aanleiding
     en leverde *"Element — 9f1282d4… · Aangemaakt (+1 afgeleid)"* — 14.398 regels. Het criterium is
     **inhoudelijk** (`_is_betekenisloos`: de hele `wijziging` bevat niets dan de discriminator), niet
     op tabelnaam — zo vangt het ook een toekomstig subtype zonder namenlijst. `aantal_afgeleid` telt
     alleen betekenisdragende records, anders droeg élke aanmaak een "(+1 afgeleid)" die nergens
     naar verwees.
  2. **`_toon_naam`** — de naam van TÓÉN wint: eerst de vastgelegde naam uit `wijziging.naam`
     (bij `delete` de `oud`-waarde), dan pas de huidige uit `entiteit_resolutie`. **Bij een
     verwijdering nooit de huidige** — het object hoort niet te bestaan, dus wat daar uitkomt is een
     hergebruikt id of een halfverwijderde rij. Anders verandert de geschiedenis mee bij elke
     hernoeming en klopt het log niet meer met wat er destijds op het scherm stond.
  De SAMENVATTING (`entiteit_type`/`entiteit_naam`/`actie`/`aantal_afgeleid`) staat op
  `AuditGebeurtenis` zelf. De UI mag hem niet opnieuw afleiden: deden beide kanten dat, dan lopen ze
  uiteen zodra één verandert.
  ⚠ **Les uit deze slice:** de delete-tak zat eerst inline in de leslus en een opzettelijke breuk
  erin bleef **groen** — geen enkele toets oefende hem. Een keuze die een eigen regel is, verdient
  een eigen functie, juist om hem te kúnnen breken.
- **"Wie"-filter volgt de WEERGAVE-keten, niet één bron (LI048 — was een fout).** Het audit-filter
  op naam deed alleen `Partij`(persoon) `naam ILIKE %frag%` → `actor_sub IN (subs)`, met een vroege
  `return [], None` bij nul treffers. Maar de kolom *Wie* toont `naam or e-mail`: elke actor zónder
  gekoppelde persoon was dus **onvindbaar terwijl zijn e-mailadres in beeld stond** — geen fout, wel
  "Geen gebeurtenissen gevonden", en de consultant concludeert dat er niets gebeurd is.
  Nu (`auditlog_service._record_filters`): `OR` van (a) naam-treffer via `subs`, en (b)
  `actor_email ILIKE %frag%` **beperkt tot `actor_sub.notin_(gekoppelde_subs)`** — want een rij mét
  koppeling toont de naam, en hem vinden op zijn e-mailadres zou hem vinden op iets wat nergens
  staat. Geen vroege return meer: een fragment zonder naam-treffer kan nog een e-mail-treffer
  hebben; vindt geen van beide iets, dan levert de query zelf leeg op.
  Escaping/tenant-scoping ongewijzigd; AND-combineerbaar met het exacte actor(sub)-filter.
  Search-semantiek (fragment), dus UI = vrije tekst, niet ZoekSelect-pick.
  Helper: `actor_resolutie.gekoppelde_subs(session, tid)`. Regel: likara-ux §P8b.
- **gebruiker_persoon-koppeltabel (Fase 2).** Tenant-scoped, FORCE RLS, `keycloak_sub` UNIQUE +
  `persoon_id` UNIQUE per tenant, composiet-FK `(tenant_id, persoon_id) → element` ON DELETE
  CASCADE, index op `(tenant_id, keycloak_sub)`. De brug login↔persoon; ontstaat bij aanmaak
  (geen handmatige koppelstap). In `AUDIT_TENANT_ENTITEITEN`.
- **Objecthistorie hergebruikt de audit-leeslogica.** `GET /objecthistorie/{type}/{id}` voegt
  geen tweede audit-mechanisme toe: het roept `auditlog_service.lijst` met `component_id` (rijk
  pad incl. afgeleide records via jsonb-diff) voor component/applicatie, of het generieke
  `entiteit_id`-filter voor de overige types (plateau/work_package/deliverable/gap/contract/partij).

## V016-patronen (DC016 — ADR-023a meervoudige flow-koppelingen)

- **Naam-verplicht-per-type via twee lagen.** Een type-afhankelijke verplichting (`naam` verplicht
  voor flow, optioneel voor andere relatietypen) zit in een **Pydantic `model_validator(after)`** op
  `RelatieCreate` (kent het `relatietype`) → 422-native. Bij **update** kent `RelatieUpdate` het
  `relatietype` niet (immutabel, niet in het schema) → de regel staat dáár in de **servicelaag**
  (`werk_bij`, leest `obj.relatietype`) → 422-envelope (`OngeldigeRegistratie`). Patroon: "verplicht
  bij type X" → validator waar het type bekend is, anders servicelaag.
- **Overrulebare dubbel-signalering (geen harde blokkade, geen engine-poort).** Een "dubbel" =
  gelijk op `(bron, doel, naam, protocol, richting, impact_bij_verbreking)`; de vrije `omschrijving`
  telt **niet** mee. In `maak_aan` wordt de treffer **apart** berekend (`_dubbele_flow`, puur lezend),
  zodat hij twee dingen kan voeden: (1) treffer + `negeer_waarschuwing == False` → `409
  KOPPELING_DUBBEL` (via `RegistratieConflict(code, …)` — geen nieuwe exceptieklasse/handler nodig,
  de bestaande mapt generiek op 409 met de raise-site-code); (2) treffer + vlag → aanmaken. De FE
  hersubmit met `negeer_waarschuwing=true` (REST, stateless).
- **Override audit-naspeurbaar via een ECHTE kolom.** De audit-diff (`bouw_wijziging`) capture't
  uitsluitend **mapped columns** → een markering moet een echte kolom zijn (geen jsonb, geen aparte
  audit-gebeurtenis). `relatie.dubbel_waarschuwing_genegeerd boolean NOT NULL default false` (migratie
  0040); alleen **true bij een echte override** (`dubbel and negeer_waarschuwing`), nooit bij elke
  aanmaak-met-vlag. Verschijnt zo vanzelf in de objecthistorie van de koppeling.
- **`RELATIE_BESTAAT` (409) nu alleen non-flow.** De `except IntegrityError`-backstop in `maak_aan`
  vangt na de partiële index (0039) enkel nog de niet-flow-typen (association/assignment/aggregation/
  realization), die uniek per `(bron,doel,type)` blijven. Flow mag meervoud → geen IntegrityError meer.
- **Engine-borging gehandhaafd.** `relatie_service` importeert geen lifecycle/score/blokkade-symbolen
  (offline `hasattr`-test) en flows (incl. override) laten **geen `component_profiel`** ontstaan
  (live-test); de signalering/markering is registratief, geen engine-poort.

## Ongeordend-paar-filter (DC017, relaties API)

Optionele filterparameters `paar_bron_id` + `paar_doel_id` op GET /relaties:
- Beide vereist (anders negeren).
- WHERE `(bron_id=A AND doel_id=B) OR (bron_id=B AND doel_id=A)`.
- Naast bestaande gericht-gerichte `bron_id`/`doel_id` filters.

## Partij aard=burger (DC017, migratie 0041)

- Geen organisatie_id vereist/toegestaan (service-side + CHECK).
- Geen afdeling_id toegestaan.
- Geen leden (geen personen/organisatie_eenheden als kinderen).
- Geen "Hoort bij"-subtitel in PartijDetail.
- In ZoekSelect voor gebruikersgroep-organisatie: aard_in=['organisatie','burger'].

## Canoniek dev-seed scenario (DC017)

Functie `_seed_bvowb_scenario` in dev_seed_testdata.py — leidend scenario:
BvoWB als shared-services dienstenprovider voor Gemeente Tiel, Culemborg, West Betuwe.
Scoringsplan: Zaaksysteem geblokkeerd (89+blokkade), BRP migratieklaar (89),
DMS/Klantportaal/Burgerzaken-suite deels, overige 7 concept.
Gebruiker_persoon: _seed_dev_gebruikers koppelt j.devries/p.vandijk/m.bakker
aan hun BvoWB-persoon via hardcoded KC-subs (deterministisch, geen runtime-KC-dep).

## architectuur_service — partij-naam-fix (LI018)

Partijen joinen als element-zelf via `partij_self = aliased(Partij)`.
De `naam_expr`-coalesce én `_naam()` hebben een partij-tak.
Zonder deze join verschijnen partijen als fallback-naam "partij {uuid[:8]}".

Patroon bij elke nieuwe cross-element projectie die partijen toont:
zorg dat de `partij_self`-join aanwezig is in de query.

## Contracthiërarchie-projecties (LI018)

- `contract_service.deelcontracten` geeft per deelcontract leverancier + gekoppelde
  applicaties terug (één extra association-query, geen N+1).
- `component_contract_service.contracten_van_component` voegt `mantelcontract_id` +
  `mantelcontract_naam` toe via een `mantel = aliased(Contract)` zelf-join (bottom-up
  contractketen App → Contract → Mantelcontract).
- Engine onaangeroerd; afgeleide read-only velden, geen schema/migratie.

## LI020-patronen (kaart-projectie naast de engine)

- **"Bestaat de relatie/het verband al?" → altijd eerst een feitencheck tegen de code, nooit
  gokken.** Verdict in drie buckets: **werkt al / kleine fix / registratie ontbreekt**. Deze
  sessie herhaald bevestigd (samenstelling, organisatiestructuur, eigenaar-organisatie,
  artefact-herkomst): vaak bleek de relatie al geregistreerd (FK-kolom of relatie-rij) en was
  alleen de **kaart-projectie** de ontbrekende schakel — geen schema/registratie nodig.
- **Kaart-projectie is additief & read-only.** Afgeleid uit BESTAANDE relaties/kolommen (geen
  verzonnen relaties, ADR-023 besluit 7); dubbele engine-borging per slice: offline
  import-afwezigheidstest (géén `lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/
  `ComponentProfiel`/`Blokkade`) **én** read-only bronscan (géén `session.add/commit/flush/delete`).
  Voorbeelden LI020: `eigenaar_organisatie_id` als node-attribuut; "gebruikt door organisatie(s)"
  afgeleid uit serving × `gebruikersgroep.organisatie_id` (set + org-loos-flag, één pass, geen
  extra query); organisatiestructuur-edges uit `partij.organisatie_id`/`afdeling_id`.
- **Gaten meeleveren, niet verbergen.** Een afgeleide scope laat de buiten-scope-gevallen
  herkenbaar (None/lege set + expliciete flag), zodat de voorkant ze eerlijk kan tonen.

## LI021-patronen (kaart-schaalarchitectuur — set-scoped, geverifieerd)

- **De Landschapskaart laadt NOOIT de volledige graaf bij schaal.** Bij 300+ componenten is
  "het hele model" een onleesbare plaat + zware render. Architectuur: de kaart laadt
  **set + 1-hop**.
  - `haal_grafdata_op(session, tenant, *, component_ids=None, diepte=1)` — `None` = volledige
    graaf (back-compat/tests), anders **set-scoped** via een discovery-pass
    (`scope_ids = S ∪ 1-hop-buren ∪ org-hiërarchie ∪ eigenaar-orgs`) + een `_sc(col)`-filter
    (`col.in_(scope_ids)` of `true()`) op de tenant-brede where-clausules. Werkte omdat de
    ring-classificatie al `bron/doel ∈ id-set` was (geen transitieve afleiding) → set-scoping
    = enkel een where-filter toevoegen.
  - Endpoint **POST `/landschapskaart/subgraaf`** `{component_ids, diepte}` (POST i.v.m. lange
    id-lijst; GET-volledige-graaf blijft voor back-compat). De **organisatiestructuur-ring
    drijft op de rol-personen ván S**, niet álle (anders lekt de hele hiërarchie binnen).
- **Leverancier-zoek = afgeleide EXISTS-filter op `/componenten`** (geen Component-kolom):
  via roltoewijzing `technisch_beheer`/`contractbeheer`→externe_partij OF
  association→`contract.leverancier_id` — exact de keten van `landschapskaart_service.lev_map`.
  EXISTS-subqueries i.p.v. extra join → keyset-paginering intact.
- **Eigenaar-edge "is eigendom van"** = afgeleide read-only context-projectie uit
  `Component.eigenaar_organisatie_id` (organisatie→component), alleen als de organisatie als
  knoop meekomt (geen dangling endpoint). Context (het `IMPACT_RINGEN`-onderscheid is met de
  Impact-verkenner afgeschaft — de constante bestaat niet meer [LI035]). Dekt het
  "scopebalk-tekent-organisaties"-spoor af (zelfde projectie). Dezelfde dubbele engine-borging
  als LI020 (import-afwezigheid + read-only bronscan) blijft per slice verplicht.

## LI022-patroon (context → onderliggende-componenten read-endpoint)

Een "context → onderliggende componenten"-route (databron voor de Landschapskaart-subgraaf) **deelt
het association-/relatie-where-patroon** met een bestaand endpoint maar levert **bewust een andere
projectie** — geen dubbele logica: deel de WHERE, splits de projectie.
- **`GET /contracten/{id}/componenten` (Fase B slice 2a)** naast `/contracten/{id}/applicaties`: zelfde
  association (`doel=contract`, `bron=component`), maar **zonder ComponentProfiel-join** (die INNER join
  liet kale, profielloze componenten wegvallen → een contract op bv. een database-component was
  onzichtbaar) en **zonder subtype-restrictie**. Het weglaten van de profiel-join **ontkoppelt het
  endpoint juist van de engine** (gewenst). `/applicaties` blijft ongemoeid omdat een consument
  (ContractDetail) op de profiel-/rol-semantiek leunt → **nieuw endpoint, niet verbreden**.
- **Nullable composiet-sleutel als context-identiteit** (bv. `(organisatie_id|null, afdeling|null)` voor
  een gebruiker-context, `/gebruikersgroepen/contexten`): match met **`IS NOT DISTINCT FROM`**
  (`col.is_not_distinct_from(value)`) zodat de lege-deel-casus (org leeg, of afdeling leeg, bv.
  "— / Burgers") **structureel** klopt; een niet-opgegeven query-param = null-match (exacte context). Een
  **begrensde distinct-afgeleide picker-lijst** mag bewust ongepagineerd (consistent met de zuster-
  context-endpoints `/partijen/{id}/componenten`, `/contracten/{id}/componenten`).
- **Engine-borging bij een module die de engine elders wél raakt** (zoals `contract_service` dat
  `ComponentProfiel` voor `applicaties` importeert): borg de nieuwe read-functie met een **function-
  bronscan met `ast`-docstring-strip** (zie likara-tests) i.p.v. de module-brede import-afwezigheidstest.

## V028-patronen (ADR-028 componentclassificatie — filters + guard-les, geverifieerd)

- **Ordinale drempel-filter (BIV "≥"):** vertaal een catalogus-sleutel naar zijn `volgorde` en
  vergelijk "aspect-`volgorde` ≥ drempel" via een **correlated subquery** op de catalogus
  (`select(BivSchaalOptie.volgorde).where(optie_sleutel == kolom).scalar_subquery()`). Een component
  zónder waarde op dat aspect valt vanzelf weg (`NULL ≥ x` = NULL/false — precies de bedoeling:
  "geen waarde voldoet niet aan een drempel"). Ongeldige drempel-sleutel → 422 (valideer tegen de
  actieve catalogus). Multi-select rol-filter = `IN`; onbekende sleutel matcht simpelweg niets.
- **Guard-les (default-pad byte-identiek) — niet-onderhandelbaar:** bouw een filter-clause/-blok
  **uitsluitend achter `if (param)`**. Een **onvoorwaardelijk** opgebouwd filterblok op het
  default-pad (bv. een `dict`/lijst met kolom-attributen als keys, óók als het niet in de query
  landt) kan het **statement-cache-/sorteergedrag** verstoren → intermitterende sorteertest-flakiness
  (deze sessie waargenomen; asc/desc-richting flipte). **Diagnose-recept:** `git stash` de wijziging
  → vergelijk N runs stashed vs. mét-wijziging → guard het blok → hertest tot stabiel. Geen
  filter-constructie zonder actieve filter.
- **Additief opties-endpoint:** breid een bestaand `/opties`-endpoint read-only uit (rol-opties +
  ordinale BIV-niveaus) zonder contractbreuk; response-model met defaults `[]`.

## LI034-patronen — persoonlijke voorkeur-laag (ADR-041)

Service + route voor de per-gebruiker voorkeur-laag (`gebruiker_voorkeur`, zie likara-db). Vindplaats:
`services/voorkeur_service.py`, `routes/voorkeur.py`.
- **Eigen-scope hard via de auth-context:** de `sub` komt **altijd** server-side uit `huidige_actor()`
  (spiegel van `impact_view.maker_sub`), **nooit** uit de payload. Een gebruiker leest/schrijft/
  verwijdert uitsluitend zijn eigen voorkeuren — ook beheerders niet die van een ander (in de service,
  niet alleen via RBAC). `haal_waarde(session, tenant_id, sleutel)` = generieke read-API voor
  consumenten (bv. een frontend-filter of een backend-slot dat een voorkeur wil toepassen).
- **Route** `/voorkeuren`: `GET` (eigen), `PUT /{sleutel}` (upsert = create-or-replace), `DELETE /{sleutel}`
  (idempotent herroep). De `voorkeur_sleutel` reist via het **pad** met een strikte vorm
  (`^[a-z][a-z0-9_]*$`, ≤100) → native 422 vóór de service. Body `{waarde}` met `extra='forbid'` +
  **grootte-guard** (≤4096 bytes, JSON-serialiseerbaar) — de laag is generiek en kent de betekenis van
  een voorkeur niet; semantische validatie hoort bij de consument.
- **Engine onaangeroerd** (schrijvende service, maar geen lifecycle/score/blokkade): import-afwezigheid
  + geen lifecycle-mutatie, zoals gebruikelijk geborgd.

## LI035-patronen (regel-acties-PATCH, afgeleide leeslaag, audit-dekking)

- **PATCH-kenmerk-recept (regel-acties)**: een koppelregel-wijziging raakt alléén de
  KENMERK-velden; de ankers van het feit (bv. component/proces) staan niet in het
  Wijzigen-schema (`extra='forbid'` weert ze — `ProcesvervullingWijzigen`). De update is
  een gewone ORM-update (select → setattr → commit) zodat de centrale audit automatisch
  per-veld oud→nieuw logt; zelfde validaties als bij aanmaken, wijziging-naar-bestaand-
  tripel ⇒ 409 (pre-check; UNIQUE is de backstop). Referentie:
  `procesvervulling_service.werk_bij`.
- **Afgeleide-leeslaag-recept (roll-up/organisatiekijk, ADR-042 slice 5)**: pure
  leesfuncties naast de CRUD (`rollup_voor_proces`, `processen_voor_organisatie`) —
  read-only (geen enkel schrijf-primitief; per-functie bronscan-test), 404 no-leak,
  efficiënt (subboom-BFS + één join-query, geen N+1), en de **tak-groepeersleutel als id**
  (`tak_id`, in één lineaire doorloop uit de BFS-volgorde afgeleid) — nooit op namen
  groeperen, die kunnen botsen. Dubbele engine-borging (import-afwezigheid + live
  geen-mutatie via tellingen vóór/na) blijft per lees-slice verplicht:
  `test_rollup_adr042.py`.
  - **Gate-4-exemplaren onder ditzelfde recept (ADR-043/049/051)** — géén nieuw principe:
    `dekking_overzicht` en `plek_standen` (leesregel **"fijn verdringt grof bij lezen"** — het fijne
    antwoord op een plek verdringt het grove tijdens het LEZEN, nooit weggeschreven), en de
    **gebruikersgroep-keten van brok 1** (component → `serving` → gebruikersgroep ⇒ afgeleide
    `heeft_gebruikersgroep`-vlag, batch, read-only, één pass — geen tweede query-conventie; voedt de
    5e stand `werkvoorraad`). Zelfde dubbele engine-borging per lees-slice: `test_gapsignaal_adr051.py`.
- **Audit-dekking is ORM-dekking (mechanisme-feit)**: de centrale audit hangt op de
  `before_flush`/`after_flush`-Session-hooks (`app/core/audit.py`) en ziet dus ALLEEN
  ORM-mutaties — een `session.execute(insert/update/delete(...))` (core) passeert het
  vangnet onzichtbaar. Dáárom worden mutatiepaden ORM-matig gebouwd (de LI035-band-
  dekking-fix verving een core-upsert door ORM-paden). Entiteiten loggen alleen als ze in
  de allowlists staan (`AUDIT_TENANT_ENTITEITEN`/platform). **Bekend systemisch gat**: een
  delete via het element-supertype (core-delete) audit de subtype-rij niet — gedocumenteerd
  risico, opvolgpunt.

## LI039 — gate 1b: het import-pad als voorbeeld bij bestaande regels

- **Bulk-schrijven ORM-matig (voorbeeld bij §LI035 "Audit-dekking is ORM-dekking"):** de
  referentiemodel-import (`referentiemodel_import_service.voer_uit`) schrijft 297 functies +
  302 plaatsingen via de bestaande facade (`maak_aan`/`plaats` met `via_import=True`) — géén
  SQL-upsert, want die zou de audit-flush-hooks omzeilen. Prijs: per-call-commits (13–25 s
  voor de volle GEMMA-import; bezig-indicatie in de UI, markering bij afbreken — zie
  likara-resilience). Dry-run en uitvoering delen één plan (`_bepaal_plan`, puur; bronscan-
  test bewaakt dat het droge pad geen schrijf-primitief bevat).
- **`via_import`-slotpatroon:** een gebruikers-slot (`MODELINHOUD_BESCHERMD`) met één
  legitiem service-pad eromheen via een keyword-only parameter — het slot zelf blijft
  onverzwakt; de route-laag kan er nooit bij.


## LI040-patronen (filterwaarheid, afwezigheid, weigeren-niet-cascaderen)

- **Eén filterwaarheid.** De lijst en de resultaatregel-telling delen DEZELFDE filterfunctie —
  `component_service._pas_filters_toe`, gebruikt door `lijst` én `tel` — geborgd met een
  bronscan-test (`test_filterbalk_li040.py::test_tel_en_lijst_delen_een_filterwaarheid`). Een
  teller die "3 van 19" zegt terwijl de lijst iets anders toont, liegt zonder dat iemand het
  merkt. Elke clause blijft achter zijn guard (ADR-028-guard-les — default-pad byte-identiek).
- **Filteren op afwezigheid is `.is_(None)`**, nooit een sentinel-waarde: de `*_ontbreekt`-
  boolparams (levensfase/migratiepad/complexiteit/prioriteit/BIV) vertalen "nog niet vastgelegd"
  naar een NULL-filter. Enum-gelijkheidsfilters zijn enum-getypeerde Query-params (native 422
  aan de API-rand).
- **Weigeren, niet cascaderen.** Verwijderen dat verfijnde registratie zou meenemen wordt
  geweigerd met **409 + telling + leesbare reden**: `organisatiegebruik_service.verwijder` ⇒
  `GEBRUIK_HEEFT_VERFIJNING` ("… verdwijnt nooit stil"; de FK is bovendien RESTRICT als
  backstop). De gebruiker ontmantelt bewust, laag voor laag — **veldwerk verdwijnt nooit in één
  klap.** (Zelfde familie als `HEEFT_SUBPAKKETTEN` op work_package.)
