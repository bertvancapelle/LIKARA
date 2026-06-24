# ADR-033 — Impact-verkenner (stapsgewijze impact-analyse met opgeslagen views)

**Status:** Besloten (open subknopen nog uit te werken vóór bouw)
**Datum:** 2026-06-24
**Relatie:** Vervangt de huidige Impact-view én de aparte view-tabs in de Landschapskaart. Leunt op het getypeerde relatiemodel (ADR-023) en de bestaande koppeling/afhankelijkheidsrelaties.
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt niet geraakt. Puur read-only, afgeleid.

---

## Context / aanleiding

De huidige Landschapskaart heeft drie aparte view-tabs (Ego / Impact / Geheel) die de gebruiker zelf moet kiezen. Dit is verwarrend: de Impact-view met één component is functioneel identiek aan de Ego-view. De actieve set bestaat al als multi-select mechanisme maar de kaart reageert er niet intelligent op.

---

## Besluit (kern)

1. **De drie view-tabs (Ego / Impact / Geheel) vervallen.** De kaart kiest automatisch de juiste weergave op basis van de actieve set.
2. **Selecteren = toevoegen aan de actieve set.** Klik op een component in de lijst → toegevoegd aan de actieve set. Klik opnieuw → verwijderd. De "+" knop vervalt.
3. **Automatisch weergavegedrag op basis van actieve set:**
   - **Lege actieve set** → Geheel model (alles zichtbaar)
   - **1 component in actieve set** → Ego-view (dat component centraal, directe omgeving eromheen)
   - **Meerdere componenten in actieve set** → Impact-verkenner (topbalk met selectie, transitieve keten eronder)
4. **Stapsgewijze drill-down:** klik op een gerelateerde node in de Impact-verkenner → die schuift naar de topbalk, de nieuwe afhankelijkheden verschijnen eronder.
5. **Terugnavigatie:** "terug"-knop per stap om een stap terug te gaan in de verkenning.
6. **Opgeslagen views:** een gebruiker kan een startpunt (selectie van componenten in de actieve set) opslaan met een naam, zodat hij die direct kan terugvinden.
7. **Privé + deelbaar:** een opgeslagen view is standaard privé (gebruikersgebonden), maar kan gedeeld worden binnen de tenant.
8. **Startscherm:** de Landschapskaart toont een lijst van opgeslagen views als er ≥1 opgeslagen view bestaat; anders direct naar Geheel model.

---

## Model in detail

### Actieve set als universele selectie
- Lege actieve set → Geheel model.
- 1 component → Ego-view (component centraal, ringen eromheen conform aangevinkte ring-checkboxes).
- Meerdere componenten → Impact-verkenner.
- Overgangen zijn vloeiend: voeg een tweede component toe aan de actieve set → kaart schakelt automatisch naar Impact-verkenner.

### Impact-verkenner (meerdere componenten)
- **Topbalk:** horizontale rij van de componenten in de actieve set.
- **Afhankelijkheden:** verticaal eronder, transitieve keten (alle componenten die geraakt worden).
- **Drill-down:** klik op een afhankelijke node → schuift naar de topbalk, nieuwe afhankelijkheden verschijnen eronder.
- **Terugnavigatie:** "terug"-knop per stap.
- **Drill-down-staat wordt niet opgeslagen** — opgeslagen views bewaren alleen de startselect (de actieve set).

### Opgeslagen views
- Opgeslagen per gebruiker (privé default).
- Deelbaar binnen tenant (vlag).
- Bevat: naam + lijst van start-component-id's (de actieve set op het moment van opslaan).
- Beheerd via een eenvoudig CRUD-scherm binnen de Landschapskaart.

### Layout
- Geheel model: Swimlanes of Radiaal (layout-wisselaar, zie Sprint 1d).
- Ego-view: Radiaal (één component centraal).
- Impact-verkenner: topbalk + hiërarchische boom eronder. Dagre-layout vervalt.

---

## Invarianten

- **Engine onaangeroerd / score blijft enige lifecycle-driver.** Puur read-only verkenning.
- **Geen afgeleide relaties** (ADR-023 besluit 7): toont alleen expliciet geregistreerde afhankelijkheden.

---

## Gevolgen

- De drie view-tabs vervallen; de kaart is één adaptieve view.
- De "+" knop in de componentenlijst vervalt; selecteren = klikken.
- De huidige statische Impact-view (dagre) vervalt.
- Nieuwe backend-endpoints nodig: opgeslagen views (CRUD, per gebruiker + tenant-deelbaar).
- Schema-uitbreiding: tabel voor opgeslagen views (gebruiker, tenant, naam, component-ids, gedeeld-vlag).
- RBAC: opgeslagen views zijn gebruikersgebonden; delen binnen tenant vereist een tenant-leespermissie.

---

## Open subknopen (te beslissen vóór de bouw)

1. **Tabel voor opgeslagen views:** eigen tabel of hergebruik van een bestaand voorkeur-/bookmark-mechanisme? *Default: eigen lichte tabel (`impact_view_opgeslagen`).*
2. **Maximaal aantal opgeslagen views per gebruiker?** *Default: geen hard maximum in v1.*
3. **Overgangsanimatie** bij wisselen van weergave (Geheel → Ego → Impact)? *Default: geen animatie in v1; directe wissel.*
4. **RBAC:** eigen permissie-entiteit voor opgeslagen views, of valt dit onder de bestaande architectuur-leespermissie? *Default: valt onder bestaande `ARCHITECTUUR.LEZEN`; opslaan/delen vereist `ARCHITECTUUR.BEWERKEN`.*

---

## Bouw-fasering (indicatief, ná besluitvorming)

1. **Actieve set als selectiemechanisme** — klik = toevoegen/verwijderen, "+" knop vervalt, automatisch weergavegedrag op basis van actieve set.
2. **Impact-verkenner frontend** — topbalk, drill-down, terugnavigatie (read-only, geen opgeslagen views).
3. **Backend opgeslagen views** — CRUD-endpoint + schema (gate, mét migratie).
4. **Frontend opgeslagen views** — startscherm, opslaan/laden/delen.

Elke slice met engine-onaangeroerd-borging en de gangbare gate-discipline.
