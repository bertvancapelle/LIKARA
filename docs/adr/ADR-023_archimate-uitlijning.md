# ADR-023 — ArchiMate-uitlijning: element-identiteit, getypeerd relatiemodel, migratielaag

**Status**: Aanvaard — CD008 (bovenop ADR-006, head na `6eb0699`). Implementatie in deze opdracht
(Fase A–F; Open Exchange-export = latere additieve fase, buiten scope).
**Voortbouwend op**: ADR-021 (component-herfundering, supertype/subtype shared-PK, landschapsgraaf),
ADR-022 (`checklist_dragend`/beoordeling per type), ADR-020 (contractregister), ADR-019/ADR-012-A
(beheerbare catalogus met metadata), ADR-018 (gefocuste ego-graaf), ADR-013/016 (lifecycle/blokkade),
ADR-006 (audit-trail).

---

## Context

CompliData lijnt uit op de ArchiMate-definities om drie doelen inzichtelijk te maken:
inventarisatie, relaties (waar draaien componenten logisch, welke logische interfaces onderling),
en de contractuele onderbouwing van het IT-landschap — inclusief een registreerbare gap-analyse mét
migratie-work-packages. Bewust een **gecureerde subset** van ArchiMate, niet het Full Framework.
ArchiMate's eigen model (één identiteitsruimte van elementen; relaties verwijzen via source/target
naar element-id's, elk met een type) is de leidraad. Het uitwisselingsformaat is een intermediaire
export, geen interne opslagvorm.

## Besluiten

1. **Eén getypeerd relatiemodel via een gedeelde `element`-identiteit (shared-PK subtyping).** Eén
   relatie-tabel met echte FK's voor bron/doel naar de element-identiteit; relatietype uit
   catalogus. Geen polymorfe `type+id` (niet-structureel), geen exclusieve arc (slechter
   schaalbaar). `element` is supertype; `component` wordt subtype (keten
   `element.id = component.id = applicatie.id`).
2. **Eersteklas elementen:** component (+ subtypes), datatype, gebruikersgroep, contract, plateau,
   gap, work package, deliverable. Leverancier blijft FK via contract (geen element).
3. **Vervangen, niet overlay:** `koppeling` + `component_structuur` + `component_contract` migreren
   naar het ene relatiemodel; bestaande relatietypes worden ArchiMate-relatietypes.
4. **Element-typing op de catalogus:** `archimate_element` + `laag` + `aspect` als kolommen op
   `componentconfig_optie` (dim componenttype); dekkingstest dwingt mapping per actief type af.
5. **Dubbelzinnige typen:** `database`/`fileshare` → technologielaag (system software resp.
   node/artifact), de gegevens erin als gerelateerd datatype (data object); `saas_dienst` →
   application component met hosting model = saas als classifier.
6. **Relatie-subset als beheerbare catalogus-dimensie:** composition, aggregation, serving,
   assignment, flow, realization, association.
7. **Hosting model ↔ draait_op onafhankelijk:** hosting model = snelle zelf-declaratie-classifier op
   de component; draait_op = precieze node-relatie. Geen afleiding tussen beide (bewuste
   niet-koppeling, zoals oordeel↔antwoord ADR-019).
8. **Relaties worden expliciet en toerekenbaar door een gebruiker gelegd; het systeem leidt nooit
   zelf relaties af.** Bulk-/import-invoer mag (bevestigde invoer, geen afleiding); read-traversals
   (impact-graaf) blijven afgeleid (navigeren ≠ ontstaan).
9. **Uitbreidbaarheidsinvariant:** een nieuw componenttype = catalogusregel + verplichte
   ArchiMate-mapping; direct relateerbaar zonder wijziging aan het relatiemodel; shared-PK-subtype
   alléén bij type-eigen velden; eigen beoordeling via bestaande `checklist_dragend` (ADR-022).
   Toetsbaar (afwijken naar nieuwe tabel/code voor een "kaal" type = afwijking).
10. **Technische plaatsing afgedwongen via de checklist** (vraag "is technische plaatsing
    vastgelegd?" met consistentiecheck antwoord-ja ↔ bestaande draait_op-relatie). **Score blijft de
    enige lifecycle-driver**; geen tweede engine-poort. Engine-logica byte-identiek.
11. **Migratielaag:** Plateau (levende membership + dispositie per lid:
    behouden/migreren/vervangen/uitfaseren); Gap (geregistreerd object, verbindt baseline+doel-
    plateau, bevat gap-componenten, draagt work packages + toelichting; gereedheid = **rollup uit de
    bestaande lifecycle**, geen tweede readiness-bron); Work Package (hiërarchisch via self-FK,
    structurele cycluspreventie zoals contract-mantel I3); Deliverable (realisatieketen work package
    → deliverable → doel-plateau). Implementation Event uitgesteld/uit scope.
12. **Tenant-integriteit:** `UNIQUE(tenant_id, id)` op de element-identiteit; relatie-FK's verwijzen
    naar (tenant + id) → cross-tenant relaties structureel uitgesloten. Nuance: dit is
    relatie-*integriteit*; de toegangsscheiding blijft RLS+FORCE als hoofddrager (defense in depth,
    geen enkele laag absoluut). Endpoint-integriteit is hiermee opgelost (echte enkelvoudige FK's,
    geen "precies-één-gevuld"-CHECK).
13. **CASCADE-wijziging:** datatype/gebruikersgroep worden zelfstandige elementen; bij verwijderen
    van een applicatie vervalt alléén de relatie, niet het element. "Wezen" (elementen zonder enige
    relatie) worden zichtbaar gemaakt. (Gedragswijziging t.o.v. de huidige ON DELETE CASCADE.)
14. **Open Exchange-export:** latere additieve fase, **buiten scope** van deze opdracht.

## Verfijningen (CD008 v2 — OK-1/2/3)

**OK-1 — Mapping bestaande relatie → ArchiMate-relatietype (type én richting).** ArchiMate-relaties
zijn **gericht**; de migratie mapt per bestaande relatie zowel het type als de richting:

| Bestaand | ArchiMate-type | Richting (bron → doel) |
|---|---|---|
| `maakt_deel_uit_van` | **aggregation** | deel → geheel (losse geheel-deel; delen bestaan zelfstandig) |
| `draait_op` | **assignment** | **host → gehoste** (node → component) — oriëntatie **omgedraaid** t.o.v. `component_structuur` (dat sloeg component → op_component op) |
| `koppeling` | **flow** | bron → doel (gerichte informatie-/datastroom) |
| `component_contract` | **association** | component → contract |
| `gebruikersgroep` ↔ `applicatie` | **serving** | applicatie → gebruikersgroep (applicatie bedient business actor/role) |
| `datatype` ↔ `applicatie` | **access** | applicatie → datatype (actieve structuur → data object) |

De relatie-subset is hiermee **acht** typen (verfijning op Besluit 6): composition, aggregation,
serving, assignment, flow, realization, association, **access**. Richting-correctheid per
gemigreerd type is een verplichte test.

**OK-2 — Relatie-attributen als beheerbare kenmerken per relatietype.** Beschrijvende kenmerken
(bv. `protocol`, `impact_bij_verbreking`, `relatie_rol`) worden **per relatietype in de catalogus
gedefinieerd** (property-definities) en op schrijfmoment daartegen gevalideerd; opslag in **jsonb**
op de relatie. Uitbreiden = catalogusregel, geen schemawijziging (consistent met Besluit 9). De
*integriteit* van de relatie blijft volledig schema-afgedwongen: composiet-FK (tenant+id), echte
endpoint-FK's, CHECK `bron≠doel`, UNIQUE.

**OK-2-verfijning (CD008 v3) — richting is een kenmerk, geen duplicatie.** De primaire oriëntatie
van een relatie blijft `bron→doel`. Een eventuele tweezijdigheid wordt vastgelegd als een
**richting-kenmerk** (`eenrichting`/`tweerichting`) — een beheerbaar kenmerk per relatietype (bv. op
`flow`), gevalideerd tegen de catalogus-property-definitie — en **niet** als een tweede relatie.
Daarmee is de datamigratie **1-op-1**: één `koppeling` → één `flow`-relatie, ongeacht
eenrichting/tweerichting; de oorspronkelijke koppeling blijft als één relatie herkenbaar. (Dit
vervangt de eerdere "tweerichting → twee flows"-consequentie.)

**OK-3 — Resterende type-mappings + waardelijsten.** `client_software` → **system software**;
`middleware` → **system software** (beide technologie). Toegestane `laag` ∈ {business, application,
technology, implementation_migration}; `aspect` ∈ {active, passive, behavior}.
`implementation_migration` wordt alléén door de migratie-elementen (plateau/gap/work_package/
deliverable) gebruikt; `behavior` is in het huidige gecureerde model leeg (geen gedragselementen).

## Verfijning ADR-023a — meervoudige flow-koppelingen + koppeling-naam

Amendement op Besluit 1/6/12 (de invariant "`UNIQUE(tenant_id, bron_id, doel_id, relatietype)` —
één relatie per (bron, doel, type)").

- **Meervoud voor `flow`:** tussen twee systemen kunnen meerdere koppelingen (flows) in dezelfde
  richting bestaan — elk met een eigen protocol/functie (bv. een API voor functie A en een aparte
  API voor functie B). Dat zijn reële, los te beheren afhankelijkheden; de all-types-uniciteit
  verbood die legitieme registratie. De uniciteit wordt daarom **partieel**:
  `UNIQUE(tenant_id, bron_id, doel_id, relatietype) WHERE relatietype <> 'flow'` (migratie 0039).
  Alle **andere** relatietypen (association, assignment, aggregation, realization, …) blijven
  uniek per (bron, doel, type). De registratie-eenheid van een koppeling is de bestaande
  surrogaat-PK `relatie.id`.
- **Koppeling-naam:** `relatie.naam` (`String(150)`) — een identificerend, sorteerbaar veld,
  DB-nullable maar **app-verplicht voor flow** (afgedwongen in de servicelaag, Fase 2). Onderscheidt
  meerdere koppelingen tussen dezelfde twee systemen voor de gebruiker.
- **Dubbel-signalering (Fase 2):** een flow die op alle velden gelijk is aan een bestaande (op de
  vrije `omschrijving` na) levert een overrulebare waarschuwing — signalering, geen harde blokkade,
  geen engine-poort.
- Engine onaangeroerd: relatie is geen lifecycle-driver; deze verfijning is registratief.

## Gevolgen / invarianten

- Relatie tenant-consistent via composiet-FK; `bron≠doel`; relatietype-catalogus-validatie;
  cyclus-veilig lezen (visited-set).
- Gereedheid-rollup als pure functie over de bestaande lifecycle (geen tweede bron).
- Realisatieketen-integriteit (work package → deliverable → plateau); work-package-hiërarchie zonder
  cyclus.
- ArchiMate-element/relatie-typering 1-op-1 met catalogus (synctest).
- Nieuwe auditeerbare entiteiten toegevoegd aan de ADR-006-capture-allowlist.

## Niet in scope

Open Exchange-export (latere fase); Motivation/Strategy/Physical-lagen; Implementation Event;
relaties-op-relaties (junctions); leverancier als element.
