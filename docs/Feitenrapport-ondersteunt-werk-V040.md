# Feitenrapport — "ondersteunt werk" als eigenschap van het componenttype + picker-uitleg

| | |
|---|---|
| **Opdracht** | LI040-checkpoint-ondersteunt-werk (read-only feitencheck) |
| **Datum** | 2026-07-13 |
| **Commit** | `0e678a7` (LI039-afsluiting, build V040) — werktree schoon |
| **Alembic head** | `0064_gate1b_inlees_voltooid` (1 head) |
| **Modus** | Read-only. Geen code-, schema-, seed- of testwijziging; alleen dit rapport aangemaakt. DB-metingen als `lk_admin` via `docker exec lk-postgres psql` (read-only SELECT's). |

---

## 1. Uitkomst in één zin

Het `checklist_dragend`-precedent is end-to-end herbruikbaar (kolom → schema → service → beheerscherm → seed → reconcile-migratie, met audit en RBAC die gratis meebewegen), **maar** het read-pad voor de picker bestaat alleen als de nieuwe vlag expliciet aan `GET /componenten/opties` wordt toegevoegd, server-side filteren op een *set* typen kan vandaag niet (het `componenttype`-filter is enkelvoudig), er bestaat **geen** gedeelde bouwsteen voor "waarom ontbreekt hier een optie", en het precedent bevat één aantoonbare discrepantie: het beheerscherm stuurt `checklist_dragend` mee bij **aanmaken** terwijl het Create-schema (`extra='forbid'`) dat veld niet kent → 422.

---

## 2. A — De eigenschap op het componenttype

### A1 — Het precedent `checklist_dragend`, end-to-end

**Model/kolom** — `modules/bwb_ontvlechting/backend/models/models.py:1584-1586`:
`Mapped[bool]`, **NOT NULL**, `server_default text("false")`, op `ComponentConfigOptie` (platform-brede tabel, GEEN RLS/tenant_id, `dimensie`-discriminator; `models.py:1550-1586`). Code-comment (`:1581-1583`): "alléén relevant voor dim=`componenttype`" — dat is **conventie**, geen schema-borging: de kolom bestaat op álle rijen, ook de 10 niet-componenttype-rijen (zie A4).
Geïntroduceerd door migratie **`0009_adr022_e_checklist_dragend.py`** (`:24-27`: `add_column` Boolean NOT NULL server_default false; `:29-32`: backfill `applicatie=true`). Reconciles daarna: **`0023_checklist_dragend_fix.py`** (data-only: applicatie true, ál het overige binnen dimensie componenttype false; downgrade = no-op) en **`0046_database_beoordeeld.py`** (database true; spiegelt het 0023-patroon).

**Schema** — `modules/bwb_ontvlechting/backend/schemas/componentconfig.py`:
- **Create (`:49-96`)**: `checklist_dragend` **ontbreekt**; `model_config = ConfigDict(extra="forbid")` (`:50`). Een nieuw type krijgt de vlag dus via de kolom-default (false) en kan pas daarna via Update aan.
- **Update (`:99-111`)**: `checklist_dragend: bool | None = None` (`:106`), naast label/volgorde/actief/typering. `extra='forbid'`; dimensie/sleutel immutabel (niet in Update).
- **Read (`:134-152`)**: `checklist_dragend: bool = False` (`:144`).
- ⚠ **Geverifieerde discrepantie**: `frontend/src/views/ComponentConfigBeheer.vue:157` stuurt bij **aanmaken** van een componenttype altijd `data.checklist_dragend` mee (binnen het `isComponenttype`-blok `:153-158`). Offline geverifieerd tegen het echte schema: `ComponentConfigOptieCreate(..., checklist_dragend=True)` → `ValidationError: extra_forbidden`. De route (`routes/componentconfig.py:56-60`) gebruikt `ComponentConfigOptieCreate` direct, zonder stripping. **Gevolg (uit de code afgeleid): een nieuw componenttype toevoegen via het beheerscherm levert een 422 op** — het bewerken-pad (dat de vlag wél kent) werkt normaal. Niet end-to-end tegen de draaiende API getest (zie §7), maar het schemapad is eenduidig.

**Service** — `modules/bwb_ontvlechting/backend/services/componentconfig_service.py`:
- `voeg_toe` (`:50-92`) zet de vlag **niet** (kolom-default false wint).
- `wijzig` (`:113-163`): legt de oude waarde vast vóór de mutatie (`_oud_dragend`, `:128`), zet elk `exclude_unset`-veld generiek via `setattr` (`:152-153`). **Er is géén dimensie-guard op het vlag-veld zelf** — het Update-schema en de setattr-lus zouden `checklist_dragend` ook op een `archimate_relatie`-rij zetten; alleen de frontend (`editIsComponenttype`) en de leesfilters beperken het feitelijk tot componenttype. De **backfill-trigger** is wél dimensie-gebonden: `obj.dimensie == _SYSTEEM_DIMENSIE and not _oud_dragend and checklist_dragend` (`:157-162`).
- Systeem-sleutel-bescherming (`:130-138`) geldt alleen voor `actief=false` op `componenttype.applicatie` — niet voor de vlag.

**Beheerscherm** — `frontend/src/views/ComponentConfigBeheer.vue`:
- Tabelkolom: `Tag` Ja/Nee met severity success/secondary (`:325-327`, testid `cat-dragend-{id}`).
- Add-dialoog: native **checkbox** (`:462-463`) mét `<VeldUitleg veld="checklist_dragend" />` (`:465`); edit-dialoog idem (`:529-530`). De uitlegtekst leeft centraal in `modules/bwb_ontvlechting/frontend/velduitleg.js:270-274`.

**RBAC/audit**:
- `PlatformEntiteit.COMPONENTCONFIG` (`backend/app/core/platform_rbac.py:30`), beheerder LAW / operator L (`:79-82`). RBAC is entiteit-niveau: **een nieuwe kolom vergt geen RBAC-wijziging**.
- `componentconfig_optie` staat in `AUDIT_PLATFORM_ENTITEITEN` (`backend/app/core/audit.py:84-85`). De capture is mapped-column-gebaseerd (`bouw_wijziging`, `audit.py:146`, itereert `state.mapper.column_attrs`, `:157`) → **een nieuwe mapped kolom wordt automatisch per-veld geauditeerd**; er beweegt niets handmatigs mee.

**Seed** — `modules/bwb_ontvlechting/backend/services/seed_componentconfig.py`:
- De vlag staat **expliciet per type** in `_COMPONENTTYPE` (`:22-38`, comment `:18-21`: "single source = de seed, niet de kolom-default laten winnen").
- Álle rijen (ook de twee andere dimensies) dragen `checklist_dragend` in de multi-row insert (`:87`, `:94`, `:101`) — de uniforme-sleutelset-eis van `pg_insert` (`:78-81`).
- Byte-gelijkheid seed ↔ migratie: de seed is de *expand* (fresh deploy), de reconcile-migraties 0023/0046 zijn de *contract* (bestaande DB) — beide zetten exact dezelfde stand (comment `0023:9-12`).
- NB: `backend/dev_seed_testdata.py:682-716` bevat `_seed_tweede_type` die `client_software` op true zou zetten, maar die functie wordt **niet aangeroepen** vanuit `main()` (`:1801-1823` roept alleen `_seed_bvowb_scenario`); live DB bevestigt: `client_software=false`, 0 client_software-vragen. Dode/legacy seed-functie met een stale docstring ("database blijft false" — achterhaald door LI058/0046).

**Gevolg-effect bij een flip**:
- **False→True**: ná de commit draait `_activeer_type_backfill` (`componentconfig_service.py:95-110`): enumereert de `Tenant`-registry op de platform-sessie en opent per tenant een RLS-scoped worker-sessie → `checklistconfig_service.backfill_profielen` (`checklistconfig_service.py:173-201`): ontbrekende `ComponentProfiel` (lifecycle `concept`) + `herbereken_type`. Idempotent.
- **True→False**: bestaande profielen/scores blijven **inert** (docstring `:120-124`); alleen het gebruikers-invoerpad sluit (`checklistscore_service.py:124-130` → 422 `CHECKLIST_GESLOTEN`). Reversibel.
- **Kernvraag (generiek of checklist-eigen?): het mechanisme is checklist-eigen, niet generiek.** De transitie-detectie zit inline in `wijzig` en is hard bedraad aan `checklist_dragend` én aan de checklist-backfill. Er bestaat geen generieke "vlag flipt → naloop"-haak. Het *patroon* (oud-waarde vastleggen → na commit een dimensie-gebonden handler) is wel kopieerbaar. Of "ondersteunt werk" überhaupt een naloop nodig heeft is een ontwerpvraag (knoop 3, §6): de eigenschap is registratief en raakt geen profiel/engine — er is (nu) niets om te backfillen.

### A2 — De 8 componenttypen, live uit de dev-DB (2026-07-13)

`SELECT … FROM componentconfig_optie WHERE dimensie='componenttype' ORDER BY volgorde, id;`

| optie_sleutel | label | archimate_element | laag | aspect | checklist_dragend | actief |
|---|---|---|---|---|---|---|
| applicatie | Applicatie | application_component | application | active | **true** | true |
| database | Database | system_software | technology | active | **true** | true |
| server_compute | Server / compute | node | technology | active | **true** | true |
| client_software | Client-software | system_software | technology | active | false | true |
| saas_dienst | SaaS-dienst | application_component | application | active | false | true |
| integratievoorziening | Integratie-/koppelvoorziening | system_software | technology | active | **true** | true |
| fileshare | Fileshare | node | technology | active | false | true |
| landelijke_voorziening | Landelijke voorziening | application_service | application | active | **true** | true |

(Identiek aan de seed-stand in `seed_componentconfig.py:22-38` — geen drift.)

### A3 — Bestaande "tweede waarheden" over componenttypen

Brede grep (backend + frontend + modules) op hardcoded type-literals/predicaten. Per treffer: wat dwingt hij af, en verhouding tot "ondersteunt werk".

**Backend:**

| Vindplaats | Wat dwingt hij af | Verhouding tot "ondersteunt werk" |
|---|---|---|
| `component_service.py:58` (`_APPLICATIE_TYPE`), gebruikt op `:257`, `:453` (`heeft_applicatie_subtype`), `:504-538` (convergente applicatie-aanmaak), `:611` (typewissel-guard: `nieuw == 'applicatie' or is_checklist_dragend`) | Applicatie-specifiek gedrag (checklist-redirect, typewissel-bescherming) | **Los ervan** — subtype-/checklist-semantiek, geen werk-ondersteuning |
| `gebruikersgroep_service.py:36, 342-345` | Gebruikersgroep-ouder MOET `componenttype='applicatie'` (anders 404) | **Los ervan** — kind-koppelingsregel |
| `datatype_service.py:19, 145-149` | Datatype-ouder MOET `applicatie` | **Los ervan** — idem |
| `componentconfig_service.py:17-18` | Systeem-sleutel-bescherming `componenttype.applicatie` | **Los ervan** — catalogus-integriteit |
| `entiteit_resolutie.py:27` | `"applicatie"` als audit-entiteitstype → Component-naam | **Los ervan** — historische audit-records |
| `procesvervulling_service.py:6, 70` | Expliciet **component-breed** ("élk componenttype") | **Tegenovergestelde regel** — zie B4 ⚠ |

**Frontend:**

| Vindplaats | Wat dwingt hij af | Verhouding tot "ondersteunt werk" |
|---|---|---|
| `KoppelingSectie.vue:54, 66` | Flow-picker filtert hard `componenttype: 'applicatie'` — koppelingen alleen tussen applicaties in deze UI | **Los ervan**, maar het is de enige bestaande "welke typen mogen hier"-picker-inperking; zou NIET door de nieuwe vlag vervangen worden (flow ≠ functie-as) |
| `LandschapskaartView.vue:277` (`isApplicatie`), `:382` (`_isApp`: `element_type==='applicatie' \|\| laag==='application'`), `:421` (`appNodes`), `:1487` (`_heeftComponentDetail`) | Kaart is bewust applicatie-centrisch (LI034-besluit); doorklik-predicaat op ArchiMate-laag | **Los ervan** — laag-afleiding, geen werk-uitspraak |
| `BlokkadeOverzichtView.vue:102-106` | Routekeuze applicatie-detail vs. component-detail | **Los ervan** |

**Conclusie A3**: geen enkele bestaande waarheid bedoelt "ondersteunt werk". De twee assen die er het dichtst bij in de buurt komen vallen er beide **niet** mee samen:
- `checklist_dragend` (= "wordt beoordeeld") dekt vandaag óók `database`/`server_compute`/`integratievoorziening` — typen die volgens de functionele schets géén werk ondersteunen;
- `laag === 'application'` (= ArchiMate-typing) dekt `applicatie`/`saas_dienst`/`landelijke_voorziening`, maar is een afgeleide van de typering (niet los beheerbaar) en heeft een andere betekenis.

Een nieuwe eigenschap voegt dus een **derde as** toe naast deze twee — dat is precies de reden om hem als eigen, beheerbare catalogus-eigenschap te modelleren (het genomen LI039-besluit), maar het is goed te weten dát die twee andere assen bestaan en blijven bestaan.

### A4 — De twee schema-borgingsvormen, feitelijk

**Vorm 1 — NOT NULL + server_default** (kolom bestaat overal, default vult bestaande rijen):
- `0009_adr022_e_checklist_dragend.py:24-27` — `checklist_dragend` Boolean NOT NULL `server_default false` op `componentconfig_optie` + gerichte backfill.
- `0048_adr028_classificatie.py:71-77` — `componentrol` String(60) NOT NULL `server_default 'interne_applicatie'` op `component` ("bestaande rijen vullen zich vanzelf; geen datamigratie").

**Vorm 2 — conditionele CHECK per dimensie**:
- `0025_adr026_typering_volledig.py:26-29` — `ck_componentconfig_typering_volledig`: `dimensie <> 'componenttype' OR (archimate_element IS NOT NULL AND laag IS NOT NULL AND aspect IS NOT NULL)`. **Live geverifieerd** in `pg_constraint` (aanwezig, exact deze definitie). Borgt volledigheid alléén voor de dimensie componenttype; andere dimensies mogen NULL.

**Rijen zonder dimensie `componenttype`** (live, mogen de eigenschap niet dragen): **10 rijen** — 2× `structuurrelatie_type` (`draait_op`, `maakt_deel_uit_van`) + 8× `archimate_relatie` (composition, aggregation, serving, assignment, flow, realization, association, access). Alle 10 dragen vandaag `checklist_dragend = false` (de kolom is dimensie-ongebonden; er is voor `checklist_dragend` **géén** CHECK die dat afdwingt — alleen conventie plus dimensie-gefilterde leespaden zoals `is_checklist_dragend`, `componentconfig_catalog.py:30-42`).

---

## 3. B — Picker & uitleg

### B1 — De meest verwante picker: `zoekPlaatsDoelen` + `plaatsZin`

`modules/bwb_ontvlechting/frontend/views/BedrijfsfunctieLijst.vue`:
- **`zoekPlaatsDoelen` (`:399-410`)** — client-side filter over de al-geladen functieboom (`alle`), gevoed aan een `ZoekSelect` (`:980`). Weert vooraf, spiegelend aan de backend-regels (picker-regel 1, LI032): de eigen subboom + zichzelf (`subboomIds` — kring), de huidige ouders (`boom.oudersVan` — zou 409 `PLAATSING_BESTAAT` geven) en `vervallen` functies. Sorteert nl-locale; `doelWeergave` toont context ("naam — ouders"). Remount-`plaatsKey` per opening (stale-label-les).
- **`plaatsZin` (`:417-421`, getoond op `:988`)** — een computed zin die **vooraf zegt wat er gáát gebeuren**: `"X" komt óók onder "Y" te staan — het blijft één en dezelfde functie.` Zusje: `haalWegZin` (`:455-462`) benoemt het gevolg van weghalen incl. het wortel-geval.
- **Wat hij NIET doet**: uitleggen **waaróm een optie ontbreekt**. Een geweerde functie verdwijnt geluidloos uit de lijst. Dit bevestigt fase-A-patroon 11: *weren is gebouwd, uitleggen niet*.

### B2 — Kan de picker straks op de eigenschap filteren? — **Read-pad AANWEZIG (mits uitgebreid); multi-type-filter ONTBREEKT**

**Componenten-leverende endpoints voor pickers**: `GET /componenten` (`routes/component.py:45-83`) is de enige bron die de B4-pickers gebruiken (via `api.componenten.lijst`).

**Route-allowlist** (`routes/component.py:46-66`): `limit, after, sort, order, componenttype, laag, status[] (multi), hostingmodel, eigenaar_organisatie_id, leverancier_id, zoek, componentrol[] (multi), biv_*_min (×3), klaarverklaring, afwijking`.
**api.js-`_filterQuery`-allowlist** (`frontend/src/api.js`, blok `componenten.lijst`): exact dezelfde keys.

- **Server-side op componenttype filteren kan — maar alléén enkelvoudig** (`componenttype: str | None`, `:50`). Een *set* typen ("alle werk-ondersteunende typen") kan vandaag niet in één call. Precedent voor een herhaalbare multi-param bestaat op hetzelfde endpoint: `componentrol: list[str] = Query(default=[])` (`:58`). Server-side filteren op een **catalogus-vlag** (join componentconfig) bestaat nergens op dit endpoint.
- **`GET /componenten/opties` levert de catalogus-vlaggen WÉL tenant-side**: `ComponentKeuze` (schemas/component.py:216-227) draagt per componenttype `checklist_dragend` + `archimate_element` + `laag`; gevuld door `componentconfig_catalog.actieve_opties_per_dimensie` (`componentconfig_catalog.py:107-144`, select `:114-122`, dict `:137-143`) via `component_service.opties`. Tenant-RBAC `COMPONENT.LEZEN`; `lk_app` heeft SELECT op de catalogus (CD051).

**Expliciet oordeel**: het read-pad voor een catalogus-vlag naar de tenant-frontend **bestaat** (`/componenten/opties` — de platform-beheerroute is inderdaad onbereikbaar voor tenants: `routes/componentconfig.py`, `vereist_platform_permissie`). Een **nieuwe** vlag reist daar echter **niet automatisch** mee: hij moet op drie plekken worden toegevoegd — de catalog-select (`componentconfig_catalog.py:114-122`), het dict (`:137-143`) en het `ComponentKeuze`-schema. Wat **ontbreekt** is een server-side manier om de *componentenlijst zelf* op meerdere typen of op de vlag te filteren; de feitelijke opties die de code toelaat staan in knoop 5 (§6).

### B3 — Waar leeft "uitleg" vandaag? — **Bouwsteen voor "waarom ontbreekt een optie": BESTAAT NIET**

| Bouwsteen | Vindplaats | Wat hij doet |
|---|---|---|
| **VeldUitleg** ('i'-popover/inline) | component: `modules/bwb_ontvlechting/frontend/views/VeldUitleg.vue`; teksten centraal: `modules/bwb_ontvlechting/frontend/velduitleg.js` (501 regels, `VELD_UITLEG` + `OPTIE_UITLEG`, accessors met nette degradatie) | Eén gedeelde component (popover op klik/focus, of inline-regel), gebruikt in 10+ beheer-views + formulieren. Statische veld-framing + per-optie discriminatieregels. `checklist_dragend` heeft al een entry (`velduitleg.js:270-274`) |
| **ZoekSelect `#leeg`-slot** | `ZoekSelect.vue:284-287` (scoped slot met `query`; default "Geen resultaten.") | Kan vrije inhoud dragen (precedent: search-first aanmaken in `AfdelingSelect`). Vuurt **alleen bij 0 resultaten** — een geweerde database bij >0 andere treffers triggert hem niet |
| **MeldingBanner** | `frontend/src/components/MeldingBanner.vue` | Weigering/fout/info-banner (kleur+icoon+tekst) bij een gedáne poging — niet preventief |
| **plaatsZin** | `BedrijfsfunctieLijst.vue:417-421` | Zegt vooraf wat er gaat gebeuren — per scherm, inline computed, geen bouwsteen |
| **wijkMelding** | `frontend/src/composables/useToonNieuweRij.js:71, 112` | Leesbare mededeling wanneer het getoonde afwijkt van wat je zocht |

**Expliciet oordeel**: er is **geen** gedeelde bouwsteen die verklaart waarom een optie in een picker ontbreekt. De ingrediënten liggen klaar (VeldUitleg voor de tekst-huisvesting, `#leeg`-slot voor de lege staat, `plaatsZin`-vorm voor de zin), maar het "je zocht X — X valt buiten deze keuze, omdat…"-gedrag zelf is **nieuw te ontwerpen**. Fase-A-patroon 11 klopt onverkort.

### B4 — Regressie-grens: pickers die vandaag componenten tonen

Alle vindplaatsen van `api.componenten.lijst` als picker-bron:

| Picker | Vindplaats | Typen die hij nú toont |
|---|---|---|
| Koppeling (flow) — doel-applicatie | `KoppelingSectie.vue:54, :66` | **Alleen `applicatie`** (hardcoded filter) |
| Structuur (`draait_op`/assignment) — doel-component | `StructuurSectie.vue:43` | **Alle typen** (geen filter) — bv. database → server |
| Procesvervulling — component bij proces | `ProcesComponentenSectie.vue:54` | **Alle typen** — *bewust* component-breed (ADR-042-besluit; `procesvervulling_service.py:6, :70`) |
| Roltoewijzing — object-picker | `PartijRollenSectie.vue:36-44` | **Alle componenten + alle contracten** |
| Plateau-leden | `PlateauDetailView.vue:143` | **Alle typen** |
| Gap-leden | `GapDetailView.vue:154` | **Alle componenten** óf contracten |
| Kaart-beginscherm-zoek | `KaartBeginscherm.vue:68` + `_zoekParams` | Alle typen; `componenttype` alleen als gebruikers-filter |
| Audit-trail component-filter | `AuditTrailView.vue:41` | Alle typen |
| Datatype-/Gebruikersgroep-sectie | geen component-picker (`applicatie_id` vast; backend eist type applicatie: `datatype_service.py:148`, `gebruikersgroep_service.py:344`) | n.v.t. |
| ContractSectie | contract-picker (`ContractSectie.vue:39`), geen componenten-picker | n.v.t. |

**Géén van deze pickers mag door de nieuwe vlag geraakt worden** — "ondersteunt werk" is een functie-as-regel. Twee expliciete waarschuwingen:
1. ⚠ **ProcesvervullingSectie is het gevoeligste raakvlak**: de proces-koppeling is per ADR-042 *bewust* component-breed, en de velduitleg zegt dat letterlijk tegen de gebruiker (`velduitleg.js`, entry `applicatiefunctie`: *"dit geldt voor elk componenttype (ook een database of landelijke voorziening)"*). De functie-as gaat het omgekeerde doen. Twee verschillende regels op twee verschillende verbanden — feitelijk verenigbaar, maar wie de vlag als generiek filter zou hergebruiken breekt het ADR-042-besluit én die uitlegtekst.
2. ⚠ **StructuurSectie** (database → server) en **Plateau/Gap-leden** tonen terecht alle typen; een generieke toepassing van de vlag zou legitieme infra-registratie blokkeren.

---

## 4. C — Gevolgen bij bestaande data

**Componenten per type (dev-tenant `11111111-…`, live):**

| componenttype | aantal |
|---|---|
| applicatie | 16 |
| saas_dienst | 1 |
| database | 1 |
| fileshare | 1 |
| server_compute / client_software / integratievoorziening / landelijke_voorziening | 0 |

Er bestaan dus vandaag componenten van typen die (volgens de functionele schets) géén werk ondersteunen: 1 database + 1 fileshare. (saas_dienst: afhankelijk van Berts aanvink-besluit.)

**Koppeling component ↔ bedrijfsfunctie**: bestaat **niet** — bevestigd op drie niveaus:
- Model: `bedrijfsfunctie_service.py` bevat geen enkele componentreferentie (grep: 0 treffers); `procesvervulling` koppelt component↔**proces**, niet ↔functie.
- Data: 0 relaties met een component- én bedrijfsfunctie-endpoint (live query over `relatie` × `element`).
- Bestand: 299 bedrijfsfuncties (297 uit bron niet-vervallen + 1 uit bron vervallen + 1 eigen), 304 `aggregation`-plaatsingen — allemaal functie↔functie.
Gate 2 is ongebouwd, zoals verwacht.

**Reseed bij een nieuwe kolom met `server_default`**: niet nodig voor de kolom zelf — de default vult bestaande rijen (0009/0048-precedent). Wél hoort (F-6-les, `seed_componentconfig.py:18-21`): (a) de **seed** de waarde expliciet per type te dragen (single source; élke rij in `bouw_componentconfig` levert dezelfde sleutelset, `:78-81`), en (b) een **data-reconcile-migratie** in het 0023/0046-patroon de gewenste per-type-stand op bestaande DB's te zetten. Testdata-aanpassing: **nee** (geen componentrijen hoeven bij); alleen de catalogus-seed + reconcile.

---

## 5. (vervalt — geen ontwerpvoorstellen; zie §6)

---

## 6. Open knopen voor Bert

1. **Kolomvorm en dimensie-borging.** De code laat twee feitelijke vormen toe: (a) boolean NOT NULL + `server_default` zonder verdere borging — exact `checklist_dragend` (0009), waarbij de kolom ook op de 10 niet-componenttype-rijen bestaat (waarde blijft daar default); (b) idem **plus** een conditionele CHECK in de 0025-vorm die afdwingt dat de eigenschap buiten de dimensie `componenttype` zijn default houdt. `checklist_dragend` zelf heeft géén CHECK; ook de service-laag heeft geen dimensie-guard op de vlag (A1).
2. **Welke typen krijgen de eigenschap.** Feitenbasis = de A2-tabel (8 typen). Ter info de twee bestaande assen ernaast: checklist_dragend (appl/db/server/integratie/landelijk = true) en laag (application = appl/saas/landelijk). Geen van beide valt samen met de functionele schets — het aanvinken is een echt nieuw besluit per type.
3. **Flip-gedrag.** Het checklist-precedent heeft een naloop (backfill) omdat er engine-state bijhoort; "ondersteunt werk" is registratief zonder afhankelijke state — tot gate 2 er is. Opties die de code toelaat zodra functie-koppelingen bestaan en een type op False gaat: niets doen (bestaande koppelingen blijven staan — het inert-patroon van True→False bij checklist), signaleren (ADR-035-signaalpatroon), of het invoerpad sluiten met bestaande koppelingen leesbaar (het `CHECKLIST_GESLOTEN`-patroon, `checklistscore_service.py:124-130`). Bij de introductie zelf (gate 2 ongebouwd) is er niets om na te lopen.
4. **Wel/niet in het Create-schema.** `checklist_dragend` zit niet in Create (alleen Update) — en het beheerscherm stuurt hem bij aanmaken tóch mee → aantoonbare 422 op "componenttype toevoegen" (A1, geverifieerd op schema-niveau). Voor de nieuwe vlag: opnemen in Create (dan is dit meteen het patroon) óf het checklist-precedent volgen (alleen Update). De bestaande discrepantie is hoe dan ook een **losse bug-fix** buiten dit checkpoint.
5. **Server-side filtervorm voor de picker.** Drie opties die de code feitelijk toelaat: (a) `componenttype` herhaalbaar maken (multi, precedent `componentrol` op hetzelfde endpoint, `routes/component.py:58`); (b) een vlag-filterparam op `GET /componenten` die server-side tegen de catalogus joint (nieuw patroon op dit endpoint); (c) client-side: de picker leest de toegestane typen uit `/componenten/opties` en filtert de treffers — botst met server-side paginering/limit (een pagina kan leeglopen). In alle gevallen moet de nieuwe vlag aan de drie B2-plekken van `/componenten/opties` worden toegevoegd om de **uitleg** te kunnen voeden.
6. **De uitleg-bouwsteen.** Bestaat niet (B3). Te beslissen: waar de tekst leeft (het `velduitleg.js`-precedent = ontwikkelaar-beheerd; of bij de catalogus = platformbeheerder-beheerd) en welk gedrag (altijd-zichtbare regel bij de picker, `#leeg`-slot-uitbreiding, en/of een "je typte 'DMS-database' — databases ondersteunen geen werk"-reactie op de zoekterm).
7. **Bevestiging van de regressie-grens.** De vlag wordt géén generiek koppelbaarheidsfilter: de B4-pickers (m.n. StructuurSectie, ProcesComponentenSectie/ADR-042, Plateau/Gap-leden, PartijRollenSectie) blijven ongemoeid, en de bestaande hardcoded inperkingen (KoppelingSectie `'applicatie'`; kaart-predicaten) blijven staan als eigen, losse waarheden. Expliciet af te tikken zodat gate 2 dit als grens meekrijgt.

---

## 7. Wat ik NIET heb kunnen vaststellen

- **De 422 op "componenttype toevoegen" is niet end-to-end tegen de draaiende API getest** (vergt een platform-login/sessie; buiten read-only-modus wilde ik geen testverkeer genereren). De verificatie is op schema-niveau gedaan (Pydantic weigert de payload die `ComponentConfigBeheer.vue:157` bouwt) en de route geeft de body ongefilterd aan dat schema. Een browser-reproductie door Bert zou het sluitend maken.
- **Of er ooit met succes een componenttype via het beheerscherm is toegevoegd** (wat de discrepantie zou dateren): niet uit de audit-log gemeten.
- **De exacte gate-2-picker-vorm** (zoekt hij componenten, of eerst functie → dan component?): gate 2 is niet ontworpen; de B-antwoorden beschrijven de bouwstenen, niet het toekomstige scherm.
- **Frontend-testdekking van het add-pad in ComponentConfigBeheer**: niet onderzocht of een bestaande test dit pad met een gemockte api groen houdt (mocks valideren het schema niet — dat zou verklaren waarom dit onopgemerkt bleef); alleen als hypothese benoemd, niet vastgesteld.
