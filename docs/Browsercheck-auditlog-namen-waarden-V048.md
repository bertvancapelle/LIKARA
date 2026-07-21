# Browsercheck — elke regel een naam, elke waarde in schermtaal (LI048 snede 3)

**Build:** V048 · **Duur:** ~8 minuten · **Voor:** Bert
**Inloggen en menupad:** zie `docs/LOKAAL-TESTEN.md`

Wat je toetst: dat de twee soorten die na snede 1/2 nog een kale code toonden nu een naam dragen,
en dat waarden in de taal van het scherm staan in plaats van in die van de opslag.

Bij een afwijking: **stop, noteer stap + wat je zag.**

---

## Stap 1 — De checklistvraag draagt zijn vraagtekst

Ga naar **Auditlog**. Zet het filter **Onderdeel** leeg en zoek een regel die over een
checklistvraag gaat (of blader terug; er staan er 190).

✅ **Slaagt als:** je iets ziet als
**Checklistvraag — Op welke infrastructuur draait de applicatie (server, datacenter, cloudplat…**

Dus de vraagtekst zelf, afgekort met een beletselteken als hij lang is. Het begin is genoeg om de
vraag te herkennen.

❌ **Mis als:** er nog `Checklistvraag — e123f280-08d7-4093-a67e-b1b38c6c4910` staat.

> Sommige checklistvraag-regels tonen géén tekst. Dat klopt: die vragen zijn later verwijderd, en
> hun wijziging bevatte alleen `actief`. Zie de bevindingen onderaan.

---

## Stap 2 — Het componentprofiel toont zijn component

Zet **Handeling** op *Afgeleid* — dat zijn de systeemherberekeningen.

✅ **Slaagt als:** je regels ziet als **Componentprofiel — Zaaksysteem**, dus met de naam van het
component waarvoor iets herberekend is.

❌ **Mis als:** er nog `Componentprofiel — d7f127c0-dfeb-4ef3-8111-dedf4424e53c` staat.

> **Let op:** een deel van deze regels blijft naamloos. Dat is geen fout — die horen bij
> componenten die inmiddels zijn opgeruimd (oude testdata). Van de 2.085 profielregels heeft een
> minderheid nog een bestaand component. Zie de bevindingen.

---

## Stap 3 — Een gewijzigde keuzewaarde in schermtaal

Ga naar **Componenten**, open **Zaaksysteem**, en wijzig de **levensfase** (bijvoorbeeld naar
*Uitfaseren*). Sla op. Ga terug naar **Auditlog** en klap de bovenste regel open.

✅ **Slaagt als:** er staat **Levensfase: In productie → Uitfaseren** — in dezelfde woorden als op
het detailscherm.

❌ **Mis als:** er `production → phase_out` staat, of enige andere opslagterm.

**Extra controle die telt:** vergelijk de woorden met wat op het componentdetailscherm staat. Ze
moeten **identiek** zijn. Wijken ze af, dan is er een tweede vertaling ontstaan, en dat is precies
wat deze snede moest voorkomen.

---

## Stap 4 — De lange beschrijving (jouw geval)

Blijf op **Zaaksysteem**. Wijzig de **beschrijving**: laat het begin staan en voeg achteraan een
paar woorden toe. Sla op.

Ga naar **Auditlog** en klap de bovenste regel open.

✅ **Slaagt als:** de oude en nieuwe tekst **onder elkaar** staan, elk met een aanduiding ervoor:

> **Was:** Centraal systeem voor zaakgericht werken — gedeeld alle gemeenten
> **Nu:** Centraal systeem voor zaakgericht werken — gedeeld alle gemeenten en aangepast

Beide beginnen op dezelfde positie, zodat je oog ze langsloopt tot ze uiteenlopen.

❌ **Mis als:** ze op één regel staan met een pijl ertussen. Dan moet je eerst zoeken waar de ene
ophoudt en de andere begint — precies het probleem dat je aanwees.

---

## Stap 5 — Een korte waarde blijft op één regel

Wijzig van hetzelfde component de **naam** (bijvoorbeeld `Zaaksysteem` → `Zaaksysteem 2`) en kijk
opnieuw in het auditlog.

✅ **Slaagt als:** er **Naam: Zaaksysteem → Zaaksysteem 2** op één regel staat. Bij korte waarden is
dat het duidelijkst; de gestapelde vorm is er alleen voor lange.

> Zet de naam daarna terug.

---

## Stap 6 — Snede 1 en 2 zijn niet stukgegaan

✅ Werkpakketten tonen nog hun naam (**Werkpakket — WP-Audit**), niet `Element — <code>`.
✅ Zoeken op `bert` levert nog regels op; typen alleen doet nog steeds niets.
✅ Een verwijdering toont de naam zoals die wás.

---

## Bevindingen om mee te nemen

1. **Vier soorten blijven zonder naam, en dat is een besluit:** `gebruikersgroep` (heeft geen
   naamkolom — het is een aantalsfeit), `roltoewijzing`, `organisatiegebruik` en `gebruiker_persoon`
   (koppelfeiten zonder enkelvoudige naam). Elk staat met een reden in het register; ze kunnen niet
   stilzwijgend ontstaan.
2. **`blokkade` en `checklistscore` lenen hun naam van hun component, maar in het demolandschap is
   dat component meestal opgeruimd** (1 van 121, respectievelijk 267 van 2.227). De route werkt —
   de data is oud. Op een vers landschap zie je hier wél namen.
3. **`relatietype` heeft geen labelmap**, dus die waarde blijft ruw. Genoteerd, geen stille
   terugval.

## Als er iets mis is

Noteer: **stap · regel · wat je verwachtte · wat je zag** (met de tekst uit *Onderdeel* of de
opengeklapte diff).
