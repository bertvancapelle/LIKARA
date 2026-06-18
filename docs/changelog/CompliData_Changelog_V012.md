# CompliData Changelog V012

**Datum**: 2026-06-18

Sessie DC011 — ADR-024 partij-fundament (slices 1 → 2a → 2a-bis), leden-overzicht-fix,
ADR-026 componenttype-typering, en blokkade-/dashboard-fixes. Migratie head `0028`.

## Wijzigingen

### ADR-024 — Partijen (nieuw fundament)
- **Slice 1** (`fd4c299`): externe partij als element-subtype `partij` (leverancier-promotie); de
  contract-leverancierkoppeling verwijst nu naar `partij` (`aard = externe_partij`).
- **Slice 2a** (`0e02e2d`): één Partijen-beheerscherm voor **alle aarden** (externe_partij /
  organisatie / organisatie_eenheid / persoon) met aard-filter; aard verplicht bij aanmaken en daarna
  vast; optioneel soort-dropdown; `Entiteit.PARTIJ`-recht; cosmetische rename Leverancier* → Partij*.
- **Slice 2a-bis** (`b2b1216`, migratie **0028**): partij-**lidmaatschap** ("hoort bij"). Persoon/
  afdeling horen **verplicht** bij een organisatie(-achtige) partij; persoon optioneel ook bij een
  afdeling binnen die organisatie. FK-kolommen `organisatie_id`/`afdeling_id` (composiet-FK → element,
  RESTRICT) + twee CHECK-backstops; service cross-row-validatie; formulier-pickers; van-twee-kanten-
  weergave op partij-detail. Geverifieerd via fresh-reset (Fase 1 offline → Fase 2 live).
- **Leden-overzicht-fix** (`0a11038`): de api-client gaf `organisatie_id`/`afdeling_id` niet door →
  het leden-blok toonde het hele register. Gefixt + het blok is nu **server-side sorteerbaar**
  (Naam/Aard) en **gepagineerd** (ADR-017 keyset). `aard` toegevoegd aan de sorteer-allowlist.

### ADR-026 — Componenttype-typering
- (`04ed4a4`) Componenttype-typering beheerbaar gemaakt.

### Blokkades & dashboard
- (`988e337`) Tenant-brede blokkadelijst: Component-kolom + type-onafhankelijke doorklik naar
  component-detail.
- (`8923114`) Dashboard-label voor blokkades gecorrigeerd.

### Afsluiting (DC011)
- complidata-skills bijgewerkt: sorteer-eis (frontend), invariant→schema/beleid→code (db), live-DB-
  dekking + end-to-end (tests), OPVOLGPUNTEN-tracked-correctie, signalering-niet-generaliseren-vóór-n=3.
- OPVOLGPUNTEN.md canoniek herschreven (ADR-024 vervolgslices 2b–2e, scope-besluiten, contract-
  leverancier verruimen, sorteer-sweep, ADR-027, dashboard punt 2, tenant-eigen catalogi).
- Versie → **V012**.

## Teststatus
- Backend: **769 groen** (module 698 + platform 71); frontend: **330 groen**.
- Pre-existing: `test_auth_pkce` Secure-cookie env-test faalt omgevingsgebonden (geen bug).
- Kritieke bevindingen: **0**.

## Openstaand (zie OPVOLGPUNTEN.md)
ADR-024 slices 2b (rollen-catalogus) → 2e; contract-leverancier verruimen; bredere sorteer-sweep;
ADR-027 (concept nog te landen in `docs/adr`); dashboard punt 2.
