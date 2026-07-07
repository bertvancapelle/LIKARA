# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V034 · 2026-07-07
- **Commit:** `ef17fed` (12 skillpatronen) — sessie-afsluiting V034 (docs + build) volgt
- **Tests:** backend 951 / 2 skipped / 0 failed · frontend 840 groen (71 files) · 0 kritieken
- **Migratie-head:** `0054_contactpersoon_ref` (ongewijzigd — geen schema deze sessie)
- **TST-rapport:** `docs/TST-V034-Validatierapport.md`
- **Bekende ruis:** `LandschapskaartView.test.js` cytoscape-teardown-flake (unhandled-rejections; geen
  testfalen).

## Deze sessie (LI033 — ADR-040 kaart-herbouw, Fase 1) — AFGEROND
**Kader:** de fragiele alleskunner-kaart herbouwen tot twee gerichte weergaven met een deterministische
render, en het gat "wie gebruikt applicatie X" dichten. Puur read-only/afgeleid; engine onaangeroerd;
geen schema.
- **Render-eigenaar deterministisch / fcose weg (`bf5c287`).** Eén opbouw → één layout → fit via de
  layout-`stop`-callback; flits- en edges-onzichtbaar-bug structureel opgelost.
- **Tweedeling Overzicht/Praatplaat + expliciete weergave-state + schakelaar (2a, `e8fe7d3`).** De
  set-grootte-afgeleide modus vervangen; **Impact-verkenner afgeschaft**; "hele landschap" = Overzicht.
- **Voorspelbare organisatie-scope (2b, `e7f74ef`).** Reactieve auto-settle → eenmalige deterministische
  seed (alle orgs aan bij elke load, init-semantiek A); balk alleen op Overzicht, inert op de praatplaat.
- **Afgeleide gebruikt-lijn org→app (3-1, `559a34c`).** Read-only edge, 1:1 spiegel van de eigenaar-edge
  (dangling-guard + scope-add); gebruikt-ring (default aan, dragend via de ego-kring — geen IMPACT_RINGEN);
  bezit+gebruik = twee lijnen; dode afdeling-sub-picker weg.
- **Layout-herziening (samen in `559a34c`).** Samenval-fix (`animate:false`), Overzicht=`grid`
  (centrumloos, deterministisch; `cose` afgewezen wegens niet-determinisme), Praatplaat=`concentric`+
  vensterverhouding-ellips (alleen uitrekken, clamp ≤1.7), grotere knopen; layout-invariant "geen twee
  nodes op dezelfde positie" geborgd via `kaartLayout.test.js` (echte cytoscape).
- **Skills: 12 LI033-patronen** vastgelegd (`ef17fed`) over werkprotocol/tests/frontend/ux/resilience/
  domeinmodel.

## Top-5 prioriteiten volgende sessie (ADR-040 vervolgfasen)
1. **Terug/vooruit-navigatie terugbouwen** (VERPLICHT, uitgesteld) — history als losse laag bovenop de
   weergave-state.
2. **Interactie-basis** — klik = highlight + rest dimmen + verplaatsbare popup (details + relaties +
   link); dubbelklik = hercentreren (bestaat al).
3. **De 4 component-ringen volledig inrichten** (fase 2; praatplaat toont nu de ego-kring/skelet).
4. **Overige objecttypes centreerbaar** (contract/leverancier/afdeling/persoon-rol/infra) — ring-definitie
   per type op de praatplaat-motor.
5. **LI033b-stash-beslissing** (droppen vs. referentie) + herbevestigen ADR-036 coarse-UI /
   partij-picker-scope / LI032-restpunten.

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
