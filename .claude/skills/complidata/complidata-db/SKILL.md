---
name: complidata-db
description: Database-patronen voor CompliData (PostgreSQL 16, RLS, Alembic). Beschrijft de werkelijke V001-staat.
stack: PostgreSQL 16, SQLAlchemy asyncio, Alembic
bijgewerkt: V007
---

# CompliData Database Skill

## RLS-boilerplate (elke nieuwe tenant-tabel)

```sql
ALTER TABLE {tabel} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {tabel} FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON {tabel}
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
GRANT SELECT, INSERT, UPDATE, DELETE ON {tabel} TO cd_app;
```

`FORCE` is verplicht — zonder FORCE omzeilen table-owners de policy.

## GRANT-patroon

```sql
-- Tenant-tabel
GRANT SELECT, INSERT, UPDATE, DELETE ON {tabel} TO cd_app;

-- Referentietabel (geen RLS) — inclusief sequence voor de int-PK
GRANT SELECT, INSERT, UPDATE ON checklistvraag TO cd_app;
GRANT USAGE, SELECT ON SEQUENCE checklistvraag_id_seq TO cd_app;
```

## PostgreSQL enum-types in migraties

In de migratie (niet in het model) worden enum-types expliciet aangemaakt.
`postgresql.ENUM` accepteert wél `create_type=False`; de aanmaak gebeurt via
`.create(bind, checkfirst=True)`. Type-namen eindigen op `_enum`.

```python
# upgrade
hostingmodel = postgresql.ENUM(
    "on_premise", "private_cloud", "saas", "iaas", "paas", "hybride", "onbekend",
    name="hostingmodel_enum", create_type=False,
)
hostingmodel.create(op.get_bind(), checkfirst=True)
# ... daarna in create_table: sa.Column("hostingmodel", hostingmodel, ...)

# downgrade
postgresql.ENUM(name="hostingmodel_enum").drop(op.get_bind(), checkfirst=True)
```

## Index-strategie

```python
op.create_index("ix_applicatie_tenant", "applicatie", ["tenant_id"])
op.create_index("ix_applicatie_tenant_lifecycle", "applicatie",
                ["tenant_id", "lifecycle_status"])
op.create_index("ix_koppeling_tenant_bron", "koppeling",
                ["tenant_id", "bron_applicatie_id"])
```

Plaats `tenant_id` als eerste kolom in composite indexen.

## FK-volgorde en CASCADE

- Create-volgorde: ouder-tabel vóór kind-tabel (FK's resolven).
- `ON DELETE CASCADE` op kind-FK's binnen tenant-scope.
- `CHECK bron_applicatie_id <> doel_applicatie_id` op Koppeling.
- `UNIQUE (tenant_id, applicatie_id, vraag_code)` op Checklistscore.
- Drop-volgorde in downgrade: omgekeerd (kind vóór ouder).

## Referentietabel-uitzondering

`ChecklistVraag` heeft **geen** RLS en **geen** `tenant_id` — het is
platform-brede seeddata die alle tenants delen (int-PK, `code` UNIQUE).
Alleen `GRANT SELECT, INSERT, UPDATE` + sequence-grant voor `cd_app`.

## Alembic multi-location (platform + modules)

```ini
# backend/alembic.ini — separator is ":" (os.pathsep op posix)
version_locations = %(here)s/alembic/versions:%(here)s/../modules/bwb_ontvlechting/migrations/versions
```

Module-migratie: `down_revision = None` (root, want de platform-versions
zijn leeg in V001). Verificatie offline: `alembic heads`, `alembic history`,
`alembic upgrade head --sql`.

## DB-rollen — driedeling (ADR-011/012, least privilege)

| Rol | Type | Waar | Gebruik |
|---|---|---|---|
| `cd_admin` | superuser | **uitsluitend** de init-container | migratie (`alembic upgrade head`) + `platform_init`. NOOIT in de app-runtime. |
| `cd_platform` | non-superuser | app-laag | platform-endpoints (tenant-provisioning, platforminstellingen). Grants **per platform-tabel** (least privilege), GEEN `CREATE`/DDL, GEEN toegang tot tenant-tabellen. |
| `cd_app` | non-superuser | app-laag | tenant-werk onder RLS. |

- Migreren als `cd_app` **kan niet en mag niet**: `cd_app` heeft geen `CREATE`
  op schema `public` (`has_schema_privilege('cd_app','public','CREATE')=false`),
  dus DDL faalt; bovendien hoort migratie als `cd_admin` (superuser/owner).
- `cd_platform` (init-db): `CREATE ROLE cd_platform LOGIN` + `GRANT USAGE ON
  SCHEMA public` — bewust **geen** `ALTER DEFAULT PRIVILEGES`. Per platform-tabel
  in de migratie: `GRANT SELECT,INSERT,UPDATE,DELETE ON {tabel} TO cd_platform`
  én `REVOKE ALL ON {tabel} FROM cd_app` (platform-register valt buiten het
  tenant-domein). Verificatie: cd_platform op een tenant-/referentietabel →
  `permission denied`.

## Migratie + platform-seed (init-container, ADR-011)

```yaml
# docker-compose.yml — cd-migrate draait als cd_admin, run-to-completion
migrate:
  image: complidata-api:local
  command: ["sh","-c","python3 -m alembic upgrade head && python3 -m app.platform_init"]
  # DATABASE_URL(_SYNC) = cd_admin; ook ./modules gemount (seed-bron)
api:
  depends_on:
    migrate: { condition: service_completed_successfully }   # gating vóór app-start
```

- App-entrypoint blijft **alleen** `uvicorn` (geen migratie/seed in de app).
- `platform_init` zaait de 89 platform-brede checklistvragen (referentiedata,
  idempotent `ON CONFLICT DO NOTHING`); zie complidata-backend seed-patroon.
- Alembic multi-head vermijden: platform-migraties in
  `backend/alembic/versions/` ketenen aan de module-head (`down_revision`),
  zodat `alembic heads` = 1 blijft.

## Naamgeving

- Platform-prefix: `cd_` (database `complidata`, rollen, containers `cd-*`).
- App-gebruiker: `cd_app` (non-superuser — omzeilt RLS NIET).
- Platform-gebruiker: `cd_platform` (non-superuser — platform-endpoints, ADR-012).
- Admin-gebruiker: `cd_admin` — superuser, UITSLUITEND in de init-container.
- Enum-typenamen: lowercase snake_case eindigend op `_enum`
  (`hostingmodel_enum`, `lifecycle_status_enum`, `niveau_enum`).

## Enum = single source in `models.py` (V003)

De Python-enums in `modules/bwb_ontvlechting/backend/models/models.py` zijn de
bron; de migratie spiegelt exact dezelfde waarden. ADR-009-voetnoten ("voorgesteld")
zijn niet leidend — **de code is leidend**: `hostingmodel` = **7** waarden,
`migratiepad` = **6** (incl. `tijdelijk_gedeeld`), `protocol` = enum (`Koppelprotocol`).
`checklist_score`-kolom is nullable in de DB; het Create-schema dwingt non-null af
(ADR-013). ADR-009-tekst ↔ code synchroniseren staat open.

## Lifecycle-herberekening (ADR-013, Model A)

- Eén deterministische afleiding: pure `bepaal_lifecycle(huidige, aantal_gescoord,
  aantal_vragen, aantal_open_blokkades)` (DB-vrij testbaar) + tenant-scoped
  `herbereken_lifecycle(session, tenant_id, applicatie_id)` (telt vragen/scores/open
  blokkades, zet de status op het in-sessie object; caller commit). Draait na elke
  Checklistscore-/Blokkade-mutatie én na `start-inventarisatie`.
- Regel: `concept`→`concept` (enige niet-afgeleide vloer; nooit terug naar concept);
  niet-alles-gescoord → `in_inventarisatie`; alles gescoord + ≥1 open blokkade
  (`open`/`in_behandeling`) → `geblokkeerd`; anders → `migratieklaar`. Reverse mag.
- **Transitie-gebaseerde** auto-blokkade-invariant: alleen handelen als de score de
  blokkerende grens kruist (`ja/nvt ↔ nee/deels`); een ongewijzigde of
  binnen-blokkerende score laat een (handmatig) opgeloste blokkade met rust →
  "nee + opgelost" is een stabiele eindtoestand. `checklist_compleet` is **transient**
  (enum blijft, status wordt nooit gezet).

## Keyset-cursor-paginering — sorteerbaar (ADR-017, v2/v2n)

Helper: `modules/bwb_ontvlechting/backend/services/pagination.py`. De legacy
2-delige `created_at|id`-cursor (`encode_cursor`/`decode_cursor`) is met **CD021**
verwijderd — alle lijsten gebruiken nu zelfbeschrijvende sorteer-cursors.

**v2 (allowlist-sortering, ADR-017)**:
- Cursor `v2|sort|order|waarde|id` (`encode_sort_cursor`/`decode_sort_cursor`); `id`
  is de stabiele tiebreaker (totale ordening, ook bij een niet-unieke sorteerkolom).
- `ORDER BY (kolom DIR, id DIR)` met **dezelfde** richting voor kolom én tiebreaker;
  de seek is één `tuple_`-rijvergelijking: `> (waarde, id)` bij `asc`, `< (…)` bij `desc`.
- **Allowlist-enum**: een rauwe kolomnaam uit de querystring komt **nooit** in
  `ORDER BY` — alleen via een `*Sorteerveld`-enum (single source naast een
  `_SORTEERBARE_KOLOMMEN`-map + `_WAARDE_PARSERS`; een test borgt de synchroniteit).
  Onbekend sorteerveld/ongeldige richting ⇒ **422** (API-rand).
- Een `after`-cursor die **niet bij de actieve `sort`/`order`** past ⇒ **400 `ONGELDIGE_CURSOR`**
  (de cursor draagt `sort`+`order`; een mismatch wordt geweigerd i.p.v. stil verkeerd gepagineerd).
- Default (geen `sort`/`order`) = `created_at` oplopend = exact het pre-ADR-017-gedrag.

**v2n (NULLS-LAST, CD016) — voor een nullable sorteerkolom**:
- Cursor `v2n|sort|order|isnull|waarde|id` (`*_sort_cursor_nullable`) met een
  **null-vlag** (`isnull` vóór `waarde`); `keyset_order_by_nulls_last` (`.nulls_last()`,
  NULLs altijd achteraan in asc én desc) + `keyset_seek_nulls_last` (case-split:
  niet-null-regio inclusief de volledige null-staart, óf alleen de null-staart).
- Generaliseert over tekst- én timestamp-kolommen; op een NOT NULL-kolom is de
  `IS NULL`-tak een no-op → **uniform** bruikbaar (CD020 gebruikt v2n voor álle
  geretrofitte lijsten, ook waar alle kolommen NOT NULL zijn). De cursor-waarde wordt
  uit het ORM-object gelezen via `getattr(item, kolom.key)` (mapt `gewijzigd_op`→`updated_at`).
- Empirische NULL-ordening rijdt mee tot de live-DB-run (OP-20 / #23).

**Join-sortering** (CD016 blokkadesoverzicht, CD020 koppeling-`tegenpartij_naam`):
de sorteerkolom mag een **gejoinde** kolom zijn (bv. `Applicatie.naam`); de keyset/
tiebreaker blijft de eigen `id`. Bij koppeling is de join **richting-afhankelijk**
(filter op bron → join doel, op doel → join bron).

## Server-side filters (CD017)

- **LIKE/ILIKE-escaping** tegen wildcard-injectie: escape in de volgorde
  `\` → `%` → `_`, dan `kolom.ilike(f"%{escaped}%", escape="\\")`. Lengte-limieten op
  de API-rand (`Query(max_length=…)` → 422), niet alleen in de service.
- **AND-combinatie** van alle filters; afwezige/lege filters voegen géén clause toe
  (default-pad byte-identiek). **Lege multi-select = géén filter** (toon alles), niet
  "toon niets". Multi-select via een herhaalbare `?status=`-param + enum-allowlist → `IN`.

## Cursor-discipline (frontend)

De frontend **reset de cursor** bij elke sorteer-, filter- of statuswissel (begint weer
op pagina 1). Filters/sortering zitten **niet** in de cursor — reset volstaat.

## V004-patronen (CD003–CD012, geverifieerd)

- **Lifecycle-reconciliatie (ADR-016)**: blokkade-`opgelost` volledig afgeleid;
  invariant B2 klopt nu **per constructie** op beide schrijfpaden (handmatig begrensd
  tot `open ↔ in_behandeling`, `opgelost` enkel auto). `checklist_compleet` blijft
  transient (ADR-013 B4). Geen migratie/enumwijziging. [CD011]
- **ChecklistVraag = platform-referentiedata** (89 vragen, géén `tenant_id`, géén RLS;
  seed via platform-init). Koppeling vanuit Checklistscore op `vraag_code` (string),
  niet op id. [CD004]
- **Data-pass-discipline**: een ADR-die-bestaande-data-raakt (ADR-016) eerst tegen de
  DB tellen (read-only, als cd_admin); bij gevulde DB een herbereken-pass voorstellen,
  niet zelf draaien vóór akkoord. [CD011]

## V006-patronen (CD025–CD038, ADR-019, geverifieerd)

- **Optie-catalogus = referentiedata met stabiele, soft-deactiveerbare id's** (`checklistvraag_optie`,
  geen RLS): `optie_sleutel` is **stabiel** — nooit hard verwijderen of hernummeren zodra in gebruik;
  bewerken = **soft-deactivate** (`actief=false`) + evt. een nieuwe sleutel. Historische
  `antwoord_waarde` blijft resolvebaar omdat de read **alle** opties levert (incl. inactieve, met
  `actief`-vlag). `afgeleid_bron` markeert een uit een model-enum afgeleide set. [CD027/CD031]
- **Expand/contract bij geseede referentie-opties**: de **seed** is de *expand* (fresh deploys
  krijgen de nieuwe set; idempotent `ON CONFLICT DO NOTHING`); een **eenmalige, versie-getrackte
  migratie** is de *contract* (legacy-opties soft-deactiveren op bestaande DB's). De migratie draait
  vóór `platform_init`, dus op een fresh deploy raakt hij 0 rijen. Géén generieke "prune" in de seed
  (zou beheerder-toegevoegde opties dempen) — de contract is specifiek. Voorbeeld: 7.5 L/M/H → BBN
  (`0004_bio2_bbn`). [CD035]
- **Single-source vs. bewust-onafhankelijk**: een optieset alleen **afleiden van een model-enum**
  (read-only in de beheer-UI) waar de vraag *exact* hetzelfde domein beschrijft (2.1 ← `HostingModel`,
  12.1 ← `NiveauEnum`). "**Zelfde labels ≠ zelfde domein**": waar de framing anders is, blijft de set
  vrij configureerbaar (11.1 ontvlechtingsscenario ≠ `Migratiepad`-techniek). [CD027]
- **`antwoord_waarde` = jsonb, nullable, geen FK**: envelope `{"optie": id}` / `{"opties": [id…]}` /
  `{"getal": int}`. Geen DB-FK naar de catalogus — het `optie_sleutel` is stabiel en wordt nooit hard
  verwijderd; integriteit wordt app-side gevalideerd (actief + hoort bij de vraag). [CD027/CD028]
- **Additieve migratie + grants**: `0003_antwoordconfig` voegt kolom + tabel + jsonb toe (bestaande
  tabellen ongemoeid). Grants least-privilege: `cd_app` **SELECT-only** op de catalogus (validatie),
  `cd_platform` SELECT/INSERT/UPDATE (beheer); `cd_platform` SELECT/UPDATE op `checklistvraag`. [CD027]

## V007-patronen (CD039–CD056, geverifieerd)

- **Tenant-context is transactie-lokaal (norm sinds CD048)** — niet onderhandelbaar:
  een request-scoped **ContextVar** (`app/core/tenant_context.py`) + een SQLAlchemy
  **`after_begin`-sessiehook** (`app/core/database.py`) zet per transactie
  `SELECT set_config('app.tenant_id', :tid, true)` op sessies gemarkeerd met
  `session.sync_session.info['rls']=True`; **fail-fast** (`RuntimeError`) bij een
  RLS-sessie zonder context. **Verboden patroon**: eenmalig per-sessie
  `set_config(..., false)` — een `commit`→`refresh` kan dan een **contextloze
  poolverbinding** treffen (`''::uuid`-fout ná een geslaagde INSERT; duplicaat-risico
  door client-retries; latent cross-tenant-risico). `pool_pre_ping=True` op de engines.
  Aandachtspunt bij hooks: verifieer ContextVar-zichtbaarheid over de greenlet-bridge
  (asyncio ↔ sync `Session`). De `set_config(..., false)`-voorbeelden elders zijn
  historisch — de transactie-lokale `true`-variant is de norm.
- **Keycloak scheidt van de app-DB (norm sinds CD055)**: Keycloak draait op een **eigen
  database** `keycloak` met eigen rol `kc_user` (init-db/`02_keycloak.sql`: rol + DB +
  `public`-schema-owner voor PG16) — **nooit** de app-DB `complidata` delen. Een gedeeld
  `public`-schema gaf een naamruimte-collision (onze ADR-021-tabel `component` schaduwde
  Keycloak's interne `COMPONENT` → Keycloak startte niet) én lekte Keycloak-secrets in de
  `complidata`-dump (OP-22, nu gesloten). Postgres-data op een **named volume**
  (`cd_postgres_data`), zodat `down -v && up -d` echt reset; de dev-seed
  (`dev_seed_testdata.py`) is een bewuste **handmatige** fixture (niet in de init-container,
  dev-only). Reset-procedure: zie `docs/LOKAAL-TESTEN.md`.
