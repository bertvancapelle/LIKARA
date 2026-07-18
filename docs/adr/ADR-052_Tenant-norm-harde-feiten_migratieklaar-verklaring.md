# ADR-052 — Tenant-norm voor harde componentfeiten + verrijkte migratieklaar-verklaring

| | |
|---|---|
| **Status** | Aanvaard — **slices 1–3 gebouwd** (`fae7593` norm-opslag/-toetsing · `626dc76` "bewust geen" · `7e2ff25` verrijkte klaarverklaring). **Slice 4 gesplitst (besluit 14, bindende volgorde): 4a — het onderscheid tussen "bewust over de lat" en "de lat is verschoven" + het werkvoorraadsignaal (besluiten 8–11); 4b — het norm-beheerscherm (besluiten 12–13). Beide OPEN (LI045).** Subknopen 1–5 + besluiten 8–14 besloten (zie onder). |
| **Datum** | 2026-07-17 (uitgebreid 2026-07-18, LI045 — besluiten 8–14) |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-027 (component-klaarverklaring — dit verrijkt haar) · ADR-013/016 (lifecycle-engine — ongemoeid) · ADR-035 (registratiegat-signalen) · ADR-028 (BIV/componentrol) · ADR-044/049 ("bewust niets" op de bedrijfsfunctie-plek) · ADR-006 (append-only audit) · OPVOLGPUNTEN L1a (ijkpunt) + LI043-1 (beoordelingsgrondslag) |
| **Grond** | `docs/Checkpoint-tenant-norm-harde-velden-en-klaarverklaring-V044.md` (read-only) · `docs/Checkpoint-norm-beheerscherm-V045.md` (read-only, slice 4) · `docs/Meting-veldaanduiding-norm-V045.md` (read-only, slice 4c) |
| **Invariant (onschendbaar)** | **De checklist-score blijft de enige lifecycle-driver.** De tenant-norm én de klaarverklaring hangen *náást* de engine: ze gaten een menselijke verklaring, niet de machinale `lifecycle_status`. |

---

## Context / aanleiding

Vandaag betekent "migratieklaar" twee dingen die vaak samenvallen maar niet hetzelfde zijn:

- **De engine-status** `migratieklaar` (ADR-013/016): alle checklistvragen beantwoord én geen
  openstaande blokkade. Puur checklist-gedreven.
- **De menselijke klaarverklaring** (ADR-027): een coördinator/consultant verklaart een component
  klaar — engine-gescheiden, mag óók bij <100% scoring, met een reeds bestaand "afwijking"-begrip
  (klaar verklaard terwijl de checklist niet compleet is).

Wat ontbreekt: de gemeente kan niet vastleggen **welke feitelijke gegevens van een component bekend
moeten zijn** voordat het klaar verklaard mag worden. De checklist geeft inhoudelijk inzicht; de
*harde* feiten (eigenaar, BIV, koppelingen, contract, …) staan er los bij als read-only
registratiegat-signaal, zonder norm en zonder stem in de verklaring. Deze ADR sluit dat gat — met de
laagst mogelijke drempel, want inrichtingsdwang vooraf is precies wat LIKARA vermijdt.

## Besluit (kern)

1. **De tenant stelt per hard feit een norm: verplicht-ja/nee** ("moet dit bekend zijn voordat dit
   component migratieklaar verklaard mag worden?"). **MVP: geen weging** — alleen ja/nee. (De
   gewogen waarde-norm is een apart, groter spoor; zie §Verhouding.)

2. **"Compleet" = feit *vastgesteld*, niet veld *gevuld*.** Een verplicht feit telt pas als het een
   **echt antwoord** draagt. Daarmee tellen als *niet* vastgesteld: een leeg veld, een
   **sentinel-waarde** die "geen antwoord" betekent (bv. `hostingmodel = onbekend`), én — bij de
   relationele feiten — "er is nog nooit naar gekeken". Dit is de smalste, eerlijke vorm die de
   placeholder-val vermijdt zonder een volledige waarde-norm te bouwen.

3. **De norm dekt eigen velden én relationele feiten.** Naast eigen componentvelden (eigenaar,
   verantwoordelijke, BIV, hosting, levensfase, bedoeling, …) kan de tenant ook **koppelingen** en
   **contract/leverancier** verplicht stellen. Voor die relationele feiten is "nul" dubbelzinnig, dus
   krijgt de consultant een uitspreekbaar **"bewust geen"** — een volwaardig antwoord, streng
   onderscheiden van "nog niet gekeken" (dezelfde vorm als de "bewust niets"-bevinding op de
   bedrijfsfunctie-plek, ADR-044/049). **Voor de bedrijfsfunctie bestaat "bewust geen" al; voor
   koppelingen en contract nog niet — dat is nieuw bouwwerk in het MVP van deze norm.**

4. **De consultant verklaart; de norm is een lat, geen poort.** Het menselijk oordeel wint. De
   consultant ziet de checklist-status én de tenant-norm (welke verplichte feiten nog niet
   vastgesteld zijn) en verklaart op grond daarvan — inclusief het bewuste besluit *"niet alles is
   vastgesteld, maar dit is voldoende, ik verklaar het klaar."* De machine houdt niets tegen.

5. **Bevestiging alléén bij afwijking van de norm.** Verklaart de consultant klaar terwijl alle
   verplichte feiten vastgesteld zijn → **licht, geen drempel** (conform ADR-035/L1a: aandacht
   schaalt met gewicht). Ontbreekt er een verplicht feit → een **bevestiging die de openstaande
   feiten benoemt** en die de consultant **bewust accepteert** (of "eerst aanvullen" — geen
   doodlopend pad). De drempel hangt aan de **afwijking**, niet aan de handeling.

6. **Eén feit voedt het zichtbare badge én de log.** Het akkoord-met-open-feiten wordt vastgelegd op
   de klaarverklaring als een **snapshot van de openstaande verplichte feiten** + wie + wanneer.
   Daaruit leest:
   - het **badge** op het component ("klaar verklaard, maar N verplichte feiten open") — een **live
     her-afleiding** die vanzelf **dooft** zodra de consultant het feit alsnog vaststelt;
   - de **logregel** — een **bevroren snapshot** die blijft staan: *"consultant X kreeg deze open
     feiten voorgelegd en verklaarde toch klaar."*
   Beide uit **één norm-definitie**, maar tegen **verschillende peildata** (badge = nu; log = moment
   van akkoord). Dat onderscheid is bewust en mag niet vervlakken tot één van beide.

7. **Engine-grens (herbevestigd).** De norm gatet uitsluitend de **klaarverklaring** (die al
   engine-gescheiden is, ADR-027). Ze grijpt **niet** in het score-/lifecycle-/blokkade-schrijfpad.
   De engine-status `migratieklaar` blijft puur checklist-gedreven; de menselijke verklaring is de
   laag die de norm meeweegt. Twee waarheden, elk heel.

> **Uitbreiding LI045 (besluiten 8–14).** De lat verschuift in de tijd — dat is het bestaansrecht van
> een beheerscherm. Een component dat vorige maand aan de norm voldeed, voldoet er vandaag niet meer aan
> omdat de beheerder een feit toevoegde. De onderstaande besluiten scheiden "de consultant stapte bewust
> over de lat" van "de lat is sinds de verklaring verschoven", verplaatsen het signaal naar de
> werkvoorraad, en verankeren waar en in welke volgorde het beheerscherm landt.

8. **Twee soorten afwijking, streng onderscheiden — het live signaal splitst (verfijnt besluit 6).**
   "Deze consultant stapte bewust over de lat" is een uitspraak over een **persoon**; "de lat is sinds
   deze verklaring verschoven" is een uitspraak over de **organisatie**. Vandaag zien ze er identiek uit
   (één amber badge), en dat schrijft met terugwerkende kracht een keuze toe aan een mens die hem niet
   maakte — precies de misleiding die het checkpoint (blok 4) blootlegde. Voortaan zijn het **twee
   signalen**: (i) een verplicht feit dat de consultant bij het verklaren **zelf heeft afgewogen** en toch
   accepteerde blijft **amber, met verantwoording** (het staat in de bevroren snapshot); (ii) een verplicht
   feit dat **pas ná de verklaring** open kwam te staan is **neutraal van kleur én van taal** — een
   uitnodiging om opnieuw te kijken, geen verwijt. Dit **verfijnt** het enkele badge van besluit 6 tot twee
   tonen; besluit 6 blijft voor het overige ongewijzigd.

9. **Het onderscheid is een afleiding, geen nieuwe waarheid.** Er wordt **niets extra's opgeslagen**. De
   klaarverklaring bevriest al welke verplichte feiten op het besluitmoment open waren — de snapshot ís
   juist de verzameling feiten die de consultant zág en afwoog; de huidige norm-status is live bekend. Het
   **verschil** tussen die twee peildata *is* het signaal: een nu-open verplicht feit dat in de snapshot
   staat → bewust afgewogen (amber); een nu-open verplicht feit dat er niet in staat → niet afgewogen bij
   het verklaren (neutraal, "kijk opnieuw"). Dit volgt exact de bestaande regel — **één norm-definitie,
   twee peildata** (besluit 6) — en de snapshot blijft de **audit van een wilsbesluit**, nooit een
   afgeleide waarde (invariant; likara-ux §LI044).

10. **De verschoven lat is primair een werkvoorraad-gebeurtenis (herziet de reikwijdte-keuze B5).** Een
    verschoven lat raakt in één klik tientallen eerder klaar verklaarde systemen tegelijk. Laat je de
    consultant dat per component ontdekken, dan krijgt hij **ruis in plaats van werk**. Het signaal leeft
    daarom als **één gebundelde regel in zijn werkvoorraad** ("de lat is verschoven — N eerder klaar
    verklaarde systemen missen nu een verplicht feit"), met het **componentsignaal als afgeleide daarvan**
    — één bron, twee vensters (dezelfde lijn als besluit 6). Dit **herziet** de oorspronkelijke
    reikwijdte-keuze (B5), die de norm-afwijking bewust alléén als component-badge liet leven; de reden
    staat in §Reikwijdte-keuze.

11. **Het neutrale signaal noemt de lat die tóén gold.** Op het component staat niet alleen wat er nú
    ontbreekt, maar ook dat de verklaring destijds tegen de **toen geldende lat** is beoordeeld en toen
    compleet was. Zonder die zin is het neutrale signaal alsnog een verwijt in een vriendelijker kleur. De
    bevroren snapshot wordt daarmee leesbaar als **geruststelling vooraf** ("hier is niets stils gebeurd"),
    niet alleen als verantwoording achteraf.

12. **De beheerder ziet de gevolgen op het moment dat hij de lat verzet.** Bij het aan- of uitzetten van
    een feit toont het beheerscherm hoeveel componenten daardoor **niet meer** (of alsnog **wel**) aan de
    lat voldoen, en hoeveel eerdere verklaringen geraakt worden. **Geen blokkade** — de beheerder mag dit
    gewoon doen — maar met **open ogen**. De cijfers zijn puur afleidbaar uit wat er al is (de norm × de
    huidige veldwaarden), geen nieuwe opslag.

13. **Plaatsing: de norm is data van de organisatie zelf.** Het beheerscherm hoort in de **tenant-schil
    bij de beheerder**, als **broer van Checklistvragen** — niet in de platform-schil, en niet op het
    componentdetail. De lat geldt voor het hele landschap; hem laten verzetten tijdens gewoon
    registratiewerk zou beleid tot bijvangst van registratie maken. Vanuit de klaarverklaring loopt een
    **leesroute** naar de lat: **zichtbaar voor iedereen, bewerkbaar alleen voor de beheerder** (RBAC
    `COMPONENT_NORM`: iedereen leest, de beheerder stelt in).

14. **Volgorde-eis (bindend).** Het beheerscherm gaat **niet live vóór het onderscheid uit besluit 8
    bestaat**. Zolang de norm alleen via de seed beweegt is het probleem theoretisch; op het moment dat een
    beheerder de lat kan verzetten is de eerste klik meteen de gevolgschade. Daarom: **eerst** het
    onderscheid + het werkvoorraadsignaal (besluiten 8–11, slice 4a), **dan** het beheerscherm (besluiten
    12–13, slice 4b).

> **Uitbreiding LI045 slice 4c (besluiten 15–20).** De lat zichtbaar máken tijdens het invullen, niet
> pas bij het klaar verklaren. Grond: `docs/Meting-veldaanduiding-norm-V045.md` (read-only).

15. **De lat is zichtbaar tijdens het invullen, niet pas bij het klaar verklaren.** De norm is een
    uitspraak van de organisatie over wat bekend moet zijn; die achterhouden tot het beoordelingsmoment
    maakt er een **verrassing** van in plaats van een richtlijn. Achter een genormeerd feit staat daarom
    tijdens het invullen een aanwijzing dat het meetelt.

16. **Nooit het sterretje (harde grens).** Het sterretje belooft "je kunt niet opslaan zonder dit veld".
    Dat is hier **onwaar**: opslaan mag, de norm gaat over het moment van klaar verklaren. Zou de norm een
    sterretje krijgen, dan verwacht de consultant een blokkade die niet komt, én verliest het sterretje
    zijn betekenis op de plekken waar het wél blokkeert (verplichte invoer). Het sterretje blijft exclusief
    voor opslaan-blokkerende velden.

17. **Geen nieuw teken; de bestaande uitleg draagt het.** Grond (de meting): de vijf normeerbare
    formuliervelden dragen al een **blauw informatieteken ("i")** op exact de plek waar een nieuw teken zou
    landen, en er is **geen aparte informatiekleur** naast de linkkleur — een tweede blauw teken ernaast
    zou een niet te onderscheiden tweeling zijn. De norm-boodschap wordt daarom een **extra passage binnen
    de bestaande uitleg**, onder een scheidingslijn: boven de betekenis van het veld, eronder wat het voor
    de lat betekent. Het **uitroepteken is bewust níét gekozen**: de betekenis "let op" is op deze schermen
    al bezet door de amber/rode waarschuwingsfamilie (⚠), en hier is niets mis.

18. **Twee landingsplekken, één boodschap.** Vijf feiten hebben een formulierveld (eigenaar · BIV ·
    levensfase · bedoeling · hosting); vijf hebben dat niet en leven als **sectie op het componentdetail**
    (koppelingen · contract · verantwoordelijke · gebruikersgroep · bedrijfsfunctie). De aanduiding landt
    bij de eerste **achter het veldlabel**, bij de tweede **op de sectiekop** — dezelfde boodschap, dezelfde
    bouwsteen (`VeldUitleg`) waar mogelijk.

19. **De aanduiding leest de norm, en beweegt dus mee.** Geen tweede waarheid: verzet de beheerder de lat,
    dan verschijnt of verdwijnt de aanduiding vanzelf (dezelfde norm-leesbron als slice 4a/4b). Ze verdwijnt
    **niet** zodra het feit is ingevuld — het is een **regel, geen status**; anders knippert het formulier en
    kan de consultant de lat nooit meer teruglezen.

20. **Niet herhalen in het klaarverklaringsvenster.** Daar is de lat al het onderwerp (de open verplichte
    feiten staan er expliciet). Herhaling van de "telt mee"-passage maakt het luider zonder duidelijker te
    worden.

21. **Eén aanduiding per feit, op het kleinste omvattende element (algemene regel).** De aanduiding hangt
    aan het **feit**, niet aan het veld. Precies **één** aanduiding per genormeerd feit, op het kleinste
    element dat het héle feit omvat: een feit met **één veld** → achter het veldlabel; een feit met een
    **groep velden** → op de kop van die groep; een feit dat als **sectie** leeft → op de sectiekop.
    Grond: een samengesteld feit dat zijn aanduiding per veld draagt herhaalt dezelfde mededeling en
    suggereert meer latten dan er zijn — precies de ruis die de aanduiding moest voorkomen. **Illustratie:**
    BIV is één feit met drie schaalvelden → de aanduiding landt op de **legenda "BIV-classificatie"**, niet
    op de drie velden. Dit is een **generalisatie**, geen BIV-uitzondering. **Structurele borging:** de view
    geeft de bouwsteen door **welk feit** het betreft (niet een plek-boolean), zodat een tweede aanduiding
    voor hetzelfde feit opvalt; een **tellende test** per scherm eist dat het aantal zichtbare aanduidingen
    gelijk is aan het aantal genormeerde feiten. **Randgeval (te melden, niet op te lossen):** vallen de
    velden van één feit uiteen over **twee secties**, dan bestaat er geen gemeenschappelijk omvattend
    element — dat is geen plaatsingsprobleem maar een teken dat het feit verkeerd gemodelleerd is; rapporteer
    het i.p.v. een plek te verzinnen.

### L1a-uitzondering (expliciet)

L1a houdt vooruit-handelingen bewust licht. Klaar verklaren is normaal zo'n vooruit-handeling.
**Uitzondering:** klaar verklaren **terwijl verplichte feiten van de tenant-norm ontbreken** is geen
gewone vooruitgang maar het **bewust overrulen van de norm van de gemeente** — en verdient dáárom
het rijke, auditeerbare akkoord (besluit 5+6). De drempel zit in de afwijking, niet in het verklaren.
Deze uitzondering wordt hier expliciet vastgelegd zodat een latere sessie L1a niet leest als "klaar
verklaren is altijd licht" en het verantwoordingsmoment stil laat verdwijnen.

## Model / aanpak (indicatief — vorm belegd bij de bouw, ná deze ADR)

- **Norm-opslag:** een **tenant-scoped** vastlegging (per hard feit een verplicht-vlag) — de
  checklist is de enige tenant-eigen catalogus, dus dit is tenant-eigen data met het bestaande
  RLS-recept. Exacte vorm (eigen tabel vs. vlag-set) = subknoop 1.
- **"Vastgesteld"-leesbron:** één afleiding "welke verplichte feiten zijn niet vastgesteld op dít
  component" — bouwt voort op de bestaande per-component signaal-leesbron
  (`registratiegaten`/`badge_voor_component`), **uitgebreid** met de feiten die nu geen gat-signaal
  hebben (levensfase/bedoeling/complexiteit/prioriteit + de hostingmodel-sentinel) en met de
  "bewust geen"-bevinding voor koppelingen/contract.
- **"Bewust geen" voor koppelingen en contract:** een uitspreekbare bevinding per component
  (spiegel van de bedrijfsfunctie-"bewust niets"), zodat "geen koppelingen" een antwoord kan zijn.
- **Klaarverklaring-snapshot:** een kolom op de bestaande `component_klaarverklaring` die de
  openstaande-feiten-snapshot + peildatum vastlegt (de reden-dialog van `MigratiegereedheidSectie`
  toont al een open-vragen-caveat → natuurlijke plek voor de bevestiging).
- **Audit:** het rijkere besluit ("ter beoordeling gekregen, toch akkoord") landt via de
  klaarverklaring-kolom (echte kolom, want de audit vangt kolommen); ADR-006-keten ongemoeid.

## Invarianten

- **Engine onaangeroerd** — geen import van/schrijf naar lifecycle/score/blokkade vanuit de norm of
  de verklaring; dubbele engine-borging per slice (import-afwezigheid + live geen-mutatie).
- **Eén bron, meerdere ingangen** — badge en log lezen uit hetzelfde feit/dezelfde norm-definitie;
  nooit twee parallelle afleidingen die uiteen kunnen lopen.
- **De vorm bepaalt nooit de betekenis** — "leeg/sentinel/nooit-gekeken" ≠ "vastgesteld"; afwezigheid
  wordt nooit stil als antwoord gelezen. De consultant stelt vast.

## Gevolgen

- De gemeente kan haar eigen lat voor "migratieklaar" vastleggen, per feit, en toch op elk moment
  doorgaan met invullen — de norm blokkeert niets; ze weegt mee bij het verklaren.
- Een component dat écht geen koppelingen/contract heeft, kan compleet zijn (bewust geen), niet
  eeuwig "onvolledig".
- "Klaar verklaard met openstaande registratie" wordt een **zichtbaar, terug te lezen, bewust**
  besluit — het verschil tussen "het systeem liet iets door" en "een mens koos dit welbewust".
- Nieuw bouwwerk t.o.v. vandaag: de norm-opslag + -toetsing, de uitbreiding van de per-component
  leesbron, "bewust geen" voor koppelingen/contract, en de snapshot-kolom + bevestiging.

## Reikwijdte-keuze bij de bouw (B5, LI044 — HERZIEN door besluit 10, LI045)

De norm-afwijking ("verplichte feiten niet vastgesteld") en het bestaande `klaar_met_afwijking`
("checklist niet compleet") zijn **twee semantisch verschillende afwijkingen** — ze worden **nooit
samengevoegd in één teller** (dat zou misleiden; "twee waarheden, elk heel" — zie de invariant). **Dat
deel staat ongewijzigd.**

**Herzien (besluit 10, LI045).** De oorspronkelijke keuze liet de norm-afwijking bewust **alléén als
badge op het component** leven (`MigratiegereedheidSectie`), met een dashboard-/lijstsignaal als "eigen,
nog te nemen besluit". Dat besluit is nu genomen. Het checkpoint
(`docs/Checkpoint-norm-beheerscherm-V045.md`, blok 4/6) maakte duidelijk waaróm de component-only-keuze
niet houdbaar is zodra de beheerder de lat kan verzetten: één klik raakt tientallen eerder klaar
verklaarde systemen tegelijk, en dat per component laten ontdekken is **ruis, geen werk**. De
norm-afwijking krijgt daarom **wél een eigen signaal** — maar niet als dashboardteller náást
`klaar_met_afwijking`, wat de twee afwijkingssoorten zou versmelten. Ze leeft als **één gebundelde
werkvoorraadregel** ("de lat is verschoven — N systemen geraakt"), met het componentsignaal als
afgeleide (besluit 10). De twee afwijkingssoorten blijven dus streng gescheiden; dit is geen
samenvoeging maar een **eigen, tweede venster op dezelfde norm-definitie** (likara-domeinmodel
§LI041-kernregel, vierde toepassing).

## Subknopen — besloten bij de bouw (LI044)

1. **Norm-opslagvorm → BESLOTEN.** Eigen **tenant-scoped tabel `component_norm`** met het RLS-recept;
   één rij per (hard feit, verplicht-vlag). Geen vlag-set naast de componentconfig.
2. **Default-norm meeleveren → BESLOTEN.** LIKARA levert een verstandige platform-default mee:
   **eigenaar · verantwoordelijke · BIV · contract · koppelingen** verplicht (`DEFAULT_VERPLICHT`).
   Generiek voor elke tenant; een tenant die een feit niet hanteert zet het in zijn **eigen norm** uit
   (tenant-configuratie) — de default versmalt daar niet mee (likara-ux W4). Degradeert netjes: geen
   norm-rij = niet-verplicht.
3. **Welke feiten "hard" heten → BESLOTEN.** De kiesbare set = **10 harde feiten** (`HARDE_FEITEN`):
   eigenaar, verantwoordelijke, BIV, gebruikersgroep, bedrijfsfunctie, levensfase, bedoeling, hosting,
   koppelingen, contract. **`componentrol` valt af** (NOT NULL met vaste beginstand → nooit leeg →
   moot).
4. **Vorm van "bewust geen" → BESLOTEN.** Een **component-verankerde eigen tabel `component_bevinding`**
   met **dezelfde vorm** als de bedrijfsfunctie-"bewust niets" (die embedded in `functievervulling.
   geen_systeem` leeft). **Frontend geconvergeerd** → één `BewustGeenControl.vue` (2 consumenten:
   `ContractSectie`/`KoppelingSectie`); **opslag gespiegeld** (twee tabellen op dezelfde leest) tot een
   **derde drager** unificatie rechtvaardigt (n≥2 — likara-domeinmodel harde regel 8). Consistentie
   langs write-guard (409 `REGISTRATIE_BESTAAT`) + read "real wins"; de generieke `relatie_service`
   blijft onaangeroerd.
5. **Sentinel-lijst → BESLOTEN.** Kort en expliciet: **alleen `hostingmodel = onbekend`** telt als "niet
   vastgesteld". Uitbreidbaar wanneer een nieuw sentinel-veld bijkomt.

## Verhouding tot de beoordelingsgrondslag (OPVOLGPUNTEN LI043-1)

Deze ADR is de **smalle MVP-voorloper** van de grondslag: een **aanwezigheids-/vastgesteld-norm**
(ja/nee bekend), niet de volle **waarde-norm** (welke waarden tellen als juist). "Vastgesteld =
echt antwoord, sentinel telt niet mee" is bewust de eerste, smalste vorm van diezelfde waarde-norm,
zodat de latere gewogen grondslag hierop bouwt **zonder herbouw**. De grondslag zelf blijft het
grote post-MVP-ontwerpspoor.

## Bouw-fasering (indicatief, ná deze ADR)

De read-only feitenopname is gedaan (`docs/Checkpoint-tenant-norm-harde-velden-en-klaarverklaring-V044.md`).
Slices, elk met engine-onaangeroerd-borging + gate-discipline:
1. ✅ **Norm-opslag + -toetsing** (`component_norm`, tenant-scoped; de "vastgesteld"-leesbron uitgebreid) — **gebouwd `fae7593`**.
2. ✅ **"Bewust geen" voor koppelingen en contract** (`component_bevinding`, spiegel bedrijfsfunctie) — **gebouwd `626dc76`**.
3. ✅ **Verrijkte klaarverklaring** (snapshot-kolom `open_feiten` + bevestiging bij afwijking + badge/log uit één feit; slice 3b verantwoordingsvenster, 3c reden-achter-de-waarschuwing) — **gebouwd `7e2ff25`**.
4. **Norm-beheerscherm — gesplitst in de bindende volgorde van besluit 14 (LI045):**
   - 4a. ⏳ **Het onderscheid + het werkvoorraadsignaal** (besluiten 8–11): "bewust over de lat" (amber,
     met verantwoording) vs. "de lat is verschoven sinds de verklaring" (neutraal), en één gebundelde
     werkvoorraadregel met het componentsignaal als afgeleide. Puur leeslaag — geen nieuwe opslag, engine
     onaangeroerd (afleiding uit de bevroren snapshot × de live norm-status). — **OPEN (LI045-prioriteit 1).**
   - 4b. ✅ **Norm-beheerscherm** (de beheerder stelt de verplicht-vlaggen in; tenant-schil, broer van
     Checklistvragen), mét de gevolg-cijfers bij het verzetten (besluit 12) en de leesroute vanuit de
     klaarverklaring (besluit 13). **Gaat niet live vóór 4a bestaat (besluit 14, bindend).** — **gebouwd (`d748fcf`).**
   - 4c. ⏳ **De lat zichtbaar tijdens het invullen** (besluiten 15–20): de "telt mee"-passage binnen de
     bestaande `VeldUitleg`, achter het veldlabel (5 velden) én op de sectiekop (5 secties); leest de norm,
     beweegt mee; nooit het sterretje; niet herhaald in het klaarverklaringsvenster. — **OPEN (deze slice).**
