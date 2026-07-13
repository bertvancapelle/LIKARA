# Marktverkenning — wie doet dit al, en hoe goed?

| | |
|---|---|
| **Opdracht** | LI039-marktverkenning-concurrenten (onderzoek; geen code gewijzigd, geen commit) |
| **Datum** | 2026-07-13 |
| **Methode** | Webonderzoek (drie parallelle onderzoekssporen: VNG Softwarecatalogus · Nederlandse spelers · internationale APM-tools), elke bevinding gemarkeerd **[FEIT]** (documentatie/prijslijst/handleiding/officiële bron, met URL) of **[CLAIM]** (marketing/interpretatie). "Onbekend" is een geldig antwoord. |
| **Meetlint** | De zeven LIKARA-uitgangspunten: 1 bedrijfsfunctie-as · 2 GEMMA meegeleverd+gezaghebbend · 3 snel eerste inzicht · 4 gat als eerste-klas uitkomst · 5 gemaakt voor de begeleide sessie · 6 prijs/schaal passend bij 40k-gemeente · 7 impactvraag beantwoordbaar |

**Samenvatting in drie zinnen.** Het *concept* (applicaties aan een capability-as, gaten/overlap zichtbaar) is internationaal categoriestandaard en dus niet uniek; wat níémand aantoonbaar levert is de combinatie GEMMA-gecureerd + sessiewerkvorm + gemeente-passende prijs. De zwaarste bestaande voorziening — de gratis VNG Softwarecatalogus — hangt applicaties op aan *referentiecomponenten*, niet aan bedrijfsfuncties, kent geen gap-/overlap-bevindingen en geen sessieworkflow, maar wordt momenteel herbouwd op een datamodel dat de bedrijfsfunctie wél kan dragen. De reële concurrentie zit niet bij LeanIX/Ardoq maar in Nederland: de gratis VNG-route, BlueDolphin en Mavim.

---

## A. De VNG-Softwarecatalogus (softwarecatalogus.nl)

### A1. Wat registreert hij vandaag?
- [FEIT] **Leverancier → pakket → pakketversie** met functionaliteit, ondersteunde standaarden en productplanning ([hoe-werkt-de-catalogus](https://www.softwarecatalogus.nl/hoe-werkt-de-catalogus)).
- [FEIT] **Pakket ↔ GEMMA-referentiecomponent** is de kernrelatie: "de verbinding tussen het softwareaanbod van leveranciers en het softwaregebruik door gemeenten" ([gemmaonline](https://www.gemmaonline.nl/wiki/Referentiecomponenten_en_bedrijfsfuncties), [referentiecomponenten](https://www.softwarecatalogus.nl/referentiecomponenten)).
- [FEIT] **Gemeente ↔ pakketversie met levenscyclus** (in productie / gepland / uit te faseren / uitgefaseerd) ([beheerdershandleiding](https://www.softwarecatalogus.nl/node/13714)).
- [FEIT] **Koppelingen tussen pakketten** en met Landelijke Voorzieningen: richting van de gegevensstroom, standaard vs. maatwerk, status, technische toelichting (zelfde handleiding). Geëxporteerd als ArchiMate-**flow**-relaties ([AMEFF-export](https://www.gemmaonline.nl/index.php/Softwarecatalogus_AMEFF_export)).
- [FEIT] **Contractdata zit er vandaag NIET in**; in het datamodel van de **herbouw** wél (`Contract`, plus `Kwetsbaarheid` (CVE) en `Review`) ([OpenAPI-spec herbouw-repo](https://github.com/VNG-Realisatie/Softwarecatalogus), [docs](https://vng-realisatie.github.io/Softwarecatalogus/docs/intro)).

### A2. Verband met bedrijfsfuncties / gap-inzicht
- [FEIT] De koppeling referentiecomponent ↔ bedrijfsfunctie leeft **in het GEMMA-model op GEMMA Online, niet in de catalogus**: "referentiecomponenten zijn verbonden met applicatieservices; die worden gebruikt door bedrijfsfuncties" ([gemmaonline](https://www.gemmaonline.nl/wiki/Referentiecomponenten_en_bedrijfsfuncties)). Geen enkele handleiding noemt bedrijfsfuncties als registratie- of weergave-as.
- [FEIT] **Geen gap-functie gedocumenteerd** ("toon welke functies niet ondersteund worden" bestaat nergens in de documentatie). [CLAIM] Op de automatische GEMMA-landschapsplot zijn lege referentiecomponenten in beginsel visueel afleesbaar, maar dat wordt nergens als bevinding of rapportage aangeboden.
- [FEIT] Het herbouw-datamodel kent `Bedrijfsfunctie` wél als `ReferentieConcept`-type — het nieuwe fundament kán de functie-as dragen; in de backlog is over functie-koppeling of gap-analyse níéts gevonden ([issues](https://github.com/VNG-Realisatie/softwarecatalogus/issues)).

### A3. Afhankelijkheden
- [FEIT] Ja — koppelingen zijn eerste-klas objecten (richting, type, status), vergelijkbaar met andere gemeenten ([hoe-werkt-de-catalogus](https://www.softwarecatalogus.nl/hoe-werkt-de-catalogus)). Geen impactanalyse-functie ("wat raakt het als dit verdwijnt") gedocumenteerd → onbekend.

### A4. Databeheer en actualiteit
- [FEIT] Drieledig: **gemeente = bronhouder** van het eigen landschap ([Binnenlands Bestuur 2016](https://www.binnenlandsbestuur.nl/digitaal/leveranciers-helpen-gemeenten-met-juiste-registratie-software)); **leveranciers** beheren productdata onder convenant (minimaal per kwartaal actualiseren; "KING controleert dit niet" — [FAQ](https://www.softwarecatalogus.nl/veel-gestelde-vragen)); **VNG** beheert stamgegevens en exploiteert (GGU-gefinancierd).
- [FEIT] **Actualiteit is een gedocumenteerde zwakte**: GEMMA-vragenlijst 2019 — "onvoldoende actueel", "SWC is geen bron en wordt daarom niet onderhouden" ([PDF](https://www.gemmaonline.nl/images/gemma/f/f1/Open_antwoorden_op_de_vragenlijst_05032019.pdf); exacte formulering indicatief); gebruikersonderzoek 2021 (147 respondenten) — "informatie van leveranciers is niet bijgewerkt" ([gebruikersonderzoek](https://www.softwarecatalogus.nl/gebruikersonderzoek%202021)).
- [FEIT] Ingelogde gemeenten per jaar (homepage-teller): 2023: 201 · 2024: 215 · 2025: 199 — [CLAIM] grofweg 60% van de 342 gemeenten logt jaarlijks minstens één keer in.

### A5. Roadmap
- [FEIT] Project **"Vernieuwing Softwarecatalogus"** loopt (aankondiging okt. 2024; publieke repo met PvE, sprintnotulen jan–jun 2025, testverslag sept. 2025; gebouwd op Common Ground-bouwstenen OpenCatalogi/OpenRegister/OpenConnector; "de basis blijft intact"; REST-API met `/model`, `/elements`, `/relations`, `/views`) ([repo](https://github.com/VNG-Realisatie/Softwarecatalogus)). Go-live: onbekend.
- [FEIT] **Geen enkele gevonden publicatie noemt functie-koppeling, gap-analyse of landschapsvisualisatie op functieniveau als doel van de vernieuwing.** Geen aanwijzing voor uitfasering.
- Context: het huidige platform draait op verouderd Drupal 7; er liep in 2024 een marktconsultatie ([nieuws](https://www.softwarecatalogus.nl/nieuws), [EU-Supply](https://eu.eu-supply.com/ctm/Supplier/PublicPurchase/407913/0/0)).

### A6. Export/API — herbruikbaarheid
- [FEIT] **Publieke CSV-export zonder login** (live geverifieerd 13-7-2026): volledig landelijk aanbod incl. referentiecomponent-mappings (UUID's) en aantallen gebruikende gemeenten ([export-URL](https://www.softwarecatalogus.nl/swc/exports/csv/leveranciers_pakketten)).
- [FEIT] **AMEFF-export van het eigen gemeentelijke landschap** (pakketten + koppelingen in één model), importeerbaar in Archi, Bizzdesign, Mavim, Sparx, Dragon1, ValueBlue ([handleiding architectuurtools](https://www.softwarecatalogus.nl/Handleiding%20koppeling%20architectuurtools)). Een derde tool kan die data dus hergebruiken.

### A7. Het scherpe oordeel: hoeveel werk zou het VNG kosten?
Feitelijk onderbouwd: dit is **geen "één scherm erbij" maar een ander producttype** — de catalogus is een landelijk registratie-/vergelijkingsplatform (marktoriëntatie, inkoop), geen analyse-instrument; er ontbreken drie lagen tegelijk (functie-as, gap/overlap-bevindingen, sessieworkflow) en geen daarvan staat op de gevonden roadmap. **Eerlijke kanttekening [SPECULATIE, als zodanig gemarkeerd in het brononderzoek]:** het ruwe materiaal bestaat volledig en machineleesbaar (applicatie→referentiecomponent in de catalogus + referentiecomponent→functie in het GEMMA-model — dekking van die laatste schakel: ~49%, zie `Verkenning-GEMMA-context-V040.md`). VNG zóú een gap-view relatief goedkoop kunnen toevoegen omdat het nieuwe datamodel het draagt; daarvoor is tot juli 2026 geen enkele publieke aanwijzing gevonden. Het risico is dus niet wat de catalogus vandaag kan, maar een toekomstige VNG-keuze om dit collectief gratis te doen.

---

## B. Nederlandse spelers

### B1. Dragon1
- [FEIT] SaaS EA-/modelleerplatform; APM-propositie voor gemeenten bestaat, maar de productpagina's beschrijven geen bedrijfsfunctie-koppeling en geen gap/overlap-weergave ([APM gemeenten](https://www.dragon1.com/watch/459571/applicatie-portfolio-management-landschap-gemeenten)); GEMMA als voorbeeldplaat/tutorial, geen aangetoond meegeleverd model ([GEMMA-plaat](https://www.dragon1.com/watch/140715/gemma-applicatielandschap-lokale-overheid-gemeente)).
- [FEIT] Prijzen publiek: PRO €4.795/jr (1 editor) · BUSINESS €47.500/jr (15) · ENTERPRISE €92.000/jr ([pricing](https://www.dragon1.com/pricing)). **4 gemeenten in productie** volgens de Softwarecatalogus ([pakketpagina](https://www.softwarecatalogus.nl/pakket/dragon1)).

### B2. Mavim
- [FEIT] Levert een **kant-en-klaar "GEMMA Architectuur framework"** en importeert automatisch uit de Softwarecatalogus (ArchiMate/AMEFF) ([framework](https://nl.mavim.com/mavim-platform/frameworks/gemma-architectuur-framework), [SWC-pakket](https://www.softwarecatalogus.nl/pakket/mavim-gemma-enterprise-architectuur-volgens-archimate)) — de sterkste GEMMA-integratie onder de commerciële tools. **4 gemeenten in productie** met dat pakket [FEIT, zelfde pagina].
- [FEIT] Kern is proces-/Visio-georiënteerd platform ([GetApp](https://www.getapp.com/operations-management-software/a/mavim/)); prijzen niet publiek. Gap-als-bevinding: onbekend.

### B3. Bizzdesign (Enterprise Studio + Horizzon)
- [FEIT] ArchiMate-suite met portfolio-/scenario-analyse; UK G-Cloud prijsband **£5–£3.640 per licentie/jr** (viewer t/m modeler; NL-prijzen niet publiek) ([G-Cloud](https://www.applytosupply.digitalmarketplace.service.gov.uk/g-cloud/services/621609902603164)). GEMMA importeerbaar, niet meegeleverd ([gemmaonline](https://www.gemmaonline.nl/wiki/Hulpmiddelen_voor_de_architect)). Gemeentereferentie: Westland (via bureau MezzaLama) ([case](https://www.mezzalama.nl/voor-de-overheid/referenties/start-enterprise-architectuur-gemeente-westland/)).
- [FEIT] Marktconsolidatie: Bizzdesign nam MEGA (HOPEX) én Alfabet over — drie enterprise-EA-producten onder één (Nederlands) dak ([persbericht](https://bizzdesign.com/press-releases/bizzdesign-adds-alfabet-business-following-successful-closing-mega-international), [Forrester](https://www.forrester.com/blogs/the-enterprise-architecture-tool-market-starts-2025-with-a-notable-merger/)).

### B4. BlueDolphin (ValueBlue) — dichtstbijzijnde commerciële concurrent
- [FEIT] Nederlandse tool met aantoonbare gemeenteklanten: **Haarlemmermeer** ("met ruim honderd applicaties minder toe" na ordening — [Computable 2017](https://www.computable.nl/2017/06/12/bluedolphin-ordent-applicaties-haarlemmermeer/)), **Utrecht** ([presentatie](https://docplayer.nl/127955924-Gemeente-utrecht-bluedolphin-hier-komt-tekst-gebruikerservaringen-praktische-toepassing-hier-komt-ook-tekst-utrecht-nl.html)), Amsterdam genoemd ([Dutch IT Leaders](https://www.dutchitleaders.nl/news/729034/valueblue-wordt-bluedolphin-architectuur-als-cockpit-voor-ai)); [CLAIM] partner: "~100 organisaties waaronder een groot aantal gemeenten".
- [FEIT] GEMMA-import officieel ondersteund (Softwarecatalogus-toollijst); prijzen niet publiek (tiers op aantal modelers, viewers gratis — [pricing](https://bluedolphin.io/pricing/)). [CLAIM] Reviews: lage drempel voor niet-architecten. Gap-als-bevinding: onbekend; het blijft een repository die de organisatie zelf vult, geen sessiewerkvorm [FEIT: licentiemodel].

### B5. CMDB/ITSM-hoek: TOPdesk, Ultimo, Planon
- [FEIT] TOPdesk registreert het **technisch/administratieve** landschap (CI's, licenties, afhankelijkheden tussen assets — [docs](https://docs.topdesk.com/nl/configuratiebeheer.html)); de functie-/proceskoppeling gebeurt aantoonbaar búiten TOPdesk (het bestaan van de Mavim↔TOPdesk-integratie bewijst dat — [SWC](https://www.softwarecatalogus.nl/pakket/mavim-topdesk-asset-management-api)). Ultimo (fysieke assets) en Planon (vastgoed/IWMS) zitten in een ander domein [FEIT: productpagina's]. **Geen van drieën registreert het logische landschap** — wel relevant als *databron* (de applicatielijst zit vaak al in de CMDB).

### B6. Advies-/implementatiepartijen: het gereedschap
- [FEIT] **Telengy**: leunt op de Softwarecatalogus + GEMMA (case Lochem; historisch verweven met de catalogus) — geen eigen tool ([case](https://www.telengy.nl/actueel/grip-op-informatie-lochem/)).
- [FEIT] **M&I/Partners**: adviseert generiek "software voor architectuur, €25.000/jr" + 2 fte architecten — geen eigen tool ([modelgemeente](https://mxi.nl/modelgemeente/algemene-ontwikkelingen/werken-onder-architectuur)).
- [FEIT] **Quarant**: stappenplan/methode, geen tooling genoemd ([blog](https://www.quarant.nl/enterprise-architectuur-gemeenten/)). **PBLQ / VKA / BMC**: mensgedreven advies; tooling onbekend.
- [FEIT] **Native Consulting** is het bewijsstuk: stapte expliciet over van **Excel/Visio** naar BlueDolphin als partner-tool en verkoopt de inrichting als dienst ([nieuwsbericht](https://www.nativeconsulting.nl/nieuws/werken-onder-architectuur-met-bluedolphin/)). Dit is de enige gevonden expliciete bevestiging dat Excel/Visio de gangbare adviespraktijk was.
- [CLAIM] **Patroon**: adviesbureaus hebben vrijwel nooit eigen tooling; hun gereedschap is de gratis catalogus, een partner-tool of Excel/Visio. De combinatie "consultant + sessiegerichte eigen tool" is nergens aangetroffen. **De werkelijke concurrent van LIKARA aan de sessietafel is dus Excel/Visio/PowerPoint** (deels [FEIT] via Native, verder [CLAIM]).

### B7. Gemeentelijke/SSC-bouwsels
- [FEIT] **OpenCatalogi** (Rotterdam/Common Ground, open source): catalogus van beschikbare componenten (aanbodzijde), geen functie-as of gap-/impactanalyse ([GitHub](https://github.com/OpenCatalogi), [Dimpact](https://www.dimpact.nl/nieuws/opencatalogi-snel-zicht-op-beschikbare-common-ground-componenten/)).
- [FEIT] **Archi + GEMMA-export** is de de-facto gratis route: eigen landschap uit de catalogus in het gratis Archi, incl. views op bedrijfsfuncties ("RD02 Bedrijfsfuncties ruimtelijk domein met referentiecomponenten" — [voorbeeld](https://www.softwarecatalogus.nl/node/30890)). Architectentool: handwerk, geen analytics, geen sessiewerkvorm.
- [FEIT] **Gemeentelijk Gegevensmodel** (Delft, GitHub): gedeeld gegevensmodel, geen landschapstool ([repo](https://github.com/Gemeente-Delft/Gemeentelijk-Gegevensmodel/blob/master/README.md)).

---

## C. Internationale APM-/capability-tools

**Vooraf [FEIT]:** capability-map + applicatiekoppeling + heatmap + gap/overlap is gedocumenteerde kernfunctionaliteit van de hele categorie — het concept is hier niet uniek. **Geen van de internationale leiders staat in de officiële GEMMA-toollijst** (die kent alleen Archi, Bizzdesign, Mavim, Sparx, Dragon1, ValueBlue — [handleiding](https://www.softwarecatalogus.nl/Handleiding%20koppeling%20architectuurtools)). Voor geen van de zes internationale spelers is een NL-gemeentereferentie gevonden (onbekend ≠ afwezig; TenderNed is van buitenaf slecht doorzoekbaar).

| Tool | Gap/overlap | Prijs | Drempel | GEMMA | Kern-oordeel |
|---|---|---|---|---|---|
| **LeanIX (SAP)** | [FEIT] capability-heatmap; lege capability zichtbaar; overlap = rationalisatie-kern ([blog](https://www.leanix.net/en/blog/business-capability-mapping)) | [FEIT] per applicatie, onbeperkt users; bedragen niet publiek ([pricing](https://www.leanix.net/en/enterprise-architecture/pricing)); [CLAIM] "too high for smaller firms" | [CLAIM] 3–4 mnd; partner: 6–10 wkn gevulde portfolio | ✗ geen treffer | Enterprise-APM; concept volledig afgedekt, doelgroep niet |
| **Ardoq** | [FEIT] heatmaps, overlap-detectie, "pinpoint gaps" ([help](https://help.ardoq.com/en/articles/44051-getting-started-with-business-capability-modeling)) | [FEIT] per applicatie, geen bedragen ([plans](https://www.ardoq.com/plans)); [FEIT] categorie loopt tot "six-figure annual" ([eigen blog](https://www.ardoq.com/blog/enterprise-architecture-cost-in-2025)) | onbekend; graph-metamodel = EA-competentie [CLAIM] | ✗ | idem |
| **Alfabet** (nu Bizzdesign) | [CLAIM] capability-gaps/heatmaps (partnertekst) | [FEIT] US-prijslijst-anker $62.771/jr voor één module ([Carahsoft](https://static.carahsoft.com/concrete/files/2716/0026/0949/Software_AG_SLG__EDU_Price_List_-_Software_Licenses_-_Subscription.pdf)); [CLAIM] FastLane ~$30k instap | 12 mnd-klasse [CLAIM]; EA-team vereist | ✗ | Zwaar enterprise |
| **MEGA HOPEX** (nu Bizzdesign) | [CLAIM] "capability maps, heatmaps, gap analyses" prebuilt ([productpagina](https://bizzdesign.com/transformation-suite/hopex)) | [FEIT] custom quote; [CLAIM] "expensive" (Peerspot) | enterprise-platform | ✗ | idem |
| **Orbus iServer** | [FEIT] capability mapping + gap-analyse gedocumenteerd ([wiki](https://www.orbussoftware.com/resources/wiki/article/business-capability-mapping)) | [FEIT] geen bedragen; [CLAIM] verouderd anker ~$36k/100 users | M365-ecosysteem verlaagt drempel [CLAIM] | ✗ | idem |
| **Avolution ABACUS** | [CLAIM] capability-heatmaps standaard | [FEIT] Foundation-tier "small teams", bedragen niet publiek ([pricing](https://www.avolutionsoftware.com/abacus/pricing/)) | onbekend | ✗ | idem |
| **Sparx EA** | ✗ modelleertool, geen APM-analytics [FEIT] | [FEIT] **$245–750 perpetual per licentie** ([prijzen](https://www.sparxsystems.us/sparx-license-pricing/enterprise-architect/)) — goedkoopste commerciële optie | hoge expertise-drempel [CLAIM] | ✓ gedeeltelijk: officiële AMEFF-import, in GEMMA-toollijst [FEIT] | Goedkoop maar leeg vel + architect vereist |
| **Archi** | ✗ geen analytics [FEIT: featurelijst] | [FEIT] gratis ([site](https://www.archimatetool.com/)) | ArchiMate-kennis vereist | ✓✓ dé GEMMA-huistool: VNG bouwt het model zelf in Archi ([repo](https://github.com/VNG-Realisatie/GEMMA-Archi-repository)); Nijmegen-referentie [FEIT] | De gratis route; handwerk |
| **QualiWare** | [CLAIM] capability management | [FEIT] geen publieke prijs | onbekend | ✗ | Geen NL-voet gevonden |
| **Essential (open source)** | [FEIT] gap analyses prebuilt; capability-as is de ruggengraat ([site](https://enterprise-architecture.org/products/essential-open-source/)) | [FEIT] OS gratis (self-host); SaaS **vanaf $24.999/jr** ([pricing](https://enterprise-architecture.org/products/pricing-comparison/)) | zelf hosten/inrichten; consultancy-DNA [CLAIM] | ✗ | Conceptueel het dichtst bij LIKARA's analytisch model, zonder GEMMA/NL |

**Lichte variant voor een 40k-gemeente?** Niet gevonden bij de enterprise-spelers (alles contact-sales; gevonden prijsankers $25k–63k/jr). De enige "lichte" routes zijn Sparx ($245–750, maar expertise-drempel) en Archi/Essential-OS (gratis, maar handwerk + architect). **GEMMA out of the box:** alleen via de Archi/AMEFF-route en de NL-spelers; geen enkele internationale APM-leider ondersteunt het aantoonbaar.

---

## D. De eerlijke vergelijking

### D1. Matrix — kandidaten × de zeven punten

Legenda: ✓ / **G** = gedeeltelijk / ✗ / **?** = onbekend.

| Kandidaat | 1 functie-as | 2 GEMMA mee | 3 snel inzicht | 4 gat = bevinding | 5 begeleide sessie | 6 prijs 40k | 7 impact |
|---|---|---|---|---|---|---|---|
| **VNG Softwarecatalogus** | G (referentiecomponent, geen functie) | ✓ (ís de bron) | G (na zelf-invoer) | G/? (impliciet op plot) | ✗ | ✓ (gratis) | G (koppelingen wel, analyse ?) |
| **Archi + GEMMA-export** | G (views bestaan) | ✓ | ✗ (handwerk) | ✗ | ✗ | ✓ gratis / ✗ expertise | G |
| **BlueDolphin** | G | G (import) | G | ? | ✗ | ? | ✓ [CLAIM] |
| **Mavim** | G (proces-kern) | ✓ (framework) | ✗ | ? | ✗ | ? | G |
| **Bizzdesign ES/Horizzon** | G | G (import) | ✗ | ? | ✗ | ✗ | G |
| **Dragon1** | ✗ | G | ✗ | ? | ✗ | ✗ (€47,5k team) | G |
| **TOPdesk/Ultimo/Planon** | ✗ (technisch) | ✗ | n.v.t. | ✗ | ✗ | n.v.t. | ✗ |
| **Adviesbureaus (Excel/Visio)** | wisselend | ✗ | G (sessie is hun vak) | mensafhankelijk | ✓ (sessie = product, tool ontbreekt) | uurtarief | mensafhankelijk |
| **LeanIX** | ✓ | ✗ | G | ✓ | ✗ | ?/✗ | ✓ |
| **Ardoq** | ✓ | ✗ | ? | ✓ | ✗ | ? | ✓ |
| **Alfabet / HOPEX** | ✓ | ✗ | ✗ | G/✓ [CLAIM] | ✗ | ✗ | ✓ |
| **Orbus / Avolution** | ✓ | ✗ | ? | ✓/G | ✗ | ? | ✓ |
| **Sparx EA** | G | G (import) | ✗ | ✗ | ✗ | ✓ prijs / ✗ expertise | G |
| **Essential (OS)** | ✓ | ✗ | G | ✓ | G (consultancy-DNA) | ✓ OS / ✗ SaaS | ✓ |
| **QualiWare** | ✓ | ✗ | ? | ? | ✗ | ? | ✓ |
| **OpenCatalogi** | ✗ | ✗ | ? | ✗ | ✗ | ✓ (OSS) | ✗ |

### D2. Waar zit de witte vlek — en is die groot genoeg?
**Feitelijk:** geen enkele onderzochte kandidaat scoort ✓ op punten 4+5+6 tegelijk, en **punt 5 (gemaakt voor de begeleide sessie) scoort bij letterlijk niemand ✓** behalve bij de adviesbureaus — die juist géén tool hebben. De witte vlek is dus niet het concept (dat is categoriestandaard, zie C) maar de **combinatie in de Nederlandse gemeentecontext**: bedrijfsfunctie als primaire as (het hele NL-ecosysteem hangt op de referentiecomponent), GEMMA gecureerd meegeleverd, sessiewerkvorm, en een prijs die bij 40.000 inwoners past (dat prijspunt is bij álle commerciële spelers onbekend of aantoonbaar enterprise). Of die vlek "groot genoeg" is, is geen onderzoeksvraag maar een ondernemersoordeel; het onderzoek levert wél: de behoefte bestaat aantoonbaar (Native's overstap van Excel/Visio naar tooling; Haarlemmermeer's −100 applicaties; M&I budgetteert €25k/jr + 2 fte voor wat een 40k-gemeente meestal niet heeft).

### D3. Wie kan LIKARA het snelst overbodig maken?
1. **VNG** — de vernieuwde Softwarecatalogus staat op een datamodel dat de bedrijfsfunctie al kent, wordt collectief gefinancierd (gratis voor gemeenten) en heeft de data al. Wat ervoor nodig zou zijn: een functie-projectielaag (de GEMMA-keten referentiecomponent→functie dekt ~49%, zie `Verkenning-GEMMA-context-V040.md`) + gap-views + een analyse-UX. Er is **geen enkele publieke aanwijzing** dat dit gebeurt — maar het is de kortste route van een bestaande speler.
2. **BlueDolphin** — heeft de gemeenteklanten, de GEMMA-import en (per 2025/2026) een herpositionering; zou een sessie-/gap-propositie kunnen toevoegen. Wat ontbreekt: functie-as als primaire ophanging, sessiewerkvorm, transparante gemeente-prijs.
3. **Mavim** — sterkste GEMMA-integratie, maar proces-DNA en slechts 4 gemeenten op het GEMMA-pakket [FEIT].
4. **Een adviesbureau dat zelf gaat bouwen** — zij hebben de sessies en de klantrelatie; Native bewijst dat bureaus tooling-honger hebben (ze kozen partner-tooling, niet zelfbouw).

### D4. Wat doet niemand wat LIKARA wél doet?
Eerlijk gesplitst:
- **Het gat als bevinding**: in de **NL-gemeentemarkt bij niemand aangetoond** (overal ? of impliciet); **internationaal wél** — LeanIX/Ardoq/Orbus/Essential documenteren lege capabilities en gap-analyse als kernfunctie. Het onderscheid is daar dus doelgroep/drempel, niet concept.
- **Meervoudige plaatsing** (één registratie op meerdere plekken, met kenmerken per plaatsing): in APM-tools bestaat de many-to-many app↔capability-relatie standaard [FEIT: categoriefunctie]; als gekwalificeerd registratie-feit met eigen kenmerken per plaatsing is het bij geen enkele kandidaat gedocumenteerd aangetroffen (?, geen bewijs van afwezigheid).
- **Grof-dan-fijn registreren** (eerst op hoofdfunctie landen, later verfijnen, zonder datamodel-breuk): **bij geen enkele kandidaat als werkvorm gedocumenteerd** — EA-tools zijn modelleertools (alles even fijn, leeg vel), de catalogus is vlak (één niveau referentiecomponenten). Dit is het meest onbetwiste unieke punt uit de toets — met de kanttekening dat afwezigheid van documentatie geen bewijs van afwezigheid is.
- **De sessiewerkvorm als productontwerp**: nergens aangetroffen; overal is de tool een repository die de organisatie zelf vult.

### D5. Wat doet iedereen beter dan LIKARA nu?
- **Visualisatie-volwassenheid**: capability-heatmaps, portfolio-dashboards en rationalisatie-scoring van de APM-categorie zijn jaren verfijnd (LeanIX/Ardoq) — LIKARA's kaart/functieboom is jonger.
- **Data-import en integraties**: de hele NL-keten (Softwarecatalogus-AMEFF → tools) en CMDB-koppelingen (Mavim↔TOPdesk) bestaan al; LIKARA heeft nog geen catalogus-/CMDB-import (het inlees-spoor is pas ontworpen, ADR-043).
- **Vergelijken tussen gemeenten**: de Softwarecatalogus doet dit landelijk en gratis — voor een enkele tenant onbereikbaar.
- **Leveranciers-/marktdata**: de catalogus draagt het aanbod (planning, standaarden, straks CVE's/contracten) — LIKARA registreert alleen de eigen tenant.
- **Onbeperkte gratis viewers** (LeanIX/Ardoq/BlueDolphin-prijsmodel) en volwassen API's/ecosystemen.
- **Standaarden-/koppelvlakkenregister**: GEMMA zelf (via de catalogus en het model) kwalificeert component↔standaard met Verplicht/Aanbevolen — een laag die LIKARA niet heeft (zie ook de GEMMA-contextverkenning, sectie E).

---

## Wat dit betekent voor de koers (beschrijvend — geen aanbeveling)

Het onderzoek verschuift het concurrentiebeeld op drie punten:

1. **De vergelijkingsgroep is niet LeanIX, maar de gratis VNG-route en Excel.** Internationale APM dekt het concept volledig af maar bereikt de 40k-gemeente aantoonbaar niet (prijs, drempel, geen GEMMA). Aan de sessietafel is het werkelijke alternatief vandaag: Softwarecatalogus-registratie + Archi-handwerk + Excel/Visio van het adviesbureau.
2. **De Softwarecatalogus is tegelijk risico én grondstof.** Risico: herbouw op een datamodel dat de functie-as kan dragen, collectief gefinancierd — één VNG-besluit kan de gap-view gratis maken (geen aanwijzing gevonden dat dit gebeurt). Grondstof: publieke CSV + AMEFF-export betekenen dat een gemeente-landschap **voorgevuld** de sessie in kan — precies de "snel eerste inzicht"-belofte. De catalogus is vandaag feitelijk eerder databron/instapkanaal dan concurrent.
3. **Adviesbureaus zijn eerder kanaal dan concurrent.** Ze hebben de sessies en de klantrelatie, aantoonbaar geen eigen tooling, en bewezen tooling-honger (Native→BlueDolphin).

**Open vragen die eruit volgen (voor Bert):**
- Volgt LIKARA de VNG-herbouw actief (go-live onbekend; datamodel draagt de functie-as al — wanneer wordt dat een view)?
- Wordt de Softwarecatalogus-export (CSV/AMEFF) een inlees-bron naast het GEMMA-referentiemodel — en zo ja, hoe verhoudt zich dat tot de ~49%-dekking van de component→functie-keten uit de vorige verkenning?
- Is BlueDolphin benchmark, concurrent of allebei — en wat is hun werkelijke gemeente-prijs (nergens publiek)?
- Positionering richting adviesbureaus: concurrent van hun Excel, of hun gereedschap?
- Prijsstelling: geen enkele commerciële speler publiceert een gemeente-passende prijs — open veld, maar ook: geen referentieprijs om op te ankeren.

**Geen aanbeveling, geen scope-wijziging. Bert beslist.**
