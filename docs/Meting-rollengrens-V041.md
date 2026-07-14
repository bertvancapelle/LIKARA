# Meting — de rollengrens tussen beheerder en medewerker (READ-ONLY)

**Build:** V041 (naast de ongecommitte gate-2a-landing) · **Datum:** 2026-07-14 · **Modus:** READ-ONLY
**Bron:** `backend/app/core/rbac.py`, `backend/app/core/platform_rbac.py`, alle `modules/bwb_ontvlechting/backend/routes/*.py`, de services, `models/models.py`, de migraties + de dev-DB.

> Elke uitspraak draagt een vindplaats of een DB-telling. Geen advies — alleen de feiten waarop Bert beslist.

---

## Samenvatting (gebruikerstaal)

**De code formuleert Berts grens al — maar hij spreekt hem nergens uit en past hem half toe.**

De grens leeft niet in de rechtenmatrix (die geeft "verwijderen = beheerder" voor bijna alles), maar in
**welke handeling elke verwijder-knop bewaakt**. Voor vier registratie-feiten kiest de code bewust
`WIJZIGEN` in plaats van `VERWIJDEREN` — waarmee de medewerker ze mag terugnemen. De code zegt het zelfs
letterlijk (`routes/procesvervulling.py:5-7`):

> *"het opheffen van een registratie-feit is registratiebeheer (medewerker-werk), geen verwijdering van een inhouds-object."*

Dat **ís** Berts regel. Maar hij is toegepast op 4 van de ~10 registratie-feiten. De overige — waaronder
**de gate-2a-koppeling zelf** (`functievervulling`) — staan op `VERWIJDEREN` (beheerder). Precies de
inconsistentie die de consultant tegenkwam: hij mag koppelen (medewerker), maar niet ontkoppelen (beheerder),
terwijl de spiegel-registratie procesvervulling wél door de medewerker verbroken mag worden.

**Botst de grens ergens gevaarlijk?** Nee — en dat is de geruststellende bevinding. De verwijdering die écht
andermans werk vernietigt (via cascade) zit uitsluitend bij **landschapsobjecten** (type A) — met **`component`
als gevaarlijkste: één klik wist scores, blokkades, koppelingen, roltoewijzingen én gebruiksfeiten, zónder
enige weigering**. Berts grens laat die objecten juist bij de beheerder. De registratie-feiten die zouden
verschuiven (type B) nemen bij een delete **niets** uit het landschap mee — hun hele punt is dat er niets
verdwijnt. De enige nuance: `checklistscore`-delete sleept zijn 1-op-1 afgeleide blokkade mee (geen
onafhankelijk werk), en `organisatiegebruik` is al beschermd met een 409-weigering.

**Laat de grens de tenant-beheerder leeg achter?** Nee. De beheerder houdt: het vernietigen van álle
landschapsobjecten, gebruikersbeheer, tenant-instellingen, auditlog-inzage en het inlezen van het
referentiemodel.

---

## 2a. De feitelijke matrix (uit de code, niet het patroon)

### Tenant-domein (`rbac.py`, `PERMISSIES`)

**`_INHOUD` = Viewer L · Medewerker LAW · Beheerder LAWV · Auditor L.** Entiteiten op dit patroon
(`rbac.py:135-212`): `DATATYPE, GEBRUIKERSGROEP, KOPPELING, CHECKLISTSCORE, BLOKKADE, PARTIJ, CONTRACT,
ORGANISATIEGEBRUIK, COMPONENT_CONTRACT, COMPONENT, COMPONENT_STRUCTUUR, RELATIE, PLATEAU, WORK_PACKAGE,
DELIVERABLE, GAP, PROCES, PROCESVERVULLING, FUNCTIEVERVULLING, BEDRIJFSFUNCTIE, KLAARVERKLARING, CHECKLISTVRAAG`.

**Afwijkingen van `_INHOUD`** (met reden uit de code):

| Entiteit | Matrix | Vindplaats | Reden (code) |
|---|---|---|---|
| `REFERENTIEMODEL` | Medewerker **L** (geen A/W/V); Beheerder LAWV | `rbac.py:170-175` | inlezen herschrijft het hele functie-landschap → beheerder-only |
| `ARCHITECTUUR` | alle rollen **L** | `rbac.py:178` | read-only laagprojectie (F-2) |
| `IMPACT_VIEW` | Medewerker **LAWV** | `rbac.py:183` | eigen-beheer: je eigen view weggooien is geen privilege |
| `GEBRUIKER_VOORKEUR` | alle rollen **LAWV** | `rbac.py:186` | strikt persoonlijk, nooit gedeeld |
| `AUDITLOG` | alleen Beheerder+Auditor **L** | `rbac.py:193-198` | niemand muteert |
| `GEBRUIKERSBEHEER` | alleen Beheerder **LAWV** | `rbac.py:200-205` | beheer |
| `TENANT_INSTELLINGEN` | alleen Beheerder **LAWV** | `rbac.py:206-211` | beheer |

⚠ **`KOPPELING` (`rbac.py` enum) wordt door geen enkele route gebruikt** (grep `Entiteit.KOPPELING` in routes: 0 treffers) — dode entiteit.

### Platform-domein (`platform_rbac.py`, `PLATFORM_PERMISSIES`)
Alle **inrichting/catalogus**-entiteiten (`CHECKLISTCONFIG, CONTRACTCONFIG, COMPONENTCONFIG, RELATIEKENMERKCONFIG,
VRAAGBETEKENISCONFIG, PARTIJSOORTCONFIG, COMPONENTROLCONFIG, BIVSCHAALCONFIG, APPLICATIEFUNCTIECONFIG,
REFERENTIEMODELCONFIG`): **platformbeheerder LAW (géén V), operator L** — `platform_rbac.py:69-117`.
`TENANT` = beheerder LAWV; `PLATFORMINSTELLINGEN` = beheerder LAWV.

> **Structureel signaal:** het inrichtingsdomein kent **geen hard-delete** — een catalogus-optie wordt
> soft-gedeactiveerd (W), nooit vernietigd (`platform_rbac.py:55`). "Verwijderen" als destructieve daad bestaat
> uitsluitend in het tenant-domein.

### De echte plek van de grens: de verwijder-guard per route
De matrix-`V` staat via `_INHOUD` overal op beheerder. Maar de **route** kiest welke actie een DELETE bewaakt.
Alle 26 DELETE-routes (gemeten):

**Op `VERWIJDEREN` (beheerder):** component `component.py:203` · contract `contract.py:145` · partij `partij.py:128`
· bedrijfsfunctie (hele functie) `bedrijfsfunctie.py:130` · proces `proces.py:111` · gebruikersgroep
`gebruikersgroep.py:121` · datatype `datatype.py:107` · relatie `relatie.py:94` · plateau (+lid) `plateau.py:83,125`
· work_package `work_package.py:88` · deliverable (+leden) `deliverable.py:102,124,145` · gap (+lid) `gap.py:81,112`
· checklistscore `checklistscore.py:113` · component_contract `component_contract.py:47` · organisatiegebruik
`organisatiegebruik.py:74` · **functievervulling `functievervulling.py:52` (gate 2a)** · impact_view `impact_view.py:63`
· gebruiker_voorkeur `voorkeur.py:46`.

**Op `WIJZIGEN` (óók medewerker) — de vier uitzonderingen:** procesvervulling verbreken `procesvervulling.py:86`
· roltoewijzing weghalen `roltoewijzing.py:69` (→ `PARTIJ.WIJZIGEN`) · bedrijfsfunctie-plaatsing weghalen
`bedrijfsfunctie.py:106` · contract band-dekking wissen `contract.py:182`.

---

## 2b. Categorisatie langs Berts as

| Entiteit | Bak | Grond |
|---|---|---|
| component, contract, partij, bedrijfsfunctie, proces, gebruikersgroep, datatype, plateau, work_package, deliverable, gap | **Landschapsobject** | een `element`-subtype dat bestaat in het landschap |
| procesvervulling, functievervulling, roltoewijzing, organisatiegebruik, component_contract, checklistscore, klaarverklaring, bedrijfsfunctie-plaatsing, contract band-dekking, plateau/gap/deliverable-lid | **Registratie-feit** | een *uitspraak óver* dingen |
| (platform) alle *config-catalogi, checklistvraag (tenant) | **Inrichting** | bepaalt hoe LIKARA wérkt |

**Twijfelgevallen (waar Berts grens getoetst wordt):**
1. **`relatie`** — een relatie *is* een uitspraak (type B: delete neemt één edge terug, geen collateral —
   `relatie_service.py:213-215`), maar draagt óók structuur (aggregation = de functieboom/plateau-leden). Staat op
   `VERWIJDEREN`. Registratie-feit dat als objectdelete is bekabeld.
2. **`checklistscore`** — een score is een registratie-feit, maar delete cascadet zijn 1-op-1 **blokkade** mee
   (`checklistscore_service.py:417-421`; `models.py:1052`). Feit + afgeleide, geen onafhankelijk werk.
3. **`impact_view`** — een opgeslagen view is een object (type A voor het object), maar de "leden" zijn
   verwijzingen; er verdwijnt geen landschap. Al op medewerker (`_EIGEN_BEHEER`).
4. **`checklistvraag` (tenant)** — inrichting-áchtig (de vragen die beoordelingen sturen), maar tenant-eigendom
   (ADR-022, `rbac.py:187-191`); geen hard-delete (soft-deactivate via `WIJZIGEN`). Zie §2e.
5. **plateau/gap/deliverable-lid** — lidmaatschap is een uitspraak (type B), maar staat op `VERWIJDEREN` (beheerder),
   ánders dan de plaatsing/procesvervulling die op `WIJZIGEN` staan.

---

## 2c. Wat vernietigt "verwijderen" feitelijk? (A = object weg / B = uitspraak terug)

Mechaniek: elk landschapsobject is een subtype van `element` (composiet-FK `→ element ON DELETE CASCADE`); de
service verwijdert de **`element`-rij**, wat **alle feiten die naar dat element wijzen** meesleept. DB-gemeten:
tabellen die met `ON DELETE CASCADE` naar `element` wijzen zijn o.a. `relatie, organisatiegebruik, procesvervulling,
functievervulling, roltoewijzing, component_klaarverklaring, impact_view_component, contract_band_dekking`.

| Entiteit | Type | Wat verdwijnt mee | Weigering | Vindplaats |
|---|---|---|---|---|
| **component** | **A** | profiel→scores→blokkades; álle relaties; proces-/**functievervullingen**; roltoewijzingen; klaarverklaringen; organisatiegebruik; band-dekking; view-lidmaatschap | **NEE** ⚠ | `component_service.py:762-772` |
| contract | A | dekking/kostenmodel/band-dekking | JA 409 `IN_GEBRUIK` | `contract_service.py:426-441` |
| partij | A | roltoewijzingen; organisatiegebruik; NULL-t eigenaar/verantwoordelijke | JA 409 `IN_GEBRUIK` | `partij_service.py:468-487` |
| bedrijfsfunctie | A | functievervullingen; plaatsings-relaties | JA 422+409 | `bedrijfsfunctie_service.py:291-324` |
| proces | A | procesvervullingen | JA 409 | `proces_service.py:163-181` |
| gebruikersgroep / datatype / plateau / deliverable / gap | A | eigen relaties/leden | NEE | resp. service `verwijder` |
| work_package | A | — | JA 409 `HEEFT_SUBPAKKETTEN` | `work_package_service.py:144-162` |
| relatie | A/B | niets (is zelf de uitspraak) | NEE | `relatie_service.py:213-215` |
| **procesvervulling** | **B** | niets | NEE | `procesvervulling_service.py:156-159` |
| **functievervulling** | **B** | niets (grof wordt weer leesbaar) | NEE | `functievervulling_service.py:198-205` |
| **roltoewijzing** | **B** | niets | NEE | `roltoewijzing_service.py:82-94` |
| **organisatiegebruik** | **B** | niets | JA 409 `GEBRUIK_HEEFT_VERFIJNING` (RESTRICT) | `organisatiegebruik_service.py:120-152` |
| component_contract | B | niets (is een `association`-relatie) | NEE | `component_contract_service.py:99-102` |
| checklistscore | B | 1-op-1 afgeleide blokkade | NEE | `checklistscore_service.py:417-421` |
| klaarverklaring | B | — (géén delete; alleen status) | n.v.t. | `component_klaarverklaring_service.py:102` |
| bedrijfsfunctie-plaatsing / band-dekking / plateau-gap-lid | B | niets | NEE | resp. sub-resource `verwijder` |

⚠ **`component`-delete is de enige type-A-vernietiging zonder énige weigering én met de breedste collateral.** Er
bestaat een read-only `impact_analyse` (`component_service.py:841`) die telt wie erop steunt, maar `verwijder`
roept die **niet** aan — de delete waarschuwt niets.

---

## 2d. De uitzonderingen — de code zegt Berts regel al

De vier `WIJZIGEN`-guarded deletes, met vindplaats + reden:

1. **procesvervulling verbreken** — `procesvervulling.py:86`; de docstring (`:5-7`) benoemt het letterlijk:
   *"het opheffen van een registratie-feit is registratiebeheer (medewerker-werk), geen verwijdering van een
   inhouds-object."*
2. **roltoewijzing weghalen** — `roltoewijzing.py:69` (guardt op `PARTIJ.WIJZIGEN`; de koppelregel lift op de partij).
3. **bedrijfsfunctie-plaatsing weghalen** — `bedrijfsfunctie.py:106` (een plaatsing toevoegen/weghalen = registratie
   op de boom, niet de functie vernietigen).
4. **contract band-dekking wissen** — `contract.py:182` (terug naar de contract-brede dekking).

**Zijn dit precies de "registratie-feiten" uit §2b? Grotendeels JA — en dát is de kern.** Deze vier zijn allemaal
type-B uitspraken. De code formuleert Berts regel dus al, zonder hem ooit uitgesproken te hebben. **Waar hij afwijkt:**
de overige type-B feiten — **`functievervulling` (gate 2a), `organisatiegebruik`, `component_contract`,
`checklistscore`, `relatie`, plateau/gap/deliverable-lid** — staan op `VERWIJDEREN` (beheerder). De regel is dus
**half** toegepast; de gate-2a-koppeling is de zichtbaarste breuk (spiegel van procesvervulling, maar tegengesteld
gegate).

---

## 2e. Zit er inrichting in het tenant-domein?

- **Kandidaat: `checklistvraag` (tenant).** Naar aard inrichting (de vragen die de beoordeling sturen), maar
  bewust tenant-eigendom (ADR-022, `rbac.py:187-191`), op `_INHOUD` (medewerker mag aanmaken/wijzigen). Er is
  **geen hard-delete**; "verwijderen" = soft-deactivatie via `WIJZIGEN` — precies zoals het platform-inrichtingsdomein
  werkt. Het gedraagt zich dus al als inrichting, alleen tenant-scoped.
- **Andersom (inrichting-domein dat eigenlijk landschap is): niet gevonden** — alle platform-entiteiten zijn
  catalogi/instellingen, geen landschapsinhoud.
- **Gevolg voor Berts grens:** de tenant-beheerder blijft **niet leeg**. Onder Berts as houdt hij: het vernietigen
  van álle landschapsobjecten (§2c type A), plus `GEBRUIKERSBEHEER`, `TENANT_INSTELLINGEN`, `AUDITLOG`-inzage en
  `REFERENTIEMODEL` inlezen (alle al beheerder-only, `rbac.py:170-211`).

---

## 2f. Wat zou Berts grens concreet verschuiven?

De grens verschuift **op route-niveau** (guard `VERWIJDEREN`→`WIJZIGEN`), **niet in de matrix** (die blijft `_INHOUD`
— want de vier bestaande uitzonderingen doen het ook zo). Kandidaten die van beheerder naar medewerker zouden gaan
(type-B feiten die nu op `VERWIJDEREN` staan):

| Entiteit | Route nu | Zou worden | Gevaar bij de delete? |
|---|---|---|---|
| **functievervulling** (gate 2a) | `VERWIJDEREN` `functievervulling.py:52` | `WIJZIGEN` | Nee — niets verdwijnt (grof wordt weer leesbaar) |
| organisatiegebruik | `VERWIJDEREN` `organisatiegebruik.py:74` | `WIJZIGEN` | Nee — al beschermd met 409 bij verfijning |
| component_contract | `VERWIJDEREN` `component_contract.py:47` | `WIJZIGEN` | Nee — is een `association`-relatie |
| checklistscore | `VERWIJDEREN` `checklistscore.py:113` | `WIJZIGEN` | **Grens** — sleept zijn afgeleide blokkade mee (geen onafhankelijk werk, maar wél andermans beoordeling) |
| plateau/gap/deliverable-lid | `VERWIJDEREN` | `WIJZIGEN` | Nee — lidmaatschap terug, lid blijft |
| relatie (generiek) | `VERWIJDEREN` `relatie.py:94` | `WIJZIGEN` | **Grens** — breed: dekt ook structuurrelaties; delete neemt wel alleen die ene edge |

- **Aantal dat verschuift:** ~6 entiteiten/routes (afhankelijk van hoe breed `relatie` en de leden-deletes worden meegenomen).
- **Frontend-gatings die meebewegen** (`magVerwijderen`→`magBewerken`): `BedrijfsfunctieLijst.vue:1018` (gate 2a
  weghalen), `OrganisatiegebruikSectie.vue:216`, `ContractSectie.vue:329`, `GapDetailView.vue:268`,
  `PlateauDetailView.vue:267`, `DeliverableDetailView.vue:223/246`, `KoppelingSectie.vue:383/412`,
  `StructuurSectie.vue:196/217` (de laatste twee = generieke relatie).
- **Tests die meebewegen:** de RBAC-**matrix**test (`test_rbac.py::test_matrix_volledig`) **niet** (matrix onveranderd).
  Wél elke route-/integratietest die assert dat een delete beheerder vereist (per-endpoint 403-verwachtingen).
- **Gevaarlijke verschuiving?** **Geen die andermans werk vaporiseert.** De echte cascade-vernietiging (component,
  contract, partij, …) is type A en blijft bij de beheerder. De twee grensgevallen (`checklistscore`,
  `relatie`) verdienen een expliciete keuze: de eerste neemt een afgeleide blokkade mee, de tweede is een brede
  categorie die ook structuur draagt.

---

## 2g. Frontend-gating vs. backend

**Geen enkel stil functioneel gat.** De frontend gate't consequent:
`magVerwijderen = hasRole('beheerder')` op affordances waarvan de backend op `VERWIJDEREN` guardt;
`magBewerken/mag/magKoppelen = hasRole('medewerker','beheerder')` op affordances die op `WIJZIGEN` guarden
(`auth.js:77-79` = OR-check). De vier `WIJZIGEN`-gevallen zijn óók frontend-zijdig op medewerker gezet
(procesvervulling `ComponentProcessenSectie.vue:242`; roltoewijzing `VerantwoordelijkheidSectie.vue:169`;
plaatsing-weghalen `BedrijfsfunctieLijst.vue:1096`; band-dekking `ContractSectie.vue:306`).

**De enige asymmetrie (geen gat, wél inconsistent met het feit-patroon):** in gate 2a staat "Koppel systeem" op
**medewerker** (`BedrijfsfunctieLijst.vue:1061`) maar "weghalen" op **beheerder** (`:1018`) — backend-consistent
(`FUNCTIEVERVULLING.VERWIJDEREN`), maar tegengesteld aan de spiegel procesvervulling (waar verbreken = medewerker).
Dit is exact de wrijving die Bert in de browser voelde.

---

## Open beslispunten (genummerd, gebruikerstaal — niet beantwoord)

1. **Verschuift het terugnemen van een koppeling (gate 2a) naar de medewerker?** — dan is registreren geen val meer;
   opties: A) ja, gelijk aan procesvervulling (guard `WIJZIGEN`); B) nee, beheerder houdt het (huidige stand).
2. **Trekken we de regel door naar álle registratie-feiten in één keer** (functievervulling, organisatiegebruik,
   component_contract, plateau/gap/deliverable-lid), of feit-voor-feit? — A) alle tegelijk (één consistente grens);
   B) alleen gate 2a nu, rest later.
3. **Blijft `checklistscore` een uitzondering?** — de delete sleept een afgeleide blokkade mee; opties: A) toch naar
   medewerker (het is de eigen afgeleide); B) bij beheerder houden omdat het andermans beoordeling raakt.
4. **Gaat `relatie` mee?** — het is een uitspraak, maar de categorie dekt óók structuurrelaties; opties: A) hele
   `relatie` naar medewerker; B) alleen de registratie-achtige subtypes, structuur bij beheerder; C) ongemoeid laten.
5. **Krijgt `component`-delete een waarschuwing vóór de daad?** — vandaag wist één klik scores/blokkades/koppelingen
   zonder telling; opties: A) de bestaande `impact_analyse` als bevestig-stap inbouwen; B) laten zoals het is
   (buiten deze rollenvraag).
6. **Erkennen we `checklistvraag` (tenant) formeel als inrichting?** — het gedraagt zich al zo (soft-deactivate);
   opties: A) expliciet als inrichting benoemen (blijft tenant-beheer); B) ongemoeid als tenant-inhoud.

**STOP — read-only meting afgerond. `git status` toont één nieuw bestand bovenop de gate-2a-werktree.**
