---
name: complidata-domeinmodel
description: >
  Canonieke "kaart" van het CompliData-domeinmodel. Lees dit vóór elke slice
  die een element, relatie, catalogus, partij, of registratie-feit raakt.
  Dekt: element-familie + ArchiMate-typings, relatiemodel (8 typen), migratielaag
  (plateau/gap/work_package/deliverable), partijenregister (ADR-024, 4 aarden),
  catalogus-families (scope platform vs. tenant), engine-invariant, RBAC/audit-
  ankerpunten, en harde architectuurregels. De HOE (implementatiepatronen) staat
  in complidata-db en complidata-backend; dit bestand beschrijft het WAT.
stack: PostgreSQL 16, SQLAlchemy asyncio, FastAPI — ADR-021/023/024/025/026
bijgewerkt: V015
---

# CompliData Domeinmodel — Kaart

Dit is de canonieke referentie voor het domeinmodel: **wat** bestaat er, hoe hangt
het samen, en welke regels zijn onschendbaar. De **HOE** (implementatiepatronen,
RLS-boilerplate, keyset-cursor, seed-patroon) staat in complidata-db en
complidata-backend. Gebruik dit bestand als eerste oriëntatie bij elke nieuwe slice.

---

## 1. Element-familie

Eén `element`-identiteitsruimte: `UNIQUE(tenant_id, id)`, FORCE RLS.
Alle entiteiten in de onderstaande tabel zijn **element-subtypes**: ze hebben een
eigen tabel met een composiet-PK/FK `(tenant_id, id) → element(tenant_id, id)`
ON DELETE CASCADE. (Subtype-bouwrecept: zie complidata-db V009/V010-patronen.)

### Volledige element-typetabel (ELEMENT_ARCHIMATE_TYPING, V013)

| `element_type` | Eigen tabel | `archimate_element` | `laag` | `aspect` | Noot |
|---|---|---|---|---|---|
| `component` | `component` | via componenttype-catalogus | via catalogus | via catalogus | Supertype voor `applicatie` |
| `applicatie` | `applicatie` | (idem component) | (idem) | (idem) | Subtype van `component` (shared-PK) |
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

### Wanneer een nieuw element-subtype?

Alleen bij **type-eigen velden**. Een "kaal" type (alleen naam + ArchiMate-typing)
is geen subtype — het blijft een generieke `component`-rij met een componenttype
uit de catalogus.

---

## 2. Relatiemodel

Eén `relatie`-tabel: gericht `bron_id → doel_id`, composiet-FK's
`(tenant_id, bron|doel) → element(tenant_id, id)`, `CHECK bron ≠ doel`,
`UNIQUE(tenant_id, bron_id, doel_id, relatietype)`.

### De acht ArchiMate-relatietypes

| Type | Richting bron → doel | Primaire toepassing in CompliData |
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

### Type-validatie bron/doel (per facade)

De service valideert `element_type` van bron en doel per relatietype:
- `assignment` (draait_op): bron ∈ host-typen, doel ∈ component/applicatie
- `realization`: realiseerder ∈ {work_package, deliverable}, gerealiseerde ∈ {deliverable, plateau}
- `aggregation` (plateau-lid): bron = plateau, doel ∈ {component, contract}
- Ongeldig type → 422 `ONGELDIGE_BRON_TYPE` / `ONGELDIG_DOEL_TYPE`

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
- `email` (255), `telefoon` (40), `mobiel` (40), `contactpersoon` (255):
  platform-breed, gedeeld over alle aarden.
- `functietitel` (150): NIEUW, nullable — uitsluitend voor aard=persoon.
  Service dwingt af: andere aarden → 422 FUNCTIETITEL_ALLEEN_PERSOON.

### Contract → leverancier (huidig na DC013)
- FK-target: `(tenant_id, leverancier_id) → element(tenant_id, id)`, ON DELETE RESTRICT.
- Toegestane aarden: organisatie / organisatie_eenheid / externe_partij
- Persoon als contractpartij: geweigerd (422 ONGELDIGE_PARTIJ)
- Implementatie: TOEGESTANE_LEVERANCIER_AARDEN constante in contract_service
- Term "leverancier" blijft in het contract-domein (optie A, blast-radius-minimalisatie).

### Organisatie als verwijzing elders (B6, migraties 0031/0032)
- `gebruikersgroep.organisatie_id`: optionele FK → element (aard=organisatie),
  ON DELETE SET NULL (kolom-specifiek, PostgreSQL 15+).
- `component.eigenaar_organisatie_id`: idem.
- Beide tonen de gejoinde `Partij.naam` in lijsten/details (naam-in-read via alias).

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
| Checklistvraag | `checklistvraag`, `checklistvraag_optie` | Ja | Per tenant (kopie bij onboarding) | Beoordelingsvragen per componenttype |

### Grants (platform-catalogi, alle gelijk)
`cd_app` = SELECT only (validatie).
`cd_platform` = SELECT / INSERT / UPDATE — **geen DELETE** (geen endpoint, geen grant).

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
leverancier_naam, hosting_model, blokkades_open, plateau_naam, plateau_dispositie`

### LandschapsEdge
`bron_id, doel_id, relatietype, label, ring, richting, protocol`

### Vier ringen
- applicaties: flow-relaties comp↔comp, label="koppeling"
- infrastructuur: assignment-relaties (host→comp), label="draait op"
- contracten: association-relaties (comp→contract), label="valt onder"
- beheerorganisatie: roltoewijzing-records, label=rol-naam

### Drie modi (frontend, Cytoscape.js)
- Ego-view: concentric layout, centrum + ringen, klik=hercentreren
- Impact-view: cose layout, blauw=in-set/oranje=raakvlak, grensoverschrijdende koppelingen geteld
- Geheel model: alle applicaties auto-geladen, opbouw/afpel-modus

### Engine-onaangeroerd borging (extra patroon)
`blokkades_open` via `table()`-construct (geen `Blokkade`-ORM-import); `lifecycle_status`
via lichtgewicht profiel-handle (geen `ComponentProfiel`-import). Beide geborgd via de
hasattr-test + bronscan-test.

---

## 11. Snelreferentie: welke slice, welke skills lezen?

| Soort slice | Primair | Aanvullend |
|---|---|---|
| Nieuwe element-entiteit | **dit bestand** + complidata-db (subtype-recept) | complidata-backend (service/route-patroon), complidata-tests |
| Nieuw verband / relatie | **dit bestand** (facade vs. eigen tabel) + complidata-db | complidata-backend |
| Nieuwe catalogus | **dit bestand** §5 + complidata-db (grants/seed) | complidata-backend |
| Nieuwe partij-slice | **dit bestand** §4 + complidata-db | complidata-backend |
| Frontend-only / read-side | complidata-frontend + complidata-ux | dit bestand voor context |
| ADR schrijven / bijwerken | **dit bestand** (context) | senior-architect |
| Engine-naburige feature | **dit bestand** §6 (engine-invariant) | complidata-tests (borging-patroon) |

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
- **Eén tenant nu — geen per-tenant-differentiatie** (zie complidata-ux): catalogi zijn
  platform-breed/gedeeld, RBAC is één platform-brede matrix. RLS blijft technisch fundament,
  geen ontwerponderwerp tot er echt meerdere tenants zijn.
