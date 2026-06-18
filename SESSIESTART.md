# SESSIESTART — CompliData V012

**Datum**: 2026-06-18
**Platform**: CompliData — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/complidata/ bestaat
   - Zo ja: normale modus — lees alle complidata-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — CompliData V012 — [N] skills geladen"
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

# SESSIE_BRIEFING.md — CompliData V012

**Gegenereerd**: 2026-06-18

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V012 |
| Datum | June 2026 |
| Commit | 0a11038 |
| Tests | 769 backend + 330 frontend groen (1 pre-existing env-test) |
| TST-rapport | TST-V012-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
0a11038 fix(partij): leden-overzicht filtert op organisatie + server-side sorteerbaar (Naam/Aard) en gepagineerd
b2b1216 feat(partij): ADR-024 slice 2a-bis — partij-lidmaatschap (persoon/afdeling → organisatie)
0e02e2d feat(partij): ADR-024 slice 2a — Partijen-beheer (persoon + afdeling), aard-filter, PARTIJ-recht
8923114 fix(dashboard): label "Open blokkades" → "Actieve blokkades" (terminologie)
988e337 feat(blokkades): component-kolom + type met doorklik naar juiste detailscherm (checklistvraag gemarkeerd)
```

---

## Prioriteiten volgende sessie

# NEXT_SESSION.md — CompliData V011

**Gegenereerd**: 2026-06-17 (sessie DC010)
**Build**: V010 → **V011**
**Laatste feature-commit vóór de afsluiting**: `f5bc0ed` (ADR-023 Fase F — F-3 stap 2, signalering); de afsluit-commit (docs/skills/build) volgt hierop.
**Migratie head**: `0024_adr023_vraagbetekenis`
**Tests**: 746 backend + 311 frontend groen (1 pre-existing, omgevingsgebonden env-test `test_auth_pkce`)

---

## Stand van zaken (V011) — ADR-023 Fase F AFGEROND

Hele Fase F geland deze sessie (boven op de in V010 geleverde Fase A–E):

- **F-6** (`d6ecc42`) — `checklist_dragend`-drift hersteld (seed expliciet; demo-type → `client_software`).
- **F-1** (`ec4f1ba`) — migratielaag frontend-overzicht (Migratie-navgroep, 4 lijst-views).
- **Diverse UI** (`1b5fbb3`/`0d7a5cf`/`1faff1c`/`80cfd54`/`b81d8e8`) — blokkade-herkomst, checklist/blokkade-weergave, dashboard-doorklik, multi-select statusfilter, server-side sorteerbare componententabel.
- **F-4** (`4a1ae36`) — platform-beheerscherm relatie-kenmerk-catalogus (`dispositie`/`relatie_rol` beheerbaar).
- **F-2** (`77b643b`) — cross-element laagprojectie (read-only architectuuroverzicht, beide typing-bronnen).
- **F-3 stap 1** (`69ae820`) — betekenis-marker op checklistvraag (`vraagbetekenis_optie`-catalogus + `betekenis`-kolom + cross-tenant datamigratie `0024`).
- **F-3 stap 2** (`f5bc0ed`) — consistentie-signalering technische plaatsing (`GET /signalen/plaatsing` + signalenlijst-view).

Score blijft de enige lifecycle-driver — engine onaangeroerd, dubbel geborgd (offline import-afwezigheid + read-only bronscan + live geen-mutatie). Skills (db/backend/frontend/tests) bijgewerkt naar V010/V011 met de F-3-patronen (betekenis-marker, cross-tenant datamigratie, signalering-afleiding, werkwijze-lessen).

---

## Top-5 prioriteiten volgende sessie

1. **ADR-024 — Organisatorische actoren** — starten met het **leverancier-feitenrapport** (read-only VALIDATIE): hoe leverancier vandaag in het datamodel/relatiemodel zit en wat een actor-laag raakt. Daarna gefaseerd bouwen (gates per schema-slice).
2. **OPVOLGPUNTEN.md tracked/untracked-discrepantie oplossen** — het bestand is feitelijk *tracked* (niet untracked zoals bouwopdrachten aannemen). Besluit: bestand officieel als tracked projectbestand behandelen (en de "untracked"-aanname uit toekomstige opdrachten halen), óf gitignoren. Klein, eerst beslissen.
3. **Signalering-uitbreidingen (F-3 follow-up, OPVOLGPUNTEN)** — badge op component-detail + dashboard-telling-doorklik "componenten met plaatsingssignaal". Licht/additief (read-side/frontend) → doorloop.
4. **Latente `applicatie.checklist_dragend`-drift** (OPVOLGPUNTEN) — vóór code de vlag voor `applicatie` gaat vertrouwen: seed ↔ migratie 0009 in lijn brengen.
5. **checklist-dragend als beheerder-functie** (OPVOLGPUNTEN) — productkeuze + type-specifieke vragen; onboarding/ADR-werk.

---

## Bekende risico's en aandachtspunten

- **Na een `down -v`-reset opnieuw inloggen in de UI** (verlopen sessie) — géén bug.
- **Pre-existing env-test** `test_auth_pkce` (Secure-cookie, DB-onafhankelijk) — omgevingsgebonden, in deze omgeving groen.
- **Cross-tenant datamigratie draait als cd_admin (superuser, bypasst FORCE RLS)** — bij een toekomstige backfill: geen tenant-filter nodig; cd_app/cd_platform bypassen RLS NIET.

---

## Werkwijze (triggerdiscipline)

Elke opdracht-`.md` begint op **regel 1** met `START: [taaknaam]`. **`AKKOORD: commit`** is exclusief de commit-trigger op een groen (gate-)rapport. Schema-rakende slices = **gate** vóór commit; licht/additief = doorloop. CC verifieert zélf de groene staat vóór elke commit. Eén vraag/advies tegelijk. Reset-procedure: `docs/LOKAAL-TESTEN.md`. Startpunt volgende sessie: `docs/_output/CompliData_Sessiestart_V011.zip` → **ADR-024 (leverancier-feitenrapport)**.


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — CompliData V012"
4. Wacht op START: [naam] van Bert

