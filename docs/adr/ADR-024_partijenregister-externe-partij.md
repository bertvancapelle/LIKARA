# ADR-024 — Partijenregister: externe partij (leverancier-promotie)

**Status**: In uitvoering — slice 1
**Hoort bij**: ADR-023 (ArchiMate-uitlijning, element-supertype), ADR-021 (component-herfundering),
ADR-020 (leverancier-/contractregister), ADR-012 (tweelaags rollenmodel), ADR-026 (catalogus-typering).

## Context

ADR-020 modelleerde `leverancier` als een losse tenant-tabel die via `contract.leverancier_id`
(RESTRICT, NOT NULL) aan het contractregister hing — buiten het element-/relatiemodel (ADR-023
Besluit 2). ADR-024 voert een **partijenregister** in en **promoveert leverancier tot first-class
element-subtype** (`partij`, aard `externe_partij`), zodat partijen identiteit en relatievermogen
krijgen binnen het ArchiMate-uitgelijnde model. Slice 1 realiseert alléén `externe_partij`
(leverancier); organisatie / organisatie-eenheid / persoon zijn latere slices.

## Besluit (slice 1)

1. **Supertype `partij` als element-subtype.** Eén nieuwe `ElementType` `partij`, vaste typing
   `ELEMENT_ARCHIMATE_TYPING['partij']` = `business_actor` / `business` / `active`. De
   partitie-/dekkingstest (`test_archimate_fase_a`/`fase_d`) dekt `partij` en blijft sluitend.
2. **Eén `partij`-subtabel** (element-subtype-recept: shared-PK composiet-FK
   `(tenant_id, id) → element(tenant_id, id)` ON DELETE CASCADE, FORCE RLS + `tenant_isolation`
   + REVOKE/GRANT). Velden: `aard` (NOT NULL, `partij_aard_enum`), gedeelde contactvelden
   (`naam` NOT NULL; rest nullable), `soort` (optioneel). Géén aard-eigen sub-subtabel in slice 1.
3. **Partijsoort = platform-brede, eigen catalogus** (`partijsoort_optie`, GEEN RLS) — *niet* in de
   relatiekenmerk-catalogus (soort is een element-attribuut, geen relatie-kenmerk). Default-seed:
   `leverancier`, `partner`, `ketenpartner`. De soort op de partij is **optioneel** (registratiegat).
4. **Leverancier vervangen door partij** (additief + verse seed, geen backfill): de `leverancier`-
   tabel vervalt; de partij-structuur komt ervoor in de plaats.
5. **`element_type_enum` ADD VALUE `partij`** als aparte, voorafgaande migratie (0026;
   `ALTER TYPE … ADD VALUE` is niet-transactioneel) vóór de subtype-migratie (0027).
6. **Contract-koppeling — optie A (term "leverancier" behouden).** `contract.leverancier_id`
   behoudt naam/term; alleen de **FK-target** verschuift naar het partij-element: composiet-FK
   `(tenant_id, leverancier_id) → element(tenant_id, id)` ON DELETE **RESTRICT**, **NOT NULL**.
   De service borgt dat de verwijzing naar een partij met `aard = externe_partij` wijst. Contract-
   API/-schemas/-frontend blijven qua naamgeving ongemoeid; de display-naam komt uit `Partij.naam`.
7. **Naamgeving — alleen het leverancier-BEHEER hernoemt naar externe partij.** Routes
   (`/externe-partijen`), service (`externe_partij_service`), RBAC-entiteit (`EXTERNE_PARTIJ`),
   audit-allowlist (`partij`) en het beheerscherm ("Externe partijen"). Het contract-domein houdt
   "leverancier" (optie A). De bredere familie-RBAC over alle aarden is een latere-slice-knoop.
8. **Delete-pad.** Verwijderen via het element-supertype (`DELETE FROM element` → CASCADE naar de
   partij-rij), géén wees-element (les commit 109ced8). De RESTRICT-FK houdt een partij-met-
   contracten niet-verwijderbaar (app-side 409 `IN_GEBRUIK` vóór de DB-RESTRICT).

## Gevolgen

- Leverancier is nu een element-backed partij; klaar om in de architectuurprojectie/relaties mee te
  doen. **Engine onaangeroerd**: partij voedt geen lifecycle/profiel/score/blokkade (offline import-
  afwezigheid + live trigger-afwezigheid geborgd); score blijft de enige lifecycle-driver.
- Migraties: `0026_adr024_elementtype_partij` (enum) + `0027_adr024_partij_subtype` (subtabel +
  catalogus + contract-FK-omhang + leverancier-drop).

## Niet in scope (latere slices)

- Andere aarden (organisatie / organisatie-eenheid / persoon).
- Contract-leverancier optioneel maken + "leverancier onbekend"-signaal.
- Volledige rename van het contract-domein naar "partij" (optie B).
- Verantwoordelijkheidsrelatie (wie beheert wat).
- Soort-keuze in het beheerformulier (frontend-dropdown) — backend-soort is aanwezig; het
  dropdown is een lichte vervolgstap.
