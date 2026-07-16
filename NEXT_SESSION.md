# NEXT_SESSION.md — LIKARA V043

**Gegenereerd**: 2026-07-16
**Vorige build**: V043
**Branch**: master
**Laatste commit (code)**: `e0ff6d1` gate 4 brok 1 (leeslaag `heeft_gebruikersgroep` + 5e stand
`werkvoorraad`) · daarvóór `254f905` sessie-afsluiting LI041 · `6d1b3fc` veldnorm-fix

> **Sessie LI042 — het fundament onder de bedrijfsfunctie-kaart, plus de patronen verankerd.**
>
> Wat LI042 heeft opgeleverd (gebruikerstaal):
> - **Gate 4 slice 1 + herstel (gecommit, vorige sessie-einde):** koppelen vanuit het component,
>   met "Bedrijfsfunctie" als eigen tabblad op componentdetail + het werkvoorraad-gat "systeem
>   zonder bedrijfsfunctie".
> - **Gate 4 slice 2 (kaart-swap — GEBOUWD, NIET gecommit):** de proceslaan is vervangen door de
>   bedrijfsfunctie-laan van plekken (path-expansie: een functie op meerdere plekken verschijnt
>   per plek). Backend + frontend af, tests groen. Blijft bewust ongecommit — zie stap 1.
> - **Gate 4 brok 1 (datalaag — `e0ff6d1`, gecommit + gepusht):** de leeslaag weet nu per dekkend
>   systeem óf het een gebruikersgroep draagt (`heeft_gebruikersgroep`, afgeleid uit de bestaande
>   serving-relatie), en de plek kent een **5e stand `werkvoorraad`**: systeem bekend, gebruiker
>   nog niet. Streng criterium — één dekkend systeem zonder gebruikersgroep maakt de plek al
>   werkvoorraad. Geen schema, head blijft 0070.
> - **Skill-vastlegging (7 punten, deze afsluiting gecommit):** kleur = de *actieve* kaart-lezing
>   (niet absoluut status); één lezing → één render-kanaal; afgeleide-stand-exemplaren onder het
>   bestaande recept; meebewegende legenda + het `kleurOpDomein`-gat; checkpoint-vóór-vorm;
>   parallelle read-only worktrees; tool-cadans (`/doctor` · `/security-review` · `/code-review ultra`).

---

## Top-5 prioriteiten volgende sessie

1. **Werktree ontwarren — eerst, randvoorwaarde voor alles (DC016).** Slice 2 (kaart-swap) apart
   committen: `modules/.../services/landschapskaart_service.py`, `schemas/landschapskaart.py`, de
   twee `.vue` (`KaartBeginscherm`, `LandschapskaartView`), de twee frontend-tests, en de bij
   slice-2 horende assertie in `test_landschapskaart_proces.py` (`plek_stand == "werkvoorraad"`).
   Daarna een schone tree. De skills + afsluit-docs zijn deze sessie al gecommit (disjunct).

2. **Serving-richting-bug fixen (eigen kleine slice, mét richtingtest).** `registratiegaten_service`
   leest de serving-relatie op `doel_id == Component.id` (`component_zonder_gebruikersgroep`
   :264-268 en `badge_voor_component` :201-205) — **tegengesteld** aan de énige serving-creator
   (`gebruikersgroep_service.maak_aan`: bron=component → doel=gebruikersgroep). Vlagt vrijwel elk
   component onterecht als "zonder gebruikersgroep". Fix in de **gedeelde lezing**, niet in de
   consumer. Herstelt het signaal waar brok 1 én brok 2 op leunen.

3. **Gate 4 brok 2 (kaartlaag)** — op nu-betrouwbaar fundament. Ontwerp deze sessie vastgelegd +
   read-only geverifieerd (kanaal-isolatie): lezing-dropdown (**werk / status / domein** — één
   kanaal per lezing, rest neutraliseren; "Kleur op domein" gaat op in de dropdown), zachte
   thema-bewuste canvas-zweem als modus-hint, meebewegende legenda per lezing, de 5e stand
   `werkvoorraad` als eigen rand-stijl-cue, en de stand-filter (nieuw filterpad op bestaande
   `plek_stand`-node-data). Geen schema verwacht (head 0070).

4. **Gate 4 brok 3 (seed-verhaal)** — dev-seed vertelt alle 5 standen op een verse DB, incl. een
   systeem mét én één zónder gebruikersgroep op **dezelfde** plek (streng werkvoorraad-criterium)
   en de meervoudig-geplaatste-functie-casus. Seed volgt het gebruikersverhaal, tests volgen de
   seed. (**8 organisaties** in de seed, niet 4 — feitenrapport gate-4 slice-3.)

5. **Contract-spoor** (ná gate 4) — zie Openstaande beslissingen; notitie klaar, besluit open.

---

## Openstaande beslissingen

- **Contract-analyse (notitie klaar, geen besluit).** Kernpunten:
  - **A1** = afgeleide contract-afloop-status als **leeslaag** (loopt / verloopt / verlopen —
    head-neutraal, exact het `plek_standen`-patroon).
  - **A2** = spiegelsignaal "component zonder contract".
  - **B1** = verantwoordelijkheid/toelichting op contract (skills LI038 — besloten, niet gebouwd).
  - Bedrag/administratie bewust **buiten scope**. Bouwen **ná** gate 4. Besluit docs-vastleggen/ADR
    staat open. Bron: `docs/Analyse-contractregistratie-V040.md`.

---

## Bekende risico's en aandachtspunten

- **Audit-ketenbreuk in de dev-`audit_log`** (rij van 2026-07-14, vorige sessie). Twee live-tests
  in `test_audit_capture_live.py` falen omdat ze de héle geaccumuleerde keten (89k+ rijen) lezen —
  **pre-existing data-conditie, geen code-regressie**. Opschonen/herzien wanneer relevant.
- **Werktree verstrengeld** tot stap 1 is gedraaid (slice 2 bewust ongecommit).

---

## Technische schuld

- Serving-richting-bug (stap 2 hierboven) — zolang open, is elk gebruikersgroep-signaal onbetrouwbaar.
- De dubbele registratiegaten-lezing (badge + overzicht) leunt op een afspraak; fix in de gedeelde
  lezing borgt beide.

---

## Geleerde patronen deze sessie

Verwerkt in de likara-skills (deze afsluiting gecommit):
- **kleur = de actieve lezing**, niet absoluut status (frontend — herziening).
- **één lezing, één render-kanaal** (frontend — P1); **meebewegende legenda + `kleurOpDomein`-gat**
  (frontend — P3).
- **afgeleide stand uit bestaande feiten, nooit wegschrijven** — gate-4-exemplaren onder het
  bestaande recept (backend — P2).
- **checkpoint-vóór-vorm** (werkprotocol — P4); **parallelle read-only worktrees** (werkprotocol —
  P5); **tool-cadans richting productie** (werkprotocol — P7).

De kennis leeft in de skills — geen memory-duplicaat.
