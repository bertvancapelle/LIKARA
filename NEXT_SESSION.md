# LIKARA — Next Session (V028)

> **Sessie LI059 (V028):** component-focus-herfundering **volledig afgerond** — `component` is de
> enige bron in data/API/RBAC/audit.
> - **Slice 3 (LI059, migratie 0047):** `applicatie`-subtabel gedropt; `applicatie_service` als dunne
>   facade over `component`; dual-write weg; byte-compat behouden. (`03360ea`)
> - **Slice 4:** frontend-cutover — één `ComponentFormulier` (3 transitie-velden voor élk type) + één
>   rijk `ComponentDetail` (tab-IA, conditioneel); `ApplicatieFormulier`/`ApplicatieDetail` geretireerd;
>   `/applicaties*`-routes → redirects. (`6fa655e`)
> - **FacadeOpruiming:** volledige purge — `routes/applicatie.py`/`schemas/applicatie.py`/
>   `applicatie_service.py` + `api.applicaties` verwijderd; `Entiteit.APPLICATIE`/audit-allowlist/
>   objecthistorie-tak weg (RBAC-matrix 23→22); validators → `schemas/_validators.py`; creatie-kern →
>   `component_service`. (`1c40814`)
> - **Slice 5:** ADR-021/022 slotsecties "Eindstaat" + register + `likara-domeinmodel §1` bijgetrokken.
>
> Laatste commit: `1c40814`. Tests: backend **865/0** (2 skipped) · frontend **717**. Migratie-head **0047**.

## Top-5 prioriteiten (volgende sessie)

1. **Componenttype-catalogus uitbreiden** (config, ADR-026 ArchiMate-typering): integratie-/
   koppelvoorziening, landelijke voorziening/basisregistratie, server/compute; **consolidatie**
   `applicatieserver`+`middleware` → systeemsoftware/middleware. Daarna beoordeelbare typen ná
   database aanzetten (fileshare → SaaS-dienst; Bert vult de vragen in de UI).

2. **Render-/orkestratielaag Impact-verkenner herbouwen** (ná component-focus) — één deterministische
   render-eigenaar, géén cascade, met **echte** render-verificatie (headless-cytoscape/e2e) i.p.v.
   mocks. De mislukte LI054/LI055-render-patches zijn nooit gecommit (schone basis).

## Openstaande punten (volledig)

### Component-focus-herfundering — ✅ AFGEROND (LI057–LI059, migraties 0045–0047)
- Q1 per-type configureerbaar (`checklist_dragend`), Q2 velden component-breed NOT NULL + defaults,
  Q3 subtabel gedropt (0047), Q4 type vrij wijzigbaar met data-safety, Q5 enum-rename gedaan.
- Checklist-beheer is **tenant-scoped** (ADR-022 W1) — geen platform-brede checklist-baseline (bewust);
  platformbeheerder togglet `checklist_dragend` + baseline-inhoud in de seed.

### Impact-verkenner
- **Render-bug** (edges onzichtbaar op preset-pad; `nodes:visible` inzakking) — onopgelost, geagendeerd
  voor de render-herbouw (top-5 #2). Logica/model bewezen correct; zit in de echte cytoscape-render.
- Modus ego→impact ontkoppelen van set-grootte (ADR-033-revisie) — nog niet opgepakt.
- Swimlane (ADR-034, geparkeerd); Saved views als permanente hoofdingang (Fase D).
- **Los test-hygiëne-punt (pre-existing):** `LandschapskaartView.test.js` meldt ~29 unhandled-rejection-
  console­ruis uit de Cytoscape-mock (async teardown) — **geen falende test** (frontend 717/717). Bij de
  render-herbouw meenemen (schonere mock/teardown).

### ADR-035 Signalering
- Slice 3: "Registratie onvolledig" (configureerbare score-drempelwaarde) — uitgesteld.
- blokkade_zonder_eigenaar — structureel onmogelijk zonder schema-/semantiekherziening.
- badges op GebruikersgroepDetail/BlokkadeDetail — uitgesteld tot die detail-pagina's bestaan.

### Platform / detail-pagina's
- GebruikersgroepDetail + BlokkadeDetail standalone pagina's ontbreken.

### Cosmetic/klein
- Zoekbalk-contextlabel "Component toevoegen aan beeld" in kaart-modus.

### Strategisch (parked)
- Export/import/rapportage — scope apart te bepalen.
- **DC013** — GitHub-repo/remote-rename + lokale `~/complidata/`-map opruimen (Berts actie).
- Deploy-side `.env`/secrets bijwerken op andere omgevingen; `~/likara/secrets/` daadwerkelijk vullen.
