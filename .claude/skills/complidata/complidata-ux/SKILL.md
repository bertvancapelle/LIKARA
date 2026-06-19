---
name: complidata-ux
description: Interaction-design-denkmethode voor CompliData. Verplicht te raadplegen bij ELKE frontend-rakende slice (nieuw scherm, nieuwe sectie, nieuwe actie) — door zowel CC als claude.ai. Borgt dat een functie de UI logisch en compleet houdt voor de gebruiker: geen lege lijsten zonder route naar de actie, actie op de plek waar de gebruiker hem verwacht, terminologie vanuit de gebruiker. Dit is GEEN stijl-/visuele skill (dat is complidata-frontend); dit gaat over of het scherm doet wat de gebruiker verwacht.
bijgewerkt: V015
---

# CompliData UX / Interaction-Design Skill

## Kernprincipe (niet-onderhandelbaar)

**Gebruikerservaring is altijd het startpunt.**
Elke ontwerpbeslissing, elke afweging en elk advies vertrekt vanuit de vraag:
*wat is het beste voor de gebruiker van KILARA?*
Schema, migraties, RBAC en technische borging zijn vangrails die de UX-keuze
ondersteunen — ze sturen hem niet.

Dit principe overschrijft technische voorkeur als de twee conflicteren.

### Functioneel beschrijven is de NORM, niet de uitzondering (DC014, niet-onderhandelbaar)

Elke vraag, elk advies, elke afweging en elke analyse — door CC én claude.ai — vertrekt
vanuit de gebruiker van KILARA: *wat betekent dit voor de gebruiker, wat ziet/doet hij?*
Techniek (schema, endpoints, RLS, RBAC, migraties) komt **alleen** ter sprake als (a) de
gebruiker er expliciet om vraagt, of (b) als vangrail bij een gate/borging — **nooit als
opening of toon** van een antwoord. Een advies dat begint bij de tabel of het schema is
fout, óók als het technisch klopt: herformuleer het vanuit wat de gebruiker wil bereiken.

## Waarom deze skill bestaat

CompliData wordt gebouwd vanuit één vast uitgangspunt: **continu optimaliseren van de
gebruikerservaring.** Techniek, schema en proces zijn vangrail, nooit het vertrekpunt.
Deze skill maakt dat uitgangspunt operationeel voor het scherm: bij elke functie die de
UI raakt, eerst denken vanuit wat de gebruiker ziet, verwacht en wil doen — pas daarna bouwen.

## Vast uitgangspunt — GENERIEK multi-tenant platform (niet-onderhandelbaar)

CompliData/CompliMan is een **generiek multi-tenant platform**. **BWB** is slechts een
voorbeeld van een organisatie die het gebruikt; **Tiel** een voorbeeld van een
ontvlechtingscontext. Ontwerp platform, datamodel, schermen, terminologie en features
**nooit** alsof ze BWB/Tiel-specifiek zijn — alles is **tenant-agnostisch en herbruikbaar**
voor elke tenant. BWB/Tiel dienen uitsluitend als concreet voorbeeld om scenario's te
toetsen, niet als ontwerpdoel. Concreet: geen hardcoded organisatie-/operatornamen,
geen aannames over één specifieke ontvlechting, labels en velden algemeen genoeg voor
elke overheidsorganisatie. Dit geldt platform-breed (ook backend/db/frontend), maar staat
hier omdat het ontwerp-denken ermee begint.

### Eén tenant nu — géén tenant-onderscheid in deze fase (DC014, niet-onderhandelbaar)

"Tenant-agnostisch" (hierboven: niet BWB/Tiel hardcoden) is **niet** hetzelfde als
"ontwerp voor meerdere gelijktijdige tenants met per-tenant-verschillen". KILARA draait nu
als **één implementatie met één gebruikerswereld**; er is **geen functioneel
tenant-onderscheid**. Dus:

- **Niet vooruit ontwerpen op meerdere tenants** en niet de **"per-tenant"-reflex** inzetten
  bij vragen over rechten, catalogi of zichtbaarheid. Voorbeeld: RBAC is één platform-brede
  matrix (geen per-tenant-rechtenvariatie); catalogi zijn gedeeld, niet per-tenant
  gedifferentieerd, tenzij de gebruikerslogica dat écht vraagt.
- **RLS / tenant-isolatie blijft technisch bestaan als fundament** (`tenant_id` + policies) —
  maar het is **geen ontwerp- of gespreksonderwerp** tot er echt meerdere tenants zijn.
  Verschijnt "per tenant" in een advies/analyse zonder dat de gebruiker erom vroeg, dan is
  dat bijna altijd de verkeerde abstractie voor deze fase: herformuleer vanuit de ene
  gebruikerswereld.
- Verenigbaar met het bovenstaande: bouw **generiek** (geen hardcoding), maar voeg **geen
  per-tenant-differentiatielogica** toe zolang er één tenant is.

Twee concrete missers die deze skill voorkomt (DC012):
1. **Partij-detailscherm met drie leeslijsten en geen enkele toevoeg-knop.** De gebruiker
   verwachtte afdelingen/personen te kunnen toevoegen op de plek waar ze getoond worden,
   maar moest naar een ander scherm en daar de relatie handmatig terugleggen.
2. **Rollen (catalogus) wel beheerbaar in de backend, maar geen beheerscherm.** De functie
   bestond technisch, maar was voor de gebruiker onvindbaar/onbruikbaar.

In beide gevallen waren de tests groen en het datamodel correct — en tóch was de functie
voor de gebruiker niet af. Daar is deze skill voor.

---

## De denkmethode (loop dit af vóór je een frontend-slice ontwerpt of bouwt)

### 1. Gebruikersdoel
Wat wil de gebruiker hier bereiken? Formuleer het als een zin in gebruikerstaal,
niet in datamodel-/schema-taal. ("Ik wil zien wie verantwoordelijk is voor deze
applicatie" — niet "ik wil de roltoewijzing-relaties van dit element ophalen".)

### 2. Wat moet de gebruiker hier kunnen
Som de handelingen op die de gebruiker logischerwijs op dit scherm verwacht: zien,
toevoegen, wijzigen, verwijderen, doorklikken. **Een lijst die iets toont, roept bijna
altijd de verwachting op dat je er ook iets aan kunt toevoegen** — tenzij expliciet en
zichtbaar gemaakt is dat dat ergens anders gebeurt.

### 3. Acties op de juiste plek
De gebruiker verwacht een actie op de plek waar het onderwerp leeft. Een afdeling
toevoegen aan een organisatie hoort op de organisatie-pagina, niet op een generiek
aanmaakscherm waar je de organisatie terug moet kiezen. Voorinvulling van context
(de organisatie staat al ingevuld) is een teken van goede plaatsing.

### 4. Lege staten
Elke lege lijst krijgt een lege-staat die óf een route naar de actie biedt ("+ Toevoegen"),
óf uitlegt waarom hij leeg is en waar de actie dan wél zit ("Rollen wijs je toe vanaf de
applicatie of het contract."). **Een lege lijst zonder knop en zonder uitleg is een bug,
geen neutrale toestand.**

### 5. Terminologie
Labels en koppen volgen hoe de gebruiker denkt, niet de tabelnamen. "Verantwoordelijkheden",
niet "assignment-relaties". "Wie hoort hierbij", niet "lidmaatschap-FK".

### 6. Consistentie met bestaande schermen
Een nieuwe sectie hoort qua interactie te lijken op vergelijkbare bestaande secties
(zelfde knop-plaatsing, zelfde lege-staat-stijl, zelfde manier van toevoegen/verwijderen),
zodat de gebruiker niet per scherm opnieuw moet leren.

---

## Toepassing in de praktijk

- **Elke frontend-rakende bouwopdracht** opent met een korte "Wat de gebruiker straks kan"-
  beschrijving (gebruikerstaal, niet schema). Dit is de uitkomst van stap 1–2 hierboven.
- **Bij elke nieuwe lijst/sectie**: expliciet benoemen wat de lege staat toont en of er een
  toevoeg-actie hoort.
- **Bij read-only secties** (zoals "Rollen op objecten" op de partij): de lege-staat-tekst
  wijst de gebruiker naar waar de actie wél plaatsvindt.
- **Bij een nieuwe beheerbare catalogus**: controleer of er een beheerscherm bij hoort —
  een lijst configureerbaar maken in de backend zonder UI laat de functie onvindbaar.

## UX-doorlichting bij een afgeronde feature-reeks (beproefd, DC012)

Na een afgeronde reeks slices loont een **read-only UX-doorlichting** over álle geraakte
schermen, langs de denkmethode hierboven. Bevindingen geprioriteerd:
- **A — storend gat**: de gebruiker kan iets niet wat het scherm wél suggereert (lijst zonder
  toevoeg-route; beheerbare catalogus zonder beheerscherm).
- **B — inconsistentie**: jargon i.p.v. gebruikerstaal, afwijkende kolomkop/term, ontbrekende
  doorklik/sortering t.o.v. vergelijkbare schermen.
- **C — nette to-have**: kleine politoer, geen functioneel gat.
Uit de doorlichting volgen **landbare reparatie-slices** (één bevinding of een kleine bundel
per gate-slice). De doorlichting zelf muteert niets — alleen rapporteren + prioriteren.

**Toets "lijst-zonder-CRUD-op-de-plek-waar-het-leeft = gat"** (DC012 meermaals raak): toont een
scherm een lijst van X'en die daar thuishoren, dan hoort de gebruiker X daar ook te kunnen
toevoegen/wijzigen — tenzij zichtbaar gemaakt is dat het elders gebeurt (dan de lege-staat-route,
stap 4). Een leeslijst zonder die route is bijna altijd een A-gat.

## Landschapskaart UX-patronen (ADR-025, DC013)

### Drie-modus graaf
Één view, drie perspectieven via toggle:
- Ego-view: één centrum, directe buren, klik=hercentreren
- Impact-view: migratieset multi-select, raakvlak-detectie
- Geheel model: full-graph, opbouw (leeg→vol) of afpel (vol→leeg)

### Actieve set
De migratieset is een `Set<uuid>` in Vue-state. Toevoegen via zoekresultaten,
verwijderen via rechterpaneel ×-knop. "Voeg alle gefilterde toe" vult de set met het
gefilterde resultaat.

### Resultatenlijst: alleen applicaties
De zoeklijst/filters tonen ALLEEN applicaties (element_type='applicatie'). Partijen/
contracten/infra verschijnen automatisch als ring-nodes rond de geselecteerde applicaties —
nooit als kiesbare entiteiten.

### Selectie highlight
Klik actieve-set-item → `selecteerNode(id)`: `cy.elements().unselect()` →
`cy.getElementById(id).select()` → `cy.animate({ center:{eles:node}, zoom:max(zoom,1.2), 400ms })`.

### Node-detail start leeg
Het detail-paneel toont "Klik een node voor detail" bij mount; vult pas na node-klik of
set-item-klik. Toont o.a. plateau/dispositie (migratieplaatsing) indien gevuld.

### "Open applicatie →" doorklik
`router.push({ name: 'applicatie-detail', params: { id: node.id } })` — knop in het
detail-paneel (alleen voor applicatie-nodes); conditioneel "+ Voeg toe / × Verwijder uit set".

### Deep-link vanuit applicatie-detail
`<router-link :to="{ name: 'landschapskaart', query: { center: id, modus: 'ego' } }">`
"🗺 Open in Landschapskaart →". LandschapskaartView leest `?center` + `?modus` bij onMounted.

### Diepte-toggle
"1 stap (direct)" / "2 stappen" (ego + geheel). Diepte 2 voegt de indirecte applicatie-buren
toe (partijen/contracten/infra blijven op diepte 1); client-side op de geladen graaf.

## Verhouding tot andere skills

- `complidata-frontend` = hoe je bouwt (Vue/PrimeVue/Tailwind, tokens, presets). Stijl en techniek.
- `complidata-ux` (deze) = of het scherm klopt voor de gebruiker. Interaction design.
- Beide raadplegen bij frontend-werk; deze skill gaat over het ontwerp-denken vooraf,
  de frontend-skill over de uitvoering.
