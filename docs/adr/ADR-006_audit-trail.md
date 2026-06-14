# ADR-006 — Audit-trail (onweerlegbaar wijzigingsspoor)

**Status**: Aanvaard — CD008 (V008-lijn, bovenop head `0009_adr022_e_checklist_dragend`).
Implementatie openstaand — datamodel, migratie, RLS-policies, capture-hook, lees-API en RBAC
volgen als afzonderlijk, gegate bouwblok (CC stop-and-report vóór schema-/engine-werk).
**Voortbouwend op**: ADR-013 (lifecycle-herberekening — score als enige driver), ADR-016
(blokkade-`opgelost` afgeleid), ADR-022 (definitief besturingsmodel: profiel/checklist per
componenttype, tenant-eigen vragensets — bewust vóór de audit-trail afgerond), ADR-003/012
(RLS + tweelaags rollenmodel platform ↔ tenant), CD048 (transactie-lokale tenant-context via
ContextVar + `after_begin`-sessiehook).
**Deblokkeert**: het audit-trail-scherm (#14) — dit ADR (#17) levert datamodel + lees-API,
#14 bouwt het scherm.

---

## Context

- ADR-006 was gereserveerd; er bestond nog géén audit-/wijzigingsspoor in de codebase (groen
  veld). De ontvlechting Tiel ↔ BWB vereist een onweerlegbaar spoor van wie-wat-wanneer wijzigde
  aan de compliance-relevante gegevens, als verantwoording.
- ADR-022 (beoordelingsprofiel/checklist per componenttype) is bewust vóór de audit-trail
  afgerond, zodat de audit-trail meteen het definitieve besturingsmodel logt en geen verouderde
  semantiek hoeft mee te slepen.
- Dit besluit deblokkeert het audit-trail-scherm (#14): #17 levert het datamodel en de lees-API,
  #14 bouwt het scherm.
- Invariant uit de bestaande architectuur die leidend blijft: **de score is de enige
  lifecycle-driver**; blokkade-`opgelost` en lifecycle zijn systeem-afgeleid.

## Besluit

Negen vastgelegde keuzes.

### Besluit 1 — Oorzaak én gevolg loggen, gebonden met correlatie-id

Elke compliance-mutatie levert een auditrecord; de systeem-afgeleide gevolgen (blokkade,
lifecycle) krijgen een eigen record dat via één gedeeld `correlatie_id` aan de veroorzakende
handeling én dezelfde actor is gekoppeld. De score-driver en zijn afgeleide gevolgen zijn zo als
keten herleidbaar.

### Besluit 2 — App-niveau capture als primaire registratie

Een centrale SQLAlchemy `before_flush`/`after_flush`-event op de gedeelde `AsyncSession` (analoog
aan de bestaande `after_begin`-hook in `app/core/database.py`) vertaalt `session.new/dirty/deleted`
naar auditrecords. Alle huidige mutatiepaden — inclusief de afgeleide — lopen door deze flush; geen
per-service-aanpassing. Geen DB-trigger als registratiebron (wel als onwijzigbaarheids-slot, zie
Besluit 5).

### Besluit 3 — Actor via request-scoped context

De request-context (ContextVar, naast `tenant_id`) wordt uitgebreid met de actor: Keycloak-subject
(`actor_sub`) + e-mail (`actor_email`), gezet in `get_tenant_session`. De capture-hook leest actor +
correlatie-id daaruit. Systeem-afgeleide mutaties erven automatisch dezelfde actor en correlatie-id
(zelfde request-transactie). Geen actor door alle service-signatures threaden.

### Besluit 4 — Gescheiden logboeken tenant ↔ platform

Tenant-handelingen in een tenant-scoped `audit_log` (FORCE RLS). Platform-handelingen in een apart
`platform_audit_log` op de `cd_platform`-rechtenlijn (geen RLS). De tenant-isolatie blijft daardoor
intact en platform-handelingen botsen niet met FORCE RLS.

### Besluit 5 — Onwijzigbaarheid op twee niveaus afgedwongen

(a) Rechten: `GRANT SELECT, INSERT` op de audit-tabellen aan de app-rol — **geen** `UPDATE`/`DELETE`.
(b) Backstop: een `BEFORE UPDATE OR DELETE`-trigger die `RAISE EXCEPTION` doet, zodat ook
eigenaar-/migratie-paden geblokkeerd zijn. Append-only is hiermee structureel, niet conventioneel.

### Besluit 6 — Hash-keten per tenant (geserialiseerde append)

Elk record draagt `vorige_hash` + `record_hash` (`record_hash = hash(vorige_hash ‖ alle
betekenisdragende velden)`). De keten is per tenant (RLS-consistent); het `platform_audit_log`
heeft zijn eigen (globale) keten. Een verificatiefunctie verifieert de keten.

**Serialisatie van de append (CD008 v4).** De append-sequentie {lees de ketenstaart (`vorige_hash`)
→ bereken `record_hash` → insert} wordt **per tenant geserialiseerd** met een transactie-gebonden
PostgreSQL advisory lock (`pg_advisory_xact_lock`, sleutel afgeleid van `tenant_id`), genomen in het
audit-append-pad vóór het lezen van de staart. Twee gelijktijdige schrijvers binnen één tenant
kunnen daardoor **niet** op dezelfde voorganger ankeren: een fork is **structureel onmogelijk**, en
een ketenbreuk bij verificatie betekent dus altijd manipulatie — nooit gelijktijdigheid. De
platform-keten gebruikt één vaste globale lock-sleutel. De lock serialiseert uitsluitend de
audit-append (niet de onderliggende bedrijfstransactie) en valt automatisch vrij bij
commit/rollback. (Dit vervangt de eerdere "detecteren-i.p.v.-voorkomen / één-schrijver-per-tenant"-
aanname door structurele preventie.)

### Besluit 7 — Wijziging = gewijzigde-velden-diff met oude én nieuwe waarde

`wijziging` (jsonb) bevat uitsluitend de veranderde velden in de vorm `{veld: {oud, nieuw}}`. Geen
volledige snapshot, geen alleen-nieuw.

### Besluit 8 — Vaste systeem-actoren met `system:`-voorvoegsel

Mutaties zonder menselijke gebruiker dragen een herkenbare vaste actor per herkomst, bv.
`system:platform_init`, `system:dev_seed` (en bij toekomstige achtergrondtaken `system:worker`).
Geen generieke "systeem".

### Besluit 9 — Retentie: append-only/onbeperkt bewaren

Auditrecords worden nooit verwijderd. Een bewaar-/partitioneringsbeleid (bv. tijd-partitie bij
groot volume) is bewust **geparkeerd** als later, apart besluit; buiten scope van dit ADR.

## Datamodel

Tenant-scoped `audit_log` (`platform_audit_log` analoog, zónder `tenant_id` en zónder RLS):

| Kolom | Type | Inhoud |
|---|---|---|
| `id` | uuid PK | — |
| `tenant_id` | uuid, NOT NULL, index | RLS-anker |
| `tijdstip` | timestamptz, default `now()` | wanneer |
| `actor_sub` | text, NOT NULL | Keycloak-subject (of `system:`-actor) |
| `actor_email` | text, nullable | leesbaarheid (mag verouderen) |
| `entiteit_type` | text, NOT NULL | bv. `checklistscore`, `blokkade`, `component_profiel` |
| `entiteit_id` | uuid, NOT NULL | geen harde FK — polymorf + historie-behoud |
| `actie` | enum | `create` / `update` / `delete` / `derive` |
| `wijziging` | jsonb | `{veld: {oud, nieuw}}` |
| `correlatie_id` | uuid, NOT NULL, index | bindt één handeling aan zijn gevolgen |
| `record_hash` | text | keten-hash |
| `vorige_hash` | text, nullable | eerste record per tenant: `null` |

Indexen: `tenant_id`, `correlatie_id`, (`entiteit_type`, `entiteit_id`).

**Verfijning (CD008 v2) — `platform_audit_log.entiteit_id` = `text`** (i.p.v. `uuid`). De
platform-catalogus (`componentconfig_optie`/`contractconfig_optie`) heeft integer-PK's; een
polymorfe, **koppelingsloze** tekstkolom draagt zowel UUID's (Tenant) als integer-catalogus-PK's
als string. Het tenant-`audit_log` houdt `entiteit_id uuid` (alle tenant-entiteiten hebben een
UUID-PK). De overige kolommen van `platform_audit_log` zijn gelijk aan `audit_log` op `tenant_id`
na (dat ontbreekt — geen RLS).

## Gevolgen / invarianten

- Elke compliance-mutatie ⇒ ≥1 auditrecord; één score-write ⇒ 1 driver-record + N afgeleide
  records met gedeeld `correlatie_id` en gedeelde actor.
- Append-only afgedwongen op grant + trigger; per-tenant keten verifieerbaar.
- De lees-API moet gebeurtenissen mét hun correlatie-gegroepeerde gevolgen kunnen teruggeven en
  filterbaar zijn op actor / component / entiteit-type / periode (zodat #14 niets hoeft te
  herbouwen).
- Nieuwe RBAC-entiteit `AUDITLOG` (alleen lezen, bv. auditor/beheerder).

### Capture-grens (ORM-only)

De capture-hook auditeert uitsluitend mutaties die via de servicelaag/ORM-sessie lopen. Hieruit
volgen twee expliciet geaccepteerde grenzen:

1. **Servicelaag/ORM-only voor auditeerbare entiteiten.** Compliance-relevante mutaties op
   auditeerbare entiteiten verlopen altijd via de servicelaag (ORM). Rauwe `text(UPDATE/DELETE)` op
   auditeerbare entiteiten is in applicatiepaden niet toegestaan, omdat die de capture omzeilt.
   Uitsluitend seed-/setup-paden (geen gebruikershandeling, bv. catalogus-seed) mogen rauwe SQL
   gebruiken; die genereren bewust geen auditrecord. Een latere overtreding (rauwe SQL op een
   auditeerbare tabel in een applicatiepad) is hiermee toetsbaar als afwijking van deze invariant.

2. **Cascade-delete legt alleen het ouder-record vast.** Bij het verwijderen van een ouder legt de
   audit-trail de ouder-delete vast (met correlatie-id); door de database via `ON DELETE CASCADE`
   meeverwijderde kinderen krijgen geen individueel auditrecord. De betekenisvolle handeling is de
   ouder-delete; het impliciet vervallen van afgeleide kinderen is een geaccepteerde grens.

## Niet in scope

Partitionering/bewaarbeleid (geparkeerd, los besluit). Cross-tenant audit-aggregatie.
