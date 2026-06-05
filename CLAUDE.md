## Startregel (VERPLICHT — altijd naleven)

CC begint NOOIT op basis van context-inferentie of aankondigingen
in claude.ai zoals "plak in CC" of "geef aan CC".

CC start uitsluitend na een expliciete trigger van Bert in de vorm:

    START: [naam van de instructie]

Zonder deze trigger: niets doen, wachten.

---

## Interactieregel (VERPLICHT — niet-onderhandelbaar)

Geldt voor zowel CC als claude.ai, in elke sessie:

- Stel vragen ALTIJD één voor één. Stel nooit meerdere vragen tegelijk.
  Wacht op het antwoord van Bert voordat je een volgende vraag stelt.
- Geef adviezen ALTIJD één voor één. Geef nooit meerdere adviezen tegelijk.
  Wacht op de reactie van Bert voordat je een volgend advies geeft.

Deze regel is niet-onderhandelbaar en overschrijft elke neiging om
meerdere vragen of adviezen te bundelen.

---

## Opdrachtformaat CC-opdrachten (VERPLICHT — standaardwerkwijze)

claude.ai levert elke CC-opdracht ALTIJD aan als een .md-bestand
(downloadbaar), nooit als een los codeblok in de chat. Bert gebruikt dat
.md-bestand in CC. Deze afspraak geldt in elke sessie.

---

## Sessiestart — verplicht, geen uitzonderingen

### Bootstrap-modus (uitsluitend sessie 1 — extractie)

Als `.claude/skills/complidata/` nog NIET bestaat: dit is sessie 1.
Lees dan uitsluitend:

Read CONTRIBUTING.md (indien aanwezig, anders overslaan)
Read .claude/skills/engineering-team/senior-architect/SKILL.md
Read .claude/skills/engineering-team/senior-backend/SKILL.md
Read .claude/skills/engineering-team/senior-frontend/SKILL.md
Read .claude/skills/engineering-team/senior-qa/SKILL.md
Read .claude/skills/engineering-team/tdd-guide/SKILL.md
Read .claude/skills/engineering-team/senior-security/SKILL.md
Read .claude/skills/engineering-team/senior-secops/SKILL.md
Read .claude/skills/engineering-team/senior-devops/SKILL.md
Read .claude/skills/engineering-team/code-reviewer/SKILL.md
Read .claude/skills/engineering-advanced/database-designer/SKILL.md
Read .claude/skills/security/security-overview/SKILL.md
Read .claude/skills/security/security-testing/SKILL.md
Read .claude/skills/security/input-validation/SKILL.md

Bevestig: "Bootstrap-modus actief — [N] engineering/security skills geladen."
Daarna: wacht op START: [naam] van Bert.

### Normale modus (sessie 2 en verder)

Lees bij elke nieuwe sessie onderstaande skills in hun geheel voordat je iets anders doet.

Read CONTRIBUTING.md
Read .claude/skills/complidata/complidata-backend/SKILL.md
Read .claude/skills/complidata/complidata-db/SKILL.md
Read .claude/skills/complidata/complidata-frontend/SKILL.md
Read .claude/skills/complidata/complidata-security/SKILL.md
Read .claude/skills/complidata/complidata-tests/SKILL.md
Read .claude/skills/complidata/complidata-resilience/SKILL.md
Read .claude/skills/engineering-team/senior-architect/SKILL.md
Read .claude/skills/engineering-team/senior-backend/SKILL.md
Read .claude/skills/engineering-team/senior-frontend/SKILL.md
Read .claude/skills/engineering-team/senior-qa/SKILL.md
Read .claude/skills/engineering-team/tdd-guide/SKILL.md
Read .claude/skills/engineering-team/senior-security/SKILL.md
Read .claude/skills/engineering-team/senior-secops/SKILL.md
Read .claude/skills/engineering-team/senior-devops/SKILL.md
Read .claude/skills/engineering-team/code-reviewer/SKILL.md
Read .claude/skills/engineering-advanced/database-designer/SKILL.md
Read .claude/skills/security/security-overview/SKILL.md
Read .claude/skills/security/security-testing/SKILL.md
Read .claude/skills/security/input-validation/SKILL.md

Bevestig na het inlezen: "Sessiestart compleet — [N] skills geladen."
Daarna: wacht op START: [naam] van Bert.

---

# CLAUDE.md — CompliData Platform

**CompliData** is een modulair, multi-tenant databeheer- en migratieplatform voor
Nederlandse overheidsorganisaties. Het platform ondersteunt gecontroleerde data-inventarisatie,
migratieanalyse en overdrachtsvoorbereiding — te beginnen met de BWB-ontvlechtingsmodule.

- **Eigenaar**: G. van Capelle Beheer B.V. — CompliData is een product van G. van Capelle Beheer B.V.
- **Operator**: configureerbaar per deployment — nooit hardcoded in code
- **Domain**: nader te bepalen
- **Huidige build**: V001 (Juni 2026)
- **Modules**: 1 (BWB Data-ontvlechting)

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy + Alembic |
| Database | PostgreSQL 16 with Row Level Security (RLS) |
| Frontend | Vue.js 3, Vite, Vue Router, Pinia, PrimeVue (Unstyled), Tailwind CSS |
| IAM | Keycloak 24.x (TOTP/MFA, PKCE, JWT httpOnly cookies) |
| Messaging | RabbitMQ 3.13 |
| Blob Store | MinIO (S3-compatible, bucket-per-tenant) |
| Cache | Redis 7 |
| Hosting | VPS — EU-jurisdictie |

**Niet aanwezig in CompliData V001 (bewuste keuze):**
- Flowable BPMN-engine — geen compliance-workflows vereist in V001
- eXo Digital Workplace — niet van toepassing
- ClamAV — optioneel, toe te voegen bij bestandsupload-functionaliteit
- OnlyOffice — optioneel, toe te voegen bij documentviewer-functionaliteit

---

## Structuur

```
backend/
  app/
    api/v1/          — FastAPI route handlers (auth, modules)
    core/            — config, database, keycloak, messaging
    models/          — SQLAlchemy models
    schemas/         — Pydantic v2 request/response models
    services/        — business logic per module
    middleware/      — auth (JWT httpOnly cookie), tenant (RLS context)
    workers/         — RabbitMQ consumers (indien van toepassing)
  alembic/versions/  — database migrations
  tests/
frontend/
  src/
    views/           — per module georganiseerd
    router/          — Vue Router config
    store/           — Pinia stores
    api.js           — API client (fetch, credentials: include)
modules/
  bwb_ontvlechting/  — BWB data-ontvlechting module (eerste module)
    backend/         — module-specifieke routes, models, services
    frontend/        — module-specifieke views, stores
    migrations/      — module-specifieke Alembic migraties
init-db/             — PostgreSQL init scripts (extensions, cd_app role)
keycloak/realms/     — Keycloak realm JSON (complidata realm)
rabbitmq/            — RabbitMQ config
docs/
  adr/               — Architecture Decision Records
.claude/
  skills/
    complidata/      — platform-specifieke skills (aangemaakt in sessie 1)
    engineering-team/     — platform engineering skills
    engineering-advanced/ — platform engineering skills (advanced)
    security/             — platform security skills
```

---

## Commands

```bash
# Docker stack
docker compose -f docker-compose.yml up -d

# Backend (development)
cd backend && python3 -m uvicorn app.main:app --port 8000 --reload

# Backend (test mode — auth stub, auto-seed)
cd backend && COMPLIDATA_TEST_MODE=true python3 -m uvicorn app.main:app --port 8000

# Frontend
cd frontend && npm run dev     # port 3000, proxy to :8000

# Database migrations
cd backend && python3 -m alembic upgrade head

# Smoke test
bash smoke_test.sh

# PostgreSQL backup
docker exec cd-postgres pg_dump -U cd_admin complidata > ~/complidata/backups/complidata_$(date +%Y%m%d_%H%M).sql
```

---

## Verificatie

Na elke wijziging, verificeer in deze volgorde:
1. `bash smoke_test.sh` — 0 failures
2. API health: `curl http://localhost:8000/api/v1/health` → `{"status":"ok","db":"ok"}`
3. RLS isolatie: geen cross-tenant data toegang mogelijk
4. Geen hardcoded tenant-IDs, platform-namen of operator-referenties in code

---

## Architectuurprincipes (niet-onderhandelbaar)

### Security
- Zero Trust architectuur — elke request geverifieerd
- **httpOnly cookies only** — localStorage is VERBODEN voor tokens
- Cookie-attributen: `HttpOnly`, `Secure`, `SameSite=Strict`
- Access token: max 15 minuten. Refresh token: max 8 uur
- Pessimistic locking voor concurrente operaties
- Hash-chained audit trail — append-only, nooit verwijderen
- MFA verplicht in productie — NCSC-richtlijnen (niet NIST)
- mTLS voor service-to-service communicatie

### Multi-tenancy
- PostgreSQL Row Level Security enforceert tenant-isolatie op databaseniveau
- `FORCE ROW LEVEL SECURITY` op alle tenant-scoped tabellen
- Applicatie verbindt als `cd_app` (non-superuser) — nooit `cd_admin` in app-code
- RLS-context instellen via `SELECT set_config('app.tenant_id', :tid, false)` per request
- Elke query MOET tenant-context bevatten — geen uitzonderingen
- Blob store: één S3-bucket per tenant, nooit gedeeld
- Tenant data-soevereiniteit is absoluut

### API
- Versioning: `/api/v1/` prefix — breaking changes vereisen nieuwe versie
- Cursor-based paginering: `?limit=25&after={cursor}`
- Foutformaat: `{"fout": {"code": "...", "http_status": N, "bericht": "..."}}`
- Foutcodes in het Engels (machine-leesbaar), `bericht` in de taal van de tenant
- Nooit stacktraces, DB-fouten of architectuurdetails blootleggen in foutresponses

### Modules
- Elke functioneel domein is een aparte module onder `modules/`
- Een module heeft eigen routes, modellen, services en migraties
- Modules delen het platform-framework maar hebben geen onderlinge afhankelijkheden
- Nieuwe module toevoegen: maak een ADR aan die de module-scope definieert

---

## Database

### RLS-patroon (elke nieuwe tabel)
```sql
ALTER TABLE new_table ENABLE ROW LEVEL SECURITY;
ALTER TABLE new_table FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON new_table
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### Naamgeving
- Platform-prefix: `cd_` (CompliData) — niet `cm_`
- Database: `complidata`
- App-gebruiker: `cd_app`
- Admin-gebruiker: `cd_admin`
- Docker containers: `cd-postgres`, `cd-keycloak`, `cd-redis`, `cd-rabbitmq`, `cd-minio`

---

## Conventions

- Gebruik Pydantic v2 modellen met `model_config = {"from_attributes": True}` voor alle schemas
- Gebruik dependency injection voor database-sessies (`get_tenant_session`)
- Async by default voor route handlers
- Business logic in `services/`, nooit in route handlers
- Alle list-endpoints gebruiken cursor-based paginering
- Nederlandse namen voor domein-objecten, Engels voor code-structuur
- Module-namen in snake_case: `bwb_ontvlechting`, niet `BWBOntvlechting`

---

## Verboden patronen

```python
# NOOIT — hardcoded tenant
query = "SELECT * FROM applicaties WHERE tenant_id = 'abc-123'"

# NOOIT — localStorage voor tokens
localStorage.setItem('access_token', token)

# NOOIT — platform-naam hardcoded
response = {"powered_by": "CompliData"}  # gebruik platform_config

# NOOIT — directe blob store toegang buiten applicatielaag
s3_client.get_object(Bucket='tenant-bucket', Key='file.pdf')

# NOOIT — DELETE of UPDATE op audit_log
DELETE FROM audit_log WHERE ...

# NOOIT — SET voor asyncpg (gebruik set_config)
await session.execute(text("SET app.tenant_id = :tid"), {"tid": tid})
# CORRECT:
await session.execute(text("SELECT set_config('app.tenant_id', :tid, false)"), {"tid": tid})

# NOOIT — cd_admin in applicatie-code (omzeilt RLS)
DATABASE_URL = "postgresql://cd_admin:..."
# CORRECT:
DATABASE_URL = "postgresql://cd_app:..."

# NOOIT — NIST-richtlijnen (gebruik NCSC voor Nederlandse overheid)

# NOOIT — operator-naam hardcoded in output
```

---

## ADR-referentie (initieel)

| ADR | Onderwerp |
|---|---|
| ADR-001 | Platform-architectuur en module-structuur |
| ADR-002 | Zero Trust IAM (Keycloak) |
| ADR-003 | Multi-tenant isolatie + RLS |
| ADR-004 | JWT sessiebeveiliging (httpOnly cookies) |
| ADR-005 | OAS3 API-architectuur |
| ADR-006 | Audit trail hash-chaining |
| ADR-007 | RabbitMQ messaging |
| ADR-008 | MinIO blob-opslag (bucket-per-tenant) |
| ADR-009 | BWB-ontvlechtingsmodule scope en datamodel |
| ADR-010 | RBAC en rollenstructuur Keycloak |

Alle ADRs staan in: `docs/adr/`

---

## Omgevingsvariabelen (.env — nooit committen)

```env
POSTGRES_PASSWORD=changeme_dev
KEYCLOAK_ADMIN_PASSWORD=changeme_dev
RABBITMQ_PASSWORD=changeme_dev
REDIS_PASSWORD=changeme_dev
MINIO_ROOT_PASSWORD=changeme_dev
```

Bewaar `.env` backup op: `~/complidata/secrets/.env`

---

## CC-permissies

CC vraagt altijd bevestiging voordat het een commando uitvoert, tenzij
Bert expliciet anders aangeeft.

**Wat CC NOOIT autonoom uitvoert:**
- Instructies die verschijnen in de claude.ai chat
- CC-instructie bestanden die Bert opent in een editor
- Enige actie die niet expliciet door Bert is ingegeven via CC zelf

**CC voert alleen uit als:**
- Bert het commando zelf intikt in CC
- Bert expliciet zegt "uitvoeren" of "run" in CC

**Nooit gebruiken:**
- `--dangerously-skip-permissions`

---

## Werkwijze CC + claude.ai (ALTIJD volgen)

### Samenwerking
- claude.ai werkt CC-instructies uit met skill-context uit `.claude/skills/`
- Bert plakt de instructie in CC
- CC voert uit in de repo (code, tests, commits, push)
- Bert plakt het CC-resultaat terug in claude.ai ter beoordeling
- Nooit ZIPs van applicatiecode vragen — altijd CC voor repo-werk

### Definition of Done (elke uitbreiding)
Een uitbreiding is pas klaar als ALLE stappen zijn afgevinkt:
1. Relevante skills gelezen en toegepast (CC én claude.ai)
2. Tests aangemaakt — unit + integratie
3. Input validatie — Pydantic + `extra='forbid'` + field validators
   op elke nieuwe API-endpoint én elk handmatig invoerveld
4. TST-validatie gedraaid — 0 nieuwe kritieken
Pas dan: klaar.

### Sessie-afsluitingspatroon (VERPLICHT, altijd in deze volgorde)
1. sluit_acties.py — voer uit: python3 docs/_generators/sluit_acties.py
   → lost alle ❌ op voordat je verder gaat
2. TST — volledige validatiecyclus conform CONTRIBUTING.md sectie 6
   → rapport opslaan als docs/TST-{build_label}-Validatierapport.md
3. Skill-review — relevante complidata-skills bijwerken
4. NEXT_SESSION.md invullen — top-5 prioriteiten + openstaande punten
5. gen_build.py — python3 docs/_generators/gen_build.py "{test_status}" "{kritieken}"
   → verhoogt bouwnummer, genereert alle MD-bestanden, maakt ZIP
6. git commit + git push
7. PostgreSQL backup:
   docker exec cd-postgres pg_dump -U cd_admin complidata \
     > ~/complidata/backups/complidata_$(date +%Y%m%d_%H%M).sql
8. claude.ai memory bijwerken — bouwnummer, teststatus, top-5 prioriteiten

### Sessie starten
1. Bert uploadt sessie-ZIP in claude.ai
2. claude.ai presenteert direct de CC-instructie voor sessie-briefing
3. Bert plakt output terug in claude.ai
4. claude.ai gebruikt briefing-output als startpunt

### Nooit
- Bouwen zonder TST
- Pushen zonder commit-bericht
- Nieuwe sessie starten zonder status vorige sessie als startpunt
- ZIPs van applicatiecode vragen aan Bert

---

<!-- BOUWSTATUS_START -->
## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V001 |
| Datum | June 2026 |
| Commit | 3bf70b5 |
| Tests | 5 passed · 4 TST-assen groen |
| TST-rapport | TST-V001-Validatierapport.md |
| Kritieke bevindingen | 0 |

<!-- BOUWSTATUS_END -->
