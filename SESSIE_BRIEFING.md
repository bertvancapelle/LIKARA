# SESSIE_BRIEFING.md — CompliData V017

**Gegenereerd**: 2026-06-22

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V017 |
| Datum | June 2026 |
| Commit | 2bfcbd8 |
| Tests | 859 backend + 534 frontend groen + css-build groen |
| TST-rapport | TST-V017-Validatierapport.md |
| Kritieke bevindingen | 0 kritiek |

---

## Recente commits

```
2bfcbd8 docs(skills): DC016 skills-borging stap 1 — knop/tab/borging/api-filter/ADR-023a/testdata/sessiebewaking
7a6e440 feat(relatie): ADR-023a Fase 2 — naam-verplicht-flow + dubbel-signalering + override-audit
3e28481 docs(adr): ADR-030 contract-dekking per contract↔component-band (voorstel)
80f0655 feat(relatie): ADR-023a Fase 1 — meervoudige flow-koppelingen + naam-kolom (schema)
9da57d0 fix(frontend): api-client filterconventie — snake_case + allowlist (luide fout)
```

---

## Prioriteiten volgende sessie

# NEXT_SESSION.md — CompliData V017

**Gegenereerd**: 2026-06-22 (sessie DC016)
**Build**: V016 → **V017**
**Laatste commit vóór de afsluiting**: `2bfcbd8` (skills-borging DC016); de afsluit-commit (OPVOLGPUNTEN/TST/NEXT_SESSION/changelog/build) volgt hierop.
**Migratie head**: `0040`
**Tests**: 859 backend + 534 frontend groen + `test:css-build` groen (1 pre-existing test-mock-warning).

---

## Stand van zaken (V017) — UI-standaardisatie + api-borging + ADR-023a Fase 1+2

Deze sessie (DC016):

- **UI-standaardisatie & interactie-borging**: knop-preset gestandaardiseerd (`23ccfc8`); tabs +
  vaste hoogte (`55eca62`); **één hoogte (`h-10`), geen size-variatie** (`8912203`); UI-interactie-
  borging in **drie lagen** — token-contract, render-state, build-CSS-check (`cb4b9e7`); Tailwind
  **`@source`** voor module-views buiten `frontend/` (`6f04ed2`).
- **Api-client-filterconventie** (`9da57d0`): één conventie (snake_case = backend), `_filterQuery`-
  allowlist → onbekende key = **luide fout**, nooit stille drop. Fixte de Koppelingen-bug (filter viel
  stil weg → scherm toonde alle flows i.p.v. de objectspecifieke).
- **Landschapskaart** (`8de3451`): klik-popups (koppeling + knoop, enkel/dubbelklik gescheiden) +
  in-app fullscreen-overlay met staat-behoud.
- **ADR-023a meervoudige flow-koppelingen**: **Fase 1 schema** (`80f0655`, migratie 0039 — partiële
  flow-uniciteit `WHERE relatietype <> 'flow'` + `naam`-kolom) en **Fase 2 validatie** (`7a6e440`,
  migratie 0040 — naam-verplicht-voor-flow, overrulebare `KOPPELING_DUBBEL`-signalering,
  `RELATIE_BESTAAT` nu non-flow, override audit-naspeurbaar via `dubbel_waarschuwing_genegeerd`).
- **ADR-030** contract-dekking per band (voorstel, `3e28481` — extern geland).
- **Skills-borging DC016** (`2bfcbd8`): knop/tab/UI-borging/api-filter/ADR-023a/testdata-regel/
  sessiebewaking canoniek vastgelegd.

Score blijft de enige lifecycle-driver — de koppeling-uitbreiding staat náást de engine (offline
import-afwezigheid + live geen `component_profiel`).

---

## Top-prioriteiten volgende sessie (DC017)

1. **ADR-023a Fase 3** — kaart-edge-groepering (meerdere flows per `(bron,doel)` → één lijn +
   **telling vanaf 2**) + popup-fetch op het **ongeordende paar**, gegroepeerd naar richting.
   Read/contract, **geen migratie**.
2. **ADR-023a Fase 4** (het zichtbare deel) — naam-veld (verplicht) + overrulebare
   **KOPPELING_DUBBEL**-waarschuwingsdialoog; `KoppelingSectie` naam-kolom (sorteerbaar); kaart-telling
   vanaf 2; popup → **universeel master-detail** (links sorteerbare interface-lijst naam/richting,
   pijl-buiten-groen=uitgaand / pijl-binnen-rood=inkomend met **pijlrichting als hoofdsignaal**; rechts
   detail; eerste regel geselecteerd; ook bij n=1). Vervangt de enkelvoudige popup uit `8de3451`.
3. **Nieuw seed-traject** (groot) — volledige testdataset die het hele LIKARA-landschap representeert,
   **mét flow-namen + meervoudige benoemde koppelingen**. Volgt ná de ADR-023a-koppeling-keten.
4. **Resterende DC016-prioriteiten** (niet aangeraakt): **ADR-029 Fase 5** (`gereedmeld_recht`,
   per-type persoon × componenttype); **ADR-023 Fase F-rest** (E-8 checklist-consistentiecheck +
   resterende RBAC/audit); **Landschapskaart server-side ego-subgraaf** (`?center=&diepte=`);
   **LIKARA codebase-rename** (geparkeerd).
5. **ADR-030 contract-dekking per band** (design-checkpoint → bouw) — **ná** de koppeling-keten
   (de koppeling-uitbreiding als blauwdruk; open subknoop: contract-brede dekking behouden NAAST of
   vervangen).

---

## Bekende risico's en aandachtspunten

- **Reseed gebroken op flow-namen**: `dev_seed_testdata._seed_koppelingen` maakt flows **zonder naam**
  → faalt nu onder de naam-eis (ADR-023a Fase 2). Een reseed van de koppelingen is gebroken tot het
  nieuwe seed-traject draait. **Testdata-kwestie, geen migratievraagstuk.**
- **Dev-inlog** vereist de volledige stack (Keycloak); frontend draait buiten Docker
  (`cd frontend && npm run dev`, poort 3000, proxy → :8000). Migratie head dev-DB: `0040`.
- **`test:css-build` nog niet in CI** (los script) — CI-stap/pre-push-hook is de logische vervolgstap.
- **Eén tenant nu** — geen per-tenant-differentiatie ontwerpen (RBAC = één platform-brede matrix).

---

## Werkwijze (triggerdiscipline)

Elke opdracht-`.md` begint op **regel 1** met `START: [taaknaam]`. **`AKKOORD: commit`** is exclusief de
commit-trigger op een groen (gate-)rapport. Schema-/endpoint-/RBAC-/datamodel-rakende slices = **gate**
vóór commit; licht/additief = doorloop. CC verifieert zélf de groene staat vóór elke commit. Eén
vraag/advies tegelijk; functioneel beschrijven vanuit de gebruiker is de norm. Reset-procedure:
`docs/LOKAAL-TESTEN.md`. Startpunt volgende sessie: `docs/_output/CompliData_Sessiestart_V017.zip` →
**ADR-023a Fase 3**.


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — CompliData V017"
4. Wacht op START: [naam] van Bert
