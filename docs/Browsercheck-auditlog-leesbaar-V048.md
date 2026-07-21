# Browsercheck — het auditlog vertelt wat er gebeurde (LI048 snede 1+2)

**Build:** V048 · **Duur:** ~8 minuten · **Voor:** Bert
**Inloggen en menupad:** zie `docs/LOKAAL-TESTEN.md`

Wat je toetst: dat elke regel het **ding** noemt waar het over ging, met een **naam** — en niet de
interne code. En dat die naam de naam van **toen** is, ook als er sindsdien iets veranderd is.

Bij een afwijking: **stop, noteer stap + wat je zag.**

---

## Vooraf — wat het demolandschap bevat

Alle vier de gevallen zijn aanwezig (gemeten):

| Geval | Aantal | Toont een naam? |
|---|---:|---|
| Aanmaken | 44.237 | ✅ 15.210 dragen een vastgelegde naam |
| Wijzigen | 1.223 | ⚠️ slechts 44 dragen er één — de rest valt terug op de huidige naam |
| Verwijderen | 180 | ⚠️ 18 dragen er één; de rest toont bewust géén naam |
| Systeem (herberekening) | 2.088 | ❌ **geen enkele** toont een naam |

De laatste twee rijen zijn bevindingen, geen fouten — zie onderaan.

---

## Stap 1 — Het geval van je screenshot

Ga naar **Auditlog**. Kijk naar de bovenste regels, in de kolom **Onderdeel**.

✅ **Slaagt als:** je regels ziet als **Werkpakket — WP-Audit**, **Werkpakket — WP-RLS**,
**Component — PV-Test DB-component**. Dus: het soort ding in gewone taal, en de naam erachter.

❌ **Mis als:** er nog regels staan als `Element — 9f1282d4-48ec-41d8-aadc-c794ac5fabd7`. Dat was
het oude gedrag: het scherm koos de regel die alleen zei dát er iets bestond, in plaats van die
zei wát het was.

**Let ook op:** achter zo'n aanmaakregel hoort géén *"(+1 afgeleid)"* meer te staan. Die telling
verwees naar precies die betekenisloze regel.

---

## Stap 2 — Wat er ónder zit is niet verdwenen

Klap een regel **Werkpakket — WP-Audit** open.

✅ **Slaagt als:** je in de uitklap nog steeds álle onderliggende regels ziet, inclusief de
technische `Element`-regel. Er is niets weggegooid — hij is alleen niet meer de aanleiding.

❌ **Mis als:** de uitklap leeg is of regels mist.

---

## Stap 3 — De naam van toen (de kern)

Zoek een component op waarvan je de naam kent, bijvoorbeeld via **Componenten**. Noteer de naam.
**Hernoem hem** (Bewerken → naam wijzigen → opslaan).

Ga terug naar **Auditlog** en zoek de **aanmaakregel** van dat component op (zoek op wie het
aanmaakte, of blader terug).

✅ **Slaagt als:** de aanmaakregel nog steeds de **oude** naam toont — die van het moment van
aanmaken. Er staat een aparte, nieuwere regel voor de hernoeming zelf, met de nieuwe naam.

❌ **Mis als:** de oude aanmaakregel meteen de nieuwe naam toont. Dan verandert de geschiedenis mee
en klopt het log niet meer met wat er destijds op het scherm stond.

> Dit is besluit 1 en het belangrijkste punt van deze snede.

---

## Stap 4 — Een verwijdering

Zet het filter **Handeling** op *Verwijderd*.

✅ **Slaagt als:** je regels ziet met een naam erbij, bijvoorbeeld **Component — PV-Test
DB-component**, ook al bestaat dat component niet meer.

✅ **En ook goed:** regels zonder naam, bijvoorbeeld **Relatie — <code>**. Dat is bedoeld: van die
verwijderingen is destijds geen naam vastgelegd, en de naam van nú opvragen mag hier niet — het
object hoort niet meer te bestaan. Beter geen naam dan een misleidende.

❌ **Mis als:** er een naam verschijnt bij een verwijdering waar je die niet verwacht, of als álle
verwijderingen naamloos zijn.

---

## Stap 5 — Een wijziging

Zet **Handeling** op *Gewijzigd*.

✅ **Slaagt als:** de regels het gewijzigde ding met zijn naam tonen, bijvoorbeeld **Werkpakket —
WP-Cyc A**.

⚠️ **Bekende tekortkoming:** wijzig je een ánder veld dan de naam, dan staat er geen naam in die
regel vastgelegd en toont het scherm de **huidige** naam. Hernoem je zo'n object, dan verandert díé
regel wel mee. Dat is erkend en staat als opvolgpunt — je hoeft het niet te melden als fout.

---

## Stap 6 — Een systeemherberekening

Zet **Handeling** op *Afgeleid*.

⚠️ **Verwacht:** deze regels tonen **geen** naam — je ziet iets als **Componentprofiel — <code>**.
Dat is een bevinding, geen regressie: die soort heeft geen naambron en legt zelf geen naam vast.

✅ **Slaagt als:** de regels leesbaar zijn qua soort en handeling, en er geen foutmelding komt.

❌ **Mis als:** er interne opslagtaal in beeld staat (`component_profiel` in plaats van
*Componentprofiel*, of `phase_out` in plaats van *Uitfaseren*).

---

## Stap 7 — Het zoeken werkt nog

Typ `bert` in het zoekveld en klik **Zoeken**.

✅ **Slaagt als:** je regels terugkrijgt met `test:bert@test` in de kolom *Wie* — de reparatie van
vanmiddag is niet stukgegaan. Typen alléén doet nog steeds niets; alleen Enter of de knop zoekt.

---

## Bevindingen om mee te nemen

1. **Systeemherberekeningen tonen geen naam** (2.088 regels). `component_profiel` en `blokkade`
   hebben geen naambron en leggen zelf geen naam vast. Dat vraagt een aparte keuze: de naam van het
   bijbehorende component erbij halen, of accepteren.
2. **Wijzigingen van een ánder veld dan de naam** vallen terug op de huidige naam (1.179 van de
   1.223 regels). Erkend als tekortkoming, niet als ontwerp; oplossen vraagt een naam-snapshot bij
   élke mutatie.

## Als er iets mis is

Noteer: **stap · regel · wat je verwachtte · wat je zag** (met de tekst uit de kolom *Onderdeel*).
