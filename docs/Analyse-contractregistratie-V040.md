# Overzicht — logische contract-registratie in LIKARA

**Status:** Analyse / PNA-notitie (geen ADR, geen besluit)
**Datum:** 2026-07-16
**Basis:** read-only feitenopname LI042 (codebase + dev-DB, geverifieerd) + ADR-020/023/024/025/030 + skills.
**Doel:** vaststellen wat LIKARA vandaag *logisch* vastlegt rond een ICT-contract, en wat nog mist — met het
onderscheid tussen **logisch noodzakelijk** (governance-inzicht) en **administratief** (bewust buiten scope).

---

## Uitgangspunt

LIKARA registreert contracten **logisch**, niet administratief. Geen contractbeheersysteem — geen facturen,
betaaltermijnen, SLA-boetes. Wél genoeg om de governance-vraag te beantwoorden die de consultant stelt:
*"welk systeem valt onder welk contract, met wie, tot wanneer, en wat gebeurt er als het afloopt?"* Dat is de
transitie-/uitfaseervraag uit ADR-025, waarin het contract een spil is.

**Rode draad van de bevinding:** het contract is als **identiteit** vrijwel volledig vastgelegd (wie, welk
type, wat valt eronder, welke hiërarchie — structureel geborgd). Wat ontbreekt is het contract als
**feit-in-de-tijd**: er zijn datums, maar er wordt geen betekenis aan verbonden. Juist die tijdsdimensie maakt
een contract op de kaart governance-relevant.

---

## Wat we vandaag al vastleggen (geverifieerd)

### Identiteit en structuur — volledig
- **Contract als getypeerd element-subtype** (shared-PK → element, RLS/tenant-isolatie). Velden: naam, externe
  contractnummers, omschrijving/toelichting.
- **Hiërarchie mantel / deel / los** met DB-CHECK (`deelcontract ⇔ mantel verplicht`), eigen projecties en
  UI-keten. Structureel afgedwongen.
- **Datumvelden** begin / eind / vernieuwing (Date, nullable) — *puur registratief, geen validatie* (ADR-020 B4).

### Relaties — volledig belegd
- **Contract → leverancier**: verplichte FK naar partij-element (ADR-024), aard-validatie
  (organisatie/eenheid/externe partij; persoon → 422), picker spiegelt de regel. Structureel geborgd.
- **Component ↔ contract** ("valt onder"): association in het unified relatiemodel met rol-kenmerk
  (valt_onder/onderhoud/hosting), m:n, plus **band-dekking** per paar (ADR-030). Zichtbaar als kaart-ring.
- **Partij → contract (beheerrol)**: roltoewijzing, contract mag doel zijn (contractbeheerder via ADR-024).
- **Contract → mantelcontract**: self-FK, deelcontract n:1 mantel.
- **Plateau/gap → contract**: aggregation, met contractuele bevestiging als kenmerk.

### Signalering — deels
- Eén contract-signaal: **`contract_zonder_component`** (contract dat nergens aan hangt).

### Dev-DB-beeld
15 contracten (1 mantel, 2 deel, 12 los); 15/15 met begin- én einddatum; 0/15 met vernieuwingsdatum;
15/15 met leverancier; 11 hangen aan ≥1 component, 4 los; 7 van 19 componenten zonder contract.

---

## Wat we missen

### A. Logisch noodzakelijk (raakt LIKARA's kernbelofte)

**A1 — Afgeleide afloop-status uit de einddatum.** *(Het echte gat.)*
De einddatum wordt overal getoond maar nergens geïnterpreteerd (grep op afloop-logica: 0 treffers), terwijl
15/15 contracten er een dragen. Zonder een afgeleide status (*loopt / verloopt binnen X / verlopen*) kan de
contracten-ring de transitievraag van ADR-025 niet beantwoorden — het contract is een naamplaatje, geen signaal.
- **Aard:** leeslaag, geen schema. Exact het `plek_standen`-patroon: een stand afleiden uit bestaande data,
  niets wegschrijven. Head-neutraal.
- **Waarde:** dit is dé toevoeging die contracten op de kaart governance-relevant maakt.

**A2 — Component zonder contractuele dekking (het spiegelsignaal).**
Er is `contract_zonder_component`, maar niet de omgekeerde, governance-relevantere kant: een **systeem dat
onder geen enkel contract valt** (7 van 19 vandaag). Voor de consultant is "dit draait ongedekt" precies een
aandachtspunt.
- **Aard:** signaal/leeslaag, spiegelt een bestaand mechanisme. Geen schema.
- **Nuance:** "geen contract" is soms terecht (eigen bouw, open source) — het signaal moet *zichtbaar maken*,
  niet *veroordelen*; net als de functie-laan-gaten een werkvoorraad zijn, geen fout.

### B. Besloten maar niet gebouwd (staat al in de skills)

**B1 — Verantwoordelijkheid + toelichting óók op contract** (skills LI038, "registratie-feiten-spoor").
Besloten, niet gebouwd. Sluit aan op A-laag; te heroverwegen samen met A1/A2.

### C. Bewust administratief — buiten scope houden

**C1 — Contractwaarde / bedrag.** Geen bedrag-veld; het financieel-administratieve is bewust weggelaten (juist).
- **Grijs gebied:** voor uitfaseer-afwegingen ("wat levert het op dit te laten vallen") kan een grove
  ordegrootte governance-relevant zijn. **Advies: buiten scope** tenzij een concrete uitfaseer-use-case erom
  vraagt — anders sluipt de administratie binnen die LIKARA principieel vermijdt.

**C2 — Vernieuwingsdatum in de praktijk leeg** (0/15). Het veld bestaat; de vraag is of het een rol speelt in
de afloop-status (A1) of stille ballast is. Meenemen in het A1-ontwerp, niet apart.

---

## Advies (samengevat, geen besluit)

1. **A1 als eerste** — de afgeleide afloop-status is de goedkoopste en meest waardevolle toevoeging: een
   leeslaag bovenop data die er al is, exact het patroon dat gate 4 voor de functie-laan gebruikt. Head-neutraal.
2. **A2 erbij** — het spiegelsignaal "component zonder contract" maakt het risicobeeld compleet, zichtbaar niet
   veroordelend.
3. **B1 meewegen** — verantwoordelijkheid/toelichting op contract stond al besloten; logisch moment is samen met A.
4. **C bewust buiten scope** — geen bedrag, geen administratie, tenzij een concrete uitfaseer-use-case het
   afdwingt.

**Conclusie:** LIKARA mist geen contract-*fundament* — dat staat er, structureel en netjes. Het mist een dunne
**interpretatielaag in de tijd** bovenop dat fundament. Dat is een klein, gericht stuk werk in dezelfde geest
als de rest van blok A: afgeleide standen uit bestaande feiten, geen nieuw schema.

> Dit is een analyse-notitie, geen ADR en geen bouwbesluit. Een eventueel contract-status-ADR zou hierop kunnen
> voortbouwen; de bouw valt sowieso ná gate 4.
