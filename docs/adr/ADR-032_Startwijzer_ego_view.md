# ADR-032 — "Start vanuit..."-wijzer voor de ego-view

**Status:** Voorstel (open subknopen nog te beslissen)
**Datum:** 2026-06-23
**Relatie:** Bouwt voort op de Landschapskaart ego-view en ADR-031 (ring-uitbreiding).
**Invariant:** score blijft de enige lifecycle-driver — puur read-only navigatiehulp.

## Context / aanleiding

De ego-view centreert op één node. Het kiezen van dat centrum vereist nu dat de
gebruiker de graph doorzoekt of door een lange lijst scrolt. Bij grotere datasets
(200+ componenten, meerdere componenttypen) is dit onwerkbaar.

Gebruikers willen gericht starten vanuit een context die hen aanspreekt:
- "Welke componenten heeft leverancier X bij ons?"
- "Wat valt onder contract Y?"
- "Welke componenten gebruikt organisatie Z?"
- "Toon mij alle servers/switches" (infrastructuurcomponenten)
- "Wat hoort bij dit migratieplateau?"

## Besluit (kern)

Een **"Start vanuit..."-wijzer** boven de ego-view met vijf ingangen.
Elke ingang filtert een zoeklijst naar het relevante type; de gebruiker kiest
één item; de ego-view centreert daarop met de passende ringen automatisch aan.

**Vijf ingangen:**
1. **Component** — gefilterd op componenttype (Applicatie, Server, Switch, Database, etc.)
2. **Contract** — mantel- of deelcontract
3. **Partij** — organisatie, leverancier, ketenpartner, persoon
4. **Gebruiker** — gebruikersgroep of organisatie als gebruiker
5. **Plateau** — migratieplateau (start vanuit migratie-context)

## Invarianten

- Read-only / engine onaangeroerd.
- Geen nieuwe API-endpoints verwacht (bestaande list-endpoints volstaan per ingang).
- Geen schema/migratie.

## Open subknopen (te beslissen vóór de bouw)

1. **UI-vorm van de wijzer.** Uitklapbaar paneel, tabs, of modal? Default: uitklapbaar
   paneel boven de bestaande filters (minste verstoring bestaande UI).
2. **Automatisch ringen aan.** Welke ringen zet de wijzer aan per ingang?
   (bv. Contract-ingang → Contracten-ring aan; Partij-ingang → Rollen & beheer aan).
   Default: per ingang een vaste preset, overschrijfbaar.
3. **Zoek per ingang.** Server-side ZoekSelect per ingang of client-side filter?
   Default: ZoekSelect (server-side) want catalogussen kunnen groot worden.
4. **Combinatie met type-filter.** Component-ingang toont een type-dropdown
   (Applicatie/Server/Switch/etc.) vóór de zoeklijst. Default: ja.

## Bouw-fasering (indicatief, ná besluitvorming)

1. UI-hernoeming "Applicatie → Component" eerst (los issue, hoog effect).
2. Type-indicator op graph-nodes (klein, los).
3. Start-wijzer bouwen (één slice per ingang of alles tegelijk).
