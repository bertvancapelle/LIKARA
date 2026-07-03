# Architecture Decision Records — LIKARA

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
| ADR-006 | Audit-trail: append-only wijzigingsspoor, app-niveau capture, per-tenant hash-keten | Aanvaard, geïmplementeerd (Fase A–E) |
| ADR-009 | BWB-ontvlechtingsmodule — scope en datamodel | Aanvaard |
| ADR-011 | Deploy- en migratiestrategie: aparte init-container | Aanvaard |
| ADR-012 | Tweelaags rollenmodel: platform- en tenant-rollen met strikte scheiding | Aanvaard |
| ADR-013 | Lifecycle-herberekening (Model A): afgeleide blokkades + deterministische status | Aanvaard |
| ADR-014 | Canoniek foutformaat: 401 gelijktrekken, 422 bewust native | Aanvaard |
| ADR-015 | Refresh-token-subsysteem: Keycloak-gedelegeerd, Redis-opslag | Aanvaard |
| ADR-016 | Blokkade-`opgelost` volledig afgeleid (amendeert ADR-013 B1) | Aanvaard |
| ADR-017 | Server-side sorteerbare keyset-paginering (allowlist + zelfbeschrijvende cursor) | Aanvaard |
| ADR-018 | Relatievisualisatie: gefocuste ego-graaf, geen graaf-dependency | Aanvaard |
| ADR-019 | Configureerbare antwoordopties per checklistvraag (additioneel veld, score behouden) | Aanvaard |
| ADR-012 Addendum A | `PlatformEntiteit.CHECKLISTCONFIG` | Aanvaard |
| ADR-020 | Leverancier- en contractregister (registratief; koppeling applicatie ↔ contract) | Aanvaard |
| ADR-012 Addendum B | `PlatformEntiteit.CONTRACTCONFIG` | Aanvaard |
| ADR-021 | Component-herfundering: supertype Component + landschapsgraaf (subtype `Applicatie` ontbonden in LI059 — applicatie = componenttype) | Aanvaard — gerealiseerd t/m LI059 |
| ADR-012 Addendum C | `PlatformEntiteit.COMPONENTCONFIG` | Aanvaard |
| ADR-022 | Beoordelingsprofiel / checklist per componenttype (incl. Wijziging W1 — tenant-eigendom vragenset) | Aanvaard — gerealiseerd t/m LI059 |
| ADR-023 | ArchiMate-uitlijning: element-identiteit, getypeerd relatiemodel, migratielaag | Aanvaard (besluit), implementatie in deze opdracht |
| ADR-037 | Verantwoordelijke per checklistantwoord (afdeling-dan-persoon; vervangt vrije-tekst `eigenaar`, blokkade-eigenaar afgeleid) | Aanvaard — Pass 1 gerealiseerd (schema-gate), Pass 2 volgt |

> **Component-focus-herfundering (LI057–LI059, migraties 0045–0047):** `migratiepad/complexiteit/prioriteit`
> zijn component-breed, de `applicatie`-subtabel is gedropt en de applicatie-**facade** (routes/service/
> schema + `Entiteit.APPLICATIE`/audit-allowlist/objecthistorie-tak) is volledig opgeheven. Een component
> met `componenttype='applicatie'` ÍS de applicatie — `component` is de enige bron in data/API/RBAC/audit.
> Zie de slotsecties "Eindstaat" in ADR-021 en ADR-022.

ADR-002 t/m ADR-005, ADR-007, ADR-008 en ADR-010 zijn gereserveerd (zie `CLAUDE.md` →
ADR-referentie) en worden geschreven wanneer de betreffende beslissing speelt.
