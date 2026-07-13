# Verkenning — wat raakt de bedrijfsfunctie in GEMMA? (context rond het BF-filter)

| | |
|---|---|
| **Opdracht** | LI039-verkenning-gemma-context (read-only; niets gebouwd, niets gewijzigd) |
| **Datum** | 2026-07-13 |
| **Bestand** | `export/GEMMA release.xml`, commit `de0984717e69` (2026-07-01 "Release: Actief openbaarmaken") — **exact dezelfde stand als `Verkenning-GEMMA-AMEFF-V040.md`** (13.411.843 bytes; het scratchpad-exemplaar van 12 juli was gewist, opnieuw opgehaald gepind op die commit). Werkplek: sessie-scratchpad, búíten de repo. |
| **Doel** | Ontwerpbesluit van Bert voeden. **Geen bouwvoorstel, geen scope-uitbreiding; gate 1b blijft zoals besloten.** |

**Getoetste hypothese:** legt GEMMA een keten referentiecomponent → (applicatiefunctie) → bedrijfsfunctie, zodat het consultant-gesprek van *invullen* naar *bevestigen of afwijken* kan?

**Antwoord in één zin:** de keten bestaat — via **ApplicationService** als brug (er zit géén ApplicationFunction in het bestand) — en dekt **ongeveer de helft**: 126/256 referentiecomponenten (49%) hebben er een directe route over, 138/297 bedrijfsfuncties (46%) worden erdoor geraakt; de relaties zelf zijn **kaal** (geen verplicht/optioneel, geen primair/ondersteunend). Details en tegenvoorbeelden hieronder.

---

## A. De 26 elementtypen — wat het filter weggooit

Totaal **2.752 elementen** (26 typen) en **5.800 relaties**. Het BF-filter houdt 297 elementen; **2.455 elementen van 25 andere typen** vallen buiten scope:

| Aantal | Type | In gewone taal |
|---:|---|---|
| 522 | Constraint | **Standaarden en normen** (AI-verordening, SETU, IMGeo, DKIM, CMIS, …) — zie E |
| 507 | BusinessObject | Bedrijfs-/informatieobjecten ("zaak", "nummeraanduiding") — het GGM-informatiemodel, zie E |
| 426 | ApplicationService | Applicatieservices ("Registreren en delen van zaken") — dé brug in de keten, zie C |
| **297** | **BusinessFunction** | **Bedrijfsfuncties — wat we houden** |
| 256 | ApplicationComponent | **De GEMMA-referentiecomponenten** (Zaakregistratiecomponent, Burgerzakencomponent, …) |
| 176 | BusinessProcess | Bedrijfsprocessen — zie D |
| 142 | Grouping | Groeperingen (domeinen, categorieën als "Basisregistraties") |
| 81 | BusinessService | Bedrijfsservices (diensten aan burger/bedrijf) |
| 57 | SystemSoftware | Systeemsoftware (technologielaag) |
| 48 | BusinessRole | Bedrijfsrollen |
| 48 | TechnologyService | Technologieservices |
| 43 | ApplicationInterface | **Koppelvlakken/API's** — zie E |
| 31 | BusinessActor | Actoren (organisaties/instanties) |
| 26 | Capability | Vermogens (capability-map) |
| 23 | Principle | Architectuurprincipes |
| 22 | Goal | Doelen |
| 14 | DataObject | Gegevensobjecten (applicatielaag) |
| 9 | Driver | Drijfveren |
| 6 | Product / BusinessCollaboration / Value | Producten, samenwerkingen, waarden (elk 6) |
| ≤2 | BusinessInteraction (2), BusinessEvent, Contract, BusinessInterface, Artifact (elk 1) | Restant |

Relatietypen (5.800): 2.145 Aggregation · 1.388 Realization · 800 Association · 521 Serving · 493 Specialization · 181 Flow · 79 Assignment · 68 Composition · 62 Triggering · 40 Influence · 23 Access.

---

## B. Alles wat de bedrijfsfunctie rechtstreeks raakt

**528 relaties** hebben een BusinessFunction aan minstens één kant, in 8 groepen:

| Aantal | Relatietype | Andere kant | Richting | Concreet voorbeeld |
|---:|---|---|---|---|
| 302 | Aggregation | BusinessFunction | BF↔BF | 'Producten en diensten publicatie' → 'Burgerlijke stand diensten' — **de functieboom die we al kennen** |
| **190** | **Serving** | **ApplicationService** | **service → BF** | 'Beheren van openbaar toegankelijk gepubliceerde informatie' *bedient* 'Actieve openbaarmaking van informatie' — **dé schakel naar de applicatielaag** |
| 20 | Aggregation | Grouping | domein → BF | Grouping 'Fysieke leefomgeving' aggregeert 'Opdrachtbewaking' (de bekende domein-as) |
| 7 | Serving | BusinessProcess | BF → proces | 'Financieel management' bedient 'Beheren financiën' |
| 5 | Serving | BusinessProcess | proces → BF | 'Uitvoeren juridische ondersteuning' bedient 'Juridische ondersteuning' |
| 2 | Serving | BusinessFunction | BF↔BF | 'Autorisatievaststelling' bedient 'Automatiseringsmanagement' |
| 1 | Access | BusinessObject | BF → object | 'Ontvangst' raakt bedrijfsobject 'zaak' |
| 1 | Serving | BusinessInterface | BF → kanaal | 'Klant- en keteninteractie' bedient 'Kanaal (nieuw)' |

Buiten de al bekende boom (302) en domein-as (20) is er dus in de praktijk **één substantieel nieuw verband: de 190 Serving-relaties vanuit applicatieservices.** Al het andere is enkelcijferig.

---

## C. De keten naar de referentiecomponenten — de kern

### C1. Referentiecomponenten bestaan: 256 stuks
Type `ApplicationComponent`, herkenbare namen (Zaakregistratiecomponent, Burgerzakencomponent, Documentregistratiecomponent, …), deels gegroepeerd in Groupings als "Basisregistraties" (13) en "Referentiecomponenten met ondersteuning voor BIO maatregelen" (28).

### C2. Het pad bestaat — via ApplicationService, níét via ApplicationFunction
Er zit **geen enkel ApplicationFunction-element** in het bestand. De keten is:

> **referentiecomponent =Realization⇒ applicatieservice =Serving⇒ bedrijfsfunctie**

Concreet voorbeeld (compleet):
- **Burgerzakencomponent** =realiseert= 'Ondersteunen van burgerlijke stand diensten' =bedient= BF **'Burgerlijke stand diensten'** (en zo ook → 'Officiële documenten verstrekking' en → 'Nederlanderschap diensten').
- **Documentregistratiecomponent** =realiseert= 'Registreren en delen van documenten' =bedient= **drie** BF's: 'Documentcreatie', 'Output archivering', 'Informatieextractie en opslag'.

**Eerlijk tegenvoorbeeld — precies het hypothese-voorbeeld:** de **Zaakregistratiecomponent** realiseert 'Registreren en delen van zaken', maar die service **bedient geen enkele bedrijfsfunctie**; hetzelfde geldt voor de Zaakafhandelcomponent ('Beheren van zaken' → niets). Het zaaksysteem-gesprek uit de hypothese wordt door deze keten dus **niet** vooringevuld — dat zit in het 51%-gat.

### C3. Dekking — het cijfer

| Meting | Cijfer |
|---|---|
| Referentiecomponenten met de directe keten (Realization → Serving) | **126/256 = 49%** |
| Bedrijfsfuncties die daardoor geraakt worden | **138/297 = 46%** |
| Ruimer gezocht (≤3 hops, ook via Flow/Specialization-omwegen) | 147/256 (57%) AC's; 144 (48%) BF's |
| Applicatieservices gerealiseerd door ≥1 component | 269/426 |
| Applicatieservices die ≥1 BF bedienen | 157/426 |
| Services die de **complete brug** vormen (beide kanten) | 141 |
| BF's per gekoppeld component | gemiddeld 1,5 (89× één, 24× twee, 10× drie, max 7) |

**Waar landt het?** Vrijwel volledig op subfunctie-niveau: van de 148 direct bediende functies liggen er 54 op niveau 2 en 77 op niveau 3 van de boom; **132 van de 148 zijn bladeren**. Van alle 231 blad-functies wordt **57%** geraakt. De keten spreekt dus de taal van de fijnste laag van de boom — niet van de 8 wortels.

**Wie ontbreekt?** 109/256 componenten hebben geen enkel pad (≤3 hops); 39 realiseren zelfs geen enkele applicatieservice. De pad-lozen concentreren zich bij **externe/landelijke voorzieningen** (Overheid.nl, Risicokaart.nl, GWV, Ondernemersplein.nl, BRO) en **voorbeeld-placeholders** (Informatiesysteem A/B/C, Taak-specifiek component 1/2) — maar dus óók bij kern-componenten als de zaakcomponenten (C2). Aan de functiekant blijven 159 BF's onbediend, waaronder herkenbare als 'Juridische advisering', 'Werving en selectie', 'Marketing en promotie' (veel ondersteunende functies).

### C4. Kwalificatie: de keten is kaal
De Realization (component→service) en Serving (service→BF) relaties dragen **geen kwalificatie**: geen naam, geen Verbindingsrol, geen documentatie op de 190 service→BF-relaties (alle 190 zijn naam- en rol-loos). Er bestáát in het bestand wel een kwalificatie-mechanisme — de property **"Verbindingsrol"** met waarden **Verplicht (323×) / Aanbevolen (435×)** — maar die zit op **component→Constraint** (standaarden, zie E) en koppelvlak→component, **niet** op de functie-keten. "Primair/ondersteunend" of "verplicht/optioneel" op component↔functie moet dus van de gemeente komen.

---

## D. Bedrijfsprocessen ↔ bedrijfsfuncties: GEMMA legt dit verband vrijwel niet

**12 directe relaties in totaal**, beide via Serving: 7× functie→proces (vb. 'Financieel management' bedient 'Beheren financiën') en 5× proces→functie (vb. 'Uitvoeren juridische ondersteuning' bedient 'Juridische ondersteuning'). Op 176 processen × 297 functies is dat verwaarloosbaar.

De processen leven in hun **eigen** structuur: 102 Aggregations + 31 Compositions proces→proces (eigen hiërarchie), 57 Triggerings (procesketens), 45 Assignments vanuit BusinessRole, 13 Realizations naar BusinessService. Relevant voor ADR-043: het "proces als verdieping onder de functie" wordt door GEMMA **niet voorgekauwd** — dat verband moet (op 12 uitzonderingen na) van de gemeente zelf komen. GEMMA levert wél een proceshiërarchie-structuur die naast de functieboom staat.

---

## E. Wat verder opvalt (feitelijk, zonder aanbeveling)

1. **Constraint = een compleet standaardenregister mét verplicht/aanbevolen per referentiecomponent.** 522 Constraints zijn standaarden/normen (AI-verordening, SETU, IMGeo (BGT), CMIS, DKIM, SuwiML, …) met properties als Status (323), Versieaanduiding (319), URL (198), Beheerder (197), Compliancy (94). Er lopen **749 Realization-relaties component→standaard**, waarvan vrijwel alle een **Verbindingsrol Verplicht/Aanbevolen** dragen (vb. 'Bestuur- en Raadsinformatiecomponent' realiseert 'imORI'). Dit is het enige deel van het bestand waar verbanden gekwalificeerd zijn.
2. **BusinessObject = het Gemeentelijk Gegevensmodel (GGM).** 503/507 objecten dragen GGM-properties (guid, uml-type, exportdatum); 636 object↔object-Associations en 158 Specializations vormen samen een informatiemodel ("zaak", "nummeraanduiding", "boring", …). Het raakt de bedrijfsfunctie exact één keer (B).
3. **ApplicationInterface = koppelvlakken.** 43 stuks; 196 Serving-relaties koppelvlak→component (mét Verbindingsrol), en 47 Realizations koppelvlak→standaard — "welk koppelvlak hoort bij welk component en welke standaard hoort daarbij".
4. **BusinessService (81)** verbindt de dienstenkant: 43 gerealiseerd door componenten, 13 door processen, 10 bedienen een proces.
5. Relaties dragen regelmatig **namen** (761 Realizations, 649 Associations, 206 Servings) en soms documentatie — leesbare etiketten die bij een BF-only-filter buiten beeld blijven.

---

## Wat dit zou kunnen betekenen voor LIKARA (strikt beschrijvend)

- **De hypothese klopt gedeeltelijk, met een gemeten dekking van ~50%.** Voor 126 van de 256 referentiecomponenten (en 46% van de functies, geconcentreerd op blad-niveau) zou het consultant-gesprek van *invullen* naar *bevestigen of afwijken* kunnen verschuiven — GEMMA levert daar de suggestie "dit componenttype ondersteunt déze functies" kant-en-klaar, gemiddeld 1,5 functie per component. Voor de andere helft — inclusief het zaaksysteem, hét voorbeeld uit de hypothese — verandert er niets: daar blijft het gesprek invullen.
- **Elke kwalificatie op die keten zou van de gemeente moeten komen.** De component→functie-verbanden zijn kaal; het Verplicht/Aanbevolen-mechanisme dat GEMMA elders hanteert bestaat wel, maar niet hier.
- **De proces-als-verdieping uit ADR-043 wordt door GEMMA noch geleverd, noch gehinderd.** Het proces↔functie-verband is er feitelijk niet (12 relaties); een gemeente die haar processen onder functies hangt begint daar op nul, met wel een GEMMA-proceshiërarchie als mogelijke structuurbron.
- **Twee registers in het bestand liggen buiten de hypothese maar zijn dicht bij LIKARA-begrippen:** een standaardenregister mét verplicht/aanbevolen-kwalificatie per referentiecomponent (749 relaties — de hoogste dekking én de enige gekwalificeerde laag in het hele bestand), en het GGM-informatiemodel (503 objecten). De koppelvlakken (43) verbinden componenten met die standaarden.
- **Het BF-filter van gate 1b gooit dit alles bewust weg** — deze verkenning legt vast wát, met cijfers, zodat dat een geïnformeerde keuze is en geen stille.

**Geen aanbeveling, geen bouwvoorstel. Bert beslist.**

---

*Meetmethode: drie read-only Python-analyses op het AMEFF-bestand in het sessie-scratchpad (`analyse_gemma.py`, `analyse_gemma2.py`, `analyse_gemma3.py` — niet in de repo). Paden gezocht met BFS ≤3 hops over alle relatietypen; "directe keten" = exact Realization(AC→AppService) + Serving(AppService→BF).*
