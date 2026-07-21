# Browsercheck — zoeken op Auditlog vindt wat er staat (LI048)

**Build:** V048 · **Duur:** ~6 minuten · **Voor:** Bert
**Inloggen en menupad:** zie `docs/LOKAAL-TESTEN.md`

Wat je toetst: dat het zoekveld doorzoekt wat de kolom **Wie** laat zien. Vóór deze reparatie kon je
`test:bert@test` in beeld hebben en op `bert` nul regels krijgen — zonder foutmelding, dus zonder
enige aanwijzing dat er iets mis was.

Bij een afwijking: **stop, noteer stap + wat je zag.**

---

## Vooraf — wat het demolandschap wel en niet bevat

Gemeten in de database:

- **7.242 auditregels** staan op `test:bert@test` — een gebruiker **zonder** gekoppelde persoon.
  Dat is het geval dat stuk was, en het geval dat je hieronder toetst.
- Er zijn **3 gekoppelde personen** (J. de Vries, P. van Dijk, M. Bakker), maar **geen van hen heeft
  ook maar één auditregel**. Zij hebben nooit iets gemuteerd.

**Gevolg voor stap 3:** zoeken op een gekoppelde persoonsnaam is in dit landschap niet te tonen —
niet omdat het stuk is, maar omdat die personen niets gedaan hebben. Dat pad is wél in de
backendsuite geborgd (op eigen testdata). Zie de bevinding onderaan.

---

## Stap 1 — Het geval dat faalde

Ga naar **Auditlog**. Kijk eerst zonder zoekterm: de kolom **Wie** toont bij vrijwel elke regel
`test:bert@test`.

Typ nu `bert` in het zoekveld in de kop en klik op **Zoeken**.

✅ **Slaagt als:** je regels terugkrijgt, en in de kolom **Wie** staat overal `test:bert@test`.

❌ **Mis als:** je *"Geen gebeurtenissen gevonden"* ziet. Dat was precies het oude gedrag: het veld
zocht alleen in persoonsnamen, en `test:bert@test` is een e-mail-fallback.

---

## Stap 2 — Hoofdletters en deelwoorden

Wis het veld en probeer achter elkaar: `BERT`, `Test:Bert`, `@test`.

✅ **Slaagt als:** alle drie dezelfde regels opleveren. De vergelijking is hoofdletterongevoelig en
werkt op een deel van de tekst, niet op de hele.

❌ **Mis als:** één van de drie leeg blijft terwijl de andere resultaat geven.

---

## Stap 3 — Een gekoppelde persoonsnaam *(niet te tonen in dit landschap)*

Zou er een gebruiker mét gekoppelde persoon auditregels hebben, dan moet zoeken op diens naam die
regels opleveren — en moet zoeken op zijn **e-mailadres** hem juist **niet** vinden, want de kolom
toont dan zijn naam en niet zijn adres.

Probeer voor de zekerheid `de Vries`.

✅ **Slaagt als:** je *"Geen gebeurtenissen gevonden"* ziet — correct, want die persoon heeft niets
gemuteerd. Dit is dus géén fout.

❌ **Mis als:** je een foutmelding krijgt in plaats van de lege melding.

---

## Stap 4 — Een term die echt nergens voorkomt

Typ `zzz-bestaat-niet` en klik **Zoeken**.

✅ **Slaagt als:** *"Geen gebeurtenissen gevonden"* verschijnt — rustig, zonder foutmelding. Het
onderscheid tussen "niets gevonden" en "er ging iets mis" moet blijven bestaan.

❌ **Mis als:** er een rode foutmelding komt, of er tóch regels verschijnen.

---

## Stap 5 — Zoeken samen met een ander filter

Zoek op `bert`. Zet daarna het filter **Handeling** op *Aangemaakt*.

✅ **Slaagt als:** de lijst kleiner wordt en beide voorwaarden gelden — alleen aanmaak-regels van
`test:bert@test`. Zet **Handeling** terug op *Alle*: de langere lijst komt terug, je zoekterm staat
er nog.

Probeer daarna een datumbereik bij **Van** / **Tot** met de zoekterm erin. Klik tot slot **Wissen**:
alles leeg, volledige lijst terug.

❌ **Mis als:** het zetten van een filter je zoekterm wist, of als de filters elkaar uitsluiten in
plaats van samen te gelden.

---

## Stap 6 — Het label en het zoekgedrag

✅ **Slaagt als:** in het zoekveld *"Zoek op wie…"* staat — niet meer "Zoek op naam…", want die naam
staat op dit scherm meestal niet eens in beeld.

✅ **En:** typen alléén doet niets. De lijst verandert pas bij **Enter** of bij een klik op
**Zoeken**. Op een auditlog kunnen tienduizenden regels staan; elke toetsaanslag zoeken is daar geen
dienst.

❌ **Mis als:** de lijst meebeweegt tijdens het typen.

---

## Bevinding om mee te nemen

Het demolandschap kan het gekoppelde-persoon-pad niet tonen: de drie gekoppelde personen hebben geen
auditregels. Wil je dat pad ooit in de browser kunnen controleren, dan moet de dev-seed een mutatie
onder een gekoppelde gebruiker doen. Nu is dat pad alleen in de backendsuite geborgd.

## Als er iets mis is

Noteer: **stap · zoekterm · wat je verwachtte · wat je zag** (met de inhoud van de kolom Wie).
