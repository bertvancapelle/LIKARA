---
name: likara-domeinmodel
description: >
  Canonieke "kaart" van het LIKARA-domeinmodel. Lees dit vóór elke slice
  die een element, relatie, catalogus, partij, of registratie-feit raakt.
  Dekt: element-familie + ArchiMate-typings, relatiemodel (8 typen), migratielaag
  (plateau/gap/work_package/deliverable), partijenregister (ADR-024, 4 aarden),
  catalogus-families (scope platform vs. tenant), engine-invariant, RBAC/audit-
  ankerpunten, en harde architectuurregels. De HOE (implementatiepatronen) staat
  in likara-db en likara-backend; dit bestand beschrijft het WAT.
stack: PostgreSQL 16, SQLAlchemy asyncio, FastAPI — ADR-021/023/024/025/026
bijgewerkt: V028
---

# LIKARA Domeinmodel — Kaart

Dit is de canonieke referentie voor het domeinmodel: **wat** bestaat er, hoe hangt
het samen, en welke regels zijn onschendbaar. De **HOE** (implementatiepatronen,
RLS-boilerplate, keyset-cursor, seed-patroon) staat in likara-db en
likara-backend. Gebruik dit bestand als eerste oriëntatie bij elke nieuwe slice.

---

## 1. Element-familie

Eén `element`-identiteitsruimte: `UNIQUE(tenant_id, id)`, FORCE RLS.
Alle entiteiten in de onderstaande tabel zijn **element-subtypes**: ze hebben een
eigen tabel met een composiet-PK/FK `(tenant_id, id) → element(tenant_id, id)`
ON DELETE CASCADE. (Subtype-bouwrecept: zie likara-db V009/V010-patronen.)

### Volledige element-typetabel (ELEMENT_ARCHIMATE_TYPING, V013)

| `element_type` | Eigen tabel | `archimate_element` | `laag` | `aspect` | Noot |
|---|---|---|---|---|---|
| `component` | `component` | via componenttype-catalogus | via catalogus | via catalogus | élk componenttype (incl. `applicatie`) |
| `datatype` | `datatype` | `data_object` | `application` | `passive` | |
| `gebruikersgroep` | `gebruikersgroep` | `business_role` | `business` | `active` | |
| `contract` | `contract` | `contract` | `business` | `passive` | |
| `plateau` | `plateau` | `plateau` | `implementation_migration` | `passive` | |
| `gap` | `gap` | `gap` | `implementation_migration` | `passive` | |
| `work_package` | `work_package` | `work_package` | `implementation_migration` | `behavior` | ① |
| `deliverable` | `deliverable` | `deliverable` | `implementation_migration` | `passive` | |
| `partij` | `partij` | `business_actor` | `business` | `active` | Alle 4 aarden |

① `work_package` heeft `aspect = behavior` — bewuste, gedocumenteerde afwijking van
OK-3 ("behavior leeg in gecureerde subset"); volgt de ArchiMate-standaard voor
implementation migration work packages.

> **LI059 — `applicatie` is GEEN element_type/subtype (meer).** De `applicatie`-subtabel is gedropt
> (migratie 0047) en `ElementType` heeft **geen** `applicatie`-waarde. Een applicatie is **een component
> met `componenttype='applicatie'`** — `element_type='component'`, ArchiMate-typing via de
> componenttype-catalogus (ADR-026). Er is geen aparte `/applicaties`-API/-service/-schema, geen
> `Entiteit.APPLICATIE` (RBAC) en geen `applicatie`-audit-ingang meer: **`component` is de enige bron**
> in data/API/RBAC/audit. De convergente creatie-kern is `component_service.maak_applicatie_component`.
> (Historie: t/m V027 was `applicatie` een shared-PK-subtype van `component` — ADR-021.)

**Partitietest**: `test_archimate_fase_a` / `test_archimate_fase_d` bewaken dat
`ELEMENT_ARCHIMATE_TYPING`, `ELEMENT_TYPEN_VIA_COMPONENTTYPE` en (als die leeg is)
`ELEMENT_TYPEN_NOG_NIET_GEREALISEERD` samen de volledige `element_type_enum`
exact + disjunct afdekken. Een vergeten of nieuw type faalt hier zichtbaar.

### ComponentType-typing (ADR-026 — volledig geland, V013)

Component-elementen erven hun ArchiMate-typing **niet** uit ELEMENT_ARCHIMATE_TYPING
maar uit de `componentconfig_optie`-catalogus (kolommen `archimate_element`, `laag`,
`aspect` per componenttype). Regels (ADR-026):

- **Gesloten lijsten**: `archimate_element` ∈ `TOEGESTANE_ELEMENTEN` (18 waarden,
  code-constante); `laag` ∈ `TOEGESTANE_LAGEN`; `aspect` ∈ `TOEGESTANE_ASPECTEN`.
- **Volledigheid**: een **actief** componenttype moet alle drie velden ingevuld hebben
  (service-side validatie + runtime-test die dit borgt op de live DB).
- **Geen combinatievalidatie**: het systeem dwingt geen ArchiMate-puristische
  combinaties af — de platformbeheerder draagt verantwoordelijkheid voor een
  zinvolle mapping.
- **RBAC**: typing bewerken = platformbeheerder (`PlatformEntiteit.COMPONENTCONFIG`).

### Componenttype-set (LI060, V028 — 8 typen)

`applicatie` (application_component/application) · `database` (system_software/technology) ·
`server_compute` (node/technology; was `applicatieserver`) · `client_software`
(system_software/technology) · `saas_dienst` (application_component/application) ·
`integratievoorziening` (**system_software/technology** — eigen bindweefsel/ESB; was `middleware`) ·
`fileshare` (node/technology) · `landelijke_voorziening` (**application_service/application** —
extern afgenomen). **`checklist_dragend=True`** (krijgt profiel + ≥1 tenant-startvraag) voor:
`applicatie`, `database`, `server_compute`, `integratievoorziening`, `landelijke_voorziening`;
`client_software`/`saas_dienst`/`fileshare` = False. Startvragen leven in de tenant-checklist-
baseline (`seed.py`), niet platform-breed.

### Componentclassificatie (ADR-028, V028 — instance-eigenschap, engine onaangeroerd)

Twee registratieve labels op **elk** component, los van het type (puur registratief; voedt de
engine NIET):
- **`componentrol`** — `String(60)`, **NOT NULL, server_default `interne_applicatie`**,
  app-gevalideerd tegen `componentrol_optie` (intern / interne_dataprovider / externe_dataprovider /
  koppelvlak). Elk component heeft altijd een rol (geen lege staat, geen rol-registratiegat).
- **`biv_beschikbaarheid` / `biv_integriteit` / `biv_vertrouwelijkheid`** — `String(60)`, **nullable**
  (leeg = registratiegat), app-gevalideerd tegen `biv_schaal_optie` (ordinaal via `volgorde`).
- Read geeft rol + BIV + labels terug (labelresolutie ook voor gedeactiveerde sleutels).
  Migratie 0048 additief; geen datamigratie.

### Wanneer een nieuw element-subtype?

Alleen bij **type-eigen velden**. Een "kaal" type (alleen naam + ArchiMate-typing)
is geen subtype — het blijft een generieke `component`-rij met een componenttype
uit de catalogus.

---

## 2. Relatiemodel

Eén `relatie`-tabel: gericht `bron_id → doel_id`, composiet-FK's
`(tenant_id, bron|doel) → element(tenant_id, id)`, `CHECK bron ≠ doel`,
`UNIQUE(tenant_id, bron_id, doel_id, relatietype)`.

### ADR-023a — meervoudige flow-koppelingen + naam (V016, migraties 0039/0040)

De uniciteit is **partieel**: `UNIQUE(tenant_id, bron_id, doel_id, relatietype) WHERE
relatietype <> 'flow'`. **Flow mag meervoud** per `(bron, doel)` — tussen twee systemen kunnen
meerdere koppelingen in dezelfde richting bestaan (eigen protocol/functie). **Alle andere
relatietypen blijven uniek** per `(bron, doel, type)`. De registratie-eenheid van een koppeling
is de surrogaat-PK `relatie.id`.

- **`naam` (kolom, `String(150)`)**: identificerend, sorteerbaar; **verplicht voor flow**
  (servicelaag), optioneel/n.v.t. voor andere typen. DB-nullable (geen breuk op niet-flow-rijen).
- **Wederkerigheid (gevalideerd):** een flow is **ÉÉN gedeelde gerichte rij** (geen heen/terug-
  duplicaat). Dezelfde rij verschijnt bij de **bron als uitgaand** en bij het **doel als inkomend**
  (afgeleid uit `bron_id`/`doel_id` t.o.v. het object); verbreken bij A verwijdert exact de rij
  die B als inkomend zag. "Inkomend/uitgaand" (positie) ≠ het `richting`-kenmerk (een-/tweerichting).
- **Cardinaliteit-historie:** vóór ADR-023a verbood de all-types-uniciteit legitieme meervoudige
  koppelingen; meervoud-dezelfde-richting bestaat sindsdien, tegengestelde richting (`A→B`+`B→A`)
  kon altijd al (ander geordend paar).

De HOE (validatie, dubbel-signalering, override-audit) staat in likara-backend.

### De acht ArchiMate-relatietypes

| Type | Richting bron → doel | Primaire toepassing in LIKARA |
|---|---|---|
| `composition` | geheel → deel | Component-hiërarchie (deel is existentieel afhankelijk) |
| `aggregation` | geheel → deel | Plateau → lid; work_package → subpakket (lid bestaat zelfstandig) |
| `serving` | dienstverlener → bediende | Applicatie → gebruikersgroep |
| `assignment` | host/vervuller → gehoste | **draait_op**: host → component (oriëntatie!) |
| `flow` | bron → doel | Koppeling (informatie-/datastroom); richting als kenmerk |
| `realization` | realiseerder → gerealiseerde | work_package → deliverable → plateau |
| `association` | vrij | Component ↔ contract; generiek verband |
| `access` | actieve structuur → data-object | Applicatie → datatype |

**Oriëntatie-valkuil `draait_op` (assignment)**:
bron = HOST, doel = GEHOSTE COMPONENT.
Query "op welke host draait component X?" → zoek op `doel_id = X`.
Dit is **omgekeerd** t.o.v. het oude `component_structuur`-veld.

**Richting `flow` (koppeling)**:
Tweerichting wordt vastgelegd als `richting`-kenmerk op de relatie,
**niet** als twee aparte relaties. Één koppeling → één flow-relatie (1-op-1).

### Facade-over-Relatie vs. eigen tabel

**Gebruik de relatie-facade** (bestaand relatietype via `Relatie`-tabel) als:
- Het verband een ArchiMate-relatie is, EN
- `UNIQUE(tenant, bron, doel, relatietype)` de gewenste semantiek ondersteunt.

**Gebruik een eigen tenant-tabel** als:
1. De gewenste uniciteit **botst** met `UNIQUE(tenant, bron, doel, type)` — bv.
   meerdere rijen voor hetzelfde (bron, doel, type) met verschillende kenmerken, OF
2. Het verband een **registratie-feit** is, geen ArchiMate-relatie.

**Voorbeeld: `roltoewijzing`** (eigen tabel, migratie 0029/0030):
`UNIQUE(tenant_id, partij_id, object_id, rol)` — dezelfde partij kan meerdere
rollen op hetzelfde object hebben als losse rijen; onmogelijk via de `relatie`-facade
die slechts één rij per (bron, doel, type) toestaat.

### Type-validatie bron/doel — LEEFT NIET in de relatie-facade (geverifieerd V030)

**De generieke `relatie_service.maak_aan` valideert GEEN `element_type` van bron/doel per relatietype.**
Ze borgt alleen: bron ≠ doel (`ZELFVERWIJZING`), beide endpoints bestaan binnen de tenant (404),
`relatietype` is een geldige catalogus-sleutel, en de kenmerken tegen de catalogus (+ flow-dubbel).
Een `assignment` met een onzinnig bron/doel-type wordt door de facade dus NIET geweigerd.

**Endpoint-type-borging leeft uitsluitend in de eigen-tabel-services**, waar het verband een
registratie-feit is met eigen validatie:
- `roltoewijzing_service` — partij-aard/object-type per rol;
- `contract_service._valideer_contractpartij` — leverancier ∈ {organisatie, organisatie_eenheid,
  externe_partij}, nooit `persoon` (422 `ONGELDIGE_PARTIJ`);
- `gebruikersgroep_service._valideer_afdeling` — afdeling = org-eenheid binnen de grove-feit-organisatie.

Wil je bron/doel-typeborging op een ArchiMate-relatie, dan moet die expliciet worden toegevoegd — de
facade levert 'm niet gratis. (Historie: eerdere skill-versie beweerde ten onrechte dat de facade dit deed.)

### Relatie-kenmerken

Kenmerken op een relatie worden opgeslagen als **jsonb** op de `relatie`-rij,
gevalideerd tegen de `relatiekenmerk_optie`-catalogus (routing via dimensie).
Schema-integriteit (FK, UNIQUE, CHECK) blijft volledig schema-afgedwongen;
de kenmerken zijn additioneel beschrijvend, geen structurele borging.

### Lichtgewicht read-only engine-naburig patroon (DC013)
Voor read-only afleidingen naast de engine (bv. `blokkades_open` tellen,
lifecycle lezen in de Landschapskaart): gebruik een `table()`/`column()`-construct
i.p.v. een ORM-klasse-import, om engine-symbolen buiten scope te houden:

```python
from sqlalchemy import table, column, func, select
blokkade_t = table("blokkade", column("component_id"), column("opgelost_op"))
telling = select(func.count()).where(blokkade_t.c.component_id == id,
                                     blokkade_t.c.opgelost_op.is_(None))
```

Vermijdt het importeren van `Blokkade`/`ComponentProfiel` (engine-symbolen);
de import-afwezigheidstest blijft groen.

---

## 3. Migratielaag

Vier entiteiten, allen `laag = implementation_migration`, allen element-subtypes.
Modelleren de **kloof tussen huidige en gewenste situatie** en het werk om die te
dichten.

### Plateau
- Beschrijft een **levende situatie** (baseline of doelsituatie).
- **Leden** via `aggregation`-relaties (bron = plateau → doel = lid).
- Leden kunnen zijn: componenten ÉN contracten.
- Kenmerken op de lidmaatschapsrelatie (via relatiekenmerk-catalogus, dimensie `dispositie`):
  - `dispositie`: behouden / migreren / vervangen / uitfaseren
  - Contractuele bevestigingsvelden: bevestigd (bool), wie, wanneer, aantal_gebruikers, licenties
- **Readiness** = rollup uit de bestaande lifecycle — puur read-only afgeleid, **niets opgeslagen**.
  Twee aparte cijfers: technisch (lifecycle == `migratieklaar`) + contractueel (bevestigd).

### Gap
- Verbindt **baseline_plateau ↔ doel_plateau** als twee **verplichte composiet-FK's**
  direct op de gap-subtabel (geen relaties — vaste 2-ariteit, schema-afgedwongen).
- **Gap-leden** (componenten/contracten in de gap) wél via `aggregation`-relaties.
- Readiness: twee aparte cijfers (technisch + contractueel), telling + percentage.
- Leden zonder lifecycle/profiel vallen buiten de noemer.

### Work Package
- Hiërarchisch via composiet self-FK `(tenant_id, ouder_id) → work_package(tenant_id, id)`.
- Cycluspreventie in de **servicelaag** (visited-set), geen DB-trigger.
- Delete: 409 `HEEFT_SUBPAKKETTEN` bij aanwezige subboom (pre-check + RESTRICT-backstop).
- Directe zelf-koppeling geblokkeerd via `CHECK ouder_id <> id`.

### Deliverable
- Realisatieketen: `work_package → deliverable → plateau` via `realization`-relaties.
- Keten is **expliciet + optioneel**: deliverable mag zonder work_package of plateau bestaan.
- Systeem leidt de keten nooit zelf af (ADR-023 Besluit 8).

---

## 4. Partijenregister (ADR-024 — gebouwd t/m DC012, migraties 0026–0030)

### Vier aarden (één `partij`-subtabel, `partij_aard_enum`)

ADR-038 (migratie 0053): de enum telt nu **exact vier** waarden — de aparte `burger`-aard is
**verwijderd**. Burger-doelgroepen zijn gewone **externe organisaties** (aard=organisatie + scope=extern)
met afdelingen eronder.

| Aard | Omschrijving | `organisatie_id` | `afdeling_id` |
|---|---|---|---|
| `organisatie` | Organisatie als geheel (intern of extern) | — verboden — | — verboden — |
| `organisatie_eenheid` | Afdeling of team | **Verplicht** | Optioneel |
| `persoon` | Medewerker of contactpersoon | **Verplicht** | Optioneel |
| `externe_partij` | Leverancier, partner, ketenpartner | — verboden — | — verboden — |

**Schema-borging** (conditionele CHECK, migratie 0028):
```
(aard IN ('persoon','organisatie_eenheid')) = (organisatie_id IS NOT NULL)
afdeling_id IS NULL OR aard = 'persoon'
```
Fijnere cross-row regels (organisatie_id wijst naar een aard=organisatie;
afdeling_id hoort binnen die organisatie) leven in `partij_service._valideer_lidmaatschap`
→ 422 `ORGANISATIE_VERPLICHT` / `ONGELDIGE_ORGANISATIE` / `ONGELDIGE_AFDELING`.

### Intern/extern (`partij.scope`, ADR-038, migratie 0052)
Expliciet kenmerk `partij.scope` (`partij_scope_enum` = intern/extern), géén afgeleide uit de aard:
- **`organisatie`** → kiesbaar (default **extern**); de tenant markeert bewust zijn eigen organisatie
  als intern. Twee `aard=organisatie`-partijen kunnen aan verschillende kanten staan.
- **`externe_partij`** → **vast `extern`** (niet-wijzigbaar; de aard bepaalt het).
- **`organisatie_eenheid` / `persoon`** → **geen eigen waarde** (kolom NULL); ze **leiden af** van hun
  ouder-organisatie. Zo is een tegenstrijdige toestand (interne afdeling onder externe organisatie)
  structureel onmogelijk. Service: `_effectieve_scope`/`_valideer_scope` (422 `ONGELDIGE_SCOPE` /
  `EXTERNE_PARTIJ_ALTIJD_EXTERN` / `SCOPE_ALLEEN_ORGANISATIE`). UI: kiesbaar in `PartijFormulier`
  (radio, default extern), leesbaar in `PartijDetail`.

### ArchiMate-typing partij
Alle aarden: `business_actor` / `business` / `active`. Eén entry in
`ELEMENT_ARCHIMATE_TYPING` voor `element_type = partij`.

### Soort (optioneel, platform-breed)
`partijsoort_optie`-catalogus (geen RLS). Standaard-seed: `leverancier`, `partner`,
`ketenpartner`. De soort is **optioneel** op een partij (registratiegat).
**Catalogus is platform-breed** — niet tenant-eigen (zie §5).

### Roltoewijzing (`roltoewijzing`-tabel, migraties 0029/0030)

**Niet** via de relatie-facade — eigen tenant-tabel vanwege tegengestelde uniciteit.

| Veld | Beschrijving |
|---|---|
| `partij_id` | FK → element (de vervuller van de rol) |
| `object_id` | FK → element (het object: component of contract) |
| `rol` | FK → `beheerrol`-catalogus |
| `UNIQUE(tenant_id, partij_id, object_id, rol)` | Eén roltoewijzing per (vervuller, object, rol)-tripel |

Startset 9 rollen (beheerbaar door platformbeheerder), DC013:
Functioneel beheer · Technisch beheer · Applicatiebeheer · Contractbeheer ·
Product owner · Eigenaar · Proceseigenaar · **Account Manager** · **Service Delivery Manager**.

Meerdere rollen van dezelfde partij op hetzelfde object = meerdere losse rijen.
Meerdere partijen per rol op hetzelfde object = meerdere losse rijen.
Niets geforceerd (geen "één eigenaar per object").

### Contactvelden op partij (DC013, migratie 0033)
- `email` (255), `telefoon` (40), `mobiel` (40): platform-breed, gedeeld over alle aarden.
- `functietitel` (150): NIEUW, nullable — uitsluitend voor aard=persoon.
  Service dwingt af: andere aarden → 422 FUNCTIETITEL_ALLEEN_PERSOON.
- Het vrije-tekstveld `contactpersoon` (255) is **vervallen** — vervangen door de FK
  `contactpersoon_id` (ADR-039, migratie 0054; zie hieronder).

### Contactpersoon = verwijzing naar een persoon (ADR-039, migratie 0054)
- `partij.contactpersoon_id` = optionele composiet-FK `(tenant_id, contactpersoon_id) → element`,
  **ON DELETE SET NULL** (kolom-specifiek, PostgreSQL 15+; een kale SET NULL zou de gedeelde
  `tenant_id` mee-nullen). Vervangt het oude vrije-tekstveld: het aanspreekpunt is nu een echte
  verwijzing, geen losse string die stil kan gaan afwijken.
- **Leeft alleen op aard ∈ {organisatie, externe_partij}** (`_ORGANISATIE_ACHTIG`,
  `partij_service.py:26`). Andere aarden met een `contactpersoon_id` → 422
  (`_valideer_contactpersoon_aard`, ADR-039-aard-restrictie).
- **De persoon moet bij déze partij horen**: `persoon.aard = persoon` én
  `persoon.organisatie_id == deze partij` (`_valideer_contactpersoon`, `partij_service.py:143`);
  anders 422. Het aanspreekpunt wordt in de **bewerk**-flow gezet (bij Create levert
  `contactpersoon_id` terecht 422 — de persoon bestaat dan nog niet).
- Read-verrijking `contactpersoon_naam` op de lijst-/detail-items (`_verrijk_context`,
  `partij_service.py:212`). Een `externe_partij` **kán** personen dragen (organisatie-achtig).

### Gebruiker (persoon-partij): organisatie via afdeling + in-place wijzigen (LI032)
- **Een gebruiker hoort altijd bij een organisatie.** Bij aanmaken/wijzigen draagt de
  persoon-partij altijd een organisatie; die wordt **afgeleid uit de verplichte afdeling**
  (`maak_persoon_flush` / `werk_bij` → `_valideer_lidmaatschap`: afdeling = organisatie_eenheid
  binnen die organisatie). Org + afdeling worden **samen gezet en tegen elkaar gevalideerd**;
  tegenstrijdig → 422 (`ONGELDIGE_AFDELING`).
- **Aanspreekpunt-blokkade bij organisatiewissel.** Verplaats je een persoon naar een **andere**
  organisatie terwijl die persoon nog `contactpersoon_id` is van een partij die hij achterlaat →
  **weigeren** met 409 `AANSPREEKPUNT_BLOKKEERT_VERPLAATSING` (mét partijnaam;
  `gebruiker_service.py:285`), géén stille opschoning. Anders zou een registratie stil gaan liegen.
- **Wijzigen is in-place; "opheffen-en-opnieuw-aanmaken" als wijzigmechanisme is afgewezen** — dat
  breekt rollen / gebruikersgroep-lidmaatschap / aanspreekpunt / audit-continuïteit (die hangen aan
  de stabiele persoon-id). "Gebruiker opheffen" blijft een aparte, expliciete handeling.

### Contract → leverancier (huidig na DC013)
- FK-target: `(tenant_id, leverancier_id) → element(tenant_id, id)`, ON DELETE RESTRICT.
- Toegestane aarden: organisatie / organisatie_eenheid / externe_partij
- Persoon als contractpartij: geweigerd (422 ONGELDIGE_PARTIJ)
- Implementatie: TOEGESTANE_LEVERANCIER_AARDEN constante in contract_service
- Term "leverancier" blijft in het contract-domein (optie A, blast-radius-minimalisatie).

### Organisatie als verwijzing elders (B6, migraties 0031/0032)
- `component.eigenaar_organisatie_id`: optionele FK → element (aard=organisatie),
  ON DELETE SET NULL (kolom-specifiek, PostgreSQL 15+). Toont de gejoinde `Partij.naam` in
  lijsten/details (naam-in-read via alias). De eigenaar-picker filtert `aard=organisatie`.

### Gebruikersgroep: organisatie + afdeling (ADR-036 / ADR-036a / ADR-038, migraties 0050 + 0053)
- **Een groep hoort ALTIJD bij een organisatie** (ADR-038): `gebruik_id` is **NOT NULL** en de FK
  `fk_gebruikersgroep_gebruik` → `organisatiegebruik` is **ON DELETE RESTRICT** (was SET NULL — botst met
  NOT NULL; een grof feit/organisatie met groepen verdwijnt niet stil). De org-loze uitzondering vervalt.
- **Organisatie leeft NIET op de gebruikersgroep** (geen `organisatie_id`-kolom). Ze leeft op het **grove
  feit** `organisatiegebruik` (single source of truth); de gebruikersgroep verwijst er als fijne
  verfijning naar via `gebruik_id`. `organisatie_id` is een **verplicht** Create/Read-veld (Update
  optioneel-in-payload, nooit null → 422 `ORGANISATIE_VERPLICHT`), intern vertaald naar een grof feit
  (get-or-create via `organisatiegebruik_service.ensure`). Burger-doelgroepen = externe organisaties met
  afdelingen (geen aparte burger-aard meer).
- **Afdeling is structureel** (ADR-036a): `gebruikersgroep.afdeling_id` → organisatie_eenheid-partij
  binnen de grove-feit-organisatie (spiegel van persoon→afdeling), composiet-FK ON DELETE RESTRICT; geen
  vrije tekst meer. `_valideer_afdeling` borgt org-eenheid-binnen-organisatie (422 `ONGELDIGE_AFDELING`).
- **Identiteit**: "afdeling — organisatie" (bv. "Burgerzaken — Tiel"), zodat gelijknamige afdelingen van
  verschillende organisaties niet op één hoop vallen (`identiteit()`).
- Read geeft `organisatie_id`+`organisatie_naam` (uit grof feit) en `afdeling_id`+`afdeling` (partij-naam).

---

## 5. Catalogus-families

### Overzicht: platform-breed vs. tenant-eigen

**KERNREGEL**: Checklistvraag is de ENIGE tenant-eigen catalogus.
Alle andere catalogi zijn platform-breed. Dit is niet-onderhandelbaar.

| Catalogus | Tabel | RLS | Beheer door | Doel |
|---|---|---|---|---|
| Relatiekenmerk | `relatiekenmerk_optie` | Nee | Platformbeheerder (F-4) | Vocabulaire voor relatie-kenmerken (dimensies: `dispositie`, `relatie_rol`) |
| Partijsoort | `partijsoort_optie` | Nee | Platformbeheerder | Soort-aanduiding op partij |
| Beheerrol | `beheerrol` | Nee | Platformbeheerder | Rollen voor roltoewijzing |
| Vraagbetekenis | `vraagbetekenis_optie` | Nee | Platformbeheerder | Betekenis-marker op checklistvraag |
| Componentconfig | `componentconfig_optie` | Nee | Platformbeheerder | Componenttype-definitie incl. ArchiMate-typing |
| Contractconfig | `contractconfig_optie` | Nee | Platformbeheerder | Contract-attributen (dekking, kostenmodel) |
| Componentrol (ADR-028) | `componentrol_optie` | Nee | Platformbeheerder | Rol van een component (systeem-sleutel `interne_applicatie`) |
| BIV-schaal (ADR-028) | `biv_schaal_optie` | Nee | Platformbeheerder | Gevoeligheidsschaal B/I/V — **ordinaal via `volgorde`** |
| Checklistvraag | `checklistvraag`, `checklistvraag_optie` | Ja | Per tenant (kopie bij onboarding) | Beoordelingsvragen per componenttype |

**ADR-028 (V028):** `componentrol_optie` + `biv_schaal_optie` zijn **single-purpose** (geen
dimensie-discriminator; spiegel van `partijsoort_optie`). Grants exact als de andere platform-
catalogi (lk_app SELECT; lk_platform S/I/U, géén DELETE). RBAC: `PlatformEntiteit.COMPONENTROLCONFIG`
+ `BIVSCHAALCONFIG` (beheerder LAW, operator L). Beide op `AUDIT_PLATFORM_ENTITEITEN`. De BIV-schaal
is uitbreidbaar door de platformbeheerder; nieuwe niveaus krijgen hun rang via `volgorde`.

### Grants (platform-catalogi, alle gelijk)
`lk_app` = SELECT only (validatie).
`lk_platform` = SELECT / INSERT / UPDATE — **geen DELETE** (geen endpoint, geen grant).

### Soft-deactivatie
Opties worden **nooit** hard verwijderd. Deactiveren via `actief = false`.
Historische waarden blijven resolvebaar. Systeem-sleutels zijn niet deactiveerbaar
(`SYSTEEM_SLEUTEL_BESCHERMD`).

### Relatiekenmerk-catalogus — dimensies (V013)

| Dimensie | Sleutels | Toepassing |
|---|---|---|
| `dispositie` | behouden / migreren / vervangen / uitfaseren | Kenmerk op `aggregation`-relatie (plateau-lidmaatschap) |
| `relatie_rol` | valt_onder / onderhoud / hosting | Kenmerk op `association`-relatie (component↔contract) |

Routing in service: `{"type": "catalogus", "catalogus": "relatiekenmerk", "dimensie": "<dim>"}`.

---

## 6. Score/Lifecycle-engine Invariant

### De onschendbare regel
**Score is de ENIGE lifecycle-driver.**
Niets anders mag `component_profiel`, `lifecycle_status`, `Blokkade`, of
`Checklistscore` aanmaken, muteren, of afleiden buiten de score-engine.

### Wat MAG naast de engine
- **Lezen** van `Checklistscore.score` voor signalering of rapportage (read-only).
- Readiness-rollup als pure, **niet-opgeslagen** afleiding uit de bestaande lifecycle.
- Consistentiesignalering (geen engine-poort, geen blokkade-effect).
- Registratie-feiten (roltoewijzing, contractbevestiging, klaarverklaring) — volledig
  los van de engine.

### Wat NOOIT mag
Een nieuwe entiteit of feature:
- importeert `lifecycle_service` / `herbereken_lifecycle` / `bepaal_lifecycle` /
  `ComponentProfiel` / `Blokkade` / `Checklistscore` (schrijfpad).
- triggert een lifecycle-herberekening.
- slaat een tweede readiness-bron op.

### Dubbele machine-borging (verplicht per nieuwe slice naast de engine)
1. **Offline import-afwezigheidstest**: de nieuwe service importeert aantoonbaar
   NIET de verboden symbolen (statische import-scan).
2. **Live test**: de nieuwe entiteit/koppeling muteert geen `component_profiel` /
   `lifecycle_status` na aanmaken/koppelen.

Een read-only afleiding die `Checklistscore.score` **leest** mag dit — de
import-afwezigheidstest verbiedt dan alleen de schrijf-symbolen en wordt
aangevuld met een read-only bronscan (`session.add`/`commit`/`flush`/`delete`
mogen niet in de service-bron voorkomen).

---

## 7. RBAC + Audit — ankerpunten

### RBAC: `_INHOUD`-patroon (per nieuwe entiteit)

Nieuw element-type of registratie-entiteit → voeg toe aan `PERMISSIES`:
- Viewer: LEZEN
- Medewerker: LEZEN + AANMAKEN + WIJZIGEN
- Beheerder: LEZEN + AANMAKEN + WIJZIGEN + VERWIJDEREN
- Auditor: LEZEN

Platform-catalogus → `PlatformEntiteit.<NAAM>`, beheerder LAW (geen VERWIJDEREN).

RBAC-matrixtests bewegen mee bij elke toevoeging.

### Audit: ADR-006 (append-only, hash-chained)

Nieuw tenant-element → naam toevoegen aan `AUDIT_TENANT_ENTITEITEN`.
Platform-catalogus → `AUDIT_PLATFORM_ENTITEITEN`.
Relatie-koppelingen worden al via het `relatie`-spoor geauditeerd.
**Altijd meebewegen bij een nieuwe schema-slice** — niet vergeten.

---

## 8. Registratie-feiten naast de engine

Naast de ArchiMate-entiteiten en -relaties zijn er **registratie-feiten**:
feitelijke aantekeningen die geen ArchiMate-element zijn maar wél een eigen tabel
hebben. Ze raken de engine nooit.

| Registratie-feit | Tabel / locatie | Object | Semantiek |
|---|---|---|---|
| Roltoewijzing | `roltoewijzing` | component / contract | Partij vervult een beheerrol op dit object |
| Plateau-lidmaatschap bevestiging | kenmerk op aggregation-relatie (plateau-lid) | plateau-lid (component/contract) | Contractuele bevestiging incl. wie/wanneer/licenties |
| Categorie-klaarverklaring | nog te bouwen (ADR-027) | (component, categorie) | Expliciete menselijke aftekening per checklist-categorie |

---

## 9. Harde architectuurregels (samenvatting)

1. **Structureel boven conventioneel** — schema dwingt invarianten af. Geen app-side
   workaround als het schema de borging kan leveren.

2. **Facade-over-Relatie** — nieuw verband → bestaand relatietype via de `Relatie`-
   tabel, tenzij de uniciteit botst of het een registratie-feit is.

3. **Eigen tabel bij tegengestelde uniciteit** — als `UNIQUE(tenant,bron,doel,type)`
   de gewenste semantiek onmogelijk maakt → eigen tenant-tabel met eigen UNIQUE.

4. **Geen afgeleide relaties** — het systeem legt nooit relaties af (ADR-023 Besluit 8).
   Altijd expliciet door een gebruiker (of gevalideerde bulk-import) gelegd.

5. **Catalogus-scope is ononderhandelbaar** — checklistvraag is de ENIGE
   tenant-eigen catalogus. Alle andere catalogi zijn platform-breed.

6. **Engine-invariant** — zie §6. Score blijft enige lifecycle-driver.

7. **Subtype alleen bij type-eigen velden** — een "kaal" type (alleen naam +
   ArchiMate-typing) is geen subtype; het blijft een generieke component-rij.

8. **Generalisatie-discipline n≥2** — abstraheer een patroon pas als er twee
   concrete instanties zijn; bouw de tweede naast de eerste vóór je abstraheert.

9. **Intern/extern is een vlag, niet een tabel** — de grens is een kenmerk op de
   partij, geen apart datamodel.

10. **Migratie-ID ≤ 32 tekens** (`alembic_version` = `varchar(32)`) — harde
    conventie; korte, sprekende namen (`0032_adr024_eigenaar_org`).

11. **Full-graph endpoint** — de Landschapskaart levert de volledige tenant-graaf
    in één call. Geen ego-center server-side, geen paginering — de client filtert.
    Een server-side ego-subgraaf (`?center=&diepte=`) is een aparte, toekomstige slice.

---

## 10. Landschapskaart (ADR-025 — geland DC013, V013/V014)

### Endpoint
`GET /landschapskaart?diepte=1|2`
- Geeft de volledige tenant-graaf terug in één call (geen paginering — bewust
  afwijkend van het lijst-patroon; gedocumenteerd in de route).
- `diepte`-parameter is forward-compatibel, server-side no-op (client-side diepte
  op de ego-view).
- RBAC: `ARCHITECTUUR.LEZEN` (hergebruik, geen nieuwe entiteit).

### LandschapsNode
`id, naam, element_type, laag, archimate_element, lifecycle_status, soort, domein,
leverancier_naam, hosting_model, blokkades_open, plateau_naam, plateau_dispositie` +
(ADR-028) `componentrol, biv_beschikbaarheid, biv_integriteit, biv_vertrouwelijkheid`
(read-only afgeleid; None op context-nodes).

**Rol/BIV-filter (ADR-028, client-side):** rol (multi-select → alleen componenten mét die rol vallen
weg) + BIV per aspect (**drempel op de ordinale `volgorde`** uit `biv_niveaus`; een component zónder
waarde valt weg bij een drempel). **Filter-exemptie:** rol/BIV gelden UITSLUITEND voor nodes mét een
`componentrol` — context-nodes (partij/contract/gebruikersgroep, incl. org-partijen in appNodes) zijn
altijd exempt. **Randbehandeling:** `node[rol="externe_dataprovider"]` → gestippelde rand (géén nieuwe
vulkleur; vorm=type, vulkleur=lifecycle blijven) + legenda-entry.

### LandschapsEdge
`bron_id, doel_id, relatietype, label, ring, richting, protocol`

### Ringen
- applicaties: flow-relaties comp↔comp, label="koppeling"
- infrastructuur: assignment-relaties (host→comp), label="draait op"
- contracten: association-relaties (comp→contract), label="valt onder"
- beheerorganisatie: roltoewijzing-records, label=rol-naam
- *(uitgebreid na ADR-025: samenstelling, eigenaar (LI036), gebruikers, organisatiestructuur (ADR-024),
  en `gebruikt` (LI033b) — zie P4 hieronder voor het afgeleide-edge-patroon.)*

### P4 — Afgeleide read-only kaart-edges spiegelen een bestaande edge (ADR-040)

Een **afgeleide** kaart-relatie (bv. organisatie→applicatie "gebruikt") wordt gebouwd als **1:1 spiegel
van een bestaande edge** (bv. de eigenaar-edge organisatie→component): **read-only, géén schema, géén
nieuwe DB-relatie** — enkel een projectie van een bestaand feit. Vereist:
- een **dangling-guard**: emit de edge **alleen** als **beide** endpoints als knoop meekomen
  (`bron in partij_info and doel in comp_node`);
- een **scope-add**: het (nieuwe) endpoint moet als **node** de subgraaf in komen, anders is de edge
  dangling en breekt de render.

Dit is het patroon voor toekomstige afgeleide kaart-relaties. Bezit + gebruik levert bewust **twee
lijnen** (eigenaar + gebruikt) — niet onderdrukken.

### Weergaven (frontend)
> **Herzien in ADR-040:** de drie modi (Ego/Impact/Geheel, met o.a. een cose-impact-layout) zijn
> vervangen door een tweedeling **Overzicht** (centrumloos) / **Praatplaat** (radiaal, concentric); de
> impact-modus is afgeschaft. De concrete layout-keuzes staan in ADR-040; het herbruikbare patroon in
> P6a (likara-frontend).

### Engine-onaangeroerd borging (extra patroon)
`blokkades_open` via `table()`-construct (geen `Blokkade`-ORM-import); `lifecycle_status`
via lichtgewicht profiel-handle (geen `ComponentProfiel`-import). Beide geborgd via de
hasattr-test + bronscan-test.

---

## 11. Snelreferentie: welke slice, welke skills lezen?

| Soort slice | Primair | Aanvullend |
|---|---|---|
| Nieuwe element-entiteit | **dit bestand** + likara-db (subtype-recept) | likara-backend (service/route-patroon), likara-tests |
| Nieuw verband / relatie | **dit bestand** (facade vs. eigen tabel) + likara-db | likara-backend |
| Nieuwe catalogus | **dit bestand** §5 + likara-db (grants/seed) | likara-backend |
| Nieuwe partij-slice | **dit bestand** §4 + likara-db | likara-backend |
| Frontend-only / read-side | likara-frontend + likara-ux | dit bestand voor context |
| ADR schrijven / bijwerken | **dit bestand** (context) | senior-architect |
| Engine-naburige feature | **dit bestand** §6 (engine-invariant) | likara-tests (borging-patroon) |

## V015 — catalogus-beheer-principes (DC014)

- **"Geseed maar niet beheerbaar" is een schuldcategorie — breed valideren.** Voordat je één
  seed-only veld een beheerscherm geeft: **inventariseer ALLE geseede catalogi** en hun
  beheer-dekking (componentconfig/contractconfig/relatiekenmerk/vraagbetekenis/partijsoort/
  checklistvraag …), zodat je het hele gat in één keer ziet i.p.v. ad hoc te dweilen. (DC014:
  de meeste catalogi waren al volledig beheerbaar; het gat was gericht — `checklist_dragend`
  + twee volledig seed-only optiesets.)
- **Modeldefinitie (code-owned) ≠ beheercatalogus.** Niet alles wat geseed is hoort een
  beheerscherm te krijgen. `kenmerk_definitie` (welke kenmerken een relatietype mág dragen,
  hard gelezen door `relatie_service._valideer_kenmerken` + `_KENMERK_ENUMS` + de
  Landschapskaart/KoppelingSectie) is onderdeel van de relatiemodel-**definitie** (ADR-023) en
  bewust **code-eigendom**: inzien mag (read-only viewer), bewerken niet — een vrije edit breekt
  de relatie-semantiek (dode kenmerken, ontbrekende `richting`, enum/dimensie naar onbestaand).
  "Geen schuld" = alles wat een beheerder HOORT te kunnen, kan hij — **niet** "alles krijgt een
  knop". De catalogus-**inhoud** achter de verwijzingen (disposities, relatie-rollen) is wél
  beheerbaar (relatiekenmerk-beheer); alleen de **structuur** is code-vast.
- **Eén tenant nu — geen per-tenant-differentiatie** (zie likara-ux): catalogi zijn
  platform-breed/gedeeld, RBAC is één platform-brede matrix. RLS blijft technisch fundament,
  geen ontwerponderwerp tot er echt meerdere tenants zijn.

## Signalering — registratiegaten (ADR-035, V024; +BIV V028; +ADR-036 V030)

**Negen geïmplementeerde signaaltypen (3 kritiek / 6 aandacht)** op entiteiten in het domeinmodel, puur
read-only afgeleid in `registratiegaten_service.overzicht()` (gegroepeerd per ernst) en gelabeld in
`labels.js:SIGNAAL_LABELS`. De per-component `SignaleringBadge` toont via de optionele `signalen`-prop
een sprekende tooltip. **De telling volgt de code (`overzicht()` + `SIGNAAL_LABELS`), niet deze tabel —
verifieer bij twijfel daar.**

| Signaal (code) | Bron | Ernst |
|---|---|---|
| `component_zonder_eigenaar` | `eigenaar_organisatie_id IS NULL` | 🔴 Kritiek |
| `component_zonder_verantwoordelijke` | geen `roltoewijzing` op component | 🔴 Kritiek |
| `biv_classificatie_onvolledig` (ADR-028) | ≥1 van `biv_{beschikbaarheid,integriteit,vertrouwelijkheid}` IS NULL | 🔴 Kritiek |
| `component_zonder_gebruikersgroep` | geen serving-relatie van gg naar component | 🟡 Aandacht |
| `component_geisoleerd` | geen flow-relaties | 🟡 Aandacht |
| `contract_zonder_component` | geen association van component naar contract | 🟡 Aandacht |
| `gebruiksfeit_zonder_verfijning` (ADR-036) | grof gebruiksfeit zónder afdeling-verfijning eronder | 🟡 Aandacht |
| `object_zonder_roltoewijzing` | geen `roltoewijzing`-rij voor dit element | 🟡 Aandacht |

**Gepland / nog niet geïmplementeerd** (staan bewust NIET in `overzicht()`): _Registratie onvolledig_
(score onder tenant-drempel — ADR-035 slice 3, open); _Contract zonder leverancier_ (moot: `leverancier_id`
is verplicht); _Blokkade zonder eigenaar_ (structureel onmogelijk zonder schema-/semantiekherziening).

Engine-invariant: Signalering raakt nooit `component_profiel`, `checklistscore`,
`blokkade` (schrijven) of `lifecycle_status`. Geen engine-poort.

## Contract-band-dekking (ADR-030, V024)

Tabel: contract_band_dekking (tenant_id, contract_id, component_id, dekking_sleutels TEXT[])
PK: (tenant_id, contract_id, component_id) — één rij per component↔contract-koppeling.
Catalogus: contractconfig_optie (dimensie=dekking) — hergebruikt.
Weergave: contract_breed (uit ContractDekking-tag-tabel) + per_band (array) naast elkaar.
toon_per_band = per_band IS NOT NULL AND per_band != contract_breed (set-vergelijking op sleutels).
FORCE RLS, FK→element CASCADE.
