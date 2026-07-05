---
name: likara-resilience
description: Resilience-patronen voor LIKARA (health, startup-validatie, rate-limiting, healthcheck-gating). Beschrijft de werkelijke V001-staat.
stack: FastAPI, SlowAPI, Redis, Docker Compose healthchecks
bijgewerkt: V001
---

# LIKARA Resilience Skill

## Health endpoint-patroon

```python
# /api/v1/health — altijd HTTP 200 (liveness onafhankelijk van DB)
@router.get("/health")
async def health():
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {"status": "ok" if db_status == "ok" else "degraded", "db": db_status}
```

`status` is `ok` of `degraded`; `db` is `ok` of `error`. De readiness-info
zit in de body, niet in de HTTP-status (liveness blijft 200).

## Startup fail-fast

```python
# backend/app/core/config.py
def validate_startup_config():
    """Faalt leesbaar bij ontbrekende verplichte Settings-velden."""
    required = {
        "DATABASE_URL": settings.database_url,
        "KEYCLOAK_URL": settings.keycloak_url,
        "RABBITMQ_URL": settings.rabbitmq_url,
        # ... database_url_sync, admin_database_url, keycloak_realm/client_*
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError("CONFIGURATIEFOUT — ontbrekend: " + ", ".join(missing))
```

Aangeroepen in de `lifespan` — de app start niet met onvolledige config.

## SlowAPI rate-limiting

Vier niveaus, gedefinieerd in `middleware/rate_limit.py` op basis van config:

| Constante | Gebruik |
|---|---|
| `AUTH_LIMIT` | Login/auth-endpoints |
| `WRITE_LIMIT` | POST/PUT/PATCH/DELETE |
| `READ_LIMIT` | GET-endpoints |
| `ADMIN_LIMIT` | Beheer-endpoints |

```python
limiter = Limiter(key_func=_get_key, storage_uri=settings.redis_url, default_limits=[])
```

De limiter is geregistreerd (`app.state.limiter` + 429-handler met
fout-format `RATE_LIMIT_OVERSCHREDEN`). De `@limiter.limit(...)`-decorators
zijn in V001 nog niet op endpoints toegepast.

## Docker Compose healthcheck-gating

```yaml
depends_on:
  postgres: { condition: service_healthy }
  keycloak: { condition: service_healthy }
  rabbitmq: { condition: service_healthy }
  redis:    { condition: service_healthy }
  minio:    { condition: service_healthy }
```

Elke service heeft een `healthcheck`; de API start pas als alle
afhankelijkheden healthy zijn.

## Centrale verlopen-sessie-vangrail (client-side, LI032)

Eén centraal afhandelpunt in `frontend/src/api.js` vangt een verlopen sessie af, i.p.v. per
aanroeper losse 401-afhandeling (die lekt of vergeet). Kernregels:
- **Afhandelen pas op het bewezen-gefaalde-refresh-punt.** `request()` doet een **single-flight**
  token-refresh + één retry; pas als díé faalt, roept `api.js` de centrale vangrail
  (`_meldSessieVerlopen`) aan → **nooit** terwijl de sessie nog te redden is. Zo geen valse
  "sessie verlopen" bij een herstelbare 401.
- **Framework-loze bedrading.** De vangrail wordt bedraad via **callback-registratie**
  (`registreerSessieVerlopenHandler`) — géén harde `router`/`store`-import in `api.js`. Dat behoudt
  de offline testbaarheid van de api-laag (geen Vue/router-context nodig in de test). De concrete
  handler (`src/sessieVangrail.js` → `sessieVerlopenHandler(router, auth)`) wist de sessie en doet
  `router.push` naar `login?sessie_verlopen=1&next=<pad>` (behoud van de bestemming).
- **Dekt alle oppervlakken die via `request()` lopen** — één keer goed i.p.v. per component.
  **Nooit een rauwe `NIET_GEAUTHENTICEERD` in beeld**: catch-blokken tonen op 401 niets (de vangrail
  redirect), overige fouten een generieke tekst. Het navigatie-pad probeert eerst **stil te
  vernieuwen** vóór het naar login stuurt.
- Borging: `api.test.js` (handler één keer / niet bij succes), `sessieVangrail.test.js` (redirect +
  next), `authSession.test.js` (refresh-vóór-opgeven). Volledige technische uitwerking: likara-frontend
  §Centrale verlopen-sessie-vangrail.

## Afwezig in V001 — toekomstige resilience-patronen

| Patroon | Status |
|---|---|
| Circuit-breaker | Niet aanwezig — toe te voegen bij externe service-integraties |
| Transactional outbox | Niet aanwezig — geen RabbitMQ consumers/producers in V001 |
| Degradation-klassen | Niet aanwezig — health-endpoint heeft basis `degraded`/`ok` |
| Retry-mechanisme | Niet aanwezig |

RabbitMQ (ADR-007) is als framework geconfigureerd (`core/messaging.py`),
maar er zijn in V001 nog geen consumers/producers — dus geen outbox- of
DLQ-patroon geïmplementeerd.
