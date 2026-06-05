# ADR-001 — Platform-architectuur en module-structuur

| | |
|---|---|
| **Status** | Aanvaard |
| **Datum** | 2026-06-05 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-003 (multi-tenant RLS), ADR-005 (API), ADR-009 (eerste module) |

## Context

CompliData is een nieuw, multi-tenant databeheer- en migratieplatform voor
Nederlandse overheidsorganisaties. De eerste functionele module is
BWB-ontvlechting (ADR-009); er volgen er meer. We moeten vastleggen:

1. welke **architectuurstijl** het platform hanteert;
2. hoe **functionele domeinen** worden georganiseerd en geïsoleerd;
3. wat het **gedeelde framework** is waarop modules voortbouwen.

Randvoorwaarden: klein team, EU-soevereiniteit, één deploy-eenheid gewenst,
strikte tenant-isolatie, voorspelbare uitbreidbaarheid per module.

## Besluit

### B1 — Modulaire monoliet als deploy-eenheid

Het platform is één **modulaire monoliet**: één FastAPI-backend en één
Vue-frontend, samen gedeployed via Docker Compose. Geen microservices in V001.

### B2 — Functionele domeinen als modules

Elk functioneel domein is een **module** onder `modules/<module>/`:

```
modules/<module>/
  backend/      — routes, models, services, schemas van de module
  frontend/     — views, stores van de module
  migrations/   — Alembic-migraties van de module
```

Module-namen in `snake_case` (bijv. `bwb_ontvlechting`).

### B3 — Gedeeld platform-framework

Modules bouwen voort op het gedeelde framework; ze herimplementeren dit nooit:

- `backend/app/core/` — config, database, keycloak, messaging, redis
- `backend/app/middleware/` — auth (JWT httpOnly cookie), tenant (RLS-context),
  rate_limit, origin_check, security_headers
- `backend/app/models/base.py` — `Base`, `TenantMixin`, `TimestampMixin`
- `frontend/src/` — router, Pinia-stores, design system (presets + tokens)

### B4 — Module-isolatie

- Elke module heeft **eigen** routes, modellen, services en migraties.
- Modules hebben **geen onderlinge code-afhankelijkheden**. Cross-module
  interactie verloopt uitsluitend via het platform-framework of via
  events (RabbitMQ, ADR-007) — nooit via directe imports tussen modules.
- Een nieuwe module wordt **altijd** voorafgegaan door een ADR die de
  module-scope en het datamodel definieert.

### B5 — Multi-tenant op databaseniveau

Tenant-isolatie via PostgreSQL Row Level Security (ADR-003). Elke
module-tabel is tenant-scoped: `tenant_id`-kolom + `ENABLE`/`FORCE ROW LEVEL
SECURITY` + `tenant_isolation`-policy. De applicatie verbindt als `cd_app`
(non-superuser); `cd_admin` nooit in applicatiecode.

### B6 — API- en foutconventies

- Versionering via `/api/v1/`-prefix; breaking changes vereisen een nieuwe versie.
- Cursor-based paginering: `?limit=25&after={cursor}`.
- Foutformaat: `{"fout": {"code": "...", "http_status": N, "bericht": "..."}}`
  — codes Engels (machine-leesbaar), `bericht` in de taal van de tenant.
- Module-routers worden geregistreerd in `backend/app/main.py` onder `/api/v1`.

### B7 — Frontend-conventies

Vue 3 + Vite + Pinia + Vue Router + PrimeVue (Unstyled) + Tailwind CSS, met
centrale design tokens (`--cd-*`) en PassThrough-presets (ADR-047-lijn).
Module-views leven onder `modules/<module>/frontend` en worden in de
centrale router geregistreerd.

## Gevolgen

**Positief**
- Eén build/deploy, lage operationele complexiteit, gedeelde security-laag.
- Strikte, herhaalbare module-structuur → voorspelbare uitbreiding.
- Latere extractie van een module naar een aparte service blijft mogelijk
  doordat modules al geïsoleerd zijn.

**Negatief / aandachtspunt**
- Module-grenzen worden niet door het runtime-proces afgedwongen; discipline
  (en code review) moet directe cross-module imports voorkomen.
- Eén gedeelde database; schaal-isolatie per module is er niet (acceptabel op
  huidige schaal).

## Alternatieven overwogen

- **Microservices per module** — verworpen: te veel operationele overhead voor
  een klein team en één initiële module; voegt nu geen waarde toe.
- **Losse applicaties per module** (eigen backend/frontend elk) — verworpen:
  duplicatie van auth-, tenant- en security-framework; inconsistente UX.
