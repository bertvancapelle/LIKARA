# Feitenrapport — is het plateau de tranche, en is de dispositie de levensfase?

| | |
|---|---|
| **Opdracht** | LI040-checkpoint-plateau-en-tranche (read-only feitencheck) |
| **Datum** | 2026-07-14 |
| **Commit** | `7148672` — werktree bevat de twee eerdere checkpoint-rapporten (levensfase, gebruik-en-uitstap), ongemoeid; dit rapport is het enige nieuwe bestand |
| **Modus** | Read-only; code + DB-metingen (`lk_admin`, SELECT-only) |

---

## 1. Uitkomst in één zin

De dispositie is een **status-achtige notie in een scenario-vormig jasje** — het model
hangt haar aan het plateau-*lidmaatschap* (en de velduitleg zegt dat ook), maar geen
enkele lezer benut die scenario-vrijheid: de kaart reduceert tot **één waarde per
component (eerste plateau wint, niet-deterministisch)**, de readiness negeert haar
volledig en de dev-DB bevat **0 plateaus** — en het plateau zelf is **niet** de tranche:
het is een landschaps-brede momentopname zonder volgorde, zonder periode en zonder
organisatie-anker, verweven met gap/deliverable/bevestiging-machinerie die bij een
tranche niets te zoeken heeft.

---

## 2. A — Wat is een plateau feitelijk?

- **Model** (`models.py:510-530`): element-subtype (shared-PK → element, FORCE RLS) met
  precies twee eigen velden: `naam` + `toelichting`. Géén soort-veld (baseline/doel is
  louter naamconventie), géén volgorde, géén datums/periode, géén organisatie-anker.
- **Lidmaatschap** = facade over het unified relatiemodel
  (`plateau_service.py:1-14`): een `aggregation`-relatie bron=plateau → doel=lid
  (component óf contract, `_TOEGESTANE_LID_TYPES:55`), met in het jsonb-`kenmerken`-veld
  de **dispositie** (catalogus-kenmerk) en de **contractuele bevestiging**
  (registratie-kenmerken). Uniek per (plateau, lid) via de relatie-UNIQUE.
- **Betekenis**: overal "momentopname". Model-docstring (`:511-512`): *"een
  momentopname van het landschap (bv. 'Huidig'/'Doel')"*; velduitleg
  (`velduitleg.js:237-241`): *"hoe het nu is (baseline) of hoe je wilt dat het wordt
  (doelsituatie)"*. Het is dus een **tijdstand/doelbeeld van hét landschap** — een
  scenario-betekenis ("variant A vs. B") staat nergens, maar wordt door niets verhinderd
  (meerdere doel-plateaus naast elkaar kunnen gewoon).
- **Wie maakt ze**: tenant-rollen medewerker/beheerder (`Entiteit.PLATEAU` =
  `_INHOUD`-patroon, `rbac.py:47,155`), via de migratie-views
  (`frontend/src/views/migratie/PlateauLijstView/PlateauDetailView`, MIGRATIE_ROLLEN);
  de dispositie is bij het lid-koppelen **verplicht in de UI**
  (`PlateauDetailView.vue:172` — "Kies een dispositie.").
- **Volgorde**: **bestaat niet.** Geen veld, geen keten-notie; plateaus staan los naast
  elkaar. Het enige verband is de **gap**, die precies twee plateaus verbindt
  (baseline↔doel, vaste 2-ariteit) — een reeks "stap 1 → 2 → 3" is alleen als
  conventie-van-namen te maken.
- **Meting**: **0 plateaus, 0 lidmaatschappen, 0 disposities** in de dev-DB — de hele
  machinerie is gebouwd (V013) maar in de dev-praktijk nooit gevuld. Elke
  "komt het voor"-vraag hieronder is dus per data leeg; wat blijft is wat de code doet.
- **De bevestiging** (`plateau_service.py:189-200, :284-292`): een
  registratie-vinkje *"de contractuele afspraken voor dit lid zijn bevestigd"* — bij
  `ja` stempelt de server `bevestigd_door {sub,email}` + `bevestigd_op` +
  optioneel `bevestigd_aantal_gebruikers` in de kenmerken; bij `nee` worden ze gewist.
  Functioneel: het voedt de **contractuele readiness** van plateau/gap (naast de
  technische readiness = lifecycle `migratieklaar`); het is registratie, geen afdwinging.

---

## 3. B — De dispositie: status of scenario-voornemen?

- **Waarden** (relatiekenmerk-catalogus, dimensie `dispositie`; live gemeten):
  `behouden` "Behouden" · `migreren` "Migreren" · `vervangen` "Vervangen" ·
  `uitfaseren` "Uitfaseren" — alle vier actief; de catalogus is platformbeheerder-
  beheerbaar (soft-deactivate). Velduitleg (`velduidleg.js:229-231`): *"Wat er met dit
  lid in de transitie gaat gebeuren, **binnen dit plateau/deze gap**."*
- **Waar hij hangt — bewezen: aan het lidmaatschap**, niet aan het component. De
  dispositie leeft in `Relatie.kenmerken` van de aggregation-rij
  (`plateau_service.py:221,231-232`); het component-model draagt geen dispositie-kolom.
- **De toets — kan hetzelfde component per plateau verschillen?** Structureel **ja**
  (elke plaatsing een eigen rij met eigen kenmerken). Feitelijk: **niet meetbaar — 0
  plateaus in de dev-data.** En **benut wordt de mogelijkheid nergens**:
  - de **kaart** — de enige landschapsbrede lezer — pakt het **eerste** plateau per
    component en negeert de rest (`landschapskaart_service.py:203-207`:
    `plateau_map.setdefault(...)`, zonder ORDER BY op de join → bij meervoud
    **niet-deterministisch** welk plateau/dispositie de node toont);
  - de **readiness** van plateau én gap negeert de dispositie volledig (technisch =
    lifecycle, contractueel = bevestiging — `gap_service.py:286-306`,
    `plateau_service`-readiness idem);
  - geen filter, geen signalering, geen teller leest haar; de enige overige lezers zijn
    de leden-lijsten van Plateau-/GapDetail (weergave + bewerken).
- **Waar gelezen, compleet**: plateau-ledenlijst (`plateau_service.py:219-232`),
  gap-ledenlijst (zelfde patroon), kaart-node `plateau_naam`/`plateau_dispositie`
  (`landschapskaart_service.py:192-207` → popup/detailpaneel). Dat is alles.

### Het oordeel — onomwonden: **(a), in een (b)-vormig model**

`dispositie = uitfaseren` **gedraagt zich vandaag als een status van het component**:
elke lezer die ertoe doet behandelt haar als één waarde per component (de kaart dwingt
dat zelfs af via eerste-wint), niets benut de per-plateau-variatie, en de verplichte
invoer bij het koppelen maakt haar de facto "het oordeel over dit component" dat je
toevallig via een plateau invoert. **Bedoeling (Bert: status van het component) en
feitelijk gedrag sporen dus — het is de modelvorm die uiteenloopt**: het datamodel én de
velduitleg-tekst ("binnen dit plateau") beloven een scenario-vermogen dat nergens wordt
waargemaakt en dat de kaart bij echt meervoud zelfs niet-deterministisch zou tonen.

Scherpe bijvangst: de vier waarden mengen bovendien twee assen — `uitfaseren` is
fase-achtig ("gaat eruit"), maar `behouden`/`migreren`/`vervangen` zijn
**bestemmingen** (de migratiepad-familie uit het levensfase-rapport). De dispositie is
dus niet één-op-één "de levensfase verkeerd geparkeerd": één waarde is dat wél, drie
zijn bestemmings-woorden.

---

## 4. C — Is het plateau de tranche?

| Tranche-eigenschap (§1) | Kent het plateau dit? |
|---|---|
| Naam | **Ja** (`naam`, verplicht) |
| Volgorde/opeenvolging | **Nee** — geen veld, geen keten; alleen de gap (precies 2 plateaus) legt een richting tussen twee standen |
| Grove periode (optioneel) | **Nee** — geen enkel datumveld |
| Groepeert componenten | **Ja** (aggregation-leden) — én contracten, én met verplichte dispositie + bevestigingsmachinerie eraan |
| Component in geen enkele groep mogelijk (→ "nog niet ingedeeld") | **Ja** — lidmaatschap is optioneel; "in geen plateau" is een afleidbare NOT-EXISTS |
| Organisatie-gebonden of landschap-breed? | **Landschap-breed** — geen organisatie-anker, nergens; de betekenis is "momentopname van hét landschap". Twee organisaties in verschillende tranches kan het plateau alleen dragen als náámconventie ("Uitstap Tiel — tranche 2"), zonder structuur |

### Oordeel: **(3) — iets anders**

Het plateau is een **landschaps-brede toekomst-/momentstand**, verankerd in een eigen
machinerie (gap-einden met vaste 2-ariteit, deliverable-realisatieketen, contractuele
bevestiging, readiness-cijfers). De tranche uit §1 is een **organisatie-gebonden
uitstap-groepering met volgorde**. Ze delen één trekje (componenten groeperen) en
verschillen op alle andere: volgorde, periode, organisatie-anker, en de bagage eraan.

**Wat er kapot zou gaan bij hergebruik als tranche:**
1. **Betekenis-vervuiling in de bestaande machinerie**: tranche-plateaus verschijnen in
   de gap-pickers (gap = baseline↔doel — een tranche is geen van beide), in de
   deliverable-realisatieketen en in de readiness-cijfers.
2. **De kaart-badge liegt**: `plateau_naam`/`plateau_dispositie` op de node zou
   tranche-lidmaatschap als "migratieplaatsing" tonen — en bij een component in een
   doel-plateau én een tranche wint niet-deterministisch de een of de ander
   (het eerste-wint-gedrag).
3. **De verplichte dispositie**: elk tranche-lid zou bij koppelen een dispositie moeten
   kiezen (`PlateauDetailView.vue:172`) — een veld dat voor een tranche niets betekent.
4. **De bevestiging** (wie/wanneer/aantal-gebruikers) draagt contract-plateau-semantiek.
5. **Ontbrekende dragers**: volgorde, periode en organisatie-anker zouden als kolommen
   op `plateau` moeten landen en gelden dan óók voor baseline/doel-plateaus.

(Ter volledigheid optie (2) — de tranche eraan hangen: het enige haakje dat het model
biedt is "een tranche verwijst naar een plateau als resultaatstand"; niets in de huidige
code vraagt daarom, en het lost de bagage hierboven niet op. Feitelijk mogelijk, meer
niet.)

---

## 5. Open knopen voor Bert

1. **Het lot van de dispositie zodra de levensfase bestaat.** Opties die de code
   toelaat: (i) de waarde `uitfaseren` uit de dispositie-catalogus soft-deactiveren
   (beheerhandeling + reconcile-migratie; historische waarden blijven resolvebaar) zodat
   fase-taal alleen nog op het component leeft; (ii) de hele dispositie herdefiniëren
   als scenario-voornemen mét de afbakening op schrift; (iii) laten staan en alleen de
   afbakening vastleggen. NB: drie van de vier waarden zijn bestemmings-woorden — de
   afbakening raakt dus óók migratiepad (levensfase-rapport, knoop 4).
2. **Het kaart-eerste-wint-gedrag** (`setdefault`, geen ORDER BY): bij meervoudige
   plateaus niet-deterministisch. Opties: deterministisch maken (welke stand toont de
   node?), meervoud tonen, of expliciet vastleggen dat één plateau per component de
   praktijk is.
3. **De tranche-vorm** (gegeven C-oordeel 3): eigen registratie-feit — de code kent
   twee passende recepten: eigen tenant-tabel (roltoewijzing/organisatiegebruik-vorm)
   of element-subtype + relatie-facade (plateau-vorm). De §1-grens (naam + volgorde,
   periode optioneel, geen planningstool) past bij beide.
4. **Het anker van tranche-lidmaatschap**: aan het **component** (landschaps-tranche)
   of aan het **voornemen-feit** (de organisatiegebruik-rij — "Tiel stapt uit in
   tranche 2" hangt dan aan Tiel×component, consistent met "voornemen op het gebruik").
   Het gebruik-en-uitstap-rapport leverde de feiten: het grove feit is de canonieke
   gebruikslaag met een stabiele rij per (organisatie, component).
5. **De vier-waarheden-afbakening op schrift** (het ADR): levensfase (component) ·
   voornemen (gebruik) · dispositie (plan-per-plateau, of gesaneerd) · migratiepad
   (bestemming, vandaag dood). Zonder die tabel krijgt "wat verdwijnt er?" vier
   antwoorden.
6. **Dev-data**: 0 plateaus — voor elke browsercheck van komend bouwwerk rond
   plateaus/disposities is seed-data nodig (of de meting blijft leeg zoals nu).

---

## 6. Wat ik NIET kon vaststellen

- **Feitelijk gebruik van plateaus/disposities**: de dev-DB is leeg (0 plateaus) — alle
  gedragsuitspraken komen uit de code, niet uit data; hoe consultants de dispositie
  zouden inzetten (status- vs. scenario-lezing) is onmeetbaar tot er echt gebruik is.
- **Of "meerdere doel-plateaus" (scenario-varianten) ooit een beoogd gebruik was**:
  ADR-023 spreekt van "baseline of doelsituatie"; varianten worden niet genoemd en niet
  verhinderd.
- **De precieze tranche-semantiek bij gedeelde uitstappen** (twee organisaties, samen
  één tranche-plan?): domeinkeuze voor het ADR, geen codefeit.
