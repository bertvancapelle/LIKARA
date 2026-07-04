// Centrale, ontwikkelaar-beheerde veld-uitleg — naast labels.js, bereikbaar vanuit beide
// frontends via de `@modules`-alias (één bron, geen kopie per module). Houdt labels.js slank.
//
// - VELD_UITLEG: gesleuteld op veld-id (content-sleutel; niet altijd gelijk aan de formulier-
//   veldnaam waar dezelfde term in verschillende context anders uitgelegd wordt) → { uitleg, vuistregel? }.
//   Veld-niveau uitleg is de framing + vuistregel; geldt ongeacht welke opties er zijn.
// - OPTIE_UITLEG: gesleuteld op [set-naam][optie-key] (hergebruikt bestaande optie-keys uit
//   labels.js/catalogi) → discriminatie-regel per optie. Optioneel; alleen waar opties echt
//   discrimineren. Een ontbrekende optie-tooltip is géén fout — alleen tijdelijk geen extra uitleg.
//
// Nette degradatie: de accessors geven `null`/`[]` bij een ontbrekende sleutel — nooit een throw,
// nooit een geforceerde lege popover.

import { humaniseer } from './labels'

const _BIV_VUISTREGEL =
  'Laag = beperkte impact · Midden = merkbare impact op de organisatie · Hoog = grote impact ' +
  'op burgers, continuïteit of een wettelijke plicht.'

export const VELD_UITLEG = {
  // ── Checklistantwoord (ADR-037) ──────────────────────────────────────────────
  verantwoordelijke: {
    uitleg:
      'De verantwoordelijke is de afdeling of persoon uit het register die voor dít antwoord ' +
      'instaat — degene die de bron kent of het aanlevert. Kies je een persoon, dan wordt zijn ' +
      'afdeling er automatisch bij getoond.',
    vuistregel:
      'Leeg laten mag: dan wordt zichtbaar dat de bron nog ontbreekt (een aandacht-signaal, geen ' +
      'blokkade). Vul in zodra je weet wie ervoor instaat.',
  },
  // ── Component (ADR-028 / LI057-060) ──────────────────────────────────────────
  rol: {
    uitleg:
      'De rol beantwoordt: wat is de functie van dit component in het gegevenslandschap — ' +
      'werken er mensen in, is het een gegevensbron, of verbindt het alleen?',
    vuistregel:
      'Werken er mensen in → interne applicatie. Komt er data uit binnen de organisatie → ' +
      'interne dataprovider. Komt de data van buiten → externe dataprovider. Verbindt het alleen → koppelvlak.',
  },
  biv_beschikbaarheid: {
    uitleg:
      'Beschikbaarheid: hoe erg is het als dit component uitvalt of onbereikbaar is? Kies een ' +
      'niveau; leeg laten telt als niet-geclassificeerd en levert een signaal.',
    vuistregel: _BIV_VUISTREGEL,
  },
  biv_integriteit: {
    uitleg:
      'Integriteit: hoe erg is het als de gegevens in dit component onjuist of ongemerkt gewijzigd zijn?',
    vuistregel: _BIV_VUISTREGEL,
  },
  biv_vertrouwelijkheid: {
    uitleg:
      'Vertrouwelijkheid: hoe erg is het als onbevoegden inzage krijgen in de gegevens van dit component?',
    vuistregel: _BIV_VUISTREGEL,
  },
  componenttype: {
    uitleg:
      'Het componenttype bepaalt hoe LIKARA dit component behandelt: of het op volledigheid wordt ' +
      'beoordeeld, en hoe het op de kaart verschijnt. Na de eerste registratie ligt het type vast — ' +
      'kies het bewust.',
  },
  hostingmodel: {
    uitleg:
      'Waar en hoe dit component draait — in eigen beheer, in de cloud, of extern afgenomen. Zegt ' +
      'wie de techniek eronder beheert.',
  },
  migratiepad: {
    uitleg:
      'Wat er met dit component in de transitie gaat gebeuren — blijft het, gaat het mee, wordt het ' +
      'vervangen of uitgefaseerd. Legt de bedoeling vast, los van of het al gebeurd is.',
  },
  complexiteit: {
    uitleg: 'Hoe ingewikkeld de aanpak/migratie van dit component naar verwachting is.',
    vuistregel:
      'Laag = eenvoudig/standaard · Midden = enige afhankelijkheden of maatwerk · Hoog = veel ' +
      'afhankelijkheden, risico of maatwerk.',
  },
  prioriteit: {
    uitleg: 'Hoe urgent dit component in de transitie is t.o.v. de rest.',
    vuistregel: 'Laag = kan wachten · Midden = normaal · Hoog = eerst aanpakken.',
  },
  eigenaar_organisatie_id: {
    uitleg:
      'De organisatie die eigenaar is van dit component — verantwoordelijk dat het bestaat en ' +
      'beheerd wordt. Dit is een organisatie, geen persoon of beheerrol.',
    vuistregel:
      "Verwar dit niet met de verantwoordelijke personen/rollen — die leg je apart vast bij 'wie " +
      "doet wat'. Leeg laten levert een kritiek signaal.",
  },

  // ── Contract ─────────────────────────────────────────────────────────────────
  leverancier: {
    uitleg:
      'De partij die dit contract levert — een organisatie, organisatie-eenheid of externe partij ' +
      '(geen persoon).',
    vuistregel: 'Leeg laten levert een kritiek signaal.',
  },
  contracttype: {
    uitleg: 'Hoe dit contract in de contractstructuur staat: op zichzelf, of onder een groter contract.',
  },
  mantelcontract: {
    uitleg: 'Het overkoepelende contract waaronder dit deelcontract valt.',
  },
  dekking: {
    uitleg:
      'Wat dit contract dekt — welke soorten kosten of diensten eronder vallen (meerdere mogelijk).',
  },
  kostenmodel: {
    uitleg: 'Hoe de kosten van dit contract zijn opgebouwd.',
  },

  // ── Datatype ─────────────────────────────────────────────────────────────────
  datatype_categorie: {
    uitleg:
      'Het soort gegevens dat dit datatype vertegenwoordigt (bv. persoonsgegevens, zaakgegevens). ' +
      'Bepaalt mede de gevoeligheid.',
  },

  // ── Gebruikersgroep (ADR-036) ────────────────────────────────────────────────
  gg_organisatie: {
    uitleg:
      "De organisatie waarvan deze afdeling de applicatie gebruikt. Hiermee telt die organisatie " +
      "mee in 'gebruikt door' — zonder dubbele invoer.",
  },
  gg_afdeling: {
    uitleg:
      'De afdeling of het team binnen de organisatie dat de applicatie gebruikt — kies een bestaande ' +
      "afdeling van de organisatie, of maak er een aan. Samen met de organisatie vormt dit de " +
      "identiteit ('afdeling — organisatie').",
  },

  // ── Partij ───────────────────────────────────────────────────────────────────
  aard: {
    uitleg:
      'Wat voor soort partij dit is. De aard bepaalt welke gegevens verplicht zijn en ligt na ' +
      'aanmaak vast — kies bewust.',
    vuistregel:
      'Een hele organisatie → organisatie. Een afdeling/team → organisatie-eenheid (organisatie ' +
      'verplicht). Een medewerker/contactpersoon → persoon. Een leverancier/partner van buiten → externe partij.',
  },
  soort: {
    uitleg: 'Een optionele functionele typering van de partij, náást de aard.',
  },
  partij_organisatie: {
    uitleg: 'De organisatie waar deze eenheid of persoon bij hoort.',
  },
  partij_afdeling: {
    uitleg: 'De afdeling waar deze persoon bij hoort (alleen voor personen).',
  },

  // ── Roltoewijzing (beheerrol) ────────────────────────────────────────────────
  beheerrol: {
    uitleg:
      'Welke beheerrol deze partij vervult op dit component of contract. Meerdere rollen of ' +
      'meerdere partijen op één object mag — elk is een losse regel.',
  },

  // ── Koppeling (flow) ─────────────────────────────────────────────────────────
  koppelrichting: {
    uitleg:
      'Stroomt de gegevens één kant op of beide kanten? Dit beschrijft de aard van de koppeling, ' +
      'niet of dit component de bron of het doel is.',
  },
  koppelprotocol: {
    uitleg:
      'Via welke techniek de koppeling loopt (bv. API, bestandsuitwisseling, directe databasekoppeling).',
  },
  impact_verbreking: {
    uitleg:
      'Hoe erg het is als deze koppeling wegvalt — helpt bij het inschatten van risico bij migratie ' +
      'of uitfasering.',
  },

  // ── Structuur (draait-op) ────────────────────────────────────────────────────
  draait_op: {
    uitleg:
      'Kies de host (server, infrastructuur of onderliggend component) waaróp dit component draait. ' +
      'Let op de richting: je kiest waar dit component op staat, niet wat erop staat.',
    vuistregel: "Vraag jezelf af: 'waar draait dit op?' — dat antwoord kies je hier.",
  },

  // ── Checklistscore (zwaarst — inline) ────────────────────────────────────────
  score: {
    uitleg:
      'Je oordeel of dit onderdeel op orde is. Dit is de enige invoer die de lifecycle-status en ' +
      'eventuele blokkades van het component bepaalt — vul zorgvuldig in.',
  },
  checklist_antwoord: {
    uitleg:
      'Je antwoord op deze beoordelingsvraag. De vraag hoort bij dit componenttype; kies het ' +
      'antwoord dat de werkelijkheid het best beschrijft.',
  },

  // ── Blokkade ─────────────────────────────────────────────────────────────────
  blokkade_status: {
    uitleg:
      "De stand van deze blokkade. 'Opgelost' wordt automatisch gezet zodra de oorzaak is " +
      'weggenomen — dat kies je hier niet zelf.',
  },

  // ── Migratielaag ─────────────────────────────────────────────────────────────
  dispositie: {
    uitleg: 'Wat er met dit lid in de transitie gaat gebeuren, binnen dit plateau/deze gap.',
  },
  contractueel_bevestigd: {
    uitleg:
      'Vink aan als de contractuele afspraken voor dit lid bevestigd zijn (met wie en wanneer). ' +
      'Voedt de contractuele readiness.',
  },
  plateau: {
    uitleg:
      'Een plateau is een momentopname van het landschap — hoe het nu is (baseline) of hoe je wilt ' +
      'dat het wordt (doelsituatie). Je vult het met de componenten en contracten die in die situatie horen.',
  },
  gap: {
    uitleg:
      'Een gap beschrijft het verschil tussen twee plateaus (baseline en doelsituatie) en wat er ' +
      'nodig is om van het ene naar het andere te komen.',
  },
  work_package: {
    uitleg:
      'Een werkpakket is een brok werk in de transitie. Werkpakketten kunnen subwerkpakketten bevatten.',
  },
  deliverable: {
    uitleg:
      'Een op te leveren resultaat. Optioneel te koppelen aan een werkpakket (dat het maakt) en een ' +
      'plateau (dat het realiseert).',
  },

  // ── Platformbeheerder / ArchiMate (inline; gewone taal + formele term als anker) ──
  archimate_element: {
    uitleg:
      'Het ArchiMate-elementtype dat dit componenttype voorstelt — bepaalt hoe componenten van dit ' +
      'type in de architectuurweergave verschijnen.',
  },
  archimate_laag: {
    uitleg:
      'De ArchiMate-laag waarin dit type thuishoort — grofweg: bedrijf, software, techniek of transitie.',
  },
  archimate_aspect: {
    uitleg: 'Het ArchiMate-aspect: doet het iets, ondergaat het iets, of ís het een gedraging?',
  },
  checklist_dragend: {
    uitleg:
      'Aan = componenten van dit type worden op registratie-volledigheid beoordeeld (ze krijgen een ' +
      'profiel en beoordelingsvragen). Uit = dit type wordt niet gescoord.',
  },
  systeem_sleutel: {
    uitleg:
      'Een beschermde systeemsleutel: essentieel voor LIKARA, kan niet worden verwijderd of gedeactiveerd.',
  },
  volgorde: {
    uitleg:
      'Bepaalt de rangorde van dit niveau in de schaal (laag naar hoog). Filters en drempels ' +
      'gebruiken deze volgorde, niet de naam.',
  },
  dimensie: {
    uitleg:
      'De dimensie bepaalt waarvoor deze kenmerk-optie geldt (bv. dispositie voor plateau-leden, ' +
      'beheerrol voor roltoewijzing).',
  },
  antwoordtype: {
    uitleg: 'Hoe deze vraag beantwoord wordt.',
  },
  betekenis: {
    uitleg: 'Een optionele markering van wat deze vraag meet, voor rapportage en filtering.',
  },
  sleutel: {
    uitleg:
      'De technische sleutel van deze optie — vaste, korte code. Ligt na aanmaak vast; de gebruiker ' +
      'ziet het label.',
  },
}

export const OPTIE_UITLEG = {
  // Set 'componentrol' — ADR-028.
  componentrol: {
    interne_applicatie:
      'Een eigen systeem waar de organisatie zelf mee werkt — met gebruikers en functionaliteit, ' +
      'geen puur doorgeefpunt. Standaardkeuze als geen van de andere beter past.',
    interne_dataprovider:
      'Een eigen bron die vooral gegevens levert aan andere interne systemen, meer dan dat er ' +
      'mensen rechtstreeks in werken.',
    externe_dataprovider:
      'Een bron buiten de eigen organisatie waar gegevens vandaan komen: een basisregistratie ' +
      '(BAG, BRP), een landelijke voorziening of een ketenpartner. De organisatie neemt de data af ' +
      'maar beheert het systeem niet zelf.',
    koppelvlak:
      'Een technische tussenlaag die twee kanten verbindt — adapter, API-gateway of middleware. ' +
      'Geen systeem waar je in werkt en geen echte gegevensbron, maar de verbinding ertussen.',
  },

  // Set 'componenttype' — LI060 (8 typen).
  componenttype: {
    applicatie:
      'Een systeem waar gebruikers mee werken om taken uit te voeren — het klassieke ' +
      'informatiesysteem. Wordt beoordeeld op registratie-volledigheid.',
    database:
      'Een gegevensopslag/databank die applicaties gebruiken of waarop ze draaien — niet waar mensen ' +
      'in werken, maar de opslag eronder.',
    server_compute:
      'Reken- of serverinfrastructuur waarop software draait (fysiek of virtueel) — de onderlaag ' +
      'onder applicaties.',
    client_software: 'Software op het werkstation van de gebruiker (desktop-app, agent).',
    saas_dienst:
      'Een dienst die extern als abonnement wordt afgenomen (software-as-a-service) — je gebruikt ' +
      'hem, maar draait hem niet zelf.',
    integratievoorziening:
      'Verbindende software die systemen aan elkaar knoopt (ESB, middleware, berichtenbus) — het ' +
      'bindweefsel van het landschap.',
    fileshare: 'Een gedeelde bestandsopslag (netwerkschijf, share).',
    landelijke_voorziening:
      'Een landelijke, extern afgenomen voorziening — je neemt de dienst af, hij wordt buiten je ' +
      'organisatie beheerd.',
  },

  // Set 'contracttype' — keys uit labels.js CONTRACTTYPE (op betekenis gekoppeld).
  contracttype: {
    mantelcontract: 'Een overkoepelend raamcontract waaronder losse deelcontracten vallen.',
    deelcontract:
      'Een deelcontract onder een mantelcontract — kies daarna het bijbehorende mantelcontract.',
    los_contract: 'Een op zichzelf staand contract, zonder mantel-/deelstructuur.',
  },

  // Set 'dekking' — contractconfig[dekking].
  dekking: {
    licentie_aanschaf: 'De aanschaf van licenties valt onder dit contract.',
    onderhoud_support: 'Onderhoud en support vallen onder dit contract.',
    hosting: 'Hosting/infrastructuur valt onder dit contract.',
  },

  // Set 'kostenmodel' — contractconfig[kostenmodel].
  kostenmodel: {
    saas_pxq: 'Prijs per eenheid × aantal (klassiek SaaS-model, bv. per gebruiker per maand).',
    volume: 'Staffel op basis van afgenomen volume.',
    per_inwoner: 'Kosten per inwoner van de gemeente (gebruikelijk bij gemeentelijke voorzieningen).',
  },

  // Set 'aard' — PARTIJ_AARD. ADR-038: burger-doelgroepen zijn gewone (externe) organisaties.
  aard: {
    organisatie: 'Een organisatie als geheel — de eigen organisatie, een externe partij of een ' +
      'burger-doelgroep (bv. "Burgers Tiel", met segment-afdelingen eronder).',
    organisatie_eenheid:
      'Een afdeling of team binnen een organisatie. Vereist de bovenliggende organisatie.',
    persoon: 'Een medewerker of contactpersoon (natuurlijke persoon).',
    externe_partij: 'Een externe partij: leverancier, partner of ketenpartner.',
  },

  // Set 'partijsoort' — partijsoort_optie.
  partijsoort: {
    leverancier: 'Levert producten of diensten aan de organisatie.',
    partner: 'Werkt samen met de organisatie zonder klassieke leverancier-relatie.',
    ketenpartner: 'Deelt in een keten of proces gegevens/taken met de organisatie.',
  },

  // Set 'beheerrol' — relatiekenmerk[beheerrol] (9 keys).
  beheerrol: {
    functioneel_beheer:
      'Zorgt dat de applicatie functioneel doet wat gebruikers nodig hebben (inrichting, ' +
      'gebruikersvragen, functionele wensen) — niet de techniek.',
    technisch_beheer:
      'Zorgt voor de technische werking en het draaiend houden (installatie, updates, storingen).',
    applicatiebeheer:
      'Overkoepelend beheer van de applicatie als geheel, tussen functioneel en technisch in.',
    contractbeheer:
      'Beheert het contract rond dit object (afspraken, verlengingen, leveranciersrelatie).',
    product_owner: 'Bepaalt de inhoudelijke koers en prioriteiten van het product.',
    eigenaar: 'Draagt de eindverantwoordelijkheid voor dit object.',
    proceseigenaar: 'Verantwoordelijk voor het bedrijfsproces dat dit object ondersteunt.',
    account_manager: 'Onderhoudt de relatie met de leverancier/klant rond dit object.',
    service_delivery_manager: "Bewaakt de afgesproken dienstverlening en serviceniveaus (SLA's).",
  },

  // Set 'koppelrichting' — KOPPELRICHTING.
  koppelrichting: {
    eenrichting: 'Gegevens stromen van de bron naar het doel, niet terug.',
    tweerichting: 'Gegevens stromen beide kanten op tussen de twee systemen.',
  },

  // Set 'score' — SCORE.
  score: {
    ja: 'Volledig op orde.',
    deels: 'Deels op orde — er is nog werk nodig. Telt niet als afgehandeld.',
    nee: 'Niet op orde.',
    nvt: 'Niet van toepassing op dit component — telt niet mee in de beoordeling.',
  },

  // Set 'blokkade_status' — BLOKKADE_STATUS ('opgelost' is auto-afgeleid → geen keuze-uitleg).
  blokkade_status: {
    open: 'Nog niet opgepakt.',
    in_behandeling: 'Er wordt aan gewerkt.',
  },

  // Set 'dispositie' — relatiekenmerk[dispositie].
  dispositie: {
    behouden: 'Blijft ongewijzigd bestaan.',
    migreren: 'Gaat mee naar de nieuwe situatie, mogelijk aangepast.',
    vervangen: 'Wordt vervangen door iets anders.',
    uitfaseren: 'Wordt afgebouwd en verdwijnt.',
  },

  // Set 'archimate_element' — TOEGESTANE_ELEMENTEN (10 van 18 gedekt; rest degradeert).
  archimate_element: {
    application_component: 'Een softwaresysteem/toepassing (ArchiMate: application component).',
    application_service:
      'Een dienst die door software wordt geleverd en afgenomen kan worden (ArchiMate: application service).',
    system_software:
      'Ondersteunende software zoals een database, besturingssysteem of middleware (ArchiMate: system software).',
    node: 'Infrastructuur waarop software draait — server of rekenknooppunt (ArchiMate: node).',
    data_object:
      'Een stuk gegevens dat software vasthoudt of verwerkt — de informatie zelf, geen programma ' +
      '(ArchiMate: data object).',
    business_role: 'Een rol die iemand of iets in de organisatie vervult (ArchiMate: business role).',
    business_actor: 'Een organisatie, afdeling of persoon die iets doet (ArchiMate: business actor).',
    contract: 'Een formele afspraak/overeenkomst (ArchiMate: contract).',
    artifact: 'Een concreet bestand of gegevensdrager (ArchiMate: artifact).',
    technology_service: 'Een dienst geleverd door infrastructuur/techniek (ArchiMate: technology service).',
    device: 'Een fysiek apparaat waarop software draait — server, werkstation of appliance (ArchiMate: device).',
    communication_network: 'Een netwerk dat systemen met elkaar verbindt (ArchiMate: communication network).',
    business_service:
      'Een dienst die de organisatie levert, aan de buitenwereld of aan zichzelf (ArchiMate: business service).',
    business_object:
      "Een informatie-object op bedrijfsniveau — een begrip als 'zaak' of 'vergunning', los van de " +
      'techniek (ArchiMate: business object).',
    plateau: 'Een momentopname van het landschap in de transitie — een tussenstand (ArchiMate: plateau).',
    gap: 'Het verschil tussen twee plateaus — wat er nog moet gebeuren (ArchiMate: gap).',
    work_package: 'Een afgebakend brok werk in de transitie (ArchiMate: work package).',
    deliverable: 'Een concreet op te leveren resultaat van een werkpakket (ArchiMate: deliverable).',
  },

  // Set 'archimate_laag' — TOEGESTANE_LAGEN (volledig).
  archimate_laag: {
    business: 'De bedrijfslaag: organisatie, mensen, processen (ArchiMate: business).',
    application: 'De applicatielaag: software en de diensten die software levert (ArchiMate: application).',
    technology:
      'De techniek-/infrastructuurlaag: servers, netwerk, systeemsoftware (ArchiMate: technology).',
    implementation_migration:
      'De transitielaag: plateaus, gaps en het migratiewerk (ArchiMate: implementation & migration).',
  },

  // Set 'archimate_aspect' — TOEGESTANE_ASPECTEN (volledig).
  archimate_aspect: {
    active: 'Iets dat handelt of uitvoert — een actieve structuur (ArchiMate: active structure).',
    passive:
      'Iets waarop gehandeld wordt, zoals gegevens — een passieve structuur (ArchiMate: passive structure).',
    behavior: 'Een gedrag of activiteit — iets dat gebeurt (ArchiMate: behavior).',
  },

  // Set 'antwoordtype' — checklistconfig (frontend-vaste lijst).
  antwoordtype: {
    geen: 'Geen antwoord-invoer — puur informatief.',
    enkelvoudige_keuze: 'Eén keuze uit een lijst.',
    meerkeuze: 'Meerdere keuzes tegelijk mogelijk.',
    getal: 'Een getalswaarde.',
  },
}

// Veld-niveau uitleg: { uitleg, vuistregel? } of null (ontbrekend = geen extra uitleg).
export function veldUitleg(id) {
  return VELD_UITLEG[id] ?? null
}

// Optie-niveau uitleg voor één optie: string of null (nette degradatie op ontbrekende sleutel).
export function optieUitleg(set, key) {
  return OPTIE_UITLEG[set]?.[key] ?? null
}

// Alle optie-regels van een set als [{ key, label, uitleg }] voor de popover-lijst. Het label
// wordt uit de key gehumaniseerd (geen API-afhankelijkheid). Onbekende set → [] (degradatie).
export function optieUitlegLijst(set) {
  const map = OPTIE_UITLEG[set]
  if (!map) return []
  return Object.entries(map).map(([key, uitleg]) => ({ key, label: humaniseer(key), uitleg }))
}
