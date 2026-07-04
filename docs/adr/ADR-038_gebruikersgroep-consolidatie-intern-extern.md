# ADR-038 — Gebruikersgroep-consolidatie: groep hoort altijd bij een organisatie, met intern/extern-kenmerk

**Status:** Besloten (Bert, sessie LI031)
**Datum:** 2026-07-04
**Relatie:** herziet de reikwijdte van **ADR-036** (organisatiegebruik + gebruikersgroep als
verfijning) en **ADR-036a** (afdeling structureel). Vult een lacune uit het partijenregister
(**ADR-024**): een intern/extern-kenmerk op organisaties — als **vlag, geen aparte tabel**. Raakt
de Landschapskaart-read (**ADR-031/036**) en de Signalering (**ADR-035**).
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt niet
geraakt. Dit is registratie/structuur/read, geen engine.

> **Discrepantie t.o.v. de aanleiding (bewust niet gladgestreken):** ADR-024 introduceerde de
> partij-*aard* `externe_partij` vs. `organisatie`, maar **geen intern/extern-vlag op
> organisatie-partijen**. Dit ADR voert dat kenmerk **nieuw** in; het "voltooit" ADR-024 niet in
> letterlijke zin, maar dicht een gat dat ADR-024 openliet.

## Context / aanleiding

Er bestaat vandaag een inconsistentie in hoe een gebruikersgroep aan een organisatie hangt:

- Een groep is meestal "afdeling binnen organisatie gebruikt applicatie", maar er is een
  **org-loze uitzondering**: technisch een groep waarvan `gebruik_id` NULL is — hij hangt onder
  géén grof gebruiksfeit (`gebruikersgroep.gebruik_id`, nullable; `models.py:484`). Daardoor is
  "van wie zijn deze gebruikers?" soms onbeantwoordbaar.
- Er is een aparte partij-aard **`burger`** (`PartijAard.burger`, `models.py:205`), maar die kan
  **niet** als groep-organisatie dienen: `partij_service.valideer_organisatie` eist `aard=organisatie`
  (`partij_service.py:117`). De organisatie-picker in de bewerk-dialog biedt burgers echter wél aan
  (`GebruikersgroepSectie.vue:15`, `aard_in: ['organisatie','burger']`), zodat een burger-keuze bij
  opslaan met **422 `ONGELDIGE_ORGANISATIE`** faalt — een latente bug. Burger-doelgroepen zijn
  bovendien niet in afdelingen te segmenteren.
- Er is **geen** intern/extern-kenmerk op organisaties, terwijl een shared-services-organisatie
  juist het onderscheid "onze eigen organisatie" vs. "deelnemende/externe organisatie" nodig heeft.

Concreet (BvoWB-tenant, ter illustratie — het platform blijft generiek): BvoWB is de eigen
organisatie (intern); Tiel, West Betuwe en Culemborg zijn deelnemende gemeenten — óók
`aard=organisatie`, maar extern. Vier organisaties, dezelfde aard, één intern, drie extern. Het
onderscheid volgt dus **niet** uit de aard.

## Besluit

1. **Een gebruikersgroep hoort altijd bij een organisatie.** De org-loze tak vervalt; een groep is
   voortaan altijd een afdeling binnen een organisatie. Dit wordt **structureel afgedwongen**
   (harde constraint), niet alleen via service-validatie. Mechanisme: `gebruikersgroep.gebruik_id`
   wordt verplicht (NOT NULL) — een groep hangt altijd aan een grof gebruiksfeit
   (`organisatiegebruik`), dat altijd een organisatie draagt (`organisatie_id` NOT NULL,
   `models.py:441`). Het exacte mechanisme wordt in de schema-slice bevestigd.

2. **Intern/extern wordt een kenmerk op organisatie-partijen.** Het is een **vrij kenmerk** dat de
   tenant per organisatie zet — **géén** "maximaal één interne organisatie"-constraint. In de
   praktijk markeert een tenant zijn eigen organisatie als intern en al het overige
   (partnerorganisaties, burger-doelgroepen) als extern, maar dat is een gebruikspatroon, geen
   afgedwongen wet. Intern/extern volgt **niet** uit de aard: twee `aard=organisatie`-partijen
   kunnen aan verschillende kanten van de grens staan.

3. **Burger-doelgroepen zijn gewone externe organisaties.** Een burger-doelgroep (bijv.
   "Burgers Tiel") is een `aard=organisatie`-partij met kenmerk **extern**, met afdelingen eronder
   ("Burgers Tiel — Agrariërs", "Burgers Tiel — Woningbezitters"). Geen nieuw mechanisme; de tenant
   registreert ze zelf. LIKARA dwingt alleen de structuur af en kent geen ingebouwd "burger"-begrip.

4. **De `burger` partij-aard wordt volledig verwijderd** uit de enum (inclusief de bijbehorende
   migratie). Na besluit 3 is ze overbodig en laat ze anders een dode aard-waarde achter die in
   pickers kan lekken (bron van de latente bug hierboven).

5. **Geen datamigratie — herzaaien.** Ontwikkelmodus, uitsluitend testdata: de org-loze seed-groepen
   en de losse "Burgers"-partij verdwijnen; de seed vertelt voortaan het schone verhaal
   (burger-doelgroepen als externe organisaties met afdelingen). Seed volgt de gebruikersstory,
   tests volgen de seed.

6. **Dode resten opruimen.** Het read-veld `gebruikt_door_organisatieloos`
   (`schemas/landschapskaart.py:47`; nergens in de frontend geconsumeerd) en het signaal
   `gebruikersgroep_zonder_organisatie` (`registratiegaten_service.py:277`; kan na besluit 1 nooit
   meer vuren) worden verwijderd, inclusief hun labels en tests. Een dode vlag of een signaal dat
   nooit afgaat is geen acceptabele reststaat.

## Model in detail (intent — mechanisme te bevestigen in de schema-slice)

- **Intern/extern leeft op de organisatie.** Het kenmerk is alleen betekenisvol op
  `aard=organisatie`. Een `externe_partij` (leverancier/ketenpartner) is per aard al extern — geen
  vlag nodig. Afdelingen (`organisatie_eenheid`) en personen **erven** intern/extern van hun
  ouder-organisatie; ze dragen het niet zelf. Schoonste dragervorm (te bevestigen): een kolom op de
  organisatie, met afgeleide lezing voor sub-partijen.
- **Groep-organisatie blijft `aard=organisatie`** (ongewijzigde validatie `valideer_organisatie`):
  niet `externe_partij`, en — na verwijdering — niet `burger`. Burger-doelgroepen passen daar
  precies in als externe `aard=organisatie`-partijen.
- **Afdeling-structuur blijft ADR-036a**: `gebruikersgroep.afdeling_id` → een `organisatie_eenheid`
  binnen de organisatie van het grove feit. Doordat een groep nu altijd een organisatie heeft, is de
  ADR-036a-uitzondering "org-loze groep draagt geen afdeling" niet langer bereikbaar; de
  `_valideer_afdeling`-tak die dat afving (`gebruikersgroep_service.py:129-131`) wordt dood.
- **De vier seed-organisaties** krijgen expliciet hun kant: BvoWB **intern**; Tiel, West Betuwe,
  Culemborg **extern**; burger-doelgroepen **extern**.

## Invarianten / borging

- **Engine onaangeroerd**: geen lifecycle/score/blokkade; score blijft de enige lifecycle-driver.
  Dubbele engine-borging per slice.
- **Structureel boven conventioneel**: de "groep hoort bij organisatie"-regel wordt door het schema
  afgedwongen (`gebruik_id` NOT NULL), niet door conventie. De nette 422 blijft in de service.
- **Geen afgeleide/impliciete intern/extern**: het is een expliciet geregistreerd kenmerk; het
  wordt nergens uit de aard of uit relaties geraden.
- **Sub-partijen dragen het kenmerk niet zelf**: afdeling/persoon lezen het van hun
  ouder-organisatie — één bron van waarheid, hernoemen/omzetten werkt overal door.

## Gevolgen

- Lost de latente burger-picker-bug op (een keuze die bij opslaan faalde).
- Geeft de gebruiker één consistent model — "een groep is altijd een afdeling van een organisatie" —
  plus segmentatie van burger-doelgroepen via afdelingen.
- Levert de intern/extern-lens op het landschap (eigen organisatie vs. deelnemende/externe partij).
- **Raakt**: schema/migratie (**gate**); seed + tests (**doorloop**, data); invoerdialog + labels
  (**doorloop**, frontend); kaart-read + signaal-opschoning. **RBAC/audit**: niet geraakt door
  org-loosheid; het nieuwe kenmerk volgt het bestaande partij-patroon als het een eigen veld krijgt.
- De org-loze seed-groepen (`dev_seed_testdata.py:1428-1430`) en de losse "Burgers"-partij (`:1050`)
  verdwijnen bij reseed; geen databehoud-migratie (dev-fase, geen productiedata).

## Open subknopen (te bevestigen in de schema-slice — met default)

1. **Dragervorm intern/extern.** Kolom op het organisatie-subtype (`partij`), met afgeleide lezing
   voor afdeling/persoon. — *Default: ja, kolom op de organisatie; sub-partijen erven.*
2. **Handhaving "groep altijd organisatie".** Harde DB-constraint (`gebruik_id` NOT NULL) náást de
   service-validatie. — *Default: beide — constraint als structurele borging, service voor de nette 422.*
3. **Default-waarde intern/extern bij aanmaken.** — *Default: extern (veilig — de gebruiker markeert
   bewust wat intern is).*
4. **Externe_partij t.o.v. het kenmerk.** — *Default: extern vast door de aard; geen vlag op
   `externe_partij`.*

## Bouw-fasering (indicatief — ná dit ADR, elke slice met gate-discipline)

- **Slice 1 — schema-consolidatie (GATE):** `gebruik_id` verplicht + intern/extern-kenmerk op
  organisatie + `burger`-aard verwijderen (enum + migratie); `_valideer_afdeling`-tak snoeien;
  signaal (`gebruikersgroep_zonder_organisatie`) + kaart-veld (`gebruikt_door_organisatieloos`)
  opschonen; backend-tests herzien. Dubbele engine-borging.
- **Slice 2 — seed herzaaien (doorloop, data):** org-loze groepen + losse Burgers-partij weg;
  burger-doelgroepen als externe organisaties met afdelingen; de vier organisaties intern/extern
  gezet; tests op de nieuwe seed herijken.
- **Slice 3 — invoer & labels (doorloop, frontend):** organisatie verplicht in
  `GebruikersgroepSectie`, burger uit de picker, org-loze tak weg; velduitleg + frontend-tests;
  intern/extern zichtbaar en instelbaar waar een organisatie wordt geregistreerd.
- **Daarna:** GebruikersgroepDetail op het schone model (top-5 #1), met de partij-kant-ingang als
  eigen slice.

## Alternatieven overwogen

- **Org-loosheid behouden en alleen de picker repareren.** Verworpen: laat "van wie zijn deze
  gebruikers?" onbeantwoordbaar en houdt twee ongelijke concepten (org-loos vs. burger-aard) in stand.
- **Intern/extern uit de aard afleiden** (bijv. `externe_partij` = extern, `organisatie` = intern).
  Verworpen: een deelnemende gemeente is `aard=organisatie` maar extern — de aard draagt het
  onderscheid niet.
- **`burger` als aard laten staan en als groep-organisatie toestaan.** Verworpen: dan bestaan er twee
  wegen naar hetzelfde (aard `burger` én `aard=organisatie` extern), en de aard-eigen CHECK verbiedt
  afdelingen onder een `burger`-partij — segmentatie zou onmogelijk blijven.
