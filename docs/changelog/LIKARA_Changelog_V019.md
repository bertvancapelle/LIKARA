# LIKARA Changelog V019

**Datum**: 2026-06-23
**Sessie**: LI018

## Wijzigingen

### Landschapskaart
- Edge-labels standaard verborgen, zichtbaar op hover en bij geselecteerde edge;
  dagre hiërarchische layout voor Geheel model + Impact-view (cytoscape-dagre);
  ego-view behoudt de radiale layout; node-breedte op labelbreedte.
- Actieve set: zoekbalk in de resultatenlijst (filter op naam, teller "N van M"),
  "Wis alles"-knop, en "Focus op actieve set"-toggle (graph toont alleen set-nodes +
  directe buren; schakelt automatisch uit bij lege set).

### Architectuur (ArchiMate F-2)
- Visuele ArchiMate-lagenweergave naast de tabel (toggle Tabel/Lagen, default Lagen):
  gekleurde lagenbands (Business/Applicatie/Technologie/Migratie), klikbare pills met
  aspect-stijl (active/passive/behavior), migratie-toggle + aspect-filter + legenda.
- Partij-naam-fix in `architectuur_service` (partij_self-join); `partij_aard` read-only
  veld; partij toegevoegd aan de type-filter + klikbaar.

### Contracten — hiërarchie-navigatie
- Deelcontracten-sectie op mantelcontract-detail verrijkt met leverancier + gekoppelde
  applicaties (klikbaar).
- Contractketen-breadcrumb op applicatie/component-detail (App → Contract → Mantelcontract).
- Mantelcontract-link toont de mantelnaam.
- Fix: ContractDetail miste een `watch` op `props.id` → contract→contract-navigatie
  (deelcontract-/mantel-links) herlaadde niet; nu gelijk aan de andere detail-views.

### Skills / docs
- complidata-db/frontend/backend SKILL.md bijgewerkt (Laag 2 identifiers lk_*/likara,
  detail-view props.id-watch-patroon, useTerugNavigatie, Landschapskaart-state/ringen,
  ArchitectuurLagenView, architectuur_service partij-naam-fix, contracthiërarchie).
- ADR-032 "Start vanuit..."-wijzer (voorstel) vastgelegd; OPVOLGPUNTEN.md LI018-sectie.

### Engine-invariant
- Alle wijzigingen read-only / afgeleid; engine onaangeroerd; geen schema/migratie.
