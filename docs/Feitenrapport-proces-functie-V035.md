# Feitenrapport — proces/functie-inzicht (READONLY-verkenning, V035)

> Read-only verkenning n.a.v. `START: READONLY_proces_functie_inzicht_verkenning`,
> voorbereiding op een concept-ADR. Niets gewijzigd, niets gebouwd. Alle bevindingen
> geverifieerd tegen de code op commit `9128a24`. Opties staan naast elkaar zonder keuze;
> ontwerpbesluiten liggen bij PNA + Bert.

## Samenvatting (TL;DR)

- **Het subtype-recept past**, maar met een nuance: het element-supertype draagt géén
  naam (Besluit 9) → een nieuw element-type dat een naam moet dragen krijgt **altijd**
  een eigen subtabel; de "kaal type = geen subtype"-regel geldt binnen de
  componenttype-catalogus, niet voor nieuwe element-typen. Vergelijkbare elementen
  (plateau/deliverable) dragen alleen `naam` + `toelichting`.
- **`business_process`/`business_function` staan NIET in de gesloten
  `TOEGESTANE_ELEMENTEN`-whitelist** (ADR-026 Besluit 1) — uitbreiding van die
  code-constante is een expliciet ADR-punt. `behavior` als aspect is wél al toegestaan;
  work_package is nu het enige behavior-element (gemarkeerde OK-3-afwijking) en
  proces/functie zouden nr. 2 en 3 worden.
- Voor **"functie onder proces, exact één laag"** bestaan drie feitelijke vormen: de
  work_package-self-FK (onbegrensde diepte, één-laag alleen service-side), de
  relatie-facade (aggregation/composition; de facade valideert bron/doel-typen NIET),
  én een derde die het besluit letterlijk schema-af dwingt: twee aparte element-typen
  met een FK-kolom functie→proces (Gap-2-ariteit-precedent).
- Voor **"component vervult een rol in proces"** is `roltoewijzing` het 1-op-1
  herbruikbare precedent zodra meerdere rollen per (component, proces) als losse
  regels gewenst zijn; de relatie-facade kan het alleen als één rij per
  (component, proces, relatietype) met de rol als kenmerk.
- **Impact-omhoog-rollen** past als pure read-only afleiding op de bestaande
  BFS-/borging-patronen; door de één-laag-hiërarchie is de "roll-up" één join-niveau,
  geen recursie.
- **Twee discrepanties** met aannames/skills gevonden (beheerrol is een dimensie, geen
  eigen tabel; IMPACT_RINGEN op de kaart is afgeschaft) — zie de discrepantie-log.

---

## 1. Element-familie: past proces/functie in het subtype-recept?

### Type-eigen velden — wat vergelijkbare elementen dragen

| Element | Type-eigen velden | Vindplaats |
|---|---|---|
| `plateau` | `naam` (verplicht) + `toelichting` | `models.py:503-517` |
| `deliverable` | `naam` + `toelichting` | `models.py:526-540` |
| `work_package` | `naam` + `toelichting` + `bovenliggend_id` (composiet self-FK) | `models.py:551-581` |
| `gap` | `naam` + `toelichting` + `baseline_plateau_id`/`doel_plateau_id` (2 verplichte composiet-FK's — "vaste ariteit hard in het schema") | `models.py:589-603` |

**Nuance op de subtype-regel.** "Alleen een eigen tabel bij type-eigen velden" is de
regel voor **componenttypen** (catalogus-rij op de generieke `component`). Voor een
**nieuw element-type** geldt: het `element`-supertype draagt géén naam (Besluit 9,
geciteerd in de Plateau-docstring `models.py:508`) → `naam` ís al een type-eigen veld,
dus een proces-/functie-element krijgt hoe dan ook een eigen subtabel volgens het vaste
recept (shared-PK composiet-FK `(tenant_id, id) → element` ON DELETE CASCADE, FORCE
RLS, `REVOKE/GRANT lk_app` — het bouwrecept uit likara-db V009/V010). Minimaal te
verwachten velden: `naam` + `toelichting` (plateau-spiegel); voor functie evt. een
ouder-verwijzing (zie §2, vorm A2).

### ArchiMate-typing en de OK-3-lijn

- **Whitelist-feit:** `TOEGESTANE_ELEMENTEN` (`services/archimate_typing.py:28-38`)
  bevat op de business-laag alléén `business_actor`, `business_role`,
  `business_service`, `contract`, `business_object`. **`business_process` en
  `business_function` ontbreken.** Het is een bewust "gesloten, gedeelde, platform-brede
  whitelist" (ADR-026 Besluit 1; comment `:23-27`); een element erbuiten ⇒ 422.
  Uitbreiding = wijziging van deze code-constante → ADR-waardig punt.
- `laag='business'` ∈ `TOEGESTANE_LAGEN` en `aspect='behavior'` ∈ `TOEGESTANE_ASPECTEN`
  (`:20-21`) — geen blokkade daar.
- **OK-3/behavior:** het comment (`:18-19`) zegt "`behavior` is in het huidige
  gecureerde model nog leeg"; work_package doorbrak dat als **gemarkeerde afwijking**
  (`:54-55, :58`) en `test_archimate_fase_d.py:68-69` asserteert
  `typing_voor(work_package)["aspect"] == "behavior"` expliciet als "bewuste afwijking
  op OK-3". Proces (ArchiMate Business Process) en functie (Business Function) zijn
  beide gedragselementen → zouden behavior-elementen nr. 2 en 3 zijn; de OK-3-tekst en
  het comment zouden dan feitelijk achterhaald raken (ADR-onderhoudspunt).
- **Vaste typing vs. catalogus:** element-typen krijgen hun typing als code-constante in
  `ELEMENT_ARCHIMATE_TYPING` (`archimate_typing.py:42-60`), "architectonisch vast — niet
  per tenant aan te passen" (`:3-6`). Voor de hand liggende entries:
  proces → `{business_process, business, behavior}`, functie →
  `{business_function, business, behavior}`.

### Constanten en tests die meebewegen

- **`ElementType`-enum** (`models.py:177-191`) kent `proces`/`functie` niet → PostgreSQL
  `ALTER TYPE element_type_enum ADD VALUE` nodig. **Precedent:** migratie
  `0026_adr024_elementtype_partij.py` — de ADD VALUE als **aparte, voorafgaande
  migratie** vóór de subtype-migratie (0027), met `ADD VALUE IF NOT EXISTS`.
- **`ELEMENT_TYPEN_NOG_NIET_GEREALISEERD`** (`archimate_typing.py:66`) is momenteel
  `frozenset()` mét expliciete parkeerfunctie: "Een nieuw, nog-niet-gerealiseerd
  element-type wordt hier geparkeerd zodat de dekkingstest het niet stil doorheen laat
  vallen." Dit past exact bij "**begin grof: eerst proces; functie later**" — als de
  enum beide waarden in één keer krijgt, kan `functie` hier geparkeerd staan tot zijn
  slice. Let op: `test_archimate_fase_d.py:83` asserteert nu `== frozenset()` en
  beweegt dan mee.
- **Partitietest**: `test_dekkingstest_elk_elementtype_is_geclassificeerd`
  (`test_archimate_fase_d.py:12`) eist dat elk `ElementType` exact één van de drie
  buckets heeft (getypeerd / geparkeerd / via-componenttype);
  `test_realiseerbare_element_typen_concreet` (`:51`) en
  `test_vaste_typing_is_volledig_...` (`:34`) bewegen mee. Een vergeten indeling faalt
  zichtbaar — precies waarvoor het mechanisme bestaat.

---

## 2. Hiërarchie: welk constructie-patroon past voor "functie onder proces"?

### Vorm A1 — composiet self-FK (het work_package-patroon)

Feitelijk (`models.py:551-581` + `work_package_service.py`):
- Eén tabel; `UNIQUE(tenant_id, id)` als FK-target; self-FK
  `(tenant_id, bovenliggend_id) → work_package(tenant_id, id)` **ON DELETE RESTRICT**
  (subboom niet stil wegvagen; service geeft 409 `HEEFT_SUBPAKKETTEN` als pre-check);
  `CHECK bovenliggend_id <> id` als directe-self-parent-backstop.
- Transitieve cycluspreventie in de **servicelaag** (visited-set langs de ouder-keten,
  `work_package_service.py:72-80`, 422 `CYCLISCHE_HIERARCHIE`); géén DB-trigger.
- **Één-laag-consequentie:** dit patroon staat onbeperkte diepte toe; "proces boven,
  functie eronder, niet dieper" zou een extra service-regel zijn ("een ouder mag zelf
  geen ouder hebben") — conventioneel, niet schema-afgedwongen. Ook zouden proces en
  functie dan één element-type delen (met een niveau-onderscheid als afgeleide van de
  ouder-kolom) — dat botst met een eigen ArchiMate-typing per niveau
  (business_process ≠ business_function, §1).

### Vorm A2 — twee element-typen + FK-kolom (het Gap-ariteit-precedent)

Feitelijk precedent: Gap dwingt zijn vaste 2-ariteit af met **verplichte
composiet-FK-kolommen** op de subtabel i.p.v. relaties (`models.py:595-599`,
"2-ariteit hard in het schema, Besluit 1"; service valideert het doeltype, 422).
Toegepast op proces/functie: een `functie`-subtabel met composiet-FK
`(tenant_id, proces_id) → proces(tenant_id, id)`, en een `proces`-subtabel **zonder**
ouder-kolom. Daarmee is "exact één laag" **structureel onmogelijk te doorbreken**
(een functie kan geen functie-ouder krijgen, een proces geen ouder) — in lijn met
harde-architectuurregel 1 ("structureel boven conventioneel"). ON DELETE-keuze
(RESTRICT vs. SET NULL vs. CASCADE) is een ontwerpbesluit; het kolom-specifieke
SET NULL-patroon (PostgreSQL 15+) en RESTRICT-precedenten bestaan beide (likara-db B6).

### Vorm B — relatie-facade (aggregation/composition, het plateau-leden-patroon)

Feitelijk: plateau-lidmaatschap loopt als `aggregation`-relatie (bron=geheel →
doel=deel) via de unified `relatie`-tabel, kenmerken als jsonb (`models.py:509-511`;
`seed_componentconfig.py:50-56`). `composition` (geheel→deel, existentieel) bestaat
als relatietype met lege kenmerk-definitie (`:45`).
- **Type-borging-feit (geverifieerd V030, opnieuw bevestigd in
  `relatie_service.py:1-100`):** de facade valideert **geen** `element_type` van
  bron/doel — alleen bestaan-binnen-tenant (404), relatietype tegen de catalogus en
  kenmerken tegen de definitie. "Functie alleen onder proces" en "maximaal één laag"
  zouden dus volledig in extra service-/facade-checks moeten (het
  `plateau_service`/`deliverable_service`-facade-patroon doet zoiets voor zijn eigen
  richtingen), en niets in het schema belet een keten proces→functie→functie.
- Uniciteit `UNIQUE(tenant,bron,doel,relatietype)` past (één lidmaatschap per paar).

**Feitelijke observatie t.o.v. het besluit "één hiërarchische laag":** alleen vorm A2
borgt de één-laag-eis in het schema; A1 en B borgen hem uitsluitend service-side.

---

## 3. De koppeling component → proces/functie ("vervult een rol in")

### Route 1 — relatie-facade met rol-kenmerk

- **Bestaande relatietypen** (catalogus-dimensie `archimate_relatie`, gecureerde acht,
  `seed_componentconfig.py:44-72`): kandidaten voor "component ondersteunt/bedient een
  proces" zijn feitelijk `serving` (dienstverlener → bediende; nu in gebruik voor
  applicatie → gebruikersgroep, kaart-ring "gebruikers"), `realization` (realiseerder →
  gerealiseerde; nu work_package → deliverable → plateau) en `association` (vrij; nu
  component ↔ contract). Geen van drie is exclusief "component→proces"; hergebruik
  betekent dat de bestaande consumenten (kaart-ringen, impact-BFS §5) die relaties ook
  zien.
- **Rol-kenmerk-structuur:** kenmerken per relatietype staan als jsonb
  `kenmerk_definitie` op de catalogus-rij (`componentconfig_catalog.kenmerk_definitie`,
  `:89-95`) en zijn **bewust code-eigendom** (DC014: vrije edit breekt de
  relatie-semantiek; gevuld door seed/migratie 0011). Een procesrol zou de bestaande
  vorm volgen: `"procesrol": {"type": "catalogus", "catalogus": "relatiekenmerk",
  "dimensie": "<nieuw>"}` — het exacte precedent is `relatie_rol` op `association`
  (`seed_componentconfig.py:68-70`), gevalideerd in
  `relatie_service._valideer_kenmerken` (`:70-100`).
- **Uniciteits-feit:** `UNIQUE(tenant, bron, doel, relatietype) WHERE relatietype <>
  'flow'` (migratie 0039; `models.py:288-292`) → **één** relatie per (component,
  proces, type). Meerdere rollen van hetzelfde component in hetzelfde proces kunnen dan
  alleen als het kenmerk een lijst wordt (geen bestaand precedent) — losse regels per
  rol zijn op de facade onmogelijk. Dit is exact de botsing waarvoor `roltoewijzing`
  destijds een eigen tabel kreeg.

### Route 2 — eigen tabel (het roltoewijzing-precedent)

Feitelijke opzet van `roltoewijzing` (`models.py:946-990`,
`roltoewijzing_service.py`):
- Eigen tenant-scoped registratie-feit, **geen** element-subtype; docstring benoemt de
  reden letterlijk: de relatie-uniciteit maakt "meerdere rollen per (partij, object)
  als losse regels" onmogelijk (`:949-954`).
- `UNIQUE(tenant_id, partij_id, object_id, rol)`; twee composiet-FK's → `element`
  ON DELETE CASCADE; `rol` = tekst-sleutel naar de catalogus **zonder harde FK**
  (sleutel stabiel, soft-deactiveerbaar).
- Service-validatie: bron moet partij zijn (422 `ONGELDIGE_BRON`), doel ∈
  {component, contract} (422 `ONGELDIG_DOEL`), rol actief (422 `ONGELDIGE_ROL`),
  dubbel → 409 `TOEWIJZING_BESTAAT` (`roltoewijzing_service.py:54-80`).
- RBAC-detail: roltoewijzing heeft **geen eigen `Entiteit`** — de routes hergebruiken
  `Entiteit.PARTIJ` (`routes/roltoewijzing.py:37-63`).

**Herbruikbaarheid 1-op-1:** de vorm past direct op "component X vervult rol Y in
proces Z": `UNIQUE(tenant, component_id, proces_id, rol)`, zelfde composiet-FK's naar
`element`, zelfde service-typechecks (bron=component; doel ∈ {proces} of
{proces, functie}), zelfde catalogus-zonder-FK-koppeling. Of meerdere rollen per
(component, proces) daadwerkelijk gewenst zijn, is het ontwerpbesluit dat route 1 vs. 2
scheidt — het backlog-kader ("de rol is een beheerbaar catalogus-kenmerk") laat beide toe.

---

## 4. Rol-catalogus: waar landt "procesrol"?

Twee gevestigde vormen, feitelijk:

| Vorm | Opzet | Precedent | Wat erbij hoort |
|---|---|---|---|
| **Dimensie op `relatiekenmerk_optie`** | Eén tabel met `dimensie`-discriminator, `UNIQUE(dimensie, optie_sleutel)` (`models.py:1269-1281`); dimensies nu: `dispositie`, `relatie_rol`, `beheerrol` (`RelatieKenmerkDimensie`, `models.py:153-160` — "Toekomstige relatie-kenmerken landen hier eveneens") | **`beheerrol`** — de rollen-catalogus achter `roltoewijzing` ís al een dimensie hier (géén eigen tabel — zie discrepantie-log) | Python-enum + PG-enum `relatiekenmerkdimensie` uitbreiden; seed in `seed_relatiekenmerk.py` (teltest "vast 16 = 4+3+9" beweegt mee, `:67`); beheer via het bestaande relatiekenmerk-beheer |
| **Eigen single-purpose catalogus** | Eigen tabel zonder dimensie: id-PK, `optie_sleutel` UNIQUE(60), `label`, `volgorde`, `actief`; geen RLS | `partijsoort_optie` (`models.py:889`), `componentrol_optie` (`:907`, mét beschermde systeem-sleutel), `biv_schaal_optie` (`:927`, ordinaal via `volgorde`) | Grants (lk_app SELECT; lk_platform S/I/U, geen DELETE), eigen `PlatformEntiteit` + beheer-view (precedent `RolConfigBeheer.vue`), `AUDIT_PLATFORM_ENTITEITEN`, eigen seed |

Feitelijke dwarsverbanden — geen keuze:
- De **kernregel** "checklistvraag is de enige tenant-eigen catalogus" geldt voor
  beide vormen: een procesrol-catalogus is hoe dan ook platform-breed.
- Route-afhankelijkheid met §3: kiest men de **relatie-facade** (rol als
  relatie-kenmerk), dan is de dimensie-vorm de vanzelfsprekende drager (de
  kenmerk-validatie routeert al op `{"catalogus":"relatiekenmerk","dimensie":…}`).
  Kiest men de **eigen tabel**, dan zijn beide vormen bruikbaar — `roltoewijzing`
  bewijst dat een eigen-tabel-feit prima op een `relatiekenmerk`-dimensie kan leunen
  (`beheerrol`), terwijl `componentrol_optie` bewijst dat een single-purpose catalogus
  ook werkt. Naamgevings-aandachtspunt: "componentrol" (ADR-028, rol vàn een component
  in het landschap) en "procesrol" (rol van een component ín een proces) zijn
  verschillende begrippen die dicht bij elkaar liggen.

---

## 5. Impact omhoog rollen: waar leeft afgeleide impact nu?

Bestaande read-only afleidingsplekken (feitelijk):

1. **Impactanalyse per component** — `component_service.impact_analyse`
   (`component_service.py:720+`), GET `/componenten/{id}/impact`
   (`routes/component.py:132`; daarnaast `/verwijder-impact`, `:121`). Iteratieve BFS
   per niveau over de relatietypen `assignment` (host→gehoste), `aggregation`
   (deel→geheel) en `flow` (bidirectioneel), cyclus-veilig via visited-set, kortste
   afstand + pad; "Schrijft niets." Frontend: `ImpactSectie` (knop-getriggerd,
   toegankelijke tabel = waarheidsbron) op ComponentDetail.
2. **Landschapskaart** — `landschapskaart_service` levert **context-ringen**
   (infrastructuur/contracten/gebruikers/samenstelling/beheerorganisatie/
   organisatiestructuur/eigenaar/gebruikt, `:344-466`). Let op: **`IMPACT_RINGEN` is
   afgeschaft** met de Impact-verkenner (`LandschapskaartView.vue:46`) — de kaart doet
   geen impact-berekening meer, alleen context-projectie (discrepantie-log #2).
3. **Registratiegaten** — `registratiegaten_service.overzicht()`: pure read-only
   signalen uit joins/EXISTS (bv. `component_zonder_verantwoordelijke` = geen
   roltoewijzing-rij; `component_zonder_gebruikersgroep` = geen serving-relatie).
4. **Plateau-/gap-readiness** — read-only rollup uit de bestaande lifecycle, niets
   opgeslagen (Plateau/Gap-docstrings; `plateau_service.py`).

**Hoe "functie-raakvlak telt mee op procesniveau" hier feitelijk in past:**
- Door de één-laag-hiërarchie is de roll-up **één join-niveau**: "raakvlakken van
  proces P" = koppelingen op P zelf ∪ koppelingen op de functies onder P. Geen
  recursie/visited-set nodig (die wordt pas verplicht als de hiërarchie toch
  traverseerbaar diep kan zijn — vorm A1/B in §2).
- Het is een **niet-opgeslagen afleiding** naar het readiness-/signalering-model: geen
  tweede bron, geen engine-raakvlak. De omgekeerde vraag ("welke processen raakt
  component X") is dezelfde join andersom en kan zowel een eigen read-endpoint zijn
  (patroon `plaatsingsignaal_service`/`impact_analyse`) als een uitbreiding van de
  bestaande impactanalyse (die traverseert nu alleen assignment/aggregation/flow —
  een proces-koppeling meenemen is een expliciete uitbreiding van die typen-set).
- **Borging-patronen die van toepassing worden** (per bestaande norm, dubbel per
  slice): offline **import-afwezigheidstest** (geen
  `lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/
  `Blokkade`-schrijfsymbolen) + **read-only bronscan** (geen
  `session.add/commit/flush/delete`), en voor engine-naburig leeswerk het
  `table()`/`column()`-construct (DC013) resp. de function-bronscan met
  ast-docstring-strip als de module elders wél schrijft (LI022).

---

## 6. Raakvlakken die meebewegen (inventaris — niets gedaan)

| Raakvlak | Feitelijke stand + wat meebeweegt |
|---|---|
| **RBAC** | `Entiteit`-enum + `PERMISSIES` met `_INHOUD`-patroon (`rbac.py:22, :83, :123+`; Viewer L · Medewerker LAW · Beheerder LAWV · Auditor L). Nieuw: `PROCES` (en later `FUNCTIE`, óf één recht dekt beide — precedent: "één PARTIJ-recht dekt alle partij-aarden", comment `rbac.py:30-33`). De RBAC-matrixteltest beweegt mee. Een eigen koppel-tabel kan zonder eigen entiteit (precedent: roltoewijzing-routes guarden op `Entiteit.PARTIJ`, `routes/roltoewijzing.py:37-63`). Bij een beheer-catalogus: `PlatformEntiteit` (beheerder LAW, operator L; `platform_rbac.py:21`). |
| **Audit** | `AUDIT_TENANT_ENTITEITEN` (`app/core/audit.py:54`): nieuwe subtabellen (`proces`, later `functie`) toevoegen; `element` en `relatie` staan er al (facade-koppelingen gratis gedekt); een eigen koppel-tabel moet expliciet erbij (precedent: `roltoewijzing`, `:62`). Catalogus → `AUDIT_PLATFORM_ENTITEITEN` (`:78+`). |
| **Seed** | `_seed_bvowb_scenario` (`dev_seed_testdata.py:977`, idempotent skip-op-naam). Passend BvoWB/Tiel-voorbeeld op de bestaande apps (Zaaksysteem, Klantportaal, DMS, BRP-bevraging, Burgerzaken-suite, HR-systeem, e-Depot): bv. proces "Burgerzaken" met functies "BRP-beheer" en "Zaakafhandeling", gekoppeld aan Burgerzaken-suite/BRP-bevraging resp. Zaaksysteem/DMS — sluit aan op het bestaande scoringsplan (Zaaksysteem geblokkeerd, BRP migratieklaar) zodat impact-omhoog direct iets toont. Testdata-regel: geen databehoud-migratie; reseed volstaat. |
| **Signalering** | `registratiegaten_service.overzicht()` + `labels.js:SIGNAAL_LABELS`. Een 🟡 "component zonder proces" zou de 1-op-1 mal van `component_zonder_gebruikersgroep` volgen (EXISTS op de koppeling); ook de omgekeerde variant ("proces zonder component") past op de `contract_zonder_component`-mal. Of dit een gewenst signaal is = PNA-besluit. |
| **Kaart** | Nieuwe context-ring volgens het P4-patroon (afgeleide read-only edge, dangling-guard + scope-add). Aandachtspunt: de kaart is **bewust applicatie-centrisch** (`_isApp`/`appNodes`, `LandschapskaartView.vue:344, :382`) — proces-nodes zouden context-nodes worden (zoals partijen/contracten), niet zoekbaar/centreerbaar; de kaart component-/proces-breed maken is het aparte component-breed-ADR-spoor (likara-domeinmodel). |
| **Frontend** | (a) **ComponentDetail-sectie** "Processen" — sectie-precedenten: `VerantwoordelijkheidSectie` (roltoewijzing-UI: lijst + rol-dialog, `ComponentDetail.vue:461`) en `ContractSectie`; (b) **eigen lijst-/detailscherm** voor processen — precedent: de migratie-lijstviews (`PlateauLijstView` c.s., lazy routes onder `AppLayout`, `MIGRATIE_ROLLEN`-gating); nav-link ⇒ registreren in **beide** AppLayout-testrouters (vaste les); (c) elke nieuwe lijst met filters haakt op **`useLijstStaat`** aan (dit-sessie-patroon); (d) picker: proces-keuze = `ZoekSelect` (open-ended entiteit-referentie); (e) api-client: nieuwe filters in destructuring én `_query` (V012-les). |

---

## Discrepantie-log (aannames/skills vs. code)

1. **"Beheerrol"-catalogus is géén eigen tabel.** De likara-domeinmodel-skill (§5-tabel)
   noemt "Beheerrol | `beheerrol`" als eigen tabel; werkelijk is het een **dimensie** in
   `relatiekenmerk_optie` (`RelatieKenmerkDimensie.beheerrol`, `models.py:153-160`;
   seed `seed_relatiekenmerk.py:46`; de roltoewijzing-docstring verwijst er zelf naar,
   `models.py:957-958`). Relevant voor §4 (het "dimensie-precedent" is sterker dan de
   skill suggereert). Skill-correctie hoort bij de sessie-afsluiting (nu read-only).
2. **Kaart-ringen doen geen impact meer.** De opdracht noemt "kaart-ringen" als
   impact-plek; `IMPACT_RINGEN` is met de Impact-verkenner **afgeschaft**
   (`LandschapskaartView.vue:46`) — de ringen zijn context-projectie (ADR-040).
3. **`business_process`/`business_function` ontbreken in de gesloten whitelist**
   (`TOEGESTANE_ELEMENTEN`) — de uitbreiding is een expliciet, ADR-026-rakend besluit,
   geen vanzelfsprekendheid.
4. **`ELEMENT_TYPEN_NOG_NIET_GEREALISEERD` is leeg maar bestaat als parkeermechanisme**
   — het "functie later"-kader heeft dus al een voorziene landingsplek (incl. test die
   meebeweegt, `test_archimate_fase_d.py:83`).
5. **Roltoewijzing heeft geen eigen RBAC-entiteit** (hergebruikt `Entiteit.PARTIJ`) —
   relevant precedent voor de vraag of een proces-koppeling een eigen recht nodig heeft.

---

*Einde rapport — STOP conform opdracht. Geen ontwerp, geen ADR, geen bouw, geen commit;
de ontwerpbesluiten (element-vorm, hiërarchie-vorm, koppelingsroute, catalogus-vorm)
liggen bij PNA + Bert.*
