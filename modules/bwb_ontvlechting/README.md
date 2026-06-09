# Module — BWB-ontvlechting

Eerste functionele module van CompliData. Inventariseert het applicatie- en
datalandschap van de **Bedrijfsvoeringsorganisatie West-Betuwe (BWB)** en
bereidt de ontvlechting/overdracht voor bij de uittreding van gemeente Tiel.

Scope, datamodel en lifecycle: zie **`docs/adr/ADR-009_bwb-ontvlechting-module.md`** (Aanvaard).
Platform-architectuur en module-conventies: **`docs/adr/ADR-001_platform-architectuur.md`**.

## Structuur

```
backend/
  routes/     — FastAPI APIRouters (geregistreerd in backend/app/main.py onder /api/v1)
  models/     — SQLAlchemy models (tenant-scoped, RLS + FORCE)
  services/   — business-logica + lifecycle-handhaving
  schemas/    — Pydantic v2 schemas (extra='forbid', gescheiden Create/Update/Read)
frontend/
  views/      — Vue 3 views (PrimeVue Unstyled + design tokens)
  store/      — Pinia stores
migrations/   — Alembic-migraties van de module
```

## Status

Skeleton aangemaakt (V001, sessie ADR-009). **Nog geen model-code of migraties** —
die volgen na beoordeling van ADR-009.

## Checklist-antwoordconfiguratie (ADR-019) — domeinvocabulaire (O1)

De checklist-antwoordopties (ADR-019, fasen 2A–2E) bevatten **bewust** termen uit het
BWB-ontvlechtingsdomein, waaronder organisatie-/gemeentenamen:

- `BWB` / `Tiel` / `Gedeeld` bij eigenaarschap en contractpartij (vragen 1.3, 1.4, 8.1);
- `Tiel · BWB · Culemborg · West-Betuwe` bij gebruikende organisaties (3.1);
- `BWB · Tiel · Derde partij` bij koppeling-eigendom (5.6, 6.6);
- `Overdracht Tiel · Overname BWB · …` bij het ontvlechtingsscenario (11.1).

**Dit is géén hardcoded operator-/tenantnaam in de codelogica.** Het zijn
**referentiedata** (`checklistvraag_optie`) en sinds fase 2D/2E **door de
platformbeheerder configureerbaar** via `/api/v1/platform/checklistconfig`
(opties toevoegen, label/volgorde wijzigen, soft-deactiveren). Daarmee verzoend met
de "namen-niet-hardcoden"-regel uit `CLAUDE.md`: de engine en code bevatten geen
gemeente-specifieke logica; het zijn aanpasbare, platform-brede default-opties die per
deployment kunnen worden bijgesteld. De afgeleide sets (2.1 ← `HostingModel`,
12.1 ← `NiveauEnum`) zijn single-source en in de beheer-UI structureel read-only
(alleen het label aanpasbaar) — ADR-019 Besluit 12.
