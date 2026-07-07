# NEXT_SESSION.md — LIKARA V034

**Gegenereerd**: 2026-07-07
**Vorige build**: V034

> **Sessie LI033 — ADR-040 kaart-herbouw (Fase 1). Volledig geland (V034).**
>
> Afgerond in LI033:
> - **Deterministische render-eigenaar / fcose weg** (`bf5c287`) — één opbouw → één layout → fit via de
>   layout-`stop`-callback; lost de flits- en edges-onzichtbaar-bug structureel op.
> - **Tweedeling Overzicht/Praatplaat + expliciete weergave-state + schakelaar** (2a, `e8fe7d3`); de
>   set-grootte-afgeleide modus is vervangen, de **Impact-verkenner afgeschaft**.
> - **Voorspelbare organisatie-scope** (2b, `e7f74ef`) — eenmalige deterministische seed; balk alleen op
>   Overzicht, inert op de praatplaat.
> - **Afgeleide gebruikt-lijn org→app** (spiegel van eigenaar) + gebruikt-ring + dode afdeling-sub-picker
>   weg (3-1, `559a34c`).
> - **Layout-herziening** (samen in `559a34c`) — samenval-fix (`animate:false`), Overzicht=`grid`
>   (centrumloos, deterministisch; `cose` afgewezen), Praatplaat=`concentric`+vensterverhouding-ellips,
>   grotere knopen.
> - **12 skillpatronen** (`ef17fed`).
>
> Tests: backend **951** (2 skipped) · frontend **840** (71 files). Migratie-head **0054** (ongewijzigd —
> geen schema). Enig backend-raakvlak = de afgeleide read-only gebruikt-edge. Engine onaangeroerd.

---

## ⚙️ Eerste runtime-stap (dev-DB)
Geen migratie deze sessie (head blijft `0054`). Stack starten = Docker Compose **+** `cd frontend &&
npm run dev` (Keycloak redirect naar :3000). Bij twijfel over verse data: gedocumenteerde stack-reset
(`docker compose down` → `docker volume rm likara_lk_postgres_data` → `up -d` → `dev_seed_testdata.py`;
`down -v` staat op **deny**). **LI033b-stash `stash@{0}` niet droppen zonder Berts opdracht.**

---

## Top-5 prioriteiten volgende sessie (ADR-040 vervolgfasen)

1. **Terug/vooruit-navigatie terugbouwen** — VERPLICHTE terugbouw (uitgesteld, niet geschrapt). De
   render-eigenaar is ontvlochten zodat history als **losse laag** terug kan bovenop de weergave-state.
2. **Interactie-basis** — klik = highlight + rest dimmen + **verplaatsbare popup** (kern-details +
   relaties in leesbare taal + link naar de volledige pagina); dubbelklik = hercentreren (bestaat al).
3. **De 4 component-ringen volledig inrichten** (gebruikt door · beheer · contracten & leveranciers ·
   infra & koppelingen) — fase 2; de praatplaat toont nu de ego-kring (skelet).
4. **Overige objecttypes centreerbaar** (contract, leverancier, afdeling, persoon/rol, infra) — elk een
   ring-definitie op de praatplaat-motor (ADR-040 open subknoop 1).
5. **LI033b-stash-beslissing** (droppen vs. referentie houden) + herbevestigen: ADR-036 UI-restpunt,
   `VerantwoordelijkheidSectie` partij-picker-scope, LI032-restpunten (username≠e-mail, 404-friendly,
   reseed-ergonomie).

---

## Openstaande beslissingen

- **Scope-B-verfijning** (toggles onthouden over set-wijzigingen) — later, samen met het history-/scope-werk
  (nu A: elke set-wijziging → alle orgs aan).
- **LI033b-stash** — droppen of als referentie houden (Berts keuze).
- **Overzicht-filtering** die overleeft + doorschakelen naar impact (ADR-040 open subknopen 3/6, fase 5/6).

---

## Bekende risico's en aandachtspunten

- De volledige interactie-basis en de 4 ringen zijn nog **skelet** op de praatplaat — de kernvraag "wat
  raakt object X" werkt pas end-to-end na fase 2.
- Leesbaarheid van de layout is een **browsercheck-criterium** (headless meet geen labelbreedte); de
  grid-`avoidOverlapPadding` en font-grootte zijn eenvoudige tunables.

---

## Technische schuld

- Terug/vooruit-navigatie is tijdelijk niet actief langs de nieuwe weergave-state (zie top-5 #1).
- `LandschapskaartView.test.js` cytoscape-teardown-flake (unhandled-rejections bij teardown) — geen
  testfalen; mee te nemen bij de interactie-/render-fasen.

---

## Geleerde patronen deze sessie
12 patronen vastgelegd in `ef17fed` (likara-werkprotocol/tests/frontend/ux/resilience/domeinmodel) —
o.a. read-only-eerst boven aannames, volledige suite bij een gedeeld symbool, deterministische layout +
render-eigenaar, filter = niet-destructieve lens, browser-console als eerste diagnose-instrument,
afgeleide read-only kaart-edges spiegelen een bestaande edge. Niet overdoen.
