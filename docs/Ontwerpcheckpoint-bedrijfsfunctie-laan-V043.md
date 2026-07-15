# Ontwerp-checkpoint — de bedrijfsfunctie-laan op de kaart (gate 4)

**Build:** V042 · **Commit:** `254f905` · **Datum:** 2026-07-15 · **Modus:** READ-ONLY ontwerp-checkpoint
**Grond:** `docs/Feitenrapport-gate4-kaart-op-functies-V043.md` (feitencheckpoint) + de zes besluiten Bert (LI042) + codebase (canoniek).
**Reikwijdte:** vaststellen of de functie-laan met de bestaande proces-bouwstenen te tekenen is, waar de twee breukvlakken zitten, en welke keuzes vóór de bouw open zijn. **Geen wijziging, geen migratie, geen commit** — alleen dit ene bestand.

> Elke uitspraak draagt een **vindplaats** (`bestand:regel`). Waar de code afwijkt van een aanname in besluit/ADR/skill: gemeld in §7, code wint. FE = `modules/bwb_ontvlechting/frontend/views/LandschapskaartView.vue`, BE = `modules/bwb_ontvlechting/backend/services/landschapskaart_service.py`.

---

## §0 — Verdict (één alinea, gebruikerstaal)

**Ja, de functie-laan kan met de bestaande bouwstenen — maar niet gratis, en één keuze is nog niet gemaakt.** De teken-grammatica van de kaart (knoop-vormen, lijnstijl, bundeling, gap-markering, popup, de boom-layout-motor) is generiek en herbruikbaar; de proceslaan is er alleen op ~8 plekken met de woorden *"proces"/"processen"/"procesvervulling"* aan vastgedraaid. Een functie-laan is dus **"kopieer de proces-tak"** op die plekken plus een nieuwe backend-projectie — bekend werk, geen nieuw mechanisme. **De kern van het verschil zit in één ding:** een proces heeft precies **één** plek in de boom; een bedrijfsfunctie kan op **meerdere** plekken tegelijk staan (GEMMA: 7 functies met 2-4 ouders). De kaart moet daarom kiezen of ze een laan van **functies** tekent (elke functie één keer — zoals de functieboom-Diagram al doet) of een laan van **plekken** (elke plaatsing apart — zoals de werkvoorraad-leeslaag rekent). Die keuze, niet de code, is het echte werk — en ze is nog niet gemaakt.

---

## §1 — Bouwsteen voor bouwsteen: erft de functie-as hem?

De kaart tekent de proceslaan met een **mix**: het algoritme is generiek, de bedrading is per-string vastgezet. Per bouwsteen (map-verkenning, bevestigd tegen de code):

| # | Bouwsteen | Vindplaats (kern) | Erft? | Reden |
|---|---|---|---|---|
| 1 | Lanen-definitie (`RINGEN`/labels/volgorde) | FE:54,69,84,93 | **Met aanpassing** | 4 data-regels + één regel in `_laneVan` (FE:2131-2139, `et==='proces'` if-ladder; een functie valt nu door naar 'componenten') |
| 2 | Baan-/swimlane-layout (hoogte = diepte) | `laneLayout` FE:2178, `_swimlanePositions` FE:2494, motor `procesBoom.js:88` | **Motor 1-op-1; bedrading + layout nieuw** | Het algoritme kent geen proces-string, maar is via `l.key==='processen'` bedraad **én single-parent** (zie §2.1) |
| 3 | Knoop-vorm per type | `_vormVoorType` FE:1988, CY-marker FE:2674 | **Proces-specifiek, triviaal** | Eén `element_type`-tak bijzetten, parallel aan contract/partij/gg |
| 4 | Hiërarchie-lijnen ("onderdeel van") | styling FE:2231-2234 (generiek); `proces_hierarchie` FE:1847,2163 | **Styling 1-op-1; semantiek met aanpassing** | Tweede relatietype-literal op elke leesplek |
| 5 | Vervult-edges (bundeling + "Vervuld door"-popup) | FE:1544,1586,2244; BE:619-625 | **Proces-specifiek** | Hardgedraad op `procesvervulling`/`ring==='processen'`; parallelle helpers of generalisatie nodig — **én verdringing-gevoelig** (§2.2) |
| 6 | Gap-cue (dashed rand) | `_procesZonderSysteem` FE:1552, FE:2220,2695 | **Proces-specifiek + semantiek-keuze** | Kijkt **omlaag** (subboom); gate-3 `plek_standen` kijkt **omhoog** — twee verschillende vragen (§2.1) |
| 7 | Klik-popup + dubbelklik-inzoom + history | FE:1492,1906,955 | **Proces-specifiek (eigen endpoints)** | `zoomInOpProces` roept `api.processen.rollup` + `api.procesvervullingen.lijst` (FE:958-959) |
| 8 | Vervul-toggle | `popupVervulActie` FE:1607, `klikVervulActie` FE:1632 | **Proces-specifiek** | Parallel aan 5 |
| 9 | Backend hiërarchie-lezing | `Proces.ouder_id` BE:531,557,575,597 | **Single-parent (self-FK)** | Neemt structureel één ouder aan |
| 10 | Emit-vorm (node/edge) | BE:590-593,600-603,621-625 | **1-op-1** | Een functie-node/-edge past in dezelfde vorm (`element_type`, `ring`, `relatietype`, `herkomst`) — geen nieuw veld nodig |
| 11 | Functie op de kaart vandaag? | grep = 0 in BE+FE | **Bestaat niet** | De kaart toont vandaag géén bedrijfsfuncties/functievervulling — bevestigd |

**Netto:** de laan is haalbaar met bestaande bouwstenen; het enige écht nieuwe stuk is de **meervoud-ouder-layout** (§2.1). De datalaag is er al voorbereid: `meervoudBoomStructuur` (`procesBoom.js:62-82`, DAG-variant zonder één-ouder-guard) bestaat, maar er is **geen `meervoudBoomLayout`** — `procesBoomLayout` (`:88-128`) bouwt nog op de single-parent `procesBoomStructuur` (`:26`).

---

## §2 — De twee breukvlakken, met de gevolgen per optie

### 2.1 Breukvlak 1 — één functie, meerdere plekken (ADR-044)

De feiten: een proces heeft één ouder (`Proces.ouder_id`); een bedrijfsfunctie leeft in `aggregation`-plaatsingen en kan **meerdere ouders** hebben (`bedrijfsfunctie_service.py:116-136`, `_ouders_map` = lijst ouders per kind). De gap-cue/werkvoorraad hangt aan de **plaatsing**, niet aan de functie (ADR-044 besluit 4, ADR-051; `plek_standen` sleutelt op `(functie_id, ouder_functie_id)`).

**Er bestaat al een gebouwd precedent — en dat maakt de keuze scherp.** De functieboom-Diagram (`ProcesDiagram.vue`, hergebruikt door `BedrijfsfunctieLijst`) tekent meervoud vandaag als volgt (`ProcesDiagram.vue:112-118`, letterlijk): *"De layout hangt de knoop onder zijn eerste ouder … maar ÁLLE plaatsings-lijnen worden getekend."* Dat is de **laan-van-functies**-keuze: één knoop, meerdere binnenkomende lijnen. Daarom staat op de functieboom-Diagram de gap-cue **bewust uit** (`BedrijfsfunctieLijst.vue:908-911`) — een per-plek-cue past niet op een per-functie-knoop.

De open keuze voor de kaart, met gevolgen (niet beslissen — blootleggen):

| Optie | Wat de gebruiker ziet | Gevolg |
|---|---|---|
| **A — laan van functies** (elke functie één keer, onder haar eerste ouder, alle plaatsings-lijnen getekend) | Eén knoop "Toezicht", meerdere lijnen omhoog | **Herbruikt het bestaande precedent 1-op-1** (`ProcesDiagram`-aanpak). **Maar:** de per-plek-werkvoorraad (gat/hier/niets pér plek) kán niet eerlijk op één knoop — "Toezicht" die op de ene plek een systeem heeft en op de andere een gat, collapst tot één kleur. Botst met ADR-044 besluit 4 (de plaatsing is de teleenheid) en met de belofte dat de kaart de werkvoorraad eerlijk houdt (ADR-051) |
| **B — laan van plekken** (elke plaatsing = eigen knoop; een functie onder 3 ouders verschijnt 3×) | "Toezicht onder Milieu" en "Toezicht onder Vergunningen" als aparte knopen | **Matcht de leeslaag 1-op-1** (`dekking_overzicht`/`plek_standen` zijn per plek); de gap-cue mapt direct. **Maar:** vergt een **nieuwe meervoud-plek-layout** (bestaat niet); een gedeelde diepe subboom herhaalt zich onder elke voorouder-plek → het aantal render-knopen kan boven de 304 plekken groeien en moet begrensd |

**Bijkomende keuze binnen breukvlak 1 — welke gap toont de kaart?** De proces-gap-cue kijkt **omlaag** (`_procesZonderSysteem` FE:1552-1569: een knoop is gat als zijn héle subboom geen systeem draagt). Gate-3 `plek_standen` kijkt **omhoog** (vier standen: gat / via_boven / hier / niets; `functievervulling_service.py:485-488`). Dat zijn **twee verschillende vragen**: "draagt iets ónder mij iets?" vs. "draagt iets óp of bóven mij iets?". De kaart-functielaan kan niet stilzwijgend de proces-cue erven — er moet gekozen worden welke vraag ze beantwoordt.

### 2.2 Breukvlak 2 — de richting component → functies bestaat nog niet

De feiten (feitencheckpoint + code): er is **geen** `lijst_voor_component` voor functievervulling, geen route, geen sectie (`ComponentDetail.vue` mount geen functie-sectie). Zowel de **laan-vervult-edges** als de **component-detail-sectie** hebben die richting nodig.

**Kan het uit de bestaande leeslaag, zonder tweede afleiding? — JA.** `dekking_overzicht` (`functievervulling_service.py:351-478`) draagt per plek al `componenten[]` én `verdrongen[]`, met `component_id` in elke entry. De richting *"op welke plekken hangt dit component"* is een **her-indexering** van die bron: filter de plek-entries waar `component_id` in `componenten` of `verdrongen` voorkomt. Geen tweede query, geen tweede waarheid — de consument leest de uitkomst (ADR-049 besluit 5).

**Waar de tweede waarheid concreet dreigt.** De proces-tegenhanger `lijst_voor_component` (`procesvervulling_service.py:240-276`) is een **directe query** `select … where component_id = X` — dat kan bij proces, want proces kent **geen verdringing** (grof/fijn coëxisteren daar niet). Kopieer je dat patroon naar functievervulling, dan krijg je de ruwe rijen **zonder de leesregel**: het component toont "ondersteunt Toezicht — geldt overal", terwijl op plek *Milieu* een ánder systeem dat grove antwoord verdringt (`dekking_overzicht:447-476`). Twee schermen, twee waarheden, uit de pas — precies de "3-van-19"-val (LI040) en de kernles LI038. **Dezelfde val geldt voor de laan-vervult-edges:** de kaart bundelt de proces-vervult-edges nu direct uit de rijen (BE:619-625, geen verdringing); een functievervulling-bundeling die de ruwe rijen leest, tekent een edge die op een verdrongen plek niet zou moeten verschijnen.

→ **Regel voor de bouw:** zowel de component-sectie als de laan-edges lezen `dekking_overzicht` (her-geïndexeerd), nooit een verse `where component_id`-query. Dat is de "één feit, één leeslaag"-eis uit het besluit.

---

## §3 — De drie ingangen op één bouwsteen

### 3.1 Wat het koppelpad aan functiekant vandaag doet

`BedrijfsfunctieLijst.vue:546-613` (feitencheckpoint §3.2):
- **Grof/fijn** via `koppelScope`: `'overal'` (grof, `ouder_functie_id=null`) vs `'hier'` (fijn, mét plek). **Default `'overal'`** (`:564`).
- **Scope-regel:** `api.componenten.lijst({ondersteunt_werk:true})`; backend dwingt af (`functievervulling_service.py:106-110`, 422 `COMPONENT_ONDERSTEUNT_GEEN_WERK`).
- **Verdringing bij het lezen:** één keer, in `dekking_overzicht` (`:447-476`) — nooit opgeslagen.
- **Wie/wanneer-stempel:** server-side (`huidige_actor()`, `:162`), nooit uit de payload.
- Werkwoord: **kaal** ("ondersteunt"); optioneel oordeel (naar_behoren/noodoplossing/leeg).

### 3.2 Wat de component-ingang hergebruikt, en wat nieuw is

| Nodig | Hergebruik (bestaand) | Nieuw / onvermijdelijk |
|---|---|---|
| Picker | `ZoekSelect` + `ondersteunt_werk`-scope (backend spiegelt) | — |
| Rij-acties / dialogen / banner | `RijActies`, `BevestigVerwijderDialog`, `MeldingBanner` | — |
| Registreren (schrijven) | `POST /functievervullingen` accepteert het al (component-agnostisch) | Een **tweede schrijf-ingang** (nu alleen de functieboom) — raakt "één plek van registratie" (open keuze §6.3) |
| Lezen (component → plekken) | `dekking_overzicht`, her-geïndexeerd op component | Een **route** + een dunne re-index-functie (géén tweede afleiding, §2.2) |
| De sectie zelf | — | Een **component-sectie-component** |

**Convergentie-kandidaat (feitencheckpoint §3.3):** `ComponentProcessenSectie.vue` (proces, component-zijde) en `ProcesComponentenSectie.vue` (proces, proces-zijde) zijn near-dupes; een functie-sectie zou een **derde** kopie worden. Dit is het n≥2-moment om één gedeelde "koppel-sectie"-bouwsteen te maken die zowel de proces- als de functie-ingang bedient — of minstens de functie-sectie erop te enten. Idem de dubbele service-helpers (`_tenant_uuid`/`_element_type`/`_lees_een` in beide vervulling-services).

### 3.3 Grof vs. fijn vanuit het component — de stille keuze

Aan functiekant wijs je een **plek** aan (je staat al in de boom). Vanuit een component is "de plek" minder vanzelfsprekend: de gebruiker kiest eerst een **functie**, en pas dán eventueel een plek. **De stille keuze die een naïeve implementatie hier maakt:** default op **grof** ("geldt overal") zodra alleen een functie gekozen is — exact wat de functieboom doet (`koppelScope` default `'overal'`, `:564`). Dat kan juist zijn (grof = "nog niet nagevraagd wáár"), maar het is vanuit het component niet vanzelfsprekend hetzelfde als vanuit de boom — de gebruiker ziet daar geen boomcontext. **Blootgelegd, niet beslist** (§6.3).

### 3.4 Besluit 4 — "systeem zonder bedrijfsfunctie" zichtbaar en filterbaar

De feiten (seed/werkvoorraad-verkenning): dit spiegelbeeld is vandaag **nergens** zichtbaar.
- **Registratiegaten-signaal:** 9 typen (`registratiegaten_service.py:44-59`) — géén "zonder bedrijfsfunctie". Patroon bestaat (`component_zonder_gebruikersgroep`, `:229-242`).
- **Component-lijstfilter:** `*_ontbreekt`-familie bestaat (`routes/component.py:59-74`: levensfase/migratiepad/complexiteit/prioriteit/biv), maar géén "zonder bedrijfsfunctie". Patroon past 1-op-1 (`zonder_bedrijfsfunctie: bool` in de gedeelde filterset, items + telling).
- **Per-component badge:** `badge_voor_component` (`:155-225`) bundelt 6 component-signalen — géén functie-gat. Patroon past.
- **Wél gebouwd, maar de ándere kant:** `WerkvoorraadPlekView.vue` toont de vier standen **per plek** (`plek_standen`) — dat is "plek zónder systeem" (`gat`), niet "systeem zonder functie".

→ Besluit 4 is **net-nieuw** (signaal + filter + evt. badge), maar elk haakje heeft een bestaand patroon. Het is klein werk, geen nieuw mechanisme.

---

## §4 — Snijlijn: weg / blijft (erfstuk) / twijfel

### 4.1 Weg (UI-ingang — besluit 6)
- **Nav + routes:** `AppLayout.vue:129-136` (nav-processen), `router/index.js:140-141` (`proces-lijst`/`proces-detail`), `useTerugNavigatie.js:22-23`. **Tests bewegen mee:** `ProcesLijst.test.js`, `ProcesDetail.test.js`, `ProcesDiagram.test.js`, `OnderliggendeProcessenSectie.test.js`, `procesFocusSet.test.js`, `procesKaartIngang.test.js`, de "Via proces"-test in `KaartBeginscherm.test.js`.
- **Register-schermen:** `ProcesLijst.vue`, `ProcesDetail.vue`, `ProcesComponentenSectie.vue`, `OnderliggendeProcessenSectie.vue` (host-schermen weg).
- **Component-detail proces-sectie:** `ComponentProcessenSectie.vue` — vervangen door de functie-sectie (besluit 2 claimt de kop "Waarvoor gebruiken we het").
- **Formulier-subveld "Proces":** `ComponentFormulier.vue:413-463` → wordt "Bedrijfsfunctie" (besluit 3).
- **Kaart-proceslaan + proces-ingangen:** de ~8 proces-bedradingsplekken (§1), de "Via proces"-ingang (`KaartBeginscherm.vue:324-328`), "Open proces →" (FE:1492), `zoomInOpProces` (FE:955) — vervangen door de functie-laan (besluit 1).

### 4.2 Blijft (erfstuk — de functie-as erft ze)
- **Model + schema:** `Proces`/`Procesvervulling` (`models.py:667-744`), RLS-policies, `ApplicatiefunctieOptie`. (Besluit 6: model blijft; verbergen is niet slopen — voor het model.)
- **Services als bouwsteen-precedent:** `proces_service`, `procesvervulling_service` (roll-up), `procesBoom.js` (al gedeeld met de functieboom), `ProcesDiagram.vue` (al hergebruikt door de functieboom).
- **RBAC/audit:** `PROCES`/`PROCESVERVULLING`-entiteiten (`rbac.py:52,55`), audit-allowlist (`audit.py:72`). Blijven staan; geen consument in de UI, maar geen sloop.
- **Model/leeslaag-tests blijven bijten:** `test_proces_adr042.py`, `test_procesvervulling_adr042.py`, `test_rollup_adr042.py`, `test_landschapskaart_proces.py` (offline model/leeslaag-delen), `LandschapskaartView.test.js`/`kaartLayout.test.js` (kaart-leeslaag).

### 4.3 Twijfel — waarom
- **Backend proces-routes** (`routes/proces.py`, `routes/procesvervulling.py`): als de kaart geen proces meer toont én het register weg is, hebben `/processen`/`/procesvervullingen` **geen consument** meer. Weg of slapend laten? (Model blijft hoe dan ook; een route is geen model — §6.5.) De route-tests (`*_live`) bewegen mee met die keuze.
- **Organisatie-"Processen"-sectie** (`PartijProcessenSectie.vue`): afgeleid van proces; na reseed (proces-registraties weg) heeft ze geen data. Weg, of vervangen door een functie-equivalent? (§6.4)
- **De proces-sectie op componentdetail tijdens de overgang:** wordt ze in slice 1 al vervangen (proces-data blijft ongezien tot de reseed), of pas bij de reseed? (§6.1 / §8)

### 4.4 Wat beslist NIET weg mag (read-only bevestigd)
- **`ARCHITECTUUR.LEZEN`** (`rbac.py:185`) + de **kaart-projectie-structuur** (`landschapskaart_service.haal_grafdata_op`, scope-opbouw BE:82-139, dangling-guard BE:520). De functie-laan is een **nieuwe read-only verrijking onder dezelfde entiteit** — precies zoals de proceslaan (BE:494-495 "Read-only VERRIJKING … geen scope_ids-verbreding"). Het vervangen van de proceslaan door een functielaan **raakt die structuur niet**: dezelfde emit-vorm (§1 rij 10), dezelfde scope-discipline. `ARCHITECTUUR.LEZEN` blijft de leesentiteit; er komt geen schrijfactie bij.

---

## §5 — Reseed: wat er nodig is om het verhaal te vertellen

**Vandaag vertelt de seed het functie-verhaal NIET.** De GEMMA-functieboom wordt wél geïmporteerd (blok 16, `dev_seed_testdata.py:1610-1712`: 297 functies, 1 vervallen demo, 1 eigen functie), maar op de **functievervulling-as staat NIETS** — `functievervulling_service` wordt niet eens geïmporteerd, en er is 0× `maak_aan`/`registreer_geen_systeem`/`zet_oordeel`. De vijf MVP-standen ontbreken alle vijf.

Wat een verse database moet tonen, en wat daarvoor minimaal nodig is (read-only vastgesteld — niet bouwen):

| Stand | Nodig | Aandachtspunt |
|---|---|---|
| (a) grof — "geldt overal" | `functievervulling_service.maak_aan(…, ouder_functie_id=None)` | — |
| (b) fijn — één plek | `maak_aan(…, ouder_functie_id=<plek-ouder>)` | de plek moet als aggregation-paar bestaan, anders 422 `ONBEKENDE_PLEK` |
| (c) bewust niets | `registreer_geen_systeem(…, functie_id, ouder_functie_id)` | — |
| (d) noodoplossing | `maak_aan(…, oordeel="noodoplossing")` of `zet_oordeel` | — |
| (e) systeem zónder functie (het gat) | een `ondersteunt_werk`-component **niet** koppelen | onzichtbaar tot besluit 4 gebouwd is (§3.4) |

Verder nodig: `functievervulling_service` importeren in de seed; functie-id's opzoeken op naam ná de GEMMA-import (patroon `_model_functie_op_naam`, `:1669-1680`); component-id's uit de bestaande `comp_id_map` (`:1583`).

**Besluit 5 (proces-registraties verdwijnen via reseed):** de seed kent **geen wis-/reset-mechanisme** (idempotent-via-skip). Proces-blok 15 (`:1544-1608`, 6 processen + 8 koppelingen) verdwijnt alleen als dat blok **verwijderd/vervangen** wordt én de DB opnieuw opgebouwd (`down -v && up -d`, ontwikkelmodus — alleen testdata, géén datamigratie).

---

## §6 — Open keuzes voor de bouw (genummerd, gebruikerstaal — geen advies, geen voorkeur)

1. **Tekent de kaart één knoop per bedrijfsfunctie of één per plek?** Eén-per-functie is al gebouwd (de functieboom-Diagram: één knoop, alle lijnen omhoog) maar kan de werkvoorraad pér plek niet eerlijk tonen; één-per-plek matcht de werkvoorraad maar vergt een nieuwe layout. (§2.1)
2. **Welke vraag beantwoordt de gap-markering op de kaart-functielaan:** "onder deze functie draait nergens een systeem" (omlaag, zoals nu bij proces) of de vier werkvoorraad-standen per plek (omhoog: nog geen systeem / ondersteund via bovenliggende / hier draait dit / hier bewust niets)? (§2.1)
3. **Vanuit een systeem: koppelt de gebruiker standaard "geldt overal", of moet hij een plek kiezen?** Vanuit de functieboom is de default nu "geldt overal"; vanuit een systeem ziet hij geen boomcontext. (§3.3)
4. **Blijft de afgeleide "Processen"-sectie op het organisatiedetail — vervangen door een functie-equivalent, of weg?** Na de reseed heeft de proces-variant geen data meer. (§4.3)
5. **Gaan de backend proces-routes (`/processen`, `/procesvervullingen`) ook weg, of blijven ze slapend?** Het model blijft hoe dan ook; een dode route is geen model. (§4.3)
6. **Waar wordt "systeem zonder bedrijfsfunctie" de werkvoorraad:** als centraal registratiegaten-signaal, als filter in de componentenlijst, als badge op het component — of alle drie? (§3.4)
7. **Krijgen de kaart-vervul-toggle en dubbelklik-inzoom meteen een functie-equivalent, of start de laan read-only** (verkennen ja, set-acties later)? (§1 rij 7-8)
8. **Wordt de proces-sectie op het componentdetail al bij de eerste slice vervangen door de functie-sectie** (proces-data blijft dan ongezien tot de reseed), of pas tegelijk met de reseed? (§8)

---

## §7 — Discrepanties tussen skills/ADR's en de code

1. **De kaart is niet `ProcesDiagram`.** De skill-taal ("de proceslaan", "structuur-generiek gemaakt", `ProcesDiagram.vue:19-31`) suggereert één gedeelde proces-boom-bouwsteen. **Code:** de **register-Diagram** (`ProcesDiagram`) en de **kaart-laan** (LandschapskaartView) zijn twee verschillende renderers. De register-Diagram handelt meervoud al af (één knoop, alle lijnen; `:112-118`); de kaart-laan gebruikt `procesBoomLayout` (single-parent) en leest de hiërarchie uit backend-`proces_hierarchie`-edges, niet uit `ouder_ids`. De functie-laan erft dus **niet** automatisch de meervoud-afhandeling van de register-Diagram — dat is een aparte, nieuwe layout (§2.1).
2. **ADR-044 besluit 4 (plaatsing = teleenheid) ↔ het gebouwde precedent.** ADR-044/051 leggen de teleenheid op de **plaatsing**; het gebouwde functieboom-Diagram koos juist **functie-één-keer** en zette daarom de gap-cue uit (`BedrijfsfunctieLijst.vue:908-911`). Geen bug — maar de kaart moet die spanning expliciet oplossen (§6.1), niet stilzwijgend het precedent overnemen.
3. **Besluit 1 "geen tussenperiode" ↔ de ~8 bedradingsplekken.** De proceslaan zit op ~8 plekken vast (§1); "geen gat op de kaart" dwingt de vervanging in **één samenhangende slice** (verwijderen + terugplaatsen samen), niet incrementeel. Feit, geen conflict — maar het bepaalt de knip (§8, slice 4 is atomair).
4. **"Model blijft, route gaat" (besluit 6) ↔ de backend-routes.** Besluit 6 zegt "routes gaan geheel weg" (frontend-register). De **backend** proces-routes zijn een aparte keuze (§6.5) — het besluit spreekt zich er niet over uit.
5. **Stale docstring (buiten scope, gemeld).** `routes/functievervulling.py:4-6` beweert DELETE guardt op VERWIJDEREN; de code guardt op WIJZIGEN (registratie-feit, ADR-050). Documentatie-drift.

---

## §8 — Voorgestelde knip in slices (alleen knip + volgorde + waarom; geen implementatie)

Leidend: **bouw de functie-ingangen en de werkvoorraad eerst (omkeerbaar, browser-beoordeelbaar); vervang de kaart als één atomaire stap; verwijder proces + reseed als laatste** (de onomkeerbare sloop komt ná het bewijs dat de vervanger werkt). Elke slice is zelfstandig in de browser te beoordelen.

- **Slice 1 — component-detail-sectie "waarvoor gebruiken we het" → bedrijfsfuncties** (besluit 2). De gedeelde leeslaag (`dekking_overzicht` her-geïndexeerd op component) + route + één koppel-sectie-bouwsteen (convergentie-kandidaat §3.2). *Browsercheck:* open een systeem, zie op welke functies/plekken het hangt, koppel er een. Raakt de kaart niet. *(Hier valt ook §6.8: vervangt deze slice de proces-sectie al?)*
- **Slice 2 — formulier-subveld "Proces" → "Bedrijfsfunctie"** (besluit 3). Koppelen al bij het aanmaken, via dezelfde bouwsteen als slice 1. *Browsercheck:* maak een systeem aan met een functie eraan.
- **Slice 3 — werkvoorraad "systeem zonder bedrijfsfunctie"** (besluit 4). Signaal + component-lijstfilter (+ evt. badge), op de bestaande patronen (§3.4). *Browsercheck:* filter de lijst op "zonder bedrijfsfunctie", zie het gat.
- **Slice 4 — de kaart-functielaan vervangt de proceslaan** (besluit 1, **atomair**). Backend functie-projectie (aggregation-hiërarchie + meervoud) + de ~8 frontend-bedradingsplekken + de gekozen meervoud-layout (§6.1) en gap-semantiek (§6.2). Verwijderen en terugplaatsen samen — geen tussenperiode. *Browsercheck:* open de kaart, zie bedrijfsfuncties i.p.v. processen, met de vervult-edges en de gap-cue.
- **Slice 5 — procesregister-UI + routes weg, en reseed** (besluit 5/6). Pas nadat de kaart (slice 4) en de component-sectie (slice 1) de proces-ingangen hebben vervangen. Nav + routes + register-schermen weg; proces-seedblok vervangen door een functievervulling-seedblok dat de vijf standen vertelt (§5). *Browsercheck:* het menu toont geen "Processen" meer; een verse database vertelt het functie-verhaal (grof, fijn, geen-systeem, noodoplossing, het gat).

*(De backend-route-keuze §6.5 en de organisatie-sectie §6.4 haken aan bij slice 5, afhankelijk van Berts keuze.)*

---

**Ontwerp-checkpoint klaar — niets gewijzigd.**
