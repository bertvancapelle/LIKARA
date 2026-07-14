# ADR-046 — Levensfase, bedoeling en uitstap per gebruiker

| | |
|---|---|
| **Status** | Besloten (LI040) |
| **Datum** | 2026-07-14 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-036 (grof→fijn organisatiegebruik — het anker van besluit 4) · ADR-038/041 (gebruik component-breed; organisatie verplicht) · ADR-043/044 (bedrijfsfunctie-as — de doorwerking waar dit alles voor bestaat) · ADR-045 (precedent: eigenschap + bewust-aanvinken-regel) · ADR-023 (plateau/relatiemodel — wordt kleiner) · ADR-009/LI057 (migratiepad) |
| **Grond** | `docs/Feitenrapport-levensfase-component-V040.md` · `docs/Feitenrapport-gebruik-en-uitstap-V040.md` · `docs/Feitenrapport-plateau-en-tranche-V040.md` |
| **Invariant (ongewijzigd)** | Score blijft de enige lifecycle-driver. Alles in dit ADR is registratie + leeslaag; de engine wordt niet geraakt. |

---

## Context — de vier vragen die LIKARA vandaag niet kan beantwoorden

Over één systeem zijn vier zinnen tegelijk waar, en ze horen elk op een eigen plek:

1. **"Het draait."** — de levensfase van het systeem.
2. **"Als het weggaat, vervangen we het."** — de bedoeling. Waar terwijl het gewoon draait.
3. **"Tiel stopt ermee en is aan het overstappen."** — het voornemen van één gebruiker.
   Voor Culemborg is dezelfde zin **onwaar**.
4. **"Tiel doet dit in de laatste golf, want alles hangt eraan."** — de volgorde.

Vandaag kan LIKARA er geen één fatsoenlijk beantwoorden. Erger: het draagt vier
half-antwoorden op drie plekken (de drie LI040-feitenrapporten):

- **`migratiepad`** — een *bestemmings*veld, feitelijk **dood**: 19/19 componenten op
  *onbekend*, twee passieve weergaveplekken (`ComponentDetail.vue:345`, kaart-popup),
  geen kolom, filter of signaal. De eigen velduitleg (`velduitleg.js:94-98`) zegt
  letterlijk dat het de *bedoeling* vastlegt, "los van of het al gebeurd is" — het veld
  ontkent zelf de fase-vraag.
- **`dispositie`** op het plateau-**lidmaatschap** — mengt twee assen: *uitfaseren* is
  fase-taal, *behouden/migreren/vervangen* zijn bestemmingen. Eén verplichte keuze
  (`PlateauDetailView.vue:172`) voor twee vragen — en de enige landschapsbrede lezer
  (de kaart) reduceert haar tot één waarde per component met een niet-deterministische
  eerste-wint (`landschapskaart_service.py:203-207`, `setdefault` zonder ORDER BY).
- **De registratiestatus** (concept → inventarisatie → klaargemeld) — gaat over *hoe ver
  ik ben met vastleggen*, niet over de werkelijkheid buiten LIKARA. Blijft ongewijzigd.

En de kern die alles kantelt: **"het zaaksysteem wordt uitgefaseerd" is een leugen zodra
drie van de vier gemeenten blijven.** Uitstappen is een feit van een **gebruiker**, niet
van een systeem.

---

## Besluit 1 — Levensfase: een feit over het component

Drie waarden: **in ontwikkeling** (bestaat, er wordt nog niet mee gewerkt) ·
**in productie** (draait) · **uitfaseren** (draait nog, maar gaat eruit).

- Een eigenschap van het component, **door een mens gezet. Nooit afgeleid** — niet uit
  gebruikstellingen, niet uit contracten, niet uit de registratiestatus.
- ⚠ **Engine-invariant, expliciet:** de engine leest uitsluitend
  `bepaal_lifecycle(huidige, aantal_gescoord, aantal_vragen, aantal_open_blokkades)`
  (`lifecycle_service.py:48-52`) — de levensfase komt daar niet in en gaat daar niet in.
  Het enige denkbare inlek-punt is verleiding, geen mechaniek ("fase = uitfaseren, dus
  zet de registratiestatus op X") — dat zou een tweede engine-poort zijn en wordt bij de
  bouw met het bestaande dubbele borgingspatroon (import-afwezigheidstest + live
  geen-mutatie-test) afgevangen. De levensfase is een geregistreerd feit dat kaart en
  signalering **lezen**; het voedt niets en stuurt geen score.

## Besluit 2 — Bedoeling: één plek, op het component (Weg B)

De vraag *"waar gaat dit heen als het weggaat?"* krijgt **één** antwoord, op het
component — de bestaande `migratiepad`-familie: *lift-and-shift · herbouw · vervangen ·
gedeeld*.

**Uitdrukkelijk besloten:**
- De waarde **`uitfaseren` verdwijnt uit de bestemmingslijsten** — het is geen
  bestemming maar een fase, en verhuist naar besluit 1.
- **Het plateau draagt geen eigen bedoeling meer.** De `dispositie` op het
  plateau-lidmaatschap vervalt als tweede bestemmingsveld.

**Motivering (vastgelegd — dit voorkomt terugkeer):** twee plekken om te zeggen waar een
systeem heen gaat, is een **tweede waarheid**. Vandaag merkt niemand dat, omdat beide
leeg zijn (migratiepad 19/19 *onbekend*; **0 plateaus** in de data) — maar dat is
toeval, geen ontwerp. Op de dag dat iemand ze allebei invult en ze verschillen, heeft
LIKARA géén antwoord op *"wat doen we hiermee?"*, maar twee.

⚠ **Wat we opgeven, eerlijk benoemd:** het vermogen te zeggen *"in scenario A vervangen
we het, in scenario B behouden we het."* Rechtvaardiging: dat vermogen wordt **nergens
benut** (geen enkele lezer gebruikt per-plateau-variatie; readiness negeert de
dispositie volledig) en wordt door de code **niet eens waargemaakt** — bij meerdere
plateaus toont de kaart niet-deterministisch de eerste
(`landschapskaart_service.py:203-207`). Het is een belofte die nooit is afgebouwd en die
intussen een tweede waarheid in stand houdt. Wil LIKARA later écht scenario's
vergelijken, dan wordt dat **bewust** ontworpen, met een kaart die het aankan — niet als
restant.

**Het plateau blijft wat het is:** een landschaps-brede momentopname
(`models.py:510-530` — naam + toelichting), met zijn gap-/deliverable-/bevestiging-
machinerie en readiness-cijfers ongemoeid. De contractuele bevestiging op het
lidmaatschap (wie/wanneer/aantal-gebruikers) is registratie, geen bedoeling — die blijft.

## Besluit 3 — Uitstap is een feit van de gebruiker, niet van het systeem

Op de **gebruiksrelatie** (organisatie × component) komt een **stand**:

| Stand | Betekenis |
|---|---|
| **Blijft** | geen voornemen |
| **Stopt — gepland** | besloten, nog niet begonnen |
| **Stopt — in uitvoering** | de migratie loopt; er wordt nog mee gewerkt |
| **Gestopt** | deze organisatie gebruikt dit niet meer |

- ⚠ **"In uitvoering" telt gewoon mee als gebruiker.** Zolang Tiel met het zaaksysteem
  werkt, moet het systeem in de lucht blijven en is de bedrijfsfunctie ondersteund. Een
  systeem afschrijven omdat er een besluit ligt, is de klassieke migratiefout: de
  stekker eruit terwijl er nog mensen inzitten. **De kaart toont wat er is; het
  voornemen staat ernaast.**
- **Altijd expliciet door een mens gezet.** LIKARA leidt een voornemen **nooit** af —
  het staat in een bestuursbesluit, niet in data.
- **Geen automatische doorwerking naar het component.** Staan alle gebruikers op
  *gestopt*, dan wordt de levensfase **niet** automatisch *uitfaseren*. LIKARA zegt
  *"geen gebruikers meer"*; de mens trekt de conclusie.
- **Wie de stand zette en wanneer is zichtbaar op de plek zelf** — zoals bij elk oordeel
  dat andermans veldwerk kan overschrijven (ADR-045 opvolgpunt 2: server-gestempeld op
  het feit, nooit uit de payload; de audit blijft het vangnet, nooit de leeslaag).

## Besluit 4 — Het anker: het grove organisatiegebruik (met de rekening erbij)

De stand hangt aan het **organisatiegebruik** (organisatie × component,
`models.py:431-464` — `UNIQUE(tenant, organisatie, applicatie)`), **niet** aan de
gebruikersgroep.

**Motivering — het getal beslist:** **25 van de 32** gebruiksfeiten in de dev-data zijn
*grof-only* (wel de organisatie, nog niet de afdeling). Op de gebruikersgroep zou het
voornemen voor driekwart van de relaties **onregistreerbaar** zijn — precies het normale
geval na een eerste workshop: je hoort eerst *wie*, pas veel later *welke afdeling*.
Bovendien valt het besluit op organisatieniveau: **een gemeente stapt uit, geen
afdeling.** Een voornemen per afdeling zou bij één vergeten afdeling melden dat de
gemeente *half* vertrekt. De consistentie van het anker is structureel geborgd: de groep
verwijst verplicht naar het grove feit (`gebruik_id` NOT NULL, ensure-get-or-create),
en de twee lagen lopen aantoonbaar niet uiteen (0 divergentie gemeten).

⚠ **De rekening (ADR-036-restpunt, nu blokkerend):** het grove organisatiegebruik heeft
**geen invoerroute** — geen formulier, en zelfs geen `maak`/`verwijder` in de api-client
(`api.js:198-200` kent alleen `lijstVoorOrganisatie`), terwijl POST en DELETE als
endpoint bestaan (`routes/organisatiegebruik.py:63,74`). Zonder die route is er **niets
om een stand aan te hangen**. **Die invoerroute hoort bij deze slice.**

## Besluit 5 — Zwaarte is afgeleid, nooit ingevoerd

LIKARA telt de organisaties per component en toont:
- **"nog 3 gebruikers"** (na een vertrek), of
- **"geen gebruikers meer"** — dit systeem wordt door niemand anders gebruikt.

**Taal (niet-onderhandelbaar):** géén *"valt om"*, géén rood. Er is niets kapot — er is
straks alleen niemand meer die het gebruikt, en vaak is dat precies de bedoeling
(licentie opzeggen). **Neutraal, amber, alleen bij afwijking** — hetzelfde register als
*"hier gebruiken we niets"* bij een bedrijfsfunctie (ADR-044 besluit 3): een bevinding,
geen alarm.

Telbron: het **grove feit** — uniek per organisatie×component, dus dubbeltellen kan
structureel niet; de kaart leest die bron vandaag al
(`landschapskaart_service.py:108-109, :331-339`). Read-only afgeleid — **geen opgeslagen
status** (een opgeslagen zwaarte zou een tweede waarheid zijn die bij één gemiste
bijwerking gaat liegen).

## Besluit 6 — Tranche: logische groepering, geen planningstool

Een uitstap duurt maanden en is **geen big bang**. De tranche groepeert wat samen
gebeurt: **naam + volgorde**, periode **optioneel** als indicatie.

- **Grens (hard):** géén mijlpalen, géén afhankelijkheden tussen taken, géén
  voortgangspercentages, géén capaciteit, géén doorlooptijden. **LIKARA registreert de
  stand van een feit, niet de voortgang van een project.**
- **De tranche is organisatie-gebonden** (Tiel stapt uit in 3 tranches); de stand blijft
  **per gebruiksrelatie** — in tranche 2 kan één systeem al *gestopt* zijn terwijl de
  rest nog loopt.
- **"Nog niet ingedeeld" is het signaal** — sterker dan een ontbrekende datum: een
  component dat in géén enkele golf zit, is een **vergeten systeem**.
- **Waarom geen datums:** de consultant hoort in de workshop volgorde en samenhang
  (*"belastingen eerst, zaaksysteem als laatste, want alles hangt eraan"*), geen agenda.
  Datums verbergen die logica; tranches leggen haar vast.

**Het plateau is NIET de tranche** (feitenrapport plateau-en-tranche, oordeel 3): het is
landschaps-breed, zonder volgorde (geen veld, geen keten — alleen de gap verbindt
precies twee standen), zonder periode, zonder organisatie-anker. **Wat kapot zou gaan
bij hergebruik — vastgelegd zodat het idee niet terugkeert:** tranche-plateaus zouden in
de gap-pickers en de deliverable-realisatieketen opduiken en in de readiness-cijfers
meetellen; de kaart-badge zou tranche-lidmaatschap als "migratieplaatsing" tonen (en bij
meervoud niet-deterministisch kiezen); elk tranche-lid zou een verplichte — betekenisloze
— dispositie moeten krijgen; en volgorde/periode/organisatie zouden als kolommen óók op
baseline-/doel-plateaus belanden.

## Besluit 7 — Het scherm: muteren waar je kijkt

Op het component staan **alle gebruikers als eigen regel**, elk met een eigen stand —
geen samengevouwen *"3 blijven"*. Eén blik toont wie afwijkt (amber); de rest blijft
rustig.

- De consultant **muteert de stand op de rij** (keuzeveld), en kiest de tranche erbij
  zodra de stand *stopt* is. Geen omweg via een ander scherm.
- **Bulk hoort bij het besluit, niet bij het component:** twaalf systemen van Tiel in
  één keer op *gepland* zetten doe je bij **Tiel**, met **bewust aanvinken** — niets
  voorgevinkt; een vinkje is een uitspraak, en het overschrijft andermans veldwerk
  (ADR-045 besluit 7, onverkort).
- **Eén feit, twee ingangen:** dezelfde gebruiksrelatie-rij is zichtbaar vanaf het
  component (*"wie gaat er weg bij dit systeem"*) en vanaf de organisatie (*"waar staat
  Tiel"* — de bestaande `GebruikteApplicatiesSectie`-plek). Geen tweede registratie.
- De **afdeling** staat erbij, óók als hij *onbekend* is — dat is geen fout maar de
  normale stand na een eerste workshop (25/32 grof-only).

## Besluit 8 — Het liegende signaal wordt mee-gerepareerd

Het signaal `component_zonder_gebruikersgroep` telt vandaag **serving-relaties**
(`registratiegaten_service.py:229-242`) en vuurt daardoor **onterecht op 4 componenten
die wél geregistreerd (grof) gebruik hebben** (BRP, Gegevensmakelaar, Sociaal domein
suite, Zaakafhandelcomponent — elk met 4 grove gebruikers en 0 groepen).

Dat is dezelfde fout die LIKARA overal weert: **leeg ≠ fout.** Een consultant die dat
signaal ziet, zoekt naar iets wat allang geregistreerd staat — en verliest vertrouwen in
**álle** signalen. **Eén liegend signaal besmet de rest.** Het signaal telt voortaan op
het **grove feit** — dezelfde telbron als besluit 5; het is dezelfde vraag: *wat telt
als "dit component wordt gebruikt"?* Repareren in deze slice.

---

## De afbakeningstabel (de kern van dit ADR)

| De vraag van de gebruiker | Het antwoord staat op | Status |
|---|---|---|
| Draait het, gaat het eruit, of komt het nog? | **Levensfase** — component | **nieuw** (absorbeert `dispositie = uitfaseren`) |
| Waar gaat het heen als het weggaat? | **Bedoeling** (`migratiepad`) — component | bestaat; *uitfaseren* verdwijnt eruit; **enige** bestemming |
| Wie stopt met dit component, en waar staat dat? | **Stand** — gebruiksrelatie (organisatie × component) | **nieuw** |
| In welke golf? | **Tranche** — bij de uitstappende organisatie | **nieuw** |
| Hoe zwaar is dat? | **afgeleid** (nog N gebruikers / geen gebruikers meer) | **niet geregistreerd** |
| Hoe ver ben ik met vastleggen? | **registratiestatus** — ongewijzigd | bestaat |
| Hoe ziet het landschap er straks uit? | **plateau** — momentopname, zonder eigen bedoeling | bestaat, wordt **kleiner** |

---

## Invarianten

- **Engine onaangeroerd** — score blijft de enige lifecycle-driver; dubbele borging bij
  de bouw (import-afwezigheid + live geen-mutatie).
- **Geen tweede waarheid** — elke vraag heeft precies één plek; afgeleide feiten worden
  **nooit** opgeslagen.
- **LIKARA gokt nooit over een voornemen** — dat is een menselijk besluit.
- **Generiek platform** — er komt géén "uittreding", géén deelnemersregister, géén
  samenwerkingsverband-begrip. *"Een organisatie stopt met het gebruik van een
  component"* is de generieke vorm; een gedeelde-dienstenorganisatie is gewoon een
  tenant waarin dat twaalf keer tegelijk gebeurt. **BvoWB is voorbeelddata, geen
  platformfunctie.**
- **Ontwikkelmodus** — uitsluitend testdata; "migratie" = alembic-stap + reseed, nooit
  een databehoudvraagstuk.

---

## Gevolgen (benoemd, niet gebouwd — de bouwopdracht kiest de vormen)

1. **Vier registratie-oppervlakken**: de levensfase op het component (formulier/detail/
   lijst/kaart), de stand + tranche op de gebruiksrelatie (besluit 7, twee ingangen),
   de tranche-groepering bij de organisatie, en de afgeleide teller (besluit 5).
2. **De grove-invoer-slice** (besluit 4): formulier + `maak`/`verwijder`/
   `lijstVoorApplicatie` in de api-client (endpoints bestaan al).
3. **De dispositie-afbouw** (besluit 2) raakt: het verplichte veld in de
   lid-koppel-dialoog (`PlateauDetailView.vue:172`), de kenmerk-definitie op de
   `aggregation`-relatie (`seed_componentconfig.py`), de dispositie-dimensie in de
   relatiekenmerk-catalogus (soft-deactivate — historische waarden blijven resolvebaar),
   en de kaart-badge `plateau_dispositie` (het eerste-wint-gedrag verdwijnt daarmee).
4. **`uitfaseren` uit `migratiepad`** — technisch feit dat de bouwopdracht moet dragen:
   `migratiepad` is een PostgreSQL-enum en **PostgreSQL kan enum-waarden niet droppen**;
   "verdwijnen" is dus óf een enum-recreate (het `partij_aard_enum`-`burger`-precedent,
   migratie 0053: drop-CHECKs → rename → create → USING-swap → herbouw) óf de waarde
   ongebruikt laten staan + app-side weren (schema-allowlist). Beide vormen bestaan in
   de codebase; de keuze is bouwwerk. Datakost: nul (19/19 *onbekend*).
5. **Vorm-keuzes die dit ADR bewust bij de bouwopdracht laat** (langs bestaande,
   genoemde precedenten — geen nieuwe ontwerpruimte): enum vs. platform-catalogus voor
   levensfase en stand (migratiepad- vs. componentrol-recept), verplicht-met-default vs.
   nullable-registratiegat, en de tranche-tabelvorm (eigen tenant-tabel à la
   organisatiegebruik ligt gezien besluit 6 het dichtst bij; het plateau is uitgesloten).
6. **Seed**: het BvoWB-scenario gaat het nieuwe verhaal vertellen (Tiel stapt uit in
   tranches; standen per gebruiksrelatie; levensfasen gevuld) — zonder seed is geen
   enkele browsercheck van dit spoor mogelijk (0 plateaus, 19/19 *onbekend* vandaag).

---

## Alternatieven overwogen

1. **Levensfase in `migratiepad` aanvullen** — verworpen: het veld is een bestemming en
   zegt dat zelf (velduitleg). De vragen zijn **orthogonaal**: *"in productie én wordt
   vervangen"* is de normale toestand van een migratieportfolio; één veld kan dat alleen
   via combinatiewaarden — een emmer.
2. **"Uitfaseren" als status op het component laten volstaan** — verworpen: onwaar
   zodra één van vier gemeenten vertrekt; de uitstap is een gebruikersfeit.
3. **Voornemen op de gebruikersgroep** — verworpen: onregistreerbaar voor 25/32
   relaties (grof-only); het besluit valt op organisatieniveau; per-afdeling-registratie
   meldt bij één vergeten afdeling een half vertrek.
4. **Datums in plaats van tranches** — verworpen: verbergt volgorde en samenhang; "geen
   datum" is administratief, "nog niet ingedeeld" is een **vergeten systeem**.
5. **Plateau hergebruiken als tranche** — verworpen: landschaps-breed, geen
   volgorde/periode/organisatie-anker; vervuilt gap/deliverable/readiness (zie
   besluit 6 voor wat er kapot zou gaan).
6. **Weg A (fase eruit, dispositie-bestemming laten staan)** — verworpen: houdt een
   tweede bestemmingsveld in stand dat op de dag van gebruik gaat liegen.
7. **Opgeslagen zwaarte** ("valt om"-vlag) — verworpen: afleidbaar, dus tweede waarheid.
8. **Automatische levensfase bij nul gebruikers** — verworpen: LIKARA neemt geen besluit
   namens een mens.
9. **Voortgangspercentage per migratie** — verworpen: dat is een
   projectmanagementtool, geen registratie van een feit.

---

## Opvolgpunten (ook opgenomen in `docs/OPVOLGPUNTEN.md`)

1. **Bestaande dev-data**: 0 plateaus, `migratiepad` 19/19 *onbekend* — de seed moet het
   nieuwe verhaal vertellen (seed volgt de user story); elke browsercheck rond dit
   onderwerp heeft die seed nodig.
2. **Kaart-eerste-wint** (`landschapskaart_service.py:203-207`, geen ORDER BY) —
   verdwijnt met besluit 2 (de badge-bron vervalt); bij de bouw bevestigen.
3. **Stale model-docstring** (`models.py:442-443` zegt "componenttype='applicatie'
   app-side geborgd") — het gebruik-slot is sinds ADR-041 component-breed
   (`organisatiegebruik_service.valideer_component`); corrigeren bij de bouw.
4. **Spook-gebruik** — een org-wissel of groep-delete laat het oude grove feit staan en
   dat is alleen via de kale DELETE-API opruimbaar; met de invoerroute van besluit 4
   komt er een verwijder-affordance, maar het achterblijf-gedrag zelf is een los
   opvolgpunt.
5. **Contract-datums liggen ongebruikt** (begin/eind/vernieuwing bestaan op `contract`;
   geen enkele afleiding leest ze) — een aflopend contract is een impliciet
   uitstap-signaal. Eigen spoor.
6. **Bedrijfsfunctie-doorwerking** — *"2 bedrijfsfuncties raken zonder ondersteunend
   systeem als Tiel vertrekt"* is de bestuurlijke uitkomst waar dit alles voor bedoeld
   is. Zichtbaar zodra componenten aan functies hangen: **harde ontwerpeis voor
   gate 2/3** (dezelfde signaal-familie als "gedragen door een noodgreep", ADR-045
   besluit 2, en het gap-signaal per plaatsing, ADR-044 besluit 4).
