# SESSIESTART — LIKARA V027

**Datum**: 2026-07-01
**Platform**: LIKARA — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/likara/ bestaat
   - Zo ja: normale modus — lees alle likara-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — LIKARA V027 — [N] skills geladen"
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

# SESSIE_BRIEFING.md — LIKARA V027

**Gegenereerd**: 2026-07-01

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V027 |
| Datum | July 2026 |
| Commit | 73413d7 |
| Tests | backend 944/2/0, frontend 745/745 |
| TST-rapport | TST-V027-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
73413d7 feat(engine): LI058 Slice 2 — scoring per type activeren + profiel-backfill bij togglen
a7c4b1d feat(datamodel): LI057 Slice 1 — transitie-attributen component-breed + migratiepad-rename
b99b901 test(auth): OP-30 — cookie_secure expliciet in test, env-onafhankelijk
4f25ba2 feat(frontend): scope → "Organisaties in beeld" (overlay, default aan) + dode-code-opruiming (LI053)
9643919 fix(frontend): Impact-verkenner — volledige reset + telling/modus op geresolveerde leden (LI052)
```

---

## Prioriteiten volgende sessie

# LIKARA — Next Session (LI059)

> **Sessie LI057+LI058 (V027):** component-focus-herfundering Slice 1 + Slice 2 geland.
> - **Slice 1 (LI057):** `migratiepad`/`complexiteit`/`prioriteit` component-breed (basis-`component`,
>   NOT NULL + defaults); enum `tijdelijk_gedeeld → gedeeld`. Expand met dual-write naar de behouden
>   applicatie-subtabel. Migratie 0045.
> - **Slice 2 (LI058):** scoren per type via `checklist_dragend`; `database` beoordeeld (migratie 0046
>   + seed + 6-vragen startset); **profiel-backfill** bij `checklist_dragend` False→True (platform-toggle
>   → per-tenant RLS-scoped backfill, idempotent; True→False = profielen inert). Engine al generiek.
> - **OP-30:** env-afhankelijke auth-cookie-test deterministisch gemaakt (afgerond).
>
> Laatste commit: `73413d7`. Tests: backend **944/0** (2 skipped) · frontend **745**. Migratie-head **0046**.

## Top-5 prioriteiten (volgende sessie)

1. **Slice 3 (contract)** — `applicatie`-subtabel droppen (`migratiepad/complexiteit/prioriteit`) +
   `applicatie_service`/routes/schemas opheffen in `component_service`. GATE, engine-rakend,
   dubbele borging + reseed. (Dual-write vervalt; component wordt de enige bron.)

2. **Slice 4 (frontend)** — één uniform `ComponentFormulier` (de drie velden voor álle typen) +
   type-wissel-UX met data-waarschuwing; `ApplicatieFormulier`/`ApplicatieDetail` retireren.

3. **Slice 5** — tests + TST + **ADR-021/022 afronding** (herfundering formeel sluiten).

4. **Componenttype-catalogus uitbreiden** (config, ADR-026 ArchiMate-typering): integratie-/
   koppelvoorziening, landelijke voorziening/basisregistratie, server/compute; **consolidatie**
   `applicatieserver`+`middleware` → systeemsoftware/middleware. Daarna beoordeelbare typen ná
   database aanzetten (fileshare → SaaS-dienst; Bert vult de vragen in de UI).

5. **Render-/orkestratielaag Impact-verkenner herbouwen** (ná component-focus) — één deterministische
   render-eigenaar, géén cascade, met **echte** render-verificatie (headless-cytoscape/e2e) i.p.v.
   mocks. De mislukte LI054/LI055-render-patches zijn nooit gecommit (schone basis).

## Openstaande punten (volledig)

### Component-focus-herfundering (Variant A besloten)
- Q1 per-type configureerbaar (`checklist_dragend`), Q2 velden component-breed NOT NULL + defaults,
  Q3 subtabel droppen (Slice 3), Q4 type vrij wijzigbaar met data-safety, Q5 enum-rename gedaan.
- Checklist-beheer is **tenant-scoped** (ADR-022 W1) — geen platform-brede checklist-baseline (bewust);
  platformbeheerder togglet `checklist_dragend` + baseline-inhoud in de seed.

### Impact-verkenner
- **Render-bug** (edges onzichtbaar op preset-pad; `nodes:visible` inzakking) — onopgelost, geagendeerd
  voor de render-herbouw (top-5 #5). Logica/model bewezen correct; zit in de echte cytoscape-render.
- Modus ego→impact ontkoppelen van set-grootte (ADR-033-revisie) — nog niet opgepakt.
- Swimlane (ADR-034, geparkeerd); Saved views als permanente hoofdingang (Fase D).

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


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V027"
4. Wacht op START: [naam] van Bert

