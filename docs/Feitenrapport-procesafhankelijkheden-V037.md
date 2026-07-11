# Feitenrapport — Bestaan er procesafhankelijkheden (proces→proces)? (V037/LI037)

**Checkpoint:** LI037_checkpoint_procesafhankelijkheden · **Datum:** 2026-07-11 ·
**Basis:** commit ef2421f (schone werktree). Read-only — niets gewijzigd behalve dit rapport.

**Antwoord in één zin (detail in §6):** als **feature bestaan procesafhankelijkheden niet** —
`ouder_id` is de enige gemodelleerde, geseede en getoonde proces↔proces-band; het **generieke
relatiemodel laat ze technisch wél toe** (een `flow` tussen twee proces-elementen wordt door
niets geweigerd), maar er is geen UI om ze te registreren, geen seed-vulling en de kaart zou ze
niet tonen. ADR-042 hield "flow/volgorde tussen processtappen" expliciet buiten scope.

---

## 1. Model — bestaat er een tweede proces↔proces-band naast `ouder_id`?

- **`Proces` zelf kent er géén.** Het model (`models.py:634–671`) heeft als enige proces-
  verwijzing de **composiet self-FK `ouder_id`** (de hiërarchie, ON DELETE RESTRICT +
  self-parent-CHECK; transitieve kring-preventie in de service). Geen voorganger/opvolger-,
  triggert-, gebruikt- of volgorde-veld; ook geen volgorde-kolom binnen een tak (sortering is
  overal op naam). `Procesvervulling` (`models.py:673–714`) is **component→proces**, geen
  proces→proces.
- **Er is géén eigen proces→proces-relatietabel** (grep over models/migraties: alleen `proces`
  en `procesvervulling` als proces-dragende tabellen).
- **Maar: het gedeelde relatiemodel (ADR-023) staat er technisch voor open.** `Relatie` hangt
  bron/doel aan het **element**-supertype, en `proces` ís een element-subtype. De facade
  valideert **geen** `element_type` per relatietype (gevestigd feit, hergeverifieerd:
  `relatie_service.maak_aan`, r. 149 e.v., borgt alleen bron≠doel (`ZELFVERWIJZING`, r. 152),
  bestaan-binnen-tenant en catalogus-geldige kenmerken). Een `POST /relaties` met twee
  proces-ids en bv. `relatietype="flow"` (mét verplichte naam) zou dus **gewoon slagen** —
  gericht (bron→doel), kriskras tussen niveaus en tussen bomen, en bij flow zelfs meervoudig per
  paar (ADR-023a). Er is alleen **niets** dat dit als feature aanbiedt of bedoelt.
- **Bewuste scope-keuze vastgelegd:** ADR-042 r. 135 — *"Flow/volgorde tussen processtappen
  blijft buiten scope."* Procesafhankelijkheden zijn dus niet vergeten maar expliciet
  geparkeerd.

## 2. Aard (van wat er technisch zou kunnen)

Zou iemand het via de generieke API registreren, dan is de aard die van het relatiemodel:
**gericht** (`bron_id → doel_id`), typen uit de acht ArchiMate-relatietypes — de natuurlijke
drager voor "levert aan / informatiestroom" is **`flow`** (met naam verplicht,
kenmerken richting/protocol/impact via de catalogus; meervoud per paar toegestaan). Een
ArchiMate-**`triggering`** (procesvolgorde) zit **niet** in de gecureerde acht — "A triggert B"
heeft dus geen passend type; dat zou een modeluitbreiding zijn. Niveaus/bomen: geen enkele
beperking — de FK's wijzen naar `element`, dus een netwerk (ook kruislings) is structureel
mogelijk. Meerdere relaties per proces: ja (uniciteit per (bron,doel,type), flow uitgezonderd).

## 3. Vulling in de seed

**Nul.** Alle `RelatieCreate`-aanroepen in `dev_seed_testdata.py` (r. 375, 673, 934, 945, 1296,
1551) verbinden componenten/applicaties (flow app→app, assignment host→component, aggregation
suite→delen); de processen ontstaan pas daarná (r. 1616 e.v.) en krijgen uitsluitend
`ouder_id`-nesting + `Procesvervulling`-koppelregels. Geen enkele relatie-rij met een proces-id.

## 4. Leespad

- **Generiek bestaat het al:** `GET /relaties` met `bron_id`/`doel_id`/`paar_bron_id+paar_doel_id`
  (+ `relatietype`-filter) is element-generiek en zou proces→proces-relaties gewoon teruggeven;
  client-side is `api.relaties.lijst` er al. **Proces-specifiek bestaat er niets**: proces-detail
  heeft geen relatie-sectie, en er is geen servicefunctie "relaties van dit proces".
- De proces-leespaden die er wél zijn (lijst/subboom/rollup/vervullingen) gaan allemaal over
  hiërarchie + vervulling, niet over onderlinge afhankelijkheden.

## 5. Verhouding tot de kaart

De kaart-proceszone toont **uitsluitend** de hiërarchie (`proces_hierarchie`-edges, fase 1) +
de component→proces-vervulling (`procesvervulling`-edges). Zou er tóch een proces→proces-flow in
de DB staan, dan toont de kaart die **niet**: de flow-ring classificeert strikt
`bron_id ∈ component_ids AND doel_id ∈ component_ids` (`landschapskaart_service.py:347`), en ook
de overige ringen zijn per categorie-id-set gefilterd. Ook de relatie-UI biedt geen ingang: de
relatie-secties (KoppelingSectie/StructuurSectie) leven op component-detail met component-pickers.
Een proces-only diagram met afhankelijkheden zou dus **iets nieuws tonen** (registratie + leespad
+ projectie), niet iets bestaands filteren.

## 6. Conclusie (feitelijk)

**Procesafhankelijkheden proces→proces bestaan NIET als feature in LIKARA: `ouder_id` is de enige
gemodelleerde, geseede, getoonde en registreerbare proces↔proces-band.** Nuance: het generieke
relatiemodel laat een gerichte relatie (bv. `flow`) tussen twee proces-elementen **technisch toe**
(geen type-borging in de facade), maar er is geen UI-registratiepad, seed-vulling = 0, geen
proces-specifiek leespad, en de kaart zou 'm negeren. ArchiMate-`triggering` (procesvolgorde)
ontbreekt in de acht gecureerde relatietypes.

**Open punt (niet beslist):** wil Bert het proces-only diagram ooit rijker dan hiërarchie +
vervulling, dan is dit een **domein-/registratievraag** — ADR-materiaal langs de bestaande
Facade-over-Relatie-lijn (welk relatietype draagt "proces levert aan proces": `flow` hergebruiken,
of `triggering` als negende type toevoegen; plus endpoint-typeborging, registratie-UI en
kaart-/diagram-projectie). ADR-042 parkeerde dit bewust; het past binnen LIKARA's
registratie-bedoeling maar vergt een expliciet besluit. Voor een eerste proces-only diagram is er
feitelijk niets dat getoond kán worden behalve de hiërarchie + vervulling.

---

*Einde feitenrapport. Read-only; geen code, tests of data gewijzigd.*
