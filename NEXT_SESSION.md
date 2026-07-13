# NEXT_SESSION.md — LIKARA V040

**Gegenereerd**: 2026-07-13
**Vorige build**: V040
**Branch**: master
**Laatste commit**: (afsluitcommit V040; daarvóór `cf0f046` gate 1b · `85b9cf5` gate 1a-bis)

> **Sessie LI039 — De bedrijfsfunctie-as staat op het échte GEMMA-model (V040).**
>
> Afgerond in LI039:
> - **Gate 1a-bis (ADR-044, `85b9cf5`):** plaatsing als eerste-klas feit — `ouder_id`
>   vervalt, de functieboom leeft in aggregation-plaatsingen; één functie op meerdere
>   plekken (de 7 GEMMA-gevallen), getoond als "staat ook onder", nooit stil opgelost.
> - **Gate 1b (`cf0f046`):** referentiemodel inlezen — veilige AMEFF-lezer (defusedxml,
>   XXE-weigering), dry-run en uitvoering op ÉÉN plan (bronsleutel = identiteit; vervallen =
>   markeren; eigen functies ongemoeid), gecureerd GEMMA-bestand in de repo (release
>   1 juli 2026, commit-gepind, EUPL — `referentiemodellen/HERKOMST.md`), dev-seed leest het
>   echte model (297 functies · 302 plaatsingen), "Model inlezen" met voorbeeld-vóór-
>   bevestigen + platform-aanbodscherm, RBAC inlezen = beheerder.
> - **Browsercheck-fixes (zelfde commit):** aanbod-staten gevuld/leeg/fout sluiten elkaar
>   structureel uit (leeg = toestand, geen fout) · onvoltooide inlees nooit stil
>   (begin-/eindmarkering `inlees_voltooid`, migratie 0064, waarschuwing + hervat-route).
> - **Patronen-validatie fase A+B:** 32 sessie-patronen tegen de code getoetst
>   (`docs/Validatie-patronen-LI039.md` — 0 botsingen; 3 deel-correcties door Bert
>   besloten) en vastgelegd in 7 skills, mét status-markering en de 12-tekst-regels-lijst.
>
> Tests: backend **1040 (2 skipped)** / frontend **88 files, 1146** groen; TST:
> `TST-V040-Validatierapport.md` (0 kritieken). Migratie-head **0064**.

---

## Volgende stappen — TOP-5 (in deze volgorde)

### 1. ADR-026-afronding: "ondersteunt werk" als eigenschap van het componenttype *(voorwaarde voor gate 2)*
De opdracht ligt klaar. Besloten LI039: alleen wat werk ondersteunt mag aan een
bedrijfsfunctie hangen; dat wordt een **eigenschap van het componenttype** (precedent:
`checklist_dragend` op `componentconfig_optie`), geen lijst in code. ADR schrijven + de
eigenschap landen. Neem hierin mee: de **picker-uitleg** ("waarom ontbreekt mijn database")
— besloten opvolgpunt, precies hier voor het eerst nodig.

### 2. Gate 2 — koppelen: grof en fijn (ADR-044 besluit 2)
Component ↔ bedrijfsfunctie op de PLAATSING: verfijnen vervángt het grove antwoord op die
plek; "erbij" = meerdere componenten op één plaatsing; koppel-UX bij meervoud (één
zoekresultaat, "geldt overal" voorop, meerdere plekken tegelijk verfijnen). Vult ook de
in-gebruik-telling van het inlees-voorbeeld ("3 vervallen — waarvan N nog in gebruik").

### 3. Diagram-layout: links→rechts, haakse lijnen, meervoud als verwijzing *(besloten, opdracht ligt klaar)*
Vervangt de huidige top-down-weergave met alle-lijnen-getekend (expliciet zo gemarkeerd in
likara-frontend). Combineer met de **leesbaarheids-ontwerpronde van de boom bij 297
functies** (eigen ronde, nog te doen — Berts browseroordeel is de maat).

### 4. Gate 3 — het gap-signaal per plaatsing (ADR-044 besluit 4)
"Geen ondersteunend systeem" hangt aan de PLEK, niet aan de functie; "hier gebruiken we
niets" = vastgestelde bevinding ≠ "nooit naar gekeken" (besluit 3).

### 5. Gate 4 — kaart op functies + procesregister uit beeld
De kaart rust op bedrijfsfuncties; procesmenu/-ingangen eruit (model en LI038-bouw blijven
intact — hergebruik, n≥2). Daarna is de logische kaart de MVP.

**Positionering (naast de bouw):** de **ketting functie → systeem → partij → contract** als
verhaal van LIKARA — zie de drie V040-marktverkenningsrapporten
(`Marktverkenning-concurrenten-V040.md`, `Marktverkenning-ketting-V040.md`,
`Verkenning-GEMMA-context-V040.md`, meegecommit in `cf0f046`).

### Openstaand (detail + status in `docs/OPVOLGPUNTEN.md`)
Toestandsbouwsteen "leeg ≠ fout" (converge bij n≥2 — de gevaarlijkste tekst-regel) ·
picker-uitleg (→ TOP-1) · GEMMA "Toelichting"-property · zinsgrens-afkapping leeslaag (laag) ·
ADR-spoor registratie-feiten op objecten · beginscherm als vertrekpunt · plaatstaat-herstel ·
architectuur-scherm verwijderen (`ARCHITECTUUR.LEZEN` behouden — de kaart gebruikt het).

### Staande werkafspraken (ongewijzigd + LI039-aanscherpingen)
- Startregel: uitsluitend op `START: [naam]`; `AKKOORD: commit` exclusief door Bert in CC.
- UX-first; browsercheck-bevindingen → patroon-onderzoek vóór punt-fixes; groene tests ≠
  sign-off; elk UI-pad heeft een test die hem opent.
- Gate-discipline; hypothese van de PNA ≠ bouwopdracht (2× herbewezen LI039); telling vóór
  besluit; nieuwe dependency ⇒ image herbouwen; migratie bouwen ÉN toepassen binnen de slice.
- Eigen test-tenant zodra een teardown breder veegt dan de eigen fixtures.
- Kernles LI038 blijft: regels borgen in gedeelde bouwstenen; fix in de bouwsteen.

---

## Stand

| Veld | Waarde |
|------|--------|
| Build | V040 |
| Datum | 2026-07-13 |
| Tests | backend 1040 (2 skipped) / frontend 88 files, 1146 groen |
| Migratie-head | 0064_gate1b_inlees_voltooid |
| TST-rapport | TST-V040-Validatierapport.md |
| Kritieke bevindingen | 0 |
| Skills | zeven likara-skills bijgewerkt (LI039 fase B — gevalideerde patronen, status-markeringen, tekst-regels-lijst) |
| Dev-DB | 299 functies (echt GEMMA-model) · `inlees_voltooid = true` · restdata 0 |
