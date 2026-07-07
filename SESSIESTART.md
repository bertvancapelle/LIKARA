# SESSIESTART — LIKARA V034

**Datum**: 2026-07-07
**Platform**: LIKARA — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/likara/ bestaat
   - Zo ja: normale modus — lees alle likara-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — LIKARA V034 — [N] skills geladen"
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

# SESSIE_BRIEFING.md — LIKARA V034

**Gegenereerd**: 2026-07-07

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V034 |
| Datum | July 2026 |
| Commit | ef17fed |
| Tests | backend 951 (2 skipped) / frontend 840 groen (71 files) |
| TST-rapport | TST-V034-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
ef17fed [skills] LI033 — 12 herbruikbare patronen uit de ADR-040-sessie vastgelegd
559a34c [frontend+backend] ADR-040 F1 stap 3-1 + layout: gebruikt-lijn + kaart-layout herzien — ADR-040
e7f74ef [frontend] ADR-040 F1 stap 2b: scope-multiselect voorspelbaar + balk alleen op Overzicht — ADR-040
e8fe7d3 [frontend] ADR-040 F1 stap 2a: expliciete weergave-state + Impact-verkenner afgeschaft — ADR-040
bf5c287 [kaart] deterministische, fcose-vrije teken-cyclus (render-eigenaar) — ADR-040 F1 stap 1+3
```

---

## Prioriteiten volgende sessie

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


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V034"
4. Wacht op START: [naam] van Bert

