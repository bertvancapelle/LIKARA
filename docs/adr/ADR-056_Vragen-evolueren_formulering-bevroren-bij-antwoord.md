# ADR-056 — Vragen evolueren: de formulering wordt bevroren bij het antwoord

| | |
|---|---|
| **Status** | Voorstel — besloten (LI050, aangescherpt LI051); bouw volgt, sliceverdeling apart |
| **Datum** | 2026-07-23 |
| **Bijgewerkt** | 2026-07-24 — LI051-besluiten verwerkt: één sein per vraag (besluit 7), opnieuw antwoorden als bevestiging (besluit 8, vervangt de "klopt nog"-knop), tabbladgetal telt beide soorten werk (besluit 10), vraag-geschiedenis voor de consultant (besluit 17), nulpunt bij invoering (besluit 18), doving stille notitie (besluit 6) |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-019 (gestructureerd antwoord + optie-catalogus, stabiele sleutels) · ADR-022 W1–W5 (vraagbeheer: beheerder-only, categorie-entiteit, code van het scherm, sleep-volgorde) · ADR-052 (norm = lat niet poort; neutraal "lat verschoven" vs. amber "bewust afgeweken"; klaarverklaring-snapshot; "bewust geen"-demping) · ADR-006 (audit-trail) · ADR-013/016 (score = enige lifecycle-driver) · LI048 (Open punten als tabblad, teller = lijst) · LI050 (uitgezette vraag telt niet mee) |
| **Grond** | `docs/Checkpoint-vraagevolutie-V050.md` (read-only meting, LI050) · `docs/Checkpoint-vraagevolutie-bouwkant-V051.md` (read-only meting bouwkant, LI051) |
| **Invariant (onschendbaar)** | **LIKARA schrijft nooit een uitspraak toe aan een formulering die de antwoorder niet zag.** En: vraagevolutie raakt de beoordeling nooit — een verouderd antwoord landt **nooit** in het blok "dit moet nog" (dat voedt de klaarverklaring-snapshot) en "verouderd" wordt **nooit** uitgedrukt door de score te legen (de score is de enige bron van de beoordelingsstatus). |

---

## Context / het probleem in gebruikerstaal

Een beheerder stelt vragen op per categorie, en die vragen evolueren: ze worden scherper
geformuleerd of juist ingeperkt, en keuzelijsten groeien. Vandaag gebeurt dat stilzwijgend. Een
antwoord weet niet op wélke formulering het antwoord gaf (`checklistscore` verwijst alleen naar de
vraag als geheel); een uitgebreide keuzelijst laat geen spoor na (een optie draagt niet eens een
moment van ontstaan); een optielabel kan stil hernoemd worden — óók bij afgeleide sets. Daarmee kan
LIKARA een uitspraak toeschrijven aan iemand die haar niet deed — precies wat het platform elders
verbiedt (vgl. ADR-052: een verschoven lat is nooit het besluit van de consultant).

De meting (Grond) stelt vast: de vraagtekst is via de API nu al vrij wijzigbaar zonder enig gevolg;
de audit legt oud/nieuw wél vast maar is een logregel, geen leeslaag; en de niet-blokkerende
signaalcategorie ("dit valt op", Open punten blok 3) bestaat al.

## Besluiten

### 1. De vraagtekst mag wijzigen, ook mét bestaande antwoorden

*Wat de gebruiker merkt:* de beheerder verbetert een typefout of scherpt een vraag aan zonder de
vraag te hoeven uitzetten en opnieuw op te voeren.
*Vangrail:* het bestaande wijzigpad (`PATCH /vragen/{id}`) blijft de ingang; wat er verandert is
wat er ómheen gebeurt (besluiten 2–18).

### 2. De beheerder zegt zelf wat de wijziging is

*Wat de gebruiker merkt:* bij het opslaan kiest de beheerder expliciet: **verduidelijking** (er
verandert niets voor wie al antwoordde) of **dit verandert de vraag** (bestaande antwoorden gaan
als verouderd lezen). LIKARA stelt de vraag; de beheerder beantwoordt haar.
*Vangrail:* **LIKARA leidt dit nooit uit de tekst af** — geen diff-heuristiek, geen
gelijkenis-drempel. Het is een menselijk besluit met een moment en een eigenaar, en het wordt als
zodanig geauditeerd.

### 3. Eén regel voor alles wat betekenis kan verschuiven

*Wat de gebruiker merkt:* dezelfde keuze (verduidelijking of wijziging) verschijnt óók bij het
**uitbreiden van een keuzelijst** en bij het **hernoemen van een optielabel** — ook bij afgeleide
sets, waar hernoemen vandaag stil kan.
*Vangrail:* er bestaat geen stil pad ernaast: elke mutatie die de betekenis van een vraag kan
verschuiven loopt door deze keuze.
*Vangrail (LI051):* deze aanleidingen leveren géén eigen soort melding op — wat er ook wijzigde,
aan de antwoordkant is het één sein per vraag (besluit 7).

### 4. De formulering wordt bevroren bij het antwoord

*Wat de gebruiker merkt:* bij een antwoord ligt vast wát er gevraagd werd toen het gegeven werd.
"Is dit antwoord verouderd?" is daarmee een **vergelijking**, geen tweede administratie.
*Vangrail:* bij een **verduidelijking** schuift de bevroren tekst mee (de betekenis veranderde
niet); bij een **echte wijziging** blijft hij staan.
*Verworpen:*
- **Vraagversies** — een tweede identiteitsruimte naast de vraag, zonder drager: de meting telt
  267 antwoorden, 96 opties, 0 inactief. Te zwaar voor wat het moet dragen.
- **Het audit-spoor als bron** — de audit is een vangnet, nooit de leeslaag; wat de consultant op
  zijn scherm ziet mag niet uit het logboek komen.

### 5. Voor de keuzelijst geen snapshot, maar een moment

*Wat de gebruiker merkt:* niets aparts (LI051) — een optie die **ná** zijn antwoord bijkwam is,
bij een echte wijziging, een aanleiding voor hetzelfde ene sein van besluit 7; geen eigen soort
melding.
*Vangrail:* een hele lijst bevriezen bij elk antwoord is zwaar voor wat je wilt weten. Het enige
dat ontbreekt is dat een optie vandaag geen moment van ontstaan draagt (geen `created_at`,
models.py:1050) — dát moment is de minimale drager.

### 6. Verduidelijking → een stille notitie bij het antwoord

*Wat de gebruiker merkt:* de consultant wordt **niet gestoord**; wie kijkt, kan terugzien dat de
formulering is bijgewerkt.
*Beslist (LI051 — was subknoop 3):* de notitie blijft bij het antwoord staan tot **iemand mét het
recht om te antwoorden** het antwoord aanraakt — dan verdwijnt hij. Het antwoord is van het team,
niet van één persoon; is de notitie gezien, dan is hij gezien.

### 7. Echte wijziging → één sein per vraag, verouderd in neutrale toon (aangescherpt LI051)

*Wat de gebruiker merkt:* zijn antwoord leest als **verouderd** — er is niets fout gegaan; de vraag
eronder is veranderd. Nooit een waarschuwingskleur, nooit verwijt-taal. Verandert er íéts aan de
vraagstelling — de tekst, een antwoordmogelijkheid erbij, een bestaande die anders gaat heten — dan
is dat **één** melding bij het antwoord: niet per onderdeel, geen soorten met eigen gedrag. De
consultant hoeft niet te weten wélk onderdeel verschoof; hij loopt de vraag in zijn geheel na.
*Vangrail (LI051):* het sein geldt voor **iedereen die op die vraag antwoordde**, ook wie het
keuzeveld leeg liet — juist die persoon vond zijn antwoord er misschien niet in. Er wordt niet
onderscheiden tussen antwoorden mét en zónder gekozen optie.
*Vangrail:* dit is dezelfde scheiding als bij een verschoven organisatienorm (ADR-052 besluiten
8–11: "lat verschoven" = neutraal, "bewust afgeweken" = amber), één laag lager — de presentatie
volgt dat bestaande patroon.

### 8. Opnieuw antwoorden ís de bevestiging (herzien LI051 — vervangt de "klopt nog"-knop)

*Wat de gebruiker merkt:* de consultant **geeft zijn antwoord opnieuw**, óók als hij dezelfde keuze
maakt; zodra hij dat gedaan heeft, dooft het sein. Alle onderdelen openen **leeg** (afhandeling én
keuze); zijn **toelichting blijft staan** — die heeft hij zelf geschreven.
*Verworpen (LI051):* de eerdere knop "**mijn antwoord klopt nog**" — dat vinkje klik je weg zonder
de vraag opnieuw te lezen, en dan staat er een bevestiging in het systeem die niets bevestigt.
*Vangrail:* de bevestiging geldt voor **díé formulering**: wijzigt de beheerder de vraag daarna
opnieuw (als echte wijziging), dan komt het sein terug.
*Vangrail (essentieel):* het oude antwoord **blijft meetellen** tot er opnieuw geantwoord is —
anders zet één herformulering tientallen componenten terug op onvolledig, precies wat dit ADR
belooft nooit te doen (besluit 11 + de invariant). Het sein staat op de werklijst; het blokkeert
niets en leegt niets.

### 9. De oude formulering leeft in de geschiedenis van de vraag (herzien LI051)

*Wat de gebruiker merkt:* bij het antwoord staat alleen **dát** er iets gewijzigd is; wie de oude
formulering wil nalezen vindt haar in de **wijzigingsgeschiedenis van de vraag** (besluit 17) —
niet uitklapbaar bij het antwoord zelf, niet in een tweede paneel ernaast.
*Herzien (LI051):* hier stond eerder "de geschiedenis van het component" — gemeten
(Checkpoint-bouwkant-V051 §M4) landt een vraagwijziging daar niet en kán hij er zonder
component-anker niet landen: een vraag is tenant-breed. De vraag krijgt zijn eigen leesbare
geschiedenis.

### 10. Verouderd telt mee in Open punten — het tabbladgetal telt beide soorten werk (aangescherpt LI051)

*Wat de gebruiker merkt:* een verouderd antwoord staat op de **werkvoorraad** van de consultant:
het telt mee in het Open punten-getal op het tabblad. De consultant stelt bij dat getal één vraag:
*moet ik hier nog iets?* Een vraag die nooit beantwoord is en een vraag die opnieuw beantwoord moet
worden zijn voor hem hetzelfde soort werk — het verschil in herkomst is geen verschil in werk.
*Vangrail (gevolg voor de bouw, LI051):* het tabbladgetal telt vandaag **alleen** het blok "dit
moet nog" (gemeten: Checkpoint-bouwkant-V051 §M3); dat verbreedt naar beide soorten werk. **Het
getal blijft geen poort**: een component kan klaar verklaard worden terwijl er een herevaluatie
openstaat.
*Vangrail:* binnen het overzicht blijft de herkomst zichtbaar: het punt landt in het blok voor
**niet-blokkerende** signalen ("dit valt op"), in de rustige toon die daarvoor bestaat — de
categorie bestaat al en voedt niets anders dan het getal en de lijst (LI048 besluit 14: teller =
lijst). Het blok "dit moet nog" (dat de klaarverklaring-snapshot voedt) blijft buiten bereik
(invariant).

### 11. Het blokkeert niets

*Wat de gebruiker merkt:* een verouderd antwoord maakt een component **niet onklaar**; de mens
beslist of hij het opnieuw bekijkt.
*Vangrail:* zie de invariant — nooit blok 1, nooit de score legen. De lifecycle-status en de
klaarverklaring worden door vraagevolutie niet geraakt.

### 12. Het totaalbeeld leeft in het vraagbeheer-scherm

*Wat de gebruiker merkt:* de beheerder ziet **waar hij kan handelen** — in het vraagbeheer-scherm,
niet op het dashboard: een teller per vraag ("N verouderde antwoorden") en per categorie het
totaal, bij de wijziging die het veroorzaakte. En **vóór** het opslaan ziet hij de voorspelling
"dit raakt N antwoorden" — in het éne opslaan-venster van besluit 13.
*Vangrail:* de voorspelling vóór en het getal ná komen uit **dezelfde telling** — nooit twee
afleidingen (het bestaande `impact_telling` + bevestig-patroon is de vorm). En: **de beheerder kan
niet namens de antwoorders opnieuw antwoorden** — het sein dooft alleen door een nieuw antwoord van
wie het recht heeft te antwoorden (besluit 8).

### 13. Eén opslaan-moment per vraag, niet per veld

*Wat de gebruiker merkt:* de beheerder kan in één keer de vraagtekst wijzigen, een
antwoordmogelijkheid hernoemen en er een toevoegen. Bij het opslaan verzamelt LIKARA die
wijzigingen en stelt de keuze — verduidelijking of echte wijziging — **één keer**, met een
opsomming van wat er gewijzigd is en hoeveel antwoorden eronder liggen.
*Waarom:* per veld vragen zou drie keer dezelfde vraag opleveren voor één handeling — en dan wordt
de keuze een formaliteit die je wegklikt.
*Vangrail (gevolg voor de bouw):* het huidige scherm heeft één opslaan per antwoordmogelijkheid en
één per categorie, en géén voor de vraag. Dat wordt **één opslaan op het niveau van de vraag**, op
een vaste plek, met dezelfde bevestiging als het slepen.

### 14. Het antwoordtype staat op slot mét de reden, niet met een melding achteraf

*Wat de gebruiker merkt:* zodra er antwoorden op een vraag zijn gegeven, is het
antwoordtype-veld **dicht** — met in één zin waarom. De beheerder ontdekt de beperking op het
moment van kiezen, niet als voetnoot nadat hij het geprobeerd heeft.
*Vangrail:* de serverregel bestaat al (een geconfigureerde vraag wisselt niet van antwoordtype);
wat verandert is de presentatie: vandaag staat de beperking als grijze regel **onder** het veld en
weigert pas de server. Een beperking hoort te gelden op het moment van kiezen.

### 15. Een uitgezette antwoordmogelijkheid blijft zichtbaar en is weer aan te zetten

*Wat de gebruiker merkt:* wie een optie per ongeluk uitzet, kan dat terugdraaien. De optie blijft
in de beheerlijst staan, herkenbaar als uitgezet, met de handeling om hem weer te activeren. Voor
de consultant blijft hij uit de keuzelijst, en een bestaand antwoord dat ernaar wijst blijft
leesbaar.
*Waarom:* een lijst die mag evolueren, mag geen eenrichtingsverkeer zijn.
*Vangrail:* dit is een **domeinbesluit, geen schermkeuze** — heractiveren bestaat vandaag niet:
het wijzig-schema van een optie kent alleen label en volgorde (`OptieUpdate`,
schemas/checklistconfig.py:217-223) en er is geen route voor. Wat er precies voor nodig is, blijft
een bouwvraag.

### 16. In het opslaan-venster is geen keuze voorgeselecteerd

*Wat de gebruiker merkt:* de beheerder **kiest bewust** tussen verduidelijking en echte wijziging —
er staat niets voorgevinkt. Het venster benoemt per optie het gevolg in gewone taal, en zegt er
expliciet bij dat er **niets gewist en niets geblokkeerd** wordt.
*Waarom:* zou "verduidelijking" de standaard zijn, dan klikt iedereen die weg en is de hele knip
een formaliteit.
*Vangrail:* dezelfde lijn als de bestaande regel dat een vinkje een uitspraak is en nooit een
stille default.

### 17. De consultant mag de geschiedenis van een vraag inzien (nieuw, LI051)

*Wat de gebruiker merkt:* wie de vragenlijst mag lezen, mag ook de **wijzigingsgeschiedenis van
een checklistvraag** inzien — daar leest hij de oude formulering na (besluit 9). Hij leest die
lijst elke dag; dit volgt de bestaande lijn dat wie een ding mag zien, ook de geschiedenis van dat
ding mag zien (toegang volgt het object).
*Vangrail:* het afgeschermde tenant-logboek gaat hiermee **niet** open — dat blijft
beheerder/auditor-only; dit is een eigen, vraag-gebonden leesingang. Gemeten grond
(Checkpoint-bouwkant-V051 §M4): een vraagwijziging landt vandaag nergens waar de consultant kan
komen — niet in de componentgeschiedenis (geen component-anker) en niet in het voor hem gesloten
logboek.

### 18. Vandaag is het nulpunt (nieuw, LI051 — was subknoop 1)

*Wat de gebruiker merkt:* niets — en dat is het besluit: de bestaande antwoorden gelden als
gegeven op de **huidige** vraagstelling; pas een volgende wijziging levert een melding op.
*Waarom:* ze markeren als "onbekende formulering" zou betekenen dat honderden antwoorden opnieuw
gegeven moeten worden voor iets wat niemand fout heeft gedaan.
*Vangrail:* de invoering bevriest de huidige formulering bij elk bestaand antwoord — de enige
beschikbare vulling; het invoeringsmoment is het moment waarop de teller voor iedereen op nul
staat.

## Dichtgetimmerde sluippaden (invariant, geen aandachtspunt)

Uit de meting (M6), hier vastgelegd als onschendbaar:

1. **Nooit in het blok "dit moet nog".** Dat blok voedt de snapshot (`open_feiten`) bij het klaar
   verklaren; daar zou een verouderd antwoord alsnog gewicht krijgen in een besluit.
2. **Nooit de score legen** om "verouderd" uit te drukken. De score is de enige bron voor de
   beoordelingsstatus (ADR-013/016); legen zou de status terugdraaien. Besluit 4 sluit dit al uit
   (het antwoord blijft bestaan) — het staat hier zodat het ook bij de bouw niemand "handig" lijkt.

## Gevolgen — vijf teksten worden onwaar bij de bouw

*(Was "drie" — de lijst telde er al vier (gemeten: Checkpoint-bouwkant-V051 §M7, alle vier nog
aanwezig); nummer 5 komt uit besluit 10/LI051. Voor besluit 8 wordt géén code-tekst onwaar: de
bevestigingsknop is nooit gebouwd — de verwijzingen ernaar leefden alleen in dit ADR en zijn
hierboven herschreven.)*

1. De **VraagUpdate-docstring** ("bewerkbare (niet-tellende) velden… geen fan-out",
   `schemas/checklistconfig.py:132-134`) — een tekstwijziging krijgt gevolgen (markering/melding)
   en de docstring moet dat gaan zeggen.
2. De **optie-docstring** ("bewerken = soft-deactiveren via `actief`", `models.py:1053`) —
   label-hernoemen is een bewerking met een eigen regel (besluit 3), en deactiveren is geen
   eenrichtingsverkeer meer (besluit 15): het `OptieUpdate`-schema en het route-oppervlak kennen
   vandaag geen heractiveren en de beheer-UI toont "gedeactiveerd" zonder handeling — die teksten
   en oppervlakken gaan mee.
3. De **ADR-022-passage** "de herkomst toont de vraagtekst" (ADR-022:255) — bij evoluerende tekst
   toont de herkomst de **huidige** formulering; dat is na dit ADR een bewuste keuze die daar
   vermeld moet worden (de bevroren formulering leeft bij het antwoord, besluit 4).
4. De **grijze uitlegregel onder het antwoordtype-veld** ("Een reeds geconfigureerde vraag kan
   niet van antwoordtype wisselen (de server weigert dat)", ChecklistConfigBeheer.vue) — de
   beperking verhuist naar het veld zelf (dicht, met de reden in één zin, besluit 14); de
   voetnoot-vorm vervalt.
5. Het **tabbladgetal "Open punten (N)"** telt alleen het blok "dit moet nog"
   (`ComponentDetail.vue` — de `moetNog`-computed voedt het tablabel; de toelichting bovenin
   `OpenPuntenSectie.vue` beschrijft die koppeling) — met besluit 10 telt het getal beide soorten
   werk; telling én toelichting gaan mee.

## Open subknopen (bij de bouw te beslissen — geen besluiten hier)

*(Vijf eerdere subknopen zijn inmiddels besloten: waar de bewerking en de keuze in het beheerscherm
landen → besluit 13/16; optie-heractiveren → besluit 15; het nulpunt bij invoering → besluit 18;
de doving van de stille notitie → besluit 6; meerkeuze zonder gestructureerd antwoord → besluit 7 —
één sein voor iedereen die antwoordde, mét of zónder gekozen optie.)*

1. **De opslag-vorm in detail** (kolomnaam/plek van de bevroren formulering, de
   verouderd-markering, en wat heractiveren technisch vergt, besluit 15) — een bouwkeuze binnen de
   kaders van besluit 4/5/8/15, geen ontwerpvraag.
