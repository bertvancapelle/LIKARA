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
losgekoppeld van de app-DB `likara` — geen schema-collision meer en de
`likara`-dump bevat geen Keycloak-data (OP-22).

### 1b. Schoon resetten / herseeden

De Postgres-data zit in een **named volume**. **`down -v` staat op Deny** (wist het volume
niet betrouwbaar); gebruik de **expliciete volume-rm-route**:

```bash
docker compose down
docker volume rm likara_lk_postgres_data
docker compose up -d          # init-container (lk-migrate) migreert tot head + platform-seed
```

De **platform-seed** (89 applicatie-checklistvragen + beide catalogi + `checklist_dragend`-vlaggen)
loopt automatisch in de init-container. De **dev-testdata** (16 applicaties + infra, register,
structuur, database-scoring-backfill) is een aparte, idempotente fixture — draai hem ná de reset
**in de container**:

```bash
docker exec -w /app lk-api python3 dev_seed_testdata.py
```

Schone baseline daarna (dev-seed-scenario): componenten **19** (16 applicatie + 1 database +
1 fileshare + 1 saas_dienst) · applicaties **16** · contracten **15** · relaties **81**
(flow 29 · serving 31 · association 12 · assignment 6 · aggregation 3) · roltoewijzingen **75** ·
gebruikersgroepen **31**. **Profiel-stand** (LI058): applicatie 16/16 · database 1/1 · fileshare/saas 0
(niet-beoordeeld). Checklistvragen per tenant: applicatie **89** · database **6** (startset).

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

### 4b. Naar de bedrijfsfunctieboom (gate 2a — systeem koppelen)

1. Sidebar → onder het kopje **BWB-ontvlechting** → **Bedrijfsfuncties** (route
   `/bedrijfsfuncties`). Bovenaan staat de schakelaar **Boom** | **Diagram**; het koppelen
   gebeurt in de **Boom**-weergave.
2. Gebruik het **Zoeken**-veld om een functie te vinden (typen klapt de paden naar de
   treffers open). De koppel-handeling zit in de actie-rij van een functierij, knop
   **Koppel systeem**.
3. De **gate-2a-routes worden pas geladen na een herstart** van de api-container
   (`docker compose -f docker-compose.yml restart api`) — bind-mounts + `--reload` laden
   nieuwe route-modules niet altijd in een draaiend proces. Route-check (verwacht `401`):
   `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/functievervullingen/dekking`.
4. Klik-voor-klik draaiboek: `docs/Draaiboek-browsercheck-gate2a-V041.md`.

### 4c. Van gebruiker wisselen (rol-gating testen)

Rechtsboven in de blauwe topbar staat je e-mailadres met de knop **Uitloggen**. Klik
**Uitloggen** → je komt terug op het inlogscherm → log opnieuw in met een ander account
(bv. van `beheerder-test` naar `medewerker-test`). Zo test je dat een medewerker wél mag
koppelen maar niet ontkoppelen, en een beheerder beide.

> De tenant-dev-accounts (`medewerker-test`, `beheerder-test`, …; wachtwoord
> `changeme_dev`) staan in de tabel hieronder — die stond hier al en is niet gewijzigd.

### 4d. De Landschapskaart openen (LI043)

Sidebar → **BWB-ontvlechting** → **Landschapskaart**. De kaart **opent op het verkenningsscherm**
(zoeken/instap), níét op de volledige graaf — dat is bewust (schaalarchitectuur, LI021). Klik
**"Of toon het hele landschap"** om de kaart te vullen. Pas dán zijn de lezingen (Werk/Beoordelingsstatus/
Domein), de stand-kleuren en de meebewegende legenda zichtbaar.

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

### Platform-testgebruikers (ADR-012 — tenant-overstijgend)

Zelfde wachtwoord **`changeme_dev`**; deze accounts dragen **géén** tenant
(platformbeheer is tenant-overstijgend — een platform-account kan de tenant-views
niet gebruiken en andersom, strikte scheiding).

| Gebruiker | Rol | Ziet in de UI |
|---|---|---|
| `platformbeheerder-test` | platformbeheerder | catalogi lezen **én** muteren (+ Toevoegen, Bewerken, Deactiveren/Reactiveren) |
| `platformoperator-test` | platformoperator | alles alleen-lezen (geen enkele mutatieknop) |

## Platformbeheer openen

1. **Zelfde inlogscherm** als de tenant-app: `http://localhost:3000` → Inloggen →
   Keycloak → `platformbeheerder-test` / `changeme_dev`.
2. Na login stuurt de router-guard een platform-sessie **automatisch** naar de
   beheersectie (`/beheer` — de lichte `BeheerLayout`-shell; een tenant-route is
   voor dit account niet bereikbaar).
3. Navigatie (linksboven): o.a. **Contractcatalogus · Componentcatalogus ·
   Relatie-kenmerk-catalogus · Vraagbetekenis-catalogus**.
4. **Componentcatalogus** (`/beheer/componentconfig`) toont per dimensie een
   sectie; de sectie **"Componenttypen"** bovenaan heeft de knop **"+ Toevoegen"**
   (alleen zichtbaar als platformbeheerder) en per rij Bewerken/Deactiveren. De
   toevoeg-/bewerk-dialoog bevat naam, ArchiMate-typering en de vlaggen
   Checklist-dragend + Ondersteunt werk.

---

## Troubleshooting

- **Health:** `curl -s http://localhost:8000/api/v1/health` → `{"status":"ok","db":"ok"}`.
  `degraded`/`db:error` → postgres nog niet healthy of `lk-migrate` niet klaar.
- **Lege Applicatie-lijst:** verwacht — maak er één aan via "Nieuwe applicatie".
- **Wel ingelogd bij Keycloak maar de app blijft op login / `/auth/me` 401:**
  cookie-probleem. De `lk_session`-cookie is `Secure`; voor lokaal **http** staat
  daarom `COOKIE_SECURE: "false"` op de `api`-service in `docker-compose.yml`
  (dev-only; productie houdt `secure=True`). Draai je een eigen backend, zet dan
  `COOKIE_SECURE=false` in je `.env`.
- **Open `http://localhost:3000`**, niet `:8000` — anders matcht de redirect_uri/
  cookie-origin niet.
- **Keycloak nog niet klaar:** `docker logs lk-keycloak | tail`; wacht tot healthy
  (realm `likara` wordt met `--import-realm` geladen).
- **Stoppen:** dev-server met `pkill -f vite`; stack met `docker compose down`
  (data blijft in het named volume). Écht wissen = de expliciete `docker volume rm
  likara_lk_postgres_data` (zie §1b) — **niet** `down -v` (staat op Deny).

---

## Alternatief: backend zonder Docker

Kan, maar **Keycloak is alsnog nodig** voor inloggen. `LIKARA_TEST_MODE=true`
versoepelt enkel Origin-check/rate-limit; het levert **geen** sessie. Voor een
volledige doorklik-test is de Docker-stack hierboven de eenvoudigste weg.
