# CompliData — Implementatieplan

**Eigenaar**: G. van Capelle Beheer B.V.
**Build bij aanmaak**: V001
**Laatste update**: 2026-06-05

---

## Platformvisie

CompliData is een generiek platform voor data-inventarisatie
en migratievoorbereiding voor Nederlandse overheidsorganisaties.
De kern van het platform is de gestructureerde checklistmethodiek:
12 categorieën, 89 vragen, lifecycle-statussen en koppelingenlogica
die universeel toepasbaar zijn op elke organisatie die een
applicatielandschap moet inventariseren of ontvlechten.

De infrastructuur (PostgreSQL, Keycloak, RabbitMQ, MinIO) maakt
het platform mogelijk. De methodiek maakt het waardevol.

BWB (Bedrijfsvoeringsorganisatie West-Betuwe) is de eerste
tenant die het platform gebruikt voor de ontvlechting van
gemeente Tiel. De BWB-usecase illustreert de toepassing —
zij definieert haar niet.

---

## Architectuurprincipe: platform-seeddata vs. tenant-configuratie

| Onderdeel | Type | Toelichting |
|---|---|---|
| 89 checklistvragen | Platform-seeddata | Zelfde voor alle tenants — kern van de methodiek |
| 12 categorieën | Platform-seeddata | Universeel toepasbaar |
| Lifecycle-statussen | Platform-code | In service-laag gehandhaafd |
| Organisatienamen | Tenant-configuratie | Per tenant anders (BWB, Tiel, etc.) |
| Gebruikers en rollen | Tenant-data | Per tenant beheerd |
| Applicatieregister | Tenant-data | Per tenant gevuld |

---

## Architectuurcorrectie V001 — ChecklistVraag als platform-initialisatie

**Bevinding**: `seed_checklist_vragen()` wordt momenteel
aangeroepen als tenant-seeddata. De 89 vragen zijn echter
platform-breed en horen bij de initiële platform-setup.

**Correctie** (te implementeren in V002):
- `seed_checklist_vragen()` verplaatsen naar platform-initialisatie
- Aanroepen bij `alembic upgrade head` voor het gehele platform
- Niet aanroepen bij tenant-onboarding
- `ChecklistVraag` tabel bevat altijd dezelfde 89 vragen voor
  alle tenants

---

## Bouwstatus per onderdeel

### Fundament (V001 — gereed)

| Onderdeel | Status | Commit |
|---|---|---|
| Platform-extractie uit framework | ✅ Gereed | 0bcceb9 |
| Runnable scaffold (health, auth stub) | ✅ Gereed | 3ca36e0 |
| UI design system (PrimeVue + tokens) | ✅ Gereed | 117e998 |
| ADR-001 platform-architectuur | ✅ Gereed | e740bc7 |
| ADR-009 BWB-module scope en datamodel | ✅ Gereed | e740bc7 |
| Eigenaarschap G. van Capelle Beheer B.V. | ✅ Gereed | 5fc0c10 |
| Module skeleton bwb_ontvlechting | ✅ Gereed | 21e7dbd |
| SQLAlchemy-modellen (6 entiteiten) | ✅ Gereed | 3f09eb2 |
| Alembic-migratie 0001 + RLS + indexen | ✅ Gereed | 3f09eb2 |
| 89 checklistvragen seeddata | ✅ Gereed | 3f09eb2 |
| Alembic wiring (platform + module) | ✅ Gereed | f19233a |
| Sessie-afsluit infrastructuur | ✅ Gereed | e32fba7 |
| CompliData-skills (6 stuks) | ✅ Gereed | 5c0707b |
| Geen CompliMan-referenties | ✅ Gereed | 45ecf0c |

### Laag 1 — Platform-initialisatie (V002)

| Onderdeel | Status | Prioriteit | Toelichting |
|---|---|---|---|
| ChecklistVraag seed verplaatsen naar platform-init | 📋 Gepland | HOOG | Architectuurcorrectie — zie boven |
| Keycloak PKCE login/callback (ADR-002) | 📋 Gepland | HOOG | /auth/login + /auth/callback |
| RBAC rollenstructuur (ADR-010) | 📋 Gepland | HOOG | _load_roles() invullen — Viewer/Medewerker/Beheerder/Auditor |
| Tenant-onboarding flow | 📋 Gepland | HOOG | Nieuwe tenant aanmaken, Keycloak realm config |

### Laag 2 — Module CRUD-laag (V002/V003)

| Onderdeel | Status | Prioriteit | Toelichting |
|---|---|---|---|
| Applicatie CRUD endpoints | 📋 Gepland | HOOG | GET/POST/PUT/DELETE /api/v1/applicaties |
| Datatype CRUD endpoints | 📋 Gepland | HOOG | Genest onder applicatie |
| Gebruikersgroep CRUD endpoints | 📋 Gepland | HOOG | Genest onder applicatie |
| Koppeling CRUD endpoints | 📋 Gepland | HOOG | Bron + doel uit applicatielijst |
| Checklistscore CRUD endpoints | 📋 Gepland | HOOG | Per applicatie × vraag_code |
| Blokkade CRUD endpoints | 📋 Gepland | HOOG | Afgeleid van checklistscore |
| Lifecycle-handhaving service-laag | 📋 Gepland | HOOG | Status herberekenen bij score/blokkade-wijziging |
| Audit trail (ADR-006) | 📋 Gepland | HOOG | Hash-chained, append-only |

### Laag 3 — Bulkimport en export (V003)

| Onderdeel | Status | Prioriteit | Toelichting |
|---|---|---|---|
| Excel/CSV bulkimport applicaties | 📋 Gepland | HOOG | 150+ applicaties initieel laden |
| Import-validatie per rij | 📋 Gepland | HOOG | Pydantic + foutrapportage per rij |
| Bestandsopslag via MinIO (ADR-008) | 📋 Gepland | MIDDEN | Upload → blob store → verwerking |
| Export naar Excel/CSV | 📋 Gepland | HOOG | Rapportage voor bestuurlijk besluitstuk |
| PDF-export per applicatie | 📋 Gepland | MIDDEN | Overdrachtsvoorbereiding per applicatie |

### Laag 4 — Frontend module-views (V003/V004)

| Onderdeel | Status | Prioriteit | Toelichting |
|---|---|---|---|
| Login-view (PKCE-flow) | 📋 Gepland | HOOG | Keycloak redirect |
| Dashboard | 📋 Gepland | HOOG | Voortgang, statistieken, openstaande blokkades |
| Applicatieregister (lijst + filter) | 📋 Gepland | HOOG | 150+ applicaties, sorteerbaar/filterbaar |
| Applicatie detailpagina (12 tabs) | 📋 Gepland | HOOG | Één tab per categorie |
| Koppelingenkaart | 📋 Gepland | MIDDEN | Visuele weergave applicatie-relaties |
| Blokkadesoverzicht | 📋 Gepland | HOOG | Alle open/in-behandeling blokkades |
| Auditlog-view | 📋 Gepland | MIDDEN | Alleen zichtbaar voor Auditor |
| Gebruikersbeheer | 📋 Gepland | MIDDEN | Alleen voor Beheerder |

### Laag 5 — Productie-gereedheid (V004/V005)

| Onderdeel | Status | Prioriteit | Toelichting |
|---|---|---|---|
| docker-compose.prod.yml | 📋 Gepland | HOOG | Productie-configuratie |
| SSL/TLS certificaat configuratie | 📋 Gepland | HOOG | Let's Encrypt of eigen cert |
| Keycloak MFA configuratie | 📋 Gepland | HOOG | TOTP verplicht in productie |
| Live DB-run + RLS-isolatietest | 📋 Gepland | HOOG | Eerste echte alembic upgrade head |
| Smoke test uitbreiden | 📋 Gepland | MIDDEN | Meer dan 4 checks |
| Branding-tokens bijwerken | 📋 Gepland | LAAG | Wanneer huisstijl bekend is |

---

## Referentie-implementaties

### BWB Data-ontvlechting (eerste tenant)

**Context**: Gemeente Tiel treedt uit Bedrijfsvoeringsorganisatie
West-Betuwe (BWB). CompliData ondersteunt de inventarisatie en
migratievoorbereiding van het BWB-applicatielandschap (~150+ apps).

**Module**: `modules/bwb_ontvlechting/`

**Tenant-specifieke configuratie**:
- Organisatienamen: Tiel, Culemborg, West-Betuwe, BWB, extern
- Programmaperiode: juni – oktober 2026 (fase 1)
- Rapporteert aan: CTMH Interim en Advies (programmaleiding)

**Methodiek**: identiek aan alle andere tenants — 89 vragen,
12 categorieën, platform-seeddata.

---

## ADR-register (relevant voor implementatie)

| ADR | Onderwerp | Status |
|---|---|---|
| ADR-001 | Platform-architectuur en module-structuur | Aanvaard |
| ADR-002 | Zero Trust IAM (Keycloak PKCE) | Aanvaard — nog niet gebouwd |
| ADR-003 | Multi-tenant isolatie + RLS | Aanvaard — geïmplementeerd |
| ADR-004 | JWT sessiebeveiliging (httpOnly cookies) | Aanvaard — geïmplementeerd |
| ADR-005 | OAS3 API-architectuur | Aanvaard — nog niet volledig gebouwd |
| ADR-006 | Audit trail hash-chaining | Aanvaard — nog niet gebouwd |
| ADR-007 | RabbitMQ messaging | Aanvaard — framework aanwezig, geen consumers |
| ADR-008 | MinIO blob-opslag | Aanvaard — nog niet gebouwd |
| ADR-009 | BWB-ontvlechtingsmodule scope en datamodel | Aanvaard — fundament gebouwd |
| ADR-010 | RBAC en rollenstructuur Keycloak | Aanvaard — nog niet gebouwd |
