# Lokaal testen — UI doorklikken (login → shell → Applicaties)

Dit receptje is **empirisch geverifieerd** tegen de stack (build `b9bd71e`): de
login-round-trip (Keycloak Authorization Code + PKCE) en de Applicatie-data-flow
zijn programmatisch bewezen; de UI-klik zelf doe je in de browser.

> **Belangrijk:** inloggen vereist de **volledige stack** (Keycloak draait mee).
> `LIKARA_TEST_MODE` is **géén** auth-stub en seedt niets — het versoepelt
> alleen de Origin-check en de rate-limit-sleutel. Een losse backend (uvicorn)
> zonder Keycloak laat je dus niet inloggen.

---

## Snelste werkende route (volledige stack)

### 1. Stack starten

```bash
docker compose up -d
```

Wacht tot de init-container klaar is en de API healthy is:

```bash
# init-container moet exit 0 hebben en de 89 checklistvragen hebben geseed:
docker inspect lk-migrate --format '{{.State.ExitCode}}'        # → 0
docker logs lk-migrate | tail -1                                # → platform_init: 89 checklistvragen geborgd ...

# API health:
curl -s http://localhost:8000/api/v1/health                     # → {"status":"ok","db":"ok"}
```

Containers en poorten: postgres `:5432` · keycloak `:8080` · rabbitmq `:5672/:15672`
· redis `:6379` · minio `:9000/:9001` · **api `:8000`**. (De `ui`-container heeft
`profiles: [production]` en start lokaal niet mee — gebruik de dev-server hieronder.)

Keycloak heeft sinds **CD055** een **eigen database** `keycloak` (rol `kc_user`),
losgekoppeld van de app-DB `complidata` — geen schema-collision meer en de
`complidata`-dump bevat geen Keycloak-data (OP-22).

### 1b. Schoon resetten / herseeden

De Postgres-data zit in een **named volume** (CD055), dus `down -v` reset de DB echt:

```bash
docker compose down -v && docker compose up -d   # wist DB → migratie 0006 + platform-seed
```

De **platform-seed** (89 checklistvragen + beide catalogi, 9/9) loopt automatisch in de
init-container. De **dev-testdata** (12 applicaties, 14 componenten, register, structuur)
is een aparte, idempotente fixture — draai hem ná de reset handmatig:

```bash
docker exec -w /app lk-api python3 dev_seed_testdata.py
```

Schone baseline daarna: componenten **14** · structuur **3** · leveranciers **4** ·
contracten **7** · koppelingen **10** · applicaties **12** · blokkades **10** ·
component-contract **11**.

### 2. Frontend dev-server starten

```bash
cd frontend && npm run dev      # → http://localhost:3000  (proxy /api → :8000)
```

### 3. Openen en inloggen

1. Open **`http://localhost:3000`** (niet `:8000` — de redirect_uri en cookie zijn
   op `localhost:3000` afgestemd).
2. Klik **Inloggen** → je wordt doorgestuurd naar het Keycloak-inlogscherm.
3. Log in met een testgebruiker (zie tabel). Voor **alle** knoppen:
   **`beheerder-test` / `changeme_dev`**.
4. Je komt terug op het dashboard (`/`).

### 4. Doorklikken naar Applicaties

1. Sidebar → **Applicaties**.
2. De lijst is **leeg** — dat is normaal: alleen de 89 checklistvragen zijn geseed,
   er zijn **geen voorbeeld-applicaties**.
3. Klik **Nieuwe applicatie** (zichtbaar voor Medewerker/Beheerder) → vul het
   formulier in (dropdowns komen uit het opties-endpoint) → **Opslaan**.
4. Je landt op het detail; de applicatie staat nu ook in de lijst. Op het detail:
   **Bewerken**, **Start inventarisatie** (alleen bij status `concept`),
   **Verwijderen** (alleen Beheerder, met cascade-waarschuwing).

---

## Testgebruikers en rollen

Allen wachtwoord **`changeme_dev`**, tenant `11111111-1111-1111-1111-111111111111`.

| Gebruiker | Rol | Ziet in de UI |
|---|---|---|
| `viewer-test` | viewer | alleen lezen (geen aanmaak-/bewerk-/verwijder-knoppen) |
| `medewerker-test` | medewerker | + Nieuwe applicatie, Bewerken, Start inventarisatie |
| `beheerder-test` | beheerder | + Verwijderen (**alle** knoppen) |
| `auditor-test` | auditor | alleen lezen |

De rol zit vast aan de gekozen gebruiker (Keycloak-realm-rol). Rol-gating in de UI
is een *affordance*; de backend handhaaft de rechten hoe dan ook.

---

## Troubleshooting

- **Health:** `curl -s http://localhost:8000/api/v1/health` → `{"status":"ok","db":"ok"}`.
  `degraded`/`db:error` → postgres nog niet healthy of `lk-migrate` niet klaar.
- **Lege Applicatie-lijst:** verwacht — maak er één aan via "Nieuwe applicatie".
- **Wel ingelogd bij Keycloak maar de app blijft op login / `/auth/me` 401:**
  cookie-probleem. De `cd_session`-cookie is `Secure`; voor lokaal **http** staat
  daarom `COOKIE_SECURE: "false"` op de `api`-service in `docker-compose.yml`
  (dev-only; productie houdt `secure=True`). Draai je een eigen backend, zet dan
  `COOKIE_SECURE=false` in je `.env`.
- **Open `http://localhost:3000`**, niet `:8000` — anders matcht de redirect_uri/
  cookie-origin niet.
- **Keycloak nog niet klaar:** `docker logs lk-keycloak | tail`; wacht tot healthy
  (realm `complidata` wordt met `--import-realm` geladen).
- **Stoppen:** dev-server met `pkill -f vite`; stack met `docker compose down`
  (data blijft in volumes; `down -v` wist ook de database).

---

## Alternatief: backend zonder Docker

Kan, maar **Keycloak is alsnog nodig** voor inloggen. `LIKARA_TEST_MODE=true`
versoepelt enkel Origin-check/rate-limit; het levert **geen** sessie. Voor een
volledige doorklik-test is de Docker-stack hierboven de eenvoudigste weg.
