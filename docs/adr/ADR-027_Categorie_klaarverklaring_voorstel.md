# ADR-027 — Component-klaarverklaring en voortgangsrapportage

**Status:** Slice 1 GELAND (componentniveau, migratie 0036) — vervolgslices open.
**Datum:** 2026-06-17 (voorstel) · bijgewerkt 2026-06-19 (DC014, naar componentniveau)
**Relatie:** Bouwt voort op ADR-022 (tenant-eigen checklist) en sluit aan op het bestaande
niet-scorende registratie-patroon (plateau-bevestiging, ADR-023 Fase E).
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt niet
geraakt. De klaarverklaring is een **volledig gescheiden, niet-scorend mechanisme**: het telt niet
mee in de scoring, voedt de engine niet, en leidt niets af.

**Wijzigingshistorie:**
- *DC014 — verschoven van categorie- naar componentniveau; onderdeel 4 (werkverdeling per categorie)
  vervallen. Eenheid van registratie is nu (component); één levende klaarverklaring per component.*
- *DC015 (ADR-029 Fase 3b) — `verklaard_door` stempelt voortaan de Keycloak-`sub` als stabiele
  sleutel (nieuwe kolom `verklaard_door_sub`, migratie 0038); de e-mail blijft als fallback-waarde
  in `verklaard_door`. De naam wordt read-side geresolveerd via de gebruiker-persoon-koppeling
  (ADR-029) → `verklaard_door_naam`. Historische rijen houden hun e-mailstring (geen backfill).*

---

## Context / aanleiding

Bij een groot inventarisatietraject (de ontvlechting kent 250+ applicaties) verschuift de behoefte
van "kan ik dit invullen?" naar "waar moet ik zijn, en hoe sta ik ervoor?". Wat ontbrak is een
expliciet, menselijk **gereed-oordeel** naast de machinale scoring.

Twee dingen die niet door elkaar mogen lopen:

- **De checklist-score** is de motor van de lifecycle (concept → in inventarisatie → …). Een
  **machinale** maat: "hebben de vragen een waarde, en wat zegt de scoring". Engine-gedreven,
  bestaand, ongemoeid.
- **Of een component "klaar" is** is een **menselijk oordeel**. Bij grote aantallen is "alle vragen
  hebben een waarde" geen betrouwbare maat voor "klaar" — een coördinator moet expliciet kunnen
  verklaren: *"ik heb gecoördineerd dat dit beoordeeld is en verklaar het component migratieklaar."*
  Dat oordeel is juist wat je wilt sturen en rapporteren, en het mag óók bij <100% scoring.

**Niveau van het oordeel: het component, niet de categorie.** Het oorspronkelijke voorstel legde de
klaarverklaring per checklist-categorie. In de praktijk is dat te fijnmazig en dwingt het een
werkverdeling af die het systeem niet hoort te bepalen. De klaarverklaring is daarom één oordeel
**per component**: de coördinator (mens) zorgt dat de juiste mensen naar de juiste inhoud kijken;
het systeem registreert één heldere klaarverklaring per component.

---

## Besluit (kern)

1. **Component-klaarverklaring (niet-scorend).** Per component kan een coördinator het component
   expliciet **klaar verklaren**, met een **verplichte reden**. Status **klaar / open**, met
   server-gestempelde **wie** (`verklaard_door`) en **wanneer** (`verklaard_op`). Eén levende
   verklaring per component (`UNIQUE(tenant_id, component_id)`). Registratie, geen beoordelingsvraag:
   telt niet mee in de score, voedt de engine niet.
2. **Herroepbaar (symmetrisch).** Een klaar verklaard component kan weer **open** gezet worden — ook
   dat vraagt een reden. Het hele verloop (klaar → open → klaar) blijft eerlijk terug te lezen in de
   **append-only audit-trail** (per-veld-diffs, geen aparte historie-tabel).
3. **Voortgang op het component + tenant-breed (read-only afgeleid).** Voor één component in één
   oogopslag de status (klaar/open + reden + wie/wanneer); over alle componenten heen de telling
   klaar vs. open — stuurinformatie, afgeleid uit de verklaringen, niets als tweede bron opgeslagen.
4. **Afwijkingssignaal op componentniveau (read-only afgeleid).** "Component klaar verklaard terwijl
   X van Y checklistvragen nog open staan" — een zacht signaal, tenant-breed met doorklik. Het
   blokkeert niets; het maakt de spanning tussen de twee assen zichtbaar.

> **Werkverdeling per categorie — bewust niet.** Het oorspronkelijke onderdeel 4 (voortgang per
> categorie × verantwoordelijke partij/groep) is **vervallen**. Het systeem dwingt geen
> werkverdeling per categorie af: dat coördineert de mens. Per-persoon/per-type *autorisatie* om te
> mogen gereedmelden is een apart, later fundament — zie **ADR-029**.

### Kerninvariant (besloten)
De component-klaarverklaring en de score-engine zijn **twee volledig gescheiden assen**. De
klaarverklaring is hetzelfde soort niet-scorende registratie als de **contractuele bevestiging op
plateau-lidmaatschap** (ADR-023 Fase E): puur registratief, het systeem leidt of berekent er niets
uit richting lifecycle/score. "Component klaar verklaard" en "checklist compleet" (engine-status)
zijn onafhankelijke assen die naast elkaar bestaan en getoond worden, maar elkaar niet aansturen.

---

## Model in detail

### De klaarverklaring (registratie op component) — GELAND (slice 1)
- Eenheid van registratie: **(component)**. Per component ten hoogste één levende klaarverklaring
  (`UNIQUE(tenant_id, component_id)`).
- Velden: `status` (klaar/open, default klaar), verplichte `reden`, server-gestempelde
  `verklaard_door`/`verklaard_op`, timestamps. Composiet-FK `(tenant_id, component_id) →
  element(tenant_id, id)` ON DELETE CASCADE.
- **Eigen tenant-scoped tabel** `component_klaarverklaring` (FORCE RLS) — bewust een aparte,
  niet-scorende registratie buiten de scorings-/lifecycle-paden (niet als checklistvraag, die zou de
  score-engine insleuren). Functioneel mag de aftekenhandeling in de UI bovenaan het component staan.

### Voortgang + afwijkingssignaal (read-only afgeleid) — vervolgslices
- **Per component:** status klaar/open + reden + wie/wanneer.
- **Tenant-breed:** telling/verhouding klaar vs. open over alle (profiel-dragende) componenten.
- **Afwijkingssignaal:** klaar verklaard terwijl nog niet alle checklistvragen beantwoord/positief
  zijn — afgeleid uit de engine-state náást de verklaring-as, nooit met die as vermengd.

### Waarom dit aansluit op bestaande patronen
- Hergebruikt het bewezen **niet-scorende registratie**-patroon (plateau-bevestiging): registratie
  naast de engine, geen afleiding.
- De voortgang-/signaalweergave hergebruikt de bestaande signalering-/status-/doorklik-primitieven
  (status-indicator, lijstfilter, dashboard-telling met doorklik) als read-only leeslaag.

---

## Invarianten

- **Engine onaangeroerd / score blijft enige lifecycle-driver.** De klaarverklaring en de
  voortgang/het signaal voeden de engine niet en muteren geen lifecycle/score/blokkade. Dubbele
  regressie-borging per slice (offline import-afwezigheid + live geen-mutatie) — geborgd in slice 1.
- **Twee gescheiden assen.** "Component klaar verklaard" ≠ "checklist compleet" (engine). Nooit in
  één maat gemengd.
- **Voortgang is read-only afgeleid** uit de verklaringen; geen opgeslagen tweede bron.
- **Structureel boven conventioneel:** de niet-scorende aard wordt machinaal geborgd (de verklaring
  zit aantoonbaar buiten de scorings-/lifecycle-paden), niet alleen bedoeld.

---

## Gevolgen

- **Geen afhankelijkheid van ADR-024 meer.** Door het laten vervallen van de werkverdeling per
  categorie hangt ADR-027 niet langer op het partijenregister. (Slice 1 is zelfstandig geland.)
- **Raakt ADR-022.** De checklist + zijn categorieën bestaan al; het afwijkingssignaal leunt op de
  engine-state per component (read-only), niet op de categorie-structuur.
- **RBAC/audit:** wie mag klaar verklaren/heropenen via de entiteit `KLAARVERKLARING` (inhoud-patroon
  Viewer L · Medewerker LAW · Beheerder LAWV · Auditor L); de verklaringen worden geauditeerd
  (append-only historie via de bestaande audit-trail). **Grove** rol — de verfijning naar
  per-persoon/per-type komt in ADR-029.
- **Bewust géén harde poort.** De klaarverklaring blokkeert niets in de engine of de workflow; ze is
  sturings-/rapportage-informatie. Een component kan "klaar verklaard" zijn terwijl de scoring nog
  niet compleet is, en omgekeerd — twee verschillende assen, geen inconsistentie.

---

## Open subknopen (status na slice 1)

1. **Modellering van de verklaring.** ✅ Besloten + geland: aparte niet-scorende registratie-entiteit
   `component_klaarverklaring` (zoals de plateau-bevestiging), buiten de score-/lifecycle-paden.
2. **Wie mag verklaren (RBAC).** ✅ Geland: rol-gebaseerd via `KLAARVERKLARING`. *Verfijning naar
   per-persoon/per-type → ADR-029.*
3. **Herroepbaarheid.** ✅ Geland: ja, symmetrisch klaar↔open met verplichte reden; verloop in de
   audit-trail.
4. **Verplichte reden — vorm.** ✅ Geland: verplichte vrije tekst (niet leeg, max 2000). Eventueel
   later een keuzelijst-dimensie als de praktijk om standaardisatie vraagt.
5. **Afwijkingssignaal-vorm (vervolgslice).** Read-only "klaar verklaard maar nog niet volledig
   beoordeeld", tenant-breed met doorklik. *Default: zacht signaal, geen poort.*
6. *(ACHTERHAALD — categorie-spoor verlaten)* **Per-categorie granulariteit.** Het oorspronkelijke
   voorstel registreerde per (component, categorie). Verlaten in DC014 t.g.v. componentniveau.
7. *(ACHTERHAALD — categorie-spoor verlaten)* **Werkverdeling-rapportage (oud onderdeel 4)** —
   categorie × verantwoordelijke partij/groep. Vervallen; werkverdeling wordt niet afgedwongen.

---

## Bouw-fasering

1. **Klaarverklaring registratie-model** (niet-scorend, componentniveau) — entiteit + verplichte
   reden + RBAC + audit + engine-onaangeroerd dubbele borging. **GELAND** (gate, migratie 0036,
   commits d3353b5 → 4a66c17).
2. **UI** (slice 2) — component klaar verklaren / heropenen met reden + verloop tonen; knop met
   `v-if` op een rol-computed (verbergen, conform de rest van de app). Licht/additief → doorloop.
3. **Tenant-brede voortgang + afwijkingssignaal** — read-only telling/verhouding + "klaar verklaard
   maar nog open vragen", met doorklik. Licht/additief → doorloop.

Elke slice met engine-onaangeroerd-borging (offline import-afwezigheid + live geen-mutatie) en de
gangbare gate-discipline.
