# NEXT_SESSION.md — LIKARA V044

**Gegenereerd**: 2026-07-17
**Vorige build**: V044
**Branch**: master
**Laatste commit (code)**: `9b322b6` naam-fix "Beoordelingsstatus" · daarvóór `6d41dbf` slice B2 ·
`972df21` slice B1 · `ac9db21` slice A · `bd60085` brok 3 seed · `bae58b2` serving-fix

> **Sessie LI043 — de bedrijfsfunctie-kaart is nu leesbaar; de beoordelingsstatus heeft een naam.**
>
> Wat LI043 heeft opgeleverd (gebruikerstaal):
> - **Gate 4 kaart-lezing compleet.** De kaart toont per bedrijfsfunctie-plek in één oogopslag waar
>   werk ligt: **slice A** (lezing werk/status/domein + neutraliseer-model + meebewegende legenda),
>   **slice B1** (ernst-pills in de lijst) en **slice B2** (dezelfde stand-kleuren op de kaart + legenda,
>   uit één bron `standCodering`). Lijst ↔ kaart vertellen identiek: amber = werk · groen = draait ·
>   blauw = via boven · grijs = besluit.
> - **Serving-richting-fix.** "Systeem zonder gebruikersgroep" leest nu de juiste richting (bron=component);
>   het signaal waarop brok 1/2 leunen is betrouwbaar.
> - **Brok 3 dev-seed.** Een verse DB vertelt alle vijf standen (incl. een plek mét én zónder
>   gebruikersgroep); proces-seed verwijderd.
> - **Naam-fix "Beoordelingsstatus".** Het verwarrende "Lifecycle"/"Status"-veld heet overal
>   "Beoordelingsstatus", structureel uit de `VELD_LABELS`-registry (één bron, sentinel-getest).
> - **Borging:** domeinmodel-terminologie (component/type/applicatie; "systeem" geen synoniem) +
>   zes sessiepatronen in frontend/ux + LOKAAL-TESTEN.

---

## Top-5 prioriteiten volgende sessie

> **PNA-advies volgorde (kernafweging): waarde vóór fundament.** Lever eerst wat de consultant voelt (het
> open-punten-overzicht), en leg het fundament (de beoordelingsgrondslag) eronder wanneer het overzicht
> erom vraagt — niet andersom. Ervoor bouwen is het Drimmelen-/receding-horizon-patroon (maanden norm vóór
> de eerste waarde). Afwijking t.o.v. de vorige ordening: het overzicht schuift vóór de gate-4-restant.

1. **Open-punten-overzicht per component (ongewogen) — EERST.** *Grootste gebruikerswinst voor de kleinste
   bouw:* dit is waar de consultant deze sessie het hardst "de weg kwijt" bleek (vier tabbladen, twee badges,
   geen verhaal). Kan **nú** al — de bronnen zijn ophaalbaar (checklist nee/deels + `signalering.badgeComponent`;
   `feitcheck-open-punten-bronnen`) — en is browser-aftekenbaar op de bestaande data. Start met een **mockup**
   (Bert beslist het scherpst op beeld); de bronnen-inventaris ligt er al. Grond: OPVOLGPUNTEN LI043-blok.

2. **Beoordelingsgrondslag — DAARNA, niet ervoor.** *Groot, schema-rakend fundament.* Het overzicht werkt
   ongewogen prima; de grondslag is **verrijking (weging), geen voorwaarde**. Overzicht = waarde, grondslag =
   scherpte. Verankerd in OPVOLGPUNTEN (LI043-blok, item 1). Ontwerp/ADR vóór bouw; raakt vermoedelijk schema.

3. **De twee B2-bevindingen — GEKOPPELD aan de grondslag, niet los.** *Ze veranderen van betekenis zodra
   "werk" tegen een grondslag gewogen wordt — nu herijken = dubbel werk.* (a) gat en werkvoorraad delen op de
   kaart dezelfde amber; (b) de lezingen Werk/Status/Domein zijn niet symmetrisch. Herzien mét (2), niet ervoor.

4. **Gate-4-restant / ADR-046-stubs — NA het overzicht.** *Zonder het open-punten-inzicht produceren ze "een
   IT-lijst i.p.v. een governance-feit"; het overzicht geeft ze context.* levensfase / bedoeling (`migratiepad`)
   / uitstap-stand (stuk 3, `organisatiegebruik`) / tranche (stuk 4) — de laatste MVP-laag op de
   bedrijfsfunctie-as. Afhankelijkheden: OPVOLGPUNTEN (LI040/LI041-blokken, ADR-046).

5. **Contract-spoor** (ná gate 4) — zoals gepland; zie Openstaande beslissingen. Notitie klaar, besluit open.

---

## Openstaande beslissingen

- **LOKAAL-TESTEN §1b (klein).** De reseed/reset-commando's in de doc (`docker exec -w /app lk-api python3
  dev_seed_testdata.py`; volume-rm-route i.p.v. `down -v`) zijn correct en blijven. Alleen als je een andere
  vorm wilt, is dat een aparte doc-wijziging. (Vastgesteld in `vastleggen-sessiepatronen`.)
- **Contract-analyse (notitie klaar, geen besluit).** A1 afgeleide contract-afloop-leeslaag · A2 spiegelsignaal
  "component zonder contract" · B1 verantwoordelijkheid/toelichting op contract (skills LI038, besloten niet
  gebouwd). Bedrag/administratie buiten scope. Bouwen ná gate 4. Bron: `docs/Analyse-contractregistratie-V040.md`.

---

## Losse opvolgpunten (deze sessie toegevoegd — staan in OPVOLGPUNTEN.md)

- **L1a** — ijkpunt als auditeerbaar wilsbesluit (werk-terugzet/vernietig, selectieve lijn).
- **G4-1d** — kaart-state-hardening (`_herstelKaartState` herstelt een dode set na `down -v` → 0-subgraaf).
- **G4-4** — dode proces-handoff-tak op de kaart na de plek-laan-swap.
- **G4-5** — domein-lezing afleiden uit de functie-as (nu proxy: componenttype-label "Applicatie").
- **0b** — Signalering-scherm als werkvoorraad-checklist (per systeem + oplichten + klikbare badges).
- **Granulaire CRUD × persona** (post-MVP) — indien nog genoteerd; anders bij het open-punten-spoor.

---

## Bekende risico's en aandachtspunten

- **Audit-keten in de dev-`audit_log`: OPGELOST.** De 2 V043-live-tests (`test_audit_capture_live.py`)
  **slagen nu** (data-conditie weg, waarschijnlijk via reseed). Geen pre-existing failure meer.
- **Geen verstrengelde werktree** — alle LI043-bouw is per opdracht apart geland. Schone start.

---

## Technische schuld

- **De twee amber-standen (gat/werkvoorraad) delen op de kaart één kleur** — bewust (onderscheid via tekst),
  maar te herzien bij de beoordelingsgrondslag (top-4).
- **`object_zonder_roltoewijzing` vs. `component_zonder_verantwoordelijke`** — één feit, twee signaal-sleutels;
  in het open-punten-overzicht als één punt tonen (feitcheck-open-punten-bronnen).

---

## Geleerde patronen deze sessie

Verankerd in de likara-skills (deze afsluiting gecommit), geen memory-duplicaat:
- **Eén bron voor PRESENTATIE, niet alleen data** — label/kleur/icoon/legenda op één plek + verplichte
  sentinel-test (frontend — P1).
- **Canvas resolvet het token op tekenmoment** (`standKaartKleur`), nooit een tweede kleur-literal (frontend — P2).
- **Plek-stand-kleurtaal** amber/groen/blauw/grijs — een aparte as, niet te verwarren met signalering-🔴/🟡
  of de status-lezing-tinten (ux — P3).
- **Leeg ≠ een ingevulde waarde/oordeel** — geen proxy/placeholder als schijnwaarde (ux — P5).
- **Aandacht schaalt met gewicht** — bevestiging = auditeerbaar wilsbesluit (ux — P6, zie L1a).
- **Bedieningsfeiten** (kaart opent op verkenningsscherm) in LOKAAL-TESTEN (P4).
- **Terminologie** component/type/applicatie; "systeem" geen synoniem (domeinmodel).
