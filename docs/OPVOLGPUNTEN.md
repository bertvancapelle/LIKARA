# LIKARA — Opvolgpunten (backlog)

Bijgehouden met de hand. Niet door `gen_build.py` gegenereerd.
Bron: sessie 2–3 (P1–P5, OP-9 t/m OP-12). Status per punt expliciet vermeld.

---

## OPEN

### Nieuw uit LI048 (2026-07-21) — één werkvlak, drie schermsoorten zónder

0a. **De sterkere buitenrand raakt één scherm; de rest heeft helemaal geen omrand werkvlak.**
    LI048 gaf `.lk-tabvlak` de sterke rand (`--lk-color-border-sterk`) zodat de buitengrens niet
    langer even zwaar is als de scheidingslijntjes erbinnen. Maar `.lk-tabvlak` heeft **één**
    consument: `ComponentDetail.vue:550`. Daarnaast:
    - **`.card`** (46 treffers in 32 bestanden, `main.css`) draagt **geen border** — alleen
      `--lk-shadow-sm`. Kaarten bewegen dus niet mee met deze regel.
    - **Lijstschermen** (bv. `ComponentLijst.vue`) zetten hun `DataTable` niet in een omhullend
      vlak: er ís geen buitengrens om te verzwaren.
    - **De landschapskaart** tekent op `bg-[var(--lk-color-surface)]` (`LandschapskaartView.vue:3125`)
      zónder rand.
    **Waarom het uitmaakt:** de regel "de buitenrand is de sterkste lijn" geldt nu op één scherm.
    Op de andere schermen is de vraag niet "welke rand" maar "hoort hier een werkvlak?" — en dat
    raakt de nog onbeantwoorde vraag uit snede 2 over witte kaarten op een wit vlak.
    Status: **open — ontwerpvraag Bert (welke schermen dragen een omrand werkvlak?)**.

### Nieuw uit LI048 (2026-07-21) — zes schakelaars, zes vormen

0. **Hetzelfde keuze-gedrag is zes keer los nagebouwd; er is nu één bouwsteen voor.** LI048 2d
   maakte `.lk-schakelaar` / `.lk-schakelaar-stand` (main.css) voor "één keuze met N standen"
   (`role="group"` + `aria-pressed`, géén tabrij). Bij het bouwen bleek dat gedrag **al zes keer**
   te bestaan, elk met een eigen inline vorm:
   `LandschapskaartView.vue:2835` (weergave Overzicht|Praatplaat|Lagen) · `:3069` (diepte 1|2) ·
   `:3275` (kaart-lezing) · `BedrijfsfunctieLijst.vue:906` (Boom|Diagram) ·
   `ArchitectuurView.vue:113` (Lagen|Tabel) · `ArchitectuurLagenView.vue:85` (aspect-filter).
   Twee ervan (`:2835`, `:906`) zijn al een aaneengesloten schakelaar mét rand — die staan het
   dichtst bij de nieuwe bouwsteen; de andere vier zijn losse knopjes.
   **Waarom het uitmaakt:** zes vormen voor één betekenis betekent dat de gebruiker per scherm
   opnieuw moet leren wat een schakelaar is (n≥2-convergentieregel, ruim overschreden). De
   klassen zijn bewust generiek gehouden zodat alle zes erop kunnen.
   **Bewust niet omgezet in LI048 2d** — dat raakt vier schermen buiten de scope van deze snede
   en verdient een eigen browsercheck. Status: **open — eigen snede (converge-voorstel)**.

### Nieuw uit LI048 (2026-07-21) — dood seed-pad met plausibele namen

1. **`_seed_technische_laag` wordt niet aangeroepen — maar zaait wél namen die echt lijken.**
   De functie (`backend/dev_seed_testdata.py:650`) maakt `Oracle FIN-DB` (database, `:676`) en
   `Geo-fileshare` (fileshare, `:677`) plus drie assignment-relaties, maar staat **niet** in `main()`
   (`:1923` e.v. roept `_seed_bvowb_scenario` aan, niet deze). Geen van beide componenten bestaat dus in
   het demolandschap — live geverifieerd in de dev-tenant `11111111-…-111111111111`: 19 componenten,
   waarvan de enige database `Shared DB-server` heet en de enige fileshare `Shared fileshare`
   (beide uit `_seed_bvowb_scenario`, `:1487`/`:1491`).
   **Risico:** een volgende sessie leest deze namen uit de bron, gebruikt ze in een draaiboek of een
   test, en stuurt de lezer naar een component dat niet bestaat — precies wat in LI048 gebeurde
   (een browsercheck-stap wees naar "Oracle FIN-DB", waarna het scherm 0 van 19 meldde). Een dood
   seed-pad is gevaarlijker dan géén seed-pad, want het oogt geldig.
   Status: **open — besluit Bert: pad opruimen óf alsnog aansluiten in `main()`**. Bewust niet
   opgeruimd in LI048.

### Nieuw uit LI046 (2026-07-19) — terugweg naar de kaart (open ontwerpbesluit)

1. **Wat kan er stil verschuiven tussen weggaan en terugkomen op de kaart?** Bij terugkeer naar de
   Landschapskaart landt de gebruiker nu bij zijn bewaarde beeld (ADR-054), maar drie dingen kunnen
   **ongemerkt** verschuiven: (a) een **gedeeltelijk** verdwenen selectie wordt zonder aanwijzing kleiner
   getekend én de bewaarde set wordt stil opgeschoond (LI052-prune), zodat het verlies bij een volgende
   terugkeer onvindbaar is — alléén een *volledig* verdwenen selectie krijgt de eerlijke melding
   (`lk-leeg-verdwenen`, ADR-054 besluit 7); (b) de **organisatie-scope** (`scopeOrgs`) zit niet in
   `lk-state`; (c) de **rol-/BIV-filters** zitten niet in `lk-state`. Een dichte deur zie je; een verschoven
   filter of een ontbrekend lid niet. Bron: `docs/Checkpoint-terugweg-naar-de-kaart-V046.md` (blok 5).
   Status: **open — ontwerpbesluit Bert (geen oplossingsvoorkeur vastgelegd)**.

2. **View verwijderen gebeurt zonder bevestiging.** De × op een opgeslagen kijk in `KaartBeginscherm`
   (`@verwijder-view`) verwijdert direct; er is geen tussenvraag. Een per ongeluk verwijderde kijk is
   onherstelbaar weg. Status: **open — ontwerpbesluit (bevestiging ja/nee)**.
3. **"Selectie bijwerken" op een bestaande view is onbereikbaar.** Op een opgeslagen kijk bestaan alleen
   ✎ (naam wijzigen) en × (verwijderen); de **bewaarde selectie zelf** opnieuw vastleggen onder dezelfde
   naam heeft geen ingang. Wie zijn kijk wil bijstellen moet verwijderen + opnieuw opslaan. Status: **open
   — ontwerpbesluit**.
4. **"Bewust geen" bestaat niet in het gebruiksdata-model.** Voor een gebruiksrelatie
   (`organisatiegebruik`) is er geen expliciete "bewust geen"-stand: een component waarvan bewust is
   vastgesteld dat er géén organisatiegebruik is, is niet te onderscheiden van een component waar nog niet
   naar gekeken is. Vergelijk het Archiefwet-feit (ADR-053), dat die drieslag wél kent (`ja` / `bewust
   geen` / `null`). Status: **open — ontwerpvraag (hoort de drieslag ook op de gebruiksrelatie?)**.
5. **Weergave-instelling en zoom/pan reizen niet mee terug.** Bij terugkeer landt de bewaarde selectie
   (ADR-054), maar de **weergavekeuze** (Lagen/rolbanen-projectie) en de **zoom/pan-stand** zitten niet in
   `lk-state` en vallen terug op de default. Verwant aan punt 1(b/c), maar dit betreft de *weergave* — niet
   de selectie of het filter. Status: **open — ontwerpbesluit (wat hoort in `lk-state`?)**.
6. **Hercheck: is het ADR-036-vervolg en de contactpersoon-schemagate nog actueel?** Beide staan langer open;
   controleer bij de volgende sessie of ze nog kloppen tegen de huidige code (schema + endpoints) vóór er
   op wordt voortgebouwd. Status: **open — verificatie (versheid tegen de code)**.

### Nieuw uit LI045 (2026-07-18) — Archiefwet als hard componentfeit (besloten, MVP)

1. **Archiefwet-feit (ADR-053) — MVP-onderdeel, bouwen ná ADR-052 slice 4a + 4b.** Eén hard componentfeit
   "draagt dit systeem archiefbescheiden" (ja / bewust geen / niet gekeken), in de norm zoals eigenaar en
   contract; in de platform-default, **niet** standaard verplicht (de tenant zet de lat zelf). Vorm besloten,
   subknopen open. Vindplaats: `docs/adr/ADR-053_Archiefwet-als-hard-componentfeit.md`; bewaartermijn-grens
   + route: `docs/horizon/Horizon-archiefwet-bewaartermijn-via-zaaktype.md`. Status: **open — ná slice 4a/4b (nu geland)**.
2. **Tellende norm-borging is per scherm — geen globale scan.** De borging dat elk genormeerd feit precies
   één aanduiding draagt (`#[data-norm-lat]` == aantal genormeerde feiten; BIV één keer) leeft als test
   **per scherm** (`ComponentFormulier.test.js`, `ComponentDetail.test.js`). Een **nieuw** scherm dat
   norm-feiten toont heeft zijn **eigen** tellende test nodig — er is geen platform-brede scan die het
   afdwingt. Status: **open — discipline per nieuw normscherm** (geen bouwtaak nu).
3. **Secties zonder norm-doorgifte tonen geen aanduiding.** De norm-"i" verschijnt alleen als het scherm
   `provide('normVerplicht', …)` doet (via `useNormLat`). Een sectie/venster dat elders gemount wordt
   **zonder** die doorgifte toont stil géén aanduiding — geen fout, maar iets om te weten bij een nieuw
   mountpunt. Status: **open — aandachtspunt, geen defect**.
4. **`GebruikersgroepSectie`: kop tegenover feitnaam (bewust gelaten).** De sectiekop "Gebruikersgroepen"
   wijkt af van de feitnaam "Gebruikersgroep" — zelfde enkelvoud/meervoud-patroon als Contract↔Contracten.
   Bij C1 bewust **niet** aangeraakt (enkelvoud/meervoud is geen afwijking; gebruikersgroep staat niet op de
   default-lat). Status: **gelaten — eigen opdracht als Bert het toch wil**.
5. **Verificatie: draagt de publieke GEMMA Archi-repo méér relaties dan ons AMEFF-bestand?** De GEMMA-meting
   (functie↔proces, 4% dekking → geen brug) is gedaan op het gepinde AMEFF-bestand in de repo. Openstaand:
   controleer of de **publieke GEMMA Archi-repository** rijkere relaties bevat die de conclusie zouden
   veranderen. Vindplaats: `docs/Meting-gemma-functie-proces-relatie-V045.md`. Status: **open — verificatie**.
6. **README ADR-register mist ADR-049 t/m 053.** De ADR-tabel in de README/CLAUDE.md loopt tot 048; de
   deze-en-vorige-sessie geschreven ADR-049 (functievervulling) t/m 053 (Archiefwet) ontbreken. Status:
   **opgelost (LI046 — `docs/adr/README.md` aangevuld t/m ADR-054)**.
   ⚠ Randobservatie: de **status­regels ín ADR-049/050/051** zeggen nog "bouw nog niet gestart", terwijl de
   borgingstests (`test_functievervulling_adr049`/`_rollengrens_adr050`/`_gapsignaal_adr051`) bestaan → die
   ADR-koppen zijn ✓ **rechtgezet (LI046)**: register én ADR-koppen vertellen nu hetzelfde. (De gelijkluidende
   "bouw volgt"-notities ín de LI042-gate-4-addenda van ADR-049/051 blijven stale — alléén de kop-status is
   gecorrigeerd; de body-tekst viel buiten deze scope.)
7. **C2 (bewust gelaten, patroon vastgelegd).** "Bedoeling (migratiepad)" (normscherm) vs. "Bedoeling"
   (formulier); Contract↔Contracten; Verantwoordelijke↔Verantwoordelijkheden. Enkelvoud/meervoud +
   verhelderende toevoeging — gelijktrekken zou de koppen ongemakkelijker maken. Vastgelegd in likara-ux
   §LI045. Status: **gelaten met reden — geen actie**.

### Nieuw uit LI044 (2026-07-18) — tenant-norm gebouwd, procesregister-UI gesloopt

> **LI045 top-5 — eindstand (de LI046 top-5 staat in `NEXT_SESSION.md`):**
> 1. ✅ **Slice 4 — norm-beheerscherm** — geland (4a/4b/4c, `aaeeb15`/`d748fcf`/`f8a9142`); ADR-052 af.
> 2. **Open-punten-overzicht per component** — ✅ **gebouwd (LI047)**: drie blokken uit één
>    afleiding + kopknop met teller (`e89a417`/`218b9fd`). Ongewogen, op de bestaande signalen; de
>    gewogen grondslag blijft post-MVP.
> 3. **Laatste MVP-laag functie-as (ADR-046 stuk 3 → 5 → 4)** — nog **open** (draagt naar LI046).
> 4. **Dev-seed vertelt het volledige verhaal (L4)** — deels: het **schone geval** (S1, `6a0931a`) is
>    toegevoegd; het gate-3-verhaal (koppelingen/"hier draait niets"/noodoplossing) blijft **open**.
> 5. ✅ **VeldUitleg adopteert `popoverPositie.js`** — geland (slice 4c, `f8a9142`).

**Afgerond deze sessie (LI044):**
- ✅ **Gate-4 sloop** — procesregister uit de MVP-UI (nav/routes/`ProcesLijst`/`ProcesDetail`/secties/
  `PartijProcessenSectie`/`ComponentProcessenSectie`), de dode kaart-handoff en de doodlopende "Bekijk
  op kaart" opgeruimd (`c82ad80`); datamodel + bouwstenen + slapende endpoints behouden. Zie G4-4.
- ✅ **ADR-052 slices 1–3** — tenant-norm-opslag/-toetsing (`component_norm`, `fae7593`), "bewust geen"
  voor koppelingen/contract (`component_bevinding`, `626dc76`), verrijkte klaarverklaring
  (snapshot + verantwoordingsvenster + reden-achter-de-waarschuwing, `7e2ff25`). **Slice 4 open** (top-1).

**Open:**

1. **Slice 4 — norm-beheerscherm (ADR-052).** ✅ **AFGEROND (LI045).** De beheerder ziet en verzet de norm
   nu zelf (4b, `d748fcf`), met impact-voorspelling vóór opslaan en "wanneer/door wie" uit het audit-spoor;
   4a onderscheidt de verschoven lat (neutraal) van de bewuste afwijking (amber, `aaeeb15`); 4c toont de lat
   tijdens het invullen (`f8a9142`). BvoWB kan BIV nu zelf uitzetten. ADR-052 af.
2. **Dev-seed vertelt het gate-3-verhaal (L4).** Norm en "bewust geen" zitten nu in de seed, maar het
   gate-3-verhaal (koppelingen, "hier draait niets", de noodoplossing) is op een verse DB nog
   onzichtbaar. Elke browsercheck leunt op de seed. Status: **open — LI045-prioriteit 4**.
3. **`VeldUitleg`-overlay adopteert `popoverPositie.js`.** ✅ **AFGEROND (LI045, slice 4c).** `VeldUitleg`
  gebruikt nu de gedeelde `usePopoverPositie` (`fixed` + flip/klem) i.p.v. zijn eigen `absolute`-overlay
  — één bouwsteen, geen tweede positioneringslogica. Aanleiding: de 4c-norm-passage maakte het paneel
  hoger en liet het bij "Bedoeling" onderaan het (scrollende) formulier buiten beeld vallen; de Dialog
  klipt via `overflow-y-auto` en centreert via marge (géén `transform`) → `fixed` ontsnapt correct.
  **Alle 29 VeldUitleg-schermen erven de fix** (de wijziging zit in de ene bouwsteen). Geborgd met een
  regressietest (`VeldUitleg.test.js` — paneel is `fixed`, niet `absolute`). A11y (Escape/klik-buiten/
  focus-terug) ongewijzigd. **Nog open voor ándere componenten:** MigratiegereedheidSectie droeg 'm al;
  er zijn verder geen bekende eigen-overlay-componenten meer — als er een opduikt, adopteert die de
  bouwsteen op dezelfde wijze. Zie likara-frontend §Overlay-positionering (LI044).

### Nieuw uit LI043 (2026-07-17) — beoordelingsgrondslag & open-punten-overzicht

1. ⭐ **Beoordelingsgrondslag — tenant-configureerbare waarde-norm + gewogen open-punten-overzicht per
   component.** Groot **post-MVP** ontwerpspoor (in LI043 gegroeid van "waar zet ik Lifecycle" naar een
   fundament — mag niet vervlakken).
   - **Kernidee (Bert):** niet LIKARA of de code bepaalt wat "juist ingevuld" is, maar **de tenant stelt een
     beoordelingsgrondslag vast** — een norm waartegen een component wordt gewogen. Het **open-punten-
     overzicht** per component (dat de smalle beoordelings-"wegwijzer" vervangt) toont dan of de **juiste**
     dingen zijn ingevuld, gewogen tegen die norm.
   - **De grondslag is een waarde-norm, niet alleen aanwezigheid.** Per veld: welke **waarden** tellen als
     juist — niet "is het veld gevuld", maar bv. "BIV moet **geclassificeerd** zijn (niet 'niet
     geclassificeerd')", "eigenaar bekend", "levensfase bekend vóór migratie". Reden: een aanwezigheids-lat
     laat het gevaarlijkste geval door — een veld gevuld met een placeholder (BIV = "niet geclassificeerd")
     oogt in orde maar is een gat dat zich voordoet als ingevuld. De norm gaat over de waarde.
   - **Twee losgekoppelde momenten (weerlegt de drempel-zorg):** *invullen* — de consultant voert vanaf minuut
     één systemen op, koppelt, doorloopt checklists; gaat door ongeacht de grondslag. *Wegen* — pas wanneer de
     organisatie wil weten "hebben we de *juiste* dingen ingevuld", meet het overzicht tegen de grondslag.
     Apart moment; blokkeert het invullen **niet**. De grondslag is geen poort vooraf, maar een lat ernaast.
   - **Incrementeel + degradeert netjes (houdt de drempel laag — LIKARA's kernbelofte, anti-Drimmelen):** de
     grondslag hoeft niet in één keer compleet. De tenant begint met een paar regels en breidt uit wanneer ze
     eraan toe zijn. Het overzicht **werkt óók zonder grondslag**: dan toont het de open punten **ongewogen**
     (gewoon "leeg / staat op nee"), zoals de bestaande signalen nu. Zodra de grondslag er is, krijgt datzelfde
     overzicht **gewicht** ("deze afwijking telt, want jullie hebben dit veld verplicht gesteld"). Waardevol
     zonder, scherper mét — geen harde afhankelijkheid, geen big-bang-inrichting. Kandidaat: een **verstandige
     default-grondslag** meeleveren (op basis van de bestaande kritiek/aandacht-splitsing: eigenaar/
     verantwoordelijke/BIV), zodat een nieuwe tenant vanaf minuut één weegt zonder iets in te richten, en pas
     aanpast wanneer gewenst.
   - **Het open-punten-overzicht (vervangt de smalle wegwijzer):** bij het openen van een component ziet de
     consultant in één beeld **alles wat dit systeem nog nodig heeft**, uit al zijn bronnen, gesplitst in
     **"Dit moet nog"** en **"Dit zou netjes zijn"**, elk punt met de **route ernaartoe**. De
     beoordelingsstatus (lifecycle) is daarbinnen **één bron**, niet het hele verhaal.
   - **Bronnen — al ophaalbaar (feitcheck `feitcheck-open-punten-bronnen`, geen leeg-omhulsel-risico):**
     Checklist nee/deels → open punt (route `?tab=checklist&markeer=<code>`) — **lifecycle-blokkerend**;
     registratiegaten via `signalering.badgeComponent` (geen eigenaar · geen verantwoordelijke · BIV
     onvolledig = kritiek; geen gebruikersgroep · geïsoleerd · geen bedrijfsfunctie = aandacht); component-
     eigen lege velden (levensfase/bedoeling/beschrijving) — triviaal ophaalbaar (null), maar "leeg ≠ fout"
     (LI040) → alleen als de grondslag ze eist; Impact-tab: géén open-punt-bron.
   - **Moet/netjes volgt uit de grondslag (lost de impasse op):** de indeling is **niet** een vaste code-regel
     maar het **gevolg van de tenant-grondslag** — staat een veld/waarde op de grondslag → afwijking is
     "moet"; staat het er niet op → "netjes" of ongewogen. Onderscheid dat de grondslag moet kunnen
     uitdrukken: **lifecycle-blokkerend** (checklist nee/deels → voedt de engine → `geblokkeerd`) vs.
     **registratie-kritiek** (eigenaar/BIV → voedt de engine NIET). Een component kan `migratieklaar` zijn én
     tóch een kritiek registratiegat hebben — het overzicht/de grondslag moet dat eerlijk kunnen tonen zonder
     tegenstrijdigheid.
   - **Te ontdubbelen (feitcheck):** `component_zonder_verantwoordelijke` (kritiek) en
     `object_zonder_roltoewijzing` (aandacht) vuren uit dezelfde `geen_rol`-conditie — één feit, twee sleutels
     → als **één** punt tonen.
   - **Openstaande ontwerpvragen (bij de uitwerking, niet nu):** waar leeft de grondslag (per tenant — nieuw
     model / catalogus, raakt schema)? · vorm van een norm-regel per veld (aanwezig / waarde-uitsluiting /
     waarde-in-set)? · ordening van het overzicht (platte lijst per groep met herkomst-label per regel =
     lichter, vs. nesting naar herkomst = mogelijk te veel voor "één oogopslag")? · de grensgevallen als
     default (geen gebruikersgroep / geïsoleerd / geen bedrijfsfunctie — moet of netjes in de meegeleverde
     default-grondslag)?
   - **Verband:** vervangt het smalle wegwijzer-idee; bouwt op de checklist-/registratiegaten-signalen die er
     al zijn; raakt de "Lifecycle → Beoordelingsstatus"-hernoeming (aparte, kleine fix — mag vooruit).
   - **Status:** groot **post-MVP** ontwerpspoor. ✅ **Het ongewogen overzicht is in LI047 gebouwd** op de
     bestaande signalen (`component_open_punten_service`); de **weging** en de grondslag zelf blijven het
     post-MVP-fundament.

### Nieuw uit LI040 (2026-07-14) — ADR-046 levensfase, bedoeling en uitstap

> ⚠ **Bouwvolgorde LI041 HERZIEN (besluit Bert, naloper op de afsluiting):** de gates
> van de bedrijfsfunctie-as (blok A: gate 2 → 3 → 4) gaan **vóór** het uitstapspoor
> (blok B: stuk 3 → 5 → 4); de eerdere "stuk 3 eerst"-volgorde vervalt. De besluiten
> van ADR-045/046 zelf veranderen NIET. Volledige volgorde + reden: `NEXT_SESSION.md`.
> Verwijzingen hieronder als "ontwerpeis stuk 3/gate 3" zijn dependency-labels, geen
> volgorde-uitspraken — die blijven zoals ze staan.

### Nieuw uit LI041 (2026-07-14) — koppelen, gap-signaal, rollengrens

L1. ⭐ **Een component verwijderen zou moeten vertellen wat er meegaat.** Wie een component
   wegdoet, wist in één klik alle koppelingen, procesvervullingen, checklistscores,
   blokkades, roltoewijzingen én gebruiksfeiten die eraan hangen — **zonder telling en
   zonder waarschuwing** (`component_service.py:762-772`). Weken veldwerk verdwijnt met
   dezelfde kale bevestiging als de lichtste actie. **Urgenter sinds ADR-050** verwijderen
   bij meer mensen (elke medewerker) heeft neergelegd. *Open ontwerpvraag:* **spiegel**
   (toon eerst wat meegaat, zoals het model-inlees-voorbeeldscherm) óf **weigering** (409 +
   laag voor laag ontmantelen, zoals organisatiegebruik)? En: bij élk landschapsobject of
   alleen bij een grote cascade? (Suggestie: de bestaande read-only `impact_analyse`,
   `component_service.py:841`, als bevestigstap.) Status: **open — ontwerpbesluit Bert**.
L1a. ⭐ **IJkpunt als auditeerbaar wilsbesluit bij werk-terugzettende/vernietigende handelingen
   (LI043, feitcheck `feitcheck-werkvoorraad-ijkpunten`).** **Principe (Bert):** een handeling die
   **werk terugzet op de werklijst of iets vernietigt** toont een ijkpunt dat **het gevolg benoemt**
   ("deze plek komt hierdoor terug op je werklijst"). De bevestiging is een **verantwoordingsmoment**,
   terug te lezen in de audit: **wie · wanneer · welke handeling · welk getoond gevolg · bewust
   akkoord**. Het onderscheid dat nu ontbreekt — tussen "het systeem veranderde" (automatische
   mutatie-logging, ADR-006) en "een mens koos dit welbewust, met kennis van de gevolgen" — is precies
   wat dit vastlegt. **Selectieve lijn (bewust, niet strikt-overal):** vooruitgang — werk **afronden**
   (component→functie koppelen, gebruikersgroep tóevoegen, "bewust niets" vastleggen, functie plaatsen)
   — blijft **licht, geen ijkpunt**. Het ijkpunt hoort bij **werk terugzetten of vernietigen**
   (ontkoppelen, "bewust niets" terugtrekken, gebruikersgroep verwijderen, component verwijderen).
   Reden: overal bevestigen traint weg-klikken én vervuilt het audit-spoor met betekenisloze
   bevestigingen — dan verdrinkt het besluit dat ertoe doet. Aandacht schaalt met gewicht. **Eén
   gedeeld mechanisme:** het ijkpunt én de audit-trigger komen uit één bouwsteen
   (`BevestigVerwijderDialog` is de kandidaat — dekt al ontkoppelen/haalWeg/functie-verwijder), zodat
   geen impactvolle handeling ongemerkt langs het spoor glipt en de klonen
   (koppel/plaats/geenSysteem/gg-verwijder/component-verwijder als losse `Dialog`) daarnaartoe migreren
   (staat al als note bij de bouwsteen; zie ook de 11-klonen-migratie in het LI035-blok). **Het
   scherpste concrete gat (feitcheck):** **gebruikersgroep verwijderen** kantelt een plek `hier →
   werkvoorraad` (zet werk terug de consultant-lijst op) én gooit gg-gegevens weg, maar de bevestiging
   is generiek ("deze gebruikersgroep definitief verwijderen?") en **benoemt het werkvoorraad-gevolg
   niet**. Dit is het eerste dat het principe moet dichten. Rijkste referentie voor "toon wát verandert":
   component-verwijderen (ADR-022 Fase C) toont al een impact-telling — maar bespoke, niet als gedeelde
   bouwsteen (generaliseert L1 hierboven). **Correct géén ijkpunt (bevestigd, niet aanraken):** de
   koppeling-oordeel-dropdown (kantelt de stand niet — kwalificatie binnen een al-gedekte plek) en
   veld-edits die geen stand kantelen. **Te verifiëren read-only vóór de bouw (niet nu aannemen):**
   (1) kan de huidige automatische mutatie-logging (ADR-006, before/after_flush + hash-keten) de
   **"bevestigde intentie"** al dragen (mens-koos-bewust vs. systeem-muteerde), of moet daar iets bij —
   en zo ja, wat minimaal? (2) kan `BevestigVerwijderDialog` de **audit-trigger + het getoonde-gevolg**
   huisvesten zonder per-plek maatwerk? **Reikwijdte:** ~8 kantelende handelingen over 3 views
   (BedrijfsfunctieLijst · GebruikersgroepSectie · ComponentDetail); één gedeelde bouwsteen kan ze
   bedienen. Status: **post-MVP governance-verankering; sluit aan op het top-6 "destructieve bevestiging
   toont wat verwijderd wordt" (L1) en de bevestig-dialoog-migratie. Geen bouw nu.**
L2. **De bescherming van de modelinhoud leunt op een afspraak, niet op een test.**
   `MODELINHOUD_BESCHERMD` staat nu op twee mutatiepaden (`bedrijfsfunctie_service` +
   `relatie_service._weiger_modelinhoud`), maar er is **geen test die bewijst dat élk**
   relatie-mutatiepad de guard passeert. Dat is precies de constructie die de KERNLES
   afwijst (*"een regel houdt pas als een bouwsteen hem afdwingt"*) — de achterdeur is
   gedicht, maar niets bewaakt dat er geen nieuwe bijkomt. Nodig: een bronscan-/dekkingstest
   over alle relatie-schrijfpaden. Status: **open**.
L3. **Een typefout in de toelichting op een koppeling is niet te herstellen (gate 2b).**
   Er is geen PATCH-kenmerk-pad op een functievervulling; een medewerker kan zijn eigen
   vergissing alleen rechtzetten door de hele koppeling weg te gooien en opnieuw te leggen.
   Status: **open — hoort bij gate 2b**.
L4. **De dev-seed vertelt het gate-3-verhaal niet.** De seed zaait geen koppelingen, geen
   "hier draait niets"-bevinding en geen noodoplossing → **op een verse database is gate 3
   onzichtbaar** (je ziet de vier standen pas na handmatig klikken). Regel: *de seed volgt
   de user story, de tests volgen de seed.* Status: **open**.
L5. **Dode rechten-entiteiten.** `Entiteit.KOPPELING` en `Entiteit.COMPONENT_STRUCTUUR`
   hebben 0 route-treffers — restanten van een oud model. Schrappen (met de matrixtests
   die meebewegen). Status: **open, klein**.
L6. **Taalpunt gate 3 — de omhoog-cue is formeler dan de rest.** *"ondersteund via {naam}
   — hier niet bevestigd"* wijkt af van de spreektaal elders in gate 3. Kandidaat:
   *"hierboven is al iets vastgelegd — hier nog niet bevestigd."* Status: **open — taalkeuze
   Bert**.
L7. **De css-build-poort draait pas bij de closeout, niet vóór een commit.** Daardoor kon
   een veldnorm-schending landen in `78ffd5e` (de gate-3 oordeel-select) en pas uren later
   zichtbaar worden — een gat in de commit-discipline, geen codebug. Overweeg de poort naar
   de per-commit-groencheck te halen: een regel die pas aan het eind bijt, laat schuld
   ontstaan. (De schending zelf is gedicht in `6d1b3fc`.) Status: **open**.

0a. **Eén taal voor afwezigheid — sentinel-inventarisatie (LI040 §1.3).** `migratiepad.
   onbekend` is opgeruimd (migratie 0067); de rest is read-only geïnventariseerd en
   vergt per geval een BESLUIT van Bert (soms is "n.v.t." een echt antwoord — dat
   onderscheid niet zelf verzinnen):
   - `HostingModel.onbekend` — enum-sentinel, kolom NOT NULL, formulier-default: oogt
     als antwoord. Leegte of echt antwoord? (De checklist-optieset 2.1 is hiervan
     afgeleid en volgt vanzelf mee.)
   - `complexiteit`/`prioriteit` — AFGEHANDELD (LI040, migratie 0068): nullable zonder
     default, gedempt "nog niet vastgelegd" + ontbreekt-filters; enum intact (midden
     blijft een geldig, bewust te zetten oordeel).
   - `ChecklistScore.nvt` — vermoedelijk een écht oordeel ("niet van toepassing");
     bevestigen, niet aanraken zonder besluit (engine-waarde!).
   - `AntwoordType.geen` — structuurkeuze (vraag zonder getypeerd antwoord), geen
     leegte-sentinel; alleen benoemd voor volledigheid.
   - UI-leegteteksten lopen uiteen: "nog niet vastgelegd" (levensfase/bedoeling),
     "Niet geclassificeerd" (BIV-detail), "nog niet geregistreerd" (eigenaar/
     sleutelrollen), "n.v.t." (plateau-bevestiging), "—" (lijstkolommen) — één
     taal kiezen is een eigen (kleine) UX-slice.
   Status: **open — besluit per geval bij Bert**.

0. **Resultaatregel uitrollen naar de overige lijsten.** LI040 bouwde de gedeelde
   bouwsteen `FilterResultaatRegel.vue` (aantal + actieve filters uitgeschreven + los
   wisbaar) en zette de componentenlijst om. Read-only vastgesteld: contract-, partij-,
   proces-, bedrijfsfunctie- en architectuurlijst delen dezelfde filterbalk-vorm, maar
   hun lijst-endpoints missen count-support (`totaal`/`totaal_ongefilterd`) — omzetten is
   per lijst een eigen kleine slice (endpoint-telling via het gedeelde-filterwaarheid-
   patroon van `component_service.tel` + chips-bedrading + tests). Status: **open**.

0b. **Signalering-scherm wordt de werkvoorraad-als-checklist — één UX-slice (browsercheck LI043).**
   **Aanleiding:** de browsercheck van de serving-fix (`bae58b2`) legde bloot dat het Signalering-scherm
   nu een lange scroll-lijst is, gegroepeerd **per signaal**: één systeem dat meerdere gaten mist staat
   meerdere keren, verspreid; nergens een overzicht "hoe staat systeem X ervoor". De consultant werkt juist
   **per systeem**. Vier samenhangende bevindingen — één principe (*een signaal is overal klikbaar naar zijn
   betekenis én naar de plek waar je het dicht*) — **samen bouwen, ná gate 4**:
   1. **Groeperen per systeem i.p.v. per signaal.** Eén regel per systeem met zijn openstaande gaten als
      labels ernaast, **elk label gekleurd naar ernst** (rood = kritiek, amber = aandacht); kritiek-eerst
      gesorteerd. Bovenaan een **klikbare telstrook per signaaltype** ("3 zonder eigenaar · 7 zonder
      verantwoordelijke · …") die als filter werkt — zo blijft de campagne-lens bestaan zonder een tweede
      volledig per-signaal-scherm vooruit te bouwen (geen dubbele weergave).
   2. **Oplichten bij binnenkomst.** Klik op een signaal → detailscherm scrollt naar het betreffende blok en
      **accentueert het kort** (rustige, zelf-uitdovende rand/gloed; **ernst-gekleurd** = de aangeklikte
      ernst; navigatie-hint, geen tweede oordeel op het blok). Toegankelijk: het blok krijgt kort focus (niet
      alleen kleur). Vereist een **expliciete koppeling signaaltype → detailblok**; wijst een signaal naar
      een blok dat er niet is, dan land je rustig bovenaan zonder mislukte scroll. Structureel één gedeeld
      "licht-dit-blok-op-na-binnenkomst"-mechanisme dat elk detailscherm erft, niet per sectie nagebouwd.
   3. **Badges/indicatoren klikbaar naar hun betekenis.** De detailkop-indicatoren (bv. de rode blokkade-bol
      "1") en component-badges bieden nu **geen route** naar wat ze betekenen of waar je het gat dicht — een
      signaal zonder uitgang. Kern-informatie hoort niet stil in een bol/tooltip (LI039: geen kern in
      tooltip; LI034/LI039: geen doodlopend pad). Eén keer structureel oplossen, niet per plek.
   4. **Draaiboek-les (procesdiscipline).** Een browsercheck wijst naar de plek waar het signaal **echt
      leeft** (Signalering-lijst / componentenlijst), niet naar een detailkop-badge die er niet zo staat —
      de LI043-fout in het serving-fix-draaiboek. Verankert de bestaande browsercheck-regel (LI032/LI035).
   **Verband:** raakt `SignaleringView.vue`, `SignaleringBadge`, `registratiegaten_service.overzicht()`
   (read-only afgeleid, geen engine-poort, geen schema); sluit aan op de resultaatregel-/afwezigheidstaal-
   lijn (0/0a, LI040). Status: **open — één UX-slice, bouwen ná gate 4**.

1. **Dev-seed moet het ADR-046-verhaal vertellen.** Stuk 1 (LI040-bouw): de
   levensfasen zijn gezaaid (Zaaksysteem=uitfaseren, ZAC=in ontwikkeling, 4× in
   productie, 13× bewust leeg). De tranches/standen-seed volgt bij stuk 3/4.
   Status: **deels AFGEROND (levensfase); rest open — bouwvoorwaarde stuk 3/4**.
2. **Kaart-eerste-wint bij meerdere plateaus** — AFGEROND (LI040 stuk 1, migratie
   0066): `plateau_dispositie` is vervangen door `Component.levensfase`; `plateau_naam`
   toont nu álle plateaus alfabetisch (deterministisch; twee-plateaus-test in
   `test_landschapskaart.py`). Status: **afgerond**.
3. **Stale docstring `Organisatiegebruik`** — bij de LI040-bouw geverifieerd: de
   docstring (nu `models.py:464-467`) benoemt het component-brede slot al correct
   (eerder gecorrigeerd; verificatie-eerst — geen verzonnen fix op correcte code).
   Status: **afgerond (bleek al gecorrigeerd)**.
4. **Spook-gebruik**: een org-wissel of groep-delete laat het oude grove
   organisatiegebruik-feit staan; opruimen kan alleen via de kale DELETE-API. De
   ADR-046-invoerroute geeft een verwijder-affordance; het achterblijf-gedrag zelf is
   een eigen weging (grof-only is immers geldig — maar spook telt mee in de
   uitstap-teller). Status: **open**.
5. **Contract-datums ongebruikt** (`begindatum`/`einddatum`/`vernieuwingsdatum` bestaan;
   geen afleiding leest ze): een aflopend contract is een impliciet uitstap-signaal.
   Eigen spoor, na ADR-046. Status: **open**.
6. **Bedrijfsfunctie-doorwerking** — *"N bedrijfsfuncties raken zonder ondersteunend
   systeem als organisatie X vertrekt"*: **harde ontwerpeis voor gate 2/3** (zelfde
   signaal-familie als ADR-044 besluit 4 en ADR-045 besluit 2-keerzijde). Status:
   **besloten — ontwerpeis gate 2/3**.
7. **Server-side kopieën van de identiteitsvorm.** De frontend-identiteit is
   geconvergeerd (`IdentiteitLabel.vue` + `partijIdentiteit`), maar server-side leven
   nog eigen kopieën: de kaart-labels (`landschapskaart_service.py`, o.a. de
   gebruikersgroep-/persoon-namen) en `gebruikersgroep_service.identiteit`. Zolang die
   niet dezelfde vorm delen, kunnen kaart en scherm stil uiteenlopen. Status: **open**.
8. **Fantoom-ADR-comment-sweep (047 én 048).** Gemeten (LI041, opnieuw): **11
   code-verwijzingen** naar een **ADR-047** dat niet bestaat (vermoedelijk een vroege
   werktitel voor wat ADR-046 werd) **én 1 verwijzing naar ADR-048**
   (`backend/app/middleware/security_headers.py:1` — "ADR-048 Sprint 1 B5"), óók zonder
   bijbehorend ADR-bestand. Sweep = beide hernummeren of schrappen; puur comments, geen
   gedrag. ⚠ Neem **047 én 048 samen** — anders pakt een volgende sessie 048 alsnog per
   ongeluk als losse rest. Status: **open, klein**.
9. **Gebruik + Gebruikersgroepen = één laag — harde ontwerpeis voor stuk 3.** Vandaag
   zijn het twee tabbladen over hetzelfde feit (grof vs. verfijnd). Zodra de
   uitstap-stand op de gebruik-rijen landt (stuk 3), horen grof en fijn in één
   gelaagde weergave (grof → verfijning eronder) — niet twee losse tabs die elk een
   halve waarheid tonen. Status: **besloten — ontwerpeis stuk 3**.
10. ~~**"Fileshare als drager = gat, niet groen" — harde ontwerpeis voor gate 3.**~~ **VERVALLEN
    (LI044).** Verworpen door **ADR-051 besluit 3**: een fileshare is niet inherent een noodgreep — het
    oordeel "noodoplossing/naar behoren" zit op de **plek/koppeling**, niet op het componenttype
    (ADR-045 besluit 2 is daarmee ook verworpen). "Riskant" is een aparte oordeel-as, geen gat-signaal.
    Niet meer inplannen.
11a. **`platform_init` lokaal vergt een lk_admin-DATABASE_URL** (bevinding TST-V041):
    de seed loopt via `get_platform_db_session()` op de DATABASE_URL-engine — in de
    init-container is dat lk_admin (correct, ADR-011), maar het CLAUDE.md-alternatief
    "cd backend && python3 -m app.platform_init" draait lokaal als lk_app (.env) en
    faalt dan met permission denied op de platform-catalogi. Fix = docs/CLAUDE.md-regel
    aanvullen met de DATABASE_URL-override, of platform_init op de platform-engine
    zetten (klein ontwerpbesluit). Status: **open, klein**.
11. **Aard-hint-ruis in picker-opties.** Nu de identiteit (namen + organisatie) in de
    opties staat, onderscheidt de aard-hint ("organisatie", "externe partij" achter
    elke regel) meestal niets meer — afweging voor Bert: dempen/weglaten of laten
    staan. Status: **open — afweging Bert**.

### Nieuw uit LI042 (2026-07-15) — vervolg ná gate 4 (kaart-swap staat; slice 3 volgt)

> Beide punten zijn **vervolg ná gate 4** — niet nu inplannen (eerst slice 2 + 3
> committen, tree schoon). Richting/wens, geen besluit; geen ADR. Vóór de bouw hoort
> telkens een read-only feitencheckpoint (waar haakt het aan, kleinste vorm, echte impact).

G4-1. **Kaart: filter- en detailkolom auto-hide met hover + pin (zelfstandige UX-slice).**
   Het Lagen-scherm is vol: de linker filterkolom + de rechter detail/actieve-set-kolom nemen
   samen veel breedte, waardoor de kaart in het midden smaller is dan nodig. *(Lost "de
   kolommen nemen breedte" op — NIET "de kaart zelf is druk"; dat laatste is een aparte vraag
   die scope-keuze A raakt.)* **Model (besloten met Bert, LI042):** default = **los/ingeklapt**
   (elke kolom klapt in tot een smalle rand/tab; kaart standaard volle breedte); **hover brengt
   terug** (hover over de rand → open; muis weg → dicht); **pin = vast** (per kolom een pin die
   'm vast openzet; pin los → terug naar hover). Twee kolommen, elk apart pinbaar → vier
   werkstanden. **Niet-onderhandelbaar voor een niet-broze hover-ervaring:** (a) **sluitvertraging**
   — kolom blijft een fractie open nadat de muis de rand verlaat (naar een dropdown net buiten
   de rand bewegen zonder het paneel te verliezen); (b) **open-drempel** — openen pas na een kort
   moment hover (geen knipperend paneel bij diagonaal langs-scheren); (c) **de ingeklapte
   filterrand verraadt een actief filter** (stip/teller "N filters actief") — de ingeklapte stand
   mag NOOIT verbergen dát er gefilterd wordt (anders snapt de gebruiker niet waarom de kaart
   weinig knopen toont). **Scope-grens:** pin-stand leeft **binnen de sessie**; onthouden-over-
   sessies is een aparte persistentie-vraag (raakt de bewaarde-staat-discipline) → **apart
   geparkeerd**, niet in de eerste vorm. Zelfstandige UX-slice, **los van gate 4** (raakt
   kaart-layout, niet de laan-logica of leeslaag); oppakken ná gate 4 als eigen taak.
   Status: **richting besloten (model), bouw geparkeerd — ná gate 4**.

G4-1b. **Pin-stand onthouden over sessies (afgeparkeerd van G4-1).** De vast-gepinde
   kolomstand persisteren over sessies/apparaten heen — raakt de bewaarde-staat-/voorkeur-laag
   (kijkfilter, niet invoerregel; ADR-041-lijn). Bewust uit de eerste vorm van G4-1 gehouden om
   de UX-slice klein te houden. Status: **geparkeerd — pas ná G4-1 wegen**.

G4-1c. **Kaart-lezing zit in sessie-state, filters in de voorkeur-laag — asymmetrie, bij de "onthoud
   als mijn standaard"-slice gelijktrekken (LI043).** **Bevinding (slice-A-gate-rapport):** de kaart-lezing
   (werk/status/domein, `ac9db21`) leeft in de sessie-`lk-state`, terwijl de kaart-**filters** in de
   **voorkeur-laag** persisteren (server-persistent per gebruiker). Het oude `kleurOpDomein` zat óók in de
   voorkeur-laag; slice A haalde de lezing bewust naar sessie-state om de slice klein te houden. Gevolg: een
   opgeslagen standaardkijk draagt de kleur-lezing niet meer — een lichte asymmetrie. **Besluit (LI043):** de
   kleur-lezing is bij uitstek een **vaste bril** (ADR-041: "hoe ik altijd kijk" — kleur-op-domein staat er
   letterlijk als voorbeeld); bij de "onthoud als mijn standaard"-slice voor de kaart hoort de lezing
   **naast de filters in de voorkeur-laag** — additief, geen herbouw. Tot dan blijft de lezing een
   momentkeuze in de sessie-state. Status: **geparkeerd — meenemen bij de kaart-voorkeur-slice (ADR-041)**.

G4-1d. **Kaart valt bij een niet-resolvende herstelde selectie terug op "Geen componenten" i.p.v. het
   beginscherm (LI043).** **Bevinding (diagnose `diagnose-kaart-regressie-heellandschap`, browser-bevestigd):**
   na `docker compose down -v` + reseed houdt een overlevende browser-tab de sessionStorage-`lk-state` vast.
   `_herstelKaartState` (`LandschapskaartView.vue:2737`) herstelt de opgeslagen `actieveSet` **zonder
   bestaanscheck**; na de reset zijn alle ids nieuw, dus de herstelde set bevat uitsluitend dode ids → mount
   doet `POST /subgraaf([dode ids])` → 200 OK met 0 nodes → `nodes.value = []` → "Geen componenten in deze
   selectie". **Geen regressie van slice 2/A** (git-blame weerlegt dat: het laad-pad is niet geraakt, weken
   oud); **de kaart werkt** (verse/incognito tab toont "toon hele landschap" correct). **Besluit (LI043):**
   kleine, gerichte **hardening** — `_herstelKaartState` mag een `actieveSet` niet blind herstellen; laat
   niet-resolvende ids vallen, of val bij een 0-respons op een herstelde set **terug op het beginscherm**
   i.p.v. een doodlopend "Geen componenten" (zelfde geen-doodlopend-pad-principe, LI034/LI039). **Test-gat
   (mee te nemen bij de fix):** geen test mount met een `lk-state` waarvan de set-ids 0 teruggeven uit
   subgraaf; regressietest = herstel een set van niet-bestaande ids → assert nette terugval (beginscherm /
   lege set), niet "Geen componenten" (groene suite ≠ werkende kaart, LI035/LI041 — mocks gaven subgraaf
   altijd data). **Ernst: laag** — trigger is dev-only (`down -v` met overlevende tab); niet blokkerend voor
   slice B (laad-pad ongemoeid). Status: **geparkeerd — kleine hardening, eigen slice**.

G4-2. **Bron-verwijzing op objecten — VERWIJZEN, geen documentopslag.** Een registratie in
   LIKARA is vandaag een bewering zonder spoor naar haar onderbouwing; er is geen manier om aan
   te geven **waar meer detail te vinden is**. Gewenst: een object verwijst naar waar de
   bron/meer info staat. **Kern — nadrukkelijk verwijzen, NIET opslaan:** LIKARA slaat **geen
   documenten** op (wordt geen DMS — de gemeente heeft er al één); het draagt alleen het **adres**
   van waar meer staat (een bestand, maar net zo goed een link naar een systeem, pagina of
   specifiek item). **Vorm (licht — dit is bijna de hele waarde):** een verwijzing = **adres
   (URL/pad) + soort (document/systeem/pagina/ticket/…) + label** ("Beheerdocument zaaksysteem
   §3"), uniform ongeacht het doel; **hangt aan een object**, zichtbaar in context (bv. blok
   "Bronnen & meer info" op het applicatiedetail — geen losse bijlagenbak); klik = open het adres
   (nieuw tabblad). **LIKARA controleert de inhoud niet** — het is "wat de registrant opgaf als
   bron", geen geverifieerd feit; het staat ernáást de bewering, niet vermengd. Doodlopende
   links/verplaatste docs zijn geen LIKARA-probleem; toegang tot het doel regelt het doelsysteem
   (veiliger dan documenten binnenhalen — LIKARA beheert geen rechten op gevoelige stukken).
   **Rolgrens (bestaand patroon):** toevoegen/corrigeren = registratiefeit (medewerker+); bekijken
   = iedereen die het object mag zien. **Bewust NIET in de eerste vorm:** previews,
   link-geldigheidscontrole, categorieën, versies (kern eerst: adres + soort + label, in context,
   medewerker beheert). **Samenhang:** tegenhanger van de import/wizard-horizon — import vult
   vánuit een bron, de verwijzing laat de gebruiker terug náár de bron; herkomst en verwijzing =
   twee kanten van dezelfde eerlijkheid. **Startpunt-advies:** begin bij **alleen de applicatie**
   (één object-type, één scherm) — ~80% van de waarde; later additief naar koppeling/
   verantwoordelijkheid/plek. "Meteen aan alles" is de generieke eindvorm maar groter (raakt de
   gedeelde element-structuur + meerdere schermen). **Positie:** zelfstandig (geen externe bron,
   geen AI, geen tweede referentiemodel nodig) → mogelijk eerder oppakbaar dan de wizard-horizon.
   Status: **richting/wens — ná gate 4; read-only feitencheckpoint vóór de bouw**.

### Sluitprotocol LI042 (2026-07-16) — afsluitpunten

G4-3. **Audit-ketenbreuk in de dev-`audit_log` (data-conditie, niet-blokkerend).** Twee live-tests
   in `test_audit_capture_live.py` (`test_keten_verifieert_over_echte_rijen` +
   `test_gelijktijdige_appends_blijven_lineair_geen_fork`) verifiëren de héle geaccumuleerde keten
   (89k+ rijen) en falen op een breuk-rij van **2026-07-14** (vorige sessie). Ze lezen DB-inhoud,
   niet code; audit is append-only. **Geen code-regressie.** Status: **opschonen/herzien wanneer
   relevant** (bv. verse dev-DB of keten-herstart) — niet als nieuwe breuk lezen.

G4-4. **Dode proces-handoff-tak op de kaart na de bedrijfsfunctie-plek-laan-swap (LI043).** **Gebruiker:**
   vanaf proces-detail zet "Bekijk op kaart" nog de chip **"Proceslandschap: X"** en landt op een proceslaan
   die na slice 2 (`095491b`) niet meer op de kaart rendert — een doodlopend pad zolang het procesregister
   nog zichtbaar is. **Wat nog leeft (`LandschapskaartView.vue`):** de proces-handoff-tak `openViaProces` /
   `procesIngang` / `toonHeleBoom` / `wisProcesIngang` / `procesInzoom` / `zoomInOpProces` + de chip-banner
   "Proceslandschap: X" + de `onMounted` mount-handoff-tak (~regel 2793), gevoed door de "Bekijk op kaart"-
   handoff op proces-detail/-lijst (`zetKaartHandoff`). **Besluit (LI043):** adresseren in de
   **proces-register-afbouw (sloop-stap binnen gate 4)**, in één keer samen met de proces-schermen die de
   handoff voeden. **Niet** als losse halve patch: alleen de chip weghalen maakt de "Bekijk op kaart"-knop op
   proces-detail doodlopend; de tak schoon verwijderen vraagt tóch de proces-schermen aan te raken — en dat
   ís de sloop-stap. Eén sloop, niet twee. **Verband:** G10 (backend proces-endpoints blijven slapend —
   slice 3); `docs/Feitenrapport-gate4-slice3-sloop-en-seed-V043.md` §1a (Groep B: "samen met ProcesDetail/
   ProcesLijst slopen, niet los"). Status: ✅ **AFGEROND (LI044, `c82ad80`)** — de procesregister-UI is
   gesloopt (nav/routes/`ProcesLijst`/`ProcesDetail`/secties/`PartijProcessenSectie`); de kaart
   proces-ingang/-inzoom-handoff, de chip "Proceslandschap: X", de `onMounted` mount-handoff en de
   doodlopende "Bekijk op kaart" zijn weg. Bouwstenen + slapende backend-endpoints behouden.

G4-5. **Domein-lezing op de kaart toont nog een placeholder — afleiden uit de bedrijfsfunctie-as (samen
   met brok 3, LI043).** **Bevinding (feitcheck `feitcheck-domein-bron`):** de kaart-domein-lezing (slice A,
   `ac9db21`) kleurt op `LandschapsNode.domein`, maar dat veld is een **componenttype-proxy** — het schema
   zegt letterlijk "componenttype-label · proxy voor functioneel domein" (`schemas/landschapskaart.py:21`;
   `landschapskaart_service.py:237`). Er is **geen** `component.domein`-kolom en **geen**
   `Bedrijfsfunctie.domein`. Gevolg: alle 16 applicaties resolven naar één waarde "Applicatie" → de lezing
   onderscheidt niets. De vier displays die `n.domein` tonen (kaart-kleur+legenda, zoek-string, node-popup,
   detail-paneel) tonen daardoor allemaal "Applicatie" als domein. **Besluit (LI043):** het domein van een
   component wordt **afgeleid uit de bedrijfsfunctie(s)** waar het onder hangt (component → functievervulling
   → omhoog door de aggregation-boom → wortel = domein) — read-only leeslaag, **geen schema, geen eigen
   `component.domein`-kolom** (dat zou een tweede waarheid naast de functie-as zijn); hergebruikt gate 4.
   **Bouwen samen met brok 3 (seed-verhaal):** nu draagt slechts **3/19** componenten een functievervulling;
   een afgeleide domein-lezing zou tot brok 3 voor 16/19 leeg zijn → brok 3 vult de component→functie-
   koppelingen, de afgeleide domein-lezing landt daarbovenop. **Open keuze bij de bouw (niet nu):** welke
   **boomlaag** is "het domein"? Gevonden zijn **8** GEMMA-wortels (Belastingoplegging · Bewaking · Klant- en
   keteninteractie · Ondersteuning · Ontwikkeling · Regievoering · Sturing · Uitvoering); een herkenbaardere
   domein-laag (sociaal domein / publieksdiensten / fysieke leefomgeving / veiligheid) zit vermoedelijk een
   laag dieper. Plus **meervoud** — een component onder meerdere domeinen → alle tonen, nooit stil één kiezen
   (LI041-kernregel, ADR-044). Status: **geparkeerd — bouwen samen met brok 3**.

G4-6. **Slice B verbreed — de vijf plek-standen als één ernst-taal in lijst én kaart (gedeelde codering,
   LI043).** **Aanleiding (mockup goedgekeurd):** in de Bedrijfsfuncties-lijst valt "nog niet vastgelegd
   waarmee dit werk gedaan wordt" nu weg — het herhaalt zich in dezelfde grijstint bij elke functie, dus de
   consultant ziet niet dat daar werk ligt. Oplossing: geef **elke stand zijn ernst-kleur**, consistent —
   niet één label rood. **Ontwerp (belegd):** één **gedeelde ernst-codering** (bron voor kleur + icoon +
   tekst per stand) die **lijst én kaart** erven — "één feit, meerdere ingangen", geen twee talen die uit de
   pas lopen:
   - **er ligt werk → amber:** `gat` ("nog niet vastgelegd waarmee dit werk gedaan wordt") én `werkvoorraad`
     ("systeem bekend, gebruiker nog niet vastgelegd") — beide amber, eigen icoon/tekst zodat het soort werk
     leesbaar blijft.
   - **hier draait iets → groen:** `hier` ("hier draait: {systeem}").
   - **gedekt via boven → blauw:** `via_boven` ("ondersteund via {bovenliggende functie}") — informatief,
     geen werk.
   - **bewust niets → grijs/rustig:** `niets` ("hier wordt bewust niets gebruikt") — een afgerond besluit,
     omrand en gelabeld zodat het niet leest als leeg.
   **Scope-verbreding t.o.v. de oorspronkelijke slice B:** slice B was "de vijf standen als rand-cue op de
   **kaart**"; het wordt "**de vijf standen zichtbaar als één ernst-taal in beide vensters** (lijst + kaart),
   uit één gedeelde codering". De lijst toont de standen-pills (mockup); de kaart dezelfde standen als
   rand/kleur uit diezelfde bron. **Verband:** voedt óók de stand-filter (slice C — alleen filteren op
   zichtbare standen, LI043-besluit D). Status: **besloten — bouwen als (verbrede) slice B**.

C1. **Contract-registratie — leeslaag + spiegelsignaal (notitie klaar, besluit open).** Bron:
   `docs/Analyse-contractregistratie-V040.md`. Kernpunten:
   - **A1** = afgeleide **contract-afloop-status** als leeslaag (loopt / verloopt / verlopen),
     head-neutraal, exact het `plek_standen`-patroon (afgeleide stand uit bestaande feiten, nooit
     wegschrijven — likara-backend §Afgeleide-leeslaag-recept).
   - **A2** = spiegelsignaal **"component zonder contract"** (registratiegat, zoals "zonder
     bedrijfsfunctie").
   - **B1** = verantwoordelijkheid/toelichting op contract (skills LI038 — besloten, niet gebouwd).
   - Bedrag/administratie bewust **buiten scope**. Bouwen **ná** gate 4. Besluit docs-vastleggen/ADR
     staat open. Status: **richting/wens — besluit + read-only feitencheckpoint vóór de bouw**.

T1. **Tool-cadans actief per volgende sessie (vastgelegd in likara-werkprotocol).** Sessiestart
   `/doctor` (health + volledige checkup); pre-commit `/security-review` (smal) + `/code-review ultra`
   (breed; `/ultrareview` = deprecated alias), met `/code-review ultra` verzwarend naar **vaste
   pre-commit-stap** richting productie. Alle user-triggered (CC kan ze niet zelf starten). Status:
   **actief — geen bouwpunt, borging-in-gedrag**.

### Nieuw uit LI040 (2026-07-13) — ADR-045 "ondersteunt werk"

1. **"Geweerd tonen mét reden" — evaluatiepunt in echt gebruik.** ADR-045 besluit 3
   verwierp de uitleg-bouwsteen ("waarom ontbreekt deze optie") voor de MVP: in een
   onvolledig landschap is "niet gevonden" meestal *niet geregistreerd*, niet *geweerd* —
   een verklaring zou dan raden. De koppel-picker krijgt een altijd-ware scope-regel
   ("Componenten waarmee werk gedaan wordt"); dáárop kan "geweerd tonen mét reden" later
   groeien, zonder herbouw. Status: **geparkeerd, evalueren in echt gebruik**.
2. **Registratie-feiten: teruggeknipt (besloten LI040).** Het brede spoor
   (verantwoordelijkheid, benoemde verwijzingen, twee ankers, verplichte reden) blijft
   **blok D — ná de MVP**. Gate 2 neemt wél mee (hoort bij de registratie zelf):
   **wie/wanneer server-gestempeld op het feit** (zichtbaar op de plek; audit = vangnet,
   nooit de leeslaag) + **optionele vrije toelichting** bij "hier gebruiken we geen
   systeem". Verplichte reden verworpen voor de MVP (leert ruis typen). Zie ADR-045
   opvolgpunt 2. Status: **besloten — gate-2-scope**.
2b. **Gate-2-/import-ontwerpeisen uit de plaatsingsstabiliteitsmeting (ADR-044
   addendum LI040, meting: 0 verhangen over 9 maanden, 301/301 identiek).** Geen
   overleef-machinerie; wél twee vangrails: (1) het inleesvoorbeeld benoemt een
   **verhuizing** als vierde categorie ("X verhuist van A naar B — hier hangen N
   componenten en M bevindingen aan"); (2) de import verwijdert **nooit stilzwijgend
   een plaatsing mét registratie** (markeren + melden, nooit CASCADE over veldwerk).
   Herhaalmeting bij elke nieuwe release-curatie (releasegeschiedenis in HERKOMST.md).
   Status: **besloten — ontwerpeis gate 2/import**.
3. **Gelijktijdig vastleggen door twee consultants op dezelfde plaatsing.** Geen
   taakvraag maar een registratievraag: weigeren of eerlijk melden, nooit stil de laatste
   laten winnen. Status: **ontwerppunt gate 2**.
4. **Dode functie `_seed_tweede_type` in de dev-seed (stale docstring).**
   `backend/dev_seed_testdata.py:682` wordt niet aangeroepen vanuit `main()` en de
   docstring ("database blijft false") is achterhaald door LI058/migratie 0046
   (checkpoint-bevinding LI040). Opruimen bij de ADR-045-bouw of expliciet parkeren.
   Status: **open**.

### Nieuw uit LI039 gate 1b (2026-07-13) — referentiemodel inlezen

1. **GEMMA "Toelichting"-property (169/297 functies) blijft in de MVP liggen.** Het
   AMEFF-bestand draagt naast de `<documentation>`-definitie een vrije-tekst-property
   "Toelichting" (voorbeelden, uitleg). De parser (`services/ameff.py`) leest hem bewust
   niet — bewuste MVP-keuze, geen stille beslissing (opdracht gate 1b §1.1). Bij
   oppakken: meenemen als tweede leesveld op de functie (weergavevraag: waar toont de
   UI hem). Status: **open**.
2. **Toestandsbouwsteen "lege uitkomst ≠ fout" (fase-A patroon 8) — converge bij n≥2.**
   De `aanbodStaat`-enum die 'fout' (rood) en 'leeg' (rustig) structureel uitsluit is
   PER SCHERM gebouwd (inleesdialoog, BedrijfsfunctieLijst). Het volgende scherm met een
   lijst + foutpad kan dezelfde overlap-bug opnieuw maken — de fout van de LI039-
   browsercheck, wachtend op herhaling. Zodra een tweede scherm dit nodig heeft: één
   gedeelde bouwsteen (composable) i.p.v. een tweede inline enum. Status: **open (n=1)**.
3. **Picker-uitleg "waarom ontbreekt een optie" (fase-A patroon 11) — HERZIEN door
   ADR-045 (LI040).** Het voornemen "picker legt uit waarom een optie ontbreekt" is bij de
   LI040-weging verworpen (een verklaring van afwezigheid kan in een onvolledig landschap
   niet betrouwbaar zijn) en vervangen door een altijd-ware **scope-regel** onder de
   picker (ADR-045 besluit 3). "Geweerd tonen mét reden" staat geparkeerd als
   evaluatiepunt (zie LI040-punt 1 hierboven). Status: **herzien — zie ADR-045**.
4. **Afkappen definitie-leeslaag op zinsgrens i.p.v. regelgrens — te wegen.** De
   tweelaags rij kapt de definitie op twee regels (`line-clamp`, woordgrens); een
   zinsgrens-garantie bestaat niet. In de praktijk zelden relevant (mediaan
   GEMMA-definitie ≈ 90 tekens). Status: **open, laag**.

### Nieuw uit LI038 (2026-07-12) — ADR-043 herijkt ADR-042

1. **ADR-042 is herijkt door ADR-043** (`docs/adr/ADR-043_Bedrijfsfunctie_als_logische_ruggengraat.md`):
   de "waarvoor"-as van de logische kaart verschuift van **proces** naar **bedrijfsfunctie**
   (eigen element-as, ArchiMate BusinessFunction; referentiemodel als eerste-klas begrip,
   GEMMA = instantie 1; bronsleutel = identiteit; vervallen ≠ verwijderen).
2. **Het procesregister is GEPARKEERD — verborgen, niet verwijderd** (ADR-043 MVP-scope):
   in de MVP geen menu-item/ingang/proceskolom; `proces`/`procesvervulling` en de LI038-bouw
   (boom, diagram, inzoom/history, gap-cue) blijven intact en worden door de functie-as
   **hergebruikt** (n≥2-abstractie). Terugkeer later als detaillering ónder de functie-as,
   nooit ernaast. Status: **besloten (LI038); bouw-fasering + open subknopen in ADR-043**.
3. **ADR-043: 8 open subknopen** — te beslissen vóór de bouw van de bedrijfsfunctie-as
   (subtype, bronsleutel-plek, referentiemodel-entiteit, koppelregel-vorm, topgroeperingen,
   soft-vervallen, AMEFF-parser, verhouding tot het registratie-feiten-spoor). Status: **open,
   eerste stap van TOP-1**.
4. **ADR-spoor "generieke registratie-feiten op objecten"** (besloten LI038; vastgelegd in
   likara-domeinmodel §LI038/ADR-043): verantwoordelijkheid (met rol) + toelichting/benoemde
   verwijzingen op component, contract, proces/bedrijfsfunctie **én koppeling** (`relatie.id`).
   Twee ankers, geen polymorfe FK, document = benoemde verwijzing (geen upload).
   **Dwarsdoorsnede:** de "eigen laag bij een referentie-object" (ADR-043 besluit 5) is
   hiervan een instantie → **samen ontwerpen met de bedrijfsfunctie-as**, niet erna, anders
   bouwen we de eigen-laag twee keer. Status: **open, ADR-waardig**.

### Nieuwe opvolgpunten uit LI037 (2026-07-11)

1. **Proces-only diagram — GESLOTEN (geland LI038, commits 82806ff/e91f2a2/f1d3270).**
   Boom|Diagram-schakelaar in het processen-scherm, zoeken (label-niet-filter + ×-wis in
   ZoekSelect), klik-popup met drie uitgangen, dubbelklik-inzoom op proces-ids + history
   ("← Terug"), "Toon in procesbeeld" vanuit de Boom. Ook het gate-1-punt "centrum vervalt
   bij weergave-wissel" is in gate 3 **gesloten** (`centrumGewijzigd` behoudt de plek).
2. **ADR-spoor procesafhankelijkheden/flow (spoor 2).** Proces→proces bestaat NIET als feature
   (`ouder_id` = enige band; ADR-042 parkeerde flow). Harde belofte: de "opzij" in het Diagram
   is nu **zusjes**; doorstroom-opzij komt er bovenop **zonder herbouw**. Let op: de
   relatie-facade valideert **géén** bron/doel-elementtype → een flowlaag vergt expliciete
   type-borging. *Urgentie gedaald door ADR-043 (proces is niet langer de dragende as).*
   Status: **open, ADR-waardig**.
3. **Detailscherm-procesbeheer.** Verwijderen/verhangen óók op het proces-detailscherm (nu
   alleen op de lijst). **Besluit A: nu niet** — de taakverdeling (structuur = lijst, inhoud =
   detail) is bewust. Status: **kandidaat-slice**.
4. **Rollenmodel: generieke matrix vs. functionele rollen.** Bv. een "Procesbeheerder" die de
   processtructuur en -toepasbaarheid beheert, los van de technische platformbeheerder.
   Strategisch ADR (raakt RBAC/Keycloak/seed platformbreed); + aanpalend concept
   **proces-toepasbaarheid** (wel/niet van toepassing, mogelijk per tenant — bestaat nu niet).
   Status: **te groot voor nu, bewust geparkeerd**.
5. **Productie-evaluatiepunt: proces-ingang-weergave.** Slimme default + wisselen achteraf
   (geen keuzevraag vooraf). Met echte gebruikers toetsen of een expliciete keuze of een
   voorkeur-laag (ADR-041) gemist wordt. Status: **evaluatie in productiegebruik**.
6. **History-grens hele-landschap-herstel** (bestaand punt, herbevestigd LI037). "← Terug"
   over de set→hele-landschap-vlag-grens herstelt de vlag niet (`_herstelToestand`); de
   inzoom-terugweg set↔set werkt volledig. Status: **read-only checkpoint + fix in een
   volgende sessie**.

---

### Stand V037 (sluitprotocol LI036 — Lagenweergave mét proceslaan, 2026-07-10)

Build **V036 → V037**. Geland: **"Lagen" als derde kaart-weergave** (preset-baanposities +
HTML-band-overlay, meet-stap-render-fix, maatwissel = resize+fit, `7b4c00c`), **rolbanen met
rol-accent** (partij als instance per rolbaan, rol-tags delen dim-staat, `7b4c00c`), **"ring uit
wint van gaps" + organisatiebalk in-beeld model i** (`0b4a5dd`), **proceslaan slice 2 stap 1–3**:
backend proces-projectie (roll-up naar hoofdproces, cyclus-veilig, één roll-up-definitie, engine
onaangeroerd, `d2b07f3`) + proceslaan/ring "Processen"/proces-vorm (`5fa5fe0`) + aantal-badge/
herkomst-popup/vervul-toggle met exact-ongedaan-maken (`f9a8a6f`). 16 patronen geborgd in vijf
likara-skills (`9914c25`); ADR-034/040 bijgewerkt naar de gebouwde realiteit — diepte-punt "alleen
hoofdprocessen" prominent als tussenstand (`a99fe23`). Tests: backend 1001/2 skipped, frontend
80 files/1006. Migratie-head **0059** (geen schema-wijziging).

**Top-6 volgende sessies: zie NEXT_SESSION.md** (deelprocessen eerste-klas op de kaart incl.
proces-als-vertrekpunt; plaatstaat-herstel na onderbreking; Architectuur-scherm verwijderen;
beginscherm als enige vertrekpunt; rapportage & export; bredere ruggengraat).

**Losse/kleinere punten uit LI036 (niet in de top-6):**

1. **Rol-accent beknopt/uitgebreid als persoonlijke kijkvoorkeur via ADR-041** — ná
   browserbevestiging van de uitgebreide vorm.
2. **Labelkeuze "Rollen & beheer" → "Partijen & rollen"?** — de baan verzamelt alle
   partij-rollen (gebruikt/levert/beheert/eigenaar), niet alleen beheer.
3. **ADR-register aanvullen** — `docs/adr/README.md` mist de rijen ADR-026 t/m 033, 035 en 036
   (ouder gat, door CC gemeld deze sessie; ADR-034/040-rijen zijn wél bijgewerkt).

---

### Stand V036 (sluitprotocol LI035 — lijststaat + ADR-042 volledig, 2026-07-09)

Build **V035 → V036**. Geland: lijststaat-patroon (`useLijstStaat`, 4 lijstschermen, `9128a24`) en
**ADR-042 volledig** — procesregister (nestbare boom, migraties 0056/0057), applicatiefunctie-catalogus +
koppelregel (0058/0059, `ddb7b7a`), proces-schermen + regel-acties + MeldingBanner (`3a65c3b`),
componentkant met vier-vragen-Overzicht + overlay-formulier (`0c4fe60`), en roll-up-inzicht +
organisatie-proceskijk + succes-toast-standaard (`8a76f55`). Zes browsercheck-bevindingen zijn als
systeembrede patronen geland (Dialog-primitive incl. scroll-schaduw, breedte-override-borging,
MeldingBanner, samengevoegd "Onderliggende processen"-blok, succes-toast, regel-acties) en met de
correcties vastgelegd in de acht likara-skills. Tests: backend 997/2 skipped, frontend 80 files/965.
Migratie-head **0059**.

**Nieuwe/geactualiseerde opvolgpunten uit LI035 (volgorde-advies):**

1. **ADR-034-herbouw lagenweergave (mét proces-laan).** De lagenweergave opnieuw opbouwen op de
   kaart-selectie, nu inclusief een proces-laan. Drie LI035-ontwerpnotities meenemen: (a) nesting van de
   procesboom binnen de business-laan (hoe diep tonen), (b) selectie-semantiek (wat betekent een
   proces-klik voor de kaart-set), (c) roll-up in de laan (toont een hoofdproces de doorgerolde
   componenten of alleen de directe).
2. **Audit-dekking entiteit-deletes (systemisch, pre-existing) — HOOG.** De centrale audit hangt op
   ORM-flush-hooks; een delete via het element-supertype (core-execute) audit de subtype-rij niet.
   Structurele oplossing kiezen (ORM-delete-norm, expliciete audit-regel bij element-delete, of
   DB-level vangnet). Zie likara-backend/-security (LI035).
3. **UI-consistentie-bundel.** (a) 11 bevestigingsdialoog-klonen migreren naar de gedeelde
   `BevestigVerwijderDialog`; (b) 2 bestaande warn-banners (ChecklistscoreSectie, MigratiegereedheidSectie
   e.o.) naar `MeldingBanner`; (c) `PartijRollenSectie` mist de verwijder-symmetrie (regel-acties-patroon).
4. **Kaart component-breed maken (ADR-spoor, herbevestigd).** IJkpunt: een database is nu niet
   zoekbaar/doorklikbaar op de kaart.
5. **Beginscherm-/kaartverfijningen (herbevestigd, was 3–6 in LI034):** filterbalk verbergen op leeg
   beginscherm; opgeslagen view + organisatie-scope (ADR-033-vervolg); filterbalk vereenvoudigen
   (BIV/Rol achter "geavanceerd"); beginscherm-contextvelden unie-feedback.
6. **GEMMA-procesimport/startset (eigen ADR-spoor, ná ADR-034).** Startset processen importeren
   (GEMMA-geënt); notitie: sturend/primair/ondersteunend als filter-/typeringsvraag meenemen; de
   LI035-validatie dat het GEMMA-landschap 1-op-1 op het model past is de basis.
7. **LandschapskaartView: historische "LI036"-commentlabels rechtzetten** (mislabeld — die wijzigingen
   waren LI034; klein, alleen comments).

**Reeds afgerond in LI035 (uit de actieve lijst):** lijststaat-terugnavigatie (was 1e taak);
proces/functie-inzicht punt 1 (ADR-042, volledig — het "koppel aan het directe ondersteunende
component, erf de rest"-uitgangspunt is in de ADR verwerkt; component-breed als vangnet gerealiseerd).

**Herbevestigd (blijft open, uit eerdere sessies):** ADR-035 slice 3 (signalering-vervolg); ADR-036
UI-restpunt (coarse organisatiegebruik-form); `VerantwoordelijkheidSectie` partij-picker-scope
(ADR-024-domeinvraag); LI032-restpunten (username≠e-mail post-check, 404-friendly display,
reseed-ergonomie, auth #5c end-to-end); LI033b-stash `stash@{0}` (beslissing Bert: droppen of houden);
ADR-040-vervolgfasen (terug/vooruit-navigatie = verplichte terugbouw, interactie-basis, 4 ringen,
overige objecttypes centreerbaar, scope-B).

---

### Stand V035 (sluitprotocol LI034 — ADR-041 voorkeuren + kaart-bugfixes, 2026-07-08)

Build **V034 → V035**. Geland: ADR-041 persoonlijke voorkeur-laag (`gebruiker_voorkeur`, migratie **0055**,
RBAC eigen-scope, `9498983`), component-breed organisatiegebruik-schrijf-slot (`b05cc53`), terugrol
sectie-voorkeur (`f5e7afe`), kaart-kijkfilter-standaard + reload-fix (`c8ae3c7`), kaart-bug B doorklik
(`33fa485`), kaart-bug A leeg canvas (`3d889ab`), + 7 skillpatronen. Tests: backend 960/2 skipped,
frontend 71 files/869. Migratie-head **0055**.

**Eerste taak volgende sessie (read-only):** lijststaat (filter/zoek/sortering) behouden bij terugnavigeren
vanuit een detailscherm — bevestigd op Partijen. Momentkeuze-behoud bij terugkeer, géén voorkeur-laag.
Zie NEXT_SESSION.md.

**Nieuwe/geactualiseerde opvolgpunten uit LI034 (volgorde-advies):**

1. **Proces/functie-inzicht (groot, ADR-waardig — VERDER VERDIEPEN).** Component "vervult een rol in" een
   proces/functie; proces/functie als één hiërarchische laag (proces boven, functie eronder); impact rolt
   omhoog (functie-raakvlak telt mee op procesniveau); rol als beheerbaar catalogus-kenmerk; **begin grof**
   (proces + koppeling eerst, functie later); flow/volgorde tussen stappen bewust buiten scope.
   **Kern-uitgangspunt (LI034, nog te verdiepen):** een proces koppelt aan het **component dat het
   functioneel ondersteunt** (in de praktijk vrijwel altijd de applicatie/dienst — het "loket"). De
   **onderliggende afhankelijkheden (database, infra, contract, leverancier) worden geërfd via de al-
   geregistreerde component-ketens** — niet dubbel vastleggen. De impactvraag "wat raakt dit proces" volgt
   dan automatisch de bestaande keten (proces → applicatie → …). **Component-breed blijft als vangnet
   mogelijk** (koppeling mág aan elk componenttype als een proces rechtstreeks op iets zonder applicatie-
   tussenlaag steunt), maar de norm is: koppel aan het directe ondersteunende component, erf de rest.
   Sluit aan op LIKARA's principe "relatie één keer vastleggen, impact volgt de keten" (geen dubbele/
   afgeleide registratie). **Dit uitgangspunt expliciet verder verdiepen in de uitwerking** — de grens
   tussen directe koppeling en geërfde keten, en wanneer een directe niet-applicatie-koppeling terecht is.
   Aanpak: read-only verkenning (element-familie-subtypes, hiërarchie-constructie, relatiekenmerk-
   catalogus) → concept-ADR.
2. **Kaart component-breed maken (ADR-spoor).** De kaart is bewust applicatie-centrisch (`appNodes`/
   zoeklijst, `componentBuren`, buren/context-set-acties, diepte-2-ego). Elk componenttype zoekbaar/
   doorklikbaar/als buur maken raakt die ontwerpkeuze → eigen ADR. IJkpunt: een technology-component
   (database) is nu niet zoekbaar en heeft geen doorklik.
3. **Beginscherm-filterbalk verbergen op het lege beginscherm.** De linker filterbalk dubbelt met "Begin
   je verkenning" zolang de kaart leeg is; balk pas tonen zodra de kaart getekend is. (Apart: horen de
   start-filters Laag/Hosting/Eigenaar achter "+ Filters" daar wel?)
4. **Opgeslagen view onthoudt de organisatie-scope niet (ADR-033-vervolg).** Een view bewaart bewust
   alleen de set, geen kijk-instellingen. Weging: wil je dat een view ook de organisatie-scope (en evt.
   andere kijk-instellingen) bewaart, tegen de "view = startpunt"-intentie in?
5. **Filterbalk vereenvoudigen.** BIV-drempels + Rol zijn specialistisch (audit-/risicolens, alleen op
   geclassificeerde componenten) — kandidaat voor een "geavanceerd"-inklap; op beide weergaven of alleen
   Overzicht?
6. **Beginscherm-contextvelden (unie-gedrag).** Leverancier/Contract/Organisatie stapelen additief (unie
   met dedup). Wenselijk? Feedback per veld ("N toegevoegd")?

**Reeds afgerond in LI034 (uit de actieve lijst):** ADR-041 (persoonlijke voorkeuren + kaart-kijkfilter-
standaard + reload-fix); kaart-bugs A (leeg canvas) en B (doorklik gelijkgetrokken); component-breed
organisatiegebruik-schrijf-slot.

---

### Stand V034 (sluitprotocol LI033 — ADR-040 kaart-herbouw, 2026-07-07)

Build **V033 → V034**. Geland (ADR-040 Fase 1): deterministische render-eigenaar / fcose weg
(`bf5c287`), tweedeling Overzicht/Praatplaat + expliciete weergave-state + schakelaar, Impact-verkenner
afgeschaft (2a, `e8fe7d3`), voorspelbare organisatie-scope (eenmalige seed, balk alleen op Overzicht,
2b, `e7f74ef`), afgeleide gebruikt-lijn org→app + gebruikt-ring + afdeling-sub-picker weg (3-1,
`559a34c`), layout-herziening (samenval-fix `animate:false`, Overzicht=grid centrumloos, Praatplaat=
concentric+ellips, grotere knopen; `559a34c`), en 12 skillpatronen (`ef17fed`). Tests: backend 951/2
skipped, frontend 71 files/840. Geen schema-wijziging (migratie-head **0054** ongewijzigd); enig
backend-raakvlak = de afgeleide read-only gebruikt-edge.

**Vervolgfasen ADR-040 (open, geprioriteerd):**
- **Terug/vooruit-navigatie — VERPLICHTE terugbouw (uitgesteld, niet geschrapt).** De render-eigenaar is
  ontvlochten zodat history als **losse laag** terug kan. Hoog: het is bestaand gedrag dat tijdelijk niet
  door de nieuwe weergave-state loopt.
- **Interactie-basis: klik = highlight + rest dimmen + verplaatsbare popup** (kern-details + relaties in
  leesbare taal + link naar de volledige pagina). Dubbelklik = hercentreren (bestaat al). Fase 2.
- **De 4 component-ringen volledig inrichten** (gebruikt door · beheer · contracten & leveranciers ·
  infra & koppelingen) — fase 2; de praatplaat toont nu de ego-kring (skelet).
- **Overige objecttypes centreerbaar** (contract, leverancier, afdeling, persoon/rol, infra) — elk een
  ring-definitie op de praatplaat-motor (ADR-040 open subknoop 1).
- **Scope-B-verfijning** (toggles onthouden over set-wijzigingen) — later, samen met history-/scope-werk
  (nu A: elke set-wijziging → alle orgs aan).
- **LI033b-stash `stash@{0}`** — handoff/org-bron/`toonImpactVoor`/grof-only bleken al geland vóór de
  herbouw; alleen gebruikt-edge + gebruikt-ring + sub-picker waren nieuw (geland in 3-1). **Beslissing
  Bert:** stash droppen of als referentie houden — niet zelf droppen.

**Herbevestigd (blijft open, uit eerdere sessies):**
- ADR-036 UI-restpunt (coarse `organisatiegebruik`-form).
- `VerantwoordelijkheidSectie` partij-picker-scope (ADR-024-domeinvraag).
- LI032-restpunten: gebruikersnaam≠e-mail post-check, 404-friendly display, reseed-ergonomie.

### Stand V033 (sluitprotocol LI032 — gebruiker-cluster, 2026-07-05)

Build **V032 → V033**. Geland: contactpersoon uit register (ADR-039, migratie 0054), centrale
sessie-vangrail, ter-plekke-aanmaken afdeling (gedeelde `AfdelingSelect`, 4 plekken), gebruiker
aanmaken + bewerken (organisatie intern-only + gescoopte afdeling), account-/picker-reparaties
(conditionele Keycloak-aanroep, PUT zonder username, 2e interne testorganisatie, stale-label-`:key`,
param-filterende picker-integratie-testhelper), en 18 LI032-skillpatronen. Tests: backend 866+80,
frontend 825; migratie-head 0054.

**Nieuw geparkeerd deze sluiting:**
- **Provisioning username==email-aannames.** De update-PUT stuurt geen `username` meer (opgelost in
  `ca8c999`); controleer of elders in de provisioning-flow nog impliciete `username==email`-aannames
  zitten. Laag, auth.
- **404 op een verdwenen bewerk-/detailitem** vriendelijker tonen — inline "bestaat niet (meer)"
  i.p.v. een toast op een leeg formulier. Laag, UX (kwam op bij de reseed-stale-id-casus).
- **`LandschapskaartView.test.js` / `LandschapskaartPopups` parallel-flake** (cytoscape
  unhandled-rejections bij teardown) — geen falende test; mee te nemen bij de impact-verkenner-
  render-herbouw.

### Auth-cluster (LI032 — na de verlopen-sessie-vangrail)

- **#5c — echte end-to-end auth-keten-test (eerste vervolg binnen het auth-cluster).** De 401→refresh→
  retry-logica is nu **structureel** gedekt (offline, gemockt): frontend `api.test.js` (3 refresh-takken +
  vangrail-handler), backend `test_auth_pkce.py` (`/auth/refresh` happy + 3 faalpaden). **Het gat:** geen
  test die de seams samen bewijst — een kortlevende `lk_session` → echte `/auth/refresh` → echte Keycloak
  refresh-grant → echte Redis-handle-rotatie → geslaagde retry, plus een écht-verlopen refresh die naar
  login leidt. Vergt de volledige stack + een manier om access-token-expiry te forceren (korte TTL).
- **Reseed/herstart doodt sessies stil (dev-ergonomie).** Een stack-reset (Redis/Keycloak weg) →
  `auth_refresh:{sessie_id}` verdwijnt → refresh faalt → 401. De centrale vangrail (LI032) vangt het
  symptoom nu **netjes** af (redirect naar login i.p.v. rauwe code). Resteren: na een reseed opnieuw
  inloggen is verwacht gedrag; Redis/Keycloak-persistentie over een reset heen is een aparte,
  lager-geprioriteerde afweging.

### Stand V032 (sessie-afsluiting LI031 — ADR-038 gebruikersgroep-consolidatie + intern/extern, 2026-07-04)

Build **V031 → V032**. Eén consistent model: een gebruikersgroep hoort **altijd** bij een organisatie;
burger-doelgroepen zijn gewone **externe organisaties met afdelingen**. Intern/extern is een expliciet
kenmerk op partijen (kiesbaar + zichtbaar). Dode resten opgeruimd.

**Geland deze sessie:**

| Commit | Slice |
|---|---|
| `1d9ab3a` | ADR-038 geschreven (register bijgewerkt) |
| `2f1c816` | Slice 1a — `partij.scope` (`partij_scope_enum` intern/extern, additief), migratie `0052`: nullable + 2 CHECKs (gezet iff organisatie/externe_partij; externe_partij vast extern; afdeling/persoon leiden af); default extern op organisatie; seed BvoWB=intern; dubbele engine-borging |
| `195c489` | Slice 1b — consolidatie, migratie `0053`: `gebruikersgroep.gebruik_id` NOT NULL (FK → RESTRICT); `burger`-aard uit `partij_aard_enum` (type-recreate); organisatie verplicht (Create + service-422; werk_bij weigert null); dode resten weg (kaart-veld `gebruikt_door_organisatieloos` + signaal `gebruikersgroep_zonder_organisatie`); seed: burger-doelgroepen = 3 externe organisaties + 6 segment-afdelingen + 5 groepen |
| `edb4eb8` | Slice 2a — groep-dialoog organisatie verplicht (client-side inline-melding + `*`-markering; org-loze payload-tak weg; dode `orgAard`-state opgeruimd) |
| `3ec3320` | Slice 2b — intern/extern-UI: kiesbaar in `PartijFormulier` (radio-kaartjes, default Extern; vast "Extern" bij externe partij; niet bij afdeling/persoon), leesbaar in `PartijDetail` |
| `6702bd2` | Slice 2c — kaart: dood burger-silhouet/label/legenda/predicate opgeruimd |

**Nieuw opvolgpunt uit LI031 — top-prioriteit LI032:**

1. **Contactpersoon als keuze uit personen van de eigen organisatie — SCHEMA-GATE (ADR-waardig).**
   **Expliciet vóór GebruikersgroepDetail (besluit Bert).** Vrije tekst → verwijzing naar een
   **persoon-partij van de organisatie zelf**. Sjabloon = ADR-036a/037 (FK-kolom `partij.contactpersoon_id`
   + validator "persoon binnen deze organisatie" + read-verrijking `contactpersoon_naam` + migratie +
   dev-reseed). Bouwstenen klaar: read `api.partijen.lijst({aard:'persoon', organisatie_id})`, `ZoekSelect`,
   identiteit "persoon — afdeling — organisatie" (`_verrijk_context`). Beslist: optioneel; keuze uitsluitend
   uit personen met `organisatie_id = deze partij`; geen vrije tekst meer. **Vijf open ontwerpvragen vóór bouw:**
   (a) VOORAAN — contactpersoon ter plekke aanmaken bij nog-geen-personen (zoals de afdeling-picker), of
   alleen kiezen uit bestaande? (b) op welke aarden het veld — alleen organisatie-achtig (organisatie +
   externe_partij) i.p.v. alle? (c) vervangen vs. additief (aanbeveling: vervangen, met reseed);
   (d) `telefoon`/`mobiel`/`email`-vrijvelden bewust buiten scope; (e) migratie-landing defensief/reseed
   zoals `0053`.

**Runtime-restpunt:** verse reseed vóór browserverificatie (BvoWB=intern + burger-doelgroepen zichtbaar):
`docker compose down` → `docker volume rm likara_lk_postgres_data` → `up -d` → `dev_seed_testdata.py`
(`down -v` = deny).

**Doorgeschoven (ongewijzigd geldig):** GebruikersgroepDetail (opzet + signaal-scope beslist) + BlokkadeDetail
(conceptuele keuze eerst); org-context-patroon naar leverancier-picker + PartijLijst (+ intern/extern-kolom);
auth/sessie-cluster; Impact-verkenner render-herbouw; ADR-036 begin-grof-invoerroute.

Tests: backend **851** (module) + **80** (platform), 2 skipped · frontend **780**. Migratie-head **0053**.
ADR-register: **ADR-038** opgenomen.

---

### Stand V031 (sessie-afsluiting LI030 — ADR-037 verantwoordelijke per checklistantwoord, 2026-07-03)

Build **V030 → V031**. Het vrije-tekstveld "Eigenaar" op een checklistantwoord vervangen door een
gestructureerde **verantwoordelijke** (afdeling óf persoon uit het register); blokkade-eigenaar afgeleid.

**Geland deze sessie:**

| Commit | Slice |
|---|---|
| `e21a28e` | ADR-037 Pass 1 — schema-gate (migratie `0051`): `checklistscore.verantwoordelijke_id` (composiet-FK, SET NULL) vervangt `eigenaar`; `blokkade.eigenaar` gedropt (afgeleid); aard-validatie 422; dubbele engine-borging; seed-scenario |
| `4c8d113` | ADR-037 Pass 2 — verantwoordelijke-picker (afdeling/persoon, `aard_in`); aandacht-signaal `antwoord_zonder_verantwoordelijke` (engine-veilig via `table()`-handle) + velduitleg; Opslaan-knop leesbaar; identiteit "afdeling — organisatie" / "persoon — afdeling — organisatie" in lijst/veld/na-selectie |

**Nieuwe opvolgpunten uit LI030 (van meest naar minst gebruikerswaarde):**

1. **Detailpagina's — GebruikersgroepDetail + BlokkadeDetail.** GebruikersgroepDetail verst (grounding
   gedaan; scherm + identiteit-/applicatie-weergave + signalen-ter-plekke + objecthistorie-ontsluiting
   ontbreken). BlokkadeDetail: **open conceptuele keuze** (eigen pagina vs. doorklik naar de component-
   checklisttab) — eerst met Bert uitdenken vóór bouw; detail-read verrijken met herkomst.

2. **Breder org-context-patroon** — "afdeling — organisatie"-ontdubbeling (via `gebruikersgroepIdentiteit`)
   ook toepassen op de **ContractFormulier-leverancier-picker** + **PartijLijst** (de resterende niet-org-
   gescoopte afdeling/persoon-lijsten). ADR-037 paste het toe op de verantwoordelijke-picker.

3. **Auth/sessie-cluster** (uit het `NIET_GEAUTHENTICEERD`-onderzoek): (a) dev-sessie-robuustheid bij
   reseed — een stack-herstart (Redis/Keycloak) doodt levende sessies stil; persistentie of
   gedocumenteerde re-login; (b) UX-vangrail — 401 na gefaalde refresh → gebruiker naar opnieuw inloggen
   leiden i.p.v. een kale rode `NIET_GEAUTHENTICEERD`-toast; (c) auth/refresh-testgat — nu overal gemockt,
   geen echte 401→refresh→retry-dekking.

**Incident-lessen LI030 (geborgd in skills):** groene tests dekten tweemaal een kapotte UX niet (pas in
de browser zichtbaar): onleesbare Opslaan-knop (`--lk-color-accent` #E8F0FB + `text-white` = wit-op-
bijna-wit) en veld-vs-lijst-identiteit. Vuistregels toegevoegd aan `likara-frontend` (knop-leesbaarheid),
`likara-tests` (toets visuele/interactie-staat, niet alleen payload; browser-check vóór commit) en
`likara-ux` (identiteit-patroon voor niet-org-gescoopte afdeling/persoon-lijsten).

---

### Stand V030 (sessie-afsluiting ADR-036 + Velduitleg + ADR-036a, 2026-07-03)

Build **V029 → V030**. Organisatiegebruik van applicaties **end-to-end** gebouwd, veld-uitleg op alle
formulieren, afdeling structureel gemaakt, plus drie gerichte UI-fixes.

**Geland deze sessie:**

| Commit | Slice |
|---|---|
| `8e7e419` | ADR-036 pass 1 — grof gebruiksfeit + gebruikersgroep-verfijning (schema) |
| `bff1254` | ADR-036 pass 2 — kaart-afleiding + signaal + identiteit (read-only) |
| `889fc4d` | ADR-036 invariant-test "afdeling-met-org ⟹ grof feit" |
| `7cc6e24` | Velduitleg slice 1 — `VeldUitleg`-component + centrale `velduitleg.js` |
| `8ea87be` | Velduitleg slice 2 — content-uitrol (popover-'i') over alle formulieren |
| `480fa84` | ADR-036a pass 1 — gebruikersgroep-afdeling structureel (schema+service+seed, migratie 0050) |
| `a09a8cb` | ADR-036a pass 2 — afdeling-picker (search-first create-in-lege-zoekstaat) |
| `929435e` | Fix — bewerken-voorvulling gebruikersgroep (organisatie voorvullen uit grof feit) |
| `0e439d3` | Fix — contract-leverancier-picker versmald (`aard_in`) + seed geverifieerd geldig |

- **ADR-036 (compleet):** grof "organisatie gebruikt applicatie"-feit (`organisatiegebruik`) +
  gebruikersgroep als fijne verfijning (`gebruik_id`); kaart-afleiding "gebruikt door", read-only signaal
  "gebruik bekend, detaillering ontbreekt", identiteit "afdeling — organisatie". Invariant geborgd.
- **Velduitleg-slice:** alle formulieren voorzien van popover-'i'; ADR-036a-identiteit partij-verankerd.
- **ADR-036a (afdeling structureel):** `gebruikersgroep.afdeling` (vrije tekst) → `afdeling_id` →
  organisatie_eenheid-partij binnen de grove-feit-organisatie (migratie **0050**).
- **Drie UI-fixes:** bewerken-voorvulling (organisatie uit grof feit); contract-leverancier-picker
  versmald; (+ search-first afdeling-picker uit ADR-036a pass 2).

**Afgevinkt / opgelost deze sessie:**
- **Eigenaar-organisatie-picker** — onderzocht, **geen defect**: filter is correct (`aard=organisatie`),
  seed compleet (4 orgs), query levert alle 4. "Alleen BvoWB" was **stale seed-data** (reseed lost het op).
- **Afdeling-structureel** (ADR-036a) — gebouwd.
- **Contract-leverancier picker-scope** — versmald naar `aard_in=[organisatie, organisatie_eenheid,
  externe_partij]`; **seed geverifieerd geldig** (12 externe_partij + 3 organisatie voor de BvoWB-DVO's;
  nul persoon/burger). Geen seed-wijziging nodig.

**Nieuw open (verwerkt in de top-5):**
- **GebruikersgroepDetail + BlokkadeDetail** — nu ontgrendeld (betekenislaag is er). BlokkadeDetail-
  restpunten: `BlokkadeRead` verrijken met herkomst; eigenaar = vrij tekstveld; `objecthistorie._TYPES`
  uitbreiden met `gebruikersgroep` + `blokkade`.
- **ADR-036 "begin grof"-invoerroute** — frontend-formulier om een grof feit los vast te leggen
  (backend bestaat al). Zonder dit vuurt "detaillering ontbreekt" alleen op seed-data.
- **Verantwoordelijkheid-/roltoewijzing-partij-picker** — eerst de **domeinvraag** (welke aarden mogen een
  beheerrol dragen?), dán de scoping. Bewust niet blind versmald.

**Klein / parked toegevoegd:** RelatieKenmerk-dimensie-velduitleg (content klaar in `velduitleg.js`;
wacht op een invoerveld — nu sectie-gedreven).

**Nog open (ongewijzigd):** Impact-verkenner render-herbouw (top-5, echte cytoscape-render); ADR-035
Slice 3 (configureerbare score-drempel); ADR-029 Fase 5; ADR-023 Fase F-rest; OP-30. **Test-hygiëne:**
~30–33 Cytoscape-mock-consoleruis in `LandschapskaartView.test.js` (geen falende test) — bij render-herbouw.

Tests: backend **914/0** (2 skipped) · frontend **763**. Migratie-head **0050**.
ADR-register: **ADR-036** + **ADR-036a** opgenomen.

---

### Stand V029 (sessie-afsluiting LI060 + ADR-028, 2026-07-02)

Build **V028 → V029**. Componenttype-catalogus uitgebreid (top-5 #1 geland) én
**componentclassificatie (ADR-028) end-to-end** — rol + BIV door data/API/beheer/formulier/
detail/lijst/kaart/signalering.

**Geland:**
- **LI060 (`7c36b33`):** componenttype-catalogus **8 typen** — `applicatieserver`→`server_compute`,
  `middleware`→`integratievoorziening` (nu system_software/technology), nieuw `landelijke_voorziening`;
  drie extra beoordeelbaar (elk 1 tenant-startvraag). Geen migratie (seed = single source; reseed).
- **ADR-028 slice 1 (0048, `d61bddf`):** schema-fundament — 2 platform-catalogi (`componentrol_optie`,
  `biv_schaal_optie`) + 4 component-kolommen (rol NOT NULL default `interne_applicatie`; 3× BIV nullable)
  + RBAC (2 `PlatformEntiteit`) + audit. Engine-borging dubbel.
- **ADR-028 slice 2 (`939dbf2`):** componentformulier + detail (rol + BIV) + `RolConfigBeheer`/
  `BivConfigBeheer` + additief `/componenten/opties` (rol-opties + ordinale BIV-niveaus).
- **ADR-028 slice 3 (`131b674`):** rol/BIV-filter in lijst (server-side, drempel op `volgorde`) + kaart
  (client-side, filter-exemptie context-nodes) + gestippelde rand voor `externe_dataprovider`.
- **ADR-028 slice 4 (`b351b59`):** kritiek signaal "BIV-classificatie onvolledig" (≥1 BIV-veld leeg) —
  signalering nu **11 signaaltypen** (6 kritiek / 5 aandacht). ADR-035 bijgewerkt.

**ADR-036 (nieuw — functioneel besloten, bouw uitgesteld):** organisatiegebruik van applicaties —
grof "organisatie gebruikt applicatie"-feit + de gebruikersgroep als fijne verfijning (identiteit =
afdeling + organisatie) + read-only signaal "gebruik bekend, detaillering ontbreekt". Schema-rakend,
meerdere gate-slices; **design-checkpoint first** (open bouwknopen in `docs/adr/ADR-036`).

**Detailpagina's (gebruikersgroep + blokkade) — grounding gedaan, geparkeerd tot ADR-036 beslist**
(de groep-pagina hangt aan de nieuwe betekenislaag). BlokkadeDetail-restpunten: detail-read
(`BlokkadeRead`) verrijken met **herkomst** (checklist-item `vraag_code`/`vraag`/score — zit nu alleen
in het lijst-/overzicht-item); **eigenaar = vrij tekstveld** (bestaat + bewerkbaar; géén structurele/
roltoewijzing-afgeleide verantwoordelijke — dat is geparkeerd); **objecthistorie-route-allowlist
(`objecthistorie._TYPES`) uitbreiden** met `gebruikersgroep` + `blokkade` voor het 'i'-paneel
(audit-data bestaat al; alleen de route-allowlist + `haal_op`-resolutie ontbreekt).

**Nog open (ongewijzigd):** Impact-verkenner render-herbouw (top-5, echte cytoscape-render); ADR-035
Slice 3 (configureerbare score-drempel); ADR-029 Fase 5; ADR-023 Fase F-rest; OP-30. **Test-hygiëne:**
~30 Cytoscape-mock-consoleruis in `LandschapskaartView.test.js` (geen falende test) — bij render-herbouw.

Tests: backend **898/0** (2 skipped) · frontend **742**. Migratie-head **0048**.

---

### Stand V028 (sessie-afsluiting LI059, 2026-07-02)

Build **V027 → V028**. Component-focus-herfundering **volledig afgerond** — `component` is de enige
bron in data/API/RBAC/audit. (Slice 3/4/5 uit de V027-backlog zijn hiermee geland.)

**Geland:**
- **LI059 Slice 3 (0047, `03360ea`):** `applicatie`-subtabel gedropt; `applicatie_service` als dunne
  facade over `component`; dual-write weg; byte-compat behouden; dubbele engine-borging + verse reseed.
- **LI059 Slice 4 (`6fa655e`):** frontend-cutover — één `ComponentFormulier` (3 transitie-velden voor
  élk type) + één rijk `ComponentDetail` (tab-IA, conditioneel); `ApplicatieFormulier`/`ApplicatieDetail`
  geretireerd; `/applicaties*` → redirects. Geen functie verloren.
- **LI059 FacadeOpruiming (`1c40814`):** volledige purge — `routes/applicatie.py`/`schemas/applicatie.py`/
  `applicatie_service.py` + `api.applicaties` weg; `Entiteit.APPLICATIE`/audit-allowlist/objecthistorie-tak
  weg (RBAC-matrix 23→22 = 352); validators → `schemas/_validators.py`; creatie-kern → `component_service`.
- **LI059 Slice 5:** ADR-021/022 slotsecties "Eindstaat" + ADR-register + `likara-domeinmodel §1` bijgetrokken.

**Nog open (niet-LI059, ongewijzigd):** componenttype-catalogus uitbreiden (top-5 #1); Impact-verkenner
render-herbouw (top-5 #2; edges-onzichtbaar-bug zit in de echte cytoscape-render); ADR-035 Slice 3
(configureerbare score-drempel); ADR-029 Fase 5 (`gereedmeld_recht`); ADR-023 Fase F-rest; OP-30 (env-
auth-test, omgevingsgebonden). **Los test-hygiëne-punt:** ~29 Cytoscape-mock-console­ruis in
`LandschapskaartView.test.js` (geen falende test) — bij de render-herbouw meenemen.

Tests: backend **865/0** (2 skipped) · frontend **717**. Migratie-head **0047**.

---

### Stand V027 (sessie-afsluiting LI057+LI058, 2026-07-01)

Build **V026 → V027**. Component-focus-herfundering **Slice 1 + Slice 2** geland (+ OP-30 afgerond).

**Geland:**
- **LI057 (Slice 1, 0045):** `migratiepad/complexiteit/prioriteit` component-breed (basis-`component`,
  NOT NULL + defaults); enum `tijdelijk_gedeeld → gedeeld`. Expand met dual-write naar de behouden
  applicatie-subtabel. Dubbele engine-borging.
- **LI058 (Slice 2, 0046):** scoren per type via `checklist_dragend`; `database` beoordeeld + 6-vragen
  startset; **profiel-backfill** bij False→True (platform-toggle → per-tenant RLS-scoped backfill,
  idempotent; True→False inert). Engine al generiek.
- **OP-30:** env-afhankelijke auth-cookie-test deterministisch (afgerond, `b99b901`).

**Backlog (component-focus, volgende sessies):**
- **Slice 3 (contract):** applicatie-subtabel droppen + `applicatie_service`/routes/schemas opheffen.
- **Slice 4 (frontend):** één `ComponentFormulier`; `ApplicatieFormulier`/`ApplicatieDetail` retireren.
- **Slice 5:** tests + TST + ADR-021/022 afronding.
- **Componenttype-catalogus uitbreiden** (integratie/koppel, landelijke voorziening, server/compute;
  consolidatie applicatieserver+middleware); daarna fileshare → SaaS beoordeelbaar maken.
- **Impact-verkenner render-herbouw** (deterministische render-eigenaar; edges-onzichtbaar-bug zit in
  de echte cytoscape-render, niet in de logica).

Tests: backend **944/0** (2 skipped) · frontend **745**. Migratie-head **0046**.

---

### Stand V026 (sessie-afsluiting LI051, 2026-06-30)

Build **V025 → V026**. Deze sessie ging volledig over de **code-rebrand
`cd_`/`complidata`/`CompliData`/`CompliMan` → `lk`/`likara`/`LIKARA`** (LI038–LI050).
De oorspronkelijke V025-prioriteiten zijn NIET opgepakt en blijven de top-5 (zie
NEXT_SESSION).

**Geland in LI038–LI050:**
- LI038–040: skills/docs (senior-architect ADR-conventie + V691-legacy-banner, db-naam, naamhistorie)
- LI042: bugfix `sluit_acties.py` (scande niet-bestaande `skills/complidata`)
- S1+S8 (fd82626): cosmetische code-namen + role-prefix
- S2 (27066a1): CSS-tokens `--cd-` → `--lk-` (frontend-breed incl. module-frontend)
- S3 (84e2ce7): cookies `lk_session`/`lk_refresh`
- S4 (e9e4835): env-flags `LIKARA_TEST_MODE`/`LIKARA_FIXTURE_SET`
- S5 (4e0f6a0): localStorage `lk-sidebar-ingeklapt` + backup-basisnaam `likara_*.sql`
- LI049 (28e421c): migratie-revisie-id ≤32 (deploy-blocker) + handhavingstest
- S6 (d67e968): infra `lk_rabbit`, vhost `lk-{slug}`, MinIO `likara_admin`, paden `~/likara/`
- S7 (f7ecd7c): DB-triggerfunctie `lk_audit_append_only` (forward-migratie 0044, append-only LIVE geborgd)

**Resterend uit de rebrand (geen code meer):**
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL;
  lokale map `~/complidata/` opruimen (stack draait al op `~/likara/`). Berts GitHub-actie.
- **Deploy-side (andere omgevingen)** — `.env`/secrets bijwerken: `RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-namen `lk_session`/`lk_refresh`,
  env `LIKARA_TEST_MODE`/`LIKARA_FIXTURE_SET`; re-provision vereist.
- **Procesgat secrets-backup** — `~/complidata/secrets/.env` heeft nooit bestaan;
  CLAUDE.md documenteert nu `~/likara/secrets/` als backuplocatie die feitelijk niet
  gevuld werd → verzoenen.
- **env-test-robuustheid** — zie OP-30 (`test_callback_succes_zet_lk_session_cookie`
  laat `cookie_secure` van de omgeving afhangen; expliciet zetten).
- **Optioneel** — vangrail-greps uitbreiden met live `cd_`/`complidata` (scoped, excl. historie).

### Stand V025 (sessie-afsluiting LI024, 2026-06-29)

Build **V024 → V025**. LI024 = volledige prioriteitenlijst afgewerkt +
uitgebreide UX-verbeteringen Landschapskaart.

**Geland in LI024:**
- Skills aangemaakt: likara-werkprotocol, likara-domeinmodel, likara-ux (33ded4f)
- ADR-035 Slice 1: 2 kritieke signalen + Signalering-scherm 2 tabs (1903f14)
- ADR-035 Slice 2: 5 aandacht-signalen + centraal overzicht (0247506)
- ADR-025 "Bekijk op kaart"-knop + beginscherm-fix (f87182e)
- ADR-026 ArchiMate typering: al gerealiseerd V013 — geen bouw nodig
- ADR-030 Contract coverage per-band: migratie 0043 + service + UI (0953857)
- Klaarverklaring-blok ComponentDetail: al gerealiseerd — geen bouw nodig
- Interactieve legenda: dim/spotlight + draggable (533ec94 + 537941f)
- Zoekbalk bug fix + resultaten in kaart-modus LI028/029 (740aae3 / commit LI029)
- fcose layout-optimalisatie LI030 (537941f)
- Dubbele nodes fix LI031 (fe9873c)
- Positie-stabiele re-render LI032 (013d240)
- Detail-popup draggable + overlap-fix LI033/034 (commit LI033)
- LIKARA tagline fix LI035 (commit LI035)
- Eigenaar-ring fix LI036 (f8e735e)
- Ring-reactivity regressietest LI037 (144ecd9)

**Nieuw open (prioriteitsvolgorde voor LI025):**
1. ADR-035 Slice 3 — Registratie onvolledig (configureerbare drempelwaarde)
2. Modus ego→impact ontkoppelen van set-grootte (ADR-033-revisie)
3. GebruikersgroepDetail standalone pagina
4. BlokkadeDetail standalone pagina
5. Zoekbalk contextlabel "Component toevoegen aan beeld"

**Structureel onmogelijk / uitgesteld:**
- blokkade_zonder_eigenaar — schema-/semantiekherziening vereist
- badges GebruikersgroepDetail/BlokkadeDetail — wacht op detail-pagina's

### Stand V024 (sessie-afsluiting LI023, 2026-06-29)

Build **V023 → V024**. LI023 = Landschapskaart Fase B compleet + UX-fixes +
ADR-besluiten + PRODUCTVISIE.md.

**Geland in LI023:**
- Werkprotocol herbevestigd + geborgd in likara-werkprotocol skill (a367d3d)
- Slice 2b: 4-ingangen-beginscherm + chips (b5a6e33, cab0988)
- Slice 2b UX-fixes: z-index blokkade (94aa12e), actieknop bovenaan (ef68c40),
  zoekterm reset na aanvinken (a4979fa)
- Slice 5: detail-paneel set-acties — buren erbij + context-componenten (0b018bd)
- Slice 6: cytoscape-dagre dependency verwijderd (776ab38)
- Scope-balk fix: filtert org/gg-nodes in subgraaf-modus (097d1e9)
- Generieke re-layout watcher op getekendeNodes-compositie (1019d8f)
- PRODUCTVISIE.md toegevoegd aan projectroot (3fc3414)
- ADR-025/026 nadere besluiten + ADR-030 besloten + ADR-035 Signalering (ac4afb7)
- root-OPVOLGPUNTEN.md verwijderd — docs/OPVOLGPUNTEN.md is enige bron (0e16999)

**Nieuw besloten, nog te bouwen (prioriteitsvolgorde):**
1. ADR-035 Signalering registratiegaten
2. ADR-025 "Bekijk op kaart"-knop (praatplaat ego-view)
3. ADR-026 ArchiMate typering verplicht in componenttype-formulier
4. ADR-030 Contract coverage per-band
5. Klaarverklaring-blok op ComponentDetail (triviale gap, ADR-027 compleet)
6. Interactieve legenda als type-filter

**Landschapskaart uitgesteld na live testing:**
- Scope-balk gedrag in subgraaf-modus (bewust uitgesteld)
- Impact-modus semantiek op een set (bewust uitgesteld)
- Swimlane implementatie (ADR-034, geparkeerd)
- Saved views als permanente hoofdingang (Fase D)
- "Zoek-erop-dan-toon-het" principe

**Nieuw strategisch thema (parked):**
- Export/import/rapportage — scope en fasering apart te bepalen

### Stand V023 (sessie-afsluiting LI022, 2026-06-27)

Build **V022 → V023**. LI022 = Landschapskaart Fase B (set-gestuurd) + hygiëne/rename.

**Geland/afgerond in LI022:**
- **Fase B slice 0+1 — set-gestuurd laadpad** (`10bb35e`): de kaart opent leeg; niet-lege set →
  `POST /landschapskaart/subgraaf`; bewuste "Toon hele landschap" met "X van N"-teller; "Begin opnieuw"
  = harde reset. `api.landschapskaart.subgraaf` bedraad. **AFGEROND.**
- **Fase B slice 2a — context-routes naar componenten** (`509e9ca`): `GET /contracten/{id}/componenten`
  (incl. kale componenten; engine-ontkoppeld) + `GET /gebruikersgroepen/contexten(/componenten)`
  (distinct (org, afdeling)-picker + nullable-veilige context→componenten). **AFGEROND.**
- **Stale live-DB-tests herijkt op de verrijkte seed** (`d6cd59f`); **skill-laag hernoemd
  complidata→likara + nieuwe `likara-werkprotocol`** (`8b8a8b2`); **Laag-2 identifier-rename geborgd**
  (`6043094`); **generators-skill-paden meegerenamed** (deze afsluiting — gen_build/gen_sessiestart
  verwezen nog naar `.claude/skills/complidata/`).
- **Oude slice-3 (Typen server-side) + slice-4 (Bladeren) worden door slice 2b geabsorbeerd** — niet
  apart gebouwd (zie NEXT_SESSION voor het slice-2b-ontwerp + de herziene slice-planning).

**Nieuw klein/optioneel vervolgpunt:**
- `GET /gebruikersgroepen/contexten` is **bewust ongepagineerd** (begrensde distinct-afgeleide lijst, met
  zoek + telling). Keyset alleen nodig als een tenant extreem veel distinct (organisatie, afdeling)-
  contexten krijgt → dan een kleine eigen slice (keyset over een 2-nullable-koloms-distinct).

### Nieuwe bouwpunten besloten LI023

**ADR-025 (Praatplaat) — BESLOTEN, bouw gepland:**
"Bekijk op kaart"-knop op alle componentdetailpagina's → vooringestelde
ego-view op de Landschapskaart. Koppelingenkaart visuele weergave vervalt.
Read-API per component + frontend-integratie.

**ADR-026 (ArchiMate typering beheerbaar) — BESLOTEN, bouw gepland:**
Drie verplichte typeringsvelden in componenttype-formulier. Gesloten lijsten
(code-constanten). Seed compliant maken bij de bouw-slice.

**ADR-030 (Contract coverage) — BESLOTEN, bouw gepland:**
Per-band dekking naast contract-brede dekking (Optie B).

**ADR-035 (Signalering registratiegaten) — BESLOTEN, bouw gepland:**
Zie ADR-035 (hernummerd; ADR-031 was reeds vergeven). Coherent Signalering-scherm
(absorbeert Plaatsingssignalen). 10 signaaltypen, 2 niveaus, badges op entiteiten
+ centraal overzicht.

**Klaarverklaring op ComponentDetail — BESLOTEN, bouw gepland:**
MigratiegereedheidSectie-blok + knop plaatsen op ComponentDetail.
ADR-027 is compleet; triviale implementatiegap.

**Interactieve legenda als type-filter — BESLOTEN, bouw gepland:**
Klik op type in legenda → filtert graaf op dat type.

**Export/import/rapportage — NIEUW STRATEGISCH THEMA (parked):**
Breder thema dan alleen praatplaat-export. Scope en fasering apart te bepalen.

### Subgraaf-semantiek: filter/scope/impact/swimlane op een opgebouwde set (eigen ontwerpslice)

Fase B (LI022) maakt de kaart set-gestuurd. De rijke verkenmechaniek
(impact-ringen, scope-balk, swimlane, ego/impact-modus) is gedefinieerd óver de
volledige graaf en is in Fase B verhuisd naar de "hele landschap"-modus (waar de
volledige graaf nog bestaat). Wat deze mechaniek betekent op een **opgebouwde set
(subgraaf = set + 1-hop)** is bewust nog niet ontworpen — een set ís al focus, dus
mogelijk is een deel ervan daar overbodig of anders gedefinieerd.

Te beslissen in een eigen ontwerpslice (rond het interactiemodel, Fase B slice 5):
welke van filter/scope/impact/swimlane zinvol zijn op een subgraaf, en hoe ze zich
daar gedragen. Pas dán de set-tests inhoudelijk herijken (nu dekken die alleen de
bedrading). Geen workaround vooruit; structureel definiëren wanneer de beslissing valt.

### Stand V022 (sessie-afsluiting LI021, 2026-06-25)

Build **V022**. LI021 = test-hygiëne + seed-verrijking + Landschapskaart-vertrekpunt **fase A** (achterkant-kern).

**Geland in LI021:**
- **Test-hygiëne** (`0c4371b`) — twee live-DB-tests zelf-opruimend via `finally`
  (`test_component_contract_op_niet_applicatie_component`, `test_score_write_driver_plus_afgeleide_delen_correlatie`);
  cleanup draait ook bij falen → geen residu-lek meer (vervuilings-cirkel gebroken).
- **Seed-verrijking** (`ae905c1`, data-only/idempotent in `_seed_bvowb_scenario`): infrastructuur
  (technology-laag: Shared DB-server/fileshare/extern SaaS-platform) + draait-op-relaties;
  component-samenstelling (Burgerzaken-suite → Aangiften/Reisdocumenten/Verkiezingen); bewuste
  scope-gaten (Archiefbeheer zonder eigenaar; Klantportaal uitsluitend organisatieloos gebruikt).
- **Kaart-vertrekpunt fase A** (`fec08d5`, additief/read-only): POST `/landschapskaart/subgraaf`
  (set-scoped S+1-hop; `component_ids=None` = volledige graaf, back-compat); leverancier-filter op
  `/componenten` (afgeleide EXISTS, beide paden); eigenaar-edge "is eigendom van" (context, **niet**
  in `IMPACT_RINGEN`).
- **Geparkeerd "scopebalk-tekent-organisaties"-spoor is AFGEDEKT** door de eigenaar-edge (zelfde
  "is eigendom van"-projectie) — geen apart vervolgpunt meer nodig.

**Vervolg LI022 (in deze volgorde, leunt op elkaar):**
1. **Reset + seed-herijking** — de 8 pre-existing live-DB-failures groen krijgen in CC's omgeving:
   `docker compose down -v` → reseed (**handmatige dev-seed!** — `docker compose exec <api> python dev_seed_testdata.py`)
   + de stale tests herijken op `_seed_bvowb_scenario` (ze verwachten dode-seed-rijen — `GeoWorks
   Licentieovereenkomst`/`Oracle FIN-DB`/3 `client_software`-vragen — die de verrijkte seed niet maakt).
2. **Kaart-vertrekpunt fase B** — leeg openen + zoek-vertrekpunt via `/componenten`
   (naam/type/laag/hosting/eigenaar/leverancier) → set-opbouw → POST subgraaf, met accumulerende
   sub-graaf-cache. **Besloten keuzes:** selectie = alléén component-ids (org/leverancier = criterium +
   context); **cache weggooien** bij "begin opnieuw"; **1-hop norm, dieper alleen via doorklikken**;
   endpoint = POST.
3. **Fase C** — defaults omdraaien (leeg openen consistent: scopebalk niets-aan→alles + startscherm
   geen-views→hele model wég) + "zoek-erop-dan-toon-het" (auto-ring-activering op zoek, handmatig wint).
4. **Fase D** — opgeslagen views permanent náást het zoekveld (hoofdingang).

**8 pre-existing live-DB-failures — seed-drift (NIET als opgelost markeren):**
architectuur_f2, audit_capture, 4× component_fase_b_cd052, lifecycle_pertype, vraagbeheer. De
`finally`-hygiëne (`0c4371b`) brak de residu-cirkel, maar de 8 blijven rood door **seed-drift** (tests
asserteren op rijen die `_seed_bvowb_scenario` niet maakt). Opgelost door vervolgstap 1. Zie
`docs/TST-V022-Validatierapport.md`.

**Overige open punten (ongewijzigd):** ADR-034 open subknopen; interactieve legenda als type-filter;
ADR-030 contract-dekking; ADR-029 Fase 5; klaarverklaring-blok op ComponentDetail; signalerings-ADR;
dode-code-opschoning (frontend/backend); cytoscape-dagre opruimen.

---

### Stand V021 (sessie-afsluiting LI020, 2026-06-25)

Build **V021**. LI020 = ADR-033 (volledig), gebruikersbeheer-acties (ADR-029 Fase 2b),
en de Landschapskaart-reeks.

**Geland in LI020:**
- **ADR-033 (volledig)** — adaptieve Landschapskaart + Impact-verkenner (graph op canvas),
  samenstelling-edge, opgeslagen & deelbare views (entiteit + rechten + API + voorkant + startscherm).
- **Gebruikersbeheer-acties (ADR-029 Fase 2b, achter + voorkant)** — wachtwoord opnieuw instellen,
  rol wijzigen, in-/uitschakelen (sessie-afkap), gegevens corrigeren; self-lockout-guards; expliciete audit; beheer-paneel.
- **Landschapskaart-reeks** (frontend, engine onaangeroerd): selectie-highlight (enkelklik = incidente
  lijnen oranje; dubbelklik = dieper); organisatiestructuur-ring (persoon-met-rol → afdeling → organisatie,
  context, buiten `IMPACT_RINGEN`); toestand-geschiedenis (terug/vooruit) + hang-fix + auto-centreren;
  vorm-per-type + uitklapbare legenda; organisatie-scopebalk slice 1 (backend read-projectie) + slice 2 (balk).
- **ADR-034 (swimlane-herwrite)** — staat als **Voorstel** (nog niet gebouwd).

**Eerste blok LI021 (in volgorde, leunt op elkaar):**
1. **Test-hygiëne-fix** — twee lekkende live-DB-tests zelf-opruimend maken (`finally`):
   `test_component_contract_op_niet_applicatie_component` (test_component_fase_b_cd052) en
   `test_score_write_driver_plus_afgeleide_delen_correlatie` (test_audit_capture_live). Breekt de
   vervuilings-cirkel → maakt de 8 falers vermoedelijk groen.
2. **Schone reset** — `docker compose down -v` → reseed → 32 artefacten (`CD052-db-*`/`AUDIT-SRV-*`) weg.
3. **Gerichte seed-verrijking** (geen "meer data" — drie ontbrekende variaties):
   - **infrastructuur** (technology-laag) onder componenten → barrel-vorm + "draait-op"/assignment-impactrelatie zichtbaar;
   - **component-samenstelling** (component↔component, onderdeel-van) → samenstelling-ring + "onderdeel-van"-impactrelatie zichtbaar;
   - **bewuste scope-gaten** — ≥1 component zonder eigenaar + ≥1 app uitsluitend door de organisatieloze "Burgers"-groep geserved → scopebalk-gap-tellers aantoonbaar.

**8 pre-existing live-DB-failures — oorzaak nu bekend (NIET als opgelost markeren):**
Test-residu van niet-zelf-opruimende live-DB-tests (inline cleanup i.p.v. `finally`) → 32 wees-componenten
(`CD052-db-*`/`AUDIT-SRV-*`) vervuilen lijst-/sort-asserts van ándere tests → vicieuze cirkel (verklaart
"reseed lost het op"). Structureel opgelost door LI021-startpunt 1 + reseed. Zie `docs/TST-V021-Validatierapport.md`.

**Overige open punten (ongewijzigd):** ADR-034 open subknopen; interactieve legenda als type-filter
(besproken vervolg); ADR-030 contract-dekking; ADR-029 Fase 5; klaarverklaring-blok op ComponentDetail;
signalerings-ADR; dode-code-opschoning (frontend/backend); cytoscape-dagre opruimen.

**Parkeer-items (ongemoeid):** gebruikersbeheer-vervolg (self-service / MFA / AVG-anonimisering /
inactieve accounts); contract-leverancier verbreding; soort-catalogus; per-tenant catalogus-zichtbaarheid;
tenant-eigen partijsoort; friendly STATE_ONGELDIG; child-section-staleness.

---

### Stand V020 (sessie-afsluiting LI019, 2026-06-24)

Build **V020**. LI019 = Landschapskaart-filters/UI, auditlog-UI, leverancier via contract-keten,
radiaal-layout + swimlane geparkeerd.

**Nieuw in LI019:**
- **ADR-034 Swimlane herwrite** — pure HTML/CSS div-lanes + SVG-overlay voor edges (NIET Cytoscape
  compound-nodes). Lane-drag, edges tussen lanes, nodes aanklikbaar.
- **ADR-033 Impact-verkenner bouwen** — besloten, klaar voor bouw (zie `ADR-033_Impact_verkenner.md`).
- **Codebase cleanup** (inventarisatie klaar) — frontend 11 items + backend 28 items (zie
  LI019-cleanup-inventarisatie rapport).
- **8 pre-existing live-test failures skip-robuust maken** — seed-afhankelijk.
- **dagre dependency opruimen** — ongebruikt na de radiaal-overstap.
- **Per-tenant catalog optie-zichtbaarheid** (ADR-026 edge case) — geparkeerd.
- **Tenant-eigen partijsoort** — geparkeerd.
- **Contract-leverancier verbreding** — `aard=externe_partij`-constraint verbreden.
- **Signalerings-ADR registratiegaten** — object zonder rol, lege eigenaar-organisatie, contract
  zonder leverancier, lege eigenaar-blokkadelijst. **→ opgenomen in ADR-035 (Signalering registratiegaten), besloten LI023.**
- **Browser-verificatie radiaal auto-centrering na dubbelklik** (commit 0cf8559).

### Stand V018 (sessie-afsluiting DC017, 2026-06-22)

Build **V018**. DC017 = LIKARA-rebranding (Laag 1) + canoniek BvoWB-seed + Keycloak login-theme +
dev-gebruikers + kaart-edge-groepering/master-detail (ADR-023a Fase 3+4).

**Nieuw (DC017):**
1. **LIKARA Laag 2 rename** — technische identifiers: realm-ID `complidata` → `likara`,
   container-namen `cd-*`, DB-rol `lk_app`, image `complidata-api:local`, ENV `KEYCLOAK_REALM`,
   clientId `complidata-api`/`complidata-ui`. Bewuste keuze: **eigen sprint DC018** (raakt compose,
   .env, init-db, conftest, RLS-rol → reseed vereist).
2. **Reseed-verificatie (`down -v`)** verplicht na de Laag 2 rename.
3. **Dode seed-functies opruimen** in `dev_seed_testdata.py` (`_seed_applicatie`,
   `seed_landschapskaart_demo`, `_seed_koppelingen` e.a. — ongebruikt sinds `_seed_bvowb_scenario`).
4. **Child-secties stale bij detail→detail-hop** — child-secties in ComponentDetail/ApplicatieDetail
   laden zelf in `onMounted` zonder `:key`; bij een hop binnen hetzelfde type kunnen ze stale zijn.
5. **soort-catalogus uitbreiden** — "Dienstenprovider" en "Samenwerkende gemeente" bestaan niet als
   partijsoort → BvoWB + gemeenten krijgen nu `soort=None` in de seed; catalogus kan uitgebreid worden.
6. **STATE_ONGELDIG-foutmelding** — ruwe JSON tonen → vriendelijke "sessie verlopen"-pagina.
7. **Stale root `OPVOLGPUNTEN.md`** (staat nog op V012) — consolideren met `docs/OPVOLGPUNTEN.md` of verwijderen.

**Herbevestigd (blijft open):** ADR-029 Fase 5 (`gereedmeld_recht`), ADR-023 Fase F-rest (E-8 +
RBAC/audit), landschapskaart server-side ego-subgraaf, objecthistorie-diff id→naam-resolutie,
OP-30 `test_auth_pkce` Secure-cookie env-test (omgevingsgebonden).

### Stand V017 (sessie-afsluiting DC016, 2026-06-22)

Build **V017**, migratie head **`0040`**. Tests: **859** backend + **534** frontend groen +
`test:css-build` groen. Deze sessie: UI-standaardisatie (knop/tab/interactie-borging),
api-client-filterconventie, Landschapskaart popups/fullscreen, ADR-023a meervoudige
flow-koppelingen Fase 1+2.

**Nieuwe/geactualiseerde opvolgpunten (DC016)**:
- **ADR-023a Fase 3** (read/contract, geen migratie) — kaart-edge-groepering: meerdere flows per
  `(bron,doel)` → één lijn + **telling vanaf 2**; popup-fetch op het **ongeordende paar**, gegroepeerd
  naar richting (uitgaand bij bron / inkomend bij doel).
- **ADR-023a Fase 4** (frontend) — naam-veld (verplicht) + overrulebare **KOPPELING_DUBBEL**-
  waarschuwingsdialoog; `KoppelingSectie` naam-kolom (sorteerbaar); kaart-telling vanaf 2; en de
  popup ombouwen naar **universeel master-detail** (links sorteerbare interface-lijst op naam/richting,
  pijl-buiten-groen=uitgaand / pijl-binnen-rood=inkomend met **pijlrichting als hoofdsignaal**; rechts
  detail; eerste regel geselecteerd; ook bij n=1). Vervangt de enkelvoudige popup uit `8de3451`.
- **NIEUW SEED-TRAJECT (groot)** — volledige testdataset opnieuw opzetten zodat hij het **hele
  LIKARA-landschap** representeert en alle functionaliteit raakt (besloten DC016). Moet **flow-namen**
  + **meervoudige benoemde koppelingen** bevatten. Volgt ná de ADR-023a-koppeling-keten.
- **Reseed gebroken op flow-namen** — `dev_seed_testdata._seed_koppelingen` maakt flows **zonder naam**
  → faalt onder de naam-eis (ADR-023a Fase 2). Wordt opgelost in het nieuwe seed-traject; tot dan is
  een reseed van de koppelingen gebroken (testdata-kwestie, géén migratievraagstuk).
- **`test:css-build` nog niet in CI** — los script; een CI-stap of pre-push-hook is de logische
  vervolgstap (aparte slice).
- **ADR-030 contract-dekking per contract↔component-band** (voorstel, `3e28481`) — dekking als
  per-band-kenmerk op de association i.p.v. uitsluitend contract-breed. Centrale open subknoop:
  contract-brede dekking **behouden NAAST** per-band of **vervangen**. Op te pakken ná de
  koppeling-keten (n≥2: de koppeling-uitbreiding als blauwdruk). Read-only verkenning is gedaan.

### Stand V016 (sessie-afsluiting DC015, 2026-06-20)

Build **V016**, migratie head **`0038`**. Tests: **856** backend + **500** frontend groen
(1 pre-existing env-auth-test, OP-30). Deze sessie: ADR-029 (gebruikersbeheer als primaire ingang)
grotendeels gerealiseerd + objecthistorie ('i'-knop).

**AF deze sessie (DC015)**:
- Drie kleine opvolgpunten (DC014): dode `<dl>`-rijen op ApplicatieDetail + ComponentDetail
  opgeruimd; `MigratiegereedheidSectie` ook op ComponentDetail; CLAUDE.md interactie-secties
  geconsolideerd.
- **ADR-029 herschreven** (gebruikersbeheer als primaire ingang; LIKARA als bron van waarheid).
- **ADR-029 Fase 2** — backend gebruikersaanmaak: `gebruiker_persoon`-koppeltabel (migratie 0037),
  Keycloak Admin API-provisioning via dedicated service-account `likara-user-provisioning`
  (least-privilege manage-users/view-users), server-gegenereerd eenmalig wachtwoord,
  orphan-cleanup. Live-geverifieerd na realm-herimport.
- **ADR-029 Fase 4** — gebruikersbeheer-scherm (beheerder-only nav + lijst + aanmaak-dialog +
  eenmalig-wachtwoord-weergave).
- **ADR-029 Fase 3b** — sub-stempeling: `verklaard_door_sub` (klaarverklaring, migratie 0038) +
  plateau `bevestigd_door` {sub,email}; gedeelde `actor_resolutie`-helper (sub→naam, e-mail-fallback);
  read-side `verklaard_door_naam`/`bevestigd_door_naam`. ADR-027 wijzigingshistorie bijgewerkt.
- **ADR-029 Fase 3a** — audit-view + `actor_naam`-batchverrijking + actie-filter + naam-filter
  (naam→sub).
- **Objecthistorie** — `GET /objecthistorie/{type}/{id}` (toegang-volgt-object, geen AUDITLOG-gate)
  + herbruikbaar `ObjectHistoriePaneel` ('i'-knop) op 8 detailschermen, per-record diff met
  NL-veldlabels, "Meer laden".
- **Dev-seed-fix**: `dev_seed_testdata.py` crashte bij reseed op de met migratie 0034 verwijderde
  `eigenaar_naam`/`leverancier`-kwargs (pre-existing DC015-vondst).

**Volgende prioriteiten (DC015 → DC016)**:
1. **ADR-029 Fase 5** — `gereedmeld_recht` (per-type persoon × componenttype) + per-type check in
   de klaarverklaring-service. **Laatste open ADR-029-fase.**
2. **ADR-023 Fase F-rest** — checklist-consistentiecheck technische plaatsing (E-8) + resterende
   RBAC/audit nieuwe entiteiten.
3. **Landschapskaart server-side ego-subgraaf** (`?center=<id>&diepte=1|2`).
4. **LIKARA codebase-rename** (geparkeerd, DC013).

**Nieuwe opvolgpunten (DC015)**:
- **Dode backend-proxy-properties** `Applicatie.eigenaar_naam` / `.leverancier` (`models.py:382/386`)
  lezen een sinds migratie 0034 niet-bestaande kolom — inert (niet in Read-schema's), opruimbaar in
  een aparte backend-taak.
- **Naam-filter audit-view** eventueel als ZoekSelect-op-personen (nu vrije-tekst; bewuste
  search-semantiek — alleen als de praktijk een pick verkiest).
- **id→naam-resolutie in objecthistorie-diff** (`*_id`-velden tonen nu de gelogde id-waarde;
  per-veld id→naam zou een lookup per type vergen).

### Stand V014 (sessie-afsluiting DC013, 2026-06-19)

Build **V014**, migratie head **`0034`**.
Tests: **810** backend + **440** frontend groen (52 files).

**AF deze sessie (DC013)**:
- complidata-domeinmodel skill aangemaakt (CC + claude.ai)
- ADR-024 volledig geland: contract-leverancier verbreed
  (organisatie/afdeling/externe_partij; persoon geblokkeerd);
  roltoewijzing toevoegbaar vanuit partij-detail;
  ADR-024-document bijgewerkt naar werkelijke stand;
  functietitel (persoon-only, migratie 0033);
  eigenaar_naam/leverancier vrije tekst verwijderd (migratie 0034);
  9 beheerrollen (Account Manager + Service Delivery Manager)
- ADR-025 volledig geland (Landschapskaart v4, Cytoscape.js):
  Ego/Impact/Geheel model; zoeken + 4 filters; actieve set;
  node-detail + "Open applicatie →"; blokkade-icoon;
  lifecycle-kleuren; koppelingsdetails (protocol/richting) op edges;
  migratieplaatsing (plateau/dispositie) in detail-paneel;
  diepte-toggle; Koppelingenkaart vervangen; ADR-025-document bijgewerkt
- ZoekSelect-standaard vastgelegd in complidata-frontend skill
- PartijFormulier organisatie-/afdelingskiezer naar ZoekSelect
- LIKARA productnaam besloten (Logische ICT Kaart Afhankelijkheden Relaties Analyse)
- ADR-028 voorstel geland (componentrol + BIV-classificatie, geparkeerd na ADR-027)
- complidata-domeinmodel/-frontend/-ux skills bijgewerkt (DC013-patronen)

**Volgende prioriteiten (DC013 → DC014)**:

1. **ADR-027 — Component-klaarverklaring. ✅ COMPLEET** (DC014): slice 1 model
   (`component_klaarverklaring`, migratie 0036, niet-scorend, herroepbaar, engine-gescheiden) →
   slice 2 UI (Migratiegereedheid-blok + klaar verklaren/heropenen met reden op ApplicatieDetail,
   commit 979a646) → slice 3 dashboard (tellingen `klaar_verklaard` + `klaar_met_afwijking` +
   lijstfilter `klaarverklaring=klaar`/`afwijking=1`, commit 6ffd7e6). Per-categorie + werkverdeling
   bewust vervallen. **Restpunten (nieuw, zie hieronder):** klaarverklaring-blok ook op ComponentDetail.

2. **ADR-029 — Gebruiker-partij-koppeling + per-type gereedmeld-autorisatie** (geparkeerd voorstel,
   fundament voor eerste implementatie). Brug Keycloak-login ↔ persoon-partij (ADR-024) + per-type
   gereedmeld-recht aan de persoon + apart beheerder-autorisatierecht (gescheiden van PARTIJ) +
   gescheiden verantwoordingsketen. Verfijnt het grove ADR-027-recht (per-persoon/per-type,
   preventief); ADR-027 hangt er niet op. Zie docs/adr/ADR-029_Gebruiker_partij_autorisatie_voorstel.md.

3. **ADR-023 Fase F**: checklist-consistentiecheck technische plaatsing (E-8, deferred),
   platform-beheer relatie-kenmerk-catalogus, RBAC/audit nieuwe entiteiten.

4. **Landschapskaart server-side ego-subgraaf** (aparte slice): `?center=<id>&diepte=1|2`
   voor een gereduceerde graaf i.p.v. de volledige tenant-graaf. Vereist nieuw endpoint-contract.

5. **ADR-025 overige roadmap**: vervangingsrelatie, export PNG/PDF, pad-inzicht (kortste route
   A→B), clustering op domein.

**Nieuwe opvolgpunten (DC014)**:
- **Klaarverklaring-blok ook op ComponentDetail** (niet-applicatie checklist-dragende
  componenten). Het model is component-generiek; alleen ApplicatieDetail heeft nu de
  Migratiegereedheid-UI. Triviale follow-up: het herbruikbare `MigratiegereedheidSectie`-blok
  + de knop op ComponentDetail plaatsen.
- **Dode `<dl>`-rijen op ApplicatieDetail Overzicht** opruimen: "Eigenaar (naam)" + "Leverancier"
  tonen sinds migratie 0034 (velden uit schema/form verwijderd) altijd "—".
- **CLAUDE.md interactie-secties consolideren**: deels overlappende blokken (Werkprotocol +
  "Werkwijze CC + claude.ai"); samenvoegen tot één gezaghebbende bron.

**Nog open uit eerdere sessies (doorgeschoven, ongewijzigd geldig)**:
- **Signalerings-ADR / registratiegaten ("bolletjes")** — (1) object zonder toegewezen rol;
  (2) lege eigenaar-organisatie/gebruikersgroep-organisatie (geparkeerd); (3) contract zonder
  leverancier (indicator + statusfilter + dashboard-ratio); (4) lege 'Eigenaar'-kolom blokkadelijst.
  Generalisatie-discipline n≥2; read-only, geen engine-poort.
  **→ opgenomen in ADR-035 (Signalering registratiegaten), besloten LI023.**
- **Architectuuroverzicht-sortering volgt codewaarde, niet NL-label** — geaccepteerd randgeval (B2/B6-a).
- Tenant-eigen partijsoort (geparkeerd); per-tenant zichtbaarheid catalogus-opties; OP-29 label-rename;
  `SUBTYPE_HEEFT_DATA` 422↔409-heroverweging.

---

### Stand V013 (sessie-afsluiting DC012, 2026-06-18) — ADR-024-vervolg + UX-doorlichting

Build **V013**, migratie head **`0032`**. Tests: **799** backend + **429** frontend groen
(1 pre-existing env-auth-test, OP-30). Deze sessie: rol-toewijzing (eigen tabel), volledige
UX-doorlichting gedicht, migratielaag-CRUD compleet, organisatie overal als verwijzing naar
het partijenregister.

**AF deze sessie (DC012)**: UX-doorlichting **volledig gedicht** (A1–A4, B1–B6); **rol-toewijzing**
(`roltoewijzing`, slice 2b — eigen tabel bij tegengestelde uniciteit); **migratielaag-CRUD compleet**
(plateau/werkpakket/deliverable/gap beheerbaar in de UI); **`complidata-ux`-skill geland**;
architectuuroverzicht server-side sorteerbaar; B6 organisatie-uit-partijenregister (gebruikersgroep +
applicatie/component).

*(De DC012→DC013-prioriteiten zijn afgehandeld of doorgeschoven naar het V014-blok hierboven —
ADR-024-document is bijgewerkt; signalerings-ADR + sorteer-randgeval staan nu onder "Nog open uit
eerdere sessies" bij V014; ADR-025 is geland.)*

### Stand V008 (sessie-afsluiting 2026-06-13) — ADR-022 volledig afgerond

Build **V008**, migratie head **`0009`** (3 ADR-022-migraties: `0007` profiel, `0008` tenant-vragenset,
`0009` `checklist_dragend`-vlag). Tests: **567** module + **72** platform (1 pre-existing env-auth-test,
zie OP-30) + **255** frontend groen. ADR-022 (Fase A–F + W1) compleet: een componenttype kan een
eigen, **tenant-eigen** checklist dragen — profiel, scoring, lifecycle, toestand-gebaseerde type-lock,
per-type readiness — losgekoppeld van `applicatie`.

**Volgende prioriteiten**:
1. **ADR-006 — hash-chained audit-trail (#17)**: volgende grote prioriteit. ADR-022 ging er bewust
   vóór, zodat de audit-trail het definitieve besturingsmodel logt (append-only, nooit verwijderen).
2. **Tenant-onboarding (#16)**: automatische **baseline-kopie** van de vragenset bij `POST /tenants`
   (de #16-knip uit W1) — vandaag seedt alléén `dev_seed` per tenant; de platform-onboarding-hook
   ontbreekt. De seed schrijft tenant-scoped data → `lk_app` met de nieuwe tenant-RLS-context.

**Bewust vastgelegde foutcode-keuzes (ADR-022)**: `SUBTYPE_HEEFT_DATA` = HTTP **422** (Fase C
type-lock, via `OngeldigeRegistratie`; heroverweging naar 409 is open); checklistvraag type-mismatch
= HTTP **404** (`NietGevonden`, Fase B/E; OP-6-stijl, geen nieuwe code).

**Afgehandeld deze sessie**: lokale CC-settings (`settings.local.json`) nu **durable in-repo**
genegeerd via `.claude/.gitignore` (`*.org.json`, `.DS_Store`) — voorheen enkel via de globale
`~/.config/git/ignore`; het stray-bestand `settings.local.json.org.json` is opgeruimd.

### OP-29 — Impact-/graaf-lens veldlabel `aantal_applicaties` (naamsmell sinds Fase E) — OPEN (nice-to-have)

`component_service.impact_analyse` / `schemas.component.ImpactSamenvatting.aantal_applicaties` telt
sinds ADR-022 Fase E **alle** profiel-dragende geraakte componenten, niet alleen `applicatie`. De
lens is functioneel correct (profiel-generiek sinds Fase A); alleen het veldlabel is misleidend.
Verheldering = rename (bv. `aantal_beoordeeld`) — bewust buiten Fase E/F gehouden.

### OP-30 — `test_auth_pkce` Secure-cookie env-test faalt omgevingsgebonden — OPEN

`test_auth_pkce.py::test_callback_succes_zet_cd_session_cookie` faalt op de Secure-cookievlag in
test/dev; faalt identiek op een schone `HEAD` (los van ADR-022). Te onderzoeken: de Secure-cookie-
assertie omgevings-onafhankelijk maken (bv. `cookie_secure` expliciet in de testconfig forceren).

### OP-3 — Refresh-token-subsysteem (uit P2) — OPEN

P2 zet bewust geen refresh-token; sessie verloopt na 15 min en vereist
opnieuw inloggen. Bouwen: `/auth/refresh`, veilige server-side opslag van de
refresh-token gekoppeld aan een sessie-id, rotatie/intrekking, koppeling aan
de 8-uurs refresh-grens (CLAUDE.md). Geen token client-leesbaar.

### OP-4 — RP-initiated logout via Keycloak (uit P2) — AFGEROND (geverifieerd CD038)

Al geïmplementeerd (CD008/CD010): `POST /auth/logout` trekt het Redis-refresh-handle in
(haalt `id_token_hint`), wist `cd_session`+`cd_refresh`, en geeft de Keycloak
end-session-URL terug; de store (`auth.logout()`) navigeert ernaartoe zodat ook de
SSO-sessie eindigt. Werkt identiek voor tenant- én platform-accounts (gedeelde
login-/logout-infra). Gedekt door `logout.test.js` (redirect naar end-session-URL +
`/login`-fallback). In CD038 is de stale `AppLayout.vue`-comment (die nog "buiten scope"
beweerde) rechtgezet.

### OP-6 — Resource-ownership binnen tenant (P5/ADR-010) — AFGEDEKT (fase 1, P5)

Afgedekt voor fase 1 — tenant-scoped record-resolutie (kruis-tenant → 404) +
rol + RLS volstaan; per-gebruiker-eigenaarschap niet nodig in fase 1
(collaboratief register, ADR-009).

Geïmplementeerd in P5 (Applicatie-CRUD, referentie voor de overige entiteiten):
record-resolutie strikt binnen de tenant-sessie (RLS + expliciete
`tenant_id`-filter); een id buiten de tenant is niet vindbaar ⇒ HTTP 404
`NIET_GEVONDEN` (geen 403, geen onderscheid "bestaat niet" vs "andere tenant",
dus geen lek). Binnen de tenant geldt rol-gebaseerde autorisatie via
`vereist_permissie`; elke Medewerker/Beheerder mag elk record in de eigen tenant
bewerken. Fijnmazig per-gebruiker-eigenaarschap is bewust uitgesteld en pas te
heroverwegen als een toekomstige eis daarom vraagt.

### OP-7 — 401 en 403 in hetzelfde foutformaat (uit P3) — AFGEROND (geverifieerd CD037)

401 is al canoniek `{"fout":{...}}` (CD005): `NietGeauthenticeerd` +
`niet_geauthenticeerd_handler`, en `auth.py`-`_fout` levert hetzelfde envelope.
Live bevestigd op tenant-endpoint, `/auth/me`, `/auth/platform/me` en bij decode-fout;
de frontend (`api.js`) keyt op de **statuscode** en leest `body.fout.code`. 422 blijft
bewust native (ADR-014). In CD037 zijn nog twee stale route-docstrings
(`applicatie.py`/`dashboard.py`) rechtgezet en is een test toegevoegd die het
canonieke 401-envelope op een guarded tenant-route vastlegt.

### OP-13 — Platform-tabel-grants Platforminstellingen/Platformmetadata — OPEN

Het platform-permissiedomein (ADR-012) kent `Platforminstellingen` en
`Platformmetadata`, maar alleen de `tenant`-tabel bestaat. Bij het bouwen van
die endpoints: tabellen + migratie + `GRANT … TO lk_platform` /
`REVOKE … FROM lk_app` (zelfde patroon als `tenant`).

### OP-14 — Dev-credentials vervangen vóór productie — OPEN

`changeme_dev` staat als dev-default in realm (client-secret + testgebruikers)
en DB-rollen (lk_app/lk_platform/lk_admin via `POSTGRES_PASSWORD`). Vóór
productie vervangen door secrets; testgebruikers verwijderen of scheiden van
productie-realm.

### OP-16 — `tenantSlug`-getter leest verkeerd veld — AFGEROND (geverifieerd CD036)

De getter is al gecorrigeerd: `frontend/src/store/auth.js` kent **geen** `tenantSlug`
meer — de getter heet `tenantId` en leest `user.tenant_id` (de werkelijke `/auth/me`-
payload). `useTheme` gebruikt `auth.tenantId`; gedekt door `tenantId.test.js`
(`OP-16: tenantId-getter leest tenant_id`). De oorspronkelijke "leest verkeerd veld"-
bug bestaat niet meer (gefixt in een eerdere sessie, hier tegen de code bevestigd).

**Resterende testrand (CD019, minor)**: na het afhandelen van de `useTheme`-promise (`.catch` in
`tenantId.test.js`) resteert nog één pre-existing happy-dom `DOMException` (interne
resource-`fetch` van de thema-stylesheet, afgebroken bij window-teardown) op stderr —
telt niet als test-fout. Op te ruimen zodra `useTheme` echte call-sites + een
default-thema-fallback krijgt en de test wordt herontworpen met een expliciete
`onerror`-trigger i.p.v. happy-dom's toevallige `fetch`.

### OP-18 — Stale V001-docs (IMPLEMENTATIEPLAN / SESSIE_BRIEFING) — AFGEROND (CD018)

`IMPLEMENTATIEPLAN.md` is voorzien van een *HISTORISCH — V001-snapshot*-banner die naar
de live bronnen verwijst (CD013). De stale `SESSIE_BRIEFING.md`-bouwstatus is opgelost
in **CD018**: `update_claude_bouwstatus` draait nu vóór de generators (i.p.v. ná de
briefing-generatie), zodat `gen_sessie_briefing.py` het nieuwe `BOUWSTATUS`-blok leest.
Geborgd met `backend/tests/test_gen_build_volgorde.py` (functionele write-then-read +
statische volgorde-guard via `inspect.getsource`).

### OP-19 — Frontend bundle >500 kB — AFGEROND/gemitigeerd (geverifieerd CD038-sweep)

`vite build`: géén ">500 kB"-waarschuwing meer; de grootste chunk is `column-*.js`
(PrimeVue DataTable) op **384 kB** (<500 kB), geïsoleerd in een eigen chunk die alleen met
`ApplicatieDetail` laadt. **6 route-level lazy-imports** (CD012) verkleinen de initiële bundle
(`index` ≈ 164 kB). Het oorspronkelijke symptoom doet zich niet meer voor; verdere reductie is
optioneel (geen verplichting).

### OP-21 — Eigenaar-filter als distinct-dropdown (UX, optioneel) — AFGEROND (B6-b, DC012)

Ingehaald door **UX-B6-b**: `eigenaar_organisatie` is geen vrije tekst meer maar een
**verwijzing naar een organisatie-partij**. Het lijstfilter is daarmee een **zoekbare
organisatie-keuze** (`ZoekSelect` op `eigenaar_organisatie_id`, server-side), en sortering loopt
op de gejoinde organisatie-naam (v2n-keyset). De vrije-tekst-`ilike` bestaat niet meer.

### OP-20 — Live-DB-verificatie NULLS-LAST-paginering blokkadesoverzicht (#23) — OPEN

De NULLS-LAST-keyset van het tenant-brede blokkadesoverzicht (CD016, ADR-017 B5:
`encode/decode_sort_cursor_nullable` + `keyset_seek_nulls_last`) is offline
**structureel** getest (cursor-roundtrip met null-vlag, `.nulls_last()` in de
ORDER BY, IS NULL-takken in de seek), maar nog niet **empirisch** tegen Postgres.
Bevestig tijdens de **live-DB-run (#23 / Laag 5)** dat het over de NULL-grens
correct pagineert op de nullable kolommen (`toelichting`, `eigenaar`, `opgelost_op`),
in zowel `asc` als `desc`, zonder duplicaten of overgeslagen rijen.

### OP-23 — Cyclus-padbewaking bij invoer van structuurrelaties (B3) — OPEN

`component_structuur` staat cycli toe (B3): `ZELFVERWIJZING` (self) wordt geweigerd, maar een
indirecte cyclus (A→B, B→A, …) niet. De **leeskant is al cyclus-veilig** (visited-set in elke
traversal, o.a. de impactanalyse CD056). Open vraag: willen we cycli **bij invoer** detecteren/
waarschuwen (pad-bewaking in `component_structuur_service.maak_aan`), of blijft de data-laag
cycli toestaan en bewaakt alleen het leeswerk? Geen verplichting; oppakken als de praktijk
verwarrende cycli oplevert.

### OP-24 — C-drempel: catalogus-keuzevelden zoekbaar boven ~10 opties — OPEN

Catalogus-gedreven keuzevelden (componenttype, relatietype, contract-rol) zijn nu native
`<select>`. Zodra een dimensie structureel **>~10 actieve opties** krijgt, heroverwegen naar een
`ZoekSelect` (zelfde regel als entiteit-referenties, zie complidata-frontend). Geen verplichting;
drempel-gedreven. [CD049]

### OP-25 — Uvicorn-accesslog zonder timestamps — OPEN

De Uvicorn-accesslog mist timestamps, wat live-debugging bemoeilijkt. Logformat configureren
(timestamp + niveau) bij een logging-/observability-pass. Klein, nice-to-have. [CD048]

### OP-26 — `component.eigenaar_organisatie` NOT NULL vs. optionele eigenaar — AFGEROND (B6-b, DC012)

Ingehaald door **UX-B6-b** (migratie 0032): de NOT NULL-vrije-tekstkolom `eigenaar_organisatie` is
vervangen door een **optionele** composiet-FK `eigenaar_organisatie_id → element` (partij,
aard=organisatie). De `""`-workaround is verdwenen; schema's/API dragen nu `None` (echt optioneel).

### OP-27 — Dev-seed in een dev-guarded init-stap — OPEN (nice-to-have)

De dev-testdata (`dev_seed_testdata.py`) is een **handmatige** fixture (niet in de init-container,
bewust dev-only/prod-veilig). Na een reset (`down -v && up -d`) moet hij apart gedraaid worden.
Optioneel: een **dev-guarded** init-stap (bv. env-flag `SEED_DEV=true`) die de dev-seed
automatisch draait in lokale/dev-omgevingen, zodat `down -v && up -d` direct de volledige baseline
geeft — zonder risico op prod-seeding. Raakt de seed-pipeline → eigen besluit. [CD055]

### OP-28 — VPS-deployment — OPEN (roadmap-kandidaat, t.z.t.)

Besluit Bert: in een volgende sessie oppakken. Doel nog te bepalen (demo/test vs. productie).
Raakt: **OP-14** (secrets-hardening — overal `changeme_dev` vervangen door echte secrets); een
**productie-compose-variant** + reverse proxy/HTTPS (alleen 80/443 open); **Keycloak
production-mode** (`KC_HOSTNAME`, redirect-URI's/CORS op het echte domein i.p.v. localhost);
**offsite backups** (de pg_dump-keten bestaat al en is sinds CD055 Keycloak-vrij). Bij een
**productie**-doel zijn **ADR-006** (audit-trail) en **#16** (user-/tenantmanagement)
voorwaarden. EU-jurisdictie-VPS conform de platform-uitgangspunten.

### OP-22 — Backup-scope / secops: Keycloak-secrets in de DB-dump — AFGEROND (geverifieerd CD055)

Opgelost via de tweede optie: **Keycloak draait op een eigen database** `keycloak` (rol
`kc_user`, `init-db/02_keycloak.sql`), losgekoppeld van de app-DB `likara`. De backup
(`gen_build.py` → `pg_dump likara`) bevat daardoor **geen** Keycloak-auth-schema meer
(`credential`/`client`/…); geverifieerd in CD055: `pg_dump --schema-only` van `likara` levert
**0** Keycloak-tabellen. Loste tegelijk de `COMPONENT`-naamruimte-collision op (onze ADR-021-tabel
schaduwde Keycloak's interne `COMPONENT` in het gedeelde `public`-schema → Keycloak startte niet).
Zie complidata-db "V007-patronen" en `docs/LOKAAL-TESTEN.md` (named volume + reset).

---

### ADR-028 — Componentclassificatie (geparkeerd, na ADR-027)

Voorstel geland (DC013). Twee uitbreidingen op het componentmodel:
(1) **Componentrol** (platform-breed): interne_applicatie /
interne_dataprovider / externe_dataprovider / koppelvlak —
bepaalt of koppelingen zelfstandig omgehangen kunnen worden of
afhankelijk zijn van externe ketenafspraken; zichtbaar in
Landschapskaart als visueel onderscheid.
(2) **BIV-classificatie** (tenant-scoped schaal): Beschikbaarheid,
Integriteit, Vertrouwelijkheid — drie velden op component met
tenant-eigen 3- of 5-punts schaal; filterbaar in Landschapskaart,
basis voor migratieset-risicobeoordeling.
Zie docs/adr/ADR-028_componentclassificatie_voorstel.md.

---

### LIKARA — naamswijziging codebase — AFGEROND (LI038–LI050, sessie LI051)

Code-rebrand compleet: skills, docs, generators én alle gedragsbepalende identifiers
(`cd_`/`complidata` → `lk`/`likara`). Zie de V026-stand bovenaan voor de slice-uitsplitsing.
Live geverifieerd via verse provisioning + smoke + RLS-isolatie; backend 931/2/0, frontend 745/745.
**Resteert uitsluitend DC013** (GitHub-repo/remote-naam + lokale `~/complidata/`-map) — Berts
GitHub-actie, zie V026-stand.

---

### Laag-2 identifier-rename: complidata/cd_ → likara — AFGEROND (LI041–LI050)

Feitenrapport (LI041) + uitvoering in slices S1–S8 + de DB-triggerfunctie (S7, gate+migratie 0044):
- cookies `lk_session`/`lk_refresh` (S3); env `LIKARA_TEST_MODE`/`LIKARA_FIXTURE_SET` (S4);
  CSS-tokens `--lk-` (S2); infra `lk_rabbit`/vhost `lk-{slug}`/MinIO `likara_admin`/paden `~/likara/` (S6);
  audit-triggerfunctie `lk_audit_append_only` (S7).
- **`cd_`-tabelprefix bestond niet** (geverifieerd LI041) → geen tabel-migratie nodig; de enige
  schema-rakende rename was de audit-triggerfunctie (S7).
- DB-rol `cd_admin` **bewust niet hernoemd** (geen runtime-gebruik; alleen var-naam in fixtures, opgeschoond in S1).
- Vangrail-greps (`compliman|cm_|Eraneos`) en historie (migratie 0010, changelog) ongemoeid gebleven.

---

## Horizon na MVP — bron-gedreven opvoeren (denk/ontwikkelrichting)

> ⚠ **Horizon, geen backlogtaak.** Ligt nadrukkelijk **ná blok A / na de MVP-gates** en vergt
> eerst haalbaarheidsonderzoek. Geen ADR (nog geen besluit; richting, geen keuze). Vastgelegd
> LI042 (2026-07-15).

Kern: **de consultant bevestigt in plaats van invoert.** "Dit is een Zaakregistratiecomponent"
→ LIKARA doet uit gestandaardiseerde bronnen een voorzet (bedrijfsfuncties, standaarden,
betrokkenen); de mens vinkt aan, stelt bij, verwijdert. Drempel omlaag, curatie overeind.
Vier denklijnen: (1) AI-ondersteunde vulling — voorstel-generator, nooit auto-koppelen, LLM-
bevraging bewust buiten scope; (2) bronnen-import — scheid extractie (ArchiMate/catalogus) van
deductie (spreadsheets/documenten), elk resultaat draagt bron + zekerheid, output altijd een
voorstel-tot-import; (3) GEMMA Softwarecatalogus als **bron**, geen concurrent (mist juist de
bedrijfsfunctie-as); (4) de opvoer-wizard — vier bevestig-stappen, grotendeels zonder AI, leeg
blijft eerlijk leeg.

**Volledige notitie (denklijnen, grenzen, haalbaarheidsvragen, fasering):**
`docs/horizon/Horizon-bron-gedreven-opvoeren.md` — eigen notitie omdat dit een geborgde
gedachtegang van ~120 regels is, geen afvinkbaar punt; de backlog blijft zo een backlog.

---

## AFGEROND (sessie 2–3)

- **O2** — 7.5 BIO2-classificatie → BBN (CD035): de default-optieset van vraag 7.5 is
  **BBN1/BBN2/BBN3** i.p.v. Laag/Midden/Hoog. Expand/contract: `seed_antwoordconfig`
  levert fresh deploys direct BBN; migratie **0004_bio2_bbn** soft-deactiveert de legacy
  `laag/midden/hoog`-opties op bestaande deploys (incl. dev-DB). Bestaande
  `antwoord_waarde` blijft resolvebaar (inactieve sleutels mét `actief`-vlag). Idempotent;
  engine-tellingen (1·4·3·4 / 7·1·2) ongewijzigd. O3/O4 blijven open observaties.
- **OP-15** — CLAUDE.md test-mode-comment (CD013): de comment was al rechtgezet in
  V004 — `COMPLIDATA_TEST_MODE` versoepelt alleen de Origin-check + rate-limit, geen
  auth-stub, seedt niets, inloggen vereist Keycloak. Punt afgesloten.
- **OP-17** — ADR-009 enum-voetnoten ↔ code (CD013): ADR-009 bijgewerkt naar de
  werkelijke code-waarden (`models.py` als single source, == migratie): hostingmodel 7,
  migratiepad 6 (incl. `tijdelijk_gedeeld`), datatype 6 (incl. `combinatie`),
  protocol = vaste enum, `eigenaar_organisatie`/`organisatie` = vrije tekst,
  `checklist_compleet` transient (ADR-013 B4).
- **OP-1** — platform_init-seed als deploystap → vervangen door de
  init-container (ADR-011): `lk-migrate` migreert (lk_admin) → `platform_init`
  → sluit af, met gating vóór de app. CLAUDE.md Commands bijgewerkt.
- **OP-2** — plantekst + skills bijgewerkt → §Architectuurcorrectie in
  `IMPLEMENTATIEPLAN.md` gecorrigeerd; `platform_init`/deploypatroon in
  complidata-db/-security/-tests vastgelegd.
- **OP-5** — cookie-attributen settings-driven (`cookie_secure`/`samesite`/
  `domain`) bevestigd; `COOKIE_SECURE=false` voor lokaal http (P4).
- **OP-8** — CONTRIBUTING §6 As 2 gecorrigeerd naar
  `python3 -m pytest backend/tests/ modules/` (groen geverifieerd).
- **OP-9** — deploy-/migratiestrategie vastgelegd in **ADR-011** (init-container).
- **OP-10** — OIDC `redirect_uri` gelijkgetrokken (realm ↔ backend) +
  realm-import (`--import-realm`); login-round-trip werkt.
- **OP-11** — `lk_admin` volledig uit de app-laag; `lk_platform` (non-superuser)
  voor platform-endpoints (ADR-012).
- **OP-12** — rol-mapping/tweelaags rollenmodel → opgegaan in **ADR-012**
  (realm-rollen → `realm_access.roles`, platform- + tenant-domein).

## LI018 — Openstaande punten

### Besloten, nog niet gebouwd
- **UI-hernoeming "Applicatie → Component"** — overal in de UI waar "Applicatie" de
  generieke component-entiteit bedoelt: menu, lijstpagina, detailpagina, knoppen.
  Pure frontend-hernoeming, geen datamodel-wijziging.
- **Type-indicator op graph-nodes** — klein type-label of icoon op de node zelf
  zodat het componenttype zichtbaar is zonder klikken.
- **"Resultaten" → "Componenten"** hernoemen in de Landschapskaart-zijbalk.
- **ADR-032 "Start vanuit..."-wijzer** — scope besloten (5 ingangen), open subknopen
  nog te beslissen vóór de bouw.

## LI048 — Openstaande punten (lijstkop)

### Afgedaan in snede 1b
- ~~**Bedrijfsfuncties past niet in de kop.**~~ **Opgelost.** Het scherm staat nu óók op de
  bouwsteen; de weergaveschakelaar (Boom|Diagram) en "Model inlezen" zijn naar de zone ónder de kop
  gegaan. `LIJSTKOP_OPENSTAAND` is volledig verdwenen — de scan draait zonder uitzonderingenlijst.
  De les staat in `likara-frontend`: een uitzondering die geen schade doet en netjes wordt
  afgedrukt, is nog steeds een achterdeur, want hij maakt een **vorm** navolgbaar.
- **De schakelaar-teller krimpt.** De Boom|Diagram-schakelaar draagt nu `.lk-schakelaar` in plaats
  van zijn eigen inline vorm. Dat is er één van de zes uit **OPVOLGPUNT LI048-0** (zes schakelaars,
  convergentievraag) — nog vier eigen vormen te gaan (de open-punten-sectie was de eerste).

### Besluit nodig
- ~~**Auditlog is geen lijstscherm in deze zin.**~~ **Besloten in snede 2: het krijgt dezelfde kop.**
  Het is geen andere soort scherm — de consultant komt er om iets terug te vinden, dezelfde
  beweging als op Componenten. Dat het geen aanmaakknop heeft, maakt het een scherm waar twee van
  de vier onderdelen ontbreken, en daar is regel 3 voor. Eén functioneel verschil blijft: de
  **Zoeken-knop is expliciet** (`@keyup.enter`, nooit `@input`) — op een auditlog kunnen heel veel
  regels staan, en elke toetsaanslag een zoekopdracht laten afvuren is daar geen dienst. Geborgd
  met een toets die omvalt zodra iemand dat "verbetert".

### Datumvelden op het auditlog — waargenomen gedrag wijkt af van de code (LI048, onbeslist)
Bert nam waar dat **Van/Tot standaard op vandaag staan**, waardoor hij ongemerkt in één dag van een
log met 45.000 regels keek — zonder dat iets dat zei. Zelfde familie als een verstopt filter
(`likara-ux` §P8a): de lijst ziet er compleet uit en is het niet.

**Gemeten, en de code zegt iets anders:** `AuditTrailView.vue:23` initialiseert
`van: '', tot: ''` (leeg), de route declareert `van/tot: Query(None)` en de service filtert alleen
`if van is not None`. Er is **geen enkele default** in de codebase. De waarneming is dus echt maar de
oorzaak ligt elders — browser-autofill op `type="date"` is de eerste kandidaat, een bewaarde
sessiestaat de tweede (dit scherm gebruikt `useLijstStaat` níét, dus dat is minder waarschijnlijk).

**Eerst reproduceren en de oorzaak vaststellen, dan pas beslissen.** Anders wordt er een default
"weggehaald" die niet bestaat. Als het autofill is, is de remedie een andere (bijv. `autocomplete="off"`)
dan wanneer het staat-herstel is.

Ongeacht de oorzaak blijft de UX-vraag staan: als er een datumbereik actief is, hoort dat zichtbaar
te zijn zonder de filterbalk te lezen — dat is §P8a, en dat geldt vanaf het eerste geval.

### ConfigBeheer-schermen krijgen de lijstkop (besloten, eigen snede zonder voorrang)
Bert heeft besloten: de acht `*ConfigBeheer`-schermen (platform-catalogusbeheer, buiten het
hoofdmenu) krijgen dezelfde `LijstKop` als de veertien hoofdmenu-schermen. Als **eigen snede,
zonder voorrang** — het is eenvormigheid voor de beheerder, niet voor de consultant die de hele dag
van lijst naar lijst loopt. Let bij het bouwen op het scan-bereik: dat wordt nu afgeleid uit het
hoofdmenu, en deze acht staan daar niet in.

### Objecthistorie compleet (LI048) — gebouwd; twee bevindingen
- **Sub-entiteiten horen in de geschiedenis van hun ouder.** Een roltoewijzing verscheen alleen in
  de partijhistorie als hij toevallig in dezelfde handeling ontstond; deed iemand het later apart,
  dan stond het nergens. `SUB_ENTITEITEN` in `auditlog_service` spreekt nu per objecthistorie-type
  uit welke sub-entiteiten erbij horen — óók waar het antwoord "geen" is, met reden. Twee toetsen
  dwingen beide richtingen af, zoals bij `NAAMBRON`.
- **Het demolandschap bevat GEEN partij met een losse roltoewijzing.** Gemeten: 229 roltoewijzingen,
  waarvan 75 naar een nog bestaande partij verwijzen — en die ontstonden alle 75 in dezelfde
  handeling als hun partij. Het herstel is daarom niet in de browser te tonen op bestaande data; de
  integratietoets maakt het geval zelf aan (twee gescheiden audit-contexten met een commit ertussen).
  Wil je het in de browser zien, dan moet je zelf een rol toekennen aan een bestaande partij.
- **`ASSOCIATIE-typen zonder sub-entiteiten`**: plateau, werkpakket, deliverable en gap hebben hun
  lidmaatschap via koppelingen (ADR-023 Fase E), en gemeten leveren die vandaag **0** auditregels op
  met een van die vier als uiteinde. Vandaar een "geen"-uitspraak met die reden. Komen die regels er,
  dan is het hetzelfde geval als de koppelingen bij component — en dan hoort het in het register,
  niet in een losse uitzondering.

### Detailkop-tekens (LI048) — gebouwd; één bevinding
- **Er was géén iconenvoorziening**, terwijl één knop er wel naar verwees: `icon="pi pi-info-circle"`
  op de Geschiedenis-knop wees naar een primeicons-klasse, en primeicons is geen afhankelijkheid van
  dit project. Die klasse bestond nergens, dus er rendeerde al maanden niets — zonder dat iets het
  meldde. Precies de stille-lege-render-faalmodus uit likara-werkprotocol. Nu vervangen door het
  klokje, en een bron-scan (`check-css-build.mjs`, icoon-scan) vangt zo'n dode verwijzing bij elke
  build: zowel een onbekende `<Icoon naam="…">` als élk `icon="pi …"`-attribuut.
- **Twee tekens, bewust geen pakket.** `src/components/Icoon.vue` draagt `kaart` en `geschiedenis`.
  Komt er ooit een derde wegwijzer bij, dan hoort die hier — en pas als het er véél worden is een
  pakket een afweging waard. De grens wanneer iets een teken mag zijn staat in likara-ux §P9.

### Auditlog component-filter — hersteld; één na-MVP-punt en twee bevindingen

**NA-MVP — zoeken in het auditlog naar soorten ZONDER eigen scherm.**
In het auditlog kun je alleen op een component filteren. Voor de **zeven soorten met een
detailscherm** (component, contract, partij, plateau, werkpakket, deliverable, gap) is dat opgelost:
daar geeft de **Geschiedenis-knop** het antwoord — je zoekt niet *naar* een ding in het log, je
vraagt de geschiedenis *van* het ding waar je toch al staat. Die knop bestaat op alle zeven schermen
en de weg erachter is soortonafhankelijk (`routes/objecthistorie.py`).

Wat overblijft zijn de soorten **zonder** eigen scherm — checklistvraag, koppeling, gebruikersgroep.
Dáár is nu geen weg naartoe. Eén zoekveld waarin alles kiesbaar is blijft de gewenste vorm
(nadrukkelijk **niet** eerst een soort kiezen en dan een naam: die extra stap dwingt de gebruiker te
weten in welk hokje zijn ding valt), maar het gaat om een kleinere verzameling dan dit punt eerder
suggereerde. **Niet inplannen als "alles doorzoekbaar maken"** — dat is grotendeels al gedaan.

De route accepteert al een `entiteit_type` (`routes/auditlog.py:41`, ongebruikt door de UI); dat is
een aanknopingspunt, geen oplossing. Zodra dit er is, heet het filter niet langer *Component*.

**Vindbaarheid is de échte openstaande vraag.** De Geschiedenis-knop bestond al op alle zeven
schermen, en tóch liep de consultant vast in het auditlog. Sinds LI048 draagt die knop bovendien geen
woord meer maar een klokje — mogelijk minder vindbaar, niet meer. Dat is een UX-vraag voor de
browsercheck, geen bouwvraag.

**Bevindingen uit deze snede:**
- **De dev-seed schrijft de complete seed onder ÉÉN correlatie_id** — 1.648 records, 18 soorten.
  Filteren op een geseed component levert daardoor één onbruikbaar grote "gebeurtenis" op. Geen
  fout van het filter en niet door deze snede veroorzaakt (de oude clausule gaf dezelfde groep);
  wel de reden dat het filter in de demo raar oogt. Van de 15.551 correlaties zijn er 15.382
  kleiner dan 20 records, dus bij echte handelingen speelt het niet. Kleinste stap: de dev-seed
  per logisch object een eigen correlatie geven.
- **Filterlabel, veldtekst en kolomkop staan op drie losse plekken** in `AuditTrailView.vue` (regels
  151, 152, 190) zonder gedeelde bron — precies waardoor de tekst iets anders kon beloven dan het
  label. Label en veldtekst staan nu naast elkaar en zijn met een toets geborgd; een gedeelde
  constante zou hier weinig toevoegen (ze zeggen bewust nét iets anders: "Component" vs "Kies een
  component…"). Het patroon speelt breder dan dit scherm — eigen afweging waard.

### Auditlog snede 3 — namen en waarden; vier punten open
- **`*_id`-waarden blijven een code** (besluit 4, bewust). ~20.000 vermeldingen; vraagt een
  id→naam-lookup per veld. Eigen slice.
- **`relatietype` heeft geen labelmap in `labels.js`**, dus die waarde valt terug op de ruwe tekst.
  Gemeten, niet aangenomen — staat als NB in `_WAARDENBRON`. Kleinste stap: de map toevoegen zoals
  de andere dertien.
- **Vier soorten dragen bewust geen naam:** `gebruikersgroep` (heeft geen naamkolom — aantalsfeit
  onder een gebruiksfeit; een naam zou twee stappen ver geleend moeten worden),
  `roltoewijzing`, `organisatiegebruik`, `gebruiker_persoon`. Elk met een reden in `NAAMBRON`, en
  een toets dwingt af dat een nieuwe soort niet stilzwijgend naamloos kan binnenkomen.
- **`entiteit_resolutie.py` draagt een ENGINE-INVARIANT in commentaar, zonder toets.** Het bestand
  mag geen lifecycle/score-symbolen importeren (`ComponentProfiel`/`Blokkade`/`Checklistscore`/
  `lifecycle_*`). Die regel is bij deze snede gerespecteerd (component_profiel, checklistscore en
  blokkade lenen hun naam van hun component, dus geen import nodig) — maar niets houdt een volgende
  wijziging tegen. Kleinste stap: een bronscan zoals de bestaande import-scans.

### Auditlog leesbaar — snede 1+2 gebouwd, drie punten open
- **De terugval op de huidige naam is een tekortkoming, geen ontwerp** (besluit 1). Bij een
  wijziging van een ánder veld dan de naam staat er geen naam in de auditrij, dus toont het scherm
  de **huidige** naam — en verandert díé regel alsnog mee bij een hernoeming. Raakt **1.179 van de
  1.223** wijzigingsregels. Oplossen vraagt een **naam-snapshot bij élke mutatie** (de capture-hook
  zou de naam van het geraakte object altijd moeten meeschrijven, ook als die niet wijzigt). Dat is
  een wijziging in de vastlegging, geen weergave — eigen slice, eigen afweging over logvolume.
- **Systeemherberekeningen tonen géén naam** (2.088 `derive`-regels). `component_profiel` en
  `blokkade` staan niet in `entiteit_resolutie._BRONNEN` én leggen zelf geen naam vast. De
  consultant ziet dan *Componentprofiel — <code>*. Keuze: de naam van het bijbehorende **component**
  erbij halen (die staat als `component_id` in de wijziging — dus mogelijk zonder schemawijziging),
  of accepteren tot snede 4.
- **Verwijderingen zonder vastgelegde naam blijven bewust naamloos** (162 van de 180). Dat is
  besluit 1 en het is juist: de huidige naam opvragen bij een verwijderd object levert óf niets, óf
  een ander object dat het id hergebruikt. Alleen `relatie` (68 regels) had voorheen soms een naam
  via de resolutie — en juist daar is `Relatie.naam` alleen bij flow-koppelingen gevuld, dus in de
  praktijk veranderde er weinig. Genoteerd zodat het niet later als regressie wordt gelezen.

### Zoeken op Auditlog — gerepareerd, met twee resterende punten
- **Het defect (verholpen).** Het zoekveld doorzocht alleen `Partij.naam` van de gekoppelde persoon,
  terwijl de kolom *Wie* `naam or e-mail` toont. Iedereen zonder gekoppelde persoon was onvindbaar —
  in het demolandschap iedereen (7.242 auditregels op `test:bert@test`). Geen fout, alleen "Geen
  gebeurtenissen gevonden": de consultant concludeert dan dat er niets gebeurd is. Geen regressie
  van snede 2; het scherm deed dit altijd al. Regel vastgelegd als **likara-ux §P8b**.
- **Het demolandschap kan het gekoppelde-persoon-pad niet tonen.** Er zijn 3 gekoppelde personen
  (J. de Vries, P. van Dijk, M. Bakker), maar **geen van hen heeft ook maar één auditregel** — ze
  hebben nooit iets gemuteerd. Zoeken op een persoonsnaam levert daar dus altijd leeg op, en dat is
  niet van een defect te onderscheiden zonder de database te bevragen. **Kleinste stap:** de
  dev-seed één mutatie onder een gekoppelde gebruiker laten doen, dan is het pad in de browser
  controleerbaar. Nu alleen in de backendsuite geborgd (op eigen testdata).
- **Flaky toets in `ComponentLijst.test.js`** — *"een chip wegklikken werkt zonder het venster te
  openen"* viel om in één van drie volledige runs; geïsoleerd en in de twee andere runs groen. Niet
  door deze snede geraakt (die komt uit het filtervenster van LI048 snede 1). Oorzaak is zichtbaar
  in de toets zelf: hij leest `api.componenten.lijst.mock.calls.at(-1)` terwijl de debounce-timers
  van de live-teller nog lopen — onder load kan een late callback een extra aanroep toevoegen ná de
  chip-klik, en dan kijkt de assertie naar de verkeerde call. Vraagt `vi.useFakeTimers()` of een
  assertie op de juiste call in plaats van de laatste.

### Snede 2 — bevindingen die een besluit of een volgende stap vragen
- **De inventarisatie klopte niet: er zijn 22 schermen met een kop boven een lijst, niet 7.**
  Correctie op de checkpointtabel (die telde Auditlog fout, en keek alleen naar `*Lijst.vue`).
  Van die 22 staan er nu **14** op de bouwsteen — het hele hoofdmenu op Signalering na. De acht
  overige zijn `*ConfigBeheer`-schermen: platform-catalogusbeheer, géén hoofdmenu, geen werklijst.
  **Te beslissen: krijgen die ook de kop?** Ze zijn onderling al eenvormig; het argument vóór is
  dat de beheerder óók van scherm naar scherm loopt, het argument tegen dat hij dat zelden doet.
- **Signalering + Plaatsingssignalen wachten op een eigen snede.** `PlaatsingSignalenView` is géén
  los scherm: `SignaleringView.vue:16` importeert hem en rendert hem als tab "Plaatsing" (ADR-035),
  met daarnaast nog een losse route `signalen/plaatsing`. Hem apart een `<h1>` geven zou een tweede
  paginakop binnen een tabblad opleveren. Signalering draagt bovendien een **handgebouwde tabrij**
  die op de `AppTabs`-bouwsteen hoort — dat is de eigenlijke snede, en de kop komt daar achteraan.
- **`NormBeheer.vue` heeft geen enkele testfile.** Het is het enige van de veertien schermen zonder
  suite. De toelichting-toets staat daarom in `LijstKopSchermen.test.js` (bron-gebaseerd), maar het
  scherm zelf — de lat verzetten, de rechten-gate — is niet op gedrag getoetst. Aparte actie waard.
- **Architectuur is meegenomen, buiten de opdracht om.** Het viel binnen het afgeleide scan-bereik
  en had exact de Bedrijfsfuncties-behandeling nodig (schakelaar Lagen|Tabel naar de zone eronder,
  op `.lk-schakelaar`). Het buiten laten zou een uitzonderingenlijst hebben vereist — precies wat
  snede 1b heeft afgeschaft. **Derde van de zes schakelaars uit LI048-0; nog drie te gaan.**

### Defect dat en passant is verholpen (niemand had het gemeld)
- **Vier lijstschermen hadden twéé zoekvelden.** Componenten, Partijen, Contracten en
  Bedrijfsfuncties droegen zoeken zowel in de kop als in de filterbalk eronder, elk met een eigen
  `v-model`-binding. De consultant kon in het ene veld typen terwijl het andere meefilterde — de
  lijst hoorde dan bij geen van beide velden, zonder dat iets dat aangaf. Nu geborgd op twee
  niveaus: een vitest-toets per scherm (`heeft precies één zoekveld`) én een bronscan-regel
  (`>1 type="search"` = overtreding, ook als beide netjes in de kop zouden staan).

### Bijvangst — geconstateerd, niet stilzwijgend meegenomen
- **Partijen en Contracten maken hun aanmaakknop met de hand**, niet met het Button-preset:
  een `router-link` met eigen kleur/radius/hover. Bewust gelaten (een link moet in een nieuw
  tabblad te openen zijn — dat kan een `<Button>` niet), maar de stijl staat nu op twee plekken.
  In deze snede alleen de **hoogte** gelijkgetrokken (`--lk-veld-h`) zodat hij op één lijn staat
  met het zoekveld. Kleinste echte stap: een `lk-knop-link`-recept in `main.css`, zodat het
  knopuiterlijk één bron heeft ongeacht of het een knop of een link is.

## LI047 — Openstaande punten

### VÓÓR PRODUCTIE oplossen — niet parkeren

*Deze kop bevat uitsluitend wat níét mee mag naar productie. Alles wat kán wachten staat onder
Parkeer-items — laat die twee niet door elkaar lopen.*

- **Kolom `organisatiegebruik.applicatie_id`** (`models.py`, klasse `Organisatiegebruik`) — een
  ECHTE databasekolom die het id van elk componenttype draagt (ADR-041 maakte de grove laag al
  component-breed; de kolomnaam bleef, met de opmerking "de kolomnaam is historisch").
  **Schemastap met migratie — eigen besluit van Bert**, niet meeliften.
- **De namenkaart in `KoppelingSectie.vue` haalt 100 componenten op zonder paginering**
  (`api.componenten.lijst({ limit: 100 })` in `_zorgCompNamen`). Die kaart resolveert de naam van
  de tegenpartij, want de flow-relatie draagt geen endpoint-namen.
  **Waarom dit niet kan blijven staan:** met 19 componenten merkt niemand iets, maar een echte
  organisatie zit daar zo overheen. Wat er dan gebeurt is **stil** — er breekt niets en er komt
  geen foutmelding; de tegenpartij-kolom toont simpelweg een **lege naam**. De consultant
  concludeert dat de koppeling naar een naamloos component wijst en meldt het niet, want er is
  niets om te melden. Een fout die zichzelf verbergt kost meer dan een fout die klapt.
  **Stand:** het probleem bestond al vóór LI047; de verbreding van de koppelingen naar elk
  componenttype maakt het alleen waarschijnlijker (meer componenten in beeld als tegenpartij).
  **Oplossingsrichting:** de namen per pagina meeleveren vanuit de relatie-respons, of de kaart
  gericht opvragen voor de id's die daadwerkelijk in beeld zijn — niet het limiet ophogen, want
  dan verschuift de grens alleen.

### Opruiming die is vrijgekomen (LI047)

- **`SignaleringBadge` is sinds LI047 ongebruikt.** De kopknop "Open punten" verving het rode
  bolletje op het componentdetailscherm; dat was de enige consument. Ongebruikt: de component
  `SignaleringBadge.vue`, `frontend/tests/SignaleringBadge.test.js`,
  `api.signalering.badgeComponent` (`api.js:362`) en de verwijzing in de docstring van
  `DetailKop.vue:13`. **Bewust laten staan** — een bouwsteen weggooien is onomkeerbaarder dan hem
  niet meer mounten; de tenant-brede Signalering leest een ándere bron en is ongemoeid.

### Kleine, benoemde punten (LI047)

- **Foutcode `GROEP_ZONDER_APPLICATIE`** (`gebruikersgroep_service.py`) — de gebruikerstekst is
  hersteld naar "component", de CODE niet. Machine-leesbaar contract: hernoemen raakt afnemers
  zonder dat er voor de gebruiker iets tegenover staat. Meenemen bij een volgende contractwijziging
  op dat endpoint.
- **`heeft_applicatie_subtype`** (API-veld, `ComponentRead`/`ComponentLijstItem`) — eigen
  betekenisvraag (het veld zegt "subtype" terwijl er geen subtabel meer is), dus geen simpele
  hernoeming.
- **"door onbekend · datum"** in `MigratiegereedheidSectie.vue:215` — geen gat (grammaticaal
  correct), maar "onbekend" leest als een persoon. De open-punten-zin lost dit anders op ("wie dat
  deed is niet vastgelegd"), maar dat is een volzin waar dit een compacte metaregel is.
  **Alleen zinvol als dat blok blijft bestaan** — de kopknop van LI047 vervangt het mogelijk.
- **`likara-werkprotocol` staat op 595 regels**, met vier nieuwe koppen onder §Gate-discipline na
  LI047. Een sectie met vier nieuwe koppen beschrijft niet meer één ding. **Wie er patronen bij wil
  zetten, consolideert eerst** — een protocol dat niemand meer leest geeft schijnzekerheid, en elke
  discipline die erop leunt leunt dan op niets. Staat als punt 0 in NEXT_SESSION.

### Parkeer-items (geen actie tot opgepakt)
- **Uitleg-icoon schaalt niet mee met zijn buur** — de "i" in `VeldUitleg.vue:129` is vast
  20 px (`h-5 w-5`) met 12 px tekst (`--lk-text-xs`), ongeacht of hij naast een kop van 24 px
  of een veldlabel van 16 px staat. Meeschalen vraagt een relatieve maat (`em`) plus een rij
  die de kopgrootte draagt, en raakt **alle 60 call-sites** — óók de 52 waar het icoon naast
  een gewoon veldlabel staat en waar niets mis is. Eigen afweging, geen bijvangst van de
  kop-rij-slice (LI047).
  **Vaststelling: pas de moeite als er een aanleiding voor komt** — de uitlijning is met
  `.lk-kop-rij` verholpen, en dat was de klacht. De maat op zichzelf is niet gemeld als
  probleem.
- **`font-mono` staat buiten het tokenstelsel** — 25 vermeldingen (sleutelkolommen,
  sleutelinvoervelden, bevestigingsdialogen in de 9 config-beheerschermen +
  `GebruikersbeheerView.vue:465,498`) gebruiken Tailwinds `--font-mono`; er is geen
  `--lk-font-mono`. Consequent toegepast en inhoudelijk verdedigbaar (sleutels lees je teken
  voor teken), maar de reden staat nergens vastgelegd — geen ADR, commit-bericht of
  commentaar. Kleinste stap: token toevoegen mét de reden, de 25 plekken erop laten wijzen.

## LI018 — Parkeer-items (geen actie tot opgepakt)
- Dedicated vitest-tests voor edge-popup-per-ring + groepeer-toggle Landschapskaart.
- Aardsortering "Afdeling" sorteert op enum-positie i.p.v. label-alfabetisch.
- COMPLIDATA_TEST_MODE → LIKARA_TEST_MODE (optioneel, feature-flag geen identifier).
- Pre-existing failing integratietest: `test_component_contract_op_niet_applicatie_component`
  (DB-state afhankelijk, faalt op schone reseed — niet door LI018).
- Skill-directorynamen `complidata-*` en `.claude/skills/complidata/` hernoeming
  (Laag 2 Fase 3 — bewust uitgesteld).
- Markdown-prose in session-docs (NEXT_SESSION/SESSIE_BRIEFING etc.) bevatten
  nog cd_app/cd-* in tekst — doc-pass indien gewenst.
