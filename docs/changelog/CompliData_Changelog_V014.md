# CompliData Changelog V014

**Datum**: 2026-06-19

## V014 — DC013 (2026-06-19)

### Nieuw
- complidata-domeinmodel skill (CC + claude.ai sessiestart)
- ADR-025: Landschapskaart v4 (Cytoscape.js, 3 modi, zoek/filter, actieve set,
  koppelingsdetails, migratieplaatsing, diepte-toggle)
- ADR-024: contract-leverancier verbreed, roltoewijzing vanuit partij,
  functietitel (persoon-only)
- ZoekSelect-standaard in complidata-frontend skill
- ADR-028 voorstel (componentrol + BIV, geparkeerd)
- LIKARA productnaam besloten

### Gewijzigd
- eigenaar_naam/leverancier vrije tekst verwijderd (migratie 0033/0034)
- Koppelingenkaart vervangen door Landschapskaart
- PartijFormulier organisatie-/afdelingskiezer → ZoekSelect
- 9 beheerrollen (was 7)
- complidata-domeinmodel/-frontend/-ux skills bijgewerkt (DC013-patronen)

### Technisch
- Cytoscape.js geïnstalleerd (runtime-dependency)
- Migratie head: 0034
- Backend: 810 tests · Frontend: 440 tests (52 files)
