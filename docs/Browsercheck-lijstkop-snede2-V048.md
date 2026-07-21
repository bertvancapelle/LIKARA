# Browsercheck — de lijstkop op alle veertien schermen (LI048, snede 2)

**Build:** V048 · **Duur:** ~12 minuten · **Voor:** Bert
**Inloggen en menupad:** zie `docs/LOKAAL-TESTEN.md`

Snede 1 bracht vier schermen op één kop; deze snede tien erbij. Wat je toetst is of de belofte
overeind blijft **naarmate het er meer worden**: dat je op veertien schermen achter elkaar niet
opnieuw hoeft te zoeken waar je zoekt en waar je iets aanmaakt.

Bij een afwijking: **stop, noteer stap + scherm + wat je zag** — niet doorlopen en aan het eind
melden.

---

## Stap 1 — De hele menubalk langs (het hele punt)

Loop het hoofdmenu van boven naar beneden af en blijf op elk scherm twee tellen staan. Kijk alleen
naar de bovenste rij. Houd je muis stil op de plek waar de aanmaakknop staat.

**Componenten → Bedrijfsfuncties → Partijen → Contracten → Gebruikersbeheer → Auditlog →
Blokkades → Architectuur → Checklistvragen → Migratienorm → Plateaus → Gaps → Werkpakketten →
Deliverables**

✅ **Slaagt als:** de schermnaam overal links staat op dezelfde hoogte, en waar een aanmaakknop is
(`Nieuw component`, `+ Nieuw plateau`, `+ Nieuwe gap`, `Gebruiker toevoegen`, …) die **uiterst
rechts** staat, op dezelfde lijn. Je muis mag blijven staan waar hij staat.

❌ **Mis als:** de knop op één scherm hoger, lager of naar links verschoven staat; of de naam op één
scherm een andere grootte of kleur heeft.

> Let op de schermen **zonder** zoekveld (Plateaus, Gaps, Werkpakketten, Deliverables,
> Gebruikersbeheer, Migratienorm, Architectuur). Juist dáár moet de knop op dezelfde plek staan —
> de ruimte in het midden blijft leeg. Dat is de kern van deze snede.

---

## Stap 2 — Auditlog: zoeken gebeurt bewust

Ga naar **Auditlog**. Typ een naam in het zoekveld in de kop, maar druk **niet** op Enter. Wacht
drie tellen en kijk naar de lijst.

✅ **Slaagt als:** de lijst **niet** verandert terwijl je typt. Pas als je op **Enter** drukt of op
**Zoeken** klikt, wordt er gezocht.

❌ **Mis als:** de lijst meebeweegt tijdens het typen. Op een auditlog kunnen heel veel regels staan;
elke toetsaanslag een zoekopdracht laten afvuren is daar geen dienst.

**Vervolg:** klik op **Zoeken** — nu moet de lijst wél reageren. Zet daarna een van de filters
eronder (Van/Tot/Onderdeel/Handeling) en controleer dat die samen met je zoekterm gelden. Klik
**Wissen** en controleer dat alles leeg is.

---

## Stap 3 — Migratienorm: de toelichting staat er nog

Ga naar **Migratienorm**.

✅ **Slaagt als:** onder de schermnaam een korte alinea staat die uitlegt wat "de lat voor
migratieklaar" is — **direct leesbaar**, niet verstopt achter een "i"-icoon. De tekst is **smal**
(ongeveer een kolombreedte), niet uitgesmeerd over het hele scherm.

❌ **Mis als:** de tekst weg is, achter een uitleg-icoon zit, of over de volle breedte loopt.

**Waarom dit zo is:** die alinea is geen extra informatie maar de sleutel tot het scherm. Je bepaalt
hier wat er straks bij élk component als verplicht verschijnt — te ingrijpend om op een gok te doen.

---

## Stap 4 — Architectuur: de schakelaar staat onder de kop

Ga naar **Architectuur**.

✅ **Slaagt als:** in de kop alleen de naam "Architectuur — lagen" staat, en de schakelaar
**Lagen | Tabel** eronder — als één blokje met een omlijning en een scheidingslijntje ertussen,
waarvan de gekozen stand gevuld is. Dezelfde vorm als **Boom | Diagram** op Bedrijfsfuncties.

❌ **Mis als:** de schakelaar naast de titel staat, of eruitziet als twee losse knoppen op een
grijze plaat (dat was de oude vorm).

**Vervolg:** klik op **Tabel** en dan terug op **Lagen** — de weergave moet wisselen en je keuze moet
bewaard blijven als je het scherm verlaat en terugkomt.

---

## Stap 5 — Blokkades en Checklistvragen: het filter zit in de kop

Ga naar **Blokkades**, daarna naar **Checklistvragen**.

✅ **Slaagt als:** het keuzemenu (Status bij Blokkades, Categorie bij Checklistvragen) **in de
bovenste rij** staat, rechts van de schermnaam — op dezelfde plek waar op Componenten de
**Filter**-knop zit. Kiezen ververst de lijst.

❌ **Mis als:** het filter in een aparte balk onder de kop staat.

---

## Stap 6 — Smal venster

Maak het browservenster smal (of zoom in tot ~150%). Loop minstens vier schermen langs, waaronder
**Architectuur** (dat heeft de langste naam) en **Auditlog**.

✅ **Slaagt als:** de rij netjes **afbreekt** naar een volgende regel en de schermnaam **volledig
leesbaar** blijft. Zoekveld en knoppen mogen smaller worden of onder elkaar komen.

❌ **Mis als:** de naam wordt afgekapt (`Architectuur — la…`), of er verschijnt een horizontale
schuifbalk over de hele pagina.

---

## Stap 7 — Toetsenbord

Ga naar **Auditlog**. Klik één keer in een leeg stuk van de pagina, druk dan herhaald op **Tab**.

✅ **Slaagt als:** de focus in leesvolgorde loopt — eerst het zoekveld, dan **Zoeken**, dan de
filters eronder — en elk element een **duidelijk zichtbare focusrand** krijgt. Enter op het
zoekveld voert de zoekopdracht uit.

Herhaal kort op **Plateaus** (een scherm zonder zoekveld): Tab moet daar meteen op
**+ Nieuw plateau** landen, niet eerst door een onzichtbaar veld.

❌ **Mis als:** de focus in een andere volgorde springt dan je hem ziet staan, een element geen
zichtbare rand krijgt, of je op een leeg element belandt.

---

## Als er iets mis is

Noteer per afwijking: **stap · scherm · wat je verwachtte · wat je zag**. Niet zelf herstellen — de
bevinding stuurt de volgende snede (Signalering + Plaatsingssignalen staan al gepland).
