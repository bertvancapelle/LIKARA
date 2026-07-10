# ADR-042 — Procesregister en component-in-proces-koppeling (proces-inzicht)

> **Nummering:** geland als ADR-042 (eerstvolgende vrije nummer, LI035).

**Status:** Gerealiseerd (LI035, V036) — alle 5 slices geland
(slice 1 proces+boom `cc43418` · slice 2+3 applicatiefunctie-catalogus+koppelregel `ddb7b7a` ·
slice 4a proces-schermen `3a65c3b` · slice 4b componentkant `0c4fe60` · slice 5 roll-up `8a76f55`).
**Ontwerpherzieningen tijdens de bouw (LI035, browsercheck):** (1) proces-detail = twee blokken —
"Componenten in dit proces" bovenaan, daaronder ÉÉN samengevoegd blok "Onderliggende processen"
(deelproces-kopjes + doorgerolde regels per tak via `tak_id`; pad-bijschrift alleen bij diepere
lagen); (2) roll-up **open-tenzij-groot** (±10 doorgerolde regels, uniek geteld, uitklapstand
onthouden via het lijststaat-patroon); (3) organisatie-proceskijk als afgeleide read-only sectie
"Processen" op de organisatie (eigendom + geregistreerd gebruik samengenomen, dedupe per proces,
eerlijke (i): "hier wordt niets geregistreerd").
**Datum:** 2026-07-08 (besloten) · 2026-07-09 (gerealiseerd)
**Relatie:** Bouwt op het element-subtype-recept (ADR-023), het roltoewijzing-patroon
(ADR-024), de gesloten ArchiMate-typering (ADR-026) en de werkpakket-boom (hiërarchie-
precedent). Basis: `docs/Feitenrapport-proces-functie-V035.md`.
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt
niet geraakt. De proceslaag is registratie + read-only inzicht.

---

## Context / aanleiding

LIKARA beantwoordt "wat raakt het als component X verandert of verdwijnt?" nu op het
niveau van applicaties, contracten, infrastructuur en beheer. Wat mist is de vraag die
de proceseigenaar en bestuurder stellen: **"welke processen raakt het?"** Daarvoor moet
een gebruiker kunnen vastleggen dat een component een rol vervult in een proces — en
moet dat inzicht omhoog optellen door de procesindeling heen.

**Begripsverheldering (GEMMA/ArchiMate, bepalend geweest voor het ontwerp):**
- **Proces** — wat de organisatie dóét; in GEMMA gelaagd (bedrijfsproces → werkproces →
  processtap). Eén nestbare as.
- **Bedrijfsfunctie** — wat de organisatie kán, los van volgorde (business-laag). Een
  ándere as die processen doorkruist; **bewust geparkeerd** als eigen, later ADR-spoor.
- **Applicatiefunctie** — wat een systeem dóét binnen een proces ("zaken registreren").
  In GEMMA de koppelbrug tussen applicatie en proces (Softwarecatalogus-lijn). In dit
  ADR: het wát-veld op de koppelregel.

Het oorspronkelijke backlog-kader sprak van "proces boven, functie eronder (één laag)".
Dat is in LI035 **bewust herzien**: het blad-element "functie" vervalt (een dieper
niveau is gewoon een dieper proces), en "functie" in de betekenis van het backlog-punt
blijkt de **applicatiefunctie** op de koppelregel te zijn. Redenen: aansluiting op hoe
gemeenten al denken (GEMMA is zelf gelaagd in processen), geen model dat GEMMA-kenners
op het verkeerde been zet (bedrijfsfunctie ≠ kind van proces), en een kleiner model
(één nieuw element i.p.v. twee).

---

## Besluiten (kern)

### 1. Proces = volwaardig element in de bestaande familie
Een proces is iets wat de gebruiker opzoekt, benoemt, toelicht en aanklikt — een
volwaardig registratie-object, conform het element-subtype-recept (eigen subtabel met
naam + toelichting; het supertype draagt geen naam). ArchiMate-typing:
`business_process` / business / behavior.
- De gesloten `TOEGESTANE_ELEMENTEN`-lijst (ADR-026) wordt met **business_process**
  uitgebreid — expliciet ADR-punt.
- Dit wordt de **tweede gemarkeerde behavior-uitzondering** op de OK-3-lijn, naast
  work_package; de partitietest beweegt mee.
- `business_function` wordt **niet** toegevoegd; de bedrijfsfunctie-as is geparkeerd.
  Het bestaande parkeermechanisme (`ELEMENT_TYPEN_NOG_NIET_GEREALISEERD`) wordt daar
  níét voor gebruikt — er komt in dit ADR geen functie-elementtype.

### 2. Processen zijn nestbaar; plek = niveau
- Een proces kan onder een proces hangen (bedrijfsproces → werkproces → desgewenst
  processtap). De diepte is de keuze van de gebruiker, per tak; geen dieptelimiet
  (vrijheid boven betutteling).
- **Geen niveau-label.** De plek in de boom ís het niveau; een label kan gaan liegen
  ("werkproces" bovenaan) en voegt niets toe. GEMMA-labels kunnen later desgewenst als
  afgeleide weergave.
- Constructie naar het **werkpakket-boom-precedent**: optionele ouder-verwijzing binnen
  hetzelfde type, een proces met deelprocessen verdwijnt nooit stil (verwijderen
  geblokkeerd zolang er kinderen zijn), verplaatsen = één veldwijziging, kringetjes
  structureel onmogelijk (directe zelf-verwijzing geblokkeerd; transitieve bewaking in
  de servicelaag, zoals bij werkpakketten).
- Overal waar processen buiten hun boomcontext verschijnen (pickers, lijsten): toon de
  procescontext ("Aanvraag behandelen — Vergunningverlening"), naar het bestaande
  identiteit-patroon; broodkruimel in de detail-kop.

### 3. Koppelregel (component, proces, applicatiefunctie) — component-breed
- **Elke regel = het tripel (component, proces, applicatiefunctie)**: "Zaaksysteem
  vervult *zaken registreren* in *Vergunningverlening*". Meerdere applicatiefuncties
  van hetzelfde component in hetzelfde proces = meerdere losse, elk apart verwijderbare
  regels. Niets dwingt één regel af.
- Dit spiegelt het **roltoewijzing-patroon** (ADR-024) 1-op-1: een eigen
  registratievorm, omdat de gewone relatielaag maar één regel per paar toestaat —
  exact dezelfde reden als destijds.
- **Component-breed:** élk componenttype is koppelbaar (ook database, SaaS-dienst,
  landelijke voorziening). De sectie heet "Componenten in dit proces".
- **Veldnaam = "applicatiefunctie"** (GEMMA-term, herkenbaar voor architecten), óók als
  de regel een niet-applicatie betreft; de (i)-uitleg vermeldt expliciet dat elk
  componenttype koppelbaar is.
- De **applicatiefunctie-catalogus** is een beheerbare platform-catalogus (soft-
  deactivatie, nooit hard weg), door de gebruiker zelf te vullen — desgewenst geënt op
  de GEMMA-lijst. Strikt ArchiMate zou de applicatiefunctie een eigen element zijn; wij
  kiezen bewust de lichte catalogusvorm — **gemarkeerde deviatie**, zoals bij de
  beheerrol.
- Koppelen kan op **elk niveau** van de procesboom (grof op het hoofdproces, fijn op
  het werkproces) — dat ís "begin grof".

### 4. Impact rolt omhoog — pure kijklaag
Op elk proces is zichtbaar wat er in de onderliggende processen speelt: een raakvlak op
"Aanvraag behandelen" telt zichtbaar mee op "Vergunningverlening", door de hele boom.
- **Niets wordt opgeslagen of herberekend** — het is altijd de actuele optelsom van de
  registraties eronder (read-only afleiding; boom-lezen cyclus-veilig).
- Vaste dubbele engine-borging per slice (import-afwezigheid + read-only bronscan +
  live geen-lifecycle-mutatie).

### 5. Schermen (fase "begin grof")
1. **Processen-lijstscherm** — eigen navigatie-ingang: de procesboom, zoeken, aanmaken/
   hernoemen, doorklik. Erft het lijststaat-patroon (`useLijstStaat`) vanaf dag één.
2. **Proces-detailpagina** — naam, toelichting, (i)-uitleg; deelprocessen mét
   "+ deelproces toevoegen" op de plek zelf (het proces is voorgevuld — actie waar het
   onderwerp leeft); sectie "Componenten in dit proces" (koppelregels toevoegen/
   verwijderen, per regel de applicatiefunctie) + het omhoog-gerolde beeld.
3. **Component-detailpagina** — nieuwe sectie "Vervult een rol in": processen mét
   applicatiefunctie; toevoegen kan óók hier (de gebruiker denkt vanuit beide kanten;
   dezelfde koppelregel, twee ingangen).
4. **Catalogus-beheerscherm** voor de applicatiefunctie — een beheerbare lijst zonder
   scherm is onvindbaar (bekende les).

**(i)-naleesbaarheid (vaste eis):** de begrippen zijn in het scherm zelf naleesbaar via
een (i)-uitleg op de plek waar de gebruiker ze tegenkomt, in gebruikerstaal mét
voorbeeld:
- *Proces* — wat de organisatie doet, van grof naar fijn nestbaar. Voorbeeld:
  Vergunningverlening → Aanvraag behandelen.
- *Applicatiefunctie* — wat een systeem dóét binnen een proces; geldt voor elk
  componenttype. Voorbeeld: Zaaksysteem vervult "zaken registreren" in
  Vergunningverlening.

**Bewust nog niet in deze fase:** het proces op de landschapskaart (raakt het
kaart-component-breed-ADR-spoor) en een signalering "component zonder proces" (eerst
registraties laten ontstaan). Flow/volgorde tussen processtappen blijft buiten scope.

> **Statusverwijzing (LI036/LI037):** het kaart-punt hierboven is inmiddels ingehaald —
> de **proceslaan** is geland met LI036 (zie ADR-034 §Proceslaan) en de **proces-diepte**
> (deelprocessen eerste-klas op de kaart) is besloten in LI037
> (zie ADR-034 §"Proces-diepte — besloten (LI037)").

---

## Invarianten

- **Engine onaangeroerd / score blijft enige lifecycle-driver.** De proceslaag is
  registratie + read-only inzicht; dubbele borging per slice.
- **Relaties/koppelingen altijd expliciet** — het systeem leidt geen proces-koppelingen
  af.
- **Structureel boven conventioneel** — de blad-/boomregels en de koppel-uniciteit
  worden door het schema afgedwongen, niet door afspraak.
- **Catalogus platform-breed** — de applicatiefunctie-catalogus volgt de vaste
  catalogus-regels (checklistvraag blijft de enige tenant-eigen catalogus).

## Gevolgen / meebewegers

- RBAC: nieuwe entiteiten volgens het `_INHOUD`-patroon; catalogus-beheer platform-
  gescoped; matrixtests bewegen mee.
- Audit: nieuwe tenant-entiteiten op de audit-allowlist; catalogus op de platform-
  allowlist.
- Seed/testdata: het BvoWB-scenario krijgt een herkenbaar procesvoorbeeld
  (bv. Vergunningverlening → Aanvraag behandelen, met Zaaksysteem-koppelregels);
  tests volgen de seed. Alleen testdata — reseed, geen datamigratievraagstuk.
- Enum-uitbreiding element-type volgens het bestaande precedent (aparte voorafgaande
  toevoeg-stap).
- ADR-026-lijst + OK-3-markering bewegen mee (besluit 1).

## Open subknopen (te beslissen vóór de bouw — met voorlopige default)

1. **Naamgeving element/tabel** (`proces`). *Default: `proces`.*
2. **Kenmerken op de koppelregel** naast de applicatiefunctie (toelichting?
   ingangsdatum?). *Default: alleen een optionele toelichting; uitbreiden kan later
   additief.*
3. **Catalogusvorm applicatiefunctie**: eigen single-purpose catalogus (zoals
   beheerrol/partijsoort) of nieuwe dimensie op de relatiekenmerk-catalogus. *Default:
   single-purpose (spiegel van beheerrol) — het is een zelfstandig begrip met eigen
   beheerscherm.*
4. **Startinhoud catalogus**: leeg beginnen of een kleine GEMMA-geënte startset seeden.
   *Default: kleine startset (herkenbaar beginnen), vrij uitbreidbaar/deactiveerbaar.*
5. **Roll-up-presentatie**: hoe het omhoog-gerolde beeld op de proces-pagina toont
   (telling + uitklap? aparte sub-sectie "incl. deelprocessen"?). *Default: directe
   koppelingen als lijst; roll-up als telling met uitklap — definitief bij het
   schermontwerp.*
6. **Zoek-/vindbaarheid componenten-sectie**: de component-picker in de koppelregel is
   component-breed (elk type) — bevestigen dat het bestaande componenten-zoekendpoint
   dit dekt. *Te valideren in de bouw-voorbereiding (read-only checkpoint).*

## Bouw-fasering (indicatief, ná subknoop-besluiten)

1. **Read-only checkpoint** (CC): aanhaking op bestaande code verifiëren (enum-stap,
   partitietest, picker-endpoint, catalogus-recept) vóór de eerste bouwslice.
2. **Proces-element + boom** (gate: schema/RBAC/audit/seed).
3. **Koppelregel + applicatiefunctie-catalogus + beheerscherm** (gate: schema).
4. **Schermen**: Processen-lijst + proces-detail + component-sectie (gate-per-slice,
   browsercheck vóór commit).
5. **Roll-up-inzicht** (read-only; dubbele engine-borging).

Elke slice met de gangbare gate-discipline; browsercheck bij elke UX-rakende slice.
