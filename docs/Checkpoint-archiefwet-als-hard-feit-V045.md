# Read-only checkpoint — kan "Archiefwet" landen als hard componentfeit?

**Sessie:** LI045 · **Build:** V045 · **Aard:** feitenopname, geen bouw · **Grond-commit:** `d661846`

> Voorgenomen vorm: **één hard componentfeit** met "Archiefwet" in het label, drie toestanden —
> **ja / bewust geen / nog niet naar gekeken** — normeerbaar in de tenant-norm zoals eigenaar en
> contract. Deze opname beslist of dat past op wat er staat, of nieuw bouwwerk vraagt.

---

## Kernuitkomst in één zin

**De naam-/norm-kant is goedkoop (de norm is sleutelgestuurd), maar het hart — een drie-toestand-antwoord
mét een positieve "ja" — past níét op het bestaande "bewust geen"-mechanisme; dat is relatie-verankerd
en tweeledig. Archiefwet wordt daarmee een nieuw eigen-veld-feit met eigen kolom, enum, migratie,
norm-tak en scherm-bedrading — géén meelifter — en het raakt vermoedelijk de meerderheid van het
landschap, niet een niche.**

---

## Blok 1 — Kan de norm een nieuwe feitsleutel dragen?

**Ja voor de opslag — de norm is sleutelgestuurd, niet kolomgestuurd.** De tabel `component_norm` bewaart
per rij `(tenant_id, feit_sleutel String(60), verplicht bool)`, `UNIQUE(tenant_id, feit_sleutel)`. De
kiesbare set is de code-constante `HARDE_FEITEN` (10 sleutels) in `component_norm_service.py`. Een elfde
sleutel `"archiefwet"` toevoegen is **één regel in die tuple** — geen schemawijziging aan de norm-tabel.

**Maar "verplicht kunnen stellen" ≠ "kunnen toetsen".** De toetsing `norm_status._status()` heeft
expliciete takken per feit-familie (signaal-feiten / relationele feiten via bevinding / hosting /
levensfase / bedoeling) met een sluit-tak `else: vast = True` (in de code gemarkeerd als "onbereikbaar").
Een nieuw feit dat niet in een bestaande tak valt, komt in die `else` terecht en zou **altijd als
'vastgesteld' lezen** — fout. Archiefwet vereist dus een **nieuwe tak** in `norm_status` (code), en een
bron van waarheid om die tak op te laten leunen (zie blok 2). Dat is het echte werk, niet de sleutel.

**Wat erven bestaande tenants?** De default-norm wordt per tenant geseed door `seed_component_norm`
(`ON CONFLICT (tenant_id, feit_sleutel) DO NOTHING`, draait bij onboarding/dev_seed). Een nieuwe sleutel
krijgt bij een **al geseede** tenant dus **geen rij**, en `haal_norm` leest een ontbrekende sleutel als
`.get(feit, False)` → **niet-verplicht**, ongeacht `DEFAULT_VERPLICHT`, tot er opnieuw geseed wordt (in
dev: reseed; de productie-onboarding-seed is overigens nog niet eens bedraad — zie
`Checkpoint-norm-beheerscherm-V045.md` blok 3). Netjes degraderend, maar het betekent dat "iedere tenant
erft archiefwet verplicht" **niet** vanzelf klopt.

**Hoort het standaard verplicht te zijn?** Die keuze komt nergens uit logica — `DEFAULT_VERPLICHT` is een
**met de hand gekozen `frozenset`** in de code (nu: eigenaar · verantwoordelijke · biv · contract ·
koppelingen). Archiefwet erbij zetten zou het platform-breed verplicht maken; een tenant die het niet
hanteert zet het in zijn eigen norm uit (W4: de tenant-wens versmalt de platform-default nooit — hier
gerespecteerd). **Ik stel alleen vast hoe de keuze tot stand komt; ik kies niets.**

---

## Blok 2 — Generaliseert "bewust geen"? (de scherpste vraag)

**Hard antwoord: nee, niet naar dit feit.** Het bestaande mechanisme is relatie-verankerd en tweeledig;
archiefwet is een eigen-veld-feit en drieledig. Dat is een wezenlijk andere zaak.

**Hoe "bewust geen" nu gebouwd is (koppelingen/contract):**
- `ComponentBevinding` (`component_bevinding`-tabel), `soort` = **enum** `ComponentBevindingSoort`
  (`koppelingen`, `contract`), één rij per `(component, soort)`. De rij betekent **alleen** "bewust geen —
  vastgesteld dat er geen is". Er is **geen "ja"-toestand** in de bevinding.
- De "ja"-kant komt **niet** uit de bevinding maar uit `heeft_echte_registratie` — **soort-specifiek
  hardcoded**: koppelingen = een `flow`-relatie op het component, contract = een `association` naar een
  contract. "Real wins": een echte registratie wint van (en verbiedt) een "bewust geen".
- Frontend `BewustGeenControl.vue` (gedeelde bouwsteen, 2 consumenten) is navenant een **twee-toestand-
  affordance**: ⊘ "bewust geen" óf "nog niet vastgesteld" — en toont **niets** zodra `heeftEcht` waar is
  (dan spreekt de lijst). De "ja" leeft dus in een **náást liggende lijst**, niet in het control.

**Waarom dat niet past op archiefwet:**
- "Bewust geen" werkt daar omdat **nul relaties dubbelzinnig** is (geen koppeling = niet gekeken, óf
  bewust geen?). Archiefwet werkt op een **eigen veld** — er is geen relatie en dus geen
  `heeft_echte_registratie` om de **"ja, hier leven archiefbescheiden"** te dragen. Die positieve
  toestand heeft in het huidige model **geen enkele plek** — niet in de bevinding-tabel (die kent alleen
  "geen"), niet in een náást liggende lijst (die bestaat niet voor archiefwet).
- Een derde `soort` in de bevinding-enum toevoegen is bovendien géén schema-vrije stap: een PostgreSQL-
  enum uitbreiden vergt een **migratie** (`ALTER TYPE`). En zelfs dan blijft "ja" onuitdrukbaar.

**Hoe "vastgesteld" zou meelopen — mits het als eigen veld wordt gebouwd.** De natuurlijke vorm is een
**nieuwe nullable enum-kolom op `component`** (spiegel van `levensfase`/`migratiepad`/`hostingmodel`):
waarden `{ja, bewust_geen}`, NULL = "nog niet naar gekeken". Dan is "vastgesteld" simpelweg
`kolom IS NOT NULL` — precies de bestaande levensfase/bedoeling-tak in `norm_status`, en een "bewust
geen"-antwoord (een non-null waarde) telt **vanzelf** als vastgesteld. Maar dat vergt: nieuwe kolom +
nieuwe enum + migratie + nieuwe `norm_status`-tak. Dat is nieuw bouwwerk, geen hergebruik van "bewust
geen".

---

## Blok 3 — Past het in het scherm zonder nieuw patroon

**Plek: ja, zonder eigen sectie.** De harde feiten staan op het componentdetail als leesregels in het
"wat is dit"-blok (bv. BIV als `dd` met `label || 'Niet geclassificeerd'`; levensfase/bedoeling/hosting
idem). Een nieuw eigen-veld-feit past daar als **nog een leesregel** — geen nieuwe sectie nodig.

**Gesloten antwoordset: bestaande vorm, maar géén één-bouwsteen om te hergebruiken.** BIV/hosting/
levensfase zijn gesloten enums die read-only als **label** getoond worden en in het bewerk-formulier via
een **native `<select>`** bewerkt worden (conform de likara-frontend-regel voor gesloten lijsten ≤10).
Er is **geen gedeelde "gesloten-feit"-bouwsteen** — elk feit is los bedraad (een `dd` in de leesweergave
+ een `<select>` in het formulier + een label-map). Archiefwet zou dus **dezelfde bewezen vorm** volgen,
maar als **eigen bedrading** (de zoveelste native-select-instantie) — het bestaande patroon, geen nieuw
patroon, maar ook geen gratis meelifter. De `BewustGeenControl`-bouwsteen is er wél, maar past (blok 2)
niet op een drie-toestand-eigen-veld.

**Registratiegat-signaal: niet automatisch.** Het per-component norm-badge (`MigratiegereedheidSectie`)
draagt archiefwet **pas** zodra `norm_status` een tak heeft die het bepaalt (de kolom uit blok 2). Het
aparte Signalering-scherm "registratiegaten" is een **vaste lijst** van signaaltypen (zonder-eigenaar,
BIV-onvolledig, …) — daar verschijnt archiefwet **niet** zonder eigen bouwwerk (en dat is vermoedelijk
ook niet nodig: het norm-badge is het relevante venster). Kortom: het gat-signaal volgt **niet** vanzelf
uit "genormeerd"; het volgt uit de nieuwe `norm_status`-tak.

---

## Blok 4 — Raakt het het uitstapverhaal

**Nee — de ADR-046-brokken dragen geen archief-dimensie, en de plek waar die zou moeten hangen is
gebruiker-, niet component-scoped.** `levensfase` en `migratiepad` zijn component-eigen nullable enums
(de eigen levensfase/bedoeling van het systeem). De **uitstap** is in ADR-046 besluit 3 bewust een
**feit van de gebruiker, niet van het systeem** (welke gemeente vertrekt + in welke tranche) — het leeft
op het organisatiegebruik, niet op het component. Er is dus **geen component-veld "uitstap-stand"** dat
een archief-dimensie zou kunnen mee-dragen.

Een archief-dimensie "dit systeem gaat uit én is bewaarplek" is een **component-feit** (naast levensfase/
bedoeling), orthogonaal op het gebruiker-scoped uitstapfeit. Het datamodel heeft plaats voor nóg een
component-enum, maar **niets vandaag legt de verbinding** tussen "gaat uit" (gebruiker) en "is
bewaarplek" (component); die ontmoeten elkaar alleen in het hoofd van de consultant. **Alleen
vaststellen — er ligt niets voorbereid, en er hoeft in deze opname niets voorbereid te worden.**

---

## Blok 5 — Meting op de dev-database

**19 componenten**, per type: **16 applicatie · 1 database** (Shared DB-server) **· 1 fileshare** (Shared
fileshare) **· 1 saas_dienst** (Extern SaaS-platform).

**Het componenttype/de laag onderscheidt "bewaarplek" niet** — er is geen veld dat het markeert, dus
mechanisch is de groep niet te tellen. Op naam/rol beoordeeld is de applicatie-laag echter gevuld met
**zaaksystemen en registers** die archiefbescheiden dragen: Zaaksysteem, Zaakafhandelcomponent, DMS,
Archiefbeheer, BRP, Burgerzaken-suite, Reisdocumenten, Aangiften, Verkiezingen, Sociaal domein suite,
Vergunningensysteem, Omgevingsloket — plus de database en de fileshare (klassieke bewaarplekken). Slechts
een handvol (Extern SaaS-platform, HR-systeem, Financieel systeem, Gegevensmakelaar) is twijfelachtig of
overhead.

**De verwachting "kleine groep" wordt hiermee gefalsifieerd, niet bevestigd.** Bewaarplek is in dit
landschap plausibel de **meerderheid** (ruim over de helft), niet een niche. Gevolg: een verplicht feit
"archiefwet" zou op de **meeste** componenten "nog niet naar gekeken" tonen — een groot open gat, geen
randverschijnsel. De drempel is dus **groter dan gedacht**, en dat hoort hier zwart-op-wit te staan.

---

## Blok 6 — Oordeel

**Past dit op wat er staat? Deels — en juist op het beslissende punt niet.** De goedkope helft klopt: de
norm is sleutelgestuurd, dus een label met "Archiefwet" als elfde feitsleutel kost geen schemawijziging
aan de norm-tabel, en op het scherm past het als leesregel zonder eigen sectie. Maar de dure helft — het
drie-toestand-antwoord (ja / bewust geen / niet gekeken) — **past niet op een bestaand mechanisme**:

- **Het "bewust geen"-mechanisme generaliseert niet** (blok 2, hard): het is relatie-verankerd en
  tweeledig, en de positieve "ja" heeft nergens een plek. Archiefwet wordt daarmee een **nieuw eigen-veld-
  feit**: nieuwe nullable component-enum-kolom + enum + **migratie** + nieuwe `norm_status`-tak. Middelzwaar,
  niet triviaal, en aantoonbaar géén hergebruik.
- **De schermbedrading is bestaand patroon maar nieuw werk**: dd-leesregel + native select + label-map +
  norm-badge-tak — de zoveelste instantie, niet één-regel-hergebruik.
- **Het gat-signaal volgt niet vanzelf** uit "genormeerd"; het hangt aan de nieuwe `norm_status`-tak.
- **Het uitstapverhaal draagt het niet** — orthogonaal, geen bestaand slot.
- **Het landschap is er niet klein voor**: bewaarplek is plausibel de meerderheid → een verplicht
  archiefwet-feit produceert meteen een groot open gat.

Netto: het is **bouwbaar en het botst met niets**, maar het is een **nieuw, op zichzelf staand eigen-veld-
feit met eigen kolom/enum/migratie/norm-tak/scherm** — niet een gratis meelifter op "bewust geen" of op
het uitstapwerk. "Kan waarschijnlijk wel" is dus de verkeerde samenvatting; de juiste is: *ja te bouwen,
als kleine zelfstandige feature, met de drie-toestand-opslag als het echte werk en een doelgroep die
groter is dan een niche.*

**Wat ik niet kon vaststellen:** of het beoogde antwoord echt binair is (`{ja, bewust_geen}`) of nuance
vraagt (bv. "gedeeltelijk"); of "bewaarplek" ooit uit componenttype afleidbaar zou moeten zijn (vandaag
niet); en de exacte labeltekst/wetstaal ("Archiefwet") — dat zijn ontwerpkeuzes voor de ADR, niet af te
lezen uit de code.

---

## Afsluiting

1. **Read-only — niets gewijzigd, niets gebouwd, niets gecommit.**
2. `git status` van deze worktree: alleen dit nieuwe document (plus het eerder onderhanden
   `Meting-gemma-…-V045.md`) is ongetrackt; verder schoon.
3. **Slice-4a-worktree onaangeraakt:** er is geen aparte slice-4a-bouwworktree (slice 4a stopte bij het
   pre-build-checkpoint, niets gebouwd). De enige worktree staat op de schone commit `d661846`; deze
   opname las tegen gecommitte grond.
