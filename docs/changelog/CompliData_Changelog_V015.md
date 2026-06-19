# CompliData Changelog V015

**Datum**: 2026-06-19
**Sessie**: DC014
**Migratie head**: 0036 (geen schema-wijziging deze build)
**Tests**: 833 backend + 474 frontend groen · 0 kritieken

## Wijzigingen

### ADR-027 — component-klaarverklaring COMPLEET
- **Slice 2 — UI** (`979a646`): herbruikbaar `MigratiegereedheidSectie`-blok op ApplicatieDetail
  (tab Overzicht): status-Tag (klaar/open) + wie/wanneer + reden + afwijkingssignaal; knop
  "Klaar verklaren"/"Heropenen" met verplichte reden (rol-gegate, verbergen). Hergebruikt de
  bestaande vragen-stand (geen tweede telling).
- **Slice 3 — dashboard** (`6ffd7e6`): twee read-only tellingen op `GET /dashboard`
  (`klaar_verklaard`, `klaar_met_afwijking`) + klikbare tegels → componentlijst gefilterd
  (`klaarverklaring=klaar` / `afwijking=1`). Het afwijkingsgeval is puur de join van de
  klaar-status met de bestaande `lifecycle_status` (compleet ⟺ ∈ {migratieklaar, geblokkeerd}) —
  geen tweede telling, engine ongemoeid (live geverifieerd).

### Catalogi-beheer-schuld gedicht (`ed51d36`)
- **vraagbetekenis_optie** + **partijsoort_optie** beheerbaar (platform-beheer-endpoints +
  schermen + nav; 2 nieuwe platform-entiteiten; grants bestonden al → geen migratie).
- **`checklist_dragend`-toggle** op ComponentConfigBeheer + **read-only-invariant**: een gesloten
  checklist (`checklist_dragend=false`) blokkeert score-INVOER (422 `CHECKLIST_GESLOTEN`) zonder
  de engine te raken; bestaande antwoorden blijven leesbaar (velden disabled + banner).
- **`kenmerk_definitie` read-only viewer**: modeldefinitie (ADR-023), code-eigendom — inzien mag,
  bewerken niet.

### Skills + docs
- Skills bijgewerkt naar V015 (ux/backend/db/frontend/domeinmodel): read-only-bij-sluiten,
  twee-assen read-only afleiding, niet-scorende registratie naast de engine, "geseed ≠
  beheercatalogus", functioneel-first als norm, één-tenant-nu (geen per-tenant-differentiatie).
- OPVOLGPUNTEN: ADR-027 afgevinkt; 3 nieuwe punten (klaarverklaring-blok op ComponentDetail,
  dode `<dl>`-rijen ApplicatieDetail, CLAUDE.md interactie-secties consolideren).

### Geen schema-migratie
Alle V015-werk draait op bestaande kolommen/grants; migratie-head blijft 0036.
