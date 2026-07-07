# LIKARA Changelog V034

**Datum**: 2026-07-07
**Sessie**: LI033 — ADR-040 kaart-herbouw (Fase 1)

## Wijzigingen

### Landschapskaart — ADR-040 herbouw (Fase 1)
- **Deterministische render-eigenaar / fcose weg** (`bf5c287`): één opbouw → één layout → fit via de
  layout-`stop`-callback. Lost de flits- en edges-onzichtbaar-bug structureel op.
- **Tweedeling Overzicht/Praatplaat** met expliciete weergave-state (`weergave: 'overzicht' |
  'praatplaat'`) + zichtbare schakelaar (2a, `e8fe7d3`). De set-grootte-afgeleide modus is vervangen; de
  **Impact-verkenner is afgeschaft**. "Hele landschap" = Overzicht zonder geseed centrum.
- **Voorspelbare organisatie-scope** (2b, `e7f74ef`): reactieve auto-settle → eenmalige deterministische
  seed (alle aanwezige orgs aan bij elke load, init-semantiek A); scope-balk alleen op Overzicht, inert op
  de praatplaat (geen stille organisatie-verberging).
- **Afgeleide gebruikt-lijn org→app** (3-1, `559a34c`): read-only edge, 1:1 spiegel van de eigenaar-edge
  (dangling-guard + scope-add van de gebruiker-org); gebruikt-ring (default aan, dragend via de ego-kring
  — geen aparte impact-bedrading); bezit + gebruik = twee lijnen. Dode afdeling-sub-picker verwijderd.
- **Layout-herziening** (samen in `559a34c`): samenval-fix (`animate:false`), **Overzicht = `grid`**
  (centrumloos, deterministisch; `cose` afgewezen wegens niet-determinisme), **Praatplaat = `concentric` +
  vensterverhouding-volgende ellips** (alleen uitrekken, clamp ≤1.7), grotere knopen (font 11→14).
  Layout-invariant "geen twee nodes op dezelfde positie" geborgd via `frontend/tests/kaartLayout.test.js`
  (echte cytoscape).

### Skills
- **12 herbruikbare patronen** uit de sessie vastgelegd (`ef17fed`) in likara-werkprotocol/tests/frontend/
  ux/resilience/domeinmodel (o.a. read-only-eerst boven aannames, volledige suite bij een gedeeld symbool,
  deterministische layout + render-eigenaar, filter = niet-destructieve lens, browser-console als eerste
  diagnose-instrument, afgeleide read-only kaart-edges spiegelen een bestaande edge).

### Docs
- ADR-040 bijgewerkt naar de gebouwde realiteit (grid/ellips-besluiten, gebruikt-lijn via ego-kring,
  opgeloste open subknopen); OPVOLGPUNTEN/NEXT_SESSION/PROJECTGEHEUGEN + TST-V034-validatierapport.

## Techniek
- **Tests**: backend 951 passed / 2 skipped · frontend 71 files / 840 groen · build clean.
- **Migratie-head**: `0054_contactpersoon_ref` (ongewijzigd — geen schema). Engine onaangeroerd; enig
  backend-raakvlak = de afgeleide read-only gebruikt-edge.
