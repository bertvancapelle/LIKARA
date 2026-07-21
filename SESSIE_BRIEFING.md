# SESSIE_BRIEFING.md — LIKARA V049

**Gegenereerd**: 2026-07-21

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V049 |
| Datum | July 2026 |
| Commit | 44ef3f8 |
| Tests | backend 1136 passed / 2 skipped (module) + 80 passed (platform) · frontend 102 files / 1374 passed · vite build OK · 14 scans groen |
| TST-rapport | TST-V049-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
44ef3f8 [skills] LI048 — zes veralgemeniseringen en één ontdubbeling
e8931a3 [docs] LI048 objecthistorie — draaiboek, kleiner na-MVP-punt, ConfigBeheer-besluit
1aff74b [skills] LI048 — SUB_ENTITEITEN: wat hoort er in de geschiedenis van een ding
f6710bd [auditlog] LI048 — de geschiedenis van een ding bevat zijn sub-entiteiten
48027be [docs] LI048 detailkop-tekens — draaiboek en de icoon-bevinding
```

---

## Prioriteiten volgende sessie

# NEXT_SESSION.md — LIKARA V048

**Gegenereerd**: 2026-07-20
**Vorige build**: V047 → **V048**
**Branch**: master
**Laatste commit (code)**: `134fd6c` seedherstel + verantwoordingszin · `218b9fd` kopknop + één ingang ·
`529c122` koppelingen component-breed · `e89a417` open-punten-tabblad · `14e1dbe` `component_id` ·
`388f3da` ADR-055 gebouwd · `1dfe435` kopstijl + kop-rij
**Laatste commit (docs/skills)**: `f11fd1c` LI047-patronen · `56aa06f` ADR-055 + register ·
`e26d150` checkpoint gebruik-component-breed

> **Sessie LI047 — de consultant ziet nu per component wat er nog nodig is, met per punt een weg
> erheen. En wat hij ooit bewust heeft beantwoord, telt als beantwoord.**
>
> Wat een gebruiker ná LI047 kan dat hij vanochtend niet kon:
> - **Eén blik op wat dit component nog nodig heeft.** Het stond verspreid over zes tot acht plekken —
>   velden op het Overzicht, de contracten, de verantwoordelijkheden, de koppelingen, de checklist. Nu
>   staat het bij elkaar in drie blokken, met **per punt een knop naar de plek waar je het vastlegt**.
>   Wat hij bewust heeft beantwoord ("bewust geen koppelingen") telt als antwoord: het verdwijnt uit de
>   lijst én uit "Dit valt op", zodat het scherm zichzelf niet tegenspreekt over hetzelfde feit.
> - **De kop zegt zonder klikken of er werk ligt.** Een knop "Open punten" met een getal — en dat getal
>   **kan niet uit de pas lopen** met de lijst eronder, want beide lezen hetzelfde object. Is er niets
>   open, dan draagt de knop géén getal: de rust is het signaal. Het rode signaleringsbolletje is weg;
>   twee tellers die verschillende getallen roepen over hetzelfde component was een tweede waarheid.
> - **Bij élk component vastleggen wie het gebruikt en welke koppelingen er zijn.** Ook bij een gedeelde
>   fileshare of een databaseserver — precies waar dat bij een ontvlechting het hardst speelt. Wat de
>   registratie tegenhield bleek geen domeinregel maar een restant van een structuur die niet meer
>   bestaat (ADR-055). Waar de vraag inhoudelijk niet geldt, wordt hij ook niet gesteld.
> - **Het beheer leest niet langer als een ander product.** Eén bron voor de titelmaat (30 schermen
>   kozen zelf), en het uitleg-icoon hangt niet meer los naast zijn kop.
> - **Geen tekst meer die niemand leest, en geen melding die iets beweert wat niet meer waar is.**
>   Dode passages weg, uitleg op één plek, en de foutmelding die "applicatie" zei terwijl je naar een
>   fileshare kijkt is rechtgezet.
> - **Het demolandschap is weer volledig op te bouwen uit de seed** — inclusief de gevallen die de
>   browserchecks nodig hebben (schoon · beide soorten afwijking · alleen verschoven · bewuste
>   vaststelling · de fileshare mét gebruikersgroep · de gebundelde checklistregel).

---

## Vertrekpunt LI049 — begin hier

### 0. Consolideer de skills vóór je er iets bij zet

**Dit gaat vóór alles wat hieronder staat.** Het stond ook als punt 0 van LI048 en is er niet van
gekomen; er zijn in plaats daarvan zes patronen bijgezet. Bewuste afweging (er wordt niets in geheugen
bewaard, dus wat niet landt is weg), maar de schuld is daarmee groter geworden, niet kleiner.

**Drie dingen, in deze volgorde:**

**(a) `likara-werkprotocol` — 621 regels, 22 koppen.** Vijf daarvan zijn chronologische
verzamelbakken (`LI035`, `LI036`, `LI039`, `LI040`, `LI048`), samen 105 regels. Het probleem is niet
hun lengte maar dat ze **concurreren met de onderwerpskoppen**: een browsercheck-les kan in
§Browsercheck (84 regels) óf in §LI035 landen; een UX-first-les in drie verschillende secties. Hef de
vijf sessiekoppen op en hang hun inhoud onder het onderwerp waar ze bij horen — verplaatsen, niet
herschrijven. Voeg daarna de drie UX-first-koppen samen. Verwachte uitkomst: ~15 koppen, geen regel
minder inhoud. Let ook op §Gate-discipline: 142 regels, bijna een kwart, en het bevat
bestandsoperatie-lessen die bij §Browsercheck horen.

**(b) De P-reeks in `likara-ux` staat in omgekeerde volgorde.** In het bestand: P8 → P9 → P8d → P8c →
P8b → P8a. Elk nieuw stuk is vóór het vorige anker ingevoegd (in LI048 vier keer). Wie het bestand
leest komt P8d tegen vóór P8a. Puur een leesprobleem, snel op te lossen, en het groeit door bij elke
volgende toevoeging.

**(c) Drie borgingsregels staan in `likara-frontend` terwijl ze niet frontend-specifiek zijn:** het
bereik-van-een-scan-versmalt-stiller-patroon, de uitzondering-is-een-precedent-regel, en
afleiden-i.p.v.-opsommen. Ze horen in `likara-tests`. **Dit is geen ordeningsdetail:** een
borgingsregel in de frontend-skill wordt niet gevonden door wie aan de backend werkt — en drie van de
vijf misgelopen bijt-bewijzen van LI048 gingen juist over backend-toetsen. Verplaatsen kost
verwijzingen die elders naar `likara-frontend` wijzen; controleer die.

**Regel voor LI049: wie er patronen bij wil zetten, consolideert eerst.** Voor de tweede keer
opgeschreven — als het ook nu niet gebeurt, is de regel zelf het probleem en hoort hij te vervallen
of afgedwongen te worden.

Waarom dit vooropgaat: een protocol dat niemand meer leest geeft **schijnzekerheid**. Elke discipline
die erop leunt — de gate, de browsercheck, de commit-trigger — leunt dan op niets. Het signaal komt nu,
terwijl het nog leesbaar is; dat is het goede moment, niet als het al te laat is.

Aanknopingspunten: de vier LI047-koppen onder §Gate-discipline horen waarschijnlijk bij elkaar onder één
noemer ("wat je vaststelt vóór je bouwt"), en §Browsercheck draagt inmiddels drie verschillende soorten
regels (voorbereiden, uitvoeren, en het draaiboek zelf).

---

### 0b. Laat de vereisten-check van `gen_build` actualiteit toetsen, niet alleen bestaan

*Klein, en het hoort naast de consolidatie omdat het dezelfde soort fout afvangt.*

De check leest nu of een pad **bestaat**. Daardoor zou de sessie-ZIP van V048 bijna een
`PROJECTGEHEUGEN.md` hebben gebundeld dat nog V047 zei — met 1159 tests en de mededeling dat de
LI046-afsluitcommit nog moest komen — zónder dat er iets rood werd. Dat bestand is het **vertrekpunt
van de volgende sessie**.

**Wat het zou doen:** vergelijk het bouwnummer dat gegenereerd wordt met het nummer dat ín het bestand
staat. Staat daar het vórige nummer, dan is het niet bijgewerkt → rood.

**Alleen voor de bestanden die een MENS bijwerkt** — `docs/PROJECTGEHEUGEN.md` en `NEXT_SESSION.md`.
`CLAUDE.md` en `SESSIE_BRIEFING.md` worden dóór `gen_build` gegenereerd en dragen op het moment van de
check per definitie het oude nummer; die meenemen levert alleen vals alarm.

⚠ **Wat het NIET vangt:** een bestand waarin alleen het nummer is opgehoogd boven verouderde inhoud.
Het vangt **vergeten, niet slordigheid** — zet dat erbij in de code, anders ontstaat er
schijnzekerheid en leunt de volgende sessie op een check die minder bewijst dan hij lijkt.

**Kosten:** een handvol regels in `gen_build.py`, plus een testje dat hem laat bijten op een bestand met
het vorige nummer. Niet in LI047 gebouwd omdat `gen_build` al gedraaid was en de ZIP gevalideerd — er
dan code bij leggen betekent opnieuw draaien en een bouwnummer dat verspringt.

---

## Vóór productie oplossen — niet parkeren

- **De namenkaart zonder paginering** (`KoppelingSectie.vue`, `_zorgCompNamen`): haalt 100 componenten
  op zonder paginering, terwijl die kaart de naam van de tegenpartij resolveert. Bij 19 componenten
  merkt niemand iets; een echte organisatie zit daar zo overheen. Het gevolg is **stil** — er breekt
  niets en er komt geen foutmelding; de tegenpartij-kolom toont een **lege naam**, en de consultant
  concludeert dat de koppeling naar een naamloos component wijst. Een fout die zichzelf verbergt kost
  meer dan een die klapt. *Oplossingsrichting: namen per pagina meeleveren vanuit de relatie-respons,
  of de kaart gericht opvragen voor de id's die in beeld zijn — niet het limiet ophogen, want dan
  verschuift de grens alleen.*
- **`organisatiegebruik.applicatie_id`**: een echte databasekolom die het id van elk componenttype
  draagt (ADR-041 maakte de grove laag al component-breed; de naam bleef). **Schemastap met migratie —
  eigen besluit van Bert**, niet meeliften.

## Vrijgekomen opruiming (sinds LI047 ongebruikt)

`SignaleringBadge.vue`, `frontend/tests/SignaleringBadge.test.js`, `api.signalering.badgeComponent`
(`api.js:362`) en de verwijzing in de docstring van `DetailKop.vue:13`. Bewust laten staan: een
bouwsteen weggooien is onomkeerbaarder dan hem niet meer mounten.

## Kleine, benoemde punten

- **De tekstkeuze op het migratiegereedheid-blok** — `MigratiegereedheidSectie.vue:215` schrijft
  "door onbekend · datum". Geen gat (grammaticaal correct), maar "onbekend" leest als een persoon.
  **Alleen zinvol als dat blok blijft bestaan** — snede 2 vervangt het mogelijk.
- **Foutcode `GROEP_ZONDER_APPLICATIE`** — de gebruikerstekst is hersteld naar "component", de code
  niet. Machine-leesbaar contract: meenemen bij een volgende contractwijziging op dat endpoint.
- **`heeft_applicatie_subtype`** — API-veld met een eigen betekenisvraag (het zegt "subtype" terwijl er
  geen subtabel meer is), dus geen simpele hernoeming.

---

## Openstaand uit LI048 — in volgorde van wat de consultant merkt

> Deze vier komen vóór de MVP-prioriteiten hieronder in **zichtbaarheid**, niet per se in gewicht.
> Punt 1 is de scherpste openstaande vraag vóór MVP en is alleen in de browser te beantwoorden.

1. **Vindbaarheid van de Geschiedenis-knop.** Kwam deze sessie **drie keer** terug: de knop bestond
   al op alle zeven detailschermen, de weg erachter is soortonafhankelijk — en Bert liep tóch vast in
   het auditlog en zocht daar naar een checklistvraag. Sinds LI048 draagt de knop bovendien géén
   woord meer, alleen een klokje: mogelijk **minder** vindbaar, niet meer.
   Geen bouwvraag maar een UX-vraag; alleen te beantwoorden door het scherm te gebruiken. Zolang dit
   openstaat, is niet vast te stellen of het na-MVP-punt "zoeken naar soorten zonder eigen scherm"
   (OPVOLGPUNTEN) wel het echte probleem is — misschien is het probleem dat niemand de knop ziet.
   **Doe dit vóór er iets aan het auditlog-zoeken wordt gebouwd.**

2. **De datumvelden op het auditlog.** Waargenomen: Van/Tot staan standaard op vandaag, waardoor je
   ongemerkt in één dag van 45.000 regels kijkt. **De code zegt iets anders** — overal leeg/`None`,
   geen enkele default (gemeten in LI048). Eerst reproduceren en de oorzaak vinden (autofill?
   staat-herstel?), dán beslissen; anders wordt een default "weggehaald" die niet bestaat. De
   UX-vraag staat los van de oorzaak en geldt vanaf het eerste geval (`likara-ux` §P8a).
   Volledig punt: OPVOLGPUNTEN.

3. **Signalering + Plaatsingssignalen** — het laatste hoofdmenu-scherm dat anders leest. Draagt een
   handgebouwde tabrij die naar `AppTabs` moet, plus de lijstkop. Plaatsingssignalen is géén los
   scherm maar een tabblad ván Signalering (`SignaleringView.vue:16`, ADR-035) en hoort in dezelfde
   snede — apart een `<h1>` geven zou een tweede paginakop binnen een tabblad opleveren.

4. **De acht beheerschermen** (`*ConfigBeheer`, buiten het hoofdmenu). Besloten: zij krijgen dezelfde
   lijstkop, als eigen snede **zonder voorrang** — eenvormigheid voor de beheerder, niet voor de
   consultant die de hele dag van lijst naar lijst loopt. ⚠ Let op het scan-bereik: dat wordt
   afgeleid uit het hoofdmenu (`check-css-build.mjs`, lijstkop-scan) en deze acht staan daar niet in.

---

## Top-5 prioriteiten LI049

> **Volgorde: eerst de leesbaarheid van het protocol waar alles op leunt (0), dan de MVP-feiten die nog
> ontbreken.**

1. **Archiefwet-feit bouwen (ADR-053).** *De norm-slices zijn geland; het feit kan erin.* Eén hard
   componentfeit "draagt dit component archiefbescheiden" (`ja` / `bewust geen` / `null` = niet
   gekeken), in de platform-default maar **niet** standaard verplicht — de tenant zet de lat zelf.
   Eigen enum-kolom op het component (géén "bewust geen"-relatiemechanisme; dat is relatie-verankerd).
   Subknopen open. Grond: `docs/adr/ADR-053_Archiefwet-als-hard-componentfeit.md`.
   **Raakt schema (kolom + migratie) → gate.**

2. **Laatste MVP-laag op de functie-as (ADR-046 stuk 3 → 5 → 4).** *Maakt de MVP af; lag bewust ná
   gate 4.* Uitstap-stand op de gebruiksrelatie (`organisatiegebruik`, stuk 3) → afgeleide
   zwaarte-telling (stuk 5, nooit opgeslagen) → tranche (stuk 4). Grond: ADR-046, OPVOLGPUNTEN
   LI040/LI041.

3. **ADR-register bijwerken naar de gebouwde realiteit.** ADR-055 staat op "Besloten — gebouwd", maar
   ADR-052 (open-punten-overzicht) en ADR-054 verdienen een statusregel die klopt met wat LI047 heeft
   opgeleverd. Werkprotocol §ADR-onderhoud.

4. **Terugweg-fijnslijpen (open ontwerpbesluiten LI046).** *De kaart landt terug, maar niet alles reist
   mee.* Beslis wat er wél/niet in `lk-state` hoort: org-scope, Rol/BIV-filter, weergavekeuze,
   zoom/pan; en of view-verwijderen een bevestiging krijgt en "selectie bijwerken" een ingang.

5. **Dev-seed: het gate-3-verhaal (L4-restant).** Het schone geval (S1) staat er, en LI047 voegde het
   fileshare-geval toe. Nog niet in de seed: koppelingen + "hier draait niets" + de noodoplossing; een
   **partij die van hetzelfde component eigenaar én gebruiker is** met meerdere beheerrollen (het geval
   waarvoor de baan-scheiding op hoedanigheid is gebouwd); en een **knooppaar met relaties van meerdere
   hoedanigheden** (cross-ring overlap komt 0× voor in de dev-data).

---

## Openstaande beslissingen

- **Terugweg naar de kaart (LI046, punten 1–5).** Bij terugkeer landt de bewaarde selectie (ADR-054),
  maar org-scope, Rol/BIV-filter, weergavekeuze en zoom/pan reizen niet mee; een gedeeltelijk verdwenen
  selectie wordt stil kleiner getekend. Open ontwerpbesluiten, geen oplossingsvoorkeur vastgelegd.
- **"Bewust geen" op de gebruiksrelatie.** `organisatiegebruik` kent die stand niet, anders dan het
  Archiefwet-feit (ADR-053). Of die drieslag daar hoort is een eigen besluit.
- **Reikwijdte norm-afwijking (B5/D4).** Niet samengevoegd met `klaar_met_afwijking` in de
  dashboardteller. Uitbreiding naar een dashboard-/lijstsignaal is een eigen besluit (ADR-052).
- **Archiefwet-subknopen (ADR-053).** Vorm besloten (eigen enum-feit); de subknopen open.
- **Beoordelingsgrondslag (post-MVP).** ADR-052 is de smalle voorloper; de volle gewogen waarde-norm
  blijft het grote post-MVP-spoor.

---

## Bekende risico's en aandachtspunten

- **Geen verstrengelde werktree** — alle LI047-bouw is per opdracht apart geland; docs/skills apart
  (`f11fd1c`, `56aa06f`, `e26d150`). Schone start.
- **Suites groen:** backend **1179 passed / 2 skipped** · frontend **98 files / 1275 passed** ·
  vite build OK · css-build OK (vier bronscans, elk met zelftest) · alembic 1 head (`0073`), 0 branches.
- **Migraties deze sessie: 0.** ADR-055 en de `component_id`-hernoeming zijn beide zonder
  schemawijziging gebouwd — dat was in beide gevallen het bewijs dat het om een applicatielaag-restant
  ging.
- **Tellingen in gate-rapporten zijn momentopnamen.** Wie ze later als stand overneemt, zit ernaast —
  hermeten binnen de tenant-context is de regel. Dit ging LI047 **drie keer** mis, telkens in een andere
  vorm (werkprotocol §Meet tenant-data binnen de tenant-context).
- **Norm-borging is per scherm** — een nieuw scherm dat norm-feiten toont heeft zijn **eigen** tellende
  test nodig; er is geen globale scan (OPVOLGPUNTEN LI045-2/3).
- **Open verificatie GEMMA** — of de publieke GEMMA Archi-repo méér functie↔proces-relaties draagt dan
  ons AMEFF-bestand (4% gemeten) staat nog open.

---

## Geleerde patronen deze sessie

Verankerd in de likara-skills (`f11fd1c`), geen memory-duplicaat. Dertien patronen; de scherpste:

- **Een bewijs over de gewijzigde bestanden zegt niets over wie ze gebruikt** — de AST-vergelijking bij
  een hernoeming was correct en gaf daardoor *valse* zekerheid; de seed brak en 1176 groene tests
  raakten het niet (werkprotocol §Gate-discipline).
- **Sneden die dezelfde functie ontsluiten, beoordeel je op één beeld** — beide sneden waren afzonderlijk
  goedgekeurd en samen fout; geen test vangt dat (werkprotocol §Gate-discipline).
- **Meet tenant-data binnen de tenant-context; een rapport is geen meting** (werkprotocol).
- **Een typegebonden beperking zónder ADR is vaak een restant** — zoek de herkomst én het precedent
  (werkprotocol, ADR-055).
- **Teller en lijst uit één laadpunt, niet alleen één bron** — twee aanroepen zijn geen tweede waarheid
  maar wél twee laadmomenten (frontend §LI047).
- **Een scan met een benoemde uitzondering is een achterdeur** — derde eis naast bijten en
  geen-vals-positieven (frontend).
- **Nul is een uitkomst: een lijst legt uit, een teller zwijgt** (ux).
- **Een weigering zegt wát er aan de hand is** — "er is niets" en "die vraag geldt hier niet" zijn
  verschillende antwoorden (ux).
- **Wat je zelf onwaar maakt, herstel je in dezelfde commit** — strenger dan verergeren (werkprotocol).
- **Een bestandsoperatie doet niet wat hij leest** — vier faalvormen; de verificatie achteráf is de
  belangrijkere helft (werkprotocol §Browsercheck).
- **Een draaiboekstap is een claim over de code** — toets hem vóór je hem opschrijft (werkprotocol).
- **`vi.clearAllMocks()` wist aanroepen, niet implementaties** (tests §LI047).


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V049"
4. Wacht op START: [naam] van Bert
