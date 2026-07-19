---
name: likara-werkprotocol
description: Werkprotocol voor PNA-interacties (claude.ai) en CC-uitvoering. Niet-onderhandelbaar. Lees bij elke sessiestart.
bijgewerkt: V042
---

# LIKARA Werkprotocol

## Kernprincipe — niet-onderhandelbaar

**Elk antwoord, elke analyse en elk advies vertrekt vanuit het continue verbeteren
van de gebruikerservaring met LIKARA.**

Techniek en proces zijn vangrail — nooit het startpunt, nooit de toon.
Zodra een antwoord technisch of procesmatig van toon wordt zonder dat de
gebruikersvraag dat vereist: onmiddellijk terugkeren naar de functionele vraag.

Bekende faalpatroon: te snel/diep de techniek of het proces in duiken.
Correctie: terug naar de gebruikersvraag. Altijd.

---

## KERNLES LI038 — een regel in de skills is geen borging; hij houdt pas als een gedeelde bouwsteen hem afdwingt

**Bewijs (twee onafhankelijke gevallen, beide gevonden in de browser — niet door 1000+
groene tests en niet door de skills zelf):**

- **Picker-regel 4** ("voorgevuld openen toont de volledige lijst; de voorgevulde waarde is
  een label, nooit een zoekfilter") stond **sinds LI032 in likara-ux** — en `ZoekSelect` deed
  het aantoonbaar níét (het filter-slot; faalmodus in likara-frontend §LI038).
- Het **draggable-overlay-recept** stond beschreven in likara-ux — maar leefde **twee keer
  inline** in `LandschapskaartView` (legenda + klik-popup), in strijd met de
  n≥2-convergentieregel die óók al in twee skills stond.

**Werkregel:**
1. Bij elke slice die een **bestaande skill-regel** raakt: **verifieer read-only dat de code
   de regel daadwerkelijk nakomt** — een geschreven regel is een *claim*, geen *garantie*.
2. Leg een regel bij voorkeur vast **in een gedeelde bouwsteen** (composable/component/
   service), niet alleen in tekst. Alleen dan erft elke nieuwe consument hem automatisch.
3. Wordt een regel geschonden aangetroffen: **fix in de bouwsteen, niet in de consument** —
   anders plant je de volgende schending.
4. **Sterkste borging = structureel onmogelijk maken** (zie "Scope voeren op eigen ids"
   hieronder: de api-vrije view).

**Derde geval (LI041, security-instantie): elk pad dat de regel kan omzeilen, moet hem dragen — of
het pad moet niet bestaan.** `MODELINHOUD_BESCHERMD` zat alléén op de voordeur
(`bedrijfsfunctie_service`); het generieke relatie-pad (`relatie_service.verwijder`/`werk_bij`) had
**geen enkele guard** en wiste elke relatie op id. De modelinhoud was dus beschermd via de voordeur
en stond open via de achterdeur. Dat dit toevallig beheerder-only was, was **geluk, geen
bescherming**. De fix voerde de guard terug op de bestaande bescherming
(`is_modelinhoud_plaatsing` → `_weiger_modelinhoud`, op beide mutatiepaden). ⚠ **Nog niet gebouwd
(opvolgpunt):** een test die bewijst dat **élk** relatie-mutatiepad de guard passeert — nu leunt de
dekking op de handmatig toegevoegde `_weiger_modelinhoud`, niet op een structurele scan. Tot die
test bestaat is dit een aanname, geen borging.

## Scope voeren op de ids van je eigen domein (LI038)

Voer een set-/scope-actie op de identiteiten van het domein dat je toont — niet op een
naburig domein. LI038: de proces-inzoom voert op **proces-ids** (proces-only pad); het
component-/vervuller-subgraaf-pad was ongeschikt (component-scope, **weigert bij 0
vervullers**). **Sterkste borging is structureel:** `ProcesDiagram` is **api-vrij** (data als
props uit de lijst) — een vervuller-call is daarmee *onmogelijk*, niet slechts "niet
aangeroepen". Verkies dit boven een afspraak of een test.

---

## Interactieregels (claude.ai — PNA-rol)

1. **Vragen één voor één.** Nooit meerdere vragen tegelijk. Wacht op antwoord.
2. **Adviezen één voor één.** Nooit meerdere adviezen tegelijk. Wacht op reactie.
3. **CC-taken één voor één**, OF in één pass uitsluitend als:
   - er geen openstaande vragen zijn, én
   - er geen adviezen zijn die een terugkoppeling vragen.
   Nooit vragen, adviezen en taken mengen in één beurt.
4. **Formuleer altijd functioneel en bondig.** Technische of schema-taal alleen
   als Bert dit expliciet vraagt.
5. **Analyses altijd vanuit functioneel gebruikersperspectief.**

---

## CC-opdrachtenformaat (niet-onderhandelbaar)

- Elke CC-opdracht = een volledig, op zichzelf staand `.md`-bestand via
  outputs + present_files. **Nooit** als losse chattext of codeblok.
- Vervolgstappen en correcties = altijd een volledige vervangende `.md` (v2-).
- Elk instructie-`.md` begint op regel 1 met: `START: [taaknaam]`
- claude.ai geeft altijd expliciet aan welk antwoord als `.md` naar CC moet.

---

## Commit-discipline

- De **enige** commit-trigger is de letterlijke zin: `AKKOORD: commit`
- "akkoord", "akkoord advies", "akkoord commit" (zonder dubbele punt) zijn
  **geen** commit-triggers.
- Akkoord met een advies ≠ commit-goedkeuring.
- claude.ai scheidt dit strikt in alle formuleringen.
- `AKKOORD: commit` wordt **uitsluitend door Bert, rechtstreeks in CC** gegeven — **nooit**
  door claude.ai in een opdracht-`.md` geschreven (een `.md` bevat alleen `START:`-instructies).
  Zo commit CC nooit op bestandsinhoud.
- **Doc/checkpoint krijgt een eigen commit-akkoord (W5, LI044).** Een checkpoint/doc lift niet mee met
  bouwwerk — het krijgt zijn eigen `AKKOORD: commit`. **Uitzondering:** een **ADR en het read-only
  checkpoint dat hem grondt** landen in **één** commit; de ADR verwijst ernaar met `Grond:`. (LI044:
  ADR-052 + `docs/Checkpoint-…-V044.md` samen gecommit, de ADR draagt `| Grond | … |`.)

### Stapelen in één werktree — alléén bij samenhangend, samen-committend werk (ADR-040)

Uitzondering op "één opdracht per werktree": een stap mag **ongecommit blijven terwijl een volgende
erop bouwt**, mits ze aantoonbaar **één geheel** zijn (samen ontworpen, samen te committen) en er een
**stash als vangnet** is. Anders: eerst committen. (Deze sessie: een backend-slice bleef ongecommit
tot de layout-fix die hij onthulde — ze landden samen in één commit.)

### Parallelle read-only sporen in een eigen worktree (LI042)

Aansluitend op — niet in strijd met — de root-commit-discipline (CLAUDE.md → Commit-discipline;
CONTRIBUTING.md sectie 7: **één commit per opdracht, sequentieel, één taak per schone werktree**).
Die discipline blijft **ongewijzigd** voor alles wat muteert.

- Een **read-only** leesopdracht (feitenopname, checkpoint, dekkingsscan — die **niets** muteert en
  **niet** commit) mag **parallel** draaien in een **tweede terminal met een eigen worktree**.
- **Voorwaarde: een ándere worktree dan een lopende bouw.** Deelt het read-spoor de werktree van een
  lopende bouw, dan leest het een **tussenstand** mee (half-gebouwde code, ongecommitte slices) — dat
  besmet de feitenopname. Eigen worktree = schone, gecommitte grond om tegen te lezen.
- **Bouw en commit blijven strikt sequentieel**, één taak per schone worktree — parallellisme geldt
  **uitsluitend** voor het lezen. Een read-spoor dat een wijziging blijkt te willen: stoppen en als
  eigen `START:` in de bouw-worktree inplannen.
- Dit is tevens de kiem van het latere **meer-personen-model** (meerdere lezers naast één bouwer).

---

## Gate-discipline (CC)

- **Schema-rakende slices** (nieuwe tabel / RLS / migratie / RBAC / audit, of
  iets dat het werkende domein raakt): CC bouwt volledig + draait tests +
  **STOPT met gate-rapport vóór commit**; Bert verifieert, dan `AKKOORD: commit`.
- **Lichte, volledig additieve fases** (read-side / frontend / constanten;
  geen schema): autonome doorloop tot eindrapport met één afsluitende commit
  toegestaan.
- **Design-heavy / rimpel-fases**: altijd eerst checkpoint — CC legt codestaat
  vast + open vragen + gefaseerd bouwplan en STOPT; claude.ai lost open vragen
  één voor één op met Bert vóór de bouw-instructie de deur uit gaat.

### Read-only-eerst boven aannames (ADR-040)

Bij elke diagnose **spreekt de code, niet de hypothese**. Een PNA-/instructie-aanname (ook een
"besloten" diagnose) is **richting, geen waarheid**. CC verifieert de aanname tegen de code (grep,
lezen, een read-only reproductie) en **stopt-en-rapporteert bij discrepantie** — schrijf géén fix
voor een filter/symbool/bug die niet blijkt te bestaan. (Deze sessie: een "verweesde-org-opruimfilter"
dat er niet was; een scope-bug die scenario-afhankelijk bleek, geen defect.)

### Reikwijdte-scan vóór een klasse-fix (LI037)

Een fout die een **klasse** kan zijn (een niet-idempotente seed-stap, te-ruime rol-gating, een
gedupliceerd patroon) wordt eerst read-only **breed geïnventariseerd** — waar zit hetzelfde
patroon nog? — vóór de fix wordt afgebakend. Niet één plek dichten en de rest laten staan; de
scan bepaalt de reikwijdte, Bert beslist over de afbakening. (LI037: seed-idempotentie en
verwijder-gating beide zo aangepakt — de gating-scan vond zes plekken i.p.v. één, én
falsifieerde een vermeende zevende.)

### Adversariële checkvraag vóór de bouw (LI041)

Waar een ontwerp een keuze maakt die **niet expliciet besloten** is — een tiebreak, een
categorie-indeling, een vertrekpunt — stel dan een **read-only checkvraag** die die keuze
blootlegt, vóórdat er gebouwd wordt. **Bouw niet door op een aanname die zich voordoet als een
besluit.**

> De vraag is niet *"hoe implementeer ik dit?"* maar: *"welke keuze maak ik hier stilzwijgend, en
> wie heeft die genomen?"*

Dit is de sterkste vangrail van LI041: **drie van de vier stille keuzes** (de UUID-tiebreak in de
omhoog-cue, de tabel-knip en de endpoint-knip op de rollengrens) zijn niet door een test maar door
een read-only checkvraag/checkpoint vóór de bouw gevangen — de suite bleef groen. De checkvraag is
de vooraf-tegenhouder bij de kernregel *"de vorm bepaalt nooit de betekenis"* (likara-domeinmodel
§LI041); zonder deze stap is die kernregel een spreuk. De twee horen bij elkaar.

**Het uitvoerder-gedrag dat de skill wil:** CC's eigen **twee stops** in LI041 — stoppen op de
relatietype-classificatie (aggregation draagt zowel GEMMA-grond als component-samenstelling) en op
de component-samenstelling, i.p.v. stil een classificatie kiezen. Stoppen op een onbeslisbare
classificatie is correct gedrag, geen vertraging (Gate-werkwijze: "bij twijfel stoppen").

**UI-/vorm-toepassing (checkpoint-vóór-vorm, LI042).** De checkvraag geldt óók vóór een
**visuele/vorm-keuze**, niet alleen bij backend/schema: check read-only of het render-kanaal/
mechanisme dat je wilt gebruiken **vrij** is — is de kleur al bezet, is de rand al bezet, bestaat er
al een filter-pad? Leg nooit een tweede betekenis op een bezet kanaal zonder dat eerst vast te
stellen. De kanaal-lijst van de kaart (likara-frontend §Signaal-kanalen · kaart-kleur-lezing:
werk→rand-stijl, status→vulling, domein→rand-kleur, selectie→amber-rand) **ís** de concrete
checkvraag voor UI-ontwerp. **Is geen kanaal vrij: stoppen en melden, geen compromis kiezen.**
(LI045-instantie: **amber** was al bezet door de bewuste afwijking, **blauw** door de linkkleur én de
bestaande "i" — de verschoven lat kreeg daarom een **neutraal/gedempt** kanaal, geen vierde kleur op
een bezet kanaal.)

### Herijk de fasering als stappen niet los toetsbaar blijken

Klein-houden is een **middel, geen doel**. Als een gate niet zelfstandig in de browser te beoordelen
is (iets ertussen maskeert het resultaat), is **samenvoegen juist correct** — meld de reden. (Deze
sessie: twee stappen waren niet los verifieerbaar door een tussenliggende layout-fallback → samengevoegd.)

### Vraag geen metadata over een gebeurtenis die in deze slice nog niet kan bestaan (LI045)

Kan de **handeling** pas in een latere slice plaatsvinden, dan is *"wanneer en door wie"* daar **niet
afleidbaar** zonder een derde bron of nieuwe opslag — **stop en rapporteer**, verzin geen metadata en
zet geen opslag vooruit. **Het veld ontstaat waar de handeling ontstaat.** (LI045: in slice 4a bestond
er nog geen handeling "de lat verzetten" — die kwam pas met het beheerscherm 4b; de "wanneer/door wie"
werd daarom **niet** in 4a gebouwd maar in 4b uit het audit-spoor van de toggle gelezen, zonder nieuwe
opslag.) Zusje van de adversariële checkvraag ("welke afleiding maak ik, en kan de bron die dragen?")
en van de engine-invariant "geen tweede bron".

---

## Browsercheck vóór commit — niet-optioneel bij UX-/picker-/auth-slices (LI032)

**Stap 0 van élk browsercheck-draaiboek (LI046, niet-optioneel):** na een slice die nieuwe
bestanden of nieuwe importketens introduceert begint het draaiboek met **dev-server herstarten
en de modulecache verwijderen** (`rm -rf node_modules/.vite` + `npm run dev` opnieuw), gevolgd
door een harde refresh. Les LI046: een dagenlang draaiende Vite-server serveerde stale modules;
de browser toonde oud gedrag terwijl de suite terecht groen was — de bevinding leek een codebug
en was er (deels) geen. Zonder stap 0 is een browserbevinding niet interpreteerbaar.

Een **groene testrun betrapt geen kapotte UX**: mocks verbergen een verkeerde picker-bron, een
lege/onleesbare picker, voorvul-verdringing, een stale label, en een onnodige/foutgevoelige
account-aanroep. Bewezen deze sessie — drie keer bleef de suite groen terwijl het scherm in de
browser stuk was. Daarom: bij elke slice die **UX, keuzevelden (pickers), of auth/provisioning**
raakt, verifieert **Bert de betrokken schermen in de echte browser vóór `AKKOORD: commit`**. Het
gate-rapport levert daarvoor een **browsercheck-draaiboek** (per stap: handeling → verwacht
resultaat). Groene tests ≠ commit-toestemming.

**LI041 = zevende bevestiging:** zeven bevindingen deze sessie, geen enkele zichtbaar in 1200+
groene tests. De regel is niet nieuw — dit is opnieuw bewijs dat de browsercheck het sluitpunt is.

**Rol-gating toetst met béíde rollen in de echte browser (LI037).** Een mock dekt "welk recht"
niet: een groene test zag "knop verborgen bij magBewerken=false", maar niet dat verwijderen een
**ánder** recht eist dan bewerken (medewerker zag de knop en kreeg pas een 403 in de dialoog).
Bij elke slice die rol-gating raakt bevat het draaiboek stappen als medewerker én als beheerder.

**Seed de demostaat zó dat de browsercheck iets te zien geeft (LI044).** Een browsercheck toetst een
leeg scherm als de demodata het te tonen verschijnsel niet draagt — een norm-badge is pas zichtbaar
bij een genormeerd, klaar-verklaard component **mét** open feiten. Prepareer die staat (idempotent, op
de dev-tenant, exact wat de seed doet) vóór het draaiboek, en benoem in het draaiboek welk component
welk geval toont. Leesbare tegenhanger van de walkthrough-baseline-regel (benoemde begintellingen).
(LI044: Archiefbeheer = klaar mét open feiten → badge. **S1/LI045**: seed óók een SCHOON geval —
HR-systeem, volledig norm-compleet → géén signaal, óók na een latverschuiving — zodat de browsercheck
kán aantonen dat een signaal terécht wégblijft. Zonder schoon geval is een "geen signaal"-vinkje
onbewijsbaar: bij slice 4a is "Klantportaal toont geen signaal" afgevinkt terwijl Klantportaal ná de
bedoeling-toggle juist de verschoven-lat droeg. Een leeg antwoord ("bewust geen koppelingen") is dáár
een écht antwoord, geen gat.) **Regel: elk signaal heeft in de seed zowel een geval dat het draagt als
een geval dat het terecht níét draagt — en het schone geval wordt geborgd met een test** (die de
seed-stap aanroept en signaalloosheid ná een latverschuiving assert; hij valt om zodra een
seedwijziging het schone geval vervuilt). Referentie: `_seed_schoon_geval` (HR-systeem) +
`test_seed_schoon_geval_s1`.

## Tool-cadans richting productie (LI042 — vaste stappen)

Vaste slash-commando-cadans naast de gate-werkwijze. **Alle vier zijn user-triggered: Bert typt ze
zelf; CC kan ze niet zelf aanroepen** (CC mag ze wél voorstellen). Namen/functies geverifieerd tegen
de echte CC-setup (LI042).

**Sessiestart** (na ZIP-ingest + skills-read, vóór de eerste bouw) — rapport-only, fixt niets zonder
bevestiging:
- **`/doctor`** — health van de CC-installatie + **volledige checkup** die issues kan fixen (leest de
  settings-bestanden, kan CLAUDE.md trimmen/migreren, ongebruikte extensies uitzetten).
  ⚠ **`/checkup` bestaat NIET als apart commando** — de "full checkup"-functie zit ín `/doctor`.

**Pre-commit** (ná de browsercheck, vóór `AKKOORD: commit`) — het net onder de browserverificatie;
de browsercheck blijft het echte sluitpunt (§Browsercheck vóór commit):
- **`/security-review`** — **smal**: scant de diff op het security-oppervlak (RLS/rol/Keycloak/
  auth/validatie), kan fixes voorstellen.
- **`/code-review ultra`** — **breed**: cloud-hosted multi-agent review van de branch/PR (logica,
  edge-cases, kwaliteit). `ultra` is het effort-niveau, geen apart commando; `/ultrareview` is de
  **deprecated alias** ervan. Billed. **Richting productie is `/code-review ultra` een vaste
  pre-commit-stap, niet alleen bij gates** — nu er echte tenant-data in beeld komt, weegt de
  grondigheid zwaarder dan de snelheid.

## Geen schuld laten ontstaan (LI032)

- Een bekende (rand)bug wordt **óf in de slice dichtgetimmerd, óf expliciet als eigen benoemd
  vervolgpunt** vastgelegd (OPVOLGPUNTEN.md) — **nooit stil geparkeerd**. Een half-gedichte bug die
  groen-maar-kapot blijft, komt gegarandeerd bij de volgende klik terug.
- Een **tweede implementatie van iets bestaands wordt naar de gedeelde bouwsteen geconvergeerd**,
  niet ernaast laten bestaan (bv. afdeling-inline-aanmaak → één `AfdelingSelect`).
- **Reparatie mag bovenop een ongecommitte gate-staat** verder bouwen, met de **laatste schone
  commit als expliciete terugval**; terugdraaien alleen als de gerichte fix niet lukt (niet als
  eerste reflex).
- **Verergert een slice een bestaand gebrek, repareer het binnen dezelfde changeset — mits het
  adoptie is, geen verbouwing (LI045).** Maak je een bestaand probleem groter (bv. de norm-passage
  maakte het VeldUitleg-paneel hoger → het viel buiten beeld), dan los je het in dezelfde slice op als
  de fix **adoptie** van een bestaande gedeelde bouwsteen is (één wijziging, alle consumenten erven
  hem — zie KERNLES LI038 #3). Is het een **verbouwing** (nieuwe bouwsteen, brede blast-radius): **eigen
  slice met expliciete bevinding**, niet meegelift. Stap 1 is daarom read-only vaststellen wélke van de
  twee het is, en stoppen als het verbouwing blijkt.

---

## CC-autonomiescope

- CC draait autonoom tot eindrapport **uitsluitend binnen de LIKARA projectroot**.
- Nooit autonoom iets buiten de projectroot uitvoeren of wijzigen.
- Valt iets buiten de besloten keuzes (onvoorziene model/RLS/semantiek-keuze):
  CC stopt altijd en rapporteert terug.

---

## Structurele oplossing — niet-onderhandelbaar

Altijd de structurele oplossing implementeren (surrogate PK, composiet UNIQUE,
echte FK's, schema dwingt invarianten af). Nooit een conventie-gebaseerde
workaround. Pre-productie is het goedkoopste moment.
claude.ai adviseert structureel en presenteert een workaround nooit als
gelijkwaardig alternatief.

---

## UX-first als correctieprotocol

Als claude.ai merkt dat een antwoord technisch of procesmatig van toon wordt
terwijl de gebruikersvraag functioneel is:

1. Stop.
2. Stel de functionele vraag opnieuw centraal.
3. Geef het antwoord vanuit de gebruikerservaring.

Conflict tussen gebruikerslogica en procesvoorkeur: **gebruikerservaring wint.**

---

## Operationele afspraken

### Stack opstarten
"Start de gehele stack" = altijd Docker Compose + frontend dev-server samen.
Nooit alleen Docker Compose zonder dev-server — de gebruiker kan dan niet inloggen
(Keycloak redirect_uri wijst naar :3000).

Volgorde:
1. `docker compose up -d`
2. `cd frontend && npm run dev` (of via CC achtergrondtaak)
3. Verifieer: `docker compose ps` (alle services healthy) + :3000 bereikbaar

---

## UX-first analysekader (LI024, bevestigd werkprotocol)

Bij elke feature-vraag, ADR-besluit of technische keuze:

1. **Wat ziet/doet de gebruiker?** (startpunt — altijd)
2. **Welk probleem lost het op voor de gebruiker?** (context)
3. **Wat is de eenvoudigste oplossing die dat doel dient?** (richting)
4. Pas dan: technische uitwerking als vangrail.

Een analyse die bij stap 4 begint, is een overtreding van dit protocol.
Een advies zonder stap 1–3 mag niet worden uitgebracht.

Dit kader is niet-onderhandelbaar en overschrijft elke neiging om met
technische overwegingen te openen.

---

## ADR-onderhoud — bijwerken naar de gebouwde realiteit (ADR-040)

Onderweg-afwijkingen van een ADR moeten **terug de ADR in, met de reden**. Bij sessieafsluiting: toets
de ADR tegen wat **écht gebouwd** is en veranker de afwijkingen — de ADR beschrijft de gerealiseerde
oplossing, niet het oorspronkelijke voorstel. (Deze sessie: de ADR schreef een layout voor die
niet-deterministisch bleek; gebouwd werd een deterministische variant → dat hoort terug in de ADR.)

## Keuze-sortering vóór je iets onthoudt (LI034, pointer)

Vóór je een keuze onthoudt: sorteer 'm — **platformvormend → centraal beheer; persoonlijke werkstijl →
voorkeur-laag; momentkeuze → inline/vers**. Detail (vaste bril vs. momentkeuze, "onthoud als mijn
standaard") in **likara-ux**.

## LI035 — UX-first-aanscherping + browsercheck-als-patroonbron (bevestigd)

- **Gebruikerservaring is áltijd het uitgangspunt**; techniek, schema-keuzes, gates en
  commit-discipline zijn vangrails — nooit de toon of het vertrekpunt van een antwoord.
  Conflicteert gebruikerslogica met een technische voorkeur, dan wint de
  gebruikerservaring.
- **Kort, bondig, functioneel**: analyses starten bij de gebruiker, niet bij de tabel.
  Vragen én adviezen strikt één voor één; CC-opdrachten altijd als zelfstandig leesbaar
  `.md` met `START:` op regel 1.
- **Browsercheck-bevindingen zijn patroon-signalen, geen punt-fixes.** De LI035-les: zes
  bevindingen (overlay gedrukt, omlijning geclipt, voetbalk scrolde mee, schaduw grijs,
  blokken versnipperd, succes stil) leidden elk tot patroon-onderzoek en werden zes
  systeembrede patronen (breedte-override-borging, Dialog-primitive-regels,
  scroll-schaduw, samengevoegd blok, succes-toast-standaard, MeldingBanner). Eerst de
  vraag "waar bestaat dit nog meer / wat is de regel?", dán pas de fix.

## LI036 — set-acties wijzigen nooit de weergave (herziening ADR-040 "ingang → brede plaat")

Bevestigd besluit: **een set-actie muteert uitsluitend de set, nooit de weergave.**
Toevoegen/verwijderen/"haal buren erbij"/"voeg vervullende componenten toe" laten de
gebruiker in de weergave waar hij is (Lagen blijft Lagen; de nieuwe componenten
verschijnen dáár). Hercentreren/weergave-wissel hoort bij dubbelklik en de expliciete
weergave-schakelaar. De vroegere ADR-040-regel "een set opbouwen via een ingang = brede
plaat → overzicht" (`toonOverzicht()` in het gedeelde set-pad) is hiermee HERZIEN en uit
de code verwijderd. (Hoort óók terug in ADR-040 — staat op de ADR-onderhoudslijst.)

## LI039 — werkprotocol-aanscherpingen (gevalideerd fase A: `docs/Validatie-patronen-LI039.md`)

*(Alle regels hieronder zijn procesdiscipline: tekst-regels zonder bouwsteen — ze rusten op
naleving, niet op structuur. De bestaande regels waar ze op aanhaken staan erbij.)*

- **Read-only-eerst, tweemaal herbewezen (aanvulling op §Read-only-eerst).** Een hypothese
  van de PNA is richting, geen bouwopdracht — LI039 leverde er twee die bij validatie
  ANDERS bleken: de dubbele-melding-oorzaak (geen leeg aanbod maar een 500 door een
  model↔schema-mismatch) en "de dev-seed vult het aanbod" (het is `platform_init` +
  migratie 0061). Beide keren was de fix een andere dan de hypothese suggereerde.
- **Telling vóór besluit — "denkbaar is niet geteld" (aanscherping op §Reikwijdte-scan).**
  Een ontwerpbesluit over een verschijnsel begint met de meting ervan: ADR-044 (meervoudige
  ouders) is genomen op de GETELDE 7 gevallen uit de bron (Verkenning §B1), niet op "dat kan
  voorkomen". Wie niet telt, dimensioneert op fantasie. *(LI040 herbevestigd: 25/32 grof-only
  gebruiksfeiten besliste waar de uitstap-stand landt — ADR-046 besluit 4; en de vóór/ná-metingen
  van 0066/0067/0068 bevestigden "datakost nul" feitelijk i.p.v. aangenomen.)*
- **Convergentie-vorm bij twee waarheden (aanvulling op de KERNLES):** nooit een tweede
  implementatie — een **tweede export in dezelfde module**, met de bestaande consument
  byte-compatibel. Referentie: `procesBoom.js` (`procesBoomStructuur` ongewijzigd voor
  ProcesLijst; `meervoudBoomStructuur` ernaast voor ADR-044).
- **Nieuwe dependency ⇒ image herbouwen — deploy-consequentie in het gate-rapport.** Een
  dependency in `requirements.txt` bestaat pas in de container ná `docker compose build`;
  tot die tijd draait de api de oude omgeving (LI039: defusedxml — de api viel om tot de
  rebuild). Het gate-rapport benoemt de rebuild expliciet.
- **Migratie: bouw ÉN toepassing horen bij de slice.** Een model↔schema-mismatch legt élk
  endpoint op die tabel plat (LI039-incident: `inlees_voltooid` in het ORM, migratie 0064
  nog niet toegepast → 500 op het aanbod-endpoint). De migratie wordt gebouwd én toegepast
  binnen dezelfde slice, vóór de code actief wordt; een onderbroken slice laat dit als
  EERSTE herstelpunt na. (De lk-migrate-keten past bij een stackstart automatisch toe — het
  gat ontstaat lokaal, bij bind-mounted code zonder upgrade.)


## LI040 — sessielessen (gevalideerd)

- **Browserverificatie-faalmodus: de stil niet-geresolvede component.** Een ontbrekende `import`
  van een Vue-component geeft GEEN fout — Vue rendert het element stil leeg, en de suite blijft
  groen (mocks zien het niet). Dit is de scherpste reden achter de bestaande browsercheck-regel
  (LI032) én de tests-regel "assert op zichtbare tekst" (likara-tests, LI040).
- **Een volle CC-sessie levert stil kwaliteitsverlies.** Bij ~100% context: **verse sessie + een
  zelfstandige overdracht-`.md`** (zelfde vorm als elke opdracht: stand vaststellen read-only,
  suites bevestigen, dan wachten). Elke opdracht is zó geschreven dat opnieuw beginnen bijna
  niets kost — dat is een eigenschap van het opdrachtformaat, geen toeval.
- **Reproduceerbaarheid van externe bronnen.** Van elk ingelezen referentiemodel liggen
  **commit-hash (gepind) + SHA-256** vast in `HERKOMST.md`
  (`modules/bwb_ontvlechting/backend/referentiemodellen/`) — zodat een meting later herhaalbaar
  is. *(Reden uit LI040: de verkenning liep vast doordat een eerdere GEMMA-release niet meer
  vindbaar was; de raw-URL op de commit-hash haalt hem exact terug.)* Zie ook likara-domeinmodel
  §ADR-043/044.
- **Bedieningskennis hoort in de bedieningsdoc.** Wat een mens nodig heeft om te testen
  (platform-inlog, menupad) staat in `docs/LOKAAL-TESTEN.md` (de platform-login staat daar
  inmiddels, regel ~117-131) — niet alleen in een skill. *(LI040: een browsercheck-draaiboek liep
  vast op een platform-login die al bestónd maar alleen in skill-context leefde.)*
