# ADR-036 — Organisatiegebruik van applicaties: grof gebruiksfeit + fijne verfijning

**Status:** Voorstel (functioneel besloten; bouw uitgesteld naar een verse sessie)
**Datum:** 2026-07-02
**Relatie:** Herdefinieert de betekenis van de gebruikersgroep (afdeling-van-één-organisatie) en
voert een grof "organisatie gebruikt applicatie"-feit in. De twee ontbrekende detailpagina's
(GebruikersgroepDetail + BlokkadeDetail) hangen aan dit besluit.
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt niet
geraakt. Puur registratief.

## Context / aanleiding

LIKARA is een generiek platform; in de canonieke voorbeeld-tenant levert een shared-services-
organisatie één applicatie (bv. een Zaaksysteem) aan meerdere organisaties (partijen van het type
organisatie). De natuurlijke vraag is dan een **applicatie**-vraag met meerdere organisaties als
antwoord: "welke organisaties gebruiken dit component?".

Vandaag kan dat alleen **indirect**: de enige plek om een organisatie aan een applicatie te hangen
is een **gebruikersgroep** (één afdeling, van één organisatie, met een aantal gebruikers, die één
applicatie bedient). Wie alleen het grove feit kent ("organisatie X gaat dit gebruiken") maar nog
geen afdeling of aantal, wordt gedwongen een half-lege groep te verzinnen — óf onwaarheid
registreren, óf het feit verliezen. Dat schuurt met het uitgangspunt: **registreren om zichtbaar
te maken wat je nog niet weet.**

## Besluit (functionele kern)

1. **"Organisatie gebruikt applicatie" wordt een eersteklas, op-zichzelf-vastlegbaar feit**
   (grof), los van een afdeling of aantal gebruikers. Onvolledig vastleggen is een **nette,
   geldige toestand** — LIKARA laat het staan en blokkeert niets.
2. **De gebruikersgroep blijft de fijne verfijning:** afdeling + organisatie + aantal gebruikers,
   ónder dat grove gebruiksfeit. Een groep **identificeert zich met afdeling + organisatie**
   (niet met de afdelingsnaam alleen — anders zijn drie "Burgerzaken"-groepen niet te
   onderscheiden).
3. **"Welke organisaties gebruiken dit component" op de applicatie is een afgeleide** van de
   vastgelegde gebruiksfeiten (∪ de groepen daaronder) — geen dubbele invoer.
4. **Signaal (read-only, geen blokkade):** een gebruiksfeit **zónder verfijning** (nog geen
   afdeling/aantal) wordt aangestipt — "gebruik bekend, detaillering ontbreekt" — zodat verdere
   invulling zichtbaar op de agenda staat. Nette toestand én zichtbaar gat, tegelijk.

## Invarianten

- Engine onaangeroerd; puur registratief/relationeel.
- Generiek platform: "organisatie" = partij van het type organisatie; nooit "gemeente" of een
  tenant-specifiek begrip in model/UI/terminologie.
- Onvolledig-mogen-registreren is een functie (signaleren, niet blokkeren).

## Open bouwknopen (te beslissen aan het begin van de bouwsessie — design-checkpoint first)

1. **Datamodel van het grove feit.** Is "organisatie gebruikt applicatie" een eigen relatie
   (organisatie-partij → applicatie, vermoedelijk `serving`/`association`) of een eigen tabel?
   Hoe verhoudt de bestaande gebruikersgroep (serving via component) zich ertoe — wordt de groep
   een **verfijning-van** het gebruiksfeit (expliciete koppeling), of blijven ze parallel met een
   afgeleide "gebruik = grove feiten ∪ organisaties-van-groepen"?
2. **Verschuiving van de bestaande afleiding.** De Landschapskaart-afleiding "gebruikt door
   organisatie(s)" loopt nu via de groepen; die moet meebewegen naar "grove feiten ∪ groepen"
   zonder dubbeltelling.
3. **Signaal-definitie.** Wanneer precies "detaillering ontbreekt" — geen enkele
   afdeling/verfijning onder het gebruiksfeit? Aantal onbekend? Kritiek of aandacht?
4. **Groep-identiteit in de UI.** Afdeling + organisatie als titel/identiteit overal waar een
   groep verschijnt (lijst, kaart-node, detail, doorklik).
5. **De twee detailpagina's** (GebruikersgroepDetail + BlokkadeDetail) worden **ná** dit besluit
   gebouwd; de grounding is al gedaan (zie OPVOLGPUNTEN). BlokkadeDetail heeft daarnaast eigen
   knopen (detail-read verrijken met herkomst; eigenaar = vrij tekstveld zonder structurele
   verantwoordelijke; objecthistorie-allowlist uitbreiden voor het 'i'-paneel).
6. **ArchiMate-typering** van het grove gebruiksfeit.

## Gevolgen

- Herdefinieert de gebruikersgroep-identiteit (afdeling + organisatie).
- Nieuw grof gebruiksfeit + nieuw read-only signaal.
- Kaart-afleiding "gebruikt door organisatie" verschuift.
- De twee ontbrekende detailpagina's wachten op dit besluit.
- Schema-rakend → meerdere gate-slices; start met een design-checkpoint (open knopen hierboven).
