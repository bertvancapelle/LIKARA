# Marktverkenning deel 2 — sluit iemand de ketting? En wat kost BlueDolphin werkelijk?

| | |
|---|---|
| **Opdracht** | LI039-marktverkenning-ketting (onderzoek; geen code gewijzigd, geen commit) |
| **Datum** | 2026-07-13 |
| **Aanvullend op** | `docs/Marktverkenning-concurrenten-V040.md` (deel 1) |
| **Methode** | Webonderzoek in drie parallelle sporen (ketting-toets EA/APM · ServiceNow/ITSM/CMDB · BlueDolphin-kosten). Per bevinding **[FEIT]** (documentatie/metamodel/gunning/case, met URL) of **[CLAIM]** (marketing/reviews/interpretatie). "Onbekend" is een geldig antwoord. |

**De toets-zin:** *"Deze bedrijfsfunctie draait op dit systeem, dat wordt beheerd door die afdeling, geleverd door die partij, onder dat contract dat over acht maanden afloopt — en het raakt deze vier andere systemen."* In één beeld, zonder tweede systeem.

**Samenvatting in drie zinnen.** De hypothese ("niemand overbrugt de naad") houdt grotendeels stand, maar niet volledig: **Alfabet** en **ServiceNow** sluiten de ketting op datamodel-niveau — de eerste via een aparte betaalde Contract-module op een enterprise-platform, de tweede over drie aparte SKU's heen, en bij **geen van beiden bestaat het éne standaardbeeld** dat de toets-zin toont. **BlueDolphin is niet aantoonbaar duur** (geen enkele publieke prijs, historisch maandelijks opzegbaar, zit al bij gemeenten van 27k–46k inwoners) — de werkelijke drempel is daar niet geld maar **inrichting + doorlopend beheer + consultant**, met een gedocumenteerd faalpatroon (Drimmelen) als de borging ontbreekt. De witte vlek verschuift daarmee van "functionaliteit" naar "de ketting-vraag beantwoorden zónder inrichtingsproject en zónder doorlopende beheerlast".

---

## Deel A — Sluit iemand de ketting?

### A1. De slottabel

Legenda: ✓ / **G** = gedeeltelijk / ✗ / **?** = onbekend. "Contract" = contract als entiteit mét looptijd/einddatum/leverancier(/waarde).

| Kandidaat | 1 capability-as | 2 contract | 3 beheerrollen/partijen | 4 afhankelijkheden | 5 ketting in één beeld | 6 standaard of extra? |
|---|---|---|---|---|---|---|
| **Alfabet** (Bizzdesign) | ✓ | **✓** start/einddatum, vendor verplicht, kosten, deliverables→applicatie | **✓** standaard rollenmodel (App Manager, Business/IT Owner, Operations-org) | ✓ information flows | **G** — datamodel volledig in één repository; één gecombineerde view niet aangetoond | contract = **aparte licentie-module** |
| **ServiceNow** | ✓ (capability map, EA/APM) | ✓ (Contract Mgmt: einddatum-signalering, vendors) | ✓ (deels [CLAIM] op veldniveau) | ✓ (CMDB/dependency maps) | **G** — datatechnisch sluitbaar in één platform; het éne beeld bestaat niet (contract is geen CI, verschijnt in geen map) | **drie aparte SKU's** (ITSM + EA/SPM + CMDB-vulling) + configuratie |
| **Ardoq** | ✓ | ✗ standaard — officieel **DIY-recept** mét einddatum/jaarkosten ([helpcenter](https://help.ardoq.com/en/articles/279847-representing-contracts-and-license-agreements-in-ardoq): "There is not, currently, an Ardoq Use Case Solution for representing contracts") | ✓ (Person/Org; Owns→Contract na configuratie) | ✓ | na configuratie plausibel; ✗ out-of-the-box | configuratie (laagste drempel v.d. flexibele metamodellen) |
| **LeanIX** | ✓ | ✗ in het EA-product (zat in apart product SMP; SaaS Discovery "does not provide insight into … contracts" [FEIT]) | ✓ subscriptions + Provider (alleen via IT Component, niet direct aan applicatie [FEIT]) | ✓ (Interface) | **G** — alles behalve het contract | contract = configuratie óf tweede product |
| **Bizzdesign ES/Horizzon** | ✓ | G — ArchiMate-Contract-elément standaard, **zonder** einddatum/waarde-attributen ([spec](https://pubs.opengroup.org/architecture/archimate31-doc/chap08.html)) | ? als standaard | ✓ | ✗ niet standaard | configuratie (metamodel-profielen) |
| **BlueDolphin** | ✓ (ArchiMate) | ✗ standaard; objecttype bestaat, attributen via questionnaires | ? standaard; via questionnaires | ✓ [deels CLAIM] | ✗ niet aangetoond als standaard — zie deel B | configuratie (+ betaalde ITSM-koppeling) |
| **Mavim** | G [CLAIM] | ✗ standaard; topic-model zelf in te richten | G [CLAIM] | G [CLAIM] | ✗; TOPdesk-koppeling = tweede systeem | configuratie (+ integratie) |
| **Dragon1** | ✓ (metamodel kent Function/Capability) | **✗ — Contract komt niet voor in het metamodel** ([metamodel](https://www.dragon1.com/resources/dragon1/enterprise-architecture-meta-model)) | ✗/? | G [CLAIM] | ✗ | maatwerk, mager gedocumenteerd |
| **Orbus** | ✓ (ArchiMate 3.2) | ✗ standaard gevonden; metamodel uitbreidbaar | G [CLAIM: owner/vendor-attribuut] | G [CLAIM] | ✗ niet aangetoond; ServiceNow-Connect wijst naar tweede systeem | configuratie |
| **TOPdesk** | **✗** geen capability-concept ([docs](https://docs.topdesk.com/en/asset-types---templates.html); eigen assettype = maatwerk zonder betekenislaag) | ✓ Contractbeheer & SLM-module: einddatum-waarschuwing, leverancierskaarten ([docs](https://docs.topdesk.com/nl/managen-van-je-dienstverlening-en-leverancierscontracten.html)) | ✓ (leveranciers, budgethouders, behandelaarsgroepen) | ✓ (asset-afhankelijkheden + statuspropagatie) | **✗** — het "waarvóór" ontbreekt als as | contractmodule = aparte module |
| **Ultimo** | ✗ (EAM, fysieke assets) | ✓ contractmodule | ✓ | G | ✗ | n.v.t. |
| **Planon** | ✗ (vastgoed/IWMS) | ✓ (vastgoedcontracten) | ✓ | ✗ | ✗ | n.v.t. |

### A2. ServiceNow — de hoofdverdachte, uitgeschreven

- [FEIT] **De capability-as is echt**: business capabilities met hiërarchie en capability map zijn eersteklas concepten in ServiceNow EA (vh. APM); business applications worden aan capabilities toegewezen ([docs](https://www.servicenow.com/docs/r/application-portfolio-management/business-capability.html)). De hypothese-stelling "ITSM-tools kennen geen bedrijfsfunctie" is voor ServiceNow **onjuist**.
- [FEIT] **Contractbeheer is volwaardig**: levenscyclus, einddatums met nachtelijke expiratie-notificatie, vendors; contracten koppelbaar aan CI's via `ast_contract_instance` ([docs](https://www.servicenow.com/docs/r/it-service-management/contract-management/c_ContractManagement.html)).
- [FEIT+CLAIM] **Maar het éne beeld bestaat niet standaard**: contract is geen CI en verschijnt daarom **niet** in de CI-/dependency-/BSM-maps ([community](https://www.servicenow.com/community/spm-forum/relationship-between-the-contract-and-the-ci/m-p/1030283)); contractdata aan business applications is "not visible within the Technology Portfolio"; het Application 360-dashboard toont performance/kosten, geen contracten; TCO vergt zelfs een externe ITFM-bron [FEIT, docs]. De toets-zin vergt een **custom dashboard over drie modules heen** = configuratie.
- [FEIT] **Drie aparte SKU's** (ITSM voor contracten; EA/SPM voor capabilities; CMDB-vulling via discovery of handwerk); prijzen niet publiek. [CLAIM] ITSM-indicaties $70–200/fulfiller/mnd; implementatie 3–5× licentie.
- [FEIT] **Het enige harde NL-gemeente-datapunt**: gemeente Utrecht (~370k inw.) — ServiceNow-platformdiensten (ITSM+SecOps) gegund voor **€1.845.245 over drie jaar**, exclusief licenties ([gunning](https://www.tender.app/aanbestedingen/vrijwillige-transparantie-servicenow-platform)). [CLAIM] Geen NL-gemeente van ±40k met ServiceNow gevonden; zelfs een 73k-gemeente (Almelo) tendert klassiek ITSM+FMIS zonder EA-component ([tender](https://www.tender.app/aanbestedingen/itsm-fmis-tool)). **Voor een 40k-gemeente niet realistisch** (afwezigheid ≠ sluitend bewijs).

### A3. De gekoppelde-tools-praktijk — de facto concurrent

- [FEIT] **Mavim ↔ TOPdesk**: bestaat als productkoppeling ([SWC](https://www.softwarecatalogus.nl/pakket/mavim-topdesk-asset-management-api)); CMDB-data gekoppeld aan processen in Mavim; exacte objectmapping onbekend (404-pagina's).
- [FEIT] **BlueDolphin ↔ TOPdesk**: standaardintegratie als **betaalde managed service** (vaste jaarfee per integratieconfiguratie); synchroniseert records inclusief properties, maar **"relationships need to be managed within BlueDolphin"** ([FAQ](https://www.valueblue.com/integrations-faq), [marketplace](https://marketplace.topdesk.com/it-landscape-insights/)).
- [FEIT] **LeanIX ↔ ServiceNow**: officiële Store-app; synct applications/capabilities/CI-relaties ([docs](https://help.sap.com/docs/leanix/ea/servicenow-integration)).
- **Betekenis [CLAIM]:** het bestáán van precies deze koppelingen (EA-tool voor het "waarvóór", ITSM voor het "van wie/onder welk contract") is zelf het sterkste bewijs dat geen van beide kanten de ketting alleen sluit — anders was de koppeling overbodig. Het beeld ontstaat altijd in de EA-tool, tegen dubbele licentie, met handmatig relatie-onderhoud, en het contract-einddatum-perspectief komt níét standaard mee.

---

## Deel B — BlueDolphin: wat kost het, en hoe zwaar is het?

**Contextnoot [FEIT]:** ValueBlue is in april 2026 gerebrand naar "BlueDolphin" en positioneert zich als "AI-powered business transformation platform" ([Businesswire](https://www.businesswire.com/news/home/20260406527673/en/), [Dutch IT Channel](https://www.dutchitchannel.nl/news/729034/valueblue-gaat-verder-als-bluedolphin)). Het oude supporthelpcenter is offline — detailclaims steunen deels op zoekindex-snippets.

### B1. Licentiekosten
- [FEIT] Prijsmodel: betaald per **modeler**, viewers/contributors onbeperkt gratis; tiers Tactical (max 3 modelers, niet uitbreidbaar) / Strategic (5+, 1 connector, free trial) / Enterprise (15+) — **geen enkel bedrag** op [bluedolphin.io/pricing](https://bluedolphin.io/pricing/). Integraties (TOPdesk e.d.) = aparte managed service met vaste jaarfee ([FAQ](https://www.valueblue.com/integrations-faq)).
- [FEIT] **De harde-bronnen-zoektocht leverde nul euro-waarden op**: geen G-Cloud-listing ("0 results" op ValueBlue én BlueDolphin), geen vindbare TenderNed-aankondiging of -gunning, geen bedrag in gevonden raadsstukken/inkoopregisters (één ogenschijnlijke treffer — inkoopregister Noord-Brabant — bleek na volledige controle vals positief), geen prijs op review-sites (TrustRadius/Capterra/G2: "quotation based").
- [CLAIM] Het ontbreken op TenderNed is consistent met inkoop **onder de aanbestedingsdrempel** — een indicatie van ordegrootte, geen bewijs. [FEIT, historisch] Haarlemmermeer (2017): "maandelijks opzegbaar" ([Computable](https://www.computable.nl/2017/06/12/bluedolphin-ordent-applicaties-haarlemmermeer/)).
- **Netto: er bestaat geen enkele publieke prijs. BlueDolphin is daarmee níét aantoonbaar duur — en een kleine gemeente kan de kosten ook nergens publiek benchmarken.**

### B2. Implementatie: kosten en tijd
- [CLAIM] Partner CINX: "binnen 6–8 weken volledig operationeel"; ValueBlue zelf: "first value" in 30 dagen, strategic backbone na 6 maanden ([success](https://bluedolphin.io/success/)).
- [FEIT] **Gemeente Drimmelen (~27k inw.)** — de belangrijkste bevinding: een bestaande BlueDolphin-omgeving was "te ingewikkeld en sloot niet aan bij de kennis en verantwoordelijkheden van de interne IV-organisatie", verwaterde, en is in een **6 maanden** durend herinrichtingstraject met Native Consulting opnieuw opgezet ([case](https://www.nativeconsulting.nl/casussen/gemeente-drimmelen-verbeterde-functionaliteit-en-borging-van-bluedolphin/)). Het faalpatroon én de herstelkosten in één case.
- [FEIT] **Gemeente Soest (~46k inw.)**: overstap van Visio/Excel naar BlueDolphin met Native als begeleider; interne trekker + applicatiebeheerders voor metadata ([case](https://www.nativeconsulting.nl/nieuws/hoe-gemeente-soest-haar-applicatielandschap-transformeerde-met-bluedolphin/)). Haarlemmermeer: één architect + ValueBlue-consultant, uitgegroeid naar 40–50 gebruikers, ~350→~225 applicaties [FEIT, Computable].
- [FEIT] Partner 2-CNNCT verkoopt "**EA-as-a-Service**": licentie, inrichting én beheer volledig uitbesteed ([2-cnnct.nl](https://2-cnnct.nl/bluedolphin/)) — dit model bestaat júíst omdat kleine organisaties het niet zelfstandig dragen [CLAIM]. Partnertarieven: nergens gepubliceerd.

### B3. Wie kan het bedienen?
- [FEIT] Elke gemeentecase kent een vaste interne bezetting (Drimmelen: coördinator IV + I-adviseur + benoemde "Beheerder BlueDolphin" + team functioneel beheerders; Haarlemmermeer: architect als "driving force"; Soest: strategisch adviseur als trekker). Er bestaat een formeel trainingsaanbod: Fundamentals, **Admin-training**, 2-daagse Masterclass, 3-daagse ArchiMate-certificering ([academy](https://academy.bluedolphin.io/learn)).
- [CLAIM] Conclusie: een **repository die doorlopend beheer vergt**, geen workshop-tool. Alleen de viewer/contributor-kant is licht.

### B4. Wat komt er standaard in? (GEMMA)
- [FEIT] GEMMA komt **niet mee**: zelf het AMEFF-bestand downloaden en importeren (Admin-rol vereist; [GEMMA Online](https://www.gemmaonline.nl/wiki/ArchiMate_modelleren)); de officiële workflow is puur handmatig ([SWC-handleiding](https://www.softwarecatalogus.nl/Handleiding%20koppeling%20architectuurtools)); een nieuwe GEMMA-release = opnieuw handwerk, geen update-mechanisme gevonden.
- [FEIT] Gedocumenteerde frictie: AMEFF-modellen als GEMMA faalden op het niet-ondersteunde ArchiMate-`grouping`-element (supportforum; fix-status onbekend, helpcenter offline). De typering "officiële GEMMA-import" uit deel 1 verdient dus nuance: het is een **generieke AMEFF-import**, geen onderhouden GEMMA-integratie [CLAIM].

### B5. De ketting-vraag voor BlueDolphin
- [FEIT] Contract bestaat als objecttype (ArchiMate); einddatum/leverancier/beheerder zijn **geen kant-en-klaar register** maar worden ingericht via questionnaires + aanpasbaar metamodel. [FEIT, historisch] Dat de ketting gebóuwd kan worden bewijst Haarlemmermeer 2017: vervangingskalender op contract-einddatums, licenties aan applicaties, ontbrekende technisch beheerders geïdentificeerd — gevoed via TOPdesk/SCCM-koppelingen.
- [CLAIM] Netto-antwoord: de toets-zin is in BlueDolphin **haalbaar als inrichtingsproject** (metamodel + questionnaires + relatie-onderhoud + betaalde ITSM-koppeling), niet als out-of-the-box gemeentesjabloon — precies dát inrichtingswerk is wat de partners als dienst verkopen, en wat in Drimmelen misging.

### B6. Drempel voor een 40k-gemeente
- [FEIT] BlueDolphin is **aantoonbaar geen G4-product**: naast Amsterdam/Utrecht/Den Haag/Eindhoven/Tilburg/Haarlemmermeer ook **Soest (~46k)** en **Drimmelen (~27k)**; er bestaat een jaarlijkse "BlueDolphin Gemeentedag" — een gevestigd gemeentelijk ecosysteem. De Tactical-tier (3 modelers, viewers gratis) past qua opzet op een kleine gemeente.
- [CLAIM] De werkelijke drempel is niet de licentie maar de **bediening**: alle kleine-gemeente-cases lopen via een adviesbureau, en zonder geborgd intern beheer verwatert de omgeving (Drimmelen).

---

## Deel C — De eerlijke conclusie

### C1. Hypothese bevestigd of weerlegd?
**Grotendeels bevestigd, met twee gekwalificeerde uitzonderingen — en één bevinding die overeind blijft bij iedereen.**
- **Weerlegd op datamodel-niveau door Alfabet** (volwaardige Contract-klasse + standaard beheerrollenmodel + dependencies in één repository — als aparte betaalde module op een zwaar enterprise-platform) **en ServiceNow** (capability→app→CI→contract→vendor in één platform — over drie aparte SKU's, met Utrecht's €1,85M/3jr als enig NL-prijsanker). "EA stopt bij de applicatie" en "ITSM kent geen functie" zijn als absolute stellingen onjuist.
- **Bevestigd op beeld-niveau bij iedereen**: het éne standaardbeeld van de toets-zin — functie t/m aflopend contract t/m geraakte systemen — is bij **geen enkele** van de twaalf kandidaten gedocumenteerd aangetroffen. Bij ServiceNow verschijnt het contract in geen enkele map; bij Alfabet is een gecombineerde view niet aangetoond; bij alle flexibele-metamodel-tools (BlueDolphin, Mavim, Bizzdesign, Orbus, Ardoq, LeanIX) is het contractdeel configuratie, een tweede product of een DIY-recept. Kanttekening die erbij hoort: **afwezigheid van documentatie is geen bewijs van afwezigheid.**
- **De gemeentelijke praktijk bevestigt de naad**: de bestaande EA↔TOPdesk-koppelingen (Mavim, BlueDolphin — betaalde managed service, relaties handmatig) bestaan júíst omdat geen van beide kanten het alleen kan.

### C2. Waar staat LIKARA dan nog — feitelijk, gecombineerd met deel 1?
Wat wegvalt: de capability-as (gemeengoed), het gat-als-bevinding (conceptueel bekend bij APM), de ketting-als-datamodel (Alfabet/ServiceNow kunnen het), visualisatie/import/viewers (anderen volwassener). Wat feitelijk overblijft:
1. **De ketting als stándaardbeeld, zonder inrichtingsproject** — bij niemand aangetroffen; overal is het configuratie, een module, een tweede systeem of een consultanttraject.
2. **De sessiewerkvorm als productontwerp** — bij niemand aangetroffen (deel 1); de praktijk bewijst de behoefte (elke kleine-gemeente-case loopt via een adviesbureau).
3. **GEMMA gecureerd meegeleverd mét bijwerk-mechanisme** — overal elders een handmatige AMEFF-import met gedocumenteerde frictie en zonder release-updatepad.
4. **Grof-dan-fijn registreren** — nergens als werkvorm gedocumenteerd (deel 1).
5. **Geen doorlopende beheerlast als bestaansvoorwaarde** — het Drimmelen-patroon (repository verwatert zonder benoemde beheerder; herstel = 6 maanden consultancy) is de gedocumenteerde achilleshiel van het repository-model dat álle concurrenten delen.
Dat is smal — het zit niet in functionaliteit maar in vorm, drempel en curatie. Maar het is na twee verkenningsrondes nog steeds niet weerlegd.

### C3. De reële drempel van de alternatieven — gemeten
| Alternatief | Geld | Tijd | Expertise |
|---|---|---|---|
| ServiceNow (3 SKU's) | €1,85M/3jr platformdiensten bij 370k-gemeente [FEIT]; licenties daarbovenop; [CLAIM] impl. 3–5× licentie | maanden–jaren | platformteam |
| Alfabet | ankers $30k–63k/jr + Contract-module [deel 1/2] | 12-mnd-klasse [CLAIM] | EA-team |
| LeanIX/Ardoq/Orbus | contact-sales, enterprise [deel 1] | weken–maanden mét partner | EA-competentie |
| BlueDolphin | **onbekend — geen enkele publieke prijs**; historisch maandelijks opzegbaar; niet aantoonbaar duur | 6–8 wkn operationeel [CLAIM] tot 6 mnd herinrichting [FEIT, Drimmelen] | benoemde beheerder + adviesbureau; Admin-training; ArchiMate-kennis |
| VNG-route (SWC+Archi) | gratis [deel 1] | handwerk | architect met ArchiMate |
| Excel/Visio + bureau | uurtarief | per sessie | de consultant zelf |

**De witte vlek zit dus niet waar deel 1 hem nog vermoedde (prijs — BlueDolphin weerlegt "te duur voor klein"), maar in de bedieningsdrempel**: elke bestaande route vergt óf een inrichtingsproject + doorlopend intern beheer (BlueDolphin/EA-tools), óf een architect met modelleerkennis (VNG-route), óf blijft steken in platen zonder register (Excel/Visio). Een tool die de ketting-vraag beantwoordt zonder die drie belastingen bestaat — voor zover vindbaar — niet.

### C4. Vijf open koersvragen (beschrijvend, geen aanbeveling)
1. **Kan LIKARA het verschil "standaard vs. inrichtingsproject" demonstreerbaar maken?** Het onderscheid is nu een claim over vorm; de toets-zin in één demo-beeld tonen waar een BlueDolphin-consultant een traject nodig heeft, is het bewijs dat de propositie draagt — of niet.
2. **Hoe ontloopt LIKARA het Drimmelen-patroon?** Elke registratie-tool verwatert zonder borging; is de begeleide sessie-cadans (consultant komt terug) het antwoord, en is dat een product- of een diensteigenschap?
3. **Wat betekent BlueDolphins rebrand (april 2026, generiek AI-transformatieplatform) voor het gemeentesegment** — ruimte omdat de focus verschuift, of juist versnelling zodra AI-invoer de inrichtingsdrempel verlaagt?
4. **Alfabet en ServiceNow bewijzen dat de ketting-behoefte op enterprise-niveau al verzilverd wordt** — is het segment onder die drempel (gemeenten 20k–100k, SSC's) groot genoeg, en bereikbaar zonder het adviesbureau-kanaal te passeren?
5. **Prijstransparantie als positionering**: geen enkele concurrent publiceert een prijs — is een publieke, gemeente-passende prijs zelf een onderscheid, of verspeelt het onderhandelingsruimte?

**Geen aanbeveling, geen scope-wijziging. Bert beslist.**
