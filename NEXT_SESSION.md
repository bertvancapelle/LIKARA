# NEXT_SESSION.md — LIKARA V024

**Gegenereerd**: 2026-06-29 (sessie-afsluiting LI023)
**Build**: V023 → **V024**
**Migratie head**: `0042` (`0042_adr033_opgeslagen_view`) — LI023 had géén schema-/migratiewijziging
(alles frontend + docs/ADR).
**Tests**: frontend **698 groen** (63 files) + `vite build` + `test:css-build` ok; backend **910 passed / 2 skipped**.
**TST**: `docs/TST-V024-Validatierapport.md` — 0 kritieken.

---

## Stand van zaken (V024) — Landschapskaart Fase B compleet + UX-fixes + ADR-besluiten

Deze sessie (LI023):
- **Werkprotocol** herbevestigd + geborgd in `likara-werkprotocol` (`a367d3d`).
- **Slice 2b** — 4-ingangen-beginscherm + "in beeld"-chips (`b5a6e33`); beginscherm expliciet sluiten
  via "Toon N op de kaart" (`cab0988`).
- **Slice 2b UX-fixes** — z-index/pointer-events-blokkade (`94aa12e`), actieknop als actiebalk bovenaan
  (`ef68c40`), zoekterm/dropdown reset na aanvinken (`a4979fa`).
- **Slice 5** — detail-paneel set-acties: "Haal buren erbij" + "Voeg alle componenten toe" (`0b018bd`).
- **Slice 6** — dode `cytoscape-dagre`-dependency verwijderd (`776ab38`).
- **Scope-fix** — scope-balk filtert in subgraaf-modus org/gg-nodes i.p.v. de componenten (`097d1e9`).
- **Generieke re-layout** — watcher op `getekendeNodes`-compositie + debounce (`1019d8f`).
- **PRODUCTVISIE.md** toegevoegd (`3fc3414`); **ADR-025/026 nadere besluiten + ADR-030 besloten +
  ADR-035 Signalering** (`ac4afb7`); **root-OPVOLGPUNTEN.md verwijderd** (`0e16999`).

Landschapskaart Fase B (set-gestuurd beginscherm + ingangen + interactie) is daarmee functioneel rond;
verfijningen op een opgebouwde set (scope/impact/swimlane-semantiek) zijn bewust uitgesteld na live testing.

---

## Vertrekpunt volgende sessie — top-5 prioriteiten (BESLOTEN, nog te bouwen)

1. **ADR-035 — Signalering registratiegaten.** Coherent Signalering-scherm (absorbeert
   Plaatsingssignalen), 10 signaaltypen in 2 niveaus, badges op entiteiten + centraal overzicht.
   Read-only, geen engine-poort. n≥2-discipline: bouw eerst 2 concrete signalen (component zonder
   eigenaar + contract zonder leverancier).
2. **ADR-025 — "Bekijk op kaart"-knop** op alle componentdetailpagina's → vooringestelde ego-view op
   de Landschapskaart (hergebruik bestaande infra). Koppelingenkaart-visueel vervalt.
3. **ADR-026 — ArchiMate-typering verplicht** in het componenttype-formulier (3 verplichte velden,
   gesloten lijsten/code-constanten; seed compliant maken bij de slice).
4. **ADR-030 — Contract-dekking per-band** naast contract-breed (Optie B).
5. **Klaarverklaring-blok op ComponentDetail** — MigratiegereedheidSectie + knop (ADR-027 compleet;
   triviale implementatiegap). + **interactieve legenda als type-filter** (klein).

## Openstaande punten / bewust uitgesteld
- **Subgraaf-semantiek** (filter/scope/impact/swimlane op een opgebouwde set) — eigen ontwerpslice na live testing.
- **Swimlane** — geparkeerd (ADR-034, HTML/CSS-herwrite).
- **Saved views als permanente hoofdingang** (Fase D); "zoek-erop-dan-toon-het"-principe.
- **Nieuw strategisch thema (parked)**: export/import/rapportage — scope/fasering apart te bepalen.

Zie `docs/OPVOLGPUNTEN.md` (de enige backlog-bron) voor het volledige overzicht.
