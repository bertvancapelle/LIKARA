---
name: likara-werkprotocol
description: Werkprotocol voor PNA-interacties (claude.ai) en CC-uitvoering. Niet-onderhandelbaar. Lees bij elke sessiestart.
bijgewerkt: V050
---

# LIKARA Werkprotocol

## Kernprincipe — niet-onderhandelbaar

**Elk antwoord, elke analyse en elk advies vertrekt vanuit het continue verbeteren
van de gebruikerservaring met LIKARA.**

Techniek en proces zijn vangrail — óók schema-keuzes, gates en commit-discipline — en
nooit het startpunt, nooit de toon. Zodra een antwoord technisch of procesmatig van toon
wordt zonder dat de gebruikersvraag dat vereist: onmiddellijk terugkeren naar de
functionele vraag. Conflicteert gebruikerslogica met een technische of procesvoorkeur,
dan wint de gebruikerservaring. (LI035)

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

**Vierde geval (LI046): een per-tak-regel wordt vergeten — maak er een invariant van, geen afspraak.**
Twee regels die deze sessie tekstueel vastlagen en tóch misgingen: (1) de **`gebruikt`-tak** van de
edge-popup ontbrak → de doorklik viel stil door naar het koppeling-pad; (2) twee binnenkomst-takken
zetten `beginschermOpen = false`, de **derde niet** → de terugkeer tekende werk dat niemand zag. Beide
"afgedekt" in proza. De fix in beide gevallen: **niet nóg een tak-regel opschrijven, maar de regel
structureel onvergeetbaar maken** — een dekkingsscan (`RINGEN ⊆ _EDGE_TAKKEN`) resp. **één eenmalige
regel ná de beslisboom** i.p.v. een vlag per tak (ADR-054 besluit 6). Vuistregel: **staat een regel
"in elke tak/plek moet je X doen", dan is X vergeten wachten te gebeuren** — hef de herhaling op (één
gedeelde plek) of laat een scan de afwezigheid vangen. Dit is KERNLES LI038 toegepast op fan-out:
tekst dekt geen tak die nog niet bestaat.
**Zelfde les, nieuw geval (LI046 banen) — géén nieuwe regel:** de baan-verdeling
(`kaartBanen.js:baanVerdeling`) rekent puur op het **knooppaar**, niet op de ring/soort — een nieuwe
relatiesoort krijgt een eigen baan zónder hier een tak toe te voegen. Geometrie soort-agnostisch **ís**
de invariant, i.p.v. "regel het per ring". Geborgd door de erven-test (`kaartBanen.test.js`: een
onbekend relatietype krijgt een eigen baan).

- **Convergentie-vorm bij twee waarheden (aanvulling op de KERNLES):** nooit een tweede
  implementatie — een **tweede export in dezelfde module**, met de bestaande consument
  byte-compatibel. Referentie: `procesBoom.js` (`procesBoomStructuur` ongewijzigd voor
  ProcesLijst; `meervoudBoomStructuur` ernaast voor ADR-044).
  (LI039, gevalideerd fase A: `docs/Validatie-patronen-LI039.md`.)

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

- **Kort, bondig, functioneel**: analyses starten bij de gebruiker, niet bij de tabel.
  Vragen én adviezen strikt één voor één; CC-opdrachten altijd als zelfstandig leesbaar
  `.md` met `START:` op regel 1. (LI035)

### Bronplicht — elke bewering draagt haar bron (LI050)

Bert kan aan een antwoord niet zien waarop het rust. Een advies dat op een samenvatting steunt
leest identiek aan een advies dat op het rapport zelf steunt — en corrigeert zichzelf pas als de
echte bron alsnog binnenkomt. Daarom:

1. **Elke feitelijke bewering draagt haar bron in de zin zelf** — niet als voetnoot achteraf:
   *"in het rapport §2A"*, *"uit jouw samenvatting"*, *"uit likara-db §Testdata-regel"*, *"gemeten
   door CC"*. Is de bron niet in te vullen, dan staat het feit niet vast: dat is het signaal om te
   meten of te vragen, niet om door te schrijven.
2. **Een genoemd maar niet-ontvangen bestand wordt opgevraagd, niet omheen geredeneerd.** Een
   CC-terugkoppeling in de chat is de melding dát er een rapport is — niet het rapport. Advies op
   zo'n melding is voorlopig en zegt dat er expliciet bij.
3. **Valideren gaat vóór aannemen; de repo is de referentie.** Niet hier herhaald — de norm staat
   al bij de uitvoerkant (CC verifieert tegen de code, niet tegen een hypothese of het geheugen).
   Deze regel trekt hem door naar claude.ai's eigen uitspraken: ook een advies wordt onderbouwd met
   wat er in de repo staat, niet met wat er plausibel lijkt.

**Twee hefbomen van Bert.** Beide woorden werken zonder discussie, uitleg of verdediging:

- **"protocol"** — de beurt wordt overgedaan volgens deze interactieregels.
- **"waarop rust dit?"** — het vorige antwoord wordt per bewering uitgesplitst naar bron.

⚠ **Deze regel heeft geen technische bouwsteen** (zie KERNLES LI038): chatgedrag is niet machinaal
af te dwingen. De borging zit in de vorm — een bron ín de zin valt op zodra hij ontbreekt — en in de
twee hefbomen, die de controle bij Bert leggen. Zwakker dan een scan; het is wat hier mogelijk is.

**Spanning met punt 4 ("kort en bondig"), bewust aanvaard:** een bron per bewering kost woorden. De
regel compenseert zichzelf deels — een bewering zonder invulbare bron vervalt.

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
- **Een letterlijke trigger is geen ontheffing van de groene staat.** CC verifieert vóór élke commit
  zélf de suites én de werktree, en **weigert te committen op een rode/incomplete werktree** — óók bij
  een letterlijke `AKKOORD: commit`; dan melden waarom + opties (incident-les CD051, voluit in
  CLAUDE.md §Triggerdiscipline).
- claude.ai scheidt dit strikt in alle formuleringen.
- `AKKOORD: commit` wordt **uitsluitend door Bert, rechtstreeks in CC** gegeven — **nooit**
  door claude.ai in een opdracht-`.md` geschreven (een `.md` bevat alleen `START:`-instructies).
  Zo commit CC nooit op bestandsinhoud.
- **Doc/checkpoint krijgt een eigen commit-akkoord (W5, LI044).** Een checkpoint/doc lift niet mee met
  bouwwerk — het krijgt zijn eigen `AKKOORD: commit`. **Uitzondering:** een **ADR en het read-only
  checkpoint dat hem grondt** landen in **één** commit; de ADR verwijst ernaar met `Grond:`. (LI044:
  ADR-052 + `docs/Checkpoint-…-V044.md` samen gecommit, de ADR draagt `| Grond | … |`.)
- **OPVOLGPUNTEN.md is een NORMAAL TRACKED projectbestand** (besluit DC011 — geverifieerd `git ls-files`,
  niet in `.gitignore`). Behandel het als elk ander tracked bestand. De achterhaalde aanname
  "OPVOLGPUNTEN is untracked tijdens de sessie en landt pas bij close" geldt **niet** meer — niet
  herintroduceren. Bij een feature-commit hoort een OPVOLGPUNTEN-wijziging er niet stil in mee te liften:
  gebruik **gerichte staging** (`git add <expliciete feature-paden>` + `git diff --cached --stat` als
  bewijs); de afsluit-/parkeer-updates van OPVOLGPUNTEN landen in de **sessie-afsluit-commit**. (V010 Fase F, geverifieerd)

### Stapelen in één werktree — alléén bij samenhangend, samen-committend werk (ADR-040)

Uitzondering op "één opdracht per werktree": een stap mag **ongecommit blijven terwijl een volgende
erop bouwt**, mits ze aantoonbaar **één geheel** zijn (samen ontworpen, samen te committen) en er een
**stash als vangnet** is. Anders: eerst committen. (Deze sessie: een backend-slice bleef ongecommit
tot de layout-fix die hij onthulde — ze landden samen in één commit.)

### Verstrengelde werktree ontwarren — precedent + waarom (LI046)

Raken twee slices tóch verstrengeld in **één bestand** (LI046: `LandschapskaartView.vue` = linkerkolom
+ banen), volg CONTRIBUTING.md sectie 7 (niet hier dupliceren): **hunk-niveau splitsen** met
`git apply --cached` van een slice-only patch (`sed -n '…p' full.patch` → `--check` → `--cached`), per
commit een **`git diff --cached --stat` + grep-bewijs** dat niets van de andere slice meelift, en een
**groene suite** tussendoor. **Waaróm:** een commit moet bevatten **wat er getest is**, niet meer —
anders lift ongetest/ongerelateerd werk mee de historie in. (LI046: `3a72b35` kolom · `6651f1f` banen ·
`f7929a9` docs — drie schone commits uit één werktree; Bert koos de splitsing expliciet.)

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
- **LI046-bewijs + waar-sta-je-eerst.** Twee shells die in **dezelfde** worktree schreven leverden een
  feiten-tegenspraak op: een verificatierapport zag "ongecommit" wat een andere shell intussen al had
  **gecommit** (HEAD was verschoven). Regel bevestigd — **één shell schrijft per repo**; en bij twijfel
  over de stand eerst read-only **vaststellen waar je staat** (`git branch --show-current`/`log -1`/
  `cat-file -e <hash>` → branch · HEAD · aanwezige commits · behind-remote) **vóór** je iets schrijft of
  een "ongecommit"-bevinding opschrijft. Een achterlopende shell laat de bevinding vervallen, niet de
  werkelijkheid.

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
- De bouwopdracht-`.md` markeert expliciet gate of doorloop. (V009/V010, geverifieerd)
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
- **Read-only meting in het gate-rapport (borging)**: bij een afgeleide read-API meet je de **feitelijke
  dev-stand** (welke componenten welk signaal, met waarom) via een klein script onder `_run_rls`, en zet
  je die in het gate-rapport zodat Bert de regel op echte data toetst (F-3: 8× `beoordeeld_niet_vastgelegd`). (V010 Fase F, geverifieerd)

### Sneden die dezelfde functie ontsluiten, beoordeel je op ÉÉN beeld (LI047)

Wordt een functie in meerdere sneden gebouwd, dan is er **één beoordelingsmoment waarop ze samen op
het scherm staan** — anders keur je twee keer iets goed dat sámen niet klopt. Geen enkele test vangt
dit: beide sneden zijn op zichzelf correct.

(LI047: "Open punten" kreeg in snede 1 een tabblad en in snede 2 een kopknop. Beide afzonderlijk
akkoord bevonden; sámen stonden ze naast elkaar naar dezelfde plek te wijzen, allebei actief. De
correctie was goedkoop — maar alleen omdat het vóór productie opviel.)

### Read-only-eerst boven aannames (ADR-040)

Bij elke diagnose **spreekt de code, niet de hypothese**. Een PNA-/instructie-aanname (ook een
"besloten" diagnose) is **richting, geen waarheid**. CC verifieert de aanname tegen de code (grep,
lezen, een read-only reproductie) en **stopt-en-rapporteert bij discrepantie** — schrijf géén fix
voor een filter/symbool/bug die niet blijkt te bestaan. (Deze sessie: een "verweesde-org-opruimfilter"
dat er niet was; een scope-bug die scenario-afhankelijk bleek, geen defect.)

**LI046 — de code wint óók van de OPDRACHT/mockup, niet alleen van een diagnose.** Twee keer weersprak
de codebase een aanname ín een opdracht, en beide keren was stoppen-en-voorleggen juist: (1) het
"detailpaneel resolvet op één ring"-vermoeden — wél waar, maar de premisse eromheen niet; (2) de
mockup-premisse "contract + beheerrol liggen als lijnen tússen twee systemen" — de code tekent contract
naar een **contractknoop** en beheerrol vanaf een **partij**, niet tussen de twee systemen. Toets een
mockup/aanname **tegen het model vóór de bouw**; stoppen is geen vertraging maar de **goedkoopste
correctie** (bouwen op een verkeerde premisse levert een feature die niet doet wat de mockup belooft).

- **Read-only-eerst, tweemaal herbewezen (aanvulling op §Read-only-eerst).** Een hypothese
  van de PNA is richting, geen bouwopdracht — LI039 leverde er twee die bij validatie
  ANDERS bleken: de dubbele-melding-oorzaak (geen leeg aanbod maar een 500 door een
  model↔schema-mismatch) en "de dev-seed vult het aanbod" (het is `platform_init` +
  migratie 0061). Beide keren was de fix een andere dan de hypothese suggereerde.

### Meet tenant-data BINNEN de tenant-context (LI047)

Een meting als `lk_admin` ziet **álle** tenants; RLS bepaalt wat de applicatie ziet. Meet daarom met
de app-rol binnen de tenant-context, en zeg **welke tenant** je gemeten hebt.

**En een rapport is geen meting.** Een checkpoint draagt de stand van zijn **eigen commit**; citeer je
het als huidige stand, dan presenteer je een momentopname als feit.

Deze fout trad in LI047 **drie keer** op, telkens in een andere vorm: (1) een checkpoint van vóór een
reseed geciteerd als verse meting ("component_norm = 0 rijen" — het waren er 10); (2) als `lk_admin`
gemeten dat er één `nee`-checklistscore was, terwijl de dev-tenant er nul had (die score zat in een
andere tenant); (3) "nul nee/deels-scores, de gebundelde regel is niet te bekijken" als vaststaand
gerapporteerd, terwijl een verse seed er wél één levert — het was **drift**, geen ontbrekende data.
**Regel: hermeten, of de commit erbij noemen.** Tellingen in gate-rapporten zijn momentopnamen.

**LI048 — een inventarisatie is een meting, geen indruk.**

**Het incident.** Een READ-ONLY checkpoint moest vaststellen welke lijstschermen al "zoek + filter
+ knop" hadden. De detectie zocht naar zoek-achtige tekst in de bron en pikte op het Auditlog-scherm
`placeholder="Zoek een component…"` op — de placeholder van een ZoekSelect *filterveld*. Conclusie
in de tabel: "Auditlog heeft een zoekveld ✅". Bij het bouwen bleek: `type="search"` = 0,
aanmaakknop = 0, `FilterResultaatRegel` = 0. Het scherm was geen beheerslijst maar een
**doorzoekscherm** — een andere soort, die de hele opdracht anders maakt.

**De fout is niet de regex.** Het is dat een bron is gelezen zonder te toetsen of hij beschrijft
wat hij lijkt te beschrijven. Dezelfde soort fout als bij "Oracle FIN-DB": een naam die klinkt als
het ding, aangezien voor het ding. Een placeholder is *tekst in een veld*, geen bewijs dat het veld
een zoekveld ís.

**Regels die hieruit volgen:**
- **Tel het ding zelf, niet iets wat erop lijkt.** "Heeft dit scherm een zoekveld?" meet je met
  `type="search"`, niet met het woord "zoek". Kies per vraag het kenmerk dat alleen waar kan zijn
  als het antwoord ja is.
- **Een checkpointtabel is een meting met een teller per cel** — geen ✅/❌ zonder getal. Een 0 die
  als ✅ leest valt op zodra er een getal naast staat.
- **Wijkt de code van je eigen eerdere rapport af: het rapport is fout, niet de code.** Meld het
  expliciet en corrigeer de vindplaats, anders bouwt de volgende sessie op de foute tabel. Staat
  het rapport alleen in de chat en niet als `.md`, leg de correctie dan vast waar hij wél
  teruggevonden wordt (OPVOLGPUNTEN of de betrokken skill) — een correctie in chat is geen
  correctie.

- **Reproduceerbaarheid van externe bronnen (LI040):** van elk ingelezen referentiemodel liggen
  commit-hash (gepind) + SHA-256 vast in `HERKOMST.md` — voluit in likara-domeinmodel
  §"LI039/ADR-044 — plaatsing als eerste-klas feit".

### Een typegebonden beperking zónder ADR is vaak een restant (ADR-055/LI047)

Tref je een beperking aan (`if type != X: weiger`), zoek dan eerst de **herkomst** vóór je hem als
domeinregel behandelt: staat er een ADR, een besluit, een toelichting? Staat er niets, kijk dan naar
het **schema** — ligt de beperking daar niet vast, dan leeft ze alleen in de applicatielaag en is ze
waarschijnlijk meegekomen uit een structuur die niet meer bestaat.

**Zoek ook het precedent.** (LI047: de gebruikersgroep-beperking bleek een overblijfsel van de
opgeheven applicatie-subtabel — twaalf ADR's noemden gebruikersgroepen, geen enkele grondde de grens,
en alle vreemde sleutels wezen al naar generieke doelen. ADR-041 had dezelfde herziening één laag
hoger al gedaan, met exact dezelfde vaststelling: *"de onderliggende structuur bleek al
component-breed"*. Zonder dat precedent was het een domeinvraag geweest; mét precedent was het een
afmaakklus.)

### Een bewijs over de GEWIJZIGDE bestanden zegt niets over WIE ZE GEBRUIKT (LI047)

Bij een hernoeming of contractwijziging is "ik heb bewezen dat de gewijzigde bestanden alleen van
naam veranderden" **valse zekerheid** — het bewijs is inhoudelijk correct en toch te smal.

**Bewijs (twee keer op één dag, beide gemist door 1176 groene tests):** een AST-vergelijking toonde
aan dat de drie hernoemde bestanden semantisch identiek bleven; de **aanroepers** stonden buiten de
sweep, in de platform-backend terwijl de sweep in de module keek — de dev-seed crashte en het
demolandschap was niet meer op te bouwen. En dezelfde blindheid liet een tweede scherm dezelfde
gebeurtenis anders benoemen (e-mailadres i.p.v. de ge-resolveerde naam).

**Regel:** toets na een hernoeming/contractwijziging **alle aanroepers, repo-breed** — niet binnen
één module, want juist die grens is waar het misgaat. Waar het zich leent: leg het vast in een scan
die zijn doelen **afleidt** (referentie: `test_schema_aanroepen_scan.py` — élke aanroep van een
`extra="forbid"`-schema tegen de schemavelden; een nieuw schema doet vanzelf mee).

### Reikwijdte-scan vóór een klasse-fix (LI037)

Een fout die een **klasse** kan zijn (een niet-idempotente seed-stap, te-ruime rol-gating, een
gedupliceerd patroon) wordt eerst read-only **breed geïnventariseerd** — waar zit hetzelfde
patroon nog? — vóór de fix wordt afgebakend. Niet één plek dichten en de rest laten staan; de
scan bepaalt de reikwijdte, Bert beslist over de afbakening. (LI037: seed-idempotentie en
verwijder-gating beide zo aangepakt — de gating-scan vond zes plekken i.p.v. één, én
falsifieerde een vermeende zevende.)

- **Telling vóór besluit — "denkbaar is niet geteld" (aanscherping op §Reikwijdte-scan).**
  Een ontwerpbesluit over een verschijnsel begint met de meting ervan: ADR-044 (meervoudige
  ouders) is genomen op de GETELDE 7 gevallen uit de bron (Verkenning §B1), niet op "dat kan
  voorkomen". Wie niet telt, dimensioneert op fantasie. *(LI040 herbevestigd: 25/32 grof-only
  gebruiksfeiten besliste waar de uitstap-stand landt — ADR-046 besluit 4; en de vóór/ná-metingen
  van 0066/0067/0068 bevestigden "datakost nul" feitelijk i.p.v. aangenomen.)*
  (LI039, gevalideerd fase A: `docs/Validatie-patronen-LI039.md`.)

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
en de modulecache verwijderen** (de vite-cache: `find frontend/node_modules/.vite -type f -delete`
+ `find frontend/node_modules/.vite -depth -type d -delete`, dán `npm run dev` opnieuw — **`rm`
staat in de CC-deny-lijst**, dus `find … -delete`, zie de LI010-note), gevolgd
door een harde refresh. Les LI046: een dagenlang draaiende Vite-server serveerde stale modules;
de browser toonde oud gedrag terwijl de suite terecht groen was — de bevinding leek een codebug
en was er (deels) geen. Zonder stap 0 is een browserbevinding niet interpreteerbaar.

**Een bestandsoperatie doet niet wat hij leest — toon eerst, verifieer daarna (LI046/LI047).**
Vier instrumenten, dezelfde faalfamilie:
- een **glob die breder matcht dan hij oogt**: `?` en `*` zijn in `-name` wildcards, dus
  `V???.zip` matcht elk `V`+3-tekens, niet de string `V???`. In LI046 wiste
  `find -name "LIKARA_Sessiestart_V???.zip" -delete` **30** gitignored sessie-ZIPs i.p.v. de ene
  stray — `find -delete` omzeilt de prullenbak en gitignored betekent niet via git terug;
- een **verzameling paden in één shell-variabele**: woordsplitsing levert één argument
  (`for f in $BACKEND`, `git checkout HEAD -- $VUES`);
- **twee backups met dezelfde basename**: `schemas/gebruikersgroep.py` en
  `routes/gebruikersgroep.py` heten allebei `gebruikersgroep.py`, dus de tweede `cp` overschreef
  de eerste en het terugzetten beschadigde een bestand;
- een **knip op een ankerpunt** dat ná in plaats van vóór het doelblok staat, of een **regex** die
  buiten de bedoelde waarde om ook de inspringing platslaat.

**Regel:** schrijf paden **expliciet** uit (geen variabelen, geen patronen); toon een
verwijderpatroon **eerst met `-print`** en gebruik bij één doelbestand de **exacte naam**; leid een
backupnaam af van het **volledige pad**, nooit van de basename.

⚠ **De verificatie achteraf is de belangrijkere helft.** Van de zeven voorvallen in LI047 faalde er
**één luidruchtig**; de rest **stil** — en de suite bleef groen, omdat het geraakte bestand buiten de
getoetste paden viel. Het beschadigde schema-bestand werd alleen gevonden doordat het eigen resultaat
werd nagekeken. Sluit elke bestandsoperatie daarom af met een controle van de **stand**: `diff -q`,
`head -1`, `grep -c` — niet met de aanname dat het commando deed wat het leek te doen.
(`rm` staat in de CC-deny-lijst; `find … -delete` is de vervanging, en een veiligheidsregel zonder
zijn eigen valkuil is een halve regel.)

**Een draaiboekstap is een claim over de code — toets hem vóór je hem opschrijft (LI047).** Een stap
die verwijst naar een knop, veld of tabblad dat er niet is, kost de lezer een zoektocht en ondermijnt
het hele draaiboek. Verifieer elke genoemde route, elk testid en elke schermnaam tegen de code;
"logisch dat het daar staat" is geen verificatie. (LI047: een stap wees naar een uitleg-"i" naast
Eigenaar-organisatie; `ComponentDetail.vue` bevatte er geen enkele — dat feit leefde alleen in de
bewerk-overlay.)

Een **groene testrun betrapt geen kapotte UX**: mocks verbergen een verkeerde picker-bron, een
lege/onleesbare picker, voorvul-verdringing, een stale label, en een onnodige/foutgevoelige
account-aanroep. Bewezen deze sessie — drie keer bleef de suite groen terwijl het scherm in de
browser stuk was. Daarom: bij elke slice die **UX, keuzevelden (pickers), of auth/provisioning**
raakt, verifieert **Bert de betrokken schermen in de echte browser vóór `AKKOORD: commit`**. Het
gate-rapport levert daarvoor een **browsercheck-draaiboek** (per stap: handeling → verwacht
resultaat). Groene tests ≠ commit-toestemming.

**Twee eisen aan dat draaiboek, allebei vanuit de gebruiker (LI048):**

1. **Elke stap draagt óók een faalbeeld** — niet alleen "wat je moet zien", maar **waaraan je ziet
   dát het mis is**. Zonder faalbeeld moet de beoordelaar zelf bedenken wanneer iets fout is, en dan
   wordt "het ziet er goed uit" de uitkomst van elke twijfel. Het faalbeeld is bovendien de plek waar
   het defect wordt benoemd dat de slice oploste — daarmee weet de beoordelaar waar hij op let.
2. **De taal is die van het scherm, niet van de bouw.** Geen commando's, geen bestandsnamen, geen
   vindplaatsen, geen testids — schermnamen, knopteksten en menupaden. Wie het scherm beoordeelt
   hoeft de code niet te kennen; staat er een bestandsnaam in, dan is de stap voor de bouwer
   geschreven en niet voor de gebruiker.

**En meld wat het landschap NIET kan tonen.** Dekt de demodata een geval niet, zeg dat vóór de stap
in plaats van de beoordelaar te laten zoeken naar iets wat er niet is — of laat hem het geval zelf
aanmaken, met de handeling erbij. (LI048: het demolandschap bevatte geen partij met een los
toegekende rol, geen gebruiker mét gekoppelde persoon in het auditlog, en geen componentprofiel met
een nog bestaand component. Drie draaiboeken openen daarom met wat er ontbreekt.)

**LI041 = zevende bevestiging:** zeven bevindingen deze sessie, geen enkele zichtbaar in 1200+
groene tests. De regel is niet nieuw — dit is opnieuw bewijs dat de browsercheck het sluitpunt is.

**LI046 = drie gevallen met dezelfde gemene deler: de test bootst niet na wat de gebruiker doet.**
(a) de gebruikt-doorklik werd nergens als **keten** getest — alleen de twee helften apart, dus een
vergeten popup-tak viel niet op; (b) de "de bezoeker wint"-poort werd getest op een component **zonder**
checklistvragen — een situatie die in de praktijk niet bestaat, dus de aanleiding-wis-bug (die alléén op
componenten mét vragen optreedt) bleef groen; (c) een per-tak-regel stond in **twee van drie** takken,
maar de test oefende alleen de gezette takken. Elk geval: assert de **keten** en de **echte** gebruikers-
staat (mét de feiten die het randgeval dragen), niet de helft of het schone geval.

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

- **Browsercheck-bevindingen zijn patroon-signalen, geen punt-fixes.** De LI035-les: zes
  bevindingen (overlay gedrukt, omlijning geclipt, voetbalk scrolde mee, schaduw grijs,
  blokken versnipperd, succes stil) leidden elk tot patroon-onderzoek en werden zes
  systeembrede patronen (breedte-override-borging, Dialog-primitive-regels,
  scroll-schaduw, samengevoegd blok, succes-toast-standaard, MeldingBanner). Eerst de
  vraag "waar bestaat dit nog meer / wat is de regel?", dán pas de fix.
- **Browserverificatie-faalmodus: de stil niet-geresolvede component.** Een ontbrekende `import`
  van een Vue-component geeft GEEN fout — Vue rendert het element stil leeg, en de suite blijft
  groen (mocks zien het niet). Dit is de scherpste reden achter de bestaande browsercheck-regel
  (LI032) én de tests-regel "assert op zichtbare tekst" (likara-tests §Frontend-testpatroon, LI040).
- **Bedieningskennis hoort in de bedieningsdoc.** Wat een mens nodig heeft om te testen
  (platform-inlog, menupad) staat in `docs/LOKAAL-TESTEN.md` (de platform-login staat daar
  inmiddels, regel ~117-131) — niet alleen in een skill. *(LI040: een browsercheck-draaiboek liep
  vast op een platform-login die al bestónd maar alleen in skill-context leefde.)*

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
- **Maakt je slice een bestaande tekst of aanname ONWAAR, herstel dat in DEZELFDE commit (LI047).**
  Anders bevat de historie een commit die een onwaarheid introduceert en een tweede die hem weghaalt —
  en tussen die twee staat de fout in productiewaardige code. Dit is **strenger dan verergeren**: bij
  verergeren mag je afwegen (adoptie versus verbouwing, zie hieronder), bij onwaar-maken niet.
  (LI047: de melding `GROEP_ZONDER_APPLICATIE` sprak over "applicatie" en kon ná de verbreding op een
  fileshare verschijnen; de servicedocstring beschreef gedrag dat in dezelfde slice was veranderd.)
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

## Sessiecapaciteit en overdracht

- **Een volle CC-sessie levert stil kwaliteitsverlies.** Bij ~100% context: **verse sessie + een
  zelfstandige overdracht-`.md`** (zelfde vorm als elke opdracht: stand vaststellen read-only,
  suites bevestigen, dan wachten). Elke opdracht is zó geschreven dat opnieuw beginnen bijna
  niets kost — dat is een eigenschap van het opdrachtformaat, geen toeval. (LI040)

### Afsluiten is Berts besluit, nooit dat van Claude (LI050)

- **Claude vraagt ALTIJD of we de sessie afsluiten; Claude besluit dit NOOIT autonoom.** Ook niet
  bij een schone werktree, een groene suite of een afgerond spoor — dat zijn signalen, geen besluit.
- Claude mag het moment wél **aandragen**, in termen van risico en staat (ongecommitte slices,
  verstrengeling, te veel open sporen) — nooit in termen van de gesteldheid van de gebruiker.
- Zegt Bert ja, dan geldt het volledige afsluitprotocol; een verkorte variant kiest Claude nooit
  zelf.

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

De LI036-kaartregel — een set-actie muteert uitsluitend de set, nooit de weergave — staat
voluit in likara-ux §LI036-kaartpatronen (herziening ADR-040; in de ADR zelf al verankerd).

## Keuze-sortering vóór je iets onthoudt (LI034, pointer)

Vóór je een keuze onthoudt: sorteer 'm — **platformvormend → centraal beheer; persoonlijke werkstijl →
voorkeur-laag; momentkeuze → inline/vers**. Detail (vaste bril vs. momentkeuze, "onthoud als mijn
standaard") in **likara-ux**.

