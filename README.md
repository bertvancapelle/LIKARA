# CompliData Platform V001 — een product van G. van Capelle Beheer B.V.

Modulair, multi-tenant databeheer- en migratieplatform voor Nederlandse
overheidsorganisaties. Eerste module: **BWB Data-ontvlechting**.

## Stack

Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy + Alembic · PostgreSQL 16 (RLS) ·
Vue 3 + Vite + Pinia + PrimeVue + Tailwind · Keycloak 24 · RabbitMQ 3.13 ·
MinIO · Redis 7.

## Snel starten (development)

```bash
# 1. .env aanmaken (zie CLAUDE.md → Omgevingsvariabelen)
cp .env.example .env   # indien aanwezig; anders handmatig invullen

# 2. Infrastructuur starten
docker compose -f docker-compose.yml up -d

# 3. Database-migraties
cd backend && python3 -m alembic upgrade head

# 4. Frontend (dev)
cd frontend && npm install && npm run dev
```

## Documentatie

- `CLAUDE.md` — platform-architectuur, conventies, werkwijze
- `docs/adr/` — Architecture Decision Records

CompliData is een zelfstandig platform, ontwikkeld door G. van Capelle Beheer B.V.
Applicatielogica wordt per module opgebouwd onder `modules/`.
