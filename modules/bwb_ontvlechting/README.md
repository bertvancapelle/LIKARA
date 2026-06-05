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
