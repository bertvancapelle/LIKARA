# ADR-013 — Lifecycle-herberekening (Model A): afgeleide blokkades en deterministische statusafleiding

| | |
|---|---|
| **Status** | Aanvaard |
| **Datum** | 2026-06-06 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-009 (BWB-ontvlechtingsmodule, datamodel + lifecycle), ADR-003 (multi-tenant RLS), ADR-010 (tenant-RBAC) |

## Context

De BWB-ontvlechtingsmodule (ADR-009) geeft elke `Applicatie` een
`lifecycle_status` met de waarden `concept`, `in_inventarisatie`,
`checklist_compleet`, `geblokkeerd`, `migratieklaar`. ADR-009 liet open *wie*
de status zet en *hoe* de afgeleide statussen (`geblokkeerd`, `migratieklaar`)
ontstaan.

Twee koppelende entiteiten bepalen de werkelijke voortgang:

- **Checklistscore** — een antwoord (`ja`/`deels`/`nee`/`nvt`) op een vraag uit
  de platform-brede vragenset (`ChecklistVraag`, 89 vragen).
- **Blokkade** — een belemmering die voortvloeit uit een onvoldoende score.

Zonder een eenduidige regel ontstaat statusdrift: handmatig gezette statussen
die niet meer overeenkomen met de feitelijke scores en blokkades. Er is een
deterministische, herhaalbare afleiding nodig.

## Besluit

### B1 — Model A: automatisch afgeleide blokkades

> **Geamendeerd door [ADR-016](ADR-016_lifecycle-reconciliatie-blokkade-opgelost.md)
> (V012):** handmatig alleen `open ↔ in_behandeling`; `opgelost` ontstaat
> uitsluitend via de auto-logica (score `ja`/`nvt`). Een handmatige `opgelost` ⇒
> 409. Lees de onderstaande zin "doorloopt handmatig `open → in_behandeling →
> opgelost`" met die beperking.

Een **Blokkade ontstaat automatisch** zodra een Checklistscore de waarde `nee`
of `deels` krijgt (start in status `open`). De mens vult vervolgens
`toelichting`/`eigenaar` en doorloopt handmatig `open → in_behandeling →
opgelost` (waarbij `opgelost_op` wordt gezet). Een gebruiker maakt of verwijdert
blokkades **niet** handmatig.

### B2 — Invariant Checklistscore ↔ Blokkade

> Een Checklistscore met score `nee`/`deels` heeft een **actieve** blokkade
> (`open` of `in_behandeling`); een score `ja`/`nvt` heeft een **opgeloste of
> geen** blokkade.

De service handhaaft dit bij elke Checklistscore-schrijf:

- score wordt `nee`/`deels` en er is geen blokkade → maak er één (`open`);
  bestaat er een `opgelost`e blokkade → heropen (`status=open`,
  `opgelost_op=null`).
- score wordt `ja`/`nvt` en er is een actieve blokkade → **auto-oplossen**
  (`status=opgelost`, `opgelost_op=nu`), **niet verwijderen**.
- Handmatige `open ↔ in_behandeling` door de gebruiker blijft ongemoeid door de
  auto-logica.

`score` is in Create **verplicht** (niet-null); een Checklistscore-rij betekent
dus altijd dat de vraag is gescoord (`nvt` telt mee). Het schema is daarmee
strikter dan de — om historische redenen nullable — DB-kolom; het datamodel
wordt niet gewijzigd.

### B3 — Deterministische herberekening

Eén pure functie `herbereken_lifecycle(applicatie)` leidt de canonieke status af
uit de huidige feiten en draait **na elke mutatie** van een Checklistscore of
Blokkade van die applicatie, en na de handmatige `start-inventarisatie`:

```
niet gestart (status concept)             → blijft concept
gestart, niet alle vragen gescoord        → in_inventarisatie
alle vragen gescoord, ≥ 1 OPEN blokkade   → geblokkeerd
alle vragen gescoord, geen open blokkade  → migratieklaar
```

- "Open blokkade" = status `open` of `in_behandeling` (beide = nog niet opgelost).
- "Alle vragen gescoord" = het aantal Checklistscore-rijen (tenant, applicatie)
  is gelijk aan het aantal `ChecklistVraag`-rijen (de actieve set; nu 89).
- **`concept` is de enige niet-afgeleide vloer.** De herberekening zet de status
  nooit terug naar `concept`; `concept` wordt uitsluitend verlaten door de
  handmatige `start-inventarisatie` (ADR-009 / P5).
- **Reverse toegestaan.** Verandert een score of komt er een vraag bij, dan mag
  de status terugzakken (bijv. van `migratieklaar` naar `in_inventarisatie`, of
  van `migratieklaar` naar `geblokkeerd`). De functie is een pure her-afleiding,
  geen forward-only toestandsmachine.
- Randgeval: zijn er 0 vragen in de actieve set, dan geldt de inventarisatie niet
  als compleet → `in_inventarisatie`.

### B4 — `checklist_compleet` is transient (afwijking van ADR-009)

ADR-009 noemt `checklist_compleet` als ruststatus. In Model A is "alle vragen
gescoord" slechts een **doorgangsmoment** dat onmiddellijk naar `geblokkeerd` of
`migratieklaar` leidt, afhankelijk van openstaande blokkades. `checklist_compleet`
wordt daarom **nooit als ruststatus opgeslagen**.

De enum-waarde blijft in het datamodel bestaan (geen migratie/datamodelwijziging),
maar de herberekening kent hem niet toe. Dit is een **bewuste afwijking van
ADR-009**, hier vastgelegd.

## Gevolgen

**Positief**
- De `lifecycle_status` is op elk moment een zuivere functie van de feiten —
  geen statusdrift, herhaalbaar en testbaar (de beslisregel is DB-vrij).
- Blokkades zijn altijd consistent met de scores (invariant B2).
- Geen handmatige statusmanipulatie na de start; minder foutgevoelig.

**Negatief / aandachtspunten**
- `checklist_compleet` is een "dode" enum-waarde geworden — bij een latere
  datamodel-opschoning te heroverwegen (buiten scope hier; datamodel ongemoeid).
- De herberekening leest per mutatie drie tellingen (vragen, scores, open
  blokkades); voor de huidige schaal (89 vragen, beperkt aantal applicaties per
  tenant) verwaarloosbaar.

## Niet in scope

- Wijzigingen aan het datamodel, de enums of de seed (89 vragen).
- Een "actief/inactief"-vlag op `ChecklistVraag` (de actieve set = alle vragen).
- RLS- of rolwijzigingen (ADR-003/010/012 blijven leidend).
