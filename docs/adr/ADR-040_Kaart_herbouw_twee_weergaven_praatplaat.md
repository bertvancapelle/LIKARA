# ADR-040 — Kaart-herbouw: twee gerichte weergaven + object-centrische praatplaat-motor

**Status:** Deels geland — **Fase 1 gebouwd** (V034); vervolgfasen open (zie "Gebouwde realiteit" + fasering)
**Datum:** 2026-07-06 (voorstel) · 2026-07-07 (Fase 1 geland, V034)
**Vervangt:** **ADR-025** (Applicatie-centrische praatplaat) — die wordt in zijn geheel *Superseded*.
Deze ADR neemt de praatplaat-gedachte volledig over en verbreedt haar (élk object centreerbaar, twee
weergaven, expliciete interactie- en render-laag).
**Relatie:** Leeslaag bovenop het getypeerde relatiemodel (ADR-023) en het partijenregister (ADR-024).
Bouwt op de bestaande, gezonde kaart-backend (`landschapskaart_service`, 9 read-only edge-typen).
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt niet geraakt.
Puur read-only, afgeleid.

---

## Context / aanleiding

De Landschapskaart moet twee wezenlijk verschillende gebruikersvragen dienen:

1. **Overzicht** — "hoe hangt het landschap samen": wie gebruikt wat, hoe koppelt het, rustig kunnen
   verkennen en filteren.
2. **Impact** — "ik pak component X om aan te passen (uitfaseren, verhuizen, vervangen) — wat raakt het?
   Welke gebruikers, afdelingen, organisaties, contracten, leveranciers en infrastructuur hangen eraan?"

Vandaag perst één canvas beide vragen door **vijf modi** (leeg/geheel/ego/impact/overzicht), impliciet
afgeleid uit de set-grootte, met modus-afhankelijke layouts die in elkaar overlopen. Die alleskunner is
door opeenvolgende uitbouw **fragiel** geworden. Twee sessies zijn besteed aan symptomen van dezelfde
oorzaak: een wankele teken-cyclus.

**Bewijs (deze sessie, read-only vastgesteld):**
- **Flits-diagnose:** bij het openen tekent de kaart twee keer — Render 1 (concentric) toont de lijnen,
  waarna de node-set nog groeit (scope-balk-settle) en Render 2 in de fcose-fallback valt, precies het
  pad met de edges-onzichtbaar-render-bug → de lijnen "flitsen op en zijn weg".
- **Inventarisatie:** het *fundament* is gezond — de backend-edge-projectie (9 read-only edge-typen,
  dubbel engine-geborgd, goed getest) klopt, en de ring-data per objecttype (component, contract,
  leverancier, afdeling, persoon/rol, infra) bestaat vrijwel volledig. Wat wankelt is uitsluitend de
  **teken-cyclus + de modus-logica + de scope-balk-settle** in de frontend.

Conclusie: geen totale ombouw en geen andere graafbibliotheek — een **frontend render-/interactie-
herbouw** op het bestaande, stabiele data-fundament. Dit is het goedkoopste moment: ontwikkelmodus,
alleen testdata, geen gebruikers.

---

## Besluit (kern)

1. **Twee gerichte weergaven, elk met één taak** — in plaats van één modus-alleskunner:
   - **Overzicht** — de brede plaat: hoe hangt het landschap samen; verkennen en filteren; meerdere
     objecten; gelaagde layout.
   - **Impact-praatplaat** — één object centraal met zijn directe kring eromheen (diepte 1, radiaal);
     doelgericht "wat raakt een verandering aan dit object".
   De weergaven **schakelen door**: in het Overzicht een object kiezen → "toon impact" → je landt in
   diens praatplaat.

2. **Eén praatplaat-motor; per objecttype een eigen ring-definitie.** Élk object is centreerbaar (component,
   contract, leverancier, afdeling, persoon, rol, infrastructuur). De motor weet per objecttype welke
   kring eromheen hoort. Een nieuw objecttype toevoegen = "geef zijn ringen op", niet "herbouw de kaart".

3. **Vier ringen om een component** (het eerste en belangrijkste objecttype):
   - **Gebruikt door** — organisaties, afdelingen, gebruikersgroepen die het component gebruiken.
   - **Beheer** — intern: afdeling/persoon met hun beheerrol.
   - **Contracten & leveranciers** — de contracten die gelden, met de leverancier erachter.
   - **Infrastructuur & koppelingen** — waarop het draait (`draait_op`) en met welke applicaties het
     koppelt (flow).
   (Ring-definities van de overige objecttypes: zie open subknopen.)

4. **Interactielaag — consistent voor elk objecttype:**
   - **Eén klik = inspecteren, zonder de plaat te verlaten:** de relaties (lijnen) van het object lichten
     op, de rest **dimt**, en een **verplaatsbare popup** toont de kern-details + de relaties in leesbare
     taal, met een link naar de volledige detailpagina.
   - **Dubbelklik = hercentreren:** het object wordt het nieuwe centrum met zijn eigen ringen (diepte 1).

5. **Deterministische teken-cyclus als expliciet ontwerpprincipe.** Elke weergave heeft één, voorspelbaar
   teken-gedrag: één graaf-opbouw, één layout, geen dubbele render, geen set-grootte-afgeleide modus-
   omschakeling, geen layout-fallback die de verkeerde kant kiest. De radiale praatplaat (vaste ring-set
   rond één centrum) lost de flits-oorzaak structureel op — geen groeiende node-set tussen twee renders.

6. **Cytoscape behouden.** De problemen zijn aansturing/orkestratie, geen limiet van de bibliotheek. Een
   ego-plaat op diepte 1 is radiaal en legt zichzelf netjes; het overzicht is een gelaagde plaat. Geen
   bibliotheekwissel.

7. **Gewone taal, geen ArchiMate-notatie.** Relaties worden hertaald (gebruikt, draait op, valt onder
   contract, wordt beheerd door), zoals in ADR-025 al besloten. Publiek: niet-technisch (teamleider,
   proceseigenaar, bestuurder) én de beheerder die een verandering doordenkt.

---

## Wat behouden blijft vs. opnieuw (de eerlijke knip)

**Behouden (solide fundament):**
- De backend-edge-projectie (`landschapskaart_service`, 9 read-only edge-typen, dubbel engine-geborgd).
- De ring-data-reads per objecttype (bestaan vrijwel volledig).
- Het ring-concept + de edge-zichtbaarheid per ring.
- Herbruikbare frontend-primitieven: de highlight (hl-node/hl-edge), het versleepbare paneel, de
  client-side filter-predicaten.

**Opnieuw (fragiel/opgestapeld):**
- De teken-cyclus (dubbele render, `vorigePosities`-mix-tak, fcose-fallback, debounce-coördinatie,
  `setTimeout`-fit) en de verwevenheid met de toestand-geschiedenis.
- De set-grootte-afgeleide modus-computed (5 modi) → vervangen door de expliciete tweedeling.
- De fcose-render (edges-onzichtbaar) en de scope-balk-settle.

**Backend-impact:** minimaal en additief — hooguit twee afgeleide, read-only edges (**afdeling → applicatie**
en **contract → leverancier**), volgens het bewezen spiegelpatroon van de eigenaar-/gebruikt-edge.
**Geen schema, geen migratie, engine onaangeroerd.**

---

## Invarianten

- **Read-only / engine onaangeroerd.** Afgeleide inzicht-/communicatielaag bovenop bestaande relaties;
  voedt de engine niet. Dubbele engine-borging per slice.
- **Geen afgeleide relaties in de DB** (ADR-023 besluit 7): de kaart *toont* bestaande, expliciet
  geregistreerde relaties (en projecteert grove feiten als read-only edges); ze verzint er geen in het
  datamodel.
- **Een plaat is zo goed als de registratie.** Lege relaties → lege ring. Bijvangst: registratiegaten
  worden zichtbaar (bv. de "nog niet verfijnd"-markering).
- **Structureel boven conventioneel.** Eén deterministische render-eigenaar in plaats van opgestapelde
  fallbacks.

---

## Gevolgen

- **ADR-025 vervalt** (Superseded); deze ADR is het enige geldige anker voor de kaart. De historie van
  025 blijft leesbaar via de statusverwijzing.
- **De flits-bug en de impact-edges-onzichtbaar-bug** (voorheen top-5 #2) worden opgelost dóór de
  herbouw, niet als losse pleister.
- **De LI033b-bouw** (overzicht-modus + gebruikt-lijn + impact-inzoom + sub-picker-opruiming) staat
  ongecommit; hij leunt op een betrouwbaar tekenende kaart en wordt **opgenomen in / vervangen door** de
  herbouw i.p.v. apart gecommit. (Zie fasering.)
- **Opgeslagen views** bewaren alleen een set-id-lijst → een herbouw van modi/interactie breekt de data
  niet; en het is toch testdata.
- **De scope-balk** ("organisaties in beeld") is in de radiale praatplaat waarschijnlijk overbodig; de
  bijbehorende settle-fragiliteit vervalt mee (zie open subknopen).
- **RBAC/audit:** ongewijzigd — hergebruik `ARCHITECTUUR.LEZEN`; de nieuwe afgeleide edges vallen onder de
  bestaande leesrechten.

---

## Gebouwde realiteit — Fase 1 (V034, 2026-07-07)

Wat daadwerkelijk is gebouwd (met de afwijkingen t.o.v. het voorstel, en de reden):

- **Render-eigenaar deterministisch, fcose weg** (`bf5c287`). Eén opbouw → één layout → fit via de
  layout-`stop`-callback; de modus-computed/positie-behoud/preset-fcose-mix zijn verwijderd. Lost de
  flits- en edges-onzichtbaar-bug structureel op.
- **Tweedeling met expliciete weergave-state + schakelaar** (2a, `e8fe7d3`). `weergave: 'overzicht' |
  'praatplaat'` vervangt de set-grootte-afgeleide modus (dunne `modus`-adapter blijft voor de leesplekken).
  De **Impact-verkenner is afgeschaft** (`IMPACT_RINGEN`/`drillPad`/`impactDirect` verwijderd) — de
  praatplaat vervangt haar. "Hele landschap" = Overzicht zonder geseed centrum.
- **Voorspelbare organisatie-scope** (2b, `e7f74ef`). De reactieve auto-settle is vervangen door een
  **eenmalige deterministische seed** ("alle aanwezige orgs aan" bij elke load; init-semantiek **A**). De
  scope-balk staat **alleen op Overzicht**; op de praatplaat is de scope **inert** (geen stille
  organisatie-verberging). → **lost open subknoop 4 op.**
- **Afgeleide gebruikt-lijn** (3-1, `559a34c`). Read-only edge organisatie→applicatie, **1:1 spiegel van
  de eigenaar-edge** (dangling-guard + scope-add van de gebruiker-org). "Dragend in impact" is vervuld via
  de **ego-kring** (`gebruikt` is een default-AAN ring die meedoet in `_burenVan`) — **geen aparte
  IMPACT_RINGEN-bedrading** (die is afgeschaft). Bezit + gebruik = **twee lijnen** (bewust). De dode
  afdeling-sub-picker in `KaartBeginscherm` is verwijderd.
- **Layout-herziening** (samen in `559a34c`). De gebruikt-lijn (dichtere graaf) onthulde een pre-existing
  layout-fout (knopen vielen samen → leeg canvas). Besluiten, geankerd:
  - **Overzicht = `grid`** (built-in, **centrumloos, deterministisch**). **`cose` bewust afgewezen**:
    niet-deterministisch en dezelfde force-familie als het verwijderde `fcose` (edges-onzichtbaar-bug).
    Een concentric op een centrumloos Overzicht gaf een stervorm → daarom een centrumloze layout.
  - **Praatplaat = `concentric` + vensterverhouding-volgende ellips.** Post-layout schaling in de
    `stop`-callback (leest `cy.width()/height()`); **alleen uitrekken langs de langere as, nooit
    comprimeren** (geen nieuwe overlap), **mild geclamped (≤1.7)** zodat weinig buren een lichte ellips
    geven.
  - **Niet-geanimeerd** (`animate:false`): de van-(0,0)-animatie liet nodes op een dichte graaf
    samenvallen. **Leesbaarheidsmaatstaf A:** namen op knopen én tekst op lijnen leesbaar zonder inzoomen;
    grotere knopen (font 11→14); een grote set mag groter zijn dan het venster (pannen; **"Centreer"** =
    terug naar geheel).
  - **Layout-invariant:** *"geen twee nodes op dezelfde positie"* — geborgd via `frontend/tests/kaartLayout.test.js`
    (echte cytoscape: distinct + deterministisch; praatplaat-ellips breder-dan-hoog).
- **Overgang Overzicht→praatplaat** (open subknoop 6): `drillNaar`/deep-link/één-component-kiezen →
  praatplaat; dubbelklik = hercentreren. → **subknoop 6 grotendeels ingevuld.**
- **LI033b bleek grotendeels al geland** vóór de herbouw (handoff-composable, org-bron
  `lijst_voor_organisatie`, `grofOnlyIds`, "toon impact"=`drillNaar`). Alleen de **gebruikt-edge**,
  de **gebruikt-ring** en de **sub-picker-opruiming** waren nieuw (3-1). De stash `stash@{0}` blijft
  geparkeerd als referentie (Berts beslissing over droppen — niet zelf gedaan).

**Nog niet gebouwd (vervolgfasen):** de volledige interactie-basis (klik=highlight+dim+popup), de 4
component-ringen volledig, overige centreerbare objecttypes, terug/vooruit-navigatie (uitgesteld, niet
geschrapt), scope-B-verfijning. Zie OPVOLGPUNTEN.md + de fasering hieronder.

---

## Open subknopen (te beslissen vóór/ tijdens de bouw — met voorlopige default)

1. **Ring-definities per niet-component-objecttype.** Wat hoort er om een *contract*, *leverancier*,
   *afdeling*, *persoon/rol*, *infrastructuur*? *Default: per type de reads uit de inventarisatie (§3);
   exacte ring-indeling per type beslissen bij de betreffende fase — component eerst.*
2. **Inhoud van de klik-popup per objecttype.** Welke kern-velden + welke "relaties in leesbare taal".
   *Default: naam/type/status + een korte, per-type relatie-samenvatting + "open volledige pagina".*
3. **Filtering op Overzicht vs. praatplaat.** Welke van de bestaande attribuutfilters (type/leverancier/
   hosting/lifecycle/rol/BIV) blijven op Overzicht; op de praatplaat stuurt vermoedelijk alleen de
   ring-keuze. *Default: attribuutfilters op Overzicht; praatplaat via ring-keuze, geen attribuutfilters.*
4. **Scope-balk.** Vervalt die volledig, of blijft een lichte org-scope op Overzicht? *Default: vervalt
   op de praatplaat; op Overzicht heroverwegen zonder de auto-settle-fragiliteit.*
5. **Context-ringen buiten de 4** (samenstelling comp↔comp, eigenaar, organisatiestructuur). Tonen als
   optionele context-ring of buiten de component-praatplaat houden? *Default: als optionele context-ring
   (default uit), niet in de kern-4.*
6. **Overgang Overzicht → praatplaat.** Precieze affordance (node-actie / popup-knop "toon impact").
   *Default: knop in de klik-popup + dubbelklik = hercentreren binnen dezelfde weergave-familie.*
7. **Diepte.** Praatplaat vast op diepte 1 (hercentreren om verder te wandelen), of instelbaar? *Default:
   vast diepte 1 — leesbaarheid boven volledigheid; wandelen via hercentreren.*

---

## Bouw-fasering (indicatief, ná besluitvorming)

Frontend-zwaar; de backend is stabiel en additief. Werktree-discipline: één slice tegelijk, gate per
slice, browsercheck vóór commit (de render is alleen in de browser te verifiëren).

1. **Fundament — deterministische teken-cyclus + de tweedeling.** De nieuwe render-eigenaar (één opbouw,
   één layout per weergave), de twee weergaven (Overzicht + praatplaat-motor-skelet), en het opruimen van
   de modus-computed/fcose-fallback/scope-settle. Lost de flits- en edges-onzichtbaar-bugs structureel op.
   Neemt de bruikbare delen van LI033b hierin op (overzicht-gedachte, gebruikt-lijn) i.p.v. die apart te
   committen.
2. **Component-praatplaat — de 4 ringen** volledig, met de interactielaag (klik = highlight+dim+popup,
   dubbelklik = hercentreren). De kernvraag "wat raakt component X" werkt end-to-end.
3. **Twee afgeleide edges** waar nog nodig (afdeling→app, contract→leverancier) — read-only spiegel van
   eigenaar/gebruikt; geen schema.
4. **Overige objecttypes gefaseerd centreerbaar** (contract, leverancier, afdeling, persoon/rol, infra) —
   elk een ring-definitie op de bestaande motor.
5. **Overzicht afronden** — filtering die overleeft, verkennen, doorschakelen naar impact.
6. **Opschonen** — verweesde modi/paden/tests, scope-balk-beslissing, opgeslagen-views-gedrag.

Elke slice read-only/afgeleid, met engine-onaangeroerd-borging en de gangbare gate-discipline.

---

## Alternatieven overwogen

- **De bestaande alleskunner-kaart incrementeel blijven repareren** (per bug een pleister). Afgewezen:
  twee sessies bewezen dat de bugs symptomen zijn van één oorzaak (de wankele teken-cyclus + de
  set-grootte-afgeleide modus). Blijven dweilen houdt de fragiliteit in stand.
- **Een andere graafbibliotheek** (weg van Cytoscape). Afgewezen: de knelpunten zijn aansturing/
  orkestratie (dubbele render, layout-keuze), geen limiet van de bibliotheek; een radiale ego-plaat op
  diepte 1 legt Cytoscape probleemloos. Een wissel voegt risico toe zonder het echte probleem te raken.
- **Eén universele modus behouden en alleen de fcose-render herbouwen.** Afgewezen: dat lost de
  edges-onzichtbaar-bug op maar niet de onderliggende verwarring van twee gebruikersvragen in één canvas;
  de tweedeling (Overzicht vs. praatplaat) is de eigenlijke functionele winst.
