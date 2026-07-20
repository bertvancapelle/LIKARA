# SESSIESTART — LIKARA V048

**Datum**: 2026-07-20
**Platform**: LIKARA — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/likara/ bestaat
   - Zo ja: normale modus — lees alle likara-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — LIKARA V048 — [N] skills geladen"
5. Wacht op START: [naam] van Bert

---

## Interactieregel (VERPLICHT — niet-onderhandelbaar)

Geldt voor zowel CC als claude.ai, in elke sessie:

- Stel vragen ALTIJD één voor één. Stel nooit meerdere vragen tegelijk.
  Wacht op het antwoord van Bert voordat je een volgende vraag stelt.
- Geef adviezen ALTIJD één voor één. Geef nooit meerdere adviezen tegelijk.
  Wacht op de reactie van Bert voordat je een volgend advies geeft.

Deze regel is niet-onderhandelbaar en overschrijft elke neiging om
meerdere vragen of adviezen te bundelen.

---

## Opdrachtformaat CC-opdrachten (VERPLICHT — standaardwerkwijze)

claude.ai levert elke CC-opdracht ALTIJD aan als een .md-bestand
(downloadbaar), nooit als een los codeblok in de chat. Bert gebruikt dat
.md-bestand in CC. Deze afspraak geldt in elke sessie.

---

# SESSIE_BRIEFING.md — LIKARA V048

**Gegenereerd**: 2026-07-20

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V048 |
| Datum | July 2026 |
| Commit | f11fd1c |
| Tests | backend 1179 passed / 2 skipped · frontend 98 files / 1275 passed · vite build OK · css-build OK |
| TST-rapport | TST-V048-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
f11fd1c [skills] LI047-patronen vastgelegd — dertien lessen, elk getoetst tegen de code
134fd6c [herstel] LI047 — de seed werkt weer, en de verantwoording zegt wie én wanneer
218b9fd [frontend] LI047 snede 2 — de ingang in de kop, en dan ook maar één
529c122 [frontend] LI047 — koppelingen kun je bij elk component vastleggen
e89a417 [backend+frontend] LI047 snede 1 — het tabblad "Open punten" per component
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

## Vertrekpunt LI048 — begin hier

### 0. Consolideer het werkprotocol vóór je er iets bij zet

**Dit gaat vóór alles wat hieronder staat.** `likara-werkprotocol` staat op **595 regels**, en
§Gate-discipline kreeg deze sessie **vier nieuwe koppen** erbij. Een sectie met vier nieuwe koppen
beschrijft niet meer één ding — die is een verzameling geworden.

**Regel voor LI048: wie er patronen bij wil zetten, consolideert eerst.**

Waarom dit vooropgaat: een protocol dat niemand meer leest geeft **schijnzekerheid**. Elke discipline
die erop leunt — de gate, de browsercheck, de commit-trigger — leunt dan op niets. Het signaal komt nu,
terwijl het nog leesbaar is; dat is het goede moment, niet als het al te laat is.

Aanknopingspunten: de vier LI047-koppen onder §Gate-discipline horen waarschijnlijk bij elkaar onder één
noemer ("wat je vaststelt vóór je bouwt"), en §Browsercheck draagt inmiddels drie verschillende soorten
regels (voorbereiden, uitvoeren, en het draaiboek zelf).

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

## Top-5 prioriteiten LI048

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
3. Bevestig: "Sessie-briefing geladen — LIKARA V048"
4. Wacht op START: [naam] van Bert

