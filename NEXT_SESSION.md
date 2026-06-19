# NEXT_SESSION.md — CompliData V015

**Gegenereerd**: 2026-06-19 (sessie DC014)
**Build**: V014 → **V015**
**Laatste feature-commit vóór de afsluiting**: `6ffd7e6` (ADR-027 slice 3 — dashboard-voortgang); de afsluit-commit (docs/skills/build) volgt hierop.
**Migratie head**: `0036`
**Tests**: 833 backend + 474 frontend groen (1 pre-existing, omgevingsgebonden env-test `test_auth_pkce`)

---

## Stand van zaken (V015) — ADR-027 COMPLEET + catalogi-beheer-schuld gedicht

- **ADR-027 — component-klaarverklaring volledig**: slice 1 model (`component_klaarverklaring`,
  migratie 0036, niet-scorend, herroepbaar, engine-gescheiden) → slice 2 UI
  (Migratiegereedheid-blok + klaar verklaren/heropenen met reden op ApplicatieDetail, `979a646`)
  → slice 3 dashboard (tellingen `klaar_verklaard` + `klaar_met_afwijking` + lijstfilter
  `klaarverklaring=klaar`/`afwijking=1`, `6ffd7e6`). Per-categorie + werkverdeling bewust vervallen.
- **Catalogi-beheer-schuld gedicht** (`ed51d36`): vraagbetekenis + partijsoort beheerbaar (platform),
  `checklist_dragend`-toggle + read-only-invariant (gesloten checklist = invoer dicht, data leesbaar),
  `kenmerk_definitie` read-only viewer (code-eigendom, geen editor).

Score blijft de enige lifecycle-driver — alle drie de schakels staan náást de engine, dubbel geborgd
(offline import-afwezigheid + live geen-mutatie). Skills (ux/backend/db/frontend/domeinmodel) bijgewerkt
naar V015 met de DC014-patronen (read-only-bij-sluiten, twee-assen-afleiding, niet-scorende registratie,
"geseed ≠ beheercatalogus", functioneel-first, één-tenant-nu).

---

## Top-prioriteiten volgende sessie

1. **ADR-029 — gebruiker↔partij-autorisatie** (eerste echte implementatie-fundament): brug
   Keycloak-login ↔ persoon-partij + per-type gereedmeld-recht + apart beheerder-autorisatierecht.
   Begin met een feitenrapport (read-only) vóór de gefaseerde bouw.
2. **ADR-023 Fase F-rest**: checklist-consistentiecheck technische plaatsing (E-8, deferred) +
   eventuele resterende RBAC/audit-punten.
3. **Landschapskaart server-side ego-subgraaf** (aparte slice): `?center=<id>&diepte=1|2` i.p.v. de
   volledige tenant-graaf. Vereist nieuw endpoint-contract.
4. **KILARA — codebase-rename** (geparkeerd, DC013): product-/codenaam doorvoeren.

**Nieuwe opvolgpunten (DC014, klein):**
- Klaarverklaring-blok ook op **ComponentDetail** (niet-applicatie checklist-dragende componenten);
  het herbruikbare `MigratiegereedheidSectie`-blok + knop plaatsen (model is al component-generiek).
- Dode `<dl>`-rijen "Eigenaar (naam)" / "Leverancier" op ApplicatieDetail Overzicht opruimen (sinds 0034 altijd "—").
- **CLAUDE.md interactie-secties consolideren** (Werkprotocol + "Werkwijze CC + claude.ai") tot één bron.

---

## Bekende risico's en aandachtspunten

- **Na een `down -v`-reset opnieuw inloggen in de UI** (verlopen sessie) — géén bug.
- **Pre-existing env-test** `test_auth_pkce` (Secure-cookie, DB-onafhankelijk) — omgevingsgebonden, in deze omgeving groen.
- **Eén tenant nu** — geen per-tenant-differentiatie ontwerpen (RBAC = één platform-brede matrix; catalogi gedeeld). RLS blijft technisch fundament, geen ontwerponderwerp.

---

## Werkwijze (triggerdiscipline)

Elke opdracht-`.md` begint op **regel 1** met `START: [taaknaam]`. **`AKKOORD: commit`** is exclusief de
commit-trigger op een groen (gate-)rapport. Schema-/endpoint-/RBAC-rakende slices = **gate** vóór commit;
licht/additief = doorloop. CC verifieert zélf de groene staat vóór elke commit. Eén vraag/advies tegelijk;
functioneel beschrijven vanuit de gebruiker is de norm. Reset-procedure: `docs/LOKAAL-TESTEN.md`.
Startpunt volgende sessie: `docs/_output/CompliData_Sessiestart_V015.zip` → **ADR-029 (feitenrapport)**.
