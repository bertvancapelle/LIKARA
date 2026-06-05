# Architecture Decision Records — CompliData

ADR's leggen significante architectuur- en scope-beslissingen vast. Eén bestand
per beslissing, oplopend genummerd, nooit hergebruikt of verwijderd (vervallen
beslissingen krijgen status `Vervallen` met verwijzing naar de opvolger).

## Conventie

- Bestandsnaam: `ADR-NNN_kebab-case-titel.md`
- Status: `Voorgesteld` → `Aanvaard` → (`Vervangen door ADR-XXX` | `Vervallen`)
- Vaste secties: **Status/metadata**, **Context**, **Besluit**, **Gevolgen**,
  **Alternatieven overwogen**
- Operator en platformnaam nooit hardcoden in code — ADR's mogen ze
  uiteraard benoemen.

## Register

| ADR | Titel | Status |
|---|---|---|
| ADR-001 | Platform-architectuur en module-structuur | Aanvaard |
| ADR-009 | BWB-ontvlechtingsmodule — scope en datamodel | Aanvaard |

ADR-002 t/m ADR-008 en ADR-010 zijn gereserveerd (zie `CLAUDE.md` →
ADR-referentie) en worden geschreven wanneer de betreffende beslissing speelt.
