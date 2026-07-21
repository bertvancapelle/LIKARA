# Browsercheck — de eenvormige lijstkop (LI048, snede 1 + 1b)

**Build:** V048 · **Duur:** ~10 minuten · **Voor:** Bert
**Inloggen en menupad:** zie `docs/LOKAAL-TESTEN.md`

Wat je toetst is niet of het er mooi uitziet, maar of je **op vier schermen achter elkaar niet
opnieuw hoeft te zoeken** waar je zoekt en waar je iets aanmaakt. Loop de stappen in volgorde af.
Bij een afwijking: **stop, noteer stap + wat je zag** — niet doorlopen en aan het eind melden.

---

## Stap 1 — De vier schermen achter elkaar (het hele punt)

Ga achtereenvolgens naar **Componenten → Partijen → Contracten → Bedrijfsfuncties**. Kijk bij elk
scherm alleen naar de bovenste rij, en houd je muis stil op de plek waar de aanmaakknop stond.

✅ **Slaagt als:** de schermnaam op alle vier links staat, het zoekveld er direct naast, en de
aanmaakknop uiterst rechts — op **dezelfde hoogte en dezelfde plek**. De knop mag niet per scherm
een stukje opschuiven.

❌ **Mis als:** de knop op één scherm hoger/lager staat of naar links is geschoven; of de naam op
één scherm een andere grootte of kleur heeft.

> Let op Bedrijfsfuncties: dat scherm heeft géén Filter-knop (het heeft geen filtervenster). De
> aanmaakknop hoort dan alsnog op exact dezelfde plek te staan als op de andere drie — dat is
> precies wat hier wordt getoetst.

---

## Stap 2 — Nergens meer een tweede zoekveld

Blijf op elk van de vier schermen even staan en kijk of er **onder** de kop nóg een veld staat waar
je een naam in kunt typen.

✅ **Slaagt als:** je op elk scherm precies **één** zoekveld ziet — dat in de kop.

❌ **Mis als:** er onder de kop (in een filterbalk of los kadertje) nog een tweede zoekveld staat.
Dit is de kern van een defect dat hier is verholpen: er stonden er twee, elk met een eigen
werking. Typte je in het ene terwijl het andere gevuld was, dan zag je een lijst die bij geen van
beide hoorde.

**Extra proef (Componenten):** typ een naam in het zoekveld in de kop. De lijst moet meteen
meebewegen. Open daarna **Filter**, kies een filter, en klik Toepassen — je zoekterm moet blijven
staan en beide moeten samen gelden.

---

## Stap 3 — Bedrijfsfuncties: wat er niet meer in de kop staat

Ga naar **Bedrijfsfuncties**.

✅ **Slaagt als:**
- in de kop staat: `Bedrijfsfuncties` · zoekveld · `Nieuwe functie`;
- **onder** de kop staat de schakelaar **Boom | Diagram** — als één blokje met een omlijning en een
  scheidingslijntje ertussen, waarvan de gekozen stand gevuld is (dezelfde vorm als de schakelaar
  in het Open punten-tabblad van een component);
- **Model inlezen** staat rechts op diezelfde regel, als lichte tekstknop met een onderstreping —
  niet als volwaardige knop naast `Nieuwe functie`.

❌ **Mis als:** de schakelaar of `Model inlezen` weer bovenin naast de titel staat; of als de
schakelaar eruitziet als twee losse knoppen in plaats van één blokje met standen.

**Waarom dit zo is:** de schakelaar bepaalt *hoe* je naar dezelfde functies kijkt, niet *welke* je
ziet — dat hoort bij de inhoud, niet bij de besturing. En `Model inlezen` doe je één of twee keer
per jaar en het raakt de hele lijst in één keer; naast een wekelijkse actie in dezelfde vorm zouden
ze even gewoon lezen.

---

## Stap 4 — De zoekbalk in Diagram-stand

Sta nog op **Bedrijfsfuncties**. Noteer eerst waar `Nieuwe functie` staat. Klik dan op **Diagram**.

✅ **Slaagt als:** het zoekveld verdwijnt (het diagram toont alles en wordt er niet door gefilterd,
dus een zichtbaar veld zou doen alsof het iets doet) **én `Nieuwe functie` op exact dezelfde plek
blijft staan** — niet naar links opschuiven.

❌ **Mis als:** de knop naar links springt zodra het zoekveld weg is. Dat is dé fout die deze
opzet moet voorkomen: dan staat hij per stand ergens anders.

Klik terug naar **Boom** — het zoekveld hoort terug te komen, met je zoekterm nog erin.

---

## Stap 5 — Smal venster

Maak het browservenster smal (of zoom in tot ~150%). Loop de vier schermen nog eens langs.

✅ **Slaagt als:** de rij netjes **afbreekt** naar een volgende regel, en de schermnaam **volledig
leesbaar** blijft — hij mag niet worden afgekapt of platgedrukt. Het zoekveld mag wél smaller
worden.

❌ **Mis als:** de naam wordt afgekapt (`Bedrijfsfuncti…`), of de knoppen lopen buiten beeld en er
verschijnt een horizontale schuifbalk.

---

## Stap 6 — Toetsenbord door de kop

Ga naar **Componenten**. Klik één keer in een leeg stuk van de pagina, druk dan herhaald op **Tab**.

✅ **Slaagt als:** de focus in leesvolgorde gaat — eerst het zoekveld, dan `Filter`, dan
`Nieuw component` — en elk element een **duidelijk zichtbare focusrand** krijgt. Met **Enter** op
`Filter` opent het filtervenster; met **Esc** sluit het en komt de focus terug op de Filter-knop.

❌ **Mis als:** de focus door de kop springt in een andere volgorde dan je hem ziet staan, een
element geen zichtbare rand krijgt, of de focus na Esc ergens anders belandt.

Herhaal kort op **Bedrijfsfuncties**: Tab moet daar van zoekveld naar `Nieuwe functie` gaan, en
daarna pas naar de schakelaar eronder.

---

## Als er iets mis is

Noteer per afwijking: **stap · scherm · wat je verwachtte · wat je zag**. Niet zelf herstellen —
de bevinding stuurt de volgende snede.
