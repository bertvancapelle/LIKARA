# Browsercheck — twee wegwijzers als teken (LI048)

**Build:** V048 · **Duur:** ~6 minuten · **Voor:** Bert
**Inloggen en menupad:** zie `docs/LOKAAL-TESTEN.md`

Wat je toetst: dat de twee knoppen die je *ergens heen brengen* nu een teken zijn, dat de knoppen
die *iets veranderen* woorden zijn gebleven, en dat de rij niet uit elkaar is gevallen.

Bij een afwijking: **stop, noteer stap + wat je zag.**

---

## Stap 1 — Het componentdetail: beide tekens

Ga naar **Componenten** en open **Zaaksysteem**. Kijk naar de knoppenrij in de kop.

✅ **Slaagt als:** je ziet — van links naar rechts —

> `Bewerken` · `Start beoordeling` / `Klaar verklaren` · 🗺 · 🕘 · | · `Verwijderen`

Dus: **Bewerken** en de statusknop als woord, dan het **kaartje** en het **klokje** als teken, en
rechts apart **Verwijderen** als woord.

✅ **En:** de tekens staan **op dezelfde hoogte** als de woorden ernaast — dezelfde bovenkant,
dezelfde onderkant, geen knop die uit de rij springt.

❌ **Mis als:** een teken groter of kleiner is dan de tekst ernaast, of hoger/lager staat. Dan is de
rij visueel uiteengevallen.

❌ **Mis ook als:** er een leeg vlak staat waar een teken hoort. Dat betekent dat het teken niet
rendert — precies wat er met het oude informatie-icoontje aan de hand was.

---

## Stap 2 — De tooltips

Houd je muis stil op het **kaartje** (zonder te klikken). Wacht een seconde.

✅ **Slaagt als:** er *"Bekijk op kaart"* verschijnt.

Doe hetzelfde op het **klokje**.

✅ **Slaagt als:** er *"Geschiedenis"* verschijnt.

---

## Stap 3 — Ze doen nog wat ze deden

Klik op het **kaartje**.

✅ **Slaagt als:** je op de landschapskaart belandt, met Zaaksysteem in beeld. Ga terug.

Klik op het **klokje**.

✅ **Slaagt als:** het geschiedenisvenster opengaat met de gebeurtenissen van dit component. Sluit
het weer.

---

## Stap 4 — De handelingen zijn onveranderd

Kijk nog eens naar **Bewerken**, de statusknop (**Klaar verklaren** of **Heropenen**) en
**Verwijderen**.

✅ **Slaagt als:** dat alle drie nog gewoon **woorden** zijn, precies zoals eerst.

❌ **Mis als:** een van die drie een teken is geworden. Dat is bewust níét gedaan: die knoppen
veranderen iets — Heropenen geeft werk terug aan de wachtrij, Verwijderen is definitief — en moeten
in één blik te lezen zijn, ook door iemand die dit scherm voor het eerst ziet. Een tooltip
verschijnt pas als je blijft hangen, en op een tablet helemaal niet.

---

## Stap 5 — Een tweede detailscherm

Ga naar **Partijen** en open een partij (bijvoorbeeld **Gemeente Tiel**).

✅ **Slaagt als:** je daar **alleen het klokje** ziet, naast `Bewerken` en `Verwijderen`. Geen
kaartje — dat hoort alleen bij componenten.

Probeer ook een **Plateau** of een **Werkpakket** (menu *Plateaus* / *Werkpakketten*): daar hoort
hetzelfde beeld te staan. De geschiedenisknop is gedeeld, dus alle zeven detailschermen kregen hem
in één keer.

---

## Stap 6 — Toetsenbord

Ga terug naar **Zaaksysteem**. Klik één keer in een leeg stuk van de pagina en druk herhaald op
**Tab**.

✅ **Slaagt als:** de focus door de knoppen loopt in **dezelfde volgorde als je ze ziet staan** —
Bewerken, statusknop, kaartje, klokje, Verwijderen — en elk element een **duidelijk zichtbare
focusrand** krijgt, óók de twee tekens.

✅ **En:** met **Enter** op het klokje gaat het geschiedenisvenster open; met **Esc** weer dicht.

❌ **Mis als:** de tekens worden overgeslagen, of geen zichtbare rand krijgen.

---

## Als er iets mis is

Noteer: **stap · scherm · wat je verwachtte · wat je zag**.
