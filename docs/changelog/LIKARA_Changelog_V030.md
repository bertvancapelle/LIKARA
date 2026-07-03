# LIKARA Changelog V030

**Datum**: 2026-07-03

## Wijzigingen

**ADR-036 + Velduitleg + ADR-036a — organisatiegebruik end-to-end + afdeling structureel.**

- **ADR-036 (`8e7e419`, `bff1254`, `889fc4d`):** grof "organisatie gebruikt applicatie"-feit
  (`organisatiegebruik`) + gebruikersgroep als fijne verfijning (`gebruik_id`); kaart-afleiding
  "gebruikt door", read-only signaal "gebruik bekend, detaillering ontbreekt", identiteit
  "afdeling — organisatie"; invariant-test "afdeling-met-org ⟹ grof feit".
- **Velduitleg (`7cc6e24`, `8ea87be`):** `VeldUitleg`-component + centrale `velduitleg.js`; popover-'i'
  uitgerold over alle formulieren.
- **ADR-036a (`480fa84`, `a09a8cb`, migratie 0050):** afdeling structureel — `gebruikersgroep.afdeling`
  (vrije tekst) → `afdeling_id` composiet-FK → organisatie_eenheid-partij binnen de grove-feit-organisatie
  (ON DELETE RESTRICT); search-first afdeling-picker (aanmaken in de lege zoekstaat).
- **UI-fixes:** bewerken-voorvulling gebruikersgroep (`929435e`) — organisatie voorvullen uit grof feit
  + `initieel-weergave`; contract-leverancier-picker versmald (`0e439d3`) naar
  `aard_in=[organisatie, organisatie_eenheid, externe_partij]`, seed geverifieerd geldig.
- **Onderzocht, geen wijziging:** eigenaar-organisatie-picker (geen defect — stale seed-data).
- **Skill-reconciliaties:** signaaltelling gecorrigeerd naar 9 (3 kritiek / 6 aandacht); relatie-facade
  doet géén bron/doel-typevalidatie (vastgelegd).

**Tests:** backend 914/2/0 · frontend 763 groen. **Migratie-head:** `0050_adr036a_gg_afdeling`.
**TST:** `docs/TST-V030-Validatierapport.md` — 0 kritieke bevindingen.
