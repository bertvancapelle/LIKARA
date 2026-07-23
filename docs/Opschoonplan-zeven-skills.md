# Opschoonplan — de zeven resterende skills (LI050, spoor 1)

**Vastgelegd:** LI049 (2026-07-22, HEAD `5c4879a`) · **Besluit Bert:** LI050 begint met de
complete opschoning van de zeven resterende skills, zodat het geheel schoon staat vóór er
verder gebouwd wordt.
**Canonieke meting:** `docs/Checkpoint-resterende-opschoning-negen-skills-V049.md` — alle
getallen hieronder komen dáárvandaan; wijkt de werkelijkheid bij aanvang LI050 af, dan wint een
verse hermeting (een rapport is geen meting — werkprotocol §Meet tenant-data).
**Het bewezen recept:** de tests-consolidatie van LI049 (`201092d` → `558f39d` → `87ab572`).

---

## Deel 1 — de kaart

**7 van de 9 skills dragen de chronologie-kwaal: 82 chronologische koppen, 2.539 regels beslag
= 37% van alle 6.805 skill-regels.** Gerangschikt op ernst:

| # | Skill | Chronologische ##-koppen | Regelbeslag | % van skill |
|---|---|---:|---:|---:|
| 1 | **backend** | 17 | 473 | **66%** |
| 2 | **db** | 11 | 266 | **54%** |
| 3 | **ux** | 14 | 554 | **51%** |
| 4 | **frontend** | 23 | 799 | **43%** |
| 5 | **security** | 5 | 109 | **33%** |
| 6 | **domeinmodel** | 11 | 316 | **31%** |
| 7 | **resilience** | 1 | 22 | **15%** |

`werkprotocol` en `tests` staan op **0 chronologische koppen** — de LI049-consolidatie is
beklijfd; dat is tegelijk het bewijs dat het recept werkt.

Nuance uit de meting: een deel van de 82 is geen grabbelzak maar één-onderwerp-met-sessieprefix
(daar is hernoemen het werk, niet uiteenrafelen); de verhouding per skill stelt het per-skill-
checkpoint vast, zoals destijds bij tests.

---

## Deel 2 — de eerste beslissing van LI050, vóór skill 1: borging

De kopverwijzingen-scan borgt dat verwijzingen ergens op landen; **de kop-vorm zelf (onderwerp
i.p.v. sessiekop) ligt principieel buiten zijn bereik** (checkpoint blok 4.2). Vóór de eerste
verhuizing beslist Bert:

- **Wél borgen** — een nieuwe controle (bv. een kop-vorm-check in de bestaande scan-familie:
  géén `##`-kop die met `LI0xx`/`V0xx` begint, met zelftest en de gebruikelijke
  uitschakelvoorwaarde). Consequentie: eenmalig bouwwerk aan het begin, maar de opschoning
  beklijft structureel — een nieuwe sessiekop wordt rood in plaats van gewoonte.
- **Niet borgen** — sneller starten; tekstdiscipline moet het houden. Consequentie: de kwaal
  kan over tien sessies terugkeren, precies zoals hij nu in zeven skills terugkwam terwijl de
  regel ("consolideer eerst") twee keer opgeschreven stond.

Dit besluit gaat vooraf omdat het de gate-rapporten van álle zeven blokken raakt (mét borging
draagt elk blok het bewijs "scan blijft groen én kop-check blijft groen").

---

## Deel 3 — het recept per skill (bewezen bij tests, LI049)

Elke skill doorloopt dezelfde vier stappen; geen stap overslaan, geen twee stappen vermengen:

1. **Read-only checkpoint** — koppen meten (aantal, beslag, grabbelzak vs.
   één-onderwerp-met-prefix), per alinea de thuiskop bepalen (bestaand of nieuw benoemd),
   verwijzingen repo-breed in kaart (scan-bewaakt vs. onbewaakt handwerk), dubbelingen en
   kop-naam-collisions signaleren, markers-zonder-eigen-herkomst tellen,
   `(geverifieerd)`-bundelkwalificaties noteren. Eindigt met STOP + rapport.
2. **Verbatim verhuizing** — chronologische koppen → onderwerpskoppen; "eruit = erin",
   machinaal geborgd (multiset-bewijs); markers en bundelkwalificaties reizen mee per alinea;
   één-onderwerp-secties worden hernoemd (onderwerpsnaam + sessiemarker als suffix);
   kop-genoemde verwijzingen bewegen mee (de scan vangt ze — bewezen bij domeinmodel:996 en de
   vier `§LI039`-coderefs); onbewaakte verwijzers met de hand, gelijst in het rapport.
3. **Dubbelingen als apart besluit** — nooit meeliften met de verhuizing. Per geval de
   functionele beslisregel: *waar zoekt iemand deze regel als hij hem nodig heeft?* Daar staat
   hij voluit; de andere plek wordt één scan-bewaakte verwijzing. Aanvullend ≠ tegenstrijdig:
   bij inhoudsverschil stoppen en voorleggen; samenvoegen is herformuleren en dus per geval
   Berts besluit.
4. **Gate-rapport + eigen commit** — bewijsregels: gewijzigde bestanden benoemd · regeltelling
   eruit = erin (+ markers apart) · koppen vóór/ná · alembic gelijk · suites gelijk · scan
   groen. Checkpoint-rapport en bouwwerk in gescheiden commits; `AKKOORD: commit` per blok.

---

## Deel 4 — de sessie-indeling

### Veilig (aanbevolen): vijf blokken

| Blok | Skills | Waarom deze knip |
|---|---|---|
| 1 | **backend** | zwaarst (66%) + draagt de dode verwijzing; eerste, schone testcase van het recept op een grote skill |
| 2 | **db** | tweede in ernst (54%); inhoudelijk verwant aan backend maar eigen werktree |
| 3 | **frontend** | grootste bestand (1.860 regels, 23 koppen) — verdient onverdeelde aandacht |
| 4 | **ux + domeinmodel** | samen: hun dubbelingen zijn onderling verweven (KIJKFILTER-regel, applicatie-centrisch ×3) — die knopen zijn alleen in één blik te ontwarren |
| 5 | **security + resilience** | samen: de twee lichtste (5+1 koppen, 131 regels) |

Elke blokgrens is een **schoon pauzepunt**: werktree leeg, commit geland, push bevestigd. Bert
beslist per pauzepunt of LI050 doorgaat of dat een verse sessie het volgende blok neemt —
Claude sluit nooit autonoom en signaleert in risico-/borgingstermen (CLAUDE.md §Sessiebewaking).

### Tempo: drie blokken

backend+db · frontend · ux+domeinmodel+security+resilience. **Bovengrens-optimisme**: alleen
haalbaar als de per-skill-checkpoints weinig cross-skill-verwevenheid tonen — pas te bevestigen
ná stap 1 van elk blok, niet vooraf te beloven.

### De capaciteitsgrens, expliciet

"De zeven in één sessie" loopt tegen de sessiecapaciteit-grens aan: **een volle CC-sessie
levert stil kwaliteitsverlies** (LI040-les, nu werkprotocol §Sessiecapaciteit en overdracht —
verse sessie + zelfstandige overdracht; elke opdracht is zó geschreven dat opnieuw beginnen
bijna niets kost). De vijf-blokken-indeling bestaat júíst om na elk blok te kunnen stoppen
zonder iets half achter te laten.

---

## Deel 5 — meegewogen aandachtspunten (uit de meting)

- **Dode verwijzing** `schemas/applicatie.py` — likara-backend **r151 + r342**; het bestand is
  met LI059 opgeheven, de helpers leven vermoedelijk in `schemas/_validators.py` (bij de
  reparatie éérst verifiëren, dan pas wijzen). Repareren **binnen het backend-blok**.
- **Kop-naam-collisions (5)** — backend "V016-patronen" ×2 (r370/r486) · frontend "LI034 —" ×2
  (r1420/r1436) en "LI046-patronen" ×2 (r1777/r1824) · ux "LI023 —" ×2 (r478/r521) en
  "LI046 —" ×2 (r1021/r1053). Ze maken `§`-verwijzingen ambigu (de scan kan twee gelijknamige
  koppen niet onderscheiden); oplossen **binnen het betreffende blok** — de consolidatie heft
  ze bijna vanzelf op omdat de koppen onderwerpsnamen krijgen.
- **Cross-skill-dubbelingen om in de blokken mee te nemen** (elk als apart stap-3-besluit):
  het **vitest-testrecept** frontend §Testopzet ↔ tests §Frontend-testpatroon (echte dubbeling,
  deels woordelijk — hoort bij blok 3) · de **KIJKFILTER-regel** domeinmodel ↔ ux (echte
  dubbeling met accentverschil — hoort bij blok 4) · twee grensgevallen (applicatie-centrisch
  ×3; beginschermOpen ux↔frontend) — per geval meten of het bewuste verdeling of drift is.
- **Frontmatters** — alle 9 verouderd (db zelfs V015, 34 builds); elke skill-aanraking bumpt de
  eigen frontmatter; de rest gaat mee in de LI049-afsluiting.
- **Volgordenuance** — begin bij backend (hoogste percentage + de dode verwijzing), **tenzij**
  het eerstvolgende bouwpunt van LI050+ een andere skill zwaarder raakt; dan mag die skill naar
  voren, met de reden in het gate-rapport.

---

## Deel 6 — expliciete niet-doelen

- **Geen inhoud herschrijven** behalve waar een dubbeling-besluit dat vraagt — en dan is het
  Berts keuze per geval, met benoemd behoud (dekking, reden, herkomst).
- **De opschoning verandert de vindbaarheid, niet de betekenis** van enige regel — "eruit =
  erin" is per blok het telbare bewijs.
- **Geen bouwwerk vermengen met de opschoning** — één spoor per werktree; een bouwbehoefte die
  tijdens een blok opduikt wordt een eigen `START:` ná het pauzepunt.

---

## Deel 7 — Hygiëneborging: hoe het schoon blíjft

Opschonen zonder borging betekent dat de kwaal over tien sessies terugkeert — zoals hij nu in
zeven skills terugkwam terwijl de regel "consolideer eerst" twee keer opgeschreven stond.

### De diagnose — waarom de vorige hygiënebewaker faalde (en het ontwerp verklaart)

1. **Hij lag bij claude.ai, niet in het protocol.** De bewaking hing aan een terugkerende vraag
   die Bert stelde en claude.ai uitvoerde — maar claude.ai is elke sessie een verse instantie
   zonder geheugen aan de vorige. Een bewaker die continuïteit vereist, mag daar niet liggen.
2. **Hij optimaliseerde op toevoegen, niet op ordenen.** "Leg vast wat we niet mogen missen"
   maakt de skills voller, niet schoner; er was geen opruim-vraag ("stond dit er al?", "hoort
   dit onder een onderwerp of een sessienummer?").
3. **Hij valideerde tegen een onbetrouwbare bron.** "Valideer tegen de skills" bevestigt de
   vervuiling zolang de skills zélf de wanorde zijn. In LI048 werden 18 patronen "gevalideerd"
   waarvan er 10 al bestonden — de dubbeling was niet te vínden. *(Herkomst van dit getal: de
   LI048/LI049-grond; het is in de LI049-checkpoints niet apart hermeten.)*
4. **Er was geen verplicht meetmoment.** De vervuiling ontstond sluipend — geen enkele sessie
   voegde genoeg toe om "groot genoeg" te voelen voor een controle; het resultaat is gemeten:
   82 chronologische koppen, 37% van alle skill-regels. Een check die alleen draait "als er
   reden toe is", mist per definitie de sluipende vervuiling — die geeft nooit een reden.

De borging repareert alle vier, op drie plekken, in aflopende kracht.

### Verankering 1 — de onvoorwaardelijke afsluit-hygiënecheck (de kern)

Het afsluitprotocol krijgt een **verplichte, machinale hygiënecheck** die **bij elke afsluiting
draait** — of er nu iets gewijzigd is of niet — en die **de afsluiting blokkeert bij rood**:

- **Onvoorwaardelijk**: geen gevolg van "gaan we iets aanpassen?" maar de meting die bepaalt óf
  er iets moet gebeuren — de directe reparatie van faalpunt 4;
- **Machinaal**: de kopverwijzingen-scan (bestaat) + de kop-vorm-scan (verankering 3, LI050) +
  een telling of er chronologische koppen of nieuwe dubbelingen zijn bijgekomen;
- **Blokkerend**: rood → de afsluiting stopt tot het schoon is. Geen groen, geen afsluiting;
- Dit **vervangt/versterkt de bestaande skill-review-stap**: van "review de skills" (menselijk,
  optioneel voelend) naar "meet de skills, onvoorwaardelijk, en blokkeer bij rood".

### Verankering 2 — het vier-staps skill-wijzigingsprotocol (het voorwaardelijke deel)

Draait **alleen als** de hygiënecheck of het sessiewerk uitwijst dat er iets de skills in moet.
Vaste volgorde, geen stap overslaan:

1. **Bepalen (claude.ai)** — welke les hoort structureel vastgelegd, en onder welk **onderwerp**
   (nooit onder een sessienummer). Weging, geen inventarisatie; *"geen enkele skill hoeft
   aangepast" is een geldige, zelfs gebruikelijke uitkomst* — de reparatie van faalpunt 2.
2. **Valideren tegen de eigen skills (claude.ai)** — klopt de voorgestelde wijziging met
   UX-first, de domeinregels en de borgingsprincipes.
3. **CC-validatie tegen de repo (read-only, vóór enige schrijfopdracht)** — staat het er al?
   botst het met een kop? hoort het onder een ander onderwerp? **Én: is de
   kopverwijzingen-scan groen** — anders valideer je tegen mogelijke wanorde (faalpunt 3).
   Pas bij groen mag stap 4.
4. **Schrijfopdracht aan CC** — de `.md` die de wijziging wegschrijft. Nooit vóór stap 3 groen
   is.

Kernregel: **"bepalen" en "wegschrijven" zijn gescheiden stappen met een verplichte read-only
validatie ertussen** — de vervuiling ontstond doordat ze één handeling waren.

### Verankering 3 — de twee sessiestart-regels + de kop-vorm-scan

- **Sessiestart-regels** (gelezen door elke verse instantie, niet uit geheugen — de reparatie
  van faalpunt 1): (a) validatie tegen de skills is pas betrouwbaar nadat de
  kopverwijzingen-scan groen is; (b) een patroon dat je meent te herkennen zoek je eerst op
  voordat je het als nieuw behandelt.
- **De kop-vorm-scan** (machinaal): een nieuwe controle die rood wordt zodra een `##`-kop een
  sessie- of versieprefix draagt (`LI0xx`/`V0xx` — hetzelfde criterium als de meting), met
  zelftest en de gebruikelijke uitschakelvoorwaarde. Dit maakt de chronologie-kwaal
  **structureel onmogelijk** in plaats van afhankelijk van discipline. **Dit is de eerste
  bouwstap van LI050, vóór skill 1** — de opschoning heeft geen zin als de kwaal daarna vrij
  terugkeert. *(Dit besluit valt samen met Deel 2: verankering 3 ís de "wél borgen"-route.)*

### De grens — de borging mag niet zelf het probleem worden

**De borging mag niet meer onderhoud vragen dan de wanorde die hij tegenhoudt** (Berts eigen
les). Concreet:

- de onvoorwaardelijke check levert bij een schone staat in seconden "groen" — geen ritueel dat
  elke afsluiting vertraagt;
- het wijzigingsprotocol draait alleen als er echt iets de skills in wil; "geen wijziging" is de
  normale uitkomst, geen falen;
- **niet meer dan deze drie verankeringen** — geen extra lagen erbovenop. Geeft een verankering
  twee sessies op rij vals alarm, dan geldt de bestaande uitschakelvoorwaarde-conventie.

---

*Dit plan is een vastlegging van het besluit en de route — de metingen erin verouderen; hermeet
per blok bij stap 1.*
