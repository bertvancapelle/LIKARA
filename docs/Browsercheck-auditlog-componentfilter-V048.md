# Browsercheck — het component-filter op Auditlog (LI048)

**Build:** V048 · **Duur:** ~5 minuten · **Voor:** Bert
**Inloggen en menupad:** zie `docs/LOKAAL-TESTEN.md`

Twee dingen worden getoetst: dat het filter heet naar wat het dóét, en dat het álles teruggeeft wat
er met een component gebeurd is — inclusief zijn koppelingen, die er eerder buiten vielen.

Bij een afwijking: **stop, noteer stap + wat je zag.**

---

## Stap 1 — Het label

Ga naar **Auditlog** en kijk naar de filterbalk onder de kop.

✅ **Slaagt als:** het derde filter **Component** heet, en het veld *"Kies een component…"* toont.

✅ **En:** de kolom in de tabel heet nog steeds **Onderdeel**.

❌ **Mis als:** het filter nog *Onderdeel* heet. Dat beloofde alle soorten terwijl er alleen
componenten kiesbaar zijn — precies waardoor je op een checklistvraat zocht en nooit iets vond.

> Dat filter en kolom verschillende namen hebben is nu bedoeld: het filter dekt één soort, de kolom
> toont ze allemaal.

---

## Stap 2 — Zoeken op een deel van een naam

Klik in het **Component**-veld en typ `portaal`.

✅ **Slaagt als:** **Klantportaal** in de lijst verschijnt. Er wordt op een deel van de naam gezocht,
niet alleen vanaf het begin, en hoofdletters maken niet uit (probeer ook `PORTAAL`).

❌ **Mis als:** de lijst leeg blijft.

**Extra:** wis het veld en typ niets. Je krijgt de eerste tien componenten als startlijst. Staan er
meer dan tien, dan hoort onderaan **"Meer resultaten — verfijn je zoekopdracht."** te staan. Die
melding moet blijven: je moet kunnen zien dát er meer is.

---

## Stap 3 — De koppelingen komen mee (het herstel)

Kies **Zaaksysteem** in het Component-filter.

✅ **Slaagt als:** je in de lijst óók regels ziet die over **koppelingen** gaan — dus met
**Koppeling** of **Relatie** in de kolom *Onderdeel*, waarbij Zaaksysteem het ene of het andere
uiteinde is. Voor Zaaksysteem zijn dat er 15.

❌ **Mis als:** je alleen regels over het component zelf ziet (aanmaken, wijzigen, profiel, scores)
en geen enkele koppeling. Dat was het oude gedrag: haalde iemand de koppeling naar DigiD weg, dan
was dat via dit filter onvindbaar — terwijl dát vaak precies is wat je zoekt als er iets niet meer
werkt.

**Probeer ook:** *Klantportaal* (12 koppelingen), *Burgerzaken-suite* (12), *Gegevensmakelaar* (12).

---

## Stap 4 — De afgeleide regels komen ook mee

Blijf op **Zaaksysteem** gefilterd.

✅ **Slaagt als:** je naast het component zelf ook regels ziet over zijn **componentprofiel**
(systeemherberekeningen), **checklistscores** en **functievervullingen**. Alles wat over dit
component gaat, staat er.

❌ **Mis als:** alleen de regels over het component zelf verschijnen.

---

## Stap 5 — Samen met de andere filters

Houd **Zaaksysteem** staan en zet **Handeling** op *Gewijzigd*.

✅ **Slaagt als:** de lijst kleiner wordt en beide voorwaarden gelden. Zet **Handeling** terug op
*Alle*: de langere lijst komt terug, je component-keuze staat er nog.

Typ daarna `bert` in het zoekveld en klik **Zoeken** — zoeken en filteren moeten samen gelden.

❌ **Mis als:** het zetten van een filter je component-keuze wist.

---

## Wat je waarschijnlijk ziet en wat het betekent

In dit demolandschap levert het filter vaak **één grote gebeurtenis** op met heel veel onderliggende
regels. Dat is **geen fout van dit filter**: de dev-seed schrijft de complete seed onder één
gebeurtenis-id (1.648 regels, 18 soorten). Elke koppeling uit die seed hoort dus bij die ene
gebeurtenis.

Bij echte handelingen gebeurt dit niet: van de 15.551 gebeurtenissen in het log zijn er **15.382
kleiner dan 20 regels**. Wil je het filter realistisch beoordelen, kijk dan naar een component dat
je zelf hebt aangemaakt en gewijzigd.

Dit staat als bevinding in `docs/OPVOLGPUNTEN.md`.

## Als er iets mis is

Noteer: **stap · component · wat je verwachtte · wat je zag** (met de tekst uit *Onderdeel*).
