# ADR-021 — Component-herfundering: supertype `Component`, subtype `Applicatie`, landschapsgraaf

**Status**: Aanvaard (CD006-sessie)
**Datum**: juni 2026
**Context-ADR's**: ADR-009 (huidig applicatie-datamodel — wordt geherfundeerd), ADR-013/016
(lifecycle-/blokkade-engine — verankering blijft ongewijzigd), ADR-019/020 (catalogus-patroon),
ADR-012 + Addenda A/B (platform-RBAC-patroon), ADR-020 (contractregister — koppeling
generaliseert mee).

## Context

In het huidige model (ADR-009) is `applicatie` een monoliet: één hostingmodel, één technische
identiteit, en alle relaties (koppelingen, contracten, datatypes, gebruikersgroepen, checklist,
lifecycle, blokkades) hangen aan dat ene object. De technische opbouw van een applicatie
(client, applicatieserver, database, middleware) bestaat alleen beschrijvend — in
checklistcategorie 2 (oordeelsvragen) en vrije tekst. Daardoor is niet uitdrukbaar: "app X
draait op database Y", "app A en app B delen database Y" (het gedeelde-infrastructuurrisico van
vraag 2.7, nu alleen als oordeel), of "dit contract hoort bij de database, niet bij de app".

Tegelijk is het applicatie-perspectief precies wat management en gebruikers onder "het
ICT-landschap" verstaan. De waarde van CompliData is de **brug**: het logische landschap
(applicaties, checklists, readiness, contracten) en het technische landschap (componentengraaf)
als twee lenzen op één model — vanuit een applicatie afdalen ("waar draait dit op"), vanuit een
component opstijgen ("welke applicaties — en dus welke readiness en contracten — raakt het als
dít verhuist").

**Pre-productie-context (eenmalige luxe, expliciet gemarkeerd):** er draait geen productie;
alle dev-data is reproduceerbare, idempotente seed (Aanvulling A–D). Deze herfundering gebeurt
daarom **zonder datamigratiepaden**: het schema wordt herfundeerd en de dev-DB opnieuw geseed.
Zodra er ooit echte tenant-data bestaat, vereisen modelwijzigingen wél migratiepaden — dit ADR
is de laatste van dit soort.

## Besluit

### Kernmodel — supertype/subtype als twee tabellen (class-table)

1. **`component`** (tenant-scoped, RLS) — het knooppunt van de landschapsgraaf. Velden:
   `naam` (verplicht), `componenttype` (sleutel uit de componentcatalogus, verplicht),
   `hostingmodel` (bestaande enum, verhuist van applicatie naar component), `eigenaar_organisatie`,
   `eigenaar_naam`, `leverancier` (vrije tekst, verhuist mee — registratieve aantekening; het
   contractregister blijft de structurele waarheid), `beschrijving`.

2. **`applicatie`** (tenant-scoped, RLS) — subtype, **1-op-1** aan zijn component
   (`component_id` FK, UNIQUE, ON DELETE CASCADE vanaf component is uitgesloten — zie 4).
   Draagt exclusief het applicatie-apparaat: `lifecycle_status`, `migratiepad`, `complexiteit`,
   `prioriteit`. Geen eigen naam (de component-naam is dé naam).

3. **Engine-verankering ongewijzigd**: checklist, scores, blokkades blijven aan `applicatie`
   hangen — de tabellen, de afleidingsregels (ADR-013/016) en de tellingen wijzigen niet.
   Datatypes en gebruikersgroepen blijven eveneens aan `applicatie` (B1).

4. **Subtype-grens is structureel**: alleen `applicatie` draagt checklist/lifecycle/blokkades;
   een component zonder subtype kán dat niet. Een nieuw checklist-dragend type is per definitie
   een nieuw subtype-besluit → eigen ADR. Verwijderregels: een component met subtype wordt via
   het applicatie-pad verwijderd (subtype + component samen, atomair in de service); een
   "kale" component (technische laag) is direct verwijderbaar mits geen relaties (409 conform
   ADR-020-patroon).

### De graaf — twee relatiesoorten op componentniveau

5. **`koppeling` generaliseert** naar component↔component: bron/doel worden component-FK's;
   velden (richting, protocol, impact_bij_verbreking, omschrijving) en CHECK bron≠doel blijven.
   Semantiek: **gegevensuitwisseling/integratie** — beantwoordt de migratievolgorde-vraag.

6. **Nieuwe `component_structuur`** (tenant-scoped): `component_id` (de afhankelijke, bv. de
   applicatie) → `op_component_id` (waarop het draait/waarvan het deel uitmaakt),
   `relatietype` (sleutel uit de catalogus: o.a. `draait_op`, `maakt_deel_uit_van`),
   `omschrijving` (optioneel). CHECK component≠op_component; UNIQUE
   (tenant, component, op_component, relatietype). Semantiek: **opbouw/afhankelijkheid** —
   dé bron voor de impactanalyse en de feitelijke onderlegger van "gedeelde infrastructuur".
   Vrije graafdiepte (app → middleware → database); cyclusbewaking beperkt tot de self-ref-CHECK
   in deze fase (B3).

7. **Contracten generaliseren**: `applicatie_contract` → **`component_contract`**
   (component-FK + contract-FK + relatie-rol; UNIQUE op tenant+component+contract). Gedrag,
   rol-catalogus en UI-patronen uit ADR-020 ongewijzigd; élk component kan contracten dragen
   (Oracle-licentie op de database; Squit-contract op de applicatie).

### Configuratie — componentcatalogus (patroon ADR-019/020)

8. Twee nieuwe platform-brede catalogus-dimensies: **`componenttype`** (default-set, besloten:
   `applicatie`, `database`, `applicatieserver`, `client_software`, `saas_dienst`, `middleware`,
   `fileshare`) en **`structuurrelatie_type`** (default: `draait_op`, `maakt_deel_uit_van`).
   Vorm: eigen tabel `componentconfig_optie(dimensie, optie_sleutel, label, volgorde, actief)`
   + `PlatformEntiteit.COMPONENTCONFIG` als **ADR-012 Addendum C** (rechten identiek aan
   Addendum B; geen V) + beheer-UI naast de contractcatalogus (B2). Het type `applicatie` is
   een **systeem-sleutel**: niet deactiveerbaar (gekoppeld aan het subtype-mechanisme); de
   overige typen zijn vrij beheerbaar.

### UI — applicatie-taal primair, technische laag opt-in

9. De bestaande applicatie-navigatie, -lijst en -detail blijven het primaire perspectief
   (terminologie ongewijzigd); een applicatie aanmaken blijft één handeling (service maakt
   component + subtype atomair). Nieuw: (a) nav-item **Componenten** voor de technische laag
   (lijst/detail van alle componenten, gefilterd op type); (b) sectie **"Opbouw / draait op"**
   in ApplicatieDetail (structuurrelaties beheren, ZoekSelect voor de doel-component);
   (c) de Contracten-sectie verschijnt op élk component-detail (zelfde component-mechanisme).
   Opt-in diepte: een tenant die alleen applicaties inventariseert merkt niets van de
   technische laag.

10. **Impactanalyse** als afgeleide, read-only view (latere fase binnen dit blok): vanaf een
    component de afhankelijke applicaties via de structuurgraaf, met hun lifecycle/blokkade-
    status en contracten — geen schrijfacties, geen engine-koppeling.

### Herfundering (pre-productie)

11. Migratie **`0006_component_herfundering`**: herfundeert het schema direct naar het
    doelmodel (component + applicatie-subtype + geherankerde FK's + `component_structuur` +
    `component_contract` + componentcatalogus). Géén datamigratie; `dev_seed_testdata.py` en
    `seed_contractconfig`-achtige platform-seeds worden bijgewerkt en de dev-DB wordt opnieuw
    geseed. RLS/grants conform de gevestigde patronen (CD040): tenant-tabellen RLS+FORCE op
    `cd_app`; catalogus `cd_app` SELECT-only / `cd_platform` CRUD.

## Gevolgen

- Het logische en technische landschap zijn twee lenzen op één model; de impactanalyse
  ("Y verhuist → welke apps/readiness/contracten") wordt een traversal i.p.v. handwerk.
- Engine, checklists en scores: semantisch ongewijzigd; alleen de buitenring (graaf, contracten)
  herankert.
- ADR-020-functionaliteit blijft volledig; alleen het anker wordt generieker.
- Eenmalig: dev-DB wordt opnieuw geseed; lopende handmatige dev-invoer gaat verloren (geaccepteerd).

## Beslissingen (alle besloten — CD006-sessie)

- **B1 · Datatypes & gebruikersgroepen — BESLOTEN: blijven aan `applicatie`.** Functioneel zijn
  het inventarisgegevens van de applicatie; verplaatsen naar component kan later additief als de
  praktijk erom vraagt (bv. datatypes op een database-component).
- **B2 · Catalogus-vorm — BESLOTEN: eigen `componentconfig_optie` + Addendum C** (consistent,
  klein). De bestaande contractcatalogus-tabel blijft ongemoeid.
- **B3 · Cyclusbewaking structuurrelatie — BESLOTEN: alleen self-ref-CHECK.** Een cyclus in
  registratieve data is onzinnig maar onschadelijk; service-side padbewaking is een latere
  verfijning (registreren in OPVOLGPUNTEN).
- **B4 · `leverancier`-vrije-tekstveld — BESLOTEN: verhuist mee naar `component`** als
  registratieve aantekening (het register is de structurele waarheid).
- **B5 · Seed — BESLOTEN: bestaande app↔app-koppelingen blijven; de nieuwe seed voegt een
  technische laag toe** (o.a. een gedeelde Oracle-database-component onder Belastingsysteem +
  Financieel, conform het CD046-landschap) zodat structuurrelatie en impactanalyse
  demonstreerbaar zijn.

## Niet in scope

- Checklists/lifecycle voor niet-applicatie-typen (nieuw subtype = nieuw ADR).
- Cyclus-/diepte-algoritmiek op de graaf (B3); kwantitatieve impact-scoring.
- CMDB-ambities (configuratie-items, versies, baselines).
- Migratiepaden voor bestaande data (pre-productie; expliciet eenmalig).
- Auditing (ADR-006 volgt ná dit blok, op het definitieve model).

## Alternatieven overwogen

- **Platte typeloze component-tabel** (alles conditioneel aan type): verworpen — de
  subtype-grens wordt conventie en de engine-semantiek erodeert.
- **`applicatiecomponent` als child-tabel onder applicatie**: verworpen — lost de
  graaf-generalisatie (koppelingen/contracten op elk niveau) niet op.
- **Eén relatiesoort voor uitwisseling én opbouw**: verworpen — verschillende velden,
  verschillende vragen, verschillende overzichten; samenvoegen dwingt conventie-misbruik van
  richting/protocol af (functionele verdieping in de sessie).
- **Strangler-/plateau-migratie**: verworpen — over-engineering zonder productiedata;
  herfunderen + herseeden is korter en schoner (besluit Bert).

## Realisatienotitie — shared-PK (CD051)

Het kernmodel hierboven beschrijft het subtype als een 1-op-1 met een eigen `component_id`-FK.
De **realisatie koos Optie 2: shared-PK** (class-table inheritance): `applicatie.id` ís tegelijk
de primaire sleutel **én** de FK naar `component.id` (zelfde waarde — er is geen aparte
`component_id`-kolom). Voordeel: bestaande API-responsen blijven byte-compatibel doordat
`Applicatie` **read-only proxy-properties** heeft (`naam`/`hostingmodel`/`eigenaar_*`/
`leverancier`/`beschrijving` → de component), en de relatie `Applicatie.component` is
`lazy="joined"`. Dit is de gerealiseerde norm; zie complidata-backend "V007-patronen"
(subtype-patroon).

## Wijziging W1 (CD054b) — verenigde Componenten-UI

Besluit 9 (UI-perspectief) herzien op grond van een ontwerp-bevinding tijdens de
walkthrough. De tenant-UI hanteert nu één **verenigde Componenten-ingang**:

- **Menu-sanering**: het aparte menu-item "Applicaties" vervalt. "Componenten" is de
  enige ingang; "alle applicaties" = het typefilter Applicatie. De route `/applicaties`
  (lijst) redirect naar de Componenten-lijst met `type=applicatie`; het detail
  `/applicaties/:id` (ApplicatieDetail) blijft de rijke subtype-view.
- **Convergente aanmaak**: een component aanmaken met type `applicatie` wordt niet langer
  geweigerd, maar maakt atomair het applicatie-subtype met defaults (`lifecycle=concept`,
  `migratiepad=onbekend`, `complexiteit/prioriteit=midden`) via dezelfde service-kern —
  één implementatie, twee routes. Verwijderen van een subtype via het component-pad
  delegeert naar het applicatie-delete-pad (engine-kinderen cascaden; een onderlegger-
  relatie blokkeert met 409 `IN_GEBRUIK`). Het TYPE wijzigen van/naar `applicatie` blijft
  beschermd (422 `SUBTYPE_BESCHERMD`) — nu de enige plek waar die bescherming leeft.
- **Besturingskolommen**: de verenigde lijst toont Eigenaar/Complexiteit/Prioriteit/Status
  via een LEFT JOIN op het subtype — gevuld voor checklist-dragende typen, "—" voor de rest.

Checklist-per-componenttype (beoordelingsprofielen voor niet-applicatie-typen) volgt als
eigen ontwerpblok in **ADR-022** en valt buiten deze wijziging.
