# Feitenrapport — het gap-signaal per plek (gate 3)

**Build:** V041 · **Commit:** `980587b` · **Datum:** 2026-07-14 · **Modus:** READ-ONLY checkpoint
**Meetbron:** dev-DB (`lk_admin`, read-only) + codebase (canoniek). Geen wijziging, geen commit.

> Elke uitspraak draagt een **vindplaats** (`bestand:regel`) of een **telling** uit de dev-DB.
> Waar de code afwijkt van een aanname in de opdracht/ADR: gemeld (code wint).

---

## Samenvatting (gebruikerstaal)

**Wat de consultant vandaag ziet:** een centraal "Registratiegaten"-scherm met 9 signaaltypen — maar
**allemaal over componenten, contracten, gebruikersgroepen en checklistantwoorden**. **Op de
bedrijfsfunctieboom en op plaatsingen staat vandaag géén enkel signaal.** Een plek zonder koppeling
toont simpelweg niets. De drie werkvoorraad-standen die gate 3 belooft (*nog geen systeem · grof
gekoppeld, verfijning ontbreekt · geen systeem, vastgesteld*) bestaan nog niet.

**De scherpste open knoop is technisch én ontwerpmatig tegelijk:** de gate-2a-registratie
(`functievervulling`) kan **"hier gebruiken we niets — vastgesteld" niet dragen zonder een
schemastap** (`component_id` is NOT NULL, er is geen uitkomst-kolom). De gate-2a-opdracht beweerde
dat de vorm gate 3 "zonder herbouw" zou dragen — **de code weerlegt dat**: ADR-049 zelf rekent op een
*alembic-schemastap + reseed*; "zonder herbouw" sloeg op *geen datamigratie*, niet op *geen
schemawijziging*.

**En de kernvraag van Bert (staat in géén ADR):** een koppeling op een hoge functie (bv. *Uitvoering*,
met **110 nazaten**) helpt vandaag geen enkele functie eronder — die melden allemaal "geen systeem".
Moet dat zo blijven (strikt), moet de plek "ondersteund via bovenliggende" tonen (omhoog-cue), of moet
één koppeling de hele subboom groen maken (rollup)? Dat is de doorwerkingsvraag, en ze verandert
tussen **0 en 110** plekken per koppeling.

---

## 2. Wat de gebruiker vandaag ziet (schermen eerst)

### 2.1 De bestaande signalering — 9 typen, allemaal component/contract-gericht
⚠ **Discrepantie (opdracht):** de aggregator heet **`registratiegaten()`**, niet `overzicht()`
(`registratiegaten_service.py:372`). `overzicht()` bestaat wél, maar in `referentiemodel_import_service.py`.

De functie geeft `{"kritiek": {...}, "aandacht": {...}}`:

| Ernst | Sleutel | Label (gebruiker) | Aggregator |
|---|---|---|---|
| kritiek | `component_zonder_eigenaar` | "Component zonder eigenaar" | `:376` (`labels.js:368`) |
| kritiek | `component_zonder_verantwoordelijke` | "Component zonder verantwoordelijke" | `:377` |
| kritiek | `biv_classificatie_onvolledig` | "BIV-classificatie onvolledig" | `:378` |
| aandacht | `component_zonder_gebruikersgroep` | "Component zonder gebruikersgroep" | `:381` |
| aandacht | `component_geisoleerd` | "Component zonder koppeling (geïsoleerd)" | `:382` |
| aandacht | `contract_zonder_component` | "Contract zonder gekoppeld component" | `:383` |
| aandacht | `gebruiksfeit_zonder_verfijning` | "Gebruik bekend, detaillering ontbreekt" | `:384` |
| aandacht | `object_zonder_roltoewijzing` | "Object zonder roltoewijzing" | `:385` |
| aandacht | `antwoord_zonder_verantwoordelijke` | "Antwoord zonder verantwoordelijke" | `:386` |

Sleutel-constanten `registratiegaten_service.py:44-59`. **Alle dragers zijn component / contract /
gebruikersgroep / checklistantwoord** — geen proces, geen bedrijfsfunctie, geen plaatsing.

**UI-landing — beide patronen:**
- **Centraal scherm:** `frontend/src/views/SignaleringView.vue` — tab "Registratiegaten", per ernst
  gegroepeerd (`:18-34`, render `:113-131`), via `api.signalering.registratiegaten()` (`:65`).
- **Per-object badge:** `SignaleringBadge.vue:3`, gevoed door `badge_voor_component()`
  (`registratiegaten_service.py:155`), **alleen op ComponentDetail** (`ComponentDetail.vue:41,301`).
- *(Losse bevinding: `SignaleringView.vue:29` toont nog een dode groep `gebruikersgroep_zonder_organisatie`
  die sinds ADR-038 nooit meer vuurt — `registratiegaten_service.py:52-53`.)*

### 2.2 Enig signaal op bedrijfsfuncties of plaatsingen? → NEE (bewezen)
- `registratiegaten_service.py`: 0 treffers op `bedrijfsfunctie`/`functievervulling`/`plaatsing`
  (gemeten); de imports (`:21-30`) bevatten geen bedrijfsfunctie-/functievervulling-/proces-model.
- `plaatsingsignaal_service.py` bestaat, maar is een **component**-signaal (checklist-antwoord
  `technische_plaatsing` vs. een `draait_op`-relatie; `:53-102`) — géén bedrijfsfunctie-plek. ⚠ **De
  naam "plaatsingsignaal" is dus al bezet** (naamconflict voor gate 3).
- Frontend: geen signaal-scherm/badge op bedrijfsfuncties. De functieboom toont *dekking* (koppelingen),
  geen *signaal*.

### 2.3 De gap-cue in de boom — subboom-semantiek (kijkt OMLAAG)
De "geen ondersteunend systeem"-cue bestaat op de **processen**-lijst en de **kaart**:
- `ProcesLijst.vue`: `laadGapCue()` `:198-224`, `gapIds` `:197`, tekst-cue in de rij `:583-589`,
  diagram-kanaal `:474`.
- `ProcesDiagram.vue`: gestippelde rand via `node[?procesGap] border-style: dashed` `:337`, vlag uit
  `props.gapIds` `:370`, popup-badge `:203`, prop-definitie `:48`.
- `LandschapskaartView.vue`: eigen dashed-cue, subboom-afgeleid (`:1548`).

**Afleiding = frontend (client-side), op backend-data.** De subboom-**data** komt backend:
`procesvervulling_service.rollup_voor_proces()` (`:282`) loopt de hele subboom via
`proces_service.subboom()` (visited-set, cyclus-veilig). De **gap-set** wordt in de browser berekend:
per wortel `rollup` + eigen regels ophalen, elke vervulling "dekt" zijn proces **en klimt omhoog naar
de voorouders** (`ProcesLijst.vue:213-218`, cyclus-veilig via `gedekt`-guard); `gapIds` = alles wat niet
gedekt is (`:220`). **Semantiek: een proces is pas een gat als zijn héle subboom geen enkele vervulling
draagt.**

**Herbruikbaar? De cue-VORM ja, de afleiding nee.** Het `gapIds`-kanaal op `ProcesDiagram` is generiek
(dashed rand + popup, label uit `teksten.gap`), en de functieboom hergebruikt `ProcesDiagram` al
(`BedrijfsfunctieLijst.vue:8,41,811`). De functieboom voedt vandaag alleen `vervallenIds` (`:294,814`)
en **laat `gapIds` bewust leeg** — "het gap-kanaal blijft vrij voor gate 3" (`:292-293,809-810`; test
`BedrijfsfunctieLijst.test.js:417` borgt `gapIds == null`). Voor gate 3 hoeft alleen een functie-gap-set
berekend en aan `:gap-ids` gehangen te worden (+ `DIAGRAM_TEKSTEN.gap` zetten). **De afleiding zelf
(OMHOOG) bestaat nog niet** en is per scherm (ProcesLijst berekent zijn eigen set).

### 2.4 Plek zonder koppeling → toont NIETS (bevestigd)
De dekking-regel staat onder `v-if="dekkingVoorRij(rij)"` (`BedrijfsfunctieLijst.vue:1006-1007`);
`dekkingVoorRij` geeft `null` als er geen dekking-record is (`:143`), en dan valt de hele regel weg. Er
is **geen gap-/leeg-alternatief** in die tak.

---

## 3. De drie standen — wat kan de registratie vandaag dragen?

### 3.1 "Hier gebruiken we niets — vastgesteld" → NEE, vergt een schemastap ⚠ (de scherpste technische knoop)
- `Functievervulling.component_id` is **NOT NULL** (`models.py:797`; migratie `0069:38`); `functie_id`
  idem (`:798`/`:39`); alleen `ouder_functie_id` is nullable (`:799`/`:40`). Alle drie de composiet-FK's
  wijzen naar een echt `element` (`0069:60-71`).
- **Geen** discriminator/uitkomst-kolom (volledige kolomlijst `0069:35-45`: id, tenant_id, component_id,
  functie_id, ouder_functie_id, toelichting, verklaard_door_sub, verklaard_door, created_at, updated_at).
- Een "niets"-bevinding is semantisch een uitkomst op een **plek zónder component** — de vorm codeert
  juist *welk component* de plek draagt. Dat vergt een schemastap: `component_id` nullable + een
  uitkomst/discriminator (om "geen systeem" te onderscheiden van een half-ingevoerde rij), **óf** een
  aparte bevinding-tabel. De twee partiële UNIQUE-indexen (`uq_functievervulling_grof/fijn`, `0069:48-57`)
  staan óók op `component_id` en zouden mee moeten.
- **Discrepantie met de gate-2a-opdracht/ADR-049:** ADR-049 punt 7 (`ADR-049:159-161`) zegt letterlijk
  *"gate 3 registreert 'geen systeem — vastgesteld' … alembic-schemastap + reseed — geen
  datamigratievraagstuk."* **"Zonder herbouw" betekende dus: geen datamigratie, niet: geen
  schemawijziging.** De claim in de gate-2a-oplevering dat de vorm het "zonder herbouw" droeg, klopt
  alleen in die enge zin.

### 3.2 Grof · fijn · niets — wat de leeslaag vandaag kan
`dekking_overzicht` (`functievervulling_service.py:235-333`) onderscheidt **grof** en **fijn** via het
veld `herkomst` (`"fijn"` `:322`, `"grof"` `:329`; ook `_lees_een` `:230`). De registratie zelf:
`ouder_functie_id IS NULL` = grof, gevuld = fijn (split `:276-279`). **"NIETS" ontbreekt:** een plek
zonder koppeling **staat niet in de output** (docstring `:240-241`; de append-lus voegt alleen toe bij
fijn `:309` of grof `:324`). De leeslaag kent dus vandaag **twee** van de drie standen; de derde
(*niets* / *niets-vastgesteld*) is er nog niet.

### 3.3 Wortelfuncties
Een wortelplek `(functie, None)` wordt toegevoegd wanneer de functie geen ouder heeft (`:290-292`); omdat
`fijn_per_plek` alleen bij `ouder NOT NULL` wordt gevuld, kan een wortel **nooit** een fijn-antwoord
dragen — grof en fijn vallen daar samen (spiegelt `ADR-049:157-158`). Voor een gap-signaal: op een wortel
is er maar één stand (grof of niets); de "verfijning ontbreekt"-stand is er per definitie niet.

---

## 4. "Ondersteunt werk" ≠ "volwaardig ondersteund"

### 4.1 Bestaat het noodgreep/volwaardig-onderscheid? → NIET in code
- "noodgreep"/"volwaardig" komt **alleen in docs/ADRs** voor (ADR-045:71, ADR-046:326, OPVOLGPUNTEN:85,
  feitenrapporten) — **nergens als code-eigenschap**.
- **Kolommen van `componentconfig_optie`** (alle assen die een componenttype draagt): `dimensie,
  optie_sleutel, label, volgorde, actief, checklist_dragend, archimate_element, laag, aspect,
  kenmerk_definitie, ondersteunt_werk`. Geen "noodgreep"/"volwaardig".
- **Wél een incidenteel scheidende as: `laag`.** Onder de vijf koppelbare typen:

| Type | ondersteunt_werk | laag | checklist_dragend |
|---|---|---|---|
| applicatie | ✅ | **application** | ✅ |
| landelijke_voorziening | ✅ | **application** | ✅ |
| saas_dienst | ✅ | **application** | ❌ |
| fileshare | ✅ | **technology** | ❌ |
| client_software | ✅ | **technology** | ❌ |

De twee "noodgreep"-kandidaten (fileshare, client_software) zijn precies de **`laag = technology`**-typen;
de drie volwaardige de **`laag = application`**-typen. **Maar `laag` wordt nergens als kwaliteits-/
volwaardigheidsas gebruikt** (grep leeg) — het is een ArchiMate-typering. Of dat de juiste as is, is een
ontwerpknoop (§beslispunt 3). *(Verwant: het component draagt ook `levensfase` — de "gedragen door iets
dat verdwijnt"-familie uit ADR-046:326 — een tweede smaak van "niet volwaardig".)*

### 4.2 Componenten per type (dev-DB)
| Type | Aantal | Koppelbaar | laag |
|---|---|---|---|
| applicatie | 16 | ✅ | application |
| fileshare | 1 | ✅ | technology (noodgreep-kandidaat) |
| saas_dienst | 1 | ✅ | application |
| database | 1 | ❌ | technology |
| **Totaal** | **19** | **18 koppelbaar / 1 niet** | |

---

## 5. De doorwerking omhoog en omlaag — Berts kernvraag (staat in géén ADR)

### 5.1 De GEMMA-boom (gemeten)
| Meting | Waarde |
|---|---|
| Niveaus (min-diepte vanaf wortels) | **5** |
| Functies per niveau | N1: 8 · N2: 48 · N3: 136 · N4: 105 · N5: 2 (= 299) |
| Knopen mét kinderen | **66** |
| Bladeren (zonder kinderen) | **233** |
| Plaatsingen (= plekken, de teleenheid) | **304** |
| Huidige koppelingen (`functievervulling`) | **1** (incidentele testdata) |

### 5.2 Precedent "subboom-signaal" — maar het kijkt de ándere kant op
De proces-cue (§2.3) is **OMLAAG**: *"draagt iets ónder mij (mijn subboom) een vervulling?"* — een
vervulling laag in de boom dekt óók haar voorouders (`ProcesLijst.vue:213-218`; backend-rollup
`procesvervulling_service.py:282`, cyclus-veilig).

Gate 3 is **OMHOOG**: *"hangt er iets bóven/op mij — een koppeling op déze plek of op een voorouder?"*
De richting is omgekeerd. De **cue-vorm** (dashed + popup via `gapIds`) is herbruikbaar; de **afleiding**
(dekking omlaag laten doorwerken naar nazaten) is nieuw en bestaat nergens.

### 5.3 De drie varianten — wat de consultant ziet + hoeveel plekken veranderen
Read-only simulatie: een koppel-gedachte op **Uitvoering** (110 nazaten in de subboom).

| Variant | Wat de consultant ziet | Plekken die van stand veranderen (voorbeeld *Uitvoering*) |
|---|---|---|
| **strikt** | elke plek telt voor zichzelf; een koppeling op de ouder helpt niet — de 110 nazaten blijven "geen systeem" | **0** nazaten (alleen *Uitvoering* zelf wordt "grof gekoppeld") |
| **omhoog-cue** | de plek meldt *"ondersteund via een bovenliggende functie"* — een derde kleur tussen gat en groen | **110** nazaat-functies krijgen de derde stand |
| **rollup** | één koppeling op de ouder maakt de hele subboom groen | **110** nazaten worden "ondersteund" (+ *Uitvoering* = 111 functies) |

*(Plekken ≠ functies bij meervoud: 7 functies staan op meerdere plekken; bovenstaande telt nazaat-functies.
De teleenheid blijft de plaatsing — ADR-044 besluit 4.)* De keuze verschuift dus **0 → 110** per hoge
koppeling; dat is het gewicht van deze knoop.

---

## 6. Aanhaking (niet bouwen — inventariseren)

### 6.1 Past een plaatsings-signaal in de bestaande aggregator? → NEE, het wringt
Elk bestaand signaal levert `{id, naam, signaal, niveau}` waar `id` = de **primaire sleutel van één
element** (`_item` `:107-111`, `_aitem` `:79-84`; `Component.id` `:119,132`, `Contract.id` `:275`, enz.).
Een **plek heeft geen enkelvoudige element-id** — hij is een tuple `(functie_id, ouder_functie_id)`
(`functievervulling_service.py:273-307`), en bij de "niets"-stand is er per definitie geen component om
naar te linken. Een plaatsings-signaal past dus **niet** in het `{id, naam}`-contract zonder een nieuw
itemtype (tuple-sleutel i.p.v. element-id) — óf een aparte plek-signaal-service.

### 6.2 Precedent voor een gedeelde afgeleide teller (read-only, niet opgeslagen)? → JA
- `dashboard_service.py:65-97` — `func.count()` per type, live afgeleid, nooit opgeslagen.
- `registratiegaten_service.py:155` (`badge_voor_component`) — telt kritiek/aandacht on-the-fly.
- **Sterkst, ditzelfde domein:** `dekking_overzicht` levert al `grof_totaal_plekken`/`grof_geldt_op`
  ("N plekken, geldt op M"), uit dezelfde afleiding, expliciet nooit opgeslagen
  (`functievervulling_service.py:296-304,325-331`). ADR-045:191 beschrijft exact de gevraagde vorm.

### 6.3 Tests die gate 3 raakt
`test_functievervulling_adr049.py` · `test_registratiegaten.py` · `test_bedrijfsfunctie_adr043.py` ·
`test_adr045_ondersteunt_werk.py` · `test_plaatsingsignaal_f3.py` (⚠ naamconflict — test het bestaande
component-`plaatsingsignaal`, niet gate 3) · frontend `BedrijfsfunctieLijst.test.js` (borgt `gapIds == null`).

---

## Open beslispunten (genummerd, gebruikerstaal — NIET door CC beantwoord)

1. **Werkt een koppeling op een hoge functie door naar de functies eronder?** — de kernvraag. Opties:
   **A strikt** (elke plek voor zichzelf; ~230 bladeren blijven leeg tenzij apart gekoppeld); **B
   omhoog-cue** (een derde kleur "ondersteund via bovenliggende"; tot 110 plekken per hoge koppeling);
   **C rollup** (één koppeling groent de hele subboom). *Voor de consultant:* A is het eerlijkst maar
   veel werk; C is snel maar verbergt waar het werk écht gebeurt; B toont beide.
2. **Hoe leggen we "hier gebruiken we niets — vastgesteld" vast?** — de huidige tabel kan het niet dragen.
   Opties: **A** `functievervulling.component_id` nullable + een uitkomst-kolom (grof/fijn/geen-systeem);
   **B** een aparte bevinding-tabel per plek. *Voor de consultant:* beide maken "vastgesteld niets"
   onderscheidbaar van "nooit naar gekeken"; A houdt één tabel, B houdt de koppeltabel schoon.
3. **Waaraan zien we dat een fileshare een noodgreep is, geen volwaardig systeem?** — bestaat niet in code.
   Opties: **A** de bestaande `laag`-as gebruiken (application = volwaardig, technology = noodgreep); **B**
   een nieuwe derde eigenschap op het componenttype; **C** het alleen in de gap-leeslaag afleiden, niet
   opslaan. *Voor de consultant:* bepaalt of een G-schijf-plek "ondersteund" of "zorgwekkend" oogt.
4. **Waar leeft het plek-signaal?** — het past niet in de per-component aggregator. Opties: **A** een nieuw
   tuple-itemtype in `registratiegaten()`; **B** een eigen plek-signaal-service met een gedeelde teller.
   *Voor de consultant:* onzichtbaar in het scherm; bepaalt of het gat naast de component-gaten of op de
   boom zelf verschijnt.
5. **Hoe noemen we het?** — "plaatsingsignaal" is al bezet (component-`draait_op`). Een nieuwe naam nodig
   voor het functie-plek-gapsignaal.

**STOP — read-only checkpoint afgerond. `git status` toont exact één nieuw bestand.**
