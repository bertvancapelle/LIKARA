# Feitenrapport — Rechten voor proces-beheer: aanmaken / hernoemen / verwijderen / verhangen (V037/LI037)

**Checkpoint:** LI037_checkpoint_proces_beheer_rechten · **Datum:** 2026-07-11 ·
**Basis:** de nog-ongecommitte tree-view-gate-2-werktree (op ca6501a). Read-only — niets gewijzigd
behalve dit rapport.

**Antwoord in één zin (bewijs in D):** de backend en de RBAC-matrix zijn consistent en bewust
(medewerker = Lezen/Aanmaken/Wijzigen, **verwijderen = beheerder-only** — het standaard
`_INHOUD`-patroon); de bug zit in de **frontend-gating**: de gate-2-verwijderknop hangt aan
dezelfde ruwe `medewerker|beheerder`-check als aanmaken, waardoor een medewerker de actie ziet en
pas de backend-403 ("Onvoldoende rechten voor deze actie.") in de dialoog terugkrijgt — variant
**(b)**: gating-op-de-verkeerde-plek. Verhangen (= WIJZIGEN) mag de medewerker wél; die gating
klopt.

---

## Blok A — Frontend-gating per actie

### A1. Zichtbaarheid per actie (`ProcesLijst.vue`)

Alle vier de acties hangen aan **één en dezelfde** check:

```js
const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))   // r. 28
```

| Actie | Gate (template) | Vindplaats |
|---|---|---|
| Aanmaken ("Nieuw proces") | `v-if="magBewerken"` | r. 372 |
| Hernoemen | `v-if="magBewerken"` | rij-knop |
| **Verwijderen** (gate 2) | `v-if="magBewerken"` | r. 478 |
| Verplaats naar… (gate 2) | `v-if="magBewerken"` | r. 469 |

**Ze lopen dus allemaal via dezelfde rol-check** — er is in de frontend géén onderscheid tussen
AANMAKEN/WIJZIGEN en VERWIJDEREN, terwijl de backend dat onderscheid wél maakt (blok B).
De gating is bovendien een **ruwe rol-lijst** (`hasRole`), geen permissie-per-actie-afleiding —
het gangbare affordance-patroon in LIKARA ("UI verbergt knoppen; de backend handhaaft"), maar
hier met de verkeerde rol-lijst voor verwijderen.

### A2. De "Onvoldoende rechten voor deze actie."-melding

Dat is **niet** een frontend-check maar het **backend-403-bericht**: `ONVOLDOENDE_RECHTEN` in
`backend/app/middleware/authz.py:82` (het canonieke `{"fout":{…}}`-envelope; `api.js` zet
`bericht` op `e.message`). In `ProcesLijst.bevestigVerwijder` vangt de catch alles behalve
401/409 als `verwijderFout = e?.message` → de 403-zin verschijnt **ín** de bevestigingsdialoog.
**Er wordt dus nergens vóór het openen van de dialoog een recht gecheckt**: de knop is zichtbaar
(A1), de dialoog opent, en pas de bevestiging (de echte API-call) stuit op de server-guard.
De waargenomen volgorde klopt exact met de code.

### A3. Detailscherm (proces-detail + secties)

Zelfde ruwe check, overal:
- `ProcesComponentenSectie.vue:36` — `magKoppelen = hasRole('medewerker','beheerder')` gate't de
  Bewerken/Verwijderen-kolom én de toevoegregel (r. 249/272) voor **procesvervullingen**.
- `OnderliggendeProcessenSectie.vue:33` — `magBewerken = hasRole('medewerker','beheerder')` voor
  "+ Deelproces toevoegen".
- `ProcesDetail.vue:34` — `magKaartZien` (alle vier leesrollen) voor de kaartknop.

**Bijvangst (zelfde klasse, pre-existing sinds LI035):** `PROCESVERVULLING` volgt óók het
`_INHOUD`-patroon (medewerker géén VERWIJDEREN, blok B), maar de verwijder-regelactie in
`ProcesComponentenSectie` is voor de medewerker zichtbaar via `magKoppelen` — een medewerker die
daar een koppelregel verwijdert loopt tegen dezelfde 403 aan. De lijst-bug is dus geen unicum
van gate 2.

## Blok B — Backend-recht per endpoint (`routes/proces.py`)

| Endpoint | Permissie-dependency | Vindplaats |
|---|---|---|
| POST /processen (aanmaken) | `vereist_permissie(Entiteit.PROCES, Actie.AANMAKEN)` | r. 64 |
| PATCH /processen/{id} (hernoemen **én** verhangen — één route; `ProcesUpdate` draagt naam/toelichting/ouder_id) | `vereist_permissie(Entiteit.PROCES, Actie.WIJZIGEN)` | r. 105 |
| DELETE /processen/{id} (verwijderen) | `vereist_permissie(Entiteit.PROCES, Actie.VERWIJDEREN)` | r. 114 |

Alles op **dezelfde entiteit** (`PROCES`) maar met **verschillende acties** — en de matrix maakt
dáár het onderscheid (`backend/app/core/rbac.py`):

```python
_INHOUD = { VIEWER: _L, MEDEWERKER: _LAW, BEHEERDER: _LAWV, AUDITOR: _L }   # r. 88–93
Entiteit.PROCES: dict(_INHOUD),            # r. 153
Entiteit.PROCESVERVULLING: dict(_INHOUD),  # r. 155
```

### B5. Bewust onderscheid, geen inconsistentie (backend-zijde)

De medewerker mist voor verwijderen precies **`Actie.VERWIJDEREN`** — en dat is het **bewuste,
platformbrede `_INHOUD`-patroon** (vastgelegd in de RBAC-ankerpunten: "Viewer L · Medewerker
LEZEN+AANMAKEN+WIJZIGEN · Beheerder +VERWIJDEREN · Auditor L"; élke tenant-inhouds-entiteit volgt
het, en de RBAC-matrixtests her-coderen het onafhankelijk). Verwijderen is dus per ontwerp een
zwaarder (beheerder-)recht. **Verhangen valt onder WIJZIGEN** (dezelfde PATCH als hernoemen) en
is voor de medewerker dus wél toegestaan — consistent met "structuur onderhouden zonder te
vernietigen".

## Blok C — De rol zelf

De testgebruikers die processen mogen aanmaken zijn **medewerkers**: `keycloak/realms/
likara-realm.json` → `j.devries` en `p.vandijk` dragen realm-rol `['medewerker']`
(`m.bakker` = `['auditor']`). Volgens de matrix hoort een medewerker: aanmaken ✓, hernoemen ✓,
**verhangen ✓** (WIJZIGEN), **verwijderen ✗** (beheerder-only). De rol mist het verwijder-recht
dus **terecht** volgens de definitie — de tegenstrijdigheid zit niet in de rol.

## Blok D — Conclusie (feitelijk)

**D7. Het loopt uiteen in de FRONTEND-gating → variant (b).** Backend-permissies (B) en
rol-definitie (C) zijn onderling consistent en volgen het bewuste `_INHOUD`-patroon; de bug is
dat de **verwijder-actie zichtbaar/klikbaar is voor een rol die het recht mist** — de gate-2-knop
gate't op `magBewerken` (medewerker|beheerder) waar het backend-recht beheerder-only is. De
"melding in de dialoog" is simpelweg de doorgegeven backend-403 (er is geen dialoog-check). Voor
**verhangen** bestaat er géén bug: WIJZIGEN dekt het, de medewerker mag het, en de gating klopt.

**D8. Gating "vooraf weren" sluit dus voor drie van de vier acties aan op het backend-recht**
(aanmaken/hernoemen/verhangen: medewerker|beheerder ⟺ AANMAKEN/WIJZIGEN) **en voor verwijderen
niet** (medewerker|beheerder ⟺ VERWIJDEREN=beheerder). De latere fix-richting die hieruit
feitelijk volgt (niet uitgevoerd): de verwijder-affordance gaten op het verwijder-recht
(beheerder — bv. een aparte `magVerwijderen`-computed), conform de affordance-norm "de UI toont
alleen wat mag; de backend blijft handhaven"; en desgewenst dezelfde correctie voor de
procesvervulling-verwijder-regelacties in `ProcesComponentenSectie` (de A3-bijvangst — zelfde
klasse, pre-existing). Of Bert in plaats daarvan medewerkers wél proces-verwijderrecht wil geven
(matrix-wijziging) is een expliciete RBAC-/ADR-keuze — de huidige matrix zegt bewust van niet.

---

*Einde feitenrapport. Read-only; geen code, tests of data gewijzigd.*
