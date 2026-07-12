# LIKARA Changelog V039

**Datum**: 2026-07-12

## Wijzigingen

### Proces-only structuurbeeld (LI038, 3 gates — frontend + read-side, geen schema)
- **Boom | Diagram-schakelaar** op het processen-scherm; het Diagram is een strikt proces-only
  structuurbeeld (`ProcesDiagram.vue`, api-vrij: volledige set + gap-cue als props). Zoeken →
  proces centraal met ouderketen (boven), subboom (beneden) en zusjes (opzij) via de pure
  afleiding `procesFocusSet` (`procesBoom.js`). (`82806ff`)
- **ZoekSelect-bouwsteen-fix (picker-regel 4):** een gekozen waarde is een **label, geen
  zoekfilter** — klik op een al-gefocust veld opent de volledige lijst; nieuw ×-wis-gebaar
  ("Wis en zoek opnieuw"), platform-breed geërfd door alle pickers. (`82806ff`)
- **Klik-popup** (enkele klik = kijken): oranje selectie incl. verbindingen; naam, klikbare
  plek-in-woorden, eerlijke gap-cue; drie gescheiden uitgangen — "Toon hele processenlandschap"
  (binnen het beeld), "Bekijk op de kaart →" (bewuste overstap via de bestaande handoff),
  "Open proces →". **`useSleepbaar`** geconvergeerd als dé gedeelde overlay-sleep-bouwsteen;
  kaart-legenda en kaart-popup draaien er nu ook op. (`e91f2a2`)
- **Dubbelklik-inzoom op proces-ids** (`procesSubboomSet`: proces + subboom; werkt óók bij 0
  kinderen/0 vervullers) + snapshot+cursor-history met "← Terug"; **"Toon in procesbeeld"**
  als rij-actie in de Boom (neutraal openen, plek behouden via `centrumGewijzigd`). (`f1d3270`)

### ADR-043 — Bedrijfsfunctie als logische ruggengraat (herijkt ADR-042)
- De "waarvoor"-as verschuift van **proces** naar **bedrijfsfunctie** (ArchiMate
  BusinessFunction); **referentiemodel** wordt een eerste-klas begrip (GEMMA = instantie 1;
  bronsleutel = identiteit; vervallen ≠ verwijderen; motor generiek, aanbod gesloten).
  Procesregister in de MVP **verborgen, niet verwijderd** (LI038-bouw wordt hergebruikt).
  Grond: `Feitenrapport-referentiemodel-bedrijfsfuncties-V038.md`. (`6c49ed3`)

### Borging
- **Skill-review** (4 likara-skills): kernles *"een regel in de skills is geen borging — een
  gedeelde bouwsteen dwingt af"*, useSleepbaar/ZoekSelect-faalmodus, proces-only-beeldpatronen,
  ADR-043-terrein. (`d7df7e3`)
- Checkpoint-feitenrapport proces-only structuurbeeld. (`97d5b69`)

### Kwaliteit
- Tests: backend **1001 (2 skipped)** · frontend **84 files, 1089 groen** (+43 nieuwe tests) ·
  0 kritieken (`TST-V039-Validatierapport.md`).
- Migratie-head ongewijzigd: `0059_adr042_procesvervulling`.
