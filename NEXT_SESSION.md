# NEXT_SESSION.md — LIKARA V037

**Gegenereerd**: 2026-07-10
**Vorige build**: V037
**Branch**: master

> **Sessie LI036 — Lagenweergave mét proceslaan volledig geland (V037).**
>
> Afgerond in LI036:
> - **"Lagen" als derde kaart-weergave** — Cytoscape preset-baanposities + HTML-band-overlay,
>   render-fix eerste frame (meet-stap `updateStyle` + `layoutDimensions` in de preset-tak),
>   maatwissel = resize + fit zonder re-layout (`7b4c00c`).
> - **Rolbanen met rol-accent** — partij als visuele instance per rolbaan (`id@baan`, interactie op
>   `logischId`), rol-tags als HTML-pill-overlay die de dim-staat delen (`7b4c00c`).
> - **"Ring uit wint van gaps"** + **organisatiebalk toont alleen in-beeld-organisaties (model i,
>   contrafeitelijk; uitzetten omkeerbaar)** (`0b4a5dd`).
> - **Proceslaan (slice 2, stap 1–3)**: backend proces-projectie in de subgraaf — roll-up naar
>   hoofdproces, cyclus-veilig, één roll-up-definitie, engine onaangeroerd (`d2b07f3`) · frontend
>   proceslaan + ring "Processen" + proces-vorm afgeronde rechthoek/verloop-pijl (`5fa5fe0`) ·
>   aantal-badge + inklapbare herkomst-popup + vervul-toggle met exact-ongedaan-maken (`f9a8a6f`).
> - **16 patronen geborgd in vijf likara-skills** (`9914c25`); **ADR-034/040 bijgewerkt naar de
>   gebouwde realiteit** — diepte-punt "alleen hoofdprocessen" prominent als tussenstand (`a99fe23`).
>
> Tests: backend **1001** (2 skipped) / frontend **80 files, 1006** groen. Migratie-head **0059**
> (geen schema-wijziging deze sessie).

---

## Volgende stappen — TOP-6 (in deze volgorde)

### 1. Deelprocessen eerste-klas op de kaart — ✅ GELAND in LI037
Volledig gebouwd en gecommit in LI037 (fase 0–4: seed 3 niveaus + ADR-034-amendement,
backend-subboom-projectie, proceszone-als-boom + gap-cue, twee proces-ingangen via één
handoff met oranje-selectie-focus, dubbelklik-inzoom) — plus tree-view-procesbeheer
(lijnen/gap-cue, verwijderen + verhangen) en de gating-/vorm-fix. **Zes nieuwe
opvolgpunten uit LI037 staan in `docs/OPVOLGPUNTEN.md`** (proces-only diagram; ADR-spoor
procesafhankelijkheden; detailscherm-procesbeheer; rollenmodel/functionele rollen;
proces-ingang-evaluatie; history-grens hele-landschap). Oorspronkelijke opdracht hieronder
ter referentie.

#### (oorspronkelijk) Deelprocessen eerste-klas op de kaart (besloten top-1)
Component→(deel)proces zichtbaar (niet weggerold); proceshiërarchie deelproces→hoofdproces als
knopen+lijnen; deelprocessen uitvouwbaar detail-op-aanvraag; plotbaar vanuit component én vanuit
(deel)proces. Herziet de stap-1-diepte-keuze ("alleen hoofdprocessen" = tussenstand — zie
ADR-034 ⚠ bewust openstaand).

**Bevat het geparkeerde "proces als kaart-vertrekpunt":** "Bekijk op kaart" vanaf een
(deel)proces zet dát proces als centrum; opent in **Lagen**; laadt de **doorgerolde
subboom-vervullers** (unie procesvervullingen + rollup); **neutraal openen** (niet gedimd);
vanaf een deelproces → hoofdproces-context mét oorsprong-signaal (deelproces benoemd).
Ingangen: knop op ProcesDetail + "Via proces"-zoekingang in KaartBeginscherm. Puur frontend
(kaartHandoff + weergave-veld). **Start met een read-only checkpoint + ontwerpdialoog.**

### 2. Plaatstaat-herstel na onbedoelde onderbreking
lk-state (set/weergave/ringen/scope) overleeft timeout/herlaad/browser-dicht — **zonder
tijdslimiet**; alleen bewuste actie (uitloggen/"Begin opnieuw"/nieuwe verkenning) geeft schone
start. Herstel-na-onderbreking, géén bewaarde voorkeur (ADR-041 blijft). Eerst read-only
feitencheck: Keycloak-sessie-/tokenlevensduur + waar lk-state leeft + bewaarplek
(privacy-randje). Raakt de auth/401-cluster.

### 3. Architectuur-scherm compleet verwijderen (besluit A)
Lagen-view + Tabel-view + zijbalk-menu + route. Ingehaald door de kaart-lagenweergave; elk
elementtype heeft z'n eigen register. Eerst read-only inventarisatie van alles wat eraan hangt —
**KRITISCH: `ARCHITECTUUR.LEZEN` NIET verwijderen** (de Landschapskaart gebruikt die ook); check
`architectuur_service`, inkomende "Open in Architectuur"-links, tests. Eigen slice met gate +
browsercheck.

### 4. Beginscherm als enige vertrekpunt
Linker filterkolom verbergen/inklappen zolang er geen selectie is (0 in beeld); pas tonen zodra
er een set is; "Begin opnieuw" → terug naar alleen het beginscherm. Open: verbergen vs.
inklappen; wat de kolom toont bij lege set.

### 5. Rapportage & export (eigen strategisch spoor, eerst doordenken)
PDF van een kaart-selectie: (a) grafische weergave van de getoonde plaat + (b) leesbare
beschrijving van álle getoonde relaties (via de bestaande relatie-hertaling). Bundelt oude
fragmenten (ADR-025 import/export/rapportage; PDF-per-applicatie; Excel/CSV bestuurlijk;
PNG/PDF-kaart). Open: scope (hele selectie vs. per knoop); v1 sjabloon-tekst (deterministisch)
vs. AI-proza (later, governance-kanttekening); render (SVG/PNG uit Cytoscape); backend- vs.
frontend-PDF; UI-plek; RBAC; performance bij schaal.

### 6. Bredere ruggengraat (uit OPVOLGPUNTEN)
Audit-dekking op deletes; UI-consistentiebundel (11 bevestig-dialogen → één, 2 waarschuwingen →
standaard, verwijder-asymmetrie partijrollen); kaart component-breed (ADR-verkenning: elk
componenttype zoekbare knoop); contactpersoon als keuze uit personen eigen organisatie
(schema-gate); GEMMA-procesimport (eigen ADR-spoor).

### Staande werkafspraken (ongewijzigd)
- Startregel: uitsluitend op `START: [naam]`; `AKKOORD: commit` is de exclusieve commit-trigger.
- UX-first: gebruikerservaring is het uitgangspunt, techniek is vangrail; browsercheck-bevindingen
  → patroon-onderzoek vóór punt-fixes.
- Gate-discipline: schema-/UX-slices stoppen met gate-rapport + browsercheck-draaiboek vóór commit;
  vitest altijd vanuit `frontend/`; backend-suite vanaf de repo-root.

---

## Stand

| Veld | Waarde |
|------|--------|
| Build | V037 |
| Datum | 2026-07-10 |
| Tests | backend 1001 (2 skipped) / frontend 80 files, 1006 groen |
| Migratie-head | 0059_adr042_procesvervulling |
| TST-rapport | TST-V037-Validatierapport.md |
| Kritieke bevindingen | 0 |
| Skills | vijf likara-skills bijgewerkt (16 LI036-patronen); ADR-034/040 → gebouwde realiteit |
