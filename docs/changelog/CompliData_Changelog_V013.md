# CompliData Changelog V013

**Datum**: 2026-06-18

Sessie DC012 — ADR-024-vervolg (rol-toewijzing), volledige UX-doorlichting gedicht
(A1–A4 + B1–B6), migratielaag-CRUD compleet, en "organisatie" overal als verwijzing
naar het partijenregister. Migratieketen t/m **`0032`** (`0029`–`0032`).

## Wijzigingen

### ADR-024 — Rol-toewijzing (slice 2b)
- **Rol-toewijzing** (`7d99ab0`, migraties **0029/0030**): partij vervult een rol op een object
  (component/contract). Eigen tenant-scoped tabel `roltoewijzing` (`UNIQUE(tenant,partij,object,rol)`)
  i.p.v. de relatie-facade — meerdere rollen per (partij,object) als losse regels (tegengestelde
  uniciteit; les geland in `complidata-db`). Rol uit de `beheerrol`-catalogus. `VerantwoordelijkheidSectie`
  (op component-/contract-detail) + `PartijRollenSectie` (read-only op partij-detail).

### complidata-ux-skill
- **Skill geland** (`d767e15`): interaction-design-denkmethode (gebruikersdoel · CRUD-op-de-juiste-plek ·
  lege-staten-met-route · terminologie · consistentie), verplicht bij elke frontend-rakende slice. In
  het sessiestart-protocol opgenomen.

### UX-doorlichting — reparatie-slices
- **A1** beheerrollen beheerbaar in de UI (catalogus-beheerscherm voor `beheerrol`).
- **A2/A3** leden (persoon/afdeling) toevoegen vanaf de organisatie/afdeling, met voorinvulling van de
  context + terugkeer naar de ouder na opslaan.
- **A4-1…4** migratielaag volledig beheerbaar in de UI: plateau, werkpakket, deliverable, gap
  (aanmaken/wijzigen, baseline/doel, leden, readiness).
- **B-bundel B1–B5** (`33a5f85`): lege-staat-pointer (partij-rollen); doorklik op architectuuroverzicht
  + plaatsingsignalen; gebruikerstaal i.p.v. jargon (ArchiMate-element→Soort, draait_op-intro,
  Readiness→Gereedheid, gecureerde select-labels); kolomkop Omschrijving→Toelichting.
- **B2-sortering** (`33a5f85`): architectuuroverzicht server-side sorteerbaar op Naam/Type/Laag/Aspect/
  Soort (ADR-017 v2n-keyset; Laag/Aspect/Soort afgeleid in SQL via dynamische CASE + componentconfig-join).

### B6 — Organisatie als verwijzing naar het partijenregister
- **B6-a** (`c795db4`, migratie **0031**): `gebruikersgroep.organisatie` (vrije tekst) →
  optionele FK `organisatie_id → element` (partij, aard=organisatie). Kolom-specifieke
  `ON DELETE SET NULL (organisatie_id)`. Architectuur-projectie + sortering via partij-join.
- **B6-b** (`c7dd827`, migratie **0032**): `component.eigenaar_organisatie` (vrije tekst NOT NULL) →
  optionele FK `eigenaar_organisatie_id → element`. Beide lijst-services (component + applicatie)
  sorteren/filteren op de gejoinde organisatie-naam; `applicatie_service` omgezet naar de v2n-keyset +
  naam-in-read. Frontend: zoekbare optionele organisatie-keuze (`ZoekSelect`) op formulieren, doorklik
  naar de organisatie op detail + lijst, lijstfilter = organisatie-keuze.

### Afsluiting (DC012)
- complidata-skills bijgewerkt: generiek-platform-uitgangspunt + UX-doorlichting-werkwijze
  (`complidata-ux`); eigen-tabel-bij-tegengestelde-uniciteit, kolom-specifieke SET NULL en naam-in-read
  via partij-join (`complidata-db`, V013-patronen).
- OPVOLGPUNTEN.md → V013-stand (signalerings-ADR/registratiegaten, ADR-024-document bijwerken als eerste
  prioriteit, sorteer-op-codewaarde-randgeval); OP-21 en OP-26 afgerond door B6-b.
- Versie → **V013**.

## Teststatus

- Backend: **799** groen (`pytest backend/tests/ modules/`).
- Frontend: **429** groen (`vitest run`, 52 files).
- Migratie head **`0032`**, één head, geen branches. As4-grep 0. Engine onaangeroerd.
- 1 pre-existing omgevingsgebonden auth-test (OP-30).
