# Browsercheck — de geschiedenis van een ding is compleet (LI048)

**Build:** V048 · **Duur:** ~7 minuten · **Voor:** Bert
**Inloggen en menupad:** zie `docs/LOKAAL-TESTEN.md`

Wat je toetst: dat het klokje op een detailscherm **alles** toont wat er met dat ding gebeurd is —
ook de dingen die eraan hangen, zoals een rol die je aan een partij geeft.

Bij een afwijking: **stop, noteer stap + wat je zag.**

---

## Vooraf — dit geval moet je zelf maken

Gemeten in de database: er zijn 229 roltoewijzingen, waarvan er **75 naar een nog bestaande partij
verwijzen**. Alle 75 zijn samen met hun partij aangemaakt, in dezelfde handeling.

**Er is dus geen enkele partij met een "losse" roltoewijzing in het demolandschap.** Dat is precies
het geval dat het herstel oplost, dus stap 2 vraagt je er zelf een te maken. Dat kost één minuut en
is de enige manier om dit in de browser te zien.

*(De integratietoets maakt het geval zelf aan — twee gescheiden handelingen met een commit ertussen
— dus het is wel geborgd, alleen niet zichtbaar op bestaande data.)*

---

## Stap 1 — Het uitgangspunt

Ga naar **Partijen** en open een leverancier, bijvoorbeeld **Gemeente Tiel** of een andere externe
partij. Klik op het **klokje** in de kop.

✅ **Slaagt als:** je de geschiedenis van die partij ziet — wie, wanneer, welke handeling — en het
venster niet leeg is. Staat er niets, dan hoort er *"Nog geen geschiedenis voor dit object."* te
staan, geen leeg vlak.

Noteer hoeveel regels je ziet. Sluit het venster.

---

## Stap 2 — Geef die partij een rol (het echte geval)

Ga naar **Componenten**, open **Zaaksysteem**, en zoek de sectie waar je een **rol** aan een partij
toekent. Ken de partij uit stap 1 de rol **Contractbeheer** toe en sla op.

> Dit is nu een **aparte handeling**, los van het aanmaken van die partij. Precies wat er eerder
> misging: zo'n losse toekenning verdween uit beeld.

---

## Stap 3 — De rol staat in de geschiedenis van de partij

Ga terug naar **Partijen**, open dezelfde partij, en klik op het **klokje**.

✅ **Slaagt als:** er nu een regel bij staat over de **roltoewijzing** — met *Contractbeheer* erin,
en jouw naam als wie.

❌ **Mis als:** de geschiedenis er nog precies zo uitziet als in stap 1. Dan is de rol wél toegekend
maar nergens terug te vinden — de geschiedenis ziet er compleet uit en is het niet.

**Vervolg:** neem de rol weer weg op het componentscherm, en kijk opnieuw. Ook het **intrekken**
hoort in de geschiedenis te staan — dat is de vraag *"sinds wanneer niet meer"*.

---

## Stap 4 — Een component is onveranderd

Open **Zaaksysteem** en klik op het **klokje**.

✅ **Slaagt als:** je ziet wat je gewend was: de aanmaak, de wijzigingen, de systeemherberekeningen,
de scores — en sinds vanmiddag ook de koppelingen. Er mag hier **niets** veranderd zijn; het
componentdetail had al zijn eigen, rijkere weg.

**Controle die telt:** ga naar **Auditlog** en filter op **Component = Zaaksysteem**. Dezelfde vraag
via een andere weg hoort hetzelfde antwoord te geven.

---

## Stap 5 — Een derde soort ter controle

Ga naar **Plateaus** (of **Werkpakketten**) en open er een. Klik op het **klokje**.

✅ **Slaagt als:** je de geschiedenis van dat plateau ziet — aanmaak en wijzigingen.

⚠️ **Verwacht:** géén extra regels over lidmaatschap. Het lidmaatschap van plateaus en werkpakketten
loopt via koppelingen, en gemeten leveren die vandaag **0** auditregels op. Dat staat als bewuste
uitspraak in de code, met die reden erbij.

---

## Stap 6 — De rechten zijn ongewijzigd

Log in als een gebruiker met een **kijkersrol** (zonder auditlogrecht) en open een partijdetail.

✅ **Slaagt als:** het klokje er staat en werkt. De toegang volgt het **object**, niet het auditlog:
wie het ding mag zien, mag zijn geschiedenis zien.

❌ **Mis als:** er een foutmelding komt of het venster leeg blijft.

---

## Als er iets mis is

Noteer: **stap · scherm · wat je verwachtte · wat je zag** (met de regels uit het geschiedenisvenster).
