# ADR-053 — Archiefwet als hard componentfeit

| | |
|---|---|
| **Status** | **Voorstel — vorm besloten, bouw ná ADR-052 slice 4a en 4b.** **MVP-onderdeel**, geen post-MVP-spoor (zie §Waarom MVP). Subknopen open (zie onder). |
| **Datum** | 2026-07-18 |
| **Beslissers** | Bert van Capelle (G. van Capelle Beheer B.V.) |
| **Gerelateerd** | ADR-052 (tenant-norm harde feiten — dit voegt een feit toe) · ADR-046 (levensfase/bedoeling/uitstap — het uitstap-slot dat dit feit **niet** heeft) · ADR-035 (registratiegat-signalen) · ADR-028 (BIV/componentrol als eigen-veld-feiten — de vorm die dit feit spiegelt) |
| **Grond** | `docs/Checkpoint-archiefwet-als-hard-feit-V045.md` (read-only) · `docs/Meting-gemma-functie-proces-relatie-V045.md` (read-only) |
| **Horizon** | `docs/horizon/Horizon-archiefwet-bewaartermijn-via-zaaktype.md` (de bewaartermijn-route, bewust buiten deze ADR) |
| **Invariant** | De checklist-score blijft de enige lifecycle-driver. Dit feit hangt náást de engine — het gatet, net als de rest van de norm (ADR-052), uitsluitend de menselijke klaarverklaring; het raakt het score-/lifecycle-/blokkade-pad niet. |

---

## Context / de gebruikersvraag

Bij een ontvlechting of uitfasering is *"waar blijft het archief?"* de vraag waar het bestuurlijk op
vastloopt. LIKARA brengt in beeld waar informatie leeft; zonder dit feit stelt het die vraag niet. De
consultant moet per systeem kunnen zien **of hier archiefbescheiden leven** — niet hoe lang ze bewaard
moeten blijven. Dat laatste (de bewaartermijn) hangt aan zaaktypen en kan een systeem niet dragen; het
is een eigen horizon (zie de Horizon-verwijzing) en bewust géén onderdeel van deze ADR.

De grond onder dit voorstel is de read-only opname `Checkpoint-archiefwet-als-hard-feit-V045.md`: die
stelde vast dat de norm een nieuw feit kan dragen, maar dat de drie-toestand-vorm nieuw eigen bouwwerk
vraagt en niet op het bestaande "bewust geen"-mechanisme meelift. Deze ADR legt de **vorm** vast; de
opslag- en schermkeuzes worden bij de bouw belegd.

## Waarom dit MVP is (en niet een post-MVP-spoor)

De archief-vraag is niet een nette toevoeging achteraf — ze is de kern van het migratie-/ontvlechtings-
verhaal waarvoor LIKARA bestaat. Een landschapsbeeld dat "waar leeft informatie" toont maar niet
"draagt dit systeem archiefbescheiden", laat juist het bestuurlijk zwaarste gat open. Het is bovendien
een **smal** feit dat past in de bestaande norm-machinerie (ADR-052). Daarom: MVP-onderdeel, in te
plannen zodra de norm bedienbaar is (besluit 6). Dit expliciet vastleggen voorkomt dat een latere sessie
het als "leuk later"-spoor wegzet.

---

## Besluit (kern)

1. **Eén hard componentfeit, in de taal van de wet.** Het label draagt het woord **"Archiefwet"**. Grond:
   dat is het begrip waar de gemeenteambtenaar op zoekt, en dat een verantwoordelijke én een
   toezichtcyclus kent. Een formulering als *"houdt gegevens vast"* is **verworpen** — geen referentie-
   taal voor de gebruiker (likara-ux: taal is een ontwerpbesluit, geen laklaag).

2. **Drie toestanden:** **ja** (hier leven archiefbescheiden) · **bewust geen** · **nog niet naar
   gekeken**. De derde is de stille toestand die vandaag het probleem is (afwezigheid die zich voordoet
   als een antwoord); de tweede is een **echt antwoord** en telt als *vastgesteld*, gelijkwaardig aan
   "ja" voor de norm-volledigheid. "Vastgesteld ≠ leeg" — dezelfde lijn als ADR-052 besluit 2.

3. **Nooit een bewaartermijn op het component.** Een termijn volgt uit zaaktype en resultaat en kan een
   systeem niet dragen. Een termijnveld op het componentscherm zou iets beloven dat LIKARA niet waar kan
   maken. Dit is een **harde grens**, geen voorlopige scope-inperking — de bewaartermijn-route is een
   eigen horizon (zie de Horizon-verwijzing), niet een latere uitbreiding van dit feit.

4. **Reikwijdte-afbakening — "bewust geen" betekent niet "hier staat niets belangrijks".** Dit feit dekt
   uitsluitend de **Archiefwet**. Er zijn systemen zónder archiefbescheiden die tóch data dragen die bij
   migratie niet mag verdampen — persoonsgegevens (AVG), bewijslast, bedrijfsvoeringsdata. Een antwoord
   *"nee, bewust geen"* op dit feit betekent daarom **niet** dat er niets van waarde in het systeem staat;
   het zegt alleen iets over de Archiefwet. Deze grens hoort expliciet in de ADR — zonder deze zin wordt
   het veld over een jaar gelezen als een algemeen "hier hoeft niets bewaard te blijven", en dat is fout.

5. **In de meegeleverde feitenverzameling, niet standaard verplicht.** Het feit hoort bij de platform-
   default die elke tenant krijgt (het zit in de kiesbare set `HARDE_FEITEN`); de **verplichtstelling**
   is een tenant-keuze (het zit **niet** in `DEFAULT_VERPLICHT`). Grond (uit het checkpoint): componenttype
   onderscheidt "bewaarplek" niet, dus standaard verplicht stellen laat bij de eerste reseed het **hele
   landschap tegelijk** oplichten met "nog niet naar gekeken" — óók op systemen waar het antwoord triviaal
   nee is. Dan wordt het **behang in plaats van signaal**. Zet de gemeente het zelf aan, dan is dat een
   besluit met een moment en een eigenaar. Dit is verenigbaar met de regel dat een tenant-wens de
   platform-default nooit versmalt (ADR-052 / likara-ux W4): het feit zit er **voor iedereen** in — alleen
   de **lat** is een keuze.

6. **Volgorde-eis (inhoudelijk, geen planning).** Bouwen kan pas **ná het norm-beheerscherm** (ADR-052
   slice 4a + 4b). Zonder dat scherm kan een gemeente het feit niet aanzetten, en een feit dat niemand kan
   verplichten is stille dode letter. Dit is een inhoudelijke voorwaarde, geen volgorde-voorkeur.

---

## De gefalsifieerde aannames (de kern van dit document)

Bij het overwegen van dit feit leken drie dingen vanzelfsprekend. De read-only opname weerlegde ze alle
drie. Dit expliciet vastleggen is de eigenlijke waarde van deze ADR — zonder deze sectie wordt het feit
over een paar maanden opnieuw te licht ingeschat.

- **Aangenomen: "bewust geen" lift mee op het bestaande mechanisme.** *Onjuist.* Het "bewust geen"-
  mechanisme (`component_bevinding`, ADR-052 slice 2) is **relatie-verankerd**: het leidt de positieve
  kant ("ja, er is een koppeling/contract") af uit het **bestaan van een echte registratie**, en de
  bevinding zelf legt alleen de *afwezigheid* vast. Archiefwet is een **eigen veld zonder relatie** — er
  is geen echte registratie die de "ja" kan dragen. De "ja"-toestand heeft in dat mechanisme geen plek.
  Archiefwet vraagt dus **eigen opslag**. ⚠ Keerzijde (subknoop 5, besloten): de gebruiker ziet tóch
  hetzelfde woord "bewust geen" — dat is een **taalkeuze, geen gedeeld mechanisme**. Het woord convergeert
  voor de gebruiker; de constructie **niet** convergeren.
- **Aangenomen: het gaat om een kleine groep componenten (grofweg één op zeven).** *Onjuist.*
  Componenttype/laag onderscheidt "bewaarplek" niet, dus de groep is niet vooraf te versmallen. ⚠ De
  dev-meting (19 componenten) is **te klein** om de verhouding hard te maken — de conclusie rust op het
  **ontbreken van een onderscheidend kenmerk**, niet op dat aantal. Praktisch gevolg: reken op een groot
  deel van het landschap, niet op een niche (dit voedt besluit 5).
- **Aangenomen: het uitstapwerk (ADR-046) biedt een slot voor een archiefdimensie.** *Onjuist.* Uitstap is
  in ADR-046 een **gebruiksfeit** (welke gemeente vertrekt, in welke tranche), verankerd op het grove
  organisatiegebruik — **niet component-scoped**. Er is geen component-slot "gaat uit én is bewaarplek".
  Dat signaal vraagt dus eigen bouwwerk (zie subknoop uitstap).

---

## Open subknopen (te beslissen vóór de bouw)

Geformuleerd als open vragen, niet als voorstellen. Elk met een **voorlopige richting**, geen besluit.

1. **Binair of drieledig antwoord?** Is het antwoord binair (`ja` / `bewust geen`, met leeg = niet
   gekeken), of hoort er een derde inhoudelijke waarde bij — bv. *"gedeeltelijk"* of *"onbekend bij de
   beheerder"*? Dit raakt de betekenis, niet de opmaak.
2. **De exacte labeltekst en de vraagzin op het scherm.** "Archiefwet" staat vast (besluit 1); de
   volledige vraagzin ("Leven er archiefbescheiden in dit systeem?" o.i.d.) en de antwoord-labels zijn
   nog te kiezen, getoetst tegen het randgeval (een fileshare, een database — niet alleen een zaaksysteem).
3. **Loopt het registratiegat-signaal vanzelf mee zodra het feit genormeerd is?** Uit het checkpoint: het
   per-component norm-badge draagt het feit pas zodra de "vastgesteld"-bepaling een tak voor archiefwet
   heeft; het aparte Signalering-registratiegaten-scherm draagt het **niet** automatisch. Te bepalen of dat
   laatste nodig is.
4. **Waar landt "gaat uit én is bewaarplek"?** Bij het uitstap-verhaal (ADR-046), in de werkvoorraad, of
   beide? De archiefdimensie is component-scoped, het uitstapfeit gebruiker-scoped — de verbinding is
   nieuw en moet een plek krijgen.
5. **Taalkeuze "bewust geen" — BESLOTEN (geen open subknoop meer); de opslagvorm blijft richting.** De
   term **"bewust geen" blijft voor de gebruiker gelijk** aan die bij koppelingen/contract. Reden: de
   consultant leest daar al "bewust geen" en begrijpt daaruit *ik heb gekeken, en het antwoord is niets*;
   bij de Archiefwet betekent het **exact hetzelfde**. Het verschil dat het checkpoint terecht signaleerde
   — bevinding op een relatie versus antwoordwaarde op een eigen veld — is **onze constructie, niet zijn
   ervaring**. Twee woorden voor één begrip zou hem laten denken dat er iets anders bedoeld wordt.

   > ⚠ **De waarschuwing die dit besluit draagbaar houdt.** Gedeelde woorden nodigen uit tot gedeelde
   > bouwstenen. Iemand die later twee keer "bewust geen" in de code ziet staan, zal ze conform de
   > n≥2-convergentieregel naar één mechanisme willen brengen. Dat is hier **fout**: het ADR-052-mechanisme
   > is relatie-verankerd en leidt de positieve kant af uit het bestaan van een échte registratie; het
   > Archiefwet-feit is een eigen veld zonder relatie. De overeenkomst is **taal voor de gebruiker, niet
   > constructie**. Convergeren zou een relatie-mechanisme oprekken naar een plek waar het niet past. (Dit is
   > de keerzijde van de gefalsifieerde aanname *"'bewust geen' lift mee"* hierboven — de twee wijzen naar
   > elkaar.)

   De **opslagvorm** zelf blijft **richting, geen besluit**: het checkpoint noemt een nullable enum-kolom op
   `component` (waarden `{ja, bewust_geen}`, NULL = niet gekeken; "vastgesteld = kolom IS NOT NULL" loopt
   vanzelf mee) als natuurlijke vorm; de definitieve drager (kolom vs. andere) wordt bij de bouw vastgesteld.

---

## Gevolgen

- De consultant kan bij uitfasering per systeem zien of er archiefbescheiden leven, in de taal van de wet
  — het bestuurlijk zwaarste gat wordt zichtbaar in plaats van stil.
- Een gemeente die het feit verplicht stelt, krijgt een werkvoorraad "nog niet naar gekeken" die ze
  bewust en op eigen moment aanzet — geen opgedrongen behang.
- Het feit belooft **nooit** een bewaartermijn; de scheiding tussen "draagt archief" (component-feit) en
  "hoe lang bewaren" (zaaktype-keten, horizon) blijft schoon.
- Nieuw bouwwerk t.o.v. vandaag: een eigen-veld-drager voor het drie-toestand-antwoord, de "vastgesteld"-
  tak in de norm-toetsing, en de scherm-bedrading (leesregel + keuzeveld) — bevestigd door het checkpoint
  als een kleine, zelfstandige feature, niet een meelifter.

## Alternatieven overwogen

- **"Bewust geen" hergebruiken (ADR-052 slice 2).** Verworpen op grond van de meting: relatie-verankerd,
  draagt geen positieve "ja" voor een eigen veld (zie gefalsifieerde aannames).
- **Een bewaartermijn-veld op het component.** Verworpen als harde grens (besluit 3): onwaarmaakbaar; de
  termijn hangt aan het zaaktype, niet aan het systeem.
- **Standaard verplicht stellen.** Verworpen (besluit 5): laat het hele landschap oplichten als "niet
  gekeken" → behang i.p.v. signaal.
- **Een neutralere/algemenere labeltekst** ("houdt gegevens vast"). Verworpen (besluit 1): geen
  referentietaal; de ambtenaar zoekt op "Archiefwet".
