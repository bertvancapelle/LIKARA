# NEXT_SESSION.md — LIKARA V038

**Gegenereerd**: 2026-07-11
**Vorige build**: V038
**Branch**: master

> **Sessie LI037 — Deelprocessen eerste-klas + tree-view-procesbeheer volledig geland (V038).**
>
> Afgerond in LI037:
> - **Deelprocessen eerste-klas op de kaart (fase 0–4)** — seed 3 niveaus + gap-deelproces
>   (`ba6f688`) · backend **subboom-projectie**: elk subboom-lid als knoop, hiërarchie-edges
>   "onderdeel van", vervult-edges op het geregistreerde (deel)proces, één roll-up-bron
>   (`8904b2a`) · proceszone als **boom** + gap-cue met subboom-semantiek (`4a29f2a`) ·
>   **twee proces-ingangen** via één handoff, herkomst = oranje selectie + centrering
>   (`932f607`) · **dubbelklik-inzoom** = set-inperking, terug via history (`a970fac`).
>   Het LI036-diepte-punt ("alleen hoofdprocessen") is hiermee gesloten (ADR-034-amendement).
> - **Seed-idempotentie** — verantwoordelijken op vaste identiteit, twee-runs-stabiel (`ef2421f`).
> - **Tree-view procesregister** — verbindingslijnen op gedeelde `procesBoomStructuur` + gap-cue
>   (`ca6501a`); verwijderen + verhangen met kring-preventie-vóóraf (`ed0799b`); gating-/
>   vorm-consistentie: destructief → `magVerwijderen` op 6 plekken, rij-acties als danger-knoppen
>   (`d4b7266`).
> - **Borging** — 12 patronen in vier likara-skills + zes opvolgpunten (`d87aad7`).
>
> Tests: frontend **81 files, 1046** groen; backend + TST: zie `TST-V038-Validatierapport.md`.
> Migratie-head **0059** (geen schema-wijziging deze sessie).

---

## Volgende stappen — TOP-5 (in deze volgorde)

### 1. Plaatstaat-herstel na onbedoelde onderbreking
lk-state (set/weergave/ringen/scope) overleeft timeout/herlaad/browser-dicht — **zonder
tijdslimiet**; alleen bewuste actie (uitloggen/"Begin opnieuw"/nieuwe verkenning) geeft schone
start. Herstel-na-onderbreking, géén bewaarde voorkeur (ADR-041 blijft). Eerst read-only
feitencheck: Keycloak-sessie-/tokenlevensduur + waar lk-state leeft + bewaarplek
(privacy-randje). Raakt de auth/401-cluster.

### 2. Architectuur-scherm compleet verwijderen (besluit A)
Lagen-view + Tabel-view + zijbalk-menu + route. Ingehaald door de kaart-lagenweergave; elk
elementtype heeft z'n eigen register. Eerst read-only inventarisatie van alles wat eraan hangt —
**KRITISCH: `ARCHITECTUUR.LEZEN` NIET verwijderen** (de Landschapskaart gebruikt die ook); check
`architectuur_service`, inkomende "Open in Architectuur"-links, tests. Eigen slice met gate +
browsercheck.

### 3. Beginscherm als enige vertrekpunt
Linker filterkolom verbergen/inklappen zolang er geen selectie is (0 in beeld); pas tonen zodra
er een set is; "Begin opnieuw" → terug naar alleen het beginscherm. Open: verbergen vs.
inklappen; wat de kolom toont bij lege set.

### 4. Rapportage & export (eigen strategisch spoor, eerst doordenken)
PDF van een kaart-selectie: (a) grafische weergave van de getoonde plaat + (b) leesbare
beschrijving van álle getoonde relaties (via de bestaande relatie-hertaling). Bundelt oude
fragmenten (ADR-025 import/export/rapportage; PDF-per-applicatie; Excel/CSV bestuurlijk;
PNG/PDF-kaart). Open: scope (hele selectie vs. per knoop); v1 sjabloon-tekst (deterministisch)
vs. AI-proza (later, governance-kanttekening); render (SVG/PNG uit Cytoscape); backend- vs.
frontend-PDF; UI-plek; RBAC; performance bij schaal.

### 5. Bredere ruggengraat (uit OPVOLGPUNTEN)
Audit-dekking op deletes; UI-consistentiebundel (11 bevestig-dialogen → één, 2 waarschuwingen →
standaard, verwijder-asymmetrie partijrollen); kaart component-breed (ADR-verkenning: elk
componenttype zoekbare knoop); contactpersoon als keuze uit personen eigen organisatie
(schema-gate); GEMMA-procesimport (eigen ADR-spoor).

### Nieuw uit LI037 (niet gerangschikt — detail + status in `docs/OPVOLGPUNTEN.md`)
Proces-only diagram (te ontwerpen, eigen slice); ADR-spoor procesafhankelijkheden/flow
(bepaalt de rijkdom van het proces-diagram); detailscherm-procesbeheer (besluit A: nu niet);
rollenmodel generiek vs. functioneel + proces-toepasbaarheid (te groot voor nu, strategisch
ADR); proces-ingang-weergave (productie-evaluatiepunt); history-grens hele-landschap-herstel
(read-only checkpoint + fix).

### Staande werkafspraken (ongewijzigd)
- Startregel: uitsluitend op `START: [naam]`; `AKKOORD: commit` is de exclusieve commit-trigger
  (uitsluitend door Bert, rechtstreeks in CC — nooit in een opdracht-`.md`).
- UX-first: gebruikerservaring is het uitgangspunt, techniek is vangrail; browsercheck-bevindingen
  → patroon-onderzoek vóór punt-fixes; rol-gating browserchecken met béíde rollen.
- Gate-discipline: schema-/UX-slices stoppen met gate-rapport + browsercheck-draaiboek vóór commit;
  reikwijdte-scan vóór een klasse-fix; vitest altijd vanuit `frontend/`; backend-suite vanaf de
  repo-root.

---

## Stand

| Veld | Waarde |
|------|--------|
| Build | V038 |
| Datum | 2026-07-11 |
| Tests | backend zie TST-V038 / frontend 81 files, 1046 groen |
| Migratie-head | 0059_adr042_procesvervulling |
| TST-rapport | TST-V038-Validatierapport.md |
| Kritieke bevindingen | 0 |
| Skills | vier likara-skills bijgewerkt (12 LI037-patronen); domeinmodel → subboom-realiteit |
