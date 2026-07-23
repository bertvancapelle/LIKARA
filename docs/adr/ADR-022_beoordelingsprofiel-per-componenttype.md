# ADR-022 — Beoordelingsprofiel / checklist per componenttype

**Status**: Aanvaard (besluit). Implementatie openstaand — concreet datamodel, migratie en
RLS-policies volgen als afzonderlijk, gegate blok (CC stop-and-report vóór schema-/engine-werk).
**Wijziging W1** herziet Besluit 4 (platform-beheerd → tenant-eigendom van de vragenset); zie de
sectie "Wijziging W1" onderaan.
**Volgorde**: ADR-022 **vóór** ADR-006 — de audit-trail logt het definitieve besturingsmodel;
eerst het model vaststellen, dan auditen.
**Voortbouwend op**: ADR-021 (component-herfundering, supertype/subtype shared-PK,
`SUBTYPE_BESCHERMD`) en ADR-021 Wijziging W1 (CD054b — verenigde Componenten-UI, convergente aanmaak),
ADR-013 (lifecycle-herberekening), ADR-016 (blokkade-reconciliatie), ADR-019 (configureerbare
antwoordopties), ADR-012-addenda (catalogus-familiepatroon).
**Vervangt**: ADR-022_VOORBEREIDING.

---

## Context

Vandaag draagt alleen het subtype `applicatie` een checklist + lifecycle + blokkades; kale infra
(database, fileshare, …) heeft enkel registratie. Besluit Bert: een componenttype kan een eigen
beoordelingsprofiel (checklist) krijgen. Besturing volgt het type, niet de invoerroute. Deze ADR
legt vast óf en hoe andere typen een profiel krijgen, en herijkt de type-wijzigingsbescherming.

## Besluiten

### Besluit 1 — Checklist-dragend = engine-dragend (geen scores-only-tier)

Een componenttype dat een checklist krijgt, krijgt het volledige engine-apparaat: deterministische
lifecycle-statusberekening (ADR-013) en auto-blokkades (ADR-016), byte-identiek aan `applicatie`.
Er komt geen tweede, engine-loze "scores-only"-klasse. De `ja/deels/nee/nvt`-score blijft de enige
driver van alle lifecycle- en blokkade-logica (ADR-019); configureerbare antwoordopties zijn
cosmetisch/contextueel. Een eventuele puur adviserende (niet-blokkerende) checklist wordt uitgedrukt
**binnen** de engine via vraag-/wegingsconfiguratie, niet via een aparte tier.

Rationale: de engine is reeds puur score-gedreven en deterministisch; uniform aansluiten is
configuratie, geen nieuwe logica. Eén besturingsmodel is bovendien schoner te auditen (ADR-006).

### Besluit 2 — Type-wijzigingsbescherming op toestand i.p.v. op type

De bescherming hangt niet langer statisch aan het type (`applicatie` ja/nee), maar aan de
**toestand** van het profiel/subtype — bestaat er al engine-data of niet. Daarmee is de regel
type-agnostisch en generiek toepasbaar op elke profiel-grens.

- **Leeg profiel → type vrij wijzigbaar.** Het lege profiel/subtype wordt verwijderd; bij een ander
  checklist-dragend doeltype wordt een schoon doelprofiel met defaults aangemaakt.
- **Gevuld profiel → type vergrendeld.** De UI toont "type vergrendeld"; de enige weg is het
  component **verwijderen** via een bevestigingsdialoog die expliciet opsomt wát verdwijnt (aantal
  scores, blokkades, gekoppelde datatypes/gebruikersgroepen).
- **Drempel "gevuld"**: minstens één ingevulde checklist-score, óf minstens één blokkade, óf een
  gekoppeld datatype/gebruikersgroep, óf lifecycle voorbij `concept`. Alles daaronder = leeg.
- **Backend is bron van waarheid.** Wijzigbaarheid wordt server-side, transactie-lokaal bepaald en
  als capability-vlag (`type_wijzigbaar`) op het component meegegeven. De UI is een hint; de PATCH
  herevalueert de toestand en weigert zo nodig met canonieke fout.
- **Gewonnen capability**: een kale component zonder data kan in-place gepromoveerd worden naar een
  checklist-dragend type (nieuw gedrag t.o.v. de statische guard).
- **Foutcode**: `SUBTYPE_BESCHERMD` blijft semantisch passend; een preciezere `SUBTYPE_HEEFT_DATA`
  is een open verfijning (zie Openstaand).

Dit ontkoppelt de lock van de aanmaak: de convergente aanmaak (CD054b) blijft werken; de drempel
verschuift van "subtype bestaat" naar "subtype gevuld".

### Besluit 3 — Geïntegreerd, per type gesegmenteerd readiness-beeld

Eén landschapsscherm dat readiness type-bewust segmenteert: per componentsoort een eigen rollup
("n van m gereed"), zonder één gefuseerde mengscore over heterogene profielen. De engine rekent per
profiel (byte-identiek ADR-013/016); uitsluitend de rapportagelaag wordt type-aware en aggregeert.
Sluit aan op de bestaande landschapslens (graaf + impactanalyse, CD056).

### Besluit 4 — Eén platform-beheerd vragenbeheer met type-discriminator

**[Herzien — zie Wijziging W1]**

Vragensets worden in één beheerscherm onderhouden; per vraag een binding aan een `componenttype`.
Hergebruik `checklistvraag` met een type-discriminator — geen aparte vragentabel per type. Het
catalogus-familiepatroon (ADR-012-addenda) is van toepassing: platform-beheerd, stabiele
soft-deactiveerbare ID's. "Een nieuw type een checklist geven" is daarmee een configuratiehandeling,
geen schema-uitbreiding.

### Besluit 5 — Generiek profiel-construct, geen subtype-tabel per type

Eén generiek profiel-construct bovenop `component` draagt de engine-state (lifecycle, scores,
blokkades), gebonden aan een `componenttype`. `applicatie` behoudt zijn eigen subtype-tabel voor
type-eigen velden (`migratiepad`, `complexiteit`, `prioriteit`). Afweging: een subtype-tabel per
type geeft sterkere typing en type-eigen velden maar kost bij elk nieuw type schema-werk; het
generieke profiel houdt nieuw-type = configuratie. De keuze in Besluit 4 (config in één scherm)
wijst naar het generieke profiel.

## Gevolgen

- De subtype-grens-bescherming wordt toestand-gebaseerd en type-agnostisch en geldt voortaan voor
  elke profiel-grens, niet alleen `applicatie`.
- De convergente aanmaak (CD054b) blijft intact; de lock-drempel verschuift.
- De destructieve bevestigingsdialoog (verwijderen van een gevuld profiel) sluit aan op de
  hash-chained audit-trail (ADR-006): een bewuste destructieve handeling wordt auditbaar.
- Het besturingsmodel is uniform (één engine), wat de audit-modellering vereenvoudigt.

## Niet in scope van deze ADR (implementatie-gated)

Concreet datamodel, kolommen, migratie, RLS-policies, service- en UI-realisatie. Dit volgt als
afzonderlijk blok met een CC stop-and-report-checkpoint vóór wijzigingen aan datamodel, migraties,
RLS-policies, auth- of query-semantiek.

## Wijziging W1 — Besluit 4 herzien: tenant-eigendom van de vragenset

**Aanleiding**: functionele eis — elke tenant moet zijn eigen checklistvragen kunnen definiëren en
volledig aanpassen (toevoegen, bewerken, verwijderen). Dit vervangt het platform-beheerde model uit
het oorspronkelijke Besluit 4 en lost tevens de cross-tenant fan-out-knoop op (zie onder).

**Herziening**:

- `checklistvraag` wordt **tenant-scoped** (`tenant_id` + RLS + FORCE), eigendom van de tenant.
  Identiteit: `UNIQUE(tenant_id, componenttype, code)` (surrogate-PK `id` blijft — Knoop 3 Optie B).
  `checklistvraag_optie` volgt als tenant-data (RLS).
- **Volledige CRUD door de tenant** via `cd_app` binnen de eigen RLS-context. De grants op
  `checklistvraag`/`checklistvraag_optie` verschuiven van `cd_platform`-CRUD naar `cd_app`-CRUD
  onder RLS. Het bestaande optie-beheer (`/platform/checklistconfig`, `cd_platform`,
  `ChecklistConfigBeheer.vue`) verhuist naar een **tenant-facing** pad.
- **Verwijderen = soft-deactivatie** via `checklistvraag.actief` (ontpart de eerder geparkeerde
  whole-question-deactivatie). Een gedeactiveerde vraag valt uit de actieve set en uit
  `aantal_vragen`; bestaande scores blijven als historie bestaan. Harde verwijdering hooguit voor
  een nooit-gescoorde vraag (optioneel).
- **Platform-baseline als kopie-bij-onboarding**: een baseline-vragenset (de huidige
  seed-definitie) wordt bij tenant-onboarding (#16) in de tenant gekopieerd; daarna volledig
  eigendom van de tenant en vrij aanpasbaar. Geen levende gedeelde platform-vragentabel, geen
  koppeling tussen tenants.

**Gevolg voor de fan-out** (vervangt de cross-tenant-analyse): doordat vragen tenant-scoped zijn,
raakt een vraag-mutatie uitsluitend de eigen tenant. De lifecycle-herberekening van bestaande
componenten van het betrokken componenttype gebeurt **in-tenant**, atomair, in één `cd_app`-
transactie binnen RLS. Er is **geen** cross-tenant write, **geen** BYPASSRLS-rol en **geen**
stale-venster. `lifecycle_status` blijft opgeslagen (ADR-013 ongemoeid).

**Gevolg voor Besluit 3 (readiness)**: readiness is per definitie per-tenant (elke tenant een eigen
vragenset); cross-tenant vergelijking is bewust niet aan de orde.

**Ongewijzigd**: Besluit 1 (checklist-dragend = engine-dragend), Besluit 2 (toestand-gebaseerde
type-lock), Besluit 5 (generiek profiel-construct; `applicatie` behoudt zijn eigen subtype-tabel).

## Openstaand

- Foutcode-keuze: `SUBTYPE_BESCHERMD` (bestaand) versus preciezere `SUBTYPE_HEEFT_DATA` — t.z.t.

## Eindstaat — gerealiseerd t/m LI058/LI059

De ADR is volledig geïmplementeerd:

- **Scoren per componenttype** (LI058, migratie `0046`): de `checklist_dragend`-vlag op
  `componentconfig_optie` (platform, togglebaar) bepaalt of een type een `ComponentProfiel` +
  checklist krijgt. Bij `False→True` loopt een **profiel-backfill** (per tenant, RLS-scoped worker-
  sessie → ontbrekende profielen + `herbereken_type`); `True→False` laat profielen inert (nooit
  scoringsdata vernietigen). `database` is als tweede beoordeeld type geactiveerd (6 vragen).
- **Generiek profiel zonder subtype** (LI059): Besluit 5 wordt aangescherpt — het generieke
  `component_profiel` (shared-PK met `component`) is nu de **enige** engine-state-drager voor élk
  checklist-dragend type, óók `applicatie`. De oude formulering "`applicatie` behoudt zijn eigen
  subtype-tabel" is **achterhaald**: de `applicatie`-subtabel is gedropt (0047) — een component met
  `componenttype='applicatie'` is de applicatie (zie ADR-021 "Eindstaat — LI057–LI059").
- **Type-lock (Besluit 2)** blijft: een gevuld component kan niet van type wisselen
  (`SUBTYPE_BESCHERMD`/`SUBTYPE_HEEFT_DATA`, toestand-gebaseerd).

Borging: `test_engine_borging_li057`/`_li059` (score = enige lifecycle-driver),
`test_backfill_beoordeeld_li058` (backfill), verse reseed (16 applicaties + database-scoring).
Status: **Aanvaard — gerealiseerd t/m LI059**.

## Wijziging W2 — LI050: vraagbeheer wordt een beheerdersbevoegdheid

| | |
|---|---|
| **Status** | Aanvaard |
| **Datum** | 2026-07-23 |
| **Beslissers** | Bert van Capelle |
| **Grond** | `docs/Analyse-rechtenverdeling-V050.md` (M3-1) + `docs/Checkpoint-productie-gereedheid-V050.md` (§2A) |

**Context.** W1 maakte de vragenset tenant-eigendom, maar liet het mutatierecht op het
inhoud-patroon staan (medewerker mag aanmaken/wijzigen/deactiveren). De rechtenanalyse LI050
stelde vast dat vraagbeheer **organisatiebreed** reikt: één mutatie verandert wat er van élk
component van een type gevraagd wordt (deactiveren raakte in de meting 20 componenten en 5
gegeven antwoorden). Dat is dezelfde reikwijdte waarvoor het referentiemodel-inlezen eerder al
van het inhoud-patroon naar beheerder-only is gecorrigeerd.

**Besluit.** Vraagbeheer blijft per tenant, maar de mutaties (vraag aanmaken, wijzigen,
antwoordtype en antwoordopties beheren, uit-/aanzetten) zijn **uitsluitend voor de
beheerdersrol van de tenant**. Lezen blijft voor álle tenant-rollen — de vragenlijst is het
antwoord op *"waarom vraagt LIKARA mij dit?"* en blijft voor iedereen inzichtelijk.

**Vorm.** Eén plek: de `CHECKLISTVRAAG`-entry in de rechtenmatrix (`rbac.py`) volgt nu het
REFERENTIEMODEL-patroon (Viewer/Medewerker/Auditor L · Beheerder LAWV). Alle acht
mutatie-routes van `/checklistconfig` erven dit via hun bestaande guards — geen per-route
wijziging. UI: bewerk-affordances afwezig voor niet-beheerders, met de uitlegzin
*"De vragenlijst wordt bepaald door de beheerder van uw organisatie."* (NormBeheer-patroon).

**Buiten dit besluit** (bekende gebreken rond deactiveren, blijven eigen vervolgpunten): de
engine telt scores op gedeactiveerde vragen mee, en een blokkade op een gedeactiveerde vraag
is via de UI niet af te sluiten (Checkpoint V050 §G2-1/G2-2).
