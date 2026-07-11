# Feitenrapport — Reikwijdte: te-ruime verwijder-gating + tekstlink-vs-knop beheeracties (V037/LI037)

**Checkpoint:** LI037_checkpoint_reikwijdte_beheeracties · **Datum:** 2026-07-11 ·
**Basis:** de nog-ongecommitte tree-view-gate-2-werktree (op ca6501a). Read-only — niets gewijzigd
behalve dit rapport. Grond: `docs/Feitenrapport-proces-beheer-rechten-V037.md`.

**Kern in twee zinnen:** de te-ruime-gating-klasse telt **zes** plekken (ProcesLijst + vijf
component-detail-secties, alle op `medewerker|beheerder` waar het endpoint VERWIJDEREN =
beheerder eist), allemaal van het type "achteraf-403"; het correcte vooraf-weren-patroon
(`magVerwijderen = hasRole('beheerder')`) bestaat al op **zeven** detail-schermen. De
tekstlink-vorm en de ontbrekende gevaar-stijl zitten **uitsluitend** in `ProcesLijst.vue` —
overal elders zijn destructieve acties al rode `severity="danger"`-Buttons.

**⚠ Correctie op het vorige rechten-rapport:** de daar genoemde "bijvangst"
(`ProcesComponentenSectie`-procesvervulling-verwijderen zou dezelfde bug dragen) is **onjuist
gebleken**: de DELETE-route van procesvervulling guardt op **`PROCESVERVULLING.WIJZIGEN`**
(`routes/procesvervulling.py`, delete-decorator; bevestigd door de RBAC-comment "koppelregel:
… verbreken guardt op WIJZIGEN") — de medewerker-gating dáár is dus **correct**. Zelfde geldt
voor roltoewijzing-verwijderen (`PARTIJ.WIJZIGEN`).

---

## Deel 1 — Te-ruime destructieve gating

### Methode
Alle destructieve api-aanroepen in de frontend geïnventariseerd (grep `.verwijder(` over
views/components: 17 plekken), per plek de gate-conditie herleid en vergeleken met de
permissie-dependency van het bijbehorende DELETE-endpoint.

### 1a. De klasse "affordance zichtbaar zonder recht → achteraf-403" — ZES plekken

Endpoint eist `Actie.VERWIJDEREN` (= beheerder-only per het `_INHOUD`-patroon), UI toont de
actie al bij `hasRole('medewerker','beheerder')`. Geen van deze plekken checkt een recht in de
dialoog — de medewerker ziet de knop, bevestigt, en krijgt pas dan de backend-403:

| # | Plek (vindplaats) | Actie | Gate (te ruim) | Endpoint-recht |
|---|---|---|---|---|
| 1 | `ProcesLijst.vue:28/492` *(gate-2-werktree — de aanleiding)* | proces verwijderen | `magBewerken` = medew\|beh | `PROCES.VERWIJDEREN` (`routes/proces.py:114`) |
| 2 | `KoppelingSectie.vue:31` (+ danger-knop `kp-verwijder-*`) | flow-koppeling verwijderen | `mag` = medew\|beh | `RELATIE.VERWIJDEREN` (`routes/relatie.py:97`) |
| 3 | `StructuurSectie.vue` (`st-ontkoppel-*`) | samenstelling/draait-op ontkoppelen | `mag` = medew\|beh | `RELATIE.VERWIJDEREN` |
| 4 | `DatatypeSectie.vue:21` (`dt-verwijder-*`) | datatype verwijderen | `mag` = medew\|beh | `DATATYPE.VERWIJDEREN` |
| 5 | `GebruikersgroepSectie.vue` (`gg-verwijder-*`) | gebruikersgroep verwijderen | `mag` = medew\|beh | `GEBRUIKERSGROEP.VERWIJDEREN` |
| 6 | `ContractSectie.vue` (`ct-ontkoppel-*`) | contract-koppeling ontkoppelen | `mag` = medew\|beh | `COMPONENT_CONTRACT.VERWIJDEREN` |

*(2 t/m 6 zijn pre-existing secties op het componentdetail; 1 is de nog-ongecommitte gate 2.)*

### 1b. Correct geregeld — het bestaande normzettende patroon

- **Vooraf-weren op het verwijder-recht bestaat al**, consequent op zeven detail-schermen:
  `magVerwijderen = computed(() => auth.hasRole('beheerder'))` in `ComponentDetail.vue:81`,
  `ContractDetail.vue:45`, `PartijDetail.vue:34`, en de vier migratie-details (o.a.
  `PlateauDetailView.vue:27`). Opvallend goed: de migratie-details gaten óók hun
  **leden-"Ontkoppelen"** (= `RELATIE.VERWIJDEREN`) op `magVerwijderen`
  (`PlateauDetailView.vue:291`) — precies het patroon dat de zes plekken hierboven missen.
- **Destructief-op-WIJZIGEN, medewerker-gating correct:** `ProcesComponentenSectie` /
  `ComponentProcessenSectie` (procesvervulling verbreken = `PROCESVERVULLING.WIJZIGEN`) en
  `VerantwoordelijkheidSectie` (roltoewijzing = `PARTIJ.WIJZIGEN`).
- **Eigen-beheer/afwijkende matrixen kloppen:** kaart-views verwijderen
  (`IMPACT_VIEW` = `_EIGEN_BEHEER`, medewerker hééft V → `magViewsBeheren` ✓);
  `GebruikersbeheerView` (beheerder ⟺ `GEBRUIKERSBEHEER`-matrix ✓); de platform-config-schermen
  (platformbeheerder; catalogi kennen géén delete — soft-deactivate via WIJZIGEN ✓).
- **Niet in de UI:** organisatiegebruik- en checklistscore-verwijderen hebben wel een
  VERWIJDEREN-endpoint maar geen verwijder-affordance in een scherm (geen gating-kwestie).

### 1c. Vooraf vs. achteraf

Alle zes 1a-plekken zijn "achteraf-403": knop zichtbaar → bevestigingsdialoog → pas de echte
call stuit op de server-guard (`authz.py:82`, "Onvoldoende rechten voor deze actie."). Nergens
een dialoog-recht-check. De zeven 1b-detail-schermen weren wél vooraf.

## Deel 2 — Tekstlink vs. knop

### 2a. De norm (bestaand en breed gevolgd)

Beheeracties zijn **Button-preset-knoppen**: "Bewerken" default/`secondary`, destructief
(Verwijderen/Ontkoppelen/Definitief verwijderen/Deactiveren) **`severity="danger"`** (rood,
knopstandaard), bevestiging via de gedeelde `BevestigVerwijderDialog` of een eigen dialoog met
danger-bevestigknop. De inventaris (grep `severity="danger"`) toont dit patroon op ±20
schermen/secties — inclusief álle zes 1a-plekken: die hebben de juiste **vorm**, alleen de
verkeerde **gating**.

### 2b. De afwijkers — alléén ProcesLijst

`ProcesLijst.vue` is het enige scherm met beheeracties als **tekstlinks** (`<button>` met
`hover:underline`): "Hernoemen" (r. 475, pre-existing sinds ADR-042 slice 4a) en de gate-2-
toevoegingen "Verplaats naar…" (r. 484) en "Verwijderen" (r. 492). **Veiligheidspunt (2/4):**
de verwijder-tekstlink draagt geen gevaar-stijl (alleen `hover:text-danger`) — de meest
destructieve actie op het scherm oogt het minst gevaarlijk, in strijd met de knopstandaard.
Verder géén tekstlink-beheeracties gevonden (repo-brede scan); navigatielinks (broodkruimel,
"← Terug", rij-namen) zijn geen beheeracties en tellen niet mee.

## Deel 3 — Reikwijdte-conclusie (feitelijk, niet beslist)

### (a) Te-ruime destructieve gating

| Plek | Hoort bij |
|---|---|
| `ProcesLijst.vue` (proces-verwijderen) | **deze slice** (de nog-ongecommitte gate 2 — fix vóór landing voorkomt dat de bug überhaupt landt) |
| `KoppelingSectie` / `StructuurSectie` / `DatatypeSectie` / `GebruikersgroepSectie` / `ContractSectie` | **zelfde klasse, pre-existing** → kandidaat voor een eigen kleine consistentie-slice (vijf identieke één-regel-wijzigingen `mag` → `magVerwijderen`-variant + testregels), of desgewenst meteen meenemen — Berts keuze |

### (b) Tekstlink / ontbrekende gevaar-stijl

Alleen `ProcesLijst.vue` (drie acties, waarvan één destructief zonder rood) → **deze slice**;
er is geen bredere achterstand.

### Gedeelde oplossing vs. per-plek (schets, geen keuze)

1. **Per-plek een `magVerwijderen`-computed** (het bestaande detail-scherm-patroon kopiëren):
   zes kleine wijzigingen, nul abstractie, direct leesbaar; nadeel: de rol-lijst blijft per
   scherm gedupliceerd (zoals nu al voor `magBewerken` — bestaand aanvaard patroon).
2. **Gedeelde gating-helper** (bv. een `useRechten()`-composable die per entiteit+actie de
   rollen levert): één bron client-side, maar **dupliceert de backend-RBAC-matrix** in de
   frontend → drift-risico bij matrix-wijzigingen, tenzij `/auth/me` de effectieve permissies
   gaat meesturen — dat is een backend-uitbreiding (buiten een frontend-slice).
3. **Gedeelde actie-knoppen-component** (rij-acties Bewerken/Verwijderen als één component):
   lost vooral de vórm-consistentie op (die op één scherm na al bestaat), niet de gating;
   n is groot genoeg, maar de winst is klein zolang alleen ProcesLijst afwijkt.

---

*Einde reikwijdte-rapport. Read-only; geen code, tests of data gewijzigd.*
