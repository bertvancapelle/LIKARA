# LIKARA Changelog V036

**Datum**: 2026-07-09

## Wijzigingen

### Lijststaat-patroon (terugnavigatie, `9128a24` + feitenrapport `233cc0c`)
- `useLijstStaat`-composable: filter/zoek/sortering blijven behouden over een detail-bezoek
  én een reload heen (sessionStorage-momentstaat; precedentie deep-link > bewaard > default;
  cursor nooit mee). Aangesloten op de partij-, component-, contract- en proces-lijst.

### ADR-042 — Procesregister + component-in-proces (volledig, 5 slices; docs `2ff8fa9`)
- **Slice 1 (`cc43418`)**: `proces` als nestbaar element-subtype (self-FK RESTRICT,
  cycluspreventie, 409 bij deelprocessen; migraties 0056/0057) + subboom-leestraversal.
- **Slice 2+3 (`ddb7b7a`)**: `applicatiefunctie_optie`-platformcatalogus (GEMMA-geënte
  startset, migratie 0058) + koppelregel `procesvervulling` — het tripel (component, proces,
  applicatiefunctie), component-breed, meerdere functies = losse regels (migratie 0059).
- **Slice 4a (`3a65c3b`)**: Processen-lijst (boomweergave, zoek-open) + proces-detail met
  koppelregels; regel-acties-patroon (bewerk-dialog + BevestigVerwijderDialog) en
  MeldingBanner gevestigd; band-dekking-audit omgebouwd naar ORM-paden.
- **Slice 4b (`0c4fe60`)**: componentkant — vier-vragen-Overzicht (wat is dit / wie is
  verantwoordelijk / waarvoor gebruiken we het / hoe staat het ervoor), ComponentFormulier
  als overlay met verzamel-procesregels + retry-pad; Dialog-primitive verbeterd (vaste
  kop/voetbalk via #footer-slot + min-h-0, tweezijdige CSS-scroll-schaduw in primair-blauw,
  breedte-override-borging).
- **Slice 5 (`8a76f55`)**: roll-up-inzicht — samengevoegd blok "Onderliggende processen"
  (kopje per deelproces, tak_id-groepering, pad-bijschrift bij diepere lagen,
  open-tenzij-groot met onthouden uitklapstand) + organisatie-proceskijk (afgeleid beeld via
  eigendom + geregistreerd gebruik, dedupe per proces) + succes-toast-standaard
  (`toastSucces` op de 8 stille acties). Read-only leeslaag met dubbele engine-borging.

### Patronen + skills
- Zes browsercheck-bevindingen omgezet in systeembrede patronen (geen punt-fixes);
  LI035-patronen + correcties (CD004-scope, beheerrol = dimensie op `relatiekenmerk_optie`,
  AppLayout-testlocatie, IMPACT_RINGEN afgeschaft) vastgelegd in de acht likara-skills.
- CSS-borging uitgebreid: token-verwijzings-check (fallback-loze `var(--lk-…)`) in de
  css-build-check; globale CLAUDE.md-committrailer geactualiseerd (Claude Fable 5).

### Teststand
Backend **997 passed / 2 skipped** · frontend **80 files / 965 groen** · migratie-head
**0059** · TST-V036: 0 kritieken.
