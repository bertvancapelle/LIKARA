# SESSIE_BRIEFING.md — LIKARA V041

**Gegenereerd**: 2026-07-14

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V041 |
| Datum | July 2026 |
| Commit | 6cc7db0 |
| Tests | backend 1095 (2 skipped) / frontend 92 files, 1199 groen |
| TST-rapport | TST-V041-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
6cc7db0 [frontend] LI040: DetailKop-bouwsteen — de acties horen bij het object, niet bij het einde van de pagina
3349905 [bwb_ontvlechting] LI040: 'Midden' is geen oordeel als niemand het gaf — oordelen nullable + vindbaar gat — ADR-046-lijn
feb27f9 [bwb_ontvlechting] LI040: 'nog niet vastgelegd' is vindbaar — ontbreekt-filters + onbekend uit migratiepad — ADR-046
39eb2ef [bwb_ontvlechting] LI040: de filterbalk vertelt wat hij doet — bedoeling-filter, resultaatregel, BIV op de hoogste as
b027095 [bwb_ontvlechting] LI040 stuk 1: levensfase op het component + bedoeling opgeschoond — ADR-046
```

---

## Prioriteiten volgende sessie

# NEXT_SESSION.md — LIKARA V041

**Gegenereerd**: 2026-07-14
**Vorige build**: V041
**Branch**: master
**Laatste commit**: (afsluitcommit V041; daarvóór `6cc7db0` detailkop · `3349905` geen-oordeel · `feb27f9` leeg-vindbaar · `39eb2ef` filterbalk · `b027095` levensfase-stuk-1 · `05e8a93` stuk 2 + identiteit · `87dc120` ADR-045 · `7148672` veldbouwsteen)

> **Sessie LI040 — Vier vragen, vier plekken; en LIKARA verzint niets meer (V041).**
>
> Wat LI040 heeft opgeleverd (gebruikerstaal):
> - **De platformbeheerder kan weer een componenttype toevoegen** (dat was kapot) en
>   bepaalt zelf wat werk ondersteunt — een eigenschap in de catalogus, geen lijst in
>   code (**ADR-045**, `87dc120`).
> - **De consultant kan vastleggen wélke organisatie een systeem gebruikt**, zónder de
>   afdeling te weten (ADR-046 stuk 2, `05e8a93` — het ADR-036-restpunt is gedicht);
>   verwijderen dat verfijning zou meenemen wordt geweigerd met telling + reden
>   (409 — *"verdwijnt nooit stil"*).
> - **ADR-046 vastgelegd én stuk 1 gebouwd**: levensfase · bedoeling · uitstap per
>   gebruiker · tranche — **vier vragen, vier plekken**. Levensfase op het component
>   (`b027095`); `uitfaseren` uit de bedoeling (migratie 0066); plateau-dispositie
>   afgebouwd; het niet-deterministische kaart-eerste-wint-gedrag is weg.
> - **LIKARA verzint niets meer**: "Onbekend" (migratie 0067) en de gratis
>   "Midden"-oordelen (migratie 0068) zijn weg — leeg heet overal gedempt *"nog niet
>   vastgelegd"* en is **vindbaar** (ontbreekt-filters: het registratiegat is de
>   werkvoorraad van de consultant). De filterbalk vertelt wat hij doet: *"3 van 19
>   componenten"*, elk filter als chip, los wisbaar (`39eb2ef`).
> - **Vier bouwstenen mét een scan die bijt**: veldhoogte (`.lk-veld`) · identiteit
>   (`IdentiteitLabel` — faalt luid) · filterresultaat (`FilterResultaatRegel`) ·
>   detailkop (`DetailKop`, `6cc7db0` — acties bij het object, destructief in een
>   eigen zone; 8 detailschermen omgezet). Veld- + detailkop-scan draaien met
>   zelftests mee in `test:css-build`.
> - **Gemeten, niet aangenomen**: 0 verhangen plaatsingen over 9 maanden (de plaatsing
>   is een houdbaar anker); **25/32 gebruiksfeiten zijn grof-only** → de uitstap-stand
>   hangt aan het organisatiegebruik; vóór/ná-metingen bij elke opruimmigratie
>   (19×onbekend→NULL; 19×midden→NULL ×2).
> - **38 sessie-patronen gevalideerd en vastgelegd** in de 7 likara-skills (met
>   vindplaatsen; "bewust aanvinken" + "amber/neutrale taal" expliciet als
>   ontwerpbesluit gemarkeerd, niet als code-claim).
>
> Tests: backend **1095 (2 skipped)** / frontend **92 files, 1199** groen; TST:
> `TST-V041-Validatierapport.md` (**0 kritieken**; migratieketen 0001→0068 vanaf schoon
> bewezen op een scratch-DB, seed vertelt de user story). Migratie-head **0068**.

---

## Volgende stappen — TOP-3 (besloten volgorde, ADR-046)

### 1. Stuk 3 — stand per gebruiker + Gebruik/Gebruikersgroepen één laag
De stand (*blijft · stopt-gepland · stopt-in uitvoering · gestopt*) is een feit op de
**gebruiksrelatie** (`organisatiegebruik`) — want *"het zaaksysteem wordt uitgefaseerd"*
is onwaar zodra drie van de vier gemeenten blijven. Invoer in de Gebruik-tabel (de
kolommen Stand/Tranche zijn daar al voorzien, geen herbouw). ⚠ **Harde ontwerpeis**
(OPVOLGPUNTEN LI040-punt 9): *Gebruik* en *Gebruikersgroepen* zijn nu twee tabbladen
over hetzelfde feit — zodra de stand op de gebruik-rijen landt horen grof en fijn in
**één gelaagde weergave** (grof → verfijning eronder). De zwaarte (*"nog 3 gebruikers"*)
blijft **geteld**, nooit opgeslagen; neutrale taal, amber, nooit rood (ADR-046 besluit 5).

### 2. Stuk 5 — het liegende signaal
`component_zonder_gebruikersgroep` telt serving-relaties en vuurt **onterecht op 4
componenten** met wél geregistreerd grof gebruik. Telt voortaan op het grove feit
(zelfde telbron als de zwaarte). **Eén liegend signaal besmet de rest.**

### 3. Stuk 4 — tranche
Logische groepering van een uitstap: naam + volgorde; periode optioneel; *"nog niet
ingedeeld"* is het signaal. **Geen planningstool** (ADR-046 besluit 6; eigen
tenant-tabel à la organisatiegebruik ligt het dichtst bij — vormkeuze bij de bouw).

### Daarna
- **Sentinel-besluiten** (OPVOLGPUNTEN 0a — per geval bij Bert): `HostingModel.onbekend` ·
  `ChecklistScore.nvt` · `AntwoordType.geen` · één taal voor de vijf leegte-woorden.
- **Resultaatregel-uitrol** naar contract-/partij-/proces-/bedrijfsfunctie-/architectuurlijst
  (punt 0 — per lijst count-support via het `tel`-patroon).
- **Ontwerpeisen gate 2/3** (LI039-lijn blijft staan): koppelen grof/fijn (ADR-044 b2),
  gap-signaal per plaatsing (b4), bedrijfsfunctie-doorwerking (punt 6) en *"fileshare als
  drager = gat, niet groen"* (punt 10); diagram-layout links→rechts; gate 4 kaart-op-functies.
- **Kleiner**: server-side identiteitskopieën (7) · ADR-047-comment-sweep (8, 9 verwijzingen) ·
  spook-gebruik (4) · contract-datums als uitstap-signaal (5) · aard-hint-ruis (11) ·
  `platform_init`-lokaal vergt lk_admin-URL (11a).

### Staande werkafspraken (ongewijzigd + LI040-aanscherpingen)
- Startregel: uitsluitend op `START: [naam]`; `AKKOORD: commit` exclusief door Bert in CC,
  letterlijk (varianten tellen niet).
- UX-first; browserverificatie is het sluitpunt (een niet-geresolvede component rendert
  STIL leeg — de suite blijft groen); assert op zichtbare tekst.
- Eén taak per schone worktree; commit landt vóór de volgende `START:`; bij ~100% context:
  verse sessie + zelfstandige overdracht-`.md`.
- Meten vóór besluiten; vóór/ná-metingen bij elke datamigratie; leeg ≠ fout maar wél
  vindbaar; LIKARA verzint nooit een antwoord.
- Fix in de bouwsteen; nieuwe regels waar mogelijk met een bron-scan die aantoonbaar bijt.

---

## Stand

| Veld | Waarde |
|------|--------|
| Build | V041 |
| Datum | 2026-07-14 |
| Tests | backend 1095 (2 skipped) / frontend 92 files, 1199 groen |
| Migratie-head | 0068_li040_geen_oordeel |
| TST-rapport | TST-V041-Validatierapport.md |
| Kritieke bevindingen | 0 |
| Skills | zeven likara-skills bijgewerkt (LI040 — 38 gevalideerde patronen met vindplaatsen) |


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V041"
4. Wacht op START: [naam] van Bert
