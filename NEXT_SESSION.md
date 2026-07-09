# NEXT_SESSION.md — LIKARA V036

**Gegenereerd**: 2026-07-09
**Vorige build**: V036
**Branch**: master

> **Sessie LI035 — lijststaat-patroon + ADR-042 volledig (procesregister t/m roll-up). Geland (V036).**
>
> Afgerond in LI035:
> - **Lijststaat-patroon** — `useLijstStaat` (sessionStorage-momentstaat, route-leave + beforeunload,
>   precedentie deep-link > bewaard > default) op partij-/component-/contract-/proces-lijst (`9128a24`).
> - **ADR-042 volledig, 5 slices**: procesregister (nestbare boom, element-subtype, migraties 0056/0057,
>   `cc43418`) · applicatiefunctie-catalogus + koppelregel procesvervulling (0058/0059, `ddb7b7a`) ·
>   proces-schermen met regel-acties + MeldingBanner (`3a65c3b`) · componentkant: vier-vragen-Overzicht +
>   overlay-formulier (`0c4fe60`) · roll-up-inzicht + organisatie-proceskijk + succes-toast-standaard
>   (`8a76f55`).
> - **Zes browsercheck-bevindingen → zes systeembrede patronen**: Dialog-primitive (vaste kop/voetbalk,
>   min-h-0, scroll-schaduw in primair-blauw), breedte-override-borging, MeldingBanner (kleur+icoon+
>   positie+scroll-vangnet), samengevoegd "Onderliggende processen"-blok, succes-toast-standaard
>   (`toastSucces`), regel-acties-patroon.
> - **Acht likara-skills** bijgewerkt met de LI035-patronen + correcties (CD004-scope, beheerrol=dimensie,
>   AppLayout-testlocatie, IMPACT_RINGEN afgeschaft); globale CLAUDE.md-trailer → Claude Fable 5.
>
> Tests: backend **997** (2 skipped) / frontend **80 files, 965** groen. Migratie-head **0059**.

---

## Volgende stappen

### 1e taak — ADR-034-herbouw: lagenweergave op de kaart-selectie, mét proces-laan

De lagenweergave opnieuw opbouwen op de kaart-selectie. Drie LI035-ontwerpnotities meenemen:
- **nesting** van de procesboom binnen de business-laan (hoe diep tonen);
- **selectie-semantiek** (wat betekent een proces-klik voor de kaart-set);
- **roll-up in de laan** (toont een hoofdproces de doorgerolde componenten of alleen de directe).

**Kader:** ontwerp eerst (PNA + Bert), dan bouwen; de proceswereld (ADR-042) is de nieuwe laag die
deze weergave af moet dekken.

### Daarna — zie OPVOLGPUNTEN.md (geprioriteerd, Stand V036)
Top-5 LI036: (1) ADR-034-herbouw lagenweergave; (2) audit-dekking entiteit-deletes (systemisch
core-execute-gat, hoog); (3) UI-consistentie-bundel (11 dialoog-klonen → BevestigVerwijderDialog,
2 warn-banners → MeldingBanner, PartijRollenSectie-verwijder-asymmetrie); (4) kaart component-breed
(ADR-verkenning); (5) beginscherm-/kaartverfijningen. Daarna: GEMMA-procesimport (eigen ADR-spoor,
ná ADR-034).

### Staande werkafspraken (ongewijzigd)
- Startregel: uitsluitend op `START: [naam]`; `AKKOORD: commit` is de exclusieve commit-trigger.
- UX-first: gebruikerservaring is het uitgangspunt, techniek is vangrail; browsercheck-bevindingen
  → patroon-onderzoek vóór punt-fixes (LI035-les).
- Gate-discipline: schema-/UX-slices stoppen met gate-rapport + browsercheck-draaiboek vóór commit;
  vitest altijd vanuit `frontend/`; backend-suite vanaf de repo-root.

---

## Stand

| Veld | Waarde |
|------|--------|
| Build | V036 |
| Datum | 2026-07-09 |
| Tests | backend 997 (2 skipped) / frontend 80 files, 965 groen |
| Migratie-head | 0059_adr042_procesvervulling |
| TST-rapport | TST-V036-Validatierapport.md |
| Kritieke bevindingen | 0 |
| Skills | acht likara-skills bijgewerkt (LI035-patronen + correcties) |
