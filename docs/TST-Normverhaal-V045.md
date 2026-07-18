# TST — Het normverhaal in één doorloop (integrale test)

**Sessie:** LI045 · **Build:** V045 · **Grond-commit:** `f8a9142` · **Reikwijdte:** ADR-052 slices 1–3 + 4a + 4b + 4c samen.

> Dit is een **testronde**, geen bouwronde. Er is niets aan de code gewijzigd en niets gecommit. De
> getallen in dit draaiboek zijn **read-only geverifieerd** tegen de draaiende services (afwijking-
> classificatie, werkvoorraad, impact) op de geseede dev-database.

---

## 1. Poortenstand

| Poort | Resultaat |
|---|---|
| Backend | **1157 passed, 2 skipped** |
| Frontend | **1200 passed** (93 files) |
| `vite build` | **OK** |
| `test:css-build` | **OK** (76 views, 0 afwijkingen) |
| `alembic heads` / `branches` | **`0073` — 1 head, 0 branches** |

**Reseed-noot (belangrijk).** Een volledige reset (`docker compose down -v`) is in deze omgeving
**geweigerd**; ik kon alleen de idempotente `dev_seed` op de bestaande DB draaien (die zaait de norm en
de demostaat). De geverifieerde stand weerspiegelt het **werkelijke seed-gedrag** (zie bevinding S1),
dus de getallen kloppen — maar vóór de browserdoorloop hoort Bert wél een **schone** reseed te doen
(`down -v && up -d` + `python3 dev_seed_testdata.py`), zodat er geen oud residu meespeelt.

**Geseede norm (de lat):** verplicht = **eigenaar · verantwoordelijke · BIV · contract · koppelingen ·
bedoeling**; niet-verplicht = bedrijfsfunctie · gebruikersgroep · hosting · levensfase.
**Klaar verklaard (4):** Archiefbeheer, DMS, Klantportaal, Zaaksysteem.

---

## 2. Het draaiboek — vijf rollen die elkaar opvolgen

> Log in met de juiste rol per stap. Namen tussen «» zijn zoals ze in beeld staan.

### Stap 1 — De **beheerder** legt de lat

| # | Handeling | ✅ Verwacht |
|---|---|---|
| 1.1 | Open «Migratienorm» in het menu | Een lijst van tien feiten; **verplicht**: Eigenaar-organisatie, Verantwoordelijke, BIV-classificatie, Contract, Koppelingen, Bedoeling (migratiepad). De rest «Niet verplicht». Per feit een soort-tag («bewust geen» mogelijk vs. eigen veld). |
| 1.2 | Klik «Aanzetten» bij **Gebruikersgroep** | Een rustig venster (géén amber): *«Dit raakt **12** systemen die er nu niet aan voldoen — waarvan **1** eerder klaar is verklaard.»* + «Geen blokkade — je mag dit doen.» |
| 1.3 | Klik «Verplicht stellen» | Bevestiging; Gebruikersgroep staat nu op «Verplicht». |

**Kern-controle (tellen de getallen op?)** — de voorspelde **1** eerder-klaar-verklaarde moet straks
terugkomen als **1** in de werkvoorraad én **1** component met het signaal. (Geverifieerd: het enige
klaar-verklaarde component zonder gebruikersgroep is **Archiefbeheer**.)

### Stap 2 — De **medewerker** vult een component in

| # | Handeling | ✅ Verwacht |
|---|---|---|
| 2.1 | Open een component (Bewerken) → klik de **«i»** achter **Eigenaar-organisatie** | Onder de veld-uitleg, na een scheidingslijn: *«Dit feit telt mee om dit systeem klaar te kunnen verklaren. **Opslaan kan wel zonder.**»* Het hele paneel staat in beeld (ook onderaan het formulier). |
| 2.2 | Open de «i» bij **Hostingmodel** | **Geen** «telt mee»-passage (hosting staat niet op de lat) — alleen de gewone uitleg. |
| 2.3 | Open het componentdetail → tab **Gebruikersgroepen** → «i» naast de kop | De «telt mee»-passage staat er nu **wél** — het feit dat de beheerder zojuist aanzette (stap 1) is hier opgedoken. |
| 2.4 | Rol-controle | De medewerker kan «Migratienorm» **openen en lezen**, maar ziet daar **geen** «Aanzetten/Uitzetten»-knoppen (alleen de beheerder verzet de lat). |

### Stap 3 — De **medewerker** verklaart klaar

| # | Handeling | ✅ Verwacht |
|---|---|---|
| 3.1 | Open **Klantportaal** → blok «Migratiegereedheid» → «Klaar verklaren» | In het venster staat de lat: nog niet vastgestelde verplichte feiten (bij Klantportaal: **Bedoeling (migratiepad)**). Knop «Toch klaar verklaren» / «Eerst aanvullen». |
| 3.2 | Leesroute | In dat venster staat **«Bekijk de migratienorm →»** — hij komt zo bij de lat (leesbaar voor de medewerker). |
| 3.3 | «Eerst aanvullen» → vul **Bedoeling** in → klaar verklaren | Nu voldoet Klantportaal volledig → **geen** amber/neutraal norm-signaal (het «voldoet volledig»-geval). *(Zie bevinding S1: zónder Bedoeling in te vullen voldoet géén enkel component volledig.)* |
| 3.4 | Open een component dat een verplicht feit mist en verklaar het toch klaar | **Amber** regel: «Klaar verklaard, maar N verplichte feiten nog niet vastgesteld: …». Klik erop → het verantwoordingsvenster toont de bevroren stand (wat hij toen accepteerde) + reden. |

### Stap 4 — De **beheerder** verzet de lat opnieuw, ná die verklaringen (het scharnier)

| # | Handeling | ✅ Verwacht |
|---|---|---|
| 4.1 | Terug naar «Migratienorm» → dit is de stap waarin de al-eerder aangezette **Gebruikersgroep** (stap 1) zijn werk doet, ná de verklaringen | — |
| 4.2 | Open «Signalering» → tab «Registratiegaten» → sectie **«↔ De lat is verschoven»** | Een neutrale (gedempt-grijze, géén 🔴/🟡) sectie: **«Gebruikersgroep — 1 systeem: Archiefbeheer»** met «verplicht gesteld door {beheerder} · {datum}». |
| 4.3 | Open **Archiefbeheer** → blok «Migratiegereedheid» | **Neutraal** blok (géén amber): «Deze verklaring is destijds beoordeeld tegen de lat die toen gold. Sindsdien is **Gebruikersgroep** verplicht gesteld — daar is hier nog niet naar gekeken.» → **geen besluit toegeschreven dat de consultant niet nam**. |
| 4.4 | Op datzelfde Archiefbeheer | Daarnaast staat óók het **amber** blok (BIV-classificatie / Eigenaar-organisatie / Verantwoordelijke — die hij bij het verklaren **wél** bewust accepteerde). **Beide signalen naast elkaar**, elk in zijn eigen toon. |
| 4.5 | **Randgeval** — open een component dat **nooit** klaar is verklaard (bv. **Gegevensmakelaar**) | **Géén** enkel norm-signaal — ook niet ná de latwijziging. (Geverifieerd: bewust=[], verschoven=[].) |

### Stap 5 — De **beheerder** versoepelt de lat

| # | Handeling | ✅ Verwacht |
|---|---|---|
| 5.1 | «Migratienorm» → klik «Uitzetten» bij **Gebruikersgroep** | Venster: *«**1** openstaand signaal vervalt, en **N** systemen voldoen daardoor alsnog volledig.»* |
| 5.2 | «Niet meer verplicht» → terug naar «Signalering» | De regel «Gebruikersgroep — 1 systeem» is **weg** uit «De lat is verschoven». |
| 5.3 | Open **Archiefbeheer** opnieuw | Het neutrale «Gebruikersgroep»-blok is **weg**; er blijft **niets** achter dat naar een lat verwijst die niet meer geldt. (Het amber blok en de bedoeling-regel blijven — die horen bij de nog geldende lat.) |

---

## 3. Bevindingen (stap · verwacht · gezien)

### Blokkerend — **0**

### Storend — **1**

**S1 — Alle vier klaar-verklaarde componenten dragen out-of-the-box de «Bedoeling»-verschoven-lat; er
is geen «voldoet volledig»-component in de demostaat.**
- *Stap:* 3.3 / 4.2.
- *Verwacht (uit het 4a-gate-rapport):* Klantportaal = norm-compleet → geen signaal; DMS/Zaaksysteem =
  pure verschoven; Archiefbeheer = beide.
- *Gezien:* de werkvoorraad toont **«Bedoeling (migratiepad) — 4 systemen»** (Archiefbeheer, DMS,
  Klantportaal, Zaaksysteem). Oorzaak: de seed zet **bedoeling** (4a) verplicht, maar **`migratiepad`
  wordt op géén enkel component geseed** (vormkeuze B — LIKARA verzint geen bedoeling), dus élk klaar
  component mist bedoeling. Klantportaal is dáárdoor **niet** «geen signaal» maar toont de
  bedoeling-verschoven-lat. **Geen reseed-artefact** (de seed zet migratiepad niet — óók een schone
  reset laat het NULL). *Gevolg:* het «voldoet volledig»-geval (stap 3.3) is alleen te tonen als de
  consultant eerst zélf Bedoeling invult. De feature-logica is correct; de **demostaat** is minder scherp
  dan het 4a-rapport claimde. **Reparatie-optie (niet uitgevoerd, Berts keuze):** óf de seed zet
  bedoeling niet standaard verplicht, óf hij vult migratiepad op een component in zodat er een echt
  «geen signaal»-geval is.

### Cosmetisch — **2**

**C1 — De feit-naam op de norm/werkvoorraad/badge wijkt af van de sectiekop waar de aanduiding landt.**
- *Verwacht:* hetzelfde feit, overal dezelfde naam.
- *Gezien:* de feit-naam is **consistent** op het normscherm, de werkvoorraad én het component-badge
  (alle `NORM_FEIT_LABEL`), maar de **sectiekop** waar de «i» landt heet anders: Contract↔**Contracten**,
  Verantwoordelijke↔**Verantwoordelijkheden**, Gebruikersgroep↔**Gebruikersgroepen**, en het grootst:
  Bedrijfsfunctie↔**«Waarvoor gebruiken we het»**. Voor een consultant is «Contract» ↔ «Contracten»
  triviaal; «Bedrijfsfunctie» ↔ «Waarvoor gebruiken we het» is het opvallendst (maar bedrijfsfunctie
  staat niet op de default-lat).

**C2 — «Bedoeling» heet op het normscherm «Bedoeling (migratiepad)», op het formulier «Bedoeling».**
- *Gezien:* de norm/werkvoorraad tonen de sleutel-verduidelijking «(migratiepad)»; het invulveld niet.
  Triviaal, maar het is een verschil in dezelfde doorloop.

### Wat expliciet KLOPTE (kern van de test)

- **De getallen tellen op — geen tweede telling.** De werkvoorraadregel, het aantal componenten met het
  signaal en de «eerder klaar verklaard»-tak van de impactvoorspelling komen alle drie uit **dezelfde**
  afleiding: voor Gebruikersgroep zijn dat er **1** (Archiefbeheer); voor Bedoeling **4**. De brede
  impact-teller («12 systemen die niet voldoen») is een ánder, eerlijk getal (klaar + niet-klaar) — niet
  hetzelfde als de werkvoorraad (alleen klaar) en dus geen tegenspraak.
- **Het scharnier klopt** (stap 4): een ná de verklaring toegevoegd feit geeft het **neutrale** signaal,
  niet amber — er wordt geen besluit toegeschreven dat de consultant niet nam. Een bewust geaccepteerd
  feit blijft amber; op Archiefbeheer staan beide naast elkaar.
- **Randgeval klopt** (stap 4.5): een nooit-klaar-verklaard component draagt geen enkel norm-signaal, ook
  na een latwijziging.
- **Rol-gating klopt**: de medewerker leest de lat, verzet hem niet (geverifieerd in de code:
  `COMPONENT_NORM.WIJZIGEN` = beheerder; de knoppen zijn gegate op `hasRole('beheerder')`, de backend
  handhaaft).
- **De leesroute** vanuit het klaarverklaringsvenster naar de norm bestaat.

---

## 4. Oordeel — kan een gemeente hier in één doorloop mee werken?

**Ja.** Het normverhaal is over de vier slices heen **consistent**: dezelfde lat verschijnt op het
normscherm, het formulier, de sectiekoppen, de werkvoorraad en het component; de getallen tellen op
(geen tweede telling); en het beslissende punt — dat het systeem na een latwijziging geen keuze
toeschrijft die een mens niet maakte — houdt stand. Er is **geen blokkerende** bevinding. Wat de
doorloop nog niet strak maakt is de **demostaat** (S1: elk klaar-verklaard component draagt out-of-the-box
de Bedoeling-verschoven-lat, dus het «voldoet volledig»-geval moet de consultant zelf opwekken door
Bedoeling in te vullen) en twee **cosmetische** naamverschillen tussen de norm-woorden en de sectiekoppen.
Die raken de werking niet, alleen de scherpte van het verhaal — een gemeente kan er in één doorloop mee
werken zonder een tegenstrijdigheid tegen te komen.

---

## 5. Afsluiting

1. **Poortenstand:** backend 1157p/2s · frontend 1200p · vite OK · css OK · alembic `0073` (1 head, 0 branches). *(Boven herhaald.)*
2. **Bevindingen:** blokkerend **0** · storend **1** (S1 demostaat) · cosmetisch **2** (C1/C2 naamverschillen).
3. **Oordeel:** ja — in één doorloop werkbaar, mét de genoemde demostaat- en woord-kanttekeningen.
4. **Niets gewijzigd of gecommit.** Aan de code is niets veranderd; de enige mutatie is de **toegestane
   reseed** (`dev_seed`, die de norm/demostaat zaaide). Geen commit.

**Ik heb geen enkele bevinding gerepareerd.** Bert beslist of S1/C1/C2 eigen slices worden.
