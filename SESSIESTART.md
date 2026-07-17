# SESSIESTART — LIKARA V044

**Datum**: 2026-07-17
**Platform**: LIKARA — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/likara/ bestaat
   - Zo ja: normale modus — lees alle likara-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — LIKARA V044 — [N] skills geladen"
5. Wacht op START: [naam] van Bert

---

## Interactieregel (VERPLICHT — niet-onderhandelbaar)

Geldt voor zowel CC als claude.ai, in elke sessie:

- Stel vragen ALTIJD één voor één. Stel nooit meerdere vragen tegelijk.
  Wacht op het antwoord van Bert voordat je een volgende vraag stelt.
- Geef adviezen ALTIJD één voor één. Geef nooit meerdere adviezen tegelijk.
  Wacht op de reactie van Bert voordat je een volgend advies geeft.

Deze regel is niet-onderhandelbaar en overschrijft elke neiging om
meerdere vragen of adviezen te bundelen.

---

## Opdrachtformaat CC-opdrachten (VERPLICHT — standaardwerkwijze)

claude.ai levert elke CC-opdracht ALTIJD aan als een .md-bestand
(downloadbaar), nooit als een los codeblok in de chat. Bert gebruikt dat
.md-bestand in CC. Deze afspraak geldt in elke sessie.

---

# SESSIE_BRIEFING.md — LIKARA V044

**Gegenereerd**: 2026-07-17

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V044 |
| Datum | July 2026 |
| Commit | 5c4e479 |
| Tests | backend 1133 passed / 2 skipped / 0 failed · frontend 95 files / 1222 passed · vite build OK |
| TST-rapport | TST-V044-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
5c4e479 [skills][docs] LI043 — zes sessiepatronen vastgelegd (presentatie-single-source, canvas-token, plek-stand-kleurtaal, bediening, leeg-is-geen-oordeel, aandacht-schaalt-met-gewicht)
9b322b6 [frontend] LI043 naam-fix — beoordelings-veldlabel → "Beoordelingsstatus", structureel uit de VELD_LABELS-registry
6d41dbf [frontend] LI043 slice B2 — stand-codering op de kaart + meebewegende standen-legenda (gedeelde bron, optie A) — G4-6
8937e95 [docs] LI043 ontwerpspoor — beoordelingsgrondslag (tenant-waarde-norm) + gewogen open-punten-overzicht
38b02eb [skills] LI043 domeinmodel — terminologie component/type/applicatie vastgelegd; "systeem" geen synoniem
```

---

## Prioriteiten volgende sessie

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

1. **Gate 4 restant / ADR-046-stubs — de resterende MVP-gate-stappen.** Ná de nu-voltooide kaart-lezing:
   levensfase / bedoeling (`migratiepad`) / uitstap-stand (stuk 3, `organisatiegebruik`) / tranche (stuk 4).
   Dit is de laatste MVP-laag op de bedrijfsfunctie-as. Volgorde + afhankelijkheden: OPVOLGPUNTEN
   (LI040/LI041-blokken, ADR-046).

2. **Open-punten-overzicht per component (kan EERDER, ongewogen).** Het overzicht "alles wat dit systeem
   nog nodig heeft" (Dit moet nog / Dit zou netjes zijn, met route) kan al landen op de **bestaande
   ophaalbare** bronnen (checklist nee/deels + `signalering.badgeComponent`) — de weging komt later. Ontwerp
   (mockup) eerst. Grond: OPVOLGPUNTEN LI043-blok + feitcheck `feitcheck-open-punten-bronnen`.

3. **Beoordelingsgrondslag (groot post-MVP ontwerpspoor) — het fundament onder (2).** Tenant-configureerbare
   waarde-norm; "moet/netjes" volgt eruit; degradeert netjes (werkt ongewogen). Verankerd in OPVOLGPUNTEN
   (LI043-blok, item 1). Ontwerp/ADR vóór bouw; raakt vermoedelijk schema (nieuw model/catalogus).

4. **De twee B2-bevindingen — koppelen aan de beoordelingsgrondslag.** (a) Op de kaart delen gat en
   werkvoorraad dezelfde amber (onderscheid leest via lijst-pill/hover) — herzien of dat volstaat; (b) de
   lezingen Werk/Status/Domein zijn niet symmetrisch (Werk draagt de stand-kleuren, de andere niet). Beide
   pas herzien wanneer de beoordelingsgrondslag er is; niet los oplossen.

5. **Contract-spoor** (ná gate 4) — zie Openstaande beslissingen; notitie klaar, besluit open.

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


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V044"
4. Wacht op START: [naam] van Bert

