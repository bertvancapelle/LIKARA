# Horizon — bewaartermijn via het zaaktype (denk/ontwikkelrichting)

| | |
|---|---|
| **Status** | **Horizon — géén backlogtaak, géén besluit.** Een grens die we nú trekken op grond van een meting, mét de route erbij als die ooit opengaat. Geen ADR: dit is richting. |
| **Vastgelegd** | LI045 (2026-07-18), opdracht van Bert — docs-only |
| **Grond (meting)** | `docs/Meting-gemma-functie-proces-relatie-V045.md` (read-only, deze sessie) |
| **Verwant besluit** | `docs/adr/ADR-053_Archiefwet-als-hard-componentfeit.md` (het feit "draagt archief"; de bewaartermijn valt hier bewust buiten) |

---

## De grens die we trekken

**Een bewaartermijn is geen LIKARA-feit zolang de bron de keten niet meelevert.** LIKARA legt vast dat
er archiefbescheiden in een systeem leven (ADR-053, één hard componentfeit). Het legt **niet** vast hoe
lang die bewaard moeten blijven — dat is geen scope-inperking uit voorzichtigheid, het is een **besluit
met een meting eronder**. Deze horizon legt die meting en de reden vast, zodat de grens later niet als
"gewoon nog niet gedaan" wordt heropend.

---

## De gemeten grond

Uit de read-only meting op het gecureerde GEMMA-bestand (release 2026-07-01, gepind):

- **Twaalf** directe relaties tussen bedrijfsfunctie en bedrijfsproces, **dekking 4%** (12 van de 297
  functies), allemaal van het zwakste type (`Serving`, "dient"), en uitsluitend in de **bedrijfsvoerings-
  hoek** (juridische ondersteuning, inkoop, communicatie, personeel, archiefbeheer, …) waar functie en
  proces bijna hetzelfde woord zijn.
- **Geen indirecte brug**: geen groepering, dienst of rol verbindt de functieboom met de procesboom.
- **Nul** verwijzingen naar selectielijst, zaaktype of bewaartermijn in het model als machineleesbaar
  gegeven (geen property, geen relatie; op géén enkel proces). De woorden komen alleen als losse proza in
  de applicatielaag voor.

**De bedrijfsfunctie-as draagt dit niet, en gaat het niet dragen.** De keten *systeem → functie → proces
→ selectielijst-procestype → bewaartermijn* is in de bron zelf op meerdere plekken open; hem via de
functie-as leggen zou een implementatieproject vóór er waarde ontstaat betekenen — precies de wijkende
horizon die LIKARA vermijdt.

---

## Waarom dat opzet is, geen omissie

GEMMA presenteert **bedrijfsfuncties ("wat")** en **bedrijfsprocessen ("hoe")** uitdrukkelijk als **twee
perspectieven op de gemeente, niet als twee lagen van één boom.** De twaalf relaties die we vonden komen
overeen met de enige gepubliceerde view die de twee koppelt (de ondersteunende processen ↔
bedrijfsfuncties). Ons bestand **mist dus niets** — het model is niet incompleet ingelezen; de brug
bestáát daar zo niet. Dat is een modelleerkeuze van VNG, geen gat in onze bron.

---

## Waar de keten wél sluit

Van **zaaktype naar bewaartermijn** is de keten publiek en gemodelleerd — alleen langs een andere as dan
de bedrijfsfunctie:

- **selectielijst-procestype** (de generieke VNG-selectielijst kent er 29) **→ resultaattype →
  archiefregime/bewaartermijn**;
- de **concordans** naar de GEMMA-bedrijfsprocessen ligt als bijlage 5 bij de selectielijst;
- de koppeling **zaaktype ↔ selectielijst-procestype** zit in het **RGBZ/ZTC**-informatiemodel.

Belangrijk: de termijn hangt aan een **procesobject** — hij begint pas te lopen als dat object (de
zaak/het resultaat) **vervalt**. Een bewaartermijn is dus geen statisch etiket op een systeem, maar een
gebeurtenis-gedreven feit rond een zaak. Dat is nóg een reden waarom hij niet als component-veld kan
landen (ADR-053 besluit 3).

---

## De route als die ooit opengaat

Niet via de bedrijfsfunctie, maar via het **zaaktype** — en dat is het cruciale verschil: het zaaktype
is **geen referentiemodel dat wij moeten inlezen**, het staat **al ingericht in het zaaksysteem van de
gemeente zelf** (de zaaktypencatalogus, ZTC). De keten sluit dus niet in een generiek model dat LIKARA
cureert, maar in de concrete inrichting van déze gemeente.

De concrete toekomstige vraag luidt daarom niet *"levert GEMMA de brug?"* (gemeten: nee), maar:

> **Kunnen we de zaaktypencatalogus van deze gemeente lezen?**

Dat is een tenant-specifieke bron (zoals de Softwarecatalogus-export in de andere horizon), geen
gecureerd platform-referentiemodel. Pas als die bron ontsloten is, en alleen dan, wordt de bewaartermijn
een afleidbaar feit — en dan nog gebeurtenis-gedreven, per zaak, niet als etiket op het systeem.

---

## Wat niet is vastgesteld (openstaande verificatie)

- Of het **volledige** GEMMA-model uit de publieke Archi-repository méér relaties functie↔proces bevat
  dan ons gecureerde AMEFF-bestand. Onwaarschijnlijk gezien de overeenkomst met de enige gepubliceerde
  view (ondersteunende processen ↔ bedrijfsfuncties), maar **niet bewezen**. Te verifiëren op een gepinde
  versie als de vraag ooit terugkeert — niet nu.

---

## Verhouding tot de andere horizon

Deze horizon deelt de lijn van `Horizon-bron-gedreven-opvoeren.md`: de rijkste waarde zit in **tenant-
eigen bronnen** (Softwarecatalogus-export, zaaktypencatalogus) die de gemeente zelf aanlevert, niet in
generieke referentiemodellen die LIKARA cureert. Het gecureerde model (GEMMA-bedrijfsfuncties) is het
vertrekpunt; de bewaartermijn-keten is uitdrukkelijk **geen** verlengstuk daarvan.
