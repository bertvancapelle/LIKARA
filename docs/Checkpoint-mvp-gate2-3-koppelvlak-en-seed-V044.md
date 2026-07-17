# Checkpoint — bedrijfsfunctie-as vóór het ordenen van de MVP-restlaag (V044)

**Aard:** read-only feitenopname. Niets gewijzigd, niets gemigreerd, niets geseed, niets gecommit.
**Grond:** schone `master`, commit `5c4e479` (V044). Live stack draaide (11u up) → live-DB read-only geteld als lk_admin, náást de seed-broncode.
**Discipline:** de code spreekt. Waar de hypothese in de opdracht afwijkt van de gebouwde realiteit, staat dat expliciet benoemd.

---

## Blok 1 — De koppel-flow: kan de consultant vandaag al een systeem aan een functie-plek hangen?

**Bevinding: JA — dit is grotendeels gebouwd, niet "besloten, nog te doen".**

De consultant koppelt vandaag al een systeem aan een bedrijfsfunctie, grof én fijn, met directe opslag.

1. **De koppelregel bestaat** — `functievervulling` (tabel/service/route/schema, ADR-049 gate 2a).
   - Service `functievervulling_service.py`; route `functievervulling.py`; migratie `0069_adr049_functievervulling.py`.
   - Velden: `component_id`, `functie_id`, `ouder_functie_id`, `toelichting`, `oordeel`, `geen_systeem`, `verklaard_door_sub`, `verklaard_door` (+ `TimestampMixin`).
   - **Het anker is het ADRES van de plek**, niet `relatie.id`: `functie_id` + `ouder_functie_id` (NULL = grof "geldt overal", gevuld = fijn "déze plek"). Bewust anders dan `procesvervulling`, dat een tripel met applicatiefunctie draagt (functievervulling_service.py:3-6).
   - **Uniciteit:** pre-check op `(component_id, functie_id, ouder_functie_id)` ⇒ 409 `KOPPELING_BESTAAT`; de partiële UNIQUE is de DB-backstop (functievervulling_service.py:146-158).

2. **Grof vs. fijn (ADR-044 besluit 2) — GEBOUWD, als LEESLAAG.** "Verfijnen vervangt het grove op díé plek" leeft één keer, in `dekking_overzicht` (functievervulling_service.py:352-487), read-only, **nooit opgeslagen**. Op een plek met een fijn antwoord wint dat; het grove wordt uit *beeld* gedrukt maar blijft in de DB bestaan (`verdrongen[]` + `grof_totaal_plekken`/`grof_geldt_op` worden meegeleverd, functievervulling_service.py:463-486). Verwijder je de fijne koppeling, dan wordt het grove antwoord automatisch weer leesbaar (verwijder, :239-246). De vervanging is dus geen schrijfactie — precies de ADR-049-invariant.

3. **Waar leeft de koppel-UX** — vanaf het **systeem** (componentdetail), niet vanaf de functie:
   - `ComponentBedrijfsfunctieSectie.vue` ("Waarvoor gebruiken we het"), gemount in `ComponentDetail.vue:474` én `ComponentFormulier.vue:407` (aanmaak-overlay).
   - Picker = `ZoekSelect` op bedrijfsfuncties (filtert vervallen weg, :79-86); scope-radio grof/fijn (:277-294); plek-keuze uit `gekozenFunctie.ouder_ids` (:288-294). Endpoint: `POST /functievervullingen` (`api.functievervullingen.maak`).
   - De componentkant leest de gedeelde leesregel via `GET /functievervullingen/component/{id}` (`overzicht_voor_component`, :506-585) — indexeert `dekking_overzicht` her op dit component; **rekent de verdringing nooit zelf na** (bronscan-geborgd, :509-514).
   - De **functiekant** (per-plek registreren, incl. "geen systeem") leeft in `BedrijfsfunctieLijst.vue` (de functieboom).

4. **Wie/wanneer op het feit (LI040-scope) — server-gestempeld, NIET als leeslaag getoond.**
   - `maak_aan` stempelt `verklaard_door_sub` + `verklaard_door` uit `huidige_actor()` (:163-168); `functievervulling` staat in `AUDIT_TENANT_ENTITEITEN` (audit.py:74).
   - Maar `dekking_overzicht`/`overzicht_voor_component` geven **geen** `verklaard_door_naam`/`created_at` terug; `ComponentBedrijfsfunctieSectie` toont wie/wanneer niet. Wie/wanneer is dus **audit als vangnet, niet als leeslaag op de plek** — conform de gate-2/LI040-intentie.

**Checkvraag (raakt "verfijnen op één plek" een meervoudig geplaatste functie?):** Nee, geen stille functie-brede verdringing. Een fijne koppeling wordt opgeslagen op `(functie, ouder)` en `dekking_overzicht` sleutelt `fijn_per_plek` op exact dat paar (:415, :460). Grof (`ouder=None`) geldt over álle plekken van de functie; fijn verdringt uitsluitend zijn eigen plek. De consultant kiest expliciet wélke plek hij verfijnt (`plekOpties` uit `ouder_ids`). **Geen stille "eerste ouder"-keuze.**

---

## Blok 2 — Het gat per plek: plek-gebonden, en draagt het alle standen?

**Bevinding: JA — plek-gebonden, vijf standen, één gedeelde bron.**

1. **Teleenheid = de plek** (ADR-044 besluit 4). `plek_standen` (functievervulling_service.py:588-666) sleutelt per `(functie_id, ouder_functie_id)`. Zowel de boom-cue (`BedrijfsfunctieLijst`) als de centrale signalering (`WerkvoorraadPlekView` in `SignaleringView` tab "werkvoorraad") lezen `GET /functievervullingen/standen` — dezelfde `plekken` + gedeelde `tellers`; het venster rekent zelf niets (WerkvoorraadPlekView.vue:7-8, 67-68). `plek_standen` leunt zélf op `dekking_overzicht` → **één afleiding, twee vensters**.

2. **De vijf standen bestaan alle vijf** in `tellers` (functievervulling_service.py:643): `gat` / `via_boven` / `hier` / `werkvoorraad` / `niets` (+ hulp-teller `zonder_oordeel`). `gat` en `werkvoorraad` worden onderscheiden (beide "er ligt werk"), maar delen op de kaart bewust één amber-kleur; het onderscheid leest de consultant via de pill-tekst (`standCodering.js:24-58`, `STAND_LEGENDA` :68-73). De stand-presentatie leeft in één bron (`standCodering.js`), gedeeld door lijst-pill + kaart-canvas + legenda (kaart resolvet hetzelfde token via `standKaartKleur`, :100-110).

3. **"Fijn verdringt grof bij lezen, nooit bij schrijven" — gebouwd.** Zie blok 1.2. De leeslaag meldt dát er een grof antwoord onder zit (`verdrongen[]`) en telt de reikwijdte van het grove (`grof_geldt_op` van `grof_totaal_plekken`, in de UI: "geldt op X van de N plekken", ComponentBedrijfsfunctieSectie.vue:54-62).

**Checkvraag (telt een plek gedragen door alléén een fileshare/noodgreep als groen of als gat?):**

> **Let op — de hypothese in de opdracht is achterhaald.** De opdracht verwijst naar "ADR-045 besluit 2-keerzijde: besloten dat dit een gat is". Die harde ontwerpeis is door **ADR-051 besluit 3 expliciet verworpen** (ADR-051:78-97, "Wat dit ADR herijkt" :133): *"Een fileshare is niet inherent een noodgreep."* Het noodgreep-oordeel is verhuisd van het **componenttype** (ADR-045) naar de **koppeling/plek** (`oordeel`: naar_behoren / noodoplossing / leeg), voor élk componenttype.

Feitelijk in de code:
- Een plek gedragen door een component (welk werk-ondersteunend type ook) staat op `hier` of `werkvoorraad` — de split hangt **uitsluitend** af van `heeft_gebruikersgroep` (functievervulling_service.py:655), **niet** van het componenttype en **niet** van het `oordeel`.
- `fileshare` heeft `ondersteunt_werk = True` (seed_componentconfig.py:39) → een fileshare **kan** de enige drager zijn en leest dan als `hier`/`werkvoorraad` (dus "gedekt"), **niet** als `gat`.
- Het `oordeel` (incl. `noodoplossing`) verandert de stand niet; het voedt alleen de aparte teller `zonder_oordeel` (:656-657).

**Conclusie:** conform de gebouwde beslissing (ADR-051) is een fileshare-/noodgreep-gedragen plek géén gat. Het "riskant maar draaiend"-verhaal loopt via de **oordeel-as** (naar_behoren/noodoplossing/nog niet beoordeeld), niet via de stand-kleur. Dit is een bewuste keuze, geen defect — maar het is een **breuklijn t.o.v. de opdracht-premisse** en verdient een expliciete bevestiging vóór stap 2/3 (zie blok 6).

---

## Blok 3 — "Hier gebruiken we niets" als bevinding

**Bevinding: JA — volledig registreerbaar, backend én frontend, en onderscheiden van "nooit naar gekeken".**

1. **Registratiepad bestaat.** `POST /functievervullingen/geen-systeem` → `registreer_geen_systeem` (functievervulling_service.py:279-303): schrijft een `Functievervulling`-rij met `component_id=None, geen_systeem=True` (XOR-CHECK: nooit component én bevinding op dezelfde rij; `_weiger_tegengesteld` weert een koppeling én bevinding náást elkaar op dezelfde plek, :186-207). **Frontend:** dialoog in `BedrijfsfunctieLijst.vue` (`geenSysteemRij`, :674-702, `api.functievervullingen.geenSysteem`), per plek op de functieboom. Ook zichtbaar op de kaart-popup (`lk-popup-geen-systeem`).

2. **"Bevinding" (vastgestelde uitkomst) vs. "nooit naar gekeken" — onderscheiden en zichtbaar.**
   - Bevinding → stand `niets` (grijs, "hier wordt bewust niets gebruikt", standCodering.js:52-57).
   - Nooit naar gekeken (geen enkele rij) → stand `gat` (amber) of `via_boven` (blauw).
   Grijs vs. amber is de zichtbare scheiding; er wordt niets voor een `gat` weggeschreven (een gat is de afwezigheid van registratie).

---

## Blok 4 — Wat vertelt een verse database?

**Bevinding: de seed vertelt het gate-3-verhaal zonder handmatig klikken.** De bedrijfsfunctie-as is bewust NIET leeg op een verse reseed (`_seed_bvowb_scenario`, secties 16-17, `dev_seed_testdata.py:1543-1712`).

**Seed-broncode (wat een verse run zaait):**

| Meting | Aantal | Bron |
|---|---|---|
| Bedrijfsfuncties (via échte GEMMA-import `voer_uit`) | ~297 + 1 eigen ("Datagedreven werken") + 1 vervallen-demo | dev_seed:1599-1643 |
| Referentiemodel | 1 (`gemma_bedrijfsfuncties`, "release 1 juli 2026") | dev_seed:1568-1576 |
| component→functie-koppelingen (allen **grof**) | 8 | `_verhaal`, dev_seed:1682-1700 |
| geen-systeem-bevinding | 1 (Toezicht en handhaving veiligheidsdomein) | dev_seed:1702-1710 |

**Live-DB (huidige stand, read-only geteld — bevat sessie-residu):**

```
bedrijfsfuncties 299 (298 modelinhoud + 1 eigen), 1 vervallen
functievervulling 12 = 8 grof + 3 fijn + 1 geen_systeem
distinct gekoppelde componenten 8 / 19 totaal
zonder oordeel (comp) 6 · noodoplossing 0
aggregation-relaties 307
```

Duiding van het verschil seed↔live: de seed maakt **8 grof + 1 niets = 9** rijen. De live-DB toont **3 fijn** extra — de seed maakt **geen** fijne koppelingen, dus die 3 zijn **handmatig sessie-residu** (iemand testte in de browser), geen seed-output. Dit bevestigt: meet het seed-verhaal tegen de broncode, niet tegen de 11u-oude live-DB.

**Antwoorden op de deelvragen:**
1. **8 componenten** gekoppeld (allen grof), niet 3. **G4-5's "3/19" is achterhaald** — de seed is gegroeid naar 8/19.
2. Standen op een verse DB, elk aantoonbaar aanwezig (dev_seed:1645-1648, commentaar bevestigd door de couplinglijst):
   - `hier`: Zaaksysteem → Bezwaar- en beroepafhandeling (+ Sociaal domein/Omgevingsloket/Reisdocumenten met gebruikersgroep = "schoon hier").
   - `werkvoorraad`: BRP → Gegevensmanagement (BRP bewust **zonder** gebruikersgroep).
   - `via_boven`: Klantportaal → Klantenservice (ouder met 4 kinderen).
   - `niets` (bevinding): Toezicht en handhaving veiligheidsdomein.
   - `gat`: de ~297 ongekoppelde GEMMA-bladeren leveren de gaten (afwezigheid, geen rij).
   - meervoud (ADR-044): DMS + BRP delen dezelfde functie Gegevensmanagement; Burgerzaken-suite → Identiteitvaststelling (meerdere plekken).
   - **Plek mét én zónder gebruikersgroep:** ja — DMS (mét) vs. BRP (zónder) op dezelfde functie is exact het werkvoorraad-contrast.
3. **Noodgreep-/fileshare-als-enige-drager: NEE.** De enige fileshare in het lopende scenario ("Shared fileshare", dev_seed:1475) draagt géén functievervulling (alleen `assignment`/draait_op). Er is geen `noodoplossing`-oordeel in de seed (live: 0). Het gat-verhaal van blok 2 (fileshare/noodgreep als drager) is dus **niet** in de seed vertegenwoordigd — los van de vraag of dat verhaal überhaupt nog een `gat` moet worden (blok 2/6).
4. **Oordeel:** de seed zet geen enkel oordeel → alle 8 koppelingen zijn "nog niet beoordeeld" (`zonder_oordeel`-teller vult zich). Dat toont die stand, maar er is geen `naar_behoren`/`noodoplossing`-voorbeeld.

**Kort oordeel:** de seed dráágt het gate-3-verhaal (hier/werkvoorraad/via_boven/niets/gat + meervoud) op een verse DB — de zichtbaarheids-slice en het koppelen kunnen erop leunen. **Twee gaten in het verhaal:** (a) geen ingevuld `oordeel` (naar_behoren/noodoplossing) → de oordeel-as blijft onverteld; (b) geen noodgreep-/riskante-drager-voorbeeld. Een seed-herschrijving is niet blokkerend, wel wenselijk om die twee assen te tonen.

---

## Blok 5 — De procesregister-sloop: scope nog zoals gedocumenteerd?

**Bevinding: het feitenrapport V043 klopt in hoofdlijn; het model/leeslaag/de bouwstenen blijven, alleen de UI-ingangen verdwijnen. Eén tak is al feitelijk verweesd.**

1. **UI-ingangen / routes / menu:**
   - Routes: `proces-lijst` → `processen` → `ProcesLijst.vue` (router/index.js:143); `proces-detail` → `processen/:id` → `ProcesDetail.vue` (:144). `ProcesDiagram` heeft **geen** eigen route (ingebedde bouwsteen).
   - Nav: "Processen" → `proces-lijst`, **onvoorwaardelijk zichtbaar** (geen gating), `AppLayout.vue:129-136`.
   - Ingebedde proces-secties (geen routes): `ProcesComponentenSectie`, `OnderliggendeProcessenSectie`, `PartijProcessenSectie`, `ComponentProcessenSectie`.

2. **Proces-handoff-takken op de kaart** (`LandschapskaartView.vue`): `procesIngang` (:872), `_zetProcesFocus` (:888), `toonHeleBoom` (:899, popup :3527), `wisProcesIngang` (:905, chip-× :2989), `popupToonLandschap` (:916), `procesInzoom` (:928), `_inzoomProcesIds` (:932), `zoomInOpProces` (:962), `openViaProces` (:994), `_pasProcesIngangToe` (:1008); chip-banner "Proceslandschap:" (:2984-2989); mount-handoff-consumer in `onMounted` (:2799-2810, `neemKaartHandoff`). `wisSet`/`toonHeleLandschap` resetten `procesIngang`/`procesInzoom` mee.
   - **Feeders van de handoff:** store `kaartHandoff.js` (`zetKaartHandoff`/`neemKaartHandoff`), builder `procesKaartIngang.js` (`bouwProcesKaartHandoff`). Aangeroepen door `ProcesDetail.vue:119-127` ("Bekijk op kaart") en `ProcesLijst.vue:409-425` (`ProcesDiagram`-popup-uitgang). `GebruikteApplicatiesSectie.vue:72` deelt dezelfde store maar is de **component**-handoff (LI033), géén proces-ingang.

3. **Behouden als bouwsteen vs. slopen:**
   - **Behouden** (de functie-as hergebruikt ze): `procesBoom.js` (`meervoudBoomStructuur` gebruikt door `BedrijfsfunctieLijst.vue:41`), `ProcesDiagram.vue` (gebruikt door `BedrijfsfunctieLijst.vue:923` met `teksten`-prop), `useSleepbaar.js` (kaart-legenda/popup). De **backend** proces-as (`proces`/`procesvervulling` service/route/schema) staat los van de bedrijfsfunctie-as (geen gedeelde endpoints; de deling zit puur in de frontend-bouwstenen).
   - **Slopen** (proces-UI-ingangen): nav-item "Processen", routes `proces-lijst`/`proces-detail`, `ProcesLijst.vue`/`ProcesDetail.vue` + hun secties, en de proces-handoff-takken op de kaart (§2).

4. **"Samen slopen, niet in stukjes" — klopt.** De chip (`procesIngang`/`wisProcesIngang`) en de handoff-feeders ("Bekijk op kaart") zijn één keten: alleen de chip weghalen maakt "Bekijk op kaart" doodlopend. **Uitzondering die tóch los kan:** `openViaProces` (:994) + zijn expose (:2892) zijn **al verweesd** — de "Via proces"-beginscherm-ingang verviel (`KaartBeginscherm.vue:316-317`), er is geen template-aanroeper meer. Dat is dode code die onafhankelijk opruimbaar is.

---

## Blok 6 — Verrassingen & breuklijnen (adversarieel — benoemd, niet opgelost)

1. **Meervoudige plaatsing — correct afgehandeld, mét de LI041-fix zichtbaar.** `plek_standen._dichtstbijzijnde_dragers` (:618-635) klimt omhoog vanaf de **eigen** `ouder_functie_id` van de plek (niet vanaf álle ouders van de functie) en geeft bij meerdere dragers op gelijke afstand `enige=None` + het aantal terug — **nooit** een UUID-tiebreak. Geen stille één-ouder-keuze. **Subtiele observatie (geen defect):** `functies_met_koppeling` (:604) is functie-breed, niet plek-breed — een `via_boven`-cue kan dus naar een bovenliggende functie wijzen die alléén op een *zusterplek* gedekt is. ADR-051 besluit 1 kadert de cue bewust als "kijk hier", geen antwoord; toch is dit een keuze om te bevestigen als de kaart de cue prominenter maakt.

2. **Component→functies-richting bestaat al.** Het LI042-feitenrapport noemde deze richting mogelijk ontbrekend; ze is gebouwd: `overzicht_voor_component` (:506-585) + `GET /functievervullingen/component/{id}` + `ComponentBedrijfsfunctieSectie.vue`. Beide leesrichtingen bestaan.

3. **Stille keuze die zich voordoet als besluit — de fileshare/noodgreep-stand (herhaling blok 2, kern).** De opdracht behandelt "fileshare = gat" als een besluit; de code volgt ADR-051 (fileshare = gewone drager, oordeel is een aparte optionele as die de stand niet raakt). Wie de opdracht heeft geschreven, leunt op ADR-045; de code leunt op ADR-051 dat ADR-045 op dit punt herriep. **Besluit genomen door ADR-051 (LI041), niet stil in code.** Vóór stap 2/3: bevestigen dat de oordeel-as (i.p.v. een stand-downgrade) het gewenste "riskant maar draaiend"-verhaal draagt.

4. **Herordening van de zes MVP-stappen — implicaties:**
   - **Stap "koppelen" (gate 2) is grotendeels gebouwd** (blok 1): grof/fijn koppelen, oordeel, geen-systeem-bevinding, verdringing-leeslaag, beide leesrichtingen — allemaal aanwezig. De rest is UX-politoer/afronding, geen fundament.
   - **Stap "zichtbaarheid" (gate 3) rust op een verhalende seed** die al bestaat (blok 4) — niet blokkerend. Wél twee lege assen in de seed: geen ingevuld oordeel, geen noodgreep-drager.
   - **De seed-herschrijving (L4) is dus niet blokkerend**, maar zou (a) een `naar_behoren`- en een `noodoplossing`-koppeling en (b) een riskante-drager-plek moeten toevoegen om de oordeel-as en het "eerlijk gat"-verhaal te tonen.
   - **De sloop (stap 1)** is helder afbakenbaar (blok 5) en heeft één gratis meelift: de verweesde `openViaProces`.
   - **Openstaand ontwerpbesluit vóór de bouw:** de blok-2-breuklijn (fileshare/noodgreep-stand) — dit raakt zowel de afleiding als het seed-verhaal en hoort als adversariële checkvraag beantwoord vóór stap 2/3.

---

*Einde rapport. Niets gewijzigd/gemigreerd/gecommit. Wacht op de PNA.*
