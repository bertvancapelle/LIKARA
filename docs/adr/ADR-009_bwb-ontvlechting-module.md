# ADR-009 — BWB-ontvlechtingsmodule: scope en datamodel

| | |
|---|---|
| **Status** | Voorgesteld — open vragen openstaand (zie §Open vragen) |
| **Datum** | 2026-06-05 |
| **Beslissers** | Bert van Capelle (Eraneos) |
| **Gerelateerd** | ADR-001 (module-structuur), ADR-003 (RLS), ADR-005 (API), ADR-008 (blob) |

## Context

`bwb_ontvlechting` is de **eerste functionele module** van CompliData. De
modulenaam en het bestaan ervan staan vast (CLAUDE.md); de **functionele scope
en het datamodel zijn nog niet door Eraneos vastgelegd** en kunnen niet uit de
codebase worden afgeleid.

> **Aanname, te bevestigen:** "BWB" verwijst naar het **Basiswettenbestand**
> (de geconsolideerde wet- en regelgeving van de Nederlandse overheid), en
> "ontvlechting" betreft het gecontroleerd inventariseren, analyseren en
> voorbereiden van overdracht/migratie van data die nu met de BWB verweven is.
> Deze aanname stuurt de rest van deze ADR en moet worden bevestigd of
> gecorrigeerd voordat de status naar *Aanvaard* gaat.

Deze ADR legt nu vast wat **platform-bepaald** al zeker is, en markeert het
domein-deel expliciet als open.

## Besluit (platform-bepaald deel — al zeker)

### B1 — Plaatsing en isolatie
De module leeft onder `modules/bwb_ontvlechting/` (`backend/`, `frontend/`,
`migrations/`) conform ADR-001 B2/B4. Geen code-afhankelijkheden naar andere
modules.

### B2 — Tenant-scoping
Alle module-tabellen zijn tenant-scoped: `tenant_id` + `ENABLE`/`FORCE ROW
LEVEL SECURITY` + `tenant_isolation`-policy (ADR-003). Elke query in
module-code bevat een expliciete `tenant_id`-filter naast RLS.

### B3 — API
Module-endpoints onder `/api/v1/...`, geregistreerd in `backend/app/main.py`.
Cursor-paginering en het standaard foutformaat (ADR-005). Server-only velden
(`tenant_id`, `id`, timestamps) nooit in input-schemas; Pydantic
`extra='forbid'` op alle schemas.

### B4 — Bestandsopslag (indien van toepassing)
Brondocumenten/bewijs worden opgeslagen via de blob-store (MinIO,
bucket-per-tenant, ADR-008) — nooit directe S3-toegang buiten de
applicatielaag.

### B5 — Audit
Mutaties op ontvlechtings-data worden vastgelegd in een append-only,
hash-chained audit trail (ADR-006).

## Datamodel — TE BEPALEN

Het concrete datamodel wordt vastgesteld zodra de open vragen hieronder zijn
beantwoord. **Bewust nog geen tabellen/entiteiten gedefinieerd** om foutieve
aannames over het BWB-domein te vermijden. Na beantwoording volgt hier:
entiteiten, relaties, statussen/lifecycle, en de bijbehorende Alembic-migraties
in `modules/bwb_ontvlechting/migrations/`.

## Open vragen (te beantwoorden door Bert / Eraneos)

1. **Domein** — Klopt de aanname dat BWB = Basiswettenbestand? Zo niet, wat is
   de juiste betekenis en broncontext?
2. **Doel van "ontvlechting"** — Wat is de concrete uitkomst die de module
   levert? (bijv. inventarisatie van objecten, migratie-analyse,
   overdrachtsdossier, impact-analyse — of iets anders)
3. **Bron(nen)** — Uit welk(e) systeem/systemen komt de data? Hoe komt die
   binnen (handmatige upload, API-koppeling, bestandsimport)?
4. **Kern-entiteiten** — Welke objecten beheert de module? (de CLAUDE.md noemt
   `applicaties` als voorbeeld — is dat een echte entiteit, en welke andere?)
5. **Workflow/lifecycle** — Doorlopen records statussen? Is er een vier-ogen-,
   review- of goedkeuringsstap?
6. **Gebruikers/rollen** — Welke rollen werken met de module? (samenhang met
   ADR-010 RBAC)
7. **Output/levering** — Wat is het eindproduct (rapport, export, dossier) en
   in welk formaat?

## Gevolgen

- Tot de open vragen zijn beantwoord blijft deze ADR *Voorgesteld* en wordt er
  **geen** module-code of migratie geschreven (conform ADR-001 B4: module volgt
  op vastgestelde scope).
- Het platform-bepaalde deel (B1–B5) ligt vast en verandert niet door de
  domein-antwoorden; alleen het datamodel en de functionele scope worden
  ingevuld.

## Alternatieven overwogen

Niet van toepassing zolang de functionele scope open is; alternatieven voor het
datamodel worden afgewogen zodra de domein-input beschikbaar is.
